"""代码契约单测（确定性、与模型无关）——贴死精确值/边界。

叙事/分数相关的断言不在这里，在 notebook 内嵌 test_（方向性）。
"""
import numpy as np
import pandas as pd

from src import data as d
from src import evaluation as ev


def _toy():
    # 6 笔交易，time step 33..36，标签含 unknown(3)
    return pd.DataFrame(
        {
            "txId": [1, 2, 3, 4, 5, 6],
            "Time step": [33, 34, 34, 35, 36, 35],
            "f1": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "class": [1, 2, 3, 1, 2, 3],
        }
    )


def test_temporal_split_boundary_inclusive():
    tr, te = d.temporal_split(_toy(), train_max_step=34)
    # unknown(3) 应被 labeled_only 丢掉：train 剩 txId 1,2；test 剩 txId 4,5（6 是 unknown）
    assert sorted(tr["txId"]) == [1, 2]
    assert sorted(te["txId"]) == [4, 5]
    # 边界：step==34 进 train，step==35 进 test
    assert tr["Time step"].max() == 34
    assert te["Time step"].min() == 35


def test_feature_columns_excludes_id_time_class():
    cols = d.feature_columns(_toy())
    assert cols == ["f1"]
    assert "Time step" not in cols and "txId" not in cols and "class" not in cols


def test_base_rate_is_positive_share():
    assert ev.base_rate([1, 1, 2, 2, 2, 2]) == 2 / 6


def test_yield_at_budget_monotone_and_exact():
    # 分数与标签完全对齐（前两名是 illicit）
    y = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]     # 2 个正类 / 10
    s = [0.9, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    rows = ev.yield_at_budget(y, s, budgets=(0.1, 0.2))
    # budget 10% -> k=1，命中 1 个 illicit：recall=1/2，precision=1/1
    assert rows[0]["k"] == 1 and rows[0]["recall"] == 0.5 and rows[0]["precision"] == 1.0
    # budget 20% -> k=2，命中 2 个：recall=1.0，precision=1.0
    assert rows[1]["k"] == 2 and rows[1]["recall"] == 1.0 and rows[1]["precision"] == 1.0


def test_log_experiment_upsert_idempotent(tmp_path):
    csv = tmp_path / "exp.csv"
    base = {"experiment": "tx_baseline", "task": "transaction", "split": "temporal",
            "model": "LightGBM"}
    ev.log_experiment({**base, "pr_auc": 0.80}, csv)
    ev.log_experiment({**base, "pr_auc": 0.81}, csv)   # 同逻辑键 → 覆盖
    rows = pd.read_csv(csv)
    assert len(rows) == 1 and float(rows.iloc[0]["pr_auc"]) == 0.81
