import pandas as pd
import numpy as np

rng = np.random.default_rng(42)

# ── Load data ──────────────────────────────────────────────────────────────
df_pol = pd.read_excel("../data/Political.xlsx", sheet_name="原始回答資料")
df_personas = pd.read_excel("../data/personas_3000.xlsx")

# ── Survey → Persona mappings ──────────────────────────────────────────────
reg_code_to_name = {
    1:"新北市", 2:"臺北市", 3:"桃園市", 4:"臺中市", 5:"臺南市", 6:"高雄市",
    7:"宜蘭縣", 8:"新竹縣", 9:"苗栗縣", 10:"彰化縣", 11:"南投縣", 12:"雲林縣",
    13:"嘉義縣", 14:"屏東縣", 15:"臺東縣", 16:"花蓮縣", 17:"澎湖縣",
    18:"基隆市", 19:"新竹市", 20:"嘉義市", 21:"金門縣", 22:"連江縣",
}

reg_to_group = {
    "新北市":"北部", "臺北市":"北部", "桃園市":"北部", "基隆市":"北部",
    "新竹市":"北部", "新竹縣":"北部", "宜蘭縣":"北部",
    "臺中市":"中部", "苗栗縣":"中部", "彰化縣":"中部", "南投縣":"中部", "雲林縣":"中部",
    "臺南市":"南部", "高雄市":"南部", "嘉義市":"南部", "嘉義縣":"南部",
    "屏東縣":"南部", "澎湖縣":"南部",
    "臺東縣":"東部", "花蓮縣":"東部",
    "金門縣":"離島", "連江縣":"離島",
}

age_code_to_group = {
    1:"15–24歲", 2:"25–34歲", 3:"25–34歲", 4:"35–44歲", 5:"35–44歲",
    6:"45–54歲", 7:"45–54歲", 8:"55–64歲", 9:"55–64歲",
    10:"65歲以上", 11:"65歲以上",
}

edu_code_to_cat = {
    1:"國小以下", 2:"國中", 3:"高中(職)", 4:"專科", 5:"大學", 6:"碩士以上",
}

gender_code_to_str = {1:"男", 2:"女"}

q12_map = {
    1:"民進黨", 2:"國民黨", 3:"台灣民眾黨",
    90:"不偏任何黨", 94:"其他政黨", 96:"不知道", 98:"拒答",
}

q13_map = {
    1:"民進黨", 2:"國民黨", 3:"台灣民眾黨",
    94:"其他政黨", 95:"都很討厭", 96:"不知道/沒意見", 98:"拒答",
}

# ── Enrich survey data with mapped demographics ────────────────────────────
df_pol["region"]       = df_pol["vQ1"].map(reg_code_to_name)
df_pol["region_group"] = df_pol["region"].map(reg_to_group)
df_pol["age_group"]    = df_pol["vQ14"].map(age_code_to_group)
df_pol["edu"]          = df_pol["vQ15"].map(edu_code_to_cat)
df_pol["gender"]       = df_pol["vQ16"].map(gender_code_to_str)

# ── 國家信任指數: Q2~Q5 加總後標準化至 0~10 ─────────────────────────────
# 量表: 1=非常有信心 2=還算有信心 3=不太有信心 4=完全沒有信心
# 反轉使高分=高信任: inverted = 5 - value
# 取有效題目(1~4)的平均，再縮放至 0~10
def compute_trust(row):
    vals = []
    for q in ["vQ2", "vQ3", "vQ4", "vQ5"]:
        v = row[q]
        if v in (1, 2, 3, 4):
            vals.append(5 - v)   # 4=高信任, 1=低信任
    if not vals:
        return np.nan
    mean_val = np.mean(vals)     # range [1, 4]
    return round((mean_val - 1) / 3 * 10, 2)

df_pol["trust_index"]    = df_pol.apply(compute_trust, axis=1)
df_pol["party_pref"]     = df_pol["vQ12"].map(q12_map)
df_pol["dislike_party"]  = df_pol["vQ13"].map(q13_map)

