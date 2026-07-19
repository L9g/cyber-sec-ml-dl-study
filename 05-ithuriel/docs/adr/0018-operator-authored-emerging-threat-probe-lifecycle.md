# ADR 0018 — 操作员把新兴攻击情报转化为版本化探针（Threat-intel → Probe lifecycle）

日期：2026-07-14 · 状态：proposed（待用户拍板；尚未实现） · 关联：`0016`（verdict provenance / Claim warrant）、`0017`（内部试用报告 view）、`docs/papers/ai-redteam-pipeline-learning-note.md` D5（探索/确认双循环）、`docs/architecture-seams-D8.md` #7（discovery 与 confirmation 独立）、`docs/ontology_schema.yaml`（attack corpus governance）、`docs/Project_Memory.md`（下一步从真实用户试用倒推）

## 背景：一个真实的安全审核操作员任务

安全审核操作员可能从论文、新闻、供应商通告、同行交流或未经证实的传闻中遇到一种新的 AI 注入攻击思路。他需要回答的不是“能否把一段攻击 prompt 粘进工具”，而是：

> 能否把这条来源和可信度各异的攻击情报，转化为一个有明确威胁假设、成功判据、安全边界、复现协议和适用范围的测试资产；在独立确认后，再用它对目标系统产生可审计的 Finding 与 Claim？

这可以成为 Ithuriel 第一个清晰的用户 job-to-be-done：

> **把新出现的攻击情报，转化成受治理、可复跑、可审计的保证测试。**

现有设计已经有两端：

- pipeline D5 已约定“探索循环 → 毕业闸门 → 确认循环”；
- D8 已有固定 AgentDojo 场景 → bare/defended → Evidence/Finding/Claim 的确认路径。

当前缺口是两端之间没有操作员可用的 authoring contract：没有机器可读的候选探针、生命周期、毕业记录，也没有一条安全地把模糊想法编译到受控 runner 的路径。当前 harness 只能通过环境变量选择已有 `suite/user_task/injection_task/attack`，不能承载操作员新建的声明式场景。

## 决策摘要

新增一条 **Threat-intel → Probe** 工作流，但不建设“任意插件开发平台”：

1. 操作员登记来源材料与自己的攻击假设；LLM 可以协助结构化，但不能发布、执行或裁定。
2. 操作员创建的是声明式 `ProbeCandidate`，不是 Python、shell 或任意插件。
3. 候选探针由受控 compiler 映射到已有 runner/capability；表达不了的新攻击面诚实落 `unsupported`，不得自动生成绕过执行边界的代码。
4. 探索运行只产生 `ProbeValidationRecord`，不产生目标的正式 pass Finding。
5. 候选必须经过正对照、负对照、重复运行、安全审查与独立 holdout confirmation 才能毕业。
6. 毕业产物是内容寻址、版本化的 `ProbePackage`；只有 released package 才能进入现有 bare/defended → Finding → Claim 确认链。

本 ADR 冻结的是上述语义、边界和毕业纪律。具体 Pydantic/YAML 全字段、存储布局、UI、LLM prompt 和通用 compiler 均不在规划阶段一次冻死；由第一条 operator-authored probe 切片的真实 fixture 反推。

## 核心边界：Probe 不是 Plugin

“新攻击思路”通常包含几种不同变化：新的措辞或混淆技巧、新的注入位置、新的恶意目标、新的多步编排，或全新的攻击面。不能把这些都等同于“写一个插件”。

本 ADR 将职责分开：

- **ProbeCandidate / ProbePackage（差异化层，自建）**：声明测试意图、威胁模型、刺激、oracle、协议、来源、安全边界和适用范围。
- **Runner / environment（Base，借）**：AgentDojo、PyRIT、garak、未来 seeded tenant 等负责执行已有环境能力。
- **Thin adapter/compiler（薄适配）**：把声明式探针翻译成某个 runner 的受控输入，不拥有任意代码执行权。
- **Executor / ModelExecutor（PEP）**：任何真实模型调用、数据外发或副作用仍经过预算、RoE、允许列表和审批闸门；Probe 不得绕过。

因此普通操作员能 author probe，但不能借此 author executable code。只有当攻击思路需要一个尚不存在的交互面（例如 persistent memory 写入、跨 agent 消息或真实邮箱副作用）时，才进入开发者审阅的 capability/adapter 开发流程。

