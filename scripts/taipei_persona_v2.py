import pandas as pd
import numpy as np

rng = np.random.default_rng(42)

BASE_TP      = "../taipei_data/"
BASE_TP_2020 = "../taipei_data_2020/"
BASE         = "../data/"

# ── 1. 居住地 & 性別（113_genderXarea.ods 12月份）─────────────────────────────
df_gender = pd.read_excel(BASE_TP + "113_genderXarea.ods", engine="odf", sheet_name="12月", header=None)

DISTRICTS = ['松山區','信義區','大安區','中山區','中正區','大同區',
             '萬華區','文山區','南港區','內湖區','士林區','北投區']

pop_data = {}   # {district: (total, male, female)}
for i in range(4, 16):
    row = df_gender.iloc[i]
    dist = str(row[0]).strip()
    if dist not in DISTRICTS:
        continue
    pop_data[dist] = (int(row[6]), int(row[7]), int(row[8]))

total_tp_pop = sum(v[0] for v in pop_data.values())
dist_weights = np.array([pop_data[d][0] / total_tp_pop for d in DISTRICTS])
gender_prob  = {d: (pop_data[d][1] / pop_data[d][0],
                    pop_data[d][2] / pop_data[d][0]) for d in DISTRICTS}

# ── 2. 年齡 by 行政區（113_ageXarea.ods）──────────────────────────────────────
df_age = pd.read_excel(BASE_TP + "113_ageXarea.ods", engine="odf", sheet_name="年齡", header=None)

# 5歲組合計欄位（from header row 1）
AGE5_COLS = {
    '15–19': 22, '20–24': 28, '25–29': 34, '30–34': 40,
    '35–39': 46, '40–44': 52, '45–49': 58, '50–54': 64,
    '55–59': 70, '60–64': 76, '65–69': 82, '70–74': 88,
    '75–79': 94, '80–84': 100, '85–89': 106, '90–94': 112,
    '95–99': 118, '100+': 124,
}

AGE5_MIN = {
    '15–19': 15, '20–24': 20, '25–29': 25, '30–34': 30,
    '35–39': 35, '40–44': 40, '45–49': 45, '50–54': 50,
    '55–59': 55, '60–64': 60, '65–69': 65, '70–74': 70,
    '75–79': 75, '80–84': 80, '85–89': 85, '90–94': 90,
    '95–99': 95, '100+': 100,
}
AGE5_MAX = {
    '15–19': 19, '20–24': 24, '25–29': 29, '30–34': 34,
    '35–39': 39, '40–44': 44, '45–49': 49, '50–54': 54,
    '55–59': 59, '60–64': 64, '65–69': 69, '70–74': 74,
    '75–79': 79, '80–84': 84, '85–89': 89, '90–94': 94,
    '95–99': 99, '100+': 100,
}

DIST_AGE_ROW = {
    '松山區': 5,  '信義區': 107, '大安區': 233, '中山區': 395,
    '中正區': 524,'大同區': 620, '萬華區': 698, '文山區': 809,
    '南港區': 941,'內湖區': 1004,'士林區': 1124,'北投區': 1280,
}

def _safe_int(v):
    try: return int(str(v).replace(',', '').strip())
    except: return 0

age5_weights = {}   # {district: {band: weight}}
for dist, ridx in DIST_AGE_ROW.items():
    row = df_age.iloc[ridx]
    counts = {band: _safe_int(row[col]) for band, col in AGE5_COLS.items()}
    total = sum(counts.values())
    age5_weights[dist] = {band: cnt / total for band, cnt in counts.items()} if total > 0 else {band: 1/len(AGE5_COLS) for band in AGE5_COLS}

GROUP_LABELS = ['15–24歲','25–34歲','35–44歲','45–54歲','55–64歲','65歲以上']

def age_to_group(a):
    if a <= 24: return '15–24歲'
    if a <= 34: return '25–34歲'
    if a <= 44: return '35–44歲'
    if a <= 54: return '45–54歲'
    if a <= 64: return '55–64歲'
    return '65歲以上'

def sample_age(district):
    w = age5_weights[district]
    bands = list(w.keys())
    probs = np.array([w[b] for b in bands])
    band  = rng.choice(bands, p=probs / probs.sum())
    lo = AGE5_MIN[band]
    hi = min(AGE5_MAX[band], 100)
    return int(rng.integers(lo, hi + 1))

# ── 3. 教育程度 by 行政區（113_educationXarea.ods）───────────────────────────
df_edu = pd.read_excel(BASE_TP + "113_educationXarea.ods", engine="odf", sheet_name="工作表1", header=None)

EDU_CATS = ['碩士以上','大學','專科','高中(職)','國中','國小以下']

