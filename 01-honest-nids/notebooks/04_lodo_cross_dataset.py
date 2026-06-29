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
    # 04 · LODO 跨数据集泛化矩阵 —— 真正的诚实落差

    > **本系列：01 故意踩坑 → 03 诚实单数据集 → 04（本文）跨数据集泛化测试**

    ---

    ## 核心问题

    notebook 03 的诚实 baseline 在 NF-UNSW-NB15-v3 上**满分**：macro-F1 ≈ 1.0、PR-AUC ≈ 1.0
    （去 IP/端口 + 真 temporal split 后依然如此——因为这个合成数据集本身完美可分）。模型够好了吗？

    **还没有——满分恰恰是危险信号。**

    UNSW-NB15 是一个**特定实验室、特定时段、特定攻击工具**下采集的数据集。
    真实 SOC 运维的网络，流量分布和攻击构成跟这里的测试集完全不同。
    我们需要问：**在另一个网络环境里，这个模型还能用吗？**

    ---

    ## 方法：Leave-One-Dataset-Out (LODO)

    用 NetFlow-**v3** 同一特征体系（53 特征，arXiv 2503.04404）下的三个独立数据集：

    | 数据集 | 来源 | 流量规模 | 攻击占比 | 主要攻击类型 |
    |---|---|---|---|---|
    | NF-UNSW-NB15-v3 | UNSW Canberra 实验室 | 2.37M | **5.4%** | 9 类（DoS、Exploits、Recon...） |
    | NF-ToN-IoT-v3 | UNSW IoT 实验室 | 27.5M | **39.0%** | IoT 设备攻击 |
    | NF-CSE-CIC-IDS2018-v3 | Canadian Institute CIC | 20.1M | **12.9%** | Web 攻击、暴力破解、Bot... |

    三个数据集在不同的网络、不同的年份、不同的攻击场景下采集。
    **攻击占比差异悬殊**（5.4% vs 39.0%）是后面结果的关键解释因素。
    训练/测试时各分层采样至 3M 行（`load_netflow_sampled`，duckdb 在 parquet 层采样防 OOM）。

    LODO 方法：在一个数据集上训练，在另一个数据集上测试（6 个 train→test 对）。
    结果组成 3×3 矩阵，对角线 = 同分布，非对角线 = 跨数据集泛化。
    """)
    return


@app.cell
def _(mo):
    import sys
    sys.path.append(str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.metrics import confusion_matrix

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
        confusion_matrix,
        d,
        ev,
        fe,
        mo,
        np,
        pd,
    )


@app.cell
def _(DATA_DIR, d, pd):
    DS_FILES = {
        "UNSW":    "NF-UNSW-NB15-v3",
        "ToN-IoT": "NF-ToN-IoT-v3",
        "CSE-CIC": "NF-CSE-CIC-IDS2018-v3",
    }

    # v3 的 ToN-IoT 27.5M / CSE-CIC 20M → duckdb 在 parquet 层分层采样至 3M 行（防 OOM、保攻击占比）
    MAX_ROWS = 3_000_000

    def _find(name):
        for ext in [".parquet", ".csv"]:
            p = DATA_DIR / f"{name}{ext}"
            if p.exists():
                return p
        raise FileNotFoundError(f"{name} not found in {DATA_DIR}")

    dfs = {}
    for _key, _fname in DS_FILES.items():
        _df = d.load_netflow_sampled(_find(_fname), max_rows=MAX_ROWS)
        print(f"{_key}: {len(_df):>9,} 行 (cap={MAX_ROWS:,}), attack%={_df['Label'].mean():.4f}")
        dfs[_key] = _df

    dfs, DS_FILES
    return DS_FILES, MAX_ROWS, dfs


@app.cell
def _(dfs, fe, pd):
    def prep(df):
        extra = [c for c in ["Attack", "Dataset"] if c in df.columns]
        work = df.drop(columns=extra)
        work = fe.drop_leakage_features(work)
        for col in work.select_dtypes(include="object").columns:
            if col != "Label":
                work[col] = pd.factorize(work[col])[0]
        return work

    prepped = {k: prep(v) for k, v in dfs.items()}
    feat_sets = [set(v.columns) - {"Label"} for v in prepped.values()]
    shared_feats = sorted(set.intersection(*feat_sets))
    all_same = all(s == feat_sets[0] for s in feat_sets)
    print(f"去泄漏后特征数: {len(shared_feats)}  |  三数据集特征集一致: {all_same}")
    print("（三个数据集都来自 NetFlow-v2 统一特征体系，特征列应完全相同）")

    prepped, shared_feats
    return prepped, shared_feats


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## LODO 训练 + 评估

    对每个训练集：训练一个 vanilla LightGBM（无 class_weight，与 notebook 03 同配置），
    然后在另外两个测试集上分别评估。共 6 个实验，形成 3×3 矩阵的非对角项。

    **注意**：我们不在这里做 class_weight 调整，目的是让「是否泛化」这个问题有干净的答案，
    不被「class_weight 选择」这个独立变量污染。
    """)
    return