## 一个探针必须表达什么

一段攻击文本不是完整探针。最小测试语义必须能回答：

1. **攻击从哪里进入**：user query、tool/API response、RAG content、persistent memory、inter-agent message、environment observation 或 reflection output。
2. **攻击技术是什么**：例如权威冒充、指令优先级覆盖、编码/分片、多轮铺垫或上下文污染。
3. **攻击者要达成什么恶意目标**：泄漏 canary、调用禁止工具、越权读取、污染持久状态或改变环境。
4. **怎样确定攻击成功**：优先使用 nonce/canary、结构化 tool call、state delta、forbidden action 等确定性 oracle；不能仅凭“输出看起来可疑”。
5. **正常任务是否仍完成**：安全 oracle 必须与 utility oracle 成对，防止把“检测到可疑文本就中止一切”误报成整体安全。
6. **在什么威胁模型下成立**：攻击者 access level、所需 capability、注入位置控制力、是否知道系统/工具结构。
7. **在哪种环境与保真度下运行**：mock、frozen fixture、seeded tenant 或经授权 sandbox。

示例：“把高优先级指令藏入日历事件，诱导 agent 上传云盘文件”需要拆成：日历描述这一 entry surface、攻击载荷策略、未授权外传这一 malicious goal、带每次运行唯一 nonce 的文件/工具调用 oracle，以及原始日历查询任务的 utility oracle。

## 生命周期与状态语义

候选探针的成熟度不是 Finding.status；不得借用 `pass/fail/not_applicable/inconclusive` 表示探针开发状态。

建议的生命周期语义为：

| 状态 | 含义 | 能否产生正式目标 Finding |
|---|---|---|
| `idea` | 只登记来源材料和操作员描述 | 否 |
| `draft` | 已形成结构化攻击假设，但可能缺 runner/oracle | 否 |
| `runnable_candidate` | schema、安全预检和 capability 匹配通过，可在指定隔离环境探索运行 | 否 |
| `discovery_supported` | 探索样本中观察到稳定信号；尚未独立确认 | 否 |
| `confirmed` | 在独立 holdout/重跑上复现，毕业条件满足 | 否；等待发布冻结 |
| `released` | 已版本化、内容寻址、审阅签发并进入确认语料 | 是 |
| `deprecated` / `quarantined` | 已失效、误报、许可/安全问题或被撤回 | 否 |

探索阶段可以记录 candidate hit/no-hit/error，但“候选未命中”绝不能变成目标 `pass`。未验证的探针可能是载荷弱、环境不支持、oracle 错误或前提不成立；它尚无资格对目标安全作结论。

## 最小概念对象（字段待第一 fixture 定形）

### `ThreatIntelRecord`

保存来源而不假装来源具有同等权威：

- `source_type`: paper / news / advisory / practitioner_report / hearsay；
- `source_ref`、作者/发布者、发布日期与获取日期；
- 操作员摘要与原始材料哈希/引用；
- license/使用限制；
- `source_confidence` 与“尚未核实”声明；
- 谁在何时登记。

对于传闻，允许创建 idea，但必须保持 `unverified`；不得在后续报告中把它改写成已发表事实。

### `AttackHypothesis`

- 关联 control/标准（候选映射，需人工确认）；
- entry surface、攻击技术、malicious goal；
- P1–P6 advisory 标签；
- threat model：access level、required capabilities、前提与非目标；
- 预期的安全属性违反方式。

### `ProbeCandidate`

- `probe_id`、candidate version、当前 lifecycle state；
- 来源与 hypothesis 引用；
- target requirements / capability requirements；
- benign user task、注入位置、payload template 与变量；
- security oracle + rule version；
- utility oracle + rule version；
- discovery/confirmation 运行计划；
- safety class、execution tier、data-egress 与 side-effect 声明；
- 所需证据与明确的未覆盖面。

### `ProbeValidationRecord`

- candidate hash、runner/environment/model provenance；
- 正/负对照、discovery 与 holdout 的样本身份；
- attempted/valid/hit/error 计数与 CI（若适用）；
- oracle 校准结果及已知 false-positive/false-negative；
- capability/safety 审查结果；
- 毕业或拒绝理由；
- reviewer/approval record。

### `ProbePackage`

released 的不可变信封：

