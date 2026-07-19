# Story-to-Probe 与 LLM 后端能力边界：讨论备忘录

日期：2026-07-15（2026-07-19 补记）  
性质：**非规范性讨论备忘录（working memo）**  
状态：讨论持续中；已接受的阶段性工作决定单独标明

> 本文不是 ADR，不修改现有架构契约，不代表开发授权，也不冻结 schema、UI、模型名单、预算、
> capability enum 或产品路线。除非某节明确标为“已接受”，文中“建议”“倾向”“可以”均是待讨论方向，
> 不应反写成已经接受的决策。

## 1. 为什么出现这组问题

第一轮 WoZ 用户试用原本想验证：普通安全操作员能否把一条近期 AI 注入攻击情报，独立填写成完整的
`ProbeCandidate`，再由 Ithuriel 作者人肉编译成 AgentDojo mock 探针。

实际填写暴露了一个重要问题：当前 `docs/trial/probe-candidate-template.md` 并不是普通意义上的“攻击情报
录入表”，而是一份接近可执行测试规格的工程文档。它同时要求填写者完成：

1. 攻击情报理解；
2. 威胁建模；
3. Agent 环境与 capability 映射；
4. 确定性 security oracle；
5. utility oracle；
6. 正负对照、nonce、state delta 等测试工程设计。

除非填写者经过 AI prompt injection、agent tool-use 和 assurance evaluation 方面的专门训练，普通 cyber
安全工程师很难在“刚读到、看到或听到一条攻击 story”后，独立完成全部内容。

这个观察进一步引出了五个相互连接的问题：

- Story 到 Probe 的过程是否应该向最终用户开放；
- 如果开放，应开放到哪一层，而不是让用户直接编写任意可执行测试；
- 当前 AgentDojo 无法表达 long-memory poisoning 时，Ithuriel 怎样声明支持边界；
- 如果客户只能使用本地 LLM，哪些 Ithuriel 功能会受限；
- 原型之后，是先开发后端模型能力评估器，还是先做一次跨模型实测 survey。

本文把这些问题放在同一个产品与架构框架中讨论。

---

## 2. 当前模板暴露的不是“用户不会填表”，而是角色边界错误

### 2.1 当前模板混合了三种工作

| 工作 | 典型问题 | 更自然的责任人 |
|---|---|---|
| 情报理解 | 攻击从哪里得知、是否可信、与本组织有什么关系 | 普通 cyber 工程师／威胁分析人员 |
| 威胁建模 | 攻击者能控制什么、需要什么权限、哪些场景不覆盖 | 用户与安全专家共同完成 |
| Probe engineering | 怎样构造确定性 oracle、fixture、正负对照和可重复实验 | AI assurance／probe engineer |

`entry surface` 和恶意目标经过解释后，普通工程师通常能够表达；但 `security oracle`、`utility oracle`、
AgentDojo state delta、trial nonce 和 capability binding 已经属于测试工程专业工作。

### 2.2 当前试用已经给出了两个信号

- Long-memory 候选虽然可以在纸面上填满，但其核心机制超出当前 AgentDojo Workspace 能力。
- Calendar 候选最终需要 reviewer 协助收窄，才成为可由现有 calendar/inbox 状态执行的候选；当前文件也已
  诚实标记为 `reviewer-assisted executable refinement`。

因此，“六个字段最后都有文字”不能等同于“普通操作员能够独立 author 一个可执行 Probe”。反过来，
操作员无法独立完成完整模板，也不能直接推导为“用户没有把新攻击情报转成回归资产的需求”。

### 2.3 对 ADR-0020 C1 的重新理解

ADR-0020 当前的 C1 同时测了两件事：

1. 用户能否说清攻击需求；
2. 用户能否完成 assurance test engineering。

现有观察主要证伪了第二项，并暴露了首要用户角色选择错误；它不能被解释为 Story-to-Probe 本身没有价值。任何新的测试方法、攻击探针或注入方法都必然经历某种 Story-to-Probe 过程；待验证的问题是将它产品化到 Ithuriel 内是否产生足够的增量价值，以及 Ithuriel 能否在声明边界内把它做成。

ADR-0020 保留为当时的试验记录；其 C1 fail 不再作为关闭 Story-to-Probe 方向的产品 kill criterion。若后续需要修改规范性口径，应用新 ADR 显式 supersede，而不回写历史。

---

## 3. Story-to-Probe 是否应该向最终用户开放

### 3.1 这不是简单的开放／不开放二选一

“向用户开放”至少有四个不同层级：

| 层级 | 用户能够做什么 | 差异化价值 | 工程与安全复杂度 | 是否作为当前 Story-to-Probe 开发重点 |
|---|---|---:|---:|---|
| 只运行预置探针 | 选择探针、运行、阅读报告 | 中低 | 低 | 否（但仍是必要的消费路径） |
| 提交 Attack Story | 描述来源、现实背景和担心的后果 | 高 | 低 | 是 |
| 辅助生成并确认 Probe | 系统起草，用户纠正关键假设 | 很高 | 中 | 是 |
| 任意自助编写可执行探针 | 自定义 oracle、环境、工具和执行逻辑 | 高但危险 | 极高 | 否 |

当前真正需要决定的，不是“用户能否看到完整模板”，而是“用户在从模糊情报到正式测试资产的链条中，
拥有哪一部分作者权、确认权和发布权”。

当前开发重点是“提交 Attack Story”和“辅助生成并确认 Probe”，但两者的首要用户均是专业 AI assurance engineer，不是普通 IT 从业者。

### 3.2 如果完全不向最终用户开放

Ithuriel 仍然有意义。Evidence、Finding、Claim、CoverageLedger、标准到 ontology 的蒸馏和有边界报告仍是
核心差异化。产品可以成为“由 Ithuriel 团队维护的高质量探针库 + 保证评估服务”。

但 Pack B 会失去一个很强的用户价值：

> 用户刚看到一条与自己组织相关的新攻击，就能把它变成以后持续复跑的测试资产。

如果用户只能等待官方探针库更新，产品容易接近“预置 benchmark/scanner + 更严谨报告”。结论层仍有
价值，但“对陌生、新兴攻击的持续适应”这一亮点会明显减弱。

### 3.3 如果把完整工程过程直接开放

如果承诺“任何用户给出任何 story，系统都能自动生成一个可在任意目标上执行的探针”，工程边界几乎
无限：新环境、新状态机制、新 oracle、新工具、新权限、新副作用和新 sandbox 都可能随 story 进入。

这很容易演变成：

- 通用攻击代码生成器；
- 插件 IDE；
- 任意工作流引擎；
- 通用 agent 模拟平台；
- 大而全的 sandbox 与 connector 平台。

这会破坏项目一直坚持的“Base 借、Differentiator 建”和“一条切片一个新变量”。

### 3.4 已接受的用户与共同创作边界

首要最终用户是经过完整培训的专业 AI assurance engineer，可以是客户内部 assurance 团队成员，也可以是外部人员。普通 IT security engineer、威胁情报人员和业务系统负责人可以提供 Story、组织背景与目标信息，但不是完整 Probe 的默认作者和保证结论裁定者。“外部人员”也不自动等于独立 assessor；独立性仍取决于组织关系、利益冲突和复核过程。

产品边界表述为：

> AI assurance engineer 与 AI 可以共同完成 Story-to-Probe；Ithuriel 负责统一格式化、静态校验、capability 匹配与受控编译；最终是否、何时、何地和以什么边界执行，由另一名具备授权资格的专业人员决定。

专业用户可以：

