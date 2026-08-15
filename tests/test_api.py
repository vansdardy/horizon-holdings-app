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
