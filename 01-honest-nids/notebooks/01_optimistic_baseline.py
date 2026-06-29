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
    # 01 · 乐观 Baseline —— 故意踩两个经典陷阱

    > **本系列共四个 notebook，构成一条完整的「先踩坑 → 逐一封堵 → 测泛化」叙事。**
    > 01（本文）= 故意制造虚高 → 03 = 诚实单数据集 → 04 = 跨数据集泛化测试

    ---

    ## 背景：为什么 ML-based NIDS 的数字不可轻信

    基于机器学习的网络入侵检测（NIDS）在论文里常见 accuracy > 99%、F1 > 0.98。
    这些数字看着漂亮，但 Arp et al.（2022）系统性地复现了 30 篇顶会论文后发现：
    **绝大多数虚高来自可重复的方法学错误**，而非真实的检测能力。

    本 notebook 刻意重现其中最常见的两个：

    | 陷阱 | 问题 | Arp 编号 |
    |---|---|---|
    | **随机切分** | 同一攻击会话的流同时出现在训练集和测试集（temporal snooping） | P3 |
    | **保留身份特征** | IP 地址/端口直接编码了「攻击机 → 受害机」的关系（捷径学习） | P4 |

    > **数据基座已是 NetFlow v3**（含真 IP + 真时间戳，见 `reports/data-prep-v3.md`）。
    > 与旧 v2 镜像最大的不同：**IP 列真实存在**，乐观版可以拿到「攻击机固定 IP」这个最直接的捷径——
    > 这正是 v2 镜像（IP 被预删）演示不了的。

    我们先拿到虚高的数字，notebook 03 再逐一封堵，看落差有多大。
    """)
    return


@app.cell
def _(mo):
    import sys
    sys.path.append(str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.metrics import accuracy_score

    from config import SEED, seed_everything, EXPERIMENTS_CSV, DATA_DIR
    from src import data as d
    from src import evaluation as ev

    seed_everything()
    return (
        DATA_DIR,
        EXPERIMENTS_CSV,
        LGBMClassifier,
        SEED,
        accuracy_score,
        d,
        ev,
        mo,
        np,
        pd,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. 数据集：NF-UNSW-NB15-v3

    **UNSW-NB15** 由澳大利亚 UNSW Canberra 网络安全实验室构造，包含真实良性流量和
    9 类合成攻击（Fuzzers / DoS / Exploits / Generic / Reconnaissance / Backdoor /
    Analysis / Shellcode / Worms）。

    我们用的是 Sarhan/Layeghy/Moustafa/Portmann 将其标准化为 **53 个 NetFlow 特征的 v3 版本**
    （arXiv 2503.04404），含真 IP 与真时间戳。下载来源、溯源核验、去重实测全过程见
    `reports/data-prep-v3.md`。

    | 项目 | 数值 |
    |---|---|
    | 总流量 | 2,365,424 条（未去重，≈原始；v2 镜像为去重后 1.99M） |
    | 攻击占比 | 5.40% |
    | 特征数 | 53（+ Label、Attack 两列） |
    | 关键新特征 | `IPV4_SRC/DST_ADDR`（真 IP）、`FLOW_START/END_MILLISECONDS`（真时间戳）、IAT 统计 |
    | unique 源/目的 IP | **仅 40 / 40**（实验室固定靶机 → IP 是极强捷径） |

    **注意攻击占比仅 5.40%**：这是典型的不平衡安全数据集。
    Accuracy 在这里近乎没有意义——全预测良性就能得到 94.6% accuracy。
    """)
    return


