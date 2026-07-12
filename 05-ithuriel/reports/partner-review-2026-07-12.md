# Ithuriel partner review — 2026-07-12

总体判断：方向正确、差异化层边界克制，`bare ASR=0 → inconclusive`、内容寻址 manifest、注册表悬空引用校验都值得保留；但当前“诚实闸门”仍有可产生过度声明的漏口。
设计层 3 条 / 代码层 5 条 / 纪律层 0 条。
两层模型与 thin-slice 纪律本身成立；本次没有建议建设桶 B，也没有建议扩写借来的扫描/防御底座。
基线验证：`.venv/bin/python -m pytest src/tests/ -q` → `55 passed`。

| ID | 层 | 严重度 | 位置 | 一句话 |
|----|----|--------|------|--------|
| D1 | design | high | §4.1 / seams §7 differential attrition | 差分删失在契约中要求使 delta 失效，实际数据模型却没有 `confounded` 状态，最终只能写 note |
| D2 | design | high | §4.5 ComparisonSpec | `invariants` 是一份共享上下文快照，不是 baseline/treatment 两臂的比较，无法执行“未声明差异即 invalid” |
| D3 | design | high | §4.3 security⊗utility | defended Finding 仍可在 utility=0 时标 `pass`，tradeoff 附注没有落实“安全与效用共同决定防御通过” |
| C1 | code | high | `scripts/run_bare_vs_defended.py:245` | 严重 differential attrition 只追加 note，`security_delta_assertable` 仍可为 true |
| C2 | code | med | `src/ithuriel/derive.py:53` | defended utility 未测量时被分类为 `blocks_by_refusing`，把未知当成低效用 |
| C3 | code | high | `scripts/run_bare_vs_defended.py:118` | 全局 provenance 只记整跑首个响应，bare/defended 实际 served model 漂移会被隐藏 |
| C4 | code | med | `src/ithuriel/derive_session.py:154` | `tooling_unsupported` 被构造成无理由的 `not_applicable`，与冻结 schema 的明确语义相反 |
| C5 | code | med | `src/ithuriel/models.py:71` | `AiRunRecord.n_runs` 实装为 n_valid，丢失 total attempts/error accounting 并违反 schema 定义 |

### D1 — 差分删失没有进入可表达的裁定状态
- 层 / 严重度：design / high
- 位置：§4.1 valid⊥underpowered；`docs/architecture-seams-D8.md:81`；`src/ithuriel/models.py:118`
- 触发场景（代码层必填，输入→错误输出）：n/a
- 我的判断：这是否 §6 已列的 F2–F5？☐ 否，新发现
- 建议（要落到具体字段/行为，非“考虑重构”）：给比较裁定增加最小的 `confounded` 表达（可以是 `assertable=false` + 新 `invalidity_reason=differential_attrition`，无需建设统计机器）；明确 `assertable = valid ∧ ¬underpowered ∧ ¬confounded`。删失阈值暂可沿用 harness 现有规则并版本化。
- 挑战纪律？：否；这是把已经冻结的 seams §7 语义落地，不是加 parked 机器。

### D2 — ComparisonSpec 没有实际比较两个 MeasurementContext
- 层 / 严重度：design / high
- 位置：§4.5 ComparisonSpec；`src/ithuriel/derive.py:240`；`src/ithuriel/derive_session.py:202`
- 触发场景（代码层必填，输入→错误输出）：n/a
- 我的判断：这是否 §6 已列的 F2–F5？☐ 否，新发现
- 建议（要落到具体字段/行为，非“考虑重构”）：最小改法是让每臂携带自己的不可变 context/hash，`build_comparison` 删除两边唯一允许的 `defense_hash` 后做 canonical equality；不相等时强制 `assertable=false` 并列出差异字段。当前 `invariants=mctx` 只能声明期望，不能证明期望成立。
- 挑战纪律？：否；这是 seams #5 已承诺的 fail-closed 检查，形状不必扩成 ExperimentManager。

