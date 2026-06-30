# 相关工作与视角 — 谁也在用这个数据集、发现了什么

> 范围：项目一主数据集 = **NetFlow-v3 统一系列**（Sarhan et al. 扩展到 53 特征，含真 IP + 真时间戳；
> NF-UNSW-NB15-v3 / NF-ToN-IoT-v3 / NF-CSE-CIC-IDS2018-v3；论文 arXiv 2503.04404）。
> 此文档写于迁 v3 之前（2026-06-27），视角中对 v2/v3 的引用视上下文解读。
> 本文件回答两个问题：**(1) 近期还有谁用这个数据集、做出了什么不同的发现；(2) 这些发现对项目一是强化还是挑战。**
>
> **核实约定**：每条标 `发表载体 / 评审状态 / 核实方式`。
> 核实方式：✅原文摘要页已读 ｜ ⚠️仅二手搜索摘要 ｜ ❌未读。
> 关联到 [[findings.md §0]] 的方法局限，以及记忆 `project-cyber-ml-portfolio`。
> 整理日期 2026-06-27。

---

## A. 真正使用 NetFlow-v2 / NF-* 数据集的论文（直接回答原问题）

| # | 论文 | 发表载体 | 评审 | 核实 | 用了哪个 NF | 与项目一关系 |
|---|---|---|---|---|---|---|
| A2 | **Layeghy & Portmann (UQ)**, "Explainable Cross-domain Evaluation of ML-based NIDS"（预印本旧题 "On Generalisability of ML-based NIDS", arXiv 2205.04112） | **Computers & Electrical Engineering** Vol.108, 2023 (Elsevier) | ✅同行评审期刊 | ✅核实 | NFv2 四件套（UNSW/CIC-2018/ToN/BoT） | **强化**：NF-v2 跨数据集崩塌的**正主引用**。8 个有/无监督模型无一跨全部数据集泛化；无监督>有监督；源/目标互换不对称 |
| A2b | **Popoola, Gui, Adebisi, Hammoudeh, Gacanin**, "Federated Deep Learning for Collaborative Intrusion Detection in Heterogeneous Networks" | **IEEE VTC2021-Fall**, 2021, pp.1–6（Cantone ref[48]） | ✅同行评审会议 | ⚠️引文已确认；数字经两处二手（Cantone + 检索摘要）一致佐证，原文 PDF 付费未读 | NF-v2 四件套，训练 NF-ToN-IoT-v2 | **强化**：**中心化基线** within F1 94.91% → cross 78.96/29.19/62.83（在 NF-UNSW-NB15-v2/NF-BoT-IoT-v2/NF-CSE-CIC-IDS2018-v2）。注：该文卖点是 FL 把跨集拉回，故这串是 baseline 非主结果 |
| A3 | Temporal Analysis of NetFlow Datasets / **NF3-Datasets**（Luay, Layeghy, Sarhan, Moustafa, Portmann 等） | 预印本，引 IEEE Access 2026 DOI（应已录用） | ⚠️作者=数据集原作者 | ✅ | 由同源造第三代 NF3 | **⚠️挑战**（见下） |
| A4 | Always be Pre-Training: Representation Learning for NIDS with GNNs（Gu 等） | **ISQED'24** 会议 | ✅同行评审 | ✅ | NF-UQ-NIDS-v2 | **正交**：自监督预训练，<4% 标签达 SOTA 98% |
| A5 | Self-supervised Learning for NIDS with GNN（Xu 等） | 预印本（无 venue） | ⚠️预印本 | ✅ | NF-BoT-IoT(/-v2)、NF-CSE-CIC-IDS2018(/-v2) | **正交**：图对比学习，自称首个 GNN 自监督多分类 |
| A6 | BigFlow-NIDS（Uddin 等） | **Data Brief** 2026 (Elsevier) | ⚠️数据描述刊（轻量评审） | ✅ | 合并 NF-*-**v3** + Spark 去重 → 66.9M 流 | **强化**（仅作"v3 去重数据集存在"证据，非分析结论） |
| A7 | GNN + Scattering Transform for Anomaly Detection（Zoubir, Missaoui） | 预印本 | ⚠️预印本 | ✅ | 摘要只说"benchmark NIDS datasets"，**NF 未明写** | 正交（⚠️数据集待核，否则降级） |

## B. 主题高度相关、但**不使用** NetFlow-v2 的批判性参考（做 related-work 框架，别冒充成数据集用户）

