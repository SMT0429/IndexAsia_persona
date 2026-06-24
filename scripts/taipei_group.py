import numpy as np
import pandas as pd

from pipeline_common import read_stage, write_stage, make_rng, AGE_GROUP_LABELS, PROFILE

df = read_stage("religion")

ETHNICITIES = ['閩南', '客家', '外省', '原住民']

# 台北市基準比例（客委會 110 年調查 + 學術調整，§4）
BASE = {
    '閩南':   0.680,
    '客家':   0.174,
    '外省':   0.110,
    '原住民': 0.020,
    # 其他/新住民 0.016 不列入輸出類別，透過正規化吸收
}

# 外省比例年齡調整乘數（§5.1）
AGE_WAISHENG_MULT = {
    '65歲以上': 2.5,
    '55–64歲':  1.8,
    '45–54歲':  1.2,
    '35–44歲':  0.8,
    '25–34歲':  0.5,
    '15–24歲':  0.3,
}

# 外省比例居住地調整乘數（§5.2，葉高華 1966 年人口普查地理分布）
DISTRICT_WAISHENG_MULT = {
    '中正區': 1.4,
    '大安區': 1.4,
    '北投區': 1.3,
    '士林區': 1.2,
    '信義區': 1.1,
    '中山區': 1.1,
    '松山區': 1.0,
    '內湖區': 0.9,
    '文山區': 0.9,
    '南港區': 0.9,
    '萬華區': 0.7,
    '大同區': 0.7,
}

# 政黨調整乘數：(外省乘數, 閩南乘數)（§5.3，吳乃德 2002）
PARTY_MULT = {
    '國民黨':    (1.6, 0.85),
    '民進黨':    (0.4, 1.15),
    '台灣民眾黨': (0.8, 1.00),
    '其他政黨':  (0.9, 1.00),
}

WAISHENG_MAX  = 0.60
MINNAN_MIN    = 0.15
PROB_FLOOR    = 0.001


def assign_ethnicity(age_group: str, district: str, party: str, rng) -> str:
    probs = dict(BASE)

    # 步驟 2：年齡調整（外省↑/↓，閩南反向）
    w_age = min(probs['外省'] * AGE_WAISHENG_MULT[age_group], WAISHENG_MAX)
    delta = w_age - probs['外省']
    probs['外省'] = w_age
    probs['閩南'] = max(probs['閩南'] - delta, MINNAN_MIN)

    # 步驟 3：居住地調整（外省↑/↓，閩南反向）
    w_dist = min(probs['外省'] * DISTRICT_WAISHENG_MULT[district], WAISHENG_MAX)
    delta = w_dist - probs['外省']
    probs['外省'] = w_dist
    probs['閩南'] = max(probs['閩南'] - delta, MINNAN_MIN)

    # 步驟 4：政黨調整（外省＆閩南乘法修正）
    w_mult, m_mult = PARTY_MULT[party]
    probs['外省'] = probs['外省'] * w_mult
    probs['閩南'] = probs['閩南'] * m_mult

    # 步驟 5：邊界條件 + 正規化
    for k in ETHNICITIES:
        probs[k] = max(probs[k], PROB_FLOOR)
    probs['外省'] = min(probs['外省'], WAISHENG_MAX)
    probs['閩南'] = max(probs['閩南'], MINNAN_MIN)

    total = sum(probs[e] for e in ETHNICITIES)
    p = np.array([probs[e] / total for e in ETHNICITIES])

    return rng.choice(ETHNICITIES, p=p)


rng = make_rng()

if PROFILE == 'taiwan':
    # 全台版：直接讀 ethnic_base.csv 各縣市 {閩南,客家,外省,原住民} 比例（methodology §4），
    # 依 persona 居住縣市抽樣（地理已內含於縣市比例，不再疊台北式行政區乘數）。
    import region_profile as rp
    eth = rp.load_ethnic_base()

    def _assign_taiwan(region: str) -> str:
        p = np.array([eth.loc[region, e] for e in ETHNICITIES], dtype=float)
        return rng.choice(ETHNICITIES, p=p / p.sum())

    df['族群'] = df['居住地'].apply(_assign_taiwan)
else:
    df['族群'] = df.apply(
        lambda row: assign_ethnicity(row['年齡組'], row['居住地'], row['政黨傾向'], rng),
        axis=1,
    )

# ── 驗證輸出 ──────────────────────────────────────────────
print("=== 整體分布 ===")
dist = df['族群'].value_counts(normalize=True).reindex(ETHNICITIES)
print(dist.round(3))

print("\n=== 年齡組 × 族群交叉表 ===")
cross = pd.crosstab(
    df['年齡組'],
    df['族群'],
    normalize='index',
)[ETHNICITIES].reindex(AGE_GROUP_LABELS).round(3)
print(cross)

print("\n=== 居住地 × 外省比例 ===")
district_cross = (
    df.groupby('居住地')['族群']
    .apply(lambda x: (x == '外省').mean())
    .round(3)
    .sort_values(ascending=False)
)
print(district_cross)

out = write_stage(df, "group")
print(f"\n✅ 完成，已輸出至 {out}（18 欄）")
