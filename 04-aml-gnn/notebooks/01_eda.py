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
    # 01 · Elliptic++ EDA —— 把「标签来源」摆到台面上

    > **项目四共四步 MVP**：01（本文）EDA → 02 temporal split → 03 表格 LightGBM baseline。
    > 卖点不是「又一个 Elliptic GNN」，而是 **selective labeling / label provenance 下的诚实 AML**。

    ## 这一步要回答的三个问题

    1. **规模与结构**：交易图多大？特征多少？图连通吗？
    2. **标签真相**：illicit/licit/unknown 各占多少？——重点是 **unknown ≠ 良性**，
       它是「未被调查过」而非「已确认合法」。这是 AML 标签比 NIDS 标签更脏的根因。
    3. **时间结构**：illicit 占比、标注覆盖**随时间是否漂移**？——决定了为什么必须
       temporal split（步骤 02），以及为什么不能拿整体分数当部署期望（步骤 07 标签审计）。

    > 评估铁律（继承项目一）：不平衡安全数据看 **PR-AUC**，随机基线 = **illicit 占比**（不是 0.5）。
    """)
    return


@app.cell
def _(mo):
    import sys
    sys.path.insert(0, str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    from config import seed_everything, LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN
    from src import data as d

    seed_everything()

    df = d.load_tx_graph()           # 一行一交易：txId + Time step + 182 特征 + class
    edges = d.load_tx_edges()        # txId1 -> txId2 有向边
    return LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN, df, edges, pd, plt


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. 规模与图结构
    """)
    return


@app.cell
def _(df, edges, mo, pd):
    n_nodes = df.shape[0]
    n_feats = df.shape[1] - 3        # 去 txId / Time step / class
    n_edges = len(edges)

    # 度分布（有向图：出度+入度）
    deg = pd.concat([edges["txId1"], edges["txId2"]]).value_counts()
    nodes_in_edges = deg.index.nunique()

    scale = pd.DataFrame(
        {
            "指标": ["交易节点数", "特征维度", "有向边数", "边覆盖节点数",
                    "平均度", "最大度", "孤立节点数"],
            "值": [
                n_nodes, n_feats, n_edges, nodes_in_edges,
                round(2 * n_edges / n_nodes, 2), int(deg.max()),
                n_nodes - nodes_in_edges,
            ],
        }
    )
    mo.md(f"""
    交易图是**稀疏有向图**：{n_nodes:,} 个节点、{n_edges:,} 条边、{n_feats} 维特征。
    平均度仅约 {round(2*n_edges/n_nodes,2)}——典型的金融交易链（长链 + 少量 fan-in/fan-out），
    正是表格模型看不见、图模型理应受益的结构（升档再验证「图是否真有用」）。

    {mo.ui.table(scale, selection=None)}
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. 标签真相：unknown 不是良性

    Elliptic 标签编码 **1=illicit / 2=licit / 3=unknown**。绝大多数节点是 unknown——
    它们是「**没被调查过**」，不是「确认合法」。把 unknown 当良性是 AML 评估最常见的乐观偏差。
    """)
    return


