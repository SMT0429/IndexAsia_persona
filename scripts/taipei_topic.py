"""
taipei_topic.py
輸入：taipei_personas_3000_value.xlsx（23 欄）
輸出：taipei_personas_3000_topic.xlsx（23 + 2 = 25 欄）

新增欄位：
  關注議題     str  1–3 個議題類別完整名稱，以「、」分隔
  關注子議題   str  對應每個類別中隨機抽取的 1 個代表子議題，以「、」分隔

理論基礎：後物質主義、生命歷程理論、議程設定、政治社會化、Schwartz 價值觀
詳細方法論：method/topic_column_methodology.md
"""

import pandas as pd
import numpy as np
from collections import Counter

from pipeline_common import read_stage, write_stage

# 刻意保留舊式全域種子（np.random.seed + randint/choice）；
# 換成 default_rng 會改變抽樣序列→改變輸出。
np.random.seed(42)

df = read_stage("value")

# ── 議題代號、類別全名、代表子議題 ────────────────────────────────────────────

ISSUES = ['ECO', 'HSG', 'XS', 'ENV', 'WEL', 'EDU', 'SOC', 'GOV']

ISSUE_LABELS = {
    'ECO': '經濟 / 就業',
    'HSG': '居住 / 房價',
    'XS':  '兩岸 / 國安',
    'ENV': '環境 / 能源',
    'WEL': '社福 / 長照',
    'EDU': '教育 / 人才',
    'SOC': '社會進步',
    'GOV': '政治 / 治理',
}

ISSUE_SUBISSUES = {
    'ECO': ['薪資停滯', '通貨膨脹', '失業', '產業轉型'],
    'HSG': ['房價高漲', '囤房稅', '社會住宅', '租屋市場'],
    'XS':  ['兩岸關係', '國防預算', '主權認同'],
    'ENV': ['空汙', '核電存廢', '淨零排放', '氣候變遷'],
    'WEL': ['老人照護', '健保財務', '年金改革', '少子化'],
    'EDU': ['教育改革', '技職教育', '少子化衝擊', 'AI 教育'],
    'SOC': ['婚姻平權', '性別平等', '移工政策', '身心障礙'],
    'GOV': ['司法改革', '反腐', '媒體自由', '選制改革'],
}

# ── 主函式 ────────────────────────────────────────────────────────────────────

