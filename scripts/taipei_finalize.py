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

from pipeline_common import REPO_ROOT, FINAL_DIR, read_stage

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

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = FINAL_DIR / f"taipei_persona_{ts}.xlsx"
    out.to_excel(dest, index=False)

    print(f"✓ 最終交付檔：{dest.relative_to(REPO_ROOT)}（{len(out)} 筆 × {len(out.columns)} 欄）")
    print(f"  已移除：{'、'.join(DROP_COLS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
