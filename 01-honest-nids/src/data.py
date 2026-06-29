"""数据加载与切分策略——乐观（随机）vs 诚实（时间）。

切分策略本身就是项目一的卖点：随机切分会让同一攻击会话同时进训练和测试
（temporal snooping，Arp P3），产生虚高分数；temporal split 杜绝它。
方法论出处见 `pendlebury2019tesseract`（注意原域是 malware，借思想非数据）。
"""
from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split

from config import SEED


def load_netflow(path: str) -> pd.DataFrame:
    """读 NetFlow 文件（csv 或 parquet）。原始数据不入库，路径来自 data/。"""
    if str(path).endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def load_netflow_sampled(
    path: str,
    max_rows: int | None = None,
    label_col: str = "Label",
    seed: int = SEED,
) -> pd.DataFrame:
    """内存安全的分层采样加载（v3 的 ToN-IoT 27.5M / CSE-CIC 20M 行直接 pandas 读会 OOM）。

    用 duckdb 在 parquet 层做**按 label 分层**的可复现 reservoir 采样，只把采样后的
    ~max_rows 行物化进 pandas。max_rows=None 或文件本就更小 → 全量读取。
    """
    import duckdb

    p = str(path)
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    n = con.execute(f"SELECT count(*) FROM '{p}'").fetchone()[0]
    if max_rows is None or n <= max_rows:
        return con.execute(f"SELECT * FROM '{p}'").df()

    frac = max_rows / n
    counts = con.execute(
        f'SELECT "{label_col}", count(*) FROM \'{p}\' GROUP BY "{label_col}"'
    ).fetchall()
    parts = []
    for lab, c in counts:
        k = max(1, round(c * frac))  # 各类按原比例分配，保持分层
        lab_sql = lab if not isinstance(lab, str) else f"'{lab}'"
        # ⚠️ duckdb 的 USING SAMPLE 在 WHERE 之前作用于扫描——必须先在子查询里
        # 过滤出该类、再对子查询采样，否则会"先全表抽 k、再过滤"导致少数类被严重稀释。
        parts.append(
            f'(SELECT * FROM (SELECT * FROM \'{p}\' WHERE "{label_col}"={lab_sql}) '
            f"USING SAMPLE reservoir({k} ROWS) REPEATABLE({seed}))"
        )
    return con.execute(" UNION ALL ".join(parts)).df()


def optimistic_split(
    df: pd.DataFrame, label_col: str = "Label", test_size: float = 0.2
):
    """Step 1 乐观切分：随机分层切分——故意制造虚高 baseline。"""
    return train_test_split(
        df.drop(columns=[label_col]),
        df[label_col],
        test_size=test_size,
        stratify=df[label_col],
        random_state=SEED,
    )


def temporal_split(
    df: pd.DataFrame,
    time_col: str,
    label_col: str = "Label",
    train_frac: float = 0.8,
    extra_drop: list[str] | None = None,
):
    """Step 2 诚实切分：按时间排序后前 train_frac 训练、其余测试。

    保证「未来」不泄漏进训练。NF-v3 有真时间戳 `FLOW_START_MILLISECONDS`，故这是
    **真 temporal split**（不再是 v2 镜像的行序代理）。

    `time_col` 用于排序后会**从特征中移除**——绝对时间戳本身做特征是另一种泄漏
    （模型可学「时间 > T = 测试分布」）。`extra_drop` 用来一并剔除如
    `FLOW_END_MILLISECONDS` 这类同源绝对时间列（保留 FLOW_DURATION 等相对量）。
    """
    if time_col not in df.columns:
        raise KeyError(
            f"{time_col!r} 不在列里；若该发行版无 per-flow 时间戳，"
            "需改用 activity-based split，详见 reports/findings.md。"
        )
    ordered = df.sort_values(time_col, kind="stable").reset_index(drop=True)
    cut = int(len(ordered) * train_frac)
    train, test = ordered.iloc[:cut], ordered.iloc[cut:]
    drop = [label_col, time_col] + [
        c for c in (extra_drop or []) if c in ordered.columns
    ]
    return (
        train.drop(columns=drop),
        test.drop(columns=drop),
        train[label_col],
        test[label_col],
    )
