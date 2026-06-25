#!/usr/bin/env python3
"""
taiwan_persona_v2.py — 全台 profile 的 demographics 生成（v2 階段）。

只生成「台北以外」的 21 縣市（台北 314 由 finalize 從 Taipei 3000 抽樣併入）。
資料來源：data/derived/regions/*.csv（prep_taiwan_sources.py 產出，經 region_profile loaders）。
欄位與類別字串刻意對齊 Taipei 版（碩士以上/高中(職)/國小以下、民進黨…、X(Twitter)…），
使 finalize 與台北重用列 concat 後 schema 一致。

對應 taipei_persona_v2.py 的欄位邏輯（年齡 floor、職業 by 年齡、媒體 65+ 禁用/LINE 保底、
國家認同與厭惡政黨民調分層），差異僅在：地理單位＝縣市、各結構改讀 region CSV。
僅在 PERSONA_PROFILE=taiwan 時由 run_pipeline 呼叫。
"""

import numpy as np
import pandas as pd

import region_profile as rp
from pipeline_common import (
    N_TOTAL, RAW_DIR, stage_path, PERSONAS_SHEET, make_rng,
    AGE_GROUP_LABELS as GROUP_LABELS, OCC_CATS, age_to_group,
)

rng = make_rng()
BASE = str(RAW_DIR) + "/"

# ── 類別字串對齊 Taipei 版 ────────────────────────────────────────────────────
EDU_CATS = ['碩士以上', '大學', '專科', '高中(職)', '國中', '國小以下']
# census_edu.csv 欄名 → Taipei 教育類別
EDU_SRC_TO_CAT = {
    '研究所以上': '碩士以上', '大學': '大學', '專科': '專科',
    '高中職': '高中(職)', '國中': '國中', '國小及以下': '國小以下',
}
PARTY_CATS = ['民進黨', '國民黨', '台灣民眾黨', '其他政黨']
PARTY_SRC = {'DPP': '民進黨', 'KMT': '國民黨', 'TPP': '台灣民眾黨', 'Other': '其他政黨'}

# 媒體平台（對齊 Taipei PLATFORMS）；值 = media_age.csv 欄名
PLATFORMS = ['LINE', 'Facebook', 'YouTube', 'Instagram', 'TikTok', '小紅書', 'WeChat',
             'Threads', 'X(Twitter)', 'WhatsApp', 'Telegram', 'Pinterest', 'LinkedIn',
             'Tumblr', 'Snapchat']
MEDIA_COL = {  # PLATFORMS 名 → CSV 欄名（多數同名，兩個例外）
    'X(Twitter)': 'X(前身為Twitter)', 'Snapchat': 'SnapChat',
}
BANNED_65PLUS = {'Instagram', 'TikTok', '小紅書', 'Threads', 'X(Twitter)', 'LinkedIn'}

# 年齡 floor（同 Taipei）
EDU_MIN_AGE = {'碩士以上': 22, '大學': 18, '專科': 19, '高中(職)': 15, '國中': 0, '國小以下': 0}
EDU_PRIMARY_AGE_MULT = [(25, 0.0), (35, 0.05), (50, 0.30)]

# 年齡組 → (下限, 上限) 供組內均勻取齡
AGE_GROUP_RANGE = {
    '15–24歲': (15, 24), '25–34歲': (25, 34), '35–44歲': (35, 44),
    '45–54歲': (45, 54), '55–64歲': (55, 64), '65歲以上': (65, 90),
}

# ── 載入 region-keyed 資料 ───────────────────────────────────────────────────
GEN_REGIONS = rp.GEN_REGIONS                 # 21 縣市（不含台北）
counts_all = rp.allocate(N_TOTAL)            # 含台北
gender_ratio = rp.load_gender()
age_df = rp.load_age()
edu_df = rp.load_edu()
occ_df = rp.load_occupation()
married_rate = rp.load_marriage_age()        # age_group → 有偶率（全國）
media_df = rp.load_media_age()               # age_group × 平台
party_df = rp.load_election_party()          # region × DPP/KMT/TPP/Other

# 各縣市年齡組權重、教育權重、職業權重（正規化）
age_w = {r: (age_df.loc[r, GROUP_LABELS] / age_df.loc[r, GROUP_LABELS].sum()).values
         for r in GEN_REGIONS}
