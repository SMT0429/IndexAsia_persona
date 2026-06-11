"""
pipeline_common.py — Taipei persona pipeline 共用工具與常數

本模組集中三件事，讓 12 支生成腳本一致、CWD 無關、可一鍵重現：
  1. 路徑解析（錨定 repo root，與當前工作目錄無關）
  2. stage 讀寫樣板（read_stage / write_stage，並釘住 v2 多 sheet 檔的 'Personas'）
  3. RNG 工廠與跨腳本共用常數（DISTRICTS、年齡組、收入區間、職業類別、非就業標記…）

重要原則（重構不得改變任何統計輸出）：
  - 共用常數的值與「各腳本原本的在地宣告」逐位元組相同，純粹是去重，不改語意。
  - make_rng() 等同 np.random.default_rng(seed)，只取代「本來就是 default_rng(42)」的寫法，
    RNG 串流位元相同。industry（stdlib random）、topic（np.random.seed 舊式全域）刻意不改引擎，
    因為換引擎會改變抽樣序列。
詳細欄位依賴與規則以 method/field_dependency_map.md（v2.3）為權威來源。
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ── 路徑（CWD 無關，錨定 scripts/ 的上一層 = repo root）────────────────────────
# data/ 重整為三層：raw/（原始輸入）、WIP/（pipeline 中繼）、taipei_final/（交付）。
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"           # 原始輸入：Basic.xlsx、Political.xlsx、taiwan_political_events/…
WIP_DIR = DATA_DIR / "WIP"           # pipeline 12 階段中繼檔（STAGE_FILES）
FINAL_DIR = DATA_DIR / "taipei_final"  # 最終交付檔（taipei_finalize.py 輸出）
TAIPEI_DATA_DIR = RAW_DIR / "census"           # 普查來源（113_*.ods 等）
TAIPEI_DATA_2020_DIR = RAW_DIR / "elections_2020"  # 2020 中選會 .xls


def data_path(name: str) -> Path:
    """data/ 根目錄下檔案的絕對路徑。"""
    return DATA_DIR / name


def raw_path(name: str) -> Path:
    """原始輸入檔的絕對路徑（data/raw/ 下，如 Basic.xlsx、Political.xlsx、taiwan_political_events/）。"""
    return RAW_DIR / name


def stage_path(stage: str) -> Path:
    """某 pipeline 階段中繼檔的絕對路徑（data/WIP/ 下）。"""
    return WIP_DIR / STAGE_FILES[stage]


def taipei_data_path(name: str) -> Path:
    """data/raw/census/ 下檔案的絕對路徑（113_*.ods 等普查來源）。"""
    return TAIPEI_DATA_DIR / name


def taipei_2020_path(name: str) -> Path:
    """data/raw/elections_2020/ 下檔案的絕對路徑（2020 中選會 .xls）。"""
    return TAIPEI_DATA_2020_DIR / name


# ── stage 檔名表與 sheet 契約 ─────────────────────────────────────────────────
# key 對應 field_dependency_map.md §1 的 12 個 pipeline 階段。
STAGE_FILES = {
    "v2":            "taipei_personas_3000_v2.xlsx",
    "politicalEvent": "taipei_personas_3000_politicalEvent.xlsx",
    "industry":      "taipei_personas_3000_industry.xlsx",
    "income":        "taipei_personas_3000_income.xlsx",
    "religion":      "taipei_personas_3000_religion.xlsx",
    "group":         "taipei_personas_3000_group.xlsx",
    "splitTicket":   "taipei_personas_3000_splitTicket.xlsx",
    "value":         "taipei_personas_3000_value.xlsx",
    "topic":         "taipei_personas_3000_topic.xlsx",
    "speakingStyle": "taipei_personas_3000_speakingStyle.xlsx",
    "clan":          "taipei_personas_3000_clan.xlsx",
    "property":      "taipei_personas_3000_property.xlsx",
}

# v2 是唯一的多 sheet 工作簿；persona 資料在這張 sheet。
# v2 的 ExcelWriter 與 read_stage('v2') 共用此常數，避免「靠第一張剛好是它」的脆弱。
PERSONAS_SHEET = "Personas"


def read_stage(stage: str, *, sheet_name=0) -> pd.DataFrame:
    """讀入某 pipeline 階段的 persona 表。

    stage=='v2' 時內部強制讀 PERSONAS_SHEET（v2 是多 sheet 檔，
    其餘階段皆為單 sheet，預設讀第 0 張即可）。
    """
    if stage == "v2" and sheet_name == 0:
        sheet_name = PERSONAS_SHEET
    return pd.read_excel(stage_path(stage), sheet_name=sheet_name)


def write_stage(df: pd.DataFrame, stage: str) -> Path:
    """把 df 寫到該階段的標準輸出檔（data/WIP/ 下，單 sheet, index 不寫）。

    注意：v2 為多 sheet 輸出，請勿用本函式（會吃掉 5 張驗證表），
    v2 仍以自有 ExcelWriter 輸出，只是輸出路徑改用 stage_path('v2')。
    """
    out = stage_path(stage)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out, index=False)
    return out


# ── RNG 工廠 ──────────────────────────────────────────────────────────────────
DEFAULT_SEED = 42


def make_rng(seed: int = DEFAULT_SEED) -> np.random.Generator:
    """標準 RNG 工廠。等同 np.random.default_rng(seed)。"""
    return np.random.default_rng(seed)


# ── 跨腳本共用常數（去重；值與各腳本原本在地宣告逐位元組相同）─────────────────
# 12 行政區（順序具意義：索引對應人口/性別配額權重向量）。
DISTRICTS = ['松山區', '信義區', '大安區', '中山區', '中正區', '大同區',
             '萬華區', '文山區', '南港區', '內湖區', '士林區', '北投區']

# 6 個年齡組標籤（注意分隔符為 U+2013 EN DASH「–」，非 hyphen「-」）。
# 順序對應各腳本機率/乘數向量索引。
AGE_GROUP_LABELS = ['15–24歲', '25–34歲', '35–44歲', '45–54歲', '55–64歲', '65歲以上']

# 6 個月收入區間（順序對應 income/property 等權重向量索引）。
INCOME_LABELS = ['4萬以下', '4~6萬', '6~10萬', '10~15萬', '15~25萬', '25萬以上']

# 7 個就業者職業類別（v2 抽樣的職業空間；順序對應 TAIPEI_OCC_W）。
OCC_CATS = ['管理/主管', '專業人員', '技術/助理專業', '事務人員',
            '服務/銷售', '農林漁牧', '技術工/勞工']

# 非就業人口在「產業別」欄的標記值。
NON_EMP_MARKER = '無（非就業人口）'

# 視為非就業人口的職業集合（產業別不抽樣，直接給 NON_EMP_MARKER）。
NON_EMPLOYED_OCCS = {'退休', '學生', '家管', '其他/待業'}


def age_to_group(a: int) -> str:
    """年齡 → 年齡組（deterministic，對應 AGE_GROUP_LABELS）。"""
    if a <= 24:
        return '15–24歲'
    if a <= 34:
        return '25–34歲'
    if a <= 44:
        return '35–44歲'
    if a <= 54:
        return '45–54歲'
    if a <= 64:
        return '55–64歲'
    return '65歲以上'
