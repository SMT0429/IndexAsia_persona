#!/usr/bin/env python3
"""
region_profile.py — 全台 persona 的「地理設定檔」抽象與 region-keyed 資料載入。

提供給各 stage 腳本：
  - REGIONS / REGION_NAMES：22 縣市清單（臺北市標記 reuse，不重新生成）。
  - allocate(n_total)：把 N 依人口佔比分配到各縣市（最大餘數法，每縣市至少 1）。
    臺北市配額單獨回傳（由 finalize 從既有 Taipei 3000 抽樣帶入，不進生成管線）。
  - load_*()：讀 data/raw/regions/*.csv，回傳 region/age-keyed 結構。
  - sample_taipei_reuse(n)：從最新 data/taipei_final/*.xlsx 隨機抽 n 筆（25 欄成品）。

資料來源由 scripts/prep_taiwan_sources.py 產生。
"""

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
REGIONS_DIR = REPO_ROOT / "data" / "raw" / "regions"
TAIPEI_FINAL_DIR = REPO_ROOT / "data" / "taipei_final"

REUSE_COUNTIES = {'臺北市'}
DEFAULT_SEED = 42


# ── 區域清單 ──────────────────────────────────────────────────────────────────
def _regions_df() -> pd.DataFrame:
    return pd.read_csv(REGIONS_DIR / "regions.csv")


REGIONS = _regions_df()
REGION_NAMES = list(REGIONS['region_name'])
GEN_REGIONS = [r for r in REGION_NAMES if r not in REUSE_COUNTIES]  # 需生成的 21 縣市


# ── N 配額分配（最大餘數法）─────────────────────────────────────────────────
def allocate(n_total: int) -> dict:
    """N 依人口佔比 → 各縣市人數（每縣市至少 1，最大餘數補足，總和 = n_total）。"""
    share = REGIONS.set_index('region_name')['pop_share']
    raw = share * n_total
    floor = np.floor(raw).astype(int).clip(lower=1)
    remainder = n_total - floor.sum()
    # 依小數餘數大小補/扣
    frac = (raw - np.floor(raw)).sort_values(ascending=False)
    counts = floor.to_dict()
    if remainder > 0:
        for name in frac.index[:remainder]:
            counts[name] += 1
    elif remainder < 0:
        for name in frac.index[remainder:]:
            counts[name] -= 1
    assert sum(counts.values()) == n_total
    return counts


def taipei_quota(n_total: int) -> int:
    return allocate(n_total)['臺北市']


# ── region-keyed loaders ─────────────────────────────────────────────────────
def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(REGIONS_DIR / name)


def load_gender() -> dict:
    """region → (male_ratio, female_ratio)。"""
    df = REGIONS.set_index('region_name')
    return {r: (df.loc[r, 'male_ratio'], df.loc[r, 'female_ratio']) for r in REGION_NAMES}


def load_age() -> pd.DataFrame:
    """region × 6 年齡組 人數（index=region_name）。"""
    return _csv("census_age.csv").set_index('region_name')


def load_edu() -> pd.DataFrame:
    return _csv("census_edu.csv").set_index('region_name')


def load_occupation() -> pd.DataFrame:
    return _csv("census_occupation.csv").set_index('region_name')


def load_marriage_age() -> dict:
    """age_group → 有偶率（全國）。"""
    df = _csv("marriage_age.csv")
    return dict(zip(df['age_group'], df['married_rate']))


def load_media_age() -> pd.DataFrame:
    """age_group × 平台 使用率（全國，index=age_group）。"""
    return _csv("media_age.csv").set_index('age_group')


def load_housing() -> pd.DataFrame:
    return _csv("housing.csv").set_index('region_name')


def load_election_party() -> pd.DataFrame:
    """region × {DPP,KMT,TPP,Other} 不分區立委得票比例。"""
    return _csv("election_party.csv").set_index('region_name')


def load_election_pres() -> pd.DataFrame:
    """region × {DPP,KMT,Other} 總統得票比例。"""
    return _csv("election_pres.csv").set_index('region_name')


def load_ethnic_base() -> pd.DataFrame:
    """region × {閩南,客家,外省,原住民} 比例。"""
    return _csv("ethnic_base.csv").set_index('region_name')


# ── 臺北重用 ──────────────────────────────────────────────────────────────────
def latest_taipei_final() -> Path:
    files = sorted(TAIPEI_FINAL_DIR.glob("taipei_persona_*.xlsx"))
    if not files:
        raise FileNotFoundError(f"找不到 Taipei 3000 交付檔於 {TAIPEI_FINAL_DIR}")
    return files[-1]


def sample_taipei_reuse(n: int, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """從最新 Taipei 3000 隨機抽 n 筆（不改任何欄值），作為全台的臺北市配額。"""
    src = pd.read_excel(latest_taipei_final())
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(src), size=n, replace=False)
    return src.iloc[np.sort(idx)].reset_index(drop=True)


if __name__ == '__main__':
    N = 3000
    counts = allocate(N)
    print(f"N={N} 分配（總和={sum(counts.values())}）：")
    for r in REGION_NAMES:
        flag = '  ← reuse(Taipei3000)' if r in REUSE_COUNTIES else ''
        print(f"  {r}: {counts[r]}{flag}")
    print(f"\n臺北市配額 = {taipei_quota(N)}")
    tp = sample_taipei_reuse(taipei_quota(N))
    print(f"臺北重用抽樣：{tp.shape}，居住地樣本={sorted(tp['居住地'].unique())[:4]}")
    print(f"欄位數={tp.shape[1]}（應 25）")
