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


# ------------------------------------------------------------- quote units
# The London Stock Exchange quotes ordinary shares in pence, and Yahoo passes
# that straight through, so a GBP-denominated constituent arrives priced a
# hundred times too high with nothing in the response to say so.
#
# It is worth being precise about what that broke, because the obvious guess is
# wrong. It did NOT move the index NAV: the same inflated price decided how many
# shares to buy AND valued them afterwards, so the error cancelled exactly —
# which is why it survived so long looking healthy. What it corrupted is every
# figure that depends on price alone: share counts a hundred times too small,
# and the market value of a real position typed in from a broker statement a
# hundred times too large.

def test_london_listings_are_known_to_be_quoted_in_pence():
    import universe as u

    pence = u.pence_quoted()
    assert pence, "the universe contains London listings, so some must be pence-quoted"
    for t in pence:
        assert u.UNIVERSE[t]["ccy"] == "GBP"
        assert u.price_divisor(t) == 100.0

    for t in ("AAPL", "NESN.SW", "SAP", "4568.T"):
        assert u.price_divisor(t) == 1.0, f"{t} is not quoted in a minor unit"


def test_pence_migration_leaves_the_fund_worth_exactly_what_it_was(db, monkeypatch):
    import universe as u

    uk = u.pence_quoted()[0]
    other = "AAPL"

    # A database in the old, wrong state: pence prices and the hundredth of the
    # share count that buying at those prices produces.
    db.upsert_prices([
        {"date": "2026-03-02", "ticker": uk, "close": 1200.0},     # £12.00 in pence
        {"date": "2026-03-02", "ticker": other, "close": 300.0},
    ])
    db.save_index_state({uk: 1_000, other: 5_000}, {"GBP": 42.0})
    db.set_meta(db.PENCE_MIGRATION_KEY, "")   # pretend the migration never ran

    before_uk = 1200.0 * 1_000
    db.init()

    after = db.prices_asof("2026-03-02")
    holdings, cash = db.load_index_state()

    assert after[uk]["close"] == 12.0, "the archive should now be in pounds"
    assert holdings[uk] == 100_000, "and the share count should be true"
    assert after[uk]["close"] * holdings[uk] == before_uk, (
        "market value — and therefore NAV — must not move by a penny")

    assert after[other]["close"] == 300.0, "a non-pence listing must be untouched"
    assert holdings[other] == 5_000
    assert cash["GBP"] == 42.0, "cash was already in pounds and is not rescaled"


def test_pence_migration_runs_once(db):
    import universe as u

    uk = u.pence_quoted()[0]
    db.upsert_prices([{"date": "2026-03-02", "ticker": uk, "close": 1200.0}])
    db.save_index_state({uk: 1_000}, {})
    db.set_meta(db.PENCE_MIGRATION_KEY, "")

    db.init()
    db.init()
    db.init()

    assert db.prices_asof("2026-03-02")[uk]["close"] == 12.0, (
        "a second run must not divide again — the flag, not the values, decides")
    assert db.load_index_state()[0][uk] == 100_000


def test_pence_migration_raises_a_notice_only_when_it_changed_something(db):
    import universe as u

    uk = u.pence_quoted()[0]
    db.upsert_prices([{"date": "2026-03-02", "ticker": uk, "close": 1200.0}])
    db.save_index_state({uk: 1_000}, {"GBP": 900.0})
    db.set_meta(db.PENCE_MIGRATION_KEY, "")
    db.set_meta(db.GBX_CASH_NOTICE_KEY, "")

    db.init()
    assert db.get_meta(db.GBX_CASH_NOTICE_KEY), (
        "a database that actually held pence prices has an oversized GBP cash "
        "pool, and the page should say so")


def test_a_clean_database_gets_no_cash_notice(db):
    # Nothing to migrate: no notice, or every new user sees a warning about a
    # bug that never touched them.
    db.set_meta(db.PENCE_MIGRATION_KEY, "")
    db.init()
    assert not db.get_meta(db.GBX_CASH_NOTICE_KEY)
