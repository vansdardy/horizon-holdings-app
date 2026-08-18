# -*- coding: utf-8 -*-
"""
Local backend for the Buffett-style 78-stock portfolio dashboard.

Run:  python server.py           -> http://127.0.0.1:8000
Env:  MARKETDATA_MOCK=1          -> use deterministic fake prices (testing only)
      PORTFOLIO_DB=/path/to.db   -> override DB location
      FETCH_HOUR=18              -> local hour for the daily fetch (default 18)
"""
import os
import re
import sys
import math
from contextlib import asynccontextmanager
import datetime as dt
import threading
import time
import traceback

# Force UTF-8 for our own output before anything else runs, rather than trust
# PYTHONIOENCODING alone. desktop/main.js sets that env var when it spawns this
# process, and that is necessary — but it is not sufficient. A user reported a
# crash on Windows with a non-UTF-8 system locale: "UnicodeEncodeError:
# 'charmap' codec can't encode characters ... character maps to <undefined>",
# raised from inside a bundled dependency's own text handling, which reads the
# OS locale codepage directly rather than going through sys.stdout. No print()
# in this codebase contains a character cp1252 cannot represent, so the trigger
# was not ours to fix at the source — but reconfiguring the streams here means
# every later write through them, including a library's, inherits utf-8 too.
#
# This also covers a gap PYTHONIOENCODING alone leaves open: running
# `python server.py` directly, as this project's own README tells developers
# to do, never goes through Electron's spawn() at all, so on a non-UTF-8-locale
# Windows machine it previously had no protection whatsoever.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import config  # loads .env before anything reads os.environ
import db
import universe as u
import index_engine
import marketdata

# PyInstaller unpacks bundled data files (static/) under sys._MEIPASS, which in
# a --onedir build is the _internal directory — NOT where __file__ resolves for
# a frozen module. Read-only assets come from the bundle; anything written at
# runtime goes next to the database instead (see api_backup).
if config.FROZEN:
    HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
FETCH_HOUR = config.FETCH_HOUR

def _start_scheduler():
    t = threading.Thread(target=_scheduler, daemon=True)
    t.start()
    config.print_summary()
    print(f"[startup] scheduler running (daily fetch at {FETCH_HOUR}:00 local)")
    print(f"[startup] data source: {'MOCK — NOT REAL PRICES' if marketdata.USE_MOCK else 'Yahoo Finance'}")
    print(f"[startup] database: {db.DB_PATH}")
    _idx = _find_index()
    if _idx:
        print(f"[startup] frontend: {_idx}")
    else:
        print(f"[startup] WARNING: index.html not found in "
              f"{os.path.join(STATIC, 'index.html')} or {os.path.join(HERE, 'index.html')} "
              f"— the API works, but the web page will show setup instructions instead")


@asynccontextmanager
async def _lifespan(app):
    _start_scheduler()
    yield


app = FastAPI(title="Portfolio NAV Service", version="1.0", lifespan=_lifespan)

# Allows opening static/index.html directly from disk (file:// sends Origin: null)
# while still refusing arbitrary remote sites. The server binds to 127.0.0.1 only.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(null|file://.*|https?://(localhost|127\.0\.0\.1)(:\d+)?)$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

db.init()


@app.exception_handler(RequestValidationError)
def _validation_handler(request, exc):
    """
    FastAPI echoes the offending input back in its 422 body. If that input is
    inf/NaN the response itself fails to serialize and turns into a confusing 500,
    even though validation worked correctly. Scrub non-finite values so the client
    gets a proper 422.
    """
    def clean(o):
        if isinstance(o, float) and not math.isfinite(o):
            return str(o)
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        return o

    return JSONResponse(status_code=422, content={"detail": clean(exc.errors())})

_fetch_lock = threading.Lock()


