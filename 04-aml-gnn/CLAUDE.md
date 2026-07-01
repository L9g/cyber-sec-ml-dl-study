# Rules — 04-aml-gnn（项目四：金融犯罪 / AML 图学习）

继承工作区根 `../CLAUDE.md` 通用约束。本文件只列项目四特定规则。
卖点 = **标签来源泄漏（label provenance / selective labeling）下的可信 AML 分诊**，
不是 Elliptic 上刷 GNN AUC。详见 `README.md` 与主线文档 §三 项目四。

## Codex 项目记忆
- Codex 专用项目记忆在 `.codex/memory/`。新会话开始或做方法学决策前，先读：
  `.codex/memory/index.md`、`.codex/memory/current-context.md`、`.codex/memory/decisions.md`。
- 用户说“存记忆 / 保存上下文 / 把这个结论存进项目上下文”时，优先更新 `.codex/memory/`；
  若内容面向项目读者，再同步到 `reports/*.md` 或 README 链接。
- `.codex/memory/` 只存稳定项目事实、决策和待办；不要存原始数据、密钥、token、长篇论文摘录。

## 数据基座（Elliptic++）
- 主数据 = **Elliptic++**：交易图 + 地址图，托管在 Google Drive（非 git），用 `gdown --folder` 拉到 `data/raw/`。
  下载/许可/文件清单见 `data/README.md`。**原始数据不入 git**（2.1G）。
- ⚠️ **许可未显式声明**：仅作学术/求职演示，引用 Weber 2019 + Elmougy 2023；商业用途前须向作者核实。
- 标签编码（见 `config.py`）：**1=illicit, 2=licit, 3=unknown(未标注)**。`unknown ≠ licit`——这是 label-provenance 审计的核心。
- 已核实事实（2026-06-30）：交易 203,769 笔 / 49 时间步；illicit=4,545（占**已标注** 9.76%、占全体 2.23%）；
  地址 822,942（illicit=14,266）。**PR-AUC 随机基线 = illicit 占比（已标注内 ≈0.098），不是 0.5**——报告必带。

## 主线设计（2026-07-01 锁定）
卖点重定位为 **"When AML queues disagree: scoring granularity or label provenance?"**（见 README）。硬约束：
- **2×2**：{transaction scoring, actor scoring} × {transaction label, wallet label}。对角=原生任务，off-diagonal=评估单元/标签口径错配格（是审计对象，不是四个并列模型）。
- **join 已验证可行**（2026-07-01）：AddrTx txId ∩ txs_classes = **99.53%**、AddrTx 地址 100% 被 wallets_classes 覆盖 → 投影/2×2 可建。
- **【2026-07-01 纠错】actor provenance 病根 = 标签结构无时间维，不是活动跨期**。原写"每地址跨最多 47 步→无法做真 temporal"这条**佐证已被数据证伪**：input+output 合并测得 **92.5% 的 actor 只出现在单一时间步**（跨 split 边界 ≤34&>34 的 actor 仅 10,471 个、其中 illicit **仅 49 个**），故 actor **完全可以按活动时间做 temporal split**，activity-span 泄漏在量上可忽略。真正的病根是 **`wallets_classes` 一址一枚不可变 class、无 per-time-step 地址标签 → 标签本身没有活动时间语义**：即便把单步 actor 干净切进测试期，它带的仍是建库时对全链历史的**事后/全局裁定**（编码了活动时当时拿不到的未来信息）。→ 这是**项目一「切分干净 ≠ 特征干净」在标签层的复现**（干净 actor temporal split 也堵不住事后标签泄漏），是最锋利的 provenance 发现。操作纪律不变：actor-label 的 temporal 结果标 "retrospective"、配 static 对照、**不与 tx temporal 直接同类比**。⚠️ **不预答**旗舰问句（granularity vs provenance 谁主导队列不一致，由 yield 对照+归因表挣，见下）。
- **【2026-07-01 数据坐实】钱包 illicit 标签 = 交易 illicit 标签的确定性传播**：`wallet-illicit ⟺ 地址参与过(input 或 output)≥1 illicit 交易`，**14,266/14,266 双条件零例外**（licit 侧 0 污染）。即 actor illicit 标签是 tx 标签的 OR/max 传播（guilt-by-association、事后/全局）。后果：(1) actor 标签**非独立监督**（= tx 任务透过 max 算子再看一遍），把 "actor-level PR-AUC 0.736" 当独立成绩报是误导；(2) illicit 类上 tx 与 wallet 标签**构造上不可能冲突** → 本切片队列不一致 = **unknown 覆盖缺口(69%)** + detection-miss，**不是** illicit 的 label-conflict；⚠️ **scoring granularity/投影损失在 max 下 ≡0**（transaction-first≡actor-first，Jaccard=1），是 mean/sum 聚合才有的现象、不能拿 §2 的 tx-vs-actor yield 差冒充（那是口径差、符号随预算翻转）。这是数据不变量、不预答模型比较。见 `notebooks/04` §3/§5。
- **【2026-07-01 granularity 扇出已做，见 `notebooks/05` + `reports/aggregation-fanout-granularity.md`】** mean/sum/top3 解除 max 退化后，granularity 成实腿，形态：(1) **分歧是队首现象**——0.5% 预算 mean-vs-max 队列 Jaccard≈0.17，5% 收敛回≈0.89（多数地址单笔交易→四聚合恒等，分歧只来自被推上队首的少数多笔地址）；(2) **整体 PR-AUC 掩盖之**（max 0.7362 仅比 mean 高 0.016，又一次「报曲线不报单点」）；(3) **投影损失格填上但双向**（1% 预算 mean 从 max illicit 队首掉 785／另捞 567＝重排非单调损失）；(4) **对称 volume bias**（队首 mean n_tx：sum 5.1↑／mean 1.5↓／max 2.6 居中）；(5) **granularity 不独立于 provenance**——标签 OR/max 传播 ⇒ **max 是匹配算子、PR-AUC 最高（近乎同义反复，非检测力背书，回溯循环仍在）**。两轴纠缠、非二选一。
- **单一 split 口径 = temporal**（MVP）；static/random 仅作 actor retrospective 的解释性对照表，不进主结果叙事。
- **归因非加法**：queue disagreement 拆成 projection loss / label conflict / coverage gap 用**归因/列联表**（对每个只进一队列的 actor 判主导成因），**禁写 `= A+B+C` 等式**（会 over-claim，砸诚实签名）。
- **聚合策略即风控决策**：actor 投影审计 max / mean / top-k / sum(volume bias) / time-decay / counterparty-weighted；不是 scope creep，是 projection 核心。
- **"unknown≠benign"** 专节：设置 A 只在 labeled 评估 / B unknown excluded / C unknown 当 benign（错误示范）/ D PU-learning 或纯 ranking。
- **薄切片优先**：先 tx baseline→单一聚合(max)→一条 yield 对照曲线→设置C→归因表雏形跑绿，再扇出其余聚合/audit。
- 主线旗舰文档 `docs/*-v2.md` 项目四章节**等薄切片跑绿再改**，避免代码前把方向说死。