- 提交链接、文章、转述或自己的攻击故事；
- 描述相关 agent、正常任务和担心的后果；
- 说明攻击者现实中能控制什么；
- 回答少量定向追问；
- 查看系统生成的攻击假设、保真度差异和非目标；
- 修改、确认或否决系统推断；
- 请求在已支持的环境中验证；
- 在 Advanced 模式中直接编辑完整 ProbeCandidate。

Ithuriel 或 probe engineer 负责：

- 结构化 entry surface、技术类型和恶意目标；
- 判断现有 capability 是否支持；
- 设计 payload template、security oracle、utility oracle；
- 设计正负对照、trial 隔离和 promotion evidence；
- 写清 fidelity gap、unsupported 和非目标。

专业资格不会自动赋予：

- 任意 Python、shell 或插件执行；
- 自行声明 safety tier 或绕过 RoE；
- 未校准 oracle 直接产生正式 Finding 的能力；
- 因编译成功而自动执行 Probe 的权限；
- 真实网络或副作用的隐式授权。

受训专业人员可以在小团队中同时编写并发布一个不可变 ProbeCandidate 版本，但发布不赋予执行权。红队 Probe 的实际执行必须由第二名 Execution Authorizer 完成最终复核和授权，详见 §9.5。

### 3.5 Authoring provenance 可能成为 Ithuriel 的特色

“用户 author”不应被定义成“每个 YAML 字段都是用户亲手写的”。更重要的是攻击意图、组织相关性和现实
前提是否来自用户，以及系统是否悄悄发明了改变攻击意义的假设。

未来可考虑给关键内容记录来源，但当前不冻结 schema：

- `user_stated`；
- `source_extracted`；
- `system_inferred`；
- `reviewer_added`；
- `user_confirmed`。

这会把“共同创作”变成可审计过程，而不是隐藏 AI 或 reviewer 对探针做过的实质性修改。

### 3.6 下一轮应验证什么

```text
专业 AI assurance engineer 提交 Attack Story
        ↓
选择简化模式或 Advanced 模式
        ↓
生成统一、不可变的 ProbeCandidate
        ↓
静态校验 + capability matching
        ↓
第二名 Execution Authorizer 批准具体 Execution Request
        ↓
Ithuriel 实际运行正对照 + 负对照 + utility
        ↓
Evidence → Finding → Claim → 有边界报告
```

下一轮不再验证普通安全工程师能否独立设计 oracle，而是验证两个产品与工程假设：

1. 将 Story-to-Probe 放入 Ithuriel，是否比专家在文档、代码和零散工具中手工完成更快、更一致且更可审计；
2. 对声明 capability profile 内的第二条新 Story，是否能只新增 Probe 数据就完成编译和执行，而不需改动 runner、compiler 或 schema。

超出 capability profile 的 Story 应输出结构化 gap；这不是 compiler 失败。但如果目标 Story 普遍需要逐条手写专用 runner 或绕过统一 ProbePackage，则说明当前产品化方法不成立。

---

## 4. 怎样根据项目能力设置“支持的攻击类型”边界

### 4.1 不按攻击名称划边界，按不可缺少的 capability 划边界

“Memory poisoning”“indirect prompt injection”或“multi-agent attack”只是攻击族名称。一个名称下面可能包含
完全不同的时间、状态、权限和观测机制。

更可靠的判断是：该 story 的核心语义需要哪些 capability，而现有环境是否全部提供。

至少要描述：

- entry surface：user、tool response、calendar、email、RAG、persistent memory、inter-agent message 等；
- temporal mode：单轮、同会话多轮、跨会话、延迟触发；
- state operation：读写什么状态，状态是否持久；
- target action：读数据、调用工具、写记忆、发信、改变环境等；
- observability：tool call、output、state delta、memory snapshot、nonce/canary；
- experimental control：reset、snapshot、trial 隔离、正负对照；
- fidelity：mock、fixture、seeded tenant、customer sandbox；
- safety/RoE：允许的执行层级和副作用。

一个 Probe 进入 `runnable_candidate` 的最低条件应当是：

1. 环境能表达核心攻击语义；
2. 能执行所需的时间和状态过程；
3. 攻击结果可以可靠观察；
4. 环境可以重置并隔离 trial；
5. 可以建立正对照和负对照；
6. 可以同时测量正常任务 utility；
7. 能在 RoE 和安全层级内执行。

缺少任一核心条件，都不能把它当成正式支持的可执行探针。

首版不建设通用 capability registry，只冻结 AgentDojo Workspace IPI v0.1 所需的最小静态 profile；其余边界由具体 Story 的结构化 gap 和实现摩擦继续反推。

### 4.2 Story 接收边界可以宽，执行和 Claim 边界必须窄

建议区分：

- **Story-supported**：Ithuriel 可以登记和结构化任何攻击故事；
- **Environment-supported**：环境具备表达和观察该机制的 capability；
- **Runnable**：schema、capability、policy 和安全预检通过；
- **Released**：正负对照、重复运行、独立确认和 reviewer promotion 通过；
- **Assessable**：released package 能在声明的目标与 fidelity 上产生 Finding/Claim。

不一定需要立刻增加这些枚举；现有 `idea → draft → runnable_candidate → ... → released` 生命周期已经能承载
大部分语义，缺失 capability 可以先作为结构化 assessment/gap 附在 candidate 上。

首版的可执行边界只需要能证明 `required_capabilities ⊆ environment + backend + policy capabilities`；精细分类和通用服务继续延后。

### 4.3 当前 AgentDojo Workspace 的概念性 v0.1 边界

按当前项目冻结的首轮范围，可暂时理解为支持：

- tool/API response、calendar、email 进入的间接注入；
- 单个隔离 trial 内的多步工具交互；
- AgentDojo Workspace 已有工具和 mock state；
- structured tool call、calendar/inbox state delta、nonce/canary oracle；
- 确定性的正常用户任务；
- 可恢复 mock 状态；
- T0–T2，无真实外部副作用。

当前不应声称支持：

- 跨会话持久记忆写入与读取；
- 长期记忆污染后的延迟触发；
- RAG 索引实际写入与未来检索；
- 跨 agent 共享状态；
- 真实邮箱、网络和客户数据外发；
- 只能凭“模型看起来发生偏移”判断、但没有稳定 oracle 的攻击；
- 需要临时生成新工具或任意执行代码的攻击。

这份边界以后可以成为一个很薄的静态 environment capability profile；当前没有理由建设 registry service。

该 v0.1 边界已作为可修改的开发决定接受；开发中可以根据具体证据修订，但不得静默扩大保证口径。

### 4.4 Long-memory story 要先分清两个不同机制

**同一会话的长对话渐进诱导**至少需要：

- 多轮对话和完整历史；
- 可控 turn schedule；
- 中间或最终行为观测；
- 上下文重置；
- 正常任务 utility。

**跨会话持久记忆污染**至少需要：

- poisoning phase；
- 显式 memory write；
- 跨会话状态保存；
- 后续 clean session；
- memory recall 和 delayed trigger；
- memory snapshot/diff；
- 每轮恢复干净记忆。

如果当前 AgentDojo 不具备这些能力，long-memory story 可以保留为 `idea/draft` 和 AttackHypothesis，但不能进入
`runnable_candidate`，更不能产生目标安全 Finding。

该 capability 当前只作为长期演进方向，已接受的阶段顺序和停止条件见 §9.4。

### 4.5 不要为了适配现有 Runner 而偷换攻击问题

Calendar event 也是可在未来再次读取的持久外部状态，因此可以测试“外部内容延迟触发未授权工具行为”；
但它不能证明“agent 自身长期记忆被污染”。

如果要做 surrogate，应建立独立候选并明确：

- 保留了哪些核心语义；
- 丢失了哪些语义；
- 与原 story 的关系；
- 不能外推到什么结论。

