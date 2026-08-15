/**
 * Checks on static/index.html that do not need a browser.
 *
 * These exist because of three bugs that all reached an installed build and
 * were found by a user rather than by the suite. None of them was a logic
 * mistake anyone could reason about — they were a typo, an attribute left on an
 * element, and a lifecycle misunderstanding — and all three were invisible
 * until the app ran. The tests are correspondingly mechanical.
 *
 * The page is one long inline script with no build step, so there is no bundler
 * or linter in front of it to catch a misspelled name. That is the trade the
 * project made deliberately (see the guide), and this file is the price of it.
 */

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..', '..');
const HTML = fs.readFileSync(path.join(ROOT, 'static', 'index.html'), 'utf8');

/** The inline <script> blocks, in document order, ignoring any with a src. */
function inlineScripts(html) {
  const out = [];
  const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;
  let m;
  while ((m = re.exec(html)) !== null) out.push(m[1]);
  return out;
}

// ---------------------------------------------------------------------------
// 1. No reference to a name that is never declared.
//
// The bug: `const IB = stot.base_ccy` — the result of a careless rename that
// turned `st.base_ccy` into `stot.base_ccy`. It sat inside renderNav(), which
// is wrapped in try/catch so a failure hides the panel rather than breaking the
// page. The whole NAV chart silently disappeared and nothing was logged.
//
// This is a miniature no-undef check: collect every name the script declares,
// then look for identifiers it uses that are neither declared nor a known
// browser or project global. Deliberately conservative — it only reads
// declarations, so anything it flags is worth a human look.
// ---------------------------------------------------------------------------

const BROWSER_GLOBALS = new Set([
  'window', 'document', 'console', 'navigator', 'location', 'localStorage',
  'fetch', 'alert', 'confirm', 'setTimeout', 'clearTimeout', 'setInterval',
  'clearInterval', 'requestAnimationFrame', 'Promise', 'Math', 'JSON', 'Date',
  'Number', 'String', 'Boolean', 'Object', 'Array', 'Set', 'Map', 'Error',
  'isNaN', 'isFinite', 'parseFloat', 'parseInt', 'encodeURIComponent',
  'decodeURIComponent', 'Intl', 'URL', 'Blob', 'FileReader', 'AbortController',
  'getComputedStyle', 'CustomEvent', 'Event', 'FormData', 'Headers', 'Request',
  'Response', 'structuredClone', 'queueMicrotask', 'globalThis', 'undefined',
  'NaN', 'Infinity', 'arguments', 'this', 'true', 'false', 'null',
  // Loaded from separate <script src> tags before the inline blocks.
  'Chart', 'PortfolioLib', 'I18N',
]);

/**
 * Every identifier bound by a declaration, parameter, or catch clause.
 *
 * Binding positions only — deliberately not "every identifier inside the
 * declaration". `const IB = stot.base_ccy` must contribute `IB` and not `stot`,
 * or the typo this whole test exists for would declare itself and pass.
 */
