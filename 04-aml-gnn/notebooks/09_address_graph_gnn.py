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
    # 09 · 静态地址图 GraphSAGE（Reference 档）—— 到了有跨期边的图，图就赢了吗？

    > nb07 在**交易图**上证「图 > 表格」不自动成立，但交易图**按时间步断开**（Δt≡0），故把「图的大增益只可能来自
    > 跨期时序」留给了**地址图**。nb08 已证实地址图**确有**跨期结构（~20% 边跨时间步、一整块连通）。
    > 本节在地址图上跑 GraphSAGE，诚实回答：**有了跨期边和全局连通，消息传递到底加不加分？能不能逼近 tx 投影 0.74？**

    ## 三层对照（同 nb07，隔离两个混淆）
    | 模型 | 特征 | 图消息传递 | 隔离什么 |
    |---|---|---|---|
    | LightGBM（= nb06 原生 actor） | 51 维地址特征 | ✗ | GBDT 上限（~0.30） |
    | **MLP** | 同上 | ✗ | 控制 **NN vs GBDT** |
    | **GraphSAGE** | 同上 | ✓ | **纯消息传递增益 = SAGE − MLP** |

    两条**外部参照线**（常数，来自前面 notebook，勿当本节训练结果）：
    **原生 actor GBDT ≈ 0.30**（nb06 地址特征诚实上限）／**tx 投影 ≈ 0.74**（nb04/06，被 guilt-by-association 循环抬高）。

    ## 诚实边界（先说，不预答）
    1. **严格 inductive**：地址图有 **2.88% 跨界边**（nb08），若 full-batch 直接训练，train 节点会经跨界边
       聚合到 test 节点特征 = transductive 泄漏。故**训练只用「两端首现≤34」的诱导子图**、推理才用全图——
       test 节点特征训练时完全不参与（对齐 nb06 无实体泄漏的 inductive 口径）。
    2. **unknown 进图不进 loss**：68% 节点是 unknown（nb08），它们参与消息传递（半监督利用结构）但不算 loss。
    3. **retrospective 不因换模型而变**：钱包标签仍是全局/事后裁定；图能改的是**特征侧**能挤出多少结构信号，
       改不了**标签口径**（provenance 主线）。若图增益来自 illicit 地址相互连接（同构），那本身也是
       guilt-by-association 的**结构版**、非独立新信号——本节会点出。
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
    import lightgbm as lgb

    from config import seed_everything, EXPERIMENTS_CSV, LABEL_ILLICIT
    from src import data as d
    from src import evaluation as ev

    seed_everything()
    torch.set_num_threads(8)
    DEVICE = "cpu"

    NATIVE_GBDT_REF = 0.297   # nb06 原生 actor GBDT（地址特征上限，外部参照）
    PROJECTION_REF = 0.741    # nb04/06 tx 投影到 actor（被标签循环抬高，外部参照）
    return (
        DEVICE, EXPERIMENTS_CSV, F, LABEL_ILLICIT, NATIVE_GBDT_REF, PROJECTION_REF,
        SAGEConv, d, ev, lgb, mo, nn, np, pd, seed_everything, torch,
    )


