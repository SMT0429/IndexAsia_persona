"""
fix_temp_consistency.py
依 QA/reports/consistency_check_taipei_personas_3000_temp_20260610.md 之 7 項發現，
對 data/WIP/taipei_personas_3000_temp.xlsx 逐筆套用修正，原地覆蓋輸出。

此修正邏輯與下列生成腳本的同步修正一致（未重跑整條 pipeline，僅針對受影響欄位
做等效的後處理，以保留 QA 已驗證通過的 99.9% 既有資料與其象限不變量）：
  - scripts/taipei_persona_v2.py  （issue 1 / 2 / 3 / 5）
  - scripts/taipei_income.py       （issue 4 / 7）
  - scripts/taipei_property.py      （issue 6）

注意：社會價值觀_CO/ST分數、主類型、核心動機、關注議題、分裂投票傾向等「機率/軟性
分數」欄位刻意不重算——QA 已驗證其象限一致性（主類型↔CO/ST、核心動機↔主類型）100%
通過，重算需全域重新縮放會牽動全部 3000 筆。如需軟性分數與新輸入完全一致，請以修正後
的腳本重跑整條 pipeline。
"""

import os
import numpy as np
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..", "..")
PATH = os.path.abspath(os.path.join(BASE, "data", "WIP", "taipei_personas_3000_temp.xlsx"))

NON_EMP_BASE = "無（非就業人口）"
INCOME_LABELS = ["4萬以下", "4~6萬", "6~10萬", "10~15萬", "15~25萬", "25萬以上"]
HIGH_INCOME_NONEMP = {"10~15萬", "15~25萬", "25萬以上"}          # issue 4：≥10萬
HIGH_INCOME_STUDENT = {"6~10萬", "10~15萬", "15~25萬", "25萬以上"}  # issue 7：≥6萬

df = pd.read_excel(PATH)
before = df.copy()
log = {}

# ── Issue 1：15 歲 persona 持有正式職業 → 強制學生 ─────────────────────────────
m1 = (df["年齡"] == 15) & (df["職業"] != "學生")
df.loc[m1, "職業"] = "學生"
df.loc[m1, "產業別"] = NON_EMP_BASE          # 學生 → 非就業人口
df.loc[m1, "月收入區間"] = "4萬以下"          # 義務教育階段，個人所得封頂
log["issue1_15歲非學生"] = int(m1.sum())

# ── Issue 2：17 歲卻持有專科學歷 → 降為高中(職) ───────────────────────────────
m2 = (df["年齡"] == 17) & (df["教育程度"] == "專科")
df.loc[m2, "教育程度"] = "高中(職)"
log["issue2_17歲專科"] = int(m2.sum())

# ── Issue 3：媒體習慣未包含 LINE → 強制保底 LINE（置於最前） ───────────────────
def _ensure_line(cell):
    items = [x for x in str(cell).split("、") if x]
    if "LINE" not in items:
        items = ["LINE"] + items
    return "、".join(items)

m3 = ~df["媒體習慣"].fillna("").apply(lambda s: "LINE" in str(s).split("、"))
df.loc[m3, "媒體習慣"] = df.loc[m3, "媒體習慣"].apply(_ensure_line)
log["issue3_媒體缺LINE"] = int(m3.sum())

# ── Issue 4：非就業人口（家管/其他·待業）月收入 ≥10 萬 → 封頂 4~6萬 ─────────────
m4 = df["職業"].isin(["家管", "其他/待業"]) & df["月收入區間"].isin(HIGH_INCOME_NONEMP)
df.loc[m4, "月收入區間"] = "4~6萬"
log["issue4_非就業高收入"] = int(m4.sum())

# ── Issue 5：<35 歲僅「國小以下」學歷 → 升為國中 ───────────────────────────────
# （國中與國小以下在收入修正鍵「國中以下」、CO/ST 賦值上完全等值，故不影響下游軟性分數）
# 35–49 歲之國小以下屬可接受統計尾巴，依報告維持不動。
m5 = (df["年齡"] < 35) & (df["教育程度"] == "國小以下")
df.loc[m5, "教育程度"] = "國中"
log["issue5_未滿35歲國小以下"] = int(m5.sum())

# ── Issue 7：在學學生月收入 ≥6 萬 → 封頂 4~6萬 ─────────────────────────────────
m7 = (df["職業"] == "學生") & df["月收入區間"].isin(HIGH_INCOME_STUDENT)
df.loc[m7, "月收入區間"] = "4~6萬"
log["issue7_學生高收入"] = int(m7.sum())

# ── Issue 6：15–24 歲以本人名義持有房產 → 依修正後 property 權重導向 B/C/D ───────
# 對齊 scripts/taipei_property.py 修正後 '15–24歲' 乘數，排除 A（自有本人）重抽。
CATEGORIES = ["自有（本人/配偶）", "自有（家人名義）", "租屋", "借住/配住"]
PROP_BASE = np.array([0.72, 0.06, 0.18, 0.04])
AGE_MULT_15_24 = np.array([0.05, 1.8, 2.2, 1.8])
INCOME_MULT = {
    "4萬以下":  (np.array([0.3, 1.2, 2.0, 1.8]) + np.array([0.6, 1.3, 1.5, 1.2])) / 2,
    "4~6萬":   np.array([0.6, 1.3, 1.5, 1.2]),
    "6~10萬":  np.array([1.0, 1.0, 1.0, 0.7]),
    "10~15萬": np.array([1.2, 0.8, 0.7, 0.5]),
    "15~25萬": np.array([1.4, 0.6, 0.5, 0.4]),
    "25萬以上": np.array([1.4, 0.6, 0.5, 0.4]),
}
MARITAL_MULT = {
    "已婚": np.array([1.3, 0.9, 0.7, 0.6]),
    "未婚": np.array([0.7, 1.1, 1.5, 1.3]),
}

def _redirect_housing(row):
    im = INCOME_MULT.get(str(row["月收入區間"]), np.ones(4))
    mm = MARITAL_MULT.get(str(row["婚姻狀況"]), np.ones(4))
    w = PROP_BASE * AGE_MULT_15_24 * im * mm
    w[0] = 0.0                                  # 排除 A（自有本人），確保導向 B/C/D
    w = w / w.sum()
    rng = np.random.default_rng(int(row["id"]))
    return rng.choice(CATEGORIES, p=w)

m6 = (df["年齡組"] == "15–24歲") & (df["房產持有狀態"] == "自有（本人/配偶）")
df.loc[m6, "房產持有狀態"] = df.loc[m6].apply(_redirect_housing, axis=1)
log["issue6_年輕人自有房產"] = int(m6.sum())

# ── 輸出覆蓋 ──────────────────────────────────────────────────────────────────
df.to_excel(PATH, index=False)

print("=== 修正筆數 ===")
for k, v in log.items():
    print(f"  {k}: {v}")
print(f"\n總變更儲存格列：{int((before.fillna('§') != df.fillna('§')).any(axis=1).sum())} 筆")
print(f"✅ 已原地覆蓋輸出：{PATH}（{len(df)} 筆，{len(df.columns)} 欄）")
