import marimo

__generated_with = "0.23.11"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 08 · 地址图结构 EDA —— 跨期图信号到底在不在？

    > nb07 交易图 GNN 的诚实收口是：交易图**按时间步完全断开**（所有边 Δt=0），故消息传递只在同期内、
    > 图的**大**增益（若有）只可能来自**跨期时序结构**——而那只有到**地址图**才谈得上。
    > 但 nb07 结尾那句「AddrAddr 有跨期边」当时是**未验证的前提**。本节先把它证实/证伪，
    > 并把地址图的结构事实与「给地址赋时间」的口径钉死，为下一步静态 GraphSAGE 立好靶和**诚实边界**。

    ## 为什么地址图与交易图是两种东西
    - 交易图：节点=交易，每笔交易恰有一个 `Time step` → 边的 Δt 良定义、实测**恒为 0**（同期断开）。
    - 地址图（`AddrAddr_edgelist`）：**静态坍缩图，边不带时间**。地址可跨多个时间步（实测多数单步），
      要度量「边是否跨期」必须先给每个地址一个时间坐标——本节用**首现步**（`min(Time step)`，
      与 `native_actor_temporal_split` 同口径）。

    ## 本节要回答（纯事实、不建模、不预答旗舰问句）
    1. 图有多大、清洗后多少边、是不是一整块（**连通性决定消息传递能否全局传播**）。
    2. 标签覆盖：多少节点 illicit/licit/**unknown**（selective labeling 的规模）。
    3. **关键**：多少边跨时间步（Δfirst_step>0）？多少边跨 ≤34/>34 的 split 边界？
       —— 前者证成「地址图有跨期结构」，后者**限定** inductive 评估下 train→test 能传多少信息。
    """)
    return


@app.cell
def _(mo):
    import sys

    sys.path.insert(0, str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    from config import seed_everything, LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN
    from src import data as d

    seed_everything()
    return (
        LABEL_ILLICIT,
        LABEL_LICIT,
        LABEL_UNKNOWN,
        coo_matrix,
        connected_components,
        d,
        mo,
        np,
        pd,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 1. 图规模与清洗（自环 / 重复边）""")
    return


@app.cell
def _(d, mo, pd):
    E_raw = d.load_addr_addr()  # 原始，保留自环与重复边以如实报计数
    n_edges_raw = len(E_raw)
    n_self = int((E_raw.input_address == E_raw.output_address).sum())
    n_dup = int(E_raw.duplicated(["input_address", "output_address"]).sum())

    E = d.load_addr_addr(drop_self_loops=True, dedup=True)  # 建图用：去自环 + 去重复有向边
    n_edges = len(E)

    nodes = pd.unique(pd.concat([E_raw.input_address, E_raw.output_address], ignore_index=True))
    n_nodes = len(nodes)

    mo.md(f"""
    | 量 | 值 |
    |---|---|
    | 唯一地址（节点） | **{n_nodes:,}** |
    | 原始边 | {n_edges_raw:,} |
    | · 自环（input==output） | {n_self:,}（{n_self / n_edges_raw:.1%}） |
    | · 完全重复有向边 | {n_dup:,}（{n_dup / n_edges_raw:.1%}） |
    | **清洗后边（去自环+去重）** | **{n_edges:,}** |

    对比交易图（nb07）：节点 203,769 / 边 234,355。地址图**大一个量级**（节点 ×4、边 ×12），
    是 CPU 上算力压力最大的一步——但仍在本机 32G 内存可载入范围（稀疏图 + 特征张量 ~百 MB 级）。
    """)
    return E, n_edges, n_nodes, nodes


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 2. 连通性 —— 消息传递能全局传播吗？""")
    return


@app.cell
def _(E, connected_components, coo_matrix, mo, n_nodes, nodes, np):
    idx = {a: i for i, a in enumerate(nodes)}
    si = E.input_address.map(idx).to_numpy()
    di = E.output_address.map(idx).to_numpy()
    A = coo_matrix((np.ones(len(si)), (si, di)), shape=(n_nodes, n_nodes))
    n_comp, comp = connected_components(A, directed=False)
    sizes = np.bincount(comp)
    largest_frac = sizes.max() / n_nodes

    mo.md(f"""
    - 连通分量数（无向）：**{n_comp}**；最大分量 **{sizes.max():,}** 节点 = 全图 **{largest_frac:.4%}**。
    - **⭐ 地址图是一整块**（几乎单一巨型连通分量）——与交易图**按时间步碎成 49 个不连通子图**形成鲜明对比。
      → 在地址图上，消息传递**能跨节点全局传播**（结构上具备「跨期信号可传导」的前提，交易图没有）。
    """)
    return largest_frac, n_comp


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 3. 标签覆盖 —— selective labeling 的规模""")
    return


@app.cell
def _(LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN, d, mo, n_nodes, nodes, pd):
    wc = d.load_wallet_classes()
    node_lab = pd.DataFrame({"address": nodes}).merge(wc, on="address", how="left")
    vc = node_lab["class"].value_counts(dropna=False)
    n_illicit = int(vc.get(LABEL_ILLICIT, 0))
    n_licit = int(vc.get(LABEL_LICIT, 0))
    n_unknown = int(vc.get(LABEL_UNKNOWN, 0))

    mo.md(f"""
    图节点标签分布（100% 节点都有一条 wallets_classes 记录）：

    | 类 | 数量 | 占全图 |
    |---|---|---|
    | illicit (1) | **{n_illicit:,}** | {n_illicit / n_nodes:.2%} |
    | licit (2) | {n_licit:,} | {n_licit / n_nodes:.2%} |
    | **unknown (3)** | **{n_unknown:,}** | **{n_unknown / n_nodes:.1%}** |

    - **unknown 占 ~68%** —— 与投影 actor 队列的覆盖缺口一致（nb04 §5）。
      unknown≠benign（nb04 Setting C 已证误当 benign 会砸评估）→ 地址图 GNN 的监督只能在
      labeled（illicit+licit）节点上算 loss，unknown 节点仍**进图传消息**（半监督利用结构）但不进 loss。
    - illicit 仅 1.73%（**PR-AUC 随机基线**按评估口径另算：labeled-only 内 illicit/(illicit+licit) ≈ 5.4%）。
    """)
    return n_illicit, n_licit, n_unknown


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 4. ⭐ 边跨时间了吗？—— 地址图相对交易图的**质变**""")
    return


@app.cell
def _(E, d, mo, np):
    wf = d.load_wallet_features()
    first_step = d.address_first_step(wf)  # address → 首现步

    si_ft = E.input_address.map(first_step).to_numpy()
    di_ft = E.output_address.map(first_step).to_numpy()
    both = ~(np.isnan(si_ft) | np.isnan(di_ft))
    dft = np.abs(si_ft[both] - di_ft[both])

    frac_within = float((dft == 0).mean())          # 同一首现步
    frac_cross_time = float((dft > 0).mean())        # 跨时间步（地址图独有）
    frac_cross_split = float(
        ((si_ft[both] <= 34) != (di_ft[both] <= 34)).mean()
    )                                                # 跨 ≤34/>34 split 边界
    pct = np.percentile(dft, [50, 90, 95, 99, 100]).astype(int)

    mo.md(f"""
    每条边两端地址按**首现步**比较（{int(both.sum()):,} / {len(E):,} 条边两端都有时间）：

    | 度量 | 地址图 | 交易图(nb07) |
    |---|---|---|
    | Δfirst_step == 0（同期） | {frac_within:.1%} | 100% |
    | **Δfirst_step > 0（跨时间步）** | **{frac_cross_time:.1%}** | **0%** |
    | 跨 ≤34/>34 split 边界 | {frac_cross_split:.2%} | 0% |

    Δfirst_step 分位（50/90/95/99/max）：**{list(pct)}**。

    - **⭐ 前提证实**：地址图**确有跨期边**——约 **{frac_cross_time:.0%}** 的边连接首现于不同时间步的地址，
      尾部可跨到 max={pct[-1]} 步。这正是交易图（Δt≡0）给不出、而地址图**独有**的跨期结构信号，
      证成「到地址图才谈得上时序图增益」这句 nb07 的收口。
    - **⚠️ 诚实边界（必须先说）**：但只有 **{frac_cross_split:.2%}** 的边跨越 ≤34/>34 的 temporal split 边界。
      做 **inductive** group temporal split（首现 ≤34 训 / >34 测）时，train↔test 之间的消息传递通道很**窄**——
      非零（交易图是零），但稀。→ 这**从结构上限定**了「图能带来多少 train→test 增量」的上限，
      不能等 GraphSAGE 跑完再补这条边界。跨期信号更多在**训练期内部**（same-side 跨步边）传导。
    """)
    return first_step, frac_cross_split, frac_cross_time, frac_within


@app.cell(hide_code=True)
def _(frac_cross_split, frac_cross_time, largest_frac, mo, n_unknown, n_nodes):
    mo.md(f"""
    ## 5. 收口 → 下一步（静态地址图 GraphSAGE）

    地址图结构事实已钉死，三条决定下一步怎么搭：

    1. **一整块连通图**（最大分量 {largest_frac:.2%}）→ 消息传递可全局传播（交易图碎成 49 块做不到）。
    2. **{frac_cross_time:.0%} 的边跨时间步** → 地址图**确有**跨期结构信号（交易图 0%）；这是「为什么用图」
       三段论里「图的大增益只可能来自跨期时序」的落点。
    3. **仅 {frac_cross_split:.2%} 边跨 split 边界** → inductive 评估下 train→test 传导窄，**预期图增量有限**；
       诚实靶：GraphSAGE 须同打过原生 actor(0.30) 与 tx 投影(0.74)，且证明增量来自结构/时序，
       很可能实证「再复杂也修不了标签口径」（呼应 Weber 2019 + nb06 guilt-by-association 循环）。

    **下一步 nb09 = 静态地址图 GraphSAGE**，沿用 nb07 的**三层对照**隔离混淆：
    LightGBM(GBDT 无图) / MLP(NN 无图) / GraphSAGE(NN+消息传递)，用 51 维地址特征
    （`wallet_feature_columns`，绝对 block 列已剔）、group-aware inductive temporal split
    （`native_actor_temporal_split` 口径，无实体泄漏）、labeled 节点算 loss、unknown 进图不进 loss。
    EvolveGCN（49 快照时序版）仍留云主机（无 GPU，见算力记忆）。
    """)
    return


@app.cell
def _(largest_frac):
    def test_address_graph_is_one_giant_component():
        # 结构事实：地址图几乎是单一巨型连通分量（与交易图碎成 49 块相反）
        assert largest_frac > 0.99

    return


@app.cell
def _(frac_cross_time):
    def test_address_graph_has_cross_time_edges():
        # ⭐ 前提证实：地址图确有可观的跨时间步边（交易图为 0）——方向性带 margin
        assert frac_cross_time > 0.10

    return


@app.cell
def _(frac_cross_split):
    def test_split_boundary_crossing_is_sparse():
        # 诚实边界：跨 ≤34/>34 split 边界的边很稀（限定 inductive 下图的 train→test 增量）
        assert frac_cross_split < 0.10

    return


@app.cell
def _(n_illicit, n_licit, n_unknown, n_nodes):
    def test_label_coverage_sums_and_unknown_dominates():
        # 覆盖事实：三态相加=全节点；unknown 占多数（selective labeling 规模）
        assert n_illicit + n_licit + n_unknown == n_nodes
        assert n_unknown / n_nodes > 0.5

    return


if __name__ == "__main__":
    app.run()
