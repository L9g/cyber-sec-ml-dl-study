# ADR 0022 — 独立开发阶段的「一人两帽」治理：角色分离、非人员独立

日期：2026-07-22 · 状态：accepted（项目负责人批准） · 关联：`0018`（operator-authored probe lifecycle 与 T0–T3）、`0020`（第一轮有界用户试用）、`0013`（Executor/PEP 与 RoE）、`docs/Project_Memory.md`（Story-to-Probe 与 Execution Authorizer 决策）

## 背景与 forcing

Ithuriel 把 Probe authoring、执行授权、证据裁定和真实用户试用刻意分开，以减少自证、事后改规则和越权执行。但当前项目由独立开发者推进；若把「第二名人员」作为所有开发期 synthetic/mock 实验的前置条件，日常 T0–T2 验证会被组织条件而不是安全风险阻塞。

反过来，让开发者无记录地自行设计、批准、执行和解释，也会破坏本项目的核心卖点：可审计、可复现且有边界的保证结论。真正要守住的不是形式上的两个账号或两个签名，而是：规则在数据前冻结、执行请求不可变、结果不被选择性重写、利益冲突机器可见、结论不冒充独立验证。

本 ADR 因此建立正式的开发期「一人两帽」模式。它是对 2026-07-19「第二名 Execution Authorizer」决策的**窄例外**：只适用于内部开发的 T0–T2 synthetic/mock 工作；不改变 T3、客户环境、真实副作用和对外 assurance 的第二人要求。

## 先拆开三个经常混称为「操作员」的角色

1. **Probe Author / Developer**：把风险故事转成任务、payload、授权谓词、security/utility oracle、样本量、判据和代码。
2. **Execution Authorizer**：决定这一个不可变执行请求是否可在指定 target/environment、预算、数据外发、动作与副作用边界内运行。
3. **Trial User / Operator**：作为真实目标用户，证明自己能表达风险、完成 authoring、理解有界报告并据此作决定。

同一名独立开发者在本 ADR 范围内可以兼任前两项，但**不能用自己替代第三项**。开发者太了解 schema、runner 和预期答案；自测不能证明真实用户能独立完成 ADR-0020 的 C1–C4，也不能证明 Story-to-Probe 的产品假设成立。

## 决策一：按执行风险决定能否自行授权

| 层级/场景 | 一人两帽 | 必须条件 | 仍然禁止的声称 |
|---|---|---|---|
| **T0**：文本、schema、静态 fixture、纯离线自检 | 允许 | 冻结输入与预期；结果可复核 | 不称独立审阅 |
| **T1**：模型调用，但无工具、客户数据或外部副作用 | 允许 | 明确模型/provider、数据外发、预算上限与停止规则 | 不称真实用户验证或独立 assurance |
| **T2**：AgentDojo/mock/seeded tenant 中受控工具和可恢复状态 | 允许 | synthetic/public 数据；环境隔离且可重置；无客户系统；执行请求哈希绑定；RoE/预算/副作用边界写明 | 不外推真实系统，不称人员独立 |
| **T3**：客户 scoped sandbox、真实账号/数据、针对真实 target 的网络动作或其他真实外部副作用 | **不允许** | 第二名合格 Execution Authorizer；合同/target-scoped RoE；PEP；凭据、恢复和事故边界 | 无第二人时不得执行 |

以下情形即使技术上像 T0–T2，也不得靠一人两帽完成最终放行：

- 使用客户未公开数据、客户凭据或真实客户账号；
- 可能产生不可可靠回滚的持久外部状态、消息、邀请、针对真实 target 的网络动作或权限变化，或者产生超出预批准硬上限或不可控的费用；
- 对外发布独立评估、客户 assurance、合规或认证式结论；
- 把 Probe 晋级为对外声称「已独立验证」的 released assurance asset；
- 执行范围超出已批准的预算、provider、target、数据外发或 RoE。

没有第二人时，这些工作应保持 blocked，或退回明确标注 fidelity gap 的 synthetic/mock surrogate；不得通过拆命令、换账号或降低文字风险等级绕过。

