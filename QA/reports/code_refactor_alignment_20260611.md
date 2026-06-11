# Pipeline 程式碼重構與 method 對齊報告

**日期：** 2026-06-11
**範圍：** `scripts/` 整條 12 階段 pipeline 全面重構（依使用者選定）
**權威依據：** `method/field_dependency_map.md`（v2.3）及各欄位 method 文件
**重要前提：** 本次**未更動 `method/` 下任何文件**（唯讀權威來源）。以下僅為程式碼變更與驗證紀錄，供參考。

---

## 一、做了什麼（不改任何生成邏輯/數值/輸出）

| 類別 | 內容 |
|------|------|
| 新增 | `scripts/pipeline_common.py`：集中「路徑解析、`read_stage`/`write_stage`、`make_rng`、共用常數」 |
| 新增 | `scripts/run_pipeline.py`：依 §1 順序、以子行程逐階段執行的編排器（fail-fast） |
| 新增 | `requirements.txt`：pandas / numpy / openpyxl / odfpy / xlrd |
| 重構 | 12 支 `taipei_*.py`：統一路徑（CWD 無關）、讀寫樣板、RNG 寫法、去重共用常數 |

### 解決的既有不一致
1. **路徑慣例三套混用** → 全部錨定 repo root，任何 CWD 皆可執行（v2 不再需 `cd scripts/`、income/religion/group 不再需 repo-root）。
2. **`political_events` 讀 v2 多 sheet 檔未指定 sheet** → `read_stage('v2')` 內部釘 `sheet_name='Personas'`，契約由 `PERSONAS_SHEET` 單一來源管控。
3. **共用常數散落** → `DISTRICTS`、`AGE_GROUP_LABELS`、`INCOME_LABELS`、`OCC_CATS`、`NON_EMP_MARKER`、`NON_EMPLOYED_OCCS`、`age_to_group` 集中於 `pipeline_common`（值與原各檔逐位元組相同）。
4. **無編排/環境檔** → 補 `run_pipeline.py` 與 `requirements.txt`。

### 刻意保留（改了會變輸出，故不動）
- `taipei_industry.py` 的 **stdlib `random.seed(42)` + `random.choices`**（換 numpy 會改抽樣序列）。
- `taipei_topic.py` 的 **舊式 `np.random.seed(42)` + `np.random.randint/choice`**（同理）。
- `taipei_persona_v2.py` 的 **6-sheet `ExcelWriter`**（保留 5 張驗證表，不走單 sheet 的 `write_stage`）。
- `taipei_property.py` 的 **per-id `np.random.default_rng(pid)`**（順序無關，已是標準工廠形狀）。
- 各腳本在地的權重/乘數/評分字典與私有重映射（如 income 的 `AGE_MAP`→`未滿25歲`、religion 的 3 段 `15-35/36-55/56+`）——屬該欄位私有語意，未集中。

### 各腳本變更摘要
| 腳本 | 路徑 | 讀 | 寫 | RNG | 常數 |
|------|------|----|----|-----|------|
| persona_v2 | ✅絕對化 | — | out_path 改 `data_path` | `make_rng()` | 匯入 DISTRICTS/年齡組/OCC_CATS/age_to_group；writer 用 `PERSONAS_SHEET` |
| political_events | ✅ | `read_stage('v2')`（釘 sheet） | `write_stage` | — | — |
| industry | ✅ | `read_stage` | `write_stage` | **保留 random** | 匯入 NON_EMP_MARKER/NON_EMPLOYED_OCCS |
| income | ✅ | `read_stage` | `write_stage` | `make_rng()` | 匯入 INCOME_LABELS（在地映射保留） |
| religion | ✅ | `read_stage` | `write_stage` | `make_rng()` | 3 段年齡保留在地 |
| group | ✅ | `read_stage` | `write_stage` | `make_rng()` | 匯入 AGE_GROUP_LABELS |
| splitTicket | ✅ | `read_stage` | `write_stage` | 無（deterministic） | 選舉檔走 `taipei_2020_path` |
| value | ✅ | `read_stage` | `write_stage` | 無 | 評分表保留在地 |
| topic | ✅ | `read_stage` | `write_stage` | **保留 np.random.seed** | — |
| speakingStyle | ✅ | `read_stage` | `write_stage` | 無 | — |
| clan | ✅ | `read_stage` | `write_stage` | 無 | — |
| property | ✅ | `read_stage` | `write_stage` | 保留 per-id | — |

