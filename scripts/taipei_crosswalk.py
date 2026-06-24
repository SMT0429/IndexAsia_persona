#!/usr/bin/env python3
"""
taipei_crosswalk.py — 還原「全台版台北 agent ↔ Taipei 專版」的連結鍵。

背景：
  全台交付檔（data/taiwan_final/）中居住地=臺北市的 N 筆,其實是 Taipei 專版
  （data/taipei_final/）的原封子集——同一批 agent。finalize 階段在併入時覆寫了
  兩個欄位,使兩份無法直接 join:
    - 居住地 → 統一改成「臺北市」(丟掉行政區)
    - id     → 重新編號 1..3000

  本模組把被覆寫掉的 taipei 原始 id 與行政區還原出來,輸出對照表(crosswalk):
    taiwan_id ↔ taipei_id ↔ 行政區。

兩種用途:
  1. Backfill（本檔 CLI）：對「已產出」的 taiwan_final 檔,用屬性精確比對還原。
  2. By-construction（taipei_finalize.py import 用）：產檔當下手上就有來源列,
     直接以 build_crosswalk_from_source() 組表,精確、無需比對。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 對照表欄位（Part A backfill 與 Part B finalize 共用,避免兩套定義漂移）。
# taiwan_id / taipei_id / 行政區 為連結鍵;性別 / 年齡 附帶供肉眼抽查。
CROSSWALK_COLS = ["taiwan_id", "taipei_id", "行政區", "性別", "年齡"]

# 比對用 key 須排除的欄位:id（兩邊各自編號）與居住地（taiwan 已被改成臺北市）。
_NON_MATCH_COLS = ("id", "居住地")


def _attr_key(df: pd.DataFrame, attr_cols: list[str]) -> pd.Series:
    """把指定欄位串成一個可雜湊的字串 key（逐欄轉字串後以 || 連接）。"""
    return df[attr_cols].astype(str).agg("||".join, axis=1)


def build_crosswalk_by_attrs(taiwan_df: pd.DataFrame, taipei_df: pd.DataFrame) -> pd.DataFrame:
    """以屬性精確比對,還原 taiwan 台北列對應的 taipei id 與行政區。

    取 taiwan 中「居住地==臺北市」的列,以除 id/居住地 外的所有共同欄位組 key,
    精確 join 回 taipei 還原 taipei_id 與行政區。對不上、有重複、或 taipei 端
    key 不唯一即主動失敗（比照 finalize 的 fail-fast,避免靜默產出錯誤對照表）。
    """
    attr_cols = [c for c in taipei_df.columns if c not in _NON_MATCH_COLS]
    missing = [c for c in attr_cols if c not in taiwan_df.columns]
    if missing:
        raise SystemExit(f"✗ taiwan/taipei 欄位不一致,無法比對:{missing}")

    tp_key = _attr_key(taipei_df, attr_cols)
    if tp_key.duplicated().any():
        n = int(tp_key.duplicated().sum())
        raise SystemExit(f"✗ taipei 專版有 {n} 組重複屬性,無法唯一還原 id。")

    lookup = pd.DataFrame({
        "k": tp_key,
        "taipei_id": taipei_df["id"].values,
        "行政區": taipei_df["居住地"].values,
    })

    tw_tp = taiwan_df[taiwan_df["居住地"] == "臺北市"].copy()
    tw = pd.DataFrame({
        "taiwan_id": tw_tp["id"].values,
        "性別": tw_tp["性別"].values,
        "年齡": tw_tp["年齡"].values,
        "k": _attr_key(tw_tp, attr_cols).values,
    })

    merged = tw.merge(lookup, on="k", how="left")
    unmatched = int(merged["taipei_id"].isna().sum())
    dup = len(merged) - merged["k"].nunique()
    if unmatched:
        raise SystemExit(f"✗ {unmatched} 筆台北列在 Taipei 專版找不到對應（資料可能已變動）。")
    if dup:
        raise SystemExit(f"✗ 有 {dup} 筆對應到多列,無法唯一還原。")

    out = merged.assign(taipei_id=merged["taipei_id"].astype(int))
    return out[CROSSWALK_COLS].sort_values("taiwan_id").reset_index(drop=True)


def build_crosswalk_from_source(reuse_df: pd.DataFrame, taiwan_ids) -> pd.DataFrame:
    """產檔當下組表:reuse_df 是未覆寫的 Taipei 來源列,taiwan_ids 為其在全台檔的新 id。

    供 taipei_finalize.py 使用——此時 taipei 原始 id（reuse_df['id']）與行政區
    （reuse_df['居住地']）都還在,直接對上即可,毋須屬性比對。
    """
    if len(reuse_df) != len(taiwan_ids):
        raise SystemExit(
            f"✗ crosswalk 長度不符:來源 {len(reuse_df)} ≠ taiwan_ids {len(taiwan_ids)}"
        )
    out = pd.DataFrame({
        "taiwan_id": list(taiwan_ids),
        "taipei_id": reuse_df["id"].astype(int).values,
        "行政區": reuse_df["居住地"].values,
        "性別": reuse_df["性別"].values,
        "年齡": reuse_df["年齡"].values,
    })
    return out[CROSSWALK_COLS].sort_values("taiwan_id").reset_index(drop=True)


def crosswalk_dest(taiwan_path: Path) -> Path:
    """對照表輸出路徑:與 taiwan 交付檔同目錄、同 timestamp,後綴 _taipei_crosswalk.csv。"""
    return taiwan_path.with_name(f"{taiwan_path.stem}_taipei_crosswalk.csv")


def write_crosswalk(df: pd.DataFrame, dest: Path) -> Path:
    """寫出對照表 csv（utf-8-sig 便於 Excel 開啟中文）。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False, encoding="utf-8-sig")
    return dest


# ── Backfill CLI ─────────────────────────────────────────────────────────────
def _latest(glob_dir: Path, pattern: str) -> Path:
    files = sorted(glob_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"找不到 {pattern} 於 {glob_dir}")
    return files[-1]


def main(argv: list[str] | None = None) -> int:
    import argparse

    import region_profile as rp
    from pipeline_common import REPO_ROOT

    taiwan_final_dir = REPO_ROOT / "data" / "taiwan_final"

    ap = argparse.ArgumentParser(description="Backfill 全台版台北 agent ↔ Taipei 專版 對照表")
    ap.add_argument("taiwan_xlsx", nargs="?", help="指定 taiwan_final 檔（預設取最新）")
    args = ap.parse_args(argv)

    taiwan_path = Path(args.taiwan_xlsx) if args.taiwan_xlsx else _latest(
        taiwan_final_dir, "taiwan_persona_*.xlsx"
    )
    taipei_path = rp.latest_taipei_final()

    taiwan_df = pd.read_excel(taiwan_path)
    taipei_df = pd.read_excel(taipei_path)

    xwalk = build_crosswalk_by_attrs(taiwan_df, taipei_df)
    dest = write_crosswalk(xwalk, crosswalk_dest(taiwan_path))

    print(f"✓ 對照表:{dest.relative_to(REPO_ROOT)}（{len(xwalk)} 筆）")
    print(f"  taiwan：{taiwan_path.name}")
    print(f"  taipei：{taipei_path.name}")
    print(f"  unmatched=0, dup=0；行政區分布={xwalk['行政區'].nunique()} 區")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
