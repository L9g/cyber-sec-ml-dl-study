# 知识库：DS / ML / DL × Cyber-Security

> 这是**持久参考层**，不是项目文档。目标：长期积累本领域有影响力/有用的论文与材料，按主题组织、可检索。
> 与 `docs/projectN-reading-list.md` 的分工见下面「两层怎么分工」。

---

## 两层怎么分工（重要）

| | 知识库（本目录） | 项目阅读清单（`docs/projectN-reading-list.md`） |
|---|---|---|
| **职责** | 广度——某主题该知道的东西 | 克制——交付该项目的**最小必读集** |
| **增长** | 自由生长，只增不删（除非证伪） | 严格控制，多了就是稀释 |
| **组织** | 按知识主题 T1–T8 | 按项目、按交付阶段（MVP→Research-grade） |
| **引用** | 一句话 takeaway + tag + bibkey | 详细笔记 + 实验产物映射 |

> 项目清单**不复制** BibTeX，按 bibkey 引用 `references.bib`。这样项目清单保持精简，知识库随便长，互不污染。

---

## 约定（conventions）

- **唯一引用源**：所有 BibTeX 只放 `references.bib`。别处一律按 `bibkey` 引用，不再粘贴 BibTeX。
- **bibkey 规范**：`authorYYYYkeyword`（全小写），如 `arp2022dodonts`、`weber2019aml`。
- **每篇一句话 takeaway**：进知识库的门槛是「我能用一句话说出从它拿到什么」。说不出 → 还没真读，先标 🔖。
- **状态标签**：`⭐ 核心` ｜ `○ 参考` ｜ `🔖 待读` ｜ `✅ 已读`。
- **喂给哪个项目**：P1 NIDS ｜ P2 Prompt-Injection ｜ P3 SIEM/SOC ｜ P4 AML ｜ `—` 通用基础。
- **待核**：作者/venue/页码没核实的，在 `references.bib` 里标 `note = {待核}`，落地引用前二次确认。

---

## 主题分类（taxonomy）

🌱 已有种子 ｜ 📋 计划中（随项目推进填充）

| 主题 | 范围 | 状态 |
|---|---|---|
| **T1** 安全 ML 方法学与诚实评估 | 评估偏差、data snooping、base-rate、方法论陷阱 | 🌱 |
| **T2** NIDS / 网络流量、数据集与跨数据集泛化 | 流量数据集、特征集、LODO、数据质量 | 🌱 |
| **T3** 图学习与金融犯罪 (AML) | GNN、动态图、子图检测、可解释、不平衡 | 🌱 |
| **T4** 对抗 ML 与鲁棒性 | 现实威胁模型、evasion、动态防御 | 🌱 |
| **T5** LLM / Agent 安全（prompt injection） | AgentDojo、防御范式 | 📋 (P2) |
| **T6** SIEM / SOC / 日志与横向移动 | Mordor/EVTX/BOTS、图横向移动、LLM 解释 | 📋 (P3) |
| **T7** 数据治理、合规与英国监管 | NCSC/GDPR/FCA·PRA SS1/23/AISI、model risk | 📋 |
| **T8** 表示学习 / 安全基础模型 | 流量/日志自监督预训练 | 🌱 |

> 单个主题论文变多时，从本 README 拆出 `topics/Tx-xxx.md` 独立文件。现阶段集中在此处够用。

---

## 主索引（master index）

### T1 · 安全 ML 方法学与诚实评估
| 状态 | bibkey | 一句话 takeaway | 项目 |
|---|---|---|---|
| ⭐✅ | `sommer2010outside` | 找攻击 ≠ 一般 ML：极低基率 + 高误报代价 + 缺标注 + 闭世界不成立 | — / P1 |
| ⭐🔖 | `arp2022dodonts` | 安全 ML 的 10 大方法论陷阱——项目一「乐观 vs 诚实」对比表的理论骨架 | P1（全部） |
| ○🔖 | `apruzzese2023sok` | 从从业者「部署后值不值」视角评估 NIDS，而非刷分视角 | P1 |
| ⭐🔖 | `pendlebury2019tesseract` | temporal/spatial bias + AUT 指标；⚠️ 原域 malware，迁方法非数据 | P1 |
| ⭐🔖 | `axelsson2000baserate` | 极低基率下高检测率也被误报淹没——base-rate fallacy 奠基文献 | P1 |

