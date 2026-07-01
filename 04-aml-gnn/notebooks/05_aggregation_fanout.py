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
    # 05 · 聚合策略扇出 —— scoring granularity 那条腿的正式登场

    > nb04 只做 **max** 投影，并证明了 **max 下 transaction-first ≡ actor-first**（Jaccard=1、
    > 投影损失≡0）——granularity 轴被 max **退化**藏起来了。本节扇出 **mean / sum / top-k**，
    > 解除退化：队列开始分叉、投影损失非零，归因表里那格 0 被填上。

    ## 一个把 granularity 锚回 provenance 的核心论点（本节要立的）
    §3 已证 **wallet-illicit 标签 = 交易 illicit 标签的 OR/max 传播**（双条件零例外）。
    OR/max 传播意味着：**max 聚合是与「标签怎么被造出来」相匹配的打分器**——一个地址只要有一笔
    illicit 交易就被染红，那么「取它最红那笔的分」正是复刻标签的构造。故：

    - mean/sum/top-k 相对 max 的一切偏离 = **granularity 造成的队列不一致**，
    - 且这个不一致的**方向由标签传播算子决定**（OR/max）→ **granularity 与 provenance 不独立**。

    这不是「哪个聚合 AUC 高」的擂台，是「**聚合策略即风控决策，且『正确』的聚合被标签来源钉死**」。

    ## 诚实边界（先说）
    1. **任务内可比**：四个聚合评的是**同一批 labeled 地址**（同标签、同 base rate），只是分数/排序不同
       → 它们的 PR-AUC **可以直接比**（CLAUDE.md「pr_auc−base_rate 任务内 sanity」）。跨 tx 任务仍只比曲线。
    2. **回溯循环仍在**：actor 标签是 tx 标签传播（§3 nb04），故这里比的是「**哪个聚合最保住 tx 信号到 actor 排序**」，
       **不是**独立检测质量。max 若胜出是「匹配标签算子」的**近乎同义反复**，是**发现**不是**成绩**。
    3. **sum 分不是概率**：sum 把 volume 混进分数，排序仍有效但**高活跃地址天然上浮**（§4 量化这个 bias）。
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

    # 与 nb04 完全同一条 pipeline（SEED=42、同超参 → 同一个模型、同一批分数）
    full = d.load_tx_graph()
    train_df, _test_lab = d.temporal_split(full, train_max_step=34)
    feats = d.feature_columns(full)
    y_train = (train_df["class"] == 1).astype(int)

    model = LGBMClassifier(
        n_estimators=300, learning_rate=0.05, num_leaves=64,
        n_jobs=4, verbose=-1, random_state=42,
    )
    model.fit(train_df[feats], y_train)

    # 全部测试期交易（含 unknown）打分 → 投影用
    test_all = full[full["Time step"] > 34].copy()
    test_all["score"] = model.predict_proba(test_all[feats])[:, 1]
    scores = dict(zip(test_all["txId"], test_all["score"]))

    part = d.actor_participation(include_outputs=True)   # [address, txId] input∪output
    wc = d.load_wallet_classes()                         # address → class（全局/事后）
    return (
        EXPERIMENTS_CSV,
        LABEL_ILLICIT,
        LABEL_LICIT,
        LABEL_UNKNOWN,
        ev,
        mo,
        np,
        part,
        pd,
        plt,
        proj,
        scores,
        wc,
    )


