# -*- coding: utf-8 -*-
"""
Shared test setup.

The application modules read configuration from the environment at *import*
time, so anything that must not point at real data has to be set before the
first import happens — which is why this lives in conftest.py rather than in a
fixture. Getting this wrong means a test run quietly operating on the real
portfolio database.
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_scratch = tempfile.mkdtemp(prefix="horizon-tests-")
os.environ["MARKETDATA_MOCK"] = "1"
os.environ["PORTFOLIO_DB"] = os.path.join(_scratch, "import-time.db")
os.environ["PORTFOLIO_ENV_FILE"] = os.path.join(_scratch, "no-such.env")

import pytest  # noqa: E402

import db as db_module  # noqa: E402
import universe as u  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A freshly created, empty database, isolated per test.

    db.conn() reads DB_PATH at call time rather than capturing it at import,
    which is what makes this substitution work at all.
    """
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init()
    return db_module


@pytest.fixture
def fx():
    """Every non-USD currency worth exactly one USD.

    Deliberately not realistic: it makes expected values checkable by hand, so a
    failing assertion points at the logic rather than at arithmetic nobody can
    verify by reading.
    """
    return {c: 1.0 for c in u.CURRENCIES if c != u.NUMERAIRE}


@pytest.fixture
def prices():
    """Every constituent priced at 10 units of its own currency."""
    return {t: 10.0 for t in u.UNIVERSE}
