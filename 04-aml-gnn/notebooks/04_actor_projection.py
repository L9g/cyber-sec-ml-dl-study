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
    # 04 · Transaction score → actor 队列投影 + 标签来源审计

    > 薄切片第二段。把 nb02 的**同一批交易分数**用 **max 聚合**投影到 actor(地址)队列，
    > 问旗舰问题的前半：**scoring granularity vs label provenance**。**只做 max**（其余聚合升档扇出），
    > actor 评估只在 **labeled 地址**上（Setting A；unknown 当 benign 的错误示范 = 下一段 Setting C）。

    ## 三条诚实边界（先说）
    1. **max 下 transaction-first ≡ actor-first**：按 tx 分数降序走、每个地址首次出现即其 max 分，
       故两种队列取到的**地址集合相同（Jaccard=1）**。看点**不在 which-actor、也不是投影损失**（max 下为 0），
       而在 **标签口径**（tx vs wallet 标签体系）；真正的投影损失要到 mean/sum 聚合才非零。
    2. **actor 标签是 retrospective**：`wallets_classes` 一址一枚、无 per-time-step 标签。actor 的
       temporal 结果标 retrospective，**不与 tx temporal 直接同类比**（prevalence 也不同：actor≈8% vs tx≈6.5%）。
    3. **报曲线不报单点**（项目一 §2.1 教训）；`pr_auc − base_rate` 只任务内 sanity。
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

    from config import seed_everything, EXPERIMENTS_CSV, LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN
    from src import data as d
    from src import evaluation as ev
    from src import projection as proj

    seed_everything()

    # 复用 nb02 口径：labeled∩temporal 训练；Time step 不进特征
    full = d.load_tx_graph()
    train_df, test_lab = d.temporal_split(full, train_max_step=34)   # labeled only
    feats = d.feature_columns(full)
    y_train = (train_df["class"] == 1).astype(int)

    model = LGBMClassifier(
        n_estimators=300, learning_rate=0.05, num_leaves=64,
        n_jobs=4, verbose=-1, random_state=42,
    )
    model.fit(train_df[feats], y_train)

    # tx 曲线：labeled 测试交易（同 nb02）
    y_tx = (test_lab["class"] == 1).astype(int).values
    sc_tx = model.predict_proba(test_lab[feats])[:, 1]

    # 投影要用**全部**测试期交易（含 unknown，地址也触 unknown 交易）
    test_all = full[full["Time step"] > 34].copy()
    test_all["score"] = model.predict_proba(test_all[feats])[:, 1]
    return (
        EXPERIMENTS_CSV,
        LABEL_ILLICIT,
        LABEL_LICIT,
        LABEL_UNKNOWN,
        d,
        ev,
        pd,
        plt,
        proj,
        sc_tx,
        test_all,
        y_tx,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Max 投影 → actor 队列（覆盖率 + unknown 缺口）
    """)
    return


@app.cell
def _(LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN, d, ev, mo, proj, test_all):
    # 参与边 = input(AddrTx) ∪ output(TxAddr)，与 wallet illicit 标签同 universe（见 §3 双条件）
    part = d.actor_participation(include_outputs=True)        # [address, txId]
    wc = d.load_wallet_classes()                             # address → class（全局/事后）
    scores = dict(zip(test_all["txId"], test_all["score"]))
    actors = proj.project_scores_to_actors(part, scores, agg="max", addr_col="address").merge(
        wc, on="address", how="left"
    )
    n_all = len(actors)
    n_unknown = int((actors["class"] == LABEL_UNKNOWN).sum())
    lab_act = actors[actors["class"].isin([LABEL_ILLICIT, LABEL_LICIT])].copy()
    y_act = (lab_act["class"] == LABEL_ILLICIT).astype(int).values
    sc_act = lab_act["actor_score"].values
    br_act = ev.base_rate(y_act)

    mo.md(f"""
    投影到 **{n_all:,}** 个测试期**参与地址（input+output）**；其中 **unknown 钱包标签占 {n_unknown / n_all:.1%}**
    （{n_unknown:,} 个）——这批地址在 Setting A 里**被排除**，正是下一段「unknown≠benign 错误示范」的靶。
    labeled 地址 **{len(lab_act):,}** 个，illicit base rate = **{br_act:.1%}**（≠ tx 的 6.5%，故 PR-AUC 不跨任务比）。
    """)
    return actors, br_act, n_unknown, part, sc_act, wc, y_act


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. 两个标签体系下的 yield@budget 对照（不同调查单元/分母，**非配对一致性**）
    """)
    return


