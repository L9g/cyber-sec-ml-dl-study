# 地址图 GNN:到了有跨期边的图,图就赢了吗?——三层对照 + 建图/参数/方法学全解

> 一步步拆解「到了一张**有跨期边、全图连通**的地址图上跑 GraphSAGE,图能翻盘吗?
> ——仍不能;消息传递只加了 +0.015,而且 SAGE 0.361 仍**远低于** tx 投影天花板 0.74。
> 图改变不了『标签是全局/事后裁定』这个病根(provenance 主线不因换模型、换图而变)」。
> 数据来源:`notebooks/08_address_graph_eda.py`(结构 EDA)+ `notebooks/09_address_graph_gnn.py`
> (三层对照)+ `results/experiments.csv`。strict inductive,CPU 训练(h=128,~26 分钟,峰值 ~6 GB,无需 GPU)。

本篇是 [tx-graph-gnn-does-graph-help.md](tx-graph-gnn-does-graph-help.md) 的续集。交易图那篇的收口是:
「图的**大**增益只可能来自**跨期时序**,而交易图按时间步断开(边 Δt=0)→ 要到**地址图**才谈得上」。
nb08 先把「地址图有跨期边」这个当时**未验证的前提**证实,nb09 再在这张图上做同款三层对照。

---

## 0. 结果:三层对照,以及与交易图的「赢家反转」

strict inductive split(首现 ≤34 训 / >34 测)、51 维地址特征、测试集 illicit base rate 5.3%、n_test=92,451:

| 层 | 特征 | 图消息传递 | PR-AUC | recall@1% |
|---|---|---|---|---|
| GBDT (LightGBM, **未加权**) | 51 维 | ✗ | 0.315 | 0.111 |
| GBDT (LightGBM, 加权) | 51 维 | ✗ | 0.246 | 0.080 |
| MLP | 同上 | ✗ | 0.346 | 0.135 |
| GraphSAGE | 同上 | ✓ | **0.361** | 0.145 |

四个关键差值:

- **纯消息传递增益 = SAGE − MLP = +0.015**(图**确有**微弱正信号,非零、非翻盘)。
- **⭐ 真实 NN vs 树反转 = MLP − 未加权 GBDT = +0.031**(注意**符号**:地址图上 NN **赢**树,
  但幅度**小**——用**同口径未加权**基准才是诚实数)。
- **⚠️ 类别加权非免费 = 未加权 − 加权 GBDT = +0.069**:排序度量(PR-AUC)下给 GBDT 加
  `scale_pos_weight` 反而**牺牲排序**(0.315→0.246)。若像旧稿那样拿**加权** GBDT 当基准,
  「反转」会被虚报成 +0.100——**三倍于真实值**。这本身是一条方法学教训(见 §4 末「方法学盒子」)。
- **✅ 反转经调参守门**:未加权 GBDT 12 组网格(num_leaves × min_child_samples × n_estimators)
  最优 **0.322**(num_leaves=63/min_child_samples=100/n_estimators=300)**仍 < MLP 0.346**(gap +0.024)
  → 「NN 微赢树」**不是 GBDT 欠调的假象**,反转对超参稳(`test_reversal_survives_gbdt_tuning` 断言守护)。

**⭐ 与交易图(nb07)的赢家反转**——同一批人、同一套框架,两张图上「树 vs 神经网络」的赢家反过来
(地址图侧用**未加权** GBDT,与 nb07 口径一致):

| | GBDT | MLP | GraphSAGE | 谁赢 | 图增益 |
|---|---|---|---|---|---|
| 交易图(nb07) | **0.813** | 0.624 | 0.660 | **树赢** | +0.036 |
| 地址图(nb09) | 0.315 | 0.346 | **0.361** | **NN 微赢** | +0.015 |

读法:**「谁赢」高度依赖数据形态,没有普适答案**;地址图上 NN 只**微弱**领先未加权树(+0.031),
且**两张图上消息传递都只是微弱正增益**——「图 > 表格不自动成立」被两种图各证一次。

**⭐ 主线不变**:即便上了 nb08 证实有跨期边(~19.7%)的连通地址图,SAGE 0.361 仍远低于
tx 投影参照 0.74(见 [native-actor-vs-projection.md](native-actor-vs-projection.md))——
guilt-by-association 的回溯循环仍在,**图修不了标签口径(provenance)**。