- 冻结后的 ProbeSpec；
- scenario/fixture/holdout refs；
- oracle 与 compiler/runner binding 版本；
- provenance/license/safety metadata；
- validation record 与 promotion record；
- package content hash、corpus release/version hash；
- deprecated/superseded relationship。

`ProbePackage` 是测试资产，不是某次目标测试的 Evidence；某次运行必须另外记录“使用了哪个 package hash + 哪个 MeasurementContext”。

## 探索循环与确认循环的硬边界

### 探索循环

目的：判断攻击假设是否值得冻结为测试，而不是判断目标是否安全。

- 可以使用 payload mutation、garak/PyRIT、AgentDojo adaptive attack 或人工变体；
- 可以调整 prompt、injection placement 和 oracle；
- 每次调整产生新 candidate revision；
- 产出 ProbeValidationRecord，不进入 CoverageLedger；
- 发现该攻击的具体样本不得同时证明其稳定性。

### 毕业闸门

候选至少满足以下条件才能 confirmed/released：

1. 来源、许可、操作员解释与版本可追溯；
2. 威胁模型、目标前提和 capability 需求明确；
3. security oracle 可复核，优先确定性；若用 LLM judge，则 judge 自身带独立 model/run/calibration provenance；
4. 有正对照：在已知易受影响的 bare/seeded target 上能观察到信号；
5. 有负对照：无攻击或安全变体不应误报；
6. 重复运行达到 probe 自己声明的有效样本计划；
7. discovery 与 confirmation 使用独立 holdout 或独立重跑；
8. utility 同时测量；
9. runner、场景、模型、oracle、种子计划和环境版本被钉死；
10. RoE、安全分类、数据外发和副作用审查通过；
11. promotion 由有身份的 reviewer 明确签发；高风险探针可要求双人复核。

不规定全局统一的 `k/n` 毕业数字。不同攻击面、detector 和执行成本需要不同协议；每个 ProbeSpec 必须声明自己的门槛与统计理由，Ithuriel 负责如实执行和记录，不用一个魔法阈值伪造通用性。

### 确认循环

只有 released package 可以进入正式保证路径：

`ProbePackage@hash → bare/defended interleaved trials → RawArtifact/trajectory → TrialOutcome → Finding/ComparisonSpec → Claim/report`

确认循环继续遵守现有不变量：positive control、最少有效运行数、CI/underpower、两臂 provenance invariant、differential attrition、security×utility 联合裁定与范围声明。

## LLM 在 authoring workflow 中的权限

LLM 可以协助：

- 从材料中提取候选攻击假设；
- 建议 entry surface、control mapping、P1–P6 标签和缺失前提；
- 生成 payload template 的候选变体；
- 提醒缺少 oracle、正/负对照、utility task 或 capability；
- 将经操作员确认的内容转换为声明式草稿。

LLM 不得：

- 自动发布或晋级候选；
- 自动决定 RoE、safety class 或审批；
- 自动生成并执行任意 Python/shell；
- 直接持有生产凭据、发布权限或真实副作用工具；
- 把探索命中自动升级成正式 Finding；
- 把来源内容中的指令当作 authoring agent 的控制指令。

论文、网页、邮件和新闻本身都是不可信输入，可能包含针对 authoring agent 的 prompt injection。材料解析必须在无执行工具、无凭据、无发布权限的隔离上下文中进行，并把原文严格标记为 data。客户未公开材料未经授权不得外发给第三方模型。

## 执行安全分层

首版概念上区分：

- **T0**：纯文本/静态 fixture lint，不调用模型；
- **T1**：调用模型但无工具、无客户数据和外部副作用；
- **T2**：AgentDojo/mock/seeded tenant 中的受控工具与可恢复状态；
- **T3**：客户 scoped sandbox 或真实外部副作用，必须有合同、target-scoped RoE、PEP 和按风险所需的 approval。

操作员声明探针不能自行把 execution tier 升高。compiler 根据 required capabilities 与 environment binding 计算实际 tier；任何不一致 fail-closed。

## 第一条实现切片（本 ADR 的建议，不在本提交实施）

唯一新变量：**一个操作员编写的声明式候选探针，而非 AgentDojo 内置攻击。**

严格收敛范围：