# ----------------------------------------------------------------- core job
def run_daily_update(day_offset=0, window=1):
    """
    Fetch -> PERSIST TO DISK -> recompute NAV. Safe to call repeatedly.

    Persistence happens before valuation, so even if the NAV math fails the raw
    market data is already banked. Valuation uses the latest stored close per
    constituent as of each session (standard index practice), which keeps NAV
    correct when an exchange is on holiday instead of pretending a stale quote
    is today's.

    Any sessions inside the fetched window that have no NAV row yet are computed
    in chronological order, so a few days of downtime self-heal rather than
    leaving permanent holes in the track record.
    """
    with _fetch_lock:
        valuation_date, price_rows, fx_rows = marketdata.fetch(
            day_offset=day_offset, window=window)

        # --- persist raw market data FIRST ---
        n_p = db.upsert_prices(price_rows)
        n_f = db.upsert_fx(fx_rows)
        db.set_meta("last_fetch_ok", dt.datetime.now().isoformat(timespec="seconds"))
        db.set_meta("data_source", "MOCK" if marketdata.USE_MOCK else "yahoo")
        db.set_meta("last_fetch_error", "")

        # --- which sessions still need a NAV point? ---
        have = db.nav_dates()
        sessions = sorted({r["date"] for r in price_rows})
        inception = db.get_meta("inception_date")

        if not inception:
            # First ever run: seed at the NEWEST session only.
            # Seeding at the oldest bar in the lookback window would try to value
            # a date whose FX bars may not exist yet (FX and equity series do not
            # start on the same day), and backfilling before inception is
            # meaningless anyway — the curve is defined to start at deployment.
            todo = [valuation_date]
        else:
            todo = [d for d in sessions if d not in have and d >= inception]
            if not todo:
                todo = [valuation_date]

        results, backfilled, skipped = [], [], []
        # Every currency except the internal numeraire needs a USD rate; the
        # base/reporting currency needs one too (unless it IS the numeraire).
        need_ccy = [c for c in u.CURRENCIES if c != u.NUMERAIRE]
        if u.BASE_CCY != u.NUMERAIRE and u.BASE_CCY not in need_ccy:
            need_ccy.append(u.BASE_CCY)

        for d in todo:
            fx = db.fx_asof(d)
            missing_fx = [c for c in need_ccy if not fx.get(c)]
            if missing_fx:
                # Cannot translate every currency into USD on this date, so any
                # NAV computed here would be wrong. Skip it rather than crash or
                # silently mis-value.
                skipped.append({"date": d, "reason": f"missing FX: {','.join(missing_fx)}"})
                continue

            asof = db.prices_asof(d)
            if not asof:
                skipped.append({"date": d, "reason": "no prices on or before this date"})
                continue

            prices = {t: v["close"] for t, v in asof.items()}
            stale = [t for t, v in asof.items() if v["date"] < d]
            try:
                r = index_engine.update(d, prices, fx)
            except index_engine.StaleValuationError as e:
                skipped.append({"date": d, "reason": str(e)})
                continue
            r["stale_constituents"] = len(stale)
            r["stale_tickers"] = sorted(stale)[:10]
            results.append(r)
            if d != valuation_date:
                backfilled.append(d)

        if not results:
            reasons = "; ".join(f"{s['date']}: {s['reason']}" for s in skipped[:4]) or "no sessions returned"
            raise index_engine.StaleValuationError(
                f"no NAV point could be computed. {reasons}")

        out = dict(results[-1])
        out["rows_persisted"] = n_p + n_f
        out["sessions_computed"] = len(results)
        out["backfilled_dates"] = backfilled
        out["skipped_sessions"] = skipped
        out["symbols_missing"] = sorted(set(u.UNIVERSE) - {r["ticker"] for r in price_rows})
        return out


def run_fundamentals_update(force=False):
    """
    Refreshes P/E, dividend yield, and beta — but only once per calendar
    quarter (Jan/Apr/Jul/Oct 1), since these move slowly and the per-ticker
    endpoint that provides them is far heavier than the batched price fetch.
    `force=True` bypasses the quarter gate (used by the manual endpoint).
    """
    quarter = marketdata.current_quarter()
    if not force and db.get_meta("last_fundamentals_quarter") == quarter:
        return {"skipped": True, "quarter": quarter, "reason": "already fetched this quarter"}
    with _fetch_lock:
        rows, failed, flagged = marketdata.fetch_fundamentals(list(u.UNIVERSE.keys()))
        as_of = dt.date.today().isoformat()
        n = db.upsert_fundamentals(quarter, as_of, rows)
        db.set_meta("last_fundamentals_quarter", quarter)
        db.set_meta("last_fundamentals_fetch", as_of)
        db.set_meta("last_fundamentals_failed", ",".join(failed))
        db.set_meta("last_fundamentals_flagged", " | ".join(flagged))
        return {"skipped": False, "quarter": quarter, "as_of": as_of,
                "fetched": n, "failed": failed, "flagged": flagged}


def _scheduler():
    """
    Fires once per day at/after FETCH_HOUR, and catches up if the app was offline.

    Deliberately tracked under its OWN key (`last_scheduled_date`) rather than the
    shared `last_fetch_date`: a manual refresh in the morning must not cancel that
    evening's scheduled run, or the day would be permanently recorded at
    mid-session prices instead of the close.
    """
    consecutive_failures = 0
    while True:
        sleep_for = 600
        try:
            today = dt.date.today().isoformat()
            last = db.get_meta("last_scheduled_date")
            now = dt.datetime.now()
            if last != today and now.hour >= FETCH_HOUR:
                run_daily_update()
                db.set_meta("last_scheduled_date", today)
                db.set_meta("last_fetch_date", today)
                db.set_meta("last_fetch_error", "")
                consecutive_failures = 0
                print(f"[scheduler] daily update done for {today}")

                # Cheap to check every day; the function itself only actually
                # fetches once per calendar quarter (see run_fundamentals_update).
                try:
                    fr = run_fundamentals_update()
                    if not fr["skipped"]:
                        print(f"[scheduler] fundamentals updated for {fr['quarter']}: "
                              f"{fr['fetched']} ok, {len(fr['failed'])} failed, "
                              f"{len(fr.get('flagged', []))} flagged as implausible"
                              + (f" ({', '.join(fr['failed'][:10])})" if fr['failed'] else "")
                              + (f" [flagged: {'; '.join(fr['flagged'][:5])}]" if fr.get('flagged') else ""))
                except Exception as e:
                    # Non-fatal: fundamentals are a slow-moving nice-to-have,
                    # a failure here must never block the daily price/NAV update.
                    print(f"[scheduler] fundamentals update FAILED (non-fatal): {e}")
        except Exception as e:
            # A failure must not silently retire the scheduler for the rest of
            # the day: back off and retry, and surface the reason in /api/status.
            consecutive_failures += 1
            msg = f"{type(e).__name__}: {e}"
            db.set_meta("last_fetch_error", msg[:500])
            db.set_meta("consecutive_failures", consecutive_failures)
            print(f"[scheduler] attempt {consecutive_failures} FAILED: {msg}")
            if consecutive_failures <= 5:
                sleep_for = min(600, 60 * consecutive_failures)
            else:
                print("[scheduler] repeated failures; check /api/status and "
                      "/api/check_symbols, then POST /api/refresh manually")
        time.sleep(sleep_for)




