# Agent 議題接收方法論
## 根據 Persona 欄位決定每個 Agent 看到什麼新聞

---

## 一、總體架構

```
真實新聞/議題
   │
   ▼
① 議題封裝（同一事件 × 多種媒體框架版本）
   │
   ▼
② 曝光機率模型（依 persona 欄位計算每個 agent 看到哪個版本、看不看得到）
   │
   ▼
③ 演算法饋送（社群媒體使用者的個人化 feed）
   │
   ▼
④ 人際/網絡二次擴散（沒直接看到新聞的 agent 從別人那裡聽到）
   │
   ▼
⑤ 寫入 agent 記憶 → 互動討論 → 民調作答
```

---

## 二、使用哪些 Persona 欄位（欄位 → 機制對應表）

| Persona 欄位 | 在議題接收中的作用 | 理論依據 |
|---|---|---|
| **媒體習慣**（核心欄位） | 決定管道組合：電視/報紙/廣播/網路新聞/社群/LINE 群組的接觸機率 P(管道\|agent) | 選擇性接觸理論（Stroud 2008） |
| **年齡** | 調節數位 vs 傳統媒體比例：18–29 歲偏社群接收政治資訊，50 歲以上偏電視/報紙 | 臺灣傳播調查資料庫（TCS）實證分布 |
| **教育程度、收入、職業** | 決定新聞接觸總量與硬新聞（政治/財經）vs 軟新聞比例；政治興趣 → 主動搜尋議題的機率 | 知識落差/媒體使用研究（TCS） |
| **政黨傾向、國家認同** | 選擇性接觸加權：同立場媒體的曝光機率加權提高、對立媒體降低（建議加權倍率 1.5–3x，可校準） | Stroud 2008；Bakshy et al. 2015 |
| **居住地、族群分布、地方派系、宗親** | 地方新聞曝光、人際傳播權重、所屬社群的意見領袖是誰 | 兩級傳播理論（Katz 1957） |
| **歷年投票紀錄、政治事件、民主歷史印記** | 議題顯著性權重：與自身政治記憶相關的議題更容易被注意、記住 | 議題設定理論（McCombs & Shaw 1972） |
| **性別、婚姻狀況** | 議題類別興趣差異（育兒/教育/長照/兵役等議題的注意力權重） | 媒體使用人口學差異（TCS） |
| **隱性變數**（房產、產業、宗教信仰） | 特定議題敏感度開關：房價、能源、勞工、宗教爭議等議題對相關 agent 強制提高曝光與顯著性 | 自身利益關聯性（issue salience） |

---

## 三、五步驟方法論

### Step 1 議題封裝（Issue Packaging）
同一事件不要只做一個版本。依台灣媒體光譜製作 3–5 個「框架版本」（不同標題、語調、歸因），例如同一條新聞的偏綠媒體版/偏藍媒體版/中立版/社群懶人圖版。Agent 接收到的是「他的媒體會怎麼報」，不是原始事實。

- 依據：框架理論 Entman (1993), *Framing: Toward Clarification of a Fractured Paradigm* — https://academic.oup.com/joc/article-abstract/43/4/51/4160153
- 議題設定 McCombs & Shaw (1972)，媒體決定大眾「想什麼」— 概述見 https://en.wikipedia.org/wiki/Agenda-setting_theory

### Step 2 曝光機率模型（Exposure Model）
對每個 agent × 每則議題計算：

```
P(曝光) = 管道觸達率(媒體習慣×年齡×教育)
        × 選擇性接觸加權(政黨傾向×國家認同 vs 媒體立場)
        × 議題顯著性(投票紀錄×隱性變數×居住地)
```

用加權隨機抽樣決定該 agent 是否看到、看到哪個框架版本。參數用真實調查資料校準（見第四節）。

- 選擇性接觸：Stroud (2008), *Media Use and Political Predispositions* — https://www.researchgate.net/publication/226564066_Media_Use_and_Political_Predispositions_Revisiting_the_Concept_of_Selective_Exposure
- 同溫層實證：Bakshy, Messing & Adamic (2015, Science)，意識形態決定臉書上看到的新聞 — 相關綜述 https://web.stanford.edu/class/comm1a/readings/messing-selective-exposure.pdf

### Step 3 演算法饋送（Algorithmic Feed，限社群媒體使用者）
媒體習慣含社群的 agent，額外模擬 feed 排序（按讚數/追蹤關係/互動歷史排序貼文），這是 LLM 社會模擬的標準做法：

- Törnberg et al. (2023), *Simulating Social Media Using LLMs to Evaluate Alternative News Feed Algorithms* — https://arxiv.org/abs/2310.05984
- OASIS（百萬級 agent 社群模擬，含推薦系統模組，開源可直接參考實作）— 論文 https://arxiv.org/abs/2411.11581 ｜ 程式碼 https://github.com/camel-ai/oasis

### Step 4 人際/網絡二次擴散（Two-Step Flow）
沒被 Step 2–3 觸達的 agent，仍可能從家人、宗親、地方派系網絡「聽到」議題（帶著轉述者的立場）。在 agent 間建立社會網絡（依居住地/族群/宗親欄位連邊），由意見領袖節點轉傳。

