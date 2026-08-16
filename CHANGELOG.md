# Changelog

Versions follow [semantic versioning](https://semver.org): `MAJOR.MINOR.PATCH`.
MAJOR means something that used to work now behaves differently, MINOR means new
capability with nothing existing changed, PATCH means a fix only.

Installers are on the [Releases page](https://github.com/vansdardy/horizon-holdings-app/releases).
They are unsigned — see the README for what Windows will show you.

---

## v1.10.2

**Added**

- **A note above the cash table explaining the oversized pound pool**, on any
  database that was migrated out of pence. The pool is real money and the NAV
  counts it correctly — but it is roughly ninety times what buying whole shares
  should leave, because until v1.10.1 the index rounded down in steps a hundred
  times too coarse, and that remainder is still sitting in cash rather than in
  shares. On the real database: 14,143 GBP against the ~156 a correct allocation
  would have left, a drag of 0.00015% of the fund.

  **It takes itself down.** The notice is not a date or a hardcoded string: the
  migration raises a flag, and `index_engine` lowers it the moment a rebalance
  happens — which is exactly when the pool is reinvested, since a rebalance
  reallocates the entire NAV, cash included. Verified end to end against a copy
  of the real database: after simulating the January rebalance the GBP pool
  falls from 14,143 to 126.80, the notice disappears, and NAV moves by
  0.000000 USD.

  A clean database never shows it, so nobody who was not affected sees a warning
  about a bug that never touched them.

**Fixed**

- `db.set_meta` opened its own connection, which deadlocks if called from inside
  an open write transaction. Callers already holding a cursor now use
  `_set_meta(c, …)`; the public function is unchanged.

---

## v1.10.1

**Fixed**

- **London prices were being stored in pence and labelled as pounds.** The LSE
  quotes ordinary shares in GBX — 100 pence to the pound — and Yahoo passes that
  straight through, so AstraZeneca arrived as `11708` and was recorded as
  £11,708 rather than £117.08. Nothing in the response says which unit it is in:
  the batched download returns bare numbers, and the currency genuinely *is*
  GBP. Eight constituents were affected.

  **The NAV was not wrong.** That is worth stating plainly, because it is the
  first thing anyone assumes. The same inflated price decided how many shares to
  buy *and* valued them afterwards, so the error cancelled exactly — measured on
  the real database, UK holdings came to 8.6641% of the fund against a target of
  8.6643%. That is also precisely why the bug could sit there looking healthy.

  What it did corrupt is every figure that depends on the price alone:

  - **Share counts a hundred times too small** — the index held 11,192 shares of
    AstraZeneca where it should have held 1,119,200. Those counts became visible
    for the first time in v1.10.0's holdings table.
  - **The market value of any UK position you entered yourself would have come
    out a hundred times too large**, since your real share count would have been
    multiplied by a pence price treated as pounds. Nothing had been entered yet,
    so no position data was affected.
  - Shares-to-target for UK names, and a GBP cash pool inflated by rounding a
    hundred times more coarsely than the others.

  Prices are now converted at the moment they arrive, and existing databases are
  migrated once at startup: prices ÷ 100 and share counts × 100 together, so the
  market value — and therefore every NAV point ever recorded — does not move by
  a penny. Verified against the real database: the difference is exactly
  0.000000000. A copy is written to `portfolio-before-gbx-<timestamp>.db` first,
  because the rewrite has no undo.

  If you keep UK positions in the app, note that prices are now in **pounds**,
  so a cost basis entered in pence should be divided by 100.

---

## v1.10.0

**Added**

- **The index's actual book, under the NAV chart.** Every constituent with the
  number of shares the index holds, its price, market value and weight against
  target — plus the cash left over in each of the seven currencies. The index
  buys whole shares only, so every position leaves a remainder that stays as
  cash in the currency it was left in, and holdings plus that cash, marked at
  the latest close, *is* the NAV.

  The point is that the number can now be checked rather than trusted. A new
  `/api/index_holdings` endpoint publishes the ledger, valued through the same
  code path as the NAV series itself — the same forward-filled prices, the same
  FX, the same USD numeraire — because a second, subtly different valuation
  would produce figures that almost agree, which is worse than showing nothing.

  Four tests hold it to that: securities plus cash equals the published NAV to
  within floating-point noise, the ledger is marked on the NAV's own date, every
  holding is a whole number of shares with a non-negative cash remainder, and
  the weights plus cash account for the whole fund. Measured against the real
  series, the two agree to about 1 part in 10^16.

- **The ticker tape stops while you read it.** Hovering pauses it; so does
  focusing it, since the tape is now reachable by keyboard and someone who
  cannot use a mouse could not stop it at all before.

---

## v1.9.2

**Fixed**

- **The build guide wasted most of a maximised window, and had been shrinking
  its own diagrams.** The stylesheet said figures, tables and code blocks should
  break out of the prose column to the full width. They never did. The selectors
  were written `.flow > figure`, but a figure lives inside
  `<section class="part">`, not directly in `.flow` — and the rule above capped
  `.flow > *`, the sections themselves, at the reading measure, so nothing
  inside one could have been wider even had the selector matched.

  Nothing about that fails visibly; the page just looks deliberate and the
  diagrams look small. Every diagram in the guide is drawn at 900px and was
  being displayed at 578 — a third of the detail thrown away — and the wide
  comparison tables were folded into a column meant for prose.

  Diagrams, tables and code now use the full column: 1140px on a wide screen,
  835px in the app's own guide window, up from 578 everywhere.

**Changed**

- **On screens wider than 1500px the asides move into the margin** beside the
  text they annotate, rather than interrupting the argument to sit in the middle
  of it. They were already the "did you know" boxes — *The thing that will
  confuse you first*, *What you do not need yet* — so the empty space is filled
  with the writing that most wants to be there, not with filler.

  Body text stays at 66 characters per line at every width. That is the measure
  a reader can actually follow, and widening it to fill a monitor would make the
  page worse, not more balanced.

---

## v1.9.1

**Fixed**

- **"Start at login" never showed a tick, whether it was on or off.** It is a
  checkbox menu item and always was; what was broken is the state it read back.

  Windows stores autostart as a command line in the registry, and Electron wrote
  this app's entry *unquoted*:

  ```
  T:\Software\Horizon\Horizon Holdings\Horizon Holdings.exe --hidden
  ```

  The installation path contains spaces, so when Electron read the key back it
  could not tell where the executable name ended. `getLoginItemSettings()`
  returned `launchItems: []` — it did not see the entry at all — and so reported
  the setting as off for an entry sitting in the registry working. Clicking the
  item toggled the real setting correctly every time; only the tick was wrong,
  which is the one part a user can see.

  Autostart is now read and written directly on Windows, with the path properly
  quoted. Writing it also repairs the unquoted entry left behind, since an
  unquoted path with spaces leaves Windows guessing where the program name ends.
  macOS and Linux keep Electron's API, which works correctly there.

  Any application whose install path contains a space hits this, which on
  Windows is most of them.

---

## v1.9.0

**Added**

- **The installer asks before putting an icon on your desktop.** A checkbox on
  a new page after the install location, ticked by default because that is what
  Windows installers do, but yours to untick.

  The awkward part is not the checkbox. An *update* runs the same installer
  silently, with no user and no dialogs, so a naive version would read an
  unticked box on every update and delete the desktop icon of someone who wanted
  one — or put one back, every release, on the desktop of someone who did not.
  The answer is recorded when a human gives it and replayed on silent installs.
  Uninstalling deliberately leaves that one registry value behind, because an
  update runs the old uninstaller before the new install, and erasing the answer
  there would lose it moments before it is needed.

**Fixed**

- **The repository could not build its own installer.** `.gitignore` said
  `build/`, which matches a directory of that name at *any* depth, so it had
  been silently excluding `desktop/build/` — electron-builder's build resources
  directory, holding the application icon and now the installer script. Those
  are source, not output. Everything existed on the author's machine, so nothing
  ever looked wrong; a fresh clone of this public repository simply could not
  produce an installer, and had no app icon. The rule is now anchored to the
  repository root (`/build/`), the resources are committed, and a test asserts
  they are tracked. Exactly the same failure as `preload.js` missing from the
  packaged files list in v1.3.0: works here, absent for everyone else, silent
  either way.
- **Company names in "My Positions" stayed in Chinese in the English
  interface.** The API had been returning both names since v1.6.0; the table
  simply rendered the Chinese one. Searching now matches either name whatever
  the interface language, since someone reading the English page may still know
  a company by its Chinese name.

---

## v1.8.0

The first release that existing installs can take automatically — v1.7.0 added
the updater, and this is the version it will offer.

**Added**

- **A menu bar: File, View and Help.** Everything the app could do lived in the
  tray icon, which is the same mistake as putting "Import database" only there:
  nobody right-clicks a tray icon to answer "what version is this?". The menu
  carries the same commands, plus **Help → About**, which is where that question
  has been answered by convention for forty years. Check for updates is in Help,
  and reports its own progress in both places at once.
- **The version is in the window**, in the masthead beside the guide link. It
  was technically there before — 10.5px, grey, in a row of controls far down the
  page — which the person looking for it correctly reported as not being there.

**Changed**

- **The page uses the window.** The content was capped at 1240px, chosen when
  this was a web page, where a narrow measure is a virtue. In a 1500px
  application window it left 130px of empty background down each side while the
  positions table crushed thirteen columns into what was left.
- **The positions table gives its space to the things that need it.** Table
  headings are nowrap throughout the page, which is right for short ones but
  meant "Shares to target" and "Actual weight" each reserved a full line of
  width — 133px and 113px — for columns showing six characters. That width came
  out of Company (101px) and Region (96px), which wrapped to several lines and
  pushed every row to 114px tall. Numeric headings now wrap onto two lines, the
  numeric columns are held to a fixed width, and Region no longer breaks across
  lines. Company went from 101px to 344px and rows from 114px to 58px.

**Fixed**

- **The positions table still showed Chinese exchange names in English.** The
  same bug fixed in v1.7.0 for the constituents table, in a second place that
  was missed — and the test written for it only checked the first table, so it
  passed. Both tables now go through the language helper, and the test checks
  both.
- The guide shipped inside v1.7.0 still announced "v1.6.0" in its masthead and
  colophon. Now checked by a test against `desktop/package.json`, along with the
  changelog having an entry for the version being released.

---

## v1.7.0

**Added**

- **The app updates itself.** It checks for a new version fifteen seconds after
  launch and every six hours after that, and offers the update rather than
  taking it: nothing is downloaded until you say yes, and nothing is installed
  until you say yes again. A check that finds nothing is silent unless you
  asked for it from the tray. Until now the only way to get a fix was to
  uninstall, find the Releases page, and download 116 MB by hand — four steps
  and a decision, for a fix you had not heard about.

  The backend is stopped and *waited for* before the installer runs. It lives
  inside the directory the installer replaces, and on Windows a running process
  holds its own executable open, so "asked it to stop" is not "it has stopped".

  Your database, settings and NAV history are untouched by an update — they
  live in the per-user data directory, never in the install directory. That
  separation is why replacing the install directory wholesale is safe.

- The tray's update entry reports its own state — checking, downloading with a
  percentage, or ready to install — instead of being a menu item that gives no
  sign anything happened.

**Fixed**

- **Sector and country names stayed in English after switching to Chinese.**
  Both charts were built once, at the top level of the script, so there was no
  function to call to relabel them. They are now built inside functions the
  language switch calls, like every other render on the page. The sector drift
  chart at the bottom had the same symptom for a different reason — it lived in
  a function, but the switch never called it.
- **Exchange names ignored the language entirely.** The table printed the
  Chinese name whatever the language, and the filter dropdown fell back to the
  raw key — which is a code like `SIX`, not a name. Every exchange now has a
  real name in both languages, and the notes beside them too.
- **The same names rendered in two different fonts.** The sector chart asked for
  Inter at 11px, the country chart for Inter at 12px, and the drift chart asked
  for nothing at all, so it inherited the monospace default — the same eleven
  sector names in two typefaces on one page, in English as much as in Chinese.
  There is now one font for every category name in a chart, with Chinese
  fallbacks named explicitly rather than left to the browser.

**Documentation**

- Part 13, updating what you shipped: why almost every small project stops at
  the first release, the five steps every self-updater performs in every
  language, the metadata file people forget to upload and the silent "you are
  up to date" that follows, the defaults worth refusing, the fact that the first
  version with an updater cannot deliver itself, an honest section on updaters
  as a remote code execution channel and what going unsigned costs, how to test
  a feature that needs two versions and a network, and where to start in Java,
  .NET, Go, macOS and Linux. Parts 13–17 renumbered to 14–18.

**Note for existing users**

Copies at v1.6.1 and earlier were built before the updater existed and cannot
update themselves. Install this version by hand once; from then on it will
offer updates on its own.

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
