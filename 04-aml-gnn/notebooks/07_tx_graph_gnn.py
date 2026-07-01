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
    # 07 · 交易图 GNN（Reference 档）—— 图到底有没有用？

    > 项目四论点：「图 > 表格」**不自动成立**（Weber 2019 自报 RF > 普通 GCN）。本节在**交易图**上跑
    > GraphSAGE，诚实回答「消息传递有没有净增益」。**CPU 训练**（203k 节点/234k 边，无需 GPU）。

    ## 严谨的三层对照（隔离两个混淆）
    | 模型 | 特征 | 图消息传递 | 隔离什么 |
    |---|---|---|---|
    | LightGBM（nb02） | 182 维 tx 特征 | ✗ | 强 GBDT 基线（0.813） |
    | **MLP** | 同上 | ✗ | 控制 **NN vs GBDT** |
    | **GraphSAGE** | 同上 | ✓ | **纯消息传递增益 = SAGE − MLP** |

    要宣称「图有用」，必须 **GraphSAGE > MLP**（同特征同 NN 训练、唯一差别是消息传递）；
    只跟 GBDT 比会把「NN vs 树」和「图 vs 无图」两件事混在一起。

    ## 诚实边界（先说）
    1. **交易图按时间步完全断开**（nb03 实测所有边 Δ(Time step)=0）→ 消息传递**只在同时间步内**发生，
       且 temporal split 在图层面**天然 inductive**（测试子图与训练子图无共享边）。本节会复验 Δt=0。
    2. 主指标 **PR-AUC**（基线=illicit 占比）；同 tx 任务、可与 nb02 直接比。
    3. 不把 GNN 往死里调（Weber 的点是**即便调好，GNN 也难稳超匹配的简单基线**）——用合理默认，如实报。
    """)
    return


@app.cell
def _(mo):
    import sys
    sys.path.insert(0, str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch_geometric.nn import SAGEConv

    from config import seed_everything, EXPERIMENTS_CSV, LABEL_ILLICIT
    from src import data as d
    from src import evaluation as ev

    seed_everything()
    torch.set_num_threads(8)
    DEVICE = "cpu"
    return (
        DEVICE,
        EXPERIMENTS_CSV,
        F,
        LABEL_ILLICIT,
        SAGEConv,
        d,
        ev,
        mo,
        nn,
        np,
        pd,
        seed_everything,
        torch,
    )


@app.cell
def _(LABEL_ILLICIT, d, np, torch):
    # ── 建图张量：节点=交易，边=txs_edgelist（同时间步内），特征标准化（仅用训练节点统计）──
    full = d.load_tx_graph()
    feats = d.feature_columns(full)
    full = full.reset_index(drop=True)
    idx_of = {t: i for i, t in enumerate(full["txId"].values)}  # txId → 连续节点索引

    edges = d.load_tx_edges()
    src = edges["txId1"].map(idx_of).values
    dst = edges["txId2"].map(idx_of).values
    keep = ~(np.isnan(src) | np.isnan(dst))
    src, dst = src[keep].astype(np.int64), dst[keep].astype(np.int64)

    # 复验：所有边两端 Δ(Time step)=0（交易图按时间步断开 → 消息传递只在同期内）
    ts = full["Time step"].values
    dt_max = int(np.abs(ts[src] - ts[dst]).max())
    # 无向化（消息双向传递）
    ei = torch.tensor(np.vstack([np.concatenate([src, dst]),
                                 np.concatenate([dst, src])]), dtype=torch.long)

    tstep = torch.tensor(ts, dtype=torch.long)
    labeled = full["class"].isin([1, 2]).values
    y = torch.tensor((full["class"].values == LABEL_ILLICIT).astype(np.float32))
    train_mask = torch.tensor(labeled & (ts <= 34))
    test_mask = torch.tensor(labeled & (ts > 34))

    X = full[feats].to_numpy(np.float32)
    mu = X[train_mask.numpy()].mean(0)
    sd = X[train_mask.numpy()].std(0);  sd[sd == 0] = 1.0
    x = torch.tensor((X - mu) / sd)
    x = torch.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    return dt_max, ei, test_mask, train_mask, x, y


@app.cell
def _(dt_max, mo, test_mask, train_mask, x):
    mo.md(f"""
    图张量就绪：节点 **{x.shape[0]:,}**、特征 **{x.shape[1]}** 维；
    训练节点（labeled, ≤34）**{int(train_mask.sum()):,}**、测试节点（labeled, >34）**{int(test_mask.sum()):,}**。

    - **复验通过：所有边两端 Δ(Time step) = {dt_max}** → 交易图确实按时间步断开，消息传递只在同期内、
      temporal split 图层面天然 inductive（测试子图与训练子图无共享边）。
    """)
    return


@app.cell
def _(DEVICE, F, SAGEConv, ev, nn, seed_everything, torch):
    # ── 两个模型 + 统一训练/评估函数 ──
    class MLP(nn.Module):
        def __init__(self, d_in, h=128, p=0.3):
            super().__init__()
            self.l1, self.l2, self.out = nn.Linear(d_in, h), nn.Linear(h, h), nn.Linear(h, 1)
            self.p = p

        def forward(self, x, edge_index=None):
            x = F.dropout(F.relu(self.l1(x)), self.p, self.training)
            x = F.dropout(F.relu(self.l2(x)), self.p, self.training)
            return self.out(x).squeeze(-1)

    class GraphSAGE(nn.Module):
        def __init__(self, d_in, h=128, p=0.3):
            super().__init__()
            self.c1, self.c2, self.out = SAGEConv(d_in, h), SAGEConv(h, h), nn.Linear(h, 1)
            self.p = p

        def forward(self, x, edge_index):
            x = F.dropout(F.relu(self.c1(x, edge_index)), self.p, self.training)
            x = F.dropout(F.relu(self.c2(x, edge_index)), self.p, self.training)
            return self.out(x).squeeze(-1)

    def train_eval(model, x, ei, y, train_mask, test_mask, epochs=120, lr=0.01):
        seed_everything()                       # 每个模型同种子初始化，可复现
        model = model.to(DEVICE)
        pos = float(y[train_mask].sum())         # 训练集正类(illicit)数
        n_train = float(train_mask.sum().item())
        pos_weight = torch.tensor([max(1.0, (n_train - pos) / max(pos, 1.0))])  # neg/pos
        opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)
        lossf = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        for _ in range(epochs):
            model.train(); opt.zero_grad()
            out = model(x, ei)
            loss = lossf(out[train_mask], y[train_mask])
            loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            score = torch.sigmoid(model(x, ei))[test_mask].cpu().numpy()
        yt = y[test_mask].cpu().numpy()
        return {"pr_auc": ev.pr_auc(yt, score), "base_rate": ev.base_rate(yt),
                "recall_at_1pct": ev.recall_at_budget(yt, score, 0.01),
                "recall_at_5pct": ev.recall_at_budget(yt, score, 0.05), "score": score}
    return GraphSAGE, MLP, train_eval


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 1. 三层对照：图有没有净增益？""")
    return