@app.cell
def _(LABEL_ILLICIT, LABEL_LICIT, ev, part, proj, scores, wc):
    # 四种聚合。max=nb04 已证的 transaction-first 基准；mean/sum/top3_mean 是扇出。
    # ⚠️ 地址**集合**四种聚合完全相同（同参与边、同已打分交易）——只是 actor_score/排序不同。
    #    故 labeled 集合与 base rate 恒定 → PR-AUC 任务内可比。
    AGGS = {
        "max": "max",
        "top3_mean": proj.make_topk_mean(3),
        "mean": "mean",
        "sum": "sum",
    }
    frames = {}
    for _name, _agg in AGGS.items():
        _a = proj.project_scores_to_actors(
            part, scores, agg=_agg, addr_col="address"
        ).merge(wc, on="address", how="left")
        frames[_name] = _a

    # 参照系：地址集合、labeled 掩码、base rate（对所有聚合相同）
    ref = frames["max"]
    n_all = len(ref)
    lab_mask = ref["class"].isin([LABEL_ILLICIT, LABEL_LICIT]).values
    # 每个 frame 的地址顺序不同，故不能靠位置对齐；用 address 做键统一取标签
    cls_by_addr = dict(zip(ref["address"], ref["class"]))
    base_rate_actor = ev.base_rate(
        [1 if cls_by_addr[a] == LABEL_ILLICIT else 0
         for a in ref["address"] if cls_by_addr[a] in (LABEL_ILLICIT, LABEL_LICIT)]
    )
    return AGGS, base_rate_actor, cls_by_addr, frames, n_all


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Setting A PR-AUC × 4 聚合（任务内可比，同 labeled 集合/同 base rate）
    """)
    return


@app.cell
def _(AGGS, LABEL_ILLICIT, LABEL_LICIT, base_rate_actor, ev, frames, mo, pd):
    _rows = []
    pr_by_agg = {}
    for _name in AGGS:
        _a = frames[_name]
        _lab = _a[_a["class"].isin([LABEL_ILLICIT, LABEL_LICIT])]
        _y = (_lab["class"] == LABEL_ILLICIT).astype(int).values
        _s = _lab["actor_score"].values
        _pa = ev.pr_auc(_y, _s)
        pr_by_agg[_name] = _pa
        _rows.append({
            "aggregation": _name,
            "PR-AUC (Setting A)": round(_pa, 4),
            "lift vs base": round(_pa - base_rate_actor, 4),
            "recall@1%": round(ev.recall_at_budget(_y, _s, 0.01), 3),
            "recall@5%": round(ev.recall_at_budget(_y, _s, 0.05), 3),
        })
    t1 = pd.DataFrame(_rows)
    best = max(pr_by_agg, key=pr_by_agg.get)
    gap_max_mean = round(pr_by_agg["max"] - pr_by_agg["mean"], 4)

    mo.md(f"""
    同一批 **labeled 地址**（base rate = **{base_rate_actor:.1%}**，四聚合恒定），四种聚合各自的 Setting A 成绩：

    {mo.ui.table(t1, selection=None)}

    - **最高 = `{best}`**；max 比 mean 高 **{gap_max_mean:+.4f}** PR-AUC。
    - 若 `max` 胜出：印证核心论点——标签是 OR/max 传播，**max 是匹配算子**，任何稀释性聚合(mean)
      都把 illicit 地址那笔关键红交易的信号摊薄 → 排序变差。这是**近乎同义反复的发现，不作检测力背书**。
    - ⚠️ **别被这张小差距骗了**：整体 PR-AUC 把全预算平均、**掩盖了队首的剧烈重排**（§2/§3 显示
      0.5% 预算下 mean 与 max 只重叠 ~0.17、互换掉数百个 illicit 地址）。聚合选择的杀伤力在**队首**，
      正是整体 AUC 看不见的地方——所以下面立刻转 operational 曲线。
    - `sum` 的分不是概率、混入 volume（§4）；它的 PR-AUC 只说明「按活动量加权排序」有多接近标签，
      **不能**读成「sum 是好检测器」。
    """)
    return best, gap_max_mean, pr_by_agg


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. ⭐ 队列偏离曲线：mean/sum/top-k **相对 max(=transaction-first)** 的 Jaccard

    nb04 证了 max 下 actor-first ≡ transaction-first（Jaccard=1）。把 max 当 transaction-first 基准，
    量每个聚合把队列**搬动**了多少——**这就是被 max 藏住的 scoring-granularity 信号**。
    """)
    return


