# -*- coding: utf-8 -*-
"""
Model index mechanics (same rules verified earlier):
  - NAV 10,000,000,000 USD / 200,000,000 shares => $50.00 at inception
  - integer shares only; residual stays as cash in the LOCAL currency
  - annual rebalance on the first observation of a new calendar year
  - daily mark-to-market
"""
import math
import db
import universe as u


def to_usd(amount, ccy, fx):
    if ccy == u.NUMERAIRE:
        return amount
    r = fx.get(ccy)
    if not r:
        raise ValueError(f"missing FX for {ccy}")
    return amount * r


def from_usd(amount, ccy, fx):
    if ccy == u.NUMERAIRE:
        return amount
    r = fx.get(ccy)
    if not r:
        raise ValueError(f"missing FX for {ccy}")
    return amount / r


def usd_per_base(fx):
    """How many USD one unit of the reporting currency is worth."""
    if u.BASE_CCY == u.NUMERAIRE:
        return 1.0
    r = fx.get(u.BASE_CCY)
    if not r:
        raise ValueError(f"missing FX for base currency {u.BASE_CCY}")
    return r


def to_base(amount_usd, fx):
    return amount_usd / usd_per_base(fx)


def from_base(amount_base, fx):
    return amount_base * usd_per_base(fx)


def _allocate(nav_usd, prices, fx):
    """Buy integer shares at target weights; residual -> local-currency cash."""
    weights = u.target_weights()
    live = {t: w for t, w in weights.items() if prices.get(t)}
    wsum = sum(live.values())
    if wsum <= 0:
        raise ValueError("no priced constituents")

    holdings, cash = {}, {}
    for t, w in live.items():
        ccy = u.UNIVERSE[t]["ccy"]
        alloc_usd = nav_usd * (w / wsum)
        alloc_local = from_usd(alloc_usd, ccy, fx)
        n = int(math.floor(alloc_local / prices[t]))
        holdings[t] = n
        cash[ccy] = cash.get(ccy, 0.0) + (alloc_local - n * prices[t])
    return holdings, cash


def _mark(holdings, cash, prices, fx):
    """Returns (equity_usd, cash_usd, unpriced_held_tickers)."""
    equity = 0.0
    unpriced = []
    for t, n in holdings.items():
        if not n:
            continue
        meta = u.UNIVERSE.get(t)
        if meta is None:
            # Stored state references a ticker no longer in the universe (renamed
            # or removed constituent). Ignore it rather than crashing; the next
            # rebalance rebuilds holdings from the current universe.
            continue
        px = prices.get(t)
        if not px:
            unpriced.append(t)
            continue
        equity += to_usd(px * n, meta["ccy"], fx)
    cash_usd = sum(to_usd(a, c, fx) for c, a in cash.items())
    return equity, cash_usd, unpriced


class StaleValuationError(RuntimeError):
    """Raised when a held position has no price, so NAV would be understated."""


def update(date, prices, fx):
    """
    Idempotent daily update. Returns a summary dict.
    Seeds the index on first ever run; rebalances when the calendar year turns.

    Refuses to persist a NAV point if any HELD position lacks a price: valuing a
    real holding at zero would silently understate NAV, and a wrong number written
    into a multi-decade track record is far worse than a missing day.
    """
    inception = db.get_meta("inception_date")
    holdings, cash = db.load_index_state()
    rebalanced = False

    stored_base = db.get_meta("index_base_ccy")
    if inception and stored_base is None:
        # This index has an inception date but no currency tag. That combination
        # only happens on a database seeded by a version of this code older than
        # the BASE_CCY feature itself, when the index was always implicitly
        # denominated in USD. Treating "unknown" as "safe to proceed" would mark
        # old USD-target holdings to market and report the result as if it were
        # a fresh BASE_CCY seed — silently wrong, not just imprecise.
        stored_base = u.NUMERAIRE
    if inception and stored_base != u.BASE_CCY:
        raise StaleValuationError(
            f"this index was seeded in {stored_base} but BASE_CCY is now {u.BASE_CCY}. "
            f"A NAV series cannot change denomination midway — either set "
            f"BASE_CCY={stored_base} back in .env, or POST /api/reset_index to "
            f"re-seed at 50.00 {u.BASE_CCY} (market data and your positions are kept).")

    if not inception or not holdings:
        # ---- seed ----
        seed_usd = from_base(float(u.INITIAL_NAV_BASE), fx)
        holdings, cash = _allocate(seed_usd, prices, fx)
        db.save_index_state(holdings, cash)
        db.set_meta("inception_date", date)
        db.set_meta("last_rebalance_year", date[:4])
        db.set_meta("index_base_ccy", u.BASE_CCY)
        rebalanced = True
    else:
        last_year = db.get_meta("last_rebalance_year", date[:4])
        if date[:4] != last_year:
            equity, cash_usd, unpriced = _mark(holdings, cash, prices, fx)
            if unpriced:
                raise StaleValuationError(
                    f"cannot rebalance: {len(unpriced)} held positions have no price "
                    f"({', '.join(sorted(unpriced)[:8])})")
            holdings, cash = _allocate(equity + cash_usd, prices, fx)
            db.save_index_state(holdings, cash)
            db.set_meta("last_rebalance_year", date[:4])
            rebalanced = True

    equity, cash_usd, unpriced = _mark(holdings, cash, prices, fx)
    if unpriced:
        raise StaleValuationError(
            f"NAV not written for {date}: {len(unpriced)} held positions have no price "
            f"({', '.join(sorted(unpriced)[:8])}). Valuing them at zero would corrupt "
            f"the track record.")

    nav_usd = equity + cash_usd
    nav_base = to_base(nav_usd, fx)
    nps = nav_base / u.SHARES_OUTSTANDING          # per share, in BASE_CCY
    n_priced = sum(1 for t in u.UNIVERSE if prices.get(t))

    db.upsert_nav(date, nav_usd, nps, equity, cash_usd, n_priced, rebalanced,
                  nav_base=nav_base, base_ccy=u.BASE_CCY)
    return {"date": date, "nav_usd": nav_usd, "nav_base": nav_base,
            "base_ccy": u.BASE_CCY, "nav_per_share": nps, "equity_usd": equity,
            "cash_usd": cash_usd, "n_priced": n_priced, "rebalanced": rebalanced}


