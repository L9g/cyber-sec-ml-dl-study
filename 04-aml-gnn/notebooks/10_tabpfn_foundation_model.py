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
    # 10 · 表格基础模型 TabPFN（Reference 档）—— 换更强的表格模型，修得了标签口径吗？

    > nb06 证地址特征的**诚实上限 ≈0.30**（LightGBM），nb09 证到了有跨期边的地址图、上了消息传递，
    > GraphSAGE 仍卡在 **0.36** 附近、远低于 tx 投影的 **0.74**（后者是 guilt-by-association 循环、非检测本事）。
    > 本节把对照升级到**表格基础模型 TabPFN**（in-context 预训练 transformer，`fit` 只是把训练样本塞进上下文、
    > 不做梯度训练），诚实回答：**一个 SOTA 级表格模型，能不能突破 0.30–0.36 带、逼近 0.74？**
    >
    > 论点预告（不预答，由数字挣）：若 TabPFN 仍停在同一带，则「0.74 是标签循环、不是可学的信号」再获一个
    > 更强模型的背书——**换多强的表格模型都修不了标签口径**（provenance 主线）。

    ## 六层对照（在同一个共享 test 子样本上算指标，差值才同管线）
    | 模型 | 训练数据 | 图 | 隔离什么 |
    |---|---|---|---|
    | LightGBM（全 train，未加权） | 172k | ✗ | 树的上限（≈nb06/nb09） |
    | MLP（全 train，无图） | 172k | ✗ | NN vs 树 |
    | GraphSAGE（全 train，+消息传递） | 172k | ✓ | 纯消息传递 = SAGE − MLP |
    | **LightGBM@2k**（同 context 对照） | 2k | ✗ | **等数据**下 tree 基准 |
    | **TabPFN**（in-context） | 2k | ✗ | **基础模型 vs 树（等数据）= TabPFN − LightGBM@2k** |
    | **TabPFN + G2T-FM**（+结构列） | 2k | ✓(特征) | **结构列增益 = G2T-FM − TabPFN** |

    外部参照线（常数，勿当本节训练结果）：原生 actor GBDT ≈ **0.30**（nb06）／ tx 投影 ≈ **0.74**（nb04/06）。

    ## 诚实边界 & 工程约束（先说，不预答）
    1. **许可**：用**开放版 `tabpfn==2.2.0`**（commercialization 前、对应 Nature 2025 TabPFN v2，免 token 从 HF 拉权重）；
       新版 8.x 已把基础权重关进商用 license 墙（需注册 + `TABPFN_TOKEN`）。仅学术/求职演示。
    2. **算力**：本机无 GPU；TabPFN CPU 推理是 O(context²) 且慢（实测 ctx=2000≈133 s/1k test 行）。故
       TabPFN 用 **2000 分层 context**（in-context 小数据模型的标准用法）、`n_estimators=1`，**六层指标统一算在
       8000 分层 test 子样本上**（GBDT/MLP/SAGE 全量数仅作 magnitude 注脚、不当差值操作数）。全量/更大 context 属云 GPU 升档。
    3. **G2T-FM 不改架构**（arXiv:2508.20906）：把图结构算成特征列喂 TabPFN。核心列「**邻居 illicit 比例**」
       **只用训练标签**（`y & train_mask`）算，零 test 泄漏——它正是 **guilt-by-association 的结构版**：
       若靠它涨分=实锤结构版标签循环、若不涨=更证瓶颈是标签口径。**两向都收紧非翻案**。
    """)
    return


@app.cell
def _(mo):
    import os
    import sys

    sys.path.insert(0, str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch_geometric.nn import SAGEConv
    import lightgbm as lgb
    from sklearn.model_selection import train_test_split
    from tabpfn import TabPFNClassifier

    from config import seed_everything, EXPERIMENTS_CSV, LABEL_ILLICIT
    from src import data as d
    from src import evaluation as ev

    seed_everything()
    torch.set_num_threads(8)
    DEVICE = "cpu"

    # ── 算力参数（NB10_SMOKE=1 缩规模做冒烟）──
    SMOKE = bool(os.environ.get("NB10_SMOKE"))
    CONTEXT_N = 400 if SMOKE else 2000     # TabPFN in-context 训练样本（分层）
    TEST_SUB_N = 800 if SMOKE else 8000    # 共享 test 子样本（六层指标都算在此）
    EPOCHS = 8 if SMOKE else 120           # MLP/SAGE
    N_EST = 1                              # TabPFN 集成数（CPU 求速度）

    NATIVE_GBDT_REF = 0.297   # nb06 原生 actor GBDT（地址特征上限，外部参照）
    PROJECTION_REF = 0.741    # nb04/06 tx 投影到 actor（被标签循环抬高，外部参照）
    return (
        CONTEXT_N, DEVICE, EPOCHS, EXPERIMENTS_CSV, F, LABEL_ILLICIT, N_EST,
        NATIVE_GBDT_REF, PROJECTION_REF, SAGEConv, SMOKE, TEST_SUB_N,
        TabPFNClassifier, d, ev, lgb, mo, nn, np, pd, seed_everything, torch,
        train_test_split,
    )


@app.cell
def _(LABEL_ILLICIT, d, np, pd, torch):
    # ── 建图（同 nb09）：节点=地址，边=AddrAddr，特征=全节点快照（含 unknown）──
    E = d.load_addr_addr(drop_self_loops=True, dedup=True)
    nodes = pd.unique(pd.concat([E.input_address, E.output_address], ignore_index=True))
    idx = {a: i for i, a in enumerate(nodes)}
    n_nodes = len(nodes)

    wf = d.load_wallet_features()
    wc = d.load_wallet_classes()
    snap = d.all_address_snapshots(wf, wc)
    snap = snap.set_index("address").reindex(nodes).reset_index().rename(columns={"index": "address"})
    feats = [c for c in d.wallet_feature_columns(snap) if c != "first_step"]  # first_step=时间代理，剔

    first_step = snap["first_step"].to_numpy()
    cls = snap["class"].to_numpy()
    labeled = np.isin(cls, [1, 2])
    y = torch.tensor((cls == LABEL_ILLICIT).astype(np.float32))
    train_mask = torch.tensor(labeled & (first_step <= 34))
    test_mask = torch.tensor(labeled & (first_step > 34))

    src = E.input_address.map(idx).to_numpy()
    dst = E.output_address.map(idx).to_numpy()

    def undirected(s, t):
        return torch.tensor(np.vstack([np.concatenate([s, t]), np.concatenate([t, s])]), dtype=torch.long)

    ei_full = undirected(src, dst)                               # 推理：全图
    keep_tr = (first_step[src] <= 34) & (first_step[dst] <= 34)  # 训练：两端首现≤34 的诱导子图
    ei_train = undirected(src[keep_tr], dst[keep_tr])

    # 原始特征矩阵（GBDT/TabPFN 用；树与 TabPFN 各自做预处理，不手动标准化）
    X = snap[feats].to_numpy(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    # 标准化版（MLP/SAGE 用，仅训练节点统计）
    mu = X[train_mask.numpy()].mean(0)
    sd = X[train_mask.numpy()].std(0); sd[sd == 0] = 1.0
    x = torch.nan_to_num(torch.tensor((X - mu) / sd), nan=0.0, posinf=0.0, neginf=0.0)
    return (X, ei_full, ei_train, feats, n_nodes, test_mask, train_mask, x, y)


@app.cell
def _(CONTEXT_N, TEST_SUB_N, np, test_mask, train_mask, train_test_split, y):
    # ── 分层抽样：TabPFN context（2000）+ 共享 test 子样本（8000，六层指标统一算在此）──
    yv = y.numpy()
    train_idx = np.where(train_mask.numpy())[0]
    test_idx = np.where(test_mask.numpy())[0]

    def stratified(idx_pool, n, seed=42):
        n = min(n, len(idx_pool))
        if n == len(idx_pool):
            return idx_pool
        keep, _ = train_test_split(idx_pool, train_size=n, stratify=yv[idx_pool], random_state=seed)
        return np.sort(keep)

    ctx_idx = stratified(train_idx, CONTEXT_N)     # TabPFN/GBDT@2k 的训练上下文
    sub_idx = stratified(test_idx, TEST_SUB_N)     # ⭐ 共享评估集
    return ctx_idx, sub_idx, test_idx, train_idx, yv


@app.cell
def _(ctx_idx, mo, n_nodes, sub_idx, test_idx, train_idx, yv):
    mo.md(f"""
    图就绪：节点 **{n_nodes:,}**。全 labeled 训练 **{len(train_idx):,}**（illicit {int(yv[train_idx].sum()):,}、{yv[train_idx].mean():.2%}）、
    全 labeled 测试 **{len(test_idx):,}**（illicit {int(yv[test_idx].sum()):,}、{yv[test_idx].mean():.2%}）。

    - **TabPFN context**（分层抽样）：**{len(ctx_idx):,}** 样本（illicit {int(yv[ctx_idx].sum()):,}）。
    - **⭐ 共享 test 子样本**（六层指标统一算在此）：**{len(sub_idx):,}**（illicit {int(yv[sub_idx].sum()):,}、
      base rate **{yv[sub_idx].mean():.2%}** ≈ 全测试集，PR-AUC 随机基线）。
    """)
    return


@app.cell
def _(ei_full, n_nodes, np, torch, train_mask, y):
    # ── G2T-FM 结构列（不改架构，把图结构算成特征喂 TabPFN）──
    #  degree：label-free 结构量，用全图（推理时可观测）。
    #  邻居 illicit 比例 / 计数：★ 只用训练标签（y & train_mask），零 test 泄漏 = guilt-by-assoc 结构版。
    tgt = ei_full[1]                                     # 无向图，每条边聚到 target
    src_illicit_tr = ((y == 1) & train_mask).float()[ei_full[0]]
    src_trainlab = train_mask.float()[ei_full[0]]
    ones = torch.ones(ei_full.shape[1])

    def scatter(vals):
        out = torch.zeros(n_nodes)
        out.index_add_(0, tgt, vals)
        return out.numpy()

    degree = scatter(ones)
    nb_illicit_cnt = scatter(src_illicit_tr)             # 邻居中「训练已知 illicit」计数
    nb_trainlab_cnt = scatter(src_trainlab)              # 邻居中「训练已标注」计数
    nb_illicit_frac = nb_illicit_cnt / np.maximum(nb_trainlab_cnt, 1.0)
    has_trainlab_nb = (nb_trainlab_cnt > 0).astype(np.float32)

    STRUCT = np.column_stack([
        np.log1p(degree), np.log1p(nb_illicit_cnt), np.log1p(nb_trainlab_cnt),
        nb_illicit_frac, has_trainlab_nb,
    ]).astype(np.float32)
    struct_cols = ["log_degree", "log_nb_illicit_cnt", "log_nb_trainlab_cnt",
                   "nb_illicit_frac", "has_trainlab_nb"]
    return STRUCT, struct_cols


@app.cell
def _(DEVICE, EPOCHS, F, SAGEConv, ev, nn, seed_everything, torch):
    # ── MLP / GraphSAGE + 统一训练；返回全节点 score，评估时再按 idx 取 ──
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

    def train_score_all(model, x, ei_train, ei_eval, y, train_mask, lr=0.01):
        seed_everything()
        model = model.to(DEVICE)
        pos = float(y[train_mask].sum())
        n_tr = float(train_mask.sum().item())
        pos_weight = torch.tensor([max(1.0, (n_tr - pos) / max(pos, 1.0))])
        opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)
        lossf = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        for _ in range(EPOCHS):
            model.train(); opt.zero_grad()
            loss = lossf(model(x, ei_train)[train_mask], y[train_mask])
            loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            return torch.sigmoid(model(x, ei_eval)).cpu().numpy()   # 全节点 score

    return GraphSAGE, MLP, train_score_all


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 1. 六层对照：更强的表格模型突破得了 0.30–0.36 带吗？""")
    return


