# 项目四（金融 AML 图学习）阅读清单与知识储备

> 配套主文档 `DS-ML-DL-Cyber-Security-v2.md` 第三章「项目四」。
> 持久参考层见 `knowledge-base/`（主题 T3）；本清单只列**交付项目四的必读**，BibTeX 以 `knowledge-base/references.bib` 为准。
> 两个目的：(A) 积累 AML 图学习近年有影响力/新颖的论文；(B) 想清楚「**为什么用图学习，而不是 XGBoost/普通 ML**」——这是项目四 README「动机」一节的核心。
> 图例：⭐ 必读 ｜ ○ 选读/扩展。BibTeX 细节落地引用前请二次核对。

---

## 阅读顺序（建议）

1. ⭐ Weber et al. 2019（Elliptic 起点 + GCN 思路 + 诚实的 RF 对照）
2. ⭐ Elmougy & Liu 2023（Elliptic++，你的主数据集）
3. ⭐「为什么用图」分析节（见文末，结合 Egressy + Elliptic2 + 表格对照）
4. ⭐ EvolveGCN 2020（动态图基线，时序切分的直接基础，见 §C）
5. ⭐ Eddin et al. 2021（真实银行 AML alert triage + 图特征降误报，见 §D）
6. ⭐ Egressy et al. 2024（结构感知 GNN，AML=有向多重图子图检测）
7. ⭐ GNNExplainer 2019（为 investigator 生成关键子图/特征解释，见 §D）
8. ⭐ Altman et al. 2023（银行转账合成数据，完整 ground truth）
9. ○ Bellei et al. 2024 Elliptic2（子图级范式，Research-grade）/ TGN / GraphSMOTE / 综述

---

## A. 核心数据集与方法

### ⭐ Anti-Money Laundering in Bitcoin: GCN for Financial Forensics (KDD-AnomalyDetection Workshop 2019)
- **作者/出处**：Weber, Domeniconi, Chen, Weidele, Bellei, Robinson, Leiserson（MIT-IBM Watson AI Lab + Elliptic）。
- **链接**：https://arxiv.org/abs/1908.02591
- **核心**：发布原始 **Elliptic** 数据集（200K+ 交易节点、234K 边、166 特征、49 时间步），用 GCN/Skip-GCN/EvolveGCN 做 illicit 检测。
- **⚠️ 关键诚实发现**：论文里 **Random Forest（用节点特征）实际强于普通 GCN**；图的价值要靠时序（EvolveGCN）才更明显。**这正是你项目四「表格 baseline 不是陪衬，而是检验图是否真有用的对照」的依据。**

```bibtex
@inproceedings{weber2019aml,
  title={Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics},
  author={Weber, Mark and Domeniconi, Giacomo and Chen, Jie and Weidele, Daniel Karl I. and Bellei, Claudio and Robinson, Tom and Leiserson, Charles E.},
  booktitle={KDD Workshop on Anomaly Detection in Finance}, year={2019}
}
```

### ⭐ Demystifying Fraudulent Transactions and Illicit Nodes — Elliptic++ (KDD 2023)
- **作者/出处**：Youssef Elmougy, Ling Liu（Georgia Tech）；ACM SIGKDD 2023。
- **链接**：https://arxiv.org/abs/2306.06108 ｜ 数据 https://github.com/git-disl/EllipticPlusPlus
- **核心**：扩展 Elliptic——**交易图**（每笔加 17 特征）+ **actors/钱包地址图**（822K+ 地址、56 特征、1.27M 时序交互）。支持「非法交易检测」和「非法地址检测」两类任务。
- **对项目四**：你的主数据集。地址图让你能做比原 Elliptic 更丰富的关系建模。

```bibtex
@inproceedings{elmougy2023ellipticpp,
  title={Demystifying Fraudulent Transactions and Illicit Nodes in the Bitcoin Network for Financial Forensics},
  author={Elmougy, Youssef and Liu, Ling},
  booktitle={ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD)}, year={2023}
}
```

### ⭐ Realistic Synthetic Financial Transactions for AML (NeurIPS 2023 D&B)
- **作者/出处**：Altman, Blanuša, von Niederhäusern, Egressy, Anghel, Atasu（IBM）；NeurIPS 2023。
- **链接**：https://arxiv.org/abs/2306.16424 ｜ NeurIPS 页见 papers.neurips.cc
- **核心**：**银行转账（非加密）**合成数据生成器 + 数据集（AMLworld），刻意贴近真实交易，并提供 **完整 ground truth**。
- **为什么升 ⭐**：它正面解决真实 AML 最大问题之一——真实数据标签天然不完整（大量洗钱从未被发现），导致 recall 评估失真；合成数据的完整标签让评估更诚实。可作为项目四「第二数据集」做银行场景对照，避免只懂加密。

