# P1/P2 长尾摘要（读它们，好让你不必读原文）

> 产出：2026-07-09。配套 `domain-map-agentic-security.md`（两篇 survey 的领域地图）。
> 每条 = **一句 takeaway → 关键内容 → 落哪个 schema 槽位/缺口 → 借/建 → 待核**。
> 缺口编号沿用领域地图 §7：①缺机理根因层 P1–P6 ②memory/reflection 盲区 ③缺长/多轮+多 agent 累积危害控制 ④控制缺 `threat_model` 字段。
> 分三档：**深读=填缺口**、**中读=注入+评估基建**、**略读=定位/track**。

---

## 档 1 · 深读（直接填 schema 缺口，改设计前须看）

### ⭐ Formalizing the Safety/Security/Functional Properties of Agentic AI (`2510.14133`, ICLR'26 Workshop, Purdue)
**Takeaway**：给 agentic 系统一套**形式化状态机 + 时序逻辑属性**，让"任务生命周期/审批/多 agent 协调"可被形式验证——正是你 RoE/ActionPlan/Finding 状态该抄的骨架。

- 两模型：**Host Agent Model**（顶层：拆任务、经 A2A 委派 agent、经 MCP 调工具，兼 controller+monitor）+ **Task Lifecycle Model**（子任务状态机）。
- **子任务状态集**（直接对标你的 ActionPlan/Finding 生命周期）：`CREATED → AWAITING_DEPENDENCY → READY → DISPATCHING → IN_PROGRESS → COMPLETED / FAILED / RETRY_SCHEDULED / FALLBACK_SELECTED / CANCELED / ERROR`，转移由外部事件（依赖满足/失败信号/timeout）驱动。
- **30 条属性**（16 host + 14 lifecycle），分四类：**liveness**（"提交请求后终会有最终回复"，防死锁/饥饿）/ **safety**（"风险算完前不得提前执行"，防不一致状态）/ **completeness** / **fairness**，全用 temporal logic 表达。

→ **落点**：缺口④的上位——不仅加 `threat_model`，更该给**执行流**一个显式状态机。你现在 `finding_status` 是**结果**四态（pass/fail/na/inconclusive），但**执行过程**（ActionPlan 从计划→审批→执行→证据）没有状态机；这篇给你现成的一套，且 "safety property=前置条件没满足不得执行" 正好形式化你的 `requires_approval` 闸门。
→ **借/建**：概念**借**（状态集+属性分类），落成你自己的 schema 字段（不引入 MCP/A2A 全套）。
→ **待核**：Workshop 论文；30 条属性的完整列表在 Table 1，要逐条抄前回看 PDF。

### SAGA: Security Architecture for Governing AI Agentic Systems (`2504.21034`, Northeastern)
**Takeaway**：多 agent 的**身份/授权/委派**治理参考架构——不是给你封装的工具，是"一个受治理的 agent 系统长什么样"的**评估标尺**（你测目标系统时对照它缺了哪层）。

- **Provider**（中央注册实体）持有 agent 联系方式 + **用户定义的 Access Contact Policy**；用**密码学派生的访问控制 token**（从一次性密钥 OTK 派生）对 inter-agent 通信做细粒度授权；agent 间走 TLS、不经 Provider（可扩展）。
- 卖点：**user-controlled agent lifecycle**（用户对自己 agent 有全程 oversight），且实测开销极小、不损任务效用——填补"以往身份/授权方案全是纯理论"的空白。

→ **落点**：`AI-AGENT-TOOL-01`（工具越权）+ 未来多 agent 控制的**判定基线**——测目标 agent 有没有：可撤销授权 / 最小权限 token / 委派链校验 / 用户 oversight。也给 `standards`-类注册表一个"agent 治理良好实践"来源。
→ **借/建**：作**参考模型建**（写进控制的 evidence_requirements），不封装 SAGA 本体（它是部署期治理框架，非黑盒测试器）。

### AgentHarm (`2410.09024`, ICLR'25, Gray Swan + **UK AI Security Institute**)
**Takeaway**：110 个**显式恶意** agent 任务的公开基准，测"拒绝 + 越狱后是否仍保持多步能力"——补缺口③的**危害语料**，且 **UK AISI 出品 = 你 UK 治理叙事的强背书**。

- 110 任务（+augmentation 共 440），**11 类危害**（fraud / cybercrime / harassment …）。评分不只看拒不拒，还看**越狱后 agent 能否维持能力完成多步任务**（单纯拒绝拿不了高分）。
- 三个发现：①头部 LLM **不越狱就相当顺从**恶意 agent 请求；②通用越狱模板能迁移到 agent；③越狱后能维持连贯的多步恶意行为。

→ **落点**：`AI-AGENT-COMP-01`（越界/滥用）语料来源；`attack_corpus_governance.safety_class` = **`potentially_harmful`**（须加密存储、限访问、禁进公开仓）。填缺口③"每步局部可接受、累积成害"的一半（越狱维持能力）。
→ **借/建**：语料**借**（HuggingFace 公开），归一化进你的场景库并打 provenance+license+safety_class。
→ **待核**：许可（AISI/Gray Swan 发布条款）；含 offensive 内容，取用须走双用途边界。