### T2 · NIDS / 网络流量、数据集与跨数据集泛化
| 状态 | bibkey | 一句话 takeaway | 项目 |
|---|---|---|---|
| ⭐🔖 | `engelen2021troubleshooting` | CICIDS2017 流构造/标注系统性错误，重标 20%+ 流 | P1 |
| ⭐🔖 | `lanvin2023errors` | CICIDS2017 packet misorder/漏标，引入 "X–Attempted" 标签 | P1 |
| ⭐🔖 | `sarhan2021standardfeature` | 把多数据集统一成 43 个 NetFlow 特征（NF-v2），跨数据集公平比较 | P1 |
| ○🔖 | `sarhan2022evaluating` | 统一特征集既利于泛化也利于解释 | P1 |
| ⭐🔖 | `crossdataset2024nids` | 同数据集内近完美，跨数据集常近随机——LODO 实验要复现的结论 | P1 |
| ⭐🔖 | `ring2019survey` | 数据集选择本身就是 NIDS 研究的核心风险 | P1 |
| ○🔖 | `moustafa2015unswnb15` | UNSW-NB15 九类攻击/采集环境/标签语义 | P1 |
| ○🔖 | `tavallaee2009nslkdd` | KDD99 冗余与缺陷——为什么不拿老数据集作主实验 | P1 |

### T3 · 图学习与金融犯罪 (AML)
| 状态 | bibkey | 一句话 takeaway | 项目 |
|---|---|---|---|
| ⭐🔖 | `weber2019aml` | 发布 Elliptic；⚠️ RF（节点特征）强于普通 GCN，图增益靠时序 | P4 |
| ⭐🔖 | `elmougy2023ellipticpp` | Elliptic++：交易图 + 钱包地址图，支持非法交易/地址两类任务 | P4（主数据集） |
| ⭐🔖 | `altman2023synthetic` | 银行转账合成数据 + 完整 ground truth，解真实标签不完整问题 | P4 |
| ○🔖 | `bellei2024shape` | Elliptic2：把 AML 重定义为子图分类；节点级是次优抽象层级 | P4（Research） |
| ⭐🔖 | `egressy2024provably` | port numbering/ego ID/reverse MP 让 GNN 可证明检测任意有向子图 | P4（Research） |
| ⭐🔖 | `pareja2020evolvegcn` | 用 RNN 演化 GCN 权重适应图随时间变化——snapshot 时序图基线 | P4 |
| ○🔖 | `rossi2020tgn` | event-based 动态图通用框架（memory + MP），区别于 snapshot | P4（Research） |
| ⭐🔖 | `ying2019gnnexplainer` | 为单个预测输出关键子图/邻居/边/特征——业务化为「为何优先看」 | P4 |
| ○🔖 | `zhao2021graphsmote` | 图上少数类要合成节点+生成边，普通 SMOTE 不能直接套；属升档 | P4（扩展） |
| ⭐🔖 | `eddin2021aml` | 真实银行 AML：规则出 alert，ML 做 triage，图特征降误报 | P4 |

### T4 · 对抗 ML 与鲁棒性
| 状态 | bibkey | 一句话 takeaway | 项目 |
|---|---|---|---|
| ○🔖 | `apruzzese2021modeling` | 真实攻击者不用梯度白盒，威胁模型必须现实 | P1（扩展） |
| ○🔖 | `evasion2023impractical` | 反主流：多数学术对抗攻击在现实约束下不实用，动态模型更难绕 | P1（扩展） |

### T8 · 表示学习 / 安全基础模型
| 状态 | bibkey | 一句话 takeaway | 项目 |
|---|---|---|---|
| ○🔖 | `lin2022etbert` | 加密流量字节当「语言」自监督预训练；擅长应用分类≠解决 NIDS 泛化 | P1（扩展） |

---

## 待填（next）

- **T5 / T6 / T7** 随项目二、三推进补充（prompt injection、SIEM 日志、UK 治理）。
- 综述/工业材料（NVIDIA AML blueprint、blockchain ML survey 2404.18251、continual graph learning AML 2503.24259）：仅作辅助佐证，**不进主索引承担论证权重**，需要时单列 `topics/_industry-notes.md`。