@app.cell
def _(
    GraphSAGE, MLP, N_EST, STRUCT, TabPFNClassifier, X, ctx_idx, ei_full,
    ei_train, ev, lgb, np, sub_idx, test_mask, train_mask,
    train_score_all, x, y, yv,
):
    # 全节点 score（MLP/SAGE 一次前向即可），随后按 sub_idx 取指标
    d_in = x.shape[1]
    score_mlp = train_score_all(MLP(d_in), x, ei_train, ei_full, y, train_mask)      # 无图
    score_sage = train_score_all(GraphSAGE(d_in), x, ei_train, ei_full, y, train_mask)  # +消息传递

    def _new_gbdt():
        return lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=63,
                                  random_state=42, n_jobs=8, verbose=-1)   # 未加权（nb09 诚实基准口径）

    train_idx_all = np.where(train_mask.numpy())[0]
    test_idx_all = np.where(test_mask.numpy())[0]
    gbdt_full = _new_gbdt().fit(X[train_idx_all], yv[train_idx_all])
    s_gbdt_full = gbdt_full.predict_proba(X[sub_idx])[:, 1]                # 全 train 树 @sub
    s_gbdt_ctx = _new_gbdt().fit(X[ctx_idx], yv[ctx_idx]).predict_proba(X[sub_idx])[:, 1]  # 等数据 2k

    def _tabpfn_score(feat_mat):
        clf = TabPFNClassifier(device="cpu", n_estimators=N_EST,
                               ignore_pretraining_limits=True, random_state=42)
        clf.fit(feat_mat[ctx_idx], yv[ctx_idx].astype(int))
        return clf.predict_proba(feat_mat[sub_idx])[:, 1]

    Xaug = np.column_stack([X, STRUCT]).astype(np.float32)   # G2T-FM：原特征 + 结构列
    s_tabpfn = _tabpfn_score(X)                              # vanilla TabPFN
    s_g2tfm = _tabpfn_score(Xaug)                            # + 结构列

    # ── 六层指标统一在 sub_idx 上组装 ──
    def _pack(s):
        return {"pr_auc": ev.pr_auc(yv[sub_idx], s), "base_rate": ev.base_rate(yv[sub_idx]),
                "recall_at_1pct": ev.recall_at_budget(yv[sub_idx], s, 0.01),
                "recall_at_5pct": ev.recall_at_budget(yv[sub_idx], s, 0.05), "score": s}
    res = {
        "gbdt_full": _pack(s_gbdt_full), "mlp": _pack(score_mlp[sub_idx]),
        "sage": _pack(score_sage[sub_idx]), "gbdt_ctx": _pack(s_gbdt_ctx),
        "tabpfn": _pack(s_tabpfn), "g2tfm": _pack(s_g2tfm),
    }
    # 全测试集注脚（便宜模型；magnitude 参照，不当差值操作数）
    foot = {
        "gbdt_full_ft": ev.pr_auc(yv[test_idx_all], gbdt_full.predict_proba(X[test_idx_all])[:, 1]),
        "mlp_ft": ev.pr_auc(yv[test_idx_all], score_mlp[test_idx_all]),
        "sage_ft": ev.pr_auc(yv[test_idx_all], score_sage[test_idx_all]),
    }
    return foot, res


