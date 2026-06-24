"""
taipei_finalize.py — pipeline 後處理：產出最終交付檔。

輸入：taipei_personas_3000_property.xlsx（pipeline 終點，30 欄）
輸出：data/taipei_final/taipei_persona_<YYYYMMDD_HHMMSS>.xlsx（25 欄）

說明：
  這些維度仍須在 pipeline 中計算（下游維度有依賴，如價值觀/拆票用到「宗教與
  地方信仰」），故僅在「全程跑完之後」於最終交付檔移除，不影響中繼計算。

移除欄位（5 欄；30 → 25，含 id）：
  宗教            → 宗教與地方信仰
  說話風格        → 說話風格_正式程度 / _溝通取向 / _語言切換
  宗親地方組織連結強度 → 宗親地方組織連結強度
"""

from datetime import datetime

import pandas as pd

from pipeline_common import REPO_ROOT, FINAL_DIR, read_stage, PROFILE, N_TOTAL

# 最終交付檔須移除的欄位（拿掉宗教、說話風格、宗親地方組織連結強度）
DROP_COLS = [
    "宗教與地方信仰",
    "說話風格_正式程度",
    "說話風格_溝通取向",
    "說話風格_語言切換",
    "宗親地方組織連結強度",
]

# 預期最終欄數（含 id）；對不上即視為 pipeline 結構改變，主動失敗以免靜默交錯檔。
EXPECTED_COLS = 25


def main() -> int:
    df = read_stage("property")

    missing = [c for c in DROP_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"✗ property 輸出缺少預期欄位，無法裁切：{missing}")

    out = df.drop(columns=DROP_COLS)
    if len(out.columns) != EXPECTED_COLS:
        raise SystemExit(
            f"✗ 裁切後欄數 {len(out.columns)} ≠ 預期 {EXPECTED_COLS}，請檢查 pipeline 欄位異動。"
        )

    name_prefix = "taipei_persona"
    crosswalk = None  # 全台 profile 才會組:台北重用列 ↔ Taipei 專版原始 id/行政區。
    if PROFILE == 'taiwan':
        # 併入台北重用樣本（從 Taipei 3000 抽 N_台北 筆，欄位對齊後 concat → 3000×25）。
        import region_profile as rp
        from taipei_crosswalk import build_crosswalk_from_source
        quota = rp.taipei_quota(N_TOTAL)
        tp = rp.sample_taipei_reuse(quota).reindex(columns=out.columns)
        # 在覆寫 id/居住地「之前」擷取來源:taipei 原始 id 與行政區（供對照表）。
        tp_source = tp[['id', '居住地']].copy()
        # 台北重用列的居住地統一標為「臺北市」（與其他縣市同層級，不顯示行政區）。
        tp['居住地'] = '臺北市'
        missing = [c for c in out.columns if tp[c].isna().all()]
        if missing:
            raise SystemExit(f"✗ 台北重用樣本缺欄位（與管線 schema 不符）：{missing}")
        out = (pd.concat([tp, out], ignore_index=True)
               .pipe(lambda d: d.assign(id=range(1, len(d) + 1))))
        if len(out) != N_TOTAL:
            raise SystemExit(f"✗ 併入後列數 {len(out)} ≠ {N_TOTAL}")
        # 台北列排在 concat 最前,renumber 後其新 id 即 1..quota,直接對上來源資訊。
        crosswalk = build_crosswalk_from_source(
            tp_source.assign(性別=tp['性別'].values, 年齡=tp['年齡'].values),
            taiwan_ids=range(1, quota + 1),
        )
        name_prefix = "taiwan_persona"
        print(f"  併入台北重用 {quota} 筆 + 生成 {len(out) - quota} 筆 = {len(out)} 筆")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = FINAL_DIR / f"{name_prefix}_{ts}.xlsx"
    out.to_excel(dest, index=False)

    print(f"✓ 最終交付檔：{dest.relative_to(REPO_ROOT)}（{len(out)} 筆 × {len(out.columns)} 欄）")
    print(f"  已移除：{'、'.join(DROP_COLS)}")

    if crosswalk is not None:
        from taipei_crosswalk import crosswalk_dest, write_crosswalk
        cw_dest = write_crosswalk(crosswalk, crosswalk_dest(dest))
        print(f"  對照表（台北重用 ↔ Taipei 原始 id/行政區）：{cw_dest.relative_to(REPO_ROOT)}（{len(crosswalk)} 筆）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
