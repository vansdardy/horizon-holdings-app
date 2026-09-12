# -*- coding: utf-8 -*-
"""
The index mechanics.

These are the tests that matter most in this project. Everything else can be
re-derived from the price archive; a NAV series that is quietly wrong cannot,
because nobody notices until the number has been believed for months.
"""
import math

import pytest

import index_engine as eng
import universe as u


# --------------------------------------------------------------- conversion
def test_numeraire_needs_no_rate(fx):
    assert eng.to_usd(100.0, u.NUMERAIRE, fx) == 100.0
    assert eng.from_usd(100.0, u.NUMERAIRE, fx) == 100.0


def test_conversion_round_trips():
    fx = {"CHF": 1.25}
    assert eng.from_usd(eng.to_usd(80.0, "CHF", fx), "CHF", fx) == pytest.approx(80.0)


def test_missing_rate_is_an_error_not_a_guess(fx):
    """A missing rate must never be treated as 1.0 — that silently mis-values."""
    with pytest.raises(ValueError, match="missing FX"):
        eng.to_usd(100.0, "CHF", {})


# --------------------------------------------------------------- allocation
def test_allocation_buys_whole_shares_only(fx, prices):
    holdings, _ = eng._allocate(1_000_000.0, prices, fx)
    assert holdings, "expected some holdings"
    for ticker, n in holdings.items():
        assert isinstance(n, int), f"{ticker} got a fractional share count"


def test_allocation_residual_is_kept_as_cash(fx, prices):
    """Nothing may be lost to rounding: shares + cash must equal what went in."""
    nav = 1_000_000.0
    holdings, cash = eng._allocate(nav, prices, fx)

    equity = sum(prices[t] * n for t, n in holdings.items())   # all prices are 1 USD-equivalent
    residual = sum(cash.values())
    assert equity + residual == pytest.approx(nav, rel=1e-9)


def test_allocation_respects_target_weights(fx, prices):
    """A score-6 name should get roughly twice a score-3 name."""
    holdings, _ = eng._allocate(10_000_000.0, prices, fx)
    weights = u.target_weights()
    big = max(u.UNIVERSE, key=lambda t: u.UNIVERSE[t]["score"])
    small = min(u.UNIVERSE, key=lambda t: u.UNIVERSE[t]["score"])
    ratio_held = holdings[big] / holdings[small]
    ratio_target = weights[big] / weights[small]
    assert ratio_held == pytest.approx(ratio_target, rel=0.02)


def test_unpriced_constituents_are_renormalised_away(fx, prices):
    """
    A name with no price is dropped and the rest are scaled up to fill the gap.
    Without this the portfolio would silently sit partly in cash and understate
    its own return.
    """
    dropped = next(iter(prices))
    partial = {t: p for t, p in prices.items() if t != dropped}

    holdings, cash = eng._allocate(1_000_000.0, partial, fx)
    assert dropped not in holdings

    equity = sum(partial[t] * n for t, n in holdings.items())
    assert equity + sum(cash.values()) == pytest.approx(1_000_000.0, rel=1e-9)


def test_allocation_without_any_prices_is_refused(fx):
    with pytest.raises(ValueError, match="no priced constituents"):
        eng._allocate(1000.0, {}, fx)


# --------------------------------------------------------------- valuation
def test_mark_reports_unpriced_held_positions(fx, prices):
    holdings, cash = eng._allocate(1_000_000.0, prices, fx)
    held = next(t for t, n in holdings.items() if n > 0)

    _, _, unpriced = eng._mark(holdings, cash, {t: p for t, p in prices.items() if t != held}, fx)
    assert held in unpriced


def test_mark_ignores_tickers_that_left_the_universe(fx, prices):
    """Stored state can name a constituent that no longer exists; that must not crash."""
    equity, cash_usd, unpriced = eng._mark({"DELISTED-XYZ": 100}, {}, prices, fx)
    assert equity == 0.0 and unpriced == []


# --------------------------------------------------------------- seeding
def test_seeds_at_exactly_fifty_per_share(db, fx, prices):
    result = eng.update("2026-01-05", prices, fx)
    assert result["nav_per_share"] == pytest.approx(50.0, rel=1e-9)
    assert result["rebalanced"] is True
    assert result["base_ccy"] == u.BASE_CCY


