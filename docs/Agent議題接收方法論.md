# Agent 新聞接收與記憶寫入方法論 v3
## 單向流程：輸入新聞 → 依文獻規則 → 寫入 3,000 位 Agent 記憶

**對應資料集：** 台北市虛擬市民 Persona（N=3,000，24 欄位）
**範圍界定：** 不模擬平台演算法、不模擬 agent 間互動；新聞 raw data 不需平台來源欄位
**更新日期：** 2026-06-12

---

## 一、設計原則

1. **理論骨幹單一且公認**：全流程建立在 Zaller (1992) 的 RAS 模型（Receive–Accept–Sample，接收–接受–取樣）之上。此書被學界稱為 V. O. Key 以降最重要的民意研究著作，正是在回答「個人如何把媒體訊息轉化為政治意見」這個問題，與本專案的需求完全同構。
2. **文獻決定方向，資料決定參數**：每條規則的「方向」由論文界定；需要數值處，優先取自 persona 欄位既有的官方統計與民調基底（與 24 欄位建構方法論同一原則），不引入無文獻依據的自由參數。
3. **不依賴新聞來源欄位**：RAS 模型中，個人是否接收一則訊息取決於其**政治覺察程度**（political awareness），而非訊息來自哪個平台——這使本設計天然不需要新聞 raw data 帶有平台/來源欄位。

---

## 二、總體流程（RAS 骨幹）

```
新聞 raw data（純文字即可）
   │
   ▼
Step 1  新聞自動標註（議題分類、框架、立場）          ← Entman 1993; Gilardi et al. 2023
   │
   ▼
Step 2  接收判定 Receive：誰會注意到這則新聞           ← Zaller 1992 接收公理; Krosnick 1990
   │
   ▼
Step 3  接受評價 Accept：接收者如何解讀（同意/反駁/存疑） ← Zaller 1992 抗拒公理;
   │                                                      Taber & Lodge 2006; Vallone et al. 1985
   ▼
Step 4  記憶寫入 Encode：以「個人化解讀」存入記憶流      ← Park et al. 2023
   │
   ▼
Step 5  民調作答 Sample：從可及記憶中取樣形成意見        ← Zaller 1992 取樣公理; Argyle et al. 2023
```

---

## 三、五步驟細節與欄位對應

### Step 1　新聞自動標註（前處理）

對每則輸入新聞，以 LLM 標註三個屬性（新聞本身不需任何 metadata）：