edu_w_src = {r: (edu_df.loc[r] / edu_df.loc[r].sum()) for r in GEN_REGIONS}
EDU_SRC_ORDER = ['研究所以上', '大學', '專科', '高中職', '國中', '國小及以下']
edu_w = {r: np.array([edu_w_src[r][s] for s in EDU_SRC_ORDER]) for r in GEN_REGIONS}  # 對齊 EDU_CATS 序
occ_w = {r: (occ_df.loc[r, OCC_CATS] / occ_df.loc[r, OCC_CATS].sum()).values for r in GEN_REGIONS}
party_w = {r: np.array([party_df.loc[r, k] for k in ['DPP', 'KMT', 'TPP', 'Other']]) for r in GEN_REGIONS}
media_rate = {g: np.array([float(media_df.loc[g, MEDIA_COL.get(p, p)]) for p in PLATFORMS])
              for g in GROUP_LABELS}

# ── 國家認同 & 厭惡政黨（Political.xlsx，同 Taipei 的民調分層）──────────────────
pol = pd.read_excel(BASE + "Political.xlsx", sheet_name="原始回答資料")
COUNTY_CODE = {
    1: '新北市', 2: '臺北市', 3: '桃園市', 4: '臺中市', 5: '臺南市', 6: '高雄市',
    7: '宜蘭縣', 8: '新竹縣', 9: '苗栗縣', 10: '彰化縣', 11: '南投縣', 12: '雲林縣',
    13: '嘉義縣', 14: '屏東縣', 15: '臺東縣', 16: '花蓮縣', 17: '澎湖縣', 18: '基隆市',
    19: '新竹市', 20: '嘉義市', 21: '金門縣', 22: '連江縣',
}
REGION_GROUP = {
    '北部': ['新北市', '臺北市', '桃園市', '基隆市', '新竹市', '新竹縣', '宜蘭縣'],
    '中部': ['臺中市', '苗栗縣', '彰化縣', '南投縣', '雲林縣'],
    '南部': ['臺南市', '高雄市', '嘉義市', '嘉義縣', '屏東縣', '澎湖縣'],
    '東部': ['臺東縣', '花蓮縣'], '離島': ['金門縣', '連江縣'],
}
COUNTY_TO_RG = {c: g for g, cs in REGION_GROUP.items() for c in cs}
PARTY_Q13 = {1: '民進黨', 2: '國民黨', 3: '台灣民眾黨', 94: '其他政黨',
             95: '都很討厭', 96: '不知道/沒意見', 98: '拒答'}
EDU_SURVEY = {1: '國小以下', 2: '國中', 3: '高中(職)', 4: '專科', 5: '大學', 6: '碩士以上'}


def _trust(row):
    vals = [5 - row[q] for q in ['vQ2', 'vQ3', 'vQ4', 'vQ5'] if 1 <= row[q] <= 4]
    return round((np.mean(vals) - 1) / 3 * 10, 4) if vals else np.nan


def _survey_age_grp(v):
    return ({1: '15–24歲', 2: '25–34歲', 3: '25–34歲', 4: '35–44歲', 5: '35–44歲',
             6: '45–54歲', 7: '45–54歲', 8: '55–64歲', 9: '55–64歲',
             10: '65歲以上', 11: '65歲以上'}).get(v)


pol['trust'] = pol.apply(_trust, axis=1)
pol['age_grp'] = pol['vQ14'].apply(_survey_age_grp)
pol['edu_cat'] = pol['vQ15'].map(EDU_SURVEY)
pol['gender'] = pol['vQ16'].map({1: '男', 2: '女'})
pol['county'] = pol['vQ1'].map(COUNTY_CODE)
pol['rg'] = pol['county'].map(COUNTY_TO_RG)
pol['party_dislike'] = pol['vQ13'].map(PARTY_Q13)

MIN_POOL = 10
MAIN_PARTIES = {'民進黨', '國民黨', '台灣民眾黨'}