# ----------------------------------------------------------------- models
class PositionIn(BaseModel):
    ticker: str
    shares: float = Field(ge=0, le=1e12)
    avg_cost: float = Field(ge=0, le=1e12)
    note: str = Field(default="", max_length=500)

    @field_validator("shares", "avg_cost")
    @classmethod
    def _finite(cls, v):
        if not math.isfinite(v):
            raise ValueError("value must be a finite number (NaN/Infinity rejected)")
        return v


class PositionsIn(BaseModel):
    positions: list[PositionIn] = Field(max_length=500)


class CashIn(BaseModel):
    ccy: str
    amount: float = Field(ge=0, le=1e12)

    @field_validator("amount")
    @classmethod
    def _finite_amt(cls, v):
        if not math.isfinite(v):
            raise ValueError("value must be a finite number (NaN/Infinity rejected)")
        return v


class CashListIn(BaseModel):
    cash: list[CashIn] = Field(max_length=20)


# ----------------------------------------------------------------- endpoints
@app.get("/api/fundamentals")
def api_fundamentals():
    """
    P/E, dividend yield, and beta as of the most recent quarterly fetch —
    NOT live. Every row carries its own `quarter` and `as_of` date so the
    frontend can show its actual age rather than implying same-day freshness.
    """
    latest = db.latest_fundamentals()
    last_q = db.get_meta("last_fundamentals_quarter")
    return {
        "rows": latest,
        "quarters_on_file": db.fundamentals_quarters(),
        "current_quarter": marketdata.current_quarter(),
        "last_fetch_quarter": last_q,
        "last_fetch_date": db.get_meta("last_fundamentals_fetch"),
        "last_fetch_failed": [t for t in (db.get_meta("last_fundamentals_failed") or "").split(",") if t],
        "last_fetch_flagged": [t for t in (db.get_meta("last_fundamentals_flagged") or "").split(" | ") if t],
        "up_to_date": last_q == marketdata.current_quarter(),
        "tickers_covered": len(latest),
        "tickers_total": len(u.UNIVERSE),
    }


@app.post("/api/refresh_fundamentals")
def api_refresh_fundamentals(force: bool = False):
    """
    Manual trigger for the quarterly fundamentals fetch. Without `force=true`
    this is a no-op outside the first day of a new quarter — matching the
    scheduler's own gate, so clicking it doesn't cause an off-schedule pull.
    """
    try:
        return {"ok": True, **run_fundamentals_update(force=force)}
    except Exception as e:
        raise HTTPException(500, f"fundamentals fetch failed: {e}")


@app.get("/api/universe")
def api_universe():
    w = u.target_weights()
    return {
        "base_ccy": u.BASE_CCY,
        "shares_outstanding": u.SHARES_OUTSTANDING,
        "initial_nav_base": u.INITIAL_NAV_BASE,
        "holdings": [
            {"ticker": t, "target_weight": w[t], **{k: v[k] for k in
             ("name", "yahoo", "country", "exchange", "ccy", "sector", "industry", "moat", "score",
              "name_en", "industry_en", "moat_en", "country_en", "exchange_en")}}
            for t, v in u.UNIVERSE.items()
        ],
    }


@app.get("/api/status")
def api_status():
    return {
        "data_source": db.get_meta("data_source", "none"),
        "is_mock": marketdata.USE_MOCK,
        "inception_date": db.get_meta("inception_date"),
        "last_fetch_ok": db.get_meta("last_fetch_ok"),
        "last_fetch_date": db.get_meta("last_fetch_date"),
        "last_scheduled_date": db.get_meta("last_scheduled_date"),
        "scheduled_today_done": db.get_meta("last_scheduled_date") == dt.date.today().isoformat(),
        "last_fetch_error": db.get_meta("last_fetch_error") or None,
        "latest_price_date": db.latest_price_date(),
        "nav_points": len(db.nav_history()),
        "fetch_hour": FETCH_HOUR,
        "config": config.effective(),
        "index_base_ccy": db.get_meta("index_base_ccy"),
        "base_ccy_mismatch": (db.get_meta("inception_date") is not None
                              and (db.get_meta("index_base_ccy") or u.NUMERAIRE) != u.BASE_CCY),
        "archive": db.archive_summary(),
        "fundamentals": {
            "current_quarter": marketdata.current_quarter(),
            "last_fetch_quarter": db.get_meta("last_fundamentals_quarter"),
            "last_fetch_date": db.get_meta("last_fundamentals_fetch"),
            "up_to_date": db.get_meta("last_fundamentals_quarter") == marketdata.current_quarter(),
            "tickers_covered": len(db.latest_fundamentals()),
        },
    }