function declaredNames(src) {
  const names = new Set();
  const addAll = s => (s.match(/[A-Za-z_$][\w$]*/g) || []).forEach(n => names.add(n));
  let m;

  // const/let/var, including multi-declarator lists and destructuring patterns.
  const decl = /\b(?:const|let|var)\s+/g;
  while ((m = decl.exec(src)) !== null) {
    let i = m.index + m[0].length;
    let depth = 0, target = '', seenEquals = false;
    const flush = () => { if (!seenEquals) addAll(target); else addAll(target.split('=')[0]); target = ''; seenEquals = false; };
    while (i < src.length) {
      const c = src[i];
      if ('([{'.includes(c)) depth++;
      else if (')]}'.includes(c)) { if (depth === 0) break; depth--; }
      else if (c === ';' && depth === 0) break;
      else if (c === ',' && depth === 0) { flush(); i++; continue; }
      else if (c === '=' && depth === 0 && src[i + 1] !== '=' && src[i - 1] !== '=' &&
               src[i - 1] !== '!' && src[i - 1] !== '<' && src[i - 1] !== '>') seenEquals = true;
      else if (!seenEquals) target += c;
      // `of`/`in` in a for-head end the binding target too.
      if (!seenEquals && depth === 0 && /\b(?:of|in)\s$/.test(target)) {
        target = target.replace(/\b(?:of|in)\s$/, '');
        break;
      }
      i++;
    }
    flush();
  }

  const simple = re => { let x; while ((x = re.exec(src)) !== null) names.add(x[1]); };
  simple(/\bfunction\s+([A-Za-z_$][\w$]*)/g);
  simple(/\bclass\s+([A-Za-z_$][\w$]*)/g);
  simple(/\bcatch\s*\(\s*([A-Za-z_$][\w$]*)/g);

  // Parameter lists. Over-collecting here only makes the test permissive: a
  // parameter name can never be the undeclared identifier we are hunting.
  const params = /(?:function\s*[A-Za-z_$\w]*\s*\(([^)]*)\)|\(([^)]*)\)\s*=>|([A-Za-z_$][\w$]*)\s*=>)/g;
  while ((m = params.exec(src)) !== null) addAll(m[1] || m[2] || m[3] || '');

  // Object-literal method shorthand — `{ destroy(){}, update(){} }`. These are
  // property names being defined, not names being read, and the plain scan
  // cannot tell them apart from a call because neither is preceded by a dot.
  simple(/[{,]\s*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{/g);

  return names;
}

/**
 * Blank out comments, string and template literals, and regex literals, so that
 * only code remains. Done as a single character scan rather than with regular
 * expressions: a naive strip removes `//` from inside a URL string, which
 * unbalances the quote and desynchronises everything after it. Template
 * literals keep their `${…}` contents, which really are code.
 */
function stripNonCode(src) {
  let out = '';
  let i = 0;
  // Depth of `${…}` nesting per open template literal, so a template inside an
  // interpolation inside a template still closes in the right place.
  const templates = [];
  // Whether a `/` here starts a regex literal or is a division sign. After a
  // value (identifier, `)`, `]`, literal) it divides; otherwise it opens.
  let prev = '';
  const lastMeaningful = () => prev;

  while (i < src.length) {
    const c = src[i];
    const nx = src[i + 1];

    if (c === '/' && nx === '/') {
      while (i < src.length && src[i] !== '\n') i++;
      out += ' ';
      continue;
    }
    if (c === '/' && nx === '*') {
      i += 2;
      while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i++;
      i += 2;
      out += ' ';
      continue;
    }
    if (c === "'" || c === '"') {
      const q = c;
      i++;
      while (i < src.length && src[i] !== q) i += (src[i] === '\\' ? 2 : 1);
      i++;
      out += ' 0 ';
      prev = '0';
      continue;
    }
    if (c === '`') {
      i++;
      templates.push(0);
      out += ' 0 ';
      prev = '0';
      // Consume until the matching backtick, emitting interpolations as code.
      while (i < src.length && templates.length) {
        if (src[i] === '\\') { i += 2; continue; }
        if (src[i] === '`') { templates.pop(); i++; continue; }
        if (src[i] === '$' && src[i + 1] === '{') {
          i += 2;
          let depth = 1;
          const start = i;
          while (i < src.length && depth > 0) {
            if (src[i] === '{') depth++;
            else if (src[i] === '}') depth--;
            if (depth > 0) i++;
          }
          out += ' ' + stripNonCode(src.slice(start, i)) + ' ';
          i++;
          continue;
        }
        i++;
      }
      continue;
    }
    if (c === '/' && !/[\w$)\]]/.test(lastMeaningful())) {
      // Regex literal.
      i++;
      let inClass = false;
      while (i < src.length) {
        if (src[i] === '\\') { i += 2; continue; }
        if (src[i] === '[') inClass = true;
        else if (src[i] === ']') inClass = false;
        else if (src[i] === '/' && !inClass) break;
        i++;
      }
      i++;
      while (i < src.length && /[a-z]/.test(src[i])) i++;   // flags
      out += ' 0 ';
      prev = '0';
      continue;
    }

    out += c;
    if (!/\s/.test(c)) prev = c;
    i++;
  }
  return out;
}

/** Identifiers actually referenced, minus property accesses and key positions. */
function referencedNames(src) {
  const stripped = stripNonCode(src);

  const names = new Set();
  const re = /(\.)?\b([A-Za-z_$][\w$]*)\b(\s*:)?/g;
  let m;
  while ((m = re.exec(stripped)) !== null) {
    if (m[1]) continue;            // obj.prop — a property, not a binding
    if (m[3]) continue;            // { key: … } — an object key
    names.add(m[2]);
  }
  return names;
}

