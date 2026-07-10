# 领域地图：Agentic Security（从两篇 P0 survey 蒸馏）

> 产出：2026-07-09。来源 = S1 `2606.28450`（LLM agents security **duality**，73p）+ S2 `2510.06445`（**A Survey on Agentic Security**: Applications/Threats/Defenses，59p，附 GitHub Awesome 列表 260+ 篇）。
> 用途 = 你精读 P0 论文前的**领域坐标系**。读每篇深论文时，先在这张图上找到它的位置。
> 引用锚点标 `[S1 §x]`/`[S2 §x]` 便于回溯（对齐项目 cite-or-drop 纪律）。数字来自 survey 正文；OCR 热力图里读不清的已在 §10 标 `待核`。

---

## 0. 怎么用这张图

这个领域只有两年历史（2024–2026）、260+ 篇、**碎片化严重**。两篇 survey 各给一套正交框架，合起来就是坐标系。**别按论文清单顺序读**——先用 §1 的两个坐标轴 + §2 的根因层建心智模型，再让坐标系告诉你哪几篇深论文对本项目真重要（§9）。

---

## 1. 两套正交框架（领域的两个坐标轴）

**坐标轴 A — Agent 的双重身份（S1 duality 的核心贡献）：**
- **Self-security（agent 作靶）**：agent 自身被攻击。← **本项目 AI 侧的主场**。
- **Empowered cybersecurity（agent 作矛/盾）**：用 agent 去做攻防（自动渗透、CTI、漏洞检测、事件响应）。← 本项目**网络侧**沾一点（nmap 切片），但项目定位是"评估陌生系统"而非"造自动渗透 agent"，所以这半边主要作**背景**，不是主线。
- S1 的论点：两者**协同演化**——你想用 agent 做防御（empowered），就先得解决它自己被攻破（self-security），否则防御 agent 本身成了新攻击面 `[S1 §9]`。

**坐标轴 B — 三支柱（S2 的组织方式）：** Applications（红队/蓝队/领域应用）× Threats（威胁）× Defenses（防御）。三者互锁：能力↑ → 攻击面↑ → 防御追。本项目吃的是 **Threats × Defenses 的评估视角**（我来测你有没有这些威胁、防御盖没盖住），不是 Applications（我不造应用）。

**一句话定位本项目在坐标系里的位置**：**self-security 的、以评估/保证为目的的、黑盒红队** —— 落在 A 的左半 × B 的 Threats/Defenses 交叉，且只做"测量+裁定+出可复现保证结论"，不做防御研发本身。

---

## 2. ⭐ 机理根因层 P1–P6（本图最重要的一节）

S1 最有价值的贡献：现有威胁分类都在编目**现象**（"发生了什么"），却**没说清结构性机制**（"为什么反复发生"）。它蒸馏出 6 条**架构性失效根因**，并主张用「**双相分类**」给任何威胁定位——(1) 机理诊断→落到某条根因；(2) 现象定位→落到 endogenous/exogenous/interaction `[S1 §3.1]`。

| 根因 | 名称 | 一句话 | 直接后果（现象） |
|---|---|---|---|
| **P1** | Instruction boundary collapse | control-plane 指令与 data-plane 内容无法分离，单流文本拼接→无 provenance/privilege 概念 | prompt injection、jailbreak（**领域头号根因**） |
| **P2** | State persistence & integrity hazards | 长期记忆/向量库缺 provenance/隔离/可撤销 → 休眠的投毒工件跨会话复活 | memory poisoning、RAG 投毒、backdoor |
| **P3** | Authority amplification via tools | agent 是"代花钱的 deputy"，微小指令偏差→高影响动作；**confused deputy + 违反最小权限** | 工具越权、未授权动作（**头号影响**） |
| **P4** | Untrusted observations & feedback integrity | 不校验输入（工具输出/检索/网页/日志/agent 间消息）的真伪 → 威胁面从"操纵 prompt"移到"操纵证据" | adversarial example、间接注入、检索投毒 |
| **P5** | Long-horizon composition & error amplification | 小的局部偏差沿多步轨迹自回归累积 → 质变为不安全结果；轨迹越长成功率越低 | 多轮升级攻击、规范漂移、reflection 放大偏差 |
| **P6** | Multi-agent emergence & responsibility diffusion | 不安全后果源自集体动态，无单个 agent 可归责 → 需反事实追因 | 协作机制破坏、恶意信息传播、collusion |