@app.cell
def _(LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN, df, mo, pd):
    vc = df["class"].value_counts()
    n_ill, n_lic, n_unk = vc[LABEL_ILLICIT], vc[LABEL_LICIT], vc[LABEL_UNKNOWN]
    n_lab = n_ill + n_lic
    illicit_share = n_ill / n_lab

    label_tbl = pd.DataFrame(
        {
            "类别": ["illicit (1)", "licit (2)", "unknown (3)"],
            "数量": [n_ill, n_lic, n_unk],
            "占全体": [f"{n_ill/len(df):.1%}", f"{n_lic/len(df):.1%}", f"{n_unk/len(df):.1%}"],
        }
    )
    mo.md(f"""
    {mo.ui.table(label_tbl, selection=None)}

    - **{n_unk/len(df):.0%} 的交易是 unknown**——监督学习只能用 {n_lab:,} 个已标注样本，
      丢掉 {n_unk:,} 个（步骤 06 半监督 / 步骤 07 标签审计的用武之地）。
    - **PR-AUC 随机基线 = illicit 占已标注比 = {illicit_share:.3f}**（≈{illicit_share:.1%}）。
      任何模型的 PR-AUC 必须**显著高于 {illicit_share:.3f}** 才算学到东西——baseline 报告里必带这条。
    """)
    return (illicit_share,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. 时间结构：两条「随时间漂移」的信号

    这是项目四相对项目一的方法学增量来源。两条信号都**实测可验证**——
    我们只报测到的漂移，不替它编因果故事（如「暗市关停」需独立核实，不在此断言）。
    """)
    return


@app.cell
def _(df, mo):
    g = df.groupby("Time step")["class"].agg(
        n="size",
        illicit=lambda s: (s == 1).sum(),
        licit=lambda s: (s == 2).sum(),
        unknown=lambda s: (s == 3).sum(),
    )
    g["illicit_share_labeled"] = g["illicit"] / (g["illicit"] + g["licit"])
    g["unknown_frac"] = g["unknown"] / g["n"]

    # 前34训 / 后15测（步骤 02 将采用的切点）
    tr, te = g.loc[:34], g.loc[35:]
    tr_share = tr.illicit.sum() / (tr.illicit.sum() + tr.licit.sum())
    te_share = te.illicit.sum() / (te.illicit.sum() + te.licit.sum())
    tr_unk = tr.unknown.sum() / tr.n.sum()
    te_unk = te.unknown.sum() / te.n.sum()

    mo.md(f"""
    | 区间 | illicit 占已标注 | unknown 占比（标注覆盖） |
    |---|---|---|
    | 前 34 步（拟训练） | **{tr_share:.1%}** | {tr_unk:.1%} |
    | 后 15 步（拟测试） | **{te_share:.1%}** | {te_unk:.1%} |

    - **信号 A — 类别先验漂移**：illicit 占比从 {tr_share:.1%} 掉到 {te_share:.1%}。
      训练期的 base rate **不等于**部署期——这正是「整体分数会骗人、操作点指标会漂」的根因。
    - **信号 B — 标注覆盖漂移**：晚期 unknown 比例更高（{tr_unk:.1%} → {te_unk:.1%}），
      即**越晚的交易越少被调查/标注**（核实延迟 / selective labeling 的直接实证）。
    """)
    return g, te_share, tr_share


@app.cell
def _(g, plt):
    # 轴标签用英文：matplotlib 默认字体无中文字形（叙事文字在 mo.md 里保持中文）
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.6))
    ax1.bar(g.index, g["illicit_share_labeled"], color="#c0392b")
    ax1.axvline(34.5, ls="--", c="gray")
    ax1.set_title("Signal A: illicit share (of labeled) over time")
    ax1.set_xlabel("Time step"); ax1.set_ylabel("illicit share")
    ax2.plot(g.index, g["unknown_frac"], marker="o", ms=3, color="#2c3e50")
    ax2.axvline(34.5, ls="--", c="gray")
    ax2.set_title("Signal B: unknown fraction (labeling coverage) over time")
    ax2.set_xlabel("Time step"); ax2.set_ylabel("unknown frac")
    fig.tight_layout()
    fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 小结 → 下一步

    - 图稀疏、unknown 主导、类别先验与标注覆盖**都随时间漂移**。
    - 因此：**步骤 02 必须 temporal split**（不能随机切，否则跨期漂移被掩盖）；
      **步骤 03 baseline 必报 PR-AUC 对随机基线**；**步骤 07** 把「unknown≠良性 + 覆盖漂移」做成标签审计。
    """)
    return


@app.cell
def _(df):
    def test_49_time_steps():
        assert sorted(df["Time step"].unique()) == list(range(1, 50))

    def test_three_label_states_present():
        assert set(df["class"].unique()) == {1, 2, 3}

    def test_unknown_dominates():
        # selective labeling：未标注应是多数（远超 1/3）
        assert (df["class"] == 3).mean() > 0.5

    return


@app.cell
def _(illicit_share):
    def test_illicit_is_minority_baseline():
        # PR-AUC 随机基线应是小数（不平衡），明显 < 良性、明显 > 0
        assert 0.0 < illicit_share < 0.25

    return


@app.cell
def _(te_share, tr_share):
    def test_class_prior_drifts_down():
        # 信号 A：训练期 illicit 先验显著高于测试期（带 margin，避免锁死具体值）
        assert tr_share - te_share > 0.02

    return


if __name__ == "__main__":
    app.run()