@app.post("/api/refresh")
def api_refresh(day_offset: int = 0, window: int = 1):
    """Manual trigger. Useful on first run so you don't wait for the scheduler."""
    if day_offset != 0 and not marketdata.USE_MOCK:
        raise HTTPException(400, "day_offset is only available in MARKETDATA_MOCK=1 mode; "
                                 "real market history cannot be time-shifted")
    if not (1 <= window <= 30):
        raise HTTPException(400, "window must be between 1 and 30")
    try:
        r = run_daily_update(day_offset=day_offset, window=window)
        db.set_meta("last_fetch_date", dt.date.today().isoformat())
        return {"ok": True, **r}
    except index_engine.StaleValuationError as e:
        db.set_meta("last_fetch_error", str(e))
        raise HTTPException(409, str(e))
    except Exception as e:
        db.set_meta("last_fetch_error", str(e))
        raise HTTPException(500, f"fetch failed: {e}")


@app.get("/api/index_holdings")
def api_index_holdings():
    """
    The index's actual book: how many shares of each constituent it holds, and
    the cash left over in each currency.

    This exists to make NAV checkable rather than merely reported. The index buys
    whole shares only, so every position leaves a residual that stays as cash in
    the currency it was left in — and those two things together, marked at the
    latest close, are the whole of NAV. Publishing the ledger means a reader can
    add it up themselves instead of trusting the total.

    Valuation deliberately mirrors index_engine._mark rather than reimplementing
    it: same forward-filled prices (`prices_asof`), same FX, same USD numeraire.
    A second, subtly different valuation here would produce numbers that almost
    agree with the NAV series, which is worse than none.
    """
    holdings, cash = db.load_index_state()
    asof = db.latest_price_date()

    if not holdings or not asof:
        return {"seeded": False, "as_of": asof, "base_ccy": u.BASE_CCY,
                "holdings": [], "cash": [], "unpriced": [], "totals": {}}

    prices = db.prices_asof(asof)
    fx = db.fx_asof(asof)
    weights = u.target_weights()

    def to_base(amount_usd):
        """None rather than an exception: a missing base rate must not 500 the
        whole ledger, it just means the base-currency column cannot be filled."""
        if amount_usd is None:
            return None
        try:
            return index_engine.to_base(amount_usd, fx)
        except ValueError:
            return None

    rows, equity_usd, unpriced = [], 0.0, []
    for t, n in sorted(holdings.items()):
        meta = u.UNIVERSE.get(t)
        if meta is None:
            # A ticker the universe no longer carries. _mark ignores these too;
            # the next rebalance rebuilds holdings from the current universe.
            continue
        quote = prices.get(t)
        close = quote["close"] if quote else None
        value_local = close * n if close is not None else None
        value_usd = None
        if value_local is not None:
            try:
                value_usd = index_engine.to_usd(value_local, meta["ccy"], fx)
            except ValueError:
                value_usd = None
        if n and value_usd is None:
            unpriced.append(t)
        if value_usd:
            equity_usd += value_usd
        rows.append({
            "ticker": t,
            "name": meta["name"], "name_en": meta["name_en"],
            "country": meta["country"], "country_en": meta["country_en"],
            "ccy": meta["ccy"],
            "shares": n,
            "price": close,
            "price_date": quote["date"] if quote else None,
            "value_local": value_local,
            "value_usd": value_usd,
            "value_base": to_base(value_usd),
            "target_weight": weights.get(t, 0.0),
        })

    cash_rows, cash_usd = [], 0.0
    for ccy, amount in sorted(cash.items()):
        try:
            amount_usd = index_engine.to_usd(amount, ccy, fx)
        except ValueError:
            amount_usd = None
        if amount_usd:
            cash_usd += amount_usd
        cash_rows.append({"ccy": ccy, "amount": amount, "amount_usd": amount_usd,
                          "amount_base": to_base(amount_usd)})

    nav_usd = equity_usd + cash_usd
    for r in rows:
        r["actual_weight"] = (r["value_usd"] / nav_usd) if (r["value_usd"] and nav_usd) else 0.0

    nav_base = to_base(nav_usd)
    shares_out = u.SHARES_OUTSTANDING

    # A database migrated out of pence carries one visible scar: its GBP cash
    # pool is far bigger than buying whole shares should leave, because it was
    # filled by rounding down in hundred-times steps. Nothing is wrong with the
    # number — those are real pounds and the NAV counts them — but it is not the
    # number a correct allocation would have produced, so the page says so until
    # the next rebalance reinvests it.
    #
    # Measured, not flagged. The first version of this asked a meta key that the
    # migration set — which meant it could only ever be raised on a database that
    # had not already been migrated, so every user who took the previous release
    # promptly got the fix and never got the explanation. The condition is
    # directly observable, so observe it: buying whole shares leaves a residual
    # between zero and one share's price, making half the sum of the prices the
    # expected pool. Real pools land within a factor of two of that (every other
    # currency here sits between 0.5x and 1.7x); the pence bug leaves about 90x.
    # Ten times is far outside honest variation and far below the symptom.
    #
    # Deriving it also removes the need to clear anything: after a rebalance the
    # pool is rebuilt from scratch and the ratio falls back to about one, so the
    # notice disappears because the condition did, not because a flag was reset.
    cash_notice = None
    pence_names = [t for t in u.pence_quoted() if prices.get(t)]
    if pence_names:
        typical = sum(prices[t]["close"] for t in pence_names) / 2.0
        actual = cash.get("GBP", 0.0)
        if typical > 0 and actual > 10.0 * typical:
            excess_usd = None
            try:
                excess_usd = index_engine.to_usd(actual - typical, "GBP", fx)
            except ValueError:
                pass
            cash_notice = {
                "reason": "gbx_migration",
                "ccy": "GBP",
                "amount": actual,
                "typical": typical,
                "excess": actual - typical,
                "ratio": actual / typical,
                "excess_pct_of_nav": (excess_usd / nav_usd) if (excess_usd and nav_usd) else 0.0,
                "clears_on": "next annual rebalance",
            }

    return {
        "seeded": True,
        "cash_notice": cash_notice,
        "as_of": asof,
        "base_ccy": u.BASE_CCY,
        "numeraire": u.NUMERAIRE,
        "shares_outstanding": shares_out,
        "holdings": rows,
        "cash": cash_rows,
        "unpriced": unpriced,
        "totals": {
            "equity_usd": equity_usd, "cash_usd": cash_usd, "nav_usd": nav_usd,
            "equity_base": to_base(equity_usd), "cash_base": to_base(cash_usd),
            "nav_base": nav_base,
            "cash_pct": (cash_usd / nav_usd) if nav_usd else 0.0,
            "nav_per_share": (nav_usd / shares_out) if shares_out else None,
            "nav_per_share_base": (nav_base / shares_out) if (nav_base and shares_out) else None,
            "n_holdings": sum(1 for r in rows if r["shares"]),
        },
    }