> **这一层对本项目的意义**：项目现有控制（PI/TOOL/RAG…）全是**现象级**。给每个控制/Finding 加一个 P1–P6 **根因标签**，就得到 S1 主张的"时间不变"分类——新攻击变种再多，根因就这 6 条。这是低成本高回报的 ontology 升级（详见 §7 缺口 1）。

---

## 3. 攻击面：8 入口 × agent-loop 阶段

S2 把每个攻击映射到"通过哪个通道到达 agent"，标了 **8 个入口** `[S2 §3.1]`：

1. **System prompt** · 2. **User query** —— 前两个是**前-agent 时代就有的**（stateless chatbot 也有），合计 **55% 的攻击**集中在会话输入（因为最好测：不需要工具栈/记忆/多 agent）。
3. **Tool/API response** · 4. **Retrieved content (RAG)** · 5. **Persistent memory** · 6. **Inter-agent message/observation** · 7. **Environment observation** · 8. **Reflection output** —— 后 6 个是 **agent 专属**入口。

关键事实：
- **RAG 是头号自主攻击面**（15 篇）：AgentPoison 在 <1% 投毒率下达 **62.6% 端到端 ASR** `[S2 §3.1]`。
- **Environment observation 是快速崛起面**（14 篇）：绕过文本级过滤，直接操纵被解析的环境。
- **Memory(4) 和 reflection(2) 既最少被攻击、也最少被 benchmark** —— AgentDojo/InjecAgent **完全不测**这两个面。这是领域公开空白，也是本项目的机会/盲区（§7 缺口 2）。

---

## 4. 主导威胁模型（一句话记住）

S2 `[S2 §3.3]`：**一个不持任何特权、黑盒、通过 agent 本就会读的通道操作、目标是让 agent 未授权行动或被欺骗的外部攻击者。**

拆开：
- **访问级别**：70% 黑盒（仅 query 访问）、15% 完全无访问、gray-box 9%、white-box 6%。→ 说明 **agent 默认就结构性脆弱**，无需特权即可严重攻破。
- **所需额外能力**：训练管线访问 10%、工具执行 10%、agent 间通道 7%、记忆写 6%（且多数记忆投毒**靠普通 query** 就够，不需写权限）。
- **攻击目标**（可多选）：**未授权动作 67% + 欺骗/误导 67%** 并列第一 → 内容策略违规 48% → 数据外泄 39% → DoS 15% → 提权/接管 12% → IP 窃取 3%。

> 对本项目：`AI-AGENT-TOOL-01`（未授权动作）和注入类是命中率最高的两个，与文献焦点一致；`COST-01`(DoS) 优先级本就该低。**每个探针应记录它假设的威胁模型**（黑/灰/白盒 + 所需能力），当前 `ai_run_record` 没这个字段（§7 缺口 4）。

---

## 5. 防御全景：10 策略 → 6 结构组合 → 生命周期布局

**10 种防御策略**（S2 统计占比，四轴权衡：scalability / adversarial robustness / latency / coverage）`[S2 §4.3]`：

| 策略 | 占比 | 短板 |
|---|---|---|
| LLM-Based Monitoring（次级模型异步审查） | 40.0% | 高延迟/成本，自身也可被对抗 |
| Input Sanitization & Filtering（周界过滤） | 33.3% | 挡不住语义混淆的间接注入 |
| Red-Team Simulation（自动化红队） | 28.6% | 过度依赖已知向量，难发现 0-day |
| Capability-Scoped Execution（最小权限动态授权） | 24.8% | 协调开销大，错误 gating 会打断长任务 |
| Sandboxing & Formal Verification | 21.0% | 形式化难 scale 到自然语言的开放状态空间 |
| Structured Queries（指令/数据句法隔离） | 17.1% | 模型是概率的，仍能被诱导破格 |
| Cryptographic Verification（provenance/完整性） | 14.3% | 实时加密开销高，需基建整合 |
| Dataset Sanitation & DP（护知识库防投毒） | 11.4% | 过度清洗损效用 |
| Consensus & Vaccine Seeding（分布式决策） | 10.5% | 多 agent 共识 token 成本剧增 |
| Moving Target Defense（动态改执行参数） | 8.6% | 引入不确定性，损可靠性 |

**6 种结构组合**（按主信任边界）`[S2 §4.3.2]`：Base-LLM Alignment（信了正被攻击的组件，遇复杂 jailbreak 灾难性失败）/ External Monitor（高误报）/ Formal Verification / Sandbox-Isolation（**assume-breach，限爆炸半径**）/ Cryptographic-Structural Integrity（**provenance + prompt-data 分离**）/ **Human-in-the-Loop（不可逆动作前的终极 failsafe）**。

