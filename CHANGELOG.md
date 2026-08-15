# Changelog

Versions follow [semantic versioning](https://semver.org): `MAJOR.MINOR.PATCH`.
MAJOR means something that used to work now behaves differently, MINOR means new
capability with nothing existing changed, PATCH means a fix only.

Installers are on the [Releases page](https://github.com/vansdardy/horizon-holdings-app/releases).
They are unsigned — see the README for what Windows will show you.

---

## v1.4.0

A review-and-consolidate release. No new user-facing capability; the point was
to make the next change safe rather than to add another one.

**Added**

- **A test suite.** 52 backend tests (pytest) and 22 frontend tests (Node's
  built-in runner, no dependencies). The most valuable one deliberately
  reproduces a broken situation: seed the index, remove the price of a held
  position, and assert the day is *refused* rather than written.
- `static/lib/portfolio-lib.js` — the page's currency, formatting and timeframe
  logic, extracted so it can run outside a browser.

**Fixed**

- **First-run import accepted any file.** The tray import validated that the
  chosen file was really a SQLite database; the first-run path never did, so
  selecting a PDF copied it over `portfolio.db` and the app then failed to
  start, with an error several steps from the mistake. Both paths now share one
  `pickDatabaseFile()`.

**Changed**

- Frontend logic that read hidden page variables now takes its inputs as
  parameters. The page keeps one-line adapters, so no call site changed — the
  functions became testable and easier to read at the same time.

**Documentation**

- Part 09, knowing it works: what a test is for, three layers with this
  project's real proportions, and a section on frontend testing specifically —
  including why "hard to test" is a fact about the code, not about testing.
- Part 10, keeping it changeable: why refactoring has to be continuous, the
  habits that make it cheap, and an argument that design principles are
  diagnostics to reach for when something hurts, not a syllabus to master
  before writing anything.

---

## v1.3.0

**Added**

- **"Import database…" button in the window itself**, next to Save / Export /
  Backup. It already existed in the tray menu, which turned out to be the same
  as not existing: the person who asked for the feature went looking for it in
  the app, did not find it, and assumed it had never been built.

  A page cannot open a native file dialog or restart a process, so this needed
  a preload bridge (`desktop/preload.js`) exposing exactly two named functions
  over `contextBridge` — never `ipcRenderer` itself. The button is hidden when
  `window.desktop` is undefined, which is also how the page detects it is
  running in the desktop app rather than a browser.
- The app version now appears in the window, not only the tray.

**Fixed**

- `preload.js` was missing from electron-builder's `files` list. It would have
  worked in development and silently vanished from the installed app, taking
  the new button with it and reporting nothing.

---

## v1.2.1

No functional change. The build guide ships inside the application, so
improving it changes the product and earns a release.

**Documentation**

- How `.gitignore` actually works: pattern rules, and the rule that catches
  everyone — ignoring a file that is already tracked does nothing, because
  `.gitignore` only applies to files git is not already following.
- Committed secrets: why "nobody reads my repository" is not protection, and
  the recovery order that most people get backwards. Rotate the credential
  first; rewriting history is tidying up afterwards, not the fix.
- Installing the GitHub CLI on Windows, macOS, and Linux, plus the `PATH`
  staleness that makes a freshly installed tool appear missing.
- HTTPS versus SSH: what each proves, what each costs, and when to switch.
- Licensing: what "no licence" actually means, the three families, and the
  one question that picks between them.

**Legal**

- Added `LICENSE` (MIT).
- Added `THIRD-PARTY-NOTICES.md`. The bundled fonts are under the SIL Open
  Font Licence, which requires the licence text to be distributed with them —
  an obligation this project had not been meeting.

---

## v1.2.0

**Added**

- **Import a database at any time**, from the tray menu. Previously the only
  chance to bring existing data in was the first-run prompt, so anyone who chose
  "start fresh", changed machines, or wanted to restore a backup had to quit,
  delete a file inside an AppData folder by hand, and relaunch.

  The flow is deliberately conservative, because it replaces live data: it
  rejects any file whose header is not `SQLite format 3` *before* touching the
  original, backs the current database up to `portfolio-replaced-<timestamp>.db`,
  stops the backend and waits for the process to actually exit (Windows keeps the
  file handle open past the kill), clears `-wal`/`-shm` sidecars belonging to the
  replaced database, then restarts and reloads the window.

**Documentation**

- The build guide gained three parts: keeping track of changes (how the need for
  version control emerges from a project that lacks it), getting software to
  other people (the developer/user split, tags, releases), and an honest account
  of building this with an AI assistant — including the three bugs it wrote that
  reached a built artifact.
- README now splits its first screen by audience: users go to Releases and need
  nothing installed; developers get clone-and-build instructions.
- This project is now under version control, which it was not for its first two
  releases.

---

## v1.1.0

**Added**

- The build guide ships inside the application, served at `/guide` and opening in
  its own window from the tray or the page header. Works with no network.
- Overlay-style scrollbar: invisible at rest, fading in only while scrolling, so
  the window stops reading as a web page in a frame.
- Version number shown in the tray.

**Changed**

- The tray's single ambiguous "Fetch now" became two named actions, because the
  app has two independent pipelines on different schedules: daily prices and NAV,
  and quarterly fundamentals. Both now report what they did rather than
  succeeding or failing silently.

**Fixed**

- First-run database import silently did nothing in the packaged app, because the
  path it searched resolved inside the installation directory rather than the
  project folder. Combined with a launch after the daily fetch hour, this seeded
  a second, discontinuous NAV series that looked entirely legitimate.
- Dismissing the first-run prompt with Escape or the window close button selected
  "start fresh" — the destructive option. Cancelling now quits and changes
  nothing.

---

## v1.0.0

First packaged release. Electron shell supervising a PyInstaller-frozen FastAPI
backend: runtime port selection, readiness polling, tray with minimize-to-tray so
the daily scheduler survives closing the window, single-instance lock, and
process teardown that does not orphan the backend.