def _pool(county, age_grp, edu, gender_val):
    """分層比對：persona 自身縣市 → 同區域 → 同年齡，逐步放寬至 N≥10。"""
    p = pol
    rg = COUNTY_TO_RG.get(county)
    for mask in [
        (p['county'] == county) & (p['age_grp'] == age_grp) & (p['edu_cat'] == edu) & (p['gender'] == gender_val),
        (p['county'] == county) & (p['age_grp'] == age_grp) & (p['gender'] == gender_val),
        (p['county'] == county) & (p['age_grp'] == age_grp),
        (p['rg'] == rg) & (p['age_grp'] == age_grp) & (p['edu_cat'] == edu) & (p['gender'] == gender_val),
        (p['rg'] == rg) & (p['age_grp'] == age_grp) & (p['gender'] == gender_val),
        (p['rg'] == rg) & (p['age_grp'] == age_grp),
        (p['age_grp'] == age_grp) & (p['gender'] == gender_val),
        (p['age_grp'] == age_grp),
    ]:
        sub = p[mask]
        if len(sub) >= MIN_POOL:
            return sub
    return p


def sample_political(county, age_grp, edu, gender_val, party_pref):
    pool = _pool(county, age_grp, edu, gender_val)
    tv = pool['trust'].dropna().values
    trust = (round(float(np.clip(float(rng.choice(tv)) + rng.normal(0, 0.25), 0, 10)), 1)
             if len(tv) else round(float(rng.uniform(0, 10)), 1))
    dv = pool['party_dislike'].dropna()
    if party_pref in MAIN_PARTIES:
        f = dv[dv != party_pref]
        if len(f) > 0:
            dv = f
    dislike = str(rng.choice(dv.values)) if len(dv) else '不知道/沒意見'
    return trust, dislike


# ── 職業（status by 年齡，同 Taipei；就業者用各縣市 OCC 權重）──────────────────
def sample_occ(age, edu, region):
    if age <= 15:
        return '學生'
    if age <= 17:
        cats, w = ['學生', '就業', '其他/待業'], [0.80, 0.15, 0.05]
    elif age <= 22:
        cats, w = ['學生', '就業', '其他/待業'], [0.55, 0.40, 0.05]
    elif age <= 24:
        cats, w = ['學生', '就業', '家管', '其他/待業'], [0.30, 0.60, 0.05, 0.05]
    elif age <= 59:
        cats, w = ['就業', '家管', '其他/待業'], [0.84, 0.12, 0.04]
    elif age <= 64:
        cats, w = ['就業', '退休', '家管', '其他/待業'], [0.50, 0.38, 0.09, 0.03]
    elif age <= 69:
        cats, w = ['就業', '退休', '家管', '其他/待業'], [0.20, 0.70, 0.08, 0.02]
    elif age <= 74:
        cats, w = ['就業', '退休', '家管', '其他/待業'], [0.06, 0.84, 0.08, 0.02]
    elif age < 80:
        cats, w = ['退休', '家管', '其他/待業'], [0.87, 0.11, 0.02]
    else:
        cats, w = ['退休', '家管'], [0.85, 0.15]
    pw = np.array(w, dtype=float); pw /= pw.sum()
    status = rng.choice(cats, p=pw)
    if status != '就業':
        return status
    mask = np.ones(len(OCC_CATS), dtype=float)
    if age >= 70:
        allowed = {'專業人員'}
        for j, c in enumerate(OCC_CATS):
            if c not in allowed:
                mask[j] = 0.0
    elif age >= 65:
        allowed = {'管理/主管', '專業人員'}
        for j, c in enumerate(OCC_CATS):
            if c not in allowed:
                mask[j] = 0.0
    elif age < 25:
        mask[OCC_CATS.index('管理/主管')] = 0.0
    if age < 65 and edu in ('國中', '國小以下'):
        mask[OCC_CATS.index('管理/主管')] = 0.0
        mask[OCC_CATS.index('專業人員')] = 0.0
    w_occ = occ_w[region] * mask
    if w_occ.sum() == 0:
        w_occ = occ_w[region].copy()
    return rng.choice(OCC_CATS, p=w_occ / w_occ.sum())


# ── 生成 ─────────────────────────────────────────────────────────────────────
region_seq = [r for r in GEN_REGIONS for _ in range(counts_all[r])]
rng.shuffle(region_seq)
n_gen = len(region_seq)

# 性別精確配額（各縣市）
gender_iter = {}
for r in GEN_REGIONS:
    n_r = counts_all[r]
    n_male = int(np.round(gender_ratio[r][0] * n_r))
    gl = ['男'] * n_male + ['女'] * (n_r - n_male)
    rng.shuffle(gl)
    gender_iter[r] = iter(gl)

