import pandas as pd
import numpy as np

rng = np.random.default_rng(42)
XL = "../data/Basic.xlsx"

# ── 1. 居住地 & 性別 ────────────────────────────────────────────────────────
df_gender = pd.read_excel(XL, sheet_name="地區X性別", header=None)

region_prop = {}
gender_prob = {}

for i in range(3, 25):
    row = df_gender.iloc[i]
    county = str(row[2]).strip().replace(" ", "")
    if pd.isna(row[3]) or county in ("nan", ""):
        continue
    pop_share = float(row[6])
    p_male    = float(row[7])
    p_female  = float(row[8])
    region_prop[county] = pop_share
    gender_prob[county] = (p_male, p_female)

total = sum(region_prop.values())
for k in region_prop:
    region_prop[k] /= total

regions = list(region_prop.keys())

# ── 2. 年齡分布 (15+) ──────────────────────────────────────────────────────
age_raw = []
for i in range(30, 51):
    row = df_gender.iloc[i]
    label = str(row[2]).strip()
    if pd.isna(row[3]):
        continue
    m, f = int(row[3]), int(row[4])
    age_raw.append((label, m + f))

def _start_age(lbl):
    s = lbl.split("－")[0].replace("歲","").replace("+","").replace("以上","").strip()
    return int(s) if s.isdigit() else 0

age_15plus = [(lbl, n) for lbl, n in age_raw if _start_age(lbl) >= 15]
age_labels = [lbl for lbl, _ in age_15plus]
age_counts  = np.array([n for _, n in age_15plus], dtype=float)
age_weights = age_counts / age_counts.sum()

def _parse_age_range(lbl):
    lbl = lbl.replace("歲以上","–200").replace("歲","")
    if "－" in lbl:
        a, b = lbl.split("－")
        return int(a), int(b)
    return int(lbl.replace("+","").replace("–","").split("–")[0]), 200

age_ranges = [_parse_age_range(l) for l in age_labels]

GROUP_LABELS = ["15–24歲","25–34歲","35–44歲","45–54歲","55–64歲","65歲以上"]
def age_to_group(a):
    if a <= 24: return "15–24歲"
    if a <= 34: return "25–34歲"
    if a <= 44: return "35–44歲"
    if a <= 54: return "45–54歲"
    if a <= 64: return "55–64歲"
    return "65歲以上"

# ── 3. 教育程度 by 縣市 ────────────────────────────────────────────────────
df_edu = pd.read_excel(XL, sheet_name="地區X教育程度", header=None)

EDU_CATS = ["碩士以上","大學","專科","高中(職)","國中","國小以下"]

edu_by_region = {}

def _safe(v):
    try: return float(v)
    except: return 0.0

def _edu_from_row(row):
    ma_plus = _safe(row[4]) + _safe(row[5]) + _safe(row[6]) + _safe(row[7])
    univ    = _safe(row[8]) + _safe(row[9])
    college = _safe(row[10])+_safe(row[11])+_safe(row[12])+_safe(row[13])
    highsch = _safe(row[14])+_safe(row[15])+_safe(row[16])+_safe(row[17])+_safe(row[18])
    jrhigh  = _safe(row[19])+_safe(row[20])+_safe(row[21])+_safe(row[22])
    primary = _safe(row[23])+_safe(row[24])+_safe(row[25])+_safe(row[26])
    arr = np.array([ma_plus, univ, college, highsch, jrhigh, primary], dtype=float)
    t = arr.sum()
    return arr / t if t > 0 else None

nat_edu = None
for i in range(8, 77, 3):
    row_ji = df_edu.iloc[i]
    row_m  = df_edu.iloc[i+1]
    if str(row_ji[1]).strip() not in ("計", ""):
        continue
    arr = _edu_from_row(row_ji)
    if arr is None:
        continue
    cn = str(row_m[0]).strip().replace("　","").replace(" ","")
    if cn in ("nan","") or cn.startswith("總"):
        if nat_edu is None:
            nat_edu = arr.copy()
        continue
    edu_by_region[cn] = arr

for r in regions:
    if r not in edu_by_region:
        edu_by_region[r] = nat_edu

# ── 4. 職業 by 縣市 ────────────────────────────────────────────────────────
df_occ = pd.read_excel(XL, sheet_name="地區X職業", header=None)

