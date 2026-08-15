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
    'icons in the tray. Call refreshUi() to re-label the existing one.');
  assert.match(
    handler[0], /refreshUi\s*\(\s*\)/,
    'the language handler must refresh the chrome, or the tray and menu bar ' +
    'keep the old language while the window shows the new one.');

  // refreshUi is the indirection that keeps the tray and the menu bar in step;
  // it must actually re-label the tray rather than only rebuilding the menu.
  const refresh = /function refreshUi\(\)[\s\S]*?\n}/.exec(CODE);
  assert.ok(refresh, 'refreshUi() not found');
  assert.match(refresh[0], /refreshTray\s*\(\s*\)/, 'refreshUi must re-label the tray');
  assert.match(refresh[0], /buildAppMenu\s*\(/, 'refreshUi must rebuild the menu bar');
});

test('the menu bar carries the commands people look for there', () => {
  const fn = /function buildAppMenu\(userData\)[\s\S]*?\n}/.exec(CODE);
  assert.ok(fn, 'buildAppMenu() not found');

  // About answers "what version is this?", which is the question that exposed
  // the tray-only design in the first place.
  for (const [what, re] of [
    ['an About entry', /showAbout\(/],
    ['a check-for-updates entry', /checkForUpdates\(true\)/],
    ['the guide', /openGuide/],
    ['database import', /importDatabaseNow\(/],
  ]) {
    assert.match(fn[0], re, `the menu bar is missing ${what}`);
  }

  assert.match(
    CODE, /mainWindow\.setMenuBarVisibility\(true\)/,
    'the menu bar must be visible, or building it changes nothing on screen.');
});

// ---------------------------------------------------------------------------
// Everything in desktop/ that the app loads is packaged.
//
// preload.js was once missing from this list. It worked in development and
// silently vanished from the installed app, taking the import button with it
// and reporting nothing.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Updates.
//
// The updater cannot be exercised here at all — it needs an installed build, a
// published release and a network. What can be pinned are the decisions that
// are easy to undo by accident and expensive to get wrong.
// ---------------------------------------------------------------------------

test('updates are never downloaded without asking', () => {
  assert.match(
    CODE, /autoUpdater\.autoDownload\s*=\s*false/,
    'autoDownload must stay off. It defaults to true, which would pull a ' +
    '100 MB installer the moment the app opens, on whatever connection the ' +
    'user is on.');
});

test('the backend is stopped and waited for before the installer runs', () => {
  const fn = /async function installUpdateNow\(\)[\s\S]*?\n}/.exec(CODE);
  assert.ok(fn, 'installUpdateNow() not found');

  const stopAt = fn[0].indexOf('await stopBackendAndWait()');
  const installAt = fn[0].indexOf('quitAndInstall()');
  assert.ok(stopAt !== -1,
    'installUpdateNow must await stopBackendAndWait(). The frozen backend ' +
    'lives inside the directory NSIS is about to overwrite, and a running ' +
    'process holds its own executable open on Windows.');
  assert.ok(stopAt < installAt,
    'the backend must be gone before quitAndInstall(), not after.');
});

test('electron-updater ships with the app rather than only building it', () => {
  assert.ok(
    PKG.dependencies && PKG.dependencies['electron-updater'],
    'electron-updater must be a runtime dependency. As a devDependency it ' +
    'would work in development and be missing from the installed app.');
  assert.ok(
    !(PKG.devDependencies || {})['electron-updater'],
    'electron-updater should not also be a devDependency');
  assert.ok(
    PKG.build.files.some(f => f.startsWith('node_modules')),
    'build.files is an explicit allowlist, so node_modules has to be named ' +
    'in it or the updater is absent from the packaged app.');
});

test('the publish target is configured, or no update can ever be found', () => {
  const pub = PKG.build.publish;
  assert.ok(Array.isArray(pub) && pub.length, 'build.publish is missing');
  assert.strictEqual(pub[0].provider, 'github');
  assert.ok(pub[0].owner && pub[0].repo, 'publish needs owner and repo');
});

test('every file desktop/main.js loads is in the packaged files list', () => {
  const files = PKG.build.files;
  for (const required of ['main.js', 'preload.js', 'package.json']) {
    assert.ok(
      files.includes(required),
      `"${required}" is missing from desktop/package.json build.files. It ` +
      'will work with npm start and be absent from the installed app.');
  }
});
