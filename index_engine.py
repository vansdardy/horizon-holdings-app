# -*- coding: utf-8 -*-
"""
Model index mechanics (same rules verified earlier):
  - NAV 10,000,000,000 USD / 200,000,000 shares => $50.00 at inception
  - integer shares only; residual stays as cash in the LOCAL currency
  - annual rebalance on the first observation of a new calendar year
  - daily mark-to-market
"""
import json
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
        # Nothing was held before the seed; see shares_held_on.
        db.set_meta("rebalance_snapshot", json.dumps({"date": date, "main": {}}))
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
            div_equity, div_cash_usd = dividend_book_value(prices, fx, date)
            # Remember what was held going into this session. A dividend that
            # went ex before today but is only recorded after it — Yahoo
            # publishes some late — is owed on these shares, not on the ones
            # the rebalance is about to buy.
            db.set_meta("rebalance_snapshot", json.dumps(
                {"date": date, "main": {t: int(n) for t, n in holdings.items()}}))
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
    # As of `date`, not as of now: when this is a backfill of an earlier
    # session, income recorded since must not leak into it. On a rebalance day
    # the book has just been absorbed into the holdings marked above.
    if rebalanced:
        div_equity = div_cash_usd = 0.0
    else:
        div_equity, div_cash_usd = dividend_book_value(prices, fx, date)
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


def _valuation(date, prices, fx, after_rebalance):
    """
    NAV for `date` from the main holdings stored now and the dividend book as it
    stood on `date`. Writes nothing.

    Valid only within the current rebalance period, where the main share counts
    are fixed by definition — callers must not reach back past the last
    rebalance.
    """
    holdings, cash = db.load_index_state()
    equity, cash_usd, unpriced = _mark(holdings, cash, prices, fx)
    if unpriced:
        raise StaleValuationError(
            f"cannot value {date}: {len(unpriced)} held positions have no price "
            f"({', '.join(sorted(unpriced)[:8])})")
    if after_rebalance:
        div_equity = div_cash_usd = 0.0
    else:
        div_equity, div_cash_usd = dividend_book_value(prices, fx, date)
    equity += div_equity
    cash_usd += div_cash_usd
    nav_usd = equity + cash_usd
    nav_base = to_base(nav_usd, fx)
    return {"date": date, "nav_usd": nav_usd, "nav_base": nav_base,
            "nav_per_share": nav_base / u.SHARES_OUTSTANDING,
            "equity_usd": equity, "cash_usd": cash_usd,
            "n_priced": sum(1 for t in u.UNIVERSE if prices.get(t))}


