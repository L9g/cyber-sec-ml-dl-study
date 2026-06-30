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

    > **本系列：01 故意踩坑 → 02 IP 泄漏机制 → 03 诚实单数据集 → 04（本文）跨数据集泛化测试**

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
        # 删 IP/端口（身份/环境特征）+ 绝对时间戳（编码采集时段，不可跨数据集迁移）
        work = fe.drop_leakage_features(work, extra=fe.NETFLOW_ABSOLUTE_TIMESTAMP_FEATURES)
        for col in work.select_dtypes(include="object").columns:
            if col != "Label":
                work[col] = pd.factorize(work[col])[0]
        return work

    prepped = {k: prep(v) for k, v in dfs.items()}
    feat_sets = [set(v.columns) - {"Label"} for v in prepped.values()]
    shared_feats = sorted(set.intersection(*feat_sets))
    all_same = all(s == feat_sets[0] for s in feat_sets)
    print(f"去泄漏后特征数（去 IP/端口 + 去绝对时间戳）: {len(shared_feats)}  |  三数据集特征集一致: {all_same}")
    print("（三个数据集都来自 NetFlow-v3 统一特征体系，特征列应完全相同）")

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
    ## 关键发现：跨数据集 PR-AUC 量级崩塌（recall 已降级）

    **稳健头条 = 量级落差**：分布内 PR-AUC/macro-F1 ≈ 1.0（§1，合成数据平凡可分）；6 对跨数据集
    PR-AUC 全部远离 1.0、崩向各自测试集的随机基线（=攻击占比，[[feedback-pr-auc-imbalanced]]）——
    尤其测低基率集（UNSW，基线 0.054）时全部贴/低于随机。macro-F1 也全面跌到 0.38–0.49（≈二分类随机）。

    > ⚠️ **指标降级（与 `reports/findings.md` §2.1 一致）**：旧版以「attack_recall 断崖 ≤3%」为头条。
    > 训练量敏感性审计证明 recall@0.5 **采样脆弱**（固定 1M 换 seed 即摆 8×）、且其崩塌**非阈值刀刃**
    > （攻击流概率被自信压到 0.4 以下，调阈值救不回）；「N/6 低于随机」这个二元计数也随训练量翻转。
    > 故下表 recall / Δ / 「是否低于随机」三列仅作**观察**，**卖点改押 PR-AUC 量级落差**，不押精确计数。
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
    **没有任何跨集对的 PR-AUC 接近分布内 ~1.0（实测 max≈0.79），6 对均值≈0.30，崩向随机。**
    模型在外部数据集上检测能力大幅退化；卖点是这个**量级落差**，不是某个固定阈值下的 recall 数字。

    ---

    ## 为什么会这样？—— 特征分布漂移为主，基率/阈值偏移为辅

    主因是**特征分布漂移**：跨数据集的流统计分布不同，模型学到的是「这个网络/这套合成工具的指纹」，
    不是可迁移的攻击特征（Arp P9 lab-only：同分布的「完美」不预测真实部署）。
    基率/阈值偏移是**次因**——§2.1 审计显示 recall 崩塌时攻击流概率被**自信压到 0.4 以下**（非堆在 0.49），
    说明不是单纯「阈值太保守」、调阈值救不回，而是分布漂移下评分的整体重组。

    ---

    ## 与 notebook 03 的结论如何衔接

    - notebook 03：单数据集内，去 IP/端口 + 真 temporal split 后诚实 baseline 仍**满分**（PR-AUC≈1.0）。
    - notebook 04：换一个数据集，PR-AUC 崩向随机基线、macro-F1 跌到 ≈0.4；且（§2.2 P6）**四个模型族一起崩**。

    两者**不矛盾**：单数据集满分是合成数据的可分性（连单特征 stump 都 ≈1.0，§2.2），不是检测能力的证明。
    这正是本项目的诚实论点——**刻意暴露实验室数字与真实部署之间的断层**。

    ---

    ## 对实践的启示

    1. **单一数据集的结果不可外推**：发论文要做 LODO（或至少报告多数据集结果）。
    2. **不平衡数据优先阈值无关 + rank-based 指标（PR-AUC）并给随机基线**：操作点指标（recall@固定阈值）
       在评分稀疏区采样脆弱（§2.1），不可作头条；连 PR-AUC 自己贴基线处也会抖，需诚实标注。
    3. **加模型容量救不回**：换 LogReg/MLP/单特征 stump 一起崩（§2.2），失败根因是评估/数据不是模型。
    4. **class_weight 不解决跨数据集问题**：它调阈值，但改变不了特征空间的分布漂移。
    """)
    return


@app.cell
def _(lodo_df):
    # 叙事回归（方向性，margin-vs-noise）——断言只押**稳健信号 = 分布内→跨集的量级落差**。
    # 锚点：分布内 macro-F1/PR-AUC ≈ 1.0（§1，结构性、对种子鲁棒）。
    # ⚠️ 刻意**不**对 recall@0.5 与「N/6 低于随机」计数设断言：§2.1 训练量敏感性审计证明二者
    #    采样脆弱（固定 1M 换 seed，recall 摆 8×；below-random 二元判定随训练量翻转），
    #    押它们会随 LightGBM 版本/种子漂移而误报。recall 仅作打印观察（上面表格），不进 CI 闸门。

    def test_macro_f1_collapses_from_indist():
        # 分布内≈1.0 → 跨集应跌向随机(~0.5)。<0.75 既远低于 1.0 锚点、又高于实测 max(~0.49)，双向 margin 足。
        assert lodo_df["macro_f1"].max() < 0.75

    def test_pr_auc_magnitude_collapses():
        # 稳健头条（量级，非计数）：没有任何跨集对的 PR-AUC 接近分布内 ~1.0（实测 max≈0.79，CSE→ToN）；
        # 且 6 对均值远低于 1.0（实测≈0.30）。两条都对种子/版本鲁棒。
        assert lodo_df["pr_auc"].max() < 0.9
        assert lodo_df["pr_auc"].mean() < 0.6

    def test_to_low_base_rate_target_pr_auc_near_random():
        # 测低基率集（UNSW，基线 0.054）时 PR-AUC 崩到随机附近——方向稳健（vs 分布内 1.0，margin 极大）。
        to_unsw = lodo_df.loc[lodo_df["test"] == "UNSW", "pr_auc"]
        assert to_unsw.max() < 0.2
    return


@app.cell
def _(EXPERIMENTS_CSV):
    def test_p6_collapse_is_model_invariant():
        # §2.2 P6 / Layeghy A2：崩塌跨模型族成立。对 scripts/run_model_scan.py 的产物做方向性回归。
        # 路径用 EXPERIMENTS_CSV.parent（=RESULTS_DIR，config.py 的 __file__ 锚定）——
        # ⚠️ 不用 mo.notebook_dir()：它在 pytest 下退化为 CWD，会把 results/ 指错（见 skill
        # anchor-paths-to-file-not-cwd）。注意 P6 用 **PR-AUC 均值**而非 macro-F1——后者在高基率目标上
        # 被简单模型的高 FPR 冲高（stump 跨集 macro-F1 可达 0.83），非模型不变；PR-AUC 才稳。
        import pandas as pd
        import pytest

        p = EXPERIMENTS_CSV.parent / "model_scan.csv"
        if not p.exists():
            pytest.skip("先跑 scripts/run_model_scan.py 生成 results/model_scan.csv")
        s = pd.read_csv(p)
        ind_unsw = s[(s["mode"] == "indist") & (s["train"] == "UNSW")]
        lodo = s[s["mode"] == "lodo"]
        # ① 分布内 UNSW：每个模型族都≈满分（连单特征 stump 0.998）——benchmark 平凡可分
        assert ind_unsw["macro_f1"].min() > 0.9
        # ② 跨数据集：没有任何模型族的 6 对 PR-AUC 均值接近其分布内 ~1.0（实测各模型≈0.25–0.31）
        assert lodo.groupby("model")["pr_auc"].mean().max() < 0.6
    return


if __name__ == "__main__":
    app.run()
