# -*- coding: utf-8 -*-
"""Single source of truth: the 78-stock universe, target weights, Yahoo ticker map."""

# The FX pairs available from the data source are all quoted against USD
# (CHFUSD=X etc.), so USD is used as the internal numeraire for arithmetic.
# It is NOT the reporting currency — see BASE_CCY below.
NUMERAIRE = "USD"

# Reporting / denomination currency for the model index.
# Default CHF: of the seven currencies in this portfolio it has historically
# been the least volatile, which keeps the NAV series from being dominated by
# currency noise rather than by the businesses themselves.
import config as _config
BASE_CCY = _config.BASE_CCY

# Initial NAV is denominated in BASE_CCY: 10bn / 200m shares = 50.00 per share.
INITIAL_NAV_BASE = 10_000_000_000
SHARES_OUTSTANDING = 200_000_000

UNIVERSE = {
    'BRK.B': dict(name='伯克希尔哈撒韦', yahoo='BRK-B', country='美国', exchange='NYSE', ccy='USD', sector='Financials', industry='多元化保险控股集团', moat='Buffett本尊,保险浮存金(float)+跨行业资本配置,新任CEO Greg Abel延续投资纪律', score=6),
    'AAPL': dict(name='苹果', yahoo='AAPL', country='美国', exchange='NASDAQ', ccy='USD', sector='Technology', industry='消费电子/生态系统', moat='iOS生态黏性+品牌忠诚度,Buffett实际第一大重仓股', score=6),
    'MSFT': dict(name='微软', yahoo='MSFT', country='美国', exchange='NASDAQ', ccy='USD', sector='Technology', industry='企业软件/云计算', moat='企业客户转换成本高,Azure云基础设施护城河(激进放宽项)', score=5),
    'BAC': dict(name='美国银行', yahoo='BAC', country='美国', exchange='NYSE', ccy='USD', sector='Financials', industry='零售/商业银行', moat='Buffett长期持仓,存款规模与网点护城河', score=4),
    'AXP': dict(name='美国运通', yahoo='AXP', country='美国', exchange='NYSE', ccy='USD', sector='Financials', industry='信用卡/支付', moat='Buffett经典长期持仓,支付网络+高端客群品牌溢价', score=5),
    'MCO': dict(name='穆迪', yahoo='MCO', country='美国', exchange='NYSE', ccy='USD', sector='Financials', industry='信用评级', moat='评级行业双寡头之一,Buffett长期重仓', score=5),
    'V': dict(name='Visa', yahoo='V', country='美国', exchange='NYSE', ccy='USD', sector='Financials', industry='支付网络', moat='轻资产、高利润率的全球支付网络效应', score=5),
    'MA': dict(name='万事达', yahoo='MA', country='美国', exchange='NYSE', ccy='USD', sector='Financials', industry='支付网络', moat='与Visa共同构成支付双寡头', score=4),
    'SPGI': dict(name='标普全球', yahoo='SPGI', country='美国', exchange='NYSE', ccy='USD', sector='Financials', industry='评级/指数/数据', moat='评级+指数数据双重护城河', score=4),
    'KO': dict(name='可口可乐', yahoo='KO', country='美国', exchange='NYSE', ccy='USD', sector='Consumer Staples', industry='饮料', moat='Buffett标志性持仓,全球品牌与渠道护城河', score=6),
    'PG': dict(name='宝洁', yahoo='PG', country='美国', exchange='NYSE', ccy='USD', sector='Consumer Staples', industry='日用消费品', moat='多品牌矩阵,定价权与规模效应', score=4),
    'COST': dict(name='好市多', yahoo='COST', country='美国', exchange='NASDAQ', ccy='USD', sector='Consumer Discretionary', industry='会员制仓储零售', moat='会员费驱动的商业模式,Munger长期推崇', score=5),
    'MCD': dict(name='麦当劳', yahoo='MCD', country='美国', exchange='NYSE', ccy='USD', sector='Consumer Discretionary', industry='餐饮特许经营', moat='特许经营+地产双重护城河', score=4),
    'JNJ': dict(name='强生', yahoo='JNJ', country='美国', exchange='NYSE', ccy='USD', sector='Health Care', industry='多元医疗保健', moat='多元产品线,现金流极其稳定(股息贵族)', score=4),
    'UNH': dict(name='联合健康', yahoo='UNH', country='美国', exchange='NYSE', ccy='USD', sector='Health Care', industry='managed care健康险', moat='Buffett持仓,医保规模效应(近年监管与医疗成本压力需关注)', score=3),
    'UNP': dict(name='联合太平洋铁路', yahoo='UNP', country='美国', exchange='NYSE', ccy='USD', sector='Industrials', industry='货运铁路', moat='北美铁路双寡头基础设施护城河,准入壁垒极高', score=5),
    'WM': dict(name='美国废物管理', yahoo='WM', country='美国', exchange='NYSE', ccy='USD', sector='Industrials', industry='固废处理', moat='区域垃圾处理/填埋场特许经营壁垒', score=4),
    'CVX': dict(name='雪佛龙', yahoo='CVX', country='美国', exchange='NYSE', ccy='USD', sector='Energy', industry='一体化石油天然气', moat='Buffett持仓,一体化能源龙头,资产负债表稳健', score=4),
    'OXY': dict(name='西方石油', yahoo='OXY', country='美国', exchange='NYSE', ccy='USD', sector='Energy', industry='石油天然气开采', moat='Buffett重仓,二叠纪盆地低成本资源', score=4),
    'AMT': dict(name='美国电塔', yahoo='AMT', country='美国', exchange='NYSE', ccy='USD', sector='Real Estate', industry='通信铁塔REIT', moat='通信铁塔基础设施收租模式,长期租约现金流(REIT,估值以FFO更合适)', score=3),
    'GOOGL': dict(name='谷歌/Alphabet', yahoo='GOOGL', country='美国', exchange='NASDAQ', ccy='USD', sector='Communications', industry='搜索/广告/云', moat='搜索垄断级护城河,Buffett近期新进持仓,2024年起首次分红', score=5),
    'NEE': dict(name='新纪元能源', yahoo='NEE', country='美国', exchange='NYSE', ccy='USD', sector='Utilities', industry='受监管电力+新能源', moat='受监管公用事业现金流+新能源龙头地位', score=3),
    'CSU.TO': dict(name='Constellation Software', yahoo='CSU.TO', country='加拿大', exchange='TSX', ccy='CAD', sector='Technology', industry='垂直行业软件', moat='并购整合垂直软件资产,长期复利典范(Mark Leonard式资本配置)', score=4),
    'RY.TO': dict(name='加拿大皇家银行', yahoo='RY.TO', country='加拿大', exchange='TSX', ccy='CAD', sector='Financials', industry='综合性银行', moat='加拿大寡头银行体系,监管壁垒极高', score=4),
    'ATD.TO': dict(name='Alimentation Couche-Tard', yahoo='ATD.TO', country='加拿大', exchange='TSX', ccy='CAD', sector='Consumer Staples', industry='便利店', moat='便利店行业整合者,资本配置纪律出色', score=3),
    'QSR.TO': dict(name='餐饮品牌国际', yahoo='QSR.TO', country='加拿大', exchange='TSX', ccy='CAD', sector='Consumer Discretionary', industry='餐饮特许经营', moat='汉堡王/Tim Hortons/Popeyes特许经营组合(3G资本背景)', score=2),
    'CNR.TO': dict(name='加拿大国家铁路', yahoo='CNR.TO', country='加拿大', exchange='TSX', ccy='CAD', sector='Industrials', industry='货运铁路', moat='北美铁路双寡头之一,准入壁垒极高', score=4),
    'TRI': dict(name='汤森路透', yahoo='TRI.TO', country='加拿大', exchange='TSX/NYSE', ccy='CAD', sector='Industrials', industry='专业信息与合规数据', moat='订阅制专业信息服务,客户粘性强(对标标普全球评级/数据逻辑)', score=3),
    'CNQ.TO': dict(name='加拿大自然资源', yahoo='CNQ.TO', country='加拿大', exchange='TSX', ccy='CAD', sector='Energy', industry='油砂/常规油气', moat='低成本长寿命油砂资源,自由现金流稳健', score=3),
    'NTR.TO': dict(name='加拿大Nutrien', yahoo='NTR.TO', country='加拿大', exchange='TSX/NYSE', ccy='CAD', sector='Materials', industry='钾肥/农业投入品', moat='全球最大钾肥生产商,资源禀赋壁垒', score=2),
    'FTS.TO': dict(name='Fortis Inc', yahoo='FTS.TO', country='加拿大', exchange='TSX/NYSE', ccy='CAD', sector='Utilities', industry='受监管电力/燃气', moat='50年连续股息增长记录,受监管公用事业现金流', score=3),
    'HSBA.L': dict(name='汇丰控股', yahoo='HSBA.L', country='英国', exchange='LSE', ccy='GBP', sector='Financials', industry='全球银行', moat='全球贸易融资网络,亚洲业务敞口', score=3),
    'DGE.L': dict(name='帝亚吉欧', yahoo='DGE.L', country='英国', exchange='LSE', ccy='GBP', sector='Consumer Staples', industry='烈酒', moat='烈酒品牌矩阵,提价能力强', score=4),
    'ULVR.L': dict(name='联合利华', yahoo='ULVR.L', country='英国', exchange='LSE', ccy='GBP', sector='Consumer Staples', industry='日用消费品', moat='全球日用消费品品牌矩阵', score=3),
    'AZN.L': dict(name='阿斯利康', yahoo='AZN.L', country='英国', exchange='LSE', ccy='GBP', sector='Health Care', industry='创新药', moat='肿瘤/罕见病管线专利护城河', score=4),
    'BA.L': dict(name='BAE系统公司', yahoo='BA.L', country='英国', exchange='LSE', ccy='GBP', sector='Industrials', industry='国防装备', moat='英美长期国防合约,政府客户粘性(相对Buffett传统偏好的适度放宽)', score=3),
    'RIO.L': dict(name='力拓集团', yahoo='RIO.L', country='英国', exchange='LSE', ccy='GBP', sector='Materials', industry='多元矿业', moat='低成本铁矿石资源禀赋壁垒', score=2),
    'SGRO.L': dict(name='Segro Plc', yahoo='SGRO.L', country='英国', exchange='LSE', ccy='GBP', sector='Real Estate', industry='物流地产REIT', moat='电商结构性增长受益的物流地产(REIT,估值以FFO更合适)', score=2),
    'NG.L': dict(name='国家电网', yahoo='NG.L', country='英国', exchange='LSE', ccy='GBP', sector='Utilities', industry='受监管输配电', moat='输配电网络垄断特许经营权', score=3),
    'ARM': dict(name='Arm Holdings', yahoo='ARM', country='英国', exchange='NASDAQ', ccy='USD', sector='Technology', industry='芯片架构IP', moat='移动芯片架构近垄断级授权模式,产业链chokepoint(估值偏高,风险需关注);英国公司但以ADS形式在纳斯达克以美元交易,故计价货币为USD', score=3),
    'RMS.PA': dict(name='爱马仕', yahoo='RMS.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Consumer Discretionary', industry='奢侈品', moat='极致稀缺性驱动的定价权,几乎不打折的品牌护城河', score=4),
    'MC.PA': dict(name='LVMH', yahoo='MC.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Consumer Discretionary', industry='奢侈品集团', moat='多品牌奢侈品矩阵,规模与渠道优势', score=3),
    'OR.PA': dict(name='欧莱雅', yahoo='OR.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Consumer Staples', industry='美妆', moat='全球美妆品类龙头,研发与渠道双重护城河', score=4),
    'RI.PA': dict(name='保乐力加', yahoo='RI.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Consumer Staples', industry='烈酒', moat='全球烈酒品牌组合(近年新兴市场需求波动需关注)', score=2),
    'SAN.PA': dict(name='赛诺菲', yahoo='SAN.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Health Care', industry='制药/疫苗', moat='疫苗+专科药物专利组合', score=3),
    'SU.PA': dict(name='施耐德电气', yahoo='SU.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Industrials', industry='电气化/能效设备', moat='电气化与能效设备装机基础护城河,长期结构性需求', score=4),
    'TTE.PA': dict(name='道达尔能源', yahoo='TTE.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Energy', industry='一体化能源', moat='一体化能源龙头,资产负债表稳健', score=3),
    'AI.PA': dict(name='液化空气集团', yahoo='AI.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Materials', industry='工业气体', moat='工业气体管网基础设施,客户转换成本极高', score=4),
    'DSY.PA': dict(name='达索系统', yahoo='DSY.PA', country='法国', exchange='Euronext Paris', ccy='EUR', sector='Technology', industry='工程仿真软件', moat='工程仿真/PLM软件高粘性,订阅制收入', score=3),
    'SAP': dict(name='思爱普', yahoo='SAP.DE', country='德国', exchange='XETRA', ccy='EUR', sector='Technology', industry='企业ERP软件', moat='企业ERP系统转换成本极高,云转型进展顺利', score=4),
    'ALV.DE': dict(name='安联', yahoo='ALV.DE', country='德国', exchange='XETRA', ccy='EUR', sector='Financials', industry='保险/资管', moat='欧洲最大保险集团之一,浮存金逻辑近似Buffett偏好', score=3),
    'DB1.DE': dict(name='德意志交易所', yahoo='DB1.DE', country='德国', exchange='XETRA', ccy='EUR', sector='Financials', industry='交易所基础设施', moat='交易所/清算基础设施,近似收费站商业模式', score=3),
    'SIE.DE': dict(name='西门子', yahoo='SIE.DE', country='德国', exchange='XETRA', ccy='EUR', sector='Industrials', industry='多元工业技术', moat='多元工业技术集团,自动化与基建业务组合', score=3),
    'BAS.DE': dict(name='巴斯夫', yahoo='BAS.DE', country='德国', exchange='XETRA', ccy='EUR', sector='Materials', industry='综合化工', moat='一体化化工生产网络(Verbund),周期性较强(适度放宽项)', score=2),
    'DTE.DE': dict(name='德国电信', yahoo='DTE.DE', country='德国', exchange='XETRA', ccy='EUR', sector='Communications', industry='电信运营', moat='控股T-Mobile美国,用户黏性与规模效应', score=2),
    'ASML': dict(name='阿斯麦', yahoo='ASML.AS', country='荷兰', exchange='Euronext Amsterdam', ccy='EUR', sector='Technology', industry='半导体设备', moat='EUV光刻机全球独家供应商,半导体产业链关键节点(用户示例中的激进放宽项)', score=6),
    'HEIA.AS': dict(name='喜力', yahoo='HEIA.AS', country='荷兰', exchange='Euronext Amsterdam', ccy='EUR', sector='Consumer Staples', industry='啤酒', moat='全球啤酒品牌组合,家族治理结构稳定', score=3),
    'WKL.AS': dict(name='威科集团', yahoo='WKL.AS', country='荷兰', exchange='Euronext Amsterdam', ccy='EUR', sector='Industrials', industry='监管合规信息服务', moat='法律/税务/医疗合规信息订阅护城河', score=3),
    'NESN.SW': dict(name='雀巢', yahoo='NESN.SW', country='瑞士', exchange='SIX', ccy='CHF', sector='Consumer Staples', industry='食品饮料', moat='全球最大食品饮料集团,品牌矩阵极其广泛(用户自身持仓)', score=5),
    'RO.SW': dict(name='罗氏', yahoo='RO.SW', alts=['ROP.SW', 'ROG.SW'], country='瑞士', exchange='SIX', ccy='CHF', sector='Health Care', industry='制药/诊断', moat='肿瘤/诊断领域专利护城河,诊断业务协同(RO.SW 为SIX记名股;参与证书ROP.SW为不同证券,成本价请勿混填)', score=4),
    'NOVN.SW': dict(name='诺华', yahoo='NOVN.SW', country='瑞士', exchange='SIX', ccy='CHF', sector='Health Care', industry='创新药', moat='创新药专利管线,聚焦核心治疗领域后估值重估', score=4),
    'UBSG.SW': dict(name='瑞银集团', yahoo='UBSG.SW', country='瑞士', exchange='SIX', ccy='CHF', sector='Financials', industry='财富管理/投行', moat='瑞士财富管理龙头,整合瑞信后规模效应扩大(整合执行风险需关注)', score=2),
    'ZURN.SW': dict(name='苏黎世保险', yahoo='ZURN.SW', country='瑞士', exchange='SIX', ccy='CHF', sector='Financials', industry='保险', moat='保险浮存金逻辑,资本配置纪律良好', score=3),
    'ABBN.SW': dict(name='ABB', yahoo='ABBN.SW', country='瑞士', exchange='SIX', ccy='CHF', sector='Industrials', industry='电气化/工业自动化', moat='电气化与工业自动化设备,长期电气化趋势受益', score=3),
    '8035.T': dict(name='东京电子', yahoo='8035.T', country='日本', exchange='TSE', ccy='JPY', sector='Technology', industry='半导体设备', moat='半导体前道设备寡头之一,产业链关键节点', score=4),
    '6861.T': dict(name='基恩士', yahoo='6861.T', country='日本', exchange='TSE', ccy='JPY', sector='Technology', industry='工业传感器/自动化', moat='工业传感器/机器视觉高毛利率,轻资产直销模式', score=4),
    '7741.T': dict(name='豪雅', yahoo='7741.T', country='日本', exchange='TSE', ccy='JPY', sector='Technology', industry='光掩膜基板/精密光学', moat='半导体光掩膜基板与硬盘玻璃基板利基垄断', score=3),
    '8766.T': dict(name='东京海上控股', yahoo='8766.T', country='日本', exchange='TSE', ccy='JPY', sector='Financials', industry='保险', moat='日本保险业龙头,浮存金逻辑', score=3),
    '4568.T': dict(name='第一三共', yahoo='4568.T', country='日本', exchange='TSE', ccy='JPY', sector='Health Care', industry='创新药/ADC', moat='抗体偶联药物(ADC)技术授权管线,全球license-out收入', score=2),
    '8001.T': dict(name='伊藤忠商事', yahoo='8001.T', country='日本', exchange='TSE', ccy='JPY', sector='Industrials', industry='综合商社', moat='Buffett/Berkshire实际持仓的五大商社之一,业务组合多元化', score=3),
    '8058.T': dict(name='三菱商事', yahoo='8058.T', country='日本', exchange='TSE', ccy='JPY', sector='Industrials', industry='综合商社', moat='Buffett/Berkshire实际持仓的五大商社之一,资源+贸易组合', score=3),
    '7974.T': dict(name='任天堂', yahoo='7974.T', country='日本', exchange='TSE', ccy='JPY', sector='Communications', industry='游戏/娱乐IP', moat='独特游戏IP护城河,现金充裕且几乎零负债', score=3),
    'ABI.BR': dict(name='百威英博', yahoo='ABI.BR', country='比利时', exchange='Euronext Brussels', ccy='EUR', sector='Consumer Staples', industry='啤酒', moat='全球最大啤酒集团,品牌矩阵(百威/科罗娜/时代等)+全球分销网络规模效应;SABMiller并购后杠杆一度偏高,近年持续去杠杆,现金流改善', score=3),
    'RACE.MI': dict(name='法拉利', yahoo='RACE.MI', country='意大利', exchange='Borsa Italiana/NYSE', ccy='EUR', sector='Consumer Discretionary', industry='豪华跑车', moat='严格控产驱动的极致稀缺性与定价权,行业最高毛利率,逻辑近似爱马仕但估值更高;注:控股主体Ferrari N.V.注册于荷兰,品牌/总部/研发与生产核心均在意大利马拉内罗,按此归类意大利', score=4),
    'G.MI': dict(name='忠利保险', yahoo='G.MI', country='意大利', exchange='Borsa Italiana', ccy='EUR', sector='Financials', industry='保险', moat='意大利/欧洲主要保险集团之一,浮存金逻辑与巴菲特偏好契合;意大利主权风险溢价与历史欧债包袱需关注,故信心分适度保守', score=2),
    'NOVO-B.CO': dict(name='诺和诺德', yahoo='NOVO-B.CO', country='丹麦', exchange='Nasdaq Copenhagen', ccy='DKK', sector='Health Care', industry='糖尿病/减重药物', moat='GLP-1类降糖/减重药物全球龙头(Ozempic/Wegovy),制造规模与专利先发优势构筑护城河;2024-2025年因礼来等竞争加剧及部分临床数据不及预期,估值已从高位大幅回落,波动性需关注', score=4),
    'CRH': dict(name='CRH建材集团', yahoo='CRH', country='爱尔兰', exchange='NYSE(原都柏林)', ccy='USD', sector='Materials', industry='建材/骨料', moat='全球最大建材与骨料公司之一,区域采石场资源与许可壁垒形成天然区域性护城河;起家于爱尔兰,2023年将主要上市地迁至纽约证交所', score=3),
    'KRZ.IR': dict(name='凯瑞集团', yahoo='KRZ.IR', country='爱尔兰', exchange='Euronext Dublin', ccy='EUR', sector='Consumer Staples', industry='食品配料/风味科技', moat='全球领先食品配料与风味科技公司,深度嵌入客户产品配方研发流程,转换成本高,近似隐形冠军型护城河', score=3),
}