@app.cell
def _(ev, mo, pd, sc_act, sc_tx, y_act, y_tx):
    rows = []
    for b in (0.005, 0.01, 0.02, 0.05):
        rt = ev.recall_at_budget(y_tx, sc_tx, b)
        ra = ev.recall_at_budget(y_act, sc_act, b)
        rows.append({"budget": f"{b:.1%}", "tx-yield (illicit tx)": round(rt, 3),
                     "actor-yield (illicit actor)": round(ra, 3),
                     "Δ (tx−actor)": round(rt - ra, 3)})
    tbl = pd.DataFrame(rows)
    d_lo = rows[0]["Δ (tx−actor)"]      # 小预算
    d_hi = rows[-1]["Δ (tx−actor)"]     # 5% 预算
    mo.md(f"""
    同一批分数，**交易队列**（捞 illicit 交易）vs **max 投影的地址队列**（捞 illicit 地址），
    各在**自己的标签体系**里算 recall@budget：

    {mo.ui.table(tbl, selection=None)}

    ⚠️ **这不是「投影损失」，也不是配对一致性**：两条曲线**分母不同、调查单元不同**
    （illicit 交易数 vs illicit 地址数），不可直接比高低。而且 Δ **符号随预算翻转**
    （0.5% 时 {d_lo:+.3f}、5% 时 {d_hi:+.3f}）——若是「聚合造成的产能损失」应单调，翻转说明它只是
    apples-to-oranges 的口径差。**max 下真正的 scoring-granularity/投影损失 ≡ 0**（§5 论证：
    transaction-first 与 actor-first 取到的地址集合相同、Jaccard=1），要到 mean/sum 聚合才非零——留给扇出。
    """)
    return


@app.cell
def _(ev, plt, sc_act, sc_tx, y_act, y_tx):
    xs = [0.5, 1, 2, 5]
    bs = [0.005, 0.01, 0.02, 0.05]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.plot(xs, [ev.recall_at_budget(y_tx, sc_tx, b) for b in bs], marker="o", label="tx queue (illicit tx)")
    ax.plot(xs, [ev.recall_at_budget(y_act, sc_act, b) for b in bs], marker="s", label="actor queue (illicit actor, max-proj)")
    ax.set_xlabel("investigation budget (% of queue)")
    ax.set_ylabel("yield (recall of illicit, own label system)")
    ax.set_title("tx vs actor yield by label system (max-proj, temporal; NOT paired)")
    ax.legend(); ax.grid(alpha=.3); fig.tight_layout()
    fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. ⭐ 标签来源审计：钱包 illicit 标签 = 交易 illicit 标签的确定性传播
    """)
    return


@app.cell
def _(LABEL_ILLICIT, d, mo, part, wc):
    # 双向检验：地址 illicit 是否 <=> 参与过(input 或 output) >=1 illicit 交易。
    # 复用 §1 的 participation（input+output），与投影队列同 universe。
    _txc = d.load_tx_classes()
    txcls = dict(zip(_txc["txId"], _txc["class"]))
    gp = part.assign(is_ill_tx=part["txId"].map(txcls) == LABEL_ILLICIT)
    touches = gp.groupby("address")["is_ill_tx"].any().rename("touches_illicit").reset_index()
    g = touches.merge(wc, on="address", how="left")

    wi = g[g["class"] == LABEL_ILLICIT]
    ti = g[g["touches_illicit"]]
    fwd = wi["touches_illicit"].mean()                 # wallet-illicit ⇒ 触 illicit
    bwd = (ti["class"] == LABEL_ILLICIT).mean()        # 触 illicit ⇒ wallet-illicit
    biconditional = abs(fwd - 1) < 1e-9 and abs(bwd - 1) < 1e-9

    mo.md(f"""
    | 方向 | 命题 | 命中率 |
    |---|---|---|
    | ⇒ | wallet-illicit 地址 **都触过** illicit 交易 | **{fwd:.4f}**（{len(wi):,} 个） |
    | ⇐ | 触过 illicit 交易的地址 **都是** wallet-illicit | **{bwd:.4f}**（{len(ti):,} 个） |

    **双条件成立 = {biconditional}**：`wallet-illicit ⟺ 参与过 ≥1 illicit 交易`，零例外。
    即**钱包 illicit 标签是交易 illicit 标签的确定性 OR/max 传播**（guilt-by-association），且**事后/全局**做的。
    """)
    return biconditional, bwd, fwd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 这条审计对旗舰问句意味着什么（重塑，不预答）

    - **actor 标签不是独立监督**：它就是 tx 标签用 OR/max 抬到实体级。而 actor **分数**（max 投影）
      打在 actor **标签**（= max 投影的 tx 标签）上 → actor 评估本质是**同一个 tx 任务透过 max 算子再看一遍**，
      不是新信号。→ 把「actor-level PR-AUC」当独立检测成绩报是**误导**（继承 tx 标签回溯性 + 与 tx 任务耦合）。
    - **guilt-by-association 的部署隐患**：一笔 illicit 交易把整个地址**永久、全局、事后**染成 illicit——
      收过一次可疑资金的地址就此“有罪”，是 AML 队列的真实 soundness/公平性风险。
    - **对队列不一致的归因**：illicit 类上 tx 与 wallet 标签**构造上不可能冲突**，故本切片的队列不一致
      = **scoring granularity（投影损失，§2）+ unknown 覆盖缺口（§1 的 64%）**，**不是** illicit 的 label-conflict。
      provenance 的病灶落在**回溯性/循环本身**与 licit/unknown 边界——留给归因表 + Setting C 去量化。
    """)
    return


