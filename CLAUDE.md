# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-user, fully local FastAPI service that (1) computes the daily NAV of a hypothetical
78-stock model index and (2) tracks the user's real positions against that index's target
weights. All state lives in one SQLite file (`portfolio.db`). No cloud services, no API keys.
Not a git repo. UI text and most user-facing strings are Simplified Chinese; code comments are
English. `README.md` is the user-facing manual (Chinese) and is the authority on intended
behavior — read the relevant section before changing anything it documents.

## Commands

Windows, `.venv/` already present. Use it explicitly rather than relying on activation:

```bash
.venv/Scripts/python.exe server.py
```

Serves http://127.0.0.1:8000 (page) and `/docs` (interactive API). Ctrl+C to stop.

Install/refresh deps:

```bash
.venv/Scripts/pip.exe install -r requirements.txt
```

There is **no test suite and no linter config**. The project's testing mechanism is mock mode:

```bash
MARKETDATA_MOCK=1 .venv/Scripts/python.exe server.py
```

Mock mode substitutes deterministic hash-derived prices/FX and unlocks `?day_offset=N` on
`/api/refresh`, which is the only way to exercise multi-day sequences (seeding, backfill,
year-turn rebalance) without waiting real days. Point it at a throwaway DB so you don't
pollute the real NAV series:

```bash
PORTFOLIO_DB=T:/tmp/test.db MARKETDATA_MOCK=1 .venv/Scripts/python.exe server.py
```

Typical single-scenario exercise (server running):

```bash
curl -X POST "http://127.0.0.1:8000/api/refresh?window=10&day_offset=-5"
```

Verify a live install: `curl http://127.0.0.1:8000/api/check_symbols`, confirm `healthy: true`.
(README's ⚠ section says the live Yahoo path was never verified against a real network. As of
2026-08-14 it has been: all 78 constituents and 6 FX pairs resolve, and a full live
fetch→persist→NAV cycle completes. The README text has not been updated.)

### Desktop app

Rebuild the frozen backend after **any** Python change — the Electron app runs the frozen copy
in preference to source:

```bash
.venv/Scripts/python.exe -m PyInstaller backend.spec --noconfirm --distpath build/backend --workpath build/pyinstaller
```

Run the shell in development (`desktop/main.js` falls back to `.venv` + `server.py` when no
frozen bundle exists, so the shell can be iterated on without re-freezing):

```bash
cd desktop && npm install && npm start
```

Build the Windows installer into `build/desktop-dist/`:

```bash
cd desktop && npm run dist
```

### Repository and releases

Public at `https://github.com/vansdardy/horizon-holdings-app`, `main` branch. Git Credential
Manager is configured system-wide and already holds credentials, so pushes work without setup.
`gh` is **not** installed, so GitHub Releases cannot be created from here.

**`portfolio.db` must never be committed.** It holds real positions and cost basis, and the
repository is public; git history preserves deleted files, so a single accidental commit is not
undoable by deleting it later. `.gitignore` covers `*.db`, `.env`, `build/`, `node_modules/`,
and `.venv/`. Run `git status` and read the list before any first commit in a new clone.

Release sequence: bump `desktop/package.json`, re-freeze the backend if Python changed, rebuild
the installer, verify the packaged build, update `CHANGELOG.md`, commit, `git tag -a vX.Y.Z`,
push both branch and tag, then attach the installer to a GitHub Release. The installer is never
committed — 110 MB in history would burden every clone forever.

## Architecture

Import order is load-bearing: `config` must be imported before anything reads `os.environ`,
because it populates env vars from `.env` at import time (`os.environ.setdefault`, so a real
env var always wins). `db`, `marketdata`, and `universe` each import `config` first for this
reason — keep that.

```
config.py       .env + env-var resolution, range validation (SystemExit on bad values)
universe.py     78 constituents: ticker -> {yahoo, ccy, exchange, sector, score, alts}
                target_weights() = score / sum(scores). Also NUMERAIRE / BASE_CCY constants.
marketdata.py   Yahoo (yfinance) or mock. Two independent pipelines: daily batched
                prices+FX, and quarterly per-ticker fundamentals.
db.py           All SQLite. Schema string + idempotent ALTER migrations in init().
index_engine.py Pure index mechanics on top of db: allocate / mark / update / simulate.
server.py       FastAPI app, all endpoints, the daily scheduler thread, static hosting.
static/index.html  Entire frontend: one file, inline data + CSS + JS, no build step.
static/vendor/  Chart.js + webfonts, vendored so the desktop app works offline.
backend.spec    PyInstaller --onedir freeze of the backend for the desktop app.
desktop/main.js Electron shell: supervises the backend process, tray, window.
```