@app.get("/api/nav")
def api_nav():
    pd = db.price_dates()
    return {
        "history": db.nav_history(),
        "stats": index_engine.stats(),
        "archive_range": {"first": pd[0], "last": pd[-1]} if pd else None,
    }


@app.get("/api/prices")
def api_prices():
    return {"latest": db.latest_prices_with_change(), "fx": db.latest_fx()}


@app.get("/api/positions")
def api_positions():
    """User positions joined with live prices, target weights, and drift."""
    prices = db.latest_prices()
    fx = db.latest_fx()
    pos = db.get_user_positions()
    cash = db.get_user_cash()
    weights = u.target_weights()

    rows, total_mv, total_cost = [], 0.0, 0.0
    for t, meta in u.UNIVERSE.items():
        p = pos.get(t, {})
        # defensive: never trust stored numbers blindly (hand-edited DB, older rows)
        shares = float(p.get("shares") or 0)
        avg_cost = float(p.get("avg_cost") or 0)
        if not math.isfinite(shares) or shares < 0:
            shares = 0.0
        if not math.isfinite(avg_cost) or avg_cost < 0:
            avg_cost = 0.0
        px_rec = prices.get(t)
        px = px_rec["close"] if px_rec else None
        ccy = meta["ccy"]

        mv_local = (px * shares) if (px is not None) else None
        cost_local = avg_cost * shares
        mv_usd = index_engine.to_usd(mv_local, ccy, fx) if mv_local is not None else None
        cost_usd = index_engine.to_usd(cost_local, ccy, fx) if cost_local else 0.0

        if mv_usd:
            total_mv += mv_usd
        total_cost += cost_usd or 0.0

        rows.append({
            "ticker": t, "name": meta["name"], "ccy": ccy, "country": meta["country"],
            "name_en": meta["name_en"], "country_en": meta["country_en"],
            "sector": meta["sector"], "target_weight": weights[t],
            "shares": shares, "avg_cost": avg_cost, "price": px,
            "price_date": px_rec["date"] if px_rec else None,
            "mv_local": mv_local, "cost_local": cost_local,
            "mv_usd": mv_usd, "cost_usd": cost_usd,
            "pnl_local": (mv_local - cost_local) if (mv_local is not None and shares) else None,
            "pnl_usd": (mv_usd - cost_usd) if (mv_usd is not None and shares) else None,
            "note": p.get("note", ""),
        })

    # ---- cash ----
    cash_rows, total_cash = [], 0.0
    for ccy, amt in sorted(cash.items()):
        if not amt:
            continue
        usd = index_engine.to_usd(float(amt), ccy, fx) if ccy != u.NUMERAIRE else float(amt)
        total_cash += usd
        cash_rows.append({"ccy": ccy, "amount": float(amt), "amount_usd": usd})

    # Two different denominators, because they answer different questions:
    #   invested_mv  -> "how do my holdings compare with the target weights"
    #   deployable   -> "if I also put my cash to work, what would I buy"
    invested_mv = total_mv
    deployable = total_mv + total_cash

    for r in rows:
        r["actual_weight"] = (r["mv_usd"] / invested_mv) if (invested_mv and r["mv_usd"]) else 0.0
        r["drift"] = r["actual_weight"] - r["target_weight"]
        r["target_mv_usd"] = invested_mv * r["target_weight"]
        gap_usd = r["target_mv_usd"] - (r["mv_usd"] or 0.0)
        r["gap_usd"] = gap_usd
        # same calculation, but sized against the portfolio including cash
        gap_usd_cash = deployable * r["target_weight"] - (r["mv_usd"] or 0.0)
        r["gap_usd_with_cash"] = gap_usd_cash
        if r["price"]:
            r["gap_shares"] = index_engine.from_usd(gap_usd, r["ccy"], fx) / r["price"]
            r["gap_shares_with_cash"] = index_engine.from_usd(gap_usd_cash, r["ccy"], fx) / r["price"]
        else:
            r["gap_shares"] = None
            r["gap_shares_with_cash"] = None
        r["pnl_pct"] = (r["pnl_usd"] / r["cost_usd"]) if (r.get("cost_usd") and r.get("pnl_usd") is not None) else None

    # usd_per_unit for EVERY supported currency, so the page can report in any
    # of them rather than only the two that were hardcoded before.
    rates = {u.NUMERAIRE: 1.0}
    rates.update({c: v for c, v in fx.items() if v})

    return {
        "rows": rows,
        "totals": {
            "market_value_usd": total_mv,
            "cash_usd": total_cash,
            "total_value_usd": total_mv + total_cash,
            "cash_pct": (total_cash / (total_mv + total_cash)) if (total_mv + total_cash) else 0.0,
            "cost_usd": total_cost,
            "pnl_usd": total_mv - total_cost,
            "pnl_pct": ((total_mv - total_cost) / total_cost) if total_cost else None,
            "positions_held": sum(1 for r in rows if r["shares"] > 0),
            "fx": rates,
            "base_ccy": u.BASE_CCY,
            "currencies": [c for c in config.SUPPORTED_CCY if c in rates],
        },
        "cash": cash_rows,
    }


