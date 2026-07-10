# Ithuriel 架构框图 v1 审阅结论

日期：2026-07-10

审阅对象：

- `docs/Ithuriel 架构框图 v1.htm`
- `docs/Cyber+AI_安全+合规Agent项目规划草案.md`
- `docs/papers/ai-redteam-pipeline-learning-note.md`
- `docs/ontology_schema.yaml`
- `docs/UK_Region_Profile_v0.2.yaml`

## 1. 总体结论

当前架构的产品方向正确，大约 75% 已经合理，但它目前更接近一张“产品概念与逻辑关系图”，还不是可以直接冻结编码的运行架构。

其中最正确的决策有四个：

1. 不重写 `nmap`、garak、PyRIT、AgentDojo 等成熟工具。
2. 插件只产出 `ActionPlan`，不直接产生外部副作用。
3. 将 Evidence → Finding → 覆盖度 → Reporter 作为产品脊柱。
4. 将探索循环、确认循环和真实执行环境分开。

但是，“蓝色全部借、绿色全部建”的边界划分过于绝对。更准确的原则应当是：

> 借用通用机制；自研领域语义、可信契约和保证逻辑。

通用执行、调度、存储、隔离和策略求值机制可以借用；但 `ActionPlan` 的安全契约、执行前强制策略点、证据生成语义、覆盖度语义和保证结论边界必须由 Ithuriel 自己掌握，否则系统最关键的可信性实际上被外包了。

## 2. 当前架构中合理的部分

### 2.1 两层模型方向正确

将成熟工具和执行基础设施作为 base 层，将标准蒸馏、Evidence、Finding 和 assurance 作为差异化层，能够避免把项目做成另一个通用扫描器平台。

### 2.2 插件不直接执行的约束正确

插件只返回 `ActionPlan`，所有命令和模型调用统一经过 Executor，是实现 RoE、审批、预算、凭据隔离和审计的必要前提。

### 2.3 双循环设计合理

- 探索循环用于发现新攻击、变体和长尾场景。
- 确认循环使用冻结、版本化语料进行可重复回归。
- 毕业闸门将稳定命中的探索场景晋级到确认语料。

这一结构优于把不同工具排列成一条单向“保真度阶梯”。

### 2.4 将真实副作用层推迟是合理的

MVP 先通过公开 mock benchmark 跑通端到端证据链；中期建设 seeded tenant/digital twin；后期才进入 gated 客户 sandbox。这一顺序能够先验证产品核心假设，同时避免过早承担真实环境的合同、授权和恢复风险。

### 2.5 Python MVP 的选择合理

早期主要风险是抽象错误、证据语义不完整和安全边界过松，而不是 Python 性能。现阶段不应为了预想中的性能问题重写扫描器或提前引入 Rust/Go 双技术栈。

## 3. 必须优化的架构问题

### 3.1 缺少真正的 PlanCompiler 和 RunOrchestrator

当前调用顺序是：

```text
profile_loader → policy_engine → plugin_registry → plugin
```

但 `profile_loader` 不应负责生成完整的可执行计划。一个计划至少需要同时考虑：

- Region Profile 和 control 定义；
- 被测目标、资产、身份、环境及其快照；
- 插件当前实际能力；
- RoE 和客户授权范围；
- 风险、预算和审批状态；
- Action 之间的依赖关系；
- 无法执行或未被授权的覆盖缺口。

建议新增：

- `PlanCompiler`：把上述输入编译成不可变的 `RunPlan/ActionGraph`。
- `RunOrchestrator`：管理并发、暂停审批、重试、取消、恢复和状态持久化。

MVP 可以实现简单的数据库状态机。当系统真正出现跨天审批、大量故障恢复或分布式 worker 时，再引入 Temporal 等持久化工作流基础设施。

### 3.2 PolicyEngine 的调用时机不安全

图中 PolicyEngine 在插件生成具体 `ActionPlan` 之前运行，因此它看不到最终的：

- 二进制和完整参数；
- 实际目标；
- 模型端点；
- token 和成本；
- 凭据作用域；
- 具体副作用类型。

策略至少应在两个阶段执行：

1. **计划阶段**：判断 control、target、risk 是否允许进入计划。
2. **执行前阶段**：对规范化后的具体 Action、授权票据和当前环境重新判定。

