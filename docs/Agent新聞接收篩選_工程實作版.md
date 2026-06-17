# Agent 新聞接收篩選方法（工程實作版）
## 輸入一則新聞，決定哪些 agent 會「接收到」它

**範圍：** 只到接收篩選為止。接收後的解讀與記憶寫入屬下游模組，不在本文件。
**輸入：** 新聞純文字（不需平台/來源欄位）＋ Persona 24 欄位（N=3,000）
**輸出：** 每則新聞對應的接收者名單 `receive[agent_id] ∈ {0, 1}`

---

## 方法總覽

採用民意研究標準理論 Zaller (1992) RAS 模型的**接收公理**：

> 一個人是否接收到一則政治訊息，取決於他的「政治覺察程度」（political awareness），而非訊息來自哪個管道。

因此篩選只需兩個成分，全部由既有欄位計算：

```
P(接收) = logistic( a + b × 政治覺察分數A + c × 議題關聯分數M )
```

---

## Step 1　新聞標註

每則新聞用 LLM 標一個欄位（供篩選用）：

```
issue_category ∈ {ECO, HSG, XS, ENV, WEL, EDU, SOC, GOV}   # 資料集既有 8 大議題分類
issue_subtag：對應子議題（如 HSG-房價、ENV-核電）
```

（立場、框架等標註供下游解讀模組使用，與接收篩選無關。）