# 各學歷最低合理年齡（台灣學制：高中15歲入學、大學18歲入學、碩士22歲入學）
EDU_MIN_AGE = {
    '碩士以上': 22,   # 大學畢業22歲後才能入碩
    '大學':     18,   # 18歲入大學
    '專科':     19,   # QA issue 2：專科（二專/五專畢業）最低取得年齡約 19–20 歲，17 歲不可能已具專科學歷
    '高中(職)': 15,   # 15歲入高中/高職
    '國中':      0,
    '國小以下':  0,
}

# QA issue 5：壓低年輕族群「國小以下」機率
# 台灣自1968年實施九年國教，1976年後出生者（現齡<50）僅國小以下學歷比例極低，
# <35 應趨近 0、15–24 幾乎不可能（義務教育普及）。
# (age 上限, 國小以下機率乘數)，由小至大依序套用第一個符合者。
EDU_PRIMARY_AGE_MULT = [
    (25, 0.0),    # <25：直接移除「國小以下」
    (35, 0.05),   # 25–34：趨近 0
    (50, 0.30),   # 35–49：大幅壓低
]

def _safe(v):
    try: return float(v)
    except: return 0.0

def _edu_from_row(row):
    ma_plus = _safe(row[5]) + _safe(row[6]) + _safe(row[7]) + _safe(row[8])
    univ    = _safe(row[9]) + _safe(row[10])
    college = _safe(row[11]) + _safe(row[12]) + _safe(row[13]) + _safe(row[14])
    highsch = _safe(row[15]) + _safe(row[16]) + _safe(row[17]) + _safe(row[18]) + _safe(row[19])
    jrhigh  = _safe(row[20]) + _safe(row[21]) + _safe(row[22]) + _safe(row[23])
    primary = _safe(row[24]) + _safe(row[25]) + _safe(row[26]) + _safe(row[27])
    arr = np.array([ma_plus, univ, college, highsch, jrhigh, primary], dtype=float)
    t = arr.sum()
    return arr / t if t > 0 else None

edu_by_dist = {}
for idx in range(6, len(df_edu)):
    row    = df_edu.iloc[idx]
    dist   = str(row[0]).strip()
    age_lb = str(row[1]).strip()
    gender = str(row[2]).strip()
    if dist in DISTRICTS and age_lb == '總計' and gender == '計':
        arr = _edu_from_row(row)
        if arr is not None:
            edu_by_dist[dist] = arr

# fallback to 臺北整體
taipei_edu = None
for idx in range(6, len(df_edu)):
    row = df_edu.iloc[idx]
    if str(row[0]).strip() == '總計' and str(row[1]).strip() == '總計' and str(row[2]).strip() == '計':
        taipei_edu = _edu_from_row(row)
        break

for d in DISTRICTS:
    if d not in edu_by_dist:
        edu_by_dist[d] = taipei_edu

# ── 4. 婚姻（Basic.xlsx 年齡x婚姻 基準 + 113_marryXarea.ods 區調整）─────────
df_marr = pd.read_excel(BASE + "Basic.xlsx", sheet_name="年齡x婚姻", header=None)
total_row_m   = df_marr.iloc[5, 3:21].values.astype(float)
married_row_m = df_marr.iloc[11, 3:21].values.astype(float)
p_married_5yr = married_row_m / total_row_m  # 18個5歲組 (15-19, 20-24, …)

# 各區 15+ 人口（用於計算婚姻密度）
age15plus_pop = {
    '松山區': 165240, '信義區': 184028, '大安區': 248145, '中山區': 191841,
    '中正區': 125357, '大同區': 105212, '萬華區': 157267, '文山區': 227579,
    '南港區': 100028, '內湖區': 237121, '士林區': 234616, '北投區': 211410,
}

marry_2024 = {
    '松山區': 1359, '信義區': 928, '大安區': 1360, '中山區': 797,
    '中正區': 1479, '大同區': 957, '萬華區': 983, '文山區': 622,
    '南港區': 1131, '內湖區': 1032, '士林區': 1230, '北投區': 1246,
}
city_total_marry = 13124
city_15plus_pop  = sum(age15plus_pop.values())
city_marry_rate  = city_total_marry / city_15plus_pop

district_marry_factor = {
    dist: float(np.clip(marry_2024[dist] / age15plus_pop[dist] / city_marry_rate, 0.6, 1.5))
    for dist in DISTRICTS
}