@app.cell
def _(AGGS, frames, mo, n_all, pd):
    def top_addr_set(name, k):
        # frame 已按 actor_score 降序（稳定排序），取前 k 个地址集合
        return set(frames[name]["address"].values[:k])

    budgets = (0.005, 0.01, 0.02, 0.05)
    _jac_rows = []
    for _b in budgets:
        _k = max(1, int(round(_b * n_all)))
        _max_top = top_addr_set("max", _k)
        _row = {"budget": f"{_b:.1%}", "k": _k}
        for _name in AGGS:
            if _name == "max":
                continue
            _top = top_addr_set(_name, _k)
            _row[f"J({_name},max)"] = round(len(_max_top & _top) / len(_max_top | _top), 3)
        _jac_rows.append(_row)
    jtbl = pd.DataFrame(_jac_rows)

    _head_mean = jtbl.iloc[0]["J(mean,max)"]   # 0.5% 队首
    _head_sum = jtbl.iloc[0]["J(sum,max)"]
    _j5_mean = jtbl.iloc[-1]["J(mean,max)"]    # 5% 预算
    _j5_sum = jtbl.iloc[-1]["J(sum,max)"]

    mo.md(f"""
    {mo.ui.table(jtbl, selection=None)}

    - **分歧集中在队首**：0.5% 预算（操作最尖端）mean 与 max 的重叠仅 **{_head_mean}**、sum 仅 **{_head_sum}**——
      **同一批交易分数、只换聚合算子，最该先查的地址就几乎全换了一批**。到 5% 预算才收敛回 mean {_j5_mean} / sum {_j5_sum}。
      **这正是 nb04 里恒等于 1 的那条腿**，且它在**预算越紧、越咬人的地方分歧越大**。
    - **为什么只在队首**：地址交易数中位数 = 1（多数地址只有 1 笔），对它们 max=mean=sum 恒等 → 分歧只能来自
      少数多笔地址，而这些地址**恰恰被聚合推到队首**（§4）。故整体 PR-AUC（§1）几乎看不出差别、
      **operational 曲线的队首却天翻地覆**——又一次「报曲线不报单点」。
    - 分叉不是 bug 是 **granularity 的定义**：一个地址「多可疑」取决于你把它多笔交易怎么并成一个分，
      而**没有中立的并法**——每种聚合是一种风控立场（max=最坏一笔即升级 / mean=平均画像 / sum=看累计暴露）。
    """)
    return budgets, jtbl, top_addr_set


@app.cell
def _(AGGS, budgets, n_all, plt, top_addr_set):
    fig, ax = plt.subplots(figsize=(6, 3.6))
    _xs = [_b * 100 for _b in budgets]
    for _name in AGGS:
        if _name == "max":
            continue
        _ys = []
        for _b in budgets:
            _k = max(1, int(round(_b * n_all)))
            _mt = top_addr_set("max", _k)
            _tt = top_addr_set(_name, _k)
            _ys.append(len(_mt & _tt) / len(_mt | _tt))
        ax.plot(_xs, _ys, marker="o", label=f"J({_name}, max)")
    ax.axhline(1.0, ls="--", c="gray", alpha=.6, label="max vs max ≡ 1 (nb04)")
    ax.set_xlabel("investigation budget (% of actor queue)")
    ax.set_ylabel("Jaccard overlap with max queue")
    ax.set_title("Queue divergence from transaction-first (=max): the granularity signal")
    ax.set_ylim(0, 1.05)
    ax.legend(); ax.grid(alpha=.3); fig.tight_layout()
    fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. 投影损失格填上：max 捞到、聚合丢掉的 **illicit 地址**（nb04 里那格 0）
    """)
    return


@app.cell
def _(AGGS, LABEL_ILLICIT, cls_by_addr, frames, mo, n_all, pd):
    def illicit_top(name, k):
        return {a for a in frames[name]["address"].values[:k]
                if cls_by_addr.get(a) == LABEL_ILLICIT}

    _budgets_p = (0.005, 0.01, 0.05)
    _ploss_rows = []
    ploss = {}   # {agg: dropped @1%}，喂小结/断言
    for _b in _budgets_p:
        _k = max(1, int(round(_b * n_all)))
        _max_ill = illicit_top("max", _k)
        for _name in AGGS:
            if _name == "max":
                continue
            _agg_ill = illicit_top(_name, _k)
            _dropped = len(_max_ill - _agg_ill)   # max 在队、此聚合掉出
            _gained = len(_agg_ill - _max_ill)    # 此聚合另捞到 = 双向重排
            if abs(_b - 0.01) < 1e-9:
                ploss[_name] = _dropped
            _ploss_rows.append({
                "budget": f"{_b:.1%}", "aggregation": _name,
                "illicit in max-queue": len(_max_ill),
                "DROPPED by agg": _dropped,
                "GAINED by agg": _gained,
                "net Δ": _gained - _dropped,
            })
    ptbl = pd.DataFrame(_ploss_rows)
    _mean_drop_1 = ploss.get("mean", 0)

    mo.md(f"""
    **max(=transaction-first) 队列里的 illicit 地址**，被换成别的聚合后掉出/另捞多少（跨预算）：

    {mo.ui.table(ptbl, selection=None)}

    - **DROPPED > 0 = nb04 那格 0 被填上**：这些 illicit 地址 tx 模型明明给过高分（进了 max/transaction-first 队列），
      却因聚合**稀释/重排**掉出——**纯 granularity 效应、非检测漏报**。
    - **队首规模惊人且双向**：1% 预算下 mean 从 max 的 illicit 队首**掉出 {_mean_drop_1} 个**、同时另捞回一批
      → 这是**大规模队列重排**，不是单调「损失」（GAINED 也大）。到 5% 预算重排几乎消失（呼应 §2 收敛）。
    - 呼应核心论点：重排恰恰因为聚合**偏离了标签的 OR/max 传播算子**。max 下 DROPPED 必然 0（自己比自己）。
      归因非加法：DROPPED / GAINED 各是一种失败/替换，**不相加成「总损失」**。
    """)
    return (ploss,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. sum 的 volume bias 诊断（sum 分不是概率）
    """)
    return


