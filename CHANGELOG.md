# Changelog

Versions follow [semantic versioning](https://semver.org): `MAJOR.MINOR.PATCH`.
MAJOR means something that used to work now behaves differently, MINOR means new
capability with nothing existing changed, PATCH means a fix only.

Installers are on the [Releases page](https://github.com/vansdardy/horizon-holdings-app/releases).
They are unsigned — see the README for what Windows will show you.

---

## v1.6.1

Three bugs found by running the installed app, none of which the test suite
could have seen. All three shipped in v1.6.0.

**Fixed**

- **The NAV chart never appeared.** A careless rename turned `st.base_ccy` into
  `stot.base_ccy` inside `renderNav()`. That function is wrapped in a try/catch
  which hides the panel on failure — a deliberate choice, so one bad section
  cannot take the page down with it — so the entire chart and its six KPIs
  vanished silently, with nothing logged and no error on screen. A guard that
  degrades quietly also hides the bug it degrades around.
- **Switching language reset the status bar to "Connecting…" for good.** The
  element carried `data-i18n="status.connecting"` so its first paint would read
  correctly before any request finished. Once live status replaced it the
  attribute stayed, and `applyI18n()` re-applies every `data-i18n` on the page
  at each language switch — so a working status bar reverted to "Connecting…"
  and nothing ever put it back. The app looked like it had lost its backend.
  Status is now written through `setStatusLine()`, which drops the attribute,
  and `setLang()` re-runs `loadStatus()` so the text still follows the language.
- **Switching language added a tray icon each time.** `Tray` is a live shell
  icon, not a value: constructing another adds a second icon and the first stays
  put, because the shell owns it and dropping the JavaScript reference changes
  nothing. The language handler called `buildTray()` to pick up the translated
  menu, so English → Chinese → English left three icons, two stale and labelled
  in the wrong language. The handler now re-labels the existing tray.
- The window's language is announced to the shell at startup, not only when the
  switch is clicked. Relaunching after choosing Chinese came back as a Chinese
  window with an English tray menu.

**Added**

- Eight tests over the two files that had none, because neither is reachable
  from a unit test: the page is one inline script with no build step, and the
  Electron main process cannot be imported outside Electron.
  - A miniature no-undef check that scans the page's script for identifiers it
    never declares. This is the one that would have caught `stot` — and it does:
    reintroducing the typo fails it by name.
  - A rule that no element is both `data-i18n` translated and written by script,
    which is the general form of the status-bar bug.
  - Structural checks that a `Tray` is constructed in exactly one place and that
    the language handler re-labels rather than rebuilds. These read source text
    rather than run it; weak evidence of correctness, strong evidence of intent,
    and they carry the reason with them.
- `desktop.log` records when a tray icon is created. Duplicate icons are only
  visible by eye, so the log is the one place the invariant can be checked.

---

## v1.6.0

**Changed**

- **The application interface is now English by default**, with a switch in
  the header for Chinese. It was Chinese-only, which sat oddly beside a build
  guide written in English.

**Added**

- All 78 companies now carry English names, industries and moat notes
  (`universe_en.py`), served by the API alongside the Chinese originals. The
  page's copy of that data is regenerated from `universe.py` by script rather
  than by hand, so the two cannot drift apart.
- `static/lib/i18n.js`: 177 interface strings in both languages, with a
  fallback that shows the key rather than a blank when one is missing.
- The tray menu and notifications follow the same setting. The first-run
  database prompts stay bilingual on purpose — they appear before anyone has
  expressed a preference, and getting that dialog wrong loses data.
- Ten tests for the dictionary: identical keys in both languages, no English
  string left containing Chinese, matching placeholders, and locale resolution.
  A translation fails as one label in a panel nobody looked at, in a language
  the author does not read; those checks are mechanical for that reason.

**Documentation**

- Part 15, reading the source: how to approach an unfamiliar codebase, a
  reading order for this one, and nine experiments that each make one idea
  from the guide concrete — including deliberately breaking the missing-price
  rule to see the plausible wrong number it exists to prevent.

---

## v1.5.1

No functional change. Part 14 of the guide was written with one specific
future project in mind and had over-fitted to it — two of its sections were
effectively a tutorial for that one app rather than a method anyone could
apply. Corrected:

- The "what does your app need" table now compares four sketch application
  types (tracker, editor, instrument, batch tool) instead of one, and asks the
  reader to write their own column. Only one row is true for all four, which
  makes the point better than any single example could.
- The section on domain invariants is now general — what a property is, why it
  catches cases examples never will, a table across seven domains, and the
  name (property-based testing) plus libraries to look up. The worked example
  is this project's own conservation-of-money test rather than borrowed from
  elsewhere.
- The packaged-resource trap keeps its Java illustration but now names the
  .NET, Go and Node equivalents, plus the search terms to find your own.

---

## v1.5.0

**Added**

- **Closing the window now says so.** Closing hides the app to the tray so the
  daily 18:00 fetch keeps running — which is deliberate, but an app that
  ignores the close button without explaining looks either broken or closed.
  A notification now appears the first time, and the tray tooltip carries the
  standing reminder. First time only: a message that always appears is a
  message nobody reads.
- Settings persist in `settings.json`, written via a temporary file and an
  atomic rename so a crash mid-write cannot leave an unparseable file.
- `AppUserModelId` is set explicitly, without which Windows may attribute
  notifications to "electron.app" or not show them at all.

**Documentation**

- Part 14, building something else: which parts of this architecture are
  specific to one library constraint and should not be copied, a toolchain
  translation table for Java and Node, JSON-versus-database trade-offs with
  the atomic-write pattern, and a worked comparison against an Enigma machine
  — including the two properties that make it unusually testable.
- Part 15, when you get stuck: diagnosing which kind of stuck you are in,
  reading a stack trace from the correct end, halving the problem, searching
  effectively, and asking a good question.

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