Executor 必须是 Policy Enforcement Point，不能仅仅相信上游曾经检查过。对于高风险动作，还应把审批绑定到一个具体 Action hash，而不是笼统地提升整次运行的权限。

通用策略求值器可以借用 OPA 等现有实现；但 RoE 语义、策略输入模型、审批票据和执行强制点应由 Ithuriel 自研并测试。

### 3.3 Evidence 生成过程需要拆分

当前图中是“工具原始输出 → Evidence 归一化”，中间缺少了执行事实、原始材料和结构化观察之间的边界。

建议拆成：

```text
Executor
  ├─ ExecutionReceipt：实际执行了什么
  ├─ RawArtifact：不可变原始输出
  └─ AuditEvent：策略、审批、时间和身份
          ↓
Parser / Normalizer
          ↓
Observation：从原始输出中观察到了什么
          ↓
EvidencePackage：Observation + 原始材料 + 测量上下文
          ↓
Adjudicator：按版本化规则裁定
          ↓
Finding
```

关键约束如下：

- Parser 不能覆盖或替代原始输出。
- 工具和 Executor 不能直接产生最终 Finding。
- Finding 必须引用裁定规则版本、Evidence 和适用范围。
- 自动裁定、LLM judge 和人工裁定应共享同一输出契约，但保留各自的审计信息。

### 3.4 缺少“范围与覆盖账本”

当前四态 Finding 不足以表达以下覆盖缺口：

- `not_tested`：适用，但本次没有执行；
- `unsupported`：适用，但当前没有工具或适配器；
- `out_of_scope`：因合同或授权边界未进入本次评估；
- `not_applicable`：该 control 对目标确实不适用；
- `inconclusive`：已经执行，但证据不足或存在歧义。

规划草案中“没有现成工具覆盖的控制先留 `not_applicable`”与 pipeline note 的 D1 决策冲突。应以后者为准，避免未测试表面被排除出覆盖率分母，从而产生假绿色。

建议新增独立的 `CoverageLedger`：

- 记录每个 control × target 的适用性；
- 记录是否授权、是否支持、是否执行；
- 将覆盖缺口和 Finding 分开；
- 作为范围声明与覆盖度计算的唯一数据源。

不是所有覆盖缺口都应该伪装成 Finding。

### 3.5 Reporter 不应负责形成保证结论

Reporter 应只负责 JSON、Markdown、HTML、PDF 等输出渲染。建议在 Reporter 之前增加 `Claim/Assurance Engine`，负责回答：

- 一个 Finding 支持哪条 control objective？
- 它是直接证据、部分证据还是仅提供背景？
- 还缺少哪些配置、文档或人工证明？
- 结论适用于哪个目标、时间和环境？
- 结论的有效期和证据等级是什么？

这才是安全测试与合规保证真正汇合的位置。

一个 prompt-injection Finding 不能因为映射了“NIST AI RMF MEASURE”，就自动表示整个 MEASURE 功能已经满足。标准映射必须有明确的 claim、映射强度、适用条件和缺失证据。

### 3.6 bare/defended 不应只是一个差分开关

bare/defended 应由 `ExperimentManager` 管理为配对实验，至少固定或记录：

- 相同 target snapshot；
- 相同模型和工具版本；
- 相同场景集合；
- 相同运行参数；
- 防御配置 hash；
- 运行顺序、失败和重试；
- 攻击强度和自适应等级。

只有在测量条件兼容时才能计算差分。探索语料进入确认循环时，还应执行独立重跑或使用 holdout，避免使用“发现该攻击的样本”同时证明它具有稳定性。

### 3.7 真实执行层必须具有明确调用关系

当前图为了保持连线零交叉，刻意没有画真实层的入向箭头。这适用于演示图，但不能作为实现契约。

建议把真实度表示为可替换的执行后端：

- `MockBackend`
- `SeededTenantBackend`
- `CustomerSandboxBackend`

它们共享 Action 协议和 Evidence 协议，但拥有不同的：

- 策略和审批要求；
- 凭据和网络边界；
- 隔离强度；
- 副作用恢复机制；
- fidelity gap 描述。

### 3.8 plugin_registry 的匹配语义需要调整

