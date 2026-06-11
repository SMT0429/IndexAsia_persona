import numpy as np
import pandas as pd

df = pd.read_excel("data/taipei_personas_3000_income.xlsx")

CATEGORIES = ['傳統民間信仰', '無宗教', '佛教', '道教', '基督新教', '一貫道', '天主教', '其他宗教']

# 全國 AIT 數據 × 台北市調整係數，正規化後（§4.1）
BASE_PROB = {
    '傳統民間信仰': 0.236,
    '無宗教':       0.308,
    '佛教':         0.196,
    '道教':         0.148,
    '基督新教':     0.065,
    '一貫道':       0.022,
    '天主教':       0.015,
    '其他宗教':     0.006,
}

AGE_MULTIPLIER = {
    '15-35': {
        '傳統民間信仰': 0.75,
        '無宗教':       1.40,
        '佛教':         0.90,
        '道教':         0.70,
        '基督新教':     1.20,
        '一貫道':       0.80,
        '天主教':       1.00,
        '其他宗教':     1.00,
    },
    '36-55': {
        '傳統民間信仰': 1.00,
        '無宗教':       1.00,
        '佛教':         1.00,
        '道教':         1.00,
        '基督新教':     1.00,
        '一貫道':       1.00,
        '天主教':       1.00,
        '其他宗教':     1.00,
    },
    '56+': {
        '傳統民間信仰': 1.35,
        '無宗教':       0.50,
        '佛教':         1.20,
        '道教':         1.40,
        '基督新教':     0.80,
        '一貫道':       1.20,
        '天主教':       1.00,
        '其他宗教':     1.00,
    },
}


def get_age_group(age: int) -> str:
    if age <= 35:
        return '15-35'
    elif age <= 55:
        return '36-55'
    else:
        return '56+'


def assign_religion(age: int, rng) -> str:
    age_group = get_age_group(age)
    multipliers = AGE_MULTIPLIER[age_group]

    adjusted = np.array([BASE_PROB[cat] * multipliers[cat] for cat in CATEGORIES])
    adjusted = np.maximum(adjusted, 0)
    total = adjusted.sum()
    if total == 0:
        adjusted = np.ones(len(CATEGORIES)) / len(CATEGORIES)
    else:
        adjusted /= total

    return rng.choice(CATEGORIES, p=adjusted)


rng = np.random.default_rng(seed=42)

df['宗教與地方信仰'] = df['年齡'].apply(lambda age: assign_religion(age, rng))

print("=== 整體分布 ===")
dist = df['宗教與地方信仰'].value_counts(normalize=True).reindex(CATEGORIES)
print(dist.round(3))

print("\n=== 年齡層 × 宗教與地方信仰交叉表 ===")
cross = pd.crosstab(
    df['年齡'].apply(get_age_group),
    df['宗教與地方信仰'],
    normalize='index'
)[CATEGORIES].round(3)
print(cross)

df.to_excel("data/taipei_personas_3000_religion.xlsx", index=False)
print("\n✅ 完成，已輸出至 data/taipei_personas_3000_religion.xlsx")