| # | 论文 | 发表载体 | 评审 | 核实 | 实际用的数据集 | 价值 |
|---|---|---|---|---|---|---|
| B1 | **Network Intrusion Datasets: A Survey, Limitations & Recommendations**（Goldschmidt, Chudá） | **Computers & Security** 2025 (vol.156, art.104510) | ✅顶刊 | ✅ | 综述 89 个数据集（含 NF 系列） | **承重支柱**：把"数据集普遍有方法学缺陷"系统化 |
| B2 | **Machine Learning on Public Intrusion Datasets: Academic Hype or Concrete Advances in NIDS?**（Catillo, Pecchia, Villano, Univ. Sannio） | **DSN-S 2023**（IEEE/IFIP 顶会增补卷, pp.132–136, 短文） | ✅顶会（短文档） | ✅核实数据集 | **CICIDS2017 / USB-IDS-1 / UNSW-NB15（非 NF-v2）** | **同主题背书**：公共数据集上的"完美指标"无法迁移到实际 |
| B3 | Flow Exporter Impact on Intelligent IDS（Pinto, Vitorino 等, GECAD Porto） | **ICISSP 2025** 会议 | ✅中小型会议 | ✅ | 用 HERA 导出器处理两个 benchmark（非确认 NF-v2） | **强化**：特征提取器本身是混杂源，结果随之变 |
| B4 | On the Cross-Dataset Generalization of ML for NIDS（Cantone, Marrocco, Bria） | **IEEE Access** 2024 (vol.12, 144489–144508) | ✅同行评审（巨型刊） | ✅核实数据集 | **CIC-IDS2017 / CSE-CIC-IDS2018 / LycoS-IDS2017 / LycoS-Unicas-IDS2018（非 NF-v2）** | **强化（异数据集）**：within MCC 94.63% → cross 29.35%，"与随机猜测相当"。⚠️ 原归 A 组系误判，实不用 NF-v2 |
| B5 | **Layeghy, Gallagher, Portmann (UQ)**, "Benchmarking the benchmark — Comparing synthetic and real-world Network IDS datasets"（arXiv 2104.09029） | **JISA** Vol.80, 2024, art.103689 (Elsevier) | ✅同行评审期刊 | ✅核实摘要；⚠️数据集仅"CIC/UNSW/+1"，**未确认是否 NF-v2 标准版** | 三个合成数据集 vs 两个真实网（大学网 + 中型 ISP），Wasserstein 距离 | **强化+挑战**：合成 benchmark 与真实流量统计分布**显著不同** → 近 100% 学术成绩未必迁到真实网。见视角 8 |

## C. 已剔除（核实后判定为噪声）

| 论文 | 剔除理由 |
|---|---|
| Shortcut Features as Top Eigenfunctions of NTK（NeurIPS 2025, 2602.03066） | 纯 ML 理论，与 NIDS 无关，关键词撞车 |
| Categorical Robustness Assessment for ML-NIDS（2606.12075） | 用 ACI-IoT-2023，非 NF-v2 |
| ML for Network Attacks Classification（IEEE ISCC 2026, 2603.17717） | 用 CIC-IDS-2017/UNSW-NB15 **原版**，非 NetFlow-v2 标准化版 |
| When Unknown Threat Meets Label Noise（IEEE TQ early-access） | 不可验证（卷号占位 5555），数据集未确认 |
| Deep Learning for Contextualized NetFlow NIDS（2602.05594） | taxonomy 综述、不直接用数据集；可留作综述参考但不进清单 |

---

## 七个视角（学界/业界用这个数据集做出的不同发现）

每条标【强化/挑战/正交】+ 代表论文 + 置信度。

1. **【强化】跨数据集泛化崩塌：模型学的是数据集而非攻击。** in-distribution 近乎完美、跨数据集逼近随机，这是跨多份数据集都复现的硬结论。已核实的两组数字：
   - **NF-v2 上（正主，A2/A2b）**：Popoola VTC2021（A2b，引文已确认）**中心化基线** within F1 94.91% → cross 78.96/29.19/62.83；注意该文用 FL 把跨集拉回，引用时须说明这是 baseline。LODO 范式另见 A2（UQ）。
   - **CIC/LycoS 上（B4, IEEE Access 2024，已核实原文）**：within 平均 MCC **94.63%** → cross **29.35%**，"与随机猜测相当"。
   - ✅ **更正记录**：曾把 94.9%→78.96/29.19/62.83 误植为 B4(Cantone) 的结果；实为 Popoola 联邦学习(NF-v2)数字、被 B4 在相关工作里转引。B4 本身不用 NF-v2。

2. **【挑战】标准 43 特征集本身缺时序维度（NF3, A3）。** 由数据集原作者指出：v2 没有
   inter-packet arrival time 等时序特征，故造第三代 NF3 补上。**这削弱"temporal split 揭示时间泄漏"
   的卖点**——见 [[findings.md §0]]：本项目所用 dhoogla 镜像连 per-flow 绝对时间戳都没有，只有
   FLOW_DURATION。**应对**：把主轴放在 v2 上确实成立的 **IP 泄漏 + 重复流泄漏 + LODO**，
   temporal split 降级为辅助，或引入 NF3 时序特征做对照。

3. **【强化】特征提取器是混杂源（B3）。** 同一份流量，nProbe / CICFlowMeter / HERA 提取，结果显著不同。
   给"benchmark 不可复现/虚高"叙事加一个新维度，也解释修正版 CICFlowMeter（Engelen）为何重要。

4. **【强化】重复流 = 隐性泄漏，社区已转向显式去重（A6）。** BigFlow 在合并 v3 时专设 Spark 去重管线，
   等于承认 v2 有重复流问题；重复会让随机切分时训练/测试泄漏。呼应 [[findings.md §0]] 镜像"已去重"。
   ⚠️ A6 是 Data Brief 数据描述，引它证明"去重是公认步骤"可，**不能当"重复是已证实泄漏"的分析定论**。

