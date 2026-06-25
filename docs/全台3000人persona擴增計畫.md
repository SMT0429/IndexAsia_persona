# 全台灣 3000 人 Persona — 擴增計畫

> **地理 schema 已定案**：台北市 12 行政區（重用 Taipei 3000）+ 其他 21 縣市（縣市級）。
> 普查人口資料僅到縣市層，故其他五都不再細分行政區。

## 實作進度（2026-06-18）— ✅ 全台 pipeline 端到端可跑

`PERSONA_PROFILE=taiwan python scripts/run_pipeline.py` → `data/taiwan_final/taiwan_persona_<ts>.xlsx`（**3000×25**：12 台北行政區重用 + 21 縣市生成）。

| 階段 | 產物 | 狀態 |
|---|---|---|
| 資料前處理 `scripts/prep_taiwan_sources.py` | `data/derived/regions/` **10 個 region-keyed CSV** | ✅ 完成且驗證（客家梯度、原民花東高、政黨南北差、族群全國回算閩.75/客.11/外.11/原.027） |
| 地理設定檔 `scripts/region_profile.py` | 3000→22 縣市配額（台北 314…總和 3000）、loaders、`sample_taipei_reuse()` | ✅ 完成且驗證 |
| `pipeline_common.py` profile 化 | `PROFILE`、STAGE_FILES 工廠、N_TOTAL、FINAL_DIR | ✅ 完成（taipei 值逐位元組不變） |
| `scripts/taiwan_persona_v2.py` | 全台 demographics（21 縣市 2686 列，類別字串對齊台北版） | ✅ 完成且驗證 |
| 地理相關 stage profile 化 | `taipei_group`（族群→ethnic_base）、`taipei_industry`（拿掉台北係數）、`taipei_property`（縣市 housing 基準） | ✅ 完成（taipei 走 else 分支不變） |
| `taipei_finalize.py` + `run_pipeline.py` | finalize 併入台北 314 concat → 3000×25；runner 依 profile 選 v2 | ✅ 完成且驗證 |

**驗證結果**：產業 臺中 IT 0.07 vs 雲林 0.012、房產自有 0.70、族群 national-correct、台北重用列=314、各縣市人數≈人口佔比。

**已完成的縣市區域校正**：`taipei_splitTicket` 已 profile 化，全台版用 `election_pres/party.csv` 以**縣市**為 key 算拆票 boost（臺南 0.88、臺中 0.85 高；金門/連江/花東 低），`district_adj` 為 ±0.05 微調（依方法論）。台北重用列於 finalize 統一標「臺北市」（不顯示行政區），最終 22 個居住地。

**已知限制（非阻擋）**：
- 被裁切的 5 欄（宗教/說話風格×3/宗親）在全台版仍走台北邏輯，但**不進 25 欄交付**，不影響輸出。
- **台北「重新生成」**因原始選舉檔已移到 `taiwan/`（`data/raw/elections_2020/` 已刪），無法重跑；但全台版**重用**既有 Taipei 3000，不需重生成。

---

## Context

