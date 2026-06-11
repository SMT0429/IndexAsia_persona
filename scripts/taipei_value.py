"""
taipei_value.py
輸入：taipei_personas_3000_splitTicket.xlsx（19 欄）
輸出：taipei_personas_3000_value.xlsx（19 + 4 = 23 欄）

新增欄位：
  社會價值觀_CO分數     float  -10 至 +10（負=Conservation, 正=Openness）
  社會價值觀_ST分數     float  -10 至 +10（負=Self-Enhancement, 正=Self-Transcendence）
  社會價值觀_主類型     str    開放關懷型 / 自主競爭型 / 傳統守望型 / 秩序菁英型
  社會價值觀_核心動機   str    對應主類型的核心動機句

理論基礎：Schwartz Basic Human Values Theory（1992）
詳細方法論：method/values_column_methodology.md
"""

import pandas as pd
import numpy as np
import os

INPUT  = os.path.join(os.path.dirname(__file__), "../data/taipei_personas_3000_splitTicket.xlsx")
OUTPUT = os.path.join(os.path.dirname(__file__), "../data/taipei_personas_3000_value.xlsx")

df = pd.read_excel(INPUT)

# ── 工具函式 ──────────────────────────────────────────────────────────────────

def scale(series: pd.Series, raw_min: float, raw_max: float) -> pd.Series:
    return ((series - raw_min) / (raw_max - raw_min) * 20 - 10).round(2)

def count_media(media_str) -> int:
    if pd.isna(media_str) or str(media_str).strip() == "":
        return 0
    return len([m.strip() for m in str(media_str).split("、") if m.strip()])

# ── C-O 軸賦值表 ─────────────────────────────────────────────────────────────
# 年齡組：實際資料以6組計（15–24, 25–34, 35–44, 45–54, 55–64, 65+）
# 方法論原始為5組（18-29, 30-44…）；此處依連續性做線性映射

AGE_CO = {
    "15–24歲": 3.0,   # 對應方法論 18-29 → +3.0
    "25–34歲": 2.0,   # 介於 18-29(+3) 與 30-44(+1) 之間
    "35–44歲": 1.0,   # 對應方法論 30-44 → +1.0
    "45–54歲": -1.0,
    "55–64歲": -2.0,
    "65歲以上": -3.0,
}

EDU_CO = {
    "碩士以上": 2.0,
    "大學":    1.0,
    "專科":    0.0,   # 介於大學與高中之間
    "高中(職)": -1.0,
    "國中":    -2.0,
    "國小以下": -2.0,
}

# 宗教：含包含判斷（字串 partial match 兜底）
RELIGION_CO = {
    "無宗教":    2.0,
    "基督新教":   0.0,
    "天主教":    0.0,
    "其他宗教":   0.0,
    "佛教":    -1.0,
    "道教":    -2.0,
    "傳統民間信仰": -2.0,
    "一貫道":   -2.0,   # 傳統民俗宗教，參照民間信仰
}

PARTY_CO = {
    "民進黨":    2.0,
    "台灣民眾黨":  1.0,
    "其他政黨":   0.0,
    "不知道/沒意見": 0.0,
    "無黨籍":    0.0,
    "國民黨":   -2.0,
}

ETHNICITY_CO = {
    "外省": -1.0,
    "閩南":  0.0,
    "客家":  0.0,
    "原住民": 0.0,
}

def calc_co(row) -> float:
    score = 0.0

    score += AGE_CO.get(str(row["年齡組"]), 0.0)
    score += EDU_CO.get(str(row["教育程度"]), 0.0)

    rel = str(row["宗教與地方信仰"])
    score += RELIGION_CO.get(rel, 0.0)

    score += PARTY_CO.get(str(row["政黨傾向"]), 0.0)

    ni = float(row["國家認同"]) if pd.notna(row["國家認同"]) else 5.5
    score += (5.5 - ni) * 0.5

    score += ETHNICITY_CO.get(str(row["族群"]), 0.0)

    return score

# ── S-T 軸賦值表 ─────────────────────────────────────────────────────────────

GENDER_ST = {"女": 2.0, "男": -1.0}

EDU_ST = {
    "碩士以上": 1.0,
    "大學":    0.5,
    "專科":    0.25,  # 介於大學與高中之間
    "高中(職)": 0.0,
    "國中":   -0.5,
    "國小以下": -0.5,
}