---

## 二、驗證結果（重構不得改變輸出）

以「重構前現行碼跑出的 12 階段輸出」為 golden oracle，重構後比對：

- ✅ **12 個階段全部與 golden 逐格相同**（v2 另含 5 張驗證 sheet 亦相同）；30 欄 × 3000 列零差異。
- ✅ **雙跑重現性**：整條 pipeline 連跑兩次，輸出仍與 golden 全等。
- ✅ **CWD 無關**：從 repo-root 與從 `scripts/` 單獨執行，輸出皆與 golden 全等。
- ✅ **deterministic 不變量 = 0**：年齡組↔年齡、非就業→無產業、農林漁牧→農業、厭惡政黨≠自身黨、主類型↔CO/ST 象限。

> 結論：重構純屬「路徑/讀寫/種子寫法/常數去重」的結構整理，**統計輸出零變動**。

---

## 三、需要您裁示：重生輸出 vs temp 補丁的差異（issue 5 / 6 軟尾）

重生的乾淨輸出**忠實依循 method v2.3**，而當初 `QA/scripts/fix_temp_consistency.py` 對 temp 檔做的是**比方法論更嚴格的硬性歸零**。兩者在以下兩處有「可解釋的統計尾巴」差異：

| 項 | method v2.3 規定 | 重生輸出（依 method） | temp 補丁（更嚴格） |
|----|-----------------|---------------------|--------------------|
| issue 5：<35 國小以下 | <25 ×0.0（硬移除）、**25–34 ×0.05（趨近 0，非 0）** | <25＝**0**；25–34 殘留 **3 筆**（年齡 25/26/29） | 全部硬改為「國中」＝0 |
| issue 6：15–24 自有本人 | A 乘數 **0.05（趨近 0，非 0）** | 殘留 **4 筆**（年齡 15/19/19/24） | 硬排除 A 重抽＝0 |

**說明：** 這 7 筆殘留不是 bug——method 對 issue 5（25–34 段）與 issue 6 採「機率壓低（×0.05）」而非「硬禁」，原 consistency 報告也將兩者列為 🟢 低優先「可接受統計尾巴」。由於您指示「按 method 文件為主」，目前碼與輸出正確反映 method。

**決定（2026-06-11）：採 A——維持現狀。** 依 method v2.3 保留軟尾，`method/` 不更動。

**選項（供記錄）：**
- **A（維持現狀，已採用）**：依 method 保留軟尾，7 筆屬可接受統計尾巴；temp 檔仍封存保留。
- **B（要完全零殘留）**：需把 method §3.5（25–34 段）與 §3.28（15–24 A 乘數）由「×0.05」改為「×0.0 硬禁」，並同步 `taipei_persona_v2.py` / `taipei_property.py`。**此涉及更動 method/，需您明確同意後另案處理。**

---

## 四、附註

- **`method/` 全程未由本次作業更動。** 但 git 顯示 `method/split_ticket_methodology.md`、`method/values_column_methodology.md` 為 modified——此為**本次作業之前既存的未提交變更**，非本次所為，已原樣保留、未碰。
- `QA/scripts/fix_temp_consistency.py` 與 `data/taipei_personas_3000_temp.xlsx` 依您指示**保留封存**，未汰除、未更動。
- `data/taipei_personas_3000_*.xlsx`（12 階段，最終 `property` 為 30 欄）已由重構後 pipeline 重新產生為乾淨輸出。