OCC_CATS = ["管理/主管","專業人員","技術/助理專業","事務人員","服務/銷售","農林漁牧","技術工/勞工"]

occ_by_region = {}

def _occ_row(row):
    vals = np.array([
        _safe(row[5]),
        _safe(row[8]),
        _safe(row[11]),
        _safe(row[15]),
        _safe(row[18]),
        _safe(row[21]),
        _safe(row[24]),
    ], dtype=float)
    t = vals.sum()
    return vals / t if t > 0 else np.ones(7)/7

nat_occ = _occ_row(df_occ.iloc[8])

city_rows = {
    "新北市": 10, "臺北市": 11, "桃園市": 12, "基隆市": 13,
    "新竹市": 14, "宜蘭縣": 15, "新竹縣": 16,
    "臺中市": 18, "苗栗縣": 19, "彰化縣": 20, "南投縣": 21, "雲林縣": 22,
    "臺南市": 24, "高雄市": 25, "嘉義市": 26, "嘉義縣": 27, "屏東縣": 28, "澎湖縣": 29,
    "臺東縣": 31, "花蓮縣": 32,
}
for city, ridx in city_rows.items():
    occ_by_region[city] = _occ_row(df_occ.iloc[ridx])

for r in regions:
    if r not in occ_by_region:
        occ_by_region[r] = nat_occ

# ── 5. 婚姻 by 年齡 ────────────────────────────────────────────────────────
df_marr = pd.read_excel(XL, sheet_name="年齡x婚姻", header=None)

total_row   = df_marr.iloc[5, 3:21].values.astype(float)
married_row = df_marr.iloc[11, 3:21].values.astype(float)
p_married_by_5yr = married_row / total_row

