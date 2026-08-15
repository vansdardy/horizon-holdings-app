# -*- coding: utf-8 -*-
"""
The persistence layer.

Most of these assert properties the schema is supposed to guarantee. Testing
them is not redundant with the constraints: it pins down what the surrounding
code does when a constraint is hit, which is the part that can regress.
"""
import os

import pytest


def test_price_writes_are_idempotent(db):
    row = [{"date": "2026-01-05", "ticker": "AAPL", "close": 100.0}]
    db.upsert_prices(row)
    db.upsert_prices([{"date": "2026-01-05", "ticker": "AAPL", "close": 101.0}])

    stored = db.price_history(ticker="AAPL")
    assert len(stored) == 1, "one price per ticker per day, enforced by the primary key"
    assert stored[0]["close"] == 101.0, "a re-fetch should correct the value, not duplicate it"


def test_prices_asof_forward_fills(db):
    db.upsert_prices([
        {"date": "2026-01-05", "ticker": "AAPL", "close": 100.0},
        {"date": "2026-01-07", "ticker": "AAPL", "close": 110.0},
    ])

    # A market closed on the 6th produces no row; valuation must still find the 5th.
    on_holiday = db.prices_asof("2026-01-06")
    assert on_holiday["AAPL"]["close"] == 100.0
    assert on_holiday["AAPL"]["date"] == "2026-01-05", "caller needs to know the quote is stale"

    assert db.prices_asof("2026-01-07")["AAPL"]["close"] == 110.0


def test_prices_asof_ignores_the_future(db):
    db.upsert_prices([{"date": "2026-01-07", "ticker": "AAPL", "close": 110.0}])
    assert db.prices_asof("2026-01-06") == {}, "backfill must never use a later price"


def test_day_over_day_change_comes_from_the_archive(db):
    db.upsert_prices([
        {"date": "2026-01-05", "ticker": "AAPL", "close": 100.0},
        {"date": "2026-01-06", "ticker": "AAPL", "close": 105.0},
    ])
    latest = db.latest_prices_with_change()["AAPL"]
    assert latest["close"] == 105.0
    # approx, not ==: 105/100 - 1 is 0.050000000000000044 in binary floating
    # point. Comparing computed floats exactly is a bug in the test, not a
    # tolerance the code needs.
    assert latest["chg_pct"] == pytest.approx(0.05)


def test_change_is_absent_with_only_one_session(db):
    db.upsert_prices([{"date": "2026-01-05", "ticker": "AAPL", "close": 100.0}])
    assert db.latest_prices_with_change()["AAPL"]["chg_pct"] is None


def test_positions_round_trip_and_are_logged(db):
    db.set_user_position("AAPL", 12.5, 180.25, note="fractional shares")
    stored = db.get_user_positions()["AAPL"]
    assert stored["shares"] == 12.5, "fractional shares are legitimate for a real broker"
    assert stored["avg_cost"] == 180.25

    db.set_user_position("AAPL", 20, 190.0)
    with db.conn() as c:
        entries = c.execute("SELECT COUNT(*) n FROM user_position_log WHERE ticker='AAPL'").fetchone()
    assert entries["n"] == 2, "every edit is appended to the log, nothing is overwritten silently"


def test_deleting_a_position_leaves_its_history(db):
    db.set_user_position("AAPL", 10, 100.0)
    db.delete_user_position("AAPL")
    assert "AAPL" not in db.get_user_positions()
    with db.conn() as c:
        n = c.execute("SELECT COUNT(*) n FROM user_position_log").fetchone()["n"]
    assert n == 1


def test_zero_cash_is_removed_rather_than_stored(db):
    db.set_user_cash("CHF", 500.0)
    assert db.get_user_cash()["CHF"] == 500.0
    db.set_user_cash("CHF", 0)
    assert "CHF" not in db.get_user_cash()


def test_latest_fundamentals_prefers_the_newest_quarter(db):
    db.upsert_fundamentals("2026-Q1", "2026-01-01", [{"ticker": "AAPL", "pe": 30.0, "pe_type": "trailing"}])
    db.upsert_fundamentals("2026-Q2", "2026-04-01", [{"ticker": "AAPL", "pe": 33.0, "pe_type": "trailing"}])
    # A name added later still shows its own most recent snapshot, not nothing.
    db.upsert_fundamentals("2026-Q1", "2026-01-01", [{"ticker": "KO", "pe": 24.0, "pe_type": "forward"}])

    latest = db.latest_fundamentals()
    assert latest["AAPL"]["pe"] == 33.0
    assert latest["AAPL"]["quarter"] == "2026-Q2"
    assert latest["KO"]["pe"] == 24.0


def test_backup_produces_a_readable_copy(db, tmp_path):
    db.upsert_prices([{"date": "2026-01-05", "ticker": "AAPL", "close": 100.0}])
    dest = tmp_path / "backup.db"
    db.backup_to(str(dest))

    assert os.path.getsize(dest) > 0
    import sqlite3
    c = sqlite3.connect(str(dest))
    assert c.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == 1
    c.close()


def test_renamed_tickers_carry_their_data_across(db):
    """
    Exchanges retire symbols. Old rows must follow the rename, or saved positions
    and price history are silently orphaned.
    """
    old, new = next(iter(db.TICKER_RENAMES.items()))
    db.upsert_prices([{"date": "2026-01-05", "ticker": old, "close": 250.0}])
    db.set_user_position(old, 5, 240.0)

    db._migrate_renamed_tickers()

    assert not db.price_history(ticker=old)
    assert db.price_history(ticker=new)[0]["close"] == 250.0
    assert new in db.get_user_positions()


def test_archive_summary_counts_what_is_stored(db):
    db.upsert_prices([
        {"date": "2026-01-05", "ticker": "AAPL", "close": 1.0},
        {"date": "2026-01-05", "ticker": "KO", "close": 2.0},
        {"date": "2026-01-06", "ticker": "AAPL", "close": 3.0},
    ])
    s = db.archive_summary()
    assert (s["price_rows"], s["price_dates"], s["tickers_covered"]) == (3, 2, 2)
    assert s["first_date"] == "2026-01-05" and s["last_date"] == "2026-01-06"