当前按 `control × target × method` 匹配插件，容易让插件和某一标准 control 过度耦合。

更好的方式是：

- 插件注册 capability、支持的 target type、Action 类型、风险和输出 schema；
- Test 定义需要什么 capability；
- PlanCompiler 再将 Control/Test 与 capability 匹配。

这样同一个技术能力可以服务多个标准和多个 region profile，避免为每个 control 复制插件。

### 3.9 模型调用中的 PII 处理需要区分两个阶段

“PII 脱敏”不能笼统处理：

- 如果在发送给被测目标前脱敏，可能改变测试本身；
- 如果只在日志中脱敏，则原始证据仍需要加密、分权和保留策略。

PII 检测和脱敏算法可以借用成熟库；但何时脱敏、是否保留加密原文、谁可以访问和何时删除，必须是 Ithuriel 自己的证据治理策略。

## 4. 建议的修正版主链

```text
标准原文 → Control/Claim Graph ← Region Profile
                          ↑
Target Inventory + Scope + Plugin Capabilities
                          ↓
                PlanCompiler
                          ↓
       RunPlan / ActionGraph + CoverageLedger
                          ↓
              Policy Decision + Approval
                          ↓
                RunOrchestrator
                          ↓
       执行前再次 Policy Enforcement
          ┌───────────────┴───────────────┐
   Command/Config Backend          Model/Agent Backend
          └───────────────┬───────────────┘
        RawArtifact + ExecutionReceipt + AuditEvent
                          ↓
        Observation → EvidencePackage → Finding
                          ↓
             Claim / Assurance Engine
                          ↓
                Rollup → Reporter
```

`ExperimentManager` 和攻击语料治理应横跨 Orchestrator、Evidence 和 Finding，而不是作为一个普通插件。

## 5. 应当自研的模块

| 模块 | 建议 | 原因 |
|---|---|---|
| `Control/Claim Graph` 与标准蒸馏 | 自研 | 最主要的安全与合规知识资产；同时提供 OSCAL 适配 |
| `PlanCompiler + CoverageLedger` | 自研 | 把标准、目标、能力和授权编译成可解释计划，是核心创新 |
| Evidence/Observation/Finding/Claim 模型 | 自研 | 这是跨工具的保证语义，不是普通日志格式 |
| 归一化与裁定规则 | 自研 | 工具输出如何成为有边界结论，是产品价值所在 |
| `ExperimentManager` | 自研 | bare/defended 配对、双循环毕业和测量兼容性可形成实际壁垒 |
| 攻击语料治理和场景晋级 | 自研 | 语料版本、provenance、稳定性门槛和覆盖策略是长期资产 |
| ActionPlan 协议和强制执行语义 | 自研 | 可以借执行机制，但必须自己掌握安全不变量 |
| 保证 claim 和报告内容模板 | 自研 | PDF 渲染不是创新，结论结构和边界才是 |

## 6. 应当借用的模块

以下模块不应为了“自主可控”而重写：

- 网络扫描、配置检查和 benchmark 引擎：`nmap`、`nuclei`、AgentDojo、garak、PyRIT、ToolEmu。
- 通用策略求值器，例如 OPA。
- 持久化工作流基础设施，例如后期需要时采用 Temporal。
- PostgreSQL、对象存储、消息队列和内容寻址存储的基础实现。
- OIDC、Vault/KMS、Secrets Manager 等身份和密钥基础设施。
- 容器、seccomp、gVisor、Firecracker 等隔离机制。
- PII 检测、文本脱敏、hash、签名、时间戳和密码学实现。
- HTML/PDF 渲染器、模板引擎和图表组件。
- 模型 provider SDK 和通用 API transport。

对于这些模块，Ithuriel 应自研的是受限 façade、领域配置、证据捕获和安全策略，而不是底层通用实现。

## 7. 性能优化建议

### 7.1 首先优化运行模型，而不是语言

系统的主要延迟将来自：

- 网络请求；
- 外部扫描进程；
- 模型 API；
- benchmark 多次运行；
- 大体积原始证据写入。

因此，最优先的性能工作是：