const KEYWORDS = new Set([
  'const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while',
  'do', 'break', 'continue', 'new', 'delete', 'typeof', 'instanceof', 'in',
  'of', 'try', 'catch', 'finally', 'throw', 'switch', 'case', 'default',
  'class', 'extends', 'super', 'async', 'await', 'yield', 'void', 'static',
  'get', 'set', 'export', 'import', 'from', 'as',
]);

test('the page script references no undeclared name', () => {
  const scripts = inlineScripts(HTML);
  assert.ok(scripts.length > 0, 'expected inline <script> blocks');

  // Both blocks share one global scope in the browser, so analyse them together.
  const all = stripNonCode(scripts.join('\n'));
  const declared = declaredNames(all);
  const referenced = referencedNames(all);

  const unknown = [...referenced].filter(n =>
    !declared.has(n) && !BROWSER_GLOBALS.has(n) && !KEYWORDS.has(n));

  assert.deepStrictEqual(
    unknown, [],
    `undeclared identifier(s) in static/index.html: ${unknown.join(', ')}\n` +
    'Either it is a typo (this test exists because "stot" was one) or it is a ' +
    'new global that belongs in BROWSER_GLOBALS above.');
});

// ---------------------------------------------------------------------------
// 2. Nothing translated by attribute is also written by script.
//
// The bug: the status bar carried data-i18n="status.connecting" so its first
// paint would read "Connecting…" in the right language. loadStatus() then
// replaced it with the live status — but the attribute stayed, and applyI18n()
// re-applies every data-i18n on the page on each language switch. Switching
// language reset a working status bar to "Connecting…" and nothing put it
// back, so the app looked like it had lost its backend.
//
// The rule: an element is either translated by attribute or written by script.
// If it must be both, it has to opt out of the first once it holds real data,
// which is what setStatusLine() does.
// ---------------------------------------------------------------------------

test('no element is both data-i18n translated and script written', () => {
  const i18nIds = new Set();
  const tagRe = /<[^>]*\bdata-i18n(?:-[a-z]+)?=[^>]*>/g;
  let m;
  while ((m = tagRe.exec(HTML)) !== null) {
    const id = /\bid="([^"]+)"/.exec(m[0]);
    if (id) i18nIds.add(id[1]);
  }

  const written = new Set();
  const writeRe = /(?:\$\(|getElementById\()'([A-Za-z0-9_]+)'\)\s*\.(?:innerHTML|textContent)\s*=/g;
  while ((m = writeRe.exec(HTML)) !== null) written.add(m[1]);

  const both = [...i18nIds].filter(id => written.has(id));

  assert.deepStrictEqual(
    both, [],
    `element(s) both data-i18n translated and written by script: ${both.join(', ')}\n` +
    'A language switch will overwrite whatever the script put there. Write ' +
    'through a helper that removes the attribute (see setStatusLine).');
});

// ---------------------------------------------------------------------------
// 3. The status bar keeps its opt-out.
//
// Guards the specific mechanism above rather than the general rule, so that
// deleting removeAttribute fails loudly even if the element stops matching the
// pattern the previous test looks for.
// ---------------------------------------------------------------------------

test('setStatusLine drops the data-i18n attribute before writing', () => {
  const fn = /function setStatusLine\([\s\S]*?\n}/.exec(HTML);
  assert.ok(fn, 'setStatusLine() not found in static/index.html');
  assert.match(
    fn[0], /removeAttribute\('data-i18n'\)/,
    'setStatusLine must remove data-i18n, or a language switch will reset the ' +
    'status bar to "Connecting…" with nothing to put it right.');
});

// ---------------------------------------------------------------------------
// 4. Every chart lives in a function that the language switch calls.
//
// The bug: the sector and country charts were constructed at the top level of
// the script, once, at load. Their axis labels are translated — but there was
// no function to call to redraw them, so switching to Chinese left the sector
// and country names in English. The drift chart at the bottom did live in a
// function, and was simply missing from setLang()'s list, with the same result.
//
// The rule: a chart holding translated text must be rebuildable, and setLang()
// must actually rebuild it. Both halves are checked, because either one alone
// leaves the labels stuck.
// ---------------------------------------------------------------------------

