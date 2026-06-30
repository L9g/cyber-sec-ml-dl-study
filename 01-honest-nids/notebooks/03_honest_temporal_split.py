import marimo

__generated_with = "0.23.11"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 03 · 诚实重做 —— 封堵两个陷阱，得到诚实数字

    > **本系列：01 故意踩坑 → 02 IP 泄漏机制 → 03（本文）逐一封堵 → 04 跨数据集泛化测试**

    ---

    notebook 01 踩了两个陷阱，在 v3（含真 IP）上得到**近乎满分**：accuracy=1.0、macro-F1≈1.0、
    PR-AUC≈1.0、attack recall=1.0——靠的是只有 40 个 IP 的「IP=标签」捷径。
    本 notebook 封堵它们，看**诚实的落差有多大**，并做一个 notebook 01 没做的分析：
    **在真实攻击基率下，这个模型的告警有多少是误报**（`axelsson2000baserate`, Arp P8）。

    三件事，按顺序做：

    | # | 修复 | 对应陷阱 |
    |---|---|---|
    | 1 | 识别并移除泄漏/环境特征 | Arp P4 spurious correlations |
    | 2 | 用时间顺序切分代替随机切分 | Arp P3 data snooping |
    | 3 | 在真实基率下重解读 precision（base-rate 分析） | Arp P8 base rate fallacy |
    """)
    return


@app.cell
def _(mo):
    import sys
    sys.path.append(str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix

    from config import SEED, seed_everything, EXPERIMENTS_CSV, DATA_DIR
    from src import data as d
    from src import feature_engineering as fe
    from src import evaluation as ev

    seed_everything()
    return (
        DATA_DIR,
        EXPERIMENTS_CSV,
        LGBMClassifier,
        SEED,
        accuracy_score,
        confusion_matrix,
        d,
        ev,
        fe,
        mo,
        np,
        pd,
    )


@app.cell
def _(DATA_DIR, d):
    DATASET = "NF-UNSW-NB15-v3"
    df = d.load_netflow(DATA_DIR / f"{DATASET}.parquet")
    print(f"数据集: {df.shape}")
    return DATASET, df


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 修复 1：识别并移除泄漏/环境特征（P4）

    NetFlow-v2 里有几类特征不应该进入模型：

    - **IP 地址**（`IPV4_SRC_ADDR`, `IPV4_DST_ADDR`）：实验室攻击机有固定 IP（全集仅 40 个），
      模型学「这个 IP = 攻击」——换到真实网络立刻失效。**notebook 01 正是靠它拿到满分**，
      这里把它移除才看到真实水平。
    - **L4 端口**（`L4_SRC_PORT`, `L4_DST_PORT`）：攻击工具常用固定端口，
      模型会把「端口捷径」当成泛化规则。

    `feature_engineering.py` 里有完整的特征 policy 矩阵，下面展示非 inference-safe 的列。
    """)
    return


@app.cell
def _(df, fe):
    policy = fe.build_feature_policy_matrix(df.columns.tolist())
    non_safe = policy[policy.policy != fe.POLICY_INFERENCE_SAFE]
    print(f"非 inference-safe 特征（{len(non_safe)} 列）：")
    non_safe
    return (policy,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 修复 2：时间顺序切分（P3 Temporal Snooping）

    **随机切分的问题**：一次端口扫描攻击产生 1000 条流，随机切分后，
    其中 800 条进训练集、200 条进测试集。模型在训练时已经「见过」这次攻击的统计指纹，
    测试时自然表现优异——但这是记忆，不是检测能力。

    **诚实做法**：按 `FLOW_START_MILLISECONDS`（真起始时刻）排序，前 80% 训练、后 20% 测试。
    测试集只含训练窗口**之后发生**的流，是「用历史训练、预测未来」的真实场景。

    **v3 的关键升级**：NF-UNSW-NB15-**v3** 含 per-flow 真时间戳
    （`FLOW_START/END_MILLISECONDS`），所以这是**真 temporal split**，
    不再是 v2 镜像被迫使用的「行序代理」。绝对时间戳列只用于排序，
    **排完即从特征中剔除**（否则「时间 > T = 测试集」本身又是一种泄漏）。
    以下先看攻击随真实时间的分布。
    """)
    return


@app.cell
def _(df, pd):
    # 按真实时间戳排序后分 10 个十分位，看每段的攻击占比
    _TIME_COL = "FLOW_START_MILLISECONDS"
    decile_labels = [f"D{i+1}" for i in range(10)]
    df_time = df.sort_values(_TIME_COL, kind="stable").reset_index(drop=True)
    df_time["decile"] = pd.qcut(df_time.index, q=10, labels=decile_labels)
    attack_by_decile = (
        df_time.groupby("decile", observed=True)["Label"]
        .agg(attack_count="sum", total="count")
        .assign(attack_pct=lambda x: (x.attack_count / x.total * 100).round(2))
    )
    span_h = (df[_TIME_COL].max() - df[_TIME_COL].min()) / 3.6e6
    print(f"采集时间跨度: {span_h:.1f} 小时（真时间戳，非行序代理）")
    print("攻击随真实时间的分布（D1=最早 10%，D10=最晚 10%）：")
    print(attack_by_decile.to_string())
    print("\n→ 攻击随时间高度不均匀，正是 temporal split 要诚实暴露的：")
    print("  用早期窗口训练、晚期窗口测试，模型会遇到训练时未见的攻击时段分布。")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 修复 3：去泄漏特征 + 时间切分
    """)
    return