@app.cell
def _(NATIVE_GBDT_REF, PROJECTION_REF, foot, mo, pd, res):
    br = res["gbdt_full"]["base_rate"]
    order = [
        ("LightGBM (full train, unweighted)", "gbdt_full"),
        ("MLP (full train, no graph)", "mlp"),
        ("GraphSAGE (full train, +msg passing)", "sage"),
        ("LightGBM@2k (same context)", "gbdt_ctx"),
        ("TabPFN (in-context, 2k)", "tabpfn"),
        ("TabPFN + G2T-FM (+struct cols)", "g2tfm"),
    ]
    tbl = pd.DataFrame([
        {"model": name, "PR-AUC": round(res[k]["pr_auc"], 4),
         "recall@1%": round(res[k]["recall_at_1pct"], 3),
         "recall@5%": round(res[k]["recall_at_5pct"], 3)}
        for name, k in order
    ])
    mp_gain = res["sage"]["pr_auc"] - res["mlp"]["pr_auc"]                # 纯消息传递
    fm_vs_tree = res["tabpfn"]["pr_auc"] - res["gbdt_ctx"]["pr_auc"]      # ⭐ 基础模型 vs 树（等数据）
    g2tfm_lift = res["g2tfm"]["pr_auc"] - res["tabpfn"]["pr_auc"]         # ⭐ 结构列增益
    best_tab = max(res["tabpfn"]["pr_auc"], res["g2tfm"]["pr_auc"])
    gap_to_proj = PROJECTION_REF - best_tab                              # 距 tx 投影天花板

    mo.md(f"""
    共享 test 子样本 base rate = **{br:.2%}**（PR-AUC 随机基线）。六层同一评估集：

    {mo.ui.table(tbl, selection=None)}

    全测试集注脚（magnitude 参照，非差值操作数）：LightGBM {foot['gbdt_full_ft']:.4f}／MLP {foot['mlp_ft']:.4f}／SAGE {foot['sage_ft']:.4f}
    （与 nb09 全量口径同量级）。外部参照：原生 GBDT ≈ **{NATIVE_GBDT_REF}**（nb06）／ tx 投影 ≈ **{PROJECTION_REF}**（nb04/06）。

    - **⭐ 基础模型 vs 树（等数据）= TabPFN − LightGBM@2k = {fm_vs_tree:+.4f}**（同 2k context，唯一差别是模型族）。
    - **⭐ 结构列增益 = G2T-FM − TabPFN = {g2tfm_lift:+.4f}**（同模型同 context，加了 degree+邻居 illicit 比例）。
    - **纯消息传递增益 = SAGE − MLP = {mp_gain:+.4f}**（复核 nb09 结论）。
    - **⭐ 距 tx 投影天花板 = {gap_to_proj:+.4f}**（TabPFN 家族最好一档 {best_tab:.4f} vs 0.74）。
    - {'✅ TabPFN 强过等数据树' if fm_vs_tree > 0.01 else '⚠️ TabPFN 未强过等数据树'}；
      {'✅ 结构列（guilt-by-assoc 版）有正增益 → 实锤结构版标签循环' if g2tfm_lift > 0.01 else '⚠️ 结构列增益≈0/为负 → 更证瓶颈是标签口径不是结构'}；
      {'但**仍远低于** tx 投影 0.74' if gap_to_proj > 0.1 else '且已逼近 tx 投影'}。
    """)
    return best_tab, fm_vs_tree, g2tfm_lift, gap_to_proj, mp_gain