- 兩級傳播：Katz (1957), *The Two-Step Flow of Communication* — https://academic.oup.com/poq/article-abstract/21/1/61/1886822
- 意見動力學基礎模型（有限信任）：Hegselmann & Krause (2002) — https://www.jasss.org/5/3/2.html
- LLM agent 版意見動力學：Chuang et al. (2023), *Simulating Opinion Dynamics with Networks of LLM-based Agents* — https://arxiv.org/abs/2311.09618

### Step 5 接收後寫入記憶（Memory & Retrieval）
議題以「該 agent 看到的框架版本＋接收管道＋轉述者」寫入 agent 的記憶流（memory stream），之後互動討論與民調作答時，按「新近性 × 重要性 × 相關性」檢索。真實新聞內容可用 RAG 接入避免幻覺。

- 記憶架構標準範式：Park et al. (2023), *Generative Agents: Interactive Simulacra of Human Behavior* — https://arxiv.org/abs/2304.03442
- RAG：Lewis et al. (2020), *Retrieval-Augmented Generation* — https://arxiv.org/abs/2005.11401

---

## 四、參數校準與驗證

1. **媒體習慣分布校準**：用「臺灣傳播調查資料庫 TCS」的年齡×教育×媒體使用交叉分布設定 P(管道|agent)，不要憑感覺給 — https://srda.sinica.edu.tw/plan/?idx=SRDA.AS028 ｜ https://crctaiwan.dcat.nycu.edu.tw/AnnualSurvey.asp
2. **Silicon sampling 驗證**：以人口屬性條件化 LLM 後，比對模擬作答分布與真實民調分布（algorithmic fidelity 檢驗）— Argyle et al. (2023), *Out of One, Many*, Political Analysis — https://www.cambridge.org/core/journals/political-analysis/article/out-of-one-many-using-language-models-to-simulate-human-samples/035D7C8A55B237942FB6DBAD7CAA4E49
3. **選舉級驗證基準**：ElectionSim 用百萬級選民池模擬美國大選，州級準確率 47/51，可借鏡其 PPE 評測法 — https://arxiv.org/abs/2410.20746 ｜ https://github.com/amazingljy1206/ElectionSim
4. **個體級驗證**：Park et al. (2024), *Generative Agent Simulations of 1,000 People*，以訪談建構 agent，GSS 重測一致性達真人自身的 85% — https://arxiv.org/abs/2411.10109
5. **平台級參考**：AgentSociety（清華，萬級 agent 社會模擬開源平台）— https://arxiv.org/abs/2502.08691 ｜ https://github.com/tsinghua-fib-lab/agentsociety

---

## 五、參考文獻總表

| # | 文獻 | 用途 | 連結 |
|---|---|---|---|
| 1 | Entman (1993) Framing | 議題多框架封裝 | https://academic.oup.com/joc/article-abstract/43/4/51/4160153 |
| 2 | McCombs & Shaw (1972) Agenda-Setting | 議題顯著性 | https://en.wikipedia.org/wiki/Agenda-setting_theory |
| 3 | Stroud (2008) Selective Exposure | 政黨傾向×媒體選擇 | https://www.researchgate.net/publication/226564066_Media_Use_and_Political_Predispositions_Revisiting_the_Concept_of_Selective_Exposure |
| 4 | Katz (1957) Two-Step Flow | 人際二次擴散 | https://academic.oup.com/poq/article-abstract/21/1/61/1886822 |
| 5 | Hegselmann & Krause (2002) | 意見動力學 | https://www.jasss.org/5/3/2.html |
| 6 | Park et al. (2023) Generative Agents | 記憶與檢索架構 | https://arxiv.org/abs/2304.03442 |
| 7 | Park et al. (2024) 1,000 People | 個體級驗證 | https://arxiv.org/abs/2411.10109 |
| 8 | Argyle et al. (2023) Silicon Sampling | 人口條件化與驗證 | https://www.cambridge.org/core/journals/political-analysis/article/out-of-one-many-using-language-models-to-simulate-human-samples/035D7C8A55B237942FB6DBAD7CAA4E49 |
| 9 | Törnberg et al. (2023) | News feed 演算法模擬 | https://arxiv.org/abs/2310.05984 |
| 10 | OASIS (2024) | 大規模社群模擬實作 | https://arxiv.org/abs/2411.11581 |
| 11 | ElectionSim (2024) | 選舉模擬與驗證基準 | https://arxiv.org/abs/2410.20746 |
| 12 | Chuang et al. (2023) | LLM 意見動力學 | https://arxiv.org/abs/2311.09618 |
| 13 | AgentSociety (2025) | 社會模擬平台 | https://arxiv.org/abs/2502.08691 |
| 14 | Lewis et al. (2020) RAG | 新聞內容接地 | https://arxiv.org/abs/2005.11401 |
| 15 | 臺灣傳播調查資料庫 TCS | 媒體習慣參數校準 | https://srda.sinica.edu.tw/plan/?idx=SRDA.AS028 |
