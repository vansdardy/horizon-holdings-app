# -*- coding: utf-8 -*-
"""
Fetches daily closing prices + FX.

Live source: Yahoo Finance via yfinance (free, no API key).
Mock source: deterministic pseudo-prices for offline pipeline testing.

IMPORTANT: every quote carries ITS OWN close date. Exchanges close at different
times and observe different holidays, so stamping every constituent with a single
"today" would silently re-date stale quotes and invent price history that never
happened. Each ticker is stored under the session it actually traded in.
"""
import os
import datetime as dt

import config  # loads .env before anything reads os.environ
import universe as u

USE_MOCK = config.MARKETDATA_MOCK


# ---------------------------------------------------------------- live
LOOKBACK = config.FETCH_LOOKBACK


def fetch_live():
    """
    Returns (valuation_date, price_rows, fx_rows) where each row list is
    [{"ticker"/"ccy":…, "close"/"rate":…, "date":…}, …] covering the WHOLE
    lookback window, not just the newest bar.

    Keeping every bar in the window costs nothing (same single request) and lets
    the service self-heal: if the machine was asleep for a few days, those
    sessions are backfilled instead of leaving permanent holes in the record.

    Fetching is two-phase on purpose: only the PRIMARY symbol of each constituent
    is requested up front, and fallbacks are tried in a second request solely for
    the ones that came back empty. Requesting known-retired fallbacks every day
    would print a "possibly delisted" warning every day forever — a permanent
    false alarm that trains you to ignore the log, which is exactly where a real
    outage would show up.
    """
    import yfinance as yf

    fx_syms = list(u.FX_PAIRS.values())
    primary = {t: u.UNIVERSE[t]["yahoo"] for t in u.UNIVERSE}

    def download(syms):
        if not syms:
            return None
        return yf.download(syms, period=LOOKBACK, interval="1d",
                           auto_adjust=False, progress=False, group_by="ticker",
                           threads=True)

    def series(data, sym):
        if data is None:
            return None
        try:
            s = data[sym]["Close"].dropna()
        except Exception:
            return None
        return None if s.empty else s

    # ---- phase 1: primaries + FX ----
    data = download(list(primary.values()) + fx_syms)

    resolved, price_rows = {}, []

    def take(t, sym, s):
        resolved[t] = sym
        for idx, val in s.items():
            price_rows.append({"ticker": t, "close": float(val),
                               "date": idx.date().isoformat()})

    unresolved = []
    for t, sym in primary.items():
        s = series(data, sym)
        if s is None:
            unresolved.append(t)
        else:
            take(t, sym, s)

    # ---- phase 2: fallbacks, ONLY for what actually failed ----
    dead = []
    if unresolved:
        alt_syms = []
        for t in unresolved:
            alt_syms += [s for s in u.all_symbols_for(t) if s != primary[t]]
        alt_syms = sorted(set(alt_syms))
        if alt_syms:
            print(f"[marketdata] {len(unresolved)} symbol(s) returned nothing; "
                  f"trying fallbacks: {', '.join(alt_syms)}")
        alt_data = download(alt_syms)
        for t in unresolved:
            hit = None
            for sym in u.all_symbols_for(t):
                if sym == primary[t]:
                    continue
                s = series(alt_data, sym)
                if s is not None:
                    hit = (sym, s)
                    break
            if hit:
                take(t, hit[0], hit[1])
                print(f"[marketdata] {t}: primary {primary[t]} failed, using "
                      f"fallback {hit[0]} — consider updating universe.py")
            else:
                dead.append(t)

    # ---- FX ----
    fx_rows, seen_ccy = [], set()
    for ccy, sym in u.FX_PAIRS.items():
        s = series(data, sym)
        if s is None:
            continue
        seen_ccy.add(ccy)
        for idx, val in s.items():
            fx_rows.append({"ccy": ccy, "rate": float(val),
                            "date": idx.date().isoformat()})

    if not price_rows:
        raise RuntimeError("Yahoo returned no prices for any symbol")
    # FX_PAIRS never includes the numeraire itself (USD needs no rate — it IS the
    # unit everything else converts to), so completeness is checked against
    # NUMERAIRE, not BASE_CCY. These stopped being the same currency once the
    # reporting currency became configurable.
    missing_fx = [c for c in u.CURRENCIES if c != u.NUMERAIRE and c not in seen_ccy]
    if missing_fx:
        raise RuntimeError(
            f"missing FX rates for {missing_fx}. Every currency is required to "
            f"translate NAV into USD, so no valuation was attempted.")
    if dead:
        print(f"[marketdata] WARNING: no data for {len(dead)} constituent(s): "
              f"{', '.join(dead)} — they will be excluded and weights renormalised")

    # FX and equity series do not always start on the same day; valuing a session
    # with no FX would be wrong, so only expose sessions FX actually covers.
    fx_dates = {r["date"] for r in fx_rows}
    if fx_dates:
        earliest_fx = min(fx_dates)
        price_rows = [r for r in price_rows if r["date"] >= earliest_fx]

    valuation_date = max(r["date"] for r in price_rows)
    return valuation_date, price_rows, fx_rows