records = []
TAIPEI_QUOTA = counts_all['臺北市']
for k in range(n_gen):
    region = region_seq[k]
    pid = TAIPEI_QUOTA + k + 1          # id 與台北重用列錯開（台北佔 1..314）
    gender = next(gender_iter[region])

    grp = rng.choice(GROUP_LABELS, p=age_w[region])
    lo, hi = AGE_GROUP_RANGE[grp]
    age = int(rng.integers(lo, hi + 1))
    age_grp = age_to_group(age)

    ew = edu_w[region].copy()
    for i, cat in enumerate(EDU_CATS):
        if age < EDU_MIN_AGE.get(cat, 0):
            ew[i] = 0.0
    pi = EDU_CATS.index('國小以下')
    for age_lt, mult in EDU_PRIMARY_AGE_MULT:
        if age < age_lt:
            ew[pi] *= mult
            break
    s = ew.sum()
    ew = ew / s if s > 0 else np.ones(len(EDU_CATS)) / len(EDU_CATS)
    edu = rng.choice(EDU_CATS, p=ew)

    occ = sample_occ(age, edu, region)
    if occ == '家管' and gender == '男' and rng.random() < 0.90:
        for _ in range(10):
            no = sample_occ(age, edu, region)
            if no != '家管':
                occ = no
                break

    if occ == '家管':
        marital = rng.choice(['已婚', '未婚'], p=[0.88, 0.12])
    else:
        pm = min(float(married_rate[age_grp]), 1.0)
        marital = rng.choice(['已婚', '未婚'], p=[pm, 1 - pm])

    mp = media_rate[age_grp].copy()
    if age >= 65:
        for mi, pl in enumerate(PLATFORMS):
            if pl in BANNED_65PLUS:
                mp[mi] = 0.0
    used = [PLATFORMS[i] for i, pp in enumerate(mp) if rng.random() < pp]
    if 'LINE' not in used:
        used = ['LINE'] + used
    media_str = '、'.join(used)

    pw_region = party_w[region] / party_w[region].sum()
    party_pref = PARTY_SRC[['DPP', 'KMT', 'TPP', 'Other'][int(rng.choice(4, p=pw_region))]]

    trust, dislike = sample_political(region, age_grp, edu, gender, party_pref)

    records.append({
        'id': pid, '居住地': region, '性別': gender, '年齡': age, '年齡組': age_grp,
        '教育程度': edu, '職業': occ, '婚姻狀況': marital, '媒體習慣': media_str,
        '國家認同': trust, '政黨傾向': party_pref, '厭惡政黨': dislike,
    })

df_out = pd.DataFrame(records)

# ── 驗證摘要 ─────────────────────────────────────────────────────────────────
print(f"生成 {len(df_out)} 列（台北以外 21 縣市；台北 {TAIPEI_QUOTA} 由 finalize 併入）")
print("\n各縣市人數（抽查）:")
print(df_out['居住地'].value_counts().head(6).to_string())
print("\n政黨傾向（全台生成列）:")
print(df_out['政黨傾向'].value_counts(normalize=True).round(3).to_string())
print("\n教育程度:")
print(df_out['教育程度'].value_counts(normalize=True).round(3).to_string())

# ── 儲存（多 sheet，與 Taipei v2 一致的 PERSONAS_SHEET 契約）──────────────────
out_path = stage_path("v2")
out_path.parent.mkdir(parents=True, exist_ok=True)
with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
    df_out.to_excel(writer, sheet_name=PERSONAS_SHEET, index=False)
    # 縣市 × 政黨傾向 驗證
    rows = []
    for r in GEN_REGIONS:
        sub = df_out[df_out['居住地'] == r]['政黨傾向'].value_counts()
        tot = sub.sum()
        ref = {PARTY_SRC[k2]: party_df.loc[r, k2] for k2 in ['DPP', 'KMT', 'TPP', 'Other']}
        for cat in PARTY_CATS:
            rows.append({'縣市': r, '政黨': cat,
                         '抽樣佔比': round(sub.get(cat, 0) / tot, 4) if tot else 0,
                         '選舉得票率': round(ref.get(cat, 0), 4)})
    pd.DataFrame(rows).to_excel(writer, sheet_name='政黨傾向', index=False)

print(f"\n✓ 已儲存 {out_path}  ({len(df_out)} rows)")
