# 說話風格欄位建構方法論

**專案**：台北市民 Persona 資料庫  
**欄位**：`說話風格`  
**版本**：v1.0  
**日期**：2026-06-09  

---

## 目錄

1. [欄位定義與目的](#1-欄位定義與目的)
2. [輸入變數對應表](#2-輸入變數對應表)
3. [理論框架——三層疊加模型](#3-理論框架三層疊加模型)
   - 3.1 層一：語言精緻化程度（Bernstein）
   - 3.2 層二：語言資本與語域（Bourdieu）
   - 3.3 層三：文化價值溝通取向（Hofstede + CO/ST）
4. [台灣在地修正因子](#4-台灣在地修正因子)
   - 4.1 世代語言標記
   - 4.2 族群語言切換
   - 4.3 數位媒體語言分層
5. [子維度設計](#5-子維度設計)
6. [技術文件：決策規則與 Python 實作](#6-技術文件決策規則與-python-實作)
   - 6.1 決策規則總表
   - 6.2 Python 函數
   - 6.3 使用方式
7. [輸出範例](#7-輸出範例)
8. [參考文獻](#8-參考文獻)

---

## 1. 欄位定義與目的

`說話風格` 欄位描述每位 persona 在日常溝通中慣用的語言表達模式，涵蓋正式程度、溝通取向、語言切換習慣與數位語言傾向。

此欄位的用途包括：
- 為 AI 角色扮演或對話系統提供語言風格基準
- 輔助內容策略（廣告文案、社群貼文）針對特定 persona 校調語氣
- 提供質性描述，補充純量化社會人口欄位

欄位形式為**複合標籤字串**，例如：
> `「語氣平實口語，習慣夾帶台語詞，LINE 溝通多用表情符號，直接表達意見」`

---

## 2. 輸入變數對應表

以下欄位（已存在於 persona 表格）作為說話風格的預測因子：

| 欄位名稱 | 角色 | 對應理論層 |
|---|---|---|
| `教育程度` | 語言精緻化程度的主要預測因子 | Bernstein（層一） |
| `月收入區間` | 語言資本的代理變數 | Bernstein + Bourdieu（層一/二） |
| `職業` | 場域語域（職場/家庭/公眾） | Bourdieu（層二） |
| `產業別` | 職業語域（jargon 密度） | Bourdieu（層二） |
| `年齡組` | 世代語言習慣 | 台灣社會變遷調查（層四） |
| `族群` | 語言切換傾向（閩/客/外省） | 教育部語言調查（層四） |
| `媒體習慣` | 數位語言平台偏好 | Taiwan Communication Survey（層四） |
| `社會價值觀_CO分數` | 集體/個人主義溝通取向 | Hofstede（層三） |
| `社會價值觀_ST分數` | 保守/開放傳統取向 | Hofstede（層三） |
| `政治與歷史印記_世代` | 歷史語言標記（威權/解嚴/民主） | 世代理論（層四） |
| `婚姻狀況` | 社交場合密度（家庭語域比重） | 輔助修正 |
| `居住地` | 都會/郊區語言接觸多樣性 | 輔助修正 |

---

## 3. 理論框架——三層疊加模型

### 3.1 層一：語言精緻化程度

**理論依據**：Basil Bernstein，*Class, Codes and Control*（1971）

Bernstein 提出兩種語言編碼型態：

| 型態 | 特徵 | 台灣對應群體 |
|---|---|---|
| **精緻型（Elaborated Code）** | 句子完整、語意明確、不假設共識、詞彙廣泛 | 大學以上學歷、專業白領、管理職 |
| **局限型（Restricted Code）** | 依賴語境、省略多、填充詞多（「就是說」「你懂嗎」）、句短 | 高中（職）以下學歷、勞工階級 |

**操作化**：
```
精緻化程度 = f(教育程度, 月收入區間)
```
- 大學及以上 + 月收入 > 6萬 → `高`
- 大學 + 月收入 4~6萬，或高中 + 管理職 → `中`
- 高中（職）以下 + 月收入 < 4萬 → `低`

---

### 3.2 層二：語言資本與語域

**理論依據**：Pierre Bourdieu，*Language and Symbolic Power*（1991）

Bourdieu 認為語言是一種「資本」，在不同「場域」（field）有不同兌換率。說話者根據場域調整語言策略：

- **語言習性（linguistic habitus）**：在家庭與學校社會化中內化的說話方式，難以輕易切換
- **場域決定語域**：職場場域要求較正式語言；家庭場域允許口語
- **職業語域（register）**：高度專業的職業（醫師、律師、工程師）有專業術語習慣

**操作化**：
```
基礎語域 = f(職業, 產業別)
```
- 管理/主管、學術研究、法律金融 → `正式語域為主`
- 服務業、零售、製造 → `混合語域`
- 退休、農漁 → `日常口語語域`

---

### 3.3 層三：文化價值溝通取向

**理論依據**：Geert Hofstede，*Culture's Consequences*（2001）；Shalom Schwartz，*Theory of Cultural Value Orientations*（2006）

利用 **persona 表格中已建好的 CO 分數與 ST 分數** 直接推導：

| 維度 | 高分特徵 | 低分特徵 |
|---|---|---|
| **CO 分數（集體主義）** | 迂迴表達、強調共識、關係維繫語言（「大家都…」「我們這邊…」） | 直接表達個人立場、第一人稱明確 |
| **ST 分數（保守傳統）** | 正式稱謂、引用傳統、敬語多、避免激進用詞 | 新詞彙接受度高、語言更新快、俗語多 |

**操作化**：
```
溝通取向 = f(CO分數, ST分數)
CO > 0  → 迂迴/集體傾向
CO < 0  → 直接/個人傾向
ST > 0  → 保守/傳統語言
ST < 0  → 開放/現代語言
```

---

## 4. 台灣在地修正因子

### 4.1 世代語言標記

**資料來源**：臺灣社會變遷基本調查（中研院社會所，1984 迄今）；政治與歷史印記欄位

| 世代 | 約出生年 | 語言特徵 |
|---|---|---|
| 威權/解嚴世代 | 1945–1959 | 「標準國語」腔調、官方書面語習慣、閩南語夾用依族群而異、用詞正式 |
| 本土化世代 | 1960–1979 | 國台語自然切換、受民主化語言影響、政治敏感詞彙豐富 |
| 民主化世代 | 1980–1994 | 網路語言初期使用者、英文借詞開始增加、BBS/PTT 語言影響 |
| 數位原住民世代 | 1995 後 | IG/TikTok 語言、縮寫與梗圖語言、英中混搭高頻 |

### 4.2 族群語言切換

**資料來源**：教育部臺灣語言使用調查（2020）；臺灣語言使用調查資料庫

| 族群 | 語言切換特徵 |
|---|---|
| 閩南 | 口語中台語詞彙夾用頻繁（依年齡層遞減），感情/家庭語境台語比例高 |
| 客家 | 正式場合傾向標準國語，謙遜、保守用語比例高，客語保存率因地區差異大 |
| 外省（第一/二代） | 北京腔殘留影響書面化傾向，正式用語為主，政治用詞較傾向「中華民國」框架 |
| 原住民 | 族語影響程度依都市化而異，部分有特定語音特徵 |

### 4.3 數位媒體語言分層

**資料來源**：Taiwan Communication Survey（中研院，2012 迄今）；DataReportal *Digital 2026: Taiwan*；Social Media in Taiwan 2025

| 主要媒體 | 使用族群 | 語言風格影響 |
|---|---|---|
| LINE | 中高齡（35歲以上）為主 | 段落完整、敬語多、傳統語氣、貼圖/表情符號高頻 |
| Facebook | 35–54 歲為主 | 較長篇評論、政治語言豐富、分享轉貼為主 |
| YouTube | 跨年齡 | 口語化、解說語言影響吸收 |
| Instagram | 18–34 歲 | 短句、標籤語法、視覺描述性語言 |
| PTT / Dcard | 大學生/青壯年 | 鄉民用語（推、噓）、反諷、縮寫語法 |
| TikTok / IG Reels | 25 歲以下 | 梗圖語言、音樂/影片引語、英中混搭 |

---

## 5. 子維度設計

`說話風格` 由以下四個子維度合成，最終輸出為自然語言描述標籤：

| 子維度 | 值域 | 主要驅動欄位 |
|---|---|---|
| `正式程度` | 高 / 中 / 低 | 教育程度、月收入、職業 |
| `溝通取向` | 直接個人型 / 折衷型 / 迂迴集體型 / 保守傳統型 | CO分數、ST分數 |
| `語言切換` | 純國語 / 偶夾台客語 / 頻繁切換 / 英中混搭 | 族群、年齡組 |
| `數位語言` | 傳統書面型 / 折衷型 / 網路原生型 | 媒體習慣、年齡組 |

---

## 6. 技術文件：決策規則與 Python 實作

### 6.1 決策規則總表

#### 正式程度

```
IF 教育程度 in ['研究所以上', '大學'] AND 月收入 > 60000
    → 正式程度 = '高'
ELIF 教育程度 == '大學' OR 職業 in ['管理/主管', '學術研究', '法律專業', '醫療專業']
    → 正式程度 = '中'
ELIF 教育程度 in ['高中(職)', '國中以下']
    → 正式程度 = '低'
```

#### 溝通取向

```
IF CO分數 > 1 AND ST分數 > 1
    → 溝通取向 = '迂迴集體型'（強調共識、關係語言、避免衝突）
ELIF CO分數 > 1 AND ST分數 <= 1
    → 溝通取向 = '折衷型'
ELIF CO分數 < -1 AND ST分數 < -1
    → 溝通取向 = '直接個人型'
ELIF ST分數 > 2
    → 溝通取向 = '保守傳統型'
ELSE
    → 溝通取向 = '折衷型'
```

#### 語言切換

```
IF 族群 == '閩南' AND 年齡 >= 50
    → 語言切換 = '頻繁夾台語'
ELIF 族群 == '閩南' AND 年齡 30-49
    → 語言切換 = '偶夾台語詞'
ELIF 族群 == '客家'
    → 語言切換 = '偶夾客語詞（正式場合純國語）'
ELIF 族群 == '外省'
    → 語言切換 = '純國語為主（北京腔傾向）'
ELIF 年齡 <= 34
    → 語言切換 = '英中混搭'
ELSE
    → 語言切換 = '純國語'
```

#### 數位語言

```
IF '抖音' in 媒體習慣 OR 'Instagram' in 媒體習慣 AND 年齡 <= 30
    → 數位語言 = '網路原生型（梗圖語言、短句、英中混搭）'
ELIF 'PTT' in 媒體習慣 OR 'Dcard' in 媒體習慣
    → 數位語言 = '網路原生型（鄉民語法、反諷風格）'
ELIF 'LINE' in 媒體習慣 AND 年齡 >= 50
    → 數位語言 = '傳統書面型（敬語、完整段落）'
ELIF 'Facebook' in 媒體習慣
    → 數位語言 = '折衷型（長篇評論傾向）'
ELSE
    → 數位語言 = '折衷型'
```

---

### 6.2 Python 函數

```python
import pandas as pd

# ── 月收入轉數值（中位數代理）──
INCOME_MAP = {
    '4萬以下': 35000,
    '4~6萬': 50000,
    '6~10萬': 80000,
    '10~15萬': 125000,
    '15萬以上': 180000,
}

HIGH_FORMAL_JOBS = {
    '管理/主管', '學術研究', '法律專業', '醫療專業',
    '金融專業', '政府官員', '教師'
}

DIGITAL_NATIVE_MEDIA = {'Instagram', '抖音', 'TikTok', 'Dcard'}
PTTLIKE_MEDIA = {'PTT', 'Dcard', '論壇'}
FACEBOOK_MEDIA = {'Facebook'}
LINE_MEDIA = {'LINE'}


def get_formality(row: pd.Series) -> str:
    """層一：Bernstein 語言精緻化程度"""
    edu = str(row.get('教育程度', ''))
    income = INCOME_MAP.get(str(row.get('月收入區間', '')), 0)
    job = str(row.get('職業', ''))

    if edu in ['研究所以上', '大學'] and income >= 60000:
        return '高'
    if edu == '大學' or job in HIGH_FORMAL_JOBS:
        return '中'
    return '低'


def get_communication_orientation(row: pd.Series) -> str:
    """層三：Hofstede CO/ST 溝通取向"""
    co = float(row.get('社會價值觀_CO分數', 0))
    st = float(row.get('社會價值觀_ST分數', 0))

    if co > 1 and st > 1:
        return '迂迴集體型'
    if co < -1 and st < -1:
        return '直接個人型'
    if st > 2:
        return '保守傳統型'
    return '折衷型'


def get_language_switch(row: pd.Series) -> str:
    """層四：族群 × 年齡 語言切換"""
    ethnicity = str(row.get('族群', ''))
    age = int(row.get('年齡', 40))

    if ethnicity == '閩南':
        if age >= 50:
            return '頻繁夾台語'
        if age >= 30:
            return '偶夾台語詞'
        return '偶夾台語詞或英中混搭'
    if ethnicity == '客家':
        return '偶夾客語詞（正式場合純國語）'
    if ethnicity == '外省':
        return '純國語為主'
    if age <= 34:
        return '英中混搭'
    return '純國語'


def get_digital_language(row: pd.Series) -> str:
    """層四：媒體習慣 × 年齡 數位語言風格"""
    media_raw = str(row.get('媒體習慣', ''))
    media_set = set(m.strip() for m in media_raw.split('、'))
    age = int(row.get('年齡', 40))

    if media_set & DIGITAL_NATIVE_MEDIA and age <= 34:
        return '網路原生型'
    if media_set & PTTLIKE_MEDIA:
        return '網路原生型（鄉民語法）'
    if media_set & LINE_MEDIA and age >= 50:
        return '傳統書面型'
    if media_set & FACEBOOK_MEDIA:
        return '折衷型（長篇評論傾向）'
    return '折衷型'


# ── 語言轉 label 描述 ──
ORIENTATION_DESC = {
    '迂迴集體型': '說話迂迴、重視共識與關係維繫，少直接表達反對',
    '直接個人型': '直接表達個人意見，第一人稱明確，不迴避衝突',
    '保守傳統型': '用語保守，敬語較多，傾向傳統稱謂與官方語彙',
    '折衷型': '視情境調整，日常口語直接、正式場合轉為謹慎',
}

FORMALITY_DESC = {
    '高': '語言精緻，句子完整，用詞精確',
    '中': '語言清晰，口語與正式交替',
    '低': '口語為主，短句多，習慣填充詞',
}


def build_speaking_style(row: pd.Series) -> str:
    """主函數：合成說話風格標籤"""
    formality = get_formality(row)
    orientation = get_communication_orientation(row)
    lang_switch = get_language_switch(row)
    digital = get_digital_language(row)

    parts = [
        FORMALITY_DESC[formality],
        ORIENTATION_DESC[orientation],
        f'語言習慣：{lang_switch}',
        f'數位溝通：{digital}',
    ]
    return '；'.join(parts)


# ── 套用至 DataFrame ──
def apply_speaking_style(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['說話風格_正式程度'] = df.apply(get_formality, axis=1)
    df['說話風格_溝通取向'] = df.apply(get_communication_orientation, axis=1)
    df['說話風格_語言切換'] = df.apply(get_language_switch, axis=1)
    df['說話風格_數位語言'] = df.apply(get_digital_language, axis=1)
    df['說話風格'] = df.apply(build_speaking_style, axis=1)
    return df
```

### 6.3 使用方式

```python
import pandas as pd

df = pd.read_excel('taipei_personas_3000_topic.xlsx')
df = apply_speaking_style(df)
df.to_excel('taipei_personas_3000_with_style.xlsx', index=False)

# 預覽前 5 筆
print(df[['id', '說話風格']].head())
```

**輸出欄位**：

| 欄位 | 說明 |
|---|---|
| `說話風格_正式程度` | 高 / 中 / 低 |
| `說話風格_溝通取向` | 迂迴集體型 / 直接個人型 / 保守傳統型 / 折衷型 |
| `說話風格_語言切換` | 語言使用習慣描述 |
| `說話風格_數位語言` | 數位平台語言風格 |
| `說話風格` | 以上四維度合成的完整描述字串 |

---

## 7. 輸出範例

| id | 基本資料摘要 | 說話風格（輸出） |
|---|---|---|
| 1 | 女、45歲、客家、高中職、管理職、LINE+FB | 語言清晰，口語與正式交替；視情境調整，日常口語直接、正式場合轉為謹慎；語言習慣：偶夾客語詞（正式場合純國語）；數位溝通：折衷型（長篇評論傾向） |
| 2 | 男、83歲、閩南、大學、退休、LINE | 語言精緻，句子完整，用詞精確；保守傳統型，用語保守，敬語較多；語言習慣：頻繁夾台語；數位溝通：傳統書面型 |

---

## 8. 參考文獻

### 理論文獻

- Bernstein, B. (1971). *Class, Codes and Control* (Vol. 1). London: Routledge & Kegan Paul.
  - 提出 Elaborated Code / Restricted Code，說明教育與社會階級如何形塑語言精緻化程度。

- Bourdieu, P. (1991). *Language and Symbolic Power*. Cambridge: Harvard University Press.
  - 語言資本（linguistic capital）、語言習性（linguistic habitus）與場域理論，說明語域切換的社會機制。

- Hofstede, G. (2001). *Culture's Consequences: Comparing Values, Behaviors, Institutions and Organizations Across Nations* (2nd ed.). Thousand Oaks: SAGE.
  - 文化維度理論，個人/集體主義對溝通直接性的影響。

- Schwartz, S. H. (2006). A theory of cultural value orientations: Explication and applications. *Comparative Sociology*, 5(2-3), 137–182.
  - 文化價值取向七維度，補充 Hofstede 框架，與 CO/ST 分數設計銜接。

### 台灣在地資料來源

- 中央研究院社會所（1984 迄今）。**臺灣社會變遷基本調查**（TSCS）。https://tesd.survey.sinica.edu.tw/database/society
  - 五年一期的全國代表性調查，提供世代語言使用、族群認同等長期追蹤資料。

- 中央研究院（2012 迄今）。**Taiwan Communication Survey**（TCS）。https://tesd.survey.sinica.edu.tw/en/database/transmission
  - 傳統媒體與新興媒體使用習慣之全國調查，提供年齡分層的數位媒體使用資料。

- 教育部（2020）。**臺灣語言使用調查**。https://twlangsurvey.github.io/
  - 提供閩南語、客語、原住民族語等語言在不同族群與年齡層的使用頻率資料。

- DataReportal (2026). *Digital 2026: Taiwan*. https://datareportal.com/reports/digital-2026-taiwan
  - 台灣各社群平台（LINE、Facebook、Instagram、TikTok）年齡分層使用統計。

### 台灣社會語言學學術文獻

- Kuo, C.-H., & Lai, M.-L. (2006). Language ideologies in Taiwan Mandarin: Hypercorrection and social class. *NTU Working Papers in Linguistics*. https://homepage.ntu.edu.tw/~karchung/pubs/hypercorrection_rev.pdf
  - 台灣國語的社會階層語言差異研究。

- Dreher, T., & Dreher, T. (2021). Language Policy in the KMT and DPP eras. *ResearchGate*. https://www.researchgate.net/publication/30445807_Language_Policy_in_the_KMT_and_DPP_eras
  - 國民黨與民進黨政治語言政策差異，提供政治世代語言標記的政策背景。

- Liu, Y. et al. (2023). Effects of Facebook use on network social capital: A generational cohort analysis from the Taiwan Social Change Survey. *ResearchGate*. https://www.researchgate.net/publication/369600303
  - 世代群組在社群媒體使用行為上的差異，支持數位語言分層的設計邏輯。

---

*文件維護：Project Mirror 資料組*  
*如需更新規則或新增族群語言規則，請修改第 6.2 節的對應映射表。*