## 决策二：同一人必须执行两次不同的工作，而不是一次自我确认

### Hat A — Probe Author / Developer

在看新数据之前准备执行包，至少冻结：

- Probe/task/payload 原文及 hash；
- security oracle、utility oracle、授权谓词和 measurement schema/version；
- 代码 commit、fixture/corpus hash 与环境版本；
- target、model/provider、路由/回退策略和数据外发边界；
- 样本量、valid/invalid trial 语义、随机化、统计判据与停止规则；
- 允许动作、预期 mock 副作用、恢复方式、预算硬上限；
- 可以声称、禁止声称和已知 fidelity gap。

Author 阶段结束时生成一个不可变 `execution_request_hash`。当前阶段允许用规范化 Markdown/YAML 加内容 hash 实现；在真实 consumer 逼出之前，不为此预建审批服务、UI 或通用工作流引擎。

### Freeze — 角色切换边界

- Author 内容提交后才能进入授权审阅；未提交的工作树不作为批准对象。
- 授权审阅与 authoring 使用不同的明确工作阶段；可行时隔一个工作时段再审，以减少即时自我合理化，但冷静期不冒充人员独立。
- 审阅期间不修改代码、任务、oracle 或判据。发现问题时返回 Author 阶段，产生新 commit/hash，旧批准失效。
- 不创建第二个身份、虚假 reviewer 或伪造第二人签名。AI/搭档 agent 可以找缺口，但不能产生人员独立性或替代人类授权责任。

### Hat B — Execution Authorizer

只对已经冻结的 execution request 作 approve/deny，不在签署时继续设计实验。至少逐项判断：

- target/environment 是否属于本 ADR 允许自行授权的 T0–T2；
- 攻击语义、授权动作和越权边界是否清楚；
- 数据外发、provider ToS、凭据与预算是否可接受；
- 隔离、重置、失败和停止条件是否充分；
- artifact 是否足以让未来审阅者重算判据；
- 报告是否会明确披露自我授权和非独立性。

最小签署记录：

```yaml
approved_by: <same person as author>
approval_role: execution_authorizer
authorization_mode: self_authorized_solo
role_separation: procedural
person_independence: none
independence_verification: not_applicable
conflict_of_interest: self_review
adversarial_review: none | ai_agent | peer
adversarial_review_ref: <artifact/ref or none>
approval_scope: internal_t0_t2_development
execution_request_hash: <sha256>
approved_target: <exact target/environment>
approved_provider: <provider/deployment or none>
budget_cap: <amount or none>
allowed_side_effects: <explicit synthetic/mock list>
prohibited_side_effects: <explicit list>
roe_or_policy_ref: <version/ref>
valid_from: <timestamp>
valid_until: <timestamp or run boundary>
decision: approve | deny
notes: <limitations>
```

solo 场景中的人员独立性不是未知，而是已知不存在，因此上面的固定值应为
`person_independence: none`；`independence_verification: not_applicable` 表示没有第二人的独立性可供核验。
`unverified` 只用于确有第二人、但其身份、关系或资质尚未核实的情形。

`adversarial_review` 与人员独立性正交：它只记录是否发生过对抗性找错，以及由 AI agent 还是 peer 完成。
AI 找出真实缺陷可以提高技术质量，却不会把 `person_independence` 从 `none` 升级；peer review 也只有在另有
明确角色、范围和独立性依据时，才能产生该范围内的独立保证。

批准只绑定该 hash。任何会改变安全、成本、数据外发或测量语义的修改——包括任务文本、target/provider、样本量、判据、允许动作、预算和 RoE——都使批准自动失效。纯注释或不改变 artifact 的排版改动可以另记为 non-semantic correction，但不得借此偷渡语义变化。

### Pilot — 单独授权的不可分析阶段