---

## 1. 地址图 vs 交易图:节点是「事件」还是「实体」

一句话:**交易图的节点是一次转账事件,地址图的节点是一个账户/参与者。**
同一个钱包会在很多笔交易里反复出现——交易图里它散落在多个节点上,地址图里它被收拢成一个节点。

| 维度 | 交易图 (transaction graph) | 地址图 (address graph) |
|---|---|---|
| 节点是什么 | 一笔交易(事件) | 一个钱包地址(实体) |
| 节点数 | 203,769 | 822,942 |
| 边是什么 | `txs_edgelist`:交易→交易(资金流) | `AddrAddr`:地址→地址(谁给谁转过币) |
| 边数 | 234,355 | 2,868,965(清洗后 ~2.74M) |
| 时间 | **硬**:每笔交易恰有一个时间步,边两端 **Δt=0 恒成立** | **软**:静态坍缩图,边**不带时间**;地址靠首现步 `first_step` 人为赋时间坐标 |
| 连通性 | **碎成 49 块**(每时间步一块,块间不连通) | **一整块巨型连通分量(99.999%)** |
| 跨期边 | **0%**(定义上不可能) | **~19.7%** |
| 特征 | 166 维交易特征 | 51 维钱包特征(去 4 个绝对区块列后) |
| 标签 | 每笔交易一枚(labeled 内 9.76% illicit) | 每地址一枚**不可变、全局/事后**标签(5.3% base rate) |
| 消息能传什么 | 只能同时间步内一跳 | 能**跨期**传 + 全图连通 |

**为什么这个区别是整条论证的枢纽**:交易图跨期断开 → 历史信息传不到未来 → 图天花板锁死(+0.036);
地址图有跨期边 → 早期坏地址能把风险传给晚期新地址 → 这才是「图可能带来大增益」的机制。
但实测图仍只 +0.015——原因见下一节的「两个数字」。

---

## 2. 什么是「跨期边」——GNN 能不能赢的唯一入口

**「期」= 一个时间步(1–49)**。**跨期边 = 一条边的两个端点不在同一时间步**;反义是同期边。

- **交易图边永不跨期**:每笔交易属于一个时间步,`txs_edgelist` 只连同期交易 → Δt=0 恒成立(代码每次建图复验),图碎成 49 块。
- **地址图边可以跨期,但需先定义时间**:`AddrAddr` 只说「X 给 Y 转过币」,不带时间。得先给每地址一个坐标——用**首现步**
  `first_step = groupby(地址).Time_step.min()`(`src/data.py::address_first_step`)。于是:

  ```
  地址X(首现第8步) ── 边 ── 地址Y(首现第8步)    同期边  Δfirst_step = 0
  地址X(首现第8步) ── 边 ── 地址Z(首现第40步)   跨期边  Δfirst_step = 32
  ```

  nb08 实测 **~19.7% 的边跨期**(交易图 0%),尾部 Δ 达 48 步。

**⚠️ 要分清两个数字,别搞混(这是全篇最易误读处):**

| 数字 | 含义 | nb08 实测 |
|---|---|---|
| 跨期边占比 | 两端首现步不同(Δ>0) | **~19.7%** |
| 跨 split 边界的边占比 | 一端 ≤34(训练区)、另一端 >34(测试区) | **~2.88%** |

「跨期」≠「跨越训练/测试分界线」。一条第 8 步↔第 20 步的边跨期了,但两端都在训练区内部,对预测测试节点没有直接帮助。
真正能把训练区历史送到**测试节点**的,只有那 **2.88% 跨越 34 分界线**的边——**通道很窄**,这就是 nb09 图增益虽正但只 +0.015 的结构原因。
**19.7% 证成「地址图确有跨期结构」(前提成立);2.88% 解释「但能帮到 inductive 预测的很少」(增益有限)。**

具体例子:
```
第8步:  坏地址X(illicit,训练时已知)
             │ 转过币(跨期边,Δ=32,且跨 split 边界:8≤34、40>34 → 属那 2.88%)
             ▼
第40步: 新地址Z(测试期才出现,要预测坏不坏)
```
GraphSAGE 沿这条边把 X 的「坏」聚合给 Z。但全图里这种「刚好能帮到测试节点」的边只占 2.88%,故图只能微弱加分。