def p_married(age):
    idx = min((age - 15) // 5, 17)
    return float(p_married_by_5yr[idx])

# ── 6. 媒體習慣 by 年齡組 ──────────────────────────────────────────────────
df_media = pd.read_excel(XL, sheet_name="年齡x媒體", header=None)

PLATFORMS = ["LINE","Facebook","YouTube","Instagram","TikTok","小紅書","WeChat",
             "Threads","X(Twitter)","WhatsApp","Telegram","Pinterest","LinkedIn",
             "Tumblr","Snapchat"]
PLATFORM_COLS = [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]

MEDIA_AGE_ROWS = {
    "15–24歲": 11, "25–34歲": 12, "35–44歲": 13,
    "45–54歲": 14, "55–64歲": 15, "65歲以上": 16,
}

media_prob = {}
for grp, ridx in MEDIA_AGE_ROWS.items():
    row = df_media.iloc[ridx]
    probs = np.array([_safe(row[c]) for c in PLATFORM_COLS])
    media_prob[grp] = probs

# ── 7. 政治維度 ─────────────────────────────────────────────────────────────
pol = pd.read_excel("../data/Political.xlsx", sheet_name="原始回答資料")

COUNTY_CODE = {
    1:"新北市",2:"臺北市",3:"桃園市",4:"臺中市",5:"臺南市",6:"高雄市",
    7:"宜蘭縣",8:"新竹縣",9:"苗栗縣",10:"彰化縣",11:"南投縣",12:"雲林縣",
    13:"嘉義縣",14:"屏東縣",15:"臺東縣",16:"花蓮縣",17:"澎湖縣",18:"基隆市",
    19:"新竹市",20:"嘉義市",21:"金門縣",22:"連江縣",
}
REGION_GROUP = {
    "北部": ["新北市","臺北市","桃園市","基隆市","新竹市","新竹縣","宜蘭縣"],
    "中部": ["臺中市","苗栗縣","彰化縣","南投縣","雲林縣"],
    "南部": ["臺南市","高雄市","嘉義市","嘉義縣","屏東縣","澎湖縣"],
    "東部": ["臺東縣","花蓮縣"],
    "離島": ["金門縣","連江縣"],
}
COUNTY_TO_RG = {c: g for g, cs in REGION_GROUP.items() for c in cs}

PARTY_Q12 = {1:"民進黨",2:"國民黨",3:"台灣民眾黨",90:"不偏任何黨",
             94:"其他政黨",96:"不知道",98:"拒答"}
PARTY_Q13 = {1:"民進黨",2:"國民黨",3:"台灣民眾黨",94:"其他政黨",
             95:"都很討厭",96:"不知道/沒意見",98:"拒答"}

def _trust(row):
    vals = [5 - row[q] for q in ["vQ2","vQ3","vQ4","vQ5"] if 1 <= row[q] <= 4]
    if not vals: return np.nan
    return round((np.mean(vals) - 1) / 3 * 10, 4)

def _survey_age_grp(v):
    if v == 1:        return "15–24歲"
    if v in (2, 3):   return "25–34歲"
    if v in (4, 5):   return "35–44歲"
    if v in (6, 7):   return "45–54歲"
    if v in (8, 9):   return "55–64歲"
    if v in (10, 11): return "65歲以上"
    return None

EDU_SURVEY = {1:"國小以下",2:"國中",3:"高中(職)",4:"專科",5:"大學",6:"碩士以上"}

pol["trust"]        = pol.apply(_trust, axis=1)
pol["age_grp"]      = pol["vQ14"].apply(_survey_age_grp)
pol["edu_cat"]      = pol["vQ15"].map(EDU_SURVEY)
pol["gender"]       = pol["vQ16"].map({1:"男",2:"女"})
pol["county"]       = pol["vQ1"].map(COUNTY_CODE)
pol["rg"]           = pol["county"].map(COUNTY_TO_RG)
pol["party_pref"]   = pol["vQ12"].map(PARTY_Q12)
pol["party_dislike"]= pol["vQ13"].map(PARTY_Q13)

MIN_POOL = 10
MAIN_PARTIES = {"民進黨","國民黨","台灣民眾黨"}

def _pool(county, age_grp, edu, gender_val):
    rg = COUNTY_TO_RG.get(county)
    p = pol
    for mask in [
        (p["county"]==county)&(p["age_grp"]==age_grp)&(p["edu_cat"]==edu)&(p["gender"]==gender_val),
        (p["county"]==county)&(p["age_grp"]==age_grp)&(p["gender"]==gender_val),
        (p["county"]==county)&(p["age_grp"]==age_grp),
        (p["rg"]==rg)&(p["age_grp"]==age_grp)&(p["edu_cat"]==edu)&(p["gender"]==gender_val),
        (p["rg"]==rg)&(p["age_grp"]==age_grp)&(p["gender"]==gender_val),
        (p["rg"]==rg)&(p["age_grp"]==age_grp),
        (p["age_grp"]==age_grp)&(p["gender"]==gender_val),
        (p["age_grp"]==age_grp),
    ]:
        sub = p[mask]
        if len(sub) >= MIN_POOL:
            return sub
    return p

def sample_political(county, age_grp, edu, gender_val):
    pool = _pool(county, age_grp, edu, gender_val)

    tv = pool["trust"].dropna().values
    base = float(rng.choice(tv)) if len(tv) else 5.0
    trust = round(float(np.clip(base + rng.normal(0, 0.25), 0, 10)), 1)

    pv = pool["party_pref"].dropna().values
    pref = str(rng.choice(pv)) if len(pv) else "不知道"

    dv = pool["party_dislike"].dropna()
    if pref in MAIN_PARTIES:
        filtered = dv[dv != pref]
        if len(filtered) > 0:
            dv = filtered
    dislike = str(rng.choice(dv.values)) if len(dv) else "不知道/沒意見"

    return trust, pref, dislike

# ── 8. 職業抽樣 ─────────────────────────────────────────────────────────────
NON_EMP_CATS = ["家管","學生","退休","其他/待業"]
ALL_OCC = OCC_CATS + NON_EMP_CATS

def sample_occ(age, region):
    if age <= 17:
        cats = ["學生","就業","其他/待業"]
        w    = [0.80, 0.15, 0.05]
    elif age <= 22:
        cats = ["學生","就業","其他/待業"]
        w    = [0.55, 0.40, 0.05]
    elif age <= 24:
        cats = ["學生","就業","家管","其他/待業"]
        w    = [0.30, 0.60, 0.05, 0.05]
    elif age <= 59:
        cats = ["就業","家管","其他/待業"]
        w    = [0.84, 0.12, 0.04]
    elif age <= 64:
        cats = ["就業","退休","家管","其他/待業"]
        w    = [0.50, 0.38, 0.09, 0.03]
    else:
        cats = ["就業","退休","家管","其他/待業"]
        w    = [0.12, 0.70, 0.15, 0.03]

    status = rng.choice(cats, p=np.array(w)/sum(w))
    if status == "就業":
        occ_w = occ_by_region.get(region, nat_occ)
        return rng.choice(OCC_CATS, p=occ_w)
    return status

# ── 9. 生成台北市 3000 筆 ───────────────────────────────────────────────────
TARGET_REGION = "臺北市"
n_total = 3000

records = []
for pid in range(1, n_total + 1):
    reg = TARGET_REGION

    pm, pf = gender_prob[reg]
    gender = rng.choice(["男","女"], p=[pm, pf])

    age_idx = rng.choice(len(age_labels), p=age_weights)
    amin, amax = age_ranges[age_idx]
    amin = min(amin, 95)
    amax = min(amax, 95)
    age = int(rng.integers(amin, amax + 1))
    age_grp = age_to_group(age)

    edu_w = edu_by_region.get(reg, nat_edu)
    edu = rng.choice(EDU_CATS, p=edu_w)

    occ = sample_occ(age, reg)

    pm_val = p_married(age)
    marital = rng.choice(["已婚","未婚"], p=[pm_val, 1 - pm_val])

    mprobs = media_prob[age_grp]
    used = [PLATFORMS[i] for i, pp in enumerate(mprobs) if rng.random() < pp]
    if not used:
        used = ["LINE"]
    media_str = "、".join(used)

    trust, pref, dislike = sample_political(reg, age_grp, edu, gender)

    records.append({
        "id": pid,
        "居住地": reg,
        "性別": gender,
        "年齡": age,
        "年齡組": age_grp,
        "教育程度": edu,
        "職業": occ,
        "婚姻狀況": marital,
        "媒體習慣": media_str,
        "國家認同": trust,
        "政黨傾向": pref,
        "厭惡政黨": dislike,
    })

df_taipei = pd.DataFrame(records)
out_path = "../data/taipei_personas_3000.xlsx"

# 台北市民調原始池（用於比對真實分布）
pol_taipei = pol[pol["county"] == TARGET_REGION]

with pd.ExcelWriter(out_path, engine="openpyxl") as writer:

    # ── Sheet 1: Personas ────────────────────────────────────────────────────
    df_taipei.to_excel(writer, sheet_name="Personas", index=False)

    # ── Sheet 2: 政黨傾向 ────────────────────────────────────────────────────
    samp_pref = df_taipei["政黨傾向"].value_counts().reset_index()
    samp_pref.columns = ["政黨", "抽樣人數"]
    samp_pref["抽樣佔比"] = (samp_pref["抽樣人數"] / len(df_taipei)).round(4)

    real_pref = pol_taipei["party_pref"].value_counts()
    real_pref_total = real_pref.sum()
    real_pref_map = (real_pref / real_pref_total).to_dict()
    samp_pref["民調佔比(臺北)"] = samp_pref["政黨"].map(real_pref_map).round(4)
    samp_pref["差距"] = (samp_pref["抽樣佔比"] - samp_pref["民調佔比(臺北)"]).round(4)
    samp_pref.to_excel(writer, sheet_name="政黨傾向", index=False)

    # ── Sheet 3: 厭惡政黨 ────────────────────────────────────────────────────
    samp_dis = df_taipei["厭惡政黨"].value_counts().reset_index()
    samp_dis.columns = ["政黨", "抽樣人數"]
    samp_dis["抽樣佔比"] = (samp_dis["抽樣人數"] / len(df_taipei)).round(4)

    real_dis = pol_taipei["party_dislike"].value_counts()
    real_dis_total = real_dis.sum()
    real_dis_map = (real_dis / real_dis_total).to_dict()
    samp_dis["民調佔比(臺北)"] = samp_dis["政黨"].map(real_dis_map).round(4)
    samp_dis["差距"] = (samp_dis["抽樣佔比"] - samp_dis["民調佔比(臺北)"]).round(4)
    samp_dis.to_excel(writer, sheet_name="厭惡政黨", index=False)

    # ── Sheet 4: 國家認同 by 年齡組 ─────────────────────────────────────────
    # 抽樣統計
    trust_samp = (
        df_taipei.groupby("年齡組")["國家認同"]
        .agg(抽樣人數="count", 抽樣平均="mean", 抽樣中位數="median",
             抽樣最小="min", 抽樣最大="max")
        .round(4).reset_index()
    )
    # 民調真實（臺北）
    trust_real = (
        pol_taipei.dropna(subset=["trust","age_grp"])
        .groupby("age_grp")["trust"]
        .agg(民調樣本數="count", 民調平均="mean", 民調中位數="median")
        .round(4).reset_index()
        .rename(columns={"age_grp": "年齡組"})
    )
    trust_out = trust_samp.merge(trust_real, on="年齡組", how="left")
    trust_out["平均差距"] = (trust_out["抽樣平均"] - trust_out["民調平均"]).round(4)
    trust_out.to_excel(writer, sheet_name="國家認同", index=False)

    # ── Sheet 5: 抽樣分配結果（彙總）────────────────────────────────────────
    sample_rows = []

    def _add_dim(dim, series, real_map=None):
        vc = series.value_counts().sort_index()
        total = vc.sum()
        for cat, cnt in vc.items():
            sample_rows.append({
                "維度": dim,
                "類別": cat,
                "抽樣人數": int(cnt),
                "抽樣佔比": round(cnt / total, 4),
                "真實佔比": round(real_map[cat], 4) if real_map and cat in real_map else None,
                "差距": round(cnt / total - real_map[cat], 4) if real_map and cat in real_map else None,
            })

    # 台北市男女比
    pm_tp, pf_tp = gender_prob[TARGET_REGION]
    _add_dim("性別", df_taipei["性別"], {"男": pm_tp, "女": pf_tp})

    # 年齡組（全國15+分布）
    age_group_data = {}
    for (lbl, n), (amin, amax) in zip(age_15plus, age_ranges):
        g = age_to_group(amin)
        age_group_data[g] = age_group_data.get(g, 0) + n
    total_15plus = sum(age_group_data.values())
    age_real_map = {g: age_group_data.get(g, 0) / total_15plus for g in GROUP_LABELS}
    _add_dim("年齡組", df_taipei["年齡組"], age_real_map)

    # 教育程度（台北市）
    edu_tp_map = {EDU_CATS[i]: float(edu_by_region[TARGET_REGION][i]) for i in range(len(EDU_CATS))}
    _add_dim("教育程度", df_taipei["教育程度"], edu_tp_map)

    # 職業
    _add_dim("職業", df_taipei["職業"])

    # 婚姻狀況
    _add_dim("婚姻狀況", df_taipei["婚姻狀況"])

    # 政黨傾向 vs 民調（台北）
    _add_dim("政黨傾向", df_taipei["政黨傾向"], real_pref_map)

    # 厭惡政黨 vs 民調（台北）
    _add_dim("厭惡政黨", df_taipei["厭惡政黨"], real_dis_map)

    # 國家認同（各年齡組平均）
    for _, row in trust_samp.iterrows():
        sample_rows.append({
            "維度": f"國家認同｜{row['年齡組']}",
            "類別": "平均值",
            "抽樣人數": int(row["抽樣人數"]),
            "抽樣佔比": round(row["抽樣平均"], 4),
            "真實佔比": None,
            "差距": None,
        })

    df_sample = pd.DataFrame(sample_rows,
                             columns=["維度","類別","抽樣人數","抽樣佔比","真實佔比","差距"])
    df_sample.to_excel(writer, sheet_name="抽樣分配結果", index=False)

print(f"✓ 已儲存 {out_path}  ({len(df_taipei)} rows，5 sheets，僅含臺北市)")

# ── 10. 驗證 ────────────────────────────────────────────────────────────────
print("\n=== 性別 ===")
vc = df_taipei["性別"].value_counts(normalize=True)
print(f"  男: {vc.get('男',0):.1%}  女: {vc.get('女',0):.1%}")

print("\n=== 年齡組 ===")
vc = df_taipei["年齡組"].value_counts(normalize=True).sort_index()
for g, p in vc.items():
    print(f"  {g}: {p:.1%}")

print("\n=== 教育程度 ===")
vc = df_taipei["教育程度"].value_counts(normalize=True)
for e, p in vc.items():
    print(f"  {e}: {p:.1%}")

print("\n=== 政黨傾向 ===")
vc = df_taipei["政黨傾向"].value_counts(normalize=True)
print(vc.to_string())

print("\n=== 國家認同 統計 ===")
print(df_taipei["國家認同"].describe().round(2).to_string())
