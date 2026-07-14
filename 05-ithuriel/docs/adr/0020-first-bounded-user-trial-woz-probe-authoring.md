# ADR 0020 — 第一轮有界用户试用契约：Wizard-of-Oz 探针 authoring（搭档扮操作员、原型阶段）

日期：2026-07-14 · 状态：accepted（用户拍板：更薄的 WoZ 版先于 compiler；搭档扮真实操作员、原型开发阶段） · 关联：`0018`（operator-authored probe lifecycle，本 ADR 采纳其 job-to-be-done 并解其 §283 Q1=是）、`0019`（AssessmentManifest 分母）、`0017`（内部报告 view）、`0014`（CoverageLedger）、`docs/Project_Memory.md`（从真实用户 handoff 倒推里程碑，§235–238）

## 背景与 forcing

`docs/Project_Memory.md` §235 定下：下一步停止从内部架构外推路线图，改从「Ithuriel 能被交到真实用户手里做一次有界试用」的最近里程碑倒推。这一步是**验证里程碑、不是构建里程碑**——先用最低成本退掉最大的风险。

`0018` 提出真实用户的 job-to-be-done 不是「跑一个预置 benchmark」，而是把一条来源与可信度各异的新兴攻击情报，变成受治理、可复跑、可审计的测试资产，独立确认后再对目标产出 Finding/Claim。本 ADR 采纳这个 job 作试用核心（解 `0018` §283 Q1），但对 `0018` 自己的落地顺序提一条异议并据此收窄。

**异议**：`0018` §209 的「第一实现切片」是一个能跑的 loader/compiler，那已经是「先建后验」。而这个 job 的 riskiest assumption 不是工程（能否把声明式探针编译进 AgentDojo），是人与产品：一个真实安全操作员到底有没有这个 job、能不能把一条他真正在意的新兴攻击填进 `0018` 的声明结构、会不会信任 promotion gate 与最终范围声明、会不会真用一份有界结论而不是只要一个绿勾。`0018` §243–250 那张观察清单里的每一条，都不需要 compiler 就能回答。

## 决策

第一轮试用做得比 `0018` §209 还薄一档，只引入**一个新变量：一个真实操作员对一条真实情报的声明式 authoring 尝试**；compiler 那步由作者人肉扮演（Wizard-of-Oz）。

1. **WoZ 先于 compiler**：给操作员 `0018` 的声明式结构（不给 UI、不给 compiler），观察他能否把一条真实情报填成 `ProbeCandidate`；作者人肉把它映射到一个 AgentDojo mock 场景跑正/负对照，产出 `0017`/`0019` 已建的那份有界报告与覆盖分母（mock-report-out）。若操作员填不出、或只想要绿勾，则**不建 compiler**——这正是把「怀疑框架、别自证」用到实处。
2. **搭档扮真实操作员、原型开发阶段**：不接外部真实审计员（信号最强但风险与逻辑成本最高、且内部信号都还没有，过早），也不自测（「我觉得有用」不算验证，自证风险高）。搭档是最现实的真实-job 信号来源，逻辑成本低。

**这两块工作接得上、结论层不孤儿**：`0017`/`0019` 的 manifest/report 层正是 `0018` 确认循环的「report out」一端（released ProbePackage → bare/defended → Finding → Claim → 报告 + 覆盖分母）。本试用把它当产出侧复用。

## 试用契约（Project_Memory §236 十项，锚在 0018 的 job）