@app.cell
def _(EXPERIMENTS_CSV, ev, res):
    for _name, _model, _k in [
        ("tabpfn_gbdt_full", "LightGBM-addr-full", "gbdt_full"),
        ("tabpfn_mlp", "MLP-addr-nograph", "mlp"),
        ("tabpfn_sage", "GraphSAGE-addrgraph", "sage"),
        ("tabpfn_gbdt_ctx", "LightGBM-addr-ctx2k", "gbdt_ctx"),
        ("tabpfn_vanilla", "TabPFN-v2-addr", "tabpfn"),
        ("tabpfn_g2tfm", "TabPFN-v2-G2TFM-addr", "g2tfm"),
    ]:
        _r = res[_k]
        ev.log_experiment(
            {
                "experiment": _name, "task": "address", "split": "temporal_inductive",
                "model": _model,
                "pr_auc": round(_r["pr_auc"], 4), "base_rate": round(_r["base_rate"], 4),
                "pr_auc_lift": round(_r["pr_auc"] - _r["base_rate"], 4),
                "recall_at_1pct": round(_r["recall_at_1pct"], 4),
                "n_test": int(len(_r["score"])),
                "note": "nb10 six-layer TabPFN comparison; metric on shared stratified test subsample; "
                        "TabPFN=open v2 n_est=1 2k context; G2T-FM struct cols use train-only labels; "
                        "strict inductive; label retrospective (provenance ceiling unchanged)",
            },
            EXPERIMENTS_CSV,
        )
    return