---

## 3. 图是怎么构建的(建图方法,7 步)

两张图套路一样:**① 读边表 → ② 定义节点+连续索引 → ③ 边映射成索引对 → ④ 无向化 → ⑤ 特征矩阵(标准化)→ ⑥ 标签+掩码 → ⑦ inductive:训练只用诱导子图边**。

### 交易图(nb07,较简单)
```python
full   = d.load_tx_graph()                        # 节点表:txId + 特征 + class
idx_of = {t: i for i, t in enumerate(full.txId)}  # txId → 0..N 连续编号
edges  = d.load_tx_edges()                        # txId1 → txId2
src, dst = edges.txId1.map(idx_of), edges.txId2.map(idx_of)
src, dst = src[~isnan], dst[~isnan]               # 丢掉映射不到的边
ei = [concat(src,dst), concat(dst,src)]           # ④ 无向化:每条边复制成双向
mu, sd = X[train_mask].mean(0), X[train_mask].std(0)  # ⑤ 标准化只用训练节点(防泄漏)
x  = nan_to_num((X - mu) / sd)
train_mask = labeled & (ts <= 34);  test_mask = labeled & (ts > 34)   # ⑥
```
交易图**天生 inductive**:边 Δt=0,训练子图(≤34)与测试子图(>34)本就无共享边,`ei` 不用再切。

### 地址图(nb09,多了时间和 unknown 两件麻烦事)
```python
E = d.load_addr_addr(drop_self_loops=True, dedup=True)    # ① 清洗:去自环(1.6%)+重复边(3.0%)
nodes = unique(E.input ∪ E.output);  idx = {地址: 编号}     # ② input/output 地址一起当节点
snap  = d.all_address_snapshots(wf, wc)                    # ⑤ 每地址一行快照——含 unknown!
feats = [c for c in ... if c != "first_step"]              #    剔除时间代理
src, dst = E.input.map(idx), E.output.map(idx)             # ③
ei_full  = undirected(src, dst)                            # ④ 推理:全图
keep_tr  = (first_step[src] <= 34) & (first_step[dst] <= 34)
ei_train = undirected(src[keep_tr], dst[keep_tr])          # ⑦ 训练:只留两端都≤34的边=诱导子图
train_mask = labeled & (first_step <= 34)                  # ⑥
test_mask  = labeled & (first_step > 34)
```

**地址图比交易图多出的三个讲究:**

1. **先清洗边**(`drop_self_loops` + `dedup`):原始有 1.6% 自环、3.0% 完全重复边,不去掉消息传递会重复计数/自我强化。
2. **unknown 也进图,但不进 loss**(半监督):`all_address_snapshots` 覆盖**全部**地址(含 67.8% unknown),
   它们参与消息传递(帮传结构),但掩码只框 labeled 节点 → 不进损失函数。
3. **⭐ 严格 inductive 靠「两套边索引」**:`ei_train` 只保留两端首现都 ≤34 的边(诱导子图,训练用),
   测试节点及其边**完全不参与训练**;`ei_full` 全图只在推理用。这才敢说「测试节点训练时从没见过」
   (AML 审计最爱盘问的实体泄漏点)。`ei_train` 只占全图边的一小部分——正是 §2「通道窄」的量化来源。

### 两图共通的三条防泄漏红线(建图最易翻车处)
1. 特征标准化的 `mu/sd` **只用训练节点**统计——用全体等于把测试分布偷偷泄给模型。
2. **时间/绝对区块列绝不进特征**(`first_step`、`Time step`、4 个绝对 block 列 `WALLET_ABSOLUTE_BLOCK_FEATURES`)。
3. **无向化的原因**:资金流有向(A→B),但风险要双向传(B 的风险也应回流给 A)→ 每条有向边复制成两条。

### ⭐ 一个精巧的对照设计(结论可信的关键)
nb07/nb09 的 MLP 与 GraphSAGE **结构几乎一模一样**(两层 + 输出头、同 dropout/优化器/轮数),
唯一差别:GraphSAGE 用 `SAGEConv`(聚合邻居),MLP 用 `Linear`(只看自己),MLP 的 `forward` 干脆**忽略 `edge_index`**。
于是 **`GraphSAGE − MLP` = 纯粹的消息传递增益**,把「NN vs 树」这个混淆项干净隔离——
才敢说「图只贡献 +0.036 / +0.015」,而不把「NN 打不过树」的账错记到图头上。方法学出处见 §5。

