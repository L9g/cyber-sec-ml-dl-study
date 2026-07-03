# 表格基础模型 TabPFN:换更强的表格模型,修得了标签口径吗?——六层对照 + G2T-FM 结构列

> 一句话:**不能。** 一个表格基础模型(TabPFN,in-context 预训练 transformer)+ 把图结构算成特征列
> 的 G2T-FM 变体,在地址特征上**全部落在 0.30–0.38 带**,距 tx 投影天花板 **0.74 还差 +0.43**。
> 更关键——G2T-FM 那根「邻居 illicit 比例」结构列(= guilt-by-association 的结构版)**一分没涨**(−0.006):
> 连**结构版的标签循环**都补不上这个 gap。瓶颈是**标签口径(provenance)**,不是函数族强弱、不是特征表达力。
> 数据来源:`notebooks/10_tabpfn_foundation_model.py` + `results/experiments.csv`。开放版 TabPFN v2、CPU、strict inductive。

本篇是 [address-graph-gnn-does-graph-help.md](address-graph-gnn-does-graph-help.md) 的续集。nb06/nb09 已把
「地址特征的诚实上限 ≈0.30(GBDT)/0.36(GraphSAGE)、而 tx 投影 0.74 是标签循环不是检测本事」这条钉死;
本节把对照**升级到 2024–2026 tabular DL 的 SOTA 一支——表格基础模型**,看这条结论扛不扛得住更强的函数族。

---

## 0. 结果:六层对照(同一共享 test 子样本上算指标)

strict inductive split(首现 ≤34 训 / >34 测)、51 维地址特征、**共享 8000 分层 test 子样本**、base rate **5.29%**:

| 层 | 训练数据 | 图/结构 | PR-AUC | recall@1% |
|---|---|---|---|---|
| LightGBM(全 train,未加权) | 172k | ✗ | 0.3295 | 0.277 |
| MLP(全 train,无图) | 172k | ✗ | 0.3664 | 0.314 |
| GraphSAGE(全 train,+消息传递) | 172k | ✓ | 0.3737 | 0.321 |
| **LightGBM@2k**(同 context) | 2k | ✗ | **0.3826** | 0.330 |
| **TabPFN**(in-context) | 2k | ✗ | **0.3084** | 0.256 |
| **TabPFN + G2T-FM**(+结构列) | 2k | ✓(特征) | **0.3020** | 0.249 |

> 全测试集注脚(magnitude 参照,非差值操作数):nb10 子样本 GBDT 0.330 / MLP 0.366 / SAGE 0.374 与
> nb09 全 92,451 口径(0.315 / 0.346 / 0.361)**同量级** → 8000 分层子样本对便宜模型无系统偏移,代表性 OK。

四个关键差值:

- **⭐ 基础模型 vs 树(等数据)= TabPFN − LightGBM@2k = −0.074**:同 2k context 下,开放版 TabPFN
  **输给** LightGBM。**⚠️ 诚实边界(别过度解读)**:这是**受限配置**的 TabPFN——`n_estimators=1`(关掉集成)、
  仅 2000 context、**开放版 v2**(非 2.5/3)、CPU。「TabPFN < 树」**只对此配置成立**,主线**不靠**它——
  uncapped 版(集成 + 大 context + 2.5/3)正是留给云 GPU 阶段的升档。主线靠的是下面两条。
- **⭐ G2T-FM 结构列增益 = G2T-FM − TabPFN = −0.006 ≈ 0**:同模型同 context,加了 degree + **邻居 illicit 比例**
  等结构列后**不涨反微跌**。这根列是**预注册的关键探针**(见 §3)——它没涨,是本节**最有信息量**的结果(见 §4)。
- **纯消息传递增益 = SAGE − MLP = +0.007**:复核 nb09(+0.015)——静态地址图上消息传递增益微弱,再证一次。
- **⭐ 距 tx 投影天花板 = 0.741 − 0.3084 = +0.43**:TabPFN 家族最好一档 **0.3084** 仍**远低于** tx 投影 0.74。

**一个副发现**:GBDT@2k(0.383)**略高于**全 172k train 的 GBDT(0.330)。小分层子集竟比全量还好一点——
可能是全量训练集里带了更多标签噪声/时间漂移,分层 2k 反而更「干净」。幅度不大(可能含噪),仅作注脚,不进主结论。

**⭐ 主线不变、且被加固一档**:换上表格基础模型、再加图结构特征列,整族仍卡在 0.30–0.38。
guilt-by-association 的回溯循环仍在——**换更强的函数族修不了标签口径(provenance)**。

---

## 1. TabPFN 是什么:为什么「fit 不训练」

**TabPFN(Prior-Labs / Hollmann et al., Nature 2025)= in-context 表格基础模型**。它是一个在**海量合成表格任务**上
预训练好的 transformer;用它时,`fit(X_train, y_train)` **不做任何梯度训练**——只是把训练样本当**上下文(prompt)**
塞进模型,`predict` 时一次前向、让模型在上下文里**近似贝叶斯推断**直接出预测。类比:GPT 的 few-shot in-context learning,
搬到表格分类上。

