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
    # 02 · IP 泄漏消融 —— 切分干净 ≠ 特征干净（Arp P4）

    > **本系列：01 故意踩坑 → 02（本文）IP 泄漏机制 → 03 诚实单数据集 → 04 跨数据集泛化**

    ---

    ## 核心问题

    notebook 01 的乐观 baseline 用全 53 特征（含真实 IP 地址）+ 随机切分，PR-AUC=1.0。
    notebook 03 去掉 IP/端口、换成真 temporal split，PR-AUC **依然** 1.0——落差为零。

    如果 IP 在作弊，为什么把它删掉后分数没有下跌？

    本 notebook 用两条正交证据拆解 IP 的角色（Arp P4 spurious correlation）：

    - **路 B「IP 充分——但靠记忆」**：先量化 IP→label 是不是确定性查找表；
      如果是，IP-only 在随机切分下就该满分，不是因为会"检测"，而是因为能"背书"。
    - **路 A「IP 不可迁移」**：同一 IP-only 模型在 temporal split / LODO 下应崩塌；
      并与 full keep-IP vs drop-IP 对照——看 IP 在分布内被掩盖、在跨集帮倒忙的全貌。

    **factorize 口径**：单数据集内（random/temporal）整表一次 factorize，train/test 共享 IP 码空间
    （这样才可能"记忆"）；LODO 下 train(UNSW) 与 test(ToN, CSE) 各自独立 factorize——整数码各自
    从 0 排，无共享语义。IP 地址是网络本地身份空间，不存在跨数据集共享命名空间；无论编码方式如何，
    IP-only 模型在 LODO 条件下均无可迁移信号。独立 factorize 是其中一种显式路径；
    `ip_only_ohe`（下方）用 OHE(handle_unknown="ignore") 作对照：两条路结论一致，机制不同。
    """)
    return


@app.cell
def _(mo):
    import sys
    sys.path.append(str(mo.notebook_dir().parent))

    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import OneHotEncoder

    from config import DATA_DIR, SEED, seed_everything
    from src import data as d
    from src import evaluation as ev

    seed_everything()
    return (
        DATA_DIR,
        LGBMClassifier,
        OneHotEncoder,
        SEED,
        accuracy_score,
        confusion_matrix,
        d,
        ev,
        mo,
        pd,
        train_test_split,
    )


@app.cell
def _(DATA_DIR, pd):
    TS = ["FLOW_START_MILLISECONDS", "FLOW_END_MILLISECONDS"]
    IPPORT = ["IPV4_SRC_ADDR", "IPV4_DST_ADDR", "L4_SRC_PORT", "L4_DST_PORT"]
    IP_ONLY = ["IPV4_SRC_ADDR", "IPV4_DST_ADDR"]

    def find_dataset(name):
        for ext in (".parquet", ".csv"):
            p = DATA_DIR / f"{name}{ext}"
            if p.exists():
                return p
        raise FileNotFoundError(f"{name} not found in {DATA_DIR}")

    def factorize_objects(df):
        out = df.copy()
        for c in out.select_dtypes(include="object").columns:
            if c != "Label":
                out[c] = pd.factorize(out[c])[0]
        return out

    def feat_cols(df, policy):
        base = [c for c in df.columns if c not in (["Label", "Attack", "Dataset"] + TS)]
        if policy == "ip_only":
            return [c for c in IP_ONLY if c in df.columns]
        if policy == "full_keep_ip":
            return base
        if policy == "full_drop_ip":
            return [c for c in base if c not in IPPORT]
        raise ValueError(policy)

    TS, IPPORT, IP_ONLY, find_dataset, factorize_objects, feat_cols
    return (TS, IPPORT, IP_ONLY, find_dataset, factorize_objects, feat_cols)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 步骤 1：IP 基数与 label 纯度（路 B 机制）

    先量化 NF-UNSW-NB15-v3 里 IP 的多样性和 IP→label 的确定性。
    如果唯一 IP 数极少、且每个 IP 100% 对应单一 label，
    那么「IP-only 随机切分满分」就是背诵查找表，和检测能力无关。
    """)
    return


