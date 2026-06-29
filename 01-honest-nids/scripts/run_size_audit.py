"""§2.1 训练量敏感性审计——量化「recall@0.5 脆弱 vs PR-AUC 稳健」(紧范围)。

动机：§2 头条曾称 attack_recall 断崖「对采样鲁棒」。单点对照已证伪（LightGBM,UNSW→ToN,
仅训练量 1M→2.37M 使 recall 0.21→0.0002 而 PR-AUC 仅动 8%）。本脚本把它升级为量化结论：
跨训练量测每格的 recall@0.5 与 PR-AUC，算**变异系数(CV)**，头条数字 = CV(recall) ≫ CV(PR-AUC)。
并检验「PR-AUC 低于随机」这个临界计数稳不稳，及直接给出脆弱性机制。

**审计的是头条 §2 配置**：故**时间戳入特征**（与 run_lodo.py 一致，非 §2.2 scan 的剔除版）——
这样脆弱性结论直接落在头条那张表的 recall 列上。

紧范围（设计取舍见会话记录：不做 4×6×3 全格普查）：
  模型   = LightGBM, LogReg
  数据对 = UNSW→ToN-IoT(recall 刀刃) / CSE-CIC→UNSW(PR-AUC 贴随机) / CSE-CIC→ToN-IoT(高于随机的对照)
  训练量 = 0.5M / 1M / 2M / 3M（UNSW 在 2.37M 自然饱和；3M=头条 cap，避开 CSE-CIC 20M 全量 OOM）
  重复   = 1M 处额外 2 个 seed（同样大小、不同抽样，直击「对采样鲁棒吗」）
  测试集 = 固定 1M（隔离训练量为唯一自变量）
每格记：recall@0.5 / PR-AUC / 真阳性流预测概率∈[0.4,0.5) 占比(机制) / FPR。
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from config import DATA_DIR, RESULTS_DIR, SEED, seed_everything
from src import data as d
from src import evaluation as ev
from src import feature_engineering as fe
from src.models import build_models

seed_everything()

DS_FILES = {
    "UNSW":    "NF-UNSW-NB15-v3",
    "ToN-IoT": "NF-ToN-IoT-v3",
    "CSE-CIC": "NF-CSE-CIC-IDS2018-v3",
}
PAIRS = [("UNSW", "ToN-IoT"), ("CSE-CIC", "UNSW"), ("CSE-CIC", "ToN-IoT")]
SIZES = [500_000, 1_000_000, 2_000_000, 3_000_000]
SEEDS_AT_1M = [SEED, 1, 2]   # 同样大小、不同抽样
TEST_CAP = 1_000_000

AUDIT_CSV = RESULTS_DIR / "size_audit.csv"
FIELDS = ["source", "target", "model", "train_size", "seed",
          "recall", "pr_auc", "frac_proba_40_50", "fpr", "random_baseline"]
AUDIT_MODELS = ["LightGBM", "LogReg"]


def find_dataset(name: str) -> Path:
    for ext in [".parquet", ".csv"]:
        p = DATA_DIR / f"{name}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"{name} not found in {DATA_DIR}")


def prep(df: pd.DataFrame) -> pd.DataFrame:
    """头条口径：去非特征列 + 去 IP/端口；**保留时间戳**（与 run_lodo.py 一致）。"""
    extra = [c for c in ["Attack", "Dataset"] if c in df.columns]
    work = df.drop(columns=extra)
    work = fe.drop_leakage_features(work)
    for col in work.select_dtypes(include="object").columns:
        if col != "Label":
            work[col] = pd.factorize(work[col])[0]
    return work


def cv(vals) -> float:
    """变异系数 std/mean；mean≈0 时返回 nan（recall 全 0 那种退化情形）。"""
    vals = np.asarray(vals, dtype=float)
    m = vals.mean()
    return float(vals.std(ddof=0) / m) if abs(m) > 1e-9 else float("nan")


def main() -> None:
    t0 = time.time()
    # 固定测试集（各 target 只加载一次，1M cap）
    print(f"=== 加载固定测试集（cap={TEST_CAP:,}）===")
    targets_needed = sorted({te for _, te in PAIRS})
    test_sets, baselines = {}, {}
    for te in targets_needed:
        df = d.load_netflow_sampled(find_dataset(DS_FILES[te]), max_rows=TEST_CAP)
        test_sets[te] = prep(df)
        baselines[te] = float(df["Label"].mean())
        print(f"  {te}: {len(df):,} 行, attack%={baselines[te]:.4f}")

    rows = []
    sources_needed = sorted({s for s, _ in PAIRS})
    for src in sources_needed:
        src_pairs = [(s, t) for s, t in PAIRS if s == src]
        for size in SIZES:
            seeds = SEEDS_AT_1M if size == 1_000_000 else [SEED]
            for sd in seeds:
                tload = time.time()
                tr_df = prep(d.load_netflow_sampled(
                    find_dataset(DS_FILES[src]), max_rows=size, seed=sd))
                n = len(tr_df)
                for _, te in src_pairs:
                    te_df = test_sets[te]
                    feats = sorted((set(tr_df.columns) & set(te_df.columns)) - {"Label"})
                    X_tr, y_tr = tr_df[feats], tr_df["Label"]
                    X_te, y_te = te_df[feats], te_df["Label"]
                    for mname in AUDIT_MODELS:
                        clf = build_models()[mname]
                        clf.fit(X_tr, y_tr)
                        proba = clf.predict_proba(X_te)[:, 1]
                        pred = (proba >= 0.5).astype(int)
                        m = ev.compute_metrics(y_te, pred, proba)
                        tn, fp, fn, tp = confusion_matrix(y_te, pred, labels=[0, 1]).ravel()
                        pos_proba = proba[y_te.to_numpy() == 1]
                        frac = float(((pos_proba >= 0.4) & (pos_proba < 0.5)).mean()) \
                            if len(pos_proba) else 0.0
                        rows.append({
                            "source": src, "target": te, "model": mname,
                            "train_size": n, "seed": sd,
                            "recall": m["minority_recall"], "pr_auc": m["pr_auc"],
                            "frac_proba_40_50": frac,
                            "fpr": fp / (fp + tn) if (fp + tn) else 0.0,
                            "random_baseline": baselines[te],
                        })
                        print(f"  {src:>8}→{te:<8} {mname:<9} size={n:>9,} seed={sd} "
                              f"recall={m['minority_recall']:.4f} pr_auc={m['pr_auc']:.4f} "
                              f"frac[.4,.5)={frac:.3f}")
                print(f"    ({src}@{size:,} seed={sd} load+fit {time.time()-tload:.0f}s)")

    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    df = pd.DataFrame(rows)

    # ---- 头条：训练量扫描下 CV(recall) vs CV(PR-AUC)（仅 seed=SEED，每对4个量级点）----
    print("\n=== A) 训练量敏感性：CV(recall) vs CV(PR-AUC)（越大越脆）===")
    base = df[df.seed == SEED]
    sens = []
    for (src, te, mname), g in base.groupby(["source", "target", "model"]):
        g = g.sort_values("train_size")
        sens.append({
            "pair": f"{src}→{te}", "model": mname,
            "recall_range": f"{g.recall.min():.4f}–{g.recall.max():.4f}",
            "CV_recall": round(cv(g.recall), 3),
            "pr_auc_range": f"{g.pr_auc.min():.3f}–{g.pr_auc.max():.3f}",
            "CV_pr_auc": round(cv(g.pr_auc), 3),
        })
    print(pd.DataFrame(sens).to_string(index=False))

    # ---- B) 同样 1M、3 seed 的重采样方差 ----
    print("\n=== B) 固定 1M、3 seed 的重采样方差（直击「对采样鲁棒吗」）===")
    g1 = df[df.train_size.between(900_000, 1_100_000)]
    rep = []
    for (src, te, mname), g in g1.groupby(["source", "target", "model"]):
        if g.seed.nunique() < 2:
            continue
        rep.append({
            "pair": f"{src}→{te}", "model": mname,
            "recall_seeds": ", ".join(f"{v:.4f}" for v in g.sort_values('seed').recall),
            "CV_recall": round(cv(g.recall), 3),
            "pr_auc_seeds": ", ".join(f"{v:.3f}" for v in g.sort_values('seed').pr_auc),
            "CV_pr_auc": round(cv(g.pr_auc), 3),
        })
    print(pd.DataFrame(rep).to_string(index=False))

    # ---- C) PR-AUC「低于随机」计数随训练量是否翻转 ----
    print("\n=== C) PR-AUC vs 随机基线：是否随训练量翻转 below/above ===")
    flip = []
    for (src, te, mname), g in base.groupby(["source", "target", "model"]):
        g = g.sort_values("train_size")
        signs = (g.pr_auc < g.random_baseline).tolist()
        flip.append({
            "pair": f"{src}→{te}", "model": mname,
            "baseline": round(g.random_baseline.iloc[0], 3),
            "below_random_by_size": "".join("▼" if s else "▲" for s in signs),
            "stable": "是" if len(set(signs)) == 1 else "⚠️翻转",
        })
    print(pd.DataFrame(flip).to_string(index=False))

    print(f"\n写入 {len(rows)} 行 → {AUDIT_CSV}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
