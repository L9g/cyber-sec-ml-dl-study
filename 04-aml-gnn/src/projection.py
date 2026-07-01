"""交易分数 → actor(地址) 队列投影 —— scoring granularity 轴的核心。

交易级分数聚合到地址级会**丢信息**，不同聚合策略（max / mean / sum / top-k / ...）
就是不同的风控决策。MVP 薄切片只做 **max**，其余聚合在升档时扇出。

⚠️ 两条诚实边界（写进 notebook 叙事）：
- **max 下 transaction-first 与 actor-first 队列等价**：按 tx 分数降序走，每个 actor
  首次出现即其 max 分，故「取 top-k 交易再抬到地址」= 「按 actor max 分取 top-k 地址」。
  队列不一致的看点因此**不在 which-actor**，而在 multiplicity（一个地址占多笔顶端交易）
  与**标签口径错配**（tx 标签体系 ≠ wallet 标签体系）。mean/sum 才会真分叉。
- actor 标签来自 `wallets_classes`，**全局/事后**（一址一枚、无 per-time-step 标签）→
  actor 队列 temporal 结果是 retrospective，不与 tx temporal 直接同类比。
"""
from __future__ import annotations

import pandas as pd

ADDR_COL = "address"
SCORE_COL = "actor_score"


def make_topk_mean(k: int):
    """返回「取每地址分数最高 k 笔的均值」聚合子（喂 project_scores_to_actors 的 agg）。

    介于 max(k=1) 与 mean(k=∞) 之间：不像 max 被单笔高分主导、也不像 mean 被大量低分
    交易稀释。地址交易数 < k 时取全部（nlargest 自动截断）。
    风控语义 = 「要看到 k 笔可疑才升级」。确定性、与模型无关 → src/tests 贴死。
    """
    if k < 1:
        raise ValueError("k must be >= 1")

    def _topk_mean(s):
        return s.nlargest(k).mean()

    _topk_mean.__name__ = f"top{k}_mean"
    return _topk_mean


def project_scores_to_actors(
    edges: pd.DataFrame,
    scores,
    agg="max",
    addr_col: str = "input_address",
    tx_col: str = "txId",
) -> pd.DataFrame:
    """把交易分数按地址聚合成 actor 分数。

    edges: DataFrame[addr_col, tx_col]（如 AddrTx：input_address → txId）。
    scores: dict / Series，txId -> score。**未打分的 txId 边被丢弃**（只投影已打分交易）。
    agg: pandas 聚合名（"max"/"mean"/"sum"）或可调用（如 make_topk_mean(3)）——聚合策略即风控决策。
    返回 DataFrame[address, actor_score]，一行一地址，按 actor_score 降序（队列顺序）。

    聚合是确定性的、与模型无关（模型分数在上游算好传入），故可在 src/tests 贴死精确值。
    """
    s = pd.Series(scores, dtype="float64")
    e = edges[[addr_col, tx_col]].copy()
    e[SCORE_COL] = e[tx_col].map(s)
    e = e.dropna(subset=[SCORE_COL])
    out = (
        e.groupby(addr_col)[SCORE_COL]
        .agg(agg)
        .reset_index()
        .rename(columns={addr_col: ADDR_COL})
        .sort_values(SCORE_COL, ascending=False, kind="mergesort")  # 稳定排序=可复现队列
        .reset_index(drop=True)
    )
    return out