# ---------------------------------------------------------------- mock
_MOCK_BASE_FX = {"CAD": 0.73, "CHF": 1.11, "DKK": 0.145, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0067}


def fetch_mock(day_offset=0, window=1):
    """Deterministic fake data for testing the pipeline. NOT real prices."""
    import hashlib
    import math

    def h(s):
        return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF

    price_rows, fx_rows = [], []
    offsets = range(day_offset - window + 1, day_offset + 1)
    for off in offsets:
        date = (dt.date.today() + dt.timedelta(days=off)).isoformat()
        for t in u.UNIVERSE:
            base = 20 + h(t) * 380
            drift = math.sin((h(t) * 6.28) + off * 0.08) * 0.05
            price_rows.append({"ticker": t, "close": round(base * (1 + drift), 2), "date": date})
        for c, r in _MOCK_BASE_FX.items():
            fx_rows.append({"ccy": c,
                            "rate": round(r * (1 + math.sin(h(c) + off * 0.05) * 0.02), 6),
                            "date": date})

    valuation_date = max(r["date"] for r in price_rows)
    return valuation_date, price_rows, fx_rows


def fetch(day_offset=0, window=1):
    if USE_MOCK:
        return fetch_mock(day_offset, window)
    return fetch_live()


# ---------------------------------------------------------------- fundamentals (quarterly)
def current_quarter(d=None):
    """'YYYY-Qn' for the quarter containing date d (default today).
    Boundaries are Jan/Apr/Jul/Oct 1, matching the requested fetch schedule."""
    d = d or dt.date.today()
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