### D3 — 防御的 `pass` 没有落实 security⊗utility 联合语义
- 层 / 严重度：design / high
- 位置：§4.3 security⊗utility；`docs/architecture-seams-D8.md:82`；`src/ithuriel/derive.py:214`
- 触发场景（代码层必填，输入→错误输出）：n/a
- 我的判断：这是否 §6 已列的 F2–F5？☐ 否，新发现
- 建议（要落到具体字段/行为，非“考虑重构”）：不要让 `defended ASR=0` 单独产生“防御通过”的语义。若该 Finding 只裁定 PI 安全控制，应把其含义明确命名为 security-axis verdict，并另给 comparison 一个联合 verdict；若 Finding 就代表防御效果，则 utility 未保住时不得 `pass`。当前 `pass + rationale 说明 utility=0 + blocks_by_refusing` 对下游机器仍是绿色状态。
- 挑战纪律？：否；保留三值 tradeoff 和未观测类都合理，问题是联合语义尚未进入机器可判字段。

### C1 — 差分删失只告警、不关闭 delta
- 层 / 严重度：code / high
- 位置：`scripts/run_bare_vs_defended.py:245`、`scripts/run_bare_vs_defended.py:275`
- 触发场景（代码层必填，输入→错误输出）：
    输入：`N_TRIALS=40`，bare `n_valid=40`、defended `n_valid=5`，两臂 CI 不重叠且 bare ASR>0。两臂都满足当前 `MIN_RUNS=5`，删失差为 35，超过阈值。
    结果：代码只向 `notes` 加 differential-attrition 文本；`measurement_valid=True`、`underpowered=False`，因此输出 `security_delta_assertable=True`，与 seams “该 delta 标 confounded/inconclusive”冲突。对冻结 fixture 的最小变体复现得到 `assertable=True, invalidity_reasons=[]`。
- 我的判断：这是否 §6 已列的 F2–F5？☐ 否，新发现
- 建议（要落到具体字段/行为，非“考虑重构”）：计算布尔 `differential_attrition_confounded`；触发时令 `security_delta_assertable=False`，并在 JSON/ComparisonSpec 中输出 `differential_attrition` invalidity reason，不能只写自然语言 note。
- 挑战纪律？：否

### C2 — utility 缺失被判成 blocks_by_refusing
- 层 / 严重度：code / med
- 位置：`src/ithuriel/derive.py:53`
- 触发场景（代码层必填，输入→错误输出）：
    输入：`measurement_valid=True, assertable=True, security_delta=-0.8, bare_asr_ci_low=0.7, defended_asr_ci_low=0.01, bare_utility=0.9, defended_utility=None`。
    结果：`preserved=False`，返回 `("blocks_by_refusing", None)`；实测反例已复现。没有 defended utility 证据，却生成了确定的拒绝式防御分类。
- 我的判断：这是否 §6 已列的 F2–F5？☐ 新发现；与 F2 同属 `None`/0 语义族，但不是 F2 所列的 `utility_delta` 表达式。
- 建议（要落到具体字段/行为，非“考虑重构”）：`defended_utility is None` 时返回 `(None, "utility_unmeasured")`；给 `TradeoffUnclassified` 增加这个由真实空值路径触发的 advisory 枚举。只有实际测得 `< BLOCK_UTIL` 才能判 `blocks_by_refusing`。
- 挑战纪律？：否

### C3 — 首响应全局钉死会隐藏两臂模型漂移
- 层 / 严重度：code / high
- 位置：`scripts/run_bare_vs_defended.py:118`、`src/ithuriel/provenance.py:56`、`src/ithuriel/derive.py:244`
- 触发场景（代码层必填，输入→错误输出）：
    输入：交错运行时 bare 首个响应返回 `response.model=snapshot-A`，随后 provider 滚动部署，defended 响应返回 `snapshot-B`（或不同 `system_fingerprint`）。
    结果：bare/defended 共用全局 `PROV`；`record_response` 在首个 `served_model` 非空后幂等跳过，最终只记录 A。`build_comparison` 又复制这份共享 mctx，于是输出看似 invariant 相等并可能断言 defense delta，实际 treatment 之外的 model version 已漂移。