@app.cell
def _(d, df, fe, pd):
    TIME_COL = "FLOW_START_MILLISECONDS"   # v3 真时间戳 → 真 temporal split
    END_TS   = "FLOW_END_MILLISECONDS"     # 同源绝对时间列，也只用于排序、不进特征

    drop_non_features = [c for c in ["Attack", "Dataset"] if c in df.columns]
    work = df.drop(columns=drop_non_features)
    work = fe.drop_leakage_features(work)  # 移除 IP/端口等身份特征

    for col in work.select_dtypes(include="object").columns:
        if col != "Label":
            work[col] = pd.factorize(work[col])[0]

    # 真 temporal split：按 FLOW_START 排序前 80% 训练；时间戳列排完即剔除（见 src/data.py）
    X_train, X_test, y_train, y_test = d.temporal_split(
        work, time_col=TIME_COL, label_col="Label", extra_drop=[END_TS]
    )

    n_dropped = df.shape[1] - 2 - X_train.shape[1]  # 减 Label/Attack 两非特征列
    print(f"特征数（去 IP/端口 + 去绝对时间戳后）: {X_train.shape[1]}（移除了 {n_dropped} 列：4 身份 + 2 时间戳）")
    print(f"训练集: {X_train.shape}  攻击占比: {y_train.mean():.4f}")
    print(f"测试集: {X_test.shape}   攻击占比: {y_test.mean():.4f}")
    print("→ 训练/测试攻击占比差异来自攻击随真实时间的不均匀分布（真 temporal split 的诚实代价）")
    return TIME_COL, X_test, X_train, y_test, y_train


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 结果：诚实 baseline vs 乐观 baseline

    我们训练**两个**版本，分开两个叙事目的：

    - **vanilla**（无 class_weight）：与 notebook 01 完全相同配置，只有切分策略和特征集不同。
      这是真正的 apples-to-apples 对比，落差纯归因于方法学修复。
    - **balanced**（class_weight="balanced"）：处理类不平衡，把少数类（攻击）的损失权重放大。
      这是部署时的实际选择，服务于下面的 base-rate 误报量分析。

    二者是**独立变量**：「是否用 balanced」是一个部署决策，不应混进「诚实方法学代价」的讨论里。
    """)
    return


@app.cell
def _(LGBMClassifier, SEED, X_test, X_train, accuracy_score, confusion_matrix, ev, y_test, y_train):
    def _eval(clf):
        clf.fit(X_train, y_train)
        proba = clf.predict_proba(X_test)[:, 1]
        pred  = (proba >= 0.5).astype(int)
        metrics = ev.compute_metrics(y_test, pred, proba)
        tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
        metrics["fpr"]      = fp / (fp + tn) if (fp + tn) else 0.0
        metrics["accuracy"] = accuracy_score(y_test, pred)
        return metrics

    m_van = _eval(LGBMClassifier(random_state=SEED, n_jobs=-1))
    m_bal = _eval(LGBMClassifier(random_state=SEED, n_jobs=-1, class_weight="balanced"))

    print("                    macro_f1   pr_auc   attack_recall   fpr")
    print(f"乐观（notebook 01）   1.0000    1.0000     1.0000       —   ← 靠 IP 泄漏")
    print(f"诚实 vanilla         {m_van['macro_f1']:.4f}    {m_van['pr_auc']:.4f}     {m_van['minority_recall']:.4f}    {m_van['fpr']:.4f}")
    print(f"诚实 balanced        {m_bal['macro_f1']:.4f}    {m_bal['pr_auc']:.4f}     {m_bal['minority_recall']:.4f}    {m_bal['fpr']:.4f}")
    return m_bal, m_van


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 关键发现：去掉 IP 泄漏后，诚实版**依然满分**——这才是真正的警讯

    乐观（带 IP）≈ 1.0，诚实（去 IP/端口 + 真 temporal split，仅 47 个可泛化流特征）**也 ≈ 1.0**。
    落差几乎为零。这**不是**「封堵陷阱没用」，而是一个比落差更尖锐的诚实结论：

    1. **IP 泄漏真实存在但被掩盖**：v3 全集只有 40 个 IP，乐观版能把「IP=标签」背到满分；
       但即便把 IP/端口全部移除，**剩下的流统计特征本身就让 UNSW 完美可分**——
       所以「去 IP」带不来可见落差，IP 泄漏的危害在单数据集内看不出来。
    2. **合成 benchmark「太容易」**：UNSW-NB15 由流量生成器合成，攻击工具在
       包长/时序/TTL 等统计上留下系统性指纹，使攻击与良性在 v2/v3 特征下近乎线性可分
       （呼应 `related-work-perspectives.md` 视角 8：合成数据分布显著偏离真实流量）。
    3. **真 temporal split 也没压低分数**：即使用 `FLOW_START_MILLISECONDS` 严格按时间切，
       分数仍满——可分性来自数据集本身，不是 snooping。

    **结论**：单数据集指标（哪怕诚实评估）在这种合成数据上**接近无意义**——满分恰恰是危险信号。
    模型学的是「这个数据集里攻击长什么样」，不是「攻击的本质」。
    **要证伪它，唯一办法是换一个数据集**——见 notebook 04（LODO）。下面先看一个推论：
    既然单数据集 FPR≈0，base-rate 在 UNSW 上**暂时不咬人**，但这正暴露了「在哪测」的重要性。
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Base-Rate 误报量分析（Arp P8：基率谬误）

    base-rate 谬误的机制：测试集攻击占比 5–9%，但真实网络里攻击通常 **< 0.1%**。
    当攻击极稀少时，**只要 FPR 不为零**，海量良性流量就会淹没告警台。
    用 base-rate 公式把模型的 (recall, FPR) 投射到不同攻击占比下：

    > **注意本数据集的特例**：UNSW-v3 上诚实模型 FPR≈0，所以下表里 precision 即使在 0.1%
    > 也仍很高——**base-rate 在 UNSW 上不咬人**。这不是反例，而是说明：base-rate 的杀伤力
    > 取决于模型在**真实部署分布**上的 (recall, FPR)。换到模型没见过的数据集（notebook 04），
    > 实际情况是 **recall 崩到接近 0、PR-AUC 跌向随机基线**——攻击几乎全部漏检，而非 FPR 飙升导致
    > 误报洪流（LODO 的 FPR 实测 0.001–0.023，并不高）。这张表的方法本身才是卖点：
    > 把 (recall, FPR) 投射到真实基率，就能量化「在这个部署环境里，告警里有多少是误报、
    > 有多少攻击被漏掉」——无论具体数字是哪种失败模式。
    """)
    return