@app.post("/api/positions")
def api_save_positions(payload: PositionsIn):
    known = set(u.UNIVERSE)
    for p in payload.positions:
        if p.ticker not in known:
            raise HTTPException(400, f"unknown ticker: {p.ticker}")
    for p in payload.positions:
        if p.shares == 0 and p.avg_cost == 0:
            db.delete_user_position(p.ticker)
        else:
            db.set_user_position(p.ticker, p.shares, p.avg_cost, p.note)
    return {"ok": True, "saved": len(payload.positions)}


@app.get("/api/check_symbols")
def api_check_symbols():
    """
    Probe every constituent (and FX pair) against the data source and report
    which symbols resolve. Run this first on a new install — a retired symbol
    like Roche's retired ROG.SW is otherwise only found when a fetch fails.
    """
    if marketdata.USE_MOCK:
        return {"mock": True, "note": "MARKETDATA_MOCK=1 — nothing is being checked against Yahoo"}
    try:
        import yfinance as yf
    except ImportError:
        raise HTTPException(500, "yfinance not installed")

    syms, _ = u.yahoo_symbols_with_alts()
    fx_syms = list(u.FX_PAIRS.values())
    data = yf.download(syms + fx_syms, period="5d", interval="1d",
                       auto_adjust=False, progress=False, group_by="ticker", threads=True)

    def ok(sym):
        try:
            return not data[sym]["Close"].dropna().empty
        except Exception:
            return False

    resolved, unresolved = {}, []
    for t in u.UNIVERSE:
        hit = next((s for s in u.all_symbols_for(t) if ok(s)), None)
        if hit:
            resolved[t] = {"symbol": hit,
                           "used_fallback": hit != u.UNIVERSE[t]["yahoo"]}
        else:
            unresolved.append({"ticker": t, "tried": u.all_symbols_for(t),
                               "name": u.UNIVERSE[t]["name"]})

    fx_ok = {c: ok(s) for c, s in u.FX_PAIRS.items()}
    return {
        "constituents_total": len(u.UNIVERSE),
        "constituents_ok": len(resolved),
        "using_fallback": {t: v["symbol"] for t, v in resolved.items() if v["used_fallback"]},
        "unresolved": unresolved,
        "fx_ok": fx_ok,
        "fx_missing": [c for c, v in fx_ok.items() if not v],
        "healthy": not unresolved and all(fx_ok.values()),
    }