def test_seeding_records_its_currency(db, fx, prices):
    eng.update("2026-01-05", prices, fx)
    assert db.get_meta("index_base_ccy") == u.BASE_CCY
    assert db.get_meta("inception_date") == "2026-01-05"


def test_update_is_idempotent(db, fx, prices):
    """Re-running the same day must not double-count or drift."""
    first = eng.update("2026-01-05", prices, fx)
    second = eng.update("2026-01-05", prices, fx)
    assert first["nav_usd"] == pytest.approx(second["nav_usd"])
    assert len(db.nav_history()) == 1


# ------------------------------------------------- the refusal that matters
def test_refuses_to_write_nav_when_a_held_position_is_unpriced(db, fx, prices):
    """
    The single most important behaviour in the application.

    Valuing a held position at zero understates NAV in a way that looks like a
    real market move. One missing price was measured at a phantom -2.17% day.
    A gap in the record is recoverable; a wrong number is not.
    """
    eng.update("2026-01-05", prices, fx)

    holdings, _ = db.load_index_state()
    held = next(t for t, n in holdings.items() if n > 0)
    missing = {t: p for t, p in prices.items() if t != held}

    with pytest.raises(eng.StaleValuationError) as excinfo:
        eng.update("2026-01-06", missing, fx)

    assert held in str(excinfo.value), "the error must name the offending ticker"
    assert len(db.nav_history()) == 1, "no NAV row may be written for the failed day"


def test_refuses_to_change_denomination_midway(db, fx, prices, monkeypatch):
    """A NAV series that switches currency is two incomparable series glued together."""
    eng.update("2026-01-05", prices, fx)
    monkeypatch.setattr(u, "BASE_CCY", "USD" if u.BASE_CCY != "USD" else "EUR")

    with pytest.raises(eng.StaleValuationError, match="seeded in"):
        eng.update("2026-01-06", prices, fx)


def test_reset_clears_the_index_but_keeps_market_data(db, fx, prices):
    db.upsert_prices([{"date": "2026-01-05", "ticker": "AAPL", "close": 1.0}])
    db.set_user_position("AAPL", 10, 100.0)
    eng.update("2026-01-05", prices, fx)

    db.reset_index()

    assert db.nav_history() == []
    assert db.get_meta("inception_date") is None
    assert db.price_history(), "price archive must survive a reset"
    assert "AAPL" in db.get_user_positions(), "user positions must survive a reset"


# --------------------------------------------------------------- rebalance
def test_rebalances_on_the_first_session_of_a_new_year(db, fx, prices):
    eng.update("2026-12-30", prices, fx)
    same_year = eng.update("2026-12-31", prices, fx)
    assert same_year["rebalanced"] is False

    new_year = eng.update("2027-01-04", prices, fx)
    assert new_year["rebalanced"] is True


# --------------------------------------------------------------- statistics
def test_stats_are_empty_without_history(db):
    assert eng.stats() == {"points": 0}


def test_total_return_tracks_price_moves(db, fx, prices):
    eng.update("2026-01-05", prices, fx)
    doubled = {t: p * 2 for t, p in prices.items()}
    eng.update("2026-01-06", doubled, fx)

    s = eng.stats()
    assert s["points"] == 2
    # Not exactly 100%: whole-share rounding leaves cash behind, which does not
    # double. Slightly under is the correct answer, and pinning it down is how a
    # regression in the cash handling would be noticed.
    assert 0.90 < s["total_return"] < 1.00


def test_simulate_touches_no_stored_state(db, fx, prices):
    eng.update("2026-01-05", prices, fx)
    before = db.nav_history()

    series = eng.simulate(
        ["2026-01-05", "2026-01-06"],
        lambda d: {t: {"close": p, "date": d} for t, p in prices.items()},
        lambda d: fx,
    )

    assert len(series) == 2
    assert series[0]["nav_per_share"] == pytest.approx(50.0, rel=1e-9)
    assert db.nav_history() == before, "simulation must not write anything"


# ------------------------------------------------------------------ dividends
# Reinvested income is kept in its own book so its contribution stays visible,
# it compounds because the shares it buys earn dividends themselves, and the
# annual rebalance absorbs it.
#
# The rule these tests exist to protect: the cash is credited on the EX-DATE
# (the price gaps down that morning, so the value is real from then) but it buys
# shares only on the PAY DATE, at the price of that session. Money that has not
# arrived cannot buy anything.

