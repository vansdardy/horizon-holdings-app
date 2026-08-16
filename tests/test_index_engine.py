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
