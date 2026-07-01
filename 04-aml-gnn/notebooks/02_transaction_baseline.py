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
    # 02 · 交易级 baseline —— temporal split + LightGBM（诚实指标）

    > MVP 薄切片第一段。**只做 temporal split 一种口径**（static/random 仅在后续解释
    > actor retrospective label 时作对照，不进主结果）。这一步刻意**不碰图、不碰 GNN**——
    > 先立一个调好的表格 baseline，作为「图是否真有用」的诚实对照（Weber 2019 自报 RF>普通 GCN）。

    ## 三条评估纪律（本项目锁定）
    1. 主看 **PR-AUC**，随机基线 = illicit 占比（**不是 0.5**）；`pr_auc − base_rate` 只是**任务内** sanity。
    2. **报曲线不报单点**：yield@budget 曲线（0.1%→5%），对应 AML 调查产能。
    3. **Time step 不进特征**（只用于切分）——否则学到 base-rate 漂移这个不可迁移的捷径。
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

    from config import seed_everything, EXPERIMENTS_CSV
    from src import data as d
    from src import evaluation as ev

    seed_everything()

    df = d.load_tx_graph()
    train_df, test_df = d.temporal_split(df, train_max_step=34)   # 前34步训 / 后15步测
    feats = d.feature_columns(df)                                  # 182 维，去 txId/Time step/class
    y_train = (train_df["class"] == 1).astype(int)
    y_test = (test_df["class"] == 1).astype(int)
    return (
        EXPERIMENTS_CSV,
        LGBMClassifier,
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
    ## 1. Temporal split：训练期 base rate ≠ 测试期
    """)
    return


@app.cell
def _(ev, mo, y_test, y_train):
    br_tr, br_te = ev.base_rate(y_train), ev.base_rate(y_test)
    mo.md(f"""
    | 区间 | n（已标注） | illicit base rate |
    |---|---|---|
    | 前 34 步（训练） | {len(y_train):,} | **{br_tr:.1%}** |
    | 后 15 步（测试） | {len(y_test):,} | **{br_te:.1%}** |

    测试期 illicit 占比（{br_te:.1%}）明显低于训练期（{br_tr:.1%}）——EDA 信号 A 的直接后果。
    **随机切分会把这个跨期漂移抹平、制造虚高**；temporal split 保留它，是唯一诚实的口径。
    测试期 base rate {br_te:.3f} 就是下面 PR-AUC 的随机基线。
    """)
    return (br_te,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. LightGBM baseline + PR-AUC vs 随机基线
    """)
    return


@app.cell
def _(LGBMClassifier, feats, test_df, train_df, y_train):
    model = LGBMClassifier(
        n_estimators=300, learning_rate=0.05, num_leaves=64,
        n_jobs=4, verbose=-1, random_state=42,
    )
    model.fit(train_df[feats], y_train)
    scores = model.predict_proba(test_df[feats])[:, 1]
    return (scores,)


@app.cell
def _(br_te, ev, mo, scores, y_test):
    pa = ev.pr_auc(y_test, scores)
    mo.md(f"""
    - **PR-AUC = {pa:.3f}**，随机基线 = {br_te:.3f} → lift **{pa-br_te:.3f}**。
      表格模型在**已标注**测试集上远超随机——和文献一致：Elliptic 系列的节点特征已聚合了
      不少局部信息，调好的树模型是很强的对照，**图不会自动赢**（升档再量化图增益）。
    - ⚠️ 这个 {pa:.3f} 只在 **labeled∩temporal** 上成立。真实部署面对大量 unknown（≠良性），
      notebook 后续（unknown-as-benign 错误示范 / actor 队列）会揭示它有多乐观。
    """)
    return (pa,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. yield@budget 曲线（贴合调查产能，报曲线不报单点）
    """)
    return


@app.cell
def _(ev, mo, pd, scores, y_test):
    curve = ev.yield_at_budget(y_test, scores)
    tbl = pd.DataFrame(curve)
    tbl["budget"] = (tbl["budget"] * 100).map(lambda x: f"{x:g}%")
    tbl = tbl.rename(columns={"recall": "yield(占全部illicit)", "precision": "队列内命中率"})
    mo.md(f"""
    只调查分数最高的前 budget 比例交易，能捞到多少 illicit：

    {mo.ui.table(tbl.round(3), selection=None)}

    队列顶端**极干净**（前 1-2% 命中率接近满分）——这是个重要伏笔：
    **交易级检测的顶端不是难点**；项目真正的硬问题在下一步——同样这批分数**聚合到 actor 队列**后，
    和地址标签体系是否一致（scoring granularity vs label provenance）。
    """)
    return (curve,)


@app.cell
def _(curve, plt):
    xs = [r["budget"] * 100 for r in curve]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.plot(xs, [r["recall"] for r in curve], marker="o", label="yield (recall of illicit)")
    ax.plot(xs, [r["precision"] for r in curve], marker="s", label="queue precision")
    ax.set_xlabel("investigation budget (% of test txs)")
    ax.set_ylabel("rate"); ax.set_title("Transaction-level yield@budget (temporal)")
    ax.legend(); ax.grid(alpha=.3); fig.tight_layout()
    fig
    return


@app.cell
def _(EXPERIMENTS_CSV, br_te, ev, pa, scores, y_test):
    # 落盘（upsert，逻辑键 experiment/task/split/model）
    ev.log_experiment(
        {
            "experiment": "tx_baseline", "task": "transaction", "split": "temporal",
            "model": "LightGBM", "pr_auc": round(pa, 4), "base_rate": round(br_te, 4),
            "pr_auc_lift": round(pa - br_te, 4),
            "recall_at_1pct": round(ev.recall_at_budget(y_test, scores, 0.01), 4),
            "n_test": int(len(y_test)),
            "note": "labeled∩temporal; Time step 不进特征; MVP tabular 对照",
        },
        EXPERIMENTS_CSV,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 小结 → 下一步（薄切片剩余段）
    - 表格 baseline 立住：PR-AUC 远超随机、队列顶端干净。**图要证明有用，得先跨过这条线。**
    - 下一步不是堆 GNN，而是 **actor projection（先只做 max）→ 两标签体系 yield 对照 →
      unknown-as-benign 错误示范 → 归因表雏形**，把「队列不一致来自 scoring 还是 label provenance」讲清楚。
    """)
    return


@app.cell
def _(ev, y_test, y_train):
    def test_temporal_base_rate_drops():
        # 信号 A：测试期 illicit base rate 明显低于训练期
        assert ev.base_rate(y_train) - ev.base_rate(y_test) > 0.02

    return


@app.cell
def _(br_te, ev, pa, scores, y_test):
    def test_pr_auc_beats_random_by_margin():
        # 表格 baseline 应显著高于随机基线（带 margin，不锁具体值）
        assert pa - br_te > 0.3

    def test_top_budget_queue_is_clean():
        # 顶端队列命中率应很高（前 1% 预算 precision 远超 base rate）
        p1 = ev.yield_at_budget(y_test, scores, budgets=(0.01,))[0]["precision"]
        assert p1 > 0.5

    return


if __name__ == "__main__":
    app.run()
