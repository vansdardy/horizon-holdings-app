# -*- coding: utf-8 -*-
"""
Model index mechanics (same rules verified earlier):
  - NAV 10,000,000,000 USD / 200,000,000 shares => $50.00 at inception
  - integer shares only; residual stays as cash in the LOCAL currency
  - annual rebalance on the first observation of a new calendar year
  - daily mark-to-market
"""
import math
import datetime as _dt

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
            # The dividend book is emptied into the rebalance: a year of
            # reinvested income stops being a side pocket and becomes part of
            # the index proper, redistributed at target weights like everything
            # else. Its value has to be in the pot BEFORE allocating, or the
            # shares it bought would simply vanish.
            div_equity, div_cash_usd = dividend_book_value(prices, fx)
            holdings, cash = _allocate(
                equity + cash_usd + div_equity + div_cash_usd, prices, fx)
            db.save_index_state(holdings, cash)
            db.clear_dividend_state()
            if div_equity or div_cash_usd:
                print(f"[dividends] {date}: rebalance absorbed "
                      f"{div_equity + div_cash_usd:,.2f} USD of reinvested income")
            db.set_meta("last_rebalance_year", date[:4])
            rebalanced = True

    equity, cash_usd, unpriced = _mark(holdings, cash, prices, fx)
    if unpriced:
        raise StaleValuationError(
            f"NAV not written for {date}: {len(unpriced)} held positions have no price "
            f"({', '.join(sorted(unpriced)[:8])}). Valuing them at zero would corrupt "
            f"the track record.")

    # Shares bought with reinvested dividends are part of the fund's value, so
    # they are part of NAV. Keeping them in a separate table is a bookkeeping
    # choice about visibility, not a claim that they belong to someone else.
    div_equity, div_cash_usd = dividend_book_value(prices, fx)
    equity += div_equity
    cash_usd += div_cash_usd

    nav_usd = equity + cash_usd
    nav_base = to_base(nav_usd, fx)
    nps = nav_base / u.SHARES_OUTSTANDING          # per share, in BASE_CCY
    n_priced = sum(1 for t in u.UNIVERSE if prices.get(t))

    db.upsert_nav(date, nav_usd, nps, equity, cash_usd, n_priced, rebalanced,
                  nav_base=nav_base, base_ccy=u.BASE_CCY)
    return {"date": date, "nav_usd": nav_usd, "nav_base": nav_base,
            "base_ccy": u.BASE_CCY, "nav_per_share": nps, "equity_usd": equity,
            "cash_usd": cash_usd, "n_priced": n_priced, "rebalanced": rebalanced,
            "dividend_equity_usd": div_equity, "dividend_cash_usd": div_cash_usd}


def revalue(date, prices, fx, rebalanced, stale_tickers=()):
    """
    Recompute an EXISTING session's NAV from better prices. Mark-to-market only.

    Deliberately not `update()`. That function seeds and rebalances, and it does
    both against whatever holdings are stored *now* — so replaying a past date
    through it would either re-trigger a rebalance or value an old session using
    share counts the index only acquired later. Both would corrupt the record
    this is trying to correct.

    Correct only while the holdings have not changed since `date`, which means
    the caller must not reach back past the last rebalance. Within one rebalance
    period the share counts are fixed by definition, so re-marking them at
    corrected prices reproduces exactly what the original computation would have
    produced had the data been complete at the time.

    `rebalanced` is passed back in rather than recomputed, so a revision cannot
    silently erase the flag recording that this session was a rebalance day.
    """
    holdings, cash = db.load_index_state()
    equity, cash_usd, unpriced = _mark(holdings, cash, prices, fx)
    if unpriced:
        raise StaleValuationError(
            f"cannot revalue {date}: {len(unpriced)} held positions have no price "
            f"({', '.join(sorted(unpriced)[:8])})")

    # Must mirror update(), or correcting a day would quietly write a NAV that
    # excludes every dividend-bought share.
    div_equity, div_cash_usd = dividend_book_value(prices, fx)
    equity += div_equity
    cash_usd += div_cash_usd

    nav_usd = equity + cash_usd
    nav_base = to_base(nav_usd, fx)
    nps = nav_base / u.SHARES_OUTSTANDING
    n_priced = sum(1 for t in u.UNIVERSE if prices.get(t))

    db.upsert_nav(date, nav_usd, nps, equity, cash_usd, n_priced, rebalanced,
                  nav_base=nav_base, base_ccy=u.BASE_CCY,
                  stale_count=len(stale_tickers), stale_tickers=sorted(stale_tickers),
                  revised_at=_dt.datetime.now().isoformat(timespec="seconds"))
    return {"date": date, "nav_usd": nav_usd, "nav_base": nav_base,
            "nav_per_share": nps, "n_priced": n_priced,
            "stale_count": len(stale_tickers)}


