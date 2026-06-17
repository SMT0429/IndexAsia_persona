# Taipei Persona 生成專案

以官方普查、選舉與薪資資料為條件機率來源，生成 **3,000 筆台北市虛擬選民 persona**（Silicon Sampling）。
每筆 persona 含 25 個交付欄位（年齡、性別、行政區、教育、職業、收入、族群、政黨傾向、社會價值觀、關注議題…）。

欄位依賴與抽樣規則以 [method/field_dependency_map.md](method/field_dependency_map.md)（v2.3）為**權威來源**。

---

## 目錄結構

| 路徑 | 內容 |
|------|------|
| `scripts/` | 現役 pipeline：`run_pipeline.py`（一鍵跑完）、`pipeline_common.py`（共用路徑/常數/RNG）、12 支階段腳本 `taipei_*.py`、`taipei_finalize.py`（裁切交付欄位） |
| `scripts/legacy/` | 已失效／被取代的一次性腳本（保留備參，不在 pipeline 內） |
| `method/` | 11 份單欄位方法論文件（每欄位一份，含版本與文獻依據） |
| `data/raw/` | **原始輸入**：`Basic.xlsx`、`Political.xlsx`、`distributions_real.xlsx`、`income/`、`industry/`、`taiwan_political_events/`、`census/`（113 普查 .ods）、`elections_2020/`（中選會 .xls） |
| `data/WIP/` | pipeline 12 階段中繼檔（**gitignore，可重生**） |
| `data/taipei_final/` | 最終交付檔 `taipei_persona_<時間戳>.xlsx`（25 欄） |
| `data/old_output/` | 歷史／除錯輸出歸檔 |
| `reports/` | 分析與欄位建構報告（.md/.pdf）及 md→pdf 轉檔工具 |
| `QA/` | 品質檢核：`scripts/`（一致性檢查與修正）、`reports/`（QA 報告） |
| `docs/` | 跨欄位／簡報類文件（議題接收方法論、欄位建構簡報） |

---

## 如何執行

```bash
pip install -r requirements.txt
python3 scripts/run_pipeline.py        # 從 repo root 一鍵跑完
```

每階段以獨立子行程執行（隔離 RNG 全域狀態，確保可重現），fail-fast，
完成後 `taipei_finalize.py` 於 `data/taipei_final/` 產出帶時間戳的 25 欄交付檔。

### Pipeline 12 階段（順序 = field_dependency_map.md §1）

```
1. taipei_persona_v2      基礎人口（年齡/性別/行政區/教育/政黨傾向）
2. taipei_political_events 政治世代經歷
3. taipei_industry         產業別
4. taipei_income           月收入區間
5. taipei_religion         宗教與地方信仰
6. taipei_group            族群
7. taipei_splitTicket      分裂投票傾向（2020 立委/總統票）
8. taipei_value            社會價值觀（CO/ST 維度）
9. taipei_topic            關注議題（主/子議題）
10. taipei_speakingStyle   說話風格
11. taipei_clan            宗親地方組織連結強度
12. taipei_property        房產持有狀態
   └ finalize：移除宗教/說話風格/宗親等中繼欄，輸出 25 欄交付檔
```

> 注意：`taipei_industry`（stdlib `random`）與 `taipei_topic`（舊式 `np.random.seed`）刻意不換 RNG 引擎，
> 以保留既有抽樣序列與輸出位元一致性。

---

## 資料流

```
data/raw/  ──(12 階段)──▶  data/WIP/  ──(finalize)──▶  data/taipei_final/
（原始輸入）              （中繼，可重生）              （25 欄交付檔）
```

## 文件導覽

- **要懂欄位怎麼來** → `method/`（單欄位深入）＋ [reports/field_construction_report_20260610.md](reports/field_construction_report_20260610.md)（總覽）
- **要懂 pipeline 順序/依賴** → [method/field_dependency_map.md](method/field_dependency_map.md)（權威）
- **要看資料品質檢核** → `QA/reports/`
