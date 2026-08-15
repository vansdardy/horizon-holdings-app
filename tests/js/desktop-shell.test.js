/**
 * Structural checks on desktop/main.js.
 *
 * Honest about what these are: they read source text rather than run it. The
 * Electron main process cannot be imported here — it calls app.whenReady() at
 * load and needs a real Electron runtime — and the thing that broke is a
 * lifecycle mistake that only shows up as pixels in the notification area,
 * which no unit test was ever going to observe.
 *
 * So these pin the invariant in the place where it was actually violated. A
 * test that reads source is weak evidence of correctness but strong evidence of
 * intent: it fails loudly if someone reintroduces the exact shape of the bug,
 * and it carries the reason with it. That is worth more than no test at all for
 * a file this hard to exercise.
 */

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..', '..');
const MAIN = fs.readFileSync(path.join(ROOT, 'desktop', 'main.js'), 'utf8');
const PKG = JSON.parse(fs.readFileSync(path.join(ROOT, 'desktop', 'package.json'), 'utf8'));

/**
 * main.js with comments removed, so a mention in prose is not a call — these
 * comments name buildTray() precisely to warn people off it.
 *
 * Note `[^\r\n]*` rather than `.*$`: this repository is checked out with CRLF
 * endings, and JavaScript's `.` does not match `\r`, so the anchored version
 * matched nothing at all and silently stripped no comments.
 */
const CODE = MAIN
  .replace(/\/\*[\s\S]*?\*\//g, ' ')
  .replace(/(^|[^:'"`])\/\/[^\r\n]*/g, '$1');

// ---------------------------------------------------------------------------
// The tray is constructed exactly once.
//
// The bug: switching the interface language called buildTray() again to pick up
// the translated menu. A Tray is a live shell icon, not a value — constructing
// another adds a second icon and the first stays put, because the shell owns it
// and dropping the JavaScript reference changes nothing. Switching English →
// Chinese → English left three icons in the notification area, two of them
// stale. Re-labelling is what that path wanted.
// ---------------------------------------------------------------------------

test('a Tray is constructed in exactly one place', () => {
  const constructions = CODE.match(/new Tray\s*\(/g) || [];
  assert.strictEqual(
    constructions.length, 1,
    `found ${constructions.length} "new Tray(" calls in desktop/main.js. ` +
    'Every call adds another icon to the notification area; the old one does ' +
    'not go away on its own. Re-label the existing tray instead.');
});

test('buildTray destroys an existing tray before making another', () => {
  const fn = /function buildTray\([\s\S]*?\n}/.exec(CODE);
  assert.ok(fn, 'buildTray() not found in desktop/main.js');

  const destroyAt = fn[0].indexOf('tray.destroy()');
  const createAt = fn[0].indexOf('new Tray(');
  assert.ok(destroyAt !== -1,
    'buildTray must destroy any existing tray first, or calling it twice ' +
    'leaves an orphaned icon behind.');
  assert.ok(destroyAt < createAt,
    'the destroy must come before the construction, not after.');
});

test('the language handler re-labels the tray instead of rebuilding it', () => {
  const handler = /ipcMain\.handle\('app:setLanguage'[\s\S]*?\n {4}\}\);/.exec(CODE);
  assert.ok(handler, "the 'app:setLanguage' handler was not found");

  assert.doesNotMatch(
    handler[0], /buildTray\s*\(/,
    'the language handler must not call buildTray() — that is what put three ' +
    'icons in the tray. Call refreshTray() to re-label the existing one.');
  assert.match(
    handler[0], /refreshTray\s*\(\s*\)/,
    'the language handler must re-label the tray, or the menu keeps the old ' +
    'language while the window shows the new one.');
});

// ---------------------------------------------------------------------------
// Everything in desktop/ that the app loads is packaged.
//
// preload.js was once missing from this list. It worked in development and
// silently vanished from the installed app, taking the import button with it
// and reporting nothing.
// ---------------------------------------------------------------------------

test('every file desktop/main.js loads is in the packaged files list', () => {
  const files = PKG.build.files;
  for (const required of ['main.js', 'preload.js', 'package.json']) {
    assert.ok(
      files.includes(required),
      `"${required}" is missing from desktop/package.json build.files. It ` +
      'will work with npm start and be absent from the installed app.');
  }
});