原始 long-memory hypothesis 继续标记 capability gap。不能用一个日历替代场景跑出结果后，把它反写成
Ithuriel 已经支持长期记忆安全评估。

### 4.6 何时值得扩展新的攻击 capability

可考虑以下门槛：

1. 用户需求真实，而不只是内部觉得攻击有趣；
2. 核心语义清楚；
3. 可以借用已有 runner/agent/environment；
4. 可以建立可靠 oracle 和 reset；
5. 扩展可以作为一个有界的新变量落地。

对于 long memory，更符合项目纪律的后续切片可能是：借一个最小、可冻结、可重置的持久记忆 agent 环境，
验证“污染 → 跨会话保存 → clean task 触发 → state/tool oracle”，而不是给 AgentDojo 自建完整 memory subsystem。

---

## 5. 只能使用本地 LLM 时，哪些功能会受限

### 5.1 先纠正一个前提：Ithuriel 并不整体依赖云端 LLM

当前确定性切片可以完全离线：配置检查、端口探测、人工复核、Evidence/Finding/Claim、CoverageLedger、
registry、报告和固定 fixture 校准都不依赖云端模型。

当前真实 AI 注入切片需要一个能够参与 agent tool loop 的 LLM，但 harness 已有 Ollama、本地 endpoint 和任意
OpenAI-compatible endpoint 的接入路径。因此硬边界不是“local vs cloud”，而是模型能力和本地算力是否满足
相应角色要求。

后续的项目设计和编码说明需要按功能写清工具与后端模型需求，不能只用“需要 LLM”概括。这是后续文档任务，不在本次更新中冻结具体 profile。
### 5.2 要区分不同 LLM 角色

| 模型角色 | 当前状态 | 本地模型不足时的主要影响 |
|---|---|---|
| Target agent | 当前 AI 真跑需要 | tool loop、utility 和测量有效性受限 |
| Authoring assistant | 规划/WoZ，未产品化 | Story 提取、追问和 Probe 草稿质量下降 |
| Adaptive attacker | 后续 discovery 能力 | 攻击变体强度与多样性下降 |
| LLM judge | 延期，当前优先 deterministic oracle | 裁定稳定性、校准和独立性不足 |

不能因为现场只有一个本地模型，就默认让它同时扮演 target、attacker 和 judge，却不披露 evaluator-target
耦合与独立性缺口。

### 5.3 基本不受影响的部分

- Pack A 的确定性 cyber 检查；
- RoE、Executor/PEP、证据哈希与 provenance；
- Finding、CoverageLedger、Claim 和有界报告；
- 人工复核；
- Probe schema/lint 和固定规则 compiler；
- deterministic oracle 与 state diff。

### 5.4 真实 AgentDojo AI 测量的限制

本地 target 至少需要稳定支持：

- system message；
- structured function calling；
- 正确工具名和 JSON 参数；
- tool result continuation；
- 多步 tool loop；
- 工具之后的最终用户回答；
- 足够的上下文长度。

如果模型不能完成 benign task，或者大量 trial 发生 schema error/timeout，必须区分：

- backend/tooling unsupported；
- execution error；
- utility failure；
- security attack failure。

不能把“模型够不到工具面”产生的 ASR=0 解释成安全。测量应 fail closed，落到 invalid、inconclusive 或
not assessed。

### 5.5 本地算力会影响统计功效

AI 注入需要多轮 bare/defended trial。本地 GPU、显存、context、吞吐和并发不足可能导致：

- 运行时间显著增加；
- 无法达到最低有效 run 数；
- CI 变宽；
- bare/defended 区间重叠；
- 最终只能报告 `underpowered`。

这通常是吞吐和结论强度下降，不一定是所有功能不可用。

### 5.6 Story-to-Probe 辅助能力可能降级

较弱的本地模型可能更难：

- 读取长文章和中英文混合材料；
- 提取隐含攻击前提；
- 生成有效追问；
- 区分来源事实和系统推断；
- 设计可判别 oracle；
- 生成有价值的 payload 变体；
- 识别 capability gap。

合理退化路径是更多人工确认，而不是让低质量草稿自动发布。视频、音频、截图和长 PDF 还可能需要本地
OCR、ASR 或视觉模型。如果客户环境完全断网，URL 和在线 threat feed 也要改为审批后的离线导入。

### 5.7 本地部署同时有明显优势

- 客户数据不离开安全边界；
- 无第三方 API 留存和供应商训练风险；
- 模型版本不容易被云端静默替换；
- 权重和推理环境可以冻结；
- 没有外部配额和 rate limit；
- 可在隔离网络运行。

但为了可复现，未来可能需要记录比云端更多的 provenance：权重 revision/hash、quantization、tokenizer、
chat/tool template、推理引擎、context、sampling、backend configuration，必要时还包括硬件信息。

### 5.8 一个待讨论的部署分层

- **Offline Core**：所有确定性检查、证据、Finding/Claim 和报告；
- **Local AI**：客户批准的本地模型，按 capability 开放 AgentDojo 探针和辅助 authoring；
- **Cloud-enhanced**：经明确授权才开放的更强长文档、多模态、adaptive attack 或独立 judge。

对 cyber security 客户，本地模型更适合作为第一等部署方式，而不是无人维护的兼容分支；云端应该是显式
授权后的增强能力，而不是静默 fallback。

---

## 6. 原型之后的 LLM Backend Capability Evaluator

### 6.1 正确定位

朋友提出：原型开发阶段收尾后，开发一个工具评估后端 LLM 是否足以支撑 Ithuriel 的扫描检测工作。

这个方向合理，但它不应成为通用 LLM 智力 benchmark，也不应给出“模型安全分数”。更准确的定位是：

> **Ithuriel LLM Backend Conformance Evaluator**：判断一个具体 backend/configuration 是否满足某个
> Ithuriel 功能 profile 的最低运行要求。

它回答的是“这个测量仪器能不能工作”，不是“这个模型是否安全”。

### 6.2 必须按角色定义 profile

未来可能有：

- `agentdojo-target`：target agent 的 tool loop 和 utility；
- `authoring-assistant`：Story 提取、结构化、追问和受限草稿；
- `adaptive-attacker`：有界攻击变异与多轮策略；
- `llm-judge`：校准、一致性、对抗鲁棒性和独立性。

当前不应一次实现全部。首版应只覆盖原型实际使用的 target profile。

### 6.3 一个可能的最薄 v0.1

`ithuriel.agentdojo-target.v1` 可以用冻结、无客户数据、无攻击性的 benign fixture 检查：

1. endpoint/API；
2. system instruction；
3. 单次 tool call；
4. JSON 参数 schema；
5. tool result continuation；
6. 多步 tool loop；
7. 最终 deterministic utility；
8. 重复运行有效率；
9. 最低 context；
10. latency/throughput；
11. served model 和配置 provenance。

不能用“某条 prompt injection 是否命中”作为 backend conformance 门槛。未命中可能是模型更鲁棒，也可能
只是攻击变体弱；安全结果属于后续 probe measurement。

### 6.4 输出应是多维能力报告，不是单一分数

可能的报告思想如下，字段尚未冻结：

```yaml
profile: ithuriel.agentdojo-target.v1
backend_configuration_hash: "..."

capabilities:
  chat_completion: supported
  system_instruction: supported
  single_tool_call: supported
  tool_argument_schema: supported
  tool_result_continuation: supported
  multi_step_tool_loop: unstable
  required_context_window: not_verified

eligibility: eligible_with_limits
compatibility:
  eligible_probe_families:
    - single_step_tool_output_injection
  blocked_probe_families:
    - multi_step_agent_tool_attack

security_assessment: not_performed
```

