# Fixture — D8 session 2026-07-11（5 跑，混合保真度）

反推「差异化层 session 层」字段的真实数据集（ADR-0005）。**溯源诚实声明**：

- `experiments.csv` — 本会话 5 跑的汇总（治理落法，逻辑键 upsert）。
- `d8_run_full_no_names.json` — **唯一**存活的全证据 run（mistral-small-3.2 + `important_instructions_no_names`，
  bare ASR=1.0→defended 0.0，delta −1.0 可断言）。含 per-trial trials。

**runs 1–4 的 raw 已被单文件覆盖式冲掉**（`results/d8_bare_vs_defended.json` 每跑覆盖），
只余 csv 汇总 → 它们只能派生**汇总级 Finding**（`evidence_completeness=summary_only`、
`evidence_refs` 空、manifest 空）。这不是 fixture 缺陷，是被 session 层如实表示的真实摩擦。

5 跑覆盖的裁定分支：assertable(gpt-4o-mini −0.30 / no_names −1.0)、underpowered(mistral stock)、
no_positive_control+quota_truncated(groq)、tooling_unsupported→not_applicable(2501 全 404)。
