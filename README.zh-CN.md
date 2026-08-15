# Horizon Holdings 巴菲特式全球价值组合

一个跑在自己电脑上的投资组合追踪程序,支持 Windows、macOS 和 Linux。
它维护一个由 78 家全球公司组成的模型指数(覆盖 12 个市场、7 种货币),
并把它和你**实际持有的仓位**做对比。

全部在本地运行:不需要注册账号,没有服务器,不收订阅费。
你的持仓数据存在自己硬盘上的一个文件里,不会离开这台电脑。

> 🇬🇧 English version: [README.md](README.md)

---

## 先确认你是哪一种用户

| | 我只想**用这个程序** | 我想**自己编译/ 改代码** |
|---|---|---|
| 看这里 | [安装](#安装) | [从源码构建](#从源码构建) |
| 需要先装 | 什么都不用装 | Python 3.10+、Node.js 18+ |
| 大概花 | 一分钟 | 二十分钟 |
| 要下载 | 约 110 MB 安装包 | 约 1.4 MB 源码 |

---

## 安装

| 你的系统 | 现状 |
|---|---|
| **Windows** | [Releases 页面](https://github.com/vansdardy/horizon-holdings-app/releases)上有现成的安装包 |
| **macOS** | 暂时没有现成安装包 —— 请[从源码构建](#从源码构建),约 20 分钟 |
| **Linux** | 暂时没有现成安装包 —— 请[从源码构建](#从源码构建),约 20 分钟 |

**为什么没有 Mac 和 Linux 的下载。**
后端是用 PyInstaller 打包的,而它**不能跨平台编译**:
要生成 macOS 版本,就必须**在 Mac 上**执行打包;Linux 同理。
这个项目目前只在 Windows 上打包过。

代码本身没有任何 Windows 专属的东西 —— 程序在三个系统上都能正常运行 ——
所以你在自己电脑上构建一次就能用。
如果一个项目想同时提供三个平台的安装包,通常的做法是用「持续集成」服务
(CI)在三种系统上各自构建一次。这个概念值得知道,不过对一个自用的小程序来说是杀鸡用牛刀。

### Windows:下载安装

到 [**Releases 页面**](https://github.com/vansdardy/horizon-holdings-app/releases)
下载最新的 `Horizon Holdings Setup <版本号>.exe`,双击运行即可。
它只给当前用户安装,**不需要管理员密码**。Python 已经打包在里面了,你**不需要**另外安装。

#### Windows 会弹警告,这是正常的

安装包没有做「代码签名」。签名证书每年要交钱,而且它本身并不能让软件更安全,
所以这个项目没有买。你会看到下面两种情况之一:

| 你看到的 | 该怎么办 |
|---|---|
| **「Windows 已保护你的电脑」**(SmartScreen) | 点**「更多信息」→「仍要运行」** |
| **「应用程序控制策略已阻止此文件」** | 说明开了 Smart App Control,见下面说明 |

**Smart App Control** 不是警告,而是直接拒绝运行未签名的程序。
它只能**永久关闭** —— Windows 不允许再打开,除非重装系统 —— 所以关之前请想清楚。
不想关的话,可以改成[从源码构建](#从源码构建),那条路不受影响。

### macOS:系统会拒绝打开,这也是正常的

如果你在 Mac 上自己构建了这个程序,macOS 会拒绝打开它,
因为它没有签名、也没有经过苹果公证(notarize)。
**macOS 比 Windows 更严格:第一个弹窗里根本没有「仍要运行」这个选项。**

两种办法:
在程序图标上**右键 →「打开」**(这样弹出的对话框里会多一个「打开」按钮,双击是没有的);
或者到**「系统设置 → 隐私与安全性」**里,
被拦下的程序会出现在那里,旁边有个**「仍要打开」**按钮。

正规的签名和公证需要付费的 Apple 开发者账号。
对于你自己在自己电脑上构建的程序,用上面的方式放行就是正常做法。

### 装完之后要知道的三件事

程序装好后会常驻在**系统托盘**(屏幕右下角那排小图标)。

- **点窗口右上角的「×」不会退出程序。** 它只是把窗口收起来,好让每天的自动抓价继续跑。
  真的要退出:**右键点托盘图标 → 退出**。第一次关窗口时程序会主动提示你这件事。
- **第一次启动会问你数据从哪来。** 以前用过这个项目就选「导入」,指向你原来的
  `portfolio.db`;没用过就选「全新开始」。
- **每天 18:00 自动更新一次行情**,而且只在程序开着的时候。
  电脑睡眠过也没关系,下次启动会把漏掉的交易日补回来。

---

## 这个程序做什么

### 一、模型指数净值

一个假设的投资组合:78 家公司,按「信心分」分配权重,初始 100 亿瑞郎、
拆成 2 亿份,所以每份正好 50.00。之后每天重新估值一次。

有三个细节让它像一支真基金,而不是一张 Excel 表:

- **只买整数股。** 现实中买不到 3.7 股雀巢,所以分配时向下取整,
  余下的钱按该公司**所在国家的货币**留作现金。
- **七种货币。** 内部统一用美元换算(因为汇率数据就是这么给的),
  最后再换成你选定的报告货币显示。
- **每年再平衡一次**,在新一年的第一个交易日。

净值曲线从你部署那天开始累积。**这不是回测**,里面没有任何「事后诸葛亮」。

### 二、你的真实持仓

填进你实际持有的股数和平均成本,程序会算出浮动盈亏、
你的实际权重与模型目标权重的差距,以及还差多少股才能补齐。
**支持零碎股**(比如 12.5 股)—— 「只买整数股」那条规则只管模型指数,不管你。

> 「差额股数」只是一道算术题,**不是买入建议**。
> 它不考虑你的税务情况、交易成本,也不判断现在这个价格合不合适。它只是个对照工具。

### 三、有一条规则值得专门说明

**如果你持有的某家公司当天取不到价格,程序会拒绝记录当天的净值。**

把一个真实持仓按零估值,看起来会像一次真实的市场下跌 ——
实测中,仅仅一支股票缺价就造成了 **-2.17% 的虚假单日跌幅**。
记录里少一天,以后还能补;记录里多一个「看起来很合理」的错数字,就再也没人会发现了。

### 四、市盈率 / 股息率 / Beta 是每季度更新,不是每天

这三个数字走的是另一条完全不同的数据管道:每家公司要单独请求一次
(而不是 78 家一次拿完),而且它们本身变化很慢。所以程序每个日历季度才抓一次。

带小圆点(●)的数字是当季实时抓到的,没有圆点的是内置的静态估算值。
鼠标悬停能看到具体是哪个季度抓的,以及市盈率是**静态**(基于已公布盈利)
还是**动态**(基于分析师预测)—— 对高估值公司来说,这两者可能差好几倍。

---

## 从源码构建

### 需要先装的东西

| | Windows | macOS | Linux |
|---|---|---|---|
| Python 3.10+ | [python.org 下载](https://www.python.org/downloads/) —— **一定要勾选 "Add python.exe to PATH"** | `brew install python` | `sudo apt install python3 python3-venv` |
| Node.js 18+ | `winget install OpenJS.NodeJS.LTS` | `brew install node` | `sudo apt install nodejs npm` |
| Git | `winget install Git.Git` | `brew install git` | `sudo apt install git` |

> **装完任何一个之后,请关掉命令行窗口重新开一个。**
> 命令行只在**启动的那一刻**读取系统里的程序路径,所以你之前就开着的那个窗口
> 会一直说「找不到这个命令」。这是最常见的「装失败了」,而其实根本没失败。

<details>
<summary><b>Windows 用户:在你输入 <code>python</code> 之前请先读这段</b>(能省你一个小时)</summary>

Windows 系统在 `%LOCALAPPDATA%\Microsoft\WindowsApps` 目录里预置了两个
**0 字节的占位文件**,名字就叫 `python.exe` 和 `python3.exe`。
运行它们不会执行任何 Python 代码,而是**打开微软商店**。

网上大量教程是给 macOS 写的,里面都写 `python3` —— 在 Windows 上照抄就会跳商店。

**请改用 `py`** —— 这是 Python 官方安装包附带的启动器,装在 `C:\Windows` 里,
永远排在那个商店占位文件前面:

```powershell
py --version          # 这个一定能用
py -3.12 --version    # 电脑上装了好几个 Python 版本时,指定用哪个
py --list             # 列出装了哪些版本
```

`python` 这个命令在你的电脑上**也许**能用,但那要看真正的 Python 有没有恰好排在
`WindowsApps` 前面。那是运气,不是保证,所以本文档一律用 `py`。

**`py` 默认用你装过的最新版本。** 一般来说这没问题,但如果那个版本是最近几个月才发布的,
pandas、numpy 这类库往往还没有为它编译好的现成安装包,
于是 `pip install` 会尝试从源码编译,然后报出一大堆看起来像是你搞错了的编译错误。
**那不是你的错。** 遇到这种情况,指定一个发布了一年左右的版本:

```powershell
py -3.12 -m venv .venv
```

**另外:**本项目从不要求你「激活虚拟环境」。
激活要执行一个 PowerShell 脚本,而 Windows 默认设置会直接拒绝,
报错 **「因为在此系统上禁止运行脚本」**。
直接调用虚拟环境里的 Python 就完全绕开了这个问题。
</details>

### 第 1 步:下载代码

```bash
git clone https://github.com/vansdardy/horizon-holdings-app.git
cd horizon-holdings-app
```

### 第 2 步:建虚拟环境、装依赖

**Windows(PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 第 3 步:先单独跑后端

这一步能得到**网页版**的完整程序(不带 Electron 外壳),
是确认一切正常最快的办法。

**Windows:**

```powershell
.venv\Scripts\python.exe server.py
```

**macOS / Linux:**

```bash
.venv/bin/python server.py
```

然后浏览器打开 <http://127.0.0.1:8000>。看到这几行就说明成功了:

```
[startup] scheduler running (daily fetch at 18:00 local)
[startup] data source: Yahoo Finance
INFO:     Uvicorn running on http://127.0.0.1:8000
```

如果显示 `MOCK — NOT REAL PRICES`,说明环境变量 `MARKETDATA_MOCK` 还是 `1`,
现在看到的数字**全是假的**。

**第一次安装,建议先验证股票代码。** 交易所会改代码,先跑这个能当场发现问题,
而不是几周后遇到一个莫名其妙的报错:

**Windows(PowerShell):**

```powershell
curl.exe http://127.0.0.1:8000/api/check_symbols
```

**macOS / Linux:**

```bash
curl http://127.0.0.1:8000/api/check_symbols
```

> **Windows 上必须写 `curl.exe`,不能只写 `curl`。**
> 在 PowerShell 里 `curl` 被指向了另一个完全不同的命令,
> 写 `curl -X POST ...` 会报 **「找不到与参数名称 X 匹配的参数」**,
> 这个报错完全不会告诉你真正的原因。macOS 和 Linux 上直接用 `curl` 就是对的。

返回 `"healthy": true` 表示 78 支个股和 6 组汇率全部正常。
按 `Ctrl+C` 停止服务。

### 第 4 步:把后端打包成独立可执行文件

桌面版运行的是**打包进去的那份 Python**,而不是你电脑上的这份,所以要先生成它。

**Windows:**

```powershell
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe -m PyInstaller backend.spec --noconfirm --distpath build/backend --workpath build/pyinstaller
```

**macOS / Linux:**

```bash
.venv/bin/python -m pip install pyinstaller
.venv/bin/python -m PyInstaller backend.spec --noconfirm --distpath build/backend --workpath build/pyinstaller
```

大约 90 秒,在 `build/backend/` 里生成约 90 MB 的文件。

> **只要改动了 Python 代码,就要重新跑这一步。**
> 桌面版优先用打包好的那份,所以如果你忘了重新打包,
> 会出现「我明明改了代码、重启了程序,行为却一点没变」的情况 —— 而且不会有任何报错提示你。

### 第 5 步:运行桌面版

```bash
cd desktop
npm install
npm start
```

### 第 6 步:生成安装包

```bash
npm run dist
```

结果在 `build/desktop-dist/` 里。

<details>
<summary><b>仅限 Windows:如果构建时报错「Cannot create symbolic link」(无法创建符号链接)</b></summary>

打包工具会下载一套「代码签名工具包」,里面含有 macOS 的符号链接文件,
而在 Windows 上创建符号链接需要普通账户没有的权限 —— 尽管我们**根本没在签名**。
手动解压那个压缩包、跳过 macOS 部分就行:

```powershell
$cache = "$env:LOCALAPPDATA\electron-builder\Cache\winCodeSign"
$sevenZip = ".\node_modules\7zip-bin\win\x64\7za.exe"
& $sevenZip x "$cache\<下载下来的那个文件>.7z" "-o$cache\winCodeSign-2.6.0" '-xr!darwin'
```

然后重新跑 `npm run dist`。打开 Windows 的「开发者模式」也能一劳永逸解决。
</details>

### 跑测试

**Windows:**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
node --test tests/js/*.test.js
```

**macOS / Linux:**

```bash
.venv/bin/python -m pytest tests/ -q
node --test tests/js/*.test.js
```

共 74 个测试,大约八秒。
注意前端那条要用 `*.test.js` 这种通配符写法,**不要直接给目录**——
`node --test tests/js` 在 Git Bash 下会报一个很让人困惑的 `Cannot find module`,
原因是 Git Bash 转换路径的方式,不是测试本身有问题。

---

## 你的数据存在哪

安装版会把数据库放在**程序目录之外**,因为程序安装目录是只读的,
而且升级时会被整个替换掉。

| 系统 | 位置 |
|---|---|
| Windows | `%APPDATA%\Horizon Holdings\` |
| macOS | `~/Library/Application Support/Horizon Holdings/` |
| Linux | `~/.config/Horizon Holdings/` |

嫌路径难打的话,托盘菜单里有**「打开数据文件夹」**。
如果你是从源码运行的,`portfolio.db` 还是和代码放在一起,和以前一样。

### 导入已有的数据库

托盘菜单 →**「导入数据库…」**,或者窗口里「保存持仓 / 导出 JSON」旁边那个按钮。
**任何时候都能用**,不是只有第一次启动那一次机会。

替换之前它会先确认这个文件确实是数据库,
把你当前的数据备份成 `portfolio-replaced-<时间戳>.db`,然后干净地重启后台服务。

### 备份 —— 不要直接复制那个文件

数据库用的是 SQLite 的 WAL(预写日志)模式,意思是**刚写入的数据可能还在一个
`-wal` 后缀的伴生文件里**。程序运行时只复制 `portfolio.db` 一个文件,
**可能会悄无声息地丢掉最近的记录**。请用下面任意一种:

1. 程序里的**「备份数据库」**按钮。
2. 程序运行时,用接口:
   ```powershell
   curl.exe -X POST http://127.0.0.1:8000/api/backup    # Windows
   ```
   ```bash
   curl -X POST http://127.0.0.1:8000/api/backup        # macOS / Linux
   ```
3. 程序**完全退出后**,三个文件一起复制:
   ```powershell
   Copy-Item portfolio.db,portfolio.db-wal,portfolio.db-shm C:\备份\ -ErrorAction SilentlyContinue
   ```
   ```bash
   cp portfolio.db portfolio.db-wal portfolio.db-shm ~/备份/ 2>/dev/null
   ```

不指定 `?dest=` 时,备份文件生成在数据库所在的那个文件夹里。
程序里的**「导出 JSON」**还能把持仓、净值、价格、汇率全部导成纯文本 ——
这里不存在数据锁定。

---

## 配置

可选,全部都有能用的默认值。复制模板再改:

```powershell
Copy-Item .env.example .env
notepad .env
```

```bash
cp .env.example .env
```

| 变量 | 默认 | 含义 |
|---|---|---|
| `PORT` | `8000` | 从源码运行时后端用的端口。桌面版会自动挑一个空闲端口 |
| `FETCH_HOUR` | `18` | 每天自动抓取的**本地**小时。建议设在你关注的最后一个市场收盘之后 |
| `PORTFOLIO_DB` | `./portfolio.db` | 数据库路径 |
| `FETCH_LOOKBACK` | `10d` | 每次抓取回溯多久,漏掉的交易日就是靠它补回来的 |
| `BASE_CCY` | `CHF` | 报告货币,可选 CHF、USD、EUR、GBP、CAD、JPY、DKK |
| `MARKETDATA_MOCK` | `0` | 设为 `1` 用假数据离线开发 |

如果只想**临时**改一次、不想动文件,可以用环境变量。
注意每种命令行的写法都不一样 —— 这一点最容易在不同系统之间抄错:

```powershell
$env:PORT="8001"; .venv\Scripts\python.exe server.py     # Windows PowerShell
```

```bash
PORT=8001 .venv/bin/python server.py                     # macOS / Linux
```

这种写法**只对当前这个命令行窗口有效**,关掉就没了。
这正是 `.env` 存在的意义:一个要每天运行的程序,配置得写在重启后依然还在的文件里。

改完要重启才生效。启动日志会打印每一项的实际取值和它是从哪来的;
配置写错时程序会**直接拒绝启动**,而不是跑到几小时后才出问题。

**安装版的程序把设置写在它自己的数据文件夹里**,`.env` 是给从源码运行用的。

> **指数一旦开始跑,就不允许再改 `BASE_CCY`** ——
> 一条中途换了计价货币的净值序列,等于把两段没法比较的数据硬拼在一起。
> 真要改:改 `.env` → 重启 → `POST /api/reset_index?confirm=true`。
> 你的持仓和价格存档不受影响。

---

## 它是怎么搭起来的

四层:一个 SQLite 文件、Python 逻辑、一套 HTTP 接口、一个 HTML 页面 ——
再加上 Electron 负责管理这一整套并给它套一个窗口。
页面通过 `127.0.0.1` 和后端通信,和浏览器的做法完全一样 ——
这也是为什么同一份代码既能当网站跑,也能当安装程序跑。

**`docs/building-this-app.html`** 用 16 个章节完整讲了这个程序是怎么做出来的:
架构为什么长这样、打包、测试、重构、版本控制、发布、
怎么把这套方法搬到别的语言和别的类型的程序上,以及卡住了该怎么办。
它是写给**编程第一年**的人看的。

有三种方式可以读到它 —— 之所以要说明,是因为 GitHub 会把 `.html` 文件**显示成源代码**,
而不是渲染成网页:

- **在程序里看** —— 托盘菜单 →**「这个应用是怎么做出来的」**,断网也能看。
- **从源码运行时** —— 启动后端,打开 <http://127.0.0.1:8000/guide>。
- **当成文件看** —— 把 `docs/building-this-app.html` 下载下来,用任意浏览器打开。
  它是完全自包含的,连字体都打包在里面了。

---

## 接口一览

后端运行时,交互式文档在 <http://127.0.0.1:8000/docs>。

| 端点 | 作用 |
|---|---|
| `GET /api/status` | 数据源、最近一次抓取、调度状态、错误信息 |
| `GET /api/check_symbols` | 逐一探测 78 支个股 + 6 组汇率 —— **首次安装先跑这个** |
| `POST /api/refresh` | 立即抓取。`?window=N` 指定回溯天数 |
| `GET /api/nav` | 净值历史与统计指标 |
| `GET /api/universe` | 78 支成分股与目标权重 |
| `GET /api/positions` | 持仓 + 现价 + 权重偏离 + 差额股数 |
| `POST /api/positions` | 保存持仓 |
| `POST /api/cash` | 按币种保存现金余额 |
| `GET /api/prices` | 最新价格与汇率 |
| `GET /api/archive` | 价格存档统计 |
| `GET /api/fundamentals` | 最近一次季度抓取的 P/E、股息率、Beta |
| `POST /api/refresh_fundamentals` | 手动抓基本面;`?force=true` 无视季度闸门 |
| `GET /api/price_history` | 价格序列,可按代码和日期筛选 |
| `GET /api/price_history.csv` | 整个存档导出为 CSV |
| `GET /api/nav/simulate` | 用其他起始日重算指数,只读不写 |
| `POST /api/reset_index` | 清空净值序列重新播种,需要 `?confirm=true` |
| `POST /api/backup` | 生成一致性数据库快照 |
| `GET /api/export` | 全部数据,JSON 格式 |
| `GET /guide` | 构建文档 |

---

## 故障排查

| 现象 | 原因与处理 |
|---|---|
| 输入 `python3` 却打开了微软商店 | 那是 Windows 的占位文件,不是 Python。改用 `py` |
| `curl: 找不到与参数名称 X 匹配的参数` | PowerShell 把 `curl` 指向了别的命令。改用 `curl.exe` |
| `因为在此系统上禁止运行脚本` | 系统策略挡住了虚拟环境激活脚本。别激活,直接用 `.venv\Scripts\python.exe` |
| 装完 Node 后仍提示找不到 `npm` / `node` | 命令行窗口比安装动作更早打开。关掉重开一个 |
| `Cannot find module ...tests\js` | 用通配符:`node --test tests/js/*.test.js` |
| 改了 Python 代码,程序行为没变 | 忘了重新打包后端(第 4 步)。桌面版优先用打包好的那份 |
| 页面显示「后端未连接」 | 后端没启动,或端口被占用。改 `PORT`,写法见「配置」一节 |
| macOS 拒绝打开这个程序 | 未签名的构建。右键 →「打开」,或到「系统设置 → 隐私与安全性」里放行 |
| 状态栏显示红色 MOCK | `MARKETDATA_MOCK=1` 还开着,数据是假的。去掉并重启 |
| 抓取返回 409 | 你持有的某支股票当天缺价,当日净值被**有意**拒绝写入。错误信息里会写是哪几支 |
| 抓取返回 500 | 网络或数据源问题,详见 `/api/status` 里的 `last_fetch_error` |
| 净值曲线只有一个点 | 正常。曲线从你开始运行那天起累积 |
| 净值有断档 | 停机时间超过了 `FETCH_LOOKBACK`。调大它再抓一次 |
| `possibly delisted; no price data found` | 某个代码没取到数据。如果紧接着出现 `daily update done`,说明整体抓取是**成功**的。跑 `/api/check_symbols` 确认 |
| `this index was seeded in X but BASE_CCY is now Y` | 见「配置」一节最后的说明 |
| 安装包被完全阻止运行 | Smart App Control,见[安装](#安装)一节 |

---

## 数据来源

Yahoo Finance,通过 `yfinance` 库获取,免费、不需要 API key。
一次批量请求就能拿到全部 78 支个股和 6 组汇率。

如果你要改 `universe.py`,有几个代码细节值得注意:
伯克希尔是 `BRK-B` 不是 `BRK.B`;
阿斯麦用的是阿姆斯特丹的 `ASML.AS`(欧元计价),不是纳斯达克那个美元的 ——
两者混用会把货币换算搞乱;
Arm 是英国公司但以美元在纳斯达克交易,所以按 USD 处理。

**每条报价都存在它实际成交的那个交易日下面**,而不是统一盖上「今天」的日期。
各交易所休市日不同,把一条旧报价重新盖成今天,等于凭空捏造出根本不存在的价格历史。

---

## 许可

MIT,见 [LICENSE](LICENSE)。可以自由使用、修改、商用,保留版权声明即可。

**但 MIT 不覆盖内附的第三方组件**,它们各有各的许可,其中有些对再分发方有要求:

| 组件 | 许可 | 要求 |
|---|---|---|
| Chart.js | MIT | 保留版权声明 |
| Source Serif 4 / Inter / IBM Plex Mono | SIL OFL 1.1 | 许可文本须随字体一起分发;不得单独出售字体 |
| Python / Electron / 各依赖库 | PSF / MIT / BSD / Apache 2.0 | 打进安装包,非本仓库内容 |

完整声明见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。

---

## 免责声明

本工具仅用于个人投资记录与组合结构对照,**不构成投资建议**。
价格数据来自第三方免费接口,不保证准确性与时效性,不应用于交易决策。
模型指数是假设性的,不是可以购买的基金。投资有风险,可能损失本金。
实际决策前请核实数据并咨询持牌财务顾问。