**两条领域趋势** `[S2 §1 takeaways]`：
- **security-cost Pareto frontier**：更强防御一律以延迟+token 为代价，没有免费午餐。
- **防御布局正转向 assume-breach**：post-computation monitoring + 全生命周期防护成主流（不再指望周界挡住）。

> 对本项目：项目的 **evidence-integrity(provenance 哈希链) + requires_approval(HITL) + sandbox/白名单执行** 恰好命中"Cryptographic-Structural Integrity + HITL + Sandbox"三个被文献认为最扎实的防御族。这是项目设计与领域共识对齐的强信号（§7）。

---

## 6. 领域级事实与空白（决定你别踩哪些坑）

1. **Benchmark 极度碎片化** `[S2 §3.3.5]`：36 篇 benchmark 论文里命名了 108 个基准/数据集，**92 个只被用过一次（~85% single-use）**。**只有 3 个专用 agentic-security 基准**：**AgentDojo**（4 篇）、**InjecAgent** 和 WebArena（各 3 篇）。后果：两个注入防御**无法跨论文比较**，因为发表数字不共享基准/指标——必须自己重跑。→ **这正是本项目"可复现证据 + 归一化 Finding schema"要填的基建缺口**（§7 超前点）。
2. **agent 专属面最少被测**：memory/reflection 几乎没人 benchmark；query/tool 被过度测。通用基准（AgentDojo/InjecAgent）**只测 query+tool，完全跳过 memory 与 reflection**。
3. **模态偏斜**：文本+代码为主，图像/网络流量/二进制覆盖少；动态模态（音/视频）几乎空白。
4. **backbone 垄断**：GPT 近乎通用底座 → 防御若建在同模型族上会共享脆弱性。
5. **架构在迁移**：从单体 agent → planner-executor / 多 agent 混合。
6. **多轮 & 多 agent 是公开弱项** `[S1 §8]`：多轮攻击"逐步累积毒素再引爆"没有有效防御、数据集也缺；多 agent 恶意传播无统一评估指标（有人提 Information Diffusion Rate 等雏形）。

---

## 7. ⭐ 对照本项目 `ontology_schema.yaml`：对齐 / 超前 / 天真 / 缺失

这是"对着脚手架读"的收益——两篇 survey 反过来审你已建的 schema。

### ✅ 已对齐领域共识（设计是对的）
- 7 个 AI 控制是**现象级分类**，干净映射到文献威胁类：`PI-01`↔注入(根因 P1)、`TOOL-01`↔未授权动作(P3，**文献头号影响 67%**)、`RAG-01`↔检索投毒(P2+P4，**头号自主攻击面**)、`SD-01`↔数据外泄(39%)、`OUT-01`↔下游注入、`COST-01`↔DoS(15%，本就该低优先)。
- `ai_run_record`（n_success/n_runs、非确定）**正面回应**文献痛点：agent 攻击是概率性的，单跑数字无意义。
- `verification` 三正交维 + `requires_approval`(HITL) + `evidence_integrity`(provenance) + 白名单/sandbox 执行 → 命中文献认为最扎实的三防御族（Crypto-Integrity / HITL / Sandbox），且与"assume-breach"趋势一致。

### 🚀 超前 / 差异化被验证（这是卖点，survey 帮你坐实）
- **项目的"可复现证据链（钉 tool_version + invocation_params）+ 归一化 Finding schema"直接填补文献第一大空白：benchmark 碎片化（85% single-use、无法跨论文比较）。** 学术界缺的正是"能跨工具跨运行比较的、可复现的测量基建"——这不是又一个扫描器，是评估层。**S2 §3.3.5 就是你差异化叙事的最佳外部背书。**
- `verification` 的 method⊥verdict⊥approval 三维拆分，比防御 taxonomy 里混作一团更有纪律。

### ⚠️ 天真 / 缺失（按价值排序的待补，这几条是本次阅读的最高回报）
1. **⭐ 缺机理根因层**。控制全是现象级；S1 核心论点=现象分类"欠定结构机制"。**建议给每个 control/Finding 加 `root_cause: [P1..P6]` 字段**，落 S1 的双相分类（机理+现象）。回报：ontology 对新攻击变种"时间不变"，且这是相对现有 AI-security 产品的真差异点。低成本（一个 schema 字段 + 映射表）。
2. **memory/reflection 盲区会被继承**。项目首批 `PI-01`/`RAG-01` 若只薄封装 AgentDojo/InjecAgent，就**继承了它们"不测 memory 与 reflection"的盲区**。至少要：对 memory-poisoning / reflection-manipulation 诚实标 `not_applicable` 或占位，别让报告**暗示覆盖了其实没测的面**（对齐项目"如实报告"+ Finding 四态纪律）。进一步：query-based memory poisoning 是文献明确的开放方向，自研语料补这块=真差异化。
3. **无长/多轮(P5)与多 agent(P6)控制**。现有控制都是单靶黑盒；`PI-01` 提了"单轮/多轮 probe"是好的，但没有**累积/长程危害**控制。P1 清单里的 **AgentHarm/AgentHazard 正是补这块**（"每步局部可接受、累积成害"）——读它们时对应到这里。
4. **控制/`ai_run_record` 缺威胁模型字段**。文献按黑/灰/白盒 + 所需能力刻画攻击者；建议探针记录 `threat_model`（access_level + required_capabilities），否则保证结论说不清"在什么假设下成立"，损可审计性。小改动，大收益。

