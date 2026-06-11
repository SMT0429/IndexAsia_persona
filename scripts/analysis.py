import pandas as pd
import numpy as np

rng = np.random.default_rng(42)
XL = "../data/Basic.xlsx"

# ── 1. 居住地 & 性別 ────────────────────────────────────────────────────────
df_gender = pd.read_excel(XL, sheet_name="地區X性別", header=None)

region_prop = {}   # {county: population_share}
gender_prob = {}   # {county: (p_male, p_female)}

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

# normalise just in case
total = sum(region_prop.values())
for k in region_prop:
    region_prop[k] /= total

regions = list(region_prop.keys())
region_weights = np.array([region_prop[r] for r in regions])

# ── 2. 年齡分布 (15+) ──────────────────────────────────────────────────────
# 地區X性別 second block: rows 30-50 (0-indexed), col2=age_label, col3=male, col4=female
age_raw = []
for i in range(30, 51):
    row = df_gender.iloc[i]
    label = str(row[2]).strip()
    if pd.isna(row[3]):
        continue
    m, f = int(row[3]), int(row[4])
    age_raw.append((label, m + f))

# keep only 15+
age_15plus = [(lbl, n) for lbl, n in age_raw if lbl.startswith("1") or
              any(lbl.startswith(d) for d in ["2","3","4","5","6","7","8","9","10"])]
# filter out 0-14
def _start_age(lbl):
    s = lbl.split("－")[0].replace("歲","").replace("+","").replace("以上","").strip()
    return int(s) if s.isdigit() else 0

age_15plus = [(lbl, n) for lbl, n in age_raw if _start_age(lbl) >= 15]

age_labels = [lbl for lbl, _ in age_15plus]
age_counts  = np.array([n for _, n in age_15plus], dtype=float)
age_weights = age_counts / age_counts.sum()

# map label → (min_age, max_age)
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

edu_by_region = {}  # {county: np.array of 6 weights}

# rows 8-76 odd rows = 計 (total), skip 男/女
# structure: col0=county, col1=性別, col2=總計, col3=合計,
#  col4=博士畢, col5=博士肄, col6=碩士畢, col7=碩士肄,
#  col8=大學畢, col9=大學肄, col10=專科2/3畢, col11=專科2/3肄,
#  col12=專科5後2畢, col13=專科5後2肄, col14=高中畢, col15=高中肄,
#  col16=高職畢, col17=高職肄, col18=五專前3肄, col19=國中畢, col20=國中肄,
#  col21=初職畢, col22=初職肄, col23=國小畢, col24=國小肄, col25=自修, col26=不識字

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
# Structure: rows go in triples (計, 男, 女) starting at row 8
# County name is in the '男' row (i+1), col0
for i in range(8, 77, 3):
    row_ji = df_edu.iloc[i]    # 計
    row_m  = df_edu.iloc[i+1]  # 男 → has county name in col0
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

# fill missing counties with national
for r in regions:
    if r not in edu_by_region:
        edu_by_region[r] = nat_edu

# ── 4. 職業 by 縣市 ────────────────────────────────────────────────────────
df_occ = pd.read_excel(XL, sheet_name="地區X職業", header=None)

# rows 8-32 are data rows; structure (col indices):
# col1=county, col3=Total, col4=Male, col5=Female,
# 管理: col6(合計), 專業: col9, 技術: col12, 事務: col15(skip NaN col14),
# 服務銷售: col18, 農林漁牧: col21, 技藝/機械/勞力: col24
OCC_CATS = ["管理/主管","專業人員","技術/助理專業","事務人員","服務/銷售","農林漁牧","技術工/勞工"]

occ_by_region = {}

def _occ_row(row):
    vals = np.array([
        _safe(row[5]),   # 管理/主管 合計
        _safe(row[8]),   # 專業人員   合計
        _safe(row[11]),  # 技術/助理  合計
        _safe(row[15]),  # 事務人員   合計
        _safe(row[18]),  # 服務/銷售  合計
        _safe(row[21]),  # 農林漁牧   合計
        _safe(row[24]),  # 技術工/勞工 合計
    ], dtype=float)
    t = vals.sum()
    return vals / t if t > 0 else np.ones(7)/7

