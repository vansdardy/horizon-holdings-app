'use strict';
/**
 * Frontend logic tests.
 *
 * Run with Node's built-in runner — no framework, no dependencies:
 *
 *     node --test tests/js/
 *
 * "Testing the frontend" sounds like it should mean driving a browser, and
 * mostly it should not. The overwhelming majority of frontend bugs are in
 * ordinary functions that happen to live in a browser file: a currency
 * converted the wrong way, a date window computed off by one, a null formatted
 * as "0". None of that needs a DOM — it needs those functions to be reachable,
 * which is exactly what pulling them into portfolio-lib.js achieved.
 *
 * Locale note: toLocaleString follows the machine's locale, so these assertions
 * check structure (prefix, decimal places, presence of digits) rather than
 * exact separators. A test that passes only in en-US is a trap for the next
 * person who runs it.
 */
const test = require('node:test');
const assert = require('node:assert/strict');

const lib = require('../../static/lib/portfolio-lib.js');

// ------------------------------------------------------------- currency
test('known currencies get their symbol', () => {
  assert.equal(lib.sym('USD'), '$');
  assert.equal(lib.sym('JPY'), '¥');
  assert.equal(lib.sym('CHF'), 'CHF ');
});

test('an unknown currency falls back to its code rather than breaking', () => {
  assert.equal(lib.sym('XYZ'), 'XYZ ');
});

test('only yen is written without decimals', () => {
  assert.equal(lib.noDecimals('JPY'), true);
  assert.equal(lib.noDecimals('USD'), false);
});

// ------------------------------------------------------------- conversion
test('USD needs no conversion', () => {
  assert.equal(lib.inBase(100, 'USD', {}), 100);
});

test('converting divides by USD-per-unit', () => {
  // 1 CHF = 1.25 USD, so 100 USD is 80 CHF.
  assert.equal(lib.inBase(100, 'CHF', { CHF: 1.25 }), 80);
});

test('a missing rate yields null, never zero', () => {
  // Zero is a number a reader would believe. Absence has to look like absence.
  assert.equal(lib.inBase(100, 'CHF', {}), null);
  assert.equal(lib.inBase(100, 'CHF', null), null);
});

test('a null amount stays null through conversion', () => {
  assert.equal(lib.inBase(null, 'CHF', { CHF: 1.25 }), null);
});

test('a zero rate is treated as missing, not as a divide by zero', () => {
  assert.equal(lib.inBase(100, 'CHF', { CHF: 0 }), null);
});

// ------------------------------------------------------------- formatting
test('money is prefixed with the reporting currency symbol', () => {
  const out = lib.moneyBase(100, 'CHF', { CHF: 1.25 });
  assert.ok(out.startsWith('CHF '), `expected a CHF prefix, got ${out}`);
  assert.ok(/80/.test(out.replace(/[^\d]/g, '').slice(0, 2)) || out.includes('80'));
});

test('yen is formatted without decimal places', () => {
  const out = lib.moneyBase(100, 'JPY', { JPY: 0.0067 });
  assert.ok(!/[.,]\d\d$/.test(out), `expected no decimals for JPY, got ${out}`);
});

test('other currencies keep two decimal places', () => {
  const out = lib.moneyBase(100, 'USD', {});
  assert.ok(/\d\d$/.test(out), `expected two decimals, got ${out}`);
});

test('an unknowable amount renders as an em dash, not as zero', () => {
  assert.equal(lib.moneyBase(null, 'USD', {}), '—');
  assert.equal(lib.moneyBase(100, 'CHF', {}), '—');
});

test('whole share counts print bare', () => {
  assert.equal(lib.fmtShares(12), '12');
  assert.equal(lib.fmtShares(0), '0');
});

test('fractional share counts keep their precision', () => {
  const out = lib.fmtShares(12.5);
  assert.ok(out.includes('12'), out);
  assert.ok(/[.,]5/.test(out), `expected the fraction to survive, got ${out}`);
});

test('an absent share count is an em dash', () => {
  assert.equal(lib.fmtShares(null), '—');
});

