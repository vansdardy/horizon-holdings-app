# -*- coding: utf-8 -*-
"""
The HTTP contract.

The frontend depends on these shapes, so this file is really a test of the
agreement between the two halves of the application. Note that TestClient is
deliberately NOT used as a context manager: entering it runs the app's lifespan,
which starts the daily scheduler, and a test suite that fires real fetches
depending on what time it is run is worse than no test at all.
"""
import math

import pytest
from fastapi.testclient import TestClient

import db as db_module
import server
import universe as u


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "api.db"))
    db_module.init()
    return TestClient(server.app)


# ----------------------------------------------------------------- read-only
def test_status_reports_the_data_source(client):
    body = client.get("/api/status").json()
    assert body["is_mock"] is True, "the suite must never hit the live market data source"
    assert "config" in body and "archive" in body


def test_universe_weights_sum_to_one(client):
    body = client.get("/api/universe").json()
    assert len(body["holdings"]) == 78
    assert sum(h["target_weight"] for h in body["holdings"]) == pytest.approx(1.0)


def test_universe_entries_carry_what_the_frontend_needs(client):
    row = client.get("/api/universe").json()["holdings"][0]
    for field in ("ticker", "name", "ccy", "sector", "country", "exchange", "target_weight"):
        assert field in row, f"the page renders {field}; removing it breaks the table"


def test_positions_are_listed_for_every_constituent(client):
    body = client.get("/api/positions").json()
    assert len(body["rows"]) == 78, "unheld names still appear, so gaps can be seen"
    assert body["totals"]["positions_held"] == 0


def test_guide_is_served_as_a_whole_document(client):
    r = client.get("/guide")
    assert r.status_code == 200
    assert r.text.lstrip().startswith("<!DOCTYPE html>"), "a fragment would render in quirks mode"


def test_interactive_api_docs_are_not_shadowed(client):
    """/guide must not be mounted at /docs, which FastAPI already owns."""
    assert client.get("/docs").status_code == 200


# ----------------------------------------------------------------- writes
def test_saving_a_position_round_trips(client):
    r = client.post("/api/positions", json={"positions": [
        {"ticker": "AAPL", "shares": 10, "avg_cost": 180.0, "note": "test"}]})
    assert r.status_code == 200

    row = next(x for x in client.get("/api/positions").json()["rows"] if x["ticker"] == "AAPL")
    assert row["shares"] == 10 and row["avg_cost"] == 180.0


def test_zeroing_a_position_removes_it(client):
    client.post("/api/positions", json={"positions": [
        {"ticker": "AAPL", "shares": 10, "avg_cost": 180.0}]})
    client.post("/api/positions", json={"positions": [
        {"ticker": "AAPL", "shares": 0, "avg_cost": 0}]})
    assert client.get("/api/positions").json()["totals"]["positions_held"] == 0


def test_unknown_tickers_are_rejected(client):
    r = client.post("/api/positions", json={"positions": [
        {"ticker": "NOT-A-REAL-TICKER", "shares": 1, "avg_cost": 1}]})
    assert r.status_code == 400
    assert "unknown ticker" in r.json()["detail"]