@app.cell
def _(DS_FILES, EXPERIMENTS_CSV, LGBMClassifier, SEED, confusion_matrix, ev, pd, prepped, shared_feats):
    lodo_rows = []

    for _train_key, _train_full_name in DS_FILES.items():
        _train_df = prepped[_train_key]
        _X_tr = _train_df[shared_feats]
        _y_tr = _train_df["Label"]

        _clf = LGBMClassifier(random_state=SEED, n_jobs=-1)
        _clf.fit(_X_tr, _y_tr)
        print(f"训练完: {_train_key} ({len(_X_tr):,} 行, attack%={_y_tr.mean():.4f})")

        for _test_key, _test_full_name in DS_FILES.items():
            if _test_key == _train_key:
                continue

            _test_df = prepped[_test_key]
            _X_te = _test_df[shared_feats]
            _y_te = _test_df["Label"]

            _proba = _clf.predict_proba(_X_te)[:, 1]
            _pred  = (_proba >= 0.5).astype(int)

            _metrics = ev.compute_metrics(_y_te, _pred, _proba)
            _tn, _fp, _fn, _tp = confusion_matrix(_y_te, _pred).ravel()
            _fpr = _fp / (_fp + _tn) if (_fp + _tn) else 0.0
            _metrics["fpr"] = _fpr

            print(
                f"  → 测 {_test_key}: macro_f1={_metrics['macro_f1']:.4f}  "
                f"pr_auc={_metrics['pr_auc']:.4f}  "
                f"attack_recall={_metrics['minority_recall']:.4f}  fpr={_fpr:.4f}"
            )

            _tr_abbr = _train_key.lower().replace("-", "_")
            _te_abbr = _test_key.lower().replace("-", "_")
            ev.log_experiment(
                {
                    "experiment":      f"lodo_{_tr_abbr}_to_{_te_abbr}",
                    "dataset":         _test_full_name,
                    "split":           "lodo",
                    "model":           "LightGBM",
                    "macro_f1":        _metrics["macro_f1"],
                    "pr_auc":          _metrics["pr_auc"],
                    "minority_recall": _metrics["minority_recall"],
                    "note":            f"trained on {_train_full_name}; fpr={_fpr:.4f}",
                },
                EXPERIMENTS_CSV,
            )

            lodo_rows.append({
                "train":        _train_key,
                "test":         _test_key,
                "train_dataset": _train_full_name,
                "test_dataset":  _test_full_name,
                **_metrics,
            })

    lodo_df = pd.DataFrame(lodo_rows)
    lodo_df[["train", "test", "macro_f1", "pr_auc", "minority_recall", "fpr"]]
    return (lodo_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 结果：3×3 矩阵（macro-F1）

    对角线参考值来自 notebook 03（UNSW 同分布，macro-F1 ≈ 1.000）。
    非对角线是跨数据集泛化的实际表现——全部跌到 0.38–0.49（约二分类随机水平）。
    """)
    return


@app.cell
def _(DS_FILES, lodo_df, pd):
    _keys = list(DS_FILES.keys())
    matrix = pd.DataFrame("—", index=_keys, columns=_keys)
    matrix.index.name   = "train \\ test"
    matrix.columns.name = ""

    for _, _row in lodo_df.iterrows():
        matrix.loc[_row["train"], _row["test"]] = f"{_row['macro_f1']:.4f}"

    # 在对角线上标注「同分布」参考值
    matrix.loc["UNSW", "UNSW"] = "~1.000 (§03)"
    matrix
    return (matrix,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 关键发现：attack_recall 断崖 + 半数 PR-AUC 在随机基线及以下

    最干净的信号是 **attack_recall**：单数据集内 = 1.000，6 对跨数据集**全部 ≤ 0.031**（多对 ≈ 0）——
    一个在 UNSW 上 100% 检出攻击的模型，换个数据集几乎一个攻击都抓不到。macro-F1 也全面跌到 0.38–0.49。

    **PR-AUC 比 macro-F1 更诚实**：对不平衡数据，PR-AUC 的随机基线不是 0.5，
    而是**测试集的正样本（攻击）占比**（[[feedback-pr-auc-imbalanced]]）。
    下表直接对比实测 PR-AUC 与该测试集的随机基线——**3/6 在随机基线及以下**
    （含 1 对几乎等于随机）。注意即便少数方向 PR-AUC 高于随机（如 CSE→ToN 0.79），recall 仍只有 3%：
    排序略有信号 ≠ 操作点可用。
    """)
    return