- 我的判断：这是否 §6 已列的 F2–F5？☐ 否，新发现
- 建议（要落到具体字段/行为，非“考虑重构”）：至少按 cfg 维护 `PROV[bare]` / `PROV[defended]` 并把响应捕获绑定到对应 pipeline；比较前核对 served model、fingerprint、temperature/seed 等 invariant。若一臂内部也出现多值，记录集合并使比较失效。
- 挑战纪律？：否；这是现有 provenance 与 ComparisonSpec 接缝的闭环。

### C4 — tooling_unsupported 被错误编码为 not_applicable
- 层 / 严重度：code / med
- 位置：`src/ithuriel/derive_session.py:154`、`src/ithuriel/models.py:97`、`docs/ontology_schema.yaml:52`
- 触发场景（代码层必填，输入→错误输出）：
    输入：CSV 一行 bare/defended 均 `n_valid=0`，原因是 provider/tool-use 404。
    结果：`invalidity_reasons()` 得到 `tooling_unsupported`，随后 `_not_applicable_report()` 产生 `status=not_applicable, rationale=None`。冻结 schema 明确规定 tool-less/unsupported 不是 not_applicable，且 not_applicable 必须有 reason；模型 validator 也没有拦截。
- 我的判断：这是否 §6 已列的 F2–F5？☐ 否，新发现；但它是 ADR-0005 D3 的既有显式决策，本审阅认为该决策应撤销，因为已与更高权威的冻结 schema 冲突。
- 建议（要落到具体字段/行为，非“考虑重构”）：该格输出 coverage gap `unsupported`（进入分母）而不是 Finding `not_applicable`；若当前必须保留 Finding，临时用 `inconclusive` 并带理由也比 NA 语义污染更安全。同时让 Finding validator 强制 `not_applicable` 带 rationale，防止再次静默产生无理由 NA。
- 挑战纪律？：否；恰恰是在维护 schema 冻结的权威语义。

### C5 — n_runs 把总尝试数收缩成有效样本数
- 层 / 严重度：code / med
- 位置：`src/ithuriel/models.py:71`、`src/ithuriel/derive.py:181`、`src/ithuriel/derive_session.py:127`
- 触发场景（代码层必填，输入→错误输出）：
    输入：每臂计划并实际尝试 10 次，其中 5 次 `execution_error`、5 次有效，1 次攻击成功。
    结果：Finding 的 `run_record` 输出 `n_runs=5, n_success=1, success_rate=0.2`；冻结 schema 定义 `n_runs=total attempts`，seams 也要求同时保留 `n_attempted/n_valid/n_execution_error/n_detector_error`。汇总级报告没有 raw artifact，错误计数因此从报告中消失，消费者会误读为只尝试了 5 次且无执行错误。
- 我的判断：这是否 §6 已列的 F2–F5？☐ 否，新发现
- 建议（要落到具体字段/行为，非“考虑重构”）：保留 `n_runs=n_attempted` 的既有 schema 含义，并给 `AiRunRecord` 增加已经被真实 execution-error 数据逼出的 `n_valid`、`n_execution_error`、`n_detector_error`；`success_rate` 继续明确以 n_valid 为分母。若不愿加字段，则至少不能把 n_valid 写进名为 n_runs 的字段。
- 挑战纪律？：否；这些计数已在 seams 和 harness 中真实出现，不属于想象性补字段。

## 明确认同、无需改动的部分

- “Base=借、Differentiator=建”的边界画得对；runner 保持 AgentDojo 薄封装是合理选择。
- `bare ASR=0 → inconclusive` 在 full-run 与 session 两条路径一致，当前没有发现漏回 `pass` 的路径。
- `measurement_valid` 与 `underpowered` 分字段表达、CI 重叠时 fail-closed 的基本方向正确；问题是 C1 所述第三个 confound 未并入最终闸门。
- `blocks_preserving_utility` 留定义但不伪造 fixture 的取舍合理；问题不是未观测类，而是 C2 对“未测量”的分类。
- 内容寻址 canonical JSON 的 `sort_keys + compact separators + ensure_ascii=False` 对当前 JSON 数据给出了稳定字节；manifest 不采用全局线性链的方向正确。
- 注册表的 `Finding.control_id → standards_refs → registered source` 主闭环已经闭合；`extra="ignore"` 对当前只读 thin slice 可接受，必需字段拼写错误仍会由 Pydantic 报错。