def fetch_fundamentals_live(tickers):
    """
    Per-ticker fundamentals via yfinance's Ticker.info — a separate, much
    heavier endpoint than the batched price download (one HTTP round-trip per
    symbol, not one for all 78). Each ticker is wrapped individually so one
    bad or missing symbol doesn't lose the other 77; failures are reported,
    not silently dropped.

    yfinance's official reference docs (ranaroussi.github.io/yfinance) don't
    document per-field units for Ticker.info — it's explicitly acknowledged
    by the maintainers as thin/auto-generated, and the community has long
    reported the pre-computed `dividendYield` field switching between a
    fraction (0.024) and an already-scaled percent (2.4) depending on ticker
    and Yahoo-side changes, with no reliable way to tell which one you got
    from the number alone.

    So dividend yield is now computed directly from two RAW, unambiguous
    fields instead of trusting Yahoo's pre-computed ratio:
        div_yield = dividendRate / current_price
    dividendRate is an annual cash amount (e.g. "$2.44/share") and price is
    in the same currency — dividing same-unit quantities can't have a
    percent-vs-fraction ambiguity. `dividendYield` is kept only as a fallback
    when dividendRate or price isn't available, using the old best-effort
    normalization. Either way, PLAUSIBILITY BOUNDS remain the final backstop:
    anything outside a sane range for this universe is discarded (falls back
    to the static estimate on the frontend) rather than displayed.

    Similarly, trailingPE/forwardPE are used as given (already unambiguous
    ratios — no percent/fraction issue), with price/trailingEps as a fallback
    when neither is present but earnings data is.
    """
    import yfinance as yf

    PE_RANGE = (0, 500)          # raised from 150: legitimate trailing P/E for extreme growth /
                                 # chokepoint names (e.g. ARM, thin current earnings vs high
                                 # anticipated growth) genuinely runs 200-300x+. This bound now
                                 # exists to catch broken data (negative-earnings artifacts,
                                 # unit errors), not to second-guess a real rich valuation.
    DY_RANGE = (0, 0.12)         # reject >12%; no name in this universe plausibly yields that high
    BETA_RANGE = (-1.0, 5.0)     # reject implausible beta outliers

    def sane(val, lo, hi):
        return val if (val is not None and lo <= val <= hi) else None

    rows, failed, flagged = [], [], []
    for t in tickers:
        row = None
        for sym in u.all_symbols_for(t):
            try:
                info = yf.Ticker(sym).info
                if not info:
                    continue
                price = (info.get("currentPrice") or info.get("regularMarketPrice")
                         or info.get("previousClose"))

                # ---- P/E: direct field first, computed fallback second ----
                # Which one gets used matters and must be labeled: trailing P/E
                # (based on actual reported earnings) and forward P/E (based on
                # analyst estimates) can differ by a factor of several for a
                # richly-valued, thin-current-earnings name — silently blending
                # them into one unlabeled number is itself a source of the kind
                # of "this doesn't match what I looked up" confusion this
                # fetch already had to fix once for dividend yield.
                pe_type = None
                if info.get("trailingPE") is not None:
                    pe_raw, pe_type = info["trailingPE"], "trailing"
                elif info.get("forwardPE") is not None:
                    pe_raw, pe_type = info["forwardPE"], "forward"
                else:
                    pe_raw = None
                if pe_raw is None:
                    eps = info.get("trailingEps") or info.get("forwardEps")
                    if price and eps and eps > 0:
                        pe_raw, pe_type = price / eps, "computed"
                if pe_raw is None:
                    continue  # no earnings-based valuation available at all for this symbol

                # ---- dividend yield: computed from raw currency fields first ----
                div_rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate")
                if div_rate is not None and price:
                    dy_raw = div_rate / price
                else:
                    dy_raw = info.get("dividendYield")
                    if dy_raw is not None and dy_raw > 1:
                        dy_raw = dy_raw / 100.0  # best-effort only; bounds below catch misses

                beta_raw = info.get("beta")

                pe = sane(pe_raw, *PE_RANGE)
                dy = sane(dy_raw, *DY_RANGE)
                beta = sane(beta_raw, *BETA_RANGE)
                if (pe_raw is not None and pe is None) or \
                   (dy_raw is not None and dy is None) or \
                   (beta_raw is not None and beta is None):
                    flagged.append(f"{t}(pe={pe_raw},dy={dy_raw},beta={beta_raw})")

                # pe_type is reported only when the pe value it describes actually
                # survived the plausibility check — a rejected field must never
                # carry a label implying it's trustworthy live data.
                row = {"ticker": t, "pe": pe, "div_yield": dy, "beta": beta,
                       "pe_type": pe_type if pe is not None else None}
                break
            except Exception:
                continue
        if row:
            rows.append(row)
        else:
            failed.append(t)
    return rows, failed, flagged


def fetch_fundamentals_mock(tickers):
    """Deterministic fake fundamentals for offline pipeline testing."""
    import hashlib

    def h(s):
        return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF

    rows = []
    for t in tickers:
        rows.append({
            "ticker": t,
            "pe": round(8 + h(t) * 60, 1),
            "div_yield": round(h(t + "d") * 0.06, 4),
            "beta": round(0.3 + h(t + "b") * 1.3, 2),
            "pe_type": "trailing",
        })
    return rows, [], []


def fetch_fundamentals(tickers):
    if USE_MOCK:
        return fetch_fundamentals_mock(tickers)
    return fetch_fundamentals_live(tickers)
