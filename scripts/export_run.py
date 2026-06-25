#!/usr/bin/env python3
"""
export_run.py — 按需把版本庫的某個版本匯成 Excel（「要輸出我再用 Excel 輸出」）。

pipeline 每次跑批只寫 DB（見 taipei_finalize.py），不再自動產 xlsx。需要交付檔時
用本工具把指定版本（或某 profile 最新版）匯出，預設沿用原命名慣例放回 FINAL_DIR。

用法：
  python scripts/export_run.py --latest                 # 當前 PROFILE 最新版本
  python scripts/export_run.py --latest --profile taiwan
  python scripts/export_run.py --run-id 7               # 指定版本
  python scripts/export_run.py --run-id 7 -o some/path.xlsx
  python scripts/export_run.py --list                   # 列出所有版本

taiwan 版若有對照表，會一併匯出 *_taipei_crosswalk.csv sidecar（沿用舊命名）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import persona_db
from pipeline_common import DATA_DIR, PROFILE, REPO_ROOT


def _final_dir(profile: str) -> Path:
    """該 profile 的交付目錄（taipei→taipei_final、taiwan→taiwan_final）。"""
    return DATA_DIR / f"{profile}_final"


def _default_dest(run_row: dict) -> Path:
    """沿用舊命名：{profile}_persona_<generated_at 時間戳>.xlsx 放回 FINAL_DIR。"""
    profile = run_row["profile"]
    # generated_at 為 ISO（2026-06-25T17:26:21）→ 還原成 20260625_172621。
    ts = run_row["generated_at"].replace("-", "").replace(":", "").replace("T", "_")[:15]
    name_prefix = "taiwan_persona" if profile == "taiwan" else "taipei_persona"
    return _final_dir(profile) / f"{name_prefix}_{ts}.xlsx"


def _print_runs() -> None:
    runs = persona_db.list_runs()
    if runs.empty:
        print("（版本庫尚無任何版本）")
        return
    show = ["run_id", "profile", "generated_at", "source", "git_short",
            "git_dirty", "row_count", "label"]
    cols = [c for c in show if c in runs.columns]
    print(runs[cols].to_string(index=False))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="把版本庫的某版本匯成 Excel")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-id", type=int, help="要匯出的版本 run_id")
    g.add_argument("--latest", action="store_true", help="匯出某 profile 的最新版本")
    g.add_argument("--list", action="store_true", help="列出所有版本後結束")
    ap.add_argument("--profile", default=PROFILE,
                    help="搭配 --latest 使用（預設取自 PERSONA_PROFILE）")
    ap.add_argument("-o", "--output", help="輸出路徑（預設依命名慣例放回 FINAL_DIR）")
    args = ap.parse_args(argv)

    if args.list:
        _print_runs()
        return 0

    if args.latest:
        run_id = persona_db.latest_run(args.profile)
        if run_id is None:
            print(f"✗ profile={args.profile} 尚無任何版本。", file=sys.stderr)
            return 1
    else:
        run_id = args.run_id

    # 取 run metadata（決定命名/profile）與資料。
    conn = persona_db.connect()
    try:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        print(f"✗ run_id={run_id} 不存在。", file=sys.stderr)
        return 1
    run_row = dict(row)

    df = persona_db.load_run(run_id)

    dest = Path(args.output) if args.output else _default_dest(run_row)
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(dest, index=False)
    try:
        shown = dest.relative_to(REPO_ROOT)
    except ValueError:
        shown = dest
    print(f"✓ 已匯出 run_id={run_id}（{len(df)} 筆 × {len(df.columns)} 欄）→ {shown}")

    # taiwan 版：若有對照表一併匯出 sidecar（沿用舊命名）。
    if run_row["profile"] == "taiwan":
        cw = persona_db.load_crosswalk(run_id)
        if len(cw):
            from taipei_crosswalk import crosswalk_dest, write_crosswalk
            cw_dest = write_crosswalk(cw, crosswalk_dest(dest))
            try:
                cw_shown = cw_dest.relative_to(REPO_ROOT)
            except ValueError:
                cw_shown = cw_dest
            print(f"  對照表 → {cw_shown}（{len(cw)} 筆）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
