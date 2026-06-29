"""P6 多算法基线/鲁棒性扫描（可直接 python scripts/run_model_scan.py 执行）。

把 §2 的「LightGBM 跨数据集崩塌」升级为「**所有模型一起崩**」(Arp P6 / Layeghy A2)。
对每个模型（SingleFeature/LogReg/MLP/LightGBM）测两件事：

  1. **分布内（honest temporal）**：在每个数据集自己的真 temporal split 上评估
     → 预期各模型都接近满分（合成 benchmark 平凡可分；单特征 stump 也逼近满分 = P6 反例）。
  2. **跨数据集 LODO**：在一个数据集上训练、在另外两个上测试（6 对）
     → 预期各模型 attack_recall 全部崩到 ≈0。

对照口径：分布内强 vs 跨数据集崩 = 失败根因是评估/数据而非模型容量。

与 §2 头条（run_lodo.py，LightGBM @3M，时间戳入特征）的两点差异（已在 findings 说明）：
  - cap 统一 1M（含 LightGBM 重跑），让四模型表内部可比；方向性结论不受 cap 影响。
  - **绝对时间戳 FLOW_START/END 一律不入特征**（环境标识、不可迁移），与 §3 口径一致——
    §2 头条曾把它们当特征，本扫描修正为剔除。

结果 upsert 进 results/experiments.csv（canonical），并写一份去规范化的
results/model_scan.csv（含 fpr/baseline/mode，便于报告与 notebook 直接出表）。
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sklearn.metrics import confusion_matrix

from config import EXPERIMENTS_CSV, DATA_DIR, RESULTS_DIR, SEED, seed_everything
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

# 四模型表内部可比；cap 统一（含 LightGBM）。方向性结论对 cap 鲁棒（见 findings §2.P6）。
MAX_ROWS = 1_000_000
TIME_COL = "FLOW_START_MILLISECONDS"
END_TS = "FLOW_END_MILLISECONDS"
TRAIN_FRAC = 0.8

SCAN_CSV = RESULTS_DIR / "model_scan.csv"
SCAN_FIELDS = [
    "mode", "model", "train", "test", "macro_f1", "pr_auc",
    "attack_recall", "fpr", "random_baseline", "below_random",
]


def find_dataset(name: str) -> Path:
    for ext in [".parquet", ".csv"]:
        p = DATA_DIR / f"{name}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"{name} not found in {DATA_DIR}")


def prep(df: pd.DataFrame) -> pd.DataFrame:
    """去非特征列 + 去 IP/端口泄漏 + object 列 factorize。保留时间戳列（供切分用）。"""
    extra = [c for c in ["Attack", "Dataset"] if c in df.columns]
    work = df.drop(columns=extra)
    work = fe.drop_leakage_features(work)
    for col in work.select_dtypes(include="object").columns:
        if col != "Label":
            work[col] = pd.factorize(work[col])[0]
    return work


def evaluate(clf, X_te, y_te) -> dict:
    proba = clf.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    m = ev.compute_metrics(y_te, pred, proba)
    tn, fp, fn, tp = confusion_matrix(y_te, pred, labels=[0, 1]).ravel()
    m["fpr"] = fp / (fp + tn) if (fp + tn) else 0.0
    return m


def main() -> None:
    print(f"=== 加载（cap={MAX_ROWS:,}/数据集，时间戳不入特征）===")
    prepped, baselines = {}, {}
    for key, fname in DS_FILES.items():
        df = d.load_netflow_sampled(find_dataset(fname), max_rows=MAX_ROWS)
        prepped[key] = prep(df)
        baselines[key] = float(df["Label"].mean())
        print(f"  {key}: {len(df):>9,} 行, attack%={baselines[key]:.4f}")

    feat_sets = [set(v.columns) - {"Label", TIME_COL, END_TS} for v in prepped.values()]
    shared_feats = sorted(set.intersection(*feat_sets))
    assert all(s == feat_sets[0] for s in feat_sets), "v3 三数据集特征集应一致"
    print(f"  共享特征数（去 IP/端口 + 去绝对时间戳后）: {len(shared_feats)}")

    models = build_models()
    scan_rows = []

    # ---- 1) 分布内：每数据集真 temporal split ----
    print("\n=== 分布内（honest temporal split）===")
    indist = {}  # (ds) -> (X_tr, X_te, y_tr, y_te)
    for ds in DS_FILES:
        X_tr, X_te, y_tr, y_te = d.temporal_split(
            prepped[ds], time_col=TIME_COL, label_col="Label",
            train_frac=TRAIN_FRAC, extra_drop=[END_TS],
        )
        indist[ds] = (X_tr[shared_feats], X_te[shared_feats], y_tr, y_te)

    for name, proto in models.items():
        for ds in DS_FILES:
            X_tr, X_te, y_tr, y_te = indist[ds]
            clf = build_models()[name]  # 全新实例，避免跨拟合状态泄漏
            t = time.time()
            clf.fit(X_tr, y_tr)
            m = evaluate(clf, X_te, y_te)
            print(f"  {name:>20} @ {ds:<8} f1={m['macro_f1']:.4f} "
                  f"pr_auc={m['pr_auc']:.4f} recall={m['minority_recall']:.4f} "
                  f"fpr={m['fpr']:.4f} ({time.time()-t:.0f}s)")
            scan_rows.append({
                "mode": "indist", "model": name, "train": ds, "test": ds,
                "macro_f1": m["macro_f1"], "pr_auc": m["pr_auc"],
                "attack_recall": m["minority_recall"], "fpr": m["fpr"],
                "random_baseline": baselines[ds],
                "below_random": int(m["pr_auc"] < baselines[ds]),
            })
            ev.log_experiment({
                "experiment": f"scan_indist_{ds.lower().replace('-', '_')}",
                "dataset": DS_FILES[ds], "split": "temporal", "model": name,
                "macro_f1": m["macro_f1"], "pr_auc": m["pr_auc"],
                "minority_recall": m["minority_recall"],
                "note": f"P6 scan; honest temporal; cap={MAX_ROWS}; fpr={m['fpr']:.4f}",
            }, EXPERIMENTS_CSV)

    # ---- 2) 跨数据集 LODO：全量训练 → 测另外两个 ----
    print("\n=== 跨数据集 LODO（6 对 × 模型）===")
    for name in models:
        for tr in DS_FILES:
            X_tr = prepped[tr][shared_feats]
            y_tr = prepped[tr]["Label"]
            clf = build_models()[name]
            t = time.time()
            clf.fit(X_tr, y_tr)
            ft = time.time() - t
            for te in DS_FILES:
                if te == tr:
                    continue
                X_te = prepped[te][shared_feats]
                y_te = prepped[te]["Label"]
                m = evaluate(clf, X_te, y_te)
                below = int(m["pr_auc"] < baselines[te])
                print(f"  {name:>20} {tr:>8}→{te:<8} f1={m['macro_f1']:.4f} "
                      f"pr_auc={m['pr_auc']:.4f}(base {baselines[te]:.3f}"
                      f"{' ⚠' if below else ''}) recall={m['minority_recall']:.4f}")
                scan_rows.append({
                    "mode": "lodo", "model": name, "train": tr, "test": te,
                    "macro_f1": m["macro_f1"], "pr_auc": m["pr_auc"],
                    "attack_recall": m["minority_recall"], "fpr": m["fpr"],
                    "random_baseline": baselines[te], "below_random": below,
                })
                ev.log_experiment({
                    "experiment": f"scan_lodo_{tr.lower().replace('-', '_')}_to_"
                                  f"{te.lower().replace('-', '_')}",
                    "dataset": DS_FILES[te], "split": "lodo", "model": name,
                    "macro_f1": m["macro_f1"], "pr_auc": m["pr_auc"],
                    "minority_recall": m["minority_recall"],
                    "note": f"P6 scan; trained on {DS_FILES[tr]}; cap={MAX_ROWS}; "
                            f"fpr={m['fpr']:.4f}",
                }, EXPERIMENTS_CSV)
            print(f"      ({name} fit on {tr}: {ft:.0f}s)")

    # ---- 落盘去规范化扫描表 ----
    SCAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SCAN_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SCAN_FIELDS)
        w.writeheader()
        for r in scan_rows:
            w.writerow(r)

    # ---- 汇总：每模型 分布内 vs 跨数据集 ----
    # 注意：分布内按数据集**分列**报，不取 3 数据集均值——UNSW 平凡可分(≈1.0)而
    # CSE-CIC 的 honest temporal 本身就难(即便 LightGBM recall 也低)，均值会掩盖这点。
    # P6 的锚点是「UNSW 上连单特征 stump 都≈满分」，跨数据集却全崩。
    df = pd.DataFrame(scan_rows)
    is_ind = df["mode"] == "indist"
    is_lod = df["mode"] == "lodo"
    print("\n=== 汇总：分布内(各数据集 macro-F1 / attack-recall) vs 跨数据集(6 对均值) ===")
    summ = []
    for name in models:
        row = {"model": name}
        for ds in DS_FILES:
            r = df[is_ind & (df.model == name) & (df.train == ds)].iloc[0]
            row[f"indist_{ds}"] = f"{r.macro_f1:.3f}/{r.attack_recall:.3f}"
        lod = df[is_lod & (df.model == name)]
        row["lodo_recall_mean"] = round(lod.attack_recall.mean(), 4)
        row["lodo_f1_mean"] = round(lod.macro_f1.mean(), 4)
        row["lodo_below_random"] = f"{int(lod.below_random.sum())}/{len(lod)}"
        summ.append(row)
    print(pd.DataFrame(summ).to_string(index=False))
    print(f"\n写入 {len(scan_rows)} 行 → {SCAN_CSV}  (+ upsert → {EXPERIMENTS_CSV})")


if __name__ == "__main__":
    main()