test('P/E labels distinguish trailing from forward', () => {
  assert.equal(lib.peTypeLabel('trailing'), '静态');
  assert.equal(lib.peTypeLabel('forward'), '动态');
  assert.equal(lib.peTypeLabel('computed'), '现算');
  assert.equal(lib.peTypeLabel(null), '', 'an unlabelled P/E must render no claim about which it is');
});

// ------------------------------------------------------------- timeframe
const history = [
  { date: '2024-06-01' }, { date: '2025-01-02' }, { date: '2025-06-01' },
  { date: '2026-01-02' }, { date: '2026-08-14' },
];

test('ALL returns the series untouched', () => {
  assert.equal(lib.sliceTF(history, 'ALL'), history);
});

test('an empty history survives any timeframe', () => {
  assert.deepEqual(lib.sliceTF([], '1Y'), []);
  assert.equal(lib.sliceTF(null, '1Y'), null);
});

test('YTD starts at the first of the latest year', () => {
  const out = lib.sliceTF(history, 'YTD');
  assert.deepEqual(out.map(h => h.date), ['2026-01-02', '2026-08-14']);
});

test('a month window counts back from the last session', () => {
  // Last session is 2026-08-14, so 3M reaches back to 2026-05-14.
  assert.deepEqual(lib.sliceTF(history, '3M').map(h => h.date), ['2026-08-14']);
});

test('a year window counts back from the last session', () => {
  assert.deepEqual(
    lib.sliceTF(history, '1Y').map(h => h.date),
    ['2026-01-02', '2026-08-14'],
  );
});

test('a window longer than the history falls back to everything', () => {
  // A newly deployed index asked for 10Y should show what exists, not a blank
  // chart that looks like the app is broken.
  assert.equal(lib.sliceTF(history, '10Y').length, history.length);
});


// ---------------------------------------------------------------- value map
// The universe's actual P/E spread on 2026-11-20 (all 78, with the two Tokyo
// split names at their corrected values), ARM's 298x first.
const PE = [298.3, 62.9, 50.2, 49.8, 46.2, 44.1, 43.9, 41.5, 37.8, 36.9, 35.2, 34.4, 31.7,
  31.6, 30.6, 30.2, 30.2, 30.0, 30.0, 28.6, 28.5, 28.4, 28.0, 27.8, 27.2, 27.1, 26.4, 25.9,
  25.9, 24.7, 23.8, 23.6, 23.5, 23.4, 22.7, 22.6, 22.2, 22.1, 22.1, 21.8, 21.7, 21.4, 21.4,
  21.4, 21.2, 20.8, 20.5, 20.1, 19.5, 18.8, 18.3, 17.7, 17.5, 17.3, 17.2, 17.2, 17.2, 17.1,
  17.0, 16.8, 15.9, 15.9, 15.8, 14.6, 14.4, 14.2, 14.2, 13.7, 13.6, 13.5, 12.6, 12.5, 12.4,
  12.4, 12.1, 11.7, 10.6, 9.5];

test('the far-out fence on log P/E removes ARM and nothing else', () => {
  const f = lib.outlierFences(PE, {k: 3, log: true});
  assert.deepEqual(PE.filter(x => x < f.lo || x > f.hi), [298.3]);
});

test('an implausibly low P/E is caught too, which a linear fence cannot do', () => {
  const vals = PE.concat([1.9]);
  const f = lib.outlierFences(vals, {k: 3, log: true});
  assert.ok(1.9 < f.lo, 'the 8766.T mid-split artefact sits below the log fence');
  assert.ok(lib.outlierFences(vals, {k: 3}).lo < 0, 'a linear lower fence is negative');
});

test('a handful of values is never trimmed', () => {
  const f = lib.outlierFences([1, 2, 3, 1000], {k: 3});
  assert.equal(f.lo, -Infinity);
  assert.equal(f.hi, Infinity);
});

test('non-finite values are ignored when computing fences', () => {
  const f = lib.outlierFences([NaN, null, undefined, ...PE], {k: 3, log: true});
  assert.ok(Number.isFinite(f.lo) && Number.isFinite(f.hi));
});

