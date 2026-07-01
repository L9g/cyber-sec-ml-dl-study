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
    # 03 · 非 GNN 对照层 —— node2vec+LGBM / IsolationForest

    > 补上「树 vs GNN」二元对立之间缺的一整层，让最终 budget 曲线上有五条线可比
    > （监督树 / 无监督异常 / 图特征+游走 / 社区&子图 / GNN）。本 notebook 落两条**便宜**对照：
    > **① node2vec + LightGBM**（graph-without-GNN）② **IsolationForest**（无监督异常）。
    > 同一口径：labeled∩temporal split（前34训/后15测）+ PR-AUC vs base_rate + yield@budget。

    ## 两条诚实警示（先说，别等结果出来再找补）
    - **交易图按 Time step 断开**：`txs_edgelist` 两端交易全部在同一时间步，node2vec 随机游走走不出同期子图。
      因此这个全图 node2vec 虽然是 transductive（见到测试期节点及其同期结构），但**没有跨时间步 temporal 泄漏**。
      结果显示纯拓扑嵌入仍几乎等于随机——说明 Elliptic 的判别信号在工程特征里，不在裸图结构。
    - **IsolationForest 无监督**：**异常 ≠ illicit**。结果会显示它**比随机还差**——这正是要点：
      靠不用标签绕不开脏标签问题，反而**反证 label provenance 主线**。
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
    from sklearn.ensemble import IsolationForest

    from config import seed_everything, DATA_DIR, EXPERIMENTS_CSV
    from src import data as d
    from src import evaluation as ev

    seed_everything()

    df = d.load_tx_graph()
    train_df, test_df = d.temporal_split(df, train_max_step=34)
    feats = d.feature_columns(df)
    y_train = (train_df["class"] == 1).astype(int)
    y_test = (test_df["class"] == 1).astype(int)
    br_te = ev.base_rate(y_test)
    return (
        DATA_DIR,
        EXPERIMENTS_CSV,
        IsolationForest,
        LGBMClassifier,
        br_te,
        ev,
        feats,
        pd,
        plt,
        test_df,
        train_df,
        y_test,
        y_train,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. 三个模型，同一 temporal 口径
    """)
    return


@app.cell
def _(LGBMClassifier, feats, test_df, train_df, y_train):
    # 基准 A：表格 LightGBM（同 notebook 02，作对照锚点）
    tab = LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=64,
                         n_jobs=4, verbose=-1, random_state=42)
    tab.fit(train_df[feats], y_train)
    score_tab = tab.predict_proba(test_df[feats])[:, 1]
    return (score_tab,)


@app.cell
def _(DATA_DIR, LGBMClassifier, mo, pd, test_df, train_df, y_train):
    # 基准 B：node2vec 嵌入 + LightGBM（需先跑 scripts/build_node2vec.py 缓存）
    emb_path = DATA_DIR / "node2vec_tx.parquet"
    if not emb_path.exists():
        raise FileNotFoundError(
            f"缺 {emb_path}——先运行  .venv/bin/python scripts/build_node2vec.py（~6min 缓存）"
        )
    emb = pd.read_parquet(emb_path)
    emb_cols = [c for c in emb.columns if c.startswith("emb_")]

    tr_e = train_df[["txId"]].merge(emb, on="txId", how="left")
    te_e = test_df[["txId"]].merge(emb, on="txId", how="left")
    cov = te_e[emb_cols].notna().all(axis=1).mean()

    n2v = LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=64,
                         n_jobs=4, verbose=-1, random_state=42)
    n2v.fit(tr_e[emb_cols].fillna(0.0), y_train)
    score_n2v = n2v.predict_proba(te_e[emb_cols].fillna(0.0))[:, 1]
    mo.md(f"node2vec 嵌入覆盖测试集 {cov:.1%}（缺失填 0）。")
    return (score_n2v,)


@app.cell
def _(IsolationForest, feats, test_df, train_df):
    # 基准 C：IsolationForest（无监督，只用特征、不用标签）
    iso = IsolationForest(n_estimators=300, random_state=42, n_jobs=4)
    iso.fit(train_df[feats])
    # score_samples 越小越异常 → 取负号让「越大越可疑」，与其它分数同向
    score_iso = -iso.score_samples(test_df[feats])
    return (score_iso,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. PR-AUC vs base_rate（任务内 sanity，勿跨模型当唯一裁判）
    """)
    return