@app.cell
def _(DATA_DIR, d, pd):
    DATASET = "NF-UNSW-NB15-v3"
    df = d.load_netflow(DATA_DIR / f"{DATASET}.parquet")
    print(f"数据集大小: {df.shape}")
    print()

    # 类分布
    dist = df["Label"].value_counts().rename({0: "良性", 1: "攻击"})
    dist_pct = df["Label"].value_counts(normalize=True).rename({0: "良性", 1: "攻击"})
    pd.DataFrame({"行数": dist, "占比": dist_pct.map("{:.2%}".format)})
    return DATASET, df


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. 陷阱一：随机分层切分（Temporal Snooping, P3）

    **问题机制**：一次攻击活动会产生多条连续的网络流
    （如一次端口扫描产生数百条探测流）。随机切分时，同一次攻击的不同流会
    分别落入训练集和测试集。

    模型在训练时「见过」攻击发生时的统计模式，测试时遇到同一攻击的另一批流，
    当然表现很好——但这只是在记忆同一攻击事件，不是泛化到未见过的攻击。

    **正确做法（notebook 03）**：按时间顺序切分，确保测试集只包含训练集时间窗口之后的流量。

    ---

    ## 3. 陷阱二：保留身份/环境特征（Spurious Correlations, P4）

    **问题机制**：实验室数据集的攻击流量往往来自固定的攻击机 IP，
    模型学到「这个 IP / 端口 = 攻击」——但这只在这个实验室环境里成立，
    换一个网络环境就失效了。

    v3 含真 IP（`IPV4_SRC_ADDR` / `IPV4_DST_ADDR`），整个数据集**只有 40 个源 IP / 40 个目的 IP**。
    下面乐观版**故意保留 IP 与端口**（字符串 IP factorize 成整数编码），让模型直接走「IP = 标签」的捷径。

    **正确做法（notebook 03）**：用 `feature_engineering.drop_leakage_features()` 移除 IP/端口等身份特征。
    """)
    return


@app.cell
def _(d, df, pd):
    drop_non_features = [c for c in ["Attack", "Dataset"] if c in df.columns]
    work = df.drop(columns=drop_non_features)

    # 字符串列（v3 的真 IP IPV4_SRC/DST_ADDR）factorize 成整数——乐观版故意保留所有列
    leaky_kept = [c for c in ["IPV4_SRC_ADDR", "IPV4_DST_ADDR", "L4_SRC_PORT", "L4_DST_PORT"] if c in work.columns]
    for col in work.select_dtypes(include="object").columns:
        if col != "Label":
            work[col] = pd.factorize(work[col])[0]

    # 乐观切分：随机分层，攻击比例维持 5.40%
    X_train, X_test, y_train, y_test = d.optimistic_split(work, label_col="Label")
    print(f"训练集: {X_train.shape}  |  测试集: {X_test.shape}")
    print(f"训练集攻击占比: {y_train.mean():.4f}  |  测试集攻击占比: {y_test.mean():.4f}")
    print(f"\n特征数: {X_train.shape[1]}（含身份特征：{leaky_kept}）")
    return X_test, X_train, y_test, y_train


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. 训练 + 评估

    用默认参数 LightGBM——不做任何调参，保持与 notebook 03 完全相同的模型配置，
    让切分策略和特征集成为唯一变量。
    """)
    return


@app.cell
def _(LGBMClassifier, SEED, X_test, X_train, accuracy_score, ev, y_test, y_train):
    model = LGBMClassifier(random_state=SEED, n_jobs=-1)
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    pred  = (proba >= 0.5).astype(int)

    acc = accuracy_score(y_test, pred)
    m   = ev.compute_metrics(y_test, pred, proba)

    print("指标            值        备注")
    print(f"accuracy      {acc:.4f}   ← 在 5.40% 攻击率下几乎无意义（全猜良性=94.6%）")
    print(f"macro-F1      {m['macro_f1']:.4f}   ← 对两个类等权重，比 accuracy 有意义")
    print(f"PR-AUC        {m['pr_auc']:.4f}   ← 随机基线 = 攻击占比 = 0.054，此处远超随机")
    print(f"attack recall {m['minority_recall']:.4f}   ← 攻击类的召回率")
    return acc, m


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. 解读：数字为什么「看起来」很好

    PR-AUC = 0.990，attack recall = 0.972——这些数字确实不差。但它们是被两个机制撑起来的：

    **机制 1 · 随机切分的记忆效应**：
    测试集里有训练集见过的同一次攻击的流。
    模型「记住」了这次攻击的统计模式，而不是学会了泛化的攻击特征。

    **机制 2 · IP / 端口捷径**：
    实验室只有 40 个源 IP / 40 个目的 IP，攻击流来自固定攻击机。模型学到
    「这个 IP（及端口）= 攻击」这条捷径，但这个规则在真实网络里根本不成立——
    换一批 IP 立刻失效。notebook 04 的跨数据集测试会把这层窗户纸捅破。

    **下一步**：notebook 03 用 temporal split + 去泄漏特征重做，
    看数字跌多少；notebook 04 换一个数据集测试，看模型的「泛化能力」。
    """)
    return


@app.cell
def _(DATASET, EXPERIMENTS_CSV, acc, ev, m):
    ev.log_experiment({
        "experiment":      "optimistic",
        "dataset":         DATASET,
        "split":           "random",
        "model":           "LightGBM",
        "macro_f1":        m["macro_f1"],
        "pr_auc":          m["pr_auc"],
        "minority_recall": m["minority_recall"],
        "note":            f"all features incl. leakage; accuracy={acc:.4f}",
    }, EXPERIMENTS_CSV)
    print(f"已记录乐观 baseline → {EXPERIMENTS_CSV}")
    return


@app.cell
def _(m, y_test):
    def test_optimistic_inflated_above_random():
        # 叙事回归（方向性，非硬阈值）：保留 IP/端口的乐观 baseline 远超随机基线
        # （PR-AUC 随机基线 = 测试集攻击占比）。margin 0.5 远大于跨种子/版本噪声。
        attack_rate = float(y_test.mean())
        assert m["pr_auc"] - attack_rate > 0.5
    return


if __name__ == "__main__":
    app.run()