| 標註項 | 內容 | 依據 |
|---|---|---|
| 議題分類 | 對映資料集既有 8 大議題類（ECO/HSG/XS/ENV/WEL/EDU/SOC/GOV） | 議程設定理論：媒體議題類別決定公眾注意的對象（[McCombs & Shaw 1972](https://academic.oup.com/poq/article-abstract/36/2/176/1853310)） |
| 框架四要素 | 問題界定、因果歸因、道德評價、解方建議 | 框架理論的標準操作化定義（[Entman 1993](https://academic.oup.com/joc/article-abstract/43/4/51/4160153)） |
| 政治立場分數 | 對主要政黨/兩岸立場之傾向（−1 ~ +1）與情緒強度 | 立場偵測為標準內容分析任務 |

**LLM 標註的效度依據**：[Gilardi, Alizadeh & Kubli (2023, PNAS)](https://www.pnas.org/doi/10.1073/pnas.2305016120) 以 6,183 則推文與新聞實測，ChatGPT 在議題分類、立場、框架偵測等標註任務上準確率超過人類群眾外包約 25 個百分點，且編碼者間一致性高於受訓標註員——LLM 做新聞標註有同儕審查級的效度支持。

### Step 2　接收判定（Zaller 接收公理）

> Zaller 接收公理（A1）：個人政治覺察程度越高，越可能接收到（注意並理解）一則政治訊息。

每位 agent 對每則新聞計算**接收機率**，由兩個文獻成分構成：

1. **政治覺察（general awareness）**——Zaller 以政治知識測量，本資料集以既有欄位組成代理指標：**教育程度**（主成分，文獻標準代理）＋**媒體平台數**（資訊環境豐富度）＋**關注議題標籤數**（政治興趣）。接收機率對覺察程度採單調遞增的 logistic 函數——此函數形式直接沿用 Zaller 書中的實證設定，非自創。
2. **議題公眾（issue publics）**——[Krosnick (1990, Political Behavior)](https://link.springer.com/article/10.1007/BF00992332) 證明公眾由眾多「單一議題熱衷者」組成：對個人重要的議題會被頻繁思考、高度注意。操作化：新聞的議題分類**命中該 agent 的關注議題/子議題標籤**，或命中其**利益關聯欄位**（房產持有→HSG、產業別→對應產業議題、月收入→ECO/WEL、居住地→地方議題、族群→族群議題），接收機率提升；兩者皆未命中者僅依一般覺察接收。

此步驟產生的異質性完全來自 24 欄位既有資料，無需新增假設。

### Step 3　接受評價（Zaller 抗拒公理 ＋ 動機性推理)

> Zaller 抗拒公理（A2）：人會抗拒與其政治傾向不一致的論點——但前提是他有足夠的政治覺察去辨識訊息與自身立場的關係。

接收到新聞的 agent，依下列文獻規則生成**個人化評價**（appraisal），這是寫入記憶的內容，不是新聞原文：

| 規則 | 內容 | 依據 |
|---|---|---|
| 先驗態度效應 | 與自身立場（政黨傾向、國家認同）一致的論點被評為較有力；不一致者被貶低 | [Taber & Lodge (2006, AJPS)](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-5907.2006.00214.x) 實驗實證 |
| 反駁偏誤 | 對立訊息不是被忽略，而是被「反駁後存入」——agent 記住的是「那則假新聞/帶風向報導」 | 同上（disconfirmation bias） |
| 敵意媒體效應 | 同一則中性新聞，深色立場者（國家認同 1–3 或 8–10）傾向解讀為「偏袒對方」 | [Vallone, Ross & Lepper (1985, JPSP)](https://www.semanticscholar.org/paper/6d7734416d81c1b45fb571d6183f350334105261) |
| 覺察×傾向交互 | 低覺察者不抗拒（照單全收）；高覺察且立場深者抗拒最強 | Zaller (1992) A2 的核心交互作用 |
| 厭惡政黨 | 涉及厭惡政黨的新聞：負面內容易被接受、正面內容被反駁 | 先驗態度效應在負面黨性上的直接應用（Taber & Lodge 2006） |
| 世代共鳴 | 新聞與其政治印記事件同構時（如選舉爭議 vs 兩顆子彈），情緒強度與重要性提高 | [Mannheim (1952)](https://en.wikipedia.org/wiki/The_Problem_of_Generations) 政治世代理論（欄位報告既有文獻） |

實作上：將上述規則寫入評價生成的 prompt 規則層，由 LLM 以該 agent 的 persona 欄位＋新聞標註結果生成評價文字與態度方向。

### Step 4　記憶寫入（生成式 agent 標準架構）

每筆記憶以結構化物件存入該 agent 的記憶流（memory stream）：

```json
{
  "新聞摘要": "（經 Step 3 個人化解讀後的版本，非原文）",
  "評價": "同意／反駁／存疑 ＋ 評價文字",
  "重要性分數": "議題命中與利益關聯計分（Step 2 之 Krosnick 成分）",
  "情緒強度": "立場衝突程度＋世代共鳴",
  "時間戳": "新聞日期"
}
```

檢索時按**新近性 × 重要性 × 相關性**三項加權——此記憶架構與檢索函數（含新近性之指數衰減）完整沿用 [Park et al. (2023) Generative Agents](https://arxiv.org/abs/2304.03442)，為 LLM agent 記憶的標準範式（ACM UIST，引用數千次），無需自行設計。

### Step 5　民調作答（Zaller 取樣公理）

> Zaller 取樣/回答公理（A3/A4）：人回答民調時，並非讀取固定態度，而是從「當下可及的考量（considerations）」中取樣平均。

民調作答時，agent 從記憶流檢索與題目相關的記憶（Step 4 的檢索函數），連同 persona 欄位作答。這正是 RAS 對「同一人不同時點答案會變」的解釋——新近寫入的新聞記憶改變了可及考量的組成，民意變化由此自然湧現，不需外加規則。

人口條件化作答的效度依據：[Argyle et al. (2023, Political Analysis)](https://www.cambridge.org/core/journals/political-analysis/article/out-of-one-many-using-language-models-to-simulate-human-samples/035D7C8A55B237942FB6DBAD7CAA4E49) 的矽基取樣（algorithmic fidelity）框架，與本資料集的設計目標一致。

---

## 四、欄位使用總表

| 步驟 | 使用欄位 | 文獻 |
|---|---|---|
| Step 2 接收：政治覺察 | 教育程度、媒體平台數、關注議題標籤數 | Zaller 1992 |
| Step 2 接收：議題公眾 | 關注議題/子議題、房產持有、產業別、月收入、居住地、族群 | Krosnick 1990 |
| Step 3 評價：立場 | 政黨傾向、國家認同、厭惡政黨 | Zaller 1992; Taber & Lodge 2006; Vallone et al. 1985 |
| Step 3 評價：共鳴 | 政治世代、政治事件印記、社會價值觀（CO/ST、主類型） | Mannheim 1952; Schwartz 1992 |
| Step 4 重要性計分 | 同 Step 2 議題公眾欄位＋年齡組、婚姻（生命歷程議題） | Krosnick 1990; Elder 1994 |
| Step 5 作答 | 全部欄位＋記憶流 | Zaller 1992; Argyle et al. 2023 |

未使用：分裂投票傾向（屬投票行為輸出端）、職業（已由產業別與教育涵蓋）。

---

## 五、自由參數聲明（給審視者）

本方法論僅有兩處需要數值參數，且均有處理方式：

1. **接收函數的斜率/截距**（Step 2 logistic）：函數形式來自 Zaller 原書；參數不憑空設定，以 TCS（[臺灣傳播調查資料庫](https://srda.sinica.edu.tw/plan/?idx=SRDA.AS028)）「新聞接觸頻率 × 教育 × 年齡」交叉分布校準，使模擬接收率對齊台灣實測。
2. **記憶衰減率**（Step 4）：直接沿用 Park et al. (2023) 原論文之指數衰減設定。

其餘規則皆為方向性規則（誰更注意、誰會反駁），方向全部來自上述文獻，並對所有參數做 ±50% 敏感度分析以證明結論穩健。

---

## 六、預期質疑與回應（Q&A 備查）

**Q1：新聞沒有平台來源，怎麼決定誰看得到？**
A：RAS 模型中接收的決定因素是「個人政治覺察」而非「訊息管道」（Zaller 1992, A1）。媒體習慣欄位在本設計中作為覺察代理指標的一部分，而非管道模擬——因此不需要來源欄位。

**Q2：用 LLM 標註新聞議題和立場，可靠嗎？**
A：Gilardi et al. (2023, PNAS) 實測 LLM 在議題、立場、框架標註上優於人類群眾外包 25 個百分點。可另抽 5–10% 樣本人工複核計算一致性，附在報告中。

**Q3：為什麼不是所有 agent 都收到同一則新聞？**
A：實證上政治訊息觸達本來就高度不均——Zaller 與 Krosnick 均證明注意力由覺察程度與議題重要性決定。全員等量接收反而違反文獻。

**Q4：agent 會不會被假設成只接受同溫層訊息？**
A：不會。Taber & Lodge (2006) 的發現是「對立訊息被接收但被反駁」，本設計照此實作：對立新聞仍寫入記憶，只是帶著負面評價——這比單純過濾更貼近實證。

**Q5：民意怎麼「變」？**
A：不外加任何態度改變規則。新記憶改變了作答時可取樣的考量組成（Zaller A3/A4），民意變化是湧現結果——這正是 RAS 模型解釋真實民調波動的機制。

**Q6：整體效度如何驗證？**
A：三層——(1) 分布層：模擬民調 vs TPOC 真實民調（Argyle 2023 的 algorithmic fidelity 標準）；(2) 事件層：以已發生的台北政治事件回測輿情方向（方法參照 [ElectionSim](https://arxiv.org/abs/2410.20746) 之 PPE 基準）；(3) 穩健層：參數敏感度分析。

---

## 七、參考文獻

| # | 文獻 | 角色 | 連結 |
|---|---|---|---|
| 1 | Zaller, J. R. (1992). *The Nature and Origins of Mass Opinion.* Cambridge UP | 全流程骨幹（RAS 模型） | https://www.cambridge.org/core/books/nature-and-origins-of-mass-opinion/70B1485D3A9CFF55ADCCDD42FC7E926A |
| 2 | Entman, R. M. (1993). Framing. *J. of Communication* 43(4) | 新聞框架標註 | https://academic.oup.com/joc/article-abstract/43/4/51/4160153 |
| 3 | McCombs & Shaw (1972). Agenda-Setting. *POQ* 36(2) | 議題分類依據 | https://academic.oup.com/poq/article-abstract/36/2/176/1853310 |
| 4 | Gilardi, Alizadeh & Kubli (2023). *PNAS* 120(30) | LLM 標註效度 | https://www.pnas.org/doi/10.1073/pnas.2305016120 |
| 5 | Krosnick, J. A. (1990). Issue Publics. *Political Behavior* 12 | 議題注意力規則 | https://link.springer.com/article/10.1007/BF00992332 |
| 6 | Taber & Lodge (2006). Motivated Skepticism. *AJPS* 50(3) | 評價生成規則 | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-5907.2006.00214.x |
| 7 | Vallone, Ross & Lepper (1985). Hostile Media. *JPSP* 49(3) | 深色選民解讀規則 | https://www.semanticscholar.org/paper/6d7734416d81c1b45fb571d6183f350334105261 |
| 8 | Park et al. (2023). Generative Agents. *ACM UIST* | 記憶流架構與檢索 | https://arxiv.org/abs/2304.03442 |
| 9 | Argyle et al. (2023). Out of One, Many. *Political Analysis* 31(3) | 矽基取樣效度框架 | https://www.cambridge.org/core/journals/political-analysis/article/out-of-one-many-using-language-models-to-simulate-human-samples/035D7C8A55B237942FB6DBAD7CAA4E49 |
| 10 | ElectionSim (2024). arXiv | 事件級驗證方法 | https://arxiv.org/abs/2410.20746 |
| 11 | 臺灣傳播調查資料庫（TCS） | 接收參數校準 | https://srda.sinica.edu.tw/plan/?idx=SRDA.AS028 |
| 12 | Mannheim (1952)、Elder (1994)、Schwartz (1992) | 共鳴與重要性（沿用欄位報告文獻） | 見 field_construction_report 文獻一覽 |