对本项目的意义**不是刷分,是当另一个「表格上限」证人**:
- 它是**函数族的升级**(预训练先验 vs 从零训 GBDT/MLP)——若连它都突破不了 0.30–0.38 带,「0.74=标签循环」再获一个更强模型的背书;
- 它的 **G2T-FM 变体**(§3)恰好是 nb07/nb09「消息传递消融」的**特征侧**对照。

---

## 2. 工程约束与配置(先说清楚,免得数字被误读)

### 2.1 许可:为什么用开放版 `tabpfn==2.2.0` 而非最新 8.x

`tabpfn` PyPI 包已**商业化到 8.x**(8.0.8):新版把**基础模型本地权重**都关进 license 墙,非交互环境直接抛
`TabPFNLicenseError`,要求去 `ux.priorlabs.ai` 注册、接受许可、`export TABPFN_TOKEN`。本节改用
**开放版 `tabpfn==2.2.0`**(commercialization 之前、对应 Nature 2025 的 TabPFN v2),免 token 从 HuggingFace
直接拉权重、CPU 可跑。**仅学术/求职演示**(与 Elliptic++ 许可注脚同处理)。新版 2.5/3 的更强权重需商用 token → 云阶段。

### 2.2 算力:为什么 context=2000、n_est=1、test 子样本=8000

本机无 GPU;TabPFN CPU 推理是 **O(context²)** 且慢——实测(n_est=1):

| context | 速度 | 全 92k test 外推 |
|---|---|---|
| 2000 | **133 s / 1k test 行** | ~3.4 小时 |
| 4000 | 478 s / 1k | ~12 小时 |
| 8000 + n_est=8(默认) | 5209 s / 1k | ~134 小时(不可行) |

内存不是瓶颈(29 GiB free),是纯算力。故采纳的 CPU 可跑配置:
- **TabPFN context = 从 172k train 分层抽 2000**(~108 正例)。TabPFN 本就是 **in-context 小数据模型**,2000 是其舒适区、非缩水。
- **`n_estimators=1`** 求速度(关掉 TabPFN 的内部集成)→ 这**低估** TabPFN 真实水平,是「TabPFN < 树」须打折的原因之一。
- **六层指标统一算在 8000 分层 test 子样本**(守 [same-pipeline](../../.claude/skills/same-pipeline-for-model-deltas)):
  所有差值的分子分母来自**同一评估集**,差值反映模型差、不掺采样差。全测试集数仅作 magnitude 注脚。

> **为什么这仍是干净对照**:TabPFN 用 2k context、GBDT/MLP/SAGE 用全 172k——训练数据不同**是模型差的一部分**,
> 但我们额外放了一行 **LightGBM@2k**(与 TabPFN 同 2000 context),于是「基础模型 vs 树」有一个**等数据**的干净对照(−0.074),
> 不把「TabPFN 数据少」的账错记到「基础模型不行」头上。这与 nb09「加 MLP 隔离 NN-vs-树」是同一套控制变量纪律。

---

## 3. G2T-FM:把图结构算成特征列 —— 以及防泄漏红线

**G2T-FM**(《Turning Tabular Foundation Models into Graph Foundation Models》, arXiv:2508.20906, 2025)
的思路**不改架构**:不搭 GNN,而是把邻居聚合/结构统计**算成额外特征列**,喂给 TabPFN。本节实现 5 根结构列:

```
log_degree            # 节点度(全图,label-free 结构量)
log_nb_illicit_cnt    # 邻居中「训练已知 illicit」计数
log_nb_trainlab_cnt   # 邻居中「训练已标注」计数
nb_illicit_frac       # ★ 邻居 illicit 比例 = nb_illicit_cnt / max(nb_trainlab_cnt,1)
has_trainlab_nb       # 是否有已标注训练邻居
```

### ⭐ `nb_illicit_frac` 是一根**预注册的关键探针**

这根「邻居 illicit 比例」列,正是 **guilt-by-association 的结构版**——它把「你的邻居坏不坏」直接灌成特征。
它与钱包标签的 OR/max 传播(`wallet-illicit ⟺ 触过 illicit 交易`,见 nb04)**同源**。开工前就写死了两向判读:

- **若靠它涨分** → 实锤「结构版标签循环」有效,但那**不是独立新证据**、是同一循环换个入口;
- **若不涨** → 更硬地证明瓶颈是**标签口径**,连结构版循环都补不上 gap。

**两向都收紧非翻案。** 实测结果是**后者**(−0.006,见 §4)。

### 防泄漏红线(算这根列最容易翻车处)

`nb_illicit_frac` 的分子分母**只用训练标签**(`(y==1) & train_mask` 和 `train_mask`),test 节点自身标签**从不进**。
test 节点拿到的「邻居 illicit 比例」,来自它的**训练期邻居**的标签——是推理时**真能拿到**的信息,零 test 泄漏。
degree 是 label-free 结构量(推理时可观测),用全图无泄漏问题。→ 与 nb09「unknown 进图不进 loss、
严格 inductive」同一套纪律。