# Merge in the English text. Kept in a separate module so the dict above stays
# readable and a translation can be reviewed on its own.
#
# A ticker absent from TRANSLATIONS falls back to its Chinese text rather than to
# an empty string: an untranslated row is obvious to a reader and harmless, while
# a blank one looks like missing data.
from universe_en import TRANSLATIONS as _EN, COUNTRIES as _EN_COUNTRY, EXCHANGES as _EN_EXCH

for _ticker, _entry in UNIVERSE.items():
    _t = _EN.get(_ticker, {})
    _entry["name_en"] = _t.get("name") or _entry["name"]
    _entry["industry_en"] = _t.get("industry") or _entry["industry"]
    _entry["moat_en"] = _t.get("moat") or _entry["moat"]
    _entry["country_en"] = _EN_COUNTRY.get(_entry["country"], _entry["country"])
    _entry["exchange_en"] = _EN_EXCH.get(_entry["exchange"], _entry["exchange"])

# Yahoo FX pairs: value = USD per 1 unit of the currency
FX_PAIRS = {c: c + "USD=X" for c in sorted({v["ccy"] for v in UNIVERSE.values()} - {NUMERAIRE})}


def price_divisor(ticker):
    """
    How many quote units make one unit of the listing's currency.

    London is the reason this exists. The LSE quotes ordinary shares in **pence**
    (GBX, 100 to the pound) and Yahoo passes that straight through, so AstraZeneca
    comes back as 11708 — which is £117.08, not £11,708. Nothing in the response
    says so: the batched download returns bare numbers, and `ccy` in this table
    says GBP because GBP is genuinely the currency. The quote is simply in a
    different unit from the currency it is denominated in.

    Left uncorrected this is quietly poisonous. It does NOT move the index NAV,
    because the same wrong price is used to decide how many shares to buy and to
    value them afterwards, so the error cancels — which is exactly why it can sit
    there for a long time looking fine. What it does corrupt is every number that
    depends on the price ALONE: the share counts (a hundred times too few), the
    shares-to-target arithmetic, and above all the market value of a real
    position a user has typed in from a broker statement, which comes out a
    hundred times too large.

    Keyed on the Yahoo symbol rather than the exchange name, because the `.L`
    suffix is what actually decides Yahoo's behaviour, and paired with the GBP
    check so that a dollar- or euro-denominated London line would not be caught
    by it.
    """
    meta = UNIVERSE[ticker]
    if meta["yahoo"].endswith(".L") and meta["ccy"] == "GBP":
        return 100.0
    return 1.0