1. 将串行 pipeline 改成有界并发 DAG。
2. 按 provider、target 和风险等级分别限流。
3. 将原始输出流式写入对象存储，同时计算 hash。
4. 批量写入普通运行事件，但让策略决定、审批和 Finding 保持独立可寻址。
5. 按 source/profile/plugin/corpus/config hash 缓存 PlanCompiler 结果。
6. 避免在 Python 内存中长期保存完整扫描结果和模型轨迹。

### 7.2 Evidence hash chain 不应成为并发瓶颈

当前 `prev_evidence_hash` 线性链在并行运行时可能形成全局写入热点，也难以表达分支执行。

建议：

- 每个 Action 独立生成 content-addressed artifact 和 manifest；
- 每个 Action manifest 包含输入、输出、环境、策略决定和审批引用；
- 运行结束时聚合为 run-level Merkle root；
- 将 run root 锚定到签名、外部时间戳或后期透明日志。

这样既适合并行执行，也能保持证据完整性。其 attestation 结构可参考 in-toto/SLSA 的 artifact、invocation、materials 和 environment 模式，但不应因此声称 Ithuriel 符合 SLSA。

### 7.3 Rust/Go 的引入条件

目前不建议为了性能重写 CommandExecutor、ModelExecutor 或扫描工具。

将来如果实测证明需要下沉，优先候选是：

- 可信 runner；
- 凭据处理；
- 文件和原始证据流式 hash；
- 高密度不可信子进程管理；
- 本地隔离和资源限制。

此时选择 Rust 的首要理由应是内存安全、可信边界和部署可靠性，而不是未经测量的 Python 性能担忧。如果瓶颈主要是分布式调度和网络并发，则 Go 可能更合适。两者不应同时长期维护。

## 8. 建议的实施优先级

### P0：在第一条端到端切片前完成

1. 在架构图中加入 `Target/Scope`、`PlanCompiler`、`RunOrchestrator`。
2. 将策略检查改为计划阶段与执行前双重检查。
3. 定义 `RunPlan`、typed `Action`、`ExecutionReceipt` 和最小运行状态机。
4. 将 RawArtifact、Observation、Evidence 和 Finding 分开。
5. 建立 `CoverageLedger`，落实 D1 状态词汇。
6. 增加最小 `Claim/Assurance` 映射，避免 Finding 直接等同于合规结论。

### P1：第一条切片跑通后完成

1. `ExperimentManager` 和 bare/defended 配对运行。
2. 攻击语料毕业、独立确认和版本治理。
3. content-addressed artifact manifest 和 run root。
4. evidence grade、measurement context 和 claim boundary。
5. OSCAL Assessment Plan/Results 导入导出适配。

### P2：出现真实客户和高保真环境需求后完成

1. Seeded tenant/digital twin。
2. 客户 sandbox 的合同、RoE、审批和恢复机制。
3. fidelity gap 与生产代表性 claim。
4. 签名、外部时间戳、透明日志或可信执行增强。
5. 根据性能和可信边界测量结果决定是否引入 Rust/Go。

## 9. 最终建议

保留当前框图的产品主线，但在 v2 中加入：

- `Target Inventory / Scope`
- `PlanCompiler`
- `RunOrchestrator`
- `CoverageLedger`
- `Adjudicator`
- `Claim / Assurance Engine`
- `Artifact Store / Run Ledger`
- 多阶段 Policy Enforcement

同时将“base 一律借”修订为“通用机制借用、领域契约自研”。

只有完成这些调整，Ithuriel 才会从“多个工具组成的流水线”变成真正可解释、可恢复、可审计并且能够形成有边界保证结论的 Assurance 系统。

## 10. 参考资料

- [NIST OSCAL Assessment Results Model](https://pages.nist.gov/OSCAL/learn/concepts/layer/assessment/assessment-results/)
- [Open Policy Agent Documentation](https://www.openpolicyagent.org/docs)
- [OPA Management APIs and Architecture](https://www.openpolicyagent.org/docs/management-introduction)
- [Temporal Documentation](https://docs.temporal.io/)
- [SLSA Provenance](https://slsa.dev/spec/v1.2/provenance)
- [PyRIT Documentation](https://azure.github.io/PyRIT/)
- [garak repository](https://github.com/NVIDIA/garak)
- [AgentDojo paper](https://arxiv.org/abs/2406.13352)