def stats():
    """Summary metrics over whatever NAV history exists."""
    hist = db.nav_history()
    if not hist:
        return {"points": 0}
    nps = [h["nav_per_share"] for h in hist]
    start, end = nps[0], nps[-1]
    out = {
        "points": len(hist),
        "inception": hist[0]["date"],
        "as_of": hist[-1]["date"],
        "start_nav_per_share": start,
        "nav_per_share": end,
        "nav_usd": hist[-1]["nav_usd"],
        "nav_base": hist[-1].get("nav_base") or hist[-1]["nav_usd"],
        "base_ccy": db.get_meta("index_base_ccy") or u.BASE_CCY,
        "total_return": end / start - 1 if start else 0.0,
        "cash_pct": hist[-1]["cash_usd"] / hist[-1]["nav_usd"] if hist[-1]["nav_usd"] else 0.0,
        "n_priced": hist[-1]["n_priced"],
    }
    if len(nps) > 2:
        rets = [nps[i] / nps[i - 1] - 1 for i in range(1, len(nps))]
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
        out["vol_ann"] = math.sqrt(var) * math.sqrt(252)
        peak, mdd = nps[0], 0.0
        for v in nps:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1)
        out["max_drawdown"] = mdd
        days = len(nps)
        if days > 20 and start > 0:
            out["annualized"] = (end / start) ** (252 / days) - 1
    return out


def simulate(dates, prices_asof, fx_asof):
    """
    Re-run the index from scratch over `dates`, in memory, touching no stored
    state. Used to answer "what would this look like with a different inception
    date" from the archived prices.

    This is a genuine re-run, not a rescaling of the live curve: shares are
    re-allocated as whole units at the prices of the new start date, and annual
    rebalances land on that schedule. Simply dividing the existing series by its
    value on some later day would give a subtly different answer, because the
    integer-share rounding and the rebalance calendar both depend on where the
    index actually started.

    Returns [{date, nav_per_share, nav_base, cash_pct, rebalanced}, …].
    """
    if not dates:
        return []

    holdings, cash = {}, {}
    seeded_year = None
    out = []

    for d in dates:
        asof = prices_asof(d)
        prices = {t: v["close"] for t, v in asof.items()}
        fx = fx_asof(d)
        if not prices or not fx:
            continue
        try:
            usd_per_base(fx)
        except ValueError:
            continue

        rebalanced = False
        if seeded_year is None:
            holdings, cash = _allocate(from_base(float(u.INITIAL_NAV_BASE), fx), prices, fx)
            seeded_year = d[:4]
            rebalanced = True
        elif d[:4] != seeded_year:
            equity, cash_usd, unpriced = _mark(holdings, cash, prices, fx)
            if unpriced:
                continue
            holdings, cash = _allocate(equity + cash_usd, prices, fx)
            seeded_year = d[:4]
            rebalanced = True

        equity, cash_usd, unpriced = _mark(holdings, cash, prices, fx)
        if unpriced:
            continue
        nav_usd = equity + cash_usd
        nav_base = to_base(nav_usd, fx)
        out.append({
            "date": d,
            "nav_per_share": nav_base / u.SHARES_OUTSTANDING,
            "nav_base": nav_base,
            "cash_pct": (cash_usd / nav_usd) if nav_usd else 0.0,
            "rebalanced": rebalanced,
        })
    return out
