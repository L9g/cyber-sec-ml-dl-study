# 项目四：金融犯罪 / AML 图学习

> Graph-Based Anti-Money-Laundering: Detecting Illicit Bitcoin Transactions with
> GNNs and Explainable Subgraphs

继承工作区根 `../CLAUDE.md` 通用约束；项目特定规则见 `CLAUDE.md`。
配套主线文档：`../docs/DS-ML-DL-Cyber-Security-v2.md` §三 项目四。
阅读清单 / 知识储备：`../docs/project4-reading-list.md`。

## 卖点（一句话）

> **When AML queues disagree: scoring granularity or label provenance?**
> 交易级打分和 actor/地址级调查队列往往不一致（Malik 2026 实证 Jaccard 低）。本项目**跨过**
> 「两队列不重叠」这一步，把不一致**拆成来源**：scoring granularity（聚合损失）vs
> **label provenance**（交易标签体系 ≠ 地址标签体系）。核心实证——**Elliptic++ 的钱包 illicit 标签是
> 交易标签的确定性 guilt-by-association 传播**（`wallet-illicit ⟺ 参与过 ≥1 illicit 交易`，双条件零例外），
> 一址一枚、事后/全局裁定、**标签本身无活动时间语义**（≠ 活动跨期：92.5% 地址单时间步、可 temporal 排序）——
> 故 actor 标签**不是独立监督**，干净切分也堵不住事后标签泄漏。这是把 honest-NIDS「特征泄漏」升级到
> 「标签体系先决定了哪些评估问题能被诚实回答」。

不是「又一个 Elliptic GNN 刷 AUC」。表格 baseline 是「图是否真有用」的诚实对照（Weber 2019 自报 RF>普通 GCN）；
GNN 退居 Reference 档附录（很可能证明「再复杂的模型也修不了标签口径错配」）。

## 执行顺序（薄切片优先，先跑绿主线再扇出）

1. ✅ temporal split + 交易级 LightGBM baseline（`notebooks/02`）
1b. ✅ 非 GNN 对照层：node2vec+LGBM / IsolationForest（`notebooks/03`）——交易图按时间步断开，裸拓扑近随机，给 GNN 立诚实靶
2. ✅ Transaction score → actor queue 投影（max，input+output participation）+ 两标签体系 yield 对照（`notebooks/04` §2）——**注意**：tx-yield vs actor-yield 是不同调查单元/分母的口径差（Δ 符号随预算翻转），**不是**投影损失；**max 下投影损失≡0**（transaction-first≡actor-first，Jaccard=1）
3. ✅ **标签来源审计（数据提前坐实）**：`wallet-illicit ⟺ 参与过 ≥1 illicit 交易`（14,266/14,266 双条件零例外）→ 钱包 illicit 标签是**交易标签的确定性 OR/max 传播**（guilt-by-association、事后/全局）→ actor 标签**非独立监督**，illicit 类**无 label-conflict**
4. ✅ **Setting C（unknown 当 benign 的错误示范，`notebooks/04` §4）**：unknown≠benign——把 69% unknown 当 benign 使 actor PR-AUC 0.736→0.309，但 **top 队列零 licit**，precision「崩」全来自 unknown 被误记 FP（selective-labeling artifact，非模型退化）。分步说明见 [`reports/setting-c-unknown-not-benign.md`](reports/setting-c-unknown-not-benign.md)
5. ✅ **归因表雏形（`notebooks/04` §5）**：队列位置×钱包标签列联表，每 actor 判唯一主导成因——**coverage-gap 主导**（unknown 在队 11,938@5%）> detection-miss（1,940）≫ label-conflict（licit 在队 193≈0）；**非加法**。诚实边界：**max 下 projection-loss≡0**（不稀释），投影损失是 mean/sum 才有的现象
6. ✅ **聚合扇出 mean/sum/top-k（`notebooks/05`）——granularity 从「推迟」变实腿**：解除 max 退化后 (a) **分歧是队首现象**：0.5% 预算 mean-vs-max 队列 Jaccard 仅 ~0.17，5% 才收敛回 ~0.89（多数地址单笔交易→四聚合恒等，分歧只来自被推上队首的少数多笔地址）；(b) **投影损失格填上**：1% 预算 mean 从 max 的 illicit 队首掉出 785 个（双向重排、非单调损失）；(c) **整体 PR-AUC 掩盖这一切**：max 0.7362 仅比 mean 高 0.016（又一次「报曲线不报单点」）；(d) **对称 volume bias**（队首）：sum 偏爱高吞吐(5.1 笔)、mean 偏爱单笔(1.5)、max 居中(2.6)；(e) **granularity 不独立于 provenance**：标签 OR/max 传播 → **max 是匹配算子、PR-AUC 最高**。诚实边界：回溯循环仍在，actor-PR-AUC 非独立成绩。分步说明见 [`reports/aggregation-fanout-granularity.md`](reports/aggregation-fanout-granularity.md)
7. ✅ **原生 actor 模型（`notebooks/06`，Reference 档起步）——不经 tx 投影、直接学 51 维地址特征**：group-aware **inductive** temporal split（test=首现>34 的地址、训练期从未见、无实体泄漏），但标签仍全局/事后 → **切分干净 ≠ 标签干净**。核心诚实发现:**原生独立信号很弱**（inductive PR-AUC **0.297**）而 **tx 投影碾压它（0.741）**;5% 预算 who-catches **不对称**（仅 proj 1,468 ≫ 仅 native 128）→ 原生大体是投影的更弱子集。**gap = guilt-by-association 循环的显形**:投影分下游于「是否触过 illicit 交易」这个定义标签的信号,几乎按构造匹配标签;0.30 才是地址特征的诚实上限。→ 加固 provenance 主线,给 GNN 立更硬的诚实靶。分步说明见 [`reports/native-actor-vs-projection.md`](reports/native-actor-vs-projection.md)
8. ✅ **交易图 GNN（`notebooks/07`，Reference，CPU 无需 GPU）——「图到底有没有用」的诚实三层对照**：LightGBM(GBDT 无图) **0.813** vs MLP(NN 无图) **0.624** vs GraphSAGE(NN+消息传递) **0.660**。关键分解:**纯消息传递增益 SAGE−MLP = +0.036（图确有微弱同期信号、非零）**，但大头缺口是 **NN vs 树 = −0.19**（不是「图 vs 无图」）→ 只报「GNN 0.66 < GBDT 0.81」会错把账算到图头上。交易图按时间步断开（复验 Δt=0，temporal split 图层面天然 inductive）→ 同期消息传递边际小、大增益只可能来自跨期时序（要到地址图 2.87M 边才有，按无-GPU 记忆留云主机）。实证「图 > 表格不自动成立」（呼应 Weber 2019 RF>GCN）。分步说明见 [`reports/tx-graph-gnn-does-graph-help.md`](reports/tx-graph-gnn-does-graph-help.md)
9. Reference 续（可选，需更大算力/云主机）：EvolveGCN / 地址图 GraphSAGE（跨期结构）