@app.cell
def _(EXPERIMENTS_CSV, br_act, ev, sc_act, y_act):
    # 落盘（upsert）。⚠️ task=actor 的 pr_auc 是 retrospective 且与 tx 不同 prevalence，勿跨任务比。
    ev.log_experiment(
        {
            "experiment": "actor_projection_max", "task": "actor", "split": "temporal",
            "model": "tx-LightGBM→max-proj", "pr_auc": round(ev.pr_auc(y_act, sc_act), 4),
            "base_rate": round(br_act, 4),
            "pr_auc_lift": round(ev.pr_auc(y_act, sc_act) - br_act, 4),
            "recall_at_1pct": round(ev.recall_at_budget(y_act, sc_act, 0.01), 4),
            "n_test": int(len(y_act)),
            "note": "retrospective; Setting A(labeled-only); wallet illicit label = OR-propagation of tx label (guilt-by-assoc); 勿与 tx 同类比",
        },
        EXPERIMENTS_CSV,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 4. Setting C：unknown 当 benign 的错误示范（unknown ≠ benign）""")
    return


@app.cell
def _(LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN, actors, ev, mo, pd, sc_act, y_act):
    # Setting C：把 unknown（连同 licit）都当 benign 负类，评估**全体**地址队列（错误示范）
    yC = (actors["class"] == LABEL_ILLICIT).astype(int).values
    sC = actors["actor_score"].values
    brC = ev.base_rate(yC)
    paA, paC = ev.pr_auc(y_act, sc_act), ev.pr_auc(yC, sC)

    # top-k 全地址队列构成 + A/C 队列内命中率
    srt = actors.sort_values("actor_score", ascending=False, kind="mergesort")
    cls_sorted = srt["class"].values
    n_act = len(actors)
    comp = []
    for bud in (0.005, 0.01, 0.02, 0.05):
        k = max(1, int(round(bud * n_act)))
        top = cls_sorted[:k]
        comp.append({
            "budget": f"{bud:.1%}",
            "illicit": int((top == LABEL_ILLICIT).sum()),
            "licit": int((top == LABEL_LICIT).sum()),
            "unknown": int((top == LABEL_UNKNOWN).sum()),
            "licit%": f"{(top == LABEL_LICIT).mean():.1%}",
            "precA": round(ev.yield_at_budget(y_act, sc_act, budgets=(bud,))[0]["precision"], 3),
            "precC": round(ev.yield_at_budget(yC, sC, budgets=(bud,))[0]["precision"], 3),
        })
    ctbl = pd.DataFrame(comp)
    k5 = max(1, int(round(0.05 * n_act)))
    lic_top_frac = float((cls_sorted[:k5] == LABEL_LICIT).mean())

    mo.md(f"""
    把 {(actors['class'] == LABEL_UNKNOWN).mean():.0%} 的 unknown（连同 licit）都当 benign 负类，评估**全体 {n_act:,} 地址**队列：

    - base rate {ev.base_rate(y_act):.1%}(A) → **{brC:.1%}**(C，被 unknown 稀释)；
      PR-AUC **{paA:.3f}(A) → {paC:.3f}(C)**。

    {mo.ui.table(ctbl, selection=None)}

    **关键：top 队列里 licit 几乎为 0**（5% 预算 licit 仅 {lic_top_frac:.1%}）——
    模型**根本没把 illicit 跟已知 licit 搞混**；Setting C 的 precision「崩」**全部来自 unknown 被记成 FP**。
    而 unknown≠benign：这些高分 unknown 很可能是**未被调查的 illicit**（与 illicit 同信号），无权叫 false positive。
    → **Setting C 的 {paC:.3f} 是 label-coverage 的 artifact、不是模型质量**。正确口径 = A(labeled-only，
    诚实但对覆盖乐观) 或 D(PU-learning / 纯 ranking，把 unknown 当 unlabeled 而非 negative)。
    """)
    return brC, lic_top_frac, paA, paC, sC, yC


@app.cell
def _(EXPERIMENTS_CSV, brC, ev, paC, sC, yC):
    # 落盘（upsert）。⚠️ ERROR-DEMO 行：这个 pr_auc 是 coverage artifact，勿当模型质量报。
    ev.log_experiment(
        {
            "experiment": "actor_maxproj_settingC_unknown_as_benign", "task": "actor",
            "split": "temporal", "model": "tx-LightGBM→max-proj",
            "pr_auc": round(paC, 4), "base_rate": round(brC, 4),
            "pr_auc_lift": round(paC - brC, 4),
            "recall_at_1pct": round(ev.recall_at_budget(yC, sC, 0.01), 4),
            "n_test": int(len(yC)),
            "note": "ERROR-DEMO: unknown 当 benign（selective-labeling 陷阱）；此 pr_auc 是 coverage artifact 非模型质量；对照 Setting A",
        },
        EXPERIMENTS_CSV,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## 5. 归因表雏形：队列不一致按主导成因分类（列联表，**非加法**）""")
    return


