# Horizon Holdings

A local portfolio tracker for Windows, macOS and Linux. It follows a model index of 78
global companies across 12 markets and 7 currencies, and compares it against the positions
you actually hold.

Everything runs on your own machine. There is no account, no server, and no subscription —
your positions are stored in a single file on your disk and never leave it.

> 🇨🇳 **中文说明请见 [README.zh-CN.md](README.zh-CN.md)。**

---

## Which are you?

| | You want to **use it** | You want to **build it** |
|---|---|---|
| Go to | [Install](#install) | [Build from source](#build-from-source) |
| You need | Nothing installed | Python 3.10+, Node.js 18+ |
| Takes | About a minute | About twenty minutes |
| Download | ~110 MB installer | ~1.4 MB of source |

---

## Install

| Your OS | Status |
|---|---|
| **Windows** | Prebuilt installer on the [Releases page](https://github.com/vansdardy/horizon-holdings-app/releases) |
| **macOS** | No prebuilt package yet — [build from source](#build-from-source), about 20 minutes |
| **Linux** | No prebuilt package yet — [build from source](#build-from-source), about 20 minutes |

**Why there is no Mac or Linux download.** The backend is bundled with PyInstaller, which
**cannot cross-compile**: producing a macOS app requires running the build on a Mac, and a
Linux one on Linux. This project has only been built on Windows so far. Nothing in the code
is Windows-specific — the application runs fine on all three — so if you build it on your own
machine it will work. The usual fix for a project that wants all three is a continuous
integration service that builds on each OS, which is worth knowing about but is more
machinery than a single-user app needs.

### Windows: download and run

Download the latest `Horizon Holdings Setup <version>.exe` from the
[**Releases page**](https://github.com/vansdardy/horizon-holdings-app/releases) and run it.
It installs for the current user only, so no administrator password is required. Python is
bundled inside — you do **not** need to install it.

#### Windows will warn you, and here is why

The installer is not code-signed. A signing certificate costs money each year and does not
by itself make software safer, so this project does not have one. You will see one of two
things:

| What you see | What to do |
|---|---|
| **"Windows protected your PC"** (SmartScreen) | Click **More info** → **Run anyway** |
| **"An Application Control policy has blocked this file"** | Smart App Control is enabled. See below |

**Smart App Control** blocks unsigned programs outright rather than warning. It can only be
turned *off* permanently — Windows does not allow turning it back on without reinstalling —
so think before you disable it. If you would rather not, [build from
source](#build-from-source) instead; that path is unaffected.

### macOS: expect Gatekeeper to refuse it

If you build the app yourself on a Mac, macOS will not open it, because it is unsigned and
unnotarised. macOS is stricter than Windows here: there is no "run anyway" button in the
first dialog. Either right-click the app and choose **Open** (which offers an override the
plain double-click does not), or allow it once under **System Settings → Privacy & Security**,
where a blocked app appears with an *Open Anyway* button shortly after you try to launch it.

Signing and notarising properly requires a paid Apple Developer account. For an app you built
yourself, on your own machine, the override is the normal path.

### After installing

The app lives in your system tray. Some things worth knowing on day one:

- **Closing the window does not quit the app.** It hides to the tray so the daily price
  fetch keeps running. To quit for real: right-click the tray icon → **Quit**. The app tells
  you this the first time you close the window.
- **First launch asks about your data.** If you have used this project before, choose
  *Import* and point it at your existing `portfolio.db`. Otherwise choose *Start fresh*.
- **Prices update once a day at 18:00** local time, and only while the app is running. If
  your machine was asleep, the next fetch fills in the days it missed.
- **The app updates itself.** It checks shortly after launch and every six hours, and asks
  before downloading anything and again before installing. You can also check on demand:
  right-click the tray icon → **Check for updates…**. Updating never touches your database,
  your settings or your NAV history.

  If you are on **v1.6.1 or earlier**, that version was built before updating existed and
  cannot update itself — install once by hand from the
  [Releases page](https://github.com/vansdardy/horizon-holdings-app/releases), and it will
  keep itself current from then on.

---

## What it does

### A model index

A hypothetical portfolio of 78 companies, weighted by a confidence score, starting at
10 billion CHF split into 200 million shares — so one share is worth exactly 50.00 at
inception. Each day it re-values those holdings.

Three details make it behave like a real fund rather than a spreadsheet:

- **Whole shares only.** You cannot buy 3.7 shares of Nestlé, so allocation rounds down and
  keeps the remainder as cash, in each company's own currency.
- **Seven currencies.** Everything converts through USD internally (that is how the
  exchange-rate data arrives) and is reported in your chosen currency.
- **Rebalanced annually**, on the first trading day of each new year.

The curve starts accumulating the day you deploy it. This is not a backtest, and there is no
hindsight in it.

### Your actual positions

Enter your real share counts and average cost, and the app shows unrealised profit and loss,
your actual weight versus the model's target weight, and how many shares would close the
gap. Fractional shares are supported — the whole-share rule applies to the model index, not
to you.

> The "shares needed" figure is arithmetic, not advice. It ignores your tax situation,
> trading costs, and whether the current price is sensible. It is a comparison tool.

### One rule worth knowing

**If any company you hold has no price for a given day, the app refuses to record a value for
that day at all.** Valuing a real holding at zero would look like a genuine market move — one
missing price was measured producing a phantom 2.17% single-day loss. A gap in the record can
be repaired later; a plausible wrong number cannot, because nobody notices it.

### P/E, dividend yield and beta update quarterly, not daily

These come from a different, much slower data source (one request per company rather than one
for all 78), and they move slowly. The app fetches them once per calendar quarter. Figures
pulled live show a small dot; those without one are static estimates. Hovering tells you
which quarter a number came from, and whether a P/E is trailing or forward — those can differ
by several times for a richly valued company.

---

## Build from source

### Prerequisites

| | Windows | macOS | Linux |
|---|---|---|---|
| Python 3.10+ | [python.org](https://www.python.org/downloads/) — **tick "Add python.exe to PATH"** | `brew install python` | `sudo apt install python3 python3-venv` |
| Node.js 18+ | `winget install OpenJS.NodeJS.LTS` | `brew install node` | `sudo apt install nodejs npm` |
| Git | `winget install Git.Git` | `brew install git` | `sudo apt install git` |

> **After installing anything, open a new terminal.** A shell reads its `PATH` when it
> starts, so a window you already had open will insist the program does not exist. This is
> the single most common "the install failed" that is not an install failure.

<details>
<summary><b>Windows: read this before typing <code>python</code></b> (it will save you an hour)</summary>

Windows ships a **0-byte placeholder** for `python` and `python3` in
`%LOCALAPPDATA%\Microsoft\WindowsApps`. Running either one opens the Microsoft Store instead
of running anything. Many guides written for macOS say `python3`, which on Windows does
exactly that.

Use **`py`** instead — the Python Launcher, installed by the python.org installer into
`C:\Windows`, which always resolves ahead of the Store placeholder:

```powershell
py --version          # works
py -3.12 --version    # a specific version, if you have several
py --list             # every version installed
```

`python` may also work on your machine, but only if real Python happens to sit before
`WindowsApps` in your `PATH`. That is luck, not a guarantee, so this README uses `py`.

**`py` picks the newest version you have installed.** That is usually what you want, but a
Python released in the last few months often has no prebuilt packages yet for libraries like
pandas and numpy, so `pip install` tries to compile them from source and fails with pages of
compiler errors that look like your mistake. They are not. If that happens, pin a version
that is a year or so old:

```powershell
py -3.12 -m venv .venv
```

**Also:** this project never asks you to "activate" the virtual environment. Activation
runs a PowerShell script, and on a default Windows install that fails with *"running scripts
is disabled on this system"*. Calling the environment's Python directly avoids the problem
entirely.
</details>

### 1. Get the code

```bash
git clone https://github.com/vansdardy/horizon-holdings-app.git
cd horizon-holdings-app
```

### 2. Create the Python environment and install dependencies

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 3. Run the backend on its own

This gives you the full application as a web page, without Electron. It is the fastest way
to check everything works.

**Windows:**

```powershell
.venv\Scripts\python.exe server.py
```

**macOS / Linux:**

```bash
.venv/bin/python server.py
```

Then open <http://127.0.0.1:8000>. You should see:

```
[startup] scheduler running (daily fetch at 18:00 local)
[startup] data source: Yahoo Finance
INFO:     Uvicorn running on http://127.0.0.1:8000
```

If it says `MOCK — NOT REAL PRICES`, the environment variable `MARKETDATA_MOCK` is still set
to `1` and the numbers are fake.

**On a fresh install, verify the ticker symbols first.** Exchanges rename things, and this
catches it immediately rather than as a mysterious failure weeks later:

**Windows (PowerShell):**

```powershell
curl.exe http://127.0.0.1:8000/api/check_symbols
```

**macOS / Linux:**

```bash
curl http://127.0.0.1:8000/api/check_symbols
```

> **On Windows it must be `curl.exe`, not `curl`.** In PowerShell, `curl` is an alias for a
> different command, and `curl -X POST ...` fails with *"A parameter cannot be found that
> matches parameter name 'X'"* — an error that tells you nothing about the real cause. On
> macOS and Linux, plain `curl` is correct and already installed.

`"healthy": true` means all 78 companies and 6 exchange rates resolved. Press `Ctrl+C` to
stop the server.

### 4. Freeze the backend into a standalone executable

The desktop app runs a bundled copy of Python rather than yours, so this step produces it.

**Windows:**

```powershell
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe -m PyInstaller backend.spec --noconfirm --distpath build/backend --workpath build/pyinstaller
```

**macOS / Linux:**

```bash
.venv/bin/python -m pip install pyinstaller
.venv/bin/python -m PyInstaller backend.spec --noconfirm --distpath build/backend --workpath build/pyinstaller
```

Takes about 90 seconds and produces roughly 90 MB in `build/backend/`.

> **Re-run this after any change to the Python code.** The desktop app prefers the frozen
> copy, so if you skip it you will edit a Python file, restart, and watch the app faithfully
> run the previous version — with no error to explain why.

### 5. Run the desktop app

```bash
cd desktop
npm install
npm start
```

### 6. Build the installer

```bash
npm run dist
```

The result lands in `build/desktop-dist/`.

<details>
<summary><b>Windows only: if the build fails with "Cannot create symbolic link"</b></summary>

The packaging tool downloads a code-signing toolkit containing macOS symlinks, and creating
symlinks on Windows needs a privilege ordinary accounts lack — even though nothing here is
being signed. Extract the cached archive yourself, without the macOS part:

```powershell
$cache = "$env:LOCALAPPDATA\electron-builder\Cache\winCodeSign"
$sevenZip = ".\node_modules\7zip-bin\win\x64\7za.exe"
& $sevenZip x "$cache\<the-downloaded-file>.7z" "-o$cache\winCodeSign-2.6.0" '-xr!darwin'
```

Then run `npm run dist` again. Enabling Windows Developer Mode also fixes it permanently.
</details>

### Running the tests

**Windows:**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
node --test tests/js/*.test.js
```

**macOS / Linux:**

```bash
.venv/bin/python -m pytest tests/ -q
node --test tests/js/*.test.js
```

74 tests, about eight seconds. Use the `*.test.js` glob rather than passing the directory —
`node --test tests/js` fails under Git Bash with a confusing `Cannot find module` error,
because of how Git Bash rewrites paths.

---

## Where your data lives

The installed app keeps your database outside the program folder, because installation
directories are read-only and get replaced entirely when you update.

| OS | Location |
|---|---|
| Windows | `%APPDATA%\Horizon Holdings\` |
| macOS | `~/Library/Application Support/Horizon Holdings/` |
| Linux | `~/.config/Horizon Holdings/` |

The tray menu has **Open data folder** if you would rather not type that. Running from
source instead keeps `portfolio.db` beside the code, exactly as before.

### Importing an existing database

Tray → **Import database…**, or the button in the window next to *Save* / *Export*. It works
at any time, not only on first launch. Before replacing anything it checks the file really is
a database, backs up your current one to `portfolio-replaced-<timestamp>.db`, and restarts
the backend cleanly.

### Backing up — do not just copy the file

The database uses SQLite's write-ahead logging, which means recently committed changes may
still be sitting in a companion `-wal` file. **Copying `portfolio.db` on its own while the
app is running can silently lose them.** Use any of these instead:

1. The **Backup database** button in the app.
2. The API, while the app is running:
   ```powershell
   curl.exe -X POST http://127.0.0.1:8000/api/backup    # Windows
   ```
   ```bash
   curl -X POST http://127.0.0.1:8000/api/backup        # macOS / Linux
   ```
3. With the app fully stopped, copy all three files together:
   ```powershell
   Copy-Item portfolio.db,portfolio.db-wal,portfolio.db-shm C:\backups\ -ErrorAction SilentlyContinue
   ```
   ```bash
   cp portfolio.db portfolio.db-wal portfolio.db-shm ~/backups/ 2>/dev/null
   ```

Backups are written next to the database unless you pass `?dest=`. **Export JSON** in the app
gives you positions, NAV history, prices and exchange rates in plain text — there is no lock-in
here.

---

## Configuration

Optional. Everything has a working default. Copy the template and edit it:

```powershell
Copy-Item .env.example .env
notepad .env
```

```bash
cp .env.example .env
```

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | Port for the backend when run from source. The desktop app picks a free one automatically |
| `FETCH_HOUR` | `18` | Local hour for the daily fetch. Set it after the last market you care about closes |
| `PORTFOLIO_DB` | `./portfolio.db` | Database location |
| `FETCH_LOOKBACK` | `10d` | How far back each fetch reaches, which is what fills in missed days |
| `BASE_CCY` | `CHF` | Reporting currency: CHF, USD, EUR, GBP, CAD, JPY or DKK |
| `MARKETDATA_MOCK` | `0` | Set to `1` for fake offline data while developing |

To override a setting for one run only, without editing the file — note that the syntax is
different in every shell, which catches people copying between operating systems:

```powershell
$env:PORT="8001"; .venv\Scripts\python.exe server.py     # Windows PowerShell
```

```bash
PORT=8001 .venv/bin/python server.py                     # macOS / Linux
```

These last only as long as that terminal window. That is exactly why `.env` exists: a
program meant to run every day needs its settings in a file that survives a reboot.

Changes take effect on restart. The startup log prints each setting and where it came from,
and the app refuses to start on an invalid value rather than failing hours later.

**A running app writes settings to its data folder**, not to this file — `.env` is for running
from source.

> **Changing `BASE_CCY` after the index has started is refused**, because a value series that
> switches currency midway is two incomparable series glued together. To change it anyway:
> edit `.env`, restart, then `POST /api/reset_index?confirm=true`. Your positions and price
> history are kept.

---

## How it works

Four layers: a SQLite file, Python logic, an HTTP API, and an HTML page — with Electron
supervising the whole thing and putting a window around it. The page talks to the backend over
`127.0.0.1` exactly as a browser would, which is why the same code runs as both a website and
an installed program.

**`docs/building-this-app.html`** explains the entire build in 16 parts: the architecture and
why it is shaped this way, packaging, testing, refactoring, version control, publishing
releases, adapting the approach to a different language or a different kind of app, and what
to do when you get stuck. It is written for someone in their first year of programming.

Three ways to read it, because GitHub displays `.html` files as raw source rather than
rendering them:

- **Inside the app** — tray → *How this app was built*. Works offline.
- **From source** — run the backend and open <http://127.0.0.1:8000/guide>.
- **As a file** — download `docs/building-this-app.html` and open it in any browser. It is
  entirely self-contained, fonts included.

---

## API

Interactive documentation at <http://127.0.0.1:8000/docs> while the backend is running.

| Endpoint | Purpose |
|---|---|
| `GET /api/status` | Data source, last fetch, scheduler state, errors |
| `GET /api/check_symbols` | Probe all 78 tickers and 6 currency pairs — run this first |
| `POST /api/refresh` | Fetch now. `?window=N` to reach further back |
| `GET /api/nav` | Value history and statistics |
| `GET /api/universe` | The 78 companies and their target weights |
| `GET /api/positions` | Your positions with prices, drift and gap-to-target |
| `POST /api/positions` | Save positions |
| `POST /api/cash` | Save cash balances per currency |
| `GET /api/prices` | Latest prices and exchange rates |
| `GET /api/archive` | Price archive statistics |
| `GET /api/fundamentals` | P/E, dividend yield, beta from the last quarterly fetch |
| `POST /api/refresh_fundamentals` | Fetch fundamentals; `?force=true` ignores the quarterly gate |
| `GET /api/price_history` | Price series, filterable by ticker and date |
| `GET /api/price_history.csv` | The whole archive as CSV |
| `GET /api/nav/simulate` | Re-run the index from a different start date, without saving |
| `POST /api/reset_index` | Clear the value series and re-seed; needs `?confirm=true` |
| `POST /api/backup` | Consistent database snapshot |
| `GET /api/export` | Everything, as JSON |
| `GET /guide` | The build documentation |

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `python3` opens the Microsoft Store | Windows placeholder, not Python. Use `py` |
| `curl: A parameter cannot be found` | PowerShell aliases `curl`. Use `curl.exe` |
| `running scripts is disabled on this system` | Execution policy blocks venv activation. Call `.venv\Scripts\python.exe` directly instead |
| `npm` or `node` not recognised after installing | Your terminal predates the install. Open a new one |
| `Cannot find module ...tests\js` | Pass the glob: `node --test tests/js/*.test.js` |
| Edited Python, app runs the old code | Re-freeze the backend (step 4). The app prefers the frozen copy |
| Page says backend not connected | Backend not running, or the port is taken. Change `PORT` — see Configuration for the syntax your shell needs |
| macOS refuses to open the app | Unsigned build. Right-click → **Open**, or allow it in System Settings → Privacy & Security |
| Red MOCK banner | `MARKETDATA_MOCK=1` is set. Remove it and restart |
| Fetch returns 409 | A company you hold has no price today; the day was deliberately not recorded. The message names which |
| Fetch returns 500 | Network or data-source problem. See `last_fetch_error` in `/api/status` |
| Value chart has only one point | Normal. The series accumulates from the day you start |
| Gap in the value series | The app was off for longer than `FETCH_LOOKBACK`. Increase it and fetch again |
| `possibly delisted; no price data found` | A ticker returned nothing. If `daily update done` follows, the fetch still succeeded. Run `/api/check_symbols` |
| `this index was seeded in X but BASE_CCY is now Y` | See the note under Configuration |
| Installer blocked entirely | Smart App Control. See [Install](#install) |

---

## Data source

Yahoo Finance, through the `yfinance` library — free, no API key. One batched request fetches
all 78 companies and 6 exchange rates.

A few symbol details worth knowing if you edit `universe.py`: Berkshire is `BRK-B`, not
`BRK.B`. ASML is used as `ASML.AS` in euros, not the dollar-denominated Nasdaq listing — mixing
them would corrupt the currency handling. Arm is a British company trading in dollars on
Nasdaq, and is treated as USD.

Every quote is stored under the trading session it actually belongs to, never stamped with
today's date. Exchanges close on different days, and re-dating a stale quote would invent
price history that never happened.

---

## License

MIT — see [LICENSE](LICENSE). Use it, change it, sell it; keep the copyright notice.

**MIT does not cover the components bundled inside**, which keep their own licences and place
their own conditions on redistribution:

| Component | Licence | Requires |
|---|---|---|
| Chart.js | MIT | Keep the copyright notice |
| Source Serif 4, Inter, IBM Plex Mono | SIL OFL 1.1 | Licence text must travel with the fonts; they may not be sold alone |
| Python, Electron, and dependencies | PSF / MIT / BSD / Apache 2.0 | Bundled into the installer, not this repository |

Full detail in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

---

## Disclaimer

This is a personal record-keeping and comparison tool. **It is not investment advice.** Price
data comes from a free third-party source with no guarantee of accuracy or timeliness, and
should not be relied on for trading decisions. The model index is hypothetical and is not a
fund you can buy. Investing carries risk, including loss of principal. Verify the data and
consult a licensed adviser before making decisions.