@app.cell(hide_code=True)
def _(PROJECTION_REF, best_tab, fm_vs_tree, g2tfm_lift, gap_to_proj, mo, mp_gain):
    mo.md(f"""
    ## 2. 诚实解读 → 收口

    - **基础模型 vs 树（等数据）= {fm_vs_tree:+.4f}**：{'TabPFN 在同 2k context 下确实强过 LightGBM，但幅度有限、' if fm_vs_tree > 0.01 else 'TabPFN 在同 2k context 下并未系统强过树、'}
      **落点仍在地址特征的诚实带内**（nb06 ≈0.30、nb09 ≈0.36）。基础模型换掉的是**函数族**，换不掉**标签口径**。
    - **⭐ 结构列增益（G2T-FM）= {g2tfm_lift:+.4f}**：{'邻居 illicit 比例这类列确有正增益 → 但这**恰恰是 guilt-by-association 的结构版**（把「邻居是否 illicit」灌进特征），与钱包标签的 OR/max 传播同源，**不是独立新证据**、是同一循环换个入口。' if g2tfm_lift > 0.01 else '连「邻居 illicit 比例」这种结构版循环列都挤不出增益 → 更硬地证明瓶颈是**标签口径**、不是特征/结构表达力。'}
    - **纯消息传递增益 = {mp_gain:+.4f}**：复核 nb09——静态地址图上消息传递增益有限。
    - **⭐ 距 tx 投影天花板 = {gap_to_proj:+.4f}**：TabPFN 家族最好一档 {best_tab:.4f} 仍{'**远低于**' if gap_to_proj > 0.1 else '逼近'} tx 投影 {PROJECTION_REF}。
      关键诚实点——0.74 **不是**更好的检测本事，而是 guilt-by-association 循环（钱包标签 ⟺ 触过 illicit 交易、
      投影分近乎按构造匹配标签，nb06）。**一个 SOTA 表格基础模型也补不上这个 gap**：地址侧诚实上限就在 0.3–0.4 带，
      0.74 与它的差是**循环的标签回收**、非任何模型能学的信号。
    - **对旗舰问句**：queue disagreement 的「正确解」被 **label provenance** 钉死这一结论，**跨过 tx 断图（nb07）、
      跨期地址图（nb09）、再到表格基础模型（nb10）依然成立**——换更强的函数族、加结构列，天花板仍是标签口径。
      呼应 TabArena「验证协议+集成 > 架构选择」：模型换代改不了评估/标签层的病根。
    - **升档路（需云 GPU）**：新版 TabPFN-2.5/3（更大 context、需商用 token）、全测试集、G2T-FM 更全结构列
      （PageRank/assortativity）——按算力记忆留云主机。当前 CPU 开放版闭环到此。
    """)
    return