@app.cell
def _(LABEL_ILLICIT, LABEL_LICIT, LABEL_UNKNOWN, actors, mo, pd):
    # 列联表：队列位置(top-b) × 钱包标签。每个 actor 落进唯一一格 = 唯一主导成因。
    n_u = len(actors)
    cls5 = actors.sort_values("actor_score", ascending=False, kind="mergesort")["class"].values
    tot_i = int((actors["class"] == LABEL_ILLICIT).sum())
    attr_rows = []
    for bud5 in (0.01, 0.05):
        kk = max(1, int(round(bud5 * n_u)))
        q = cls5[:kk]
        attr_rows.append({
            "budget": f"{bud5:.0%}", "k": kk,
            "TP=illicit在队": int((q == LABEL_ILLICIT).sum()),
            "label-conflict=licit在队": int((q == LABEL_LICIT).sum()),
            "coverage-gap=unknown在队": int((q == LABEL_UNKNOWN).sum()),
            "detection-miss=illicit未进队": tot_i - int((q == LABEL_ILLICIT).sum()),
        })
    atbl = pd.DataFrame(attr_rows)

    kk5 = max(1, int(round(0.05 * n_u)))
    q5 = cls5[:kk5]
    tp_5 = int((q5 == LABEL_ILLICIT).sum())
    fp_licit_5 = int((q5 == LABEL_LICIT).sum())
    cov_unknown_5 = int((q5 == LABEL_UNKNOWN).sum())
    miss_illicit_5 = tot_i - tp_5

    mo.md(f"""
    对**每个只进一队列/被误判的 actor 判一个主导成因**（budget=5%，k={kk5:,}）——队列位置 × 钱包标签列联表：

    | 5% 预算 | wallet-illicit | wallet-licit | wallet-unknown |
    |---|---|---|---|
    | **在队（被调查）** | {tp_5:,} · TP 命中 | **{fp_licit_5} · label-conflict/FP** | **{cov_unknown_5:,} · coverage-gap** |
    | **未进队** | **{miss_illicit_5:,} · detection-miss** | {int((actors['class']==LABEL_LICIT).sum())-fp_licit_5:,} · TN | {int((actors['class']==LABEL_UNKNOWN).sum())-cov_unknown_5:,} · 未标注 |

    两预算汇总：

    {mo.ui.table(atbl, selection=None)}

    三个 off-diagonal 格 = **三种不同性质的失败**，各判一个主导成因，**不相加成「总不一致」**（归因非加法）。
    """)
    return atbl, cov_unknown_5, fp_licit_5, miss_illicit_5