@app.cell
def _(ev, m_bal, pd):
    vol = ev.base_rate_alert_volume(recall=m_bal["minority_recall"], fpr=m_bal["fpr"])
    vdf = pd.DataFrame(vol)
    vdf["attack_pct"] = vdf["base_rate"].map(lambda x: f"{x:.1%}")
    vdf["false_alarm_rate"] = (vdf["false_positives"] / vdf["analyst_alerts"] * 100).round(1).astype(str) + "%"
    result = vdf[["attack_pct", "true_positives", "false_positives", "precision", "false_alarm_rate", "analyst_alerts"]]
    result.columns = ["攻击占比", "真阳", "假阳", "precision", "误报率", "分析师告警/百万流"]
    print(result.to_string(index=False))
    print()
    _r = vol[0]  # base_rate=0.1%
    print(f"→ 在 0.1% 攻击占比下：precision={_r['precision']:.3f}，"
          f"每百万流 {_r['analyst_alerts']:,} 条告警、其中 {_r['false_positives']:,} 误报。")
    print(f"  方法学要点：base-rate 把 (recall={m_bal['minority_recall']:.3f}, FPR={m_bal['fpr']:.4f})")
    print( "  投射到真实占比，量化「有多少攻击被漏掉 + 有多少告警是误报」。")
    print( "  本数据集 FPR≈0 故精度仍高；换到 LODO（notebook 04）recall 崩到≈0、")
    print( "  PR-AUC 跌向随机基线——同一张表会揭示漏检率极高。这正是「在哪测」决定「能不能用」。")
    return