冒烟、pilot 和操纵检查同样是执行，不能被放在治理边界之外。需要 pilot 时，Author 应先冻结一份范围更窄的
pilot execution request，由 Hat B 单独批准，并至少写明 `phase: pilot`、最大 attempt/费用、操纵检查、停止条件，
以及 `analysis_eligibility: excluded`。pilot 结果不得进入主比较、效应估计或确认性样本，也不得事后转为可分析数据。

pilot 通过只说明可以准备主执行请求；主运行仍须另出 hash 并重新批准。pilot 发现任务、仪器、utility 或操纵检查
失败时，必须停止，返回 Hat A 修改，产生新 commit/hash；不得在同一个 execution request 下改文案后继续累计样本。
若主运行中才发现同类问题，也应按冻结的停止规则中止并标记该批次，不得现场修复后续跑。

## 决策三：签署后把自由裁量交给机器

批准后，runner 按冻结规则执行：

- 预先生成并保存随机化/交错计划与 seed；
- 强制预算、最大 attempt、validity 和停止规则；
- 不因看见首个命中、接近显著或漂亮轨迹而临时加样本；
- discovery 与 confirmation 分开，发现样本不同时充当稳定性证明；
- 原始 artifact 不覆盖；元数据或解释错误用可哈希 correction sidecar 纠正；
- 分别保留 instrument validity、安全结果、utility、fidelity 和 authorization provenance；
- 结论由预注册的纯函数/决策表计算，人工解释不得覆盖机器 verdict。

本 ADR accepted 时，calendar runner 尚未强制读取批准记录；这是生效时的明确实现缺口，而不是已完成控制。最小闭环要求
runner 在任何付费调用或 tool execution 前读取批准 artifact，重算并比对 `execution_request_hash`，核验 target/provider、
预算、有效期和本次 phase；缺失、过期或不匹配时 fail closed。输出 artifact 至少记录
`authorization_status: approved | lapsed | absent` 与 `execution_request_hash`。在该硬门实现前，不得按本 ADR 启动新的
T1/T2 执行。

**实现状态（2026-07-22）**：calendar runner 已实现上述最小硬门。它在任何 reachability tool 或 provider
调用前读取 `CAL_AUTHORIZATION_FILE`，重算 request hash，并把冻结 runtime 与 code commit/runner SHA-256、phase、
target、provider/deployment、样本上限和 `CAL_BUDGET_CAP_USD` 逐项比对；缺失、篡改、漂移或过期均以退出码 4
fail closed。`--hash-execution-request` 提供离线 hash 计算，输出 artifact 写入批准 provenance。预算控制目前是
hash-bound cap 声明、预检和确定的最大 trial 数，**没有实时 USD usage metering**；artifact 必须如实披露这一点，
不得称作成本熔断。审批服务、签名基础设施和通用 workflow 仍未建设。

`authorization_status` 描述执行动作发生时的授权状态，不由后来过期而追溯改写：在有效授权下已完成的数据仍为
`approved`；批准到期或 execution request 发生语义改变后继续产生的数据为 `lapsed`；从未有对应批准的遗留数据为
`absent`。今后的 runner 应拒绝产生 `lapsed` 或 `absent` 新数据；这两个值保留给遗留、故障和 correction sidecar
的诚实表达。授权状态不改变测量事实，治理更正必须通过 sidecar 追加，不能覆盖原 artifact。

自动化可以压缩同一人的事后自由裁量，但**不会产生人员独立性**。测试全绿、AI reviewer 同意或两次不同会话得出同一结论，都不能把 `person_independence` 从 `none` 改成独立。

## 决策四：证据与报告必须同时表达技术有效性和治理局限

一人两帽的结果不是自动无效。只要 instrument、provenance、scope 和判据成立，它可以是有效的内部技术证据；其限制在于独立性和产品/用户归属，而不是把所有观测一律抹掉。

报告至少披露：

```yaml
technical_validity: valid | invalid | inconclusive
authorization_mode: self_authorized_solo
role_separation: procedural
person_independence: none
independence_verification: not_applicable
adversarial_review: none | ai_agent | peer
adversarial_review_ref: <artifact/ref or none>
trial_user_evidence: absent
operator_attribution: absent
assurance_level: none
target_fidelity: <mock/fixture/etc.>
authorization_status: approved | lapsed | absent
execution_request_hash: <sha256 or none>
```

