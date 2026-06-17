#!/usr/bin/env python3
"""
run_pipeline.py — 依 method/field_dependency_map.md §1 順序，一鍵跑完 12 階段 pipeline，
                  最後執行 taipei_finalize.py 產出 25 欄最終交付檔。

設計重點：
  - 每階段以「獨立子行程」執行（subprocess）。這是刻意的：industry 使用 stdlib
    random.seed、topic 使用 np.random.seed，皆會污染 process 全域 RNG 狀態；分行程
    可保證每階段都從乾淨種子起跑，輸出與逐支手動執行完全一致。
  - fail-fast：任一階段非零退出即中止並回傳該退出碼。
  - 與 CWD 無關（各腳本重構後皆錨定 repo root）。

用法：
    python scripts/run_pipeline.py          # 從 repo root
    python run_pipeline.py                  # 從 scripts/
"""

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

# 順序 = field_dependency_map.md §1（修改順序時請同步更新該文件）
PIPELINE = [
    "taipei_persona_v2.py",
    "taipei_political_events.py",
    "taipei_industry.py",
    "taipei_income.py",
    "taipei_religion.py",
    "taipei_group.py",
    "taipei_splitTicket.py",
    "taipei_value.py",
    "taipei_topic.py",
    "taipei_speakingStyle.py",
    "taipei_clan.py",
    "taipei_property.py",
]


def main() -> int:
    n = len(PIPELINE)
    t_all = time.time()
    for i, script in enumerate(PIPELINE, 1):
        path = SCRIPTS_DIR / script
        print(f"\n[{i}/{n}] ▶ {script}", flush=True)
        t0 = time.time()
        result = subprocess.run([sys.executable, str(path)], cwd=SCRIPTS_DIR)
        if result.returncode != 0:
            print(f"\n✗ 第 {i} 階段失敗：{script}（exit {result.returncode}）")
            return result.returncode
        print(f"  ✓ {script} 完成（{time.time() - t0:.1f}s）", flush=True)
    print(f"\n✅ Pipeline 完成（{n}/{n}），總耗時 {time.time() - t_all:.1f}s。")

    # 後處理：裁切交付欄位（移除宗教/說話風格/宗親），輸出帶時間戳的 25 欄最終檔。
    print("\n[finalize] ▶ taipei_finalize.py", flush=True)
    result = subprocess.run([sys.executable, str(SCRIPTS_DIR / "taipei_finalize.py")], cwd=SCRIPTS_DIR)
    if result.returncode != 0:
        print(f"\n✗ finalize 階段失敗（exit {result.returncode}）")
        return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
