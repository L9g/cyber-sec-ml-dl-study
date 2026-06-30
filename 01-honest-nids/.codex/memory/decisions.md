# Decisions

Last updated: 2026-06-30

## 2026-06-29 — Model Selection

Decision: use **LightGBM** as the main model.

Reasoning:

- The project needs a strong, fast tabular baseline for large NetFlow data.
- The author's familiarity with LightGBM and XGBoost is a valid engineering
  factor and should be stated honestly.
- The project does not claim LightGBM is theoretically superior to XGBoost or
  CatBoost.
- XGBoost is the natural same-family validation model for future work.
- CatBoost is not a mainline choice because the important categorical identity
  features, such as IP and port, are treated as leakage/environment features and
  should not be optimised as deployable predictors.

Canonical report: `reports/model-selection-decision.md`.

## 2026-06-29 — IP LODO Interpretation

Decision: keep independent factorization in the IP ablation only if the text is
explicit about what it means.

Interpretation:

- Independent factorization models the fact that IP identity namespaces do not
  share semantics across different networks or labs.
- The resulting LODO numbers, such as 0.493 / 0.221, are not evidence of true
  IP-only cross-domain detection ability.
- They should be explained as measurement under semantically broken local
  identity codes, close to target random baselines.
- One-hot with `handle_unknown="ignore"` would be a valid production-style
  transform, but it is not required for this mechanism demo.

Preferred wording:

> LODO 下 IP-only 使用 train/test 各自独立的局部 IP 编码，故测试集 IP 码与训练集 IP 码没有共享语义；
> 这里的数字不代表 IP-only 模型具备跨域检测能力，而是“环境 ID 离开原网络后退化为无意义编号”时的测量结果。

## 2026-06-29 — Metric Headline

Decision: use PR-AUC magnitude relative to the target attack base rate as the
main LODO headline.

Reasoning:

- Recall@0.5 is useful as an operating-point observation but is sensitive to
  sampling, calibration, and threshold placement.
- "N out of 6 below random" is also too brittle when values are close to the
  base-rate line.
- More stable story: in-distribution PR-AUC is near 1.0, while cross-dataset
  PR-AUC moves toward the target dataset's random baseline.

## 2026-06-29 — Absolute Timestamp Policy

Decision: absolute timestamps are not inference-safe features.

Reasoning:

- `FLOW_START_MILLISECONDS` and `FLOW_END_MILLISECONDS` encode collection
  period/environment.
- They are valid for temporal splitting and drift/time audit.
- They should be dropped from honest and LODO feature matrices unless the
  experiment is explicitly labelled as a timestamp-included sensitivity audit.

## 2026-06-30 — Post-Review Wording Boundaries

Decision: keep the main story, but tighten several claims before treating the
project as final deliverable material.

Boundaries:

- LODO failure should not be described as purely low-FPR漏检. Current FPR values
  include roughly `0.064-0.105` in some directions, so the correct framing is
  direction-dependent: some failures are mostly missed attacks, others also
  create meaningful false positives.
- Do not claim threshold tuning "cannot help" unless backed by recall-at-fixed
  FPR, precision-at-alert-budget, or PR-curve operating-point analysis.
  Evidence that positives are not in `[0.4, 0.5)` only rules out a cheap
  `0.5 -> 0.4` threshold tweak.
- "All model families collapse" means no tested model family restores
  in-distribution-like PR-AUC under LODO. It does not mean the model rows are
  numerically clustered; PR-AUC still varies materially by model, cap, and
  train/test direction.
- Tracked marimo session JSON files are risky if stale. They currently contain
  old v2 text and should be ignored, deleted from version control, or regenerated
  before any release commit.

## 2026-06-30 — Drop "portfolio" Vocabulary Workspace-Wide

Decision: remove all "portfolio" / "作品集" vocabulary across the workspace and
read every deliverable as a genuine technical project, not a job-hunt artifact.

- Delivery tier renamed: **MVP → Reference-grade → Research-grade** (the old
  middle tier "Portfolio-ready" is retired). Use `Reference-grade` in all docs,
  READMEs, reports, and reading lists going forward.
- File `docs/portfolio-project-plan-draft.md` was renamed to
  `docs/network-detection-candidates-draft.md`.
- README and project-facing prose must not reference portfolio / 求职 / 面试 /
  hiring framing. (This pass removed only the portfolio vocabulary; other
  job-hunt words in the planning docs were left untouched unless asked.)
- One identifier kept on purpose: the auto-memory slug
  `project-cyber-ml-portfolio` (a pointer, not prose).
