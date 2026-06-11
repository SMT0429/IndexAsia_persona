# 關注議題欄位建立方法論技術文件

**專案**：Taipei Persona Dataset（N=3,000）  
**欄位名稱**：關注議題  
**文件版本**：v1.2  
**建立日期**：2026-06-09  
**修訂日期**：2026-06-10（v1.1 修正錯誤引用、世代標籤對齊、script 補完世代邏輯；v1.2 對齊腳本實作：開放關懷型〔原誤植「進步關懷型」〕、年齡組 15–24歲〔原 18–24歲〕、政黨標籤「國民黨」〔原「中國國民黨」〕、收入標籤 4萬以下／15~25萬／25萬以上〔原 未滿2萬／2~4萬／15萬以上〕）

---

## 目錄

1. [欄位定義與範圍](#1-欄位定義與範圍)
2. [議題分類框架](#2-議題分類框架)
3. [理論基礎](#3-理論基礎)
4. [賦值邏輯](#4-賦值邏輯)
5. [各變數對應議題的方向性依據](#5-各變數對應議題的方向性依據)
6. [資料來源與參考文獻](#6-資料來源與參考文獻)
7. [引用限制聲明](#7-引用限制聲明)

---

## 1. 欄位定義與範圍

### 定義

「關注議題」指 persona 在日常生活與政治參與中，**主動留意、具備立場或願意討論**的公共政策或社會議題。此欄位不代表 persona 對議題的支持或反對方向，而是議題的**顯著性（salience）**。

### 賦值規格

- 每位 persona 賦予 **1–3 個議題標籤**（字串 list）
- 議題標籤取自固定的 8 類議題集合（見第 2 節）
- 賦值採**機率加權抽樣**，保留個體內部差異

### 欄位在整體建模中的位置

```
人口結構層（A–L欄）政府公開資料
    ↓
社會文化層（M–S欄）歷史印記、產業、宗教、族群、投票傾向
    ↓
心理價值層（T–W欄）Schwartz CO/ST 分數、社會價值觀主類型
    ↓
【議題關注層】← 本欄位（由上三層交互決定）
```

---

## 2. 議題分類框架

採用 **8 大類議題**，參照中研院臺灣社會變遷基本調查（TSCS）社會問題組問卷及 TEDS 議題立場模組的分類邏輯建立。

| 代號 | 議題類別 | 代表子議題 | 台灣近年政策爭議對應 |
|------|---------|-----------|-------------------|
| **ECO** | 經濟 / 就業 | 薪資停滯、通貨膨脹、失業、產業轉型 | 基本工資調升、科技業人才荒 |
| **HSG** | 居住 / 房價 | 房價高漲、囤房稅、社會住宅、租屋市場 | 打炒房條例、社宅興建 |
| **XS** | 兩岸 / 國安 | 兩岸關係、國防預算、主權認同 | 兵役延長、對中政策 |
| **ENV** | 環境 / 能源 | 空汙、核電存廢、淨零排放、氣候變遷 | 能源轉型、核電公投 |
| **WEL** | 社福 / 長照 | 老人照護、健保財務、年金改革、少子化 | 長照 2.0、健保費率 |
| **EDU** | 教育 / 人才 | 教育改革、技職教育、少子化衝擊、AI 教育 | 108 課綱爭議 |
| **SOC** | 社會進步 | 婚姻平權、性別平等、移工政策、身心障礙 | 同婚立法後續、外籍移工管理 |
| **GOV** | 政治 / 治理 | 司法改革、反腐、媒體自由、選制改革 | NCC 爭議、國會改革法案 |

---

## 3. 理論基礎

### 3.1 後物質主義價值理論（Post-Materialism）

**來源**：Ronald Inglehart (1977) *The Silent Revolution*；(1997) *Modernization and Postmodernization*

**核心命題**：個人在成長期的「物質匱乏 vs. 充裕」經驗，決定其成年後的價值取向——

- **物質主義者**：優先追求經濟安全與人身安全 → 關注 **ECO、WEL、XS**
- **後物質主義者**：優先追求自我表達與生活品質 → 關注 **ENV、SOC、GOV**

Inglehart (1997) 的跨國比較資料（涵蓋東亞社會）顯示：教育程度與後物質主義傾向呈正相關；年齡越高（在物質匱乏時期成長）則物質主義傾向越強。台灣的具體校準數值建議直接取用 **ISSP（International Social Survey Programme）台灣模組**或 **TSCS 第七期政治組**的交叉分析結果，而非援引個別課程研究的副產品。

> ⚠️ **已移除**：前版引用 Chen et al. (2019, *Journal of Futures Studies*) 佐證「台灣後物質主義轉型落後西歐一個世代」。該文為環境教育課程的參與式行動研究，原文無此跨國比較結論，引用不當，已刪除。

**操作化變數**（對應本資料集欄位）：

| 理論變數 | 操作化欄位 | 方向 |
|---------|-----------|------|
| 成長期物質條件 | `年齡組` × `月收入` | 老/低收入 → 物質主義 |
| 教育資本 | `教育程度` | 高教育 → 後物質主義 |
| 都市化 | `居住地`（行政區） | 市中心 → 後物質主義傾向 |

---

### 3.2 生命歷程理論（Life Course Theory）

**來源**：Elder, G. H. (1994). "Time, Human Agency, and Social Change." *Social Psychology Quarterly*；Jennings, M. K. & Niemi, R. G. (1981) *Generations and Politics*

**核心命題**：個人在不同人生階段面臨不同的「切身性議題」，由生命事件驅動議題關注。

| 年齡組（本資料集） | 人生階段 | 切身議題 | 推論依據 |
|-----------------|---------|---------|---------|
| 15–24歲 | 求學 / 初入職場 | ECO、HSG、EDU | 就業焦慮、居住可及性（生命歷程理論）|
| 25–34歲 | 成家立業 | HSG、ECO、EDU | 購屋壓力、育兒成本（內政部住宅狀況調查購屋年齡分布）|
| 35–44歲 | 事業高峰 | ECO、GOV、ENV | 納稅人意識、政策影響感知（理論推論）|
| 45–54歲 | 夾心世代 | WEL、ECO、XS | 照顧老父母 + 養育子女（衛福部長照需求評估）|
| 55–64歲 | 退休前期 | WEL、XS、ECO | 年金保障、兩岸穩定性（理論推論）|
| 65歲以上 | 退休期 | WEL、XS | 健保/長照依賴度最高（衛福部長照需求評估）|

---

### 3.3 媒體議程設定（Agenda-Setting）

**來源**：McCombs, M. & Shaw, D. (1972). "The Agenda-Setting Function of Mass Media." *Public Opinion Quarterly*

**核心命題**：媒體不告訴民眾「怎麼想」，但決定民眾「想什麼」。

**本資料集操作化**（對應 `媒體習慣` 欄位）：

下表的議題傾向為**基於議程設定理論的推論性對映**，反映各平台的內容特性（內容類型、年齡層用戶結構），而非來自直接測量「媒體接觸→特定議題關注」的調查數據。如需精確校準，建議取用 Reuters Institute Digital News Report Taiwan 的用戶特徵數據後另行迴歸分析。

| 媒體管道 | 議題傾向（理論推論） | 推論根據 |
|---------|-------------------|---------|
| 電視新聞 | XS、GOV、ECO | 硬新聞比例高、老年用戶為主（NCC 媒體調查各年齡層收視率）|
| LINE | XS、WEL | 封閉群組、謠言傳播（台灣事實查核中心：LINE 為最主要謠言媒介）|
| Facebook | GOV、SOC、ECO | 同溫層效應（Reuters Institute DNR Taiwan 2023 社群媒體用途）|
| YouTube | ENV、SOC、EDU | 長形內容、相對多元（Reuters Institute DNR Taiwan 2023）|
| Instagram | SOC、HSG | 用戶年輕化（Reuters Institute DNR Taiwan 2023 年齡層分布）|
| 紙本報紙 | GOV、ECO | 菁英取向（NCC 媒體使用調查教育程度交叉）|

> ⚠️ **已移除**：前版在此表的「實證根據」欄引用「Meta 台灣用戶行為報告」（查無此公開報告）。Instagram 的對映改標為「理論推論」。

---

### 3.4 政治社會化理論（Political Socialization）

**來源**：Mannheim, K. (1952). "The Problem of Generations"；Greenstein, F. (1965) *Children and Politics*

**核心命題**：個人在青少年至成年初期（約 14–24 歲）所經歷的重大政治事件，形成持久的政治議題框架。

**本資料集操作化**（對應 `政治與歷史印記_世代` 欄位，以資料集實際標籤為準）：

| 世代標籤（資料集實際值）| 形成期政治環境 | 議題敏感傾向（理論推論）|
|---------------------|-------------|----------------------|
| 威權 / 解嚴世代 | 白色恐怖、戒嚴、解嚴 | GOV（民主價值）、XS（認同複雜性）|
| 本土化世代 | 台灣省長直選、民進黨成立、經濟奇蹟 | XS（台灣主體意識）、ECO |
| 民主轉型世代 | 首次政黨輪替、SARS、公民身份確立 | GOV、XS、ECO |
| 公民運動世代 | 太陽花學運、洪仲丘案、九合一大勝 | GOV（改革訴求）、SOC |
| 社群網路 / 抗中保台世代 | 香港 2019、COVID-19、蔡英文 817 萬票 | XS（主權強化）、GOV |
| AI 與短影音世代 | 賴清德當選、AI 科技浪潮、立院藍白衝突 | ECO（AI 就業焦慮）、GOV、HSG |

> ⚠️ **已修正**：前版使用「民主鞏固世代」、「政治冷感世代」等標籤，與資料集 M 欄實際世代值不符，現已對齊。

---

### 3.5 Schwartz 基本價值觀理論（本資料集內部一致性橋接）

**來源**：Schwartz, S. H. (1992). "Universals in the Content and Structure of Values." *Advances in Experimental Social Psychology, Vol. 25*

**目的**：與現有 `社會價值觀_主類型` 欄位保持理論一致，確保「關注議題」與「核心動機」之間的內在邏輯不矛盾。

| 本資料集主類型 | Schwartz 高階類型 | 議題重心（理論推論）|
|-------------|-----------------|-------------------|
| 傳統守望型 | Conservation（傳統、順從、安全） | WEL、XS、ECO |
| 秩序菁英型 | Self-Enhancement（權力、成就） | GOV、ECO、XS |
| 自主競爭型 | Openness to Change（自主、刺激） | EDU、ECO、GOV |
| 開放關懷型 | Self-Transcendence（博愛、普世） | ENV、SOC、WEL |

> **一致性原則**：賦予 persona 的議題，其背後動機應與 `社會價值觀_核心動機` 欄位的描述相容。若出現矛盾（如「傳統守望型」被賦予 SOC 議題），需有額外的變數（如高教育或特定媒體習慣）作為覆蓋條件。

---

## 4. 賦值邏輯

### 4.1 機率加權模型

每個 persona 對每類議題計算一個加權得分，從得分分布中隨機抽取 1–3 個議題。**boost 乘數為理論性估計值，非來自實際調查的精確係數**，建議取得 TEDS/TSCS 微數據後以 logistic regression 重新校準。

```python
import pandas as pd
import numpy as np

ISSUES = ['ECO', 'HSG', 'XS', 'ENV', 'WEL', 'EDU', 'SOC', 'GOV']

def compute_issue_weights(row):
    """
    根據 persona 屬性計算各議題的基礎權重。
    boost 乘數為理論推論值，非調查實測係數。
    """
    w = {issue: 1.0 for issue in ISSUES}

    # ── 年齡組效果（生命歷程理論）──
    age_boosts = {
        '15–24歲': {'HSG': 1.5, 'EDU': 1.5, 'ECO': 1.3, 'SOC': 1.2},
        '25–34歲': {'HSG': 2.0, 'ECO': 1.5, 'EDU': 1.3},
        '35–44歲': {'ECO': 1.5, 'GOV': 1.3, 'ENV': 1.2},
        '45–54歲': {'WEL': 1.8, 'ECO': 1.4, 'XS': 1.3},
        '55–64歲': {'WEL': 1.8, 'XS': 1.5, 'ECO': 1.3},
        '65歲以上': {'WEL': 2.0, 'XS': 1.8, 'ECO': 1.2},
    }
    for issue, boost in age_boosts.get(row['年齡組'], {}).items():
        w[issue] *= boost

    # ── 教育程度效果（後物質主義理論，Inglehart 1997）──
    edu = row['教育程度']
    if edu in ['碩士以上', '大學']:
        for issue in ['ENV', 'SOC', 'GOV']:
            w[issue] *= 1.5
    elif edu in ['國中以下', '小學以下']:
        for issue in ['ECO', 'WEL', 'XS']:
            w[issue] *= 1.4

    # ── 收入效果（物質主義梯度，Inglehart 1997）──
    income = str(row['月收入區間'])
    high_income = ['15~25萬', '25萬以上', '10~15萬']
    low_income  = ['4萬以下']
    if any(h in income for h in high_income):
        for issue in ['ENV', 'GOV', 'SOC']:
            w[issue] *= 1.3
    elif any(l in income for l in low_income):
        for issue in ['ECO', 'WEL']:
            w[issue] *= 1.5

    # ── 政黨傾向效果（理論推論；方向參照 TEDS 議題立場問卷）──
    # 注意：TEDS 問卷題號未公開對應，以下為方向性對映，非題目直引
    party_boosts = {
        '民進黨':   {'XS': 1.6, 'GOV': 1.3, 'SOC': 1.3},
        '國民黨':     {'XS': 1.4, 'ECO': 1.3, 'WEL': 1.2},
        '台灣民眾黨': {'GOV': 1.5, 'ECO': 1.4, 'HSG': 1.3},
        '時代力量':  {'GOV': 1.6, 'SOC': 1.5, 'ENV': 1.3},
    }
    for issue, boost in party_boosts.get(row['政黨傾向'], {}).items():
        w[issue] *= boost

    # ── 社會價值觀主類型效果（Schwartz 1992 橋接）──
    value_boosts = {
        '傳統守望型': {'WEL': 1.4, 'XS': 1.3, 'ECO': 1.2},
        '秩序菁英型': {'GOV': 1.4, 'ECO': 1.3, 'XS': 1.2},
        '自主競爭型': {'EDU': 1.4, 'ECO': 1.3, 'GOV': 1.2},
        '開放關懷型': {'ENV': 1.4, 'SOC': 1.3, 'WEL': 1.2},
    }
    for issue, boost in value_boosts.get(row['社會價值觀_主類型'], {}).items():
        w[issue] *= boost

    # ── 媒體習慣效果（議程設定理論；為推論性對映）──
    media = str(row['媒體習慣'])
    if 'YouTube' in media:
        for issue in ['ENV', 'SOC', 'EDU']:
            w[issue] *= 1.2
    if 'LINE' in media:
        for issue in ['XS', 'WEL']:
            w[issue] *= 1.2
    if 'Instagram' in media:
        for issue in ['SOC', 'HSG']:
            w[issue] *= 1.2

    # ── 世代效果（政治社會化理論，Mannheim 1952）──
    # 使用資料集 M 欄實際世代標籤
    generation_boosts = {
        '威權/解嚴世代':        {'GOV': 1.4, 'XS': 1.3},
        '本土化世代':           {'XS': 1.4, 'ECO': 1.3},
        '民主轉型世代':         {'GOV': 1.3, 'XS': 1.2, 'ECO': 1.2},
        '公民運動世代':         {'GOV': 1.5, 'SOC': 1.3},
        '社群網路/抗中保台世代': {'XS': 1.5, 'GOV': 1.3},
        'AI與短影音世代':       {'ECO': 1.4, 'GOV': 1.2, 'HSG': 1.3},
    }
    for issue, boost in generation_boosts.get(row['政治與歷史印記_世代'], {}).items():
        w[issue] *= boost

    return w


def assign_issues(row, n_issues_range=(1, 3)):
    w = compute_issue_weights(row)
    issues = list(w.keys())
    weights = np.array([w[i] for i in issues])
    weights = weights / weights.sum()
    n = np.random.randint(n_issues_range[0], n_issues_range[1] + 1)
    chosen = np.random.choice(issues, size=n, replace=False, p=weights)
    return list(chosen)
```

### 4.2 使用方式

```python
df = pd.read_excel('taipei_personas_3000_value.xlsx')
np.random.seed(42)
df['關注議題'] = df.apply(assign_issues, axis=1)
df.to_excel('taipei_personas_3000_with_issues.xlsx', index=False)
```

### 4.3 分布驗證（建議執行）

```python
from collections import Counter

all_issues = [issue for sublist in df['關注議題'] for issue in sublist]
issue_counts = Counter(all_issues)

print("議題分布：")
for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
    pct = count / len(df) * 100
    print(f"  {issue}: {count} ({pct:.1f}%)")
```

**參考分布區間**（理論推論估計，非調查直接測量值；建議取 TEDS/TSCS 微數據校準後替換）：

| 議題 | 參考覆蓋率 | 推論依據 |
|-----|----------|---------|
| ECO | 45–60% | 台灣歷年民調中「最重要問題」高頻出現經濟相關 |
| WEL | 30–45% | 高齡化社會；65歲以上人口佔比持續提升 |
| XS | 30–50% | 兩岸議題高政黨極化，跨越藍綠均有關注但立場相反 |
| HSG | 25–40% | 近年房價議題媒體曝光度高，年輕世代切身 |
| GOV | 20–35% | 太陽花後公民意識；2024 立院改革法案爭議 |
| ENV | 15–30% | 核電公投、能源轉型；後物質主義轉型中 |
| EDU | 15–25% | 少子化、108 課綱爭議 |
| SOC | 10–20% | 同婚立法後逐步擴大關注，但整體仍屬次要議題 |

---

## 5. 各變數對應議題的方向性依據

以下為各驅動變數的**方向性對映說明**，標示每項依據的性質（直接引用 / 理論推論 / 待校準）。

### 5.1 年齡組 × 議題

| 年齡組 | 最高關注 | 依據性質 |
|-------|---------|---------|
| 15–24歲 | HSG、EDU | 生命歷程理論推論 |
| 25–34歲 | HSG、ECO | 內政部住宅狀況調查（購屋年齡分布）直接引用 |
| 35–44歲 | ECO、GOV | 生命歷程理論推論 |
| 45–54歲 | WEL、ECO | 衛福部長照需求評估（照顧者年齡分布）直接引用 |
| 55–64歲 | WEL、XS | 生命歷程理論推論 |
| 65歲以上 | WEL、XS | 衛福部長照需求評估直接引用（需求率最高組）|

### 5.2 教育程度 × 議題（Inglehart 後物質主義，跨國資料方向一致）

| 教育程度 | 傾向 | 依據 |
|---------|-----|------|
| 碩士以上 | ENV、SOC、GOV | Inglehart (1997) 跨國比較；ISSP 台灣模組（方向一致，無直接比率）|
| 國中以下 | ECO、WEL | Inglehart (1997) 物質主義梯度 |

### 5.3 政黨傾向 × 議題

方向性對映參照 TEDS 歷次選舉後調查中的黨支持者議題立場分布（可取得微數據後以交叉分析驗證）。**前版所標示之 Q31–Q45 / Q46 題組代號查無公開對應題本，已全數移除。**

| 政黨傾向 | 高關注議題（方向性）| 建議校準方式 |
|---------|-----------------|------------|
| 民進黨 | XS（主權維護）、GOV、SOC | TEDS 微數據交叉分析 |
| 國民黨 | XS（交流穩定）、ECO | TEDS 微數據交叉分析 |
| 台灣民眾黨 | GOV（反腐）、ECO、HSG | TEDS 2024 新興政黨選民研究 |
| 無 / 中立 | ECO、WEL | 切身性優先（生命歷程理論推論）|

---

## 6. 資料來源與參考文獻

### 6.1 政府公開資料集

| 資料集 | 機構 | 用途 | 網址 |
|-------|------|------|------|
| 台灣選舉與民主化調查（TEDS）| 科技部 / 政大選研中心 | 各人口群議題立場方向 | https://teds.nccu.edu.tw/ |
| 臺灣社會變遷基本調查（TSCS）| 中研院社會學所 | 社會問題關注分布 | https://www.ios.sinica.edu.tw/ |
| 內政統計年報 | 內政部統計處 | 人口結構、住宅 | https://statis.moi.gov.tw/ |
| 住宅狀況調查 | 內政部不動產資訊平台 | 購屋年齡分布 | https://pip.moi.gov.tw/ |
| 人力資源調查統計 | 主計總處 | 就業、薪資、教育 × 收入 | https://www.dgbas.gov.tw/ |
| 長照需求評估報告 | 衛生福利部 | 65歲以上 WEL 依賴度 | https://dep.mohw.gov.tw/ |
| 2025 台灣民心動向調查 | 遠見研究調查 | XS / 國安議題民意基準 | https://gvsrc.cwgv.com.tw/ |
| Digital News Report Taiwan | Reuters Institute / Oxford | 媒體管道用戶年齡特徵 | https://reutersinstitute.politics.ox.ac.uk/ |
| 媒體使用行為及滿意度調查 | NCC 國家通訊傳播委員會 | 各年齡層媒體接觸率 | https://www.ncc.gov.tw/ |

### 6.2 學術文獻

```
Inglehart, R. (1977). The Silent Revolution: Changing Values and Political Styles 
  Among Western Publics. Princeton University Press.

Inglehart, R. (1997). Modernization and Postmodernization: Cultural, Economic, 
  and Political Change in 43 Societies. Princeton University Press.

Schwartz, S. H. (1992). Universals in the content and structure of values: 
  Theoretical advances and empirical tests in 20 countries. 
  Advances in Experimental Social Psychology, 25, 1–65.

McCombs, M., & Shaw, D. (1972). The agenda-setting function of mass media. 
  Public Opinion Quarterly, 36(2), 176–187.

Elder, G. H. (1994). Time, human agency, and social change: Perspectives on 
  the life course. Social Psychology Quarterly, 57(1), 4–15.

Jennings, M. K., & Niemi, R. G. (1981). Generations and Politics: A Panel 
  Study of Young Adults and Their Parents. Princeton University Press.

Mannheim, K. (1952). The problem of generations. In P. Kecskemeti (Ed.), 
  Essays on the Sociology of Knowledge (pp. 276–320). Routledge.

Dalton, R. J. (2014). Citizen Politics: Public Opinion and Political Parties in 
  Advanced Industrial Democracies (6th ed.). CQ Press.

Zaller, J. (1992). The Nature and Origins of Mass Opinion. Cambridge University Press.
```

---

## 7. 引用限制聲明

本文件明確區分三類依據，避免混淆精確度：

| 類型 | 說明 | 在本文件中的標示 |
|-----|------|----------------|
| **直接引用** | 具體資料集或文獻中有明確的分布數值或交叉分析結果 | 標明資料集名稱與查詢方式 |
| **理論推論** | 依據已有學術理論的邏輯外推，台灣本土尚無對應數值 | 標注「理論推論」|
| **待校準估計值** | 方向合理但係數未經實際資料驗證的 boost 乘數與覆蓋率區間 | 標注「建議校準」|

**boost 乘數（1.2–2.0）與預期覆蓋率區間均屬「待校準估計值」**，其方向有理論支撐，但數值需以 TEDS 或 TSCS 微數據的實際交叉分析結果替換後，才能作為嚴格的方法論宣稱。

---

## 附錄：欄位一致性驗證清單

- [ ] **傳統守望型** persona 不應大量出現 SOC 議題（除非高教育或特定媒體）
- [ ] **65歲以上** persona 應有 >60% 包含 WEL 議題
- [ ] **月收入 4 萬以下** persona 的 ECO 覆蓋率應顯著高於全體平均
- [ ] **AI 與短影音世代** persona 應有相對高比例的 ECO / HSG（年輕就業世代切身議題）
- [ ] 各議題覆蓋率落在第 4 節參考分布區間內

---

*文件維護：如調整議題分類或 boost 係數，請同步更新版本號與修訂日期。*
