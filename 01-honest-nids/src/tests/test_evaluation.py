"""evaluation.py 的确定性单元测试——与模型无关，测代码契约（[[feedback-test-assertions-directional]]）。

这些是「招聘者点开 tests/ 想看的工程素养」：upsert 幂等、base-rate 公式、指标计算。
"""
import csv

from src import evaluation as ev

BASE_ROW = {
    "experiment": "optimistic",
    "dataset": "NF-UNSW-NB15-v3",
    "split": "random",
    "model": "LightGBM",
    "macro_f1": 0.90,
    "pr_auc": 0.80,
    "minority_recall": 0.70,
    "note": "x",
}


def _read(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def test_log_experiment_upsert_is_idempotent(tmp_path):
    """同一逻辑键写两次 → 只剩一行，且保留最新值（timestamp 不进键）。"""
    p = tmp_path / "exp.csv"
    ev.log_experiment(BASE_ROW, p)
    ev.log_experiment({**BASE_ROW, "macro_f1": 0.95}, p)  # 同键，新值
    rows = _read(p)
    assert len(rows) == 1
    assert float(rows[0]["macro_f1"]) == 0.95  # 最新覆盖旧值


def test_log_experiment_distinct_keys_coexist(tmp_path):
    """逻辑键任一字段不同（这里 model）→ 是两条独立实验，应共存。"""
    p = tmp_path / "exp.csv"
    ev.log_experiment(BASE_ROW, p)
    ev.log_experiment({**BASE_ROW, "model": "LogReg"}, p)
    assert len(_read(p)) == 2


def test_log_experiment_timestamp_not_part_of_key(tmp_path):
    """即使两次写入 timestamp 不同，同逻辑键仍折叠为一行（timestamp 是普通列）。"""
    p = tmp_path / "exp.csv"
    ev.log_experiment(BASE_ROW, p)
    ev.log_experiment(BASE_ROW, p)  # 完全相同的键，但 timestamp 会不同
    rows = _read(p)
    assert len(rows) == 1
    assert rows[0]["timestamp"]  # timestamp 列存在且非空


def test_base_rate_perfect_detector_precision_one():
    """recall=1, fpr=0 → 零假阳、precision=1（确定性边界）。"""
    r = ev.base_rate_alert_volume(
        recall=1.0, fpr=0.0, base_rates=(0.01,), total_flows=1_000_000
    )[0]
    assert r["false_positives"] == 0
    assert r["precision"] == 1.0
    assert r["true_positives"] == 10_000


def test_base_rate_low_base_rate_drowns_precision():
    """recall=1, fpr=1% 在 0.1% 攻击占比下 precision≈0.091（base-rate 谬误的算术核心）。"""
    r = ev.base_rate_alert_volume(
        recall=1.0, fpr=0.01, base_rates=(0.001,), total_flows=1_000_000
    )[0]
    # tp=1000, fp=0.01*999000=9990 → precision=1000/10990≈0.091
    assert abs(r["precision"] - 0.091) < 0.005
    assert r["false_positives"] == 9_990


def test_compute_metrics_perfect_prediction():
    """完美预测 → macro_f1 / recall / PR-AUC 全 1.0（已知输入出已知值）。"""
    y_true = [0, 0, 1, 1]
    m = ev.compute_metrics(y_true, [0, 0, 1, 1], y_score=[0.1, 0.2, 0.9, 0.8])
    assert m["macro_f1"] == 1.0
    assert m["minority_recall"] == 1.0
    assert m["pr_auc"] == 1.0


def test_compute_metrics_all_benign_zero_recall():
    """全预测良性 → 攻击召回=0；PR-AUC 退化到攻击占比附近（随机基线）。"""
    y_true = [0, 0, 0, 1]
    m = ev.compute_metrics(y_true, [0, 0, 0, 0], y_score=[0.1, 0.1, 0.1, 0.1])
    assert m["minority_recall"] == 0.0
