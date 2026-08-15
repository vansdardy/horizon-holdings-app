'use strict';
/**
 * Pure display logic, shared by the page and its tests.
 *
 * These functions used to live inside index.html, where each of them read
 * page-level variables (BASE, FXRATES, TF) directly. That made them impossible
 * to test: you cannot call a function whose inputs are invisible without
 * recreating the entire page around it.
 *
 * The fix was not clever, and it rarely is — every input became a parameter.
 * That is usually what "make it testable" turns out to mean, and the design is
 * better for it regardless of whether a test ever runs: a reader can now see
 * what each function depends on from its signature alone.
 *
 * index.html keeps one-line adapters that bind the page's current state, so no
 * call site had to change. Refactoring is far less frightening when the edit is
 * "move the body, leave the name" than when it is "touch two hundred lines".
 *
 * The wrapper below is a small UMD shim: a plain <script> tag in the browser
 * gets window.PortfolioLib, and require() in Node gets the same object. No
 * bundler, no build step, which is the same bargain the rest of the frontend
 * makes.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.PortfolioLib = factory();
})(typeof self !== 'undefined' ? self : this, function () {

  const CCY_SYMBOL = {
    USD: '$', CAD: 'C$', CHF: 'CHF ', EUR: '€', GBP: '£', JPY: '¥', DKK: 'kr ',
  };

  /** Display symbol for a currency; unknown codes fall back to the code itself. */
  function sym(ccy) {
    return CCY_SYMBOL[ccy] || (ccy + ' ');
  }

  /** Yen amounts are conventionally written without decimals. */
  function noDecimals(ccy) {
    return ccy === 'JPY';
  }

  /**
   * Convert a USD amount into the reporting currency.
   *
   * `fxRates` maps a currency to how many USD one unit of it is worth, which is
   * the direction the data source quotes and therefore the direction stored.
   * Returns null rather than 0 when the rate is unknown: zero is a number
   * someone would believe, and a missing rate is not a value of zero.
   */
  function inBase(usd, base, fxRates) {
    if (usd == null) return null;
    if (base === 'USD') return usd;
    const rate = fxRates ? fxRates[base] : null;
    return rate ? usd / rate : null;
  }

  /** inBase, formatted for display. Em dash when the value cannot be known. */
  function moneyBase(usd, base, fxRates) {
    const v = inBase(usd, base, fxRates);
    if (v == null) return '—';
    const digits = noDecimals(base) ? 0 : 2;
    return sym(base) + v.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  /**
   * Share counts: whole numbers stay bare, fractions keep enough precision to
   * show a real broker's fractional holding without inventing digits.
   */
  function fmtShares(v) {
    if (v == null) return '—';
    return Number.isInteger(v)
      ? String(v)
      : v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 });
  }

  /**
   * Chinese finance convention: 静态 is trailing P/E (actual reported earnings),
   * 动态 is forward (analyst estimates). These differ by multiples for a richly
   * valued name, so the number is never shown without saying which it is.
   */
  function peTypeLabel(t) {
    return t === 'trailing' ? '静态'
         : t === 'forward' ? '动态'
         : t === 'computed' ? '现算'
         : '';
  }

  /**
   * Trim a NAV history to a timeframe: ALL, YTD, or NM / NY.
   *
   * Falls back to the full history when the window would be empty, so a newly
   * deployed index asked for "5Y" shows what exists rather than a blank chart.
   */
  function sliceTF(hist, tf) {
    if (tf === 'ALL' || !hist || !hist.length) return hist;

    const last = new Date(hist[hist.length - 1].date + 'T00:00:00');
    let from;
    if (tf === 'YTD') {
      from = new Date(last.getFullYear(), 0, 1);
    } else {
      const n = parseInt(tf, 10);
      from = new Date(last);
      if (tf.endsWith('M')) from.setMonth(from.getMonth() - n);
      else from.setFullYear(from.getFullYear() - n);
    }

    const iso = from.toISOString().slice(0, 10);
    const out = hist.filter(h => h.date >= iso);
    return out.length ? out : hist;
  }

  return { CCY_SYMBOL, sym, noDecimals, inBase, moneyBase, fmtShares, peTypeLabel, sliceTF };
});