### The desktop layer

`desktop/main.js` holds no application logic — it supervises. Three things there are not
optional: a single-instance lock (two copies means two schedulers fetching the same day into
the same database), `taskkill /T /F` on quit (Windows does not reap a dead parent's children,
so an orphan keeps holding the port and the SQLite file), and a runtime-chosen free port
(8000 is frequently taken, including by a copy of this service started from a terminal).

**Packaging changes where paths point.** When frozen, the install directory is read-only and is
replaced wholesale on update, so nothing the user owns may live there. `config.FROZEN` gates
this: read-only bundled assets resolve from `sys._MEIPASS`, while the database, `.env`, and
backups go to a per-user directory that Electron passes in via `PORTFOLIO_DB` /
`PORTFOLIO_ENV_FILE` / `PORTFOLIO_DATA_DIR`. Running from source, every one of those paths
collapses back to the repo directory, so nothing about the old workflow changed. Electron also
sets `PYTHONIOENCODING=utf-8`, without which the backend's em-dashes and Chinese text come
back mojibake through the captured pipe.

**`ensureDatabase` behaves differently in the two modes, deliberately.** From source it copies
the repo's `portfolio.db` automatically; packaged, it cannot — the install directory has no
relationship to wherever the user kept their data — so it prompts with an import/start-fresh
dialog *before* starting the backend. Starting fresh is not a safe default for this app: with
no database and a launch after `FETCH_HOUR`, the scheduler immediately seeds a second,
discontinuous NAV series that looks entirely legitimate. An earlier version checked the repo
path in both modes and silently did nothing when packaged; this was caught only by running the
packaged build, which is why testing `win-unpacked/` and not just `npm start` matters.

**Two environment gotchas when rebuilding:**

- `electron-builder` downloads a `winCodeSign` bundle containing macOS `.dylib` symlinks, and
  extracting symlinks on Windows needs a privilege normal accounts lack — the build dies with
  "Cannot create symbolic link" even though nothing is being signed. Fix without changing
  system settings: extract the cached archive yourself, minus the macOS tree, into the
  deterministic cache path `%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\winCodeSign-2.6.0`
  (`7za x <cached>.7z -o<that path> '-xr!darwin'`). `rcedit-x64.exe` from that bundle is what
  embeds the app icon, so skipping signing wholesale would cost the icon.
- Node may not be on `PATH` in an already-running shell after install; prepend
  `/c/Program Files/nodejs`.
- **Smart App Control is ENFORCED on this machine** (`HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy`
  → `VerifiedAndReputablePolicyState = 1`). It blocks the packaged
  `Horizon Holdings.exe` outright — "An Application Control policy has blocked this file",
  logged in `Microsoft-Windows-CodeIntegrity/Operational`. This is not a build defect and
  there is nothing in the code to fix. The PyInstaller `horizon-backend.exe` is *not* blocked,
  only the rebranded Electron binary, so `npm start` (which runs Electron's own signed binary
  plus the frozen backend) remains a full test path for everything except the
  `app.isPackaged` branches. Do not attempt to disable Smart App Control — turning it off is
  irreversible without reinstalling Windows, and it is the user's decision.

### Two currencies, not one

`NUMERAIRE = "USD"` is the internal arithmetic unit, chosen because Yahoo's FX pairs
(`CHFUSD=X`) quote USD-per-unit. `BASE_CCY` (default CHF, configurable) is the *reporting*
currency the NAV is denominated in. They stopped being the same thing when BASE_CCY became
configurable — code that conflates them is a bug. Specifically: the `fx` table never contains
a row for USD; completeness checks must be written against `NUMERAIRE`, and any place needing
the base currency must additionally require `BASE_CCY`'s rate (see `need_ccy` in
`run_daily_update`). `nav_history` stores both `nav_usd` and `nav_base`/`base_ccy`.

**A seeded index cannot change denomination.** `index_engine.update` refuses to proceed if
`meta.index_base_ccy` disagrees with the configured `BASE_CCY`, and an index seeded before this
feature existed (inception set, no currency tag) is treated as USD rather than assumed safe.
The only escape is `POST /api/reset_index?confirm=true`, which clears NAV/holdings/cash but
deliberately preserves prices, FX, and user positions.

### Invariants in the daily update path

`server.run_daily_update` is the core job; each of these choices is deliberate and documented
in-place. Preserve them:

- **Raw market data is persisted before valuation.** If NAV math throws, the day's prices are
  still banked.
