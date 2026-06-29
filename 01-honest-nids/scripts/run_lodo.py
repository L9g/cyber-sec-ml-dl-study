"""LODO 跨数据集矩阵 runner（可直接 python scripts/run_lodo.py 执行）。

训练 3 个 LightGBM，各在另外两个数据集上测试，结果 upsert 进 results/experiments.csv。
与 notebooks/04_lodo_cross_dataset.py（marimo 可视化）共享同一 src/ 逻辑。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import confusion_matrix

from config import SEED, seed_everything, EXPERIMENTS_CSV, DATA_DIR
from src import data as d
from src import evaluation as ev
from src import feature_engineering as fe

seed_everything()

# NetFlow v3（含真 IP / 真时间戳 / 未去重，见 reports/data-prep-v3.md）
DS_FILES = {
    "UNSW":    "NF-UNSW-NB15-v3",
    "ToN-IoT": "NF-ToN-IoT-v3",
    "CSE-CIC": "NF-CSE-CIC-IDS2018-v3",
}

# 单数据集行数上限（duckdb 在 parquet 层分层采样，保持 Label 比例且防 OOM）；None = 全量
# v3 的 ToN-IoT(27.5M)/CSE-CIC(20M) 远大于 v2，capped 控制 runtime 与内存
MAX_ROWS = 3_000_000


def find_dataset(name: str) -> Path:
    for ext in [".parquet", ".csv"]:
        p = DATA_DIR / f"{name}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"{name} not found in {DATA_DIR}")


def cap(df: pd.DataFrame, max_rows: int | None, label_col: str = "Label") -> pd.DataFrame:
    if max_rows is None or len(df) <= max_rows:
        return df
    return (
        df.groupby(label_col)
          .sample(frac=max_rows / len(df), random_state=42)
          .reset_index(drop=True)
    )


def prep(df: pd.DataFrame) -> pd.DataFrame:
    extra = [c for c in ["Attack", "Dataset"] if c in df.columns]
    work = df.drop(columns=extra)
    work = fe.drop_leakage_features(work)
    for col in work.select_dtypes(include="object").columns:
        if col != "Label":
            work[col] = pd.factorize(work[col])[0]
    return work


def main() -> None:
    print("=== LODO 数据加载 ===")
    dfs: dict[str, pd.DataFrame] = {}
    for key, fname in DS_FILES.items():
        # 内存安全：在 parquet 层分层采样，避免把 27M 行全读进 pandas
        df = d.load_netflow_sampled(find_dataset(fname), max_rows=MAX_ROWS)
        print(f"  {key}: {len(df):>9,} 行 (cap={MAX_ROWS:,}), attack%={df['Label'].mean():.4f}")
        dfs[key] = df

    print("\n=== 预处理 ===")
    prepped = {k: prep(v) for k, v in dfs.items()}
    feat_sets = [set(v.columns) - {"Label"} for v in prepped.values()]
    shared_feats = sorted(set.intersection(*feat_sets))
    print(f"  共有特征数（去泄漏后）: {len(shared_feats)}")

    print("\n=== LODO 训练 + 评估 ===")
    results = []

    for train_key, train_full in DS_FILES.items():
        tr_df = prepped[train_key]
        X_tr = tr_df[shared_feats]
        y_tr = tr_df["Label"]

        clf = LGBMClassifier(random_state=SEED, n_jobs=-1)
        clf.fit(X_tr, y_tr)
        print(f"\n训练完: {train_key} ({len(X_tr):,} 行)")

        for test_key, test_full in DS_FILES.items():
            if test_key == train_key:
                continue

            te_df = prepped[test_key]
            X_te = te_df[shared_feats]
            y_te = te_df["Label"]

            proba = clf.predict_proba(X_te)[:, 1]
            pred  = (proba >= 0.5).astype(int)

            metrics = ev.compute_metrics(y_te, pred, proba)
            tn, fp, fn, tp = confusion_matrix(y_te, pred).ravel()
            fpr = fp / (fp + tn) if (fp + tn) else 0.0
            metrics["fpr"] = fpr

            print(
                f"  → 测 {test_key}: macro_f1={metrics['macro_f1']:.4f}  "
                f"pr_auc={metrics['pr_auc']:.4f}  "
                f"attack_recall={metrics['minority_recall']:.4f}  fpr={fpr:.4f}"
            )

            tr_abbr = train_key.lower().replace("-", "_")
            te_abbr = test_key.lower().replace("-", "_")
            ev.log_experiment(
                {
                    "experiment":      f"lodo_{tr_abbr}_to_{te_abbr}",
                    "dataset":         test_full,
                    "split":           "lodo",
                    "model":           "LightGBM",
                    "macro_f1":        metrics["macro_f1"],
                    "pr_auc":          metrics["pr_auc"],
                    "minority_recall": metrics["minority_recall"],
                    "note":            f"trained on {train_full}; fpr={fpr:.4f}",
                },
                EXPERIMENTS_CSV,
            )
            results.append({
                "train": train_key,
                "test":  test_key,
                **metrics,
            })

    print("\n=== 3×3 矩阵（macro-F1）===")
    keys = list(DS_FILES.keys())
    matrix = pd.DataFrame("—", index=keys, columns=keys)
    for r in results:
        matrix.loc[r["train"], r["test"]] = f"{r['macro_f1']:.4f}"
    print(matrix.to_string())
    print(f"\n已写入 {len(results)} 行 LODO 实验 → {EXPERIMENTS_CSV}")


if __name__ == "__main__":
    main()