---

## 4. LightGBM 参数怎么设,为什么这么设

全项目两套参数:

**A. 通用表格 baseline**(nb02/03/04/05/06,不含图那几层):
```python
LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=64,
               n_jobs=4, verbose=-1, random_state=42)
```
**B. nb09 三层对照里的 GBDT 层**(唯一加类别加权的):
```python
lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=63,
                   scale_pos_weight=spw, random_state=42, n_jobs=8, verbose=-1)
# spw = 负样本数 / 正样本数
```

| 参数 | 值 | 白话 | 为什么这么定 |
|---|---|---|---|
| `n_estimators` | 300 | 建 300 棵树,一棵纠正前一棵 | 配小学习率,够表达又不过拟合 |
| `learning_rate` | 0.05 | 每棵树只信 5% | 「300×0.05」业界稳妥搭配:慢学=更稳、更抗过拟合 |
| `num_leaves` | 64(=2⁶) | 每棵树最多 64 叶=复杂度旋钮 | **LightGBM 按叶生长(leaf-wise)**,主复杂度钮是它、不是 `max_depth` |
| `random_state` | 42 | 固定种子 | 项目硬规矩 `SEED=42`,可复现 |
| `n_jobs` | 4 / 8 | 用几个 CPU 核 | 机器 8 核 |
| `verbose` | -1 | 别刷日志 | 干净输出 |
| `scale_pos_weight` | 仅 nb09 | 给稀少的正样本放大权重 | 见下 ③ |

**三个关键考虑:**

1. **刻意不调参、跨 notebook 用同一套**。目的不是刷 AUC 榜,而是立一个「调得还行的强对照」
   ——主线论点是「图不自动赢过表格」(Weber 2019 自报 RF > 普通 GCN),表格 baseline 若是弱鸡,「图赢了」就没说服力。固定参数还让各层可比。
2. **时间/绝对区块特征一律不进模型**(`Time step`/`first_step`/4 个绝对 block 列)。它们是时间代理,
   模型会走捷径背「晚期更干净」这种**不可迁移**先验(EDA 实测 base rate 11.58%→6.5% 在漂移),部署到新时段就废——这是防泄漏。
3. **`scale_pos_weight` 只在 nb09 出现——为三层对照的公平**。两个 NN 用 `BCEWithLogitsLoss(pos_weight=...)`
   给正样本加权;为让树站同一起跑线,nb09 给 GBDT 补上对等的 `scale_pos_weight`。
   **但同时保留一条未加权 GBDT(spw=1)作诚实基准**——因为加权在排序度量下有害(见下方方法学盒子),
   「真实 NN vs 树反转」必须用未加权基准算。另跑 12 组未加权网格做**调参守门**(证反转非欠调假象)。

> **⚠️ 诚实注脚**:nb09 现在**本节同群体**同时跑两条 GBDT——加权(`scale_pos_weight`)拿 **0.246**,
> **未加权**(`num_leaves` 等其余全同)拿 **0.315**。**同一批测试地址、只差一个加权开关** → 这才是干净的
> 「加权成本」对照(0.315→0.246,净亏 **0.069**)。另有 nb06 的未加权原生 actor GBDT **0.297**
> (代码 `NATIVE_GBDT_REF`)——它是**不同 split/群体**的跨 notebook 交叉核对,与本节 0.315 接近但**非同一数**,
> 别混用。结论不因这些区分而变(都远低于 0.74、图增益都小)。

### 方法学盒子:排序度量(PR-AUC)下,类别加权为什么不是「免费的」

这是本项目一个可复用的评估纪律点——**「不平衡就加类别权重」这个教科书肌肉记忆,在排序度量下是错配的**。

**先分清三个常被混淆的概念**:**排序**(样本从最可疑到最不可疑的相对顺序,PR-AUC 只看这个)/ **校准**(分数绝对值准不准)/ **阈值**(在队里哪里划一刀判正负)。PR-AUC 是**纯排序度量**——对所有分数做任意**单调递增变换**(整体乘 3、过 sigmoid…),它**完全不变**,因为 top-k 里有几个真阳只由排序决定。