def _div(ticker, date, per_share):
    return [{"ticker": ticker, "date": date, "per_share": per_share}]


def _pay(ticker, ex_date, pay_date):
    return {(ticker, ex_date): pay_date}


def _at(price, prices):
    return {t: price for t in prices}


def test_the_ex_date_credits_cash_and_buys_nothing(db, fx, prices):
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)          # seed
    held = db.load_index_state()[0]["KO"]
    assert held > 0

    r = ie.apply_dividends("2026-06-02", prices, fx,
                           _div("KO", "2026-06-02", 1.0),
                           _pay("KO", "2026-06-02", "2026-06-20"))

    assert len(r["accrued"]) == 1 and r["settled"] == []
    e = r["accrued"][0]
    assert e["shares_held"] == held
    assert e["gross"] == pytest.approx(held * 1.0)
    assert e["shares_bought"] == 0, "nothing may be bought before the cash arrives"
    assert e["pay_date"] == "2026-06-20"

    shares, cash = db.load_dividend_state()
    assert shares == {}, "no shares on the ex-date"
    assert db.pending_dividend_cash()["KO"] == pytest.approx(held * 1.0)


def test_accrued_cash_is_in_nav_before_it_is_paid(db, fx, prices):
    """The reason accrual happens on the ex-date at all: the price gaps down
    that morning, so leaving the money out would show a dip that never happened."""
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    before = [h for h in db.nav_history() if h["date"] == "2026-06-01"][0]["nav_usd"]
    held = db.load_index_state()[0]["KO"]

    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-20"))
    r = ie.update("2026-06-02", prices, fx)

    assert r["dividend_equity_usd"] == 0, "no shares yet"
    assert r["dividend_cash_usd"] == pytest.approx(held * 1.0)
    assert r["nav_usd"] == pytest.approx(before + held * 1.0), (
        "income accrued must be in NAV the day the price gaps down")


