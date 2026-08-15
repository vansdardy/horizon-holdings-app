# Changelog

Versions follow [semantic versioning](https://semver.org): `MAJOR.MINOR.PATCH`.
MAJOR means something that used to work now behaves differently, MINOR means new
capability with nothing existing changed, PATCH means a fix only.

Installers are on the [Releases page](https://github.com/vansdardy/horizon-holdings-app/releases).
They are unsigned — see the README for what Windows will show you.

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
