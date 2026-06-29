# 项目一（诚实评估 NIDS）阅读清单与知识储备

> 配套主文档 `DS-ML-DL-Cyber-Security-v2.md` 第三章「项目一」。
> 持久参考层见 `knowledge-base/`（主题 T1/T2/T4/T8）；本清单只列**交付项目一的必读**，BibTeX 以 `knowledge-base/references.bib` 为准。
> 目的：把项目一从「又一个入侵检测分类器」讲成「一项关于诚实评估的研究」。
> 图例：⭐ 必读 ｜ ○ 选读/扩展。BibTeX 的页码/DOI 等细节落地引用前请二次核对。

---

## 阅读顺序（建议）

1. ⭐ Sommer & Paxson（建立直觉，半天）
2. ⭐ Arp et al. *Dos and Don'ts*（精读，方法论核心，1-2 天 → 见文末精读笔记）
3. ⭐ TESSERACT（temporal/spatial bias 与 AUT 指标；注意原文是 malware，借思想不照搬）
4. ⭐ Ring et al. 数据集综述（为什么数据集选择本身是 NIDS 核心风险）
5. ⭐ Engelen + Lanvin（CICIDS2017 错误，决定用哪个版本）
6. ⭐ Sarhan NetFlow 统一特征集（对应 LODO 实验）
7. ⭐ Cross-dataset generalization 2024（LODO 实验要复现的结论）
8. ○ SoK Pragmatic Assessment（部署视角）
9. ○ 对抗鲁棒性两篇
10. ○ ET-BERT（表示学习扩展，了解即可）

> base-rate 奠基文献 Axelsson 2000（见 §5）建议与第 1 篇同期读，作为 base-rate fallacy 的原始出处。

---

## 论文 → 项目产物映射

> 目的：阅读不停在「知道论文」，而是每篇绑定一个 repo deliverable。

| 论文 | 项目产物（repo deliverable） |
|---|---|
| Arp et al. | `evaluation_checklist.md`（10 大陷阱自查表） |
| TESSERACT | temporal split + drift 曲线 + AUT 指标 |
| Engelen / Lanvin | `dataset_version_decision.md`（用修正版 CICIDS2017） |
| Sarhan | 统一 NetFlow 特征集（NF-v2） |
| Cross-dataset generalization | LODO（Leave-One-Dataset-Out）实验矩阵 |
| Ring survey | README「数据集选择即核心风险」背景 |
| Axelsson / Sommer-Paxson | README base-rate fallacy + 误报量分析 |
| Arp P4 / 捷径学习 | `feature_policy_matrix.csv`（特征分级表，见 §6） |

---

## 1. 思维基石：为什么安全 ML 特别难

### ⭐ Outside the Closed World (IEEE S&P 2010)
- **作者/出处**：R. Sommer, V. Paxson；IEEE S&P 2010, pp.305–316（2020 Test-of-Time Award）。
- **链接**：https://www.semanticscholar.org/paper/8346b9a8e156d6e7a7012bcd47bc4f5d4be59e92
- **核心**：找攻击与一般 ML 任务本质不同——极低基率、误报代价高、缺真实标注、闭世界假设不成立。
- **对项目一**：README「问题背景」引用它定调，说明为什么不能只看 accuracy。

```bibtex
@inproceedings{sommer2010outside,
  title={Outside the Closed World: On Using Machine Learning for Network Intrusion Detection},
  author={Sommer, Robin and Paxson, Vern},
  booktitle={IEEE Symposium on Security and Privacy (S\&P)},
  pages={305--316}, year={2010}
}
```

### ⭐ Dos and Don'ts of ML in Computer Security (USENIX Security 2022)
- **作者/出处**：Arp, Quiring, Pendlebury, Warnecke, Pierazzi, Wressnegger, Cavallaro, Rieck；USENIX Security 2022。期刊版："Pitfalls in ML for Computer Security", CACM 2024。
- **链接**：https://www.usenix.org/system/files/sec22summer_arp.pdf ｜ 站点 https://dodo-mlsec.org/
- **核心**：审 30 篇顶会论文，归纳 10 大陷阱（见文末精读笔记）。
- **对项目一**：**整个「乐观 vs 诚实」对比表就是在复现这篇的论点**——这是项目的理论骨架。

```bibtex
@inproceedings{arp2022dodonts,
  title={Dos and Don'ts of Machine Learning in Computer Security},
  author={Arp, Daniel and Quiring, Erwin and Pendlebury, Feargus and Warnecke, Alexander and Pierazzi, Fabio and Wressnegger, Christian and Cavallaro, Lorenzo and Rieck, Konrad},
  booktitle={USENIX Security Symposium}, year={2022}
}
```