允许声称：

- 在冻结的 T0–T2 配置中观察到或未观察到某个可复核行为；
- 某次 structured action、state delta 或 deterministic oracle 已闭合；
- 某项预注册比较在内部实验中成立或未成立；
- 结果是 `internal discovery`、`self-authorized confirmation` 或 `engineering evidence`。

禁止声称：

- 独立评估、独立复核或 assessor independence；
- 真实 Trial User 已证明产品可用或 job-to-be-done 成立；
- ADR-0020 C1–C4 因开发者自测而 pass；
- 客户系统、真实 provider deployment 或合规范围得到超出 fidelity 的 assurance；
- 因同一人换了账号、隔了一天或让 AI 审阅，就获得了第二人独立性。

技术上可以单独记录 `oracle_discrimination_technical=true/false`，但没有真实操作员时不得把它改写为 ADR-0020 的「操作员照自己写法完成 C2」。同理，开发者能读懂报告不构成 C3/C4 的用户证据。

### 生效前遗留数据的过渡处置

2026-07-22 的 calendar task-shape 2×2 在本 ADR 冻结前执行，没有 `execution_request_hash` 或 Hat B 批准，且
pilot 后修改过任务文本。它不是对尚未存在规则的追溯性「违规」，也不得补签或倒填批准；应通过不可变 correction
sidecar 标为 `authorization_mode: none (pre-ADR-0022)`、`authorization_status: absent`、
`execution_request_hash: none`、`person_independence: none`。原始测量结果继续作为遗留内部 discovery evidence，
其技术有效性单独判断；它不获得本 ADR 下的合规治理归属。

## 决策五：外部人员只放在信号价值最高的里程碑

独立开发不要求每次 mock run 都找第二个人。优先在以下节点引入轻量外部复核：

1. 第一条 ProbePackage 对外 promotion；
2. 首次 T3、客户 sandbox、真实账号/数据或真实副作用；
3. 首次面向客户或公众的 assurance/report；
4. ADR-0020 或后续真实用户试用；
5. 一项内部结果准备成为长期产品/安全主张时。

外部复核可以是限定范围的同行签署、GitHub approve/deny、专业人员审阅 execution request，或目标用户完成一次真实任务；不要求对方理解整个代码库。其独立性只覆盖实际审过的对象和判断，不自动扩展到整个项目。

## 与既有决策的关系

- **ADR-0018**：T0–T3 定义、capability/fidelity 边界和 promotion discipline 不变；本 ADR 只规定谁可在开发期批准 T0–T2。
- **ADR-0020**：真实操作员试用及 C1–C4 不变；一人两帽的 self-test 只能产内部技术证据，不能替代 Trial User。
- **2026-07-19 第二名 Execution Authorizer 决策**：对 T3、真实副作用、客户数据/系统和对外 assurance 继续完全有效；仅内部 T0–T2 获得本 ADR 的窄例外。
- **Executor/PEP**：人类批准不代替机械 fail-closed。未来真实执行仍须在 dispatch 前检查 immutable action/request、RoE、allowlist 和当前 policy。

## 后果与取舍

正面：独立开发者可以持续推进低风险、可恢复的实验，不必为每次 fixture/mock 验证制造形式审批；同时每次自我授权的冲突、范围和非独立性都进入证据链。角色冻结、hash 绑定、机器判据和 append-only artifact 把最危险的事后自由裁量显著压低。

代价：流程比随手运行更慢，而且它不能回答真实用户和独立 assessor 问题。某些里程碑仍会因缺第二人而 genuinely blocked；这是需要保留的安全边界，不是流程缺陷。

本 ADR 不要求立即实现审批服务、签名基础设施、UI 或新 ontology schema。先用项目内可审计文档、git commit、内容 hash 和现有 artifact 机制执行；等真实 consumer 暴露手工流程的缺陷后，再决定哪些部分值得类型化或产品化。
