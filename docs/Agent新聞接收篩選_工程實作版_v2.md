# Agent 新聞接收篩選方法（工程實作版 v2）
## 輸入一則新聞，決定哪些 agent 會「接收到」它

> **v2 更新重點：** 接收判定改為**兩層 fallback，且管線順序為「頻道篩選先、LLM 標註後」**。
> **第一層**用「來源頻道」欄位做硬匹配（不需 LLM）：匹配成功直接接收。
> **第二層**只對「未匹配者」執行 LLM 議題標註 ＋ Zaller 覺察判定。
> 好處：LLM 標註從「全量先做」改為「只服務 fallback 子群」，省算且邏輯更清楚。

**範圍：** 只到接收篩選為止。接收後的解讀與記憶寫入屬下游模組，不在本文件。
**輸入：** 新聞純文字 ＋ **來源平台標籤 `source_platform`**（採集自 FB / Threads / 論壇；第一層用，取自採集管線、非 LLM 推論）＋ Persona 24 欄位（N=3,000）
**輸出：** 每則新聞對應的接收者名單 `receive[agent_id] ∈ {0, 1}`

---

## 方法總覽

採用**兩層 fallback**，依管線順序執行：

```
第一層　來源頻道篩選（選擇性接觸 / 管道可得性，無 LLM、無參數）
    news.source_platform ∈ agent 媒體使用習慣
        → receive = 1（直接接收，後續不再處理此 agent）
    否則 → 丟入第二層待判定池

第二層　LLM 標註 ＋ 覺察判定（Zaller RAS，僅對未匹配者）
    Step A：LLM 標註該則新聞議題（issue_category / issue_subtag）
    Step B：P(接收) = logistic( a + b × 覺察分數A + c × 議題關聯分數M )
            receive = bernoulli(P)
```

- **第一層** 處理「內容就在你慣用的平台上，你自然接觸得到」——對應**選擇性接觸 / 媒體使用慣性**（Stroud 2008）。純欄位比對，最便宜，先跑。
- **第二層** 處理「內容不在你的平台上，但你仍可能接觸到」——對應 **Zaller (1992) 接收公理**：是否接收由個人政治覺察決定，與管道無關；社群中的**偶遇接觸**（incidental exposure, Fletcher & Nielsen 2018）即由此機制承接。LLM 標註只在這一層需要。

兩層各有獨立的傳播機制、互不矛盾：第一層是「直接管道可得性」，第二層是「跨管道的覺察接收」。第二層的公式與參數沿用原 v1 設計，未更動。

### 設計取捨聲明（務必對外揭露）

1. **接收率由平台滲透率主導。** 因「匹配成功即接收」，當 `source_platform = Facebook`（樣本中 81% agent 使用）時，至少 81% agent 由第一層直接接收，第二層僅對其餘 <19% 起作用。即第一層為主力、第二層為少數兜底。此為「直接接收」設定的必然結果。
2. **選擇性偏誤。** 接收一旦吃管道，而可採集足跡僅 FB / Threads / 論壇三個平台，第一層會系統性偏袒使用這些平台的 agent。緩解：第二層必須穩穩接住未匹配者（尤其僅用 LINE / YouTube / 小紅書 的長輩族，約佔 17%），並對第二層參數做敏感度分析。
3. **與 v1 的口徑差異。** v1 主張「接收與管道無關」（純 Zaller）；v2 將管道效果限定在第一層，第二層仍維持 Zaller 的管道無關性。對外應表述為：「第一層用平台，第二層不用」。
4. **LLM 標註的觸發時機。** 標註延後到第二層，僅在「該則新聞存在未匹配 agent」時才需執行（實務上幾乎每則皆有，但對 source_platform 涵蓋極廣的新聞，第二層人數可能很少，per-agent 議題比對量隨之下降）。

---

## 第一層　來源頻道篩選（先跑，無 LLM）

對每則新聞，直接以採集管線提供的 `source_platform` 與每個 agent 的媒體習慣欄位做集合比對。

```python
news.source_platform = collect_pipeline_tag(news)   # 取自採集來源，非 LLM 推論

matched, pending = [], []
for agent in agents:
    if news.source_platform in agent.媒體習慣:       # 管道可得 → 直接接收
        agent.receive = 1
        matched.append(agent)
    else:
        pending.append(agent)                        # 交給第二層
```