# ── Hierarchical matching ──────────────────────────────────────────────────
def find_pool(region, rgroup, age_group, edu, gender, min_n=10):
    """Return survey rows matching persona demographics (falls back gracefully)."""
    p = df_pol

    def try_filter(**kwargs):
        mask = pd.Series(True, index=p.index)
        for col, val in kwargs.items():
            if val is not None:
                mask &= p[col] == val
        sub = p[mask]
        return sub if len(sub) >= min_n else None

    levels = [
        dict(region=region,       age_group=age_group, edu=edu, gender=gender),
        dict(region=region,       age_group=age_group,           gender=gender),
        dict(region=region,       age_group=age_group                         ),
        dict(region_group=rgroup, age_group=age_group, edu=edu, gender=gender),
        dict(region_group=rgroup, age_group=age_group,           gender=gender),
        dict(region_group=rgroup, age_group=age_group                         ),
        dict(                     age_group=age_group,           gender=gender),
        dict(                     age_group=age_group                         ),
    ]
    for kwargs in levels:
        result = try_filter(**kwargs)
        if result is not None:
            return result
    return p  # fallback: entire survey

# ── Assign political dimensions to each persona ────────────────────────────
trust_list   = []
pref_list    = []
dislike_list = []

for _, row in df_personas.iterrows():
    region    = row["居住地"]
    rgroup    = reg_to_group.get(region)
    age_group = row["年齡組"]
    edu       = row["教育程度"]
    gender    = row["性別"]

    pool = find_pool(region, rgroup, age_group, edu, gender)

    # 國家信任指數
    valid_trust = pool["trust_index"].dropna().values
    if len(valid_trust) > 0:
        base = float(rng.choice(valid_trust))
        jitter = rng.normal(0, 0.25)
        trust = round(float(np.clip(base + jitter, 0.0, 10.0)), 1)
    else:
        trust = round(float(rng.uniform(0, 10)), 1)
    trust_list.append(trust)

    # 政黨傾向 (Q12)
    valid_pref = pool["party_pref"].dropna().values
    pref_list.append(str(rng.choice(valid_pref)) if len(valid_pref) > 0 else "不知道")

    # 厭惡政黨 (Q13) — 排除已偏好的政黨，避免邏輯矛盾
    specific_parties = {"民進黨", "國民黨", "台灣民眾黨"}
    preferred = pref_list[-1]  # 剛才加入的政黨傾向
    valid_dis = pool["dislike_party"].dropna().values
    if preferred in specific_parties:
        filtered_dis = valid_dis[valid_dis != preferred]
        if len(filtered_dis) >= 1:
            valid_dis = filtered_dis
    dislike_list.append(str(rng.choice(valid_dis)) if len(valid_dis) > 0 else "不知道/沒意見")

df_personas["國家信任指數"] = trust_list
df_personas["政黨傾向"]     = pref_list
df_personas["厭惡政黨"]     = dislike_list

# ── Save ──────────────────────────────────────────────────────────────────
df_personas.to_excel("../data/personas_3000.xlsx", index=False)
print(f"✓ 已更新 personas_3000.xlsx  ({len(df_personas)} rows, {len(df_personas.columns)} cols)")

# ── Validation ─────────────────────────────────────────────────────────────
print("\n=== 國家信任指數 ===")
t = df_personas["國家信任指數"]
print(f"  平均={t.mean():.2f}  標準差={t.std():.2f}  min={t.min()}  max={t.max()}")

# Compare trust by age group
print("\n  信任指數 by 年齡組:")
print(df_personas.groupby("年齡組")["國家信任指數"].mean().round(2).to_string())

# Survey reference
survey_mean = df_pol["trust_index"].mean()
print(f"\n  (參考) 問卷原始平均: {survey_mean:.2f}")

print("\n=== 政黨傾向 (Q12) ===")
vc_pref = df_personas["政黨傾向"].value_counts()
total = vc_pref.sum()
survey_ref = df_pol["party_pref"].value_counts()
surv_total = survey_ref.sum()
for cat in vc_pref.index:
    pct_gen = vc_pref[cat] / total
    pct_sur = survey_ref.get(cat, 0) / surv_total
    print(f"  {cat:<10}: 生成={pct_gen:.1%}  問卷={pct_sur:.1%}")

print("\n=== 厭惡政黨 (Q13) ===")
vc_dis = df_personas["厭惡政黨"].value_counts()
total = vc_dis.sum()
survey_ref2 = df_pol["dislike_party"].value_counts()
surv_total2 = survey_ref2.sum()
for cat in vc_dis.index:
    pct_gen = vc_dis[cat] / total
    pct_sur = survey_ref2.get(cat, 0) / surv_total2
    print(f"  {cat:<10}: 生成={pct_gen:.1%}  問卷={pct_sur:.1%}")

print("\n=== 前 5 筆預覽 ===")
print(df_personas[["id","居住地","年齡組","教育程度","性別",
                   "國家信任指數","政黨傾向","厭惡政黨"]].head(5).to_string(index=False))