def test_the_pay_date_buys_at_the_price_of_that_session(db, fx, prices):
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    held = db.load_index_state()[0]["KO"]
    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-20"))

    # The price has doubled between the ex-date and the pay date. The purchase
    # must use 20.0 - the price on the day the money actually arrived.
    later = _at(20.0, prices)
    r = ie.apply_dividends("2026-06-20", later, fx, [], None)

    assert r["accrued"] == [] and len(r["settled"]) == 1
    st = r["settled"][0]
    assert st["price"] == 20.0
    assert st["shares_bought"] == int(held * 1.0 // 20.0)
    assert db.load_dividend_state()[0]["KO"] == st["shares_bought"]
    assert db.pending_dividend_cash() == {}, "the accrual is no longer pending"


def test_settlement_runs_on_a_session_with_no_dividends(db, fx, prices):
    """A pay date almost always lands on a session where nothing goes ex, so an
    early return on an empty div_rows would strand every payment forever."""
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-20"))

    r = ie.apply_dividends("2026-06-22", prices, fx, [], None)
    assert len(r["settled"]) == 1, "a pay date already passed must still settle"


def test_a_pay_date_on_a_closed_day_settles_on_the_next_session(db, fx, prices):
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-20"))   # a Saturday

    assert ie.apply_dividends("2026-06-19", prices, fx, [], None)["settled"] == []
    assert len(ie.apply_dividends("2026-06-22", prices, fx, [], None)["settled"]) == 1


def test_without_a_pay_date_the_cash_waits_indefinitely(db, fx, prices):
    """As specified: idle cash is preferable to shares bought on a guessed date.
    Yahoo publishes no pay date for any London, Tokyo or European listing."""
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    held = db.load_index_state()[0]["KO"]
    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", None))

    for day in ("2026-06-20", "2026-09-01", "2026-12-31"):
        assert ie.apply_dividends(day, prices, fx, [], None)["settled"] == []

    assert db.load_dividend_state()[0] == {}, "no shares were ever bought"
    assert db.pending_dividend_cash()["KO"] == pytest.approx(held * 1.0), (
        "but the money is still there, and still counted in NAV")


def test_dividend_shares_earn_dividends_too(db, fx, prices):
    """The compounding the separate book exists to make visible."""
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    main = db.load_index_state()[0]["KO"]

    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-20"))
    settled = ie.apply_dividends("2026-06-20", prices, fx, [], None)["settled"]
    bought = settled[0]["shares_bought"]
    assert bought > 0

    second = ie.apply_dividends("2026-09-02", prices, fx,
                                _div("KO", "2026-09-02", 1.0),
                                _pay("KO", "2026-09-02", "2026-09-20"))["accrued"][0]
    assert second["shares_held"] == main + bought, (
        "the second payment must be paid on the shares the first one bought")


def test_the_same_dividend_is_never_accrued_twice(db, fx, prices):
    """A ten-day fetch window sees the same ex-date on many consecutive days."""
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    rows = _div("KO", "2026-06-02", 1.0)
    pays = _pay("KO", "2026-06-02", "2026-06-20")

    first = ie.apply_dividends("2026-06-02", prices, fx, rows, pays)
    again = ie.apply_dividends("2026-06-02", prices, fx, rows, pays)

    assert len(first["accrued"]) == 1 and again["accrued"] == []
    held = db.load_index_state()[0]["KO"]
    assert db.pending_dividend_cash()["KO"] == pytest.approx(held * 1.0)


def test_the_same_dividend_is_never_settled_twice(db, fx, prices):
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-20"))

    first = ie.apply_dividends("2026-06-20", prices, fx, [], None)["settled"]
    again = ie.apply_dividends("2026-06-21", prices, fx, [], None)["settled"]

    assert again == []
    assert db.load_dividend_state()[0]["KO"] == first[0]["shares_bought"]


def test_an_unpriced_constituent_stays_pending(db, fx, prices):
    """Settling at a guessed price would be worse than settling a session late."""
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-20"))

    no_ko = {t: v for t, v in prices.items() if t != "KO"}
    assert ie.apply_dividends("2026-06-20", no_ko, fx, [], None)["settled"] == []
    assert db.pending_dividend_cash().get("KO", 0) > 0

    assert len(ie.apply_dividends("2026-06-21", prices, fx, [], None)["settled"]) == 1


def test_dividend_shares_count_towards_nav(db, fx, prices):
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    before = [h for h in db.nav_history() if h["date"] == "2026-06-01"][0]["nav_usd"]

    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-03"))
    ie.apply_dividends("2026-06-03", prices, fx, [], None)
    r = ie.update("2026-06-03", prices, fx)

    assert r["dividend_equity_usd"] > 0
    assert r["nav_usd"] > before, "income received must raise NAV, not vanish"


def test_the_rebalance_absorbs_the_dividend_book(db, fx, prices):
    """As requested: the dividend portfolio is emptied at the rebalance and its
    shares go back into the pot with everything else."""
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    ie.apply_dividends("2026-06-02", prices, fx, _div("KO", "2026-06-02", 1.0),
                       _pay("KO", "2026-06-02", "2026-06-03"))
    ie.apply_dividends("2026-06-03", prices, fx, [], None)
    assert db.load_dividend_state()[0].get("KO", 0) > 0

    before = ie.update("2026-06-03", prices, fx)["nav_usd"]

    r = ie.update("2027-01-04", prices, fx)      # first session of a new year
    assert r["rebalanced"] is True

    shares, cash = db.load_dividend_state()
    assert shares == {} and cash == {}, "the dividend book is emptied"
    assert r["dividend_equity_usd"] == 0

    assert r["nav_usd"] == pytest.approx(before, rel=1e-6), (
        "absorbing the book must move the shares, not the value - anything else "
        "means a year of reinvested income was dropped on the floor")


def test_the_rebalance_absorbs_cash_still_waiting_on_a_pay_date(db, fx, prices):
    """Money accrued but never paid still belongs to the fund, and a pay date
    falling after the rebalance must not buy for a book that no longer exists."""
    import index_engine as ie

    ie.update("2026-06-01", prices, fx)
    held = db.load_index_state()[0]["KO"]
    ie.apply_dividends("2026-12-30", prices, fx, _div("KO", "2026-12-30", 1.0),
                       _pay("KO", "2026-12-30", None))          # never settles
    before = ie.update("2026-12-30", prices, fx)["nav_usd"]
    assert db.pending_dividend_cash()["KO"] == pytest.approx(held * 1.0)

    r = ie.update("2027-01-04", prices, fx)
    assert r["rebalanced"] is True
    assert db.pending_dividend_cash() == {}, "pending cash is absorbed too"
    assert r["nav_usd"] == pytest.approx(before, rel=1e-6), (
        "absorbing it must move the value into the main book, not discard it")