### 第一層的文獻對應

| # | 設計決策 | 依據文獻 | 文獻的發現 | 我們的操作化 |
|---|---|---|---|---|
| 0 | 新聞來源平台落在 agent 慣用平台內 → 直接接收 | [Stroud (2008, Political Behavior)](https://link.springer.com/article/10.1007/s11109-007-9050-9) | 以 2004 NAES 資料證實:個人政治傾向與其**慣性媒體使用型態**相關，且跨媒體類型一致;研究應看習慣性接觸型態而非單次接觸決定 | 將「慣用平台」操作化為媒體習慣欄位;新聞落在其中即視為管道可得、直接接收。此為「接觸機會」機制,與第二層的「覺察」機制並列,非取代 |
| 0b | 未匹配者 fallback 至第二層,而非直接判定為「未接收」 | [Fletcher & Nielsen (2018, New Media & Society)](https://journals.sagepub.com/doi/abs/10.1177/1461444817724170) | 人們即使不主動找新聞,仍會在社群上**偶遇接觸**新聞;此效果在 YouTube / Twitter 使用者、年輕族群、低新聞興趣者中更強 | 未匹配 ≠ 接觸不到。偶遇接觸由第二層的覺察模型承接,使高覺察者仍可能接收不在其慣用平台的內容 |

> `source_platform` 不需 LLM。若一則新聞實際採集自多個平台，可存為多值，比對採聯集（見「已知限制」1）。

---

## 第二層　LLM 標註 ＋ 覺察判定（僅對 `pending`）

### Step A　LLM 新聞標註（延後到此處才做）

僅在第一層留下未匹配 agent 時，對該則新聞標註：

```
issue_category ∈ {ECO, HSG, XS, ENV, WEL, EDU, SOC, GOV}   # 資料集既有 8 大議題分類
issue_subtag：對應子議題（如 HSG-房價、ENV-核電）
```

（立場、框架等標註供下游解讀模組使用，與接收篩選無關。）

- 8 大分類為**本資料集既有的編碼方案**（見 24 欄位建構報告 E-5），非取自單一文獻；「將新聞按議題類別編碼」的研究慣例可溯及議程設定研究傳統 [McCombs & Shaw (1972)](https://academic.oup.com/poq/article-abstract/36/2/176/1853310)（注意：該文講的是媒體議題顯著性向公眾移轉，未提供分類法）
- LLM 標註效度依據：[Gilardi et al. (2023, PNAS)](https://www.pnas.org/doi/10.1073/pnas.2305016120)——LLM 在議題/立場標註上準確率優於人類群眾外包約 25 個百分點

### Step B　覺察判定（Zaller RAS）

#### Step B 每個設計決策的文獻對應

| # | 設計決策 | 依據文獻 | 文獻的發現 | 我們的操作化 |
|---|---|---|---|---|
| 1 | 不是全員收到同一則新聞；接收機率隨「政治覺察」遞增 | [Zaller (1992)](https://www.cambridge.org/core/books/nature-and-origins-of-mass-opinion/70B1485D3A9CFF55ADCCDD42FC7E926A) 接收公理（A1） | 政治訊息的觸達在人群中高度分層，由個人覺察程度決定，與訊息管道無關 | 每個未匹配 agent 各自計算接收機率，而非廣播 |
| 2 | 接收機率函數採 logistic 形式 | Zaller (1992) 第 7–10 章經驗模型；[Dobrzynska & Blais (2008, Political Behavior)](https://link.springer.com/article/10.1007/s11109-007-9049-2) | Zaller 將接收機率估計為覺察的 logistic 函數：P = 1/(1+e^−(a+b·awareness))。D&B 以加拿大選舉資料證實**接收階段**的覺察分層與 logit 形式（覺察對接收之 logit 係數 2.35，p<.01；最高/最低覺察組接收率 65% vs 30%）。注意：該文對 RAS 整體支持有限（接受階段交互作用不顯著），本設計僅引用其接收階段結果 | `sigmoid(a + b·A)` 部分直接沿用原書函數形式。**簡化假設聲明**：Zaller 原式另含逐訊息的「訊息強度」參數，本設計將其吸收進常數 a，即假設所有輸入新聞強度相同；若需放寬，可依新聞聲量為每則新聞估 aᵢ |
| 2b | 在 logistic 中加入議題關聯項 c×M | Zaller (1992) 接收公理原文＋Krosnick (1990) | **接收公理本身是議題特定的**：「對該議題的認知投入越高，越可能接收關於該議題的訊息」。多數實證以一般覺察近似之；本設計依 Krosnick 的議題公眾理論將議題特定成分操作化為 M | 注意：c×M 為理論引導的延伸項，非文獻原式照抄——對外應表述為「函數形式沿用 Zaller，自變數依接收公理的議題特定性加入議題關聯項」 |
| 3 | 覺察分數 A 用「教育＋媒體平台數＋關注議題數」三欄位代理 | [Price & Zaller (1993, POQ)](https://academic.oup.com/poq/article-abstract/57/2/133/1886901) | 以 16 則真實新聞的回憶率實測：**背景政治知識**是新聞接收的最強且最穩定預測因子，勝過自報媒體使用量；新聞受眾按知識水準明顯分層 | 模擬中沒有知識測驗分數，依此文獻用三個相關欄位組合代理：教育程度（知識的結構性來源）＋媒體平台數（資訊環境豐富度）＋關注議題標籤數（政治興趣） |
| 4 | 新聞議題命中個人重要議題 → 接收機率提高（M 分數） | [Krosnick (1990, Political Behavior)](https://link.springer.com/article/10.1007/BF00992332) | 公眾由眾多「議題公眾」組成：對個人重要的議題會被頻繁思考、高度注意、態度穩定持久 | 議題關聯分數 M：命中關注議題/子議題即加分 |
| 5 | M 的「利益關聯對映表」分三類建構 | [Boninger, Krosnick & Berent (1995, JPSP)](https://pubmed.ncbi.nlm.nih.gov/7861315/) | 態度重要性實證確立的三大成因：**自身利益**（self-interest）、**社會認同**（social identification）、**價值相關**（value relevance）；三者各自獨立顯著，且操弄自身利益會直接改變重要性（論文檢驗此三項假設成因，未排除其他成因存在） | 對映表的三個區塊即按此三類建構（見下），每一列都可回溯到三成因之一，非任意設定 |

#### B-2a. 政治覺察分數 A（每個 agent 算一次，可預先快取）

```python
A = mean( z(教育程度等級),        # Price & Zaller 1993：知識的結構性代理
          z(媒體平台數),          # 媒體習慣欄位的平台數量（1–15）
          z(關注議題標籤數) )      # 1–3，政治興趣代理
```

> 說明:媒體平台「數量」在此作為**覺察豐富度代理**(v1 即如此),與第一層用平台「種類」做管道匹配是兩個不同用途,不重複計算。

#### B-2b. 議題關聯分數 M（每個未匹配 agent × 每則新聞）

命中即累加，上限截斷 2.0：

| 命中類型（Boninger et al. 1995 三成因） | 規則 | 權重 |
|---|---|---|
| **價值相關**：關注議題直接命中 | news.issue_category ∈ agent.關注議題 | 1.0 |
| **價值相關**：子議題命中 | news.issue_subtag ∈ agent.關注子議題 | +0.5 |
| **自身利益**：利益欄位命中 | 房產持有 → HSG；產業別 → 對應議題（金融→ECO、資訊→ECO/EDU、醫療→WEL、公共行政→GOV、教育→EDU）；月收入 4萬以下→ECO/WEL、15萬以上→ENV/GOV；65歲以上→WEL；已婚25–44歲→EDU/HSG | 0.5 |
| **社會認同**：群體欄位命中 | 族群（客家/原住民→SOC、外省→XS）；居住地（新聞提及該行政區） | 0.5 |

#### B-2c. 機率計算與抽樣

```python
for agent in pending:                              # 只算未匹配者
    M = issue_match_score(agent, news.issue)
    p = sigmoid(a + b * agent.A + c * M)
    agent.receive = bernoulli(p, seed=fixed)       # 固定亂數種子，可重現
```

### 參數怎麼定（只有 a、b、c 三個；第一層無參數）

- 第一層為硬匹配，無自由參數。
- **a、b**：用 [臺灣傳播調查資料庫 TCS](https://srda.sinica.edu.tw/plan/?idx=SRDA.AS028) 的「新聞接觸頻率 × 教育 × 年齡」交叉表校準——**注意 v2 校準對象**:應僅以「未被第一層匹配的子群」之實測接收率校準 a、b,避免把第一層已接收者混入,造成第二層高估。
- **c**：以「議題命中者接收率顯著高於未命中者」（Krosnick 1990 的方向約束）做網格搜尋，並做 ±50% 敏感度分析確認結論穩健。

---

## 偽代碼（完整流程，依管線順序）

```python
# 預計算（一次）
for agent in agents:
    agent.A = awareness_score(agent)                 # B-2a

# 每則新聞
news.source_platform = collect_pipeline_tag(news)    # 來自採集管線，無 LLM

# ── 第一層：來源頻道篩選（先跑，無 LLM） ──
pending = []
for agent in agents:
    if news.source_platform in agent.媒體習慣:
        agent.receive = 1                            # 管道匹配 → 直接接收
    else:
        pending.append(agent)

# ── 第二層：僅對未匹配者，才做 LLM 標註 + 覺察判定 ──
if pending:
    news.issue = llm_annotate(news.text)             # Step A：延後到此才標註
    for agent in pending:
        M = issue_match_score(agent, news.issue)     # B-2b
        p = sigmoid(a + b * agent.A + c * M)         # B-2c
        agent.receive = bernoulli(p, seed)

# 寫入
for agent in agents:
    if agent.receive:
        write_to_memory(agent, news)                 # 下游模組
```

---

## 設計依據速查（被問時的一句話回答）

- **為什麼頻道篩選先、LLM 標註後？** → 第一層只比對欄位、最便宜,先濾掉「管道可得」的接收者;LLM 標註只為第二層的覺察判定服務,延後到只剩 fallback 子群才做,省算且職責分明。
- **接收到底用不用平台來源？** → **分層用**:第一層用平台(管道匹配,Stroud 2008 選擇性接觸);第二層不用平台,維持 Zaller 覺察決定。對外請明確說「第一層用、第二層不用」,勿一概而論。
- **為什麼匹配成功就直接接收？** → 第一層模擬「選擇性接觸 / 管道可得性」:內容就在你慣用的平台上,接觸幾乎必然。Stroud (2008) 證實慣性媒體使用型態與政治內容接觸高度相關。
- **沒匹配到的人就接觸不到嗎？** → 不是。Fletcher & Nielsen (2018) 證實社群有大量**偶遇接觸**;未匹配者由第二層的覺察模型承接,高覺察者仍可能接收。
- **為什麼第二層不再用平台？** → Zaller (1992)：接收由覺察決定、不由管道決定；Price & Zaller (1993) 實測也證明自報媒體使用量的預測力不如背景知識。第二層專責「跨管道接收」,維持此原則。
- **為什麼不是全員都收到？** → Zaller＋Krosnick：政治訊息觸達實證上高度分層；全員等量接收反而違反文獻。第二層對未匹配者仍做覺察分層。
- **覺察代理變數的依據？** → Price & Zaller (1993)：政治知識是新聞接收最強預測因子，教育與政治興趣為其標準代理。「媒體平台數」在 A 中是覺察豐富度代理,與第一層的平台種類匹配用途不同。
- **利益對映表是不是自己掰的？** → 不是。三個區塊一一對應 Boninger, Krosnick & Berent (1995) 實證確立的態度重要性三成因：自身利益、社會認同、價值相關。
- **LLM 標新聞可靠嗎？** → Gilardi et al. (2023, PNAS)，優於人類群眾外包，另有人工複核。`source_platform` 不需推論,取自採集管線。
- **參數會不會是自己掰的？** → 全模型只有 a、b、c：a、b 用 TCS 實測校準(僅以未匹配子群校準)，c 有文獻方向約束＋敏感度分析。第一層無參數。
- **這條公式是文獻原式嗎？** → `logistic(a+b×A)` 是 Zaller 原書的實作形式，Dobrzynska & Blais (2008) 證實其**接收階段**的覺察分層與 logit 形式（引用時勿說成「驗證了 RAS 模型」——該文對接受階段持保留結論）；`c×M` 是依接收公理的議題特定性（Zaller 公理原文即為 issue-specific）與 Krosnick 議題公眾理論加入的延伸項；Zaller 原式的「訊息強度」參數被吸收進常數 a（簡化假設：所有新聞強度相同）。正確表述：「函數形式沿用 Zaller，自變數擴充有理論依據，並聲明訊息強度之簡化」。

---

## 已知限制（v2）

1. **接收率受 `source_platform` 分布主導**:單則新聞只能標一個來源平台,但真實新聞常跨平台流通。若多數新聞標為 FB,整體接收率會偏高、第二層幾乎不作用。緩解:允許 `source_platform` 為多值(該則新聞實際採集到的所有平台),第一層匹配採聯集。
2. **選擇性偏誤(僅 3 個可採集平台)**:第一層偏袒 FB / Threads / 論壇使用者。約 17% 僅用 LINE / YouTube / 小紅書 的 agent 永遠走第二層;須確認第二層的接收率設定不會系統性低估此群(多為長輩),並做敏感度分析。
3. **硬匹配無強度差異**:第一層不分「重度/輕度使用該平台」,一律視為接觸。若日後有使用強度資料,可改為機率匹配。
4. **跨層校準耦合**:a、b 須僅以未匹配子群校準,否則第一層已接收者會污染第二層估計(見參數章)。

---

## 參考文獻

| # | 文獻 | 用途 | 連結 |
|---|---|---|---|
| 1 | Zaller, J. R. (1992). *The Nature and Origins of Mass Opinion.* Cambridge UP | 第二層接收公理＋logistic 函數形式 | https://www.cambridge.org/core/books/nature-and-origins-of-mass-opinion/70B1485D3A9CFF55ADCCDD42FC7E926A |
| 2 | Price, V., & Zaller, J. (1993). Who Gets the News? *POQ* 57(2), 133–164 | 覺察分數 A 的測量依據 | https://academic.oup.com/poq/article-abstract/57/2/133/1886901 |
| 2b | Dobrzynska, A., & Blais, A. (2008). Testing Zaller's Reception and Acceptance Model. *Political Behavior* 30 | 接收階段 logit 形式之實證（僅引用接收階段；該文對 RAS 整體支持有限） | https://link.springer.com/article/10.1007/s11109-007-9049-2 |
| 3 | Krosnick, J. A. (1990). Government Policy and Citizen Passion. *Political Behavior* 12, 59–92 | 議題關聯分數 M（議題公眾） | https://link.springer.com/article/10.1007/BF00992332 |
| 4 | Boninger, Krosnick & Berent (1995). Origins of Attitude Importance. *JPSP* 68(1), 61–80 | 利益關聯對映表三分類 | https://pubmed.ncbi.nlm.nih.gov/7861315/ |
| 5 | McCombs & Shaw (1972). The Agenda-Setting Function of Mass Media. *POQ* 36(2) | 「按議題編碼新聞」之研究慣例依據（8 大分類本身為資料集既有編碼方案） | https://academic.oup.com/poq/article-abstract/36/2/176/1853310 |
| 6 | Gilardi, Alizadeh & Kubli (2023). *PNAS* 120(30) | LLM 標註效度 | https://www.pnas.org/doi/10.1073/pnas.2305016120 |
| 7 | 臺灣傳播調查資料庫（TCS） | a、b 參數校準 | https://srda.sinica.edu.tw/plan/?idx=SRDA.AS028 |
| 8 | **Stroud, N. J. (2008). Media Use and Political Predispositions: Revisiting the Concept of Selective Exposure. *Political Behavior* 30(3), 341–366** | **第一層理論依據（選擇性接觸 / 慣性媒體使用）** | https://link.springer.com/article/10.1007/s11109-007-9050-9 |
| 9 | **Fletcher, R., & Nielsen, R. K. (2018). Are People Incidentally Exposed to News on Social Media? A Comparative Analysis. *New Media & Society* 20(7), 2450–2468** | **第一層→第二層 fallback 理論依據（偶遇接觸,未匹配≠接觸不到）** | https://journals.sagepub.com/doi/abs/10.1177/1461444817724170 |