def p_married(age, district):
    idx  = min((age - 15) // 5, 17)
    base = float(p_married_5yr[idx])
    return min(base * district_marry_factor.get(district, 1.0), 1.0)

# ── 5. 職業（113_career.png 數字，臺北市就業結構）────────────────────────────
OCC_CATS = ['管理/主管','專業人員','技術/助理專業','事務人員','服務/銷售','農林漁牧','技術工/勞工']

_occ_raw = np.array([418, 1236, 581, 1059, 761, 4, 650], dtype=float)
TAIPEI_OCC_W = _occ_raw / _occ_raw.sum()

NON_EMP_CATS = ['家管','學生','退休','其他/待業']

def sample_occ(age, edu):
    if age <= 15:        # QA issue 1：15 歲（含）以下仍屬國中義務教育階段，強制學生
        return '學生'
    if age <= 17:
        cats = ['學生','就業','其他/待業'];          w = [0.80, 0.15, 0.05]
    elif age <= 22:
        cats = ['學生','就業','其他/待業'];          w = [0.55, 0.40, 0.05]
    elif age <= 24:
        cats = ['學生','就業','家管','其他/待業'];   w = [0.30, 0.60, 0.05, 0.05]
    elif age <= 59:
        cats = ['就業','家管','其他/待業'];          w = [0.84, 0.12, 0.04]
    elif age <= 64:
        cats = ['就業','退休','家管','其他/待業'];   w = [0.50, 0.38, 0.09, 0.03]
    elif age <= 69:          # Issue 5：65–69，退休為主，部分就業（限高階職）
        cats = ['就業','退休','家管','其他/待業']; w = [0.20, 0.70, 0.08, 0.02]
    elif age <= 74:          # Issue 5：70–74
        cats = ['就業','退休','家管','其他/待業']; w = [0.06, 0.84, 0.08, 0.02]
    elif age < 80:           # Issue 5：75–79，僅退休或家管
        cats = ['退休','家管','其他/待業'];        w = [0.87, 0.11, 0.02]
    else:                    # Issue 5：80+，強制退休或家管
        cats = ['退休','家管'];                   w = [0.85, 0.15]

    pw = np.array(w, dtype=float); pw /= pw.sum()
    status = rng.choice(cats, p=pw)
    if status == '就業':
        occ_mask = np.ones(len(OCC_CATS), dtype=float)
        # 年齡約束（優先級最高）
        if age >= 70:        # Issue 5：70+ 只能專業人員
            _allowed = {'專業人員'}
            for _j, _c in enumerate(OCC_CATS):
                if _c not in _allowed: occ_mask[_j] = 0.0
        elif age >= 65:      # Issue 5：65–69 只能管理/主管或專業人員
            _allowed = {'管理/主管', '專業人員'}
            for _j, _c in enumerate(OCC_CATS):
                if _c not in _allowed: occ_mask[_j] = 0.0
        elif age < 25:       # 年齡太小不可能擔任管理職
            occ_mask[OCC_CATS.index('管理/主管')] = 0.0
        # 低學歷約束（僅 age < 65 時套用，避免與年齡約束衝突）
        if age < 65 and edu in ('國中', '國小以下'):
            occ_mask[OCC_CATS.index('管理/主管')] = 0.0
            occ_mask[OCC_CATS.index('專業人員')] = 0.0
        w_occ = TAIPEI_OCC_W * occ_mask
        if w_occ.sum() == 0:
            w_occ = TAIPEI_OCC_W.copy()
        return rng.choice(OCC_CATS, p=w_occ / w_occ.sum())
    return status

# ── 6. 媒體習慣（Basic.xlsx 年齡x媒體，與 analysis.py 相同）─────────────────
df_media = pd.read_excel(BASE + "Basic.xlsx", sheet_name="年齡x媒體", header=None)

PLATFORMS     = ['LINE','Facebook','YouTube','Instagram','TikTok','小紅書','WeChat',
                 'Threads','X(Twitter)','WhatsApp','Telegram','Pinterest','LinkedIn',
                 'Tumblr','Snapchat']
PLATFORM_COLS = [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]

# Issue 2：65 歲以上禁用的平台（使用率 < 2%，排除以避免不合理組合）
BANNED_65PLUS = {'Instagram', 'TikTok', '小紅書', 'Threads', 'X(Twitter)', 'LinkedIn'}

MEDIA_AGE_ROWS = {
    '15–24歲': 11, '25–34歲': 12, '35–44歲': 13,
    '45–54歲': 14, '55–64歲': 15, '65歲以上': 16,
}

media_prob = {}
for grp, ridx in MEDIA_AGE_ROWS.items():
    row = df_media.iloc[ridx]
    media_prob[grp] = np.array([_safe(row[c]) for c in PLATFORM_COLS])

# ── 7. 政黨傾向（2020不分區立委得票，taipei_data_2020）──────────────────────
df_party = pd.read_excel(
    BASE_TP_2020 + "不分區立委-A05-6-得票數一覽表(臺北市).xls",
    sheet_name="臺北市", header=None
)

PARTY_CATS = ['民進黨','國民黨','台灣民眾黨','其他政黨']

_COL_KMT  = 11          # 中國國民黨（第9黨）
_COL_DPP  = 16          # 民主進步黨（第14黨）
_COL_TPP  = 17          # 台灣民眾黨（第15黨）
_ALL_COLS = list(range(3, 22))   # 全部19黨欄位

# 取資料列（row6起）；forward-fill 行政區名；只保留投開票所列
df_ps = df_party.iloc[6:].copy().reset_index(drop=True)
df_ps[0] = df_ps[0].astype(str).replace('nan', np.nan).ffill()
df_ps[0] = df_ps[0].str.strip().str.replace('　', '').str.replace(' ', '')
df_ps = df_ps[df_ps[2].apply(lambda x: str(x).replace(',', '').strip().isdigit())]

for c in _ALL_COLS:
    df_ps[c] = df_ps[c].apply(_safe_int)

party_weights = {}   # {district: np.array(4)}
for dist in DISTRICTS:
    sub = df_ps[df_ps[0] == dist]
    dpp = int(sub[_COL_DPP].sum())
    kmt = int(sub[_COL_KMT].sum())
    tpp = int(sub[_COL_TPP].sum())
    tot = int(sum(sub[c].sum() for c in _ALL_COLS))
    oth = max(tot - dpp - kmt - tpp, 0)
    w   = np.array([dpp, kmt, tpp, oth], dtype=float)
    if w.sum() > 0:
        party_weights[dist] = w / w.sum()

# Fallback：全市總計（row 5）
_tr  = df_party.iloc[5]
_dpp = _safe_int(_tr[_COL_DPP])
_kmt = _safe_int(_tr[_COL_KMT])
_tpp = _safe_int(_tr[_COL_TPP])
_tot = sum(_safe_int(_tr[c]) for c in _ALL_COLS)
_oth = max(_tot - _dpp - _kmt - _tpp, 0)
_w   = np.array([_dpp, _kmt, _tpp, _oth], dtype=float)
_city_party_w = _w / _w.sum() if _w.sum() > 0 else np.ones(4) / 4

for d in DISTRICTS:
    if d not in party_weights:
        party_weights[d] = _city_party_w

# ── 8. 國家認同 & 厭惡政黨（Political.xlsx）──────────────────────────────────
pol = pd.read_excel(BASE + "Political.xlsx", sheet_name="原始回答資料")

COUNTY_CODE = {
    1:'新北市', 2:'臺北市', 3:'桃園市', 4:'臺中市', 5:'臺南市', 6:'高雄市',
    7:'宜蘭縣', 8:'新竹縣', 9:'苗栗縣', 10:'彰化縣', 11:'南投縣', 12:'雲林縣',
    13:'嘉義縣', 14:'屏東縣', 15:'臺東縣', 16:'花蓮縣', 17:'澎湖縣', 18:'基隆市',
    19:'新竹市', 20:'嘉義市', 21:'金門縣', 22:'連江縣',
}
REGION_GROUP = {
    '北部': ['新北市','臺北市','桃園市','基隆市','新竹市','新竹縣','宜蘭縣'],
    '中部': ['臺中市','苗栗縣','彰化縣','南投縣','雲林縣'],
    '南部': ['臺南市','高雄市','嘉義市','嘉義縣','屏東縣','澎湖縣'],
    '東部': ['臺東縣','花蓮縣'],
    '離島': ['金門縣','連江縣'],
}
COUNTY_TO_RG = {c: g for g, cs in REGION_GROUP.items() for c in cs}

PARTY_Q12 = {1:'民進黨',2:'國民黨',3:'台灣民眾黨',90:'不偏任何黨',94:'其他政黨',96:'不知道',98:'拒答'}
PARTY_Q13 = {1:'民進黨',2:'國民黨',3:'台灣民眾黨',94:'其他政黨',95:'都很討厭',96:'不知道/沒意見',98:'拒答'}
EDU_SURVEY = {1:'國小以下',2:'國中',3:'高中(職)',4:'專科',5:'大學',6:'碩士以上'}

def _trust(row):
    vals = [5 - row[q] for q in ['vQ2','vQ3','vQ4','vQ5'] if 1 <= row[q] <= 4]
    if not vals: return np.nan
    return round((np.mean(vals) - 1) / 3 * 10, 4)

def _survey_age_grp(v):
    if v == 1:        return '15–24歲'
    if v in (2, 3):   return '25–34歲'
    if v in (4, 5):   return '35–44歲'
    if v in (6, 7):   return '45–54歲'
    if v in (8, 9):   return '55–64歲'
    if v in (10, 11): return '65歲以上'
    return None

pol['trust']        = pol.apply(_trust, axis=1)
pol['age_grp']      = pol['vQ14'].apply(_survey_age_grp)
pol['edu_cat']      = pol['vQ15'].map(EDU_SURVEY)
pol['gender']       = pol['vQ16'].map({1:'男', 2:'女'})
pol['county']       = pol['vQ1'].map(COUNTY_CODE)
pol['rg']           = pol['county'].map(COUNTY_TO_RG)
pol['party_pref']   = pol['vQ12'].map(PARTY_Q12)
pol['party_dislike'] = pol['vQ13'].map(PARTY_Q13)

MIN_POOL     = 10
MAIN_PARTIES = {'民進黨','國民黨','台灣民眾黨'}

def _pool(age_grp, edu, gender_val):
    # All personas are 臺北市 → try 縣市 first, then 北部, then age only
    p = pol
    for mask in [
        (p['county'] == '臺北市') & (p['age_grp'] == age_grp) & (p['edu_cat'] == edu) & (p['gender'] == gender_val),
        (p['county'] == '臺北市') & (p['age_grp'] == age_grp) & (p['gender'] == gender_val),
        (p['county'] == '臺北市') & (p['age_grp'] == age_grp),
        (p['rg'] == '北部') & (p['age_grp'] == age_grp) & (p['edu_cat'] == edu) & (p['gender'] == gender_val),
        (p['rg'] == '北部') & (p['age_grp'] == age_grp) & (p['gender'] == gender_val),
        (p['rg'] == '北部') & (p['age_grp'] == age_grp),
        (p['age_grp'] == age_grp) & (p['gender'] == gender_val),
        (p['age_grp'] == age_grp),
    ]:
        sub = p[mask]
        if len(sub) >= MIN_POOL:
            return sub
    return p

def _sample_trust_by_party(party_pref, hi_cap=10.0):
    """Issue 1：依政黨傾向生成國家認同（截斷常態 / 均勻分布）
    hi_cap：Issue 3 由媒體習慣決定的 trust 上限"""
    if party_pref == '民進黨':
        mu, sigma, lo, hi = 7.2, 1.4, 3.0, min(10.0, hi_cap)
    elif party_pref == '國民黨':
        mu, sigma, lo, hi = 5.0, 2.0, 0.0, min(8.5, hi_cap)
    elif party_pref == '台灣民眾黨':
        mu, sigma, lo, hi = 6.0, 2.0, 1.0, min(10.0, hi_cap)
    else:                           # 其他政黨：均勻分布
        return round(float(rng.uniform(2.0, min(9.0, hi_cap))), 1)
    while True:                     # rejection sampling（截斷常態）
        v = rng.normal(mu, sigma)
        if lo <= v <= hi:
            return round(float(np.clip(v, 0, 10)), 1)

def sample_political(age_grp, edu, gender_val, party_pref, hi_cap=10.0):
    pool = _pool(age_grp, edu, gender_val)

    # 國家認同（Issue 1：依政黨傾向條件生成；Issue 3：hi_cap 限制上界）
    trust = _sample_trust_by_party(party_pref, hi_cap)

    # 厭惡政黨（Q13）：排除偏好黨
    dv = pool['party_dislike'].dropna()
    if party_pref in MAIN_PARTIES:
        filtered = dv[dv != party_pref]
        if len(filtered) > 0:
            dv = filtered
    dislike = str(rng.choice(dv.values)) if len(dv) else '不知道/沒意見'

    return trust, dislike

# ── 9. 抽樣 3000 筆 ─────────────────────────────────────────────────────────
n_total   = 3000
n_dist    = len(DISTRICTS)
guaranteed = 1
extra      = n_total - n_dist                           # 2988
extra_cnts = np.round(dist_weights * extra).astype(int)
diff       = extra - extra_cnts.sum()
extra_cnts[np.argmax(extra_cnts)] += diff
dist_counts = {d: guaranteed + extra_cnts[i] for i, d in enumerate(DISTRICTS)}

dist_seq = [d for d, cnt in dist_counts.items() for _ in range(cnt)]
rng.shuffle(dist_seq)

# 性別：各區精確配額，避免 RNG 序列造成系統性偏差
gender_by_dist = {}
for dist in DISTRICTS:
    n_d    = dist_counts[dist]
    n_male = int(np.round(gender_prob[dist][0] * n_d))
    g_list = ['男'] * n_male + ['女'] * (n_d - n_male)
    rng.shuffle(g_list)
    gender_by_dist[dist] = iter(g_list)

records = []
for pid in range(1, n_total + 1):
    dist = dist_seq[pid - 1]

    # 性別（精確配額）
    gender = next(gender_by_dist[dist])

    # 年齡
    age     = sample_age(dist)
    age_grp = age_to_group(age)

    # 教育程度（依年齡排除不可能的學歷）
    edu_w = edu_by_dist.get(dist, taipei_edu).copy()
    for _i, _cat in enumerate(EDU_CATS):
        if age < EDU_MIN_AGE.get(_cat, 0):
            edu_w[_i] = 0.0
    # QA issue 5：年輕族群「國小以下」機率壓低（九年國教普及）
    _pi = EDU_CATS.index('國小以下')
    for _age_lt, _mult in EDU_PRIMARY_AGE_MULT:
        if age < _age_lt:
            edu_w[_pi] *= _mult
            break
    _s = edu_w.sum()
    edu_w = edu_w / _s if _s > 0 else edu_w
    edu   = rng.choice(EDU_CATS, p=edu_w)

    # 職業（考慮年齡與教育程度）
    occ = sample_occ(age, edu)

    # Issue 4：家管性別修正（男性家管機率控制在 10%）
    if occ == '家管' and gender == '男' and rng.random() < 0.90:
        for _ in range(10):
            new_occ = sample_occ(age, edu)
            if new_occ != '家管':
                occ = new_occ
                break

    # 婚姻狀況（Issue 4：家管走條件機率；其他走年齡基礎機率）
    if occ == '家管':
        marital = rng.choice(['已婚','未婚'], p=[0.88, 0.12])
    else:
        pm_val  = p_married(age, dist)
        marital = rng.choice(['已婚','未婚'], p=[pm_val, 1 - pm_val])

    # 媒體習慣（Issue 2：65+ 禁用特定平台；先於 trust 抽樣，供 Issue 3 設上限）
    mprobs = media_prob[age_grp].copy()
    if age >= 65:
        for _mi, _pl in enumerate(PLATFORMS):
            if _pl in BANNED_65PLUS:
                mprobs[_mi] = 0.0
    used = [PLATFORMS[i] for i, pp in enumerate(mprobs) if rng.random() < pp]
    # QA issue 3：強制保底 LINE（台灣滲透率近全民 >90%，方法論明訂「至少保留 LINE」）
    if 'LINE' not in used:
        used = ['LINE'] + used
    media_str = '、'.join(used)

    # 政黨傾向（選舉得票比例）
    party_pref = rng.choice(PARTY_CATS, p=party_weights[dist])

    # Issue 3：媒體含 WeChat/小紅書 時正向設定 trust 上限
    _hi_cap = 10.0
    if 'WeChat' in used and '小紅書' in used:
        _hi_cap = 5.5
    elif 'WeChat' in used:
        _hi_cap = 6.0   # 確保 WeChat 用戶平均 trust ≤ 4.5
    elif '小紅書' in used:
        _hi_cap = 7.0

    # 國家認同 & 厭惡政黨
    trust, dislike = sample_political(age_grp, edu, gender, party_pref, _hi_cap)

    records.append({
        'id': pid,
        '居住地': dist,
        '性別': gender,
        '年齡': age,
        '年齡組': age_grp,
        '教育程度': edu,
        '職業': occ,
        '婚姻狀況': marital,
        '媒體習慣': media_str,
        '國家認同': trust,
        '政黨傾向': party_pref,
        '厭惡政黨': dislike,
    })

df_out = pd.DataFrame(records)

# ── 10. 驗證輸出 ──────────────────────────────────────────────────────────────
print('\n=== 居住地（各區） ===')
real_share = {d: pop_data[d][0] / total_tp_pop for d in DISTRICTS}
vc_dist = df_out['居住地'].value_counts(normalize=True)
for d in DISTRICTS:
    got  = vc_dist.get(d, 0)
    real = real_share[d]
    print(f'  {d}: 真實={real:.1%}  生成={got:.1%}  差={abs(got-real):.1%}')

print('\n=== 性別 ===')
vc_gen = df_out['性別'].value_counts(normalize=True)
total_m = sum(pop_data[d][1] for d in DISTRICTS)
total_f = sum(pop_data[d][2] for d in DISTRICTS)
real_m  = total_m / (total_m + total_f)
print(f'  男: 真實={real_m:.1%}  生成={vc_gen.get("男",0):.1%}')
print(f'  女: 真實={1-real_m:.1%}  生成={vc_gen.get("女",0):.1%}')

print('\n=== 年齡組 ===')
# Taipei 15+ age group reference (from data)
tp_age_ref = {
    '15–24歲': 0.095, '25–34歲': 0.130, '35–44歲': 0.168,
    '45–54歲': 0.176, '55–64歲': 0.170, '65歲以上': 0.263,
}
vc_age = df_out['年齡組'].value_counts(normalize=True)
for g in GROUP_LABELS:
    got  = vc_age.get(g, 0)
    real = tp_age_ref.get(g, 0)
    print(f'  {g}: 真實={real:.1%}  生成={got:.1%}  差={abs(got-real):.1%}')

print('\n=== 教育程度 ===')
tp_edu_ref = {
    '碩士以上': 0.153, '大學': 0.382, '專科': 0.122,
    '高中(職)': 0.220, '國中': 0.062, '國小以下': 0.061,
}
vc_edu = df_out['教育程度'].value_counts(normalize=True)
for e in EDU_CATS:
    got  = vc_edu.get(e, 0)
    real = tp_edu_ref.get(e, 0)
    print(f'  {e}: 真實={real:.1%}  生成={got:.1%}  差={abs(got-real):.1%}')

print('\n=== 職業 ===')
print(df_out['職業'].value_counts(normalize=True).round(3).to_string())

print('\n=== 婚姻狀況 by 年齡組（已婚率）===')
for g in GROUP_LABELS:
    sub = df_out[df_out['年齡組'] == g]['婚姻狀況']
    if len(sub):
        print(f'  {g}: {(sub=="已婚").mean():.1%}')

print('\n=== 政黨傾向 ===')
tp_party_ref = dict(zip(PARTY_CATS, _city_party_w.tolist()))
vc_p = df_out['政黨傾向'].value_counts(normalize=True)
for cat in PARTY_CATS:
    got  = vc_p.get(cat, 0)
    real = tp_party_ref.get(cat, 0)
    print(f'  {cat}: 真實={real:.1%}  生成={got:.1%}  差={abs(got-real):.1%}')

print('\n=== 厭惡政黨 ===')
print(df_out['厭惡政黨'].value_counts(normalize=True).round(3).to_string())

print('\n=== 國家認同 by 年齡組 ===')
trust_ref = {
    '15–24歲': 4.15, '25–34歲': 3.49, '35–44歲': 4.23,
    '45–54歲': 4.51, '55–64歲': 3.87, '65歲以上': 5.27,
}
for g in GROUP_LABELS:
    sub = df_out[df_out['年齡組'] == g]['國家認同']
    if len(sub):
        ref = trust_ref.get(g, '-')
        print(f'  {g}: 生成平均={sub.mean():.2f}  (民調參考={ref})')

# ── 11. 儲存 Excel ─────────────────────────────────────────────────────────
out_path = BASE + "taipei_personas_3000_v2.xlsx"
with pd.ExcelWriter(out_path, engine='openpyxl') as writer:

    # Sheet 1: Personas
    df_out.to_excel(writer, sheet_name='Personas', index=False)

    # Sheet 2: 政黨傾向驗證（全市 + 各區）
    party_rows = []
    vc_full = df_out['政黨傾向'].value_counts()
    total_full = vc_full.sum()
    for cat in PARTY_CATS:
        party_rows.append({
            '行政區': '全市', '政黨': cat,
            '抽樣人數': int(vc_full.get(cat, 0)),
            '抽樣佔比': round(vc_full.get(cat, 0) / total_full, 4),
            '選舉得票率': round(tp_party_ref.get(cat, 0), 4),
            '差距': round(vc_full.get(cat, 0) / total_full - tp_party_ref.get(cat, 0), 4),
        })
    for dist in DISTRICTS:
        sub_d   = df_out[df_out['居住地'] == dist]['政黨傾向'].value_counts()
        sub_tot = sub_d.sum()
        ref_w   = dict(zip(PARTY_CATS, party_weights[dist]))
        for cat in PARTY_CATS:
            party_rows.append({
                '行政區': dist, '政黨': cat,
                '抽樣人數': int(sub_d.get(cat, 0)),
                '抽樣佔比': round(sub_d.get(cat, 0) / sub_tot, 4) if sub_tot > 0 else 0,
                '選舉得票率': round(ref_w.get(cat, 0), 4),
                '差距': round(sub_d.get(cat, 0) / sub_tot - ref_w.get(cat, 0), 4) if sub_tot > 0 else 0,
            })
    pd.DataFrame(party_rows).to_excel(writer, sheet_name='政黨傾向', index=False)

    # Sheet 3: 厭惡政黨驗證
    pol_dis_ref = pol['party_dislike'].value_counts(normalize=True)
    vc_dis = df_out['厭惡政黨'].value_counts()
    dis_total = vc_dis.sum()
    dis_rows = []
    for cat in vc_dis.index:
        dis_rows.append({
            '政黨': cat,
            '抽樣人數': int(vc_dis[cat]),
            '抽樣佔比': round(vc_dis[cat] / dis_total, 4),
            '民調佔比': round(float(pol_dis_ref.get(cat, 0)), 4),
            '差距': round(vc_dis[cat] / dis_total - float(pol_dis_ref.get(cat, 0)), 4),
        })
    pd.DataFrame(dis_rows).to_excel(writer, sheet_name='厭惡政黨', index=False)

    # Sheet 4: 國家認同 by 年齡組
    trust_rows = []
    for g in GROUP_LABELS:
        sub = df_out[df_out['年齡組'] == g]['國家認同']
        if len(sub):
            trust_rows.append({
                '年齡組': g, '人數': len(sub),
                '平均值': round(sub.mean(), 2),
                '中位數': round(sub.median(), 2),
                '標準差': round(sub.std(), 2),
                '民調參考': trust_ref.get(g, None),
            })
    pd.DataFrame(trust_rows).to_excel(writer, sheet_name='國家認同', index=False)

    # Sheet 5: 教育程度驗證
    edu_rows = []
    vc_edu2 = df_out['教育程度'].value_counts()
    edu_total = vc_edu2.sum()
    for dist in ['全市'] + DISTRICTS:
        if dist == '全市':
            sub_edu = df_out['教育程度'].value_counts()
            ref_w   = dict(zip(EDU_CATS, taipei_edu))
        else:
            sub_edu = df_out[df_out['居住地'] == dist]['教育程度'].value_counts()
            ref_w   = dict(zip(EDU_CATS, edu_by_dist.get(dist, taipei_edu)))
        st = sub_edu.sum()
        for cat in EDU_CATS:
            edu_rows.append({
                '行政區': dist, '教育程度': cat,
                '抽樣人數': int(sub_edu.get(cat, 0)),
                '抽樣佔比': round(sub_edu.get(cat, 0) / st, 4) if st > 0 else 0,
                '真實佔比': round(ref_w.get(cat, 0), 4),
                '差距': round(sub_edu.get(cat, 0) / st - ref_w.get(cat, 0), 4) if st > 0 else 0,
            })
    pd.DataFrame(edu_rows).to_excel(writer, sheet_name='教育程度', index=False)

    # Sheet 6: 抽樣分配結果（總彙整）
    sample_rows = []

    def _add_dim(dim, series, real_map=None):
        vc = series.value_counts().sort_index()
        tot = vc.sum()
        for cat, cnt in vc.items():
            sample_rows.append({
                '維度': dim, '類別': cat,
                '抽樣人數': int(cnt),
                '抽樣佔比': round(cnt / tot, 6),
                '真實佔比': round(real_map[cat], 6) if real_map and cat in real_map else None,
                '差距': round(cnt / tot - real_map[cat], 6) if real_map and cat in real_map else None,
            })

    _add_dim('居住地', df_out['居住地'], real_share)
    _add_dim('性別', df_out['性別'], {'男': real_m, '女': 1 - real_m})
    _add_dim('年齡組', df_out['年齡組'], tp_age_ref)
    _add_dim('教育程度', df_out['教育程度'], tp_edu_ref)
    _add_dim('職業', df_out['職業'])
    _add_dim('婚姻狀況', df_out['婚姻狀況'])
    _add_dim('政黨傾向', df_out['政黨傾向'], tp_party_ref)
    _add_dim('厭惡政黨', df_out['厭惡政黨'])

    for g in GROUP_LABELS:
        sub = df_out[df_out['年齡組'] == g]['婚姻狀況']
        if len(sub):
            sample_rows.append({
                '維度': f'已婚率｜{g}', '類別': '已婚',
                '抽樣人數': int((sub == '已婚').sum()),
                '抽樣佔比': round(float((sub == '已婚').mean()), 6),
                '真實佔比': None, '差距': None,
            })

    all_plats = [p for cell in df_out['媒體習慣'] for p in str(cell).split('、')]
    plat_vc   = pd.Series(all_plats).value_counts()
    n_p = len(df_out)
    for plat, cnt in plat_vc.items():
        sample_rows.append({
            '維度': '媒體習慣(使用人數佔比)', '類別': plat,
            '抽樣人數': int(cnt),
            '抽樣佔比': round(cnt / n_p, 6),
            '真實佔比': None, '差距': None,
        })

    for g in GROUP_LABELS:
        sub = df_out[df_out['年齡組'] == g]['國家認同']
        if len(sub):
            sample_rows.append({
                '維度': f'國家認同｜{g}', '類別': '平均值',
                '抽樣人數': len(sub),
                '抽樣佔比': round(float(sub.mean()), 4),
                '真實佔比': trust_ref.get(g), '差距': None,
            })

    pd.DataFrame(sample_rows, columns=['維度','類別','抽樣人數','抽樣佔比','真實佔比','差距']).to_excel(
        writer, sheet_name='抽樣分配結果', index=False)

print(f'\n✓ 已儲存 {out_path}  ({len(df_out)} rows, 6 sheets)')