---

## 4. 为什么结构列(和消息传递)都补不上 gap —— 同一个 2.88% 窄通道

G2T-FM 结构列 **−0.006**、GraphSAGE 消息传递 **+0.007**,两条**特征侧/传播侧**的图信号都近乎为零——**同一个结构原因**:

nb08 实测地址图**只有 ~2.88% 的边跨越 ≤34/>34 的 split 边界**(19.7% 跨期,但多数在训练区内部)。strict inductive 下:
- test 节点的 `nb_illicit_frac` 只能由**跨过边界的训练邻居**赋值 → 绝大多数 test 节点这根列**是 0 或近乎无信息**;
- 同理 GraphSAGE 只能沿这 2.88% 的边把训练区的「坏」聚合给 test 节点。

**通道太窄 → 结构/图信号传不到测试节点 → 特征列和消息传递都加不了分。**

对照之下,tx 投影为什么能到 0.74?因为它**根本不是「结构传到 test 节点」**——它是把**标签的定义**
(「是否触过 illicit 交易」)当算子直接套在每个 actor 上,是**事后/全局裁定**(编码了活动当时拿不到的未来信息)。
0.74 与 0.30–0.38 带的差,是**回溯标签口径**给的,不是任何**遵守 inductive 的**模型能学到的信号——
无论这个模型是 GBDT、MLP、GraphSAGE,还是表格基础模型 TabPFN。

---

## 5. 收口:主线在 nb10 的位置

- **证人再加一个,且是最强函数族那一支**:nb06(GBDT)/nb07(tx 图)/nb09(addr 图)之后,nb10 用
  **表格基础模型 + 图特征化(G2T-FM)** 再证一次「表格族全部 << tx 投影」。
  从「TabPFN 一家」升级为「**2024–2026 的 tabular DL SOTA 谱系补不上标签口径的坑**」。
- **最信息量的一条是「结构列没涨」**:预注册的 guilt-by-association 结构探针 `nb_illicit_frac` 在 strict inductive 下
  **加不了分**(−0.006)→ 瓶颈坐实在**标签口径**,不是特征/结构表达力(呼应 nb09 消息传递 +0.015 的窄通道机制)。
- **诚实边界**:TabPFN 是**受限配置**(开放版 v2 / n_est=1 / 2k context / CPU),「TabPFN < 等数据树」只对此配置成立、
  主线不靠它;uncapped 升档(2.5/3 + 集成 + 大 context + 全测试集)留云 GPU 阶段(见下)。
- **升档路(需云 GPU)**:①TabPFN-2.5/3(商用 token、更大 context、全 92k test);②**TabDPT**(真实表预训练 FM +
  retrieval,堵「合成 prior 才不行」的借口);③更全 G2T-FM 结构列(PageRank/assortativity/clustering);
  ④EvolveGCN(49 快照时序)。**本机先做**(不必等云):RealMLP + meta-tuned GBDT defaults、TabM——加固「表格上限」本身。
  详见 [`../../docs/cloud-gpu-experiment-plan.md`](../../docs/cloud-gpu-experiment-plan.md)。

一句话记忆点:**表格基础模型 + 图结构特征列,全部停在 0.30–0.38,距 tx 投影 0.74 差 +0.43;
连「邻居 illicit 比例」这根结构版标签循环列都涨不动(−0.006)——换更强的函数族修不了标签口径。**

---

## 6. 引用与工具

- **TabPFN v2**:Hollmann, Müller, Purucker, et al., *Accurate predictions on small data with a tabular foundation model*,
  **Nature** 637, 319–326 (2025)。开放权重 `tabpfn==2.2.0`(HuggingFace `Prior-Labs/TabPFN-v2-clf`);新版 8.x 需商用 token。
- **G2T-FM**:Eremeev, Platonov, Prokhorenkova, et al., *Turning Tabular Foundation Models into Graph Foundation Models*,
  **arXiv:2508.20906**(2025)——不改架构、图结构算成特征列;报异配图强过传统 GNN(AML 图正是异配)。
- **对照方法学**(同 nb09 §5):graph-agnostic MLP baseline / message-passing ablation(Shchur 2018、Errica 2020、
  OGB 2020);本节把它从「消息传递消融」推广到「结构特征化消融」(G2T-FM − TabPFN)。
- **主线数据不变量**:钱包 illicit 标签 = 交易 illicit 标签的 OR/max 确定性传播(14,266/14,266 零例外,见 nb04 / 项目 CLAUDE.md)。

> ✅ **核验(2026-07-03)**:TabPFN license 墙、`tabpfn==2.2.0` 免 token 加载、CPU O(context²) 计时、六层数字
> 均本会话实测;G2T-FM(arXiv:2508.20906)、TabPFN Nature 2025 标题级已核。TabPFN Nature 卷期页码
> (637:319–326)属常见引用、正式外发前建议再核一次 DOI。
