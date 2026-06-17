# 全台灣 3000 人 Persona — 擴增計畫

## Context

現行 pipeline（13 階段 + finalize）100% 鎖定台北市：地理單位是寫死的 12 行政區清單
（[pipeline_common.py:114](../scripts/pipeline_common.py#L114)），census/選舉檔皆為台北專屬，
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

## 架構擴增設計（RegionProfile）

### 1. 地理模型 — 取代寫死的 `DISTRICTS`
- 新增單一真相來源 `data/raw/regions/regions.csv`：每列一個地理單位
  （欄位：`region_code, region_name, parent_county, level(county|district), pop_15plus`）。
  - 22 縣市；六都展開為行政區，其餘 16 縣市保持縣市層級。
  - 哪些都會細分由 profile 設定（預設六都，可調）。
- 在 [pipeline_common.py](../scripts/pipeline_common.py) 以此檔建出 `REGIONS`、`region_pop_weight()`，
  **取代** `DISTRICTS`（[pipeline_common.py:114](../scripts/pipeline_common.py#L114)）。
- 保留 `DISTRICTS = [台北 12 區]` 作為 `profile=taipei` 的 region 子集，**現有台北輸出不受影響**。

### 2. Profile 設定 — 取代散落的 Taipei 常數
新增 `scripts/region_profile.py`，定義 `PROFILE`（由環境變數/CLI 選 `taipei` | `taiwan`）：
- `regions`：本 profile 的地理單位清單（從 `regions.csv` 篩）。
- `census_loader` / `election_loader`：依 region 回傳該單位的 census/選舉分布
  （台北 profile = 現行 `.ods` row-index 路徑；全台 profile = 縣市別新檔）。
- `param_tables`：族群/宗親/產業/婚姻等**參數表改成資料檔**
  （`data/raw/regions/{ethnic_base,clan_tier,industry_mult,marriage_rate}.csv`，以 region 或 region_tier 為 key），
  取代 [taipei_group.py:30](../scripts/taipei_group.py#L30)、[taipei_clan.py:30](../scripts/taipei_clan.py#L30)、
  [taipei_industry.py:57](../scripts/taipei_industry.py#L57)、[taipei_persona_v2.py:160](../scripts/taipei_persona_v2.py#L160) 的寫死 dict。

### 3. 命名/N 參數化 — 取代 `taipei_personas_3000_*`
- 在 [pipeline_common.py:60](../scripts/pipeline_common.py#L60) 把 `STAGE_FILES` 改成由
  `DATASET_PREFIX`（如 `taiwan_personas_3000`）+ stage key 動態組出；`N_TOTAL` 由 profile 提供。
- `FINAL_DIR`（[pipeline_common.py:28](../scripts/pipeline_common.py#L28)）改成 `final/{profile}/`。
- 不必逐一改檔名字串，集中在工廠函式即可。

### 4. 重點階段改動
- **`taipei_persona_v2.py`（最大改動）**：把 `DIST_AGE_ROW` row-index hack
  （[taipei_persona_v2.py:62](../scripts/taipei_persona_v2.py#L62)）與 `age15plus_pop`/`marry_2024`
  （[L160](../scripts/taipei_persona_v2.py#L160)）改成走 `census_loader`（以 region 為 key 的鍵值查表）。
  抽樣 `n_total=3000`（[L396](../scripts/taipei_persona_v2.py#L396)）改成依 `REGIONS` 的 `pop_weight` 分配。
  `_pool()`（[L357](../scripts/taipei_persona_v2.py#L357)）把寫死 `臺北市` 換成 persona 自身縣市
  — 既有 `COUNTY_CODE`/`REGION_GROUP`（[L311](../scripts/taipei_persona_v2.py#L311)）正是為此預留的全國結構。
- **`taipei_splitTicket.py`**：`PRES_FILE`/`PARTY_FILE`（[taipei_splitTicket.py:16](../scripts/taipei_splitTicket.py#L16)）
  改成 `election_loader` 依縣市/區取檔。
- **`taipei_group.py` / `taipei_clan.py`**：乘數 dict → `param_tables` 的 CSV 查表（區域級）。
- **`taipei_industry.py` / `taipei_income.py`**：移除台北 multiplier/×1.35，改吃縣市別真實資料（資料已全國）。
- **理論/衍生階段（value/topic/speakingStyle 之衍生部分/political_events）**：**0 改動**。

### 5. Runner — 幾乎不動
[run_pipeline.py](../scripts/run_pipeline.py) 階段清單不變；加一個 `--profile` 參數透傳給各子行程
（環境變數 `PERSONA_PROFILE`），fail-fast 與 subprocess 隔離邏輯沿用。

---

## 需蒐集的全國資料清單（落地到 `data/raw/`）
1. **戶政司/主計總處 縣市別** 性別×年齡×教育×婚姻 分布表（取代台北 `113_*.ods`）。
2. **CEC 2020 全台** 總統 + 不分區立委 縣市/區得票（取代台北單檔；六都需到行政區層級）。
3. **109 普查 縣市別** 住宅自有/租屋率（普查本為全國，抽縣市欄）。
4. **客委會全國客家率 + 原民會 縣市別原民人口率**（族群區域基準）。
5. 既有可直接升級（已全國，無需外找）：`表7 縣市別薪資`、`industry.xls`、`Basic.xlsx`、
   `Political.xlsx`、`taiwan_political_events.xlsx`。

---

## 驗證
1. **回歸護欄**：`PERSONA_PROFILE=taipei python scripts/run_pipeline.py` 須產出與現行**逐位元組相同**的
   台北 3000 人（profile 重構不得改變台北統計輸出 — 對齊 [pipeline_common.py:9](../scripts/pipeline_common.py#L9) 的原則）。
2. **全台跑通**：`PERSONA_PROFILE=taiwan python scripts/run_pipeline.py` 產出 3000×25 交付檔。
3. **分布健檢**：
   - 各縣市人數 ≈ 內政部人口占比（誤差 < 1–2%）；
   - 政黨傾向縣市別 ≈ 2020 CEC 縣市得票（南北差應浮現）；
   - 族群：客家在桃竹苗↑、原民在東部/山地↑（對照客委會/原民會官方比例）。
4. 沿用 v2 內建的 5 張驗證 sheet（年齡/性別/教育/婚姻校驗）逐縣市抽查。