- **试用用户与 job-to-be-done**：搭档扮一名安全审核操作员；job = 把一条近期 AI 注入攻击情报变成一个有威胁假设、成功判据、安全边界、适用范围的声明式测试资产，并读懂由它产出的有界结论。
- **攻击面预先框窄（当前开发阶段=跑通即可）**：本轮攻击面**固定**为 AgentDojo workspace mock 的 tool-output / calendar / email 一类间接注入（`0018` §216 首切片范围 + §283 Q2 建议面），操作员在这个面**内**框定一个具体攻击（可取材真实情报，但不追求覆盖新攻击面）。理由=当前阶段目标是让端到端流程**跑通**、拿到一份真实产出的报告；「让操作员自由选、撞到 mock 表达不了」那种覆盖压力测试是后续阶段的事，现在放进来只会把首轮卡在跑不出报告（用户拍板：这一步薄一点、先跑通）。
- **最薄工作流与产出**：(1) 操作员登记一条情报（来源/可信度/自述假设）；(2) 把它填成声明式 `ProbeCandidate`——entry surface、攻击技术、恶意目标、security oracle、utility oracle、威胁模型、环境保真度；(3) 作者 WoZ 把它映射到上述固定面的一个 AgentDojo mock 场景，跑正对照（已知易受影响 target 上应命中）+ 负对照（无攻击/安全变体不误报）；(4) 产出复用 `0017`/`0019` 的有界报告：security 轴覆盖 + 联合裁定警示 + 门禁/缺口 + 目标保真度 + `assurance_level: none`，并对照一份只声明这一条控制的 `AssessmentManifest`。产出物是一份 mock 报告，不是对任何真实目标的保证。
- **安装/上手**：本轮零安装。纸上 + 作者 WoZ 执行；操作员只需读结构、填字段、读报告。
- **目标与 RoE 边界**：仅 `0018` 的 T0–T2（纯文本 lint / 无工具无客户数据的模型调用 / AgentDojo mock 可恢复状态）；无客户系统、无真实网络或副作用；攻击面限 AgentDojo mock 可表达者（tool-output / calendar / email 一类间接注入）。
- **fixture/mock vs 真实**：全程明标 **WoZ-compiled + mock-report**；不声称对真实目标的评估，不冒充 compiler 已存在。
- **数据外发与凭据**：源材料按不可信输入处理，在无执行工具、无凭据、无发布权限的隔离上下文解析，原文严格标 data（`0018` §196）；本轮用公开情报，不引入客户未公开材料；作者不擅自复用 local-command 里的任何 key（沿用项目 key 卫生纪律）。
- **报告/Claim 呈现**：复用 `0017` 三问视图（能说什么/凭什么/不能说什么）+ `0019` 声明分母；保持 `assurance_level: none`，不折成单一置信分数（Project_Memory §237）。
- **失败与支持预期**：本轮预期会撞到字段答不出、oracle 设计成瓶颈——这些是**要观察的信号、不是要修的 bug**；作者不为让 demo 好看而替操作员补答案（补了就污染下面 C1/C2 的判据）。
- **验收标准（可证伪的判据，非通过率；每条有明确 pass/fail 与证据）**：GO/NO-GO 落在下面四条硬判据上，`0018` §243–250 那张定性观察清单继续记录、但只作解释性上下文、不作 GO 门。
  - **C1 表达完整性（二值、逐字段）**：操作员在作者**不提示答案**下，把 `ProbeCandidate` 六个必填字段（entry surface / 攻击技术 / 恶意目标 / security oracle / utility oracle / 威胁模型）填出可执行内容。pass = 六项全填且非作者代答；fail = ≥1 项操作员填不出（记下是哪项、卡在哪）。
  - **C2 oracle 能判别（行为、二值）**：把操作员**照他自己写法**的 security oracle WoZ 跑正/负对照。pass = 正对照命中 **且** 负对照不误报；fail = 他写的 oracle 分不开正负（需作者改才判别得了）——记为 oracle-设计-瓶颈。
  - **C3 用有界结论、不要绿勾（行为、关键判据）**：读完报告后请操作员做**一个具体下游决定**——「就这份结论，你会不会保留/上线这个防御配置，凭什么」。pass = 他的理由**明确引用 ≥2 个报告维度**（如 security 轴覆盖 + `joint=utility_failed` 联合裁定、或 `target_fidelity=mock`、或 `not_assessed` 声明缺口）；fail = 他要一个整体「安全/不安全」判断、要绿勾、或无视联合裁定与保真度警示。
  - **C4 不过度声称（二值）**：问操作员他会不会对上级/客户把这份结果表述成「合规通过/pass」。pass = 他正确复述成「仅对该 mock / target variant 成立、`assurance_level: none`」；fail = 他把 assurance_level:none 当成一次通过（过度声称）。
- **明确非目标**：无任意攻击代码生成、无 LLM 自动 authoring、无真实副作用、无 UI/工作流引擎/插件市场；不把 discovery no-hit 当目标 pass；不用 discovery 样本同时做 confirmation；不因本轮修改 `ontology_schema.yaml` / UK profile / Finding 四态 / Claim 哈希契约。

## Riskiest assumption 与 kill criterion

riskiest assumption：**一个真实安全操作员既有「把新兴情报变成受治理回归资产」这个 job，又能用这套声明结构表达它，且看重有界结论甚于绿勾。** 本试用刻意在写 compiler 之前证伪或坐实它。

kill criterion（绑到上面的可证伪判据）：**C1 fail**（填不出核心字段）或 **C3 fail**（只要绿勾、不用有界结论）任一触发——则**不建 `0018` §209 的 compiler**，回到「这套结论层是否有真实用户」这个更根本的问题，而不是继续加工程。C2 fail（oracle 判别不了）不 kill，但记为「oracle 设计是真瓶颈」——它决定后续该先投 oracle 辅助还是 compiler。C4 fail 是呈现层还没把「非合规」讲透的信号，回 `0017` 呈现、不 kill。

## 后续（仅当本轮通过）

若 C1 与 C3 pass（操作员能表达、且看重有界结论），则 `0018` §209 的第一实现切片（一条声明式 `ProbeSpec` fixture + loader/compiler，AgentDojo mock，T0–T2）才拿到该建的授权。`0018` §283 Q2（攻击面选型）本轮已按「当前阶段跑通即可」定为固定的 tool-output/calendar/email 间接注入面；Q4（pydantic vs YAML）、Q5（corpus 存储治理）留到 compiler 切片按真实摩擦再定。本轮单操作员签发，promotion 独立性显式标 `independence=unverified`（解 `0018` §283 Q3 的本轮口径）。

## 后果与取舍

正面：在写任何 compiler 之前退掉最大的人/产品风险；把刚建的结论层（`0017`/`0019`）放进一个真实 job 里被真实操作员读，验证它是否被需要，而非自证。代价：WoZ 一轮拿不到工程可扩展性信号（compiler 能否覆盖多样攻击面仍未知），但那是本轮**刻意不问**的问题——一个切片一个新变量。
