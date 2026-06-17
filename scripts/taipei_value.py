"""
taipei_value.py  (v3.0 三變數重構版)
輸入：taipei_personas_3000_splitTicket.xlsx
輸出：taipei_personas_3000_value.xlsx（+4 欄）

新增欄位：
  社會價值觀_CO分數     float  -10 至 +10（負=Conservation, 正=Openness）
  社會價值觀_ST分數     float  -10 至 +10（負=Self-Enhancement, 正=Self-Transcendence）
  社會價值觀_主類型     str    開放關懷型 / 自主競爭型 / 傳統守望型 / 秩序菁英型
  社會價值觀_核心動機   str    對應主類型的核心動機句

v3.0 變更：
  - 輸入變數僅保留文獻證據最穩固的三項：年齡組、性別、教育程度
  - 權重直接按文獻效果量等比例換算（1.0 軸負荷量 = 6.0 分）：
      年齡×C-O 負荷 -.50 → ±3.0   （ESS R6: TRA +.32, STI -.32）
      教育×C-O 負荷 +.27 → ±1.6   （ESS R6: SD +.16, TRA -.19）
      年齡×S-T 負荷 +.37 → ±2.0   （ESS R6: UNI +.21, ACH -.27）
      性別×S-T 負荷 ≈+.20 → ±1.2  （Schwartz & Rubel 2005: median d=.15, max d=.32）
  - 宗教/政黨/國家認同/族群/收入/職業/媒體習慣全數移除，改列外部效標
理論基礎：Schwartz Basic Human Values Theory（1992）
文獻數據：Schwartz, Breyer & Danner (2015, ZIS/GESIS, ESS Round 6, N=54,673)
          Schwartz & Rubel (2005, JPSP, 70 國 127 樣本, N=77,528)
詳細方法論：method/values_column_methodology.md
"""

import pandas as pd

from pipeline_common import read_stage, write_stage

df = read_stage("splitTicket")

# ── 工具函式 ──────────────────────────────────────────────────────────────────

def scale(series: pd.Series, raw_min: float, raw_max: float) -> pd.Series:
    return ((series - raw_min) / (raw_max - raw_min) * 20 - 10).round(2)

# ── 賦值表（權重 ∝ 文獻效果量，詳見方法論 3.2–3.3）──────────────────────────
# 年齡組標籤使用 en-dash（–）

AGE_CO = {
    "15–24歲": 3.0,
    "25–34歲": 1.8,
    "35–44歲": 0.6,
    "45–54歲": -0.6,
    "55–64歲": -1.8,
    "65歲以上": -3.0,
}

EDU_CO = {
    "碩士以上": 1.6,
    "大學":    0.8,
    "專科":    0.0,
    "高中(職)": -0.8,
    "國中":    -1.6,
    "國小以下": -1.6,
}

AGE_ST = {
    "15–24歲": -2.0,
    "25–34歲": -1.2,
    "35–44歲": -0.4,
    "45–54歲": 0.4,
    "55–64歲": 1.2,
    "65歲以上": 2.0,
}

GENDER_ST = {"女": 1.2, "男": -1.2}  # 其他/未填 → 0.0


def calc_co(row) -> float:
    return AGE_CO.get(str(row["年齡組"]), 0.0) + EDU_CO.get(str(row["教育程度"]), 0.0)


def calc_st(row) -> float:
    return AGE_ST.get(str(row["年齡組"]), 0.0) + GENDER_ST.get(str(row["性別"]), 0.0)


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
out = write_stage(df, "value")

print(f"輸出完成：{out}")
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

# ── 驗證 A：理論一致性（輸入變數，方法論 7.1）────────────────────────────────

print("=== 驗證：65歲以上主類型（預期：傳統守望型最高）===")
print(df[df["年齡組"] == "65歲以上"]["社會價值觀_主類型"]
      .value_counts(normalize=True).round(3).to_string())
print()
print("=== 驗證：女性 vs 男性 ST 均值（預期：女 > 男，小效果）===")
for g in ["女", "男"]:
    mean = df[df["性別"] == g]["社會價值觀_ST分數"].mean()
    print(f"  {g}: ST 均值 = {mean:.2f}")
print()
print("=== 驗證：教育 × CO 均值（預期：隨教育程度上升）===")
for e in ["國小以下", "國中", "高中(職)", "專科", "大學", "碩士以上"]:
    sub = df[df["教育程度"] == e]
    if len(sub):
        print(f"  {e}: CO 均值 = {sub['社會價值觀_CO分數'].mean():.2f}")
print()

# ── 驗證 B：外部效標（不參與計分的變數，方法論 7.2）─────────────────────────

print("=== 外部效標：國民黨 vs 民進黨 CO 均值（預期：民進黨 > 國民黨）===")
for p in ["國民黨", "民進黨"]:
    mean = df[df["政黨傾向"] == p]["社會價值觀_CO分數"].mean()
    print(f"  {p}: CO 均值 = {mean:.2f}")
print()
print("=== 外部效標：收入 × ST 均值（預期：高收入 ≤ 低收入）===")
for inc in ["4萬以下", "4~6萬", "6~10萬", "10~15萬", "15~25萬", "25萬以上"]:
    sub = df[df["月收入區間"] == inc]
    if len(sub):
        print(f"  {inc}: ST 均值 = {sub['社會價值觀_ST分數'].mean():.2f}")
print()
print("=== 外部效標：宗教有無 × CO 均值（預期：無宗教 > 有宗教）===")
has_rel = df["宗教與地方信仰"].astype(str) != "無宗教"
print(f"  無宗教: CO 均值 = {df.loc[~has_rel, '社會價值觀_CO分數'].mean():.2f}")
print(f"  有宗教: CO 均值 = {df.loc[has_rel, '社會價值觀_CO分數'].mean():.2f}")