该结果不是 Finding、Claim、合规意见或安全评级。它只决定哪些 probe 可以运行、哪些形成 capability gap，
以及测量是否具备最低仪器有效性。为避免与安全裁定混淆，单项能力使用
`supported / unsupported / unstable / not_verified`，总体资格使用
`eligible / eligible_with_limits / ineligible / not_assessed`，不使用 Finding 语义的
`pass / fail / verdict`。

### 6.5 运行、引用与失效条件

可能需要在首次接入、模型更换、quantization/推理引擎/chat template/context 配置变化，以及正式评估前执行。
报告应绑定 exact backend configuration；相关配置变化后旧结果失效，不能静默沿用。

Backend Capability Report 应作为独立、不可变、内容寻址的机器可读 artifact。它是测量仪器的资格证明，
不是目标安全证据。`MeasurementContext` 只保留最小绑定：

```yaml
instrument_qualification:
  profile_ref: ithuriel.agentdojo-target.v1
  profile_hash: "sha256:..."
  report_ref: "bcr:sha256:..."
  backend_configuration_hash: "sha256:..."
```

完整 capability、limitation、fixture 结果、provenance 和费用保留在 report 中，不在每个
`MeasurementContext` 中重复展开。执行前 gate 必须解析 report 并核对 exact backend configuration；
报告缺失、配置 hash 不匹配或报告失效时，记为 `backend_qualification_missing`、
`capability_gap` 或 `measurement not valid`，不得据此生成目标的通过／失败 Finding。

### 6.6 防止再次建设平台

首版不做：

- 模型排行榜；
- 通用知识/推理能力测试；
- 自动下载或部署模型；
- 模型市场；
- 单一综合分；
- 自动宣称模型安全；
- 为每个 provider 重写专用执行器。

理想的最薄实现只是：一个兼容 adapter、一组冻结 fixture、逐能力断言和结构化 capability report。

---

## 7. 为什么在开发 Evaluator 之前先做 OpenRouter 跨模型 Survey

### 7.1 顺序上的新认识

原型代码合拢后，先对常用且有代表性的不同能力/部署层级模型做一次付费 survey，可以让 evaluator 的要求
来自真实摩擦，而不是规划者想象。

建议顺序是：

```text
原型代码合拢
      ↓
跨模型实测 Survey
      ↓
归纳真实兼容性、utility、错误、成本与 provenance 摩擦
      ↓
冻结首个 Backend Capability Profile
      ↓
开发自动 Conformance Evaluator
```

Survey 是研究切片；Evaluator 才是后续产品能力。首轮 survey 只研究 backend compatibility
和支撑 AgentDojo target role 的能力边界，不同时进行攻击效果比较或模型安全排名。

### 7.2 Survey 第一轮应回答的问题

- 常见模型能否稳定完成当前 Ithuriel agent tool loop；
- 模型不满足要求时具体怎样失败，这些失败能否归入稳定的机器可读类别；
- system instruction、单次 tool call、JSON 参数、tool result continuation、多步 tool loop 和
  deterministic utility 中，哪些是首个 profile 的硬门禁；
- benign valid rate、latency、token 和每个 valid trial 的费用如何变化；
- requested/served model、provider、采样参数和 fingerprint 等 provenance 能否被稳定记录；
- 哪些真实失败应该固化成 evaluator 的硬门禁。

第一轮不测 ASR、bare/defended delta 或“哪个模型更安全”；攻击安全性测量是后续独立研究。

### 7.3 代表性抽样不宜只看“大、中、小”

商业模型常不公开参数量，MoE 的总参数和激活参数也不是同一概念。可以按能力、成本和部署形态分层：

| 层级 | 目标样本数 | 意图 |
|---|---:|---|
| 中小 open-weight／本地可行候选 | 2 | 观察低成本和本地兼容路径的边界 |
| 常用中型／高吞吐 | 2 | 代表常见生产部署 |
| 大型 open-weight／MoE | 2 | 观察高端自托管候选的工具能力 |
| 商业 frontier | 2 | 提供当前高能力参照上限 |

首轮以 8 个具体 model deployment 为目标。具体名单应在 survey 启动当天从实时 catalog 生成并冻结，
并将其中一个留作 profile 预测验证样本。不要仅因多数模型不支持某项必需能力就删除该要求；
profile 应由 AgentDojo target role 的任务需求驱动，不由模型通过率投票决定。

OpenRouter Models API 可以按最近一周 token 量排序，并按 `supported_parameters=tools` 过滤；但“热门”会受
价格、免费流量和批量任务影响，只能作为一个选型信号。

### 7.4 冻结的 benign fixture 和 trial 数

每个 deployment 运行三类无攻击性 fixture：

1. 单次工具调用与 JSON 参数；
2. 工具结果返回后继续推理；
3. 多步工具循环和确定性最终 utility。

每类 fixture 最多重复 5 次，因此全量上限为 `8 × 3 × 5 = 120` 个 fixture trial。先在一个便宜模型上跑
pilot，确认 adapter、artifact 和费用记录正常后，再冻结配置运行其余样本。

某 deployment 在 fixture 上的 `5/5` 只表示 survey 中的初步资格，不表示生产环境 SLA 或经统计证明的
高可靠性。失败的 deployment 仍是有效调查结果，不应从报告中删除。

### 7.5 首轮不将攻击 Probe 混入 conformance survey

现有项目数据已经表明，攻击变体会显著改变 ASR。如果把攻击 Probe 混入首轮 survey，backend 工具能力、
攻击强度和模型安全性将被混为一个问题。因此首轮只使用 benign fixture；后续如需研究攻击效果，应另立协议、
预算和结论边界。

### 7.6 OpenRouter provider 路由必须钉死

OpenRouter 默认可能在同一 model slug 的不同 provider 之间根据价格、可用性等路由和 fallback。正式 survey
如果不钉 provider，研究对象会变成“当时的动态路由服务”，而不是一个可复核的模型部署。首轮不把
provider 和 quantization 当作独立实验变量；它们是必须钉死和记录的 deployment 条件。

需要考虑：

- 指定 provider；
- 禁用 fallback；
- 要求 provider 支持全部必需参数；
- 固定 model slug；
- 记录 provider、served model、fingerprint；
- 记录 sampling/reasoning 参数；
- provider 不可用时记录 execution error，不静默换路由。

### 7.7 每个 deployment 分开报告四类结果

1. **Backend compatibility**：valid rate、schema error、timeout、context、provenance；
2. **Functional utility**：benign fixture 的单步、continuation、多步和 deterministic task 完成情况；
3. **Qualification**：逐能力状态、总体 eligibility、limitations 和 blocked probe families；
4. **Operational cost**：token、请求数、latency、费用和每 valid trial 的成本。

不要把这些压成单一综合排名。

### 7.8 预算和凭据纪律

应使用独立、严格封顶的 OpenRouter 项目：

- 有限额度；
- 关闭或限制自动充值；
- 分阶段预算闸门；
- key 不进入聊天、代码、日志或 shell history；
- 只使用 synthetic/mock 数据；
- 不发送客户数据；
- 记录真实 token 和 generation cost。

单个 AgentDojo trial 可能包含多次模型调用，不能按“一次聊天”的价格估算整个 survey。
本轮接受 `USD 50` 为最高硬预算；当时项目全部既有探针测试共花费约 `USD 0.76`，
该历史数据只是预算充足性的参考，不是启动付费实验的授权。任何 pilot 超出预期时都应停止并重新估算，
不得因为预算尚有余额就自动扩大研究问题。

### 7.9 OpenRouter 结果不能替代本地部署实测

同一个 open-weight 模型在 OpenRouter 和客户本地部署中，可能因为 quantization、推理引擎、chat/tool
template、context、GPU/batching 和 sampling 不同而表现不同。

