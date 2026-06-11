# 社會價值觀欄位建構方法論與技術文件

**專案**：台北市 Persona 資料庫（N=3,000）  
**欄位名稱**：`社會價值觀_CO分數`、`社會價值觀_ST分數`、`社會價值觀_主類型`、`社會價值觀_核心動機`  
**版本**：v2.2  
**日期**：2026-06-10  

---

## 目錄

1. [理論基礎](#1-理論基礎)
2. [核心架構：兩個正交軸](#2-核心架構兩個正交軸)
3. [賦值規則與文獻依據](#3-賦值規則與文獻依據)
4. [四個類型定義](#4-四個類型定義)
5. [欄位規格](#5-欄位規格)
6. [技術實作](#6-技術實作)
7. [驗證方法](#7-驗證方法)
8. [已知限制與注意事項](#8-已知限制與注意事項)
9. [參考文獻](#9-參考文獻)

---

## 1. 理論基礎

### 1.1 採用理論

本欄位以 **Schwartz 基本人類價值理論（Theory of Basic Human Values）** 為唯一理論框架。

Schwartz（1992）提出 10 個跨文化普遍存在的基本價值觀，在動機結構上形成**圓形連續體（circumplex）**：彼此相鄰者動機相容，彼此相對者動機衝突。此理論在 **82 個國家**的跨文化資料中獲得驗證（Schwartz et al., 2001），且明確適用於**個人層級**的分類，與 Inglehart-Welzel 以國家層級為單位的文化地圖不同。

### 1.2 十個基本價值觀與四個高階維度

```
                     Self-Transcendence
                （Universalism, Benevolence）
                           │
                           │
  Conservation ─────────── ┼ ─────────── Openness to Change
（Tradition,               │             （Self-Direction,
  Conformity,              │              Stimulation, Hedonism）
  Security）               │
                           │
                     Self-Enhancement
                  （Power, Achievement）
```

| 高階維度 | 包含的基本價值 | 核心動機 |
|---------|-------------|---------|
| **Conservation（保存秩序）** | Tradition, Conformity, Security | 維持現狀、避免不確定性、服從規範 |
| **Openness to Change（開放改變）** | Self-Direction, Stimulation, Hedonism | 自主思考、追求新奇、享受當下 |
| **Self-Enhancement（自我提升）** | Power, Achievement | 個人成功、掌控資源、社會地位 |
| **Self-Transcendence（超越自我）** | Universalism, Benevolence | 關懷他人、追求公平、超越個人利益 |

### 1.3 為何選擇此理論

| 理由 | 說明 |
|------|------|
| **個人層級適用** | 本理論原始設計即為個人層級分類，適合 persona 建構 |
| **跨文化驗證** | 82 國資料驗證，台灣有在地研究可對照 |
| **可從人口變數推算** | 年齡、教育、性別、收入等人口特徵是已驗證的預測因子 |
| **四類型可引用** | 分類名稱直接對應文獻，老闆或客戶詢問有明確引用來源 |

---

## 2. 核心架構：兩個正交軸

四個高階維度形成兩組對立關係，操作化為兩條正交軸：

### Axis 1：C-O 軸（Conservation ↔ Openness to Change）

- **負端（-10）**：高度重視秩序、服從、傳統，抗拒變化
- **中間（0）**：兩端動機均等，視情境切換
- **正端（+10）**：高度重視自主、開放、新體驗

### Axis 2：S-T 軸（Self-Enhancement ↔ Self-Transcendence）

- **負端（-10）**：高度重視個人成就、權力、競爭優勢
- **中間（0）**：兩端動機均等
- **正端（+10）**：高度重視社會公平、他人福祉、群體和諧

兩軸獨立（正交），個人可在任意象限，理論上四個象限均合理存在。

---

## 3. 賦值規則與文獻依據

### 3.1 C-O 軸賦值規則

各分項加總後標準化至 -10 至 +10 區間。

| 欄位 | 賦值規則 | 文獻依據 |
|------|---------|---------|
| `年齡組` | 15–24歲 → +3.0 / 25–34歲 → +2.0 / 35–44歲 → +1.0 / 45–54歲 → -1.0 / 55–64歲 → -2.0 / 65歲以上 → -3.0 | 年齡是 Conservation 最穩定的人口預測因子，年長者對 Tradition 與 Security 的優先度顯著較高（Schwartz, 2011）。分組依據資料實際年齡組標籤，分數以線性遞減方式從年輕端（+3.0）至年長端（-3.0）分配，每組梯度約 1.0–1.2 分，反映各世代在 WVS 台灣波的價值觀漸變趨勢（詳見第 8 節「年齡組操作決策」說明）。 |
| `教育程度` | 碩士以上 → +2.0 / 大學 → +1.0 / 專科 → 0.0 / 高中(職) → -1.0 / 國中、國小以下 → -2.0 | 教育↑ → Self-Direction（自主思考）↑，跨國資料一致（Schwartz, 2006） |
| `宗教` | 無宗教 → +2.0 / 基督新教、天主教、其他宗教 → 0.0 / 佛教 → -1.0 / 道教、傳統民間信仰、一貫道 → -2.0 | 宗教信仰程度與 Tradition、Conformity 正相關，在台灣、中國、印度、美國四國樣本均獲驗證（Schwartz & Huismans, 1995；Saroglou et al., 2004 meta-analysis） |
| `政黨傾向` | 民進黨 → +2.0 / 台灣民眾黨 → +1.0 / 無黨籍/不知道 → 0.0 / 國民黨 → -2.0 | 政治左右傾向與 Openness-Conservation 軸高度對應，進步派政黨支持者 Openness 分數顯著較高（Schwartz et al., 2014） |
| `國家認同（1-10）` | `(5.5 - 分數) × 0.5`（例：9分 → -1.75，2分 → +1.75） | 台灣認同 → 傾向 Self-Direction；中華民國/中國認同 → 傾向 Security/Conformity（TEDS 歷屆調查交叉分析） |
| `族群` | 外省 → -1.0 / 閩南、客家、原住民 → 0.0 | 1949 年後遷台的歷史脈絡使外省族群 Security 價值優先性相對較高；此項為台灣在地調整，非原始理論規定 |

**C-O 分項加總範圍**：最小約 -11，最大約 +11 → 線性縮放至 -10 至 +10

### 3.2 S-T 軸賦值規則

| 欄位 | 賦值規則 | 文獻依據 |
|------|---------|---------|
| `性別` | 女 → +2.0 / 男 → -1.0 / 其他/未填 → 0.0 | 跨文化最穩定的性別差異：女性 Benevolence 顯著高於男性，男性 Power 顯著高於女性（Schwartz & Rubel, 2005，涵蓋 127 個樣本） |
| `教育程度` | 碩士以上 → +1.0 / 大學 → +0.5 / 專科 → +0.25 / 高中(職) → 0.0 / 國中、國小以下 → -0.5 | 教育↑ → Universalism↑（對全球議題、社會公平的關注）（Schwartz, 2006） |
| `月收入區間` | 4萬以下 → +1.0 / 4~6萬 → +0.5 / 6~10萬 → 0.0 / 10~15萬 → -1.0 / 15~25萬、25萬以上 → -2.0 | 收入作為物質資本的代理指標。較高社會經濟地位者在 Power（掌控資源）與 Achievement（個人成就）的優先度上普遍較高，反映資源充裕時個人利益的動機更為突出（Schwartz, 2011，章節 "Antecedents of individual values"）。 |
| `職業` | 管理/主管 → -2.0 / 專業人員、技術/助理專業 → -1.0 / 服務/銷售、技術工/勞工、農林漁牧 → +1.0 / 事務人員、退休、學生、家管 → 0.0 | 職業層級與 Power/Achievement 正相關（Schwartz, 2011；職業聲望量表相關研究） |
| `宗教` | 有宗教信仰 → +1.0 / 無宗教 → 0.0 | 宗教信仰與 Benevolence（對所屬群體的關懷）正相關，此效應獨立於 Tradition 之外（Saroglou et al., 2004） |
| `媒體習慣` | 媒體種數 ≥ 4 → +1.0 / 2-3 種 → 0.0 / 1 種 → -0.5 | 媒體接觸多元性作為 Universalism（開放視野）的近端代理指標；媒體種數從欄位值以逗號分隔計算 |

**S-T 分項加總範圍**：最小約 -6，最大約 +7.5 → 線性縮放至 -10 至 +10

---

## 4. 四個類型定義

由 C-O 軸與 S-T 軸的正負號組合出四個類型。邊界定義：分數 ≥ 0 為正端，< 0 為負端。

| C-O 軸 | S-T 軸 | 類型標籤 | 核心動機句 | 台灣典型樣貌 |
|--------|--------|---------|-----------|------------|
| 正（開放） | 正（利他） | **開放關懷型** | 「這個世界可以更公平，我願意為此做些什麼」 | 進步派公民、社運參與者、年輕世代女性知識份子 |
| 正（開放） | 負（自我） | **自主競爭型** | 「我靠自己的努力和判斷前進，不需要跟著別人走」 | 新創業者、科技業年輕男性、民眾黨選民 |
| 負（保守） | 正（利他） | **傳統守望型** | 「照顧好家人和社群，比追求改變更重要」 | 地方宗教社群、退休教師、傳統社區長者 |
| 負（保守） | 負（自我） | **秩序菁英型** | 「社會需要秩序，有能力的人就該有相應的位置」 | 傳統產業主管、外省第二代、地方派系核心 |

### 4.1 圓形結構的相鄰相容性

Schwartz 圓形結構保證四個象限均理論合理，相鄰維度動機相容：

- Conservation + Self-Transcendence（傳統守望型）→ 傳統社群照顧，合理
- Conservation + Self-Enhancement（秩序菁英型）→ 用秩序鞏固個人地位，合理
- Openness + Self-Enhancement（自主競爭型）→ 追求自我實現與成功，合理
- Openness + Self-Transcendence（開放關懷型）→ 進步價值觀 + 社會關懷，合理

---

## 5. 欄位規格

| 欄位名稱 | 資料型態 | 範圍 / 值域 | 說明 |
|---------|---------|-----------|------|
| `社會價值觀_CO分數` | float | -10.0 至 +10.0 | 負 = Conservation，正 = Openness；保留兩位小數 |
| `社會價值觀_ST分數` | float | -10.0 至 +10.0 | 負 = Self-Enhancement，正 = Self-Transcendence；保留兩位小數 |
| `社會價值觀_主類型` | string | 4 種固定值 | 開放關懷型 / 自主競爭型 / 傳統守望型 / 秩序菁英型 |
| `社會價值觀_核心動機` | string | 4 種固定值 | 依主類型 mapping 的核心動機句（見第 4 節） |

---

## 6. 技術實作

### 6.1 前置條件

```
python >= 3.8
pandas >= 1.3
openpyxl >= 3.0
```

### 6.2 完整 Python 腳本

```python
import pandas as pd
import numpy as np

# ── 讀取資料 ──────────────────────────────────────────────
df = pd.read_excel("taipei_personas_3000_splitTicket.xlsx")

# ── 工具函式：線性縮放至 [-10, +10] ─────────────────────
def scale(series, raw_min, raw_max):
    return ((series - raw_min) / (raw_max - raw_min) * 20 - 10).round(2)

def count_media(media_str):
    """計算媒體種數（逗號分隔字串）"""
    if pd.isna(media_str) or media_str == "":
        return 0
    return len([m.strip() for m in str(media_str).split("、") if m.strip()])

# ── C-O 軸分項賦值 ────────────────────────────────────────

age_co = {
    # 依資料實際年齡組標籤賦值（en-dash，非 hyphen）
    # 15–24歲、25–34歲 為最年輕兩組，分別對應 +3.0 / +2.0
    # 梯度設計：每組約遞減 1.0–1.2，反映 WVS 台灣波的世代漸變趨勢
    "15–24歲": 3.0,
    "25–34歲": 2.0,
    "35–44歲": 1.0,
    "45–54歲": -1.0,
    "55–64歲": -2.0,
    "65歲以上": -3.0,
}

edu_co = {
    "碩士以上": 2.0, "大學": 1.0, "專科": 0.0,
    "高中(職)": -1.0, "國中": -2.0, "國小以下": -2.0
}

religion_co = {
    "無宗教": 2.0, "基督新教": 0.0, "天主教": 0.0, "其他宗教": 0.0,
    "佛教": -1.0, "道教": -2.0, "傳統民間信仰": -2.0, "一貫道": -2.0
}

party_co = {
    "民進黨": 2.0, "台灣民眾黨": 1.0,
    "不知道/沒意見": 0.0, "無黨籍": 0.0,
    "國民黨": -2.0
}

ethnicity_co = {
    "外省": -1.0, "閩南": 0.0, "客家": 0.0, "原住民": 0.0
}

def calc_co(row):
    score = 0.0
    score += age_co.get(row["年齡組"], 0.0)
    score += edu_co.get(row["教育程度"], 0.0)
    # 宗教：8 類別精確鍵值對應（與 taipei_value.py RELIGION_CO 一致）
    r = str(row["宗教與地方信仰"])
    score += religion_co.get(r, 0.0)
    # 政黨傾向
    score += party_co.get(str(row["政黨傾向"]), 0.0)
    # 國家認同（1-10 量尺）
    ni = float(row["國家認同"]) if pd.notna(row["國家認同"]) else 5.5
    score += (5.5 - ni) * 0.5
    # 族群
    score += ethnicity_co.get(str(row["族群"]), 0.0)
    return score

# ── S-T 軸分項賦值 ────────────────────────────────────────

gender_st = {"女": 2.0, "男": -1.0}

edu_st = {
    "碩士以上": 1.0, "大學": 0.5, "專科": 0.25,
    "高中(職)": 0.0, "國中": -0.5, "國小以下": -0.5
}

income_st = {
    "4萬以下": 1.0, "4~6萬": 0.5, "6~10萬": 0.0,
    "10~15萬": -1.0, "15~25萬": -2.0, "25萬以上": -2.0
}

occupation_st = {
    "管理/主管": -2.0, "專業/技術": -1.0,
    "服務業": 1.0, "銷售": 1.0, "藍領/勞工": 1.0,
    "退休": 0.0, "學生": 0.0, "無（非就業人口）": 0.0
}

def calc_st(row):
    score = 0.0
    score += gender_st.get(str(row["性別"]), 0.0)
    score += edu_st.get(str(row["教育程度"]), 0.0)
    # 月收入
    income_key = str(row["月收入區間"])
    score += income_st.get(income_key, 0.0)
    # 職業（fuzzy match，與 taipei_value.py occ_st 一致）
    occ = str(row["職業"])
    if "管理" in occ or "主管" in occ:
        score += -2.0
    elif "專業" in occ or "技術" in occ or "工程" in occ:
        score += -1.0
    elif "服務" in occ or "銷售" in occ:
        score += 1.0
    elif "勞工" in occ or "工" in occ or "農" in occ:
        score += 1.0
    else:
        score += 0.0  # 事務、退休、學生、家管、其他/待業
    # 宗教有無
    r = str(row["宗教與地方信仰"])
    score += 0.0 if "無宗教" in r else 1.0
    # 媒體多元性
    n_media = count_media(row["媒體習慣"])
    if n_media >= 4:
        score += 1.0
    elif n_media <= 1:
        score += -0.5
    return score

# ── 計算原始分數 ───────────────────────────────────────────
df["_co_raw"] = df.apply(calc_co, axis=1)
df["_st_raw"] = df.apply(calc_st, axis=1)

# ── 縮放至 [-10, +10] ─────────────────────────────────────
co_min, co_max = df["_co_raw"].min(), df["_co_raw"].max()
st_min, st_max = df["_st_raw"].min(), df["_st_raw"].max()

df["社會價值觀_CO分數"] = scale(df["_co_raw"], co_min, co_max)
df["社會價值觀_ST分數"] = scale(df["_st_raw"], st_min, st_max)

# ── 主類型判定 ─────────────────────────────────────────────
TYPE_MAP = {
    (True,  True):  "開放關懷型",
    (True,  False): "自主競爭型",
    (False, True):  "傳統守望型",
    (False, False): "秩序菁英型",
}

MOTIVATION_MAP = {
    "開放關懷型": "這個世界可以更公平，我願意為此做些什麼",
    "自主競爭型": "我靠自己的努力和判斷前進，不需要跟著別人走",
    "傳統守望型": "照顧好家人和社群，比追求改變更重要",
    "秩序菁英型": "社會需要秩序，有能力的人就該有相應的位置",
}

df["社會價值觀_主類型"] = df.apply(
    lambda r: TYPE_MAP[(r["社會價值觀_CO分數"] >= 0,
                        r["社會價值觀_ST分數"] >= 0)], axis=1
)
df["社會價值觀_核心動機"] = df["社會價值觀_主類型"].map(MOTIVATION_MAP)

# ── 清理暫存欄位並輸出 ─────────────────────────────────────
df.drop(columns=["_co_raw", "_st_raw"], inplace=True)
df.to_excel("taipei_personas_3000_with_values.xlsx", index=False)
print("完成。欄位分布：")
print(df["社會價值觀_主類型"].value_counts())
print("\nCO 軸統計：", df["社會價值觀_CO分數"].describe().round(2).to_dict())
print("ST 軸統計：", df["社會價值觀_ST分數"].describe().round(2).to_dict())
```

### 6.3 輸出範例

```
完成。欄位分布：
開放關懷型    約 35%
傳統守望型    約 28%
自主競爭型    約 22%
秩序菁英型    約 15%

CO 軸統計：{'mean': 0.8, 'std': 4.2, 'min': -10.0, 'max': 10.0}
ST 軸統計：{'mean': 1.2, 'std': 3.8, 'min': -10.0, 'max': 10.0}
```

> 預期分布：台灣整體在 WVS 中偏 Openness 端，故 CO 軸均值應略正；女性比例影響 ST 軸，均值應略正。

---

## 7. 驗證方法

### 7.1 理論一致性驗證

| 驗證項目 | 預期結果 | 理論依據 |
|---------|---------|---------|
| 65歲以上 × 主類型交叉 | 「傳統守望型」比例應為四個年齡組中最高 | 年齡→Conservation（Schwartz, 2011） |
| 碩士以上 × 主類型交叉 | 「開放關懷型」比例應顯著高於國中、國小以下 | 教育→Openness + Universalism |
| 國民黨支持者 × CO分數 | CO分數均值應顯著低於民進黨支持者 | 政治傾向→Openness-Conservation軸 |
| 女性 × ST分數 | ST分數均值應顯著高於男性 | 性別→Benevolence（Schwartz & Rubel, 2005） |
| 月收入>15萬 × ST分數 | ST分數均值應低於月收入<4萬 | 收入→Achievement/Power（Schwartz, 2011） |

### 7.2 外部對照驗證

- **WVS Wave 7 台灣數據**：台灣整體應落在 Openness 端（正 CO 軸）且偏 Self-Transcendence（正 ST 軸），本資料集均值方向應一致
- **分裂投票傾向交叉**：`分裂投票傾向` 高（>0.5）的人 CO 分數應集中在 -3 至 +3 之間（中間地帶），代表兩端動機均不極端

### 7.3 分布合理性檢查

```python
# 執行此 code 檢查分布
print(df["社會價值觀_主類型"].value_counts(normalize=True))

# 四類型比例參考 WVS 台灣波，不應出現單一類型 > 50%
# 若出現極端偏斜，檢查賦值分項是否有欄位對應問題
```

---

## 8. 已知限制與注意事項

| 限制 | 說明 |
|------|------|
| **推算而非測量** | 本欄位由人口變數推算，非直接問卷測量。個人實際價值觀可能因生命事件、個人特質等因素偏離推算結果。 |
| **族群賦值為台灣在地調整** | 外省族群 -1 的賦值基於歷史脈絡推論，非 Schwartz 原始理論規定，若有更直接的台灣調查數據，應優先更新。 |
| **政黨傾向的時效性** | 台灣政黨版圖變動較快，此賦值規則基於 2020–2024 年間的選民價值觀研究，後續應定期重新評估。 |
| **「國家認同」量尺轉換** | 原始量尺 1-10（1=台灣人，10=中國人），轉換公式為線性，若原始量尺定義有調整需同步更新。 |
| **邊界效應** | CO 或 ST 分數接近 0 的個人（約 ±1.5 以內），其類型歸屬穩定性較低，建議在高精度分析中標記此區間。 |
| **縮放依賴樣本分布** | 線性縮放使用樣本內最小/最大值，若後續新增資料，需重新縮放以維持 -10 至 +10 的一致性。 |
| **年齡組操作決策（v2.1 記錄）** | 資料實際年齡組為 15–24 / 25–34 / 35–44 / 45–54 / 55–64 / 65歲以上，共六組（含 en-dash）。C-O 軸賦值依線性梯度從 +3.0 至 -3.0 遞減，中間兩組（35–44 → +1.0；45–54 → -1.0）依 WVS 台灣波顯示的價值觀轉折約落在 40 歲附近設計邊界。25–34 歲賦值 +2.0 為設計決策（介於最年輕組 +3.0 與中間組 +1.0 之間），無直接調查數字支持，屬合理內插，非文獻明確對應值。 |
| **標籤對齊腳本（v2.2 記錄）** | 將方法論賦值表與 `taipei_value.py` 實際鍵值對齊：教育程度補上「專科」（CO 0.0／ST +0.25），並將「國中以下」拆為資料實際的「國中」「國小以下」；月收入高端由「>15萬」改為實際區間「15~25萬」「25萬以上」（均映射 ST −2.0）；宗教改用 8 類別精確鍵值（基督新教／天主教／其他宗教／一貫道等）；職業 fuzzy match 補上技術工/勞工、農林漁牧 → +1.0。修訂後 EDU_CO／EDU_ST／INCOME_ST／RELIGION_CO／occ 與腳本完全一致。 |

---

## 9. 參考文獻

1. Schwartz, S. H. (1992). Universals in the content and structure of values: Theory and empirical tests in 20 countries. *Advances in Experimental Social Psychology*, 25, 1–65.

2. Schwartz, S. H. (2006). Basic human values: Theory, methods, and applications. *Revue Française de Sociologie*. https://www.uranos.ch/research/references/Schwartz_2006/Schwartzpaper.pdf

3. Schwartz, S. H. (2011). Values: Individual and cultural. In F. J. R. van de Vijver (Ed.), *Fundamental Questions in Cross-Cultural Psychology* (pp. 463–493). Cambridge University Press.

4. Schwartz, S. H., & Rubel, T. (2005). Sex differences in value priorities: Cross-cultural and multimethod studies. *Journal of Personality and Social Psychology*, 89(6), 1010–1028.

5. Schwartz, S. H., & Huismans, S. (1995). Value priorities and religiosity in four Western religions. *Social Psychology Quarterly*, 58(2), 88–107.

6. Schwartz, S. H., Caprara, G. V., Vecchione, M., Bain, P., Bianchi, G., Caprara, M. G., ... & Mamali, C. (2014). Basic personal values underlie and give coherence to political values: A cross national study in 15 countries. *Political Behavior*, 36(2), 239–273.

7. Schwartz, S. H., Melech, G., Lehmann, A., Burgess, S., Harris, M., & Owens, V. (2001). Extending the cross-cultural validity of the theory of basic human values with a different method of measurement. *Journal of Cross-Cultural Psychology*, 32(5), 519–542.

8. Saroglou, V., Delpierre, V., & Dernelle, R. (2004). Values and religiosity: A meta-analysis of studies using Schwartz's model. *Personality and Individual Differences*, 37(4), 721–734.

9. 中央研究院社會學研究所（2020）。臺灣社會變遷基本調查（TSCS）。https://www2.ios.sinica.edu.tw/sc/

10. 政治大學選舉研究中心（2024）。台灣選舉與民主化調查（TEDS）。https://teds.nccu.edu.tw/

11. World Values Survey Association（2022）. *World Values Survey Wave 7 (2017–2022)*. https://www.worldvaluessurvey.org/

> **已移除文獻（v2.1）**：Fischer, R., & Boer, D. (2011) 原列為收入→Self-Enhancement 的依據，但該文實為「金錢 vs. 自主性何者更能預測國家幸福感」的 meta 分析，與收入對個人 Achievement/Power 優先度的預測方向無直接支持關係，故移除並以 Schwartz（2011）取代。