def test_non_finite_numbers_are_rejected_with_a_readable_error(client):
    """
    NaN and Infinity must not reach the database. The custom validation handler
    exists because FastAPI echoes the offending value back, and serialising NaN
    turns a clean 422 into a confusing 500.
    """
    r = client.post("/api/positions", content=b'{"positions":[{"ticker":"AAPL","shares":NaN,"avg_cost":1}]}',
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert r.json()["detail"]


def test_negative_positions_are_rejected(client):
    r = client.post("/api/positions", json={"positions": [
        {"ticker": "AAPL", "shares": -5, "avg_cost": 10}]})
    assert r.status_code == 422


def test_unsupported_currency_is_rejected(client):
    assert client.post("/api/cash", json={"cash": [{"ccy": "XYZ", "amount": 10}]}).status_code == 400


def test_reset_requires_explicit_confirmation(client):
    """A destructive endpoint that fires on a bare POST is an accident waiting."""
    assert client.post("/api/reset_index").status_code == 400
    assert client.post("/api/reset_index?confirm=true").status_code == 200


# ----------------------------------------------------------------- the pipeline
def test_refresh_seeds_the_index_and_persists_prices(client):
    body = client.post("/api/refresh?window=3").json()
    assert body["ok"] is True
    assert body["n_priced"] == 78
    assert body["nav_per_share"] == pytest.approx(50.0, rel=1e-6)
    assert body["rows_persisted"] > 0

    assert client.get("/api/archive").json()["price_rows"] > 0, "raw data lands on disk"


def test_day_offset_is_refused_outside_mock_mode(client, monkeypatch):
    monkeypatch.setattr(server.marketdata, "USE_MOCK", False)
    r = client.post("/api/refresh?day_offset=-3")
    assert r.status_code == 400
    assert "mock" in r.json()["detail"].lower()


def test_refresh_window_is_bounded(client):
    assert client.post("/api/refresh?window=999").status_code == 400


def test_simulate_rejects_a_malformed_date(client):
    assert client.get("/api/nav/simulate?inception=not-a-date").status_code == 400


def test_simulate_reports_an_empty_archive_clearly(client):
    r = client.get("/api/nav/simulate?inception=2020-01-01")
    assert r.status_code == 400
    assert "archive" in r.json()["detail"]


def test_export_contains_every_section(client):
    client.post("/api/refresh?window=1")
    body = client.get("/api/export").json()
    for section in ("positions", "nav_history", "price_history", "fx_history", "archive"):
        assert section in body, "export is the anti-lock-in promise; a missing section breaks it"


def test_price_history_csv_is_well_formed(client):
    client.post("/api/refresh?window=1")
    r = client.get("/api/price_history.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0] == "date,ticker,close,ccy"


# ------------------------------------------------------- the index's own book
# These exist because the holdings endpoint publishes numbers a reader is
# invited to add up. If its arithmetic drifts from the NAV series by even a
# little, the page invites them to catch the application in an inconsistency —
# which is worse than never having shown the ledger at all.

def test_holdings_are_empty_before_the_index_is_seeded(client):
    body = client.get("/api/index_holdings").json()
    assert body["seeded"] is False
    assert body["holdings"] == [] and body["cash"] == []


def test_holdings_reconcile_with_the_published_nav(client):
    client.post("/api/refresh?window=3")
    book = client.get("/api/index_holdings").json()
    nav = client.get("/api/nav").json()

    assert book["seeded"] is True
    latest = nav["history"][-1]
    assert book["as_of"] == latest["date"], "the ledger must be marked on the NAV's own date"

    # The whole promise of the section: securities + cash IS the NAV.
    rows = sum(h["value_usd"] or 0 for h in book["holdings"])
    cash = sum(c["amount_usd"] or 0 for c in book["cash"])
    assert rows + cash == pytest.approx(book["totals"]["nav_usd"], rel=1e-12)
    assert book["totals"]["nav_usd"] == pytest.approx(latest["nav_usd"], rel=1e-9)
    assert book["totals"]["nav_base"] == pytest.approx(latest["nav_base"], rel=1e-9)
    assert book["totals"]["nav_per_share_base"] == pytest.approx(
        latest["nav_per_share"], rel=1e-9), "per-unit NAV is quoted in the base currency"


def test_holdings_are_whole_shares_with_the_remainder_in_cash(client):
    client.post("/api/refresh?window=3")
    book = client.get("/api/index_holdings").json()

    assert len(book["holdings"]) == 78
    for h in book["holdings"]:
        assert isinstance(h["shares"], int), f"{h['ticker']} holds a fractional share"

    # Every currency the index bought in keeps a residual cash pool, and no
    # residual can be negative: that would mean it spent money it did not have.
    assert book["cash"], "buying whole shares must leave a remainder somewhere"
    for c in book["cash"]:
        assert c["amount"] >= 0, f"{c['ccy']} cash went negative"


def test_holdings_weights_are_shares_of_the_same_nav(client):
    client.post("/api/refresh?window=3")
    book = client.get("/api/index_holdings").json()

    total = sum(h["actual_weight"] for h in book["holdings"])
    cash_pct = book["totals"]["cash_pct"]
    assert total + cash_pct == pytest.approx(1.0, abs=1e-9), (
        "actual weights plus cash must account for the whole fund")


# ---------------------------------------------------- the oversized GBP pool
# The pence bug left the pound cash pool about ninety times larger than buying
# whole shares should leave. The page explains that until a rebalance reinvests
# it — and the explanation has to be driven by MEASURING the pool, not by a flag
# the migration sets.
#
# The flag version shipped in v1.10.2 and reached nobody it was written for: it
# could only be raised while migrating, so anyone who had taken the previous
# release already carried a migrated database and never saw a word. These tests
# pin the property that made that failure possible.

def _seed_with_gbp_cash(client, gbp_cash):
    """Seed the index, then set the GBP pool to a chosen size."""
    import db as db_module
    client.post("/api/refresh?window=3")
    holdings, cash = db_module.load_index_state()
    cash["GBP"] = gbp_cash
    db_module.save_index_state(holdings, cash)


def test_an_oversized_pound_pool_is_explained(client):
    import universe as u
    import db as db_module

    client.post("/api/refresh?window=3")
    prices = db_module.prices_asof(db_module.latest_price_date())
    typical = sum(prices[t]["close"] for t in u.pence_quoted() if t in prices) / 2.0
    _seed_with_gbp_cash(client, typical * 90)      # the size the bug leaves

    note = client.get("/api/index_holdings").json()["cash_notice"]
    assert note is not None, "a pool ninety times too big must be explained"
    assert note["ccy"] == "GBP"
    assert note["ratio"] == pytest.approx(90.0, rel=0.05)
    assert note["excess"] > 0


def test_a_normal_pound_pool_is_not_explained(client):
    import universe as u
    import db as db_module

    client.post("/api/refresh?window=3")
    prices = db_module.prices_asof(db_module.latest_price_date())
    typical = sum(prices[t]["close"] for t in u.pence_quoted() if t in prices) / 2.0
    _seed_with_gbp_cash(client, typical * 1.5)     # ordinary rounding scatter

    assert client.get("/api/index_holdings").json()["cash_notice"] is None, (
        "every currency's pool varies; only a pool far outside that range is a symptom")


def test_the_explanation_does_not_depend_on_having_just_migrated(client):
    """The bug in the first attempt: the notice was raised by the migration, so a
    database migrated by an earlier release — which is every database belonging
    to someone who updates promptly — never showed it."""
    import universe as u
    import db as db_module

    client.post("/api/refresh?window=3")
    prices = db_module.prices_asof(db_module.latest_price_date())
    typical = sum(prices[t]["close"] for t in u.pence_quoted() if t in prices) / 2.0
    _seed_with_gbp_cash(client, typical * 90)

    # Exactly the state of a database migrated by the previous version: the
    # migration has run and will never run again.
    db_module.set_meta(db_module.PENCE_MIGRATION_KEY, "1")

    assert client.get("/api/index_holdings").json()["cash_notice"] is not None, (
        "the condition is still true, so it must still be explained")


def test_the_explanation_goes_away_when_the_pool_is_reinvested(client):
    """A rebalance rebuilds every pool out of the whole NAV, so the ratio falls
    back to about one. Nothing has to be cleared — the condition simply ends."""
    import universe as u
    import db as db_module

    client.post("/api/refresh?window=3")
    prices = db_module.prices_asof(db_module.latest_price_date())
    typical = sum(prices[t]["close"] for t in u.pence_quoted() if t in prices) / 2.0
    _seed_with_gbp_cash(client, typical * 90)
    assert client.get("/api/index_holdings").json()["cash_notice"] is not None

    _seed_with_gbp_cash(client, typical * 0.8)     # what a rebalance leaves
    assert client.get("/api/index_holdings").json()["cash_notice"] is None


# ------------------------------------------------------------- output encoding
# A user on a non-UTF-8-locale Windows machine hit a startup crash:
# UnicodeEncodeError: 'charmap' codec can't encode characters ... character
# maps to <undefined>. desktop/main.js sets PYTHONIOENCODING=utf-8 when it
# spawns the backend, which is necessary but was not proven sufficient — the
# crash came from somewhere that ignored it. server.py now reconfigures its own
# stdout/stderr at import time, which is the one thing that protects every
# later write through them regardless of what set the process up, including
# running `python server.py` directly with no Electron involved at all.

def test_stdout_and_stderr_are_forced_to_utf8_even_without_the_env_var():
    """The regression: with PYTHONIOENCODING absent, server.py must still leave
    stdout/stderr on utf-8 by the time it finishes importing."""
    import subprocess, sys, os

    env = dict(os.environ)
    env.pop("PYTHONIOENCODING", None)
    env.pop("PYTHONUTF8", None)
    # A non-UTF-8 preferred locale is what actually triggered the crash; force
    # one so the test fails without the fix regardless of this machine's own
    # default encoding.
    env["PYTHONIOENCODING"] = ""  # explicitly empty, not just unset

    code = (
        "import sys; "
        "before = sys.stdout.encoding; "
        "exec(open('server.py', encoding='utf-8').read()"
        ".split('from fastapi import FastAPI')[0]); "
        "print(before + '|' + sys.stdout.encoding)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=os.path.dirname(os.path.abspath(__file__)) + "/..",
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert out.returncode == 0, out.stderr
    before, after = out.stdout.strip().split("|")
    assert after == "utf-8", (
        f"server.py must force stdout to utf-8 regardless of the environment "
        f"it started with (was {before!r}, stayed {after!r})")


# --------------------------------------------------- partial NAV and revision
# Yahoo's chart endpoint publishes some constituents' closes hours after the
# session ends, so a NAV point can be computed with a previous session's close
# carried forward for those names. Before this, that was invisible AND
# permanent: n_priced counts a carried-over price as priced, and run_daily_update
# skips any date that already has a NAV row, so the archive quietly corrected
# itself while the published number never moved.

def _stalest(client):
    import db as db_module
    return {r["date"]: r for r in db_module.nav_rows_with_stale()}


def _hide_from_fetch(monkeypatch, ticker):
    """Make the fetch return no close for `ticker` on the newest session.

    This is what Yahoo's chart endpoint actually does when it has not published
    a symbol's bar yet. Deleting the row from the database instead would not
    test anything: mock mode regenerates prices on every fetch, so the deletion
    is undone by the very call under test.
    """
    real = server.marketdata.fetch

    def patched(day_offset=0, window=1):
        vd, prices, fx = real(day_offset=day_offset, window=window)
        return vd, [r for r in prices
                    if not (r["ticker"] == ticker and r["date"] == vd)], fx

    monkeypatch.setattr(server.marketdata, "fetch", patched)


def test_a_day_valued_with_a_carried_over_close_is_recorded_as_partial(client, monkeypatch):
    import db as db_module

    client.post("/api/refresh?window=3&day_offset=-1")
    _hide_from_fetch(monkeypatch, "ABBN.SW")
    client.post("/api/refresh?window=1")

    day = db_module.latest_price_date()
    row = _stalest(client).get(day)
    assert row is not None, "the day must be recorded as partial, not silently accepted"
    assert row["stale_count"] >= 1
    assert "ABBN.SW" in (row["stale_tickers"] or ""), (
        "which constituents were carried over has to be recorded, or nothing "
        "can find this day again once the data lands")


def test_a_partial_day_is_recomputed_once_the_close_arrives(client, monkeypatch):
    import db as db_module

    client.post("/api/refresh?window=3&day_offset=-1")
    _hide_from_fetch(monkeypatch, "ABBN.SW")
    client.post("/api/refresh?window=1")
    day = db_module.latest_price_date()

    before = next(h for h in db_module.nav_history() if h["date"] == day)
    assert before["stale_count"] >= 1
    assert before["revised_at"] is None

    # The late close lands in the archive, as a later fetch's window would bring it.
    db_module.upsert_prices([{"ticker": "ABBN.SW", "close": 123.45, "date": day}])
    body = client.post("/api/revise").json()

    assert day in body["revised"]
    after = next(h for h in db_module.nav_history() if h["date"] == day)
    assert after["stale_count"] == 0
    assert after["revised_at"], "a corrected point must say it was corrected"
    assert after["nav_per_share"] != before["nav_per_share"]
    assert after["rebalanced"] == before["rebalanced"], (
        "revision must not erase the flag marking a rebalance day")


def test_revision_is_idempotent(client, monkeypatch):
    import db as db_module

    client.post("/api/refresh?window=3&day_offset=-1")
    _hide_from_fetch(monkeypatch, "ABBN.SW")
    client.post("/api/refresh?window=1")
    day = db_module.latest_price_date()
    db_module.upsert_prices([{"ticker": "ABBN.SW", "close": 123.45, "date": day}])

    assert client.post("/api/revise").json()["revised"] == [day]
    assert client.post("/api/revise").json()["revised"] == [], (
        "rewriting a published number for no gain is what makes a series "
        "untrustworthy; a second pass must change nothing")


def test_revision_never_reaches_past_a_rebalance(client):
    """revalue() marks against the holdings stored NOW. Share counts change at a
    rebalance, so correcting a day on the far side would value it with shares
    the index did not own at the time."""
    import db as db_module

    client.post("/api/refresh?window=3&day_offset=-1")
    day = db_module.latest_price_date()

    # Pretend this day sits before the current rebalance period.
    db_module.set_nav_staleness(day, ["ABBN.SW"])
    db_module.set_meta("last_rebalance_year", str(int(day[:4]) + 1))

    assert client.post("/api/revise").json()["revised"] == [], (
        "a day before the last rebalance must be left alone")