INCOME_ST = {
    "4萬以下":  1.0,
    "4~6萬":   0.5,
    "6~10萬":  0.0,
    "10~15萬": -1.0,
    "15~25萬": -2.0,  # 方法論的「>15萬」區間
    "25萬以上": -2.0,
}

# 職業 → S-T 分數（fuzzy match 優先，精確 mapping 備用）
def occ_st(occ: str) -> float:
    if "管理" in occ or "主管" in occ:
        return -2.0
    if "專業" in occ or "技術" in occ or "工程" in occ:
        return -1.0
    if "服務" in occ or "銷售" in occ:
        return 1.0
    if "勞工" in occ or "工" in occ or "農" in occ:
        return 1.0
    if "事務" in occ:
        return 0.0  # 事務人員：中性，介於服務與專業之間
    return 0.0  # 退休、學生、家管、其他/待業

def calc_st(row) -> float:
    score = 0.0

    score += GENDER_ST.get(str(row["性別"]), 0.0)
    score += EDU_ST.get(str(row["教育程度"]), 0.0)
    score += INCOME_ST.get(str(row["月收入區間"]), 0.0)
    score += occ_st(str(row["職業"]))

    rel = str(row["宗教與地方信仰"])
    score += 0.0 if rel == "無宗教" else 1.0

    n_media = count_media(row["媒體習慣"])
    if n_media >= 4:
        score += 1.0
    elif n_media <= 1:
        score += -0.5

    return score

# ── 計算原始分數 ──────────────────────────────────────────────────────────────

df["_co_raw"] = df.apply(calc_co, axis=1)
df["_st_raw"] = df.apply(calc_st, axis=1)

# ── 線性縮放至 [-10, +10] ─────────────────────────────────────────────────────

co_min, co_max = df["_co_raw"].min(), df["_co_raw"].max()
st_min, st_max = df["_st_raw"].min(), df["_st_raw"].max()

df["社會價值觀_CO分數"] = scale(df["_co_raw"], co_min, co_max)
df["社會價值觀_ST分數"] = scale(df["_st_raw"], st_min, st_max)

# ── 主類型判定 ────────────────────────────────────────────────────────────────

TYPE_MAP = {
    (True,  True):  "開放關懷型",
    (True,  False): "自主競爭型",
    (False, True):  "傳統守望型",
    (False, False): "秩序菁英型",
}

MOTIVATION_MAP = {
    "開放關懷型": "這個世界可以更公平，我願意為此做些什麼",
    "自主競爭型": "我靠自己的努力和判斷前進，不需要跟著別人走",
    "傳統守望型": "照顧好家人和社群，比追求改變更重要",
    "秩序菁英型": "社會需要秩序，有能力的人就該有相應的位置",
}

df["社會價值觀_主類型"] = df.apply(
    lambda r: TYPE_MAP[
        (r["社會價值觀_CO分數"] >= 0, r["社會價值觀_ST分數"] >= 0)
    ],
    axis=1,
)
df["社會價值觀_核心動機"] = df["社會價值觀_主類型"].map(MOTIVATION_MAP)

# ── 清理暫存欄位並輸出 ────────────────────────────────────────────────────────

df.drop(columns=["_co_raw", "_st_raw"], inplace=True)
df.to_excel(OUTPUT, index=False)

print(f"輸出完成：{OUTPUT}")
print(f"欄位數：{len(df.columns)}（新增 4 欄）")
print()
print("=== 主類型分布 ===")
print(df["社會價值觀_主類型"].value_counts().to_string())
print()
print("=== CO 軸統計 ===")
print(df["社會價值觀_CO分數"].describe().round(2).to_string())
print()
print("=== ST 軸統計 ===")
print(df["社會價值觀_ST分數"].describe().round(2).to_string())
print()

# ── 驗證（方法論 7.1 理論一致性）────────────────────────────────────────────

print("=== 驗證：65歲以上主類型 ===")
print(df[df["年齡組"] == "65歲以上"]["社會價值觀_主類型"].value_counts(normalize=True).round(3).to_string())
print()
print("=== 驗證：國民黨 vs 民進黨 CO 均值 ===")
for p in ["國民黨", "民進黨"]:
    mean = df[df["政黨傾向"] == p]["社會價值觀_CO分數"].mean()
    print(f"  {p}: CO 均值 = {mean:.2f}")
print()
print("=== 驗證：女性 vs 男性 ST 均值 ===")
for g in ["女", "男"]:
    mean = df[df["性別"] == g]["社會價值觀_ST分數"].mean()
    print(f"  {g}: ST 均值 = {mean:.2f}")