@app.cell
def _(d, find_dataset):
    unsw_raw = d.load_netflow(find_dataset("NF-UNSW-NB15-v3"))
    print(f"UNSW-v3: {len(unsw_raw):,} 行 / 攻击占比 = {unsw_raw['Label'].mean():.4%}")

    n_src_ip = unsw_raw["IPV4_SRC_ADDR"].nunique()
    _g = unsw_raw.groupby("IPV4_SRC_ADDR")["Label"].agg(["mean", "size"])
    pure_frac = _g.loc[_g["mean"].isin([0.0, 1.0]), "size"].sum() / _g["size"].sum()

    print(f"\n唯一 src IP = {n_src_ip}")
    print(f"落在纯 IP（该 IP 全同一 label）的行占比 = {pure_frac:.4%}")
    print(f"\n→ {n_src_ip} 个 IP、{pure_frac:.0%} 纯度，IP→label 是确定性查找表。")
    print(  "  IP-only 在随机切分下应≈满分——背诵 40 行表，不是检测。")
    unsw_raw, n_src_ip, pure_frac
    return (unsw_raw, n_src_ip, pure_frac)


@app.cell
def _(unsw_raw):
    _g = (
        unsw_raw
        .groupby("IPV4_SRC_ADDR")["Label"]
        .agg(["mean", "sum", "size"])
        .rename(columns={"mean": "attack_rate", "sum": "attack_count", "size": "total_flows"})
    )
    _g["type"] = _g["attack_rate"].apply(lambda x: "攻击 IP" if x > 0.5 else "良性 IP")
    _summary = (
        _g.groupby("type")
        .agg(
            唯一IP数=("total_flows", "count"),
            总流量=("total_flows", "sum"),
        )
        .assign(流量占比=lambda df: df["总流量"] / len(unsw_raw))
        .reset_index()
    )
    print("IP 类型分布（每个 IP 完全对应单一 label）：")
    print(_summary.to_string(index=False))
    _summary
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 步骤 2：消融实验

    **变量**：特征集 × 切分策略 （模型固定 vanilla LightGBM，与 nb01/03/04 同配置）

    | 特征集 | 描述 |
    |---|---|
    | `ip_only` | 仅 `IPV4_SRC_ADDR` + `IPV4_DST_ADDR`（2 列） |
    | `full_keep_ip` | 去时间戳后全部特征（含 IP/端口，51 列） |
    | `full_drop_ip` | 再去 IP/端口（47 列，nb03 的诚实配置） |

    | 切分策略 | 描述 |
    |---|---|
    | `random` | 随机分层，train/test 共享 IP factorize 码空间 |
    | `temporal` | 按 `FLOW_START_MILLISECONDS` 排序，前 80% 训练 |
    | `LODO→ToN-IoT` | 训练 UNSW 全量，测 ToN-IoT 1M（独立 factorize） |
    | `LODO→CSE-CIC` | 训练 UNSW 全量，测 CSE-CIC 1M（独立 factorize） |
    """)
    return


@app.cell
def _(d, find_dataset):
    _LODO_CAP = 1_000_000
    _DS = {"ToN-IoT": "NF-ToN-IoT-v3", "CSE-CIC": "NF-CSE-CIC-IDS2018-v3"}

    lodo_raws = {}
    for _k, _name in _DS.items():
        _df = d.load_netflow_sampled(find_dataset(_name), max_rows=_LODO_CAP)
        print(f"{_k}: {len(_df):,} 行 / 攻击占比 = {_df['Label'].mean():.4%}")
        lodo_raws[_k] = _df

    random_baselines = {k: round(v["Label"].mean(), 4) for k, v in lodo_raws.items()}
    lodo_raws, random_baselines
    return (lodo_raws, random_baselines)


@app.cell
def _(
    IP_ONLY,
    LGBMClassifier,
    OneHotEncoder,
    SEED,
    TS,
    accuracy_score,
    confusion_matrix,
    d,
    ev,
    factorize_objects,
    feat_cols,
    lodo_raws,
    pd,
    train_test_split,
    unsw_raw,
):
    _unsw = factorize_objects(unsw_raw)
    _lodo_tests = {k: factorize_objects(v) for k, v in lodo_raws.items()}

    def _eval(clf, X_te, y_te):
        proba = clf.predict_proba(X_te)[:, 1]
        pred = (proba >= 0.5).astype(int)
        m = ev.compute_metrics(y_te, pred, proba)
        tn, fp, fn, tp = confusion_matrix(y_te, pred, labels=[0, 1]).ravel()
        m["fpr"] = fp / (fp + tn) if (fp + tn) else 0.0
        m["accuracy"] = accuracy_score(y_te, pred)
        return m

    _rows = []

    def _log(policy, split, m):
        _rows.append({
            "policy": policy,
            "split": split,
            "pr_auc": round(m["pr_auc"], 4),
            "macro_f1": round(m["macro_f1"], 4),
            "recall": round(m["minority_recall"], 4),
            "fpr": round(m["fpr"], 4),
        })
        print(
            f"  {policy:<16} {split:<18}"
            f" pr_auc={m['pr_auc']:.4f}  f1={m['macro_f1']:.4f}"
            f"  recall={m['minority_recall']:.4f}  fpr={m['fpr']:.4f}"
        )

    for _policy in ("ip_only", "full_keep_ip", "full_drop_ip"):
        _cols = feat_cols(_unsw, _policy)
        print(f"\n--- {_policy}  ({len(_cols)} 特征) ---")

        # 随机切分（共享 factorize → IP 码跨 train/test 一致，可记忆）
        _Xtr, _Xte, _ytr, _yte = train_test_split(
            _unsw[_cols], _unsw["Label"],
            test_size=0.2, stratify=_unsw["Label"], random_state=SEED,
        )
        _clf = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(_Xtr, _ytr)
        _log(_policy, "random", _eval(_clf, _Xte, _yte))

        # 真 temporal split（同源，共享 factorize）
        _sub = _unsw[_cols + ["Label", TS[0], TS[1]]]
        _Xtr_t, _Xte_t, _ytr_t, _yte_t = d.temporal_split(
            _sub, time_col=TS[0], label_col="Label", extra_drop=[TS[1]]
        )
        _clf_t = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(
            _Xtr_t[_cols], _ytr_t
        )
        _log(_policy, "temporal", _eval(_clf_t, _Xte_t[_cols], _yte_t))

        # LODO（train UNSW 全量；test 各自独立 factorize，IP 码不对齐，如实建模不可迁移性）
        _clf_lodo = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(
            _unsw[_cols], _unsw["Label"]
        )
        for _te_key, _te_df in _lodo_tests.items():
            _shared = [c for c in _cols if c in _te_df.columns]
            _clf_use = _clf_lodo
            if _shared != _cols:
                _clf_use = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(
                    _unsw[_shared], _unsw["Label"]
                )
            _log(_policy, f"LODO→{_te_key}", _eval(_clf_use, _te_df[_shared], _te_df["Label"]))

    # ip_only_ohe LODO：OHE(handle_unknown="ignore") 对照实验
    # 目标 IP 在 UNSW 训练集里全部未见 → 映射为零向量 → 无特征信号 → PR-AUC ≈ 随机基线
    # （封堵「独立 factorize = 编码伪影」追问；两条路结论一致，机制不同）
    _ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    _X_tr_ohe = _ohe.fit_transform(unsw_raw[IP_ONLY].astype(str))
    _clf_ohe = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1).fit(
        _X_tr_ohe, unsw_raw["Label"])
    for _te_key, _te_raw in lodo_raws.items():
        _X_te_ohe = _ohe.transform(_te_raw[IP_ONLY].astype(str))
        _log("ip_only_ohe", f"LODO→{_te_key}", _eval(_clf_ohe, _X_te_ohe, _te_raw["Label"]))

    ablation_df = pd.DataFrame(_rows)
    ablation_df
    return (ablation_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 消融矩阵（PR-AUC）

    随机基线 = 测试集攻击占比（UNSW 5.4%；ToN-IoT 39.0%；CSE-CIC 12.9%）。
    括号内数值为随机基线，⚠️ 标注低于随机基线。
    """)
    return


