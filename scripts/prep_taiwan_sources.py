#!/usr/bin/env python3
"""
prep_taiwan_sources.py — 把 data/raw/taiwan/ 的異質原始檔，清洗成 region-keyed CSV，
                         落在 data/derived/regions/ 供全台 pipeline 各 stage 的 loader 讀取。

設計原則：
  - 一個 build_* 函式對應一個輸出 CSV，彼此獨立、可單獨重跑。
  - 縣市名一律正規化為「無空格、用『臺』」的標準形（來源檔常含全形空格，如『臺 北 市』）。
  - 只做「資料對齊」，不做任何抽樣/建模（那是 stage 腳本的事）。

輸出（data/derived/regions/）：
  regions.csv         22 縣市 + 人口佔比（3000 配額權重）；臺北市標記 reuse
  census_gender.csv   縣市 × 男/女比例
  census_age.csv      縣市 × 年齡組 人數
  census_edu.csv      縣市 × 教育程度 人數
  census_occupation.csv 縣市 × 職業 人數（千人）
  marriage_age.csv    全國 年齡 × 婚姻（含同婚類型）
  media_region.csv    6 區域 × 年齡 × 平台 使用率
  housing.csv         縣市 × 自有/租用/配住/其他 戶數
  election_party.csv  縣市 × 政黨 不分區立委得票（2020 第10屆）
  election_pres.csv   縣市 × 候選人 總統得票（2020 第15任）
  ethnic_base.csv     縣市 × 閩南/客家/外省/原住民 比例（依 method/taiwan_ethnicity_methodology.md §4）
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_TAIWAN = REPO_ROOT / "data" / "raw" / "taiwan"
OUT_DIR = REPO_ROOT / "data" / "derived" / "regions"

POP_FILE = RAW_TAIWAN / "taiwan_persona人口分布.xlsx"
AGE_FILE = RAW_TAIWAN / "taiwan_age" / "縣市人口按單齡-109年12月.xls"

# 6 個 persona 年齡組（與 pipeline_common.AGE_GROUP_LABELS 一致，注意 EN DASH）。
AGE_GROUP_LABELS = ['15–24歲', '25–34歲', '35–44歲', '45–54歲', '55–64歲', '65歲以上']

# 非縣市的彙總列（解析時跳過）。
AGG_LABELS = {'總計', '臺灣省', '福建省', '臺灣地區', '中華民國'}

# 22 縣市標準名（順序 = 工作表2；亦為 3000 配額計算順序）。
COUNTY_ORDER = [
    '新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市',
    '宜蘭縣', '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣',
    '嘉義縣', '屏東縣', '臺東縣', '花蓮縣', '澎湖縣', '基隆市',
    '新竹市', '嘉義市', '金門縣', '連江縣',
]

# 重用既有 Taipei 3000 的縣市（不重新生成，finalize 抽樣併入）。
REUSE_COUNTIES = {'臺北市'}


def norm_county(name) -> str:
    """縣市名正規化：去掉所有空白（含全形）、『台』→『臺』。"""
    if name is None:
        return ''
    s = str(name).replace(' ', '').replace('　', '').strip()
    s = s.replace('台', '臺')
    return s


def _out(df: pd.DataFrame, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f"  ✓ {name}  ({len(df)} rows)")


# ── regions.csv ──────────────────────────────────────────────────────────────
def build_regions() -> pd.DataFrame:
    """工作表2 → 22 縣市人口、佔比、男女比例；臺北市標記 reuse。"""
    df = pd.read_excel(POP_FILE, sheet_name='工作表2', header=None)
    rows = []
    for i in range(2, 24):  # 22 縣市
        name = norm_county(df.iloc[i, 0])
        if name not in COUNTY_ORDER:
            continue
        rows.append({
            'region_name': name,
            'pop_total': int(df.iloc[i, 1]),
            'pop_share': float(df.iloc[i, 2]),
            'male_ratio': float(df.iloc[i, 3]),
            'female_ratio': float(df.iloc[i, 4]),
            'reuse': name in REUSE_COUNTIES,
        })
    out = pd.DataFrame(rows)
    # 依標準順序、補 region_code
    out['region_name'] = pd.Categorical(out['region_name'], COUNTY_ORDER, ordered=True)
    out = out.sort_values('region_name').reset_index(drop=True)
    out['region_name'] = out['region_name'].astype(str)
    out.insert(0, 'region_code', range(1, len(out) + 1))
    assert len(out) == 22, f"應有 22 縣市，實得 {len(out)}"
    assert abs(out['pop_share'].sum() - 1.0) < 1e-6, "人口佔比加總應 ≈ 1"
    _out(out, 'regions.csv')
    return out


# ── census_age.csv ───────────────────────────────────────────────────────────
# 單齡檔的 5 歲帶『合計』欄位置（col index）；step 6，0~4 起至 95~99。
_BAND_COLS = {age0: 3 + 6 * i for i, age0 in enumerate(range(0, 100, 5))}  # {0:3,5:9,...,95:117}


def build_census_age() -> pd.DataFrame:
    """縣市人口按單齡 → 縣市 × 6 年齡組 人數（15+）。

    群組：15–24=(15-19)+(20-24)…55–64=(55-59)+(60-64)；65+=總計−(0–64)。
    """
    df = pd.read_excel(AGE_FILE, sheet_name='04-單一年齡', header=None)
    def band(row, age0):  # 該 5 歲帶合計
        return float(row[_BAND_COLS[age0]])
    rows = []
    for i in range(df.shape[0]):
        if str(df.iloc[i, 1]).replace(' ', '').strip() != '計':
            continue  # 只取每個縣市區塊的『計』列
        name = norm_county(df.iloc[i + 1, 0]) if i + 1 < df.shape[0] else ''
        if name in AGG_LABELS or name not in COUNTY_ORDER:
            continue
        row = df.iloc[i]
        total = float(row[2])
        g = {
            '15–24歲': band(row, 15) + band(row, 20),
            '25–34歲': band(row, 25) + band(row, 30),
            '35–44歲': band(row, 35) + band(row, 40),
            '45–54歲': band(row, 45) + band(row, 50),
            '55–64歲': band(row, 55) + band(row, 60),
        }
        below65 = sum(band(row, a) for a in range(0, 65, 5))
        g['65歲以上'] = total - below65
        rows.append({'region_name': name, **{k: int(round(v)) for k, v in g.items()}})
    out = pd.DataFrame(rows)
    out['region_name'] = pd.Categorical(out['region_name'], COUNTY_ORDER, ordered=True)
    out = out.sort_values('region_name').reset_index(drop=True)
    out['region_name'] = out['region_name'].astype(str)
    assert len(out) == 22, f"census_age 應 22 縣市，實得 {len(out)}"
    _out(out, 'census_age.csv')
    return out


# ── census_edu.csv ───────────────────────────────────────────────────────────
# 6 個 persona 教育程度（與 pipeline 一致）。
EDU_LEVELS = ['研究所以上', '大學', '專科', '高中職', '國中', '國小及以下']


def _edu_level_of(group_label: str):
    """把來源教育群組標頭歸入 persona 6 級；非教育欄回 None。"""
    g = str(group_label).replace(' ', '').replace('　', '')
    if '研究所' in g:
        return '研究所以上'
    if '大學' in g:
        return '大學'
    if '專科' in g:
        return '專科'
    if '高級中等' in g or '高中' in g:
        return '高中職'
    if '國中' in g or '初職' in g:
        return '國中'
    if '國小' in g or '自修' in g or '不識字' in g:
        return '國小及以下'
    return None


def build_census_edu() -> pd.DataFrame:
    """地區X教育程度 → 縣市 × 6 教育程度 人數（取各縣市『計』列、加總葉欄）。"""
    df = pd.read_excel(POP_FILE, sheet_name='地區X教育程度', header=None)
    grp = df.iloc[4].ffill()   # 群組標頭（研究所/大學/…）
    leaf = df.iloc[7]          # 畢業/肄業/五專前三年肄
    # 每個資料欄 → persona 教育級（僅葉欄：畢業/肄業/五專…）
    col_level = {}
    for c in range(2, df.shape[1]):
        lf = str(leaf[c]).replace(' ', '')
        if lf in ('畢業', '肄業') or '五專前三年' in lf:
            lv = _edu_level_of(grp[c])
            if lv:
                col_level[c] = lv
    rows = []
    for i in range(df.shape[0]):
        if str(df.iloc[i, 1]).replace(' ', '').strip() != '計':
            continue
        name = norm_county(df.iloc[i + 1, 0]) if i + 1 < df.shape[0] else ''  # 標籤在『男』列
        if name in AGG_LABELS or name not in COUNTY_ORDER:
            continue
        agg = dict.fromkeys(EDU_LEVELS, 0.0)
        for c, lv in col_level.items():
            v = df.iloc[i, c]
            if pd.notna(v):
                agg[lv] += float(v)
        rows.append({'region_name': name, **{k: int(round(agg[k])) for k in EDU_LEVELS}})
    out = pd.DataFrame(rows)
    out['region_name'] = pd.Categorical(out['region_name'], COUNTY_ORDER, ordered=True)
    out = out.sort_values('region_name').reset_index(drop=True)
    out['region_name'] = out['region_name'].astype(str)
    assert len(out) == 22, f"census_edu 應 22 縣市，實得 {len(out)}"
    _out(out, 'census_edu.csv')
    return out


# ── census_occupation.csv ────────────────────────────────────────────────────
# 7 職業類別（與 pipeline_common.OCC_CATS 一致）→ 來源『合計』欄 index。
_OCC_COLS = {
    '管理/主管': 5, '專業人員': 8, '技術/助理專業': 11, '事務人員': 15,
    '服務/銷售': 18, '農林漁牧': 21, '技術工/勞工': 24,
}
OCC_CATS = list(_OCC_COLS)


def build_census_occupation() -> pd.DataFrame:
    """地區X職業 → 縣市 × 7 職業（千人）。臺北市可能用全國結構代理（見備註）。"""
    df = pd.read_excel(POP_FILE, sheet_name='地區X職業', header=None)
    rows = []
    for i in range(6, df.shape[0]):
        name = norm_county(df.iloc[i, 1])
        if name in {'臺灣地區'} | AGG_LABELS or name not in COUNTY_ORDER:
            continue
        rec = {'region_name': name}
        for occ, c in _OCC_COLS.items():
            v = df.iloc[i, c]
            rec[occ] = float(v) if pd.notna(v) else 0.0
        rows.append(rec)
    out = pd.DataFrame(rows)
    # 金門/連江職業可能缺 → 用全國（臺灣地區）結構比例回填
    missing = [c for c in COUNTY_ORDER if c not in set(out['region_name'])]
    if missing:
        nat = df.iloc[[i for i in range(df.shape[0])
                       if norm_county(df.iloc[i, 1]) == '臺灣地區'][0]]
        natrec = {occ: float(nat[c]) for occ, c in _OCC_COLS.items()}
        s = sum(natrec.values())
        for m in missing:
            rows.append({'region_name': m, **{occ: natrec[occ] / s for occ in OCC_CATS}})
        out = pd.DataFrame(rows)
        print(f"    ⚠️ 職業缺 {missing} → 用全國結構比例回填")
    out['region_name'] = pd.Categorical(out['region_name'], COUNTY_ORDER, ordered=True)
    out = out.sort_values('region_name').reset_index(drop=True)
    out['region_name'] = out['region_name'].astype(str)
    _out(out, 'census_occupation.csv')
    return out


# ── marriage_age.csv（全國 年齡 → 有偶率）──────────────────────────────────────
# 年齡x婚姻 age-band 欄（col3 起）→ persona 6 組的來源欄 index。
_MAR_GROUP_COLS = {
    '15–24歲': [3, 4], '25–34歲': [5, 6], '35–44歲': [7, 8],
    '45–54歲': [9, 10], '55–64歲': [11, 12], '65歲以上': list(range(13, 21)),
}


def build_marriage_age() -> pd.DataFrame:
    """年齡x婚姻 → 全國 年齡組 → 有偶率（有偶計 / 總計計）。"""
    df = pd.read_excel(POP_FILE, sheet_name='年齡x婚姻', header=None)
    def label_row(label):  # 該婚姻狀況『計』列（標籤在下一列＝男）
        for i in range(df.shape[0]):
            if norm_county(df.iloc[i + 1, 0]) == label and str(df.iloc[i, 1]).strip() == '計':
                return df.iloc[i]
        raise ValueError(label)
    total = label_row('總計')
    married = label_row('有偶')
    rows = []
    for grp, cols in _MAR_GROUP_COLS.items():
        num = sum(float(married[c]) for c in cols)
        den = sum(float(total[c]) for c in cols)
        rows.append({'age_group': grp, 'married_rate': round(num / den, 4)})
    out = pd.DataFrame(rows)
    _out(out, 'marriage_age.csv')
    return out


# ── media_age.csv（全國 年齡 → 各平台使用率）──────────────────────────────────
_MEDIA_AGE_SRC = {  # persona 年齡組 ← 媒體表年齡列標籤
    '15–24歲': '16-25歲', '25–34歲': '26-35歲', '35–44歲': '36-45歲',
    '45–54歲': '46-55歲', '55–64歲': '56-65歲', '65歲以上': '66歲及以上',
}


def build_media_age() -> pd.DataFrame:
    """年齡x媒體 → persona 年齡組 × 各平台使用率（年齡邊際；區域邊際另存備用）。"""
    df = pd.read_excel(POP_FILE, sheet_name='年齡x媒體', header=None)
    platforms = [str(x).strip() for x in df.iloc[1, 5:].tolist() if str(x).strip() != 'nan']
    plat_cols = {p: 5 + j for j, p in enumerate(platforms)
                 if p not in ('現在都沒有在使用了', '不知道')}
    # 媒體表年齡列：col2==label
    label_to_row = {str(df.iloc[i, 2]).strip(): i for i in range(df.shape[0])}
    rows = []
    for grp, src in _MEDIA_AGE_SRC.items():
        i = label_to_row[src]
        rec = {'age_group': grp}
        for p, c in plat_cols.items():
            rec[p] = round(float(df.iloc[i, c]), 4)
        rows.append(rec)
    out = pd.DataFrame(rows)
    _out(out, 'media_age.csv')
    return out


# ── housing.csv（109 普查 t083 → 縣市 × 4 房產狀態 比例）────────────────────────
HOUSING_FILE = RAW_TAIWAN / "taiwan_property" / "t083.xlsx"
HOUSING_CLASSES = ['自有本人', '自有家人名義', '租屋', '借住配住']


def build_housing() -> pd.DataFrame:
    """t083 P01 → 縣市 × {自有本人,自有家人名義,租屋,借住配住} 比例。

    來源欄：col3 自有, col4 親屬名下, col6 租用, col7 配住, col8 其他(含借住)。
    """
    h = pd.read_excel(HOUSING_FILE, sheet_name='P01', header=None)
    rows = []
    for i in range(h.shape[0]):
        name = norm_county(h.iloc[i, 1])
        if name not in COUNTY_ORDER or name in AGG_LABELS:
            continue
        total = float(h.iloc[i, 2])
        own_self = float(h.iloc[i, 3])
        own_fam = float(h.iloc[i, 4])
        rent = float(h.iloc[i, 6])
        allot = float(h.iloc[i, 7]) if pd.notna(h.iloc[i, 7]) else 0.0
        other = float(h.iloc[i, 8]) if pd.notna(h.iloc[i, 8]) else 0.0
        rows.append({
            'region_name': name,
            '自有本人': own_self / total,
            '自有家人名義': own_fam / total,
            '租屋': rent / total,
            '借住配住': (allot + other) / total,
        })
    out = pd.DataFrame(rows)
    out['region_name'] = pd.Categorical(out['region_name'], COUNTY_ORDER, ordered=True)
    out = out.sort_values('region_name').reset_index(drop=True)
    out['region_name'] = out['region_name'].astype(str)
    for c in HOUSING_CLASSES:
        out[c] = out[c].round(4)
    assert len(out) == 22, f"housing 應 22 縣市，實得 {len(out)}"
    _out(out, 'housing.csv')
    return out


# ── 選舉（2020）→ election_party.csv / election_pres.csv ──────────────────────
import glob
import re

PARTY_DIR = RAW_TAIWAN / "Taiwan不分區立委"
PRES_DIR = RAW_TAIWAN / "總統-各投票所得票明細及概況(Excel檔)"


def _to_int(x) -> int:
    s = str(x).replace(',', '').replace(' ', '').strip()
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _classify(label: str) -> str:
    """政黨/候選人標籤 → DPP/KMT/TPP/Other。"""
    if '民主進步黨' in label or '蔡英文' in label:
        return 'DPP'
    if '中國國民黨' in label or '韓國瑜' in label:
        return 'KMT'
    if '台灣民眾黨' in label or '柯文哲' in label:
        return 'TPP'
    return 'Other'


def _total_row(d: pd.DataFrame) -> int:
    for i in range(min(12, d.shape[0])):
        if str(d.iloc[i, 0]).replace('　', '').replace(' ', '').strip() == '總計':
            return i
    raise ValueError('找不到總計列')


def _election_shares(folder: Path, pattern: str, buckets) -> pd.DataFrame:
    """彙總某選舉資料夾下各縣市檔的『總計』列 → 縣市 × bucket 得票比例。"""
    rows = []
    for f in sorted(glob.glob(str(folder / pattern))):
        d = pd.read_excel(f, sheet_name=0, header=None)
        county = norm_county(pd.ExcelFile(f).sheet_names[0])
        if county not in COUNTY_ORDER:
            continue
        # 候選人/政黨標籤列：含 (n) 標記的那列
        lab_row = next(i for i in range(5)
                       if any(re.match(r'\(\d+\)', str(x).strip()) for x in d.iloc[i]))
        col_bucket = {}
        for c in range(d.shape[1]):
            lab = str(d.iloc[lab_row, c]).replace('\n', '').strip()
            if re.match(r'\(\d+\)', lab):
                col_bucket[c] = _classify(lab)
        tr = _total_row(d)
        agg = dict.fromkeys(buckets, 0)
        for c, b in col_bucket.items():
            agg[b] += _to_int(d.iloc[tr, c])
        tot = sum(agg.values())
        rows.append({'region_name': county, **{b: round(agg[b] / tot, 4) for b in buckets}})
    out = pd.DataFrame(rows)
    out['region_name'] = pd.Categorical(out['region_name'], COUNTY_ORDER, ordered=True)
    out = out.sort_values('region_name').reset_index(drop=True)
    out['region_name'] = out['region_name'].astype(str)
    assert len(out) == 22, f"選舉應 22 縣市，實得 {len(out)}"
    return out


def build_election_party() -> pd.DataFrame:
    """2020 不分區立委（第10屆）→ 縣市 × {DPP,KMT,TPP,Other} 得票比例。"""
    out = _election_shares(PARTY_DIR, '不分區立委-A05-6-*.xls', ['DPP', 'KMT', 'TPP', 'Other'])
    _out(out, 'election_party.csv')
    return out


def build_election_pres() -> pd.DataFrame:
    """2020 總統（第15任）→ 縣市 × {DPP,KMT,Other} 得票比例（2020 無 TPP 總統）。"""
    out = _election_shares(PRES_DIR, '總統-A05-2-*.xls', ['DPP', 'KMT', 'Other'])
    _out(out, 'election_pres.csv')
    return out


# ── ethnic_base.csv（依 method/taiwan_ethnicity_methodology.md §4-6）──────
ETHNIC_CLASSES = ['閩南', '客家', '外省', '原住民']

# §6 客委會 110 年寬定義客家比率（%）。
HAKKA_RAW = {
    '新竹縣': 67.8, '苗栗縣': 62.5, '桃園市': 39.9, '花蓮縣': 34.2, '新竹市': 30.3,
    '屏東縣': 23.1, '臺東縣': 20.6, '臺中市': 17.5, '臺北市': 17.4, '新北市': 16.7,
    '金門縣': 16.5, '連江縣': 16.0, '高雄市': 14.7, '基隆市': 12.5, '南投縣': 12.3,
    '澎湖縣': 9.5, '嘉義市': 9.1, '雲林縣': 8.5, '嘉義縣': 8.3, '彰化縣': 7.8,
    '宜蘭縣': 7.7, '臺南市': 7.1,
}
# §6 眷村／都會係數（外省 = 10% × 係數）。
WAISHENG_COEF = {
    '臺北市': 1.5, '新竹市': 1.6, '桃園市': 1.4, '高雄市': 1.3, '臺中市': 1.3, '屏東縣': 1.3, '基隆市': 1.3,
    '新北市': 1.0, '臺南市': 0.9, '嘉義市': 1.0, '宜蘭縣': 0.9, '花蓮縣': 0.9, '臺東縣': 0.8,
    '雲林縣': 0.5, '嘉義縣': 0.4, '彰化縣': 0.5, '南投縣': 0.5, '苗栗縣': 0.5,
    '澎湖縣': 0.4, '金門縣': 0.4, '連江縣': 0.3, '新竹縣': 0.9,
}
K_HAKKA = 0.55           # §5 客家縮放校準（單一認同目標 10.9%）
WAISHENG_BASE = 0.10
ABO_NATIONAL = 0.027     # §3.2 全國原住民占比，作 selectorate→人口比 校準錨點


def _selectorate(folder: Path, pattern: str) -> dict:
    """各縣市『總計』列的選舉人數 G（倒數第二欄）。"""
    out = {}
    for f in sorted(glob.glob(str(folder / pattern))):
        d = pd.read_excel(f, sheet_name=0, header=None)
        county = norm_county(pd.ExcelFile(f).sheet_names[0])
        if county not in COUNTY_ORDER:
            continue
        tr = _total_row(d)
        out[county] = _to_int(d.iloc[tr, d.shape[1] - 2])
    return out


def build_ethnic_base(regions: pd.DataFrame) -> pd.DataFrame:
    """縣市 × {閩南,客家,外省,原住民} 比例（methodology §4 四步驟）。

    原住民：由 山地+平地立委 選舉人數 / 總統 選舉人數 求成人比，
            再用人口權重校準到全國 2.7%（PDF 無法直讀，改以 selectorate 資料推估）。
    """
    pop = regions.set_index('region_name')['pop_total']
    shan = _selectorate(PARTY_DIR, '山地立委-A05-4-*.xls')
    ping = _selectorate(PARTY_DIR, '平地立委-A05-4-*.xls')
    pres = _selectorate(PRES_DIR, '總統-A05-2-*.xls')
    abo_adult = {c: (shan.get(c, 0) + ping.get(c, 0)) / pres[c] for c in COUNTY_ORDER}
    nat_raw = sum(abo_adult[c] * pop[c] for c in COUNTY_ORDER) / pop.sum()
    factor = ABO_NATIONAL / nat_raw
    rows = []
    for c in COUNTY_ORDER:
        p_abo = abo_adult[c] * factor
        p_hak = HAKKA_RAW.get(c, 0.0) / 100 * K_HAKKA
        p_wai = WAISHENG_BASE * WAISHENG_COEF.get(c, 1.0)
        p_hok = 1 - p_abo - p_hak - p_wai
        if p_hok < 0:                       # §4 Step4 高客家縣壓縮
            scale = (1 - p_abo) / (p_hak + p_wai)
            p_hak, p_wai, p_hok = p_hak * scale, p_wai * scale, 0.0
        rows.append({'region_name': c, '閩南': p_hok, '客家': p_hak,
                     '外省': p_wai, '原住民': p_abo})
    out = pd.DataFrame(rows)
    for col in ETHNIC_CLASSES:
        out[col] = out[col].round(4)
    # 驗證：每列和 ≈ 1
    s = out[ETHNIC_CLASSES].sum(axis=1)
    assert (s - 1).abs().max() < 0.01, "族群比例每列應加總 ≈ 1"
    _out(out, 'ethnic_base.csv')
    return out


def build_all() -> None:
    """重建全部 region-keyed CSV（供 pipeline 前置一鍵跑）。"""
    reg = build_regions()
    build_census_age()
    build_census_edu()
    build_census_occupation()
    build_marriage_age()
    build_media_age()
    build_housing()
    build_election_party()
    build_election_pres()
    build_ethnic_base(reg)
    print("✅ 全部 region CSV 重建完成。")


if __name__ == '__main__':
    print("build_regions:");        reg = build_regions()
    print("build_census_age:");     build_census_age()
    print("build_census_edu:");     e = build_census_edu()
    print("build_census_occupation:"); o = build_census_occupation()
    print("build_marriage_age:");   mar = build_marriage_age()
    print("build_media_age:");      med = build_media_age()
    print("build_housing:");        hh = build_housing()
    print("build_election_party:"); ep = build_election_party()
    print("build_election_pres:");  epr = build_election_pres()
    print("build_ethnic_base:");    eth = build_ethnic_base(reg)
    print("\nethnic_base 抽查（客家梯度 新竹縣>苗栗>桃園>花蓮；原民 臺東/花蓮高）:\n",
          eth.set_index('region_name').loc[
              ['新竹縣', '苗栗縣', '桃園市', '花蓮縣', '臺東縣', '臺北市', '雲林縣']].to_string())
    # 全國回算
    w = reg.set_index('region_name')['pop_total']
    natl = {col: round(sum(eth.set_index('region_name')[col] * w) / w.sum(), 3)
            for col in ETHNIC_CLASSES}
    print("\n全國加權回算（應 閩≈.77 客≈.11 外≈.10 原≈.027）:", natl)
    print("\n不分區立委政黨傾向（抽查 臺北/臺南/新竹縣，藍綠南北差應浮現）:\n",
          ep.set_index('region_name').loc[['臺北市', '臺南市', '新竹縣', '高雄市']].to_string())
    print("\n總統 vs 不分區（臺南 綠營，分裂投票錨點）:\n",
          "立委:", ep.set_index('region_name').loc['臺南市'].to_dict(),
          "\n  總統:", epr.set_index('region_name').loc['臺南市'].to_dict())
    print("\nmarriage_age:\n", mar.to_string())
    print("\nmedia_age (LINE/Instagram/Facebook 抽查):\n",
          med[['age_group', 'LINE', 'Facebook', 'Instagram']].to_string())
    print("\ncensus_edu 教育佔比（抽查 新竹市 vs 雲林縣，高教應有落差）:")
    ev = e.set_index('region_name')[EDU_LEVELS]
    ev = ev.div(ev.sum(axis=1), axis=0)
    print(ev.loc[['新竹市', '雲林縣', '臺北市']].round(3).to_string())
    print("\ncensus_occupation 抽查（臺北 vs 雲林，農林漁牧應差異大）:")
    print(o.set_index('region_name').loc[['臺北市', '雲林縣']].round(1).to_string())
