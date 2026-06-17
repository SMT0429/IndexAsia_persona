import random
import pandas as pd

# 注意：本腳本刻意使用 stdlib random（非 numpy）；換 RNG 引擎會改變抽樣序列→改變輸出。
from pipeline_common import read_stage, write_stage, NON_EMP_MARKER, NON_EMPLOYED_OCCS

INDUSTRIES = [
    '農林漁牧業', '製造業', '工程及公用事業', '批發及零售業',
    '住宿及餐飲業', '運輸及倉儲業', '資訊及通訊傳播業',
    '金融及保險業', '不動產及專業技術業', '公共行政及國防',
    '教育業', '醫療保健及社會工作', '其他服務業',
]

# NON_EMPLOYED_OCCS、NON_EMP_MARKER 由 pipeline_common 匯入（去重，值不變）

# 職業別條件機率權重矩陣（相對權重，未正規化）
# 依 method/industry_column_methodology.md 第 5.2 節
OCCUPATION_INDUSTRY_MATRIX = {
    '事務人員': {
        '農林漁牧業': 0,  '製造業': 5,  '工程及公用事業': 3,  '批發及零售業': 10,
        '住宿及餐飲業': 3, '運輸及倉儲業': 3, '資訊及通訊傳播業': 5, '金融及保險業': 20,
        '不動產及專業技術業': 10, '公共行政及國防': 15, '教育業': 5,
        '醫療保健及社會工作': 5,  '其他服務業': 16,
    },
    '技術/助理專業': {
        '農林漁牧業': 0,  '製造業': 15, '工程及公用事業': 10, '批發及零售業': 3,
        '住宿及餐飲業': 2, '運輸及倉儲業': 5, '資訊及通訊傳播業': 20, '金融及保險業': 5,
        '不動產及專業技術業': 10, '公共行政及國防': 8,  '教育業': 5,
        '醫療保健及社會工作': 12, '其他服務業': 5,
    },
    '技術工/勞工': {
        '農林漁牧業': 0,  '製造業': 45, '工程及公用事業': 30, '批發及零售業': 3,
        '住宿及餐飲業': 2, '運輸及倉儲業': 10, '資訊及通訊傳播業': 1, '金融及保險業': 0,
        '不動產及專業技術業': 2,  '公共行政及國防': 2,  '教育業': 0,
        '醫療保健及社會工作': 1,  '其他服務業': 4,
    },
    '服務/銷售': {
        '農林漁牧業': 0,  '製造業': 2,  '工程及公用事業': 1,  '批發及零售業': 30,
        '住宿及餐飲業': 25, '運輸及倉儲業': 5, '資訊及通訊傳播業': 1, '金融及保險業': 2,
        '不動產及專業技術業': 3,  '公共行政及國防': 2,  '教育業': 2,
        '醫療保健及社會工作': 10, '其他服務業': 17,
    },
    '專業人員': {
        '農林漁牧業': 0,  '製造業': 3,  '工程及公用事業': 2,  '批發及零售業': 2,
        '住宿及餐飲業': 1, '運輸及倉儲業': 1, '資訊及通訊傳播業': 10, '金融及保險業': 8,
        '不動產及專業技術業': 10, '公共行政及國防': 8,  '教育業': 20,
        '醫療保健及社會工作': 25, '其他服務業': 10,
    },
    '管理/主管': {
        '農林漁牧業': 0,  '製造業': 10, '工程及公用事業': 5,  '批發及零售業': 15,
        '住宿及餐飲業': 5, '運輸及倉儲業': 4, '資訊及通訊傳播業': 8, '金融及保險業': 15,
        '不動產及專業技術業': 12, '公共行政及國防': 6,  '教育業': 5,
        '醫療保健及社會工作': 5,  '其他服務業': 10,
    },
}

# 台北市行業調整係數（method/industry_column_methodology.md 第 5.3 節）
TAIPEI_MULTIPLIER = {
    '農林漁牧業':         0.05,
    '製造業':             0.25,
    '工程及公用事業':     0.60,
    '批發及零售業':       1.10,
    '住宿及餐飲業':       1.00,
    '運輸及倉儲業':       0.80,
    '資訊及通訊傳播業':   3.00,
    '金融及保險業':       2.50,
    '不動產及專業技術業': 1.50,
    '公共行政及國防':     1.80,
    '教育業':             1.30,
    '醫療保健及社會工作': 1.20,
    '其他服務業':         1.00,
}


def sample_by_occupation(occupation: str) -> str:
    raw = OCCUPATION_INDUSTRY_MATRIX[occupation]
    adjusted = {ind: raw[ind] * TAIPEI_MULTIPLIER[ind] for ind in INDUSTRIES}
    total = sum(adjusted.values())
    industries = list(adjusted.keys())
    weights = [adjusted[ind] / total for ind in industries]
    return random.choices(industries, weights=weights, k=1)[0]


def assign_industry(occ: str) -> str:
    if occ in NON_EMPLOYED_OCCS:
        return NON_EMP_MARKER
    if occ == '農林漁牧':
        return '農林漁牧業'
    return sample_by_occupation(occ)


def main():
    random.seed(42)

    df = read_stage("politicalEvent")
    df['產業別'] = df['職業'].apply(assign_industry)
    out = write_stage(df, "industry")

    print(f"輸出完成：{out}")
    print(f"總行數：{len(df)}，欄位數：{len(df.columns)}")

    non_emp = (df['產業別'] == NON_EMP_MARKER).sum()
    employed = df[df['產業別'] != NON_EMP_MARKER]
    print(f"\n非就業人口：{non_emp} 人（{non_emp / len(df):.1%}）")
    print(f"就業人口：{len(employed)} 人（{len(employed) / len(df):.1%}）")

    print("\n=== 就業人口行業分布 ===")
    dist = employed['產業別'].value_counts(normalize=True).round(3)
    print(dist.to_string())


if __name__ == "__main__":
    main()
