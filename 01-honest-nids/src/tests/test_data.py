"""data.py 的确定性单元测试——temporal split 契约 + 采样器分层（含 bug 回归测试）。"""
import numpy as np
import pandas as pd
import pytest

from src import data as d


def test_temporal_split_orders_by_time_and_drops_time_label():
    """按 FLOW_START 排序，前 train_frac 训练；时间戳列 + Label 从特征中剔除；无未来泄漏。"""
    df = pd.DataFrame(
        {
            "FLOW_START_MILLISECONDS": [5, 1, 3, 2, 4],
            "FLOW_END_MILLISECONDS": [6, 2, 4, 3, 5],
            "feat": [50, 10, 30, 20, 40],  # = start*10，便于核对顺序
            "Label": [1, 0, 1, 0, 1],
        }
    )
    X_tr, X_te, y_tr, y_te = d.temporal_split(
        df,
        time_col="FLOW_START_MILLISECONDS",
        label_col="Label",
        train_frac=0.6,
        extra_drop=["FLOW_END_MILLISECONDS"],
    )
    # 绝对时间戳列 + Label 不进特征（否则是另一种泄漏）
    assert list(X_tr.columns) == ["feat"]
    # 按时间排序：train = 最早 60%（start 1,2,3 → feat 10,20,30）
    assert list(X_tr["feat"]) == [10, 20, 30]
    assert list(X_te["feat"]) == [40, 50]
    assert y_tr.tolist() == [0, 0, 1]
    assert y_te.tolist() == [1, 1]


def test_temporal_split_missing_time_col_raises():
    df = pd.DataFrame({"feat": [1, 2], "Label": [0, 1]})
    with pytest.raises(KeyError):
        d.temporal_split(df, time_col="FLOW_START_MILLISECONDS")


def test_load_netflow_sampled_preserves_stratification(tmp_path):
    """回归测试：duckdb 的 USING SAMPLE 在 WHERE 之前作用于扫描，旧实现「先抽样后过滤」
    会把少数类严重稀释（曾把 CSE-CIC 攻击率 12.9%→2.2%）。此测试锁定分层占比被保留。"""
    n = 100_000
    df = pd.DataFrame(
        {
            "Label": [1] * 10_000 + [0] * 90_000,  # 10% 攻击
            "x": np.random.default_rng(0).random(n),
        }
    )
    p = tmp_path / "d.parquet"
    df.to_parquet(p)

    out = d.load_netflow_sampled(str(p), max_rows=10_000)
    assert 9_000 <= len(out) <= 11_000  # ≈ max_rows
    # 关键：攻击占比仍 ≈10%，没有被稀释（旧 bug 会掉到 ~1%）
    assert abs(out["Label"].mean() - 0.10) < 0.02


def test_load_netflow_sampled_repeatable(tmp_path):
    """REPEATABLE(seed) → 同参数两次采样结果一致（可复现）。"""
    df = pd.DataFrame(
        {"Label": [1] * 5_000 + [0] * 45_000, "x": range(50_000)}
    )
    p = tmp_path / "d.parquet"
    df.to_parquet(p)
    a = d.load_netflow_sampled(str(p), max_rows=5_000)
    b = d.load_netflow_sampled(str(p), max_rows=5_000)
    assert len(a) == len(b)
    assert a["Label"].mean() == b["Label"].mean()


def test_load_netflow_sampled_no_cap_returns_all(tmp_path):
    """文件本就小于 max_rows（或 None）→ 全量返回，不采样。"""
    df = pd.DataFrame({"Label": [0, 1, 0, 1], "x": [1, 2, 3, 4]})
    p = tmp_path / "d.parquet"
    df.to_parquet(p)
    assert len(d.load_netflow_sampled(str(p), max_rows=None)) == 4
    assert len(d.load_netflow_sampled(str(p), max_rows=1_000)) == 4
