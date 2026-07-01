"""AML 诚实指标 + 实验落盘（upsert）。

评估口径（本项目锁定，见 CLAUDE.md）：
- 主 **PR-AUC**，随机基线 = illicit 占比（**不是 0.5**）。`pr_auc - base_rate` 只是
  「比随机好多少」的**任务内 sanity check**，**不能跨不同 prevalence 的任务比强弱**
  （tx base rate ~9.8% vs actor ~5.4%，PR-AUC 对 prevalence 非线性）。
- 跨任务只比 **operational curves**：yield@budget、recall@budget、queue overlap。
- 不看裸 accuracy（不平衡下全猜良性也高分）。
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score

EXPERIMENT_FIELDS = [
    "timestamp",
    "experiment",      # e.g. tx_baseline / actor_projection_max
    "task",            # transaction / actor
    "split",           # temporal（MVP 唯一口径）/ static（仅对照）
    "model",
    "pr_auc",
    "base_rate",       # 正类(illicit)占比 = PR-AUC 随机基线
    "pr_auc_lift",     # pr_auc - base_rate（任务内 sanity，勿跨任务比）
    "recall_at_1pct",  # yield@1% budget 的一个代表点（曲线才是主证据）
    "n_test",
    "note",
]

# 「同一实验」的身份列；timestamp 不进键（避免旧版靠 timestamp 天然唯一造成重复）
LOGICAL_KEY = ["experiment", "task", "split", "model"]


def base_rate(y_true) -> float:
    """正类(illicit=1)占比 = PR-AUC 的随机基线。"""
    y = np.asarray(y_true)
    return float((y == 1).mean())


def pr_auc(y_true, y_score) -> float:
    return float(average_precision_score(y_true, y_score))


def yield_at_budget(y_true, y_score, budgets=(0.001, 0.005, 0.01, 0.02, 0.05)) -> list[dict]:
    """yield@budget 曲线：只调查分数最高的前 budget 比例，命中多少 illicit。

    这是贴合 AML 调查产能的 operational 指标，也是跨任务/跨聚合策略的**唯一**可比口径。
    返回每个 budget 的 dict：k、recall（占全部 illicit）、precision（队列内命中率）。
    """
    y = np.asarray(y_true)
    s = np.asarray(y_score)
    order = np.argsort(-s)             # 分数降序
    y_sorted = y[order]
    total_pos = int((y == 1).sum())
    n = len(y)
    rows = []
    for b in budgets:
        k = max(1, int(round(b * n)))
        top = y_sorted[:k]
        hits = int((top == 1).sum())
        rows.append(
            {
                "budget": b,
                "k": k,
                "recall": hits / total_pos if total_pos else 0.0,  # yield（占全部 illicit）
                "precision": hits / k,                              # 队列内命中率
            }
        )
    return rows


def recall_at_budget(y_true, y_score, budget: float = 0.01) -> float:
    """单点 recall@budget（默认 1%）——曲线里的一个代表点，写落盘用；主证据看曲线。"""
    for r in yield_at_budget(y_true, y_score, budgets=(budget,)):
        return float(r["recall"])
    return 0.0


def log_experiment(row: dict, csv_path: str | Path) -> None:
    """Upsert 一条实验记录：同逻辑键（experiment/task/split/model）旧行被替换。

    幂等——同实验重跑只保留最新一行；timestamp 是普通列不参与身份判定
    （同项目一，避免「跑前必须 rm csv」的 footgun）。
    """
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": datetime.now(timezone.utc).isoformat(), **row}

    if csv_path.exists() and csv_path.stat().st_size > 0:
        with csv_path.open("r", newline="") as f:
            existing = list(csv.DictReader(f))
        key_vals = {k: str(row.get(k, "")) for k in LOGICAL_KEY}
        existing = [
            r for r in existing
            if not all(r.get(k, "") == key_vals[k] for k in LOGICAL_KEY)
        ]
        existing.append(row)
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=EXPERIMENT_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(existing)
    else:
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=EXPERIMENT_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerow(row)
