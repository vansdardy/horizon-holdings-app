/**
 * The version number appears in more than one file, and the copies drift.
 *
 * This test exists because they did: the guide shipped inside v1.7.0 still
 * announced "v1.6.0 shipped" in its masthead and colophon. Nothing was broken
 * by it, which is exactly why nobody noticed — a wrong version number in
 * documentation is invisible to every test that checks behaviour, and visible
 * to the first person who reads the page.
 *
 * `desktop/package.json` is the single source of truth: it is what
 * `app.getVersion()` returns, what electron-builder stamps on the installer,
 * and what the updater compares against. Everything else must agree with it.
 */

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..', '..');
const VERSION = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'desktop', 'package.json'), 'utf8')).version;

test('the version is a plain semantic version', () => {
  assert.match(VERSION, /^\d+\.\d+\.\d+$/,
    `desktop/package.json version "${VERSION}" must be MAJOR.MINOR.PATCH — the ` +
    'updater compares these numerically.');
});

test('the guide announces the version it ships inside', () => {
  const guide = fs.readFileSync(
    path.join(ROOT, 'docs', 'building-this-app.html'), 'utf8');

  // Every "vX.Y.Z" that is making a claim about THIS build, as opposed to the
  // many historical references in the versioning and releases sections.
  const claims = [
    { what: 'masthead', re: /<span><b>v(\d+\.\d+\.\d+)<\/b> shipped<\/span>/ },
    { what: 'colophon', re: /Horizon Holdings v(\d+\.\d+\.\d+) — a local portfolio/ },
  ];

  const wrong = [];
  for (const { what, re } of claims) {
    const m = re.exec(guide);
    assert.ok(m, `could not find the ${what} version in docs/building-this-app.html`);
    if (m[1] !== VERSION) wrong.push(`${what}: says ${m[1]}, package.json says ${VERSION}`);
  }

  assert.deepStrictEqual(
    wrong, [],
    `the guide's version is stale — ${wrong.join('; ')}.\n` +
    'The guide ships inside the app, so a stale version there is a stale ' +
    'version shown to every user who opens it.');
});

test('the changelog has an entry for the current version', () => {
  const changelog = fs.readFileSync(path.join(ROOT, 'CHANGELOG.md'), 'utf8');
  assert.ok(
    new RegExp(`^## v${VERSION.replace(/\./g, '\\.')}$`, 'm').test(changelog),
    `CHANGELOG.md has no "## v${VERSION}" section. Releasing a version with no ` +
    'entry means the release notes have to be reconstructed from commits later.');
});