@app.cell
def _(DATASET, EXPERIMENTS_CSV, TIME_COL, ev, m_bal, m_van):
    _split = "temporal" if TIME_COL else "temporal_proxy_roworder"
    ev.log_experiment({
        "experiment":      "honest_temporal",
        "dataset":         DATASET,
        "split":           _split,
        "model":           "LightGBM",
        "macro_f1":        m_van["macro_f1"],
        "pr_auc":          m_van["pr_auc"],
        "minority_recall": m_van["minority_recall"],
        "note":            f"leakage dropped; vanilla apples-to-apples; fpr={m_van['fpr']:.4f}",
    }, EXPERIMENTS_CSV)
    ev.log_experiment({
        "experiment":      "honest_temporal_balanced",
        "dataset":         DATASET,
        "split":           _split,
        "model":           "LightGBM(balanced)",
        "macro_f1":        m_bal["macro_f1"],
        "pr_auc":          m_bal["pr_auc"],
        "minority_recall": m_bal["minority_recall"],
        "note":            f"leakage dropped; class_weight=balanced; fpr={m_bal['fpr']:.4f}",
    }, EXPERIMENTS_CSV)
    print(f"已记录 2 行（vanilla + balanced）→ {EXPERIMENTS_CSV}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 汇总：01 vs 03 对比表

    三行讲三个独立的点：

    - 第 1 行 vs 第 2 行：**方法学代价**——去 IP/端口 + 真 temporal split 让数字改变了多少？
      （答：几乎为零，但原因不是「方法学没用」，而是这个合成数据集本身就完美可分，见上）。
    - 第 3 行：**部署杠杆**——class_weight=balanced 在 UNSW 上几乎不改变结果（本就满分）；
      它的取舍要到 FPR 非零的场景才显现。
    - Base-rate 表：**评估方法**——把 precision 放回真实基率语境；本数据集 FPR≈0 故未咬人，
      但这套方法在 LODO 上会把「高性能模型」打回原形。

    **下一步**：notebook 04 做跨数据集 LODO 测试。
    我们将看到，单数据集满分的模型，换一个数据集就可能跌到随机水平以下——
    这才是「学到攻击本质」还是「背下这个数据集」的真正试金石。
    """)
    return


@app.cell
def _(EXPERIMENTS_CSV, pd):
    res = pd.read_csv(EXPERIMENTS_CSV)
    cols = ["experiment", "split", "macro_f1", "pr_auc", "minority_recall", "note"]
    keep = ["optimistic", "honest_temporal", "honest_temporal_balanced"]
    tbl = res[res.experiment.isin(keep)].drop_duplicates("experiment", keep="last")[cols]
    tbl
    return


@app.cell
def _(m_van, y_test):
    def test_honest_still_separable_within_dataset():
        # 叙事回归（方向性）：去 IP/端口 + 真 temporal split 后，单数据集内诚实模型
        # 仍远超随机基线——锁定「合成数据平凡可分、单数据集指标接近无意义」这一 v3 论点。
        attack_rate = float(y_test.mean())
        assert m_van["pr_auc"] - attack_rate > 0.5
    return


if __name__ == "__main__":
    app.run()
