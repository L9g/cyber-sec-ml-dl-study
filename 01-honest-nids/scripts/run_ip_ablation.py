"""§1.1 IP 泄漏消融——把「IP 泄漏存在但被掩盖」量化成机制证据（Arp P4 spurious correlation）。

困境（findings §1）：UNSW-v3 合成数据平凡可分，keep-IP 与 drop-IP 在分布内**都满分**，
所以标准设定看不出 IP 的边际贡献。本脚本用两条正交证据把 IP 的角色拆出来：

  路B「IP 是充分的——但靠记忆」：UNSW-v3 仅 40 个 src IP、每个 IP 100% 对应单一 label
  （IP→label 是确定性查找表）。故 **IP-only 模型在随机切分下就该 ≈满分**——纯背诵，不是检测。

  路A「IP 不可迁移」：同一 IP-only 模型在 temporal split / 跨数据集 LODO 下应崩塌
  （IP 不随时间/网络迁移）。并对照 full-keep-IP vs full-drop-IP：在分布内饱和（无落差=掩盖），
  在 LODO 看 IP 到底帮忙还是帮倒忙。

变量 = 特征集{IP-only, full-keep-IP, full-drop-IP} × 切分{random, temporal, LODO→ToN, LODO→CSE}，
模型固定 LightGBM（多模型鲁棒性是 §2.2 的事，这里只动特征/切分）。

⚠️ factorize 口径：单数据集内（random/temporal）**整表一次性 factorize**，train/test 共享 IP 码空间
（才可能记忆）；LODO 下 train(UNSW)/test(ToN,CSE) **各自独立 factorize**——整数码各自从 0 排，无
共享语义。IP 地址是网络本地身份空间，不存在跨数据集共享命名空间；无论编码方式（独立整数码 /
OHE-unknown / 直接丢弃），IP-only 模型在 LODO 条件下均无可迁移信号（§OHE 段用
OHE(handle_unknown="ignore") 对照验证：两条路结论一致，机制不同）。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

from config import DATA_DIR, SEED, seed_everything
from src import data as d
from src import evaluation as ev
from src import feature_engineering as fe

seed_everything()

DS = {"UNSW": "NF-UNSW-NB15-v3", "ToN-IoT": "NF-ToN-IoT-v3", "CSE-CIC": "NF-CSE-CIC-IDS2018-v3"}
TS = ["FLOW_START_MILLISECONDS", "FLOW_END_MILLISECONDS"]
IPPORT = ["IPV4_SRC_ADDR", "IPV4_DST_ADDR", "L4_SRC_PORT", "L4_DST_PORT"]
IP_ONLY = ["IPV4_SRC_ADDR", "IPV4_DST_ADDR"]
TEST_CAP = 1_000_000


def find(name):
    for ext in (".parquet", ".csv"):
        p = DATA_DIR / f"{name}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(name)


def factorize_objects(df):
    """整表 factorize（object→int 码）。在单数据集内调用前请保证 train/test 同源。"""
    out = df.copy()
    for c in out.select_dtypes(include="object").columns:
        if c != "Label":
            out[c] = pd.factorize(out[c])[0]
    return out


def feat_cols(df, policy):
    """按特征集 policy 返回特征列（不含 Label/时间戳）。"""
    base = [c for c in df.columns if c not in (["Label", "Attack", "Dataset"] + TS)]
    if policy == "ip_only":
        return [c for c in IP_ONLY if c in df.columns]
    if policy == "full_keep_ip":
        return base
    if policy == "full_drop_ip":
        return [c for c in base if c not in IPPORT]
    raise ValueError(policy)


def evaluate(clf, X_te, y_te):
    proba = clf.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    m = ev.compute_metrics(y_te, pred, proba)
    tn, fp, fn, tp = confusion_matrix(y_te, pred, labels=[0, 1]).ravel()
    m["fpr"] = fp / (fp + tn) if (fp + tn) else 0.0
    m["accuracy"] = accuracy_score(y_te, pred)
    return m


def main():
    t0 = time.time()
    print("=== 加载 UNSW-v3 全量（展品）===")
    unsw_raw = d.load_netflow(find(DS["UNSW"]))  # 2.37M, 100MB, 直接全量
    print(f"  UNSW: {len(unsw_raw):,} 行, attack%={unsw_raw['Label'].mean():.4f}")

    # 路B 机制：IP 基数 + label 纯度
    nip = unsw_raw["IPV4_SRC_ADDR"].nunique()
    g = unsw_raw.groupby("IPV4_SRC_ADDR")["Label"].agg(["mean", "size"])
    pure_frac = g.loc[g["mean"].isin([0.0, 1.0]), "size"].sum() / g["size"].sum()
    print(f"  [路B] 唯一 src IP={nip}；行落在纯-IP（全同 label）占比={pure_frac:.4f}")
    print(f"        → IP→label 近乎确定性查找表，IP-only 在随机切分下应≈满分（记忆而非检测）\n")

    unsw = factorize_objects(unsw_raw)
    results = []

    def log(policy, split, m, note=""):
        results.append({"policy": policy, "split": split,
                        "macro_f1": m["macro_f1"], "pr_auc": m["pr_auc"],
                        "recall": m["minority_recall"], "fpr": m["fpr"],
                        "accuracy": m["accuracy"], "note": note})
        print(f"  {policy:<13} {split:<14} acc={m['accuracy']:.4f} f1={m['macro_f1']:.4f} "
              f"pr_auc={m['pr_auc']:.4f} recall={m['minority_recall']:.4f} fpr={m['fpr']:.4f}")

    # 预载 LODO 测试集（各 1M）：保留原始字符串 IP 供 OHE；factorize 版供主实验
    lodo_raws_str = {}  # 原始数据（字符串 IP），供 §OHE 使用
    lodo_tests = {}     # factorize 整数码，供主实验使用
    for te in ("ToN-IoT", "CSE-CIC"):
        _raw = d.load_netflow_sampled(find(DS[te]), max_rows=TEST_CAP)
        lodo_raws_str[te] = _raw
        lodo_tests[te] = factorize_objects(_raw)

    for policy in ("ip_only", "full_keep_ip", "full_drop_ip"):
        cols = feat_cols(unsw, policy)
        print(f"--- {policy}  ({len(cols)} 特征) ---")

        # 1) 随机切分（同源，共享 IP 码 → 可记忆）
        Xtr, Xte, ytr, yte = train_test_split(
            unsw[cols], unsw["Label"], test_size=0.2,
            stratify=unsw["Label"], random_state=SEED)
        clf = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(Xtr, ytr)
        log(policy, "random", evaluate(clf, Xte, yte))

        # 2) 真 temporal split（同源）——检验 IP 记忆是否被时间切分打破
        sub = unsw[cols + ["Label"] + TS]
        Xtr, Xte, ytr, yte = d.temporal_split(
            sub, time_col=TS[0], label_col="Label", extra_drop=[TS[1]])
        clf = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(Xtr[cols], ytr)
        log(policy, "temporal", evaluate(clf, Xte[cols], yte))

        # 3) LODO（train UNSW 全量；test ToN/CSE 独立 factorize → IP 码无意义）
        clf = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(unsw[cols], unsw["Label"])
        for te, te_df in lodo_tests.items():
            te_cols = feat_cols(te_df, policy)
            # 对齐列（drop-IP/full 下三数据集列名一致；ip_only 同名）
            shared = [c for c in cols if c in te_df.columns]
            m = evaluate(clf if shared == cols else
                         LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(
                             unsw[shared], unsw["Label"]),
                         te_df[shared], te_df["Label"])
            log(policy, f"LODO→{te}", m, note=f"feats={len(shared)}")

    # === §S CSE-CIC 采样稳定性（ip_only factorize LODO）===
    # 检验 PR-AUC≈0.22 是否随 1M 采样种子漂移。若多 seed 均稳定高于基线（~0.13），
    # 说明独立 factorize 引入了真实的序数相关（不是纯噪声）——需用 §OHE 正面封堵。
    print("\n=== §S CSE-CIC 采样稳定性（ip_only factorize）===")
    _cols_ip = [c for c in IP_ONLY if c in unsw.columns]
    _clf_ip_stability = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(
        unsw[_cols_ip], unsw["Label"])
    _stability_aucs = []
    for _s in (42, 0, 123, 7):
        _te_stab = factorize_objects(
            d.load_netflow_sampled(find(DS["CSE-CIC"]), max_rows=TEST_CAP, seed=_s))
        _proba_stab = _clf_ip_stability.predict_proba(_te_stab[_cols_ip])[:, 1]
        _auc_stab = average_precision_score(_te_stab["Label"], _proba_stab)
        _base_stab = _te_stab["Label"].mean()
        print(f"  seed={_s}: PR-AUC={_auc_stab:.4f}  baseline={_base_stab:.4f}  delta={_auc_stab-_base_stab:+.4f}")
        _stability_aucs.append(_auc_stab)
    print(f"  → range {min(_stability_aucs):.4f}–{max(_stability_aucs):.4f}（{'稳定高于' if all(a > 0.15 for a in _stability_aucs) else '部分低于'}基线 ~0.13）")

    # === §OHE ip_only_ohe：封堵「独立 factorize = 编码伪影」追问 ===
    # 目标 IP 在 UNSW 训练集里全部未见 → OHE 映射为零向量 → 模型无特征信号 →
    # PR-AUC 应退化到目标数据集随机基线（攻击占比）。两条路结论一致，机制不同：
    #   独立 factorize → 序数噪声（有时 > 基线）；OHE-unknown → 零向量（恒 ≈ 基线）。
    print("\n=== §OHE ip_only_ohe（OHE handle_unknown='ignore'）===")
    _ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    _X_unsw_ohe = _ohe.fit_transform(unsw_raw[IP_ONLY].astype(str))
    _clf_ohe = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(
        _X_unsw_ohe, unsw_raw["Label"])
    for _te_name, _te_raw in lodo_raws_str.items():
        _X_te_ohe = _ohe.transform(_te_raw[IP_ONLY].astype(str))
        _m_ohe = evaluate(_clf_ohe, _X_te_ohe, _te_raw["Label"])
        log("ip_only_ohe", f"LODO→{_te_name}", _m_ohe, note="OHE unknown→零向量")
        print(f"    随机基线={_te_raw['Label'].mean():.4f}  PR-AUC={_m_ohe['pr_auc']:.4f}"
              f"  delta={_m_ohe['pr_auc']-_te_raw['Label'].mean():+.4f}")

    out = pd.DataFrame(results)
    out_csv = DATA_DIR.parent / "results" / "ip_ablation.csv"
    out.to_csv(out_csv, index=False)

    print("\n=== 汇总（acc / PR-AUC，按 policy×split）===")
    piv = out.pivot_table(index="policy", columns="split", values="pr_auc")
    piv = piv.reindex(index=["ip_only", "full_keep_ip", "full_drop_ip"],
                      columns=["random", "temporal", "LODO→ToN-IoT", "LODO→CSE-CIC"])
    print("PR-AUC:\n", piv.round(4).to_string())
    print(f"\n写入 {len(results)} 行 → {out_csv}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
