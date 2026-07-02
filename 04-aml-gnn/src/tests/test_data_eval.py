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


def _toy_wallets():
    # 地址 a：ts 30,35（跨界，min=30≤34）；b：ts 32（only train）；
    # c：ts 40（only test，min>34）；d：ts 36,38（only test）；e：ts 33（unknown 标签）
    return pd.DataFrame(
        {
            "address": ["a", "a", "b", "c", "d", "d", "e"],
            "Time step": [30, 35, 32, 40, 36, 38, 33],
            "first_block_appeared_in": [1, 1, 2, 9, 5, 5, 3],  # 绝对 block=泄漏列
            "g1": [0.1, 0.9, 0.2, 0.3, 0.4, 0.8, 0.5],
        }
    )


def _toy_wallet_classes():
    return pd.DataFrame({"address": ["a", "b", "c", "d", "e"], "class": [1, 2, 1, 2, 3]})


def test_wallet_feature_columns_drops_absolute_block_and_ids():
    cols = d.wallet_feature_columns(_toy_wallets())
    assert cols == ["g1"]                                  # 只剩真特征
    assert "first_block_appeared_in" not in cols           # 绝对 block 泄漏列被剔
    assert "Time step" not in cols and "address" not in cols


def test_native_actor_split_no_leakage_and_last_snapshot():
    wf, wc = _toy_wallets(), _toy_wallet_classes()
    tr, te = d.native_actor_temporal_split(wf, wc, train_max_step=34)
    # train 地址（首现≤34）：a,b（e 是 unknown 被丢）；a 取 ≤34 的最后快照 = ts30 行(g1=0.1)
    assert sorted(tr["address"]) == ["a", "b"]
    assert float(tr.loc[tr["address"] == "a", "g1"].iloc[0]) == 0.1   # 不是 ts35 的 0.9
    # test 地址（首现>34，纯 inductive）：c,d；d 取最后快照 ts38(g1=0.8)
    assert sorted(te["address"]) == ["c", "d"]
    assert float(te.loc[te["address"] == "d", "g1"].iloc[0]) == 0.8
    # 无泄漏：train/test 地址集合不相交
    assert set(tr["address"]).isdisjoint(set(te["address"]))
    # 每地址唯一一行
    assert tr["address"].is_unique and te["address"].is_unique


def test_address_first_step_is_min_timestep():
    fs = d.address_first_step(_toy_wallets())
    # a 跨 30/35 → 首现 30；d 跨 36/38 → 36；单步地址取自身
    assert fs["a"] == 30 and fs["b"] == 32 and fs["c"] == 40 and fs["d"] == 36 and fs["e"] == 33
    # 与 native_actor_temporal_split 同口径：首现 ≤34 → train 侧（a,b,e），>34 → test 侧（c,d）
    assert (fs <= 34).sum() == 3 and (fs > 34).sum() == 2


def test_all_address_snapshots_covers_unknown_and_matches_native_split():
    wf, wc = _toy_wallets(), _toy_wallet_classes()
    snap = d.all_address_snapshots(wf, wc, train_max_step=34)
    g = snap.set_index("address")
    # 覆盖全部 5 地址（含 unknown e，native split 会丢掉它）
    assert sorted(snap["address"]) == ["a", "b", "c", "d", "e"]
    # 快照选取：a 首现≤34 取 ≤34 最后(ts30,g1=0.1)；d 首现>34 取全局最后(ts38,0.8)；e unknown 取 ts33(0.5)
    assert g.loc["a", "g1"] == 0.1 and g.loc["d", "g1"] == 0.8 and g.loc["e", "g1"] == 0.5
    assert g.loc["a", "first_step"] == 30 and g.loc["d", "first_step"] == 36
    # labeled 子集与 native_actor_temporal_split 的快照**一致**（同口径、无分叉）
    tr, te = d.native_actor_temporal_split(wf, wc, 34)
    assert g.loc["a", "g1"] == float(tr.loc[tr.address == "a", "g1"].iloc[0])
    assert g.loc["d", "g1"] == float(te.loc[te.address == "d", "g1"].iloc[0])


def test_log_experiment_upsert_idempotent(tmp_path):
    csv = tmp_path / "exp.csv"
    base = {"experiment": "tx_baseline", "task": "transaction", "split": "temporal",
            "model": "LightGBM"}
    ev.log_experiment({**base, "pr_auc": 0.80}, csv)
    ev.log_experiment({**base, "pr_auc": 0.81}, csv)   # 同逻辑键 → 覆盖
    rows = pd.read_csv(csv)
    assert len(rows) == 1 and float(rows.iloc[0]["pr_auc"]) == 0.81