### ⭐ SoK: Pragmatic Assessment of ML for NID (IEEE EuroS&P 2023)
- **作者/出处**：Apruzzese, Laskov, Schneider；IEEE EuroS&P 2023。
- **链接**：https://arxiv.org/abs/2305.00550 ｜ 代码 https://github.com/hihey54/pragmaticAssessment
- **核心**：从从业者视角问「部署后到底值不值」，考虑硬件、上百种配置、对抗场景。
- **对项目一**：帮你写成「部署视角」而非「刷分视角」。

```bibtex
@inproceedings{apruzzese2023sok,
  title={SoK: Pragmatic Assessment of Machine Learning for Network Intrusion Detection},
  author={Apruzzese, Giovanni and Laskov, Pavel and Schneider, Johannes},
  booktitle={IEEE European Symposium on Security and Privacy (EuroS\&P)}, year={2023}
}
```

---

## 2. 评估方法学：时间/空间偏差与概念漂移

### ⭐ TESSERACT (USENIX Security 2019；2024 扩展版)
- **作者/出处**：Pendlebury, Pierazzi, Jordaney, Kinder, Cavallaro（扩展版加 Kan, McFadden, Arp）；USENIX Security 2019。
- **链接**：原版 USENIX 2019 https://arxiv.org/abs/1807.07838 ｜ 2024 扩展版 https://arxiv.org/abs/2402.01359 ｜ 项目页 https://s2lab.cs.ucl.ac.uk/projects/tesseract/
- **核心**：定义 **temporal bias**（训练混入未来信息）与 **spatial bias**（测试类别比例不真实）；提出约束 + 指标 **AUT**（真实部署下鲁棒性）。
- **⚠️ 范围**：原论文是 **Android malware classification**，不是 NIDS。本项目**借用其评估思想**（temporal/spatial bias、AUT），不直接照搬实验设置。面试若被追问「malware 的 AUT 为何能用在 NIDS」：评估偏差的来源（时间泄漏、测试类别比例失真）是任务无关的，迁移的是方法论而非数据/实验设置。
- **对项目一**：你的 temporal split 与 drift 曲线的方法论出处；AUT 可直接借用为评估指标。

```bibtex
@inproceedings{pendlebury2019tesseract,
  title={{TESSERACT}: Eliminating Experimental Bias in Malware Classification across Space and Time},
  author={Pendlebury, Feargus and Pierazzi, Fabio and Jordaney, Roberto and Kinder, Johannes and Cavallaro, Lorenzo},
  booktitle={USENIX Security Symposium}, year={2019}
}
```

---

## 3. 数据集质量：为什么必须用修正版 CICIDS2017

### ⭐ Troubleshooting an Intrusion Detection Dataset: CICIDS2017 (WTMC 2021)
- **作者/出处**：Engelen, Rimmer, Joosen；WTMC @ IEEE S&P Workshops 2021。
- **链接**：https://intrusion-detection.distrinet-research.be/WTMC2021/index.html
- **核心**：流构造/特征抽取/标注的系统性错误，重建并重标 **20%+ 的流**，修正 CICFlowMeter。

### ⭐ Errors in the CICIDS2017 Dataset (CRiSIS 2022 会议 / Springer LNCS 2023 proceedings)
- **作者/出处**：Lanvin, Gimenez, Han, Majorczyk, Mé, Totel 等。会议 CRiSIS 2022，论文集 Springer LNCS 13857（2023 出版）——引用时统一标注，避免年份看起来矛盾。
- **链接**：https://link.springer.com/chapter/10.1007/978-3-031-31108-6_2 ｜ 开放版 https://hal.science/hal-03775466
- **核心**：packet misorder/重复/漏标；引入 "X–Attempted" 标签；修正后性能数字显著不同。
- **对项目一**：这两篇是「不用原始版、改用修正版」的硬证据；先读再决定数据版本。

```bibtex
@inproceedings{engelen2021troubleshooting,
  title={Troubleshooting an Intrusion Detection Dataset: the CICIDS2017 Case Study},
  author={Engelen, Gints and Rimmer, Vera and Joosen, Wouter},
  booktitle={IEEE Security and Privacy Workshops (WTMC)}, year={2021}
}
@inproceedings{lanvin2023errors,
  title={Errors in the CICIDS2017 Dataset and the Significant Differences in Detection Performances It Makes},
  author={Lanvin, Maxime and Gimenez, Pierre-Fran{\c{c}}ois and Han, Yufei and Majorczyk, Fr{\'e}d{\'e}ric and M{\'e}, Ludovic and Totel, Eric},
  booktitle={CRiSIS}, year={2022}
}
```

---

## 4. 跨数据集泛化 + 统一特征集（项目一核心卖点）