@app.post("/api/reset_index")
def api_reset_index(confirm: bool = False):
    """
    Re-seed the model index from scratch (needed after changing BASE_CCY).
    Market data and user positions are preserved.
    """
    if not confirm:
        raise HTTPException(400, "pass ?confirm=true — this deletes the NAV series "
                                 "(market data and positions are kept)")
    db.reset_index()
    return {"ok": True, "note": f"index cleared; next refresh re-seeds at "
                                f"50.00 {u.BASE_CCY} per share"}


@app.get("/api/nav/simulate")
def api_nav_simulate(inception: str, end: str = None):
    """
    Re-run the index from a different inception date using the archived prices.

    This is a real re-run (whole-share allocation at that date's prices, annual
    rebalances on that schedule), not a rescaling of the live curve — so it
    answers "what if I had started then" honestly. It writes nothing.
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", inception or ""):
        raise HTTPException(400, "inception must be YYYY-MM-DD")
    if end and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", end):
        raise HTTPException(400, "end must be YYYY-MM-DD")

    dates = db.price_dates(start=inception)
    if end:
        dates = [d for d in dates if d <= end]
    if not dates:
        avail = db.price_dates()
        raise HTTPException(400,
            "no archived prices on or after that date"
            + (f"; archive covers {avail[0]} → {avail[-1]}" if avail else " (archive is empty)"))

    series = index_engine.simulate(dates, db.prices_asof, db.fx_asof)
    if not series:
        raise HTTPException(400, "could not value any session from that date "
                                 "(missing FX or prices in the archive)")
    start, last = series[0]["nav_per_share"], series[-1]["nav_per_share"]
    days = len(series)
    stats = {
        "points": days,
        "inception": series[0]["date"],
        "as_of": series[-1]["date"],
        "base_ccy": u.BASE_CCY,
        "start_nav_per_share": start,
        "nav_per_share": last,
        "total_return": (last / start - 1) if start else 0.0,
    }
    if days > 2:
        nps = [p["nav_per_share"] for p in series]
        rets = [nps[i] / nps[i - 1] - 1 for i in range(1, len(nps))]
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
        stats["vol_ann"] = math.sqrt(var) * math.sqrt(252)
        peak, mdd = nps[0], 0.0
        for v in nps:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1)
        stats["max_drawdown"] = mdd
        if days > 20 and start > 0:
            stats["annualized"] = (last / start) ** (252 / days) - 1
    return {"history": series, "stats": stats, "simulated": True}


@app.get("/api/archive")
def api_archive():
    """Proof that the daily fetches are actually on disk, and how much."""
    return db.archive_summary()


@app.post("/api/backup")
def api_backup(dest: str = None):
    """
    Consistent snapshot via SQLite's online backup API.

    Use this instead of `cp portfolio.db` while the service is running: in WAL
    mode a plain copy can omit committed transactions still sitting in the -wal
    file.
    """
    # Deliberately not HERE: when frozen that is the read-only bundle. Backups
    # land next to the database, which is writable by definition.
    dest = dest or os.path.join(
        os.path.dirname(db.DB_PATH) or ".",
        f"portfolio_backup_{dt.date.today().isoformat()}.db")
    try:
        db.backup_to(dest)
        return {"ok": True, "path": dest, "bytes": os.path.getsize(dest)}
    except Exception as e:
        raise HTTPException(500, f"backup failed: {e}")


@app.get("/api/backup.db")
def api_backup_download():
    """Download a consistent snapshot straight from the browser."""
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(),
                       f"portfolio_snapshot_{dt.date.today().isoformat()}.db")
    db.backup_to(tmp)
    return FileResponse(tmp, media_type="application/octet-stream",
                        filename=os.path.basename(tmp))


@app.get("/api/price_history")
def api_price_history(ticker: str = None, start: str = None, end: str = None, limit: int = 2000):
    if ticker and ticker not in u.UNIVERSE:
        raise HTTPException(400, f"unknown ticker: {ticker}")
    return {
        "summary": db.archive_summary(),
        "prices": db.price_history(ticker=ticker, start=start, end=end, limit=limit),
    }


@app.get("/api/price_history.csv")
def api_price_history_csv(start: str = None, end: str = None):
    """Long-format CSV of the entire stored archive."""
    import io, csv
    rows = db.price_history(start=start, end=end)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "ticker", "close", "ccy"])
    for r in rows:
        w.writerow([r["date"], r["ticker"], r["close"],
                    u.UNIVERSE.get(r["ticker"], {}).get("ccy", "")])
    return Response(buf.getvalue(), media_type="text/csv", headers={
        "Content-Disposition": f'attachment; filename="price_archive_{dt.date.today()}.csv"'})


@app.post("/api/cash")
def api_save_cash(payload: CashListIn):
    known = set(config.SUPPORTED_CCY)
    for c in payload.cash:
        if c.ccy.upper() not in known:
            raise HTTPException(400, f"unsupported currency: {c.ccy}")
    for c in payload.cash:
        db.set_user_cash(c.ccy.upper(), c.amount)
    return {"ok": True, "saved": len(payload.cash)}


@app.get("/api/export")
def api_export():
    """Everything on disk, as plain JSON, so there is never any lock-in."""
    return {
        "exported_at": dt.datetime.now().isoformat(timespec="seconds"),
        "archive": db.archive_summary(),
        "positions": db.get_user_positions(),
        "nav_history": db.nav_history(),
        "price_history": db.price_history(),
        "fx_history": db.fx_history(),
    }


# ----------------------------------------------------------------- static
def _find_index():
    """
    Locate the frontend page.

    Paths are resolved from this file's own location (never the working
    directory) so the service behaves the same when launched by Task Scheduler,
    systemd, or a shortcut, where the cwd is somewhere unrelated.

    Both layouts are accepted because files are often downloaded flat:
        <app>/static/index.html   (intended)
        <app>/index.html          (flat download)
    """
    for p in (os.path.join(STATIC, "index.html"), os.path.join(HERE, "index.html")):
        if os.path.isfile(p):
            return p
    return None


_MISSING_PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>index.html 未找到</title>
<style>body{{font-family:system-ui,sans-serif;background:#0B0F14;color:#E9E5D8;
padding:48px;line-height:1.7;max-width:820px;margin:0 auto}}
h1{{color:#C9A24B;font-size:22px}}code{{font-family:ui-monospace,monospace;
background:#151C26;border:1px solid #262E3A;padding:2px 6px;color:#4FA89B}}
pre{{background:#151C26;border:1px solid #262E3A;padding:16px;overflow:auto}}
.ok{{color:#4FA89B}}</style></head><body>
<h1>找不到前端页面 index.html</h1>
<p>后端本身<span class="ok">运行正常</span> —— 所有 API 都可用,比如
<a href="/api/status" style="color:#C9A24B">/api/status</a>、
<a href="/docs" style="color:#C9A24B">/docs</a>。缺的只是这个页面文件。</p>
<p>已在这两个位置查找过,都不存在:</p>
<pre>{p1}
{p2}</pre>
<p>把 <code>index.html</code> 放到上面任一位置即可(推荐放进 <code>static</code> 子文件夹),
然后刷新本页 —— <b>不需要重启服务</b>。</p>
<p>Windows PowerShell 建立子文件夹并移动:</p>
<pre>New-Item -ItemType Directory -Force -Path "{here}\\static"
Move-Item "{here}\\index.html" "{here}\\static\\index.html"</pre>
</body></html>"""


