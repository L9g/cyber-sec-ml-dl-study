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
    # 13 · Stage B —— 选择性标注 / reject inference（标签管线病理,headline）

    > 计划:`docs/fraud-aml-label-pipeline-experiment-plan.md` §6。**补的短板**=真实 fraud/AML 里
    > 「标签不是数据自带的真相,而是一条被旧策略偏置的生产管线的输出」。缺陷表 #2。
    >
    > **核心机制**:只有被历史策略 `π₀`(这里=**旧规则:审查高金额交易**,AML 最经典的触发器)审过的案子才拿到真值;
    > 没审的没有反事实结果。于是你训练用的标签 = **昨天风控策略的产物**,不是总体真相。
    >
    > **使能洞察**:要*量*这个偏置,必须有已知真相对照——真实脏数据没真相、测不了。故这里用
    > **已知真相的合成世界**当实验台(本骨架先用自带 stand-in,`make_truth_world()` 是唯一 SEAM,
    > 日后**换成 AMLSim**:`y_true`=账户级 SAR 独立真相[非 IS_SAR 参与派生]、特征=账户特征、`π₀`=历史审查策略)。

    ## 统一模板(注入 → 测偏置 → 缓解 → 测回收)· 四变体同评估集
    | 变体 | 训练用什么 | 角色 |
    |---|---|---|
    | **M_oracle** | 全体、真值 `y_true` | 天花板(合成才有) |
    | **M_vbias** | 全体,已审→真值 / 未审→**假定为负** | ❌ 最常见错误:把未审当良性 |
    | **M_reject**（reject inference）| **只**用已审样本、真值(不臆造负标签) | ✅ 主缓解 |
    | **M_reject_ipw** | 同上 + `1/ê(x)` 逆倾向加权 | 精修(小,视 overlap/模型族而定) |

    度量三个量(数字由实验挣,不预答):**假阴损害** = oracle−vbias、**⭐ reject 回收** = reject−vbias、
    **IPW 精修** = reject_ipw−reject。全部在**同一持有 test 集(全真值)**上评估——只训练侧被 `π₀` 污染,
    同管线(same split/特征/metric),差值才反映病理。

    ## 诚实边界(先说,不预答)
    1. **MAR vs MNAR**:`π₀` 只依赖可见 amount(MAR),IPW 才有定义;若依赖不可见混杂(MNAR)则纠不动,须声明。
    2. **positivity/overlap**:`π₀` 概率选择(`ê∈[0.03,0.97]`、不硬切),保证 overlap。
    3. **合成易学性 + 模型族**:GBDT 在 overlap 下对样本选择本就稳,**IPW 精修常很小**——这是诚实结论、不是 bug
       (IPW 的收益主要在参数模型/更强 MNAR/无 overlap 时)。结论看**相对量**,换 AMLSim 后重估 margin。
    """)
    return


@app.cell
def _(mo):
    import os
    import sys

    sys.path.insert(0, str(mo.notebook_dir().parent))

    import numpy as np
    import pandas as pd
    import lightgbm as lgb

    from config import seed_everything, EXPERIMENTS_CSV
    from src import evaluation as ev

    seed_everything()

    # ── 规模参数（NB13_SMOKE=1 缩规模做冒烟）──
    SMOKE = bool(os.environ.get("NB13_SMOKE"))
    N = 6000 if SMOKE else 40000     # 合成世界样本数
    K_FEAT = 8                       # 信号特征数（另加 1 列 amount）
    TEST_FRAC = 0.30                 # 持有 test（全真值评估）
    N_EST = 120 if SMOKE else 300    # LightGBM 树数
    IPW_CLIP = (0.03, 0.97)          # 倾向裁剪，保 positivity
    # π₀ 历史审查规则（旧规则按 amount 审）+ 真值信号强度
    SIG, INTERCEPT = 2.6, -3.0       # 真值 logit：信号强度 / 截距(压低→不平衡)
    A_AMOUNT, A_SIGNAL, SEL_C = 2.2, 0.0, 0.0  # π₀=f(amount) MAR；A_SIGNAL>0 可加隐混杂做 MNAR 对照
    return (
        A_AMOUNT, A_SIGNAL, EXPERIMENTS_CSV, INTERCEPT, IPW_CLIP, K_FEAT, N,
        N_EST, SEL_C, SIG, TEST_FRAC, ev, lgb, mo, np, pd, seed_everything,
    )


@app.cell
def _(INTERCEPT, K_FEAT, N, SIG, np):
    # ══════════════════════════════════════════════════════════════════════
    #  DATA SEAM ── 已知真相的合成世界（stand-in）
    #  ⚠️ 换 AMLSim 时只替换本函数：返回 (X, y_true, amount_z)，其余全不动。
    #     AMLSim 映射：y_true=生成前 SAR 账户设定/alert 主账户（独立真相，非 IS_SAR），
    #                 X=账户特征，amount_z=交易量代理。
    # ══════════════════════════════════════════════════════════════════════
    def make_truth_world(n=N, k=K_FEAT, seed=42):
        rng = np.random.default_rng(seed)
        X = rng.standard_normal((n, k)).astype(np.float32)
        amount = rng.lognormal(mean=0.0, sigma=1.0, size=n).astype(np.float32)  # 重尾金额
        amount_z = ((np.log1p(amount) - np.log1p(amount).mean()) / np.log1p(amount).std()).astype(np.float32)

        w_true = rng.normal(0, 1.0, size=k).astype(np.float32)
        # 真值 logit：特征信号 + amount 部分可预测（→ 按 amount 审查会与标签相关=富集）
        z = X @ w_true + 0.7 * amount_z
        z = (z - z.mean()) / z.std()
        logit = SIG * z + INTERCEPT
        p = 1.0 / (1.0 + np.exp(-logit))
        y_true = (rng.random(n) < p).astype(np.int64)

        Xfull = np.column_stack([X, amount_z]).astype(np.float32)
        return Xfull, y_true, amount_z, z, w_true

    Xfull, y_true, amount_z, z_true, _w_true = make_truth_world()
    return Xfull, amount_z, y_true, z_true


@app.cell
def _(A_AMOUNT, A_SIGNAL, N, SEL_C, TEST_FRAC, Xfull, amount_z, np, y_true, z_true):
    # ── split：train pool（施加 π₀）/ test pool（全真值评估）──
    #    随机 split（stand-in）；换 AMLSim 后改 temporal/inductive（按活动时间切、防实体泄漏）。
    rng = np.random.default_rng(7)
    perm = rng.permutation(N)
    n_test = int(TEST_FRAC * N)
    test_idx = np.sort(perm[:n_test])
    train_idx = np.sort(perm[n_test:])

    # ── 历史审查策略 π₀：旧规则按 amount 审(MAR,依赖可见 x)。A_SIGNAL>0=加隐混杂做 MNAR 对照 ──
    sel_logit = A_AMOUNT * amount_z + A_SIGNAL * z_true + SEL_C
    e_true = 1.0 / (1.0 + np.exp(-sel_logit))
    e_true = np.clip(e_true, 0.03, 0.97)            # positivity
    S = (rng.random(N) < e_true).astype(np.int64)   # 1=被审查（拿到真值）

    y_obs_vbias = np.where(S == 1, y_true, 0)        # 验证偏置：未审→假定为负
    return S, test_idx, train_idx, y_obs_vbias


@app.cell
def _(S, mo, test_idx, train_idx, y_true):
    _tr = train_idx
    _sel = S[_tr] == 1
    mo.md(f"""
    合成世界就绪。总体 prevalence(真值)=**{y_true.mean():.2%}**(PR-AUC 随机基线)。

    - train pool **{len(_tr):,}** / test pool **{len(test_idx):,}**(test 全真值评估)。
    - `π₀`(按 amount 的旧规则)审查率 = **{_sel.mean():.1%}**;被审子集 prevalence = **{y_true[_tr][_sel].mean():.2%}**
      (>总体 → 富集正类)、正类召回 = **{S[_tr][y_true[_tr]==1].mean():.1%}**
      → **漏掉的正类(多为低金额)在 vbias 里被当成负样本 = 注入假阴**。
    """)
    return


@app.cell
def _(N_EST, ev, lgb, np):
    # ── LightGBM 训练/打分 helper（同管线：同超参、同 test）──
    def fit_score(X_tr, y_tr, X_te, sample_weight=None):
        clf = lgb.LGBMClassifier(n_estimators=N_EST, learning_rate=0.05, num_leaves=63,
                                 random_state=42, n_jobs=8, verbose=-1)
        clf.fit(X_tr, y_tr, sample_weight=sample_weight)
        return clf.predict_proba(X_te)[:, 1]

    def pack_metrics(y_te, s):
        return {"pr_auc": ev.pr_auc(y_te, s), "base_rate": ev.base_rate(y_te),
                "recall_at_1pct": ev.recall_at_budget(y_te, s, 0.01),
                "recall_at_5pct": ev.recall_at_budget(y_te, s, 0.05)}

    def est_propensity(X_tr, S_tr, clip):
        # ê(x)=P(审查|x)，用于 IPW；裁剪保 positivity/稳定
        e = fit_score(X_tr, S_tr, X_tr)              # in-sample（骨架；升档可 OOF）
        return np.clip(e, *clip)

    return est_propensity, fit_score, pack_metrics


@app.cell
def _(
    IPW_CLIP, S, Xfull, est_propensity, fit_score, pack_metrics,
    test_idx, train_idx, y_obs_vbias, y_true,
):
    Xtr, Xte = Xfull[train_idx], Xfull[test_idx]
    yte = y_true[test_idx]
    ytr_true = y_true[train_idx]
    Str = S[train_idx]
    sel = Str == 1

    # M_oracle：全 train、真值
    s_oracle = fit_score(Xtr, ytr_true, Xte)
    # M_vbias：全 train、未审假定为负（单边假阴污染）
    s_vbias = fit_score(Xtr, y_obs_vbias[train_idx], Xte)
    # M_reject：只用被审样本、真值（reject inference，不臆造负标签）
    s_reject = fit_score(Xtr[sel], ytr_true[sel], Xte)
    # M_reject_ipw：被审样本 + 逆倾向加权（IPW 精修）
    e_hat = est_propensity(Xtr, Str, IPW_CLIP)
    w_ipw = 1.0 / e_hat[sel]
    s_ipw = fit_score(Xtr[sel], ytr_true[sel], Xte, sample_weight=w_ipw)

    res = {
        "oracle": pack_metrics(yte, s_oracle),
        "vbias": pack_metrics(yte, s_vbias),
        "reject": pack_metrics(yte, s_reject),
        "reject_ipw": pack_metrics(yte, s_ipw),
    }
    return (res,)


@app.cell
def _(mo, pd, res):
    order = [
        ("M_oracle (全真值,天花板)", "oracle"),
        ("M_vbias (未审=假定为负) ❌", "vbias"),
        ("M_reject (只训已审,reject inference) ✅", "reject"),
        ("M_reject_ipw (+IPW 逆倾向)", "reject_ipw"),
    ]
    tbl = pd.DataFrame([
        {"variant": name, "PR-AUC": round(res[k]["pr_auc"], 4),
         "recall@1%": round(res[k]["recall_at_1pct"], 3),
         "recall@5%": round(res[k]["recall_at_5pct"], 3)}
        for name, k in order
    ])
    br = res["oracle"]["base_rate"]
    assume_neg_cost = res["oracle"]["pr_auc"] - res["vbias"]["pr_auc"]     # 假阴损害
    reject_recovery = res["reject"]["pr_auc"] - res["vbias"]["pr_auc"]     # ⭐ reject 回收
    reject_residual = res["oracle"]["pr_auc"] - res["reject"]["pr_auc"]    # 残余选择偏置
    ipw_delta = res["reject_ipw"]["pr_auc"] - res["reject"]["pr_auc"]      # IPW 精修

    mo.md(f"""
    持有 test base rate = **{br:.2%}**。四变体同评估集:

    {mo.ui.table(tbl, selection=None)}

    - **假阴损害 = oracle − vbias = {assume_neg_cost:+.4f}**(把未审案子当良性负样本,注入假阴)。
    - **⭐ reject 回收 = reject − vbias = {reject_recovery:+.4f}**(**只用被审样本的真标签、不臆造负标签**,把损害拿回来)。
    - **残余选择偏置 = oracle − reject = {reject_residual:+.4f}**(GBDT+overlap 下样本选择本身伤害很小)。
    - **IPW 精修 = reject_ipw − reject = {ipw_delta:+.4f}**(小,符合"GBDT 下 IPW 收益有限"的诚实预期)。
    - {'✅ 假阴损害显著' if assume_neg_cost > 0.05 else '⚠️ 假阴损害不显著,调 π₀/prevalence'};
      {'✅ reject inference 大幅回收' if reject_recovery > 0.03 else '⚠️ reject 回收不足'};
      {'IPW 精修微小(诚实)' if abs(ipw_delta) < 0.03 else 'IPW 精修可见'}。
    """)
    return assume_neg_cost, ipw_delta, reject_recovery, reject_residual


@app.cell
def _(EXPERIMENTS_CSV, ev, res):
    for _name, _split, _model, _k in [
        ("stageB_oracle", "full_truth", "LightGBM", "oracle"),
        ("stageB_assume_negative", "verification_bias", "LightGBM", "vbias"),
        ("stageB_reject_inference", "reject_inference", "LightGBM", "reject"),
        ("stageB_reject_ipw", "reject_inference", "LightGBM-IPW", "reject_ipw"),
    ]:
        _r = res[_k]
        ev.log_experiment(
            {
                "experiment": _name, "task": "label_pipeline_stageB",
                "split": _split, "model": _model,
                "pr_auc": round(_r["pr_auc"], 4), "base_rate": round(_r["base_rate"], 4),
                "pr_auc_lift": round(_r["pr_auc"] - _r["base_rate"], 4),
                "recall_at_1pct": round(_r["recall_at_1pct"], 4),
                "n_test": 0,
                "note": "Stage B selective-labeling/reject-inference; SYNTHETIC truth stand-in "
                        "(swap make_truth_world->AMLSim); pi0=amount rule (MAR); headline=assume-negative "
                        "is the damage, reject-inference recovers it, IPW marginal for GBDT; margins provisional",
            },
            EXPERIMENTS_CSV,
        )
    return


@app.cell(hide_code=True)
def _(assume_neg_cost, ipw_delta, mo, reject_recovery, reject_residual):
    mo.md(f"""
    ## 解读 → 收口(骨架版,数字待 AMLSim 落地后重估)

    - **假阴损害 {assume_neg_cost:+.4f}**:真实 fraud/AML 建模的**头号错误**=把"没人审过/被系统放行"的交易当成
      干净负样本。这里把它从论点变成**测出来的数**——正是 Kaggle 干净数据抹掉、而生产天天发生的事。
    - **⭐ reject 回收 {reject_recovery:+.4f}**:**主缓解不是花哨算法,是纪律**——只用**被真正审核/裁定过**的标签训练
      (reject inference),不给未审案子臆造 `y=0`。这一步就拿回绝大部分损害。
    - **残余选择偏置 {reject_residual:+.4f} / IPW 精修 {ipw_delta:+.4f}**:样本选择本身对 GBDT(有 overlap)伤害很小,
      IPW 只是小精修。**诚实结论**:IPW 不是万能药,其价值在**参数模型 / 无 overlap / 更强 MNAR**——别宣称"完全纠正"。
    - **叙事(面试用)**:"你训练标签是历史风控策略的产物;这是把未审当负样本的偏差量、用 reject inference 拿回来的部分、
      以及 IPW 在 MNAR 下纠不动的边界。"
    - **待办(→ Reference 升档)**:①`make_truth_world` 换 **AMLSim**(独立 SAR 真相把手);
      ②开 `A_SIGNAL>0` 的 **MNAR 变体**(π₀ 依赖隐藏混杂)证 IPW 失效;③接 selective-labels-aware 评估
      (Lakkaraju contraction);④把 amlworld-plan §3(连坐传播)作为本 stage 子案例并入;
      ⑤PU-learning 对照(把未审当"未标注"而非负)。
    """)
    return


@app.cell
def _(res):
    def test_all_variants_beat_random():
        # 四变体都应显著优于随机(base rate)——合成世界可学
        for k in ("oracle", "vbias", "reject", "reject_ipw"):
            assert res[k]["pr_auc"] - res[k]["base_rate"] > 0.05

    def test_oracle_is_ceiling():
        # oracle(全真值)是上界（容 0.02 有限样本噪声）
        assert res["oracle"]["pr_auc"] + 0.02 >= max(
            res[k]["pr_auc"] for k in ("vbias", "reject", "reject_ipw")
        )

    return


@app.cell
def _(assume_neg_cost, ipw_delta, reject_recovery):
    def test_assumed_negative_is_the_damage():
        # 头号错误(未审=负)确有显著损害,且 reject inference 大幅回收(方向性带 margin)
        assert assume_neg_cost > 0.05
        assert reject_recovery > 0.03

    def test_ipw_is_bounded_refinement():
        # IPW 对 GBDT 只是小精修——非翻盘(无论正负 |·| 有界),防把噪声当疗效
        assert abs(ipw_delta) < 0.05

    return


if __name__ == "__main__":
    app.run()
