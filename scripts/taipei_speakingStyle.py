"""
taipei_speakingStyle.py
輸入：taipei_personas_3000_topic.xlsx（25 欄）
輸出：taipei_personas_3000_speakingStyle.xlsx（25 + 3 = 28 欄）

新增欄位：
  說話風格_正式程度    str  高 / 中 / 低
  說話風格_溝通取向    str  迂迴集體型 / 直接個人型 / 保守傳統型 / 折衷型
  說話風格_語言切換    str  語言使用習慣描述

理論基礎：Bernstein（1971）語言精緻化、Bourdieu（1991）語言資本與語域、
          Hofstede（2001）文化維度、台灣在地世代語言與族群切換研究
詳細方法論：method/speaking_style_methodology.md
"""

import pandas as pd
import os

INPUT  = os.path.join(os.path.dirname(__file__), "../data/taipei_personas_3000_topic.xlsx")
OUTPUT = os.path.join(os.path.dirname(__file__), "../data/taipei_personas_3000_speakingStyle.xlsx")

df = pd.read_excel(INPUT)

# ── 月收入轉數值（中位數代理）─────────────────────────────────────────────────
# 使用實際資料標籤（來自 taipei_income.py INCOME_LABELS）
INCOME_MAP = {
    '4萬以下':  35000,
    '4~6萬':    50000,
    '6~10萬':   80000,
    '10~15萬': 125000,
    '15~25萬': 200000,
    '25萬以上': 300000,
}

# 正式語域職業（對應實際資料的職業類別）
HIGH_FORMAL_JOBS = {'管理/主管', '專業人員', '技術/助理專業'}


# ── 層一：Bernstein 語言精緻化程度 ──────────────────────────────────────────
def get_formality(row: pd.Series) -> str:
    edu    = str(row.get('教育程度', ''))
    income = INCOME_MAP.get(str(row.get('月收入區間', '')), 0)
    job    = str(row.get('職業', ''))

    if edu in ['碩士以上', '大學'] and income >= 60000:
        return '高'
    if edu == '大學' or job in HIGH_FORMAL_JOBS:
        return '中'
    return '低'


# ── 層三：Hofstede CO/ST 溝通取向 ────────────────────────────────────────────
def get_communication_orientation(row: pd.Series) -> str:
    co = float(row.get('社會價值觀_CO分數', 0))
    st = float(row.get('社會價值觀_ST分數', 0))

    if co > 1 and st > 1:
        return '迂迴集體型'
    if co < -1 and st < -1:
        return '直接個人型'
    if st > 2:
        return '保守傳統型'
    return '折衷型'


# ── 層四：族群 × 年齡 語言切換 ───────────────────────────────────────────────
def get_language_switch(row: pd.Series) -> str:
    ethnicity = str(row.get('族群', ''))
    age       = int(row.get('年齡', 40))

    if ethnicity == '閩南':
        if age >= 50:
            return '頻繁夾台語'
        if age >= 30:
            return '偶夾台語詞'
        return '偶夾台語詞或英中混搭'
    if ethnicity == '客家':
        return '偶夾客語詞（正式場合純國語）'
    if ethnicity == '外省':
        return '純國語為主'
    if age <= 34:
        return '英中混搭'
    return '純國語'


# ── 賦值 ──────────────────────────────────────────────────────────────────────
df['說話風格_正式程度'] = df.apply(get_formality, axis=1)
df['說話風格_溝通取向'] = df.apply(get_communication_orientation, axis=1)
df['說話風格_語言切換'] = df.apply(get_language_switch, axis=1)

# ── 分布驗證 ──────────────────────────────────────────────────────────────────
print("=== 說話風格_正式程度 ===")
print(df['說話風格_正式程度'].value_counts(normalize=True).round(3).to_string())

print("\n=== 說話風格_溝通取向 ===")
print(df['說話風格_溝通取向'].value_counts(normalize=True).round(3).to_string())

print("\n=== 說話風格_語言切換 ===")
print(df['說話風格_語言切換'].value_counts(normalize=True).round(3).to_string())

# ── 輸出 ──────────────────────────────────────────────────────────────────────
df.to_excel(OUTPUT, index=False)
print(f"\n已輸出：{OUTPUT}（{len(df)} 筆，{len(df.columns)} 欄）")
