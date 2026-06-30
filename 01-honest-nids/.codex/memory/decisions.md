# Decisions

Last updated: 2026-06-29

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