### 🔧 一个选型提示（喂给你的 P0 阅读 + garak/PyRIT 决策）
规划草案说 AI 切片"薄封装 garak 或 PyRIT"。但 S2 数据显示：**唯一的 3 个专用 agentic 基准是 AgentDojo/InjecAgent/WebArena**，而 garak 偏通用 LLM 扫描、不是 tool-use-over-untrusted-data 场景。本项目 `AI-AGENT-PI-01` 的场景恰是"工具型 agent 处理不可信数据"——**AgentDojo 的原生场景**。所以第一切片的 base 更可能是 **AgentDojo（+ InjecAgent 补间接注入）** 而非 garak。这条留给你精读 AgentDojo 时验证/拍板。

---

## 8. 术语表（读深论文会反复撞到）

- **control-plane / data-plane confusion**：指令面 vs 数据面混淆 = P1 的本质。
- **confused deputy**：被授权组件被诱导滥用其权限（P3 的经典安全学名）。
- **indirect prompt injection**：注入藏在 agent 会读的外部内容里（网页/文档/工具输出），非用户直接输入。
- **ASR (Attack Success Rate)**：攻击成功率，agent 安全的核心度量（对应本项目 `success_rate`）。
- **assume-breach**：假定已被攻破，重心放在限爆炸半径 + 事后监控，而非周界防住。
- **black/gray/white-box threat model**：攻击者对目标模型的访问程度（仅 query / 部分内部 / 全部权重梯度）。
- **planner-executor**：把规划与执行拆成不同 agent 的架构（领域正从单体迁移到此）。
- **endogenous / exogenous / interaction threats**：S1 的现象三分（内生缺陷 / 外部恶意攻击 / 交互动态风险）。

---

## 9. 你精读 P0 的 targeting 建议（哪篇解答哪个问题）

按"读它是为了填哪个空"排，而非按清单序：
1. **AgentDojo (`2406.13352`)** —— 先读。它是你 `PI-01`/`TOOL-01` 切片的**候选 base**；读时验证 §7🔧 的选型判断，并抽出它的 task/injection-task 结构如何归一化进 Evidence。
2. **InjecAgent (`2403.02691`)** —— 间接注入 + 工具 + 私密数据外泄场景，补 AgentDojo。对应 `RAG-01`/`SD-01`。
3. **ToolEmu (`2309.15817`)** —— LM 模拟沙箱，MVP 阶段**不接真高危工具就能测危险行为**，直接服务你"破/诊断陌生系统"又不真造成损害的红队伦理约束。
4. **NIST AI 600-1 + GOV.UK AI assurance** —— 保证层与证据模型的规范骨架；读时把它们的控制/证据要求映射进 `standards` 注册表（对齐 cite-or-drop）。
5. （读完回来讨论）**P1 的 AgentHarm/AgentHazard、Formalizing Agentic Properties `2510.14133`、SAGA `2504.21034`** —— 分别补 §7 缺口 3（累积危害）、缺口 1/4（形式化 RoE/审批态/属性）、以及 agent 身份/授权/委派。这几篇我可在长尾摘要里先给你压缩版。

---

## 10. 待核项（进正式文档/引用前须确认，对齐数据治理硬约束）

- S2 图 7（威胁类×入口热力图）与图末"防御×攻击覆盖矩阵"的**逐格数字** OCR 读不清，本图只用了其文字结论；要引具体数字须回看 PDF 原图。
- 两篇 arXiv 版本较新（S1 `2606.28450`、S2 `2510.06445v3` 2026-06），正式引用前按硬约束核 venue/版本。
- "AgentPoison 62.6% ASR @ <1% poison"、各防御占比、70% 黑盒等数字均转引自 survey，未回溯到原始论文——作背景可用，进项目结论前二次确认。