## 分档与执行（先 MVP 再升档，别被 GNN 卡住）
- **MVP = 纯表格 LightGBM**（不碰 GNN）：EDA + temporal split + baseline。这是项目四能独立交付的最小档。
- 表格 baseline **不是陪衬，是检验「图是否真有用」的诚实对照**（Weber 2019 自报 RF 强于普通 GCN）。
  「图 > 表格」不自动成立——增益只来自时序 / 结构感知 / 混合，写进 README 论点。
- 升档顺序：Reference（GraphSAGE/GAT + EvolveGCN）→ Strong（GNNExplainer + Decision Card）→ Research（Elliptic2 / Egressy 有向多重图）。

## 切分（AML 最常被审计质疑的点）
- **Temporal split**：按时间步切（如前 34 训 / 后 15 测），绝不用未来预测过去。绝对时间步只排序、不进特征。
- 明确区分 **transductive（测试节点训练时已见）vs inductive（完全未见）**，两套设定各自给结论。
- 同一地址/实体跨 split 泄漏 → 按实体/时间 **group split**（呼应项目一重复流泄漏）。

## 指标（按真实 AML 工作方式，不报裸 F1）
- 主 **PR-AUC**（基线=illicit 占比）；precision@k / recall@k + **human review budget**。
- **报曲线不报单点**：yield@budget / coverage@abstention 曲线；单点指标随阈值漂移（项目一 §2.1 教训）。
- **`pr_auc − base_rate` 只任务内 sanity**（tx 基线 9.8% vs actor 5.4%，PR-AUC 对 prevalence 非线性）；
  **跨任务只比 operational curves**（yield@budget / queue overlap / top-k yield）。tx vs actor 的重点是
  **队列是否一致 + 标签口径是否可比**，不是谁 PR-AUC 高。

## 测试（两层，别混写，同根 CLAUDE.md）
- 代码契约（确定性，如标签映射 / temporal split 边界 / upsert）→ `src/tests/` pytest，贴死精确值。
- 叙事回归（模型分数相关）→ notebook 内嵌 `test_` cell，只用方向性带 margin 断言（如 `pr_auc - illicit占比 > X`），禁硬阈值。

## 命令
```bash
.venv/bin/gdown --folder "<Drive>" -O data/raw    # 拉数据（见 data/README.md）
.venv/bin/pytest src/tests/                        # 代码契约单测
.venv/bin/pytest notebooks/03_nongnn_baselines.py  # 单个 notebook 叙事回归
.venv/bin/pytest notebooks src/tests               # 目录口径；pytest.ini 收 0*_*.py notebook
```