@app.cell
def _(AGGS, frames, mo, n_all, part, pd, scores):
    # 每地址在**已打分测试交易**里的参与笔数（与投影同 universe）
    scored_ids = set(scores)
    part_scored = part[part["txId"].isin(scored_ids)]
    ntx = part_scored.groupby("address").size()
    overall_mean = float(ntx.mean())

    # ⚠️ 用**队首 0.5%** 的 **mean** n_tx：多数地址只 1 笔 → 5% 队列 median 全是 2、看不出 bias；
    #    体量偏差只在极队首、且被少数高活跃地址拉动，故看 mean 不看 median。
    _kv = max(1, int(round(0.005 * n_all)))
    _vrows = []
    for _name in AGGS:
        _top_addrs = frames[_name]["address"].values[:_kv]
        _v = ntx.reindex(_top_addrs)
        _vrows.append({
            "aggregation": _name,
            "mean n_tx in top-0.5%": round(float(_v.mean()), 1),
            "p95 n_tx": int(_v.quantile(0.95)),
            "vs overall mean": f"{_v.mean() / overall_mean:.1f}×",
        })
    vtbl = pd.DataFrame(_vrows)
    sum_mean_ntx = round(float(ntx.reindex(frames["sum"]["address"].values[:_kv]).mean()), 1)
    mean_mean_ntx = round(float(ntx.reindex(frames["mean"]["address"].values[:_kv]).mean()), 1)
    max_mean_ntx = round(float(ntx.reindex(frames["max"]["address"].values[:_kv]).mean()), 1)

    mo.md(f"""
    全体地址平均参与 **{overall_mean:.2f}** 笔（中位数 1——多数只 1 笔，故 5% 队列的 median 全是 2、看不出 bias，
    偏差只在**极队首**且由少数高活跃地址拉动）。各聚合 **top-0.5% 队列的平均活跃度**：

    {mo.ui.table(vtbl, selection=None)}

    - **对称的体量偏差**（都在队首，5% 处消失）：
      **sum = {sum_mean_ntx} 笔（体量偏差 ↑）** ≫ max = {max_mean_ntx} ≫ **mean = {mean_mean_ntx} 笔（反向偏差 ↓）**。
      sum 累加 → **高吞吐地址天然上浮**（多笔中等分之和 > 单笔高分）；mean 平均 → **偏爱单笔地址**
      （一笔高分不被稀释，多笔活跃地址被拉平）。max 居中。
    - 都**不是**「更会抓洗钱」：sum 把 volume 冒充 illicitness（交易所/混币器这类高吞吐地址会霸榜=公平性坑），
      mean 则系统性冷落高活跃地址。→ 选聚合是**风控价值判断**：惩不惩高吞吐、单笔是否即升级，全写在算子里。
    """)
    return


