'use strict';
/**
 * Interface strings, in English and Chinese.
 *
 * The application was written in Chinese first and grew an English audience
 * later, which is the usual order and the awkward one — retro-fitting
 * translation means finding every string that was written inline. The lesson
 * for a next project is cheap to state and hard to remember: if there is any
 * chance of a second language, put the strings in a table from the start, even
 * a table with one column.
 *
 * Conventions here:
 *   - Keys are `section.thing`, so a missing one is obvious in the interface
 *     rather than silently blank: t() returns the key itself when it cannot
 *     find a string.
 *   - Company names, sectors and countries are NOT in this file. They are data,
 *     not interface, and live with the rest of the constituent data.
 *   - `zh` is the original wording, preserved rather than re-translated from
 *     the English. Going through a third language loses things.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.I18N = factory();
})(typeof self !== 'undefined' ? self : this, function () {

  const STRINGS = {
    en: {
      'doc.title': 'Horizon Holdings — Global Value Portfolio',
      'chart.missing': '⚠ The chart library failed to load, so no charts will be drawn. Tables, filters, weights, profit and loss and exchange details all work normally.<br>The library ships with the program, so this usually means a file under static/vendor/ is missing or damaged — reinstalling fixes it.',

      'hero.h1': 'Global <em>Value</em> Portfolio',
      'hero.sub': 'A 78-stock portfolio built on Buffett and Berkshire\'s core selection logic — a business you can understand, a durable economic moat, honest management that allocates capital well, and a sensible margin of safety on valuation. It spans <b>11 Bloomberg sectors</b> across <b>12 markets</b> (US, Canada, Japan, UK, France, Germany, Netherlands, Switzerland, Belgium, Italy, Denmark, Ireland). The technology sector relaxes the criteria somewhat for chokepoint companies such as ASML, Arm and Tokyo Electron, while excluding pure speculation.',
      'hero.guide': 'How this app was built →',

      's01.title': 'Portfolio at a Glance',
      's02.title': 'Sector & Geographic Allocation',
      's02.desc': 'Weights are driven by a per-company "confidence score" (1–6, reflecting moat strength and fit with Buffett-style selection) — not by market capitalisation, and not by price momentum.',
      's02.sector': 'Sector · Bloomberg',
      's02.geo': 'Geography',

      's03.title': 'Value Map',
      's03.desc': 'Valuation runs along the horizontal axis (P/E — further left is cheaper) and dividend yield up the vertical (higher is more income). Bubble size is portfolio weight and colour is sector, so the portfolio\'s value-and-income character is visible at a glance. Figures are approximate estimates; hover for detail.',
      's03.legend': '// Larger bubble = larger portfolio weight · top-left quadrant = cheap and high-yielding (the classic value corner)',

      's04.title': 'Holdings',
      's04.desc': 'Click any row to see its moat and the reasoning behind including it. Click a column header to sort.',
      's04.ibkrNote': 'In the Exchange column, a <span class="ibkr-code" style="font-size:9px;padding:1px 5px;">green code</span> is the internal IBKR exchange code, checked against IBKR\'s own documentation and real user symbol mappings. Several differ from the exchange\'s common name — Frankfurt is <b>IBIS</b> at IBKR, and Tokyo is <b>TSEJ</b> to distinguish it from Toronto. The two <span class="ibkr-code unverified" style="font-size:9px;padding:1px 5px;">orange "unverified"</span> entries (Belgium and Ireland) are ones no reliable source confirmed — search by ticker or ISIN inside IBKR before trading. This column is for reference and is not an order instruction.',

      'filter.allSector': 'All sectors',
      'filter.allRegion': 'All regions',
      'filter.allExchange': 'All exchanges',
      'filter.search': 'Search ticker or company name...',
      'filter.count': '{n} of {total} companies',

      'th.ticker': 'Ticker',
      'th.company': 'Company',
      'th.region': 'Region',
      'th.exchange': 'Exchange',
      'th.ibkrCode': 'IBKR code',
      'th.sector': 'Sector',
      'th.weight': 'Weight %',
      'th.divYield': 'Div. yield %',
      'th.pe': 'P/E',
      'th.beta': 'Beta',
      'th.score': 'Score',

      's05.title': 'Model Index NAV',
      's05.desc': 'The rules: NAV starts at 10bn in the base currency (CHF by default) ÷ 200m units = <b>50.00 per unit</b>. The backend fetches prices once after the close each day and recomputes. It <b>buys whole shares only</b>, holding the remainder as cash in each listing\'s local currency (seven cash pools), and <b>rebalances once a year</b> to the confidence-score target weights on the first trading day. This is a real curve <b>accumulating forward from the day you deployed it</b> — not a backtest.',

      'rebase.body': 'The NAV series was seeded in <b id="rbOld">?</b>, but the current setting (<code>BASE_CCY</code> in <code>.env</code>) is <b id="rbNew">?</b>. Two currencies in one curve is meaningless, so further fetches are refused. Resetting clears the NAV history and re-seeds in the new currency from today — <b>your positions, cash and price archive are untouched</b>.',
      'rebase.btn': 'Re-seed in',

      'status.label': 'Status',
      'status.connecting': 'Connecting…',
      'status.refresh': 'Fetch now',
      'status.mock': '⚠ MOCK data (test mode — not real prices)',

      'offline.h4': 'Backend not running',
      'offline.p1': 'The NAV curve and position records on this page need the local backend for data and storage. To start it:',
      'offline.p2': 'Then open this page at <code>http://127.0.0.1:8000</code> rather than by double-clicking the HTML file. The first two sections work offline regardless.',
      'offline.p3': 'After the first start, click "Fetch now" once to seed the index. From then on the backend fetches once a day at <code>FETCH_HOUR</code> (18:00 by default). Data lives in <code>portfolio.db</code>, a single SQLite file.',

      'sim.label': 'Hypothetical start date',
      'sim.run': 'Recompute',
      'sim.clear': 'Back to actual',
      'nav.chartTitle': 'NAV per unit',

      'ticker.pauseHint': 'Hover or focus to pause the tape',
      'hold.title': 'What the index actually holds',
      'hold.desc': 'The book the NAV above is calculated from. The index buys <b>whole shares only</b>, so every position leaves a remainder that stays as cash in the currency it was left in — holdings plus that cash, marked at the latest close, <i>is</i> the NAV. Everything here is the model index, not your own positions.',
      'hold.asOf': 'Priced at the close of {d}',
      'hold.thShares': 'Shares held',
      'hold.thPrice': 'Price',
      'hold.thValue': 'Market value',
      'hold.thActual': 'Weight',
      'hold.thTarget': 'Target',
      'hold.cashTitle': 'Cash left over',
      'hold.thCcy': 'Currency',
      'hold.thAmount': 'Amount',
      'hold.equity': 'Securities',
      'hold.cash': 'Cash',
      'hold.nav': 'Total NAV',
      'hold.perShare': 'Per unit',
      'hold.count': '{n} of 78 held',
      'hold.cashPct': '{v} of NAV',
      'hold.notSeeded': 'The index has not been seeded yet, so there are no holdings to show. Fetch prices once and it will buy in at the target weights.',
      'hold.unpriced': '⚠ {n} held position(s) had no price at that close and are valued at zero here: {t}',
      'hold.rounding': 'Columns are rounded for display; the totals are computed from full precision.',

      's06.title': 'My Positions',
      's06.desc': 'Enter the <b>number of shares you actually hold</b> and your <b>average cost per share, in the listing\'s local currency</b> — the two numbers your broker shows you. This works out your unrealised profit and loss, your <b>actual weight</b>, the <b>drift</b> from the target weight, and <b>how many shares would close the gap</b>. Update it after each purchase and you can watch the portfolio move towards the target structure.',

      'warn.gapTitle': '⚠ About the "shares to close the gap" column',
      'warn.gapBody': 'That column is <b>pure arithmetic</b>: your current total market value × the target weight, minus what you already hold, converted into shares. It <b>does not account for</b> your cash, your tax treatment (registered versus taxable accounts differ), trading costs or currency costs, and it makes no judgement about whether the current price is sensible. <b>It is a comparison tool, not a buy recommendation.</b> Judge for yourself, and consult a licensed adviser where it matters.',

      'cash.label': 'CASH · by currency (the part not yet invested in shares)',
      'btn.save': 'Save positions',
      'btn.export': 'Export JSON',
      'btn.backup': 'Back up database',
      'btn.import': 'Import database…',
      'btn.importTitle': 'Import a portfolio.db from a file — your current data is backed up first',
      'chk.onlyHeld': 'Only held',
      'chk.cashGap': 'Include cash in the gap',
      'pos.search': 'Search ticker or company name...',
      'pos.reportCcy': 'Reporting currency',

      'posTh.shares': 'Shares',
      'posTh.avgCost': 'Avg. cost',
      'posTh.price': 'Price',
      'posTh.local': 'local',
      'posTh.marketValue': 'Market value',
      'posTh.pnl': 'P&L',
      'posTh.actualWeight': 'Actual weight',
      'posTh.targetWeight': 'Target weight',
      'posTh.drift': 'Drift',
      'posTh.gapShares': 'Shares to target',

      'drift.title': 'By sector · actual vs target weight',

      'disc.title': 'Disclaimer',
      'disc.body': 'The dividend yield, P/E, beta and expected-return figures on this page are approximate estimates based on public knowledge (around mid-2026), used for portfolio structure design and teaching. They are not live market data and are not investment advice. Verify against an authoritative source before acting, and consult a licensed financial adviser. Past performance does not indicate future returns, and investing in equities risks loss of principal.',

      'kpi.holdings': 'Holdings',
      'kpi.divYield': 'Weighted div. yield',
      'kpi.pe': 'Harmonic weighted P/E',
      'kpi.beta': 'Weighted beta',
      'kpi.capm': 'CAPM expected return',
      'kpi.effN': 'Effective holdings',
      'kpi.weightSum': 'Weights total {v}',
      'kpi.liveOf': '{live} of {n} live',
      'kpi.peStatic': 'Stricter than a simple weighted average (static estimate)',
      'kpi.dyEstimate': 'Weight-averaged (approximate)',
      'kpi.betaEstimate': 'Proxy for systematic risk (approximate)',
      'kpi.mixed': ', mixed basis — treat with care',

      'tag.live': 'live',
      'tag.estimate': 'estimate',
      'tag.unverified': 'unverified',
      'tag.ibkrVerified': 'IBKR exchange code (verified)',
      'tag.ibkrUnverified': 'Could not verify the IBKR-specific code — search by ticker or ISIN inside IBKR',
      'axis.divYield': 'Dividend yield %',
      'lang.switch': '中文',
      'kpi.peLive': '{live} of {n} live (trailing {tr} / forward {fw})',
      'kpi.dyLive': '{live} of {n} live',
      'kpi.betaLive': '{live} of {n} live',
      'kpi.capmSub': 'rf 4.6% + beta x ERP 4.5%',
      'vm.tag': ' P/E {pe}x{peTag} - yield {dy}%{dyTag} - weight {w}%',
      'vm.livePe': ' - live ({type} P/E)',
      'vm.est': ' - estimate',
      'vm.live': ' - live',
      'live.title': 'Live data ({q}, fetched {d})',
      'live.titlePe': 'Live {type} P/E ({q}, fetched {d})',
      'sb.latestPrice': 'Latest price date',
      'sb.inception': 'Inception',
      'sb.notSeeded': 'not seeded',
      'sb.navPoints': 'NAV points',
      'sb.dailyFetch': 'Daily fetch',
      'sb.archived': 'Archived prices',
      'sb.rows': '{rows} rows / {days} days',
      'sb.csv': 'Download CSV',
      'sb.disconnected': 'Backend not connected',
      'sb.live': 'Live - Yahoo Finance',
      'sb.legacyCcy': 'USD (legacy default, untagged)',
      'sb.fetching': 'Fetching...',
      'sb.fetchFailed': 'Fetch failed: ',
      'sb.holidayNote': 'Note: {n} constituents are in markets that were closed, and were valued at their last close ',
      'nav.archiveRange': 'Price archive {first} to {last}',
      'nav.pickDate': 'Pick a start date first',
      'nav.recomputing': 'Recomputing...',
      'nav.simBanner': 'Simulation: recomputed in full from the price archive using {date} as the start date (whole shares re-allocated, annual rebalances on the new calendar). The actual NAV series is unchanged.',
      'nav.allRange': 'All',
      'nav.perShare': 'NAV / unit',
      'nav.startedAt': 'started at {v}',
      'nav.windowReturn': 'Return ({win})',
      'nav.totalNav': 'Index NAV',
      'nav.units': '200m units',
      'nav.vol': 'Volatility ({win})',
      'nav.volSub': 'annualised daily returns',
      'nav.maxdd': 'Max drawdown',
      'nav.maxddSub': 'peak to trough',
      'nav.days': 'Sessions',
      'nav.simulated': 'simulated',
      'nav.daysOf': '{n} on record',
      'pos.unsaved': 'Unsaved changes (cash / positions)',
      'pos.unsavedN': '{n} unsaved changes (switching filter or currency will not lose them)',
      'pos.badCash': 'Invalid cash amount: ',
      'pos.loadFailed': 'Could not load positions: ',
      'pos.total': 'Total value',
      'pos.totalSub': 'securities + cash',
      'pos.securities': 'Securities',
      'pos.securitiesSub': '{n} positions',
      'pos.cash': 'Cash',
      'pos.cashSub': '{v} of total',
      'pos.pnl': 'Unrealised P/L',
      'pos.trackErr': 'Weight drift',
      'pos.trackErrSub': 'total deviation from target (half absolute sum)',
      'pos.reportingSub': 'portfolio base currency',
      'pos.count': '{rows} rows - {held} held',
      'pos.nothingToSave': 'Nothing to save',
      'pos.invalid': 'Invalid values (negative or not a number): ',
      'pos.saving': 'Saving...',
      'pos.saved': 'Saved {n} - {time}',
      'pos.savedCash': 'Saved (including {n} cash entries) - {time}',
      'pos.saveFailed': 'Save failed (your changes are kept, try again): ',
      'pos.backupStarted': 'Downloading a consistent snapshot (SQLite online backup)',
      'pos.exportFailed': 'Export failed: ',
      'reset.confirm': 'Clear the NAV history and re-seed in {ccy}?\n\nPositions, cash and the price archive are unaffected. This cannot be undone.',
      'reset.working': 'Working...',
      'reset.done': 'Re-seeded in {ccy}',
      'reset.failed': 'Reset failed: ',
      'fund.noBackend': 'Fundamentals (P/E, dividend yield, beta) have no backend connection - showing the static estimates from the methodology',
      'fund.updated': 'Fundamentals (P/E, dividend yield, beta) last updated:',
      'fund.fetchedOn': ' - fetched {d}',
      'fund.coverage': ' - covering {n}/78',
      'fund.stale': ' - quarter {q} not yet updated; waiting for the next automatic fetch, or check manually',
      'fund.flagged': ' - {n} values outside the plausible range were discarded (estimates used instead)',
      'fund.recheck': 'Fetch again',
      'fund.never': 'Fundamentals have never been fetched (this happens automatically on the first day of each quarter, next at {q}). P/E, dividend yield and beta currently show the static estimates from the methodology.',
      'fund.runNow': 'Check now',
      'fund.checking': 'Checking...',
      'fund.fetching': 'Fetching...',
      'fund.checkFailed': 'Check failed: ',
      'import.failed': 'Import failed: ',
      'chart.actual': 'Actual',
      'chart.target': 'Target',
    },

    zh: {
      'doc.title': '巴菲特式全球价值组合 — Buffett-Style Global Value Portfolio',
      'chart.missing': '⚠ 图表库 (Chart.js) 加载失败 —— 所有图表将不显示,但表格、筛选、权重、盈亏、交易所信息等其余功能完全正常。<br>图表库已随程序一起安装,出现本提示通常说明 static/vendor/ 下的文件缺失或损坏,重新安装即可修复。',

      'hero.h1': '巴菲特式<em>全球价值</em>组合',
      'hero.sub': '以巴菲特/Berkshire核心选股逻辑为基准 —— 可理解的商业模式、可持续的经济护城河、诚信且资本配置能力强的管理层、合理的估值安全边际 —— 构建的<b>78支个股</b>组合,覆盖<b>11个Bloomberg板块</b>与<b>12个市场</b>(美/加/日 + 英/法/德/荷/瑞士/比利时/意大利/丹麦/爱尔兰)。科技板块对chokepoint型公司(如ASML、Arm、东京电子)做了适度放宽,但排除纯题材投机标的。',
      'hero.guide': '这个应用是怎么做出来的 →',

      's01.title': '组合概览 Portfolio at a Glance',
      's02.title': '板块 & 地域配置',
      's02.desc': '权重由每支个股的"信心分"(1–6分,反映护城河强度与巴菲特式选股逻辑契合度)驱动生成 —— 非市值加权,亦非价格动量。',
      's02.sector': '行业配置 · Bloomberg Sector',
      's02.geo': '地域配置 · Geography',

      's03.title': '价值地图 Value Map',
      's03.desc': '横轴为估值(P/E,越靠左越便宜)、纵轴为股息率(越靠上收益越高)、气泡大小为组合权重、颜色代表板块 —— 直观呈现组合的"价值 + 收益"分布特征。数据为近似估算,悬停查看明细。',
      's03.legend': '// 气泡越大 = 组合权重越高 · 左上角象限 = 低估值 + 高股息(经典价值区)',

      's04.title': '持仓明细 Holdings',
      's04.desc': '点击任意行展开查看护城河 / 选股逻辑说明。点击表头可排序。',
      's04.ibkrNote': '「交易所」列的 <span class="ibkr-code" style="font-size:9px;padding:1px 5px;">绿色代码</span> 是我核对过 IBKR 官方文档与真实用户 symbol mapping 确认的 IBKR 内部代码(不少和交易所俗名不同,比如法兰克福在 IBKR 里叫 <b>IBIS</b>、东京叫 <b>TSEJ</b> 以区别于多伦多)。标注 <span class="ibkr-code unverified" style="font-size:9px;padding:1px 5px;">橙色"未核实"</span> 的两处(比利时、爱尔兰)是我没能找到可靠来源确认的,下单前请在 IBKR 里用代码或 ISIN 直接搜索核实。这一列仅供参考,不构成下单指令。',

      'filter.allSector': '全部板块 Sector',
      'filter.allRegion': '全部地区 Region',
      'filter.allExchange': '全部交易所 Exchange',
      'filter.search': '搜索代码或公司名称 Search ticker / name...',
      'filter.count': '{n} / {total} 支个股',

      'th.ticker': '代码',
      'th.company': '公司名称',
      'th.region': '地区',
      'th.exchange': '交易所',
      'th.ibkrCode': 'IBKR代码',
      'th.sector': '板块',
      'th.weight': '权重%',
      'th.divYield': '股息率%',
      'th.pe': 'P/E',
      'th.beta': 'Beta',
      'th.score': '信心分',

      's05.title': '模型指数净值 Model Index NAV',
      's05.desc': '规则:初始NAV = 100亿(基准货币,默认CHF)÷ 2亿份 = <b>每份 50.00</b>;后端每日收盘后抓取一次价格并重算NAV;<b>只买整数股</b>,余额按上市地本币留存(7个货币现金池);每年首个交易日按信心分目标权重<b>再平衡一次</b>。这是一条<b>从部署当天开始向前累积</b>的真实净值曲线 —— 不是回测。',

      'rebase.body': '净值序列以 <b id="rbOld">?</b> 播种,但当前配置(<code>.env</code> 里的 <code>BASE_CCY</code>)是 <b id="rbNew">?</b>。两种货币混在一条曲线里没有意义,继续抓取会被拒绝。重置会清空净值历史并以新货币从今天重新播种 —— <b>你的持仓、现金、价格存档都不受影响</b>。',
      'rebase.btn': '重新播种,以',

      'status.label': '状态',
      'status.connecting': '连接中…',
      'status.refresh': '立即抓取一次',
      'status.mock': '⚠ MOCK 数据(测试模式,非真实价格)',

      'offline.h4': '后端未运行',
      'offline.p1': '本页的净值曲线与持仓记录需要本地后端提供数据与持久化存储。启动方式:',
      'offline.p2': '然后用 <code>http://127.0.0.1:8000</code> 打开本页(而不是直接双击 HTML 文件),前两节的组合结构分析在离线状态下依然可用。',
      'offline.p3': '首次启动后点一次「立即抓取一次」即可播种指数,此后后端每天 <code>FETCH_HOUR</code>(默认18点)自动抓取一次。数据存在 <code>portfolio.db</code>(SQLite 单文件)。',

      'sim.label': '假设起始日',
      'sim.run': '重算',
      'sim.clear': '回到实际',
      'nav.chartTitle': '净值曲线 · NAV per Share',

      'ticker.pauseHint': '鼠标悬停或聚焦可暂停滚动',
      'hold.title': '指数的实际持仓',
      'hold.desc': '上面那条净值曲线,就是由这张表算出来的。指数<b>只买整股</b>,每个持仓都会剩下一点零头,这些零头以该股本币的形式留作现金 —— 持仓加上这些现金,按最新收盘价计价,<i>就是</i>净值本身。这里显示的是模型指数,不是你自己的持仓。',
      'hold.asOf': '按 {d} 收盘价计价',
      'hold.thShares': '持股数',
      'hold.thPrice': '价格',
      'hold.thValue': '市值',
      'hold.thActual': '权重',
      'hold.thTarget': '目标',
      'hold.cashTitle': '剩余现金',
      'hold.thCcy': '币种',
      'hold.thAmount': '金额',
      'hold.equity': '证券',
      'hold.cash': '现金',
      'hold.nav': '净值合计',
      'hold.perShare': '每份',
      'hold.count': '78 支中持有 {n} 支',
      'hold.cashPct': '占净值 {v}',
      'hold.notSeeded': '指数尚未建仓,暂无持仓可显示。抓取一次行情后,它会按目标权重买入。',
      'hold.unpriced': '⚠ 有 {n} 个持仓在该收盘日没有价格,在此按零计价:{t}',
      'hold.rounding': '表中数字为显示用四舍五入,合计按完整精度计算。',

      's06.title': '我的持仓 My Positions',
      's06.desc': '填入你<b>实际持有的股数</b>与<b>平均成本(每股,以该股上市地本币计)</b> —— 就是券商账户里显示的那两个数字。系统会算出浮盈浮亏、你的<b>实际权重</b>、与目标权重的<b>偏离度</b>,以及补齐到目标权重<b>还差多少股</b>。定投过程中每次加仓后更新一下,就能看到自己的组合怎样一步步向目标结构靠拢。',

      'warn.gapTitle': '⚠ 关于「还差多少股」这一列',
      'warn.gapBody': '该列是<b>纯数学计算</b>:按你当前组合总市值 × 目标权重,再减去你已持有的市值,换算成股数。它<b>不考虑</b>你的现金、税务处理(TFSA/RRSP/非注册账户的差异)、交易成本、汇率成本、也不判断当前价格是否合适。<b>它是一个对照工具,不是买入建议。</b>实际操作请自行判断,必要时咨询持牌顾问。',

      'cash.label': '现金余额 CASH · 按币种填写(未买成股票的部分)',
      'btn.save': '保存持仓',
      'btn.export': '导出 JSON',
      'btn.backup': '备份数据库',
      'btn.import': '导入数据库…',
      'btn.importTitle': '从文件导入 portfolio.db —— 会先自动备份当前数据',
      'chk.onlyHeld': '只看已持有',
      'chk.cashGap': '差额计入现金',
      'pos.search': '搜索代码或公司名称...',
      'pos.reportCcy': '报告货币',

      'posTh.shares': '持股数',
      'posTh.avgCost': '平均成本',
      'posTh.price': '现价',
      'posTh.local': '本币',
      'posTh.marketValue': '市值',
      'posTh.pnl': '浮盈亏',
      'posTh.actualWeight': '实际权重',
      'posTh.targetWeight': '目标权重',
      'posTh.drift': '偏离',
      'posTh.gapShares': '差额股数',

      'drift.title': '板块层面 · 实际权重 vs 目标权重',

      'disc.title': 'Disclaimer 免责声明',
      'disc.body': '本页面所有股息率 / P/E / Beta / 预期回报等数据均为基于公开认知的近似估算(约2026年年中量级),用于组合结构设计与教学演示目的,并非实时行情,不构成投资建议。实际配置前请以权威数据源(如Bloomberg终端)核实最新数据,并咨询持牌财务顾问。过往表现或历史区间不代表未来收益,投资股票存在本金损失的风险。',

      'kpi.holdings': '持仓数量 Holdings',
      'kpi.divYield': '加权股息率 Div. Yield',
      'kpi.pe': '调和加权 P/E',
      'kpi.beta': '加权 Beta',
      'kpi.capm': 'CAPM 预期回报',
      'kpi.effN': '有效持仓数',
      'kpi.weightSum': '权重合计 {v}',
      'kpi.liveOf': '{live}/{n} 支实时',
      'kpi.peStatic': '较简单加权更严谨口径(静态估算)',
      'kpi.dyEstimate': '按权重加权平均(近似估算)',
      'kpi.betaEstimate': '系统性风险代理指标(近似估算)',
      'kpi.mixed': ',混合口径仅供参考',

      'tag.live': '实时',
      'tag.estimate': '估算',
      'tag.unverified': '未核实',
      'tag.ibkrVerified': 'IBKR交易所代码(已核实)',
      'tag.ibkrUnverified': '未能核实IBKR专用代码,请在IBKR内用代码或ISIN搜索确认',
      'axis.divYield': '股息率 %',
      'lang.switch': 'EN',
      'kpi.peLive': '{live}/{n} 支实时(静态{tr}/动态{fw})',
      'kpi.dyLive': '{live}/{n} 支为实时数据',
      'kpi.betaLive': '{live}/{n} 支为实时数据',
      'kpi.capmSub': 'rf 4.6% + beta x ERP 4.5%',
      'vm.tag': ' P/E {pe}x{peTag} · 股息率 {dy}%{dyTag} · 权重 {w}%',
      'vm.livePe': ' · 实时({type}PE)',
      'vm.est': ' · 估算',
      'vm.live': ' · 实时',
      'live.title': '实时数据({q} · 拉取于 {d})',
      'live.titlePe': '实时{type}PE({q} · 拉取于 {d})',
      'sb.latestPrice': '最新价格日',
      'sb.inception': '起始日',
      'sb.notSeeded': '未播种',
      'sb.navPoints': '净值点数',
      'sb.dailyFetch': '每日抓取',
      'sb.archived': '已存档价格',
      'sb.rows': '{rows} 行 / {days} 天',
      'sb.csv': '下载 CSV',
      'sb.disconnected': '✗ 后端未连接',
      'sb.live': '● 实时 · Yahoo Finance',
      'sb.legacyCcy': 'USD(旧版本隐式默认,未标记)',
      'sb.fetching': '抓取中…',
      'sb.fetchFailed': '✗ 抓取失败: ',
      'sb.holidayNote': '注意: {n} 支成分股所在市场休市,已按其最近收盘价估值 ',
      'nav.archiveRange': '价格存档 {first} → {last}',
      'nav.pickDate': '请先选一个起始日期',
      'nav.recomputing': '重算中…',
      'nav.simBanner': '模拟模式:以 {date} 为起始日,用价格存档完整重算(整数股重新分配、年度再平衡按新日历)。实际净值序列未被改动。',
      'nav.allRange': '全部区间',
      'nav.perShare': '净值/份 NAV/Share',
      'nav.startedAt': '起始 {v}',
      'nav.windowReturn': '区间收益 ({win})',
      'nav.totalNav': '指数总市值 NAV',
      'nav.units': '2亿份',
      'nav.vol': '区间波动 ({win})',
      'nav.volSub': '日收益年化',
      'nav.maxdd': '最大回撤 Max DD',
      'nav.maxddSub': '峰值到谷底',
      'nav.days': '区间天数',
      'nav.simulated': '模拟重算',
      'nav.daysOf': '共 {n} 天记录',
      'pos.unsaved': '有未保存的修改(现金/持仓)',
      'pos.unsavedN': '{n} 项未保存的修改(切换筛选或货币不会丢失)',
      'pos.badCash': '现金金额无效: ',
      'pos.loadFailed': '✗ 无法读取持仓: ',
      'pos.total': '总资产 Total Value',
      'pos.totalSub': '证券 + 现金',
      'pos.securities': '证券市值 Securities',
      'pos.securitiesSub': '{n} 个持仓',
      'pos.cash': '现金 Cash',
      'pos.cashSub': '占总资产 {v}',
      'pos.pnl': '浮动盈亏 Unrealized P/L',
      'pos.trackErr': '权重偏离度',
      'pos.trackErrSub': '与目标权重的总偏离(半绝对值和)',
      'pos.reportingSub': '组合基准货币',
      'pos.count': '{rows} 行 · {held} 个已持有',
      'pos.nothingToSave': '没有需要保存的修改',
      'pos.invalid': '✗ 存在无效数值(负数或非数字): ',
      'pos.saving': '保存中…',
      'pos.saved': '✓ 已保存 {n} 项 · {time}',
      'pos.savedCash': '✓ 已保存(含 {n} 项现金)· {time}',
      'pos.saveFailed': '✗ 保存失败(修改仍保留,可重试): ',
      'pos.backupStarted': '✓ 正在下载一致性快照(SQLite online backup)',
      'pos.exportFailed': '✗ 导出失败: ',
      'reset.confirm': '确认清空净值历史并以 {ccy} 重新播种?\n\n持仓、现金、价格存档不会受影响,此操作不可撤销。',
      'reset.working': '处理中…',
      'reset.done': '✓ 已以 {ccy} 重新播种',
      'reset.failed': '重置失败: ',
      'fund.noBackend': '⏳ 基本面数据(P/E · 股息率 · Beta)尚未连接后端 —— 当前显示方法论中的静态估算值',
      'fund.updated': '基本面数据(P/E · 股息率 · Beta)最近更新:',
      'fund.fetchedOn': ' · 拉取于 {d}',
      'fund.coverage': ' · 覆盖 {n}/78',
      'fund.stale': ' · 当前季度 {q} 尚未更新,等下次自动抓取或手动检查',
      'fund.flagged': ' · {n} 项数值超出合理范围已自动剔除(改用估算值)',
      'fund.recheck': '手动重新拉取',
      'fund.never': '⏳ 尚未拉取过基本面数据(每季度首日自动抓取一次,即将到 {q} 季度更新)。当前 P/E / 股息率 / Beta 显示的是方法论中的静态估算值。',
      'fund.runNow': '立即检查一次',
      'fund.checking': '检查中…',
      'fund.fetching': '拉取中…',
      'fund.checkFailed': '✗ 检查失败: ',
      'import.failed': '导入失败: ',
      'chart.actual': '实际 Actual',
      'chart.target': '目标 Target',
    },
  };

  const LANGS = Object.keys(STRINGS);
  const DEFAULT = 'en';

  /**
   * Look up a string, substituting {placeholders} from `vars`.
   *
   * Returns the key itself when nothing is found. A visible `kpi.holdings` in
   * the interface is an obvious bug report; an empty space is one nobody
   * notices until a user asks what the blank column means.
   */
  function t(key, lang, vars) {
    const table = STRINGS[lang] || STRINGS[DEFAULT];
    let s = table[key];
    if (s === undefined) s = (STRINGS[DEFAULT][key] !== undefined) ? STRINGS[DEFAULT][key] : key;
    if (vars) {
      for (const k in vars) s = s.split('{' + k + '}').join(vars[k]);
    }
    return s;
  }

  /** Normalise anything into a supported language code. */
  function resolve(lang) {
    if (LANGS.indexOf(lang) !== -1) return lang;
    // "zh-CN", "zh-Hans" and friends all mean Chinese here.
    if (typeof lang === 'string' && lang.toLowerCase().indexOf('zh') === 0) return 'zh';
    return DEFAULT;
  }

  return { STRINGS, LANGS, DEFAULT, t, resolve };
});