def compute_issue_weights(row):
    w = {issue: 1.0 for issue in ISSUES}

    # 年齡組效果（生命歷程理論）
    age_group = row['年齡組']
    age_boosts = {
        '15–24歲': {'HSG': 1.5, 'EDU': 1.5, 'ECO': 1.3, 'SOC': 1.2},
        '25–34歲': {'HSG': 2.0, 'ECO': 1.5, 'EDU': 1.3},
        '35–44歲': {'ECO': 1.5, 'GOV': 1.3, 'ENV': 1.2},
        '45–54歲': {'WEL': 1.8, 'ECO': 1.4, 'XS': 1.3},
        '55–64歲': {'WEL': 1.8, 'XS': 1.5, 'ECO': 1.3},
        '65歲以上': {'WEL': 2.0, 'XS': 1.8, 'ECO': 1.2},
    }
    for issue, boost in age_boosts.get(age_group, {}).items():
        w[issue] *= boost

    # 教育程度效果（後物質主義）
    edu = row['教育程度']
    if edu in ['碩士以上', '大學']:
        for issue in ['ENV', 'SOC', 'GOV']:
            w[issue] *= 1.5
    elif edu in ['國中以下', '小學以下']:
        for issue in ['ECO', 'WEL', 'XS']:
            w[issue] *= 1.4

    # 收入效果（物質主義梯度）
    income = str(row['月收入區間'])
    high_income = ['15~25萬', '25萬以上', '10~15萬']
    low_income  = ['4萬以下']
    if any(h in income for h in high_income):
        for issue in ['ENV', 'GOV', 'SOC']:
            w[issue] *= 1.3
    elif any(l in income for l in low_income):
        for issue in ['ECO', 'WEL']:
            w[issue] *= 1.5

    # 政黨傾向效果（TEDS 議題立場資料）
    party = row['政黨傾向']
    party_boosts = {
        '民進黨':     {'XS': 1.6, 'GOV': 1.3, 'SOC': 1.3},
        '國民黨':     {'XS': 1.4, 'ECO': 1.3, 'WEL': 1.2},
        '台灣民眾黨': {'GOV': 1.5, 'ECO': 1.4, 'HSG': 1.3},
        '時代力量':   {'GOV': 1.6, 'SOC': 1.5, 'ENV': 1.3},
    }
    for issue, boost in party_boosts.get(party, {}).items():
        w[issue] *= boost

    # 社會價值觀主類型效果（Schwartz 橋接）
    val_type = row['社會價值觀_主類型']
    value_boosts = {
        '傳統守望型': {'WEL': 1.4, 'XS': 1.3, 'ECO': 1.2},
        '秩序菁英型': {'GOV': 1.4, 'ECO': 1.3, 'XS': 1.2},
        '自主競爭型': {'EDU': 1.4, 'ECO': 1.3, 'GOV': 1.2},
        '開放關懷型': {'ENV': 1.4, 'SOC': 1.3, 'WEL': 1.2},
    }
    for issue, boost in value_boosts.get(val_type, {}).items():
        w[issue] *= boost

    # 媒體習慣效果（議程設定理論）
    media = str(row['媒體習慣'])
    if 'YouTube' in media:
        for issue in ['ENV', 'SOC', 'EDU']:
            w[issue] *= 1.2
    if 'LINE' in media:
        for issue in ['XS', 'WEL']:
            w[issue] *= 1.2
    if 'Instagram' in media:
        for issue in ['SOC', 'HSG']:
            w[issue] *= 1.2

    # 世代效果（政治社會化理論，Mannheim 1952；使用 M 欄實際世代標籤）
    generation_boosts = {
        '威權/解嚴世代':         {'GOV': 1.4, 'XS': 1.3},
        '本土化世代':            {'XS': 1.4, 'ECO': 1.3},
        '民主轉型世代':          {'GOV': 1.3, 'XS': 1.2, 'ECO': 1.2},
        '公民運動世代':          {'GOV': 1.5, 'SOC': 1.3},
        '社群網路/抗中保台世代':  {'XS': 1.5, 'GOV': 1.3},
        'AI與短影音世代':        {'ECO': 1.4, 'GOV': 1.2, 'HSG': 1.3},
    }
    for issue, boost in generation_boosts.get(row['政治與歷史印記_世代'], {}).items():
        w[issue] *= boost

    return w


def assign_issues(row, n_issues_range=(1, 3)):
    w = compute_issue_weights(row)
    issues  = list(w.keys())
    weights = np.array([w[i] for i in issues])
    weights = weights / weights.sum()

    n = np.random.randint(n_issues_range[0], n_issues_range[1] + 1)
    chosen_codes = np.random.choice(issues, size=n, replace=False, p=weights)

    labels    = '、'.join(ISSUE_LABELS[c] for c in chosen_codes)
    subissues = '、'.join(
        np.random.choice(ISSUE_SUBISSUES[c]) for c in chosen_codes
    )
    return labels, subissues


# ── 賦值 ───────────────────────────────────────────────────────────────────────

df[['關注議題', '關注子議題']] = pd.DataFrame(
    df.apply(assign_issues, axis=1).tolist(), index=df.index
)

# ── 分布驗證 ───────────────────────────────────────────────────────────────────

all_labels  = [label for s in df['關注議題'] for label in s.split('、')]
label_counts = Counter(all_labels)

print("議題分布：")
for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
    pct = count / len(df) * 100
    print(f"  {label}: {count} ({pct:.1f}%)")

# ── 輸出 ───────────────────────────────────────────────────────────────────────

out = write_stage(df, "topic")
print(f"\n已輸出：{out}（{len(df)} 筆，{len(df.columns)} 欄）")