# row 8 = Taiwan total
nat_occ = _occ_row(df_occ.iloc[8])
occ_by_region["__national__"] = nat_occ

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

# row 5 = 總計(計), row 11 = 有偶(計)
# cols 3..20 = age groups: 15-19,20-24,25-29,30-34,35-39,40-44,45-49,50-54,55-59,60-64,65-69,70-74,75-79,80-84,85-89,90-94,95-99,100+
total_row   = df_marr.iloc[5, 3:21].values.astype(float)
married_row = df_marr.iloc[11, 3:21].values.astype(float)
p_married_by_5yr = married_row / total_row  # 18 values, 5-yr bands starting at 15

def p_married(age):
    idx = min((age - 15) // 5, 17)
    return float(p_married_by_5yr[idx])

# ── 6. 媒體習慣 by 年齡組 ──────────────────────────────────────────────────
df_media = pd.read_excel(XL, sheet_name="年齡x媒體", header=None)

PLATFORMS = ["LINE","Facebook","YouTube","Instagram","TikTok","小紅書","WeChat",
             "Threads","X(Twitter)","WhatsApp","Telegram","Pinterest","LinkedIn",
             "Tumblr","Snapchat"]
# col 3=樣本數, 4=合計(平均平台數), 5=LINE, 6=FB, 7=YT, 8=IG, 9=TikTok, 10=小紅書,
# 11=WeChat, 12=Threads, 13=X, 14=WhatsApp, 15=Telegram, 16=Pinterest,
# 17=LinkedIn, 18=Tumblr, 19=Snapchat
PLATFORM_COLS = [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]

# rows 11-16 = age groups (0-indexed): 16-25,26-35,36-45,46-55,56-65,66+
MEDIA_AGE_ROWS = {
    "15–24歲": 11, "25–34歲": 12, "35–44歲": 13,
    "45–54歲": 14, "55–64歲": 15, "65歲以上": 16,
}

media_prob = {}
for grp, ridx in MEDIA_AGE_ROWS.items():
    row = df_media.iloc[ridx]
    probs = np.array([_safe(row[c]) for c in PLATFORM_COLS])
    media_prob[grp] = probs

# ── 7. 政治維度（Political.xlsx）────────────────────────────────────────────
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
    if v == 1:       return "15–24歲"
    if v in (2, 3):  return "25–34歲"
    if v in (4, 5):  return "35–44歲"
    if v in (6, 7):  return "45–54歲"
    if v in (8, 9):  return "55–64歲"
    if v in (10, 11):return "65歲以上"
    return None

EDU_SURVEY = {1:"國小以下",2:"國中",3:"高中(職)",4:"專科",5:"大學",6:"碩士以上"}

pol["trust"]       = pol.apply(_trust, axis=1)
pol["age_grp"]     = pol["vQ14"].apply(_survey_age_grp)
pol["edu_cat"]     = pol["vQ15"].map(EDU_SURVEY)
pol["gender"]      = pol["vQ16"].map({1:"男",2:"女"})
pol["county"]      = pol["vQ1"].map(COUNTY_CODE)
pol["rg"]          = pol["county"].map(COUNTY_TO_RG)
pol["party_pref"]  = pol["vQ12"].map(PARTY_Q12)
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

    # 國家信任指數
    tv = pool["trust"].dropna().values
    base = float(rng.choice(tv)) if len(tv) else 5.0
    trust = round(float(np.clip(base + rng.normal(0, 0.25), 0, 10)), 1)

    # 政黨傾向
    pv = pool["party_pref"].dropna().values
    pref = str(rng.choice(pv)) if len(pv) else "不知道"

    # 厭惡政黨（排除自身偏好黨）
    dv = pool["party_dislike"].dropna()
    if pref in MAIN_PARTIES:
        filtered = dv[dv != pref]
        if len(filtered) > 0:
            dv = filtered
    dislike = str(rng.choice(dv.values)) if len(dv) else "不知道/沒意見"

    return trust, pref, dislike

# ── 8. 生成 3000 筆 ────────────────────────────────────────────────────────
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

# 每縣市保底 1 人，剩餘 2978 人按比例分配
n_total = 3000
guaranteed = {r: 1 for r in regions}                           # 22 人保底
remaining  = n_total - len(regions)                            # 2978
extra_counts = np.round(region_weights * remaining).astype(int)
diff = remaining - extra_counts.sum()
# 補足捨入差額（加到最大縣市）
extra_counts[np.argmax(extra_counts)] += diff
region_counts = {r: guaranteed[r] + extra_counts[i] for i, r in enumerate(regions)}

# 展開成每筆 persona 要用的 region 序列，打亂順序
region_seq = [r for r, cnt in region_counts.items() for _ in range(cnt)]
rng.shuffle(region_seq)

records = []
for pid in range(1, 3001):
    # region
    reg = region_seq[pid - 1]
    # gender
    pm, pf = gender_prob[reg]
    gender = rng.choice(["男","女"], p=[pm, pf])
    # age
    age_idx = rng.choice(len(age_labels), p=age_weights)
    amin, amax = age_ranges[age_idx]
    amin = min(amin, 95)
    amax = min(amax, 95)
    age = int(rng.integers(amin, amax + 1))
    age_grp = age_to_group(age)
    # education
    edu_w = edu_by_region.get(reg, nat_edu)
    edu = rng.choice(EDU_CATS, p=edu_w)
    # occupation
    occ = sample_occ(age, reg)
    # marital
    pm_val = p_married(age)
    marital = rng.choice(["已婚","未婚"], p=[pm_val, 1 - pm_val])
    # media
    mprobs = media_prob[age_grp]
    used = [PLATFORMS[i] for i, pp in enumerate(mprobs) if rng.random() < pp]
    if not used:
        used = ["LINE"]
    media_str = "、".join(used)

    # political
    trust, pref, dislike = sample_political(reg, age_grp, edu, gender)

    records.append({
        "id": pid, "居住地": reg, "性別": gender,
        "年齡": age, "年齡組": age_grp, "教育程度": edu,
        "職業": occ, "婚姻狀況": marital, "媒體習慣": media_str,
        "國家信任指數": trust, "政黨傾向": pref, "厭惡政黨": dislike,
    })

df_out = pd.DataFrame(records)
out_path = "../data/personas_3000.xlsx"
df_out.to_excel(out_path, index=False)
print(f"✓ 已儲存 {out_path}  ({len(df_out)} rows)")

# ── 8. 驗證 ────────────────────────────────────────────────────────────────
print("\n=== 居住地 TOP 6 ===")
top6_real = {
    "新北市":0.1736,"臺北市":0.1047,"桃園市":0.1011,
    "臺中市":0.1231,"高雄市":0.1167,"臺南市":0.0795,
}
vc = df_out["居住地"].value_counts(normalize=True)
for city, real in sorted(top6_real.items(), key=lambda x: -x[1]):
    got = vc.get(city, 0)
    print(f"  {city}: 真實={real:.1%}  生成={got:.1%}  差={abs(got-real):.1%}")

print("\n=== 性別 ===")
vc = df_out["性別"].value_counts(normalize=True)
print(f"  男: 真實=49.2%  生成={vc.get('男',0):.1%}")
print(f"  女: 真實=50.8%  生成={vc.get('女',0):.1%}")

print("\n=== 年齡組 ===")
age_real = {"15–24歲":0.103,"25–34歲":0.150,"35–44歲":0.168,
            "45–54歲":0.181,"55–64歲":0.171,"65歲以上":0.227}
vc = df_out["年齡組"].value_counts(normalize=True)
for g, r in age_real.items():
    got = vc.get(g, 0)
    print(f"  {g}: 真實={r:.1%}  生成={got:.1%}  差={abs(got-r):.1%}")

print("\n=== 教育程度 ===")
edu_real = {"碩士以上":0.092,"大學":0.313,"專科":0.113,"高中(職)":0.285,"國中":0.107,"國小以下":0.090}
vc = df_out["教育程度"].value_counts(normalize=True)
for e, r in edu_real.items():
    got = vc.get(e, 0)
    print(f"  {e}: 真實={r:.1%}  生成={got:.1%}  差={abs(got-r):.1%}")

print("\n=== 職業 ===")
vc = df_out["職業"].value_counts(normalize=True)
print(vc.to_string())

print("\n=== 婚姻狀況 by 年齡組 (已婚率) ===")
marr_real = {"15–24歲":0.02,"25–34歲":0.24,"35–44歲":0.55,
             "45–54歲":0.63,"55–64歲":0.67,"65歲以上":0.62}
grp = df_out.groupby("年齡組")["婚姻狀況"].apply(lambda x: (x=="已婚").mean())
for g, r in marr_real.items():
    got = grp.get(g, 0)
    print(f"  {g}: 真實={r:.0%}  生成={got:.0%}  差={abs(got-r):.0%}")

# ── 9. 匯出真實分布 xlsx ────────────────────────────────────────────────────
dist_path = "../data/distributions_real.xlsx"
with pd.ExcelWriter(dist_path, engine="openpyxl") as writer:

    # 居住地
    df_reg = pd.DataFrame([
        {"縣市": r, "人口數": int(round(region_prop[r] * 23299132)),
         "人口佔比": round(region_prop[r], 6),
         "男性佔比": round(gender_prob[r][0], 6),
         "女性佔比": round(gender_prob[r][1], 6)}
        for r in regions
    ]).sort_values("人口佔比", ascending=False).reset_index(drop=True)
    df_reg.to_excel(writer, sheet_name="居住地", index=False)

    # 性別（全國）
    total_m = sum(int(row[3]) for _, row in df_gender.iterrows()
                  if str(row[2]).strip().replace(" ","") in regions and not pd.isna(row[3]))
    # use the official totals from 地區X性別 row 2
    r2 = df_gender.iloc[2]
    tot_m, tot_f = int(r2[3]), int(r2[4])
    df_sex = pd.DataFrame([
        {"性別": "男", "人口數": tot_m, "佔比": round(tot_m/(tot_m+tot_f), 6)},
        {"性別": "女", "人口數": tot_f, "佔比": round(tot_f/(tot_m+tot_f), 6)},
    ])
    df_sex.to_excel(writer, sheet_name="性別", index=False)

    # 年齡組（15+）
    age_group_data = {}
    for (lbl, n), (amin, amax) in zip(age_15plus, age_ranges):
        grp_lbl = age_to_group(amin)
        age_group_data[grp_lbl] = age_group_data.get(grp_lbl, 0) + n
    total_15plus = sum(age_group_data.values())
    df_age = pd.DataFrame([
        {"年齡組": g, "人口數": age_group_data[g],
         "佔比": round(age_group_data[g]/total_15plus, 6)}
        for g in GROUP_LABELS if g in age_group_data
    ])
    df_age.to_excel(writer, sheet_name="年齡組", index=False)

    # 年齡（5歲組，15+）
    df_age5 = pd.DataFrame([
        {"年齡組": lbl, "人口數": n,
         "佔比": round(n/sum(age_counts), 6)}
        for lbl, n in age_15plus
    ])
    df_age5.to_excel(writer, sheet_name="年齡(5歲組)", index=False)

    # 教育程度（全國）
    nat_edu_counts = nat_edu * total_15plus
    df_edu_out = pd.DataFrame([
        {"教育程度": cat, "推估人數": int(round(nat_edu_counts[i])),
         "佔比": round(float(nat_edu[i]), 6)}
        for i, cat in enumerate(EDU_CATS)
    ])
    df_edu_out.to_excel(writer, sheet_name="教育程度(全國)", index=False)

    # 教育程度（各縣市）
    edu_county_rows = []
    for r in regions:
        w = edu_by_region[r]
        for i, cat in enumerate(EDU_CATS):
            edu_county_rows.append({"縣市": r, "教育程度": cat, "佔比": round(float(w[i]), 6)})
    pd.DataFrame(edu_county_rows).to_excel(writer, sheet_name="教育程度(各縣市)", index=False)

    # 職業（全國就業者）
    df_occ_nat = pd.DataFrame([
        {"職業類別": cat, "就業比例(就業者中)": round(float(nat_occ[i]), 6)}
        for i, cat in enumerate(OCC_CATS)
    ])
    df_occ_nat.to_excel(writer, sheet_name="職業(全國就業者)", index=False)

    # 職業（各縣市就業者）
    occ_county_rows = []
    for city in city_rows:
        w = occ_by_region[city]
        for i, cat in enumerate(OCC_CATS):
            occ_county_rows.append({"縣市": city, "職業類別": cat,
                                    "就業比例(就業者中)": round(float(w[i]), 6)})
    pd.DataFrame(occ_county_rows).to_excel(writer, sheet_name="職業(各縣市就業者)", index=False)

    # 婚姻狀況（各年齡有偶率）
    age_bands = ["15–19歲","20–24歲","25–29歲","30–34歲","35–39歲","40–44歲",
                 "45–49歲","50–54歲","55–59歲","60–64歲","65–69歲","70–74歲",
                 "75–79歲","80–84歲","85–89歲","90–94歲","95–99歲","100歲以上"]
    df_marr_out = pd.DataFrame([
        {"年齡組": age_bands[i],
         "總人口": int(total_row[i]),
         "有偶人口": int(married_row[i]),
         "已婚率(有偶)": round(float(p_married_by_5yr[i]), 6)}
        for i in range(18)
    ])
    df_marr_out.to_excel(writer, sheet_name="婚姻狀況(各年齡)", index=False)

    # 媒體習慣（各年齡組平台使用率）
    media_rows = []
    age_group_display = {
        "15–24歲": "16–25歲", "25–34歲": "26–35歲", "35–44歲": "36–45歲",
        "45–54歲": "46–55歲", "55–64歲": "56–65歲", "65歲以上": "66歲以上",
    }
    for grp, probs in media_prob.items():
        for i, plat in enumerate(PLATFORMS):
            media_rows.append({
                "年齡組(NCC調查)": age_group_display.get(grp, grp),
                "平台": plat,
                "使用率": round(float(probs[i]), 6),
            })
    pd.DataFrame(media_rows).to_excel(writer, sheet_name="媒體習慣(各年齡組)", index=False)

    # 政黨傾向（民調原始分布）
    pref_real = pol["party_pref"].value_counts()
    pref_total = pref_real.sum()
    df_pref_real = pd.DataFrame([
        {"政黨": k, "民調人數": int(v), "民調佔比": round(v/pref_total, 6)}
        for k, v in pref_real.items()
    ])
    df_pref_real.to_excel(writer, sheet_name="政黨傾向(民調原始)", index=False)

    # 厭惡政黨（民調原始分布）
    dis_real = pol["party_dislike"].value_counts()
    dis_total = dis_real.sum()
    df_dis_real = pd.DataFrame([
        {"政黨": k, "民調人數": int(v), "民調佔比": round(v/dis_total, 6)}
        for k, v in dis_real.items()
    ])
    df_dis_real.to_excel(writer, sheet_name="厭惡政黨(民調原始)", index=False)

    # 國家信任指數（民調各年齡組）
    trust_by_grp = (
        pol.dropna(subset=["trust","age_grp"])
           .groupby("age_grp")["trust"]
           .agg(樣本數="count", 平均值="mean", 中位數="median",
                最小值="min", 最大值="max")
           .round(4).reset_index()
           .rename(columns={"age_grp":"年齡組"})
    )
    trust_by_grp.to_excel(writer, sheet_name="國家信任指數(民調)", index=False)

    # ── 抽樣分配結果 ──────────────────────────────────────────────────────────
    sample_rows = []

    def _add_dim(dim, series, real_map=None):
        vc = series.value_counts().sort_index()
        total = vc.sum()
        for cat, cnt in vc.items():
            row = {
                "維度": dim,
                "類別": cat,
                "抽樣人數": int(cnt),
                "抽樣佔比": round(cnt / total, 6),
                "真實佔比": round(real_map[cat], 6) if real_map and cat in real_map else None,
                "差距": round(cnt / total - real_map[cat], 6)
                        if real_map and cat in real_map else None,
            }
            sample_rows.append(row)

    # 居住地
    _add_dim("居住地", df_out["居住地"],
             {r: region_prop[r] for r in regions})

    # 性別
    tot_pop = tot_m + tot_f
    _add_dim("性別", df_out["性別"],
             {"男": tot_m / tot_pop, "女": tot_f / tot_pop})

    # 年齡組
    age_real_map = {g: age_group_data.get(g, 0) / total_15plus for g in GROUP_LABELS}
    _add_dim("年齡組", df_out["年齡組"], age_real_map)

    # 教育程度
    edu_real_map = {EDU_CATS[i]: float(nat_edu[i]) for i in range(len(EDU_CATS))}
    _add_dim("教育程度", df_out["教育程度"], edu_real_map)

    # 職業（就業者部分與真實就業結構比對）
    _add_dim("職業", df_out["職業"])

    # 婚姻狀況
    _add_dim("婚姻狀況", df_out["婚姻狀況"])

    # 婚姻狀況（各年齡組已婚率）
    for grp in GROUP_LABELS:
        sub = df_out[df_out["年齡組"] == grp]["婚姻狀況"]
        if len(sub) == 0:
            continue
        p_m = (sub == "已婚").mean()
        sample_rows.append({
            "維度": f"已婚率｜{grp}",
            "類別": "已婚",
            "抽樣人數": int((sub == "已婚").sum()),
            "抽樣佔比": round(float(p_m), 6),
            "真實佔比": None,
            "差距": None,
        })

    # 媒體習慣（各平台被選中的比例）
    all_platforms = [p for cell in df_out["媒體習慣"] for p in str(cell).split("、")]
    plat_series = pd.Series(all_platforms)
    plat_vc = plat_series.value_counts()
    n_personas = len(df_out)
    for plat, cnt in plat_vc.items():
        sample_rows.append({
            "維度": "媒體習慣(使用人數佔比)",
            "類別": plat,
            "抽樣人數": int(cnt),
            "抽樣佔比": round(cnt / n_personas, 6),
            "真實佔比": None,
            "差距": None,
        })

    # 政黨傾向（抽樣 vs 民調）
    pref_real_map = (pol["party_pref"].value_counts(normalize=True).to_dict())
    _add_dim("政黨傾向", df_out["政黨傾向"], pref_real_map)

    # 厭惡政黨（抽樣 vs 民調）
    dis_real_map = (pol["party_dislike"].value_counts(normalize=True).to_dict())
    _add_dim("厭惡政黨", df_out["厭惡政黨"], dis_real_map)

    # 國家信任指數（抽樣各年齡組統計）
    trust_samp = (
        df_out.groupby("年齡組")["國家信任指數"]
              .agg(抽樣人數="count", 平均值="mean", 中位數="median",
                   最小值="min", 最大值="max")
              .round(4).reset_index()
    )
    for _, row in trust_samp.iterrows():
        sample_rows.append({
            "維度": f"國家信任指數｜{row['年齡組']}",
            "類別": "平均值",
            "抽樣人數": int(row["抽樣人數"]),
            "抽樣佔比": round(row["平均值"], 4),
            "真實佔比": None,
            "差距": None,
        })

    df_sample = pd.DataFrame(sample_rows,
                             columns=["維度","類別","抽樣人數","抽樣佔比","真實佔比","差距"])
    df_sample.to_excel(writer, sheet_name="抽樣分配結果", index=False)

print(f"✓ 已儲存 {dist_path}  (13 sheets)")