@app.cell
def _(res):
    def test_tabpfn_beats_random_by_margin():
        # TabPFN 与 G2T-FM 都优于随机（方向性带 margin；地址信号本就弱，margin 0.1）
        assert res["tabpfn"]["pr_auc"] - res["tabpfn"]["base_rate"] > 0.1
        assert res["g2tfm"]["pr_auc"] - res["g2tfm"]["base_rate"] > 0.1

    return


@app.cell
def _(PROJECTION_REF, best_tab):
    def test_tabpfn_stays_below_projection_ceiling():
        # ⭐ 主线诚实断言：更强的表格基础模型仍显著低于 tx 投影（0.74）——修不了标签口径
        assert best_tab < PROJECTION_REF - 0.1

    return


@app.cell
def _(best_tab):
    def test_tabpfn_within_address_feature_band():
        # 诚实靶：TabPFN 家族最好一档仍落在地址特征诚实带内（不翻盘到 0.6+）
        assert best_tab < 0.6

    return


@app.cell
def _(g2tfm_lift):
    def test_struct_col_gain_is_bounded():
        # 结构列（guilt-by-assoc 版）增益幅度有限——非翻盘（无论正负都应 |·|<0.2）
        assert abs(g2tfm_lift) < 0.2

    return


if __name__ == "__main__":
    app.run()