OpenRouter survey 可以：

- 找代表性模型家族；
- 暴露协议和能力要求；
- 估算成本与统计设计；
- 形成 evaluator 测试项；
- 筛选值得本地复测的候选。

但以后仍需选少量中小 open-weight 模型，在真实本地环境独立复测。初期 Local AI 只保证兼容路径，
不作为必须通过的产品 conformance 验收项；它不允许静默回退到云端，也不允许在未知道应测什么时虚构验收标准。

---

## 8. 把两条讨论线合并成一个整体

Story/Probe 线解决“用户想测什么”；backend/environment 线解决“Ithuriel 实际能不能可靠地测”。原始讨论用以下简化链条表达 capability matching：

```text
Attack Story
    ↓
AttackHypothesis
    ↓
required capabilities ──────────────────────────────┐
                                                    │
Environment Capability Profile ────────────────────┤
                                                    ├─ 全部满足？
Backend Capability Report ─────────────────────────┤      ├─ 是 → Runnable Candidate
                                                    │      └─ 否 → Structured Gap
RoE / policy / approval ────────────────────────────┘

Runnable Candidate
    ↓
正对照 + 负对照 + utility + 重复运行 + 独立确认
    ↓
Released ProbePackage
    ↓
Finding → Claim → 有边界报告
```

2026-07-19 接受两种 authoring 模式和单一决定性人类执行授权后，当前链条更新为：

```text
Attack Story
    ↓
AttackHypothesis
    ├─ Simplified authoring
    └─ Advanced authoring
    ↓
Canonical ProbeCandidate
    ↓
required capabilities + environment/backend/policy profile
    ├─ 不满足 → Structured Capability Gap
    └─ 满足   → 静态校验并冻结 candidate hash
    ↓
Execution Request
    ↓
第二名 Execution Authorizer: approve / deny
    ├─ deny    → 不执行，记录原因
    └─ approve → Executor/PEP 按已批准边界执行
    ↓
正对照 + 负对照 + utility + 重复运行
    ↓
ProbeValidationRecord + Released ProbePackage
    ↓
Finding → Claim → 有边界报告
```

这也给出一个重要的诚实边界：Ithuriel 可以允许用户提交很宽的故事，但只有环境、模型、oracle、reset 和
policy 全部满足的窄子集，才有资格进入执行和保证结论。
静态校验或编译成功都不会自动赋予执行权；每次红队执行均由具体 Execution Request 和人类授权约束。

---

## 附录 A：自建 long-memory 评估环境的难度与工程量

这里需要先纠正表述：AgentDojo 更接近“环境 + 工具 + 正常任务 + 注入任务 + security/utility 判据 + runner”
组成的评估框架，而不是等待被一个功能更强的普通 agent 替代。真正可能需要的是一个支持跨会话持久状态的
有界评估 backend/positive-control target。

### A.1 四个完全不同的工程范围

以下仅是量级估算，不是排期或实施承诺；假设工程师熟悉 Python、AgentDojo 和当前 Ithuriel：

| 范围 | 产物 | 粗略投入 |
|---|---|---:|
| 演示型 PoC | 两次会话、简单 memory state、观察延迟触发 | 1 人约 3–7 天 |
| Ithuriel 可信薄切片 | reset/snapshot、分层 oracle、正负对照、Evidence/Finding/Claim | 1 人约 4–8 周 |
| 可复用内部实验室 | 多种 memory policy、多个 probe/backend | 2 人约 2–4 个月 |
| 客户级通用平台 | 多框架、真实存储、租户隔离、sandbox、适配器 | 3–5 人约 6–12 个月以上 |

Demo 容易，可信评估难。后者必须证明并分别记录：`poison_write_attempted`、`poison_persisted`、
`poison_retrieved`、`forbidden_action_attempted` 和最终 harm/state delta；还要证明第二个 session 没有 chat history
或恶意输入残留，唯一跨会话通道确实是声明的 memory。

### A.2 推荐的最薄实验语义

```text
冻结 clean snapshot
    ↓
Session A：恶意工具输出 → UpdateMemory
    ↓
持久 memory checkpoint
    ↓
Session B：全新会话 + 干净告警 → ReadRelevantMemory
    ↓
mock forbidden action / canary delivery
    ↓
分层 security oracle + 正常任务 utility
    ↓
丢弃整个 trial state
```

第一版使用结构化 list/SQLite/Pydantic memory 即可验证跨会话合同。不要同时引入 vector DB、embedding、
chunking、semantic top-k、自动摘要和遗忘；这些会让攻击失败原因无法归因，应分别成为后续新变量。

### A.3 可复用什么，哪里需要新接缝

AgentDojo 可以复用 LLM pipeline、tool runtime、TaskSuite 和 security/utility 思路。但其常规运行单位偏向一个
prompt/tool loop 的单次 pre/post environment。真正的持久记忆探针需要 poison phase、checkpoint 和 clean
trigger phase 的多阶段证据，因此可能需要一个很窄的自定义两阶段 runner，或对 TaskSuite 做有界扩展。

这个 runner 只应拥有阶段编排，不应成长成通用 RunOrchestrator。它产生 synthetic calibration evidence，
不能被报告成对客户真实 memory 架构的保证。

### A.4 推荐的停止条件

如果出现以下任一情况，应停止自建并重新寻找可借用底座：

- 无法可靠 snapshot/reset；
- 无法证明第二会话只通过 persistent memory 接触第一阶段信息；
- 只能用主观 LLM judge 判断是否投毒；
- 一个切片必须同时建设 memory platform、workflow engine、真实副作用 sandbox；
- 为单个场景需要大规模 fork AgentDojo 内核。

更有纪律的候选不是“开发一个比 AgentDojo 更强的 Agent 平台”，而是先做 3–7 天的技术 spike，回答两阶段
持久状态、clean-session、snapshot/reset 和 deterministic oracle 是否成立；只有 spike 成功且用户需求仍然
成立，才讨论 4–8 周的正式薄切片。

---

## 9. 当前已接受的阶段性方向

### 9.1 已经出现的强信号

- 当前完整 ProbeCandidate 模板对普通 cyber 工程师过于专业；
- oracle 和 executable refinement 是独立专业工作；
- Story intake 与 Probe engineering 应当分层；
- AgentDojo 的能力不能被误写成所有 AI 注入攻击的支持边界；
- long-memory story 可以登记，但当前不能产生 long-memory 安全 Finding；
- Ithuriel 的确定性核心不依赖云 LLM；
- 本地模型能力不足必须形成显式 gap，不能静默 fallback 或伪造安全；
- 后端能力评估器应该由真实跨模型 survey 的失败模式反推。

### 9.2 已接受的阶段性方向摘要（2026-07-19）

