# ADR 0004 — 首个结构化 Finding（差异化层『建』半边最薄切片）

日期：2026-07-11 · 状态：draft（供讨论） · 关联：`0003-injectable-target-and-first-assertable-defense-delta.md`、`docs/architecture-seams-D8.md` v1.2（#4/#5/#6/#8）、`docs/ontology_schema.yaml` v0.6

## 背景
此前只跑了 seams 契约的**「借」半边**（AgentDojo runner → flat run JSON，`results/d8_bare_vs_defended.json`）。项目卖点「可审计/可复现的保证结论」在**「建」半边**，一直被推后（桶 A 的数据形状条目）。本轮落地最薄「建」切片：**flat run JSON → 结构化 Finding + 证据 manifest + scope 声明 + ComparisonSpec**。

纪律：**据真实摩擦反推字段，不提前按论文设计**。fixture = ADR-0003 的 detector 格真跑（`transformers_pi_detector`，n=40+40，delta −1.0 可断言），冻结副本入 `src/tests/fixtures/d8_run_detector.json`（`results/*.json` gitignored=ephemeral）。

## 落地形状（`src/ithuriel/`）
- `models.py` — pydantic v2：`Finding` / `AiRunRecord` / `ComparisonSpec` / `ScopeStatement` / `EvidenceManifest` / `AssuranceReport`。**只取 schema v0.6 required + 本数据真用到的字段**；冻结/parked 字段（remediation / threat_model / fidelity_gap / llm_judge …）**不加**。
- `derive.py` — 纯函数 `derive(dict)->AssuranceReport` + `__main__`（`python -m ithuriel.derive <in> [-o out]`）。
- `src/tests/test_derive.py` — 11 条确定性代码契约（贴死值/边界，与模型无关）。
- env：`uv add --dev pytest`；`[tool.pytest.ini_options] pythonpath=["src"]`（`package=false`，不做 editable install）。

## 四抉择定论（对话中我给默认、用户「按步骤开工」= 采纳；此处存档以便事后纠）
- **A（最关键）：一格 → 2 条 Finding，delta 不是 Finding。** schema 里 Finding = `(control × target_variant)` 裁定，`status_rule`=success_rate>0→fail。故 bare(ASR=1.0)=**fail**、defended(ASR=0)=**pass**；`−1.0` 的 assertable delta 是**跨两条 Finding 的 `ComparisonSpec`（seams #5）**，非单条「delta Finding」。纠正了记忆里「升成结构化 Finding」措辞易把 delta 压成单 Finding 的隐患。
- **B：security⊗utility 一条 Finding、不拆两条。** defended 那条 `status=pass`（security）但 rationale 内嵌 utility 附注（under-attack utility=0=检到即 abort，拿可用性换安全）。守 seams §7「绑同一 defense 联合报告」，防「拒绝一切」的退化防御在纯 security 轴刷满分。
- **C：只用磁盘上的 detector 一格。** harness 覆写同名文件 → repeat/spotlighting 两格的数只在 ADR-0003 文字里，**未并入本 run 证据**（scope.not_covered 显式列出）。
- **D：`control_id` 暂硬编字符串 `AI-AGENT-PI-01`。** 未建 control registry（桶 B）；`severity="high"` 亦为占位（真值应来自 `control.severity_if_failed`）。

## 步骤 3 暴露的真实缺口（=「据真实摩擦定字段」的实证，不现补）
harness 的 `meta` **未捕获** `ai_run_record` 需要的钉死字段与 seams §5 的 MeasurementContext 多个字段：
- `AiRunRecord.model_version / temperature / seed` → 暂 `None` 并如实标 gap（不编造）。`model` 仅存 alias（`mistral-small-latest`）非快照串。
- MeasurementContext 缺 `corpus_version / scenario.version / detector_version / aggregate_rule_version / seed_schedule / adaptive_level` → measurement_context `_absent_seams5_fields` 显式列出。

**含义**：下一次动 harness 时补记这些是「protocol-reproducible」的前置（schema `reproducible` 级别 2）。本 ADR 只**暴露**缺口、不提前给 harness 加字段（等真需要复现时的摩擦）。

## 证据/scope 形状
- **EvidenceManifest（seams #6）**：每条 raw trial → `content_hash(canonical(trial), 'trial:')` = 不可变 artifact；`index[config]=[hashes]`；`run_root=content_hash(artifacts∪index∪mctx, 'run:')`。`Finding.evidence_refs` 精确指向本 config 的 per-trial 哈希（raw→ref 不压平）。单测证 `run_root` bit-reproducible。
- **ScopeStatement（seams #8）**：`assurance_level: none` + 结构化 `not_covered`（进覆盖分母的 gap），挂 report 层**非 Finding 字段**（治理笔记 4.3）。
- **ComparisonSpec（seams #5）**：`treatment_field=defense_hash`，`assertable=measurement_valid ∧ ¬underpowered`（承载 harness 裁定、不重算），`invariants`=treatment 外须全等字段（fail-closed）。

## 一个 schema 张力（记录、未改 schema）
`finding_schema.required_fields` 列 `severity`，但其描述=「status==fail 时继承」。pass Finding 语义上无 severity → 模型里设 `Optional`、fail 时校验必填、pass 时 `None`。**未动 `ontology_schema.yaml`**（守冻结；这是 required-list 与语义的措辞张力，非不可逆形状问题，留待 schema 下次修订顺带澄清）。

## 明确**不建**（守冻结/桶 B）
control registry 加载 · CoverageLedger/rollup/coverage 分 · Claim/Assurance Engine · repeat/spotlighting 两格并入 · LLM-judge detector 及其独立 run_record · `prev_evidence_hash` 线性链（schema 已注记不作长期形状，本切片用 manifest+run_root 取代）。

## 验证
`python -m ithuriel.derive results/d8_bare_vs_defended.json` → `reports/d8_assurance_report.json`（2 findings，fail=1，run_root 稳定，assertable delta −1.0，scope=none）；`pytest src/tests/test_derive.py` 11/11 passed。

## 待办
1. 下一数据步（承 ADR-0003 方向 1）：拿已知易破的老/小模型（gpt-4o-mini / llama-3.1-8b）跑同格，作 detector −1.0 的**复现检验**兼**部分注入（0<sr<1）fixture**——验 `_status_from_success_rate` 的一般分支与 `inconclusive` 路径在真数据上成立。
2. harness 补记 model_version/temperature/seed + MeasurementContext seams §5 缺口（protocol-reproducible 前置），由真实复现需求触发、非现补。
3. borderline-confidence → `inconclusive` 需 tolerance 概念（schema status_rule 提及）——尚未定义，延后。
