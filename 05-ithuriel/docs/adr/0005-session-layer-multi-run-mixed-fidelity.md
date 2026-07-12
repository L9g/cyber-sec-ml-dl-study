# ADR 0005 — session 层（多条件 · 混合保真度 · invalid 子因）

> **⚠ D3 已被 ADR-0009 撤销（2026-07-12，搭档审阅 C4）**：`tooling_unsupported` 不再编码成
> `not_applicable` Finding（那会**出分母**、语义错）。404/工具不支持 = **unsupported、进分母**，
> 现产 findings=[] + `scope.not_covered` 记覆盖缺口。本文 §表/§落地/§D3/§验证 中所有
> 「2501→not_applicable」的表述以 ADR-0009 为准。其余决策不变。

日期：2026-07-11 · 状态：draft（供讨论，**D3 superseded by 0009**） · 关联：`0004-first-structured-finding-differentiator-layer.md`、`0003-injectable-target-and-first-assertable-defense-delta.md`、`docs/architecture-seams-D8.md` v1.2（#4/#5/#6/#8）、`results/experiments.csv`

## 背景
ADR-0004 建了单跑 `derive()`（一格全 per-trial 证据 → AssuranceReport）。但 2026-07-11 本会话真跑了 **5 个条件**（groq-8b / gpt-4o-mini / mistral-3.2 stock / mistral-2501 / mistral-3.2 `_no_names`），暴露单跑理想路径未表示的三个真实现实。**据这些摩擦反推 session 层字段，不提前按论文设计**（守 [[feedback-thin-slice-before-schema]]）。

## 5 跑逼出的字段（每跑一个决策）
| fixture 跑 | 真实现象 | 反推字段/分支 |
|---|---|---|
| mistral-3.2 `stock` vs `_no_names`（同模型 40×：ASR 0.025↔1.0） | **注入 ASR 头号驱动=攻击变体、非模型版本** | `cross_condition_notes` 显式暴露攻击变体摆动（Δ≥0.5）；跨变体不可比 |
| groq-8b（bare ASR=0、n_valid 14/13 of 40） | measurement_valid=False 有两个正交子因 | `InvalidityReason`：`no_positive_control` + `quota_truncated` |
| mistral-3.2 stock（CI 重叠） | 正对照在、但噪声主导 | `InvalidityReason.underpowered`（与上两者正交、可叠加） |
| mistral-2501（全 404 无 tool use） | harness 根本没执行 | `not_applicable` Finding + 无 comparison + `tooling_unsupported`，进覆盖分母 |
| runs 1–4（raw 已被单文件覆盖式冲掉） | 只余 csv 汇总 | `EvidenceCompleteness.summary_only`（evidence_refs 空 + manifest 空，不冒充全证据） |

## 落地形状
- `models.py` 增：`EvidenceCompleteness` / `InvalidityReason` 枚举；`Finding.evidence_completeness`；`ComparisonSpec.invalidity_reasons`；`ScopeStatement.invalidity_reasons`；`SessionReport`（跨条件信封 + 横向观察）。**全带默认值 → 不进 finding_id/run_root 哈希输入 → ADR-0004 的 11 契约不破**。
- `derive.py`：抽 `build_target_ref()`（DRY，全证据/汇总共用、不改既有 finding_id）；`derive()` 加 `completeness`/`invalidity_reasons`/`generated_from` 可选参（默认保持原行为）。
- `derive_session.py`（新）：csv 行→meta/agg 同构；`invalidity_reasons()` 结构化反推子因（tooling 独占、其余叠加）；`_summary_status()`（**bare ASR=0→inconclusive**、非 pass=不冒充『安全』）；`derive_summary_run()`（含 tooling→not_applicable 分支）；`derive_session()`（与全证据 run 同键那条走 `derive()`、其余汇总）；`cross_condition_notes()`。
- fixture：`src/tests/fixtures/d8_session_2026-07-11/`（`experiments.csv` + 唯一存活全证据 `d8_run_full_no_names.json` + README 溯源诚实声明）。
- `src/tests/test_derive_session.py`：12 条确定性契约（含 groq bare inconclusive、2501 not_applicable、攻击变体横向观察、混合保真度、invalidity 正交）。

## 决策
- **D1｜混合保真度 vs 重跑 1–4**：选混合保真度（B）。重跑代价（2501 无法 tool-use、groq 配额、花钱）不值，且**汇总级如实标弱**本身逼出 `evidence_completeness`——比伪造全证据诚实。
- **D2｜bare ASR=0 的 status**：`inconclusive`（非 pass）。宽 CI 上界非零 → 不能声称目标『安全』；正对照缺失是测量失败、不是目标胜利。
- **D3｜tooling_unsupported 独占**：不与其它子因叠加（没执行就无所谓 CI/正对照），走 `not_applicable` 而非 `inconclusive`（后者=测了但没功效）。
- **D4｜session 只聚合不重算**：assertable/delta/underpowered 全承载 harness/csv 的裁定，session 层零重算（守 seams v1.2 §7 单一真相）。

## 明确延后（不在本切片）
- `tradeoff_class`（security⊗utility 分类：ineffective/blocks_by_refusing/…）——本 5 跑全 pi-detector，spotlighting 的 `ineffective` 不在集内、四值凑不齐 → 留下一切片（等纳入 spotlighting/repeat 数）。
- harness 补钉 model_version/temp/seed（ADR-0004 §延后 2，protocol-reproducible 前置）。
- control registry（control_id 续硬编，桶 B）；inconclusive 的 tolerance 概念（ADR-0004 §延后 3）。
- **不动 `ontology_schema.yaml`**（守冻结；新枚举先只落 pydantic + advisory，据摩擦稳定后再议迁 schema）。

## 验证
`python -m ithuriel.derive_session results/experiments.csv results/d8_bare_vs_defended.json` → 5 runs：groq[3 子因]/gpt-4o-mini[assertable −0.30]/mistral-stock[underpowered]/2501[not_applicable]/no_names[per_trial −1.0]；2 横向观察（攻击变体 Δ=0.975、混合保真度 4/5）。`pytest src/tests/` = 23/23（11 旧 + 12 新）。