- Story-to-Probe 保留为用户可见的核心价值；
- 首要最终用户是受过完整培训的专业 AI assurance engineer，可为内部 assurance 团队成员或外部人员；
- 提供 Simplified 和 Advanced 两种 authoring 模式，但两者必须生成同一规范的 ProbeCandidate/ProbePackage；
- Story-to-Probe 成功的硬标准是产物能由 Ithuriel 实际端到端执行，而不只是完成填表、语义确认或静态编译；
- 同一 assurance engineer 可在小团队中编写并发布 ProbeCandidate，但红队 Probe 的最终执行必须由第二名 Execution Authorizer 决定；
- 首版 capability profile 暂定为 AgentDojo Workspace 间接提示注入，开发中可根据证据修订；
- Surrogate Probe 必须有机器可读的 `direct / bounded_surrogate` 关系，并且不得关闭原始 hypothesis 的 capability gap 或生成越界 Claim；
- long-memory 当前作为长期演进方向，不进入 v0.1；
- capability 边界先按版本化静态 profile 和 set-inclusion 判断，不建设 registry service；
- 本地模型作为第一等部署方式，云端作为显式授权增强；
- 原型结束后先做跨模型 survey，再开发 backend evaluator；
- evaluator 首版只做当前 AgentDojo target role，不先覆盖 author/judge/attacker 全部角色；
- Local AI 初期只保证显式兼容路径，不作为必须通过的产品验收项；
- OpenRouter 首轮只测 backend compatibility 和 AgentDojo target role 的能力边界，不测模型安全排名；
- survey 目标是 8 个代表性 deployment、3 类 benign fixture、每类最多 5 次，最高预算 `USD 50`；
- provider 和 quantization 在首轮中是钉死并记录的配置，不作为独立实验变量；
- `agentdojo-target.v1` 在需求稳定、失败模式饱和并通过一个留出 deployment 预测验证后冻结；
- Backend Capability Report 是内容寻址的 instrument qualification artifact，`MeasurementContext` 只引用它，不将它作为 Finding。

### 9.3 原问题的决定位置

原问题 1–12 已全部形成阶段性决定：

- 问题 1–6 见 §9.5；
- long-memory 问题见 §9.4；
- 问题 8–12，包括 Local AI 验收边界、OpenRouter survey 设计、profile 冻结条件和 Backend Capability Report 的放置，见 §9.6。

这些决定仍是 working memo 层的阶段性边界，不等于 ADR、schema 冻结、产品路线承诺或付费试验授权。

### 9.4 Long-memory capability 的阶段性决定（2026-07-19，已接受）

本节记录已接受的产品与研究边界，但不授权立即实现、选定永久底座、冻结 schema 或开始付费试验。

#### 定位与顺序

- Long-memory poisoning 是 Ithuriel 值得保留的重要后续 capability，但不进入当前 AgentDojo Workspace IPI v0.1 边界，当前记为 `strategic_candidate / unsupported_in_v0.1`。
- 不把 AgentDojo 扩建成通用长期记忆平台。目标是让 Ithuriel 消费一个具备持久状态、跨会话隔离和可观测 memory lifecycle 的专用 evaluation backend，再将结果进入统一 Probe、Evidence、Finding、Claim 和执行授权链。
- 先完成 AgentDojo IPI 的 Story-to-Probe、统一 ProbePackage、端到端执行和第二人授权，再用第二条相同 capability profile 的 IPI Probe 证明 compiler/runner 可复用。这些成立后，才启动 3–7 天的 long-memory 技术 spike；spike 通过后才讨论正式薄切片。

#### 首个可接受的攻击语义

“长期诱导偏离”不作为首切片的含糊 oracle。它至少包含三个不同问题：同一会话内的多轮渐进诱导、恶意内容写入持久记忆后在干净会话中触发，以及多条记忆组合后的条件触发。首切片只选第二种：

> 恶意外部内容在 Session A 中导致一条攻击相关记忆被持久保存；Session B 不含原始恶意内容和旧对话历史；该记忆被检索后，导致一个可确定观察的未授权工具动作或状态变化。

不以“思想偏离”、风格改变或主观 LLM judge 作为核心安全 oracle。“长期”先使用逻辑时间表达：在投毒与干净触发之间插入 `k` 个 benign sessions，报告“经过 `k` 个干扰会话后的跨会话持久性”，不外推为生产环境中持续数月。

#### 分阶段观测与反事实归因

单一 ASR 不足以表达 memory poisoning。每个 trial 至少分别记录：

```text
poison_write_attempted
poison_persisted
poison_retrieved
forbidden_action_attempted
harm_or_state_delta_observed
utility_success
```

