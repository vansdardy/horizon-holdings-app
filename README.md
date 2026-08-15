# 巴菲特式全球价值组合 — 本地净值服务

78支个股的模型指数 + 个人持仓追踪器。纯本地部署,数据存在一个 SQLite 文件里,不依赖任何云服务。

---

## 两种用法,先确认你是哪一种

**只想用这个程序** —— 去 [Releases](https://github.com/vansdardy/horizon-holdings-app/releases)
下载 `Horizon Holdings Setup x.y.z.exe`,双击安装。机器上**不需要**装 Python 或 Node。

> ⚠ 安装包**没有做代码签名**:Windows 会弹 SmartScreen 警告,需要点「更多信息 → 仍要运行」;
> 如果你的机器开启了 **Smart App Control(强制)**,会直接拒绝运行 —— 详见文末「桌面版」一节。

**想读代码 / 自己改 / 自己构建** —— 往下看。需要 Python 3.10+、Node.js,以及大约二十分钟:

```bash
git clone https://github.com/vansdardy/horizon-holdings-app.git
cd horizon-holdings-app
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python server.py                                     # 只跑后端 + 网页版
```

再往上做成桌面程序(需要 Node):

```bash
pip install pyinstaller
python -m PyInstaller backend.spec --noconfirm --distpath build/backend --workpath build/pyinstaller
cd desktop && npm install && npm start                # 开发模式运行
npm run dist                                          # 生成安装包
```

构建过程、设计取舍、发布流程为什么是这样,写在 `docs/building-this-app.html`(应用内也能直接看)。

---

## 本包包含的文件

```
portfolio_app/
├── README.md            本文件
├── requirements.txt     Python 依赖清单(pip install -r 用的就是它)
├── .env.example         配置模板 —— 复制为 .env 后修改(可选)
├── config.py            配置加载(读 .env、校验取值、打印生效配置)
├── server.py            FastAPI 服务 + 每日调度器 + 全部 API 端点
├── db.py                SQLite 持久化层(建表、读写、一致性备份)
├── index_engine.py      指数机制(播种、整数股、年度再平衡、估值)
├── marketdata.py        行情抓取(Yahoo Finance / mock 测试模式)
├── universe.py          78支成分股定义、目标权重、Yahoo 代码映射
├── backend.spec         PyInstaller 打包配置(桌面版用,见文末)
├── static/
│   ├── index.html       前端页面(单文件,内嵌数据与全部逻辑)
│   └── vendor/          图表库与字体的本地副本(不再依赖 CDN)
└── desktop/             Electron 桌面版外壳(开发中,见文末)
    ├── main.js
    └── package.json
```

> **注意 `index.html` 的位置**:逐个下载文件时容易全部平铺到一个文件夹里。
> 放进 `static\` 子文件夹是推荐做法,但直接和 `server.py` 平铺也能正常工作 —— 两个位置服务都会查找。
> 若两处都没有,打开页面会显示一段说明(而不是报错),API 仍然可用。

运行后会**自动生成**(不在本包内):`portfolio.db`(数据库)、`portfolio.db-wal` / `-shm`(WAL 文件)、`.venv/`(虚拟环境)、`.env`(你自己从模板复制的配置,若使用)。

> 若 `requirements.txt` 缺失,依赖清单为:`fastapi>=0.110`、`uvicorn[standard]>=0.27`、`pydantic>=2.0`、`yfinance>=0.2.40`,
> 也可直接 `pip install fastapi "uvicorn[standard]" pydantic yfinance`。

---

## 环境要求

- **Python 3.10 或更高**(代码使用 `list[X]` 泛型标注语法)
- 可访问 Yahoo Finance 的网络连接(抓取行情用)
- **页面本身不需要联网**:图表库 Chart.js 与三套字体都已放在 `static/vendor/` 里随程序分发,
  断网也能完整渲染。(早期版本从 CDN 加载,已改为本地副本 —— 桌面版必须能离线工作。)
  万一 `static/vendor/` 下的文件缺失或损坏,页面顶部会给出提示,
  **表格与全部数字功能不受影响,仅图表不显示**。

检查版本:

```bash
python3 --version     # 需要 >= 3.10
```

## 快速开始

```bash
cd portfolio_app
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 server.py
```

> 用 `python3` 而不是 `python` —— 多数 macOS/Linux 系统上 `python` 不存在或指向 Python 2。
> 建议用虚拟环境(venv),避免污染系统 Python;不用 venv 时某些系统需要 `pip install --break-system-packages`。

看到这行说明启动成功:

```
[startup] scheduler running (daily fetch at 18:00 local)
[startup] data source: Yahoo Finance
[startup] database: /你的路径/portfolio_app/portfolio.db
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

若 `data source` 显示 `MOCK — NOT REAL PRICES`,说明 `MARKETDATA_MOCK=1` 还开着,数据是假的。

**首次安装建议先验证行情代码**(交易所会改代码,如罗氏已从 `ROG.SW` 迁至 `RO.SW`):

```bash
curl http://127.0.0.1:8000/api/check_symbols
```

`healthy: true` 表示78支个股与6组汇率全部可取。若 `unresolved` 非空,说明该代码已失效,
需要在 `universe.py` 里更新它的 `yahoo=` 或往 `alts=[...]` 里加备选代码。

然后打开 **http://127.0.0.1:8000**,点一次「立即抓取一次」播种指数。

> 页面也支持直接双击 `static/index.html` 打开(已配置 CORS 放行 `file://` 与 localhost),
> 但仍**推荐**用 `http://127.0.0.1:8000`,路径更少出问题。

### 停止服务

前台运行时按 `Ctrl+C`。

### 让它长期在后台跑(重要)

README 承诺「每天自动抓取一次」,但**关掉终端窗口进程就没了**。要真正每天跑,选一种:

**方式一 · 简单后台(重启电脑后需重新执行)**

```bash
nohup python3 server.py > server.log 2>&1 &
echo $! > server.pid          # 记下进程号
kill $(cat server.pid)        # 需要停止时
```

**方式二 · macOS 开机自启(launchd)**

创建 `~/Library/LaunchAgents/com.local.portfolio.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
  <key>Label</key><string>com.local.portfolio</string>
  <key>ProgramArguments</key>
  <array>
    <string>/完整路径/portfolio_app/.venv/bin/python3</string>
    <string>/完整路径/portfolio_app/server.py</string>
  </array>
  <key>WorkingDirectory</key><string>/完整路径/portfolio_app</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.local.portfolio.plist
```

**方式三 · Linux 开机自启(systemd user service)**

创建 `~/.config/systemd/user/portfolio.service`:

```ini
[Unit]
Description=Portfolio NAV Service
[Service]
WorkingDirectory=/完整路径/portfolio_app
ExecStart=/完整路径/portfolio_app/.venv/bin/python3 server.py
Restart=always
[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now portfolio.service
loginctl enable-linger $USER     # 未登录时也保持运行
```

**方式四 · Windows**:用「任务计划程序」创建登录时触发的任务,操作设为
`完整路径\.venv\Scripts\python.exe 完整路径\server.py`。

### 笔记本休眠 / 关机怎么办?

不用担心漏数据。每次抓取都会取回**最近约10个交易日**的窗口,
启动时会自动把缺失日期补齐(见「断点自愈」一节)。断网超过10个交易日才会产生真正的空洞。

### 配置项在哪里改?

三种方式,**优先级从高到低**:

**方式一 · `.env` 文件(推荐,重启后依然有效)**

包里带了 `.env.example`,复制成 `.env` 再改即可:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
notepad .env
```

```bash
# macOS / Linux
cp .env.example .env
```

`.env` 就放在 `server.py` 旁边,内容是每行一个 `KEY=VALUE`,`#` 开头是注释:

```
PORT=8000
FETCH_HOUR=18
MARKETDATA_MOCK=0
```

**改完要重启服务才生效。** 启动时终端会打印实际生效的配置和它的来源:

```
[config] .env: T:\Personal\Trading\buffet_style_holdings\.env
[config]   PORT = 8000   (.env file)
[config]   FETCH_HOUR = 20   (.env file)
[config]   FETCH_LOOKBACK = 10d   (default)
[config]   MARKETDATA_MOCK = False   (default)
[config]   PORTFOLIO_DB = ...\portfolio.db   (default)
```

也可以随时访问 `/api/status` 看 `config` 字段确认。

**方式二 · 临时环境变量(只对当前终端窗口有效)**

```powershell
# Windows PowerShell —— 关掉窗口就失效
$env:PORT="8001"; python server.py
```

```cmd
REM Windows CMD
set PORT=8001 && python server.py
```

```bash
# macOS / Linux
PORT=8001 python3 server.py
```

适合临时试一下。**注意:虚拟环境(venv)不会保存这些变量**,所以别指望激活 venv 就自动带上——这正是 `.env` 存在的原因。

**方式三 · 什么都不设**

全部使用默认值即可正常运行,`.env` 不是必需的。

> 配置写错会在启动时给出明确提示并退出(例如 `FETCH_HOUR=99 is out of range; expected 0–23`),不会跑到一半才崩。

### 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `PORT` | `8000` | 服务端口 |
| `FETCH_HOUR` | `18` | 每日自动抓取的**本地**小时(0-23)。建议设在你关注的最后一个市场收盘之后;多伦多时区下 18:00 已晚于美股收盘 |
| `PORTFOLIO_DB` | `./portfolio.db` | 数据库路径 |
| `FETCH_LOOKBACK` | `10d` | 每次抓取回溯的窗口,用于补齐断点 |
| `BASE_CCY` | `CHF` | 模型指数的**基准货币**。可选 `CHF USD EUR GBP CAD JPY DKK`。播种后不可中途更改,详见下方 |
| `MARKETDATA_MOCK` | `0` | 设为 `1` 使用**假数据**测试管道,页面会显示红色 MOCK 警告 |

---

## 两个功能

### 1. 模型指数净值(第05节)

- 初始 NAV = 100亿(**基准货币**,默认 CHF)÷ 2亿份 = **每份 50.00**
  - 之所以默认瑞郎:这七种货币里它长期波动最小,用它计价可以让净值曲线更多反映企业本身而不是汇率噪音
  - 内部运算仍以美元为计价基准(行情源的汇率对都是兑美元报价的),最终换算成基准货币输出 —— 这只是数值路径,不影响结果
  - **播种后不能中途改基准货币**:换了就等于把两段不可比的序列拼在一起。真要改就改 `.env` 后重启,再 `POST /api/reset_index?confirm=true` 重新播种;**持仓与价格存档不受影响**
- 每日收盘后抓一次价格,重算 NAV 并入库
- **只买整数股**,余额按上市地本币留存(USD/CAD/GBP/EUR/CHF/JPY/DKK 七个现金池)
- 每年首个抓取日按信心分目标权重**再平衡一次**
- 曲线**从你部署当天开始向前累积** —— 这不是回测,没有前视偏差

**区间与假设起始日**

- 区间按钮:`ALL / 1M / 3M / 6M / YTD / 1Y / 5Y / 10Y`。区间收益、波动、最大回撤都按**所选区间**重算,而不是照搬全期数字;数据不足所选长度时自动退回全部区间
- 「假设起始日」:选一个日期后点「重算」,会用**价格存档完整重跑一遍指数** —— 在该日按当时价格重新分配整数股、年度再平衡按新日历推进。这和把现有曲线除以某天的净值做归一化**不是一回事**:整数股取整和再平衡时点都依赖于真实起点,两种算法结果会有差异,所以这里做的是真重算
- 模拟结果**只在页面上呈现,不写入数据库**,实际净值序列不受影响(曲线会变成青色并显示提示条,点「回到实际」即可退出)
- 可选日期受限于价格存档的覆盖范围,存档跨度会随着服务每天运行而变长

### 2. 个人持仓追踪(第06节)

在表格里填入**实际持股数**和**平均成本(每股,本币计)**,即券商账户上的两个数字。系统计算:

- 浮动盈亏(个股本币 + 你选定的报告货币)
- **报告货币可切换**:CHF / USD / EUR / GBP / CAD / JPY / DKK 全部支持,默认取基准货币
- **持股数支持小数**(券商的碎股/零股投资),与模型指数「只买整数股」互不影响 —— 后者是指数编制规则,前者是你的真实持仓
- 你的**实际权重** vs **目标权重**,以及偏离度
- **差额股数** —— 补齐到目标权重还差多少股
- 板块层面的实际 vs 目标对比图
- **顶部滚动条**:每支个股显示当前股价(按其本币,自动配正确货币符号)与涨跌幅(绿涨红跌),数据来自价格存档里最近两个交易日的收盘价对比,不额外调用任何接口。刚部署、价格存档还只有一天时只显示股价、不显示涨跌幅;后端完全没连上时退回显示权重(旧版行为)
- **现金余额**:按币种分别填写(CHF/USD/EUR/GBP/CAD/JPY/DKK)。现金很少能正好买成整数股,真实组合几乎总有余额
  - 「总资产」= 证券市值 + 现金;KPI 会显示现金占比
  - 「差额股数」默认只按**证券市值**计算(这样才和目标权重同口径)。勾选「差额计入现金」后改为按**证券+现金**计算,回答的是「把现金也投进去的话每支该买多少」

回车或点「保存持仓」即写入数据库。未保存的修改在切换筛选/货币时会保留,**只有服务器确认写入后才清除**。所有修改记录在 `user_position_log` 表里。

> **「差额股数」是纯数学计算**:当前组合总市值 × 目标权重 − 已持有市值,换算成股数。它不考虑你的现金、税务账户类型(TFSA/RRSP/非注册)、交易成本、汇率成本,也不判断当前价格是否合适。**是对照工具,不是买入建议。**

---

## P/E · 股息率 · Beta:每季度更新一次

页面顶部「组合概览」和持仓表里的这三项,**不随每日抓价更新**——它们走的是完全独立的一条管道,每个日历季度首日(1/1、4/1、7/1、10/1)才抓一次,原因两个:

1. 这几个基本面数字本身变化很慢,没必要每天拉
2. Yahoo 提供这些字段的接口(`yf.Ticker(t).info`)和批量拉收盘价的接口不是一回事——**每支个股要单独发一次请求**,78支跑一遍比拉价格慢得多,非美股(尤其欧洲、日本)也更容易缺字段或对不上

调度器每天检查一次是否进入新季度,真正发起请求平均一年只有4次。页面上每个数字旁边如果有个小圆点(●),说明这是当季实时拉取的;悬停能看到具体是哪个季度、哪天拉的。没有圆点的,用的是方法论里那份静态估算值(还没轮到抓取,或者该股票在 Yahoo 那边缺数据)。

首次部署时基本面表是空的,不用等到下个季度——组合概览上方会出现一个「立即检查一次」按钮,点一下就能拉到当季数据。这个按钮同样遵循季度闸门(不会因为你多点了几次就重复发78次请求);测试或想强制刷新的话用 `POST /api/refresh_fundamentals?force=true`。

### 数据合理性校验

参考了 yfinance 官方 API 文档(ranaroussi.github.io/yfinance)后重写了这部分抓取逻辑。文档本身对 `Ticker.info` 里每个字段的单位没有详细说明(连 yfinance 维护者自己都在 GitHub 上承认这部分文档是自动生成的、比较薄),社区长期反映 `dividendYield` 这个预计算字段的单位不统一——不同股票、不同时期可能是小数(0.024 表示 2.4%)也可能是已经乘过100的数字(2.4 表示 2.4%),这个歧义没法单靠数值本身可靠判断,原始值 `0.14` 到底是"0.14%"还是"14%"是猜不出来的。

所以股息率现在**优先从两个含义明确的原始字段直接计算**:`dividendRate`(每股年度现金分红,一个具体货币金额)÷ 当前股价,两者是同一种货币单位,相除天然没有百分比/小数的歧义。只有当 `dividendRate` 或股价缺失时,才退回旧的 `dividendYield` 字段猜测换算。P/E 同理:优先用 `trailingPE`/`forwardPE`,缺失时用股价÷每股盈利现算兜底。

不管走哪条路径,**P/E、股息率、Beta 三项最终都设了合理区间**作为最后一道防线,超出范围的字段会被丢弃、自动改用方法论里的静态估算值。超出范围的会记录在 `last_fundamentals_flagged`,页面横幅如果这次抓取有剔除项会提示"N项数值超出合理范围已自动剔除"。

### 两个曾经的真实 bug(已修复)

**P/E 合理区间原来设的是 0-150,对像 Arm Holdings 这种当期盈利很薄、但市场按未来成长定价的标的太窄了**——这类公司真实的静态市盈率(基于过去12个月实际盈利)经常在200-300倍以上,不是数据错误,是市场真的这么定价。原来的区间会把这种真实的高估值当成"离谱数据"拒绝掉,静默换回很久以前写的静态估算值——**但界面上依然显示着"实时"标记**,相当于把一个过时的猜测数字包装成"已核实"展示给你。已把上限放宽到 500(仍然会拦住真正的数据错误,比如盈利为负导致的异常市盈率),并且把"实时"标记的判定逻辑从"这支股票这次抓取是否成功"改成了"这一个具体字段是否真的通过了合理性校验"——如果 P/E 因为超出范围被剔除、退回静态估算,现在只有 P/E 这一列不显示实时标记,不会连累同一行里股息率、Beta 这些真正抓到的字段,也不会让退回的静态值冒充实时数据。

**P/E 还分静态(基于过去12个月实际盈利)和动态(基于分析师预期盈利)两种口径,两者对高估值成长股可能差出几倍。**现在会记录并展示抓到的是哪一种(静态 `trailingPE` 优先,没有则退到动态 `forwardPE`,再没有则用股价÷每股盈利现算),鼠标悬停在实时标记上能看到具体是"静态"还是"动态"——不会再出现说不清楚这个数字到底是哪个口径的情况。

### 抓取一次之后还能再拉吗?

首次拉取成功后,「立即检查一次」那个大按钮会消失,换成一句更新状态的说明文字。但说明文字后面始终跟着一个小的「手动重新拉取」链接——这是特意保留的:如果某次抓取的数据不理想(比如遇到上面这类被剔除的情况),不用干等到下个季度,随时点一下就能强制重新拉取,不受季度闸门限制。

## 每日价格是否落盘?是。

每次抓取都会把**全部 78 支个股 + 6 组汇率的收盘价**写入 `portfolio.db` 的 `prices` / `fx` 表,按日期累积,永不覆盖历史。跑得越久,你手上就攒下一份越完整的价格档案(约每天 78 行,一年约 2 万行,数据库仍然只有几 MB)。

**写盘发生在估值之前** —— 即使 NAV 计算出错,当天的原始行情也已经入库了。

### 断点自愈 Backfill

每次抓取取回的是一个**多日窗口**(默认约10个交易日)而非单日快照。窗口内任何**尚无净值记录**的交易日,都会按时间顺序补算并入库。因此:

- 笔记本休眠三天 → 下次启动自动补齐这三天
- 手动点一次抓取 → 也会顺带补齐此前的空缺
- 只有断线超过窗口长度,才会留下真正无法恢复的空洞(可调大 `FETCH_LOOKBACK`)

补算使用**该交易日当时**的价格(按 as-of 前向填充),不会用今天的价格去回填过去。

### 关于休市日的处理

**每条报价按它实际成交的那个交易日存储,而不是统一盖上"今天"的戳。**

各交易所收盘时间与假期都不同。如果统一盖今天的日期,休市市场的旧报价会被反复写成"新的一天",凭空捏造出根本不存在的价格历史。

现在的行为:休市当天该市场**不产生新行**,但 NAV 仍用它的**最近一次收盘价**照常估值全部 78 支(指数编制的标准做法)。抓取后如有休市市场,页面会提示是哪几支。

### 缺价保护

若任何**已持仓**成分股当日取不到价格,系统会**拒绝写入当天净值**并报出是哪几支。
把持仓按零估值会静默压低 NAV(实测单支缺价即造成 -2.17% 的假跌),对一条要跑 20-30 年的记录而言,
**缺一天远好过留一个错数**。修复数据源后重新抓取即可补上。

---

## 备份(重要:不要用 cp)

数据库运行在 **WAL 模式**,已提交但尚未 checkpoint 的事务存在 `portfolio.db-wal` 里。
服务运行期间直接 `cp portfolio.db` **可能丢失最近写入的数据**(实测可复现)。

正确做法,任选其一:

```bash
# 1. 通过 API(服务运行中,推荐)
curl -X POST http://127.0.0.1:8000/api/backup

# 2. 浏览器下载 —— 页面上的「备份数据库」按钮,或直接访问
#    http://127.0.0.1:8000/api/backup.db

# 3. 用 sqlite3 命令行(服务运行中也安全;部分系统需先安装 sqlite3)
sqlite3 portfolio.db ".backup 'portfolio_backup_$(date +%F).db'"

# 4. 服务已停止时,必须连 -wal 一起复制
cp portfolio.db portfolio.db-wal portfolio.db-shm /备份目录/   2>/dev/null
```

> 不指定 `?dest=` 时,备份文件生成在**数据库所在的那个文件夹**里。
> 从源码运行时那就是本文件夹;桌面版则在它自己的用户数据目录下(托盘菜单里有「打开数据文件夹」)。

页面上的「导出 JSON」可另外拿走持仓 + 净值 + 价格 + 汇率的全量明细 —— 不存在数据锁定。

---

## 数据源

Yahoo Finance,经 `yfinance` 库,免费无需 API key。每次调用一个批量请求拿全部 78 支个股 + 6 组汇率。

汇率用 `CADUSD=X` 这类代码,返回值直接就是「1单位该货币值多少美元」,正好是引擎需要的方向。

### 关于实盘数据路径:已于 2026-08-14 验证通过

**这一节早期曾警告 `fetch_live()` 未经真实联网验证** —— 生成这套代码的环境访问不了
Yahoo Finance,当时只跑通了 `MARKETDATA_MOCK=1` 的完整回路与失败路径,成功路径没验证过。

现在验证过了。2026-08-14 在打包后的独立可执行文件里实测:

- `/api/check_symbols` 返回 `healthy: true` —— **78支个股与6组汇率全部可取**,
  且没有一支需要退到备选代码(`using_fallback` 为空)
- 一次真实的 `POST /api/refresh?window=10` 落盘 **789 行**行情,`n_priced` = 78/78,
  指数按 50.00 CHF 正常播种,无跳过的交易日

顺带确认了一个容易踩的坑:`yfinance` 与它底层的 `curl_cffi`(带编译好的 libcurl 和 CA 证书)
在 PyInstaller 冻结之后依然工作正常 —— 这类库打包后失灵是很常见的问题。

首次实盘运行时仍建议检查(尤其隔了很久之后,交易所可能改代码):

1. `/api/status` 的 `latest_price_date` 是否为最近交易日
2. `n_priced` 是否等于 78(不等说明有代码没取到价)
3. 抽查几支个股价格量级是否合理(尤其日股以日元计、瑞郎、丹麦克朗)
4. `/api/archive` 的 `price_rows` 是否随天数增长

Yahoo 的非官方接口偶尔改动或限流。若失败,`/api/status` 的 `last_fetch_error` 会保留错误信息。

### 代码映射注意

- `BRK.B` → Yahoo 写作 `BRK-B`
- `ASML` 用阿姆斯特丹的 `ASML.AS`(欧元计价);若改用纳斯达克的 `ASML` 则是美元,**两者不可混用**
- `ARM` 是英国公司但以 ADS 在纳斯达克**以美元**交易,已按 USD 处理

---

## API

| 端点 | 说明 |
|---|---|
| `GET /api/status` | 数据源、最新价格日、净值点数、调度状态、错误信息 |
| `GET /api/check_symbols` | **首次安装先跑这个** —— 逐一探测78支个股+6组汇率代码是否有效 |
| `POST /api/refresh` | 手动抓取一次。`?window=N` 指定回溯天数;`?day_offset=N` **仅** mock 模式可用 |
| `GET /api/nav` | 净值历史 + 统计指标 |
| `GET /api/universe` | 78支成分股与目标权重 |
| `GET /api/positions` | 持仓 + 现价 + 权重偏离 + 差额股数 |
| `POST /api/positions` | 保存持仓 |
| `GET /api/prices` | 最新价格与汇率快照 |
| `GET /api/archive` | 价格存档统计(行数、天数、起止日期、文件大小) |
| `GET /api/fundamentals` | P/E、股息率、Beta 的最近一次季度快照,附带 `quarter` 与 `as_of` 拉取日期 |
| `POST /api/refresh_fundamentals` | 手动检查一次基本面数据;不加 `?force=true` 时遵循季度闸门,同季度内重复调用会被跳过 |
| `GET /api/price_history` | 价格序列,可加 `?ticker=` `?start=` `?end=` `?limit=` |
| `GET /api/price_history.csv` | 整个存档导出为长格式 CSV |
| `GET /api/export` | 持仓 + 净值 + 价格 + 汇率的完整 JSON |
| `POST /api/cash` | 保存各币种现金余额 |
| `GET /api/nav/simulate` | 以其他起始日重算指数(`?inception=YYYY-MM-DD`),只读不写 |
| `POST /api/reset_index` | 清空净值序列重新播种(改基准货币后用),需 `?confirm=true`;不动持仓与价格存档 |
| `POST /api/backup` | 生成一致性数据库快照(可选 `?dest=路径`) |
| `GET /api/backup.db` | 直接下载一致性快照 |

交互式接口文档: **http://127.0.0.1:8000/docs**

---

## 故障排查

| 症状 | 原因与处理 |
|---|---|
| 页面显示「后端未连接」 | 服务没起来,或端口被占用。看终端日志;换端口 `PORT=8001 python3 server.py` |
| 状态栏显示红色 MOCK | 环境变量 `MARKETDATA_MOCK=1` 还开着,数据是假的。去掉它重启 |
| 抓取返回 409 | 有已持仓成分股缺价,当日净值被**有意**拒写。看错误信息里列出的代码 |
| 抓取返回 500 | 网络或 Yahoo 接口问题,详见 `/api/status` 的 `last_fetch_error` |
| `day_offset` 返回 400 | 该参数只在 mock 模式可用,真实历史不能时移 |
| 净值曲线只有一个点 | 正常。曲线从部署当天起累积,需要时间 |
| 净值有断档 | 停机超过 `FETCH_LOOKBACK` 窗口。调大该值后重新抓取 |
| `possibly delisted; no price data found` | 该 Yahoo 代码取不到数据。若紧随其后出现 `daily update done`,说明抓取整体是**成功**的。抓取分两阶段:先只请求主代码,只有失败的才会在第二次请求里试备选代码——所以这行警告出现时,日志里同时会有 `trying fallbacks:` 或 `using fallback` 说明发生了什么。确认现状请跑 `/api/check_symbols`。若某支彻底取不到,会被自动剔除并按剩余成分股重新归一化,不影响 NAV 正确性 |
| 日志里反复出现同一个已知失效代码 | 已修正。旧版本会把备选代码一并请求,导致每天刷一次假警报;现在备选代码只在主代码失败时才请求 |
| `ValueError: missing FX for XXX` | 已修复。原因是抓取窗口内最早的交易日尚无汇率数据。现在播种固定在**最新**交易日,且汇率不全的交易日会被跳过并记录原因,不再抛异常 |
| 改了环境变量但没生效 | 环境变量只对设置它的那个终端窗口有效,**venv 不会保存它们**。改用 `.env` 文件,并重启服务;启动日志里会打印每项配置的实际来源 |
| `[config] ... is out of range` / `is not a whole number` | `.env` 里的取值写错了,按提示改正 |
| `RuntimeError: File at path ...\static\index.html does not exist` | `index.html` 没放对位置。放进 `static\` 子文件夹,或直接和 `server.py` 平铺,两者皆可。刷新页面即可,**无需重启** |
| `this index was seeded in X but BASE_CCY is now Y` | 基准货币改了。要么把 `.env` 改回 `X`,要么 `POST /api/reset_index?confirm=true` 以 `Y` 重新播种 |
| `python: command not found` | 用 `python3` |
| `externally-managed-environment` | 用 venv,或加 `--break-system-packages` |

---

## 桌面版 v1.2.0

已打包成 Electron 桌面程序:后端用 PyInstaller 冻结成独立可执行文件(90MB,目标机器不需要装
Python),Electron 负责挑一个空闲端口、启动后端、轮询等它就绪、再把窗口指过去。
**关窗口只是缩到托盘**,进程继续跑 —— 每日 18:00 的自动抓取才不会断。

安装包:`build/desktop-dist/Horizon Holdings Setup 1.1.0.exe`(110MB,装完约 358MB)。

托盘菜单里两个抓取动作是**分开**的,因为它们本来就是两条不同的管道:

| 菜单项 | 实际做什么 | 频率 |
|---|---|---|
| 更新行情与净值 | 抓收盘价与汇率,重算并写入净值 | 每天 |
| 更新 P/E、股息率、Beta | 抓基本面快照(季度闸门,同季度内重复点会跳过) | 每季度 |

两者都会在完成后弹通知告诉你结果(净值多少、更新了几支、失败几支),不再是点完没反应。
托盘里还有「这个应用是怎么做出来的」,会在应用内打开构建文档 —— 该文档随程序一起分发,
断网也能看,页面顶部也有同样的入口。

### 导入已有数据库(v1.2.0 新增)

托盘 →「导入数据库…」,**任何时候**都能用,不再只有首次启动那一次机会。
之前选了「全新开始」、换了电脑、或者想从备份恢复,都走这里。

流程是刻意保守的:先校验文件头确实是 SQLite(不是就直接拒绝,原数据不动)→
把当前数据库备份成 `portfolio-replaced-<时间戳>.db` → 停掉后台服务并等它真正退出
→ 替换 → 重启并刷新窗口。原来的 `-wal` 残留会被清掉,否则它会被套用到新库上导致损坏。

### ⚠ 本机当前无法运行打包后的程序

这台机器的 **Smart App Control 处于「强制」状态**,会直接拦截未经代码签名的可执行文件:

```
Start-Process : An Application Control policy has blocked this file.
```

这不是程序的 bug,冻结后的后端 `horizon-backend.exe` 不受影响,被拦的是 Electron 那个主程序。
三条路:

1. **用开发方式运行**(可用,已验证):`cd desktop && npm start` —— 走的是 Electron 官方签名过的
   二进制,功能与打包版完全一致
2. **给程序做代码签名** —— 需要付费证书
3. 关掉 Smart App Control —— **注意:关掉之后无法再打开,除非重装 Windows**,请自行权衡

设计思路、逐步搭建过程、发布流程与版本号约定,写在另一份文档里:`docs/building-this-app.html`
(也可在应用内直接阅读)。

---

## 许可 / License

本项目代码以 **MIT** 许可发布(见 [LICENSE](LICENSE))—— 可自由使用、修改、商用,
保留版权声明即可。

**但 MIT 不覆盖项目内附的第三方组件**,它们各有各的许可,其中有些对再分发方有要求:

| 组件 | 许可 | 要求 |
|---|---|---|
| Chart.js 4.5.1 | MIT | 保留版权声明 |
| Source Serif 4 / Inter / IBM Plex Mono | SIL OFL 1.1 | 许可文本须随字体一起分发;不得单独出售字体 |
| Python / Electron / 各依赖库 | PSF / MIT / BSD / Apache 2.0 | 打进安装包,非本仓库内容 |

完整声明见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。

---

## 免责声明

本工具仅用于个人投资记录与组合结构对照,**不构成投资建议**。所有价格数据来自第三方免费接口,不保证准确性与时效性,不应用于交易决策。模型指数是假设性的,不是可投资的基金。投资有风险,可能损失本金。实际决策前请核实数据并咨询持牌财务顾问。
