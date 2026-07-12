# ADR 0014 — 桶 B 最薄切片：CoverageLedger（跨控制 rollup + graded coverage/gating）

日期：2026-07-13 · 状态：accepted（用户拍板走桶 B、方案 A 分支） · 关联：`0011`（D8 v1 baseline）、`0012`（FW-03 config）、`0013`（FW-01 probe）、`docs/ontology_schema.yaml` §scoring（**本 ADR 实现之、不改之**）、`docs/architecture-seams-D8.md` #8（scope-gap=CoverageLedger 种子）

## 背景
三条切片落了**三个控制**（PI-01 AI-High / FW-03 config-Medium / FW-01 probe-Medium）。搭档路线：「多控制覆盖出现，再抽 CoverageLedger」。条件已到 → 建**桶 B 最薄切片**：跨控制 rollup + graded coverage/gating。**只聚合、不重算裁定**。

## 决策：实现冻结的 ontology scoring、不改 schema
`ontology_schema.yaml` §scoring 已定（frozen）：
- `coverage = 每轴「status==pass 的**适用**控制」占比`；
- `gating = 任一 High/Critical fail → 该轴 not_ready`（**单个 fail 不清零轴、只降覆盖率**，schema 注：graded）；
- denominator = **适用**控制：`not_applicable` 排除；unsupported/out_of_scope/inconclusive/gap **进分母**算未 pass（D1 覆盖词汇）。
CoverageLedger 在 pydantic advisory 层实现此规则、**未动 yaml**。

## 落地形状（最小）
- `ledger.py`（新）：`ControlOutcome{control_id, domain, severity, status, gap_kind}` · `AxisCoverage{axis, key, applicable, passed, coverage, not_ready, gating_reason}` · `CoverageLedger{outcomes, axes, generated_from}` · `control_outcome(report)`（归约）· `build_ledger(reports)`（按 `domain` 轴 rollup，纯函数、不重算）。
- 测试 `test_ledger.py`（8）：用**三真实控制 builder**（derive / config_inspection / port_scan）产 report → rollup。

## 端到端（三真实控制）
- 全 pass：ai_agent_security 1/1、network_security 2/2，两轴 ready。
- PI-01 spotlighting（defended **High fail**）：ai_agent_security **NOT_READY**（gating）、coverage 0/1；FW 两 Medium 不受影响。
- FW-01 **gap**（RoE out_of_scope）：network_security coverage 1/2（gap 进分母、非 pass），但**仍 ready**（gap 非 fail、不触发 gating）。
→ graded coverage 与 gating 的区分（fail 降覆盖、只有 High/Critical fail 才 not_ready）忠实落地。

## 归约的真实摩擦（如实标、不提前设计）
- **⭐ 多 Finding 归约**：PI-01 report 有 bare+defended 两条 → rollup 取 **defended（被保证的部署配置）** 的 `Finding.status`。**摩擦**：defended 可能 security-pass 而 `ComparisonSpec.joint_verdict=utility_failed` —— coverage 该看单臂 `Finding.status`（security 轴）还是 `joint_verdict`？本切片先用 `Finding.status`，**记录待第 4 个消费场景逼定**（不提前改）。
- **`gap` 是 rollup-only 状态**（非 Finding 四态）：0-Finding 覆盖缺口在 rollup 层承载为 `gap`（进分母、非 pass）。呼应 slice 3 的 out_of_scope —— **结构化 `ScopeGap` 模型**候选更强了（现两处用字符串/rollup-status 承载），仍未被逼到必须建。
- **ce_area / csf2_function 两轴**（schema §scoring.rollup_axes 列出）：需从 `standards_refs` 解析（cyber_essentials→ce_area、nist_csf→csf2_function）→ **derivable-deferred**（本切片只做 `domain` 轴，够验 rollup+gating 机制）。

## 明确延后（仍桶 B、需更多摩擦）
ExperimentManager · Claim/Assurance Engine · primary/root-cause rollup（schema §root_causes 亦标 DEFERRED）· PlanCompiler（capability planner，现单控制单 adapter 1:1，无候选排序需求）· ce_area/csf2_function 轴。

## 守纪律
**未动 `ontology_schema.yaml`/profile**；CoverageLedger 只读 report、不重算裁定；scoring 规则照 schema 实现。

## 验证
`pytest src/tests/` = **115/115**（107 + 8 ledger）。三真实控制 rollup 端到端如上；High fail gating / Medium fail 只降覆盖 / gap 进分母 / not_applicable 出分母 全绿。
