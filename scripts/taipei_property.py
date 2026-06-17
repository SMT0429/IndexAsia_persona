"""
taipei_property.py
輸入：taipei_personas_3000_clan.xlsx（29 欄）
輸出：taipei_personas_3000_property.xlsx（29 + 1 = 30 欄）

新增欄位：
  房產持有狀態   str  A/B/C/D → 自有（本人/配偶）/ 自有（家人名義）/ 租屋 / 借住/配住

依賴欄位：年齡組、月收入區間、婚姻狀況
  （v1.1，2026-06-10：依方法論移除「族群」特殊調整。人口及住宅普查不含
   外省/閩南族群欄位，無數據支撐；族群與年齡欄位不再納入本欄條件調整。）
  （v1.3，2026-06-10：新增 '15–24歲' 獨立年齡乘數鍵，A（自有本人）乘數降為
   0.05，修正青年以本人名義持有房產之不合理。依 QA consistency_check issue 6。）

資料基準：
  台北市 109 年人口及住宅普查 + 家庭收支調查 + 政大不動產研究中心
詳細方法論：method/property_column_methodology.md
"""

import numpy as np
import pandas as pd

from pipeline_common import read_stage, write_stage

df = read_stage("clan")

# ── 類別定義 ──────────────────────────────────────────────────────────────────
CATEGORIES = ['自有（本人/配偶）', '自有（家人名義）', '租屋', '借住/配住']

# ── 台北市底層基準分布（109 年普查 + 推算） ────────────────────────────────────
BASE = np.array([0.72, 0.06, 0.18, 0.04])

# ── 年齡乘數（方法論表 3.2，資料年齡組映射至乘數表） ────────────────────────────
# 資料年齡組 → 方法論乘數鍵值
# QA issue 6：15–24 歲（多為學生／社會新鮮人、未婚、低收）以本人名義持有房產
#   在台北房價下不合理，獨立出 '15–24歲' 鍵並大幅壓低 A（自有本人），導向
#   B（家人名義）／C（租屋）／D（借住/配住）。25–34 歲仍沿用 20–29歲 乘數。
AGE_KEY_MAP = {
    '15–24歲': '15–24歲',
    '25–34歲': '20–29歲',
    '35–44歲': '30–39歲',
    '45–54歲': '40–54歲',
    '55–64歲': '55–64歲',
    '65歲以上': '65歲以上',
}

AGE_MULT = {
    '15–24歲': np.array([0.05, 1.8, 2.2, 1.8]),  # QA issue 6：A 機率趨近 0
    '20–29歲': np.array([0.3, 1.5, 2.2, 1.5]),
    '30–39歲': np.array([0.7, 1.2, 1.4, 1.0]),
    '40–54歲': np.array([1.1, 0.8, 0.8, 0.8]),
    '55–64歲': np.array([1.2, 0.9, 0.6, 0.7]),
    '65歲以上': np.array([1.2, 1.0, 0.4, 1.2]),
}

# ── 收入乘數（方法論表 3.3，映射資料收入標籤） ────────────────────────────────
# 資料標籤：4萬以下、4~6萬、6~10萬、10~15萬、15~25萬、25萬以上
# '4萬以下' 跨越未滿3萬 & 3~6萬，取兩段平均
INCOME_MULT = {
    '4萬以下':  (np.array([0.3, 1.2, 2.0, 1.8]) + np.array([0.6, 1.3, 1.5, 1.2])) / 2,
    '4~6萬':   np.array([0.6, 1.3, 1.5, 1.2]),
    '6~10萬':  np.array([1.0, 1.0, 1.0, 0.7]),
    '10~15萬': np.array([1.2, 0.8, 0.7, 0.5]),
    '15~25萬': np.array([1.4, 0.6, 0.5, 0.4]),
    '25萬以上': np.array([1.4, 0.6, 0.5, 0.4]),
}

# ── 婚姻乘數（方法論表 3.4，資料只有已婚/未婚） ──────────────────────────────
MARITAL_MULT = {
    '已婚': np.array([1.3, 0.9, 0.7, 0.6]),
    '未婚': np.array([0.7, 1.1, 1.5, 1.3]),
}


def sample_housing_status(row: pd.Series) -> str:
    age_group = str(row.get('年齡組', ''))
    income    = str(row.get('月收入區間', ''))
    marital   = str(row.get('婚姻狀況', ''))
    pid       = int(row.get('id', 0))

    age_key = AGE_KEY_MAP.get(age_group, '40–54歲')

    am = AGE_MULT.get(age_key, np.ones(4))
    im = INCOME_MULT.get(income, np.ones(4))
    mm = MARITAL_MULT.get(marital, np.ones(4))

    weights = BASE * am * im * mm
    weights = weights / weights.sum()

    rng = np.random.default_rng(pid)
    return rng.choice(CATEGORIES, p=weights)


# ── 賦值 ──────────────────────────────────────────────────────────────────────
df['房產持有狀態'] = df.apply(sample_housing_status, axis=1)

# ── 分布驗證 ──────────────────────────────────────────────────────────────────
print("=== 房產持有狀態分布 ===")
counts = df['房產持有狀態'].value_counts()
for cat in CATEGORIES:
    n = counts.get(cat, 0)
    pct = n / len(df) * 100
    print(f"  {cat:<14} {n:4d}  ({pct:.1f}%)")

total_owned = counts.get('自有（本人/配偶）', 0) + counts.get('自有（家人名義）', 0)
print(f"\n  自有合計（A+B）：{total_owned} ({total_owned/len(df)*100:.1f}%)  目標 72–78%")

print("\n=== 婚姻狀況 × 房產持有狀態 ===")
print(df.groupby('婚姻狀況')['房產持有狀態'].value_counts(normalize=True).round(3).to_string())

# ── 輸出 ──────────────────────────────────────────────────────────────────────
out = write_stage(df, "property")
print(f"\n已輸出：{out}（{len(df)} 筆，{len(df.columns)} 欄）")
