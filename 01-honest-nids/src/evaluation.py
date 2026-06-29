"""诚实指标 + base-rate 误报量 + 实验落盘。

不看裸 accuracy（Arp P7）。用 macro-F1 / PR-AUC / per-class recall，
并在真实 base rate 下把 precision 重新解读为 SOC 误报洪流（Arp P8, `axelsson2000baserate`）。
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    recall_score,
)

EXPERIMENT_FIELDS = [
    "timestamp",
    "experiment",      # e.g. optimistic / honest_temporal / lodo_A_to_B
    "dataset",
    "split",           # random / temporal / lodo
    "model",
    "macro_f1",
    "pr_auc",
    "minority_recall",
    "note",
]

# 决定「同一实验」的身份列；timestamp 不进键（它让每行天生唯一，是旧版重复的根因）
LOGICAL_KEY = ["experiment", "dataset", "split", "model"]


def compute_metrics(y_true, y_pred, y_score=None) -> dict:
    """返回诚实指标字典。y_score 为正类概率/分数时计算 PR-AUC。"""
    out = {
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "minority_recall": float(
            recall_score(y_true, y_pred, pos_label=1, zero_division=0)
        ),
        "per_class_recall": recall_score(
            y_true, y_pred, average=None, zero_division=0
        ).tolist(),
    }
    if y_score is not None:
        out["pr_auc"] = float(average_precision_score(y_true, y_score))
    return out


def base_rate_alert_volume(
    recall: float,
    fpr: float,
    base_rates=(0.001, 0.01, 0.05),
    total_flows: int = 1_000_000,
):
    """每 total_flows 条流、在不同攻击占比下的误报量与分析师工作量。

    比单纯 PR-AUC 更贴近 SOC 现实（`axelsson2000baserate`）。
    返回每个 base rate 的 dict：真阳、假阳、precision、analyst_alerts。
    """
    rows = []
    for br in base_rates:
        positives = total_flows * br
        negatives = total_flows - positives
        tp = recall * positives
        fp = fpr * negatives
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rows.append(
            {
                "base_rate": br,
                "true_positives": round(tp),
                "false_positives": round(fp),
                "precision": round(precision, 4),
                "analyst_alerts": round(tp + fp),
            }
        )
    return rows


def log_experiment(row: dict, csv_path: str | Path) -> None:
    """Upsert 一条实验记录：同逻辑键（experiment/dataset/split/model）的旧行被替换。

    幂等——同实验重跑 N 次只保留最新一行。timestamp 是普通列，不参与身份判定。
    彻底解决了「跑前必须 rm experiments.csv」的 footgun，§5 drop_duplicates 也可撤。
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