### ○ The Shape of Money Laundering — Elliptic2 (2024)
- **作者/出处**：Bellei, Xu 等（Elliptic + MIT）。
- **链接**：https://arxiv.org/abs/2404.19109 ｜ 数据 https://github.com/MITIBMxGraph/Elliptic2
- **核心**：122K 个标注**子图**，背景图 49M 节点簇 / 196M 边——把 AML 重新定义为 **子图分类**问题，比 Elliptic1 大近三个数量级。
- **观点金句**：「AML 本质是一个**子图问题**，主流图技术一直在**次优的抽象层级**（节点级）上工作。」
- **⚠️ 定位**：**Research-grade，不建议 MVP 实现**。49M 节点簇 / 196M 边对本地资源和工程复杂度要求很高，应放最后一档。

## B. 结构感知 / 前沿方法

### ⭐ Provably Powerful GNNs for Directed Multigraphs (arXiv 2023 / AAAI 2024)
- **作者/出处**：Egressy, von Niederhäusern, Blanuša, Altman, Wattenhofer, Atasu（IBM + ETH）。
- **链接**：https://arxiv.org/abs/2306.11586 （arXiv 2023 预印本，会议版 AAAI 2024，年份以会议版为准）
- **核心**：用三个简单改造（**multigraph port numbering、ego IDs、reverse message passing**）把普通消息传递 GNN 变成「可证明强大」的有向多重图 GNN，理论上**能检测任意有向子图模式**；AML 少数类 F1 最高 +30%，并打平/超过 tree-based 与 GNN 基线（钓鱼检测也 +15%）。
- **对项目四**：这是 Research-grade 档的目标模型，也是「为什么普通 GNN 不够」的关键论据。

```bibtex
@inproceedings{egressy2024provably,
  title={Provably Powerful Graph Neural Networks for Directed Multigraphs},
  author={Egressy, B{\'e}ni and von Niederh{\"a}usern, Luc and Blanu{\v{s}}a, Jovan and Altman, Erik and Wattenhofer, Roger and Atasu, Kubilay},
  booktitle={AAAI Conference on Artificial Intelligence}, year={2024}
}
```

### ○ 综述/背景
- **Machine Learning for Blockchain Data Analysis: Progress and Opportunities** — https://arxiv.org/abs/2404.18251
- **Advances in Continual Graph Learning for AML Systems: A Comprehensive Review** — https://arxiv.org/html/2503.24259v1 （概念漂移 / 持续学习角度，呼应项目四的 temporal split）

---

## C. 动态 / 时序图（temporal graph）

> 区分两种「时序图」，否则「时序图」会写得太泛：
> - **Snapshot 时序图**：每个时间步一张图（如 Elliptic 的 49 steps）。EvolveGCN 属此类。
> - **Event-based 时序图**：每笔交易是带 timestamp 的事件流。TGN 属此类，更贴近真实交易流。

### ⭐ EvolveGCN: Evolving GCN for Dynamic Graphs (AAAI 2020)
- **作者/出处**：Pareja 等（IBM）。
- **链接**：https://arxiv.org/abs/1902.10191
- **核心**：用 RNN 演化 GCN 的权重以适应图随时间变化；Elliptic 原始论文（Weber 2019）即用它做时序实验，并显示图的时序价值在此处才更明显。
- **对项目四**：你做 temporal split / 动态图的**直接基线**，Reference-grade 档的时序模型。主文档提过它，这里单列为必读。

### ○ Temporal Graph Networks (TGN) for Deep Learning on Dynamic Graphs (2020)
- **作者/出处**：Rossi 等（Twitter）。
- **链接**：https://arxiv.org/abs/2006.10637
- **核心**：event-based 动态图的通用框架（node memory + message passing）。
- **对项目四**：Research-grade 扩展；不一定实现，但用来理解 event-based vs snapshot 的本质差异。

## D. AML 业务流程、交易监控与可解释性

> 把项目从「crypto graph classification」拉回「financial crime operations」——AML 面试常问：模型怎么进 transaction monitoring workflow、怎么降误报、怎么支持 investigator、怎么审计。解释的使用者是 compliance analyst / investigator，不是 ML 研究员。

### ⭐ Anti-Money Laundering Alert Optimization Using ML with Graphs
- **作者/出处**：Eddin 等（Feedzai / J.P. Morgan 背景）；2021。
- **链接**：https://arxiv.org/abs/2112.07508
- **核心**：真实银行 AML——规则系统产生 alerts，ML 做 **alert triage**，用图特征降低 false positive，同时保持较高 true positive detection。
- **对项目四**：比纯 Elliptic 更接近金融机构工作流；直接支撑 precision@k + human review budget 的叙事。

