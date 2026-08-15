'use strict';
/**
 * Dictionary tests.
 *
 * A translation does not fail loudly. It fails as one label in one panel that
 * nobody looked at, in the language the author does not read — which is the
 * worst kind of bug to rely on noticing. These checks are mechanical for
 * exactly that reason.
 */
const test = require('node:test');
const assert = require('node:assert/strict');

const I18N = require('../../static/lib/i18n.js');

const HAN = /[一-鿿]/;

test('both languages define exactly the same keys', () => {
  const en = Object.keys(I18N.STRINGS.en).sort();
  const zh = Object.keys(I18N.STRINGS.zh).sort();
  const missingInZh = en.filter(k => !(k in I18N.STRINGS.zh));
  const missingInEn = zh.filter(k => !(k in I18N.STRINGS.en));
  assert.deepEqual(missingInZh, [], 'keys present in English but not Chinese');
  assert.deepEqual(missingInEn, [], 'keys present in Chinese but not English');
});

test('no English string was left untranslated', () => {
  // The exception is the language switch itself, which is deliberately labelled
  // in the language it switches TO.
  const leaks = Object.entries(I18N.STRINGS.en)
    .filter(([k, v]) => k !== 'lang.switch' && HAN.test(v))
    .map(([k]) => k);
  assert.deepEqual(leaks, [], 'English values still containing Chinese characters');
});

test('no string is empty', () => {
  for (const lang of I18N.LANGS) {
    for (const [k, v] of Object.entries(I18N.STRINGS[lang])) {
      assert.ok(String(v).trim().length > 0, `${lang}.${k} is empty`);
    }
  }
});

test('placeholders match between languages', () => {
  // A {n} present in one language and missing in the other renders a sentence
  // with a hole in it, in one language only.
  const placeholders = s => (String(s).match(/\{\w+\}/g) || []).sort().join(',');
  for (const key of Object.keys(I18N.STRINGS.en)) {
    assert.equal(
      placeholders(I18N.STRINGS.zh[key]), placeholders(I18N.STRINGS.en[key]),
      `placeholders differ for ${key}`,
    );
  }
});

test('t() substitutes variables', () => {
  assert.equal(I18N.t('filter.count', 'en', { n: 12, total: 78 }), '12 of 78 companies');
});

test('an unknown key returns the key, not a blank', () => {
  // Visible nonsense is a bug report. A blank is a bug nobody files.
  assert.equal(I18N.t('no.such.key', 'en'), 'no.such.key');
});

test('an unknown language falls back to English rather than breaking', () => {
  assert.equal(I18N.t('th.ticker', 'fr'), 'Ticker');
});

test('browser locale strings resolve to a supported language', () => {
  assert.equal(I18N.resolve('zh-CN'), 'zh');
  assert.equal(I18N.resolve('zh-Hans-CN'), 'zh');
  assert.equal(I18N.resolve('en-GB'), 'en');
  assert.equal(I18N.resolve('de-DE'), 'en', 'unsupported locales get the default');
  assert.equal(I18N.resolve(undefined), 'en');
});

test('English is the default', () => {
  assert.equal(I18N.DEFAULT, 'en');
});