def _rewrite(v, rebalanced, stale_tickers):
    db.upsert_nav(v["date"], v["nav_usd"], v["nav_per_share"], v["equity_usd"],
                  v["cash_usd"], v["n_priced"], rebalanced,
                  nav_base=v["nav_base"], base_ccy=u.BASE_CCY,
                  stale_count=len(stale_tickers), stale_tickers=sorted(stale_tickers),
                  revised_at=_dt.datetime.now().isoformat(timespec="seconds"))


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
    period the main share counts are fixed by definition. The dividend book is
    not fixed — it grows with every payment — which is why it is rebuilt as of
    `date` from the ledger. Reading the running totals instead is how a revision
    on Sep 18 once wrote income with ex-dates of Sep 11-18 into the Sep 7 NAV.

    `rebalanced` is passed back in rather than recomputed, so a revision cannot
    silently erase the flag recording that this session was a rebalance day.
    """
    v = _valuation(date, prices, fx, rebalanced)
    _rewrite(v, rebalanced, stale_tickers)
    return {"date": date, "nav_usd": v["nav_usd"], "nav_base": v["nav_base"],
            "nav_per_share": v["nav_per_share"], "n_priced": v["n_priced"],
            "stale_count": len(stale_tickers)}


def restate_series(from_date, tolerance_usd=0.01):
    """
    Re-mark every stored NAV point from `from_date` on, after the dividend
    ledger has changed beneath points that were already published.

    That happens when a dividend is recorded late (its cash belongs in every NAV
    from its ex-date on) or a purchase settles at an earlier session's close.
    Only points whose value actually moves are rewritten, and each one rewritten
    is stamped `revised_at`, so a corrected number is never silently substituted
    for the original. Never crosses the last rebalance; see `_valuation`.

    Returns [{date, before, after}] for the points that changed.
    """
    floor = db.last_rebalance_on_or_before("9999-12-31")
    start = max(from_date, floor) if floor else from_date
    changed = []
    for row in db.nav_history():
        d = row["date"]
        if d < start:
            continue
        asof = db.prices_asof(d)
        if not asof:
            continue
        prices = {t: q["close"] for t, q in asof.items()}
        try:
            v = _valuation(d, prices, db.fx_asof(d), bool(row["rebalanced"]))
        except (StaleValuationError, ValueError):
            continue
        if abs(v["nav_usd"] - (row["nav_usd"] or 0.0)) <= tolerance_usd:
            continue
        stale = sorted(t for t, q in asof.items() if q["date"] < d)
        _rewrite(v, bool(row["rebalanced"]), stale)
        changed.append({"date": d, "before": row["nav_usd"], "after": v["nav_usd"]})
    if changed:
        print(f"[dividends] restated {len(changed)} NAV point(s) from {changed[0]['date']}")
    return changed


def apply_dividends(date, prices, fx, div_rows, pay_dates=None):
    """
    Accrue whatever goes ex on `date`, then settle whatever has been paid by it.

    ACCRUAL AND PURCHASE ARE SEPARATE EVENTS, and this is the decision the whole
    design turns on:

      * On the EX-DATE the cash is credited. The share price gaps down by roughly
        the dividend that morning, so the value has to be booked then or the NAV
        shows a real drop for something that cost the fund nothing. It is held as
        cash, per constituent, in that constituent's own currency.
      * On the PAY DATE that cash buys shares, at the close of the first session
        on or after it — read from the price archive, so the purchase price does
        not depend on when the job happens to run. Shares cannot be bought with
        money that has not been paid, and the price that matters is the one on
        the day of the purchase.

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

    `prices` and `fx` are no longer read here — accrual needs neither, and
    settlement prices come from the archive — but the signature is kept.

    Returns {"accrued": [...], "settled": [...]}. Both halves are idempotent: a
    re-fetch covering the same window will not accrue twice (`dividend_events` is
    keyed by (date, ticker)) nor settle twice (a settled accrual is removed from
    `dividend_pending`).
    """
    return {"accrued": accrue_dividends(date, div_rows, pay_dates),
            "settled": settle_dividends(date, prices)}


def shares_held_on(ticker, ex_date):
    """
    Shares entitled to a dividend going ex on `ex_date`: everything owned at the
    close of the day before, main book and dividend book together.

    Usually that is simply today's main holdings, which do not change between
    rebalances. The exception is a dividend recorded only after a rebalance its
    ex-date preceded; then the main book is read from the snapshot the rebalance
    left behind. Returns None when that snapshot is missing, so the caller can
    refuse rather than guess.
    """
    latest = db.last_rebalance_on_or_before("9999-12-31")
    if latest is None or ex_date > latest:
        main, _ = db.load_index_state()
    else:
        snap = json.loads(db.get_meta("rebalance_snapshot") or "null")
        if not snap or snap.get("date") != latest:
            return None
        main = snap["main"]
    eve = (_dt.date.fromisoformat(ex_date) - _dt.timedelta(days=1)).isoformat()
    div_shares, _ = dividend_book_asof(eve)
    return int(main.get(ticker, 0)) + int(div_shares.get(ticker, 0))


def _day_after(iso):
    return (_dt.date.fromisoformat(iso) + _dt.timedelta(days=1)).isoformat()


def accrue_dividends(date, div_rows, pay_dates=None):
    """
    Book the cash for every dividend going ex on `date`. Buys nothing.

    Callable for a past `date` as well as the current one: Yahoo publishes some
    dividends days after their ex-date, and a payment missing from the feed on
    the evening it goes ex must still be booked when it appears. The shares
    entitled are the ones held going into `date`, not today's.

    The cash joins the book on its ex-date (`book_date`), so every NAV from then
    on includes it. The one exception is a dividend recorded only after a
    rebalance it should have preceded: that rebalance has already redistributed
    the book, so the cash joins the new book the day after instead.
    """
    if not div_rows:
        return []

    pay_dates = pay_dates or {}
    latest = db.last_rebalance_on_or_before("9999-12-31")
    events = []

    for row in sorted(div_rows, key=lambda r: r["ticker"]):
        if row["date"] != date:
            continue
        t = row["ticker"]
        meta = u.UNIVERSE.get(t)
        if meta is None:
            continue
        if db.dividend_paid_on(date, t):
            continue
        held = shares_held_on(t, date)
        if held is None:
            print(f"[dividends] {t} ex {date}: holdings before the {latest} "
                  f"rebalance are not recorded, so the entitlement cannot be "
                  f"computed; not booked")
            continue
        if held <= 0:
            continue

        # Yahoo adjusts a dividend for every split dated AFTER its ex-date,
        # which puts it in the same basis as `held`. A dividend going ex on the
        # very day of a split is not adjusted and is still quoted per old share
        # — Japan does this routinely, both falling on a half-year record date.
        # 8035.T paid 384 JPY per pre-split share on 2026-09-29, the day of its
        # 5-for-1 split. Once that split is applied, `held` is in new shares, so
        # the amount per share must come down by the same ratio.
        per_share = float(row["per_share"])
        for sp in db.splits(t):
            if sp["effective_date"] == date:
                per_share /= sp["ratio"]
        gross = held * per_share
        pay_date = pay_dates.get((t, date))
        book_date = date if (latest is None or date > latest) else _day_after(latest)
        db.add_dividend_pending(date, t, gross, pay_date)

        ev = {"date": date, "ticker": t, "per_share": per_share,
              "ccy": meta["ccy"], "shares_held": held, "gross": gross,
              "price": None, "shares_bought": 0, "cash_after": gross,
              "pay_date": pay_date, "settled_date": None, "book_date": book_date}
        db.record_dividend(ev)
        events.append(ev)

    if events:
        known = sum(1 for e in events if e["pay_date"])
        print(f"[dividends] {date}: accrued {len(events)} payment(s), "
              f"{known} with a known pay date")
    return events


def settle_dividends(date, prices=None):
    """
    Turn accrued cash into shares for every payment whose pay date has arrived.

    The purchase is made at the close of the first archived session on or after
    the pay date, and `settled_date` records that session — not the day this
    happens to run. A payment recorded late, or a job that missed a few days,
    therefore still buys at the price of the day the money landed. If that
    session's close is not in the archive yet, the payment waits.

    Oldest accrual first, each settled in its own right, so the history can say
    which payment bought which shares.
    """
    matured = db.dividend_pending(matured_on=date)
    if not matured:
        return []

    div_shares, div_cash = db.load_dividend_state()
    settled = []

    for row in matured:
        t = row["ticker"]
        meta = u.UNIVERSE.get(t)
        if meta is None:
            continue
        ev = db.dividend_event(row["ex_date"], t) or {}
        start = max(row["pay_date"], ev.get("book_date") or row["ex_date"])
        bar = db.first_close_on_or_after(t, start, date)
        if bar is None:
            continue
        bar_date, px = bar
        if not px or px <= 0:
            continue

        pot = div_cash.get(t, 0.0) + float(row["amount"])
        bought = int(math.floor(pot / px))
        pot -= bought * px
        div_shares[t] = int(div_shares.get(t, 0)) + bought
        div_cash[t] = pot

        db.drop_dividend_pending(row["ex_date"], t)
        db.settle_dividend_event(row["ex_date"], t, bar_date, px, bought, pot,
                                 basis_seq=db.max_split_seq())
        settled.append({"date": row["ex_date"], "ticker": t, "ccy": meta["ccy"],
                        "amount": float(row["amount"]), "price": px,
                        "shares_bought": bought, "cash_after": pot,
                        "settled_date": bar_date})

    if settled:
        db.save_dividend_state(div_shares, div_cash)
        total = sum(e["shares_bought"] for e in settled)
        print(f"[dividends] {date}: settled {len(settled)} payment(s), "
              f"{total} share(s) bought")
    return settled


def dividend_book_asof(date):
    """
    (shares, cash) of the dividend book at the close of `date`, rebuilt from the
    payment ledger rather than read from the running totals.

    The running totals only ever describe *now*. Valuing a past session against
    them — a backfill, a revision, a restatement — would credit it with income
    that went ex after it, which is exactly what happened to the Sep 7 point
    when it was revised on Sep 18.

    Counted from the last rebalance at or before `date`, because a rebalance
    absorbs the whole book. Within that period:
      shares = every purchase settled by `date`
      cash   = every payment booked by `date`, less what was spent on shares
    The cash term is a plain sum, so it does not depend on the order purchases
    were made in, and it equals the running totals exactly when `date` is today.

    Share counts are in the current basis: a purchase is multiplied through
    every split applied after it was made (see db.apply_split). The cash spent
    on it is basis-free, so the cash term needs no such adjustment.
    """
    floor = db.last_rebalance_on_or_before(date)
    by_ticker = {}
    for sp in db.splits():
        by_ticker.setdefault(sp["ticker"], []).append((sp["seq"], sp["ratio"]))

    def through_splits(t, basis):
        m = 1.0
        for seq, ratio in by_ticker.get(t, ()):
            if seq > (basis or 0):
                m *= ratio
        return m

    shares, cash = {}, {}
    for e in db.dividend_events_booked(floor, date):
        t = e["ticker"]
        gross = float(e["gross"])
        if e["settled_date"] and e["settled_date"] <= date:
            n = int(e["shares_bought"] or 0)
            shares[t] = db.shares_value(shares.get(t, 0) + n * through_splits(t, e["basis_seq"]))
            cash[t] = cash.get(t, 0.0) + gross - n * float(e["price"] or 0.0)
        else:
            cash[t] = cash.get(t, 0.0) + gross
    return shares, cash


def dividend_book_value(prices, fx, asof):
    """(equity_usd, cash_usd) of the dividend book as of `asof`, marked at `prices`."""
    shares, cash = dividend_book_asof(asof)
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