### ⭐ Towards a Standard Feature Set for NIDS Datasets
- **作者/出处**：Sarhan, Layeghy, Portmann。
- **链接**：期刊版 *Mobile Networks and Applications* (Springer), 2021 ｜ ResearchGate 镜像 https://www.researchgate.net/publication/356095537（落地引用请用期刊 DOI，勿只挂 ResearchGate）
- **核心**：把 UNSW-NB15/BoT-IoT/ToN-IoT/CSE-CIC-IDS2018 统一成 **43 个 NetFlow 特征**（即 NetFlow-v2 系列），让跨数据集公平比较成为可能。
- **对项目一**：选 NetFlow 统一系列做 LODO 的直接依据。

### ⭐ Evaluating Standard Feature Sets ... Generalisability and Explainability (Big Data Research 2022)
- **链接**：https://arxiv.org/pdf/2104.07183
- **核心**：统一特征集既利于泛化也利于解释。

### ⭐ On the Cross-Dataset Generalization of ML for NIDS (2024)
- **链接**：https://arxiv.org/abs/2402.10974
- **核心**：直接做跨数据集实验——**没有模型能在所有数据集上一致表现**。
- **对项目一**：这正是你 LODO 实验要复现并讨论的结论。

```bibtex
@article{sarhan2021standardfeature,
  title={Towards a Standard Feature Set for Network Intrusion Detection System Datasets},
  author={Sarhan, Mohanad and Layeghy, Siamak and Portmann, Marius},
  journal={Mobile Networks and Applications}, year={2021}
}
```

---

## 5. 数据集背景综述与 base-rate fallacy（部署可用性）

> 用途：解释「数据集选择本身就是 NIDS 研究的核心风险」，以及为什么老数据集会虚高、真实部署里 base rate 决定一切。项目一不止用 CICIDS2017，还会碰 UNSW-NB15 / ToN-IoT / NF 系列，需要这组背景。

### ⭐ A Survey of Network-based Intrusion Detection Data Sets (Computers & Security 2019)
- **作者/出处**：Ring, Wunderlich, Scheuring, Landes, Hotho；Computers & Security, 2019。
- **链接**：https://www.sciencedirect.com/science/article/pii/S016740481930118X ｜ arXiv https://arxiv.org/abs/1903.02460
- **核心**：系统比较 NIDS 公开数据集的采集环境、标注方式、攻击类型与已知缺陷。
- **对项目一**：支撑「为什么数据集选择决定结论可信度」，README 数据集决策的综述出处。

### ⭐ The Base-Rate Fallacy and the Difficulty of Intrusion Detection (ACM TISSEC 2000)
- **作者/出处**：Stefan Axelsson；ACM TISSEC, 2000（CCS 1999 前身）。
- **链接**：https://dl.acm.org/doi/10.1145/357830.357849
- **核心**：在入侵检测里，极低攻击基率使得即便很高的检测率也会被海量误报淹没——base-rate fallacy 的**奠基原始文献**。
- **对项目一**：P8 与「每百万 flow × 不同攻击占比（0.1% / 1% / 5%）→ 误报量 / 分析师工作量」实验的直接理论出处；比单纯 PR-AUC 更贴近 SOC 现实。

### ○ UNSW-NB15: A Comprehensive Data Set for NIDS (MilCIS 2015)
- **作者/出处**：Moustafa, Slay；MilCIS 2015 / 后续期刊扩展。
- **链接**：https://ieeexplore.ieee.org/document/7348942
- **核心**：UNSW-NB15 的九类攻击、采集环境与标签定义。
- **对项目一**：若使用 NF-UNSW-NB15，需理解其原始攻击类别与标签语义，否则跨数据集对比会误读。

### ○ A Detailed Analysis of the KDD CUP 99 Data Set (CISDA 2009)
- **作者/出处**：Tavallaee, Bagheri, Lu, Ghorbani；提出 NSL-KDD。
- **链接**：https://ieeexplore.ieee.org/document/5356528
- **核心**：剖析 KDD99 的冗余记录与缺陷。
- **对项目一**：README 中说明「为什么不用 KDD99 / NSL-KDD 作主实验」，作为「老数据集导致虚高」的反例（不一定进实验）。

---

## 6. 特征泄漏与捷径学习（Feature leakage & shortcut learning）

> 把 Arp P3（data snooping）/ P4（spurious correlations）落到一个具体产物：`feature_policy_matrix.csv`。