> 2×2 设计（scoring 单元 × label 口径）、聚合策略即风控决策、「unknown≠benign」错误示范见 `CLAUDE.md`。

## 数据

- **主**：Elliptic++（比特币交易图 + 地址图）。下载/许可见 `data/README.md`。
- **辅**（可选，升档）：IEEE-CIS Fraud（表格欺诈对照）。

## 分档交付（先推到 MVP 再升档）

| 档 | 内容 | 状态 |
|---|---|---|
| **MVP** | EDA ✅ + temporal LightGBM baseline ✅ + 非 GNN 对照 ✅ + actor 投影/agreement ✅ + 标签来源审计 ✅ + Setting C ✅ + 归因表雏形 ✅ + **聚合扇出(mean/sum/top-k, granularity 实腿) ✅** | ✅ **薄切片 + granularity 扇出跑通**；下一步：原生 actor 模型 或 改 docs/*-v2 项目四章节 |
| Reference-grade | GraphSAGE/GAT + precision@k + investigator budget + EvolveGCN 时序 | ⬜ |
| Strong | GNNExplainer 业务化解释 + AML Decision Card | ⬜ |
| Research-grade | Elliptic2 子图分类 / 有向多重图 GNN（Egressy） | ⬜ |

## 指标（按真实 AML 工作方式，不报裸 F1）

- **PR-AUC**（主，随机基线 = illicit 占比）；precision@k / recall@k + **human review budget**。
- **coverage @ abstention 曲线**——报曲线不报单点（操作点指标随阈值漂移，见项目一 §2.1 教训）。
- False-positive case study：挑「判可疑但可能合法」的案例讲 analyst 怎么复核。

## 环境

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/gdown --folder "<Drive folder>" -O data/raw   # 见 data/README.md
```

## 结构

```
config.py          固定 SEED=42 + 路径 + Elliptic 标签编码
data/README.md     下载说明 + 许可（原始数据不入 git）
src/               data / evaluation / models（MVP 逐步填）
src/tests/         代码契约单测（pytest，贴死精确值）
notebooks/         marimo .py（01 EDA → 02 交易 baseline → 03 非GNN对照层）
scripts/           重计算（build_node2vec.py：~6min 缓存嵌入）
results/           experiments.csv（upsert，按逻辑键）
reports/           findings / 决策记录
```