# The build guide ships with the app so it can be read offline, from inside the
# window, rather than living only on someone's website.
#
# NOT mounted at /docs — FastAPI already serves its interactive API reference
# there, and silently shadowing it would cost a genuinely useful debugging tool.
#
# The file is authored without <!doctype>/<html>/<body> because it is also
# published as a standalone artifact that supplies its own wrapper. Serving the
# fragment raw would drop the browser into quirks mode, so the shell is added
# here. Concatenated rather than %-formatted: the document is full of CSS
# braces, which any format-string approach would try to interpret.
_GUIDE_FILE = os.path.join(HERE, "docs", "building-this-app.html")

_GUIDE_HEAD = ('<!DOCTYPE html>\n<html lang="en" data-theme="dark">\n<head>'
               '<meta charset="utf-8">'
               '<meta name="viewport" content="width=device-width, initial-scale=1">'
               '</head>\n<body>\n')
_GUIDE_TAIL = "\n</body>\n</html>"


@app.get("/guide", include_in_schema=False)
def guide():
    """The 'how this was built' document, rendered inside the app."""
    if not os.path.isfile(_GUIDE_FILE):
        return HTMLResponse(
            "<h1>构建文档未随本版本一起打包</h1>"
            "<p>The build guide was not bundled with this build. "
            f"Expected it at:<br><code>{_GUIDE_FILE}</code></p>",
            status_code=404)
    with open(_GUIDE_FILE, encoding="utf-8") as f:
        return HTMLResponse(_GUIDE_HEAD + f.read() + _GUIDE_TAIL)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/")
def root():
    p = _find_index()
    if p is None:
        return HTMLResponse(_MISSING_PAGE.format(
            p1=os.path.join(STATIC, "index.html"),
            p2=os.path.join(HERE, "index.html"),
            here=HERE), status_code=200)
    return FileResponse(p)


# index.html references its vendored assets relatively, as `vendor/...`, so that
# the same tag resolves both when the page is served at / and when it is opened
# directly from disk. Serving them at /vendor is what makes the former work.
_VENDOR = os.path.join(STATIC, "vendor")
if os.path.isdir(_VENDOR):
    app.mount("/vendor", StaticFiles(directory=_VENDOR), name="vendor")

# Same relative-path trick as /vendor, for the page's own extracted logic.
_LIB = os.path.join(STATIC, "lib")
if os.path.isdir(_LIB):
    app.mount("/lib", StaticFiles(directory=_LIB), name="lib")

if os.path.isdir(STATIC):
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    # A frozen bundle has no fork: anything that spawns a process re-executes the
    # whole executable, which without this guard becomes recursive self-launching.
    # Nothing here spawns processes today; the guard is one line and the failure
    # mode is a fork bomb, so it is not worth leaving to chance.
    import multiprocessing
    multiprocessing.freeze_support()

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=config.PORT)