### AgentHazard (`2604.02947`, Alibaba/Fudan)
**Takeaway**：2,653 个 **computer-use agent** 实例，每个把恶意目标拆成**逐步局部合法、合起来越界**的序列——这是缺口③（长程累积危害 P5）最精准的靶。

- 每实例 = 恶意目标 + 一串"单看每步都合规"的操作步骤，测 agent 能否**从累积上下文/重复工具调用/跨步依赖中识别并中断**危害。
- 结果：Claude Code + Qwen3-Coder **ASR 73.63%** → "**模型对齐单独不保证 agent 安全**"（呼应领域地图 §5 "Base-LLM Alignment 灾难性失败"）。

→ **落点**：**缺口③的核心证据**——你现有控制全是单步/单靶，这篇证明真正危险在累积。建议新增控制 `AI-AGENT-CUM-01`（累积/长程危害），根因标 **P5**。评估必须"报轨迹级"而非单步（对齐项目"报曲线不报单点"）。
→ **借/建**：语料**借**（网站公开），`safety_class=potentially_harmful`。
→ **待核**：v1 单版本、2026-04 新论文，数字与许可须核。

---

## 档 2 · 中读（注入深化 + 评估基建，喂你 P0 精读与 llm_judge 设计）

### ⭐ Indirect Prompt Injections: Firewalls All You Need, or Stronger Benchmarks? (`2510.05244`, ServiceNow/Mila)
**Takeaway**：一个简单的**双 firewall**（Tool-Input Minimizer + Tool-Output Sanitizer）就在 AgentDojo/ASB/InjecAgent/τ-Bench **全部刷到"完美安全"**——**结论不是"防御解决了"，而是"这些基准太弱、极易饱和"**。

- 揭露现有基准**三宗罪**：成功度量有缺陷、实现有 bug、**攻击太弱**。给 AgentDojo/ASB 打了补丁，提**三段级联攻击**（标准注入 + 二阶 + 自适应）作更硬的评估。

→ **落点**：**对 `AI-AGENT-PI-01` 是最重要的一条警示**——你若薄封装 AgentDojo 跑出"pass"，**那几乎不是安全证据**。必须：①`ai_run_record` 记录用的**攻击强度/自适应等级**，别把"过弱基准"当结论；②场景库纳入二阶+自适应攻击；③报 security-utility 权衡曲线，不报单点 ASR。直接支撑项目"报曲线+adaptive corpus"纪律。
→ **借/建**：firewall 是**防御**（你测别人的防御，不必自建）；但**三段攻击策略 + 基准缺陷清单**要**建**进你的 corpus 治理与度量设计。
→ **待核**："perfect security" 是在其修正后的基准上；跨模型是否成立须看原文。

### Towards Effective Offensive Security LLM Agents / CTFJudge (`2508.05674`, NYU)
**Takeaway**：给 **LLM-as-judge** 和超参一份实操配方——直接喂你 `verdict: llm_judge` 与 `ai_run_record`。

- **CTFJudge**：LLM 评判 agent 轨迹、跨解题步骤细粒度打分；**CCI**（CTF Competency Index）度量部分正确性。
- **超参发现**：temperature / top-p / max-token **显著影响** agent 表现 → 印证你 `ai_run_record` 钉死 temp/seed 的必要性。

→ **落点**：`verdict_modes.llm_judge`（rubric 打分 + 保留 prompt/response 证据 + 低置信升级人工）的设计参考；`ai_run_record` 的 temp/top-p/max-token 应全部钉死并入证据。
→ **借/建**：CTFJudge 思路**借**（LLM-as-judge over trajectory），落成你的 llm_judge 实现；CTFTiny/CCI 是 offensive 能力评估，**非你主线**（你不造攻击 agent），仅作 judge 方法参考。

### CAIBench (`2510.24317`, Alias Robotics)
**Takeaway**：cyber AI 的元基准，核心发现 **"知识 ≠ 能力"**——LLM 安全知识题刷到 70%，多步对抗只有 20–40%。

- 5 类 10k+ 实例（Jeopardy CTF / A&D CTF / Cyber Range / 知识 / 隐私）；scaffolding+模型匹配对 A&D 结果影响达 **2.6× 方差**。

→ **落点**：**评估哲学背书**——你的保证结论别停在"模型知不知道"，要测"多步能不能做/防"。支撑 `scoring` 按多步/操作点 rollup 而非知识覆盖。scaffolding 影响大 → `evidence_integrity` 钉死 scaffold/invocation_params 是对的。
→ **借/建**：定位参考，不封装（robotics/CTF 靶非你主线）。

### Not what you've signed up for (`2302.12173`, CISPA/Saarland, 2023)
**Takeaway**：**间接注入的奠基论文**——首次系统证明"藏在 agent 会读的外部内容里的指令"能劫持真实 LLM 应用。读你 P0 的 InjecAgent 前的背景。