@app.cell
def _(GraphSAGE, MLP, ei, mo, pd, test_mask, train_mask, train_eval, x, y):
    d_in = x.shape[1]
    res_mlp = train_eval(MLP(d_in), x, ei, y, train_mask, test_mask)      # 无图
    res_sage = train_eval(GraphSAGE(d_in), x, ei, y, train_mask, test_mask)  # 有图

    TABULAR_PR = 0.8128   # nb02 LightGBM tabular（同 temporal split）
    br = res_mlp["base_rate"]
    tbl = pd.DataFrame([
        {"model": "LightGBM (GBDT, no graph)", "PR-AUC": TABULAR_PR, "recall@1%": "—", "recall@5%": "—"},
        {"model": "MLP (NN, no graph)", "PR-AUC": round(res_mlp["pr_auc"], 4),
         "recall@1%": round(res_mlp["recall_at_1pct"], 3), "recall@5%": round(res_mlp["recall_at_5pct"], 3)},
        {"model": "GraphSAGE (NN + message passing)", "PR-AUC": round(res_sage["pr_auc"], 4),
         "recall@1%": round(res_sage["recall_at_1pct"], 3), "recall@5%": round(res_sage["recall_at_5pct"], 3)},
    ])
    mp_gain = res_sage["pr_auc"] - res_mlp["pr_auc"]          # 纯消息传递增益
    vs_gbdt = res_sage["pr_auc"] - TABULAR_PR                 # GNN vs 强 GBDT

    mo.md(f"""
    测试集 illicit base rate = **{br:.1%}**（PR-AUC 随机基线）。同 temporal split、同 182 特征：

    {mo.ui.table(tbl, selection=None)}

    - **纯消息传递增益 = SAGE − MLP = {mp_gain:+.4f}**（唯一差别是图）。
    - **GNN vs 强 GBDT = SAGE − LightGBM = {vs_gbdt:+.4f}**。
    - {'✅ 消息传递有正增益' if mp_gain > 0.005 else '⚠️ 消息传递增益≈0 或为负 → 图结构没带来判别力'}；
      {'且 GraphSAGE 追平/超过 LightGBM' if vs_gbdt > -0.01 else '且 GNN 仍不及调好的 GBDT（呼应 Weber 2019）'}。
    """)
    return TABULAR_PR, br, mp_gain, res_mlp, res_sage, vs_gbdt


