"""代码契约单测：actor 投影（确定性、与模型无关）——贴死精确值/边界。"""
import pandas as pd

from src import projection as proj


def _toy_edges():
    # 地址 a 触两笔(1,2)、b 触一笔(3)、c 触一笔(4，未打分应被丢)
    return pd.DataFrame(
        {"input_address": ["a", "a", "b", "c"], "txId": [1, 2, 3, 4]}
    )


def test_project_max_drops_unscored_and_takes_max():
    scores = {1: 0.1, 2: 0.9, 3: 0.5}  # tx4 无分
    out = proj.project_scores_to_actors(_toy_edges(), scores, agg="max")
    m = dict(zip(out["address"], out["actor_score"]))
    assert m == {"a": 0.9, "b": 0.5}          # c 被丢（tx4 未打分）
    # 队列按分数降序：a(0.9) 在 b(0.5) 前
    assert list(out["address"]) == ["a", "b"]


def test_project_mean_differs_from_max():
    # mean 聚合下 a=(0.1+0.9)/2=0.5，与 max(0.9) 不同——证明聚合策略非退化
    scores = {1: 0.1, 2: 0.9, 3: 0.5}
    out = proj.project_scores_to_actors(_toy_edges(), scores, agg="mean")
    m = dict(zip(out["address"], out["actor_score"]))
    assert m["a"] == 0.5 and m["b"] == 0.5


def test_project_empty_when_no_scores_match():
    out = proj.project_scores_to_actors(_toy_edges(), {999: 0.5}, agg="max")
    assert len(out) == 0
    assert list(out.columns) == ["address", "actor_score"]