@app.cell
def _(LABEL_ILLICIT, d, np, pd, torch):
    # ── 建图：节点=地址，边=AddrAddr（清洗后），特征=全节点快照（含 unknown）──
    E = d.load_addr_addr(drop_self_loops=True, dedup=True)
    nodes = pd.unique(pd.concat([E.input_address, E.output_address], ignore_index=True))
    idx = {a: i for i, a in enumerate(nodes)}
    n_nodes = len(nodes)

    wf = d.load_wallet_features()
    wc = d.load_wallet_classes()
    snap = d.all_address_snapshots(wf, wc)                       # 全节点快照（无泄漏规则）
    snap = snap.set_index("address").reindex(nodes).reset_index().rename(columns={"index": "address"})
    feats = [c for c in d.wallet_feature_columns(snap) if c != "first_step"]  # first_step 是时间代理，剔

    first_step = snap["first_step"].to_numpy()
    cls = snap["class"].to_numpy()
    labeled = np.isin(cls, [1, 2])
    y = torch.tensor((cls == LABEL_ILLICIT).astype(np.float32))
    train_mask = torch.tensor(labeled & (first_step <= 34))
    test_mask = torch.tensor(labeled & (first_step > 34))

    # 有向边 → 节点索引
    src = E.input_address.map(idx).to_numpy()
    dst = E.output_address.map(idx).to_numpy()

    def undirected(s, t):
        return torch.tensor(np.vstack([np.concatenate([s, t]), np.concatenate([t, s])]), dtype=torch.long)

    ei_full = undirected(src, dst)                              # 推理：全图
    keep_tr = (first_step[src] <= 34) & (first_step[dst] <= 34)  # 训练：两端首现≤34 的诱导子图
    ei_train = undirected(src[keep_tr], dst[keep_tr])

    # 特征标准化（仅用训练节点统计，防泄漏）
    X = snap[feats].to_numpy(np.float32)
    mu = X[train_mask.numpy()].mean(0)
    sd = X[train_mask.numpy()].std(0); sd[sd == 0] = 1.0
    x = torch.nan_to_num(torch.tensor((X - mu) / sd), nan=0.0, posinf=0.0, neginf=0.0)
    frac_train_edges = float(keep_tr.mean())
    return (X, ei_full, ei_train, feats, frac_train_edges, n_nodes,
            snap, test_mask, train_mask, x, y)


@app.cell
def _(ei_full, ei_train, frac_train_edges, mo, n_nodes, test_mask, train_mask, x):
    mo.md(f"""
    图张量就绪：节点 **{n_nodes:,}**、特征 **{x.shape[1]}** 维；
    labeled 训练节点（首现≤34）**{int(train_mask.sum()):,}**、labeled 测试节点（首现>34，inductive）**{int(test_mask.sum()):,}**。

    - 推理全图边（无向）**{ei_full.shape[1]:,}**；训练诱导子图边（两端≤34）**{ei_train.shape[1]:,}**
      = 全图的 **{frac_train_edges:.1%}**。→ test 节点特征训练时完全不参与（严格 inductive）。
    """)
    return


