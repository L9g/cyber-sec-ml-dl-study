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
    # 06 · 原生 actor 模型（不经 tx 投影）—— Reference 档第一步

    > 前 5 个 notebook 的 actor 分数都是**交易分数投影**上来的（= tx 任务透过聚合算子再看一遍，
    > §3/§5 已论证这是回溯循环）。本节建**原生 actor 模型**：直接用**地址级特征**
    > （`wallets_features`：num_txs / btc_* / lifetime / blocks_btwn_* / counterparty 等 51 维）
    > 学地址标签，**不碰交易分数**。问 Reference 档的关键问题：
    >
    > **actor 队列有没有独立于 tx 投影的信号？**（有 → 值得原生建模/上 GNN；没有 → 投影已够、图很难赢）

    ## 三条诚实边界（先说）
    1. **切分干净、标签仍脏**：用 group-aware temporal split——**test = 首现 >34 的地址（纯 inductive，
       训练期从未见）**，train/test 地址集合不相交、无实体泄漏（AML 最常被审计质疑的点）。**但**地址标签
       仍是 `wallets_classes` 的一址一枚**全局/事后**裁定 → 即使特征切分干净，PR-AUC 仍是 **retrospective**。
       这正是项目一「切分干净 ≠ 特征干净」在**标签层**的复现（这里是「切分干净 ≠ 标签干净」）。
    2. **绝对时间特征已剔**：first/last_block_appeared_in、first_sent/received_block（绝对 block 索引=时间代理、
       不可跨期迁移）像 tx 的 Time step 一样剔除；保留 lifetime / blocks_btwn_*（时间差、相对）。
    3. **与投影比较只在共同地址集 + operational 曲线**：native vs projection 的 PR-AUC 同标签同 base rate 才可比；
       跨口径只比 queue overlap / yield（守 CLAUDE.md 指标纪律）。
    """)
    return


@app.cell
def _(mo):
    import sys
    sys.path.insert(0, str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from lightgbm import LGBMClassifier

    from config import seed_everything, EXPERIMENTS_CSV, LABEL_ILLICIT, LABEL_LICIT
    from src import data as d
    from src import evaluation as ev
    from src import projection as proj

    seed_everything()

    # ── 原生 actor 模型：地址特征 → 地址标签，group-aware inductive temporal split ──
    wf = d.load_wallet_features()
    wc = d.load_wallet_classes()
    a_train, a_test = d.native_actor_temporal_split(wf, wc, train_max_step=34)
    wfeats = d.wallet_feature_columns(a_train)

    y_atr = (a_train["class"] == LABEL_ILLICIT).astype(int)
    native = LGBMClassifier(
        n_estimators=300, learning_rate=0.05, num_leaves=64,
        n_jobs=4, verbose=-1, random_state=42,
    )
    native.fit(a_train[wfeats], y_atr)

    a_test = a_test.copy()
    a_test["native_score"] = native.predict_proba(a_test[wfeats])[:, 1]
    y_ate = (a_test["class"] == LABEL_ILLICIT).astype(int).values
    return (
        EXPERIMENTS_CSV,
        LABEL_ILLICIT,
        LABEL_LICIT,
        a_test,
        a_train,
        d,
        ev,
        np,
        pd,
        plt,
        proj,
        wc,
        y_ate,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 1. 原生 actor 模型表现（inductive、无实体泄漏、标签 retrospective）""")
    return