@app.cell(hide_code=True)
def _(cov_unknown_5, fp_licit_5, miss_illicit_5, mo):
    mo.md(f"""
    ### 三个主导成因 + 一条 max 特有的诚实边界（budget=5%）

    - **coverage-gap（unknown 在队，{cov_unknown_5:,}）= 最大成因**：unknown≠benign（§4 的 per-actor 版）。
    - **label-conflict（licit 在队，{fp_licit_5:,}）≈ 0**：score-vs-label 的真冲突极少——呼应 §3 双条件，
      标签体系在 **illicit/licit 边界不冲突**（冲突被搬进了 unknown 这个覆盖洞）。
    - **detection-miss（illicit 未进队，{miss_illicit_5:,}）= 召回侧**。
    - ⚠️ **projection loss = 0 under max（逻辑性质，非经验）**：max 只保留 actor 最好那笔交易的分、**不稀释**，
      故「illicit 未进队」= tx 模型没把它任何一笔打高（**检测**问题），**不是聚合损失**。真正的
      **scoring-granularity / 投影损失要到 mean/sum 聚合才出现** → 留给下一步扇出。
    - ⚠️ **回溯循环**：TP 格的「命中」部分是**循环的**——actor 标签本身是 tx 标签传播（§3），
      不是独立监督确认。故这张表读作**失败模式的定性归因**，不作检测力背书。
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 小结 → 下一步
    - **3 条实腿立住** + 1 条明确推迟：
      ① **标签=tx 标签 guilt-by-association 传播**（§3 provenance，双条件零例外）
      ② **unknown≠benign 错误示范**（§4）
      ③ **队列不一致归因列联表**（§5，非加法，coverage-gap 主导）
      ④ **scoring-granularity / 投影损失 = max 下 null，推迟到 mean/sum**（§2 的 yield 差是口径差、符号还翻转，**不是** loss）。
    - 旗舰问句的诚实答案（当前）：**provenance 是操作轴**（illicit 类无 label-conflict，不一致 = coverage-gap + detection-miss）；
      **granularity 在 max 下不存在**，需 mean/sum 聚合才谈得上。
    - 下一步：**扇出 mean/sum/top-k 聚合**——解除「transaction-first ≡ actor-first」退化、让投影损失非零、
      填上归因表的 projection-loss 格。之后才原生 actor 模型 → Reference 档 GNN。
    """)
    return


@app.cell
def _(biconditional, bwd, fwd):
    def test_wallet_illicit_is_tx_label_propagation():
        # 数据不变量：wallet-illicit ⟺ 参与过 illicit 交易（确定性，非模型分数，故 exact）
        assert biconditional and fwd == 1.0 and bwd == 1.0

    return


@app.cell
def _(ev, sc_act, sc_tx, y_act, y_tx):
    def test_tx_actor_yield_gap_is_not_monotone_loss():
        # 两标签体系 yield 差**符号随预算翻转**（小预算 actor 高、5% tx 高）
        # → 不是单调的「投影损失」，只是不同调查单元/分母的口径差
        g_lo = ev.recall_at_budget(y_tx, sc_tx, 0.005) - ev.recall_at_budget(y_act, sc_act, 0.005)
        g_hi = ev.recall_at_budget(y_tx, sc_tx, 0.05) - ev.recall_at_budget(y_act, sc_act, 0.05)
        assert g_lo < 0 < g_hi

    def test_actor_pr_auc_beats_random_by_margin():
        # actor 队列仍显著优于随机（retrospective 标签下，方向性）
        from src import evaluation as _ev  # noqa
        assert ev.pr_auc(y_act, sc_act) - ev.base_rate(y_act) > 0.3

    return


@app.cell
def _(LABEL_UNKNOWN, actors):
    def test_unknown_wallet_fraction_is_large():
        # unknown 覆盖缺口足够大 → Setting C 有意义（>50%）
        assert (actors["class"] == LABEL_UNKNOWN).mean() > 0.5

    return


@app.cell
def _(lic_top_frac, paA, paC):
    def test_setting_c_fp_are_unknown_not_licit():
        # top 队列里已知 licit 几乎为 0 → Setting C 的「假阳」其实是 unknown，不是 licit
        assert lic_top_frac < 0.02

    def test_setting_c_deflates_pr_auc_as_artifact():
        # unknown 当 benign 明显压低 PR-AUC（coverage artifact，非模型退化）
        assert paA - paC > 0.2

    return


@app.cell
def _(cov_unknown_5, fp_licit_5, miss_illicit_5):
    def test_attribution_coverage_gap_dominates():
        # coverage-gap 是队列不一致的主导成因（远超 label-conflict，也超过 detection-miss）
        assert cov_unknown_5 > miss_illicit_5
        assert cov_unknown_5 > 50 * max(fp_licit_5, 1)

    def test_attribution_label_conflict_near_zero():
        # illicit/licit 边界几乎无 score-vs-label 冲突（licit 在队远少于 coverage-gap）
        assert fp_licit_5 < 0.05 * cov_unknown_5

    return


if __name__ == "__main__":
    app.run()