- 8 大分類為**本資料集既有的編碼方案**（見 24 欄位建構報告 E-5），非取自單一文獻；「將新聞按議題類別編碼」的研究慣例可溯及議程設定研究傳統 [McCombs & Shaw (1972)](https://academic.oup.com/poq/article-abstract/36/2/176/1853310)（注意：該文講的是媒體議題顯著性向公眾移轉，未提供分類法）
- LLM 標註效度依據：[Gilardi et al. (2023, PNAS)](https://www.pnas.org/doi/10.1073/pnas.2305016120)——LLM 在議題/立場標註上準確率優於人類群眾外包約 25 個百分點
- 品管：抽 5–10% 樣本人工複核一致性

---

## Step 2　接收判定

### Step 2 每個設計決策的文獻對應

| # | 設計決策 | 依據文獻 | 文獻的發現 | 我們的操作化 |
|---|---|---|---|---|
| 1 | 不是全員收到同一則新聞；接收機率隨「政治覺察」遞增 | [Zaller (1992)](https://www.cambridge.org/core/books/nature-and-origins-of-mass-opinion/70B1485D3A9CFF55ADCCDD42FC7E926A) 接收公理（A1） | 政治訊息的觸達在人群中高度分層，由個人覺察程度決定，與訊息管道無關 | 每個 agent 各自計算接收機率，而非廣播 |
| 2 | 接收機率函數採 logistic 形式 | Zaller (1992) 第 7–10 章經驗模型；[Dobrzynska & Blais (2008, Political Behavior)](https://link.springer.com/article/10.1007/s11109-007-9049-2) | Zaller 將接收機率估計為覺察的 logistic 函數：P = 1/(1+e^−(a+b·awareness))。D&B 以加拿大選舉資料證實**接收階段**的覺察分層與 logit 形式（覺察對接收之 logit 係數 2.35，p<.01；最高/最低覺察組接收率 65% vs 30%）。注意：該文對 RAS 整體支持有限（接受階段交互作用不顯著），本設計僅引用其接收階段結果 | `sigmoid(a + b·A)` 部分直接沿用原書函數形式。**簡化假設聲明**：Zaller 原式另含逐訊息的「訊息強度」參數，本設計將其吸收進常數 a，即假設所有輸入新聞強度相同；若需放寬，可依新聞聲量為每則新聞估 aᵢ |
| 2b | 在 logistic 中加入議題關聯項 c×M | Zaller (1992) 接收公理原文＋Krosnick (1990) | **接收公理本身是議題特定的**：「對該議題的認知投入越高，越可能接收關於該議題的訊息」。多數實證以一般覺察近似之；本設計依 Krosnick 的議題公眾理論將議題特定成分操作化為 M | 注意：c×M 為理論引導的延伸項，非文獻原式照抄——對外應表述為「函數形式沿用 Zaller，自變數依接收公理的議題特定性加入議題關聯項」 |
| 3 | 覺察分數 A 用「教育＋媒體平台數＋關注議題數」三欄位代理 | [Price & Zaller (1993, POQ)](https://academic.oup.com/poq/article-abstract/57/2/133/1886901) | 以 16 則真實新聞的回憶率實測：**背景政治知識**是新聞接收的最強且最穩定預測因子，勝過自報媒體使用量；新聞受眾按知識水準明顯分層 | 模擬中沒有知識測驗分數，依此文獻用三個相關欄位組合代理：教育程度（知識的結構性來源）＋媒體平台數（資訊環境豐富度）＋關注議題標籤數（政治興趣） |
| 4 | 新聞議題命中個人重要議題 → 接收機率提高（M 分數） | [Krosnick (1990, Political Behavior)](https://link.springer.com/article/10.1007/BF00992332) | 公眾由眾多「議題公眾」組成：對個人重要的議題會被頻繁思考、高度注意、態度穩定持久 | 議題關聯分數 M：命中關注議題/子議題即加分 |
| 5 | M 的「利益關聯對映表」分三類建構 | [Boninger, Krosnick & Berent (1995, JPSP)](https://pubmed.ncbi.nlm.nih.gov/7861315/) | 態度重要性實證確立的三大成因：**自身利益**（self-interest）、**社會認同**（social identification）、**價值相關**（value relevance）；三者各自獨立顯著，且操弄自身利益會直接改變重要性（論文檢驗此三項假設成因，未排除其他成因存在） | 對映表的三個區塊即按此三類建構（見下），每一列都可回溯到三成因之一，非任意設定 |

### 2a. 政治覺察分數 A（每個 agent 算一次，可預先快取）

```python
A = mean( z(教育程度等級),        # Price & Zaller 1993：知識的結構性代理
          z(媒體平台數),          # 媒體習慣欄位的平台數量（1–15）
          z(關注議題標籤數) )      # 1–3，政治興趣代理
```

### 2b. 議題關聯分數 M（每個 agent × 每則新聞）

命中即累加，上限截斷 2.0：

| 命中類型（Boninger et al. 1995 三成因） | 規則 | 權重 |
|---|---|---|
| **價值相關**：關注議題直接命中 | news.issue_category ∈ agent.關注議題 | 1.0 |
| **價值相關**：子議題命中 | news.issue_subtag ∈ agent.關注子議題 | +0.5 |
| **自身利益**：利益欄位命中 | 房產持有 → HSG；產業別 → 對應議題（金融→ECO、資訊→ECO/EDU、醫療→WEL、公共行政→GOV、教育→EDU）；月收入 4萬以下→ECO/WEL、15萬以上→ENV/GOV；65歲以上→WEL；已婚25–44歲→EDU/HSG | 0.5 |
| **社會認同**：群體欄位命中 | 族群（客家/原住民→SOC、外省→XS）；居住地（新聞提及該行政區） | 0.5 |

### 2c. 機率計算與抽樣

```python
P_receive = sigmoid(a + b * A + c * M)
receive   = bernoulli(P_receive, seed=fixed)   # 固定亂數種子，可重現
```

### 參數怎麼定（只有 a、b、c 三個）

- **a、b**：用 [臺灣傳播調查資料庫 TCS](https://srda.sinica.edu.tw/plan/?idx=SRDA.AS028) 的「新聞接觸頻率 × 教育 × 年齡」交叉表校準——調整 a、b 使模擬接收率的整體水準與教育/年齡層級差對齊台灣實測分布。
- **c**：以「議題命中者接收率顯著高於未命中者」（Krosnick 1990 的方向約束）做網格搜尋，並做 ±50% 敏感度分析確認結論穩健。

---

## 偽代碼（完整流程）

```python
# 預計算（一次）
for agent in agents:
    agent.A = awareness_score(agent)            # 2a

# 每則新聞
news.issue = llm_annotate(news.text)            # Step 1

for agent in agents:
    M = issue_match_score(agent, news.issue)    # 2b
    p = sigmoid(a + b * agent.A + c * M)        # 2c
    if bernoulli(p, seed):
        write_to_memory(agent, news)            # 下游模組
```

---

## 設計依據速查（被問時的一句話回答）

- **為什麼不用平台來源？** → Zaller (1992)：接收由個人覺察決定，不由管道決定；Price & Zaller (1993) 實測也證明自報媒體使用量的預測力不如背景知識。
- **為什麼不是全員都收到？** → Zaller＋Krosnick：政治訊息觸達實證上高度分層；全員等量接收反而違反文獻。
- **覺察代理變數的依據？** → Price & Zaller (1993)：政治知識是新聞接收最強預測因子，教育與政治興趣為其標準代理。
- **利益對映表是不是自己掰的？** → 不是。三個區塊一一對應 Boninger, Krosnick & Berent (1995) 實證確立的態度重要性三成因：自身利益、社會認同、價值相關。
- **LLM 標新聞可靠嗎？** → Gilardi et al. (2023, PNAS)，優於人類群眾外包，另有人工複核。
- **參數會不會是自己掰的？** → 全模型只有 a、b、c：a、b 用 TCS 實測校準，c 有文獻方向約束＋敏感度分析。
- **這條公式是文獻原式嗎？** → `logistic(a+b×A)` 是 Zaller 原書的實作形式，Dobrzynska & Blais (2008) 證實其**接收階段**的覺察分層與 logit 形式（引用時勿說成「驗證了 RAS 模型」——該文對接受階段持保留結論）；`c×M` 是依接收公理的議題特定性（Zaller 公理原文即為 issue-specific）與 Krosnick 議題公眾理論加入的延伸項；Zaller 原式的「訊息強度」參數被吸收進常數 a（簡化假設：所有新聞強度相同）。正確表述：「函數形式沿用 Zaller，自變數擴充有理論依據，並聲明訊息強度之簡化」。

---

## 參考文獻

| # | 文獻 | 用途 | 連結 |
|---|---|---|---|
| 1 | Zaller, J. R. (1992). *The Nature and Origins of Mass Opinion.* Cambridge UP | 接收公理＋logistic 函數形式 | https://www.cambridge.org/core/books/nature-and-origins-of-mass-opinion/70B1485D3A9CFF55ADCCDD42FC7E926A |
| 2 | Price, V., & Zaller, J. (1993). Who Gets the News? *POQ* 57(2), 133–164 | 覺察分數 A 的測量依據 | https://academic.oup.com/poq/article-abstract/57/2/133/1886901 |
| 2b | Dobrzynska, A., & Blais, A. (2008). Testing Zaller's Reception and Acceptance Model. *Political Behavior* 30 | 接收階段 logit 形式之實證（僅引用接收階段；該文對 RAS 整體支持有限） | https://link.springer.com/article/10.1007/s11109-007-9049-2 |
| 3 | Krosnick, J. A. (1990). Government Policy and Citizen Passion. *Political Behavior* 12, 59–92 | 議題關聯分數 M（議題公眾） | https://link.springer.com/article/10.1007/BF00992332 |
| 4 | Boninger, Krosnick & Berent (1995). Origins of Attitude Importance. *JPSP* 68(1), 61–80 | 利益關聯對映表三分類 | https://pubmed.ncbi.nlm.nih.gov/7861315/ |
| 5 | McCombs & Shaw (1972). The Agenda-Setting Function of Mass Media. *POQ* 36(2) | 「按議題編碼新聞」之研究慣例依據（8 大分類本身為資料集既有編碼方案） | https://academic.oup.com/poq/article-abstract/36/2/176/1853310 |
| 6 | Gilardi, Alizadeh & Kubli (2023). *PNAS* 120(30) | LLM 標註效度 | https://www.pnas.org/doi/10.1073/pnas.2305016120 |
| 7 | 臺灣傳播調查資料庫（TCS） | a、b 參數校準 | https://srda.sinica.edu.tw/plan/?idx=SRDA.AS028 |
