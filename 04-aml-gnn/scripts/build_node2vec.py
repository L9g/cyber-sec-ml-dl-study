"""预计算 node2vec 交易图嵌入并缓存（重计算，~5-6min，别放 notebook 冒烟里）。

产物：data/node2vec_tx.parquet（txId + emb_0..emb_{dim-1}），gitignore。
notebook 03 只加载它，不重算。

关键图事实：`txs_edgelist` 的两端交易全部落在同一 Time step，交易图按时间步断开。
因此这里的全图 node2vec 虽然是 transductive（会见到测试期节点的同期结构），但不会沿边
接触未来时间步；近随机结果是一个干净的证据：裸拓扑本身没有提供可用的跨期判别信号。

当前缓存是 undirected node2vec，对照的是「忽略资金流方向的裸拓扑」。若要检验方向信息，
应另存 directed 缓存，而不是覆盖本文件的语义。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import RAW_DIR, DATA_DIR, SEED  # noqa: E402

DIM = 64


def main() -> None:
    from pecanpy import pecanpy

    edges = pd.read_csv(RAW_DIR / "txs_edgelist.csv")
    edg_path = RAW_DIR / "_tx.edg"
    edges.to_csv(edg_path, sep="\t", header=False, index=False)

    try:
        g = pecanpy.SparseOTF(p=1, q=1, workers=4, verbose=False, random_state=SEED)
        g.read_edg(str(edg_path), weighted=False, directed=False)
        emb = g.embed(dim=DIM, num_walks=10, walk_length=30, window_size=5, epochs=1)

        node_ids = np.array(g.nodes).astype("int64")   # 行顺序对应的 txId
        out = pd.DataFrame(emb, columns=[f"emb_{i}" for i in range(DIM)])
        out.insert(0, "txId", node_ids)
        out_path = DATA_DIR / "node2vec_tx.parquet"
        out.to_parquet(out_path, index=False)
        print(f"saved {out.shape} -> {out_path}")
    finally:
        edg_path.unlink(missing_ok=True)   # 中途失败也清理临时 .edg


if __name__ == "__main__":
    main()