- **Every quote is stored under the session it actually traded in**, never stamped with
  "today". Exchanges have different holidays; re-dating stale quotes would fabricate price
  history. Consequence: a closed market produces no new row that day, and valuation uses
  `db.prices_asof(d)` (forward-fill of the latest close ≤ d) for all 78 names.
- **Missing price on a held position ⇒ no NAV row at all.** `index_engine.StaleValuationError`
  propagates to a 409. Valuing a real holding at zero silently understates NAV; a gap in a
  multi-decade series is far cheaper than a wrong number.
- **Backfill is automatic.** Each fetch pulls a ~10-day window (`FETCH_LOOKBACK`); every session
  in it without a NAV row is computed in chronological order. Sessions that can't be valued go
  into `skipped_sessions` with a reason rather than aborting the run.
- **First-ever run seeds at the newest session only**, not the oldest bar in the window — FX and
  equity series don't start on the same day, and pre-inception backfill is meaningless.

### State lives in `meta`

`meta` is a key/value table doing real work; the key names carry semantics. Notably
`last_scheduled_date` is tracked separately from `last_fetch_date` so a manual morning refresh
cannot cancel that evening's scheduled close-price run. Others: `inception_date`,
`last_rebalance_year`, `index_base_ccy`, `last_fetch_error`, `consecutive_failures`,
`last_fundamentals_quarter`.

### Ticker keys vs Yahoo symbols

The dict key in `UNIVERSE` (e.g. `SAP`, `RO.SW`) is the app's internal identity and the value
stored in every table. `yahoo` is the request symbol and may differ. Fetching is two-phase on
purpose: primaries first, and `alts` are requested only for the ones that came back empty —
requesting known-retired fallbacks daily would print a permanent false "possibly delisted"
alarm. When an internal key must change, add it to `db.TICKER_RENAMES`; `db.init()` migrates
prices, index holdings, user positions, and the edit log, handling PK collisions.

### Fundamentals are a separate, slower pipeline

P/E, dividend yield, and beta come from `yf.Ticker(sym).info` — one HTTP round-trip per symbol,
so ~78 requests, versus one batched request for all prices. Gated to once per calendar quarter
via `meta.last_fundamentals_quarter`; the scheduler checks daily but `run_fundamentals_update`
short-circuits. `?force=true` bypasses the gate.

Two hard-won rules in `fetch_fundamentals_live`: derive dividend yield from
`dividendRate / price` (same-unit division, no percent-vs-fraction ambiguity) rather than
trusting Yahoo's precomputed `dividendYield`; and **plausibility bounds are per-field** — a
rejected field falls back to the static estimate and must not carry a "live" badge, and must
not cost the other fields on the same row their badges. `pe_type` (`trailing`/`forward`/
`computed`) is stored and displayed because the two can differ by multiples.

### Frontend

`static/index.html` is a single file with no build step; `server._find_index()` also accepts a
flat `index.html` next to `server.py`, and renders a self-explaining HTML page (not an error)
when neither exists. `API` is `''` when served over HTTP and `http://127.0.0.1:8000` when opened
via `file://` (CORS regex in `server.py` permits `null`/`file://`/localhost origins only).

Two things to know before editing it:

- **`const DATA` near the top of the second `<script>` is a hand-maintained mirror of
  `universe.py`**, including the precomputed `w` weight and the *static fallback* `pe`/`dy`/
  `beta` estimates that exist nowhere else in the codebase. Changing the universe, scores, or
  weights in Python requires updating `DATA` too, or the page and API will disagree.
- Chart.js and the webfonts are vendored under `static/vendor/` and referenced **relatively**
  (`vendor/chart.umd.min.js`), so the same tag resolves whether the page is served at `/` or
  opened straight from disk. `server.py` mounts `/vendor` to make the served case work — that
  mount is not redundant with `/static`. The no-op Chart stub is still there as a safety net:
  the page is one long script block, so a single `Chart` ReferenceError would kill the tables
  and positions UI too. Keep new chart code tolerant of the stub.

## Conventions

- Comments here explain *why* a non-obvious choice was made, frequently citing a real bug that
  motivated it. When changing such code, update the reasoning rather than deleting it.
- Numeric input from the user is treated as untrusted even after it's in the DB: `/api/positions`
  re-validates stored `shares`/`avg_cost` for finiteness and sign before computing.
- Backups must go through SQLite's online backup API (`db.backup_to`, `POST /api/backup`).
  The DB runs in WAL mode, so `cp portfolio.db` while the service is running can silently drop
  committed transactions.
- Scheduler failures back off and retry within the same day and surface via
  `/api/status.last_fetch_error`; a fundamentals failure is explicitly non-fatal and must never
  block the price/NAV update.