**理论层(加权不该动排序)**:给正类加权 w 倍 ≈ 把最优后验的赔率整体乘 w:

$$\frac{p'}{1-p'} = w\cdot\frac{p}{1-p}\quad(\text{odds}'=w\cdot\text{odds})$$

w 是正常数 → 这是**保序**变换 → 样本相对顺序不变 → **PR-AUC 理论上不动**;动的只是校准、以及固定阈值下的 precision/recall **单点**(加权本就是为「分类阈值决策」服务的工具)。

**现实层(却动了)**:加权**不是**训练完的事后重标定,而是从第一步就介入的**训练过程干预**——把模型推到一个**结构/参数都不同的解**,新旧解**不再互为单调变换** → 排序变、PR-AUC 变。**树尤其剧烈**:`scale_pos_weight` 缩放正样本的梯度/Hessian → 每一次「选哪个特征、切在哪」的分裂决策都变 → 长出一棵**结构完全不同**的树(不是「同一棵树、叶子值整体缩放」);而且叶子桶的并列结构被重排,PR-AUC 恰恰对队首并列最敏感。NN 温和一点但同样非凸:`pos_weight` 放大正类梯度 → 走到**不同的局部极小**,排序照样变。

**实测**:地址图正类极稀(5.3%)+ 严格 inductive(测试是没见过的新地址、分布偏移),加权把树的目标从「整体排序好」扭向「别漏正样本」、选更粗糙泛化更差的分裂 → 队首纯度掉 → PR-AUC **0.315 → 0.246(净亏 0.069,本节同群体同口径实测)**;对 NN 则常**净赚**(稀有正类下稳住优化、别被多数类淹没)。

**纪律(带走这两条)**:
1. **排序度量下别无脑加类别权重**——那是「分类阈值时代」的习惯,错配到 ranking 上轻则纯属扰动、重则有害(呼应根 `CLAUDE.md`「PR-AUC 优先 / 报曲线不报单点」)。
2. **「公平对照」本身有副作用**:为三层对齐而给树加权,扭曲了树的真实水平 → 必须保留**未加权 0.315** 作诚实参照,否则「NN 赢树 +0.100」有**三分之二是加权假象**(真实反转只 **+0.031**)。

---

## 5. 这个「架构匹配对照」的方法学出处

§3 那个「MLP 与 GraphSAGE 只差一个 `SAGEConv↔Linear` 算子」的设计,不是独创——它在 GNN 方法学里有名字:
**graph-agnostic (MLP) baseline / message-passing ablation**。区分两个精度:

- **粗版**:随便跑个 MLP(只吃节点特征、无视图)当 baseline(多数论文/教程)。
- **严格版(本项目)**:MLP 与 GNN 共享深度/宽度/dropout/优化器/轮数,唯一换 `SAGEConv↔Linear`
  → `SAGE − MLP` 干净等于**纯消息传递边际**,把「NN vs 树」「宽窄深浅」全控住。这才是 controlled ablation。

**一、警告「别忘 MLP 对照」的方法学论文**
- Shchur et al., *Pitfalls of Graph Neural Network Evaluation*, 2018(NeurIPS RRL workshop)——思想源头:实证很多 GNN 论文漏报 MLP,而 MLP 常逼近甚至超过 GNN。
- Errica, Podda, Bacciu, Micheli, *A Fair Comparison of GNNs for Graph Classification*, 2020(ICLR)——structure-agnostic baseline,发现不少「增益」来自特征而非结构(与本项目「大头是 NN vs 树」同构)。
- Hu et al., *Open Graph Benchmark (OGB)*, 2020(NeurIPS)——leaderboard 强制报 MLP 条目;repo 里每任务 `mlp.py`/`gnn.py` 并列。
- Dwivedi et al., *Benchmarking Graph Neural Networks*, JMLR 24(43):1–48, 2023(arXiv:2003.00982, 2020)——标配 MLP 对照 + 结构消融。
- You, Ying, Leskovec, *Design Space for GNNs*, 2020(NeurIPS)——把聚合/传播当可插拔维度做消融。

**二、把「消息传递」正式拆成可插拔算子的架构论文(最贴近本设计)**
- Gasteiger (原 Klicpera), Bojchevski, Günnemann, *Predict then Propagate: GNNs meet Personalized PageRank (APPNP)*, ICLR 2019(arXiv:1810.05997)——把网络拆成 `MLP 预测` + `传播`,证明传播可加可减。本项目 `SAGE − MLP` 正是在量化这个「Propagate」项。
- Wu et al., *Simplifying Graph Convolutional Networks (SGC)*, ICML 2019(arXiv:1902.07153)——剥掉非线性,单独分离传播贡献。

**三、最契合「图不自动赢」的一支:异配图(heterophily)**
- Zhu et al., *Beyond Homophily in GNNs (H2GCN)*, 2020(NeurIPS)——消融里 MLP 在异配图上常胜 GNN。
- Lim et al., *Large Scale Learning on Non-Homophilous Graphs*, 2021(NeurIPS)——同配假设不成立时图无益。
- 对 AML 尤其相关:欺诈网络往往**异配**(坏人故意混进好人堆、伪装成正常对手方)→ 解释了地址图上消息传递只 +0.015。

**四、AML/fraud 领域实例(本项目已在这条线上)**
- Weber et al., *Anti-Money Laundering in Bitcoin (Elliptic)*, KDD '19 Workshop on Anomaly Detection in Finance(arXiv:1908.02591)——同表放 LogReg/RF/MLP/GCN,自报 **RF > GCN**,是 tabular↔graph 对照原型。
- Elmougy & Liu, *Demystifying Fraudulent Transactions and Illicit Nodes in the Bitcoin Network for Financial Forensics*（Elliptic++）, KDD '23, DOI [10.1145/3580305.3599803](https://doi.org/10.1145/3580305.3599803)(arXiv:2306.06108)——本项目数据集论文,也做 tabular vs graph 对照。
- Deprez et al. SLR(97 篇综述)——「传统模型仍有竞争力」是这类对照的元分析。

**五、可直接照看的 notebook/教程**:PyG 官方 examples(node classification 先 MLP 后 GCN)、Stanford CS224W(Leskovec)Colabs、OGB repo `examples/`(`mlp.py`+`gnn.py` 并列,最接近严格版)、DGL tutorials。

**定位**:本项目做的是 **OGB/Shchur 式 graph-agnostic MLP baseline 的严格版**,控制到只差一个算子,
归因逻辑对齐 **APPNP「predict-then-propagate」模块分解**,结论方向落在 **heterophily 那一支(图不自动赢)**。
→ 这个三层对照有文献背书、可辩护。

> ✅ **引用已核**(2026-07-02 WebSearch 逐条核对):Weber(arXiv:1908.02591、KDD '19 AML workshop)、
> Elmougy & Liu Elliptic++(DOI 10.1145/3580305.3599803、arXiv:2306.06108)、APPNP(arXiv:1810.05997、
> 作者确为 Klicpera→Gasteiger 改名)、Dwivedi Benchmarking(JMLR 24(43):1–48, 2023、arXiv:2003.00982)、
> SGC(arXiv:1902.07153)均已回填。其余方法学清单(Shchur/Errica/Hu/You/Zhu/Lim/Deprez)为标题级引用、
> DOI 未逐一核——正式投稿/简历外发前建议补核。

---

## 6. 收口:这一段在项目里的位置

- **给「为什么用图」一个诚实的实证答案的第二半**:交易图(nb07)证「同期断开的图加不了多少」;
  地址图(nb09)证「即便换成有跨期边、全图连通的图,增益仍微弱,且远够不着 provenance 天花板」。两图合起来把「图 > 表格不自动成立」钉死。
- **主线不变**:provenance(标签全局/事后)是操作轴,换模型、换图都修不了 guilt-by-association 循环。
- **算力边界**:静态地址图 GraphSAGE 本机 CPU 可跑(见 [[project-compute-no-gpu-cloud-fallback]]);
  真正需 GPU 留云的是 **EvolveGCN**(49 时间步快照+RNN,Research 档)——那才是把「跨期时序」用满的模型。

一句话记忆点:**到了有跨期边、全图连通的地址图,GraphSAGE 仍只比无图 MLP 高 +0.015,且 0.361 远低于 tx 投影 0.74;
图换不来标签口径——两种图各证一次「图 > 表格不自动成立」。**