@app.cell
def _(dfs, lodo_df, pd):
    # 随机 PR-AUC 基线 = 测试集攻击占比
    random_baselines = {k: round(v["Label"].mean(), 4) for k, v in dfs.items()}

    rows = []
    for _, r in lodo_df.iterrows():
        baseline = random_baselines[r["test"]]
        delta    = r["pr_auc"] - baseline
        rows.append({
            "训练→测试":        f"{r['train']} → {r['test']}",
            "PR-AUC":          round(r["pr_auc"], 4),
            "随机基线":         baseline,
            "Δ vs 随机":        f"{delta:+.4f}",
            "是否低于随机":      "⚠️ 是" if delta < 0 else "—",
            "attack_recall":   round(r["minority_recall"], 4),
            "FPR":             round(r["fpr"], 4),
        })

    pr_table = pd.DataFrame(rows)
    pr_table
    return (pr_table,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **3/6 的 PR-AUC 在随机基线及以下，且 6/6 的 attack_recall ≤ 3%。**
    模型在外部数据集上几乎检不出攻击；半数情况下连排序能力都不比瞎猜强。

    ---

    ## 为什么会这样？—— 阈值/基率偏移 + 特征分布漂移

    一部分来自攻击占比差异（模型把训练集基率当先验）：

    | 训练→测试（攻击率） | 效果 |
    |---|---|
    | **UNSW 5.4% → ToN-IoT 39.0%** | 阈值太保守，attack_recall=0.0002，几乎全部攻击被判良性 |
    | **CSE-CIC 12.9% → UNSW 5.4%** | 阈值偏激进，FPR=0.023（6 对里最高），但仍只抓到 0.9% 攻击 |

    但 v3 上更主要的是**特征分布漂移**：即便阈值合适，跨数据集的流统计分布也不同——
    所以 recall 普遍崩到 ≈0，而不只是阈值问题。模型学到的是「这个网络/这套合成工具的指纹」，
    不是可迁移的攻击特征。这是 Arp P9（lab-only evaluation）的核心机制：
    同分布测试集上的「完美」不能预测真实部署表现。

    ---

    ## 与 notebook 03 的结论如何衔接

    - notebook 03 结论：单数据集内，去 IP/端口 + 真 temporal split 后诚实 baseline 仍**满分**（PR-AUC≈1.0、recall=1.0）。
    - notebook 04 结论：换一个数据集，attack_recall 崩到 ≤3%，3/6 的 PR-AUC 在随机基线及以下。

    这两个结论**不矛盾**。它们共同说明：单数据集的满分是合成数据的可分性，不是检测能力的证明。
    这正是本项目的诚实论点——**我们刻意暴露了实验室数字与真实部署之间的断层**。

    ---

    ## 对实践的启示

    1. **单一数据集的结果不可外推**：发论文时要做 LODO（或至少报告多数据集结果）。
    2. **报告 PR-AUC 要同时给出随机基线**：让读者能判断数字是否有实际意义。
    3. **攻击率是分布外泛化的最大障碍之一**：真实部署需要考虑目标网络的攻击率，
       而不是直接使用实验室调好的阈值。
    4. **class_weight 不解决跨数据集问题**：它调整阈值，但不能改变特征空间的分布漂移。
    """)
    return


@app.cell
def _(lodo_df):
    def test_cross_dataset_recall_collapses():
        # 叙事回归（方向性）：同分布 attack_recall≈1.0（§1），跨数据集应崩塌。
        # 参考锚点是结构性的 ~1.0（合成数据完美可分，对种子鲁棒），故 <0.2 = 不足同分布的 1/5。
        assert lodo_df["minority_recall"].max() < 0.2

    def test_cross_dataset_macro_f1_collapses():
        # 同分布 macro-F1≈1.0；跨数据集应跌向二分类随机水平(~0.5)。<0.7 落在随机与满分之间，
        # 远低于结构性 ~1.0 的同分布参考，margin 充足。
        assert lodo_df["macro_f1"].max() < 0.7
    return


@app.cell
def _(dfs, lodo_df):
    def test_at_least_one_pr_auc_below_random():
        # 核心卖点：存在 train→test 对的 PR-AUC 低于该测试集随机基线(=攻击占比)。
        # 用 >=1（最稳的 ToN→UNSW 实测 Δ≈-0.024）；findings.md 报告的 3/6 是更强但更易漂移的陈述。
        baselines = {k: float(v["Label"].mean()) for k, v in dfs.items()}
        below = sum(r["pr_auc"] < baselines[r["test"]] for _, r in lodo_df.iterrows())
        assert below >= 1
    return


if __name__ == "__main__":
    app.run()