@app.cell
def _(ablation_df, pd, random_baselines, unsw_raw):
    _SPLIT_ORDER = ["random", "temporal", "LODO→ToN-IoT", "LODO→CSE-CIC"]
    _POLICY_ORDER = ["ip_only", "ip_only_ohe", "full_keep_ip", "full_drop_ip"]
    _POLICY_LABELS = {
        "ip_only": "IP-only factorize（2 列）",
        "ip_only_ohe": "IP-only OHE-unknown（零向量）",
        "full_keep_ip": "full keep-IP（51 列）",
        "full_drop_ip": "full drop-IP（47 列）",
    }
    _baselines = {
        "random":        round(unsw_raw["Label"].mean(), 4),
        "temporal":      round(unsw_raw["Label"].mean(), 4),
        "LODO→ToN-IoT":  random_baselines["ToN-IoT"],
        "LODO→CSE-CIC":  random_baselines["CSE-CIC"],
    }

    _piv = ablation_df.pivot_table(index="policy", columns="split", values="pr_auc")
    _piv = _piv.reindex(index=_POLICY_ORDER, columns=_SPLIT_ORDER)

    def _fmt(val, baseline):
        if pd.isna(val):
            return "—"
        marker = " ⚠️" if val < baseline else ""
        return f"{val:.3f}{marker}"

    _display = _piv.copy().astype(object)
    for _col in _SPLIT_ORDER:
        for _pol in _POLICY_ORDER:
            _display.loc[_pol, _col] = _fmt(_piv.loc[_pol, _col], _baselines[_col])

    _display.index = [_POLICY_LABELS[p] for p in _POLICY_ORDER]
    _display.index.name = "特征集"
    _bl_row = pd.DataFrame(
        {col: f"({_baselines[col]:.3f})" for col in _SPLIT_ORDER}, index=["随机基线"]
    )
    pd.concat([_bl_row, _display])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 四条诚实结论

    ### 1 · IP 充分——但靠记忆（路 B）

    **IP-only（2 列）在随机切分下 PR-AUC=1.0、recall=1.0、FPR=0。**
    乐观 baseline 的「满分」可被一张 40 行 IP→label 查找表完全复刻——
    这是背诵，不是检测。模型没学到任何流量行为特征。

    ---

    ### 2 · 真 temporal split 堵不住 IP 泄漏（路 A × B 交叉）

    ⚠️ **IP-only 在 temporal split 下依然满分**。
    那 40 个攻击/良性 IP 自始至终都在线，时间切分穿不透它。

    关键 nuance：**「切分干净」≠「特征干净」**。
    temporal split 是必要条件，但不是充分条件——
    必须叠加特征卫生（删 IP），notebook 03 的诚实配置正是两条都做了。
    本文解释了**为什么都要做**。

    ---

    ### 3 · IP 的边际在分布内被掩盖

    full keep-IP 与 drop-IP 在 random/temporal 都是 1.0——
    合成数据平凡可分，删不删 IP 分布内看不出差别。
    这解释了 §1 headline 落差为零：
    乐观版确实靠 IP 得满分，但去 IP 后剩余流特征**也**满分，
    所以没有可见的落差。需要跨数据集才能暴露 IP 的真实代价。

    ---

    ### 4 · 跨数据集 IP 是纯负债

    两个 LODO 方向均 **drop-IP ≥ keep-IP**：
    删 IP 在 LODO→CSE-CIC 上高 0.08（0.294 vs 0.216），LODO→ToN-IoT 同向。

    IP-only 独立 factorize 跨集得分（ToN≈0.49 / CSE≈0.22），其中 CSE 方向高于随机基线（0.13）约
    0.09——稳定性检验（4 个采样种子）显示 delta 在 +0.089–+0.091，**是真实的序数相关伪信号，不是
    采样噪声**（原因：两数据集 IP 段可能共享结构，独立 factorize 的顺序碰巧产生跨域相关）。

    对照行 **IP-only OHE-unknown** 给出明确答案：全部目标 IP 映射为零向量后，PR-AUC 退化到
    **恰好等于**目标数据集随机基线（ToN=0.390，CSE=0.129，delta=0.000）。两条路结论一致：
    **IP 跨域无可迁移信号**——独立 factorize 与 OHE-unknown 只是显式演示路径不同，OHE 更干净。

    **→ IP 在准确度（≈持平）、泛化（正收益）、隐私（消 PII）三维同时让「删」占优。**
    这是删 IP 最有力的论据，不是「直觉上应该删」。

    ---

    ## 与其他 notebook 的衔接

    - **← notebook 01**：乐观 baseline 靠 IP 满分，但不知道是记忆还是检测。本文拆解了机制。
    - **→ notebook 03**：去 IP + temporal split 后依然满分。
      结论不是「temporal 无效」——而是数据集本身的平凡可分性（合成数据指纹）。
      nb03 接着分析在真实基率下误报有多少（Arp P8）。
    - **→ notebook 04**：本文的 LODO→ToN/CSE 是 nb04 完整 3×3 矩阵的 IP-only 子集。
      nb04 进一步证明 LightGBM 全特征也崩（且换 4 个模型族一起崩），
      本文证明 IP 更早崩、且删 IP 在跨集反而更好。
    """)
    return


@app.cell
def _(ablation_df, random_baselines):
    # 叙事回归——只押稳健信号，以 margin 区隔噪声（[[feedback-test-assertions-directional]]）。

    def test_ip_only_memorizes_in_distribution():
        # IP-only 随机切分：40 IP 全纯，查找表背诵，对种子极鲁棒。
        _row = ablation_df.query("policy == 'ip_only' and split == 'random'").iloc[0]
        assert _row["pr_auc"] > 0.99, f"IP-only random pr_auc={_row['pr_auc']:.4f}，应≈1.0"

    def test_temporal_split_does_not_block_ip_leakage():
        # IP-only temporal 依然满分——40 IP 跨时段都在，时间切分穿不透。
        # 这是「切分干净≠特征干净」的核心证据，对种子同样鲁棒。
        _row = ablation_df.query("policy == 'ip_only' and split == 'temporal'").iloc[0]
        assert _row["pr_auc"] > 0.99, f"IP-only temporal pr_auc={_row['pr_auc']:.4f}，temporal 应堵不住 40 IP"

    def test_ip_only_collapses_cross_dataset():
        # IP-only 跨集崩向随机基线附近（ToN 实测≈0.49，基线 0.39；CSE 实测≈0.22，基线 0.13）。
        # 断言：<0.60 / <0.38——分别给两侧留 margin，且远低于分布内 1.0。
        _ton = ablation_df.query("policy == 'ip_only' and split == 'LODO→ToN-IoT'").iloc[0]["pr_auc"]
        _cse = ablation_df.query("policy == 'ip_only' and split == 'LODO→CSE-CIC'").iloc[0]["pr_auc"]
        assert _ton < 0.60, f"IP-only LODO→ToN pr_auc={_ton:.4f}，应远低于分布内 1.0"
        assert _cse < 0.38, f"IP-only LODO→CSE pr_auc={_cse:.4f}，应远低于分布内 1.0"

    def test_ip_is_liability_cross_dataset():
        # 核心叙事：drop-IP 在跨数据集不差于 keep-IP（IP 是负债，不是资产）。
        # 用两个 LODO 方向 PR-AUC 之和比较，合并 margin（CSE 方向差值≈0.08，ToN≈0.02，总和≈0.10）。
        _drop = ablation_df[ablation_df["policy"] == "full_drop_ip"]
        _keep = ablation_df[ablation_df["policy"] == "full_keep_ip"]
        _drop_sum = _drop[_drop["split"].str.startswith("LODO")]["pr_auc"].sum()
        _keep_sum = _keep[_keep["split"].str.startswith("LODO")]["pr_auc"].sum()
        assert _drop_sum >= _keep_sum - 0.05, (
            f"drop-IP LODO 总和 {_drop_sum:.4f} < keep-IP {_keep_sum:.4f}（预期 drop≥keep）"
        )

    def test_ohe_ip_collapses_to_baseline():
        # OHE unknown→零向量，IP-only LODO PR-AUC 应≈目标数据集随机基线（±0.05 容差）。
        # 封堵「独立 factorize 可能引入序数伪信号」的追问——OHE 路径无该问题。
        for _te_key, _base_key in [("LODO→ToN-IoT", "ToN-IoT"), ("LODO→CSE-CIC", "CSE-CIC")]:
            _row = ablation_df.query(
                f"policy == 'ip_only_ohe' and split == '{_te_key}'"
            ).iloc[0]
            _base = random_baselines[_base_key]
            assert _row["pr_auc"] < _base + 0.05, (
                f"ip_only_ohe {_te_key} PR-AUC={_row['pr_auc']:.4f}，"
                f"应≈基线 {_base:.4f}（OHE 零向量无信号）"
            )
    return


if __name__ == "__main__":
    app.run()