@app.cell(hide_code=True)
def _(best, gap_max_mean, mo, ploss):
    _dropped_txt = ", ".join(f"{k}={v}" for k, v in ploss.items())
    mo.md(f"""
    ## 小结 → 下一步

    **granularity 那条腿现在是实腿了**（nb04 里它在 max 下退化=null），且形态比预期锋利：

    - **分歧是"队首现象"**（§2）：0.5% 预算 mean-vs-max 队列只重叠 ~0.17，到 5% 收敛回 ~0.89。
      多数地址单笔交易（四聚合恒等），分歧只来自被聚合推上队首的少数多笔地址 → **预算越紧、分歧越大**。
    - **整体 PR-AUC 掩盖了这一切**（§1）：max−mean 仅 {gap_max_mean:+.4f}，但**队首互换掉数百 illicit 地址**
      （§3：1% 预算 mean 掉出 {_dropped_txt} 个并另捞回一批）——**又一次「报曲线不报单点」**，单点 AUC 会让人误判「聚合无所谓」。
    - **granularity 不独立于 provenance**：标签是 OR/max 传播（§3 nb04）→ **max 是匹配算子**，
      整体 PR-AUC 最高者 = **`{best}`**。这是**发现**（聚合的"正确解"被标签来源钉死），不是检测力擂台——回溯循环仍在。
    - **对称的 volume bias**（§4，都在队首）：**sum 偏爱高吞吐**（体量冒充 illicitness、公平性坑）、
      **mean 偏爱单笔**、max 居中——每种聚合是一种风控立场，**没有中立并法**。

    旗舰问句的更新答案：**granularity 是真实操作轴**（队首队列因聚合选择大幅分叉、体量偏差对称），
    但**它的"正确解"由 label provenance 决定**（OR/max 传播 ⇒ max 匹配）——两轴**纠缠**、非二选一。

    下一步（升档）：① 原生 actor 模型（不经 tx 投影、直接学地址级特征）看能否**跳出**这个投影框架；
    ② Reference 档 GNN（结构/时序传播）。当前 MVP granularity 扇出收口。
    """)
    return


@app.cell
def _(base_rate_actor, ev, frames, LABEL_ILLICIT, LABEL_LICIT, EXPERIMENTS_CSV, AGGS):
    # 落盘（upsert）：四聚合各一行，Setting A。⚠️ 均 retrospective、actor 标签=tx 标签传播，勿跨任务比。
    for _name in AGGS:
        _a = frames[_name]
        _lab = _a[_a["class"].isin([LABEL_ILLICIT, LABEL_LICIT])]
        _y = (_lab["class"] == LABEL_ILLICIT).astype(int).values
        _s = _lab["actor_score"].values
        ev.log_experiment(
            {
                "experiment": f"actor_projection_{_name}", "task": "actor", "split": "temporal",
                "model": f"tx-LightGBM→{_name}-proj",
                "pr_auc": round(ev.pr_auc(_y, _s), 4),
                "base_rate": round(base_rate_actor, 4),
                "pr_auc_lift": round(ev.pr_auc(_y, _s) - base_rate_actor, 4),
                "recall_at_1pct": round(ev.recall_at_budget(_y, _s, 0.01), 4),
                "n_test": int(len(_y)),
                "note": f"Setting A; {_name} aggregation; retrospective; actor label=tx label OR/max-propagation (guilt-by-assoc); 任务内可比、勿跨 tx 任务比",
            },
            EXPERIMENTS_CSV,
        )
    return


@app.cell
def _(pr_by_agg):
    def test_aggregation_changes_pr_auc():
        # granularity 存在的证据：不同聚合给出**不同** PR-AUC（不再是 max 退化的单一值）
        vals = list(pr_by_agg.values())
        assert max(vals) - min(vals) > 0.01

    def test_all_aggregations_beat_random():
        # 四聚合都显著优于随机（labeled Setting A，方向性带 margin）
        from src import evaluation as _ev  # noqa
        # base rate ~ 8%；每个都应远超
        assert min(pr_by_agg.values()) > 0.3

    return


@app.cell
def _(jtbl):
    def test_queue_diverges_from_max():
        # 核心：分歧集中在队首。1% 预算 mean 与 max 队列重叠远低于 1（nb04 里 ≡1 的退化被解除）；
        # 且所有聚合在队首都 < 1（严格分叉）。用队首而非 5%——5% 处已收敛（真实发现）。
        head = jtbl.iloc[1]      # 1% budget
        assert head["J(mean,max)"] < 0.5          # mean 队首与 max 大幅不同
        assert head["J(sum,max)"] < 1.0           # sum 也严格分叉（队首）
        assert head["J(top3_mean,max)"] < 0.5

    return


@app.cell
def _(ploss):
    def test_projection_loss_now_nonzero():
        # nb04 里 max 下投影损失≡0；换聚合后队首大规模掉出 illicit 地址（那格被填上、且非零幅度）
        assert max(ploss.values()) > 50

    return


if __name__ == "__main__":
    app.run()