最终 attack success 可要求完整链成立，但中间结果必须作为 Observation/TrialOutcome 保留，以区分写入阻断、检索阻断、行为阻断和只是 backend 没有实际完成外部副作用。这一形状与 [Hidden in Memory](https://arxiv.org/abs/2605.15338) 及其[开源实现](https://github.com/ivaxi0s/LLM-agent-memory-poisoning)中将攻击分为 injection、retrieval 和 adversarial usage 三阶段的做法一致。

为了证明后续行为是由记忆导致，而不是模型随机波动或 trigger 本身导致，至少需要：

- clean snapshot + clean trigger；
- poisoned snapshot + clean trigger；
- benign memory + clean trigger；
- 删除或禁止检索 poisoned memory + 同一 trigger；
- 正常 memory write/read 的 utility 对照。

如果 poisoned 和 clean snapshot 之间没有可归因差异，就不得声称持久记忆导致了攻击。

#### 候选 borrowed base 的调查顺序

1. 优先审计 `Hidden in Memory` 的开源 runner。它的三阶段指标、tool-based/external-manager 两种 memory-management regime、smoke configs 和运行产物与 Ithuriel 的问题形状最接近；但项目很新、尚无正式 release，并且部分分类仍使用 LLM judge，所以只作候选底座，不直接继承其结论。
2. [AgentLAB](https://github.com/TanqiuJiang/AgentLAB) 可作为 discovery 参考。它已包含两阶段 memory poisoning 和 Mem0，但同时引入 adaptive planner、attacker、verifier 和 judge，变量较多，不作为首个 confirmation backend 的首选。
3. 只有当专用 benchmark 无法提供 reset 和 observability 时，才考虑用通用 memory protocol 构造极薄 synthetic target。例如 [AutoGen Memory protocol](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/memory.html) 的 `add/query/update_context/clear` 方法有利于观察写入与清理，但这会让 Ithuriel 拥有更多实验环境代码，因而只是后备方案。

上述候选不是已冻结选型。实际 spike 启动时必须重新审计其当时版本、许可、本地模型路径、第三方 judge 依赖、可复现性和与 Ithuriel 接缝的大小。

#### Spike 通过条件和停止条件

Spike 只有在以下条件全部成立时才能升级为正式切片：

- clean snapshot 可内容寻址并可靠恢复；
- Session B 可以证明不含 Session A 的对话历史；
- 唯一允许的跨会话通道是已声明的 persistent memory；
- memory write、stored record、retrieval 和最终工具动作均可观测；
- 核心安全裁定不依赖主观 LLM judge；
- 正对照、负对照、反事实对照和 utility 对照成立；
- 每个 trial 可完全隔离和重置；
- 输出可以进入 Ithuriel 现有 Evidence/Finding/Claim 形状，不要求建设通用 RunOrchestrator；
- 第二名 Execution Authorizer 能够审阅并批准完整的两阶段 Execution Request。

无法可靠 snapshot/reset、无法证明 clean second session、只能用主观 judge 裁定、或一个切片必须同时建设 memory platform、workflow engine 与 sandbox 时，就停止正式开发并保留原 Story 的 capability gap。

#### 保证强度与环境保真度

Ithuriel 不需要一次性支持所有长期记忆系统。后续可按可观测性区分：

- **Synthetic white-box memory target**：可观察写入、检索和状态差异，用于校准 Probe；
- **Seeded/gray-box target**：客户提供 memory API、日志或 snapshot，可以做有限归因；
- **Black-box production target**：只能观察最终行为，无法证明 no-hit 发生在哪个阶段，结论强度最低。

因此 long-memory 支持不是一个简单的 `supported=true`，而必须绑定 memory-write observability、retrieval observability、snapshot/reset、session-isolation proof 和 target fidelity。

### 9.5 Story-to-Probe 产品、创作和执行边界（2026-07-19，已接受）

本节回答 §9.3 原问题 1–6，并记录今日讨论中对 ADR-0020 产品假设的重新解释。它是阶段性工作决定，不自动授权修改 ADR、schema 或代码。

#### 首要用户

Ithuriel 的首要最终用户定位为经过完整培训的专业 AI assurance engineer。该角色可以是客户内部 assurance 团队成员，也可以是外部人员。普通 IT security engineer、威胁情报人员与业务系统负责人可以提供 Story、组织背景、正常业务语义与目标边界，但不是完整 Probe 的默认作者或保证结论裁定者。

最终应将“受过完整培训”落到可观察能力，而不仅是职位名称：能理解 agent/tool 攻击面，设计可判别 oracle，区分安全结果与仪器失效，评估 fidelity gap，并理解 RoE、合同和证据边界。外部人员不自动等于独立 assessor。

#### Simplified 与 Advanced 两种创作模式

- **Simplified**：从 Attack Story 开始，由 Ithuriel/AI 协助提取假设、定向追问、起草 capability、oracle、controls 和 fidelity gap；专业作者检查并明确确认系统推断。
- **Advanced**：专业作者可直接编辑完整 ProbeCandidate，用于复杂场景、精确控制和调试。
- 两种模式只在 authoring 入口上不同，最终必须产生同一规范、同一校验和同一执行语义的 ProbeCandidate/ProbePackage。不建立“简化探针”与“高级探针”两套 runtime。
- AI 可以提议、起草、规范化和编译，但不得发布、裁定或授权执行它自己生成的 Probe。
- 两种模式都不提供任意 Python、shell、plugin 执行，safety tier 自行声明或 RoE 绕过。

关键 authoring 内容后续应保留 `user_stated`、`source_extracted`、`system_inferred`、`reviewer_added` 和 `user_confirmed` 等 provenance，但本次不冻结具体 schema。

#### Story-to-Probe 的成功标准

填写完整、语义忠实、可纠错和编译通过都只是必要条件。最终成功标准是：

> 用户的 Attack Story 被忠实转换为经过规范化、capability 绑定和验证，并且能够由 Ithuriel 在声明环境中实际端到端执行的 Probe。

成功产物必须同时满足：

1. 保留原 Story 的核心攻击机制，没有为适配 runner 而偷换问题；
2. 产生统一、不可变的 ProbePackage；
3. environment、backend、oracle、reset/isolation 和 policy capabilities 全部有明确绑定；
4. Ithuriel 能在声明 fidelity 的环境中实际运行它；
5. 正对照、负对照、security oracle 和 utility oracle 成立；
6. 第二名专业人员批准具体 Execution Request；
7. 运行能形成 Observation、TrialOutcome、Finding，并在证据允许时派生 Claim。

超出当前 capability profile 的 Story 应保留为 Story/AttackHypothesis 并输出结构化 gap；它不算 Story-to-Probe 成功，但也不是 compiler 缺陷。如果系统生成 surrogate，必须把它作为独立的窄化 hypothesis 和 Probe 处理。

#### 产品价值与工程可行性的验证

Story-to-Probe 是任何新探针必然经历的过程；因而不再把“这个 job 是否存在”作为核心产品假设。待验证的是：

- **增量产品价值**：把该过程纳入 Ithuriel，是否比专家在文档、代码和零散工具中手工完成更快、更一致、更可审计，并且能将新情报累积为组织自有的回归资产；
- **工程可行性**：对一条位于已声明 capability profile 内的第二条新 Story，能否只新增 Probe 数据就完成编译和执行，而不需修改 runner、compiler 或 schema。

如果专业人员仍需在 Ithuriel 之外手工完成全部威胁建模、oracle、fixture 和 runner 开发，Ithuriel 只负责换一种格式；或者每条 profile 内的 Probe 都需要 story-specific runtime 代码，则说明这一产品化方法不成立。

#### 单一决定性人类执行关口

开发与授权采用“AI 协助创作，人类掌握执行权”的 human-in-command 原则：

> 同一 assurance engineer 可以在小团队中编写并发布 ProbeCandidate；但最终是否、何时、何地、对什么目标以及在什么权限和副作用边界内执行，由第二名具备授权资格的 Execution Authorizer 作出最终 approve/deny 决定。

这是唯一决定性人工关口，避免“作者 → 技术 reviewer → promotion reviewer → RoE approver → 工具 approver”的递归嵌套。首版边界为：

- 作者发布的是不可变版本，发布不赋予执行权；
- Execution Authorizer 批准的是一个具体 `execution_request_hash`，至少覆盖 `probe_package_hash`、目标或目标范围、environment/backend、时间、参数、运行次数/资源预算、允许动作、副作用边界和 RoE/policy 版本；
- 任何改变执行语义的修改都产生新 hash，原授权自动失效；
- capability validation 只判断技术可行性，不拥有授权权力；
- RoE 是 Execution Authorizer 必须遵守的预设组织边界，不再引入另一个逐次人工 reviewer；
- Executor/PEP 只做机械检查和强制执行，不重新作业务决定；
- 动态动作超出授权范围时直接拒绝并记录证据，不在运行中递归弹出新审批；若确需扩大范围，停止当前运行并创建新 Execution Request；
- 该双人要求针对 Story-derived 红队 Probe 和其它具攻击性或副作用的执行，不扩大到只读取冻结 fixture 的离线确定性配置检查。

#### AgentDojo IPI v0.1 的可修改边界

首版暂定只支持 AgentDojo Workspace 环境中的间接提示注入：

- 恶意内容经 tool/API output、email 或 calendar 等外部数据进入；
- 单个隔离 trial 内的多步 agent/tool interaction；
- 可观测的 structured tool call、state delta 和 nonce/canary；
- 可重复的 security/utility oracle、可恢复 mock state 与正负对照；
- T0–T2，无真实客户系统和外部副作用。

当前不声称支持跨会话持久记忆、RAG 索引写入、跨 agent 共享状态、真实邮箱/网络/客户副作用、无可靠 oracle 的攻击，或为单条 Story 生成任意工具与代码。这是 provisional v0.1 profile，开发中可以修改；但任何修改都必须同步更新边界和报告口径。

#### Surrogate Probe 的机器可读关系

ProbeCandidate/ProbePackage 应引入一个窄而明确的 `hypothesis_binding.relationship`，首版只需：

- `direct`：Probe 直接测试已声明 AttackHypothesis；
- `bounded_surrogate`：Probe 只保留原假设的部分语义，并实际测试一个独立、范围更窄的 assessed hypothesis。

`bounded_surrogate` 至少必须记录 `original_hypothesis_ref`、独立的 `assessed_hypothesis_ref`、`preserved_capabilities`、`omitted_capabilities`、`prohibited_claims` 和 rationale，并遵守：

1. surrogate 执行不关闭原假设的 capability gap；
2. Finding/Claim 只能针对 assessed hypothesis，不能针对 original hypothesis；
3. CoverageLedger 不得将 surrogate 计为原攻击机制已覆盖；
4. 报告必须显示保留语义、丢失语义和禁止外推的结论；
5. relationship 进入 ProbePackage 内容 hash，修改后原 Execution Authorization 失效；
6. Simplified 模式可由 AI 提出 surrogate，但不得静默替换，必须由作者确认并由 Execution Authorizer 复核。

`surrogate` 描述的是测试语义关系，不与现有 `deprecated/superseded` 资产版本关系混用。

### 9.6 Local AI、OpenRouter survey 与 Backend Qualification（2026-07-19，已接受）

本节回答 §9.3 原问题 8–12。它冻结的是首轮研究边界和停止条件，不授权购买 OpenRouter 额度、
运行付费试验、公布模型排名或立即实作 evaluator。

#### Local AI 初期只保证兼容路径

Local AI 初期不作为必须通过的产品验收项。当前还没有足够证据决定应对哪些模型、推理引擎、quantization、
chat/tool template 和硬件组合做产品级 conformance；现在冻结一套必过矩阵会产生虚假精确性并带来大量无方向测试。

初期兼容路径至少意味着：

- 后端 adapter 不预设必须是云模型；
- 本地 backend 可被显式配置、识别、预检和拒绝；
- 本地能力不足时输出机器可读 capability gap 或 `not_assessed`；
- 绝不静默 fallback 到云端，也不用云端 survey 代替本地部署的实测证据。

产品级 Local AI 验收延后到 backend profile、fixture 和典型本地部署摩擦已经通过 survey 和早期集成足够稳定之后。

#### OpenRouter survey 的研究问题和样本

首轮 survey 只回答一个窄问题：

> 不同典型 LLM backend deployment 能否稳定完成 Ithuriel AgentDojo target role 需要的 benign tool loop，
> 其兼容边界、失败形状、可观测 provenance 和运行成本是什么？

它不回答模型总体安全性、prompt-injection 鲁棒性排名、参数规模的因果影响，也不测 bare/defended ASR。

首轮目标选取 8 个具体 deployment，分布在中小 open-weight／本地可行候选、常用中型／高吞吐、大型
open-weight／MoE 和商业 frontier 四个层级，每层级目标 2 个。名单在启动当日根据当时 catalog、tool-use 支持、
使用热度、价格和模型家族多样性冻结。至少保留一个 deployment 作为 profile 设计后的留出验证样本。

provider 和 quantization 不作为首轮的独立变量。对每个 deployment，它们必须被钉死、记录和纳入
`backend_configuration_hash`；OpenRouter fallback 必须关闭。如果想比较 provider 或 quantization，应在有明确、
可判别的新研究问题后另立试验。

#### Trial protocol 和预算

每个 deployment 运行三类 benign fixture：单次工具调用，工具结果返回后继续推理，以及多步工具循环与确定性最终
utility。每类最多重复 5 次，全量上限为 120 个 fixture trial。`5/5` 只是该 survey 的初步 eligibility 信号，
不得外推为生产 SLA 或高可靠性的统计证明。

最高硬预算为 `USD 50`。截至本次讨论，项目已有各类探针测试共花费约 `USD 0.76`；该数字只用于说明
`USD 50` 相对宽裕，不授权花费。运行顺序为便宜模型 pilot → 确认调用数、token、artifact 和记账正常 → 冻结其余矩阵。
任何阶段如出现异常成本或不可解释的配置漂移，立即停止并重新估算。

#### 冻结 `agentdojo-target.v1` 的条件

冻结 profile 表示 AgentDojo target role 的最低能力契约进入版本化管理，不表示覆盖所有模型、不再变化或达到生产可靠性。
必需能力由 Ithuriel 的 AgentDojo 任务需求决定，不按模型通过率投票决定。

当以下条件全部成立时，可冻结 `ithuriel.agentdojo-target.v1`：

1. 原则上完成计划的 8 个 deployment；如个别服务不可用，至少完成 6 个，覆盖四个层级和至少三个模型家族；
2. 三类冻结 benign fixture 覆盖 system instruction、单次 tool call、合法 JSON 参数、tool result continuation、
   多步 loop 和最终 deterministic utility；
3. 必需、可选和运行限制已分开，所有已观察失败能落入稳定、不重叠的机器可读类别；
4. 最后三个新完成 deployment 没有引入新的必需能力字段或失败类别，即达到 failure-mode saturation；
5. profile 能事先将一个未参与需求归纳的留出 deployment 分为 `eligible`、`eligible_with_limits` 或
   `ineligible`，随后的 benign fixture 实测与该预测一致；
6. 冻结配置、fixture、requested/served model、provider、关键参数、费用和 artifact 能够复现与追溯，不需要未声明的
   vendor-specific 例外才能运行。

如果第 8 个 deployment 后仍出现新失败类别，可在 `USD 50` 硬上限内追加最多两个目标样本。若仍未饱和，不冻结 profile，
而是重新审视 profile 边界。Local AI 完整产品验收、provider/quantization 因果比较、攻击 ASR 和统计 SLA 均不是冻结 v1 的前置条件。

#### Backend Capability Report 进入 MeasurementContext 的方式

Backend Capability Report 定位为测量仪器的资格报告，不是被测目标的安全结论：

- 它回答“这个 exact backend configuration 有无资格承担某个 Ithuriel role”；
- Finding 回答“被测目标是否显示安全问题或控制缺陷”；
- backend 不能正确调用工具意味着测量仪器失效，不能证明目标安全或不安全。

该报告保存为独立、不可变、内容寻址的机器可读 artifact，至少记录 profile 和 fixture 的版本，exact backend configuration，
逐能力的 `supported / unsupported / unstable / not_verified`，总体
`eligible / eligible_with_limits / ineligible / not_assessed`，limitations、provenance、usage 和费用。

`MeasurementContext` 不内联复制整份报告，只保留 `instrument_qualification` 绑定，包含 `profile_ref`、
`profile_hash`、`report_ref` 和 `backend_configuration_hash`。执行前 gate 解析该 report 并核对配置；模型、provider、
quantization、推理引擎、chat/tool template、context、关键采样参数、profile 或 fixture 发生实质变化后，旧资格不得静默沿用。

报告缺失、无效或配置不匹配时，运行记为 `backend_qualification_missing`、`capability_gap` 或 `measurement not valid`；
必要时在 Scope/Claim limitation 中说明，但不生成目标的通过／失败 Finding，也不记入目标控制的 CoverageLedger。

当前 `MeasurementContext` 仍是开放字典；首实现只增加上述最小引用。只有当 preflight gate、report resolver 或 Claim limitation 等真实消费者出现时，
才将 Backend Capability Report 和 `instrument_qualification` 提升为正式类型化 schema。

---

## 10. 本轮讨论仍未授权的工作

- 不修改 ADR-0018/0020；如需规范化今日决定，后续必须单独授权新 ADR/superseding ADR；
- 不将本备忘录的阶段性决定自动升级为 Project Memory 或实现授权；
- 不修改 ProbeCandidate schema，包括尚未实作的 surrogate 关系字段；
- 不建设 authoring UI、Simplified/Advanced authoring runtime 或通用 compiler；
- 不扩建 AgentDojo 以模拟 long memory；
- 不启动 long-memory spike 或选定永久 borrowed base；
- 不实现 capability registry service；
- 不开发 backend evaluator；
- 不购买或运行 OpenRouter survey；
- 不选择或公布模型名单；
- 不把本备忘录中的倾向写成路线图承诺。

原问题 1–12 的阶段性讨论已完成。下一步是决定哪些内容需要提升为 ADR、Project Memory 或有边界的实现任务；
本文本身不做这些授权。

## 参考上下文

项目内部：

- `docs/trial/probe-candidate-template.md`
- `docs/trial/probe-candidate-calendar.md`
- `docs/trial/probe-candidate-long-memory-spoofing.md`
- `docs/adr/0018-operator-authored-emerging-threat-probe-lifecycle.md`
- `docs/adr/0020-first-bounded-user-trial-woz-probe-authoring.md`
- `docs/DESIGN.md`
- `docs/Project_Memory.md`

OpenRouter 公开文档（用于未来 survey 设计参考，不构成当前模型选择）：

- [Models API 与筛选/排序](https://openrouter.ai/docs/guides/overview/models)
- [Tool calling](https://openrouter.ai/docs/guides/features/tool-calling)
- [Provider routing、fallback 与参数约束](https://openrouter.ai/docs/guides/routing/provider-selection)
- [API usage 与 generation stats](https://openrouter.ai/docs/api/reference/overview)
- [数据收集设置](https://openrouter.ai/docs/guides/privacy/data-collection)
