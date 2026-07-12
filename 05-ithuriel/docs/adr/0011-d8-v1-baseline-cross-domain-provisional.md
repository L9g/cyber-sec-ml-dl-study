# ADR 0011 — D8 v1 baseline：AI 切片语义固化，跨域通用性 provisional

日期：2026-07-12 · 状态：accepted（三方共识：我 + 搭档 + 用户拍板） · 关联：`0009`/`0010`（搭档审阅两批）、`docs/architecture-seams-D8.md`（v1.3 banner）、`reports/partner-review-2026-07-12.md`、**下一步 = 第二条切片 CE-UK-FW-03（确定性 config-inspection）**

## 背景
搭档审阅两批 + D3(a) 二轮 + code-review F2–F5 全收后，D8 的 **AI prompt-injection bare/defended 切片诚实性闭环已完整**（测试 66/66）。搭档建议"同步为 D8 v1 稳定契约"。我提异议（搭档采纳）：**不能现在宣布跨域稳定**——这与"让两条切片决定"的纪律自相矛盾。本 ADR 记录收敛后的 baseline 边界。

## 决策：固化「已验证语义」，但不声称「跨域通用」
- **✅ D8 v1 固化（避免自身漂移）**：AI 切片的已验证语义——诚实闸门 `assertable = valid ∧ ¬underpowered ∧ ¬differential_attrition ∧ ¬context_invariant_mismatch`；`joint_verdict`（独立算 raw inputs、confound fail-closed、语义=可归因防御结论）；per-arm provenance + 两臂 invariant 比较；`bare ASR=0→inconclusive`；`tooling_unsupported→覆盖缺口(进分母)`。这些**在 AI 切片内不再漂移**。
- **⚠ cross-domain contract: PROVISIONAL**：`Finding` / `Evidence` / `AssuranceReport` / `AiRunRecord` / `ComparisonSpec` / `joint_verdict` **明显带 AI 实验形状**（`n_runs`/`asr_ci95`/`success_rate`/bare-vs-defended 比较），**对确定性控制的适用性尚未证明**。不提前声称它们是所有控制的通用答案。
- **一句话契约**（seams v1.3 banner）：
  > D8 v1 固化 AI prompt-injection bare/defended 切片的已验证语义；其对确定性 config-inspection 的适用性仍为 provisional，由第二条切片验证。
- **不做**：不宣布 schema stable；**不改 `ontology_schema.yaml` 预判确定性检查需要哪些字段**（据真实摩擦定，守冻结）。

## 为什么这样分（诚实性 > 对称性）
D8 内部已验证语义可固定（防自身漂移）；但**跨域通用性是本项目的核心 claim、尚未有第二个数据点**。AI 切片单独证明不了"同一套 ontology/证据/保证语义能跨非确定性 AI 与确定性安全检查"——那正是第二条切片要验的。提前 stamp "stable" = over-claim（违反 CLAUDE.md 如实报告）。

## 切片路线（三方共识，一次一个新变量）
- **Slice 1（已完成）**：非确定性 AI 测量 + mock execution（AI-AGENT-PI-01）。
- **Slice 2（下一条）**：确定性 config-inspection + read-only 本地证据（**CE-UK-FW-03 default-deny**——裁定窄、易成确定性布尔；优于 CE-UK-SC-01 软件清单，后者会牵出批准基线/版本生命周期/资产范围→膨胀成供应链/资产治理）。
- **Slice 3（延后）**：active probe + RoE / PEP / approval（CE-UK-FW-01 automated_test）。

## Slice 2 要逼出的 schema 问题（观察、不提前设计）
`AiRunRecord` 装不下确定性检查（无 n 次跑/success_rate）。届时观察：① `Finding` 除可选 `AiRunRecord` 是否已够表达确定性裁定 ② 单条 Observation + rule_version 挂哪 ③ `EvidenceManifest` 能否同时承载 AI trial artifacts 与确定性配置快照 ④ `verdict_mode=automatic` 够不够 vs 需要 `verdict_source` 新形状 ⑤ 无 `ComparisonSpec` 时 `AssuranceReport` 是否仍语义完整 ⑥ control→capability→adapter 最小匹配形状。**只有被真实切片逼出才加 `deterministic_run_record`/`verdict_source` 等字段——不提前设计对称抽象。**

## 验证
本 ADR 为文档/契约边界记录，无代码改动。测试仍 66/66；`ontology_schema.yaml` 未动。
