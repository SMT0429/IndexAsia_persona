#!/usr/bin/env python3
"""
ingest_to_db.py — 把既有的歷史交付 xlsx 回填進版本庫（一次性遷移用）。

版本控制上線「之前」已經產出的 data/{taipei,taiwan}_final/*.xlsx，用本工具一次灌進
同一個 personas.db，讓過去的版本也納入管理。content_hash 去重 → 可安全重跑。

用法：
  python scripts/ingest_to_db.py --backfill         # 回填兩個 final 目錄所有歷史 xlsx
  python scripts/ingest_to_db.py <path.xlsx>        # 回填指定檔
  python scripts/ingest_to_db.py --list             # 列出版本庫現況
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

import persona_db
from pipeline_common import DATA_DIR


def _profile_of(path: Path) -> str:
    name = path.name
    if name.startswith("taiwan_persona"):
        return "taiwan"
    if name.startswith("taipei_persona"):
        return "taipei"
    raise ValueError(f"無法由檔名判斷 profile（需 taipei_/taiwan_persona 前綴）：{name}")


def _generated_at(path: Path) -> str:
    """由檔名 _<YYYYMMDD_HHMMSS> 解析產出時間 → ISO 字串。"""
    stem = path.stem  # e.g. taipei_persona_20260611_172621
    parts = stem.split("_")
    ts = "_".join(parts[-2:])  # 20260611_172621
    try:
        return datetime.strptime(ts, "%Y%m%d_%H%M%S").isoformat(timespec="seconds")
    except ValueError:
        # 檔名不含可解析時間戳時，退而用檔案修改時間。
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def _crosswalk_for(path: Path) -> pd.DataFrame | None:
    """taiwan 檔的對照表 sidecar（<stem>_taipei_crosswalk.csv），有則讀入。"""
    cw_path = path.with_name(f"{path.stem}_taipei_crosswalk.csv")
    if not cw_path.exists():
        return None
    return pd.read_csv(cw_path, encoding="utf-8-sig")


def _ingest_one(path: Path) -> None:
    profile = _profile_of(path)
    df = pd.read_excel(path)
    crosswalk = _crosswalk_for(path) if profile == "taiwan" else None
    meta = {
        "profile": profile,
        "generated_at": _generated_at(path),
        "source": f"backfill:{path.name}",
        "notes": "回填歷史交付檔；git_commit 為回填當下 HEAD，非必然為產出 commit。",
    }
    # 以回填前後的版本數判斷此檔是「新版本」還是「與既有版本內容相同被去重」。
    before = len(persona_db.list_runs())
    run_id = persona_db.insert_run(df, meta, crosswalk=crosswalk)
    deduped = len(persona_db.list_runs()) == before
    cw_n = 0 if crosswalk is None else len(crosswalk)
    tag = "↩ 內容同既有版本，併入" if deduped else "✓ 新版本"
    print(f"{tag} {path.name} → run_id={run_id}"
          f"（{len(df)} 筆，profile={profile}"
          f"{'，對照表 ' + str(cw_n) + ' 筆' if cw_n else ''}）")


def _backfill_paths() -> list[Path]:
    paths: list[Path] = []
    for profile in ("taipei", "taiwan"):
        d = DATA_DIR / f"{profile}_final"
        if d.exists():
            # 排除 Excel 暫存檔（~$ 前綴）；crosswalk 為 .csv 不會被 *.xlsx 撈到。
            paths += sorted(p for p in d.glob("*.xlsx") if not p.name.startswith("~$"))
    return paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="回填歷史交付 xlsx 進版本庫")
    ap.add_argument("xlsx", nargs="?", help="指定要回填的 xlsx")
    ap.add_argument("--backfill", action="store_true",
                    help="回填 data/{taipei,taiwan}_final/ 所有歷史 xlsx")
    ap.add_argument("--list", action="store_true", help="列出版本庫現況後結束")
    args = ap.parse_args(argv)

    persona_db.init_db()

    if args.list:
        runs = persona_db.list_runs()
        print("（版本庫尚無任何版本）" if runs.empty
              else runs[["run_id", "profile", "generated_at", "source",
                         "git_short", "row_count"]].to_string(index=False))
        return 0

    if args.backfill:
        paths = _backfill_paths()
        if not paths:
            print("找不到任何歷史 xlsx 可回填。")
            return 0
        print(f"準備回填 {len(paths)} 個檔…")
        for p in paths:
            _ingest_one(p)
        return 0

    if args.xlsx:
        _ingest_one(Path(args.xlsx))
        return 0

    ap.error("請指定 <xlsx>、--backfill 或 --list")
    return 2  # 不會到達（argparse error 會 exit）


if __name__ == "__main__":
    raise SystemExit(main())
