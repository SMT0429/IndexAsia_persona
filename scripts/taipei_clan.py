"""
taipei_clan.py
輸入：taipei_personas_3000_speakingStyle.xlsx（28 欄）
輸出：taipei_personas_3000_clan.xlsx（28 + 1 = 29 欄）

新增欄位：
  宗親地方組織連結強度   float  0.0 – 10.0

理論基礎：
  劉佩怡（2009）宗族選舉動員；Wolfinger 地方人情網絡；
  台北市眷村地理分布（李廣均 2015）；客委會 110 年客家人口調查
詳細方法論：method/clan_column_methodology.md
"""

import pandas as pd
import os

INPUT  = os.path.join(os.path.dirname(__file__), "../data/taipei_personas_3000_speakingStyle.xlsx")
OUTPUT = os.path.join(os.path.dirname(__file__), "../data/taipei_personas_3000_clan.xlsx")

df = pd.read_excel(INPUT)

# ── 第一層：族群基礎分 ────────────────────────────────────────────────────────
ETHNIC_BASE = {
    '閩南': 5.0,
    '客家': 4.0,
    '外省': 2.5,
    '原住民': 2.0,
}

# ── 第二層：年齡加權 ──────────────────────────────────────────────────────────
# 資料年齡組（6 段）對應方法論加分：
#   15–24歲 → 相當於 18–29歲 (-0.5)
#   25–34歲 / 35–44歲 → 相當於 30–44歲 (+0.5)
#   45–54歲 → +1.0；55–64歲 → +1.5；65歲以上 → +2.5
AGE_BONUS = {
    '15–24歲': -0.5,
    '25–34歲':  0.5,
    '35–44歲':  0.5,
    '45–54歲':  1.0,
    '55–64歲':  1.5,
    '65歲以上': 2.5,
}

# ── 第三層：居住地加權（行政區 × 是否外省）────────────────────────────────────
# 原住民族群使用閩南／客家欄（非眷村關聯族群）
DISTRICT_BONUS = {
    ('萬華區', False):  1.5, ('萬華區', True):  0.0,
    ('大同區', False):  1.5, ('大同區', True):  0.0,
    ('士林區', False):  1.0, ('士林區', True):  1.0,
    ('北投區', False):  0.5, ('北投區', True):  1.5,
    ('信義區', False):  0.0, ('信義區', True):  1.5,
    ('松山區', False):  0.0, ('松山區', True):  1.0,
    ('中正區', False):  0.5, ('中正區', True):  1.0,
    ('文山區', False):  0.5, ('文山區', True):  0.5,
    ('大安區', False):  0.5, ('大安區', True):  0.5,
    ('中山區', False):  0.0, ('中山區', True):  0.5,
    ('南港區', False): -0.5, ('南港區', True): -0.5,
    ('內湖區', False): -0.5, ('內湖區', True): -0.5,
}


def calc_clan_score(row: pd.Series) -> float:
    ethnicity   = str(row.get('族群', ''))
    age_group   = str(row.get('年齡組', ''))
    district    = str(row.get('居住地', ''))
    is_waisheng = (ethnicity == '外省')

    base     = ETHNIC_BASE.get(ethnicity, 3.0)
    age_adj  = AGE_BONUS.get(age_group, 0.0)
    dist_adj = DISTRICT_BONUS.get((district, is_waisheng), 0.0)

    raw = base + age_adj + dist_adj
    return round(min(max(raw, 0.0), 10.0), 1)


# ── 賦值 ──────────────────────────────────────────────────────────────────────
df['宗親地方組織連結強度'] = df.apply(calc_clan_score, axis=1)

# ── 分布驗證 ──────────────────────────────────────────────────────────────────
print("=== 宗親地方組織連結強度 ===")
print(df['宗親地方組織連結強度'].describe().round(3).to_string())
print()
print(df['宗親地方組織連結強度'].value_counts().sort_index().to_string())

# ── 族群交叉驗證 ──────────────────────────────────────────────────────────────
print("\n=== 族群 × 平均分 ===")
print(df.groupby('族群')['宗親地方組織連結強度'].mean().round(2).to_string())

# ── 輸出 ──────────────────────────────────────────────────────────────────────
df.to_excel(OUTPUT, index=False)
print(f"\n已輸出：{OUTPUT}（{len(df)} 筆，{len(df.columns)} 欄）")