### ⭐ GNNExplainer: Generating Explanations for GNNs (NeurIPS 2019)
- **作者/出处**：Ying, Bourgeois, You, Zitnik, Leskovec（Stanford）。
- **链接**：https://arxiv.org/abs/1903.03894
- **核心**：图解释的基础方法——为单个预测输出关键子图 / 关键邻居 / 关键边 / 关键特征。
- **对项目四**：输出可疑地址的 ego-subgraph。⚠️ 解释目标要**业务化**：不是解释「模型为什么分数高」，而是「这个 alert 为什么值得 investigator **优先看**」。

### ○ Machine Learning in Transaction Monitoring: The Prospect of xAI
- **核心**：transaction monitoring 中不同责任方对 xAI 的需求、审计与责任边界。
- **对项目四**：把 GNNExplainer 从「技术展示」提升到「合规 / 审计叙事」。

## E. 不平衡与半监督图学习

> AML 的少数类问题不是普通 class imbalance——图结构让 oversampling 更复杂（新合成节点还要有合理的边关系）。

### ○ GraphSMOTE: Imbalanced Node Classification on Graphs (WSDM 2021)
- **作者/出处**：Zhao, Zhang, Wang。
- **链接**：https://arxiv.org/abs/2103.08826
- **核心**：在嵌入空间合成少数类节点并生成边，说明普通 SMOTE 不能直接套到图节点。
- **对项目四**：⚠️ **扩展，不要一开始就做**。MVP 用 class_weight / focal loss / threshold tuning / precision@k 即可；GraphSMOTE 属升档。

---

## 项目可执行分层表（读完怎么落地）

> 作用：防止项目被 Elliptic2 / Egressy 这些高难内容拖成纯研究项目——先把每档跑通再升档。

| 层级 | 目标 | 论文支撑 |
|---|---|---|
| **MVP** | Elliptic++ EDA + XGBoost baseline + temporal split | Weber 2019, Elmougy 2023 |
| **Reference-grade** | GraphSAGE/GAT + precision@k + investigator budget + EvolveGCN 时序 | Weber, Elmougy, EvolveGCN, Eddin |
| **Strong** | EvolveGCN/TGN + GNNExplainer 业务化解释 | EvolveGCN, TGN, GNNExplainer |
| **Research-grade** | Elliptic2 子图分类 / 有向多重图 GNN | Bellei 2024, Egressy 2024 |

---

## 为什么用图学习，而不是其它 ML 范式（项目四 README「动机」核心）

> 论点结构：先讲图为什么**结构上**能看到表格看不到的东西 → 再讲一个**诚实反论点**（图不自动赢）→ 落到一个**站得住的论题**。

### 论据 1：洗钱是「关系」，单笔交易特征看不到
洗钱的定义性特征是**资金流的拓扑**——分层（layering）、smurfing（拆分）、fan-in/fan-out、环路、过桥地址。XGBoost 等表格模型把每笔交易**孤立**看，只能学「单笔的异常特征组合」；GNN 通过消息传递在交易图上**传播邻居信息**，天然能编码这些关系结构（主论据 Weber 2019；NVIDIA / Thoughtworks 工业博客仅作辅助佐证，README 核心论证用论文，不让博客承担论证权重）。

### 论据 2：AML 本质是「子图/motif 检测」问题
Elliptic2（Bellei 2024）直接论证：节点级是**次优抽象层级**，洗钱有特征性的「形状」（subgraph shapes）。更深一层，Egressy 2024 证明**普通消息传递 GNN 在理论上也不够**——区分不了某些有向多重图模式、数不清 motif；需要 port numbering / ego ID / reverse MP 等改造才能检测任意子图模式。所以「为什么用图」的完整答案不止「用 GNN」，而是「**用结构感知的图模型**」。

### 论据 3（诚实反论点，务必写进项目）⚠️
**「图 > 表格」并不自动成立。** 在原始 Elliptic 上，调好的 **Random Forest / XGBoost（用节点特征）常能打平甚至超过普通 GCN**——Weber 2019 自己就报告了 RF 强于 GCN。原因：Elliptic 的节点特征已经聚合了不少局部信息；浅层 GCN 的过平滑也会损失判别力。

因此**真正的图增益**来自三处，而非「换个 GNN」：
- **时序图**（EvolveGCN）：捕捉随时间演化、应对概念漂移；
- **结构感知 GNN**（Egressy）：检测表格根本无法表达的子图模式；
- **混合范式**（NVIDIA blueprint）：把 GNN 节点 embedding 当作**特征工厂**，拼接进 XGBoost 做最终判定——往往比单独任一方更强。