@app.cell
def _(a_test, a_train, ev, mo, y_ate):
    pr_n = ev.pr_auc(y_ate, a_test["native_score"].values)
    br_n = ev.base_rate(y_ate)
    r1 = ev.recall_at_budget(y_ate, a_test["native_score"].values, 0.01)
    r5 = ev.recall_at_budget(y_ate, a_test["native_score"].values, 0.05)

    mo.md(f"""
    - **train** {len(a_train):,} 地址（illicit {int((a_train['class']==1).sum()):,}）
      → **test（纯 inductive）** {len(a_test):,} 地址（illicit {int(y_ate.sum()):,}，base rate **{br_n:.1%}**）。
    - **原生 actor PR-AUC = {pr_n:.4f}**（随机基线 {br_n:.3f}，lift {pr_n - br_n:+.3f}）；
      recall@1% = **{r1:.3f}**、recall@5% = **{r5:.3f}**。
    - 特征**完全不含交易分数**（num_txs / btc / lifetime / counterparty 等 51 维）、test 地址训练期**从未见** →
      这是**独立于 tx 投影**的信号，且切分无泄漏。⚠️ 但地址标签是全局/事后裁定，故此分**仍 retrospective**
      （切分干净 ≠ 标签干净）。
    """)
    return br_n, pr_n


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. ⭐ 原生 vs tx 投影：actor 队列有独立信号吗？

    重建 tx 投影队列（tx-LightGBM → max 投影，同 nb04），在**共同地址集**上和原生模型比。
    """)
    return


@app.cell
def _(LABEL_ILLICIT, LABEL_LICIT, a_test, d, ev, mo, proj):
    # 重建 tx 投影（自包含）：tx 模型 temporal 训练 → 测试期打分 → max 投影到地址
    from lightgbm import LGBMClassifier as _LGB

    _full = d.load_tx_graph()
    _tr, _ = d.temporal_split(_full, train_max_step=34)
    _tf = d.feature_columns(_full)
    _txm = _LGB(n_estimators=300, learning_rate=0.05, num_leaves=64,
                n_jobs=4, verbose=-1, random_state=42)
    _txm.fit(_tr[_tf], (_tr["class"] == 1).astype(int))
    _ta = _full[_full["Time step"] > 34].copy()
    _ta["score"] = _txm.predict_proba(_ta[_tf])[:, 1]
    _scores = dict(zip(_ta["txId"], _ta["score"]))
    _part = d.actor_participation(include_outputs=True)
    proj_q = proj.project_scores_to_actors(_part, _scores, agg="max", addr_col="address")

    # 共同地址集 = 原生 inductive 测试地址 ∩ 有投影分的地址
    merged = a_test[["address", "class", "native_score"]].merge(
        proj_q.rename(columns={"actor_score": "proj_score"}), on="address", how="inner"
    )
    cov = len(merged) / len(a_test)

    y_sh = (merged["class"] == LABEL_ILLICIT).astype(int).values
    pr_native_sh = ev.pr_auc(y_sh, merged["native_score"].values)
    pr_proj_sh = ev.pr_auc(y_sh, merged["proj_score"].values)
    br_sh = ev.base_rate(y_sh)

    mo.md(f"""
    共同地址集 = 原生 inductive 测试地址 ∩ 有 tx 投影分的地址 = **{len(merged):,}**
    （覆盖原生测试 {cov:.1%}；illicit base rate {br_sh:.1%}，两模型同标签同分母 → PR-AUC 可比）：

    | 模型 | 信号来源 | 共同集 PR-AUC |
    |---|---|---|
    | **原生 actor** | 地址特征（独立于 tx） | **{pr_native_sh:.4f}** |
    | tx 投影（max） | 交易分数 OR/max 抬到地址 | **{pr_proj_sh:.4f}** |

    - 两者都超随机（{br_sh:.3f}），但**投影碾压原生**：差距 **{pr_proj_sh - pr_native_sh:+.4f}**（投影 − 原生）。
    - ⭐ **这个 gap 正是 guilt-by-association 循环的显形**：投影分 = max(tx 分)，而钱包标签 ⟺「是否触过 illicit 交易」
      （§3 双条件）→ 投影**几乎按构造匹配标签**（tx 模型抓 illicit 交易 → max 抬起来 ≈ 标签本身）。原生模型**没有**这层
      循环优势，得从通用地址统计（btc 量/笔数/lifetime/counterparty）**独立**预测全局标签。
    - 故 **0.74 是被 provenance 循环抬高的、不是独立检测本事**；**0.30 才是地址特征对 actor illicitness 的诚实上限**。
      gap 量化了「actor 可检测性」里**多少是循环的标签回收、多少是真实实体信号**——**大头是循环**。
    """)
    return br_sh, cov, merged, pr_native_sh, pr_proj_sh, y_sh


@app.cell
def _(ev, merged, mo, np, pd, y_sh):
    # 队列一致性 + who-catches-what（budget=5%）
    _n = len(merged)
    def _topset(col, k):
        return set(merged.sort_values(col, ascending=False, kind="mergesort")["address"].values[:k])

    _rows = []
    for _b in (0.01, 0.05):
        _k = max(1, int(round(_b * _n)))
        _nq = _topset("native_score", _k)
        _pq = _topset("proj_score", _k)
        _rows.append({"budget": f"{_b:.0%}", "k": _k,
                      "Jaccard(native,proj)": round(len(_nq & _pq) / len(_nq | _pq), 3)})
    jt = pd.DataFrame(_rows)

    # 5% 预算下各自命中的 illicit（who-catches-what）
    _k5 = max(1, int(round(0.05 * _n)))
    _ill = set(merged.loc[y_sh == 1, "address"])
    _nq5 = _topset("native_score", _k5)
    _pq5 = _topset("proj_score", _k5)
    both = len(_ill & _nq5 & _pq5)
    native_only = len(_ill & (_nq5 - _pq5))
    proj_only = len(_ill & (_pq5 - _nq5))
    neither = len(_ill - _nq5 - _pq5)

    mo.md(f"""
    **队列一致性**（native top-k 与 proj top-k 的地址重叠）：

    {mo.ui.table(jt, selection=None)}

    **5% 预算下 illicit 地址被谁抓到**（共 {len(_ill):,} 个）：

    | both | 仅 native | 仅 proj | 都没抓 |
    |---|---|---|---|
    | {both:,} | **{native_only:,}** | **{proj_only:,}** | {neither:,} |

    - **不对称、不是"互补"**：仅 proj 命中（{proj_only:,}）**远多于**仅 native（{native_only:,}）——原生模型几乎没抓到
      投影漏掉的 illicit，反过来投影抓到一大批原生漏掉的。原生**大体是投影的更弱子集**，不是独立的另一半信号。
    - Jaccard < 1 说明队列确实不一致（第三种不一致来源：**建模范式 投影 vs 原生**），但方向是**投影主导**：
      换原生范式主要是**变差**，不是发现新洗钱。→ **不支持**"上原生/GNN 就有增量"的乐观预设。
    """)
    return both, jt, native_only, neither, proj_only


@app.cell(hide_code=True)
def _(both, mo, native_only, neither, proj_only):
    mo.md(f"""
    ## 3. 小结 → 下一步

    - **原生 actor 模型立住**（inductive、无实体泄漏），但**独立信号很弱**：PR-AUC ≈ 0.30 vs 投影 ≈ 0.74。
    - ⭐ **gap = guilt-by-association 循环的显形**：投影分下游于「是否触过 illicit 交易」这个**定义标签的信号**，
      故几乎按构造匹配标签；原生特征无此循环 → 暴露 actor 任务**真实的独立难度**（低得多）。
      5% 预算 who-catches **不对称**（仅 proj {proj_only:,} ≫ 仅 native {native_only:,}）→ 原生大体是投影的**更弱子集**。
    - **对旗舰问句的贡献**：「actor 队列有没有独立于 tx 的信号？」诚实答案 = **有，但很少**；actor 可检测性**大头是循环的
      标签回收，不是实体信号**。这**加固 provenance 主线**——什么在 actor 队列上有效，由标签怎么造（tx 传播）决定。
    - ⚠️ **retrospective 未解**：切分干净（inductive）但标签仍全局/事后 → **切分干净 ≠ 标签干净**，两模型都带 provenance 债。
    - **给 GNN 立的诚实靶（更硬了）**：GNN 要同时打过原生 tabular（0.30，易）**和 tx 投影（0.74，难——且它便宜、
      只因匹配了标签 provenance）**，还要证明增益来自**结构/时序**而非再拟合一次 retrospective 标签。很可能证明
      「再复杂的模型也修不了标签口径」（呼应 Weber 2019：匹配的简单基线难被超越）。
    - 下一步：EvolveGCN / GraphSAGE（AddrAddr 图），量化图相比本节 tabular + 投影的净增益来自结构还是时序。
    """)
    return


@app.cell
def _(EXPERIMENTS_CSV, br_n, ev, a_test, pr_n, y_ate):
    ev.log_experiment(
        {
            "experiment": "native_actor_tabular", "task": "actor", "split": "temporal-inductive",
            "model": "wallet-features-LightGBM",
            "pr_auc": round(pr_n, 4), "base_rate": round(br_n, 4),
            "pr_auc_lift": round(pr_n - br_n, 4),
            "recall_at_1pct": round(ev.recall_at_budget(y_ate, a_test["native_score"].values, 0.01), 4),
            "n_test": int(len(y_ate)),
            "note": "native actor (address features, NOT tx projection); inductive no-leak split; label still global/retrospective (clean split != clean label); 勿跨任务比",
        },
        EXPERIMENTS_CSV,
    )
    return


@app.cell
def _(br_n, pr_n):
    def test_native_actor_beats_random_by_margin():
        # 原生 actor 有独立信号但弱：超随机但幅度不大（retrospective 标签下，方向性带 margin）
        assert pr_n - br_n > 0.15

    return


@app.cell
def _(pr_native_sh, pr_proj_sh, br_sh):
    def test_both_models_have_signal():
        # 共同集上原生与投影都超随机 → actor 队列有信号
        assert pr_native_sh - br_sh > 0.15
        assert pr_proj_sh - br_sh > 0.3

    def test_projection_dominates_native():
        # ⭐ 核心：tx 投影碾压原生（gap = guilt-by-association 循环显形），非"势均力敌互补"
        assert pr_proj_sh - pr_native_sh > 0.2

    return


@app.cell
def _(both, jt, native_only, proj_only):
    def test_projection_catch_is_asymmetric():
        # who-catches 不对称：仅 proj 命中远多于仅 native → 原生是投影的更弱子集，非独立另一半
        assert proj_only > 5 * native_only
        assert native_only > 0            # 但原生并非纯子集（有极少独有命中）

    def test_queues_disagree():
        # 队列确实不一致（5% 预算 Jaccard 明显 <1）
        assert jt.iloc[-1]["Jaccard(native,proj)"] < 0.6

    return


@app.cell
def _(cov):
    def test_projection_coverage_reasonable():
        # 多数原生测试地址有投影分（共同集足够大，比较有意义）
        assert cov > 0.5

    return


if __name__ == "__main__":
    app.run()