def apply_dividends(date, prices, fx, div_rows, pay_dates=None):
    """
    Accrue whatever goes ex on `date`, then settle whatever has been paid by it.

    ACCRUAL AND PURCHASE ARE SEPARATE EVENTS, and this is the decision the whole
    design turns on:

      * On the EX-DATE the cash is credited. The share price gaps down by roughly
        the dividend that morning, so the value has to be booked then or the NAV
        shows a real drop for something that cost the fund nothing. It is held as
        cash, per constituent, in that constituent's own currency.
      * On the PAY DATE that cash buys shares, at the price of the session the
        money actually arrived. Shares cannot be bought with money that has not
        been paid, and the price that matters is the one on the day of the
        purchase, not the one two to five weeks earlier.

    An earlier version did both on the ex-date. It kept NAV smooth but bought at
    a price that predated the cash.

    WHEN NO PAY DATE IS KNOWN THE CASH SIMPLY WAITS. Yahoo publishes no pay date
    for any London, Tokyo or continental European listing — 52% of this fund by
    weight — and publishes a stale one for the Swiss names. Rather than infer a
    date from a per-exchange rule of thumb, that money sits as cash until the
    annual rebalance absorbs it. Idle cash understates compounding slightly and
    visibly; a guessed purchase date writes a share count that was never real
    into a record meant to last decades.

    BACK INTO THE SAME STOCK. This is a dividend REINVESTMENT plan, so KO's
    dividend buys KO. Pooling everything and buying at target weights would be a
    rebalance, and this index rebalances once a year on purpose.

    WHOLE SHARES, REMAINDER CARRIED — the same rule the index itself follows. A
    payment too small to buy a share joins that constituent's next one, which is
    part of what makes the reinvestment compound.

    Dividends are earned on the dividend shares as well as the main holdings.

    Returns {"accrued": [...], "settled": [...]}. Both halves are idempotent: a
    re-fetch covering the same window will not accrue twice (`dividend_events` is
    keyed by (date, ticker)) nor settle twice (a settled accrual is removed from
    `dividend_pending`).
    """
    return {"accrued": accrue_dividends(date, div_rows, pay_dates),
            "settled": settle_dividends(date, prices)}


def accrue_dividends(date, div_rows, pay_dates=None):
    """Book the cash for every dividend going ex on `date`. Buys nothing."""
    if not div_rows:
        return []

    pay_dates = pay_dates or {}
    main, _ = db.load_index_state()
    div_shares, _ = db.load_dividend_state()
    events = []

    for row in sorted(div_rows, key=lambda r: r["ticker"]):
        if row["date"] != date:
            continue
        t = row["ticker"]
        meta = u.UNIVERSE.get(t)
        if meta is None:
            continue
        held = int(main.get(t, 0)) + int(div_shares.get(t, 0))
        if held <= 0:
            continue
        if db.dividend_paid_on(date, t):
            continue

        gross = held * float(row["per_share"])
        pay_date = pay_dates.get((t, date))
        db.add_dividend_pending(date, t, gross, pay_date)

        ev = {"date": date, "ticker": t, "per_share": float(row["per_share"]),
              "ccy": meta["ccy"], "shares_held": held, "gross": gross,
              "price": None, "shares_bought": 0, "cash_after": gross,
              "pay_date": pay_date, "settled_date": None}
        db.record_dividend(ev)
        events.append(ev)

    if events:
        known = sum(1 for e in events if e["pay_date"])
        print(f"[dividends] {date}: accrued {len(events)} payment(s), "
              f"{known} with a known pay date")
    return events


def settle_dividends(date, prices):
    """
    Turn accrued cash into shares for every payment whose pay date has arrived.

    Runs on EVERY session, not only ones with a dividend on them — a pay date
    lands weeks after its ex-date and generally on a session where nothing goes
    ex at all.

    Oldest accrual first, each settled in its own right, so the history can say
    which payment bought which shares. A constituent with no usable price on this
    session is left pending and tried again next time rather than being valued at
    a guess.
    """
    matured = db.dividend_pending(matured_on=date)
    if not matured:
        return []

    div_shares, div_cash = db.load_dividend_state()
    settled = []

    for row in matured:
        t = row["ticker"]
        meta = u.UNIVERSE.get(t)
        px = prices.get(t)
        if meta is None or not px or px <= 0:
            continue

        pot = div_cash.get(t, 0.0) + float(row["amount"])
        bought = int(math.floor(pot / px))
        pot -= bought * px
        div_shares[t] = int(div_shares.get(t, 0)) + bought
        div_cash[t] = pot

        db.drop_dividend_pending(row["ex_date"], t)
        db.settle_dividend_event(row["ex_date"], t, date, px, bought, pot)
        settled.append({"date": row["ex_date"], "ticker": t, "ccy": meta["ccy"],
                        "amount": float(row["amount"]), "price": px,
                        "shares_bought": bought, "cash_after": pot,
                        "settled_date": date})

    if settled:
        db.save_dividend_state(div_shares, div_cash)
        total = sum(e["shares_bought"] for e in settled)
        print(f"[dividends] {date}: settled {len(settled)} payment(s), "
              f"{total} share(s) bought")
    return settled


def dividend_book_value(prices, fx):
    """
    (equity_usd, cash_usd) of the dividend book, marked at `prices`.

    `cash_usd` covers both the remainder too small to buy a share and the money
    accrued on an ex-date that has not reached its pay date. The latter is real
    value from the moment the price gaps down, so leaving it out would make the
    NAV dip on every ex-date and recover on every pay date — the exact artefact
    that accruing on the ex-date exists to prevent.
    """
    shares, cash = db.load_dividend_state()
    for t, amount in db.pending_dividend_cash().items():
        cash[t] = cash.get(t, 0.0) + amount
    equity = 0.0
    for t, n in shares.items():
        meta = u.UNIVERSE.get(t)
        px = prices.get(t)
        if not meta or not n or not px:
            continue
        equity += to_usd(px * n, meta["ccy"], fx)
    held_cash = 0.0
    for t, amount in cash.items():
        meta = u.UNIVERSE.get(t)
        if not meta or not amount:
            continue
        held_cash += to_usd(amount, meta["ccy"], fx)
    return equity, held_cash


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
