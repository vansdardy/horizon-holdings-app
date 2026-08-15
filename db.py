# -*- coding: utf-8 -*-
"""SQLite persistence. Single file DB, no external services required."""
import sqlite3
import os
from contextlib import contextmanager

import config  # loads .env before anything reads os.environ

DB_PATH = config.DB_PATH

SCHEMA = """
PRAGMA journal_mode=WAL;

-- daily closing price per ticker, in the stock's LOCAL currency
CREATE TABLE IF NOT EXISTS prices (
    date   TEXT NOT NULL,
    ticker TEXT NOT NULL,
    close  REAL NOT NULL,
    PRIMARY KEY (date, ticker)
);

-- daily FX: usd_per_unit = USD value of 1 unit of ccy
CREATE TABLE IF NOT EXISTS fx (
    date         TEXT NOT NULL,
    ccy          TEXT NOT NULL,
    usd_per_unit REAL NOT NULL,
    PRIMARY KEY (date, ccy)
);

-- the model index's integer share count (changes only on rebalance)
CREATE TABLE IF NOT EXISTS index_holdings (
    ticker TEXT PRIMARY KEY,
    shares INTEGER NOT NULL
);

-- residual cash per currency held by the model index
CREATE TABLE IF NOT EXISTS index_cash (
    ccy    TEXT PRIMARY KEY,
    amount REAL NOT NULL
);

-- one NAV observation per day
CREATE TABLE IF NOT EXISTS nav_history (
    date          TEXT PRIMARY KEY,
    nav_usd       REAL NOT NULL,
    nav_per_share REAL NOT NULL,
    equity_usd    REAL NOT NULL,
    cash_usd      REAL NOT NULL,
    n_priced      INTEGER NOT NULL,
    rebalanced    INTEGER NOT NULL DEFAULT 0
);

-- the user's REAL positions (this is the part that is actually theirs)
CREATE TABLE IF NOT EXISTS user_positions (
    ticker        TEXT PRIMARY KEY,
    shares        REAL NOT NULL DEFAULT 0,
    avg_cost      REAL NOT NULL DEFAULT 0,   -- per share, in the stock's LOCAL currency
    note          TEXT DEFAULT '',
    updated_at    TEXT
);

-- the user's uncommitted cash, per currency. Cash rarely divides evenly into
-- whole shares, so a real portfolio almost always carries some.
CREATE TABLE IF NOT EXISTS user_cash (
    ccy        TEXT PRIMARY KEY,
    amount     REAL NOT NULL DEFAULT 0,
    updated_at TEXT
);

-- append-only log of user edits, so nothing is silently lost
CREATE TABLE IF NOT EXISTS user_position_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    ticker     TEXT NOT NULL,
    shares     REAL NOT NULL,
    avg_cost   REAL NOT NULL
);

-- quarterly fundamentals snapshot (P/E, dividend yield, beta) per ticker.
-- Unlike prices/fx this is NOT daily: it is fetched once per calendar quarter
-- (Jan/Apr/Jul/Oct 1) because these figures move slowly and the per-ticker
-- Yahoo endpoint that provides them is far heavier and less reliable than the
-- batched price download. `as_of` records the actual fetch date so the page
-- can show its own age honestly rather than implying same-day freshness.
CREATE TABLE IF NOT EXISTS fundamentals (
    quarter   TEXT NOT NULL,   -- 'YYYY-Q1' etc, the quarter this snapshot represents
    ticker    TEXT NOT NULL,
    pe        REAL,
    pe_type   TEXT,            -- 'trailing' | 'forward' | 'computed' | NULL — which P/E this is,
                                -- since trailing and forward can differ by multiples for a
                                -- richly-valued name and must never be shown unlabeled
    div_yield REAL,
    beta      REAL,
    as_of     TEXT NOT NULL,   -- actual date the data was fetched
    PRIMARY KEY (quarter, ticker)
);

-- user's own cash contributions, to track money-weighted context
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    # sqlite3.connect creates the file but not its parent, and the packaged app
    # points DB_PATH at a per-user directory that may not exist yet.
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)
        # Added after first release; ALTER is idempotent-guarded by column check.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(nav_history)")}
        if "nav_base" not in cols:
            c.execute("ALTER TABLE nav_history ADD COLUMN nav_base REAL")
        if "base_ccy" not in cols:
            c.execute("ALTER TABLE nav_history ADD COLUMN base_ccy TEXT")
        fcols = {r["name"] for r in c.execute("PRAGMA table_info(fundamentals)")}
        if fcols and "pe_type" not in fcols:
            c.execute("ALTER TABLE fundamentals ADD COLUMN pe_type TEXT")
    _migrate_renamed_tickers()


# Internal ticker keys that were renamed after data may already have been stored.
# Old rows must be carried over, otherwise saved positions and price history are
# silently orphaned (and stale keys in index_holdings crash valuation).
TICKER_RENAMES = {
    "ROG.SW": "RO.SW",   # Roche: old Yahoo symbol retired; SIX registered share is RO
}


def _migrate_renamed_tickers():
    moved = {}
    with conn() as c:
        for old, new in TICKER_RENAMES.items():
            hit = False
            for table, col in (("prices", "ticker"), ("index_holdings", "ticker"),
                               ("user_positions", "ticker"), ("user_position_log", "ticker")):
                n = c.execute(f"SELECT COUNT(*) n FROM {table} WHERE {col}=?", (old,)).fetchone()["n"]
                if not n:
                    continue
                hit = True
                # A row for the new key may already exist (unique/PK collision):
                # keep the newer data and drop the stale duplicate.
                if table in ("prices",):
                    c.execute("DELETE FROM prices WHERE ticker=? AND date IN "
                              "(SELECT date FROM prices WHERE ticker=?)", (old, new))
                else:
                    c.execute(f"DELETE FROM {table} WHERE {col}=? AND EXISTS "
                              f"(SELECT 1 FROM {table} t2 WHERE t2.{col}=?)", (old, new))
                c.execute(f"UPDATE {table} SET {col}=? WHERE {col}=?", (new, old))
                moved[f"{table}.{old}->{new}"] = n
            if hit:
                print(f"[db] migrated ticker {old} -> {new}")
    return moved


# ---------- meta ----------
def get_meta(key, default=None):
    with conn() as c:
        r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default


def set_meta(key, value):
    with conn() as c:
        c.execute("INSERT INTO meta(key,value) VALUES(?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


# ---------- market data ----------
def upsert_prices(price_rows):
    """price_rows: [{"ticker":…, "close":…, "date":…}, …]
    Each quote is stored under the session it actually traded in."""
    with conn() as c:
        c.executemany(
            "INSERT INTO prices(date,ticker,close) VALUES(?,?,?) "
            "ON CONFLICT(date,ticker) DO UPDATE SET close=excluded.close",
            [(r["date"], r["ticker"], float(r["close"])) for r in price_rows])
    return len(price_rows)


def upsert_fx(fx_rows):
    """fx_rows: [{"ccy":…, "rate":…, "date":…}, …]"""
    with conn() as c:
        c.executemany(
            "INSERT INTO fx(date,ccy,usd_per_unit) VALUES(?,?,?) "
            "ON CONFLICT(date,ccy) DO UPDATE SET usd_per_unit=excluded.usd_per_unit",
            [(r["date"], r["ccy"], float(r["rate"])) for r in fx_rows])
    return len(fx_rows)


def price_history(ticker=None, start=None, end=None, limit=None):
    """Read back the saved archive. This is the whole point of persisting it."""
    q = "SELECT date,ticker,close FROM prices WHERE 1=1"
    args = []
    if ticker:
        q += " AND ticker=?"; args.append(ticker)
    if start:
        q += " AND date>=?"; args.append(start)
    if end:
        q += " AND date<=?"; args.append(end)
    q += " ORDER BY date DESC, ticker"
    if limit:
        q += " LIMIT ?"; args.append(int(limit))
    with conn() as c:
        return [dict(r) for r in c.execute(q, args)]


def fx_history(start=None, end=None):
    q = "SELECT date,ccy,usd_per_unit FROM fx WHERE 1=1"
    args = []
    if start:
        q += " AND date>=?"; args.append(start)
    if end:
        q += " AND date<=?"; args.append(end)
    q += " ORDER BY date DESC, ccy"
    with conn() as c:
        return [dict(r) for r in c.execute(q, args)]


def prices_asof(date):
    """Latest close per ticker on or before `date` (forward-fill).
    Needed to value a past day correctly instead of using today's prices."""
    with conn() as c:
        rows = c.execute(
            "SELECT p.ticker, p.close, p.date FROM prices p "
            "JOIN (SELECT ticker, MAX(date) md FROM prices WHERE date<=? GROUP BY ticker) x "
            "ON p.ticker=x.ticker AND p.date=x.md", (date,)).fetchall()
        return {r["ticker"]: {"close": r["close"], "date": r["date"]} for r in rows}


