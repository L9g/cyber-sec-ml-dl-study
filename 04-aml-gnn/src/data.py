"""Elliptic++ 数据加载——交易图为 MVP 主战场，地址图留升档。

设计要点（与项目四签名一致）：
- 标签 1=illicit / 2=licit / 3=unknown；**unknown ≠ licit**（selective labeling），
  故加载时把三态保留，由下游显式决定「丢 unknown 做监督」还是「半监督利用」。
- 时间步是 1..49 的整数，既是 temporal split 的依据，也**不进特征**（仅排序/分组用）。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import RAW_DIR, LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN

TIME_COL = "Time step"
ID_COL = "txId"
CLASS_COL = "class"


def _p(name: str, raw_dir: Path | None = None) -> Path:
    return (raw_dir or RAW_DIR) / name


def load_tx_features(raw_dir: Path | None = None) -> pd.DataFrame:
    """交易特征：txId + Time step + 局部/聚合特征。一行一笔交易。"""
    return pd.read_csv(_p("txs_features.csv", raw_dir))


def load_tx_classes(raw_dir: Path | None = None) -> pd.DataFrame:
    """交易标签：txId + class（1/2/3）。"""
    df = pd.read_csv(_p("txs_classes.csv", raw_dir))
    # 源文件偶有把 'unknown' 写成字符串的变体——统一成整数编码。
    df[CLASS_COL] = (
        df[CLASS_COL]
        .replace({"unknown": LABEL_UNKNOWN, "1": LABEL_ILLICIT, "2": LABEL_LICIT})
        .astype(int)
    )
    return df


def load_tx_edges(raw_dir: Path | None = None) -> pd.DataFrame:
    """交易→交易有向边（txId1 → txId2）。"""
    return pd.read_csv(_p("txs_edgelist.csv", raw_dir))


def load_addr_tx(raw_dir: Path | None = None) -> pd.DataFrame:
    """地址→交易边（input_address → txId）。用于把交易分数投影到 actor 队列。"""
    return pd.read_csv(_p("AddrTx_edgelist.csv", raw_dir))


def load_tx_addr(raw_dir: Path | None = None) -> pd.DataFrame:
    """交易→输出地址边（txId → output_address）。actor 参与的 output 侧。"""
    return pd.read_csv(_p("TxAddr_edgelist.csv", raw_dir))


def actor_participation(include_outputs: bool = True, raw_dir: Path | None = None) -> pd.DataFrame:
    """地址在交易里的**参与**边表 [address, txId]，一行一(地址,交易)参与。

    include_outputs=True（默认）= input(AddrTx) ∪ output(TxAddr)——**与 wallet illicit 标签同 universe**
    （标签定义为「参与过 illicit 交易 as input 或 output」，双条件 100% 仅在 input+output 成立）。
    include_outputs=False 仅 input（花费方），双条件退化到 ~93.5%、且队列与标签 universe 不一致。
    主结果用默认（all participating actor queue）。
    """
    inp = load_addr_tx(raw_dir).rename(columns={"input_address": "address"})[["address", ID_COL]]
    if not include_outputs:
        return inp.reset_index(drop=True)
    out = load_tx_addr(raw_dir).rename(columns={"output_address": "address"})[["address", ID_COL]]
    return pd.concat([inp, out], ignore_index=True)


def load_wallet_classes(raw_dir: Path | None = None) -> pd.DataFrame:
    """地址标签（address, class）。

    ⚠️ **全局/事后**：一址一枚不可变标签、**无 per-time-step 地址标签**（标签本身没有
    活动时间语义）。故 actor 队列的 temporal 结果是 retrospective，不与 tx temporal 直接同类比。
    """
    df = pd.read_csv(_p("wallets_classes.csv", raw_dir))
    df[CLASS_COL] = (
        df[CLASS_COL]
        .replace({"unknown": LABEL_UNKNOWN, "1": LABEL_ILLICIT, "2": LABEL_LICIT})
        .astype(int)
    )
    return df


def load_tx_graph(raw_dir: Path | None = None) -> pd.DataFrame:
    """合并特征+标签，返回一行一交易的宽表（含 class、Time step）。

    不在此处丢 unknown——保留三态，丢弃与否是建模决策，留给调用方显式做。
    """
    feat = load_tx_features(raw_dir)
    cls = load_tx_classes(raw_dir)
    df = feat.merge(cls, on=ID_COL, how="left", validate="one_to_one")
    return df


FEATURE_EXCLUDE = [ID_COL, TIME_COL, CLASS_COL]


def feature_columns(df: pd.DataFrame) -> list[str]:
    """特征列 = 全列去 txId / Time step / class。

    ⚠️ Time step **不进特征**（只用于排序/切分）——否则模型会学到「晚期步 illicit 更少」
    这个 base-rate 漂移，属于不可迁移的捷径（同项目一「绝对时间戳只排序不建模」）。
    """
    return [c for c in df.columns if c not in FEATURE_EXCLUDE]


def temporal_split(df: pd.DataFrame, train_max_step: int = 34):
    """按时间步做 temporal split（前 train_max_step 步训练，其余测试）。

    绝不随机切：随机切会让同期交易泄漏、并掩盖跨期 base-rate 漂移（EDA 信号 A）。
    返回 (train_df, test_df)，均已过 labeled_only（只留 illicit/licit）。
    MVP 只做这一种口径（temporal）；static/random 仅在解释 actor retrospective label 时作对照。
    """
    lab = labeled_only(df)
    train = lab[lab[TIME_COL] <= train_max_step].copy()
    test = lab[lab[TIME_COL] > train_max_step].copy()
    return train, test


def labeled_only(df: pd.DataFrame) -> pd.DataFrame:
    """只保留已标注（illicit/licit）交易，丢 unknown——监督学习用。

    ⚠️ 这一步本身就是 label-provenance 风险点：unknown≠良性，丢弃会让评估
    乐观（漏掉「未被调查过的洗钱」）。在 notebook 里要显式标注此假设。
    """
    return df[df[CLASS_COL].isin([LABEL_ILLICIT, LABEL_LICIT])].copy()