5. **【正交】图视角 / 自监督表示（A4/A5/A7）。** 把 NetFlow 从"独立表格行"重构为主机-流图，
   或自监督预训练降低标签依赖。多数仍追 in-distribution 分数；"图视角能否改善跨数据集泛化"是开放问题，
   可作项目延伸方向。

6. **【强化·框架】整个领域评估方法学有病（B1/B2）。** C&S 2025 顶刊综述（B1）+ DSN 2023 顶会
   "学术炒作还是真进步"（B2）。**这是 related-work 的两根支柱。**

8. **【强化+挑战·新角度】真正的鸿沟也许是"合成 vs 真实世界"，而非"合成 A vs 合成 B"（B5, JISA 2024, UQ 团队）。**
   用 Wasserstein 距离比合成 NIDS 数据集与真实生产网（大学网 + ISP）的良性流量分布，发现两者**显著不同**。
   **对项目一的双刃**：(a) 强化"benchmark 虚高"主框架；(b) **挑战**——项目一只在合成 NF-v2 内部做诚实评估
   （A≠B 跨数据集），并未触及"整组合成 benchmark 可能都偏离真实网络"这一更深层问题。这是项目
   目前的空白，可作为"已知局限"诚实写明，或作为项目延伸（拿真实流量做分布对照）。⚠️ B5 数据集是否 NF-v2 标准版未确认。

7. **【风险】权威综述可能稀释卖点。** B1 已系统讲完"数据集方法学缺陷"。招聘方会问"你相对它的增量在哪"。
   **答案必须是**："我把这套批判在 NetFlow-v2 上做成了**可复现的实证 demo**（IP/重复流泄漏 + LODO），
   而非又一篇罗列式综述。"

---

## 待办 / 待核（动笔写论文前必须清掉）

- [x] ~~复核 A1 原文~~ **已做（2026-06-27）**：A1 实为 Cantone et al.，用 CIC/LycoS **非 NF-v2** → 已移至 B4；那串 94.9%→78.96/29.19/62.83 实为 **Popoola 联邦学习(NF-v2)** 数字，被 B4 转引，已更正归位为 A2b。
- [x] ~~找 Popoola 原文（A2b）~~ **引文已坐实（2026-06-27）**：Popoola et al., VTC2021-Fall, pp.1–6（Cantone ref[48]）；数字=中心化基线，FL 为其提出的修复。仅剩 [ ] 若要进正式论文，取 IEEE Xplore 原文 PDF 核对表格（VTC 付费）。
- [x] ~~确认 A2 发表载体~~ **已坐实（2026-06-27）**：Layeghy & Portmann, Computers & Electrical Engineering Vol.108, 2023（Elsevier 同行评审）；预印本旧题不同。**更正**：作者无 Gallagher（Gallagher 在另一篇 *Benchmarking the benchmark*, JISA 2024）。
- [x] ~~核实 Benchmarking the benchmark（JISA 2024）~~ **已做（2026-06-27）**：落为 B5 + 视角 8。数据集仅"CIC/UNSW/+1"、**未确认 NF-v2 标准版** → 进 B 组不进 A 组。角度是"合成 vs 真实世界"分布鸿沟，与项目一"合成内部跨数据集"正交且更深。
  - [ ] 若决定回应视角 8，需取 B5 全文确认其用的是 NF-v2 还是原版，并看能否复用其真实流量来源（大学网/ISP）。
- [ ] **确认 A7（GNN+Scattering）是否真用 NF-* 数据集**；若否，从 A 组移除。
- [x] ~~决定叙事主轴~~ **已拍板（2026-06-27）**：IP 泄漏 + 重复流泄漏 + LODO 为主。详见记忆 `project-honest-nids-narrative-axis`。
- [x] ~~数据依赖（IP/重复流在 dhoogla 镜像演示不了）~~ **已解（2026-06-28）：改用 NF3-Datasets（v3）**——已核实有 IP（IPV4_SRC/DST_ADDR）、有真时间戳（FLOW_START/END_MILLISECONDS+IAT）、流数 2.37M≈未去重；官方 UQ+DOI。替代"取原始 v2"。
- [ ] **迁移到 v3**：下载 + 校验 + 实测 `df.duplicated().sum()`（确认未去重）；§1/§2/§3 三张表在 v3 重跑（注意攻击率 5.40% vs 旧 3.78%，口径变）。
- [ ] **temporal 复活**：v3 有真时间戳 → 做真 temporal split（替换 §0.2 行序代理），原"降级"因视角2 前提消失而撤销。
- [ ] **多算法=基线/鲁棒性扫描（非擂台）**：补 Arp P6（LogReg/单特征基线），复现 A2"所有模型一起崩"。最小集 LogReg/单特征 + LightGBM + 1 个吃 IAT 的 DL。
- [ ] B1（C&S 综述）通读，把它的"13 项数据集评估维度"映射到本项目实测，作为差异化论据。