- 只支持 AgentDojo workspace mock environment；
- 只支持 tool response / email / calendar 一类间接 prompt injection；
- 只支持现有 user task + injection task 可表达的目标；
- security oracle 只支持 canary/nonce、structured forbidden tool call、environment state delta；
- utility 使用 AgentDojo 的确定性 utility；
- 只允许 T0–T2，禁止真实网络/客户系统副作用；
- 一个手写 ProbeSpec fixture + 一个 loader/compiler；
- 不建 UI、通用工作流引擎、插件市场、任意代码 sandbox 或 LLM 自动 authoring。

建议的端到端验收：

1. 操作员把一条标为 `hearsay/unverified` 的攻击描述登记成 idea；
2. 人工确认 AttackHypothesis 与 control/threat-model mapping；
3. 写成声明式 candidate，schema 校验并计算 capability/safety tier；
4. compiler 只生成受控 AgentDojo runner 输入，不接受任意代码；
5. 正对照命中、负对照不误报，错误与无效 trial 分开记；
6. discovery 和 holdout confirmation 使用不同样本；
7. promotion 生成不可变 ProbePackage、validation record 与 corpus hash；
8. released package 被现有 bare/defended harness 消费；
9. 现有 Evidence/Finding/Claim/report 结构无需为了候选生命周期而改变；
10. 报告明确展示 probe source、threat model、package hash、target fidelity 与未覆盖面。

## 对用户试用里程碑的意义

本工作流比“让用户运行一个预置 benchmark”更能验证 Ithuriel 的产品假设。试用用户完成的真实工作是：

`外部威胁情报 → 组织内部攻击知识 → 版本化测试资产 → 防御回归证据 → 有边界保证结论`

首轮试用可采用 evidence/probe-authoring-in、mock-report-out，避免一开始接入客户真实系统。需要观察的不是 UI 点击数，而是：

- 操作员能否把模糊想法说清成可测试假设；
- 哪些字段经常无法回答；
- 现有 runner/capability 能覆盖多少新思路；
- oracle 设计是否成为真正瓶颈；
- 操作员是否信任 promotion gate 与最终范围声明；
- 版本化后的探针是否能在模型/防御更新后稳定回归。

## 明确不做

- 不把 Ithuriel 建成任意攻击代码生成器或插件 IDE；
- 不允许来源材料直接触发工具、网络、凭据或发布动作；
- 不承诺所有论文/新闻攻击都能自动编译；
- 不用 LLM judge 替代可用的确定性 oracle；
- 不把 discovery no-hit 当目标 pass；
- 不用 discovery 样本同时做 confirmation；
- 不因新探针增加而重做调度器、ExperimentManager、插件市场或通用 workflow engine；
- 不在本 ADR 中修改 `ontology_schema.yaml`、UK profile、Finding 四态或现有 Claim 哈希契约。

## 后果与取舍

正面后果：

- 给用户试用一个具体且高价值的 job-to-be-done；
- 把新兴威胁持续转化为组织自己的可复现回归资产；
- 保持 Base=借、Differentiator=建：runner 借，场景治理、证据与结论层建；
- 让攻击语料强度与来源成为可审计 provenance，降低“弱 benchmark 让防御看起来很好”的风险；
- 防止未验证 prompt 直接污染正式覆盖率和保证声明。

代价与风险：

- oracle 设计往往比生成 payload 更难，需要操作员/开发者共同完成；
- 新攻击面可能频繁暴露 capability gap，不能用自动代码生成掩盖；
- corpus 是高风险双用途资产，需要访问控制、许可治理、撤回和安全发布策略；
- operator-authored probe 可能带来选择偏差，后续需披露谁选择/调整了攻击及其与防御方的关系；
- 生命周期和 promotion 会增加一些治理步骤，但这是“测试资产能否进入保证链”所必需的摩擦。

## 待拍板问题

1. 是否把本工作流定为下一轮用户试用的核心 job-to-be-done？
2. 第一条 fixture 选择 calendar/email tool-output IPI，还是选择更贴近真实新兴风险但需要新 capability 的 memory poisoning？本 ADR建议前者，以守“一条切片一个新变量”。
3. 首版 promotion 是否要求另一名 reviewer，还是允许同一操作员签发但显式标 `independence=unverified`？
4. ProbeCandidate/ValidationRecord 是进入现有 pydantic advisory 层，还是先以独立 YAML + JSON Schema fixture 运行一次再定最终模型？本 ADR建议后者。
5. 双用途/潜在有害 ProbePackage 的本地存储、加密和开源仓库排除策略如何落地？