### 站得住的论题（写进 README）
> 「图模型能捕捉表格模型在**结构上无法表达**的关系/子图信号；但在弱基线上图不自动获胜。本项目用调优的 XGBoost 作为**诚实对照**，量化图结构在何种条件下（时序、结构感知、混合）才真正带来增益，而非默认 GNN 更好。」

这条论题同时满足两件事：(1) 展示你懂图学习的真正价值与边界；(2) 延续你「诚实评估」的一贯风格（见项目一）。它也直接解释了项目四的步骤设计——**表格 baseline 不是陪衬，而是检验图是否有用的对照组**。

### 对评估的影响（呼应主文档项目四指标）
- 用 **precision@k / recall@k + human review budget** 而非整体 F1（AML 团队按调查容量看 top alerts）。
- 真实 AML 标签**不完整**（论据见 Altman 2023），所以在真实数据上的「低 recall」要谨慎解读；这也是合成数据（完整 ground truth）作对照的价值。
- 合规需要可解释：GNNExplainer / 重要子图，向反洗钱团队说明「为什么这笔/这个地址可疑」。

---

## 主线重定位（2026-07-01）：queue disagreement = scoring granularity vs label provenance

> 卖点从「Elliptic++ 上做 AML-GNN」升级为 **"When AML queues disagree: scoring granularity or label provenance?"**
> 核心原创点（跨过下方 Malik）：把交易队列 vs actor 队列的不一致**拆成来源**，并指出
> **Elliptic++ 钱包 illicit 标签是交易标签的确定性 guilt-by-association 传播**（`wallet-illicit ⟺ 参与过 ≥1 illicit 交易`，
> 双条件零例外）——一址一枚、事后/全局、**标签无活动时间语义**（≠ 活动跨期：92.5% 地址单时间步、可 temporal 排序），
> 故 actor 标签非独立监督、干净切分也堵不住事后标签泄漏。（旧写"跨最多 47 步→无法 temporal"已被数据证伪，见 CLAUDE.md 纠错。）
> 执行/指标/2×2 硬约束见 `04-aml-gnn/CLAUDE.md`「主线设计」。

### ⭐ Malik 2026 — Do Transaction-Level and Actor-Level AML Queues Agree?（arXiv:2604.23494，已核实）
- **核心**：Elliptic++ 上用 RF + 聚合算子比较 transaction-level vs actor-level 调查队列；1% 预算下
  Jaccard **0.374（temporal）/ 0.087（static）**——同数据同预算下两队列几乎不重叠。
- **定位（跨过它）**：Malik 止于「队列不一致」。我们进一步**归因**（projection loss / label conflict /
  coverage gap，归因非加法），并揭示不一致的 temporal/static 差距很可能主要由**全局钱包标签的 retrospective 性质**驱动。
- **已实测（2026-07-01，`notebooks/05` + `reports/aggregation-fanout-granularity.md`）**：聚合扇出 max/mean/sum/top-k 后，
  **granularity 是队首现象**（0.5% 预算 mean-vs-max 队列 Jaccard≈0.17、5% 收敛回≈0.89，整体 PR-AUC 掩盖之），
  且**不独立于 provenance**——钱包标签是交易标签的 OR/max 传播 ⇒ **max 是匹配算子、整体 PR-AUC 最高**（近乎同义反复、非检测力背书）。
  → 两轴纠缠、非二选一，比 Malik 的「队列不一致」多出一层机制解释。

### ⭐ Deprez et al. 2024 — Network Analytics for AML: SLR + 实验评估（arXiv:2405.19383，已核实）
- **核心**：97 篇系统综述 + 统一实验；结论「多数仍用专家规则/人工特征，DL 渐起；**类不平衡与拓扑下用 GNN 要当心**」。
- **对项目**：直接背书「传统网络特征+树模型仍具竞争力」的诚实对照，是 tabular baseline 的文献靠山。

### ○ Nguyen et al. 2025 — SAGE-FIN：半监督 GNN + Granger-causal 解释（arXiv:2507.01980，已核实）
- Elliptic++ 上做弱/未标注数据；Reference 档读物。⚠️ Granger 因果解释在复杂交易图能否真解释业务因果需审计。

### ○ Zheng et al. 2025 — ATGAT：temporal-aware GAT（arXiv:2506.21382，已核实）
- 报 **AUC 0.9130**（宣称超 XGBoost/GCN/GAT）。⚠️ **只报 ROC-AUC、不平衡集上信息量低**——只当 baseline 参考，**绝不当目标**。

### 当下必读三篇（其余留升档）
1. **Elmougy 2023**（Elliptic++ 数据结构 / AddrTx-TxAddr 映射——做投影要用）；
2. **Malik 2026**（定位到「跨过他」）；
3. **Deprez 2024**（引「传统模型仍竞争力」）。