def fx_asof(date):
    with conn() as c:
        rows = c.execute(
            "SELECT f.ccy, f.usd_per_unit FROM fx f "
            "JOIN (SELECT ccy, MAX(date) md FROM fx WHERE date<=? GROUP BY ccy) x "
            "ON f.ccy=x.ccy AND f.date=x.md", (date,)).fetchall()
        return {r["ccy"]: r["usd_per_unit"] for r in rows}


def price_dates(start=None):
    """Distinct session dates present in the price archive."""
    q = "SELECT DISTINCT date FROM prices"
    args = []
    if start:
        q += " WHERE date>=?"; args.append(start)
    q += " ORDER BY date"
    with conn() as c:
        return [r["date"] for r in c.execute(q, args)]


def nav_dates():
    with conn() as c:
        return {r["date"] for r in c.execute("SELECT date FROM nav_history")}


def backup_to(dest_path):
    """
    WAL-safe backup using SQLite's online backup API.

    A plain `cp portfolio.db` is NOT safe while the service is running: in WAL
    mode, recently committed transactions live in portfolio.db-wal and have not
    yet been checkpointed into the main file, so the copy can silently omit them.
    This routine produces a single consistent file with everything committed.
    """
    src = sqlite3.connect(DB_PATH, timeout=30)
    try:
        dst = sqlite3.connect(dest_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest_path


def archive_summary():
    """Proof-of-storage: how much market data is actually on disk."""
    with conn() as c:
        p = c.execute("SELECT COUNT(*) n, COUNT(DISTINCT date) d, COUNT(DISTINCT ticker) t, "
                      "MIN(date) mn, MAX(date) mx FROM prices").fetchone()
        f = c.execute("SELECT COUNT(*) n, COUNT(DISTINCT date) d FROM fx").fetchone()
        return {
            "price_rows": p["n"], "price_dates": p["d"], "tickers_covered": p["t"],
            "first_date": p["mn"], "last_date": p["mx"],
            "fx_rows": f["n"], "fx_dates": f["d"],
            "db_path": DB_PATH,
            "db_size_bytes": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
        }


def get_prices(date):
    with conn() as c:
        return {r["ticker"]: r["close"]
                for r in c.execute("SELECT ticker,close FROM prices WHERE date=?", (date,))}


def get_fx(date):
    with conn() as c:
        return {r["ccy"]: r["usd_per_unit"]
                for r in c.execute("SELECT ccy,usd_per_unit FROM fx WHERE date=?", (date,))}


def latest_price_date():
    with conn() as c:
        r = c.execute("SELECT MAX(date) d FROM prices").fetchone()
        return r["d"]


def latest_prices():
    """Most recent close per ticker, even if some tickers lag a day."""
    with conn() as c:
        rows = c.execute(
            "SELECT p.ticker, p.close, p.date FROM prices p "
            "JOIN (SELECT ticker, MAX(date) md FROM prices GROUP BY ticker) x "
            "ON p.ticker=x.ticker AND p.date=x.md").fetchall()
        return {r["ticker"]: {"close": r["close"], "date": r["date"]} for r in rows}


def latest_prices_with_change():
    """
    Latest close per ticker plus the prior available close, so a day-over-day
    change % can be shown (e.g. on the ticker tape) without any extra fetch —
    it's derived entirely from the price archive that's already being written
    daily. Tickers with only one day on file get prev_close=None.
    """
    with conn() as c:
        rows = c.execute(
            "WITH ranked AS ("
            "  SELECT ticker, close, date, "
            "         ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn "
            "  FROM prices"
            ") "
            "SELECT ticker, "
            "  MAX(CASE WHEN rn=1 THEN close END) close, "
            "  MAX(CASE WHEN rn=1 THEN date  END) date, "
            "  MAX(CASE WHEN rn=2 THEN close END) prev_close, "
            "  MAX(CASE WHEN rn=2 THEN date  END) prev_date "
            "FROM ranked WHERE rn<=2 GROUP BY ticker").fetchall()
        out = {}
        for r in rows:
            chg = None
            if r["prev_close"]:
                chg = r["close"] / r["prev_close"] - 1
            out[r["ticker"]] = {"close": r["close"], "date": r["date"],
                                "prev_close": r["prev_close"], "prev_date": r["prev_date"],
                                "chg_pct": chg}
        return out


def latest_fx():
    with conn() as c:
        rows = c.execute(
            "SELECT f.ccy, f.usd_per_unit, f.date FROM fx f "
            "JOIN (SELECT ccy, MAX(date) md FROM fx GROUP BY ccy) x "
            "ON f.ccy=x.ccy AND f.date=x.md").fetchall()
        return {r["ccy"]: r["usd_per_unit"] for r in rows}


# ---------- index state ----------
def save_index_state(holdings, cash):
    with conn() as c:
        c.execute("DELETE FROM index_holdings")
        c.execute("DELETE FROM index_cash")
        c.executemany("INSERT INTO index_holdings(ticker,shares) VALUES(?,?)",
                      [(t, int(n)) for t, n in holdings.items()])
        c.executemany("INSERT INTO index_cash(ccy,amount) VALUES(?,?)",
                      [(k, float(v)) for k, v in cash.items()])


def load_index_state():
    with conn() as c:
        h = {r["ticker"]: r["shares"] for r in c.execute("SELECT ticker,shares FROM index_holdings")}
        k = {r["ccy"]: r["amount"] for r in c.execute("SELECT ccy,amount FROM index_cash")}
        return h, k


def upsert_nav(date, nav_usd, nav_per_share, equity_usd, cash_usd, n_priced,
               rebalanced, nav_base=None, base_ccy=None):
    with conn() as c:
        c.execute(
            "INSERT INTO nav_history(date,nav_usd,nav_per_share,equity_usd,cash_usd,"
            "n_priced,rebalanced,nav_base,base_ccy) "
            "VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(date) DO UPDATE SET "
            "nav_usd=excluded.nav_usd, nav_per_share=excluded.nav_per_share, "
            "equity_usd=excluded.equity_usd, cash_usd=excluded.cash_usd, "
            "n_priced=excluded.n_priced, rebalanced=excluded.rebalanced, "
            "nav_base=excluded.nav_base, base_ccy=excluded.base_ccy",
            (date, nav_usd, nav_per_share, equity_usd, cash_usd, n_priced,
             int(rebalanced), nav_base, base_ccy))


def nav_history():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM nav_history ORDER BY date")]


# ---------- user positions ----------
def get_user_positions():
    with conn() as c:
        return {r["ticker"]: dict(r) for r in c.execute("SELECT * FROM user_positions")}


def set_user_position(ticker, shares, avg_cost, note=""):
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn() as c:
        c.execute(
            "INSERT INTO user_positions(ticker,shares,avg_cost,note,updated_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(ticker) DO UPDATE SET shares=excluded.shares, avg_cost=excluded.avg_cost, "
            "note=excluded.note, updated_at=excluded.updated_at",
            (ticker, float(shares), float(avg_cost), note, ts))
        c.execute("INSERT INTO user_position_log(ts,ticker,shares,avg_cost) VALUES(?,?,?,?)",
                  (ts, ticker, float(shares), float(avg_cost)))


def get_user_cash():
    with conn() as c:
        return {r["ccy"]: r["amount"]
                for r in c.execute("SELECT ccy, amount FROM user_cash")}


def set_user_cash(ccy, amount):
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn() as c:
        if not amount:
            c.execute("DELETE FROM user_cash WHERE ccy=?", (ccy,))
        else:
            c.execute("INSERT INTO user_cash(ccy,amount,updated_at) VALUES(?,?,?) "
                      "ON CONFLICT(ccy) DO UPDATE SET amount=excluded.amount, "
                      "updated_at=excluded.updated_at", (ccy, float(amount), ts))


def delete_user_position(ticker):
    with conn() as c:
        c.execute("DELETE FROM user_positions WHERE ticker=?", (ticker,))


def upsert_fundamentals(quarter, as_of, rows):
    """rows: [{"ticker":…, "pe":…, "pe_type":…, "div_yield":…, "beta":…}, …]"""
    with conn() as c:
        c.executemany(
            "INSERT INTO fundamentals(quarter,ticker,pe,pe_type,div_yield,beta,as_of) "
            "VALUES(?,?,?,?,?,?,?) ON CONFLICT(quarter,ticker) DO UPDATE SET "
            "pe=excluded.pe, pe_type=excluded.pe_type, div_yield=excluded.div_yield, "
            "beta=excluded.beta, as_of=excluded.as_of",
            [(quarter, r["ticker"], r.get("pe"), r.get("pe_type"), r.get("div_yield"),
              r.get("beta"), as_of) for r in rows])
    return len(rows)


def latest_fundamentals():
    """Most recent snapshot per ticker, even if some tickers lag a quarter
    (e.g. a name added to the universe after the last fetch)."""
    with conn() as c:
        rows = c.execute(
            "SELECT f.ticker, f.pe, f.pe_type, f.div_yield, f.beta, f.quarter, f.as_of "
            "FROM fundamentals f "
            "JOIN (SELECT ticker, MAX(quarter) mq FROM fundamentals GROUP BY ticker) x "
            "ON f.ticker=x.ticker AND f.quarter=x.mq").fetchall()
        return {r["ticker"]: dict(r) for r in rows}


def fundamentals_quarters():
    with conn() as c:
        return sorted({r["quarter"] for r in c.execute("SELECT DISTINCT quarter FROM fundamentals")})


def reset_index():
    """
    Wipe the model index (holdings, cash, NAV series) so it re-seeds from
    scratch. Market data and user positions are NOT touched.

    Needed when the reporting currency changes: a NAV series that switches
    denomination halfway through is not a series, it is two incompatible ones
    glued together.
    """
    with conn() as c:
        c.execute("DELETE FROM nav_history")
        c.execute("DELETE FROM index_holdings")
        c.execute("DELETE FROM index_cash")
        c.execute("DELETE FROM meta WHERE key IN "
                  "('inception_date','last_rebalance_year','index_base_ccy')")
