import pandas as pd
import numpy as np

from pipeline_common import read_stage, write_stage, make_rng, INCOME_LABELS

df = read_stage("industry")

# INCOME_LABELS（6 月收入區間，有序）由 pipeline_common 匯入（去重，值不變）

# 職業欄位對應方法論鍵值
OCCUPATION_MAP = {
    "管理/主管":    "管理/主管",
    "退休":        "退休",
    "學生":        "學生",
    "專業人員":    "專業技術人員",
    "家管":        "家管",
    "服務/銷售":   "服務/銷售",
    "其他/待業":   "無業/待業",
    "事務人員":    "事務/行政支援",
    "技術/助理專業": "技術/助理專業",
    "技術工/勞工": "技術/操作",
    "農林漁牧":    "農林漁牧",
}

OCCUPATION_INCOME_WEIGHTS = {
    "管理/主管":      [0.00, 0.05, 0.25, 0.35, 0.25, 0.10],
    "專業技術人員":   [0.00, 0.10, 0.35, 0.30, 0.20, 0.05],
    "事務/行政支援":  [0.02, 0.25, 0.45, 0.22, 0.05, 0.01],
    "服務/銷售":      [0.10, 0.40, 0.35, 0.12, 0.02, 0.01],
    "技術/操作":      [0.05, 0.30, 0.40, 0.20, 0.04, 0.01],
    "農林漁牧":       [0.15, 0.45, 0.30, 0.08, 0.02, 0.00],
    # QA issue 7：在學學生個人月收入封頂於「4~6萬」（兼職/實習通常更低），移除 6~10 萬以上
    "學生":           [0.60, 0.40, 0.00, 0.00, 0.00, 0.00],
    "退休":           [0.20, 0.35, 0.30, 0.10, 0.04, 0.01],
    # QA issue 4：非就業人口（待業）個人月收入無 ≥10 萬之理，移除 10 萬以上區間
    "無業/待業":      [0.70, 0.26, 0.04, 0.00, 0.00, 0.00],
    "自營/自由業":    [0.05, 0.20, 0.30, 0.25, 0.15, 0.05],
    # 資料特有職業
    "技術/助理專業":  [0.02, 0.20, 0.45, 0.25, 0.07, 0.01],  # 介於技術/操作與專業技術之間
    # QA issue 4：家管為非就業人口，個人月收入低（依賴家戶收入），移除 10 萬以上區間
    "家管":           [0.45, 0.32, 0.23, 0.00, 0.00, 0.00],
    "_default":       [0.10, 0.25, 0.35, 0.20, 0.08, 0.02],
}

# 教育程度欄位對應方法論鍵值
EDUCATION_MAP = {
    "高中(職)": "高中(職)",
    "大學":     "大學",
    "碩士以上": "研究所",
    "專科":     "專科",
    "國中":     "國中以下",
    "國小以下": "國中以下",
}

EDUCATION_MODIFIER = {
    "國中以下":  [1.5, 1.3, 0.8, 0.4, 0.2, 0.1],
    "高中(職)":  [1.2, 1.1, 1.0, 0.8, 0.5, 0.3],
    "專科":      [0.8, 1.0, 1.2, 1.1, 0.8, 0.5],
    "大學":      [0.5, 0.8, 1.2, 1.3, 1.0, 0.7],
    "研究所":    [0.2, 0.4, 0.8, 1.3, 1.5, 1.2],
    "_default":  [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
}

# 年齡組欄位對應方法論鍵值
AGE_MAP = {
    "15–24歲": "未滿25歲",
    "25–34歲": "25–34歲",
    "35–44歲": "35–44歲",
    "45–54歲": "45–54歲",
    "55–64歲": "55–64歲",
    "65歲以上": "65歲以上",
}

AGE_MODIFIER = {
    "未滿25歲":  [1.5, 1.4, 0.8, 0.3, 0.1, 0.0],
    "25–34歲":   [0.8, 1.2, 1.2, 0.9, 0.5, 0.2],
    "35–44歲":   [0.4, 0.8, 1.3, 1.3, 0.8, 0.4],
    "45–54歲":   [0.4, 0.8, 1.2, 1.3, 0.9, 0.5],
    "55–64歲":   [0.6, 0.9, 1.1, 1.1, 0.8, 0.4],
    "65歲以上":  [1.2, 1.1, 0.9, 0.7, 0.4, 0.2],
    "_default":  [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
}


def get_income_label(occupation, education, age_group, rng, age=None):
    # 18歲以下：法定未成年，頂多打工，強制4萬以下（不論職業）
    if age is not None and age < 18:
        return "4萬以下"

    occ_key = OCCUPATION_MAP.get(occupation, "_default")
    edu_key = EDUCATION_MAP.get(education, "_default")
    age_key = AGE_MAP.get(age_group, "_default")

    base = np.array(OCCUPATION_INCOME_WEIGHTS.get(occ_key, OCCUPATION_INCOME_WEIGHTS["_default"]))
    edu_mod = np.array(EDUCATION_MODIFIER.get(edu_key, EDUCATION_MODIFIER["_default"]))
    age_mod = np.array(AGE_MODIFIER.get(age_key, AGE_MODIFIER["_default"]))

    adjusted = base * edu_mod * age_mod
    adjusted = np.maximum(adjusted, 0)
    total = adjusted.sum()
    if total == 0:
        adjusted = np.ones(6) / 6
    else:
        adjusted /= total

    return rng.choice(INCOME_LABELS, p=adjusted)


rng = make_rng()

df["月收入區間"] = df.apply(
    lambda row: get_income_label(
        row["職業"],
        row["教育程度"],
        row["年齡組"],
        rng,
        age=row["年齡"],
    ),
    axis=1,
)

print("=== 整體分布 ===")
dist = df["月收入區間"].value_counts(normalize=True).reindex(INCOME_LABELS)
print(dist.round(3))

print("\n=== 職業 × 收入區間交叉表 ===")
print(pd.crosstab(df["職業"], df["月收入區間"], normalize="index")[INCOME_LABELS].round(2))

print("\n=== 教育程度 × 收入區間交叉表 ===")
print(pd.crosstab(df["教育程度"], df["月收入區間"], normalize="index")[INCOME_LABELS].round(2))

out = write_stage(df, "income")
print(f"\n✅ 完成，已輸出至 {out}")