def pence_quoted():
    """The tickers price_divisor() applies to. Used by the database migration."""
    return sorted(t for t in UNIVERSE if price_divisor(t) != 1.0)

_TOTAL_SCORE = sum(v["score"] for v in UNIVERSE.values())

def target_weights():
    return {t: v["score"] / _TOTAL_SCORE for t, v in UNIVERSE.items()}

def yahoo_symbols():
    return [v["yahoo"] for v in UNIVERSE.values()]

def all_symbols_for(ticker):
    """Primary Yahoo symbol plus any known fallbacks.

    Exchanges rename or retire symbols (Roche moved off the old ROG.SW,
    for example). Listing alternates lets a fetch recover automatically instead
    of permanently dropping a constituent.
    """
    v = UNIVERSE[ticker]
    out = [v["yahoo"]] + list(v.get("alts", []))
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq

def yahoo_symbols_with_alts():
    """Every symbol worth requesting, plus reverse map back to our tickers."""
    syms, rev = [], {}
    for t in UNIVERSE:
        for s in all_symbols_for(t):
            syms.append(s)
            rev.setdefault(s, t)
    return syms, rev

def yahoo_to_ticker():
    return {v["yahoo"]: t for t, v in UNIVERSE.items()}

CURRENCIES = sorted({v["ccy"] for v in UNIVERSE.values()})