@app.cell
def _(DEVICE, F, SAGEConv, ev, nn, seed_everything, torch):
    # ── 模型 + 统一训练/评估（训练用 ei_train、评估用 ei_eval，MLP 忽略图）──
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

    def train_eval(model, x, ei_train, ei_eval, y, train_mask, test_mask, epochs=120, lr=0.01):
        seed_everything()
        model = model.to(DEVICE)
        pos = float(y[train_mask].sum())
        n_tr = float(train_mask.sum().item())
        pos_weight = torch.tensor([max(1.0, (n_tr - pos) / max(pos, 1.0))])
        opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)
        lossf = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        for _ in range(epochs):
            model.train(); opt.zero_grad()
            loss = lossf(model(x, ei_train)[train_mask], y[train_mask])
            loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            score = torch.sigmoid(model(x, ei_eval))[test_mask].cpu().numpy()
        yt = y[test_mask].cpu().numpy()
        return {"pr_auc": ev.pr_auc(yt, score), "base_rate": ev.base_rate(yt),
                "recall_at_1pct": ev.recall_at_budget(yt, score, 0.01),
                "recall_at_5pct": ev.recall_at_budget(yt, score, 0.05), "score": score}
    return GraphSAGE, MLP, train_eval


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 1. 三层对照：到了跨期连通图，图有净增益吗？""")
    return


@app.cell
def _(GraphSAGE, MLP, X, ev, lgb, np, train_eval,
      ei_full, ei_train, test_mask, train_mask, x, y):
    # GBDT 层（无图，复现 nb06 原生 actor）——用原始特征，树对标准化不敏感
    ytr = y[train_mask].numpy(); yte = y[test_mask].numpy()
    spw = (len(ytr) - ytr.sum()) / max(ytr.sum(), 1.0)
    gbm = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=63,
                             scale_pos_weight=spw, random_state=42, n_jobs=8, verbose=-1)
    gbm.fit(X[train_mask.numpy()], ytr)
    s_gbdt = gbm.predict_proba(X[test_mask.numpy()])[:, 1]
    res_gbdt = {"pr_auc": ev.pr_auc(yte, s_gbdt), "base_rate": ev.base_rate(yte),
                "recall_at_1pct": ev.recall_at_budget(yte, s_gbdt, 0.01),
                "recall_at_5pct": ev.recall_at_budget(yte, s_gbdt, 0.05), "score": s_gbdt}

    d_in = x.shape[1]
    res_mlp = train_eval(MLP(d_in), x, ei_train, ei_full, y, train_mask, test_mask)   # 无图
    res_sage = train_eval(GraphSAGE(d_in), x, ei_train, ei_full, y, train_mask, test_mask)  # 有图
    return res_gbdt, res_mlp, res_sage


@app.cell
def _(NATIVE_GBDT_REF, PROJECTION_REF, mo, pd, res_gbdt, res_mlp, res_sage):
    br = res_gbdt["base_rate"]
    tbl = pd.DataFrame([
        {"model": "LightGBM (GBDT, no graph)", "PR-AUC": round(res_gbdt["pr_auc"], 4),
         "recall@1%": round(res_gbdt["recall_at_1pct"], 3), "recall@5%": round(res_gbdt["recall_at_5pct"], 3)},
        {"model": "MLP (NN, no graph)", "PR-AUC": round(res_mlp["pr_auc"], 4),
         "recall@1%": round(res_mlp["recall_at_1pct"], 3), "recall@5%": round(res_mlp["recall_at_5pct"], 3)},
        {"model": "GraphSAGE (NN + message passing)", "PR-AUC": round(res_sage["pr_auc"], 4),
         "recall@1%": round(res_sage["recall_at_1pct"], 3), "recall@5%": round(res_sage["recall_at_5pct"], 3)},
    ])
    mp_gain = res_sage["pr_auc"] - res_mlp["pr_auc"]      # 纯消息传递增益
    vs_gbdt = res_sage["pr_auc"] - res_gbdt["pr_auc"]     # 图 NN vs 强 GBDT
    gap_to_proj = PROJECTION_REF - res_sage["pr_auc"]     # 距 tx 投影天花板

    mo.md(f"""
    测试集 illicit base rate = **{br:.1%}**（PR-AUC 随机基线）。同 inductive split、同 51 特征：

    {mo.ui.table(tbl, selection=None)}

    外部参照：原生 actor GBDT ≈ **{NATIVE_GBDT_REF}**（nb06）／ tx 投影 ≈ **{PROJECTION_REF}**（nb04/06）。

    - **纯消息传递增益 = SAGE − MLP = {mp_gain:+.4f}**（唯一差别是图）。
    - **图 NN vs 本节 GBDT = SAGE − LightGBM = {vs_gbdt:+.4f}**。
    - **距 tx 投影天花板 = {gap_to_proj:+.4f}**。
    - {'✅ 消息传递有正增益' if mp_gain > 0.01 else '⚠️ 消息传递增益≈0/为负'}；
      {'✅ 图 NN 追平/超过 GBDT' if vs_gbdt > -0.01 else '⚠️ 图 NN 仍不及 GBDT'}；
      {'但仍**远低于** tx 投影 0.74' if gap_to_proj > 0.1 else '且已逼近 tx 投影'}。
    """)
    return br, gap_to_proj, mp_gain, vs_gbdt


@app.cell(hide_code=True)
def _(gap_to_proj, mo, mp_gain, vs_gbdt):
    mo.md(f"""
    ## 2. 诚实解读 → 收口

    - **消息传递增益 = {mp_gain:+.4f}**：{'地址图的跨期边+全局连通确实让图挤出了一些结构信号（比交易图的 +0.036 更实/更虚见数字），' if mp_gain > 0.01 else '即便有跨期边+全局连通，图相对同特征 MLP 的增益依然很小或为负，'}
      这与 nb08 的**诚实边界**一致：只有 **2.88% 边跨 ≤34/>34 split 边界** → 严格 inductive 下 train→test 传导窄，
      图能加到 test 节点的信息受结构限制。
    - **⭐ 距 tx 投影天花板 = {gap_to_proj:+.4f}**：{'图 NN 仍**远低于** tx 投影 0.74。' if gap_to_proj > 0.1 else '图 NN 逼近了 tx 投影。'}
      关键诚实点——tx 投影的 0.74 **不是**更好的检测本事，而是 guilt-by-association 循环（钱包标签 ⟺ 触过 illicit 交易、
      投影分近乎按构造匹配标签，nb06）。**换更强的图模型也修不了这个标签口径**：地址特征/结构的诚实上限就在 0.30 附近，
      0.74 与它的差是**循环的标签回收**、非模型能补的信号。
    - **图增益（若有）本身可能仍是 guilt-by-association 的结构版**：若 SAGE > MLP 来自 illicit 地址相互连接（同构邻居），
      那是把「邻居是否 illicit」传进来——与标签传播同源，不是独立新证据。**报增益要连这层一起说**，别当「图发现了新东西」。
    - **对旗舰问句**：queue disagreement 的「正确解」被 **label provenance** 钉死这一结论，**跨过 tx 断图（nb07）依然成立**——
      到了有跨期边的地址图、上了消息传递，天花板仍是标签口径，不是图结构。呼应 Weber 2019（图不自动赢）。
    - **下一步（需 GPU/云）**：EvolveGCN（49 快照时序版，跨期结构的**动态**利用）——按算力记忆留云主机。
      当前 CPU 静态地址图 GNN 闭环到此。
    """)
    return


@app.cell
def _(EXPERIMENTS_CSV, ev, res_gbdt, res_mlp, res_sage):
    for _name, _model, _r in [
        ("gbdt", "LightGBM-addr", res_gbdt),
        ("mlp", "MLP-addr-nograph", res_mlp),
        ("graphsage", "GraphSAGE-addrgraph", res_sage),
    ]:
        ev.log_experiment(
            {
                "experiment": f"addr_{_name}", "task": "address", "split": "temporal_inductive",
                "model": _model,
                "pr_auc": round(_r["pr_auc"], 4), "base_rate": round(_r["base_rate"], 4),
                "pr_auc_lift": round(_r["pr_auc"] - _r["base_rate"], 4),
                "recall_at_1pct": round(_r["recall_at_1pct"], 4),
                "n_test": int(len(_r["score"])),
                "note": "static address graph GNN Reference; strict inductive (train on first_step<=34 induced subgraph, infer on full graph); unknown in-graph out-of-loss; label retrospective",
            },
            EXPERIMENTS_CSV,
        )
    return


@app.cell
def _(res_mlp, res_sage):
    def test_models_beat_random_by_margin():
        # MLP 与 GraphSAGE 都优于随机（方向性带 margin；地址信号本就弱，margin 放宽到 0.1）
        assert res_mlp["pr_auc"] - res_mlp["base_rate"] > 0.1
        assert res_sage["pr_auc"] - res_sage["base_rate"] > 0.1

    return


@app.cell
def _(mp_gain):
    def test_message_passing_gain_is_bounded():
        # 诚实靶：纯消息传递增益幅度有限（|SAGE−MLP| 小）——跨界边窄，图非翻盘
        assert abs(mp_gain) < 0.2

    return


@app.cell
def _(PROJECTION_REF, res_sage):
    def test_graph_stays_below_projection_ceiling():
        # ⭐ 主线诚实断言：即便上图，仍显著低于 tx 投影参照（0.74）——图修不了标签口径
        assert res_sage["pr_auc"] < PROJECTION_REF - 0.1

    return


if __name__ == "__main__":
    app.run()