@app.cell
def _(br_te, ev, mo, pd, score_iso, score_n2v, score_tab, y_test):
    def _pr_table():
        rows = []
        for nm, sc in [("tabular-LGBM", score_tab),
                       ("node2vec-LGBM", score_n2v),
                       ("IsolationForest", score_iso)]:
            pa = ev.pr_auc(y_test, sc)
            rows.append({"model": nm, "pr_auc": round(pa, 3),
                         "base_rate": round(br_te, 3), "lift": round(pa - br_te, 3)})
        return pd.DataFrame(rows)

    res = _pr_table()
    mo.md(f"""
    {mo.ui.table(res, selection=None)}

    读法（本项目锁定）：`pr_auc − base_rate` 只作**任务内**「比随机好多少」。真实结果：
    **tabular ≫ node2vec ≈ IsolationForest ≈ 随机**。两个诚实结论——
    (1) node2vec 在无跨期结构泄漏的同期断图上仍近随机 → 判别信号在**工程特征**不在裸拓扑；
    (2) IsolationForest lift 为**负** → 无监督异常检测在此任务上不如乱猜，**异常≠illicit**。
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. yield@budget 曲线（跨模型唯一 apples-to-apples 口径）
    """)
    return


@app.cell
def _(ev, plt, score_iso, score_n2v, score_tab, y_test):
    def _yield_fig():
        fig, ax = plt.subplots(figsize=(6.4, 3.8))
        for nm, sc, mk in [("tabular-LGBM", score_tab, "o"),
                           ("undirected-node2vec-LGBM", score_n2v, "s"),
                           ("IsolationForest", score_iso, "^")]:
            c = ev.yield_at_budget(y_test, sc)
            ax.plot([r["budget"] * 100 for r in c], [r["recall"] for r in c],
                    marker=mk, label=nm)
        ax.set_xlabel("investigation budget (% of test txs)")
        ax.set_ylabel("yield (recall of illicit)")
        ax.set_title("Non-GNN baselines: yield@budget (labeled∩temporal)")
        ax.legend(); ax.grid(alpha=.3); fig.tight_layout()
        return fig

    _yield_fig()
    return


@app.cell
def _(EXPERIMENTS_CSV, br_te, ev, score_iso, score_n2v, y_test):
    def _log():
        for nm, sc, note in [
            ("undirected-node2vec-LGBM", score_n2v, "交易图按时间步断开；无跨期结构泄漏仍近随机；裸拓扑无判别力"),
            ("IsolationForest", score_iso, "无监督；lift 为负=不如乱猜，反证 label provenance 主线"),
        ]:
            ev.log_experiment(
                {"experiment": f"nongnn_{nm}", "task": "transaction", "split": "temporal",
                 "model": nm, "pr_auc": round(ev.pr_auc(y_test, sc), 4),
                 "base_rate": round(br_te, 4), "pr_auc_lift": round(ev.pr_auc(y_test, sc) - br_te, 4),
                 "recall_at_1pct": round(ev.recall_at_budget(y_test, sc, 0.01), 4),
                 "n_test": int(len(y_test)), "note": note},
                EXPERIMENTS_CSV,
            )
    _log()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 小结（结果反直觉，但更有力）
    - **tabular ≫ node2vec ≈ IsolationForest ≈ 随机**。两条非 GNN 便宜对照都弱——这不是 bug，是证据：
      (1) 交易图按时间步断开，node2vec 没有跨期结构泄漏仍近随机 → **判别力在工程特征、不在裸拓扑**（呼应 Weber/Deprez：Elliptic 上强的是特征而非结构本身）；
      (2) IsolationForest lift 为负 → **无监督绕不开脏标签**，反证 label provenance 主线。
    - 给 GNN 立了个诚实的靶：真正的图增益必须**同时**打过 tabular 且证明来自结构/时序，而非「换个模型」。
    - 升档：把 GNN 接上**同一 harness**（第四/五条线），再回到 actor projection 主线。
    """)
    return


@app.cell
def _(br_te, ev, score_iso, score_tab, y_test):
    def test_supervised_beats_unsupervised():
        # 监督树应明显强于无监督异常（yield@1%）
        r_tab = ev.recall_at_budget(y_test, score_tab, 0.01)
        r_iso = ev.recall_at_budget(y_test, score_iso, 0.01)
        assert r_tab > r_iso

    def test_isoforest_no_better_than_random():
        # 要点：无监督异常在此任务上不优于随机（lift ≤ 小 margin，实测为负）
        assert ev.pr_auc(y_test, score_iso) - br_te < 0.05

    return


@app.cell
def _(br_te, ev, score_n2v, score_tab, y_test):
    def test_node2vec_much_weaker_than_tabular():
        # 裸拓扑嵌入即便见到测试期同期结构，也远弱于工程特征（带大 margin）
        assert ev.pr_auc(y_test, score_tab) - ev.pr_auc(y_test, score_n2v) > 0.3

    def test_node2vec_near_random():
        # node2vec lift 很小（判别信号不在裸结构）
        assert ev.pr_auc(y_test, score_n2v) - br_te < 0.15

    return


if __name__ == "__main__":
    app.run()