現行 pipeline（13 階段 + finalize）100% 鎖定台北市：地理單位是寫死的 12 行政區清單
（[pipeline_common.py:114](scripts/pipeline_common.py#L114)），census/選舉檔皆為台北專屬，
另有 ~9 張行政區別權重表（眷村族群、宗親、產業 multiplier…）。目標是把它擴增為**全台 22 縣市、
共 3000 人**的 persona，同時**不破壞現有已驗證的台北輸出**（作為回歸基準）。

已確認的三個關鍵決策：
1. **地理分層**：以**縣市為主**，**選定都會（預設六都）再細分到行政區**。3000 人依各單位人口比例分配。
2. **選舉基準**：沿用 **2020**（總統 + 不分區立委），只是把台北單檔換成全台各縣市/區檔。
3. **族群 / 宗親**：以台北眷村/行政區歷史地理為基礎的欄位，**改用區域級近似**（非逐行政區）。

核心架構策略：引入 **RegionProfile（地理設定檔）抽象** — 把「地理單位清單 + 各單位資料來源 + 參數表」
打包成 profile。Pipeline 變成 profile-agnostic，**台北是一個 profile、全台是另一個 profile**。
這樣可 (a) 保留台北可重現性當回歸護欄、(b) 讓所有理論/衍生階段 0 改動沿用、
(c) 把工作集中在「資料蒐集 + loader + 參數表」三件事。

---

## 欄位三分類（30 構建欄 → 25 交付欄）

### A. 直接可用：理論/全國來源，邏輯不改（~12 欄）
| 欄位 | 來源 | 備註 |
|---|---|---|
| 年齡組 | 由年齡衍生 | deterministic |
| 政治與歷史印記_世代 / _事件 | `taiwan_political_events.xlsx`（全國史） | 直接沿用 |
| 社會價值觀_CO / _ST / _主類型 / _核心動機 | Schwartz ESS（跨國通用） | 與地理無關，4 欄全沿用 |
| 說話風格_正式程度 / _溝通取向 | 由教育/收入/職業/CO-ST 衍生 | 規則不變 |
| 媒體習慣 | `Basic.xlsx` 年齡別（全國調查） | 直接沿用 |
| 厭惡政黨 | `Political.xlsx` TEDS（全國） | `_pool()` 已有「縣市→北部→全國」fallback，只需把寫死的 `臺北市` 改成各 persona 自己的縣市 |
| 國家認同 | 理論截斷常態（參數依政黨） | 參數不動，隨政黨傾向資料自動更新 |

### B. 需重找全國資料（~10 欄；多為公開資料，工作量主要在蒐集+對齊）
| 欄位 | 現況 | 需要的全國資料 |
|---|---|---|
| 居住地 / 性別 / 年齡 / 教育 | 台北 `113_*.ods`（寫死 row index） | 戶政司/主計總處**縣市別** 性別×年齡×教育 表 |
| 婚姻狀況 | 台北 `113_marryXarea.ods` | 戶政**縣市別**婚姻結構 |
| 職業 | 台北就業結構（`113_career.png`） | 主計總處**縣市別**職業，或全國 + 區域調整 |
| 政黨傾向 | 2020 台北不分區立委單檔 | CEC 2020 **全台各縣市/區**不分區立委得票 |
| 分裂投票傾向 | 2020 台北總統+立委 | CEC 2020 **全台**總統 vs 不分區立委（區域別差） |
| 房產類別 | 109 普查台北自有率 | 109 普查**縣市別**自有/租屋率（已是全國普查，抽縣市即可） |
| 月收入區間 | 全國 + 台北 ×1.35 | `表7 縣市別薪資`**已是全國** → 升級成各縣市真實薪資，移除台北係數 |
| 產業別 | 全國 + `TAIPEI_MULTIPLIER` | `industry.xls`**已是全國** → 移除/區域化 multiplier |

### C. 在地近似：改區域級（3 欄）
| 欄位 | 現況（台北專屬） | 區域級近似做法 |
|---|---|---|
| 族群 | 眷村行政區乘數 `DISTRICT_WAISHENG_MULT` | 客委會全國客家率 + 原民會**縣市別原民率** + 外省**區域率**，取代逐行政區乘數 |
| 宗親地方組織連結強度 | 眷村行政區 `CLAN_WEIGHTS` | 改用**城鄉/區域層級**（都會 vs 鄉鎮）近似 |
| 說話風格_語言切換 | 族群×年齡規則 | MOE 全國語言調查；族群×年齡規則改帶**區域**（如南部台語頻率↑、桃竹苗客語↑） |

> 關注議題/子議題大致沿用台灣議題分類；台北情境 booster（房價等）擴增時檢視一次即可，非阻擋項。

---

## Taipei vs Taiwan：各欄位建立方法逐欄對照

改動程度分三級：**🟢 不動**（理論/衍生，邏輯與輸出規則完全相同）、**🟡 換源**（演算法不變，把台北資料換成縣市別、或移除台北專屬係數）、**🔴 重寫**（地理邏輯本身改變）。

| 欄位 | Taipei 方法 | Taiwan 方法 | 主要差異 | 級別 |
|---|---|---|---|---|
| 居住地 | 12 行政區，依里人口權重 | 22 縣市（六都細分行政區），依縣市人口佔比 | 地理單位 區→縣市；權重改 `人口分布.xlsx 工作表2` | 🟡 |
| 性別 | 台北各區男女比 `113_genderXarea` | 縣市別男女比 `地區X性別` | 換縣市別來源 | 🟡 |
| 年齡 | 台北各區 5 歲組（`DIST_AGE_ROW` 寫死 row index） | 縣市別 5 歲組 `地區X年齡` | 去掉 row-index hack，改縣市鍵值查表 | 🟡 |
| 年齡組 | 由年齡衍生 | 同 | 無 | 🟢 |
| 教育程度 | 台北各區 `113_educationXarea`，含年齡 floor | 縣市別 `地區X教育程度`，floor 邏輯不變 | 換縣市別來源 | 🟡 |
| 職業 | 單一台北就業結構 `113_career.png` | 各縣市職業結構 `地區X職業`（金馬缺→全國補） | 台北結構→各縣市結構 | 🟡 |
| 婚姻狀況 | Basic 全國年齡基準 × 台北各區結婚登記密度 | `年齡x婚姻`（全國年齡基準，含同婚類型） | 失去縣市微調，改全國基準（資料更細） | 🟡 |
| 媒體習慣 | Basic 純年齡別（全國） | `年齡x媒體`（**6 區域 × 年齡**） | **升級**：多了居住區域維度 | 🟡 |
| 政黨傾向 | 2020 台北不分區立委各區得票 | 2020 各縣市不分區立委 `Taiwan不分區立委/` | 台北單檔→22 縣市，依 persona 所在地取分布 | 🟡 |
| 國家認同 | 依政黨截斷常態 μ/σ + 媒體上限 | 同理論，**參數不動** | 邏輯 0 改動，僅輸入政黨分布變了 | 🟢 |
| 厭惡政黨 | `Political.xlsx` 池（台北→北部→全國 fallback） | 同池，寫死 `臺北市` 改 persona 自身縣市 | `_pool()` 縣市參數化（既有全國結構直接用） | 🟡 |
| 政治印記_世代/_事件 | 全國史，由年齡定 | 同 | 無 | 🟢 |
| 產業別 | 全國 industry × 台北 multiplier（IT 3×、金融 2.5×） | 全國 industry，移除 `TAIPEI_MULTIPLIER`（用各縣市職業導出） | 拿掉台北產業係數 | 🟡 |
| 月收入區間 | 全國 DGBAS 薪資 × 台北 1.35 溢價 | `表7` 各縣市真實薪資，移除 1.35 | 全國+台北溢價→各縣市真實基準 | 🟡 |
| 宗教與地方信仰 | AIT 全國 base × 台北都市係數 × 年齡 | AIT 全國 base × 年齡（都市係數改區域 tier 或拿掉） | 台北都市調整→全國/區域 | 🟡 |
| 族群 | 台北 base(閩68/客17.4/外11/原2) × 年齡 × **行政區眷村乘數** × 政黨 | **縣市四步驟**：原民(戶政司法定)→客家(客委會率×0.55)→外省(眷村都會係數)→閩南(殘差)，全國 4062 錨點 | **整段重寫**：行政區眷村→縣市官方率；base 台北→全國單一認同 | 🔴 |
| 分裂投票傾向 | 規則+訊號加總 + 台北 2020 總統vs不分區 區域差 | 同演算法，`district_adj` 改各縣市 2020 總統vs不分區差 | boost_map 台北各區→全台縣市 | 🟡 |
| 社會價值觀_CO/_ST/_主類型/_核心動機 | Schwartz ESS（年齡/性別/教育） | 同（跨國通用） | 無（4 欄全沿用） | 🟢 |
| 關注議題/子議題 | 台灣議題分類 + 台北情境 booster | 同分類，booster 大致沿用（房價等台北情境檢視一次） | booster 微調 | 🟢 |
| 說話風格_正式程度/_溝通取向 | 由教育/收入/職業/CO-ST 衍生 | 同 | 無 | 🟢 |
| 說話風格_語言切換 | 族群×年齡規則 | 族群×年齡×**區域**（南部台語↑、桃竹苗客語↑） | 加區域維度 | 🔴 |
| 宗親地方組織連結強度 | 族群 base + 年齡 + **行政區眷村** bonus | 族群 base + 年齡 + **城鄉/區域 tier** | 行政區眷村→區域 tier；族群 base 接新欄 | 🔴 |
| 房產類別 | 109 普查台北自有率 72% × 年齡 × 收入 × 婚姻 | `t083` 各縣市自有/租用/配住/其他率 × 年齡 × 收入 × 婚姻 | base 台北→各縣市普查率 | 🟡 |

**一句話總結**：🟢 9 類（理論/衍生）完全沿用；🟡 大多數欄位是「同演算法、換成縣市別資料／移除台北專屬係數」；🔴 只有 **族群、宗親、語言切換** 3 欄的地理邏輯需要真正重寫（都因為台北版深綁「行政區眷村地理」，全台版改成縣市/區域級）。

> 注意：**台北市那 ~314 列直接重用 Taipei 3000**（見架構 §6），故上表的 🟡/🔴 改動實際只作用在「台北以外」的縣市；台北列所有欄位（含 🔴 三欄）沿用既有台北方法的成品值，不重算。

---

## 架構擴增設計（RegionProfile）

### 1. 地理模型 — 取代寫死的 `DISTRICTS`
- 新增單一真相來源 `data/derived/regions/regions.csv`：每列一個地理單位
  （欄位：`region_code, region_name, parent_county, level(county|district), pop_15plus`）。
  - 22 縣市；六都展開為行政區，其餘 16 縣市保持縣市層級。
  - 哪些都會細分由 profile 設定（預設六都，可調）。
- 在 [pipeline_common.py](scripts/pipeline_common.py) 以此檔建出 `REGIONS`、`region_pop_weight()`，
  **取代** `DISTRICTS`（[pipeline_common.py:114](scripts/pipeline_common.py#L114)）。
- 保留 `DISTRICTS = [台北 12 區]` 作為 `profile=taipei` 的 region 子集，**現有台北輸出不受影響**。

### 2. Profile 設定 — 取代散落的 Taipei 常數
新增 `scripts/region_profile.py`，定義 `PROFILE`（由環境變數/CLI 選 `taipei` | `taiwan`）：
- `regions`：本 profile 的地理單位清單（從 `regions.csv` 篩）。
- `census_loader` / `election_loader`：依 region 回傳該單位的 census/選舉分布
  （台北 profile = 現行 `.ods` row-index 路徑；全台 profile = 縣市別新檔）。
- `param_tables`：族群/宗親/產業/婚姻等**參數表改成資料檔**
  （`data/derived/regions/{ethnic_base,clan_tier,industry_mult,marriage_rate}.csv`，以 region 或 region_tier 為 key），
  取代 [taipei_group.py:30](scripts/taipei_group.py#L30)、[taipei_clan.py:30](scripts/taipei_clan.py#L30)、
  [taipei_industry.py:57](scripts/taipei_industry.py#L57)、[taipei_persona_v2.py:160](scripts/taipei_persona_v2.py#L160) 的寫死 dict。

### 3. 命名/N 參數化 — 取代 `taipei_personas_3000_*`
- 在 [pipeline_common.py:60](scripts/pipeline_common.py#L60) 把 `STAGE_FILES` 改成由
  `DATASET_PREFIX`（如 `taiwan_personas_3000`）+ stage key 動態組出；`N_TOTAL` 由 profile 提供。
- `FINAL_DIR`（[pipeline_common.py:28](scripts/pipeline_common.py#L28)）改成 `final/{profile}/`。
- 不必逐一改檔名字串，集中在工廠函式即可。

### 4. 重點階段改動
- **`taipei_persona_v2.py`（最大改動）**：把 `DIST_AGE_ROW` row-index hack
  （[taipei_persona_v2.py:62](scripts/taipei_persona_v2.py#L62)）與 `age15plus_pop`/`marry_2024`
  （[L160](scripts/taipei_persona_v2.py#L160)）改成走 `census_loader`（以 region 為 key 的鍵值查表）。
  抽樣 `n_total=3000`（[L396](scripts/taipei_persona_v2.py#L396)）改成依 `REGIONS` 的 `pop_weight` 分配，
  但**台北市配額不在此生成**（見 §6，台北直接重用既有 Taipei 3000）→ v2 只生成「台北以外」的縣市/行政區。
  `_pool()`（[L357](scripts/taipei_persona_v2.py#L357)）把寫死 `臺北市` 換成 persona 自身縣市
  — 既有 `COUNTY_CODE`/`REGION_GROUP`（[L311](scripts/taipei_persona_v2.py#L311)）正是為此預留的全國結構。
- **`taipei_splitTicket.py`**：`PRES_FILE`/`PARTY_FILE`（[taipei_splitTicket.py:16](scripts/taipei_splitTicket.py#L16)）
  改成 `election_loader` 依縣市/區取檔。
- **`taipei_group.py`（族群，全台版改寫）**：丟掉台北眷村行政區乘數，改採
  `taiwan_clan/taiwan_ethnicity_methodology.md` 的**縣市級四步驟**——
  原住民(戶政司法定率) → 客家(客委會率 × `k=0.55`) → 外省(`WAISHENG_BASE 0.10 × 眷村都會係數`) → 閩南(殘差，<0 時壓縮客家/外省)，
  以全國 4062 調查（閩76.9/客10.9/外10/原1.4）為錨點；參數表與 `county_shares()`/`assign_ethnicity()` 參考實作就在該 md §6，落成 `regions/ethnic_base.csv` 直接讀。
- **`taipei_clan.py`（宗親）**：第一層族群基礎分改吃上面新的 `族群` 欄；行政區眷村權重改用城鄉/區域 tier 近似。
- **`taipei_industry.py` / `taipei_income.py`**：移除台北 multiplier/×1.35，改吃縣市別真實資料（資料已全國）。
- **理論/衍生階段（value/topic/speakingStyle 之衍生部分/political_events）**：**0 改動**。

### 5. Runner — 幾乎不動
[run_pipeline.py](scripts/run_pipeline.py) 階段清單不變；加一個 `--profile` 參數透傳給各子行程
（環境變數 `PERSONA_PROFILE`），fail-fast 與 subprocess 隔離邏輯沿用。
finalize 階段多一步「併入台北重用樣本」（見 §6）。

### 6. 台北市：重用既有 Taipei 3000，不重新生成（關鍵需求）
全台 3000 的**台北市配額直接從已驗證的 Taipei 3000 抽樣帶入**，不走國家普查重生成。理由：台北版已用最高精度的在地方法（眷村族群、行政區宗親）建好並驗證，重用比用縣市級近似重做更準。

- **配額**：`N_台北 = round(3000 × 台北人口佔比)`。依 `人口分布.xlsx 工作表2` 台北佔比 ≈ 10.47% → **約 314 人**（實際值由 `pop_weight` 表算，與其他縣市同一套權重，確保總和 = 3000）。
- **來源**：`data/taipei_final/taipei_persona_<最新時間戳>.xlsx`（25 欄交付檔）。
- **抽法**：以 `make_rng(DEFAULT_SEED)` 從 3000 筆**隨機抽 N_台北 筆**（保留台北內部分布），不重算任何欄位。
- **流程接點**：台北樣本已是 25 欄成品，**不進 stage 管線**；在 **finalize** 把「其他 21 縣市的管線產物」與「台北抽樣」**concat** 成 3000×25。
  - 兩邊欄位 schema 一致（同一套 25 欄定義），`居住地` 台北列為行政區（與「六都細分」一致）。
  - 若 Taipei 3000 欄序/欄名與全台管線有差，finalize 前做一次欄位對齊（reindex columns）。
- **重要推論**：🔴 重寫的三欄（族群／宗親／語言切換）**只需對「台北以外」的縣市實作新方法**；台北列沿用 Taipei 3000 既有值，台北版的眷村/行政區邏輯**不必移植**。

---

## 資料盤點（全台來源 → `data/raw/taiwan/`；狀態 2026-06-18）

| 用途 | 來源檔（已落地） | 涵蓋 | 狀態 |
|---|---|---|---|
| 居住地/性別/年齡/教育/職業/婚姻/媒體 | `taiwan/taiwan_persona人口分布.xlsx`（7 sheet） | 22 縣市；媒體為 6 區域 | ✅ 到位 |
| 房產類別 | `taiwan/taiwan_property/t083.xlsx`（P01 按縣市別） | 22 縣市，109 普查表83：自有/租用/配住/其他(含借住) | ✅ 到位，直接對應四分類 |
| 分裂投票（總統） | `taiwan/總統-各投票所…(Excel檔)/` A05-2 縣市 · A05-3 村里 · A05-4 投開票所（`.xls`） | 22 縣市，**第15任=2020**（宋/韓/蔡） | ✅ 到位 |
| 政黨傾向（不分區立委） | `taiwan/Taiwan不分區立委/不分區立委-A05-6-…(縣市).xls`（22 檔） | 22 縣市 | ✅ 到位，**已換第10屆=2020**（與總統同年）。同夾另有 區域立委 A05-2／山地・平地立委 A05-4，供原民地理交叉檢核 |
| 族群（**縣市級**：閩南/客家/外省/原住民） | `taiwan/taiwan_clan/taiwan_ethnicity_methodology.md`（權威方法）＋ `115年…原住民概況.pdf`（戶政司原民率）＋ `File_96737.pdf`/截圖（客委會＋全國錨點） | 22 縣市 | ✅ **方法到位（真區域級）**，見下方 §4 族群 |
| 月收入 | `income/表7…縣市別.xlsx` | 22 縣市 | ✅ 既有，可移除台北 ×1.35 |
| 產業別 | `industry/industry.xls` | 全國 | ✅ 既有，移除 `TAIPEI_MULTIPLIER` |
| 政治世代/事件、社會價值觀、厭惡政黨 | `taiwan_political_events.xlsx`、Schwartz(理論)、`Political.xlsx` | 全國/理論 | ✅ 既有，邏輯不改 |

**仍待補/處理（皆為解析，非缺料）**：
1. **原住民 22 縣市率**：methodology 只手抄了花蓮/臺東/屏東等幾縣；其餘須由 `115年…原住民概況.pdf`（或戶政司開放資料 CSV）讀全 22 縣市的「占縣市人口比率」落成 `ethnic_base.csv`。
2. **客家校準係數 `k`**：預設 **0.55**（單一認同目標 10.9%），可選 0.71（目標 14%）——是 config 參數，資料集說明須載明採用值。
3. 把 2024 屆選舉舊檔（`taiwan_political`/2024 那批）移到 `old_output/` 或改名 `_2024備用`，避免 loader 抓錯年份。

**前處理步驟（資料對齊，寫成一次性 `scripts/prep_taiwan_sources.py`）**：
把異質來源統一清洗成 region-keyed CSV —
(a) `人口分布.xlsx` 多區塊 sheet＋全形空格縣市名（`臺 北 市`）正規化；
(b) `t083.xlsx` P01 取 4 類算各縣市占比；
(c) 選舉 `.xls`（總統 A05-2＋不分區立委 A05-6）彙總成「縣市/區 × 政黨」得票；
(d) 族群依 methodology §4 四步驟（原民法定→客家×k→外省眷村係數→閩南殘差）算各縣市四族比例。
產物落 `data/derived/regions/{regions,census_*,election_*,housing,ethnic_base}.csv`，供各 stage 的 loader 讀取。

---

## 驗證
1. **回歸護欄**：`PERSONA_PROFILE=taipei python scripts/run_pipeline.py` 須產出與現行**逐位元組相同**的
   台北 3000 人（profile 重構不得改變台北統計輸出 — 對齊 [pipeline_common.py:9](scripts/pipeline_common.py#L9) 的原則）。
2. **全台跑通**：`PERSONA_PROFILE=taiwan python scripts/run_pipeline.py` 產出 3000×25 交付檔。
3. **台北重用檢核**（§6）：台北市那 ~314 列須是 Taipei 3000 的**子集**（每列在來源檔找得到、欄值未被改動）；台北佔比 ≈ 10.5%、總列數 = 3000。
4. **分布健檢**（主要針對「台北以外」生成列）：
   - 各縣市人數 ≈ 內政部人口占比（誤差 < 1–2%）；
   - 政黨傾向縣市別 ≈ 2020 CEC 縣市得票（南北差應浮現）；
   - 族群（依 methodology §7）：全國加權回算 閩≈76–78%/客≈11–14%/外≈10%/原≈2.7%；花蓮原民≈30.3%、臺東≈38.1%；客家梯度 新竹縣>苗栗>桃園>花蓮；每縣四族和=1 無負值。
5. 沿用 v2 內建的 5 張驗證 sheet（年齡/性別/教育/婚姻校驗）逐縣市抽查。