/** Names of functions containing a `new Chart(` call, by brace matching. */
function chartRenderers(code) {
  const found = new Map();
  const fnRe = /function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{/g;
  let m;
  while ((m = fnRe.exec(code)) !== null) {
    let i = m.index + m[0].length, depth = 1;
    while (i < code.length && depth > 0) {
      if (code[i] === '{') depth++;
      else if (code[i] === '}') depth--;
      i++;
    }
    const body = code.slice(m.index, i);
    if (/new Chart\s*\(/.test(body)) found.set(m[1], body);
  }
  return found;
}

test('every chart is built inside a function the language switch can call', () => {
  const code = stripNonCode(inlineScripts(HTML).join('\n'));

  const renderers = chartRenderers(code);
  assert.ok(renderers.size >= 3, `expected several chart renderers, found ${renderers.size}`);

  // No chart may be constructed outside a function: count all constructions and
  // compare with those accounted for inside renderers.
  const total = (code.match(/new Chart\s*\(/g) || []).length;
  const inside = [...renderers.values()]
    .reduce((n, body) => n + (body.match(/new Chart\s*\(/g) || []).length, 0);
  assert.strictEqual(
    total, inside,
    `${total - inside} chart(s) are constructed at the top level of the script. ` +
    'A chart built once at load can never be relabelled, so its translated ' +
    'axis labels stay in whatever language the page started in.');

  // And each renderer must be named in setLang()'s rebuild list.
  const setLang = /function setLang\([\s\S]*?\n}/.exec(code);
  assert.ok(setLang, 'setLang() not found');

  const missing = [...renderers.keys()].filter(name =>
    !new RegExp(`\\b${name}\\b`).test(setLang[0]));

  assert.deepStrictEqual(
    missing, [],
    `chart renderer(s) missing from setLang(): ${missing.join(', ')}\n` +
    'Their labels will keep the old language after a switch.');
});

// ---------------------------------------------------------------------------
// 5. Exchanges have a name in both languages.
//
// The bug: EXCHANGE_INFO carried only Chinese names, so the table printed
// Chinese exchange names to an English reader, and the filter dropdown fell
// back to the raw key — which is a code like "SIX", not a name.
// ---------------------------------------------------------------------------

const CJK = /[㐀-鿿豈-﫿]/;

test('every exchange has an English name, and it is not Chinese', () => {
  const block = /const EXCHANGE_INFO = \{[\s\S]*?\n\};/.exec(HTML);
  assert.ok(block, 'EXCHANGE_INFO not found');

  const entries = [...block[0].matchAll(/^\s*'([^']+)':\s*\{([^}]*)\}/gm)];
  assert.ok(entries.length >= 10, `expected the full exchange table, got ${entries.length}`);

  const missing = [], stillChinese = [];
  for (const [, key, body] of entries) {
    const en = /name_en:\s*'([^']*)'/.exec(body);
    if (!en) { missing.push(key); continue; }
    if (CJK.test(en[1])) stillChinese.push(`${key} -> ${en[1]}`);
    // A note in one language needs the other, or half the row switches.
    if (/\bnote:/.test(body) && !/\bnote_en:/.test(body)) missing.push(`${key} (note_en)`);
  }

  assert.deepStrictEqual(missing, [], `exchange entries missing English: ${missing.join(', ')}`);
  assert.deepStrictEqual(stillChinese, [],
    `exchange name_en still contains Chinese: ${stillChinese.join(', ')}`);
});

test('no table renders a raw exchange name in any language', () => {
  // The first version of this test looked only at the constituents table, so
  // when the identical bug was fixed there it kept passing while the positions
  // table went on printing Chinese to English readers. Scanning the whole file
  // for the mistake, rather than one known site of it, is the difference
  // between a test for a bug and a test for a class of bug.
  const code = stripNonCode(inlineScripts(HTML).join('\n'));
  const offenders = [];
  for (const m of code.matchAll(/\$\{\s*(ex|exchInfo\([^)]*\))\.(name|note)\s*\}/g)) {
    offenders.push(m[0]);
  }
  assert.deepStrictEqual(
    offenders, [],
    `raw exchange name/note interpolated into markup: ${offenders.join(', ')}\n` +
    '.name and .note are always Chinese. Use dispExch() / dispExchNote(), which ' +
    'follow the language.');
});

// ---------------------------------------------------------------------------
// 6. The NAV panel reads the index currency from the stats it was given.
//
// Pins the exact line the typo lived on. `st` is the merged stats object;
// anything else is the rename having gone wrong again.
// ---------------------------------------------------------------------------

test('renderNav reads base_ccy from the stats object', () => {
  const fn = /function renderNav\(\)[\s\S]*?\n}/.exec(HTML);
  assert.ok(fn, 'renderNav() not found in static/index.html');
  assert.match(fn[0], /const IB = st\.base_ccy/,
    'renderNav must read st.base_ccy (the merged stats object)');
});