把每个特征分类（落地为 CSV 的 `policy` 列）：
- **inference-safe**：部署时可得、无泄漏、无环境痕迹。
- **environment-specific**：依赖采集环境（特定 IP 段、实验室时间窗），跨数据集不可迁移。
- **suspected shortcut**：与标签强相关但可能是捷径（如端口号直接暴露攻击类型）。
- **direct leakage**：直接/间接编码了标签或未来信息（某些标注流程里流时长与标签耦合）。
- **privacy-sensitive**：含 PII / 可去匿名信息，触及 GDPR。

> 方法论依据不限 NIDS——可引 Arp 的 spurious correlations 及 ML 通用的 shortcut learning 文献。产物（特征分级表）本身比再多读一篇论文更重要。

---

## 7. 对抗鲁棒性（可选扩展，命中 Adversarial ML 岗位）

### ○ Modeling Realistic Adversarial Attacks against NIDS (ACM DTRAP 2021)
- **作者/出处**：Apruzzese et al. ｜ https://dl.acm.org/doi/10.1145/3469659
- **核心**：真实攻击者不用梯度，而用简单手段；威胁模型必须现实。

### ○ Evasion Adversarial Attacks Remain Impractical Against ML-based NIDS, Especially Dynamic Ones (2023-24)
- **链接**：https://arxiv.org/html/2306.05494v5
- **核心**：反主流结论——多数学术对抗攻击在现实约束下并不实用，动态模型更难绕过。适合写一篇有观点的 critique。

---

## 8. 新方向（前沿/加分，了解即可）

### ○ ET-BERT (WWW 2022)
- **作者/出处**：Lin, Xiong, Gou et al. ｜ https://arxiv.org/abs/2202.06335
- **核心**：把加密流量字节当「语言」做自监督预训练（Masked BURST Model），在**加密流量应用/服务分类**任务上 F1 可达 98.9%（是应用分类任务，不是 NIDS 入侵检测泛化）。
- **对项目一**：流量表示学习 / 安全基础模型新范式，作为 DL 扩展灵感。⚠️ 它**不解决**项目一核心问题（dataset leakage、temporal bias、cross-dataset collapse），**不建议 MVP 阶段实现**，仅留扩展区。

```bibtex
@inproceedings{lin2022etbert,
  title={{ET-BERT}: A Contextualized Datagram Representation with Pre-training Transformers for Encrypted Traffic Classification},
  author={Lin, Xinjie and Xiong, Gang and Gou, Gaopeng and Li, Zhen and Shi, Junzheng and Yu, Jing},
  booktitle={The Web Conference (WWW)}, year={2022}
}
```

---

## 精读笔记：Arp et al. 的 10 大陷阱 → 映射到项目一

> 这是项目一的「检查清单」。每做一步，对照它问自己：我踩了哪个坑？

| # | 陷阱 | 含义 | 在项目一里如何体现/规避 |
|---|---|---|---|
| P1 | **Sampling bias** | 训练数据分布不代表真实部署 | 讨论 CIC/UNSW 是合成/实验室流量，base rate 不真实；说明对真实 SOC 的外推限制 |
| P2 | **Label inaccuracy** | 标注本身有错 | 直接对应 Engelen/Lanvin 的 CICIDS2017 标注错误——用修正版 |
| P3 | **Data snooping（数据窥探/泄漏）** | 测试信息泄进训练 | **项目核心**：含 temporal snooping（用未来预测过去）、normalization snooping（在全量上做标准化）、k-fold snooping。诚实版要逐一封堵 |
| P4 | **Spurious correlations（伪相关/捷径特征）** | 模型学到与任务无关的环境痕迹 | 你的 feature policy matrix：IP/端口/时间戳等环境痕迹要识别为捷径特征 |
| P5 | **Biased parameter selection** | 调参时偷看了测试集 | 调参只在验证集；测试集只用一次 |
| P6 | **Inappropriate baseline** | 没和简单基线比 | 先给 LogReg / 单特征基线，再上复杂模型 |
| P7 | **Inappropriate performance measures** | 用错指标（如只看 accuracy） | 用 macro-F1、PR-AUC、per-class recall；引入 TESSERACT 的 AUT |
| P8 | **Base rate fallacy** | 忽视极低攻击占比导致的误报洪流 | 用 precision 在真实 base rate 下重新解读，讨论误报成本 |
| P9 | **Lab-only evaluation** | 只在实验室数据上评估 | 用跨数据集 LODO + drift 曲线模拟真实部署衰减 |
| P10 | **Inappropriate threat model** | 威胁模型不现实 | （若做对抗扩展）采用 Apruzzese 的现实黑盒威胁模型，而非梯度白盒 |

**一句话**：项目一的叙事 = 先故意踩 P3/P4/P7/P9 得到虚高分数 → 逐一封堵 → 展示「诚实」数字 → 用 LODO + AUT + base-rate 解读说明真实水平。这条线把一个 commodity 项目变成一篇有观点的研究。
