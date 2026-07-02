---
name: same-pipeline-for-model-deltas
description: >
  Use when computing or reporting ANY delta between two models — a
  "reversal", gain, lift, ablation margin, or gap (e.g. "NN beats tree by
  +X", "message-passing adds +Y", "GNN < GBDT by Z"). Especially when one
  of the two numbers is pulled from another notebook, an earlier run, or a
  shared results/experiments.csv row instead of being recomputed alongside
  the other. Ensures the numerator and denominator of any model-vs-model
  difference come from ONE evaluation pipeline (same split, same feature
  extraction, same test population, same hyperparameter convention, same
  metric fn), so the delta reflects the model change and not a pipeline
  change. Also covers the legit exception: borrowing a cross-pipeline number
  as a magnitude reference (ceiling/floor) but never as a subtraction operand.
---

# 模型间差值必须来自同一评估管线（别拿两个现成数相减）

## 症状（怎么认出来）
- 报告里出现「模型 A 比 B 高 X」「图增益 +Y」「反转 +Z」这类**差值**。
- 其中**一个数是从别处借的**：另一个 notebook、上一次运行、`results/experiments.csv` 里某一行——
  而不是和另一个数**在同一段代码里一起现算**。
- 典型话术：「MLP 0.346 − nb06 的 GBDT 0.297 = +0.049」。

## 根因（一句话）
两个数若来自**不同管线**，它们的差里就**混进了管线差异**（不同 split／特征提取／测试集／超参），
被冒充成「模型差异」。差值的物理意义被污染。

## 规则
**任何模型间差值，分子和分母必须在同一评估管线内现算。** 换句话说：要比 A 和 B，
就在**同一个 notebook、同一 split、同一测试集**上把 A 和 B 都跑一遍再相减——
**绝不**从两个来源各拿一个现成数做减法。

## 「同一管线」= 这五项都相同
| 维度 | 不同会怎样 |
|---|---|
| **split** | train/test 边界、inductive/transductive 口径不同 → 测试难度不同 |
| **特征提取** | 快照选取、NaN 处理、标准化、列集合不同 → 喂给模型的 X 不同 |
| **测试集群体** | 评估的样本集合不同 → base rate / 难样本占比不同 |
| **超参约定** | `num_leaves 63 vs 64`、轮数、种子不同 → 模型容量/解不同 |
| **度量函数** | PR-AUC vs ROC-AUC、budget 定义不同 → 数不可比 |

**注意**：即便 `n_test` 和 `base_rate` **看起来相同**，也不代表管线相同——特征提取和超参仍可能不同。
同规模 ≠ 同管线。

## ✅ 合法的例外：跨管线数只能当「量级参照」，不能当「减法操作数」
借一个别处的数来**标刻度**（天花板/地板/量级锚点）是可以的，只要它**不进任何差值的分子或分母**：
- ✅ 「SAGE 0.361 仍**远低于** tx 投影参照 ~0.74」——0.74 是跨 notebook 的**参照线**，只说「够不着」，不做减法。
- ✅ 「本节未加权 GBDT 0.315，与 nb06 的 0.297 **接近**（交叉核对）」——并列对照，不相减当结论。
- ❌ 「反转 = 本节 MLP 0.346 − nb06 GBDT 0.297」——0.297 成了减法操作数 → 违规。

一句话：**跨管线的数可以放在同一句里当背景，不能放在同一个减号两端当结论。**

## 真实案例（本项目 · nb09 地址图 GNN）
- 记忆里一度写「真实 NN vs 树反转 = **+0.049**」= nb09 的 MLP `0.346` − **nb06** 的未加权 GBDT `0.297`。
- 两行 `n_test` 都是 `92451`、`base_rate` 都是 `0.0529`（看着像同一批），**但管线不同**：
  nb06 走 `native_actor_temporal_split`、`num_leaves=64`；nb09 走 `all_address_snapshots`+reindex 到图节点、`num_leaves=63`。
- 在 **nb09 本节同管线**现算未加权 GBDT = `0.315`，同管线反转只 **+0.031**。
- 那 `0.049 − 0.031 = 0.018` 的差，**全是 nb06↔nb09 的管线差**，被误当成模型差。
- 修法：nb09 里**本节现算**未加权 GBDT（不借 0.297），`NATIVE_GBDT_REF=0.297` 降级为**交叉核对参照**、不入减法。

## 自检清单
- [ ] 我这个差值的两个数，是在**同一段代码/同一 notebook**里一起算出来的吗？
- [ ] 它们的 split、特征提取、测试集、超参约定、度量函数**逐项相同**吗？
- [ ] 有没有一个数是从 `experiments.csv` 或别的 notebook **借来直接相减**的？（→ 改成本节现算）
- [ ] 借来的跨管线数，是只当**参照线/量级**，还是偷偷进了**减法两端**？（后者违规）
