/**
 * Layout rules in the guide that were silently doing nothing.
 *
 * The stylesheet said figures, tables and code blocks should break out of the
 * prose measure to the full column width. They never did, for two compounding
 * reasons: the selectors were written `.flow > figure`, and a figure lives
 * inside `<section class="part">` rather than directly in `.flow`; and the rule
 * above them capped `.flow > *` — the sections themselves — at the prose
 * measure, so no descendant could have been wider even if the selector had
 * matched.
 *
 * Nothing about that fails visibly. The page looks deliberate; the diagrams are
 * simply small. Every diagram in this document is drawn at 900px and was being
 * displayed at 578, and the wide comparison tables were folded into a column
 * meant for prose.
 *
 * CSS cannot be executed here, so these read the stylesheet. That catches the
 * specific shape of the mistake — a rule that cannot match the document — which
 * is the part that went unnoticed for eighteen parts of writing.
 */

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const GUIDE = fs.readFileSync(
  path.join(__dirname, '..', '..', 'docs', 'building-this-app.html'), 'utf8');

/**
 * The contents of the <style> block, with comments removed.
 *
 * The comments matter here: the one above the flow rules quotes the broken
 * selector verbatim to explain what went wrong, so a test scanning raw CSS
 * finds the very string it is asserting the absence of, and fails on the
 * explanation rather than the code.
 */
const CSS = (() => {
  const m = /<style[^>]*>([\s\S]*?)<\/style>/.exec(GUIDE);
  assert.ok(m, 'no <style> block found in the guide');
  return m[1].replace(/\/\*[\s\S]*?\*\//g, ' ');
})();

test('wide elements break out where they actually live', () => {
  // Figures et al. are children of .part, so the breakout rule has to say so.
  for (const sel of ['.part > figure', '.part > pre', '.part > .tablewrap']) {
    assert.ok(
      CSS.includes(sel),
      `the breakout rule must target "${sel}". Written only as ".flow > …" it ` +
      'matches nothing, because these elements sit inside <section class="part">.');
  }
});

test('sections are not capped at the prose measure', () => {
  // `.flow > *{max-width:var(--col)}` caps the SECTIONS, which silently
  // prevents anything inside them from breaking out.
  assert.doesNotMatch(
    CSS, /\.flow\s*>\s*\*\s*\{\s*max-width:\s*var\(--col\)/,
    'capping .flow > * at the prose measure caps the sections themselves, so ' +
    'no figure or table inside one can ever be wider. Cap the text instead.');
  assert.match(
    CSS, /\.flow\s*>\s*\*\s*\{\s*max-width:\s*var\(--wide\)/,
    'sections should span the full column; the measure is applied to the text.');
});

test('the prose measure is still applied to prose', () => {
  // The point is not "make everything wide" — a 1140px line of body text is
  // unreadable. The measure has to survive, just on the right elements.
  assert.match(CSS, /\.part\s*>\s*\*\s*\{[^}]*max-width:\s*var\(--col\)/,
    'text inside a part must still be held to the reading measure.');
});

test('floated margin notes cannot collide with full-width elements', () => {
  // At wide viewports the asides float into the margin. A 1140px table
  // starting beside a 322px floated note would run underneath it.
  const wide = /@media\s*\(min-width:\s*1500px\)\s*\{([\s\S]*?)\n  \}/.exec(CSS);
  assert.ok(wide, 'the wide-screen media query was not found');
  assert.match(wide[1], /float:\s*right/, 'asides should move into the margin');
  assert.match(
    wide[1], /clear:\s*both/,
    'full-width elements must clear the floated notes, or they overlap.');
});