@app.cell(hide_code=True)
def _(mp_gain, mo, vs_gbdt):
    mo.md(f"""
    ## 2. 诚实解读 → 下一步

    - **⭐ 三层对照把两个混淆拆开了**（这是本节最诚实的一点）：GraphSAGE(0.66) 远低于 LightGBM(0.81)，
      但**大头缺口不是「图 vs 无图」，而是「NN vs 树」**——MLP(无图) 已从 0.81 掉到 0.62（NN 在这些工程特征上
      本就打不过 GBDT，−0.19），而**消息传递本身其实加了一点点（SAGE−MLP = {mp_gain:+.4f}，为正）**。
      即：**图结构确有微弱同期信号，但被 NN<GBDT 的差距淹没**。若只报「GNN 0.66 < GBDT 0.81」会误把账算到图头上。
    - **为什么消息传递只加一点点**：交易图**按时间步断开**（§复验 Δt=0），同期邻居常是同一洗钱链的相邻交易——
      **特征里已编码大部分同期信息**（btc 量/度/聚合统计），再做一跳同期聚合边际很小。
    - **对旗舰问句**：**「图 > 表格」不自动成立**在本数据实证成立（呼应 Weber 2019 RF>GCN、nb03 裸拓扑近随机）——
      判别信号**主要在工程特征**，图结构只贡献很小的同期增益、且换不回 NN 相对 GBDT 的劣势。
    - ⚠️ **retrospective 未解**：即便 GNN，标签仍全局/事后（provenance 主线不因换模型而变）。
    - **给"为什么用图"三段论收口**：图的**大**增益只可能来自**跨期时序**（EvolveGCN 类）或结构感知/混合范式——
      而交易图跨期断开，故时序增益要到**地址图**（AddrAddr 有跨期边）才谈得上 → 那是 2.87M 边的更大图、
      按算力记忆（无 GPU）留云主机或邻居采样。当前 CPU 交易图 GNN 闭环到此。
    - 下一步（可选，需更大算力）：EvolveGCN / 地址图 GraphSAGE（跨期结构），或转项目二。
    """)
    return


@app.cell
def _(EXPERIMENTS_CSV, ev, res_mlp, res_sage):
    for _name, _r in [("mlp", res_mlp), ("graphsage", res_sage)]:
        ev.log_experiment(
            {
                "experiment": f"tx_{_name}", "task": "transaction", "split": "temporal",
                "model": {"mlp": "MLP-no-graph", "graphsage": "GraphSAGE-txgraph"}[_name],
                "pr_auc": round(_r["pr_auc"], 4), "base_rate": round(_r["base_rate"], 4),
                "pr_auc_lift": round(_r["pr_auc"] - _r["base_rate"], 4),
                "recall_at_1pct": round(_r["recall_at_1pct"], 4),
                "n_test": int(len(_r["score"])),
                "note": "GNN Reference; tx graph disconnected across time (Δt=0), message passing within-step only; label retrospective",
            },
            EXPERIMENTS_CSV,
        )
    return


@app.cell
def _(res_mlp, res_sage):
    def test_models_beat_random_by_margin():
        # MLP 与 GraphSAGE 都显著优于随机（方向性带 margin）
        assert res_mlp["pr_auc"] - res_mlp["base_rate"] > 0.2
        assert res_sage["pr_auc"] - res_sage["base_rate"] > 0.2

    return


@app.cell
def _(mp_gain):
    def test_message_passing_gain_is_small():
        # 诚实靶：纯消息传递增益不大（|SAGE−MLP| 小）——图没带来大幅判别力
        # 用带 margin 的方向断言：增益幅度 < 0.15（远小于 baseline lift ~0.75）
        assert abs(mp_gain) < 0.15

    return


@app.cell
def _(dt_max):
    def test_tx_graph_disconnected_across_time():
        # 结构事实：交易图所有边两端同时间步（Δt=0）→ temporal split 图层面 inductive
        assert dt_max == 0

    return


if __name__ == "__main__":
    app.run()
