# -*- coding: utf-8 -*-
"""
English text for the 78 constituents.

Kept in its own file rather than inlined into `universe.py` for two reasons: the
dict literal there is already long enough to be hard to read, and a translation
is the kind of thing someone may want to review or correct on its own, without
scrolling past scores and exchange codes to do it.

`universe.py` merges these in at import time. A ticker missing from here falls
back to its Chinese text rather than showing an empty cell, so a half-finished
translation degrades to "untranslated" instead of "blank".
"""

# Country names, and the one exchange string that carries a Chinese annotation.
COUNTRIES = {
    '美国': 'United States', '加拿大': 'Canada', '英国': 'United Kingdom',
    '法国': 'France', '德国': 'Germany', '荷兰': 'Netherlands',
    '瑞士': 'Switzerland', '日本': 'Japan', '比利时': 'Belgium',
    '意大利': 'Italy', '丹麦': 'Denmark', '爱尔兰': 'Ireland',
}

EXCHANGES = {
    'NYSE(原都柏林)': 'NYSE (formerly Dublin)',
}

TRANSLATIONS = {
    # ---------------------------------------------------------- United States
    'BRK.B': dict(name='Berkshire Hathaway', industry='Diversified insurance holding',
                  moat='Buffett himself. Insurance float plus capital allocation across industries; incoming CEO Greg Abel continues the same discipline'),
    'AAPL': dict(name='Apple', industry='Consumer electronics / ecosystem',
                 moat='iOS ecosystem lock-in and brand loyalty. Berkshire\'s largest single equity position'),
    'MSFT': dict(name='Microsoft', industry='Enterprise software / cloud',
                 moat='High switching costs for enterprise customers, plus the Azure infrastructure moat (an aggressive relaxation of the criteria)'),
    'BAC': dict(name='Bank of America', industry='Retail / commercial banking',
                moat='Long-standing Buffett holding. Moat is deposit scale and branch network'),
    'AXP': dict(name='American Express', industry='Credit cards / payments',
                moat='A classic long-term Buffett holding: payment network plus a brand premium among affluent customers'),
    'MCO': dict(name='Moody\'s', industry='Credit ratings',
                moat='One of the ratings duopoly. A long-standing large Buffett position'),
    'V': dict(name='Visa', industry='Payment network',
              moat='Asset-light, high-margin global payment network effects'),
    'MA': dict(name='Mastercard', industry='Payment network',
               moat='Forms the payments duopoly together with Visa'),
    'SPGI': dict(name='S&P Global', industry='Ratings / indices / data',
                 moat='A double moat: credit ratings and index data'),
    'KO': dict(name='Coca-Cola', industry='Beverages',
               moat='Buffett\'s signature holding. Global brand and distribution moat'),
    'PG': dict(name='Procter & Gamble', industry='Household consumer goods',
               moat='A portfolio of brands, pricing power and scale'),
    'COST': dict(name='Costco', industry='Membership warehouse retail',
                 moat='Membership-fee business model. Long admired by Munger'),
    'MCD': dict(name='McDonald\'s', industry='Restaurant franchising',
                moat='A double moat of franchising and real estate'),
    'JNJ': dict(name='Johnson & Johnson', industry='Diversified healthcare',
                moat='Diversified product lines and exceptionally stable cash flow (a dividend aristocrat)'),
    'UNH': dict(name='UnitedHealth', industry='Managed care health insurance',
                moat='Buffett holding. Scale economics in managed care (recent regulatory and medical-cost pressure worth watching)'),
    'UNP': dict(name='Union Pacific', industry='Freight rail',
                moat='Half of the North American rail duopoly. Infrastructure moat with very high barriers to entry'),
    'WM': dict(name='Waste Management', industry='Solid waste',
               moat='Regional barriers around waste handling and landfill permits'),
    'CVX': dict(name='Chevron', industry='Integrated oil and gas',
                moat='Buffett holding. Integrated energy major with a solid balance sheet'),
    'OXY': dict(name='Occidental Petroleum', industry='Oil and gas production',
                moat='Large Buffett position. Low-cost Permian Basin resources'),
    'AMT': dict(name='American Tower', industry='Communications tower REIT',
                moat='Rent-collecting tower infrastructure with long leases (a REIT — FFO is the more appropriate valuation measure)'),
    'GOOGL': dict(name='Alphabet (Google)', industry='Search / advertising / cloud',
                  moat='Monopoly-grade moat in search. A recent new Berkshire position; first dividend paid from 2024'),
    'NEE': dict(name='NextEra Energy', industry='Regulated utility + renewables',
                moat='Regulated utility cash flow plus a leading position in renewables'),

    # ---------------------------------------------------------------- Canada
    'CSU.TO': dict(name='Constellation Software', industry='Vertical market software',
                   moat='Acquires and consolidates vertical software assets; a model of long-term compounding (Mark Leonard-style capital allocation)'),
    'RY.TO': dict(name='Royal Bank of Canada', industry='Universal bank',
                  moat='Canada\'s oligopolistic banking system, with very high regulatory barriers'),
    'ATD.TO': dict(name='Alimentation Couche-Tard', industry='Convenience stores',
                   moat='The consolidator of the convenience store sector, with excellent capital allocation discipline'),
    'QSR.TO': dict(name='Restaurant Brands International', industry='Restaurant franchising',
                   moat='Burger King / Tim Hortons / Popeyes franchise portfolio (3G Capital heritage)'),
    'CNR.TO': dict(name='Canadian National Railway', industry='Freight rail',
                   moat='The other half of the North American rail duopoly. Very high barriers to entry'),
    'TRI': dict(name='Thomson Reuters', industry='Professional information and compliance data',
                moat='Subscription professional information with strong customer stickiness (same logic as S&P Global\'s ratings and data)'),
    'CNQ.TO': dict(name='Canadian Natural Resources', industry='Oil sands / conventional oil and gas',
                   moat='Low-cost, long-life oil sands reserves with steady free cash flow'),
    'NTR.TO': dict(name='Nutrien', industry='Potash / agricultural inputs',
                   moat='The world\'s largest potash producer. Moat rests on resource endowment'),
    'FTS.TO': dict(name='Fortis Inc', industry='Regulated electricity / gas',
                   moat='Fifty consecutive years of dividend growth, on regulated utility cash flow'),

    # ------------------------------------------------------ United Kingdom
    'HSBA.L': dict(name='HSBC Holdings', industry='Global banking',
                   moat='Global trade finance network with substantial Asian exposure'),
    'DGE.L': dict(name='Diageo', industry='Spirits',
                  moat='A portfolio of spirits brands with strong pricing power'),
    'ULVR.L': dict(name='Unilever', industry='Household consumer goods',
                   moat='Global portfolio of household consumer brands'),
    'AZN.L': dict(name='AstraZeneca', industry='Innovative pharmaceuticals',
                  moat='Patent moat across the oncology and rare disease pipeline'),
    'BA.L': dict(name='BAE Systems', industry='Defence equipment',
                 moat='Long-running UK and US defence contracts with sticky government customers (a moderate relaxation of Buffett\'s traditional preferences)'),
    'RIO.L': dict(name='Rio Tinto', industry='Diversified mining',
                  moat='Low-cost iron ore resource endowment'),
    'SGRO.L': dict(name='Segro Plc', industry='Logistics property REIT',
                   moat='Logistics property benefiting from structural growth in e-commerce (a REIT — FFO is the more appropriate valuation measure)'),
    'NG.L': dict(name='National Grid', industry='Regulated transmission and distribution',
                 moat='Monopoly franchise over transmission and distribution networks'),
    'ARM': dict(name='Arm Holdings', industry='Chip architecture IP',
                moat='Near-monopoly licensing model for mobile chip architecture; a chokepoint in the supply chain (valuation is rich — watch the risk). A UK company, but trades as ADSs in US dollars on Nasdaq, hence USD'),

    # ---------------------------------------------------------------- France
    'RMS.PA': dict(name='Hermès', industry='Luxury goods',
                   moat='Pricing power driven by extreme scarcity; a brand that essentially never discounts'),
    'MC.PA': dict(name='LVMH', industry='Luxury goods group',
                  moat='Multi-brand luxury portfolio with scale and distribution advantages'),
    'OR.PA': dict(name='L\'Oréal', industry='Beauty',
                  moat='Global category leader in beauty, with a double moat of R&D and distribution'),
    'RI.PA': dict(name='Pernod Ricard', industry='Spirits',
                  moat='Global spirits brand portfolio (recent emerging-market demand volatility worth watching)'),
    'SAN.PA': dict(name='Sanofi', industry='Pharmaceuticals / vaccines',
                   moat='Patent portfolio across vaccines and specialty medicines'),
    'SU.PA': dict(name='Schneider Electric', industry='Electrification / energy efficiency equipment',
                  moat='Installed base of electrification and energy-efficiency equipment, meeting long-term structural demand'),
    'TTE.PA': dict(name='TotalEnergies', industry='Integrated energy',
                   moat='Integrated energy major with a solid balance sheet'),
    'AI.PA': dict(name='Air Liquide', industry='Industrial gases',
                  moat='Industrial gas pipeline infrastructure, with extremely high customer switching costs'),
    'DSY.PA': dict(name='Dassault Systèmes', industry='Engineering simulation software',
                   moat='Highly sticky engineering simulation and PLM software on subscription revenue'),

    # --------------------------------------------------------------- Germany
    'SAP': dict(name='SAP', industry='Enterprise ERP software',
                moat='Extremely high switching costs for enterprise ERP, with the cloud transition going well'),
    'ALV.DE': dict(name='Allianz', industry='Insurance / asset management',
                   moat='One of Europe\'s largest insurers; the float logic is close to Buffett\'s preference'),
    'DB1.DE': dict(name='Deutsche Börse', industry='Exchange infrastructure',
                   moat='Exchange and clearing infrastructure — close to a toll-booth business model'),
    'SIE.DE': dict(name='Siemens', industry='Diversified industrial technology',
                   moat='Diversified industrial technology group combining automation and infrastructure'),
    'BAS.DE': dict(name='BASF', industry='Diversified chemicals',
                   moat='Integrated chemical production network (Verbund); noticeably cyclical (a moderate relaxation)'),
    'DTE.DE': dict(name='Deutsche Telekom', industry='Telecommunications',
                   moat='Controls T-Mobile US; subscriber stickiness and scale effects'),

    # ----------------------------------------------------------- Netherlands
    'ASML': dict(name='ASML', industry='Semiconductor equipment',
                 moat='Sole global supplier of EUV lithography machines; a critical node in the semiconductor supply chain (the aggressive relaxation from the original brief)'),
    'HEIA.AS': dict(name='Heineken', industry='Brewing',
                    moat='Global beer brand portfolio with stable family governance'),
    'WKL.AS': dict(name='Wolters Kluwer', industry='Regulatory and compliance information',
                   moat='Subscription moat in legal, tax and medical compliance information'),

    # ---------------------------------------------------------- Switzerland
    'NESN.SW': dict(name='Nestlé', industry='Food and beverage',
                    moat='The world\'s largest food and beverage group, with an exceptionally broad brand portfolio (a position the owner already holds)'),
    'RO.SW': dict(name='Roche', industry='Pharmaceuticals / diagnostics',
                  moat='Patent moat in oncology and diagnostics, with synergy between the two (RO.SW is the SIX registered share; the ROP.SW participation certificate is a different security — do not mix cost basis between them)'),
    'NOVN.SW': dict(name='Novartis', industry='Innovative pharmaceuticals',
                    moat='Patented drug pipeline, re-rated after refocusing on core therapeutic areas'),
    'UBSG.SW': dict(name='UBS Group', industry='Wealth management / investment banking',
                    moat='Swiss wealth management leader, with scale extended by the Credit Suisse integration (execution risk worth watching)'),
    'ZURN.SW': dict(name='Zurich Insurance', industry='Insurance',
                    moat='Insurance float logic with good capital allocation discipline'),
    'ABBN.SW': dict(name='ABB', industry='Electrification / industrial automation',
                    moat='Electrification and industrial automation equipment, benefiting from the long-term electrification trend'),

    # ----------------------------------------------------------------- Japan
    '8035.T': dict(name='Tokyo Electron', industry='Semiconductor equipment',
                   moat='One of the front-end semiconductor equipment oligopoly; a critical node in the supply chain'),
    '6861.T': dict(name='Keyence', industry='Industrial sensors / automation',
                   moat='Very high margins in industrial sensors and machine vision, on an asset-light direct sales model'),
    '7741.T': dict(name='Hoya', industry='Photomask blanks / precision optics',
                   moat='Niche monopoly in semiconductor photomask blanks and hard disk glass substrates'),
    '8766.T': dict(name='Tokio Marine Holdings', industry='Insurance',
                   moat='Japan\'s leading insurer; the float logic again'),
    '4568.T': dict(name='Daiichi Sankyo', industry='Innovative pharmaceuticals / ADC',
                   moat='Antibody-drug conjugate (ADC) technology pipeline, with global licensing-out revenue'),
    '8001.T': dict(name='Itochu', industry='General trading house',
                   moat='One of the five trading houses Berkshire actually holds; a diversified business mix'),
    '8058.T': dict(name='Mitsubishi Corporation', industry='General trading house',
                   moat='One of the five trading houses Berkshire actually holds; combines resources and trading'),
    '7974.T': dict(name='Nintendo', industry='Gaming / entertainment IP',
                   moat='A distinctive moat in game IP; cash rich with almost no debt'),

    # ---------------------------------------------------- Belgium / Italy / etc
    'ABI.BR': dict(name='Anheuser-Busch InBev', industry='Brewing',
                   moat='The world\'s largest brewer: brand portfolio (Budweiser, Corona, Stella and others) plus scale in global distribution. Leverage ran high after the SABMiller acquisition but has been coming down steadily, with improving cash flow'),
    'RACE.MI': dict(name='Ferrari', industry='Luxury sports cars',
                    moat='Extreme scarcity and pricing power from strictly controlled production, with the highest margins in the industry. Similar logic to Hermès but at a richer valuation. Note: the holding company Ferrari N.V. is registered in the Netherlands, while the brand, headquarters, R&D and production all centre on Maranello, Italy — classified as Italian on that basis'),
    'G.MI': dict(name='Generali', industry='Insurance',
                 moat='One of the major Italian and European insurers; float logic fits Buffett\'s preference. Italian sovereign risk premium and the legacy of the euro debt crisis are worth watching, hence the deliberately conservative confidence score'),
    'NOVO-B.CO': dict(name='Novo Nordisk', industry='Diabetes / weight-loss drugs',
                      moat='Global leader in GLP-1 diabetes and weight-loss drugs (Ozempic, Wegovy). Moat built on manufacturing scale and patent lead. Valuation has fallen sharply from its highs through 2024-2025 on intensifying competition from Eli Lilly and some clinical data below expectations — volatility worth watching'),
    'CRH': dict(name='CRH', industry='Building materials / aggregates',
                moat='One of the world\'s largest building materials and aggregates companies. Regional quarry resources and permitting barriers create a naturally local moat. Founded in Ireland; moved its primary listing to the New York Stock Exchange in 2023'),
    'KRZ.IR': dict(name='Kerry Group', industry='Food ingredients / taste technology',
                   moat='A world leader in food ingredients and taste technology, embedded deep in customers\' product formulation and R&D processes. High switching costs — a hidden-champion style moat'),
}