→ **落点**：`AI-AGENT-PI-01`/`RAG-01`/`OUT-01` 的威胁建模根据（根因 P1+P4）；`standards`/背景引用。
→ **借/建**：背景文献，无代码可借。

---

## 档 3 · 略读（定位/track，知道存在即可，暂不进设计）

- **Cybench (`2408.08926`, Stanford, ICLR'25)** — cyber 能力评估框架：**task/subtask/environment/agent-scaffold** 四件套 + first-solve-time 难度校准。→ 若做**网络侧** agent 探针的 scaffold 结构，回来读这篇；非 AI 自安全主线。
- **CYBERSECEVAL 3 (`2408.01605`, Meta)** — 8 类风险分两组（对第三方 / 对应用方）+ 新增 offensive（自动社工、放大人工攻击、自主攻击）。→ 风险分类参考，可校准你的控制族边界。
- **CTFusion (`2605.11504`, MCP-based CTF)** — 核心贡献 = **数据污染问题**：CTF 复用旧题→agent 靠 web search 作弊。→ 喂 `attack_corpus_governance`：语料要防污染、记 provenance、live 化。
- **Evolution of Agentic AI (`2512.06659`, Microsoft)** — 单 LLM→多 agent→自主管线的路线；强调 SOC 需 **grounded data / reproducibility / accountable workflows**。→ 与你保证/可复现叙事同频，作 roadmap 措辞参考。
- **AgentSOC (`2604.20134`)** — 多层 agentic SOC 自动化框架。→ **对 MVP 太宽**（reading list 已注），track。
- **Agentic AI for Cyber Resilience (`2512.22883`, Li & Zhu)** — 系统论/博弈论，主张从 prevention 转向 **resilience**（anticipate/withstand/recover/learn）。→ 长期框架措辞，非近期编码输入。
- **AgentDyn (`2602.03117`, WUSTL)** — "你的防御在真实**动态**环境里可部署吗"：测防御在开放/动态条件下的退化。→ 语料后期**动态化**升级参考；与**项目二注入防御**更相关，可 `ln -s` 引 [[project-injection-defense-plan]]。
- **⭐ Which Defense Closes Which Threat? (`2606.02822`)** — 测 **OWASP-LLM-Top-10 的防御归因**：现有 BAS 基准只报一个聚合覆盖数，**掩盖了"哪个防御族关掉哪个威胁"**；用 L0–L3 endpoint lattice 做单轴消融，还测 paraphrase 脆性（refusal 过滤器一改写就崩）。→ **与你 `scoring.rollup_axes`（按 ce_area/csf2/domain 分轴而非单一覆盖数）哲学高度一致**；且"paraphrase 脆性"是场景库该纳入的鲁棒性测法。半档提上来的略读——做 defense↔control 映射时回看。

---

## 这批摘要替你决了什么（回接领域地图 §7 缺口）

| 缺口 | 证据来自 | 建议动作 |
|---|---|---|
| ① 缺机理根因层 P1–P6 | 两篇 survey（已在地图） | 给 control/Finding 加 `root_cause: [P1..P6]` 字段 |
| ② memory/reflection 盲区 | Firewalls + survey | AgentDojo 覆盖不到的面诚实标 `not_applicable`，别暗示覆盖 |
| ③ 缺长/多轮+多 agent 累积危害控制 | **AgentHazard**(ASR 73.63%) + AgentHarm | 新增 `AI-AGENT-CUM-01`（根因 P5），评估报轨迹级 |
| ④ 控制缺 threat_model / 执行状态机 | **Formalizing** + survey 威胁模型 | 加 `threat_model` 字段 + 给 ActionPlan 一个显式生命周期状态机 |
| 附：注入"pass"≠安全 | **Firewalls**（基准易饱和） | `ai_run_record` 记攻击强度/自适应等级；场景库纳二阶+自适应 |
| 附：llm_judge 怎么做 | **CTFJudge** | rubric+轨迹打分+保留证据+低置信升级；钉死 temp/top-p |
| 附：报归因不报聚合 | **Which Defense** | 坐实 `scoring.rollup_axes` 分轴设计 |

**未解 / 待你精读 P0 才能定**：garak vs AgentDojo 的 base 选型（地图 §7🔧）——需你读 AgentDojo 原文确认其 task/injection 结构能否干净归一化进 Evidence。

## 待核清单（进正式文档前，对齐数据治理硬约束）
- AgentHarm / AgentHazard 含 offensive 内容：许可 + 双用途边界须核，取用即走加密/限访问。
- 多篇为 2026 新 arXiv（`2604.02947` / `2602.03117` / `2606.02822` / `2510.14133`v2）：venue/版本进引用前二次确认。
- 所有转引数字（73.63% ASR、2.6× 方差、CAIBench 20–40% 等）来自各自 abstract，未回溯原始实验，作背景可用、进结论前确认。
