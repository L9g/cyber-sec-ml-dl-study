# Network Detection Project Plan Draft: ML/DL x Network Security

> Status: draft
>
> Purpose: turn the discussion after `01-honest-nids` into a concrete project roadmap. The goal is not to build more benchmark classifiers, but to show credible ability across IP networking, network security, detection engineering, ML/DL, and operational risk.

---

## 0. 定位:这是候选池,不是替换主线计划

**本文档是对 `DS-ML-DL-Cyber-Security-v2.md`(v2.1)既定四项目的补充,不是替换。** 使用规则:

- **主线 = v2.1 四项目**(① 诚实 NIDS ② LLM 注入防御 ③ SIEM/SOC 日志智能 ④ AML 图学习),按市场广度铺,优先推到 Reference-grade。其中 ④ AML-GNN 是伦敦金融命中率最高的钩子,优先级高于本文档任何候选。
- **本文档 = 预备役 backlog**。只在「某个具体岗位 JD 需要某块信号」时**抽一个**做加分项,或用来**替换**主线里事后发现较弱的一环。判断标准是「我现在投的岗位缺哪块信号」,不是「这个项目本身好不好」。
- 不要把这 8 个当 8 个待办;核心四 + 全部候选 = 规模失控,违背 MVP 分档原则。

**与主线的重叠关系(避免重复投资):**

| 本文档候选 | 与主线关系 |
|---|---|
| A. Zeek+ATT&CK / G. 内部威胁(LANL 图) | **重叠主线 ③ SIEM/SOC**——视为 ③ 的实现选型,不另开项目 |
| H. 对抗鲁棒性 | v2.1 已规划为「项目②/④的对抗扩展」——是已规划扩展,非新项目 |
| **B. DNS / C. BGP / D. TLS / E. VPC / F. IoT** | **真正净新增**(网络协议/路由深度)。其中 **C. BGP 最值得保留**——唯一能给出「比普通 ML 候选人更懂 IP 网络」的稀缺信号 |

**抽取任一候选前的硬检查:**
1. **data feasibility 先验**(隐形杀手):如 DNS DGA 数据集按家族 trivially 可分,不做 family-holdout 就是 honest-nids 虚高的翻版;**通用 BGP 劫持 ground truth 稀疏需手工策展,但 RPKI-conflict 子问题可用弱标签启动(持久性启发式)——标签质量本身必须审计,见 §3.5/§6 的标签审计层**;CERT 内部威胁是合成数据(公认不真实)。
2. **挂上方法学主轴**:每个补充项目都带 泄漏检查 + base-rate/alert budget + drift,延续 honest-nids 的「诚实评估」签名方法论。
3. 下方 §4 优先级矩阵的 `Overall` 列未透明聚合子分(implementation risk 像未作减项,如 C 风险 5 仍 Overall 4),仅作粗排参考,决策时按目标岗位重新加权。

---

## 1. Starting Point

`01-honest-nids` is valuable because it does the opposite of a typical "99% accuracy NIDS" project. It focuses on leakage, temporal split, cross-dataset generalisation, base-rate thinking, and honest evaluation.

Its main limitation is also clear: public NetFlow benchmark datasets make the project look closer to a research-reproduction and evaluation-methodology exercise than a deployable security engineering system. That is not a flaw in the current project; it is a boundary imposed by the data and task design.

The next projects should therefore add the missing dimensions:

- Telemetry-first thinking: Zeek, Suricata, DNS, TLS, BGP, VPC Flow Logs, auth logs.
- Detection engineering: ATT&CK mapping, rules, hypotheses, runbooks, analyst workflow.
- Operational constraints: alert budget, base rate, false-positive cost, drift, retraining.
- ML/DL pragmatism: use ML where it improves triage or detection, not as decoration.
- Network expertise: protocol semantics, routing, flow/session behaviour, asset context.
- Governance: model cards, data cards, privacy limits, monitoring and auditability.

The project should show that I can move from "train a classifier" to "design a detection capability."

---

## 2. Project Selection Principles

Use these principles when selecting projects after `01-honest-nids`.

| Principle | Meaning |
|---|---|
| Security realism | The project should resemble a SOC, network security, cloud security, or detection engineering workflow. |
| Network depth | It should require actual understanding of protocols, logs, routing, flows, or telemetry sources. |
| ML/DL fit | The model should solve a real problem such as prioritisation, anomaly detection, representation learning, sequence modelling, or drift monitoring. |
| Data availability | Public data must be obtainable and legally usable; when data is imperfect, the limitation must be explicit. |
| Project contrast | Each project should show a different capability from `01-honest-nids`. |
| Deployability | The output should include a detector, runbook, dashboard, API, reproducible pipeline, or monitoring story. |

---

## 3. Candidate Projects

### Project A: Zeek + ATT&CK Detection Engineering Lab

**Short description**

Build a telemetry-first detection lab from PCAP/network traffic to Zeek logs, rule-based detections, ML anomaly scoring, ATT&CK mapping, alert budget analysis, and analyst-facing investigation notes.

**Why this complements project 1**

`01-honest-nids` studies whether benchmark NIDS models generalise. This project starts from the opposite direction: real network telemetry and concrete detection hypotheses. It would show security engineering maturity beyond ML evaluation.

**Possible data sources**

- Malware-Traffic-Analysis.net PCAPs.
- Stratosphere CTU / CTU-13 botnet traffic.
- IoT-23 malicious IoT traffic.
- Public Zeek/Suricata training datasets where licenses permit.

**Technical components**

- PCAP to Zeek logs: `conn.log`, `dns.log`, `http.log`, `ssl.log`, `x509.log`, `files.log`.
- Optional Suricata alerts for rule-based signal.
- Feature engineering from connection, DNS, TLS, HTTP and host aggregation.
- Baseline rules mapped to MITRE ATT&CK techniques.
- ML anomaly scoring: Isolation Forest, Local Outlier Factor, autoencoder, or LightGBM where labels exist.
- Alert budget: how many alerts per day per threshold, analyst queue size, precision/recall tradeoff.
- Drift and deployment notes.

**Expected deliverables**

- Reproducible pipeline: PCAP -> logs -> features -> detections -> report.
- Detection cards: hypothesis, data source, ATT&CK technique, logic, expected false positives, triage steps.
- Notebook/report comparing rule-only, ML-only, and hybrid detection.
- Small dashboard or static HTML report for alert review.

**Project value**

Very high. This is closest to real detection engineering and SOC analytics. It directly addresses the "research reproduction" weakness of project 1.

---

### Project B: DNS Tunneling and DGA Detection

**Short description**

Build a DNS security analytics project that detects suspicious domains and host behaviour using lexical features, sequence models, aggregation, and operational thresholds.

**Why this complements project 1**

It moves from NetFlow-level classification to protocol-aware detection. DNS is a practical security data source, commonly available in enterprise networks, and strongly connected to malware, C2, phishing, and exfiltration.

**Possible data sources**

- Public DGA datasets.
- Public DNS tunneling datasets.
- Malware traffic PCAPs converted to Zeek `dns.log`.
- Benign domain lists with careful leakage control.

**Technical components**

- Domain lexical features: length, entropy, digit ratio, consonant ratio, n-grams, subdomain depth.
- Host-level aggregation: NXDOMAIN ratio, query volume, unique domains, TTL patterns, rare TLDs.
- Models: LightGBM/XGBoost baseline, char-CNN, BiLSTM, small Transformer, anomaly detection by host.
- Evaluation: family/tool holdout, time split, domain leakage checks.
- Deployment: threshold tied to analyst review budget.

**Expected deliverables**

- DNS feature pipeline.
- Model comparison between tree models and a character-level neural model.
- Family-holdout evaluation to test generalisation.
- Detection runbook for suspicious host/domain investigation.

**Project value**

High. It shows protocol understanding, practical feature engineering, and a meaningful place for DL.

---

### Project C: BGP Route Leak / Hijack / Outage Anomaly Monitor

**Short description**

Use public BGP data to detect routing anomalies such as origin changes, route leaks, excessive withdrawals, MOAS events, and prefix instability.

**Why this complements project 1**

This is the strongest IP networking project. It demonstrates internet routing knowledge rather than only security ML. It is also rare in typical ML/security projects.

**Possible data sources**

- RouteViews.
- RIPE RIS.
- CAIDA AS relationship data.
- RPKI/ROA validation sources.
- Public incident timelines for known leaks/hijacks.

**Technical components**

- BGP update parsing.
- Features: AS path length, origin AS changes, prefix churn, withdrawal bursts, MOAS, AS relationship violations, RPKI validity.
- Models: EWMA/change-point baselines, Isolation Forest, sequence autoencoder, graph-based anomaly features.
- Incident replay: reconstruct known BGP events and compare detection latency.

**Expected deliverables**

- Time-series anomaly pipeline.
- Incident timeline report.
- Visualisation of prefix/origin/AS-path changes.
- Clear explanation of what ML adds over deterministic routing checks.

**Project value**

Very high for network engineering credibility. Higher implementation risk than DNS or Zeek because BGP data parsing and ground truth are harder.

> 2026-06-30 更新：见 §3.5。联网核实后，BGP 的 **RPKI-conflict 子问题有可规模化弱标签**（不需手工策展事件），data-feasibility 应上调；但「诚实评估」批判角度已被 arXiv 2507.20434 部分占位，需差异化。

---

### Project D: Encrypted Traffic / TLS Metadata Detection

**Short description**

Use TLS and connection metadata rather than packet payloads to identify suspicious encrypted traffic, malware communication patterns, or application classes.

**Why this complements project 1**

Modern networks are encrypted. This project shows practical constraints: privacy, lack of payload, changing TLS fingerprints, certificate metadata, and drift.

**Possible data sources**

- Zeek `ssl.log`, `x509.log`, `conn.log` extracted from public malware PCAPs.
- Public encrypted traffic classification datasets.
- Malware traffic samples where licensing permits.

**Technical components**

- TLS metadata: SNI, certificate issuer/subject, validity period, self-signed flag, JA3/JA4 where available.
- Flow metadata: duration, bytes, packets, directionality, periodicity.
- Models: LightGBM/XGBoost baseline, autoencoder, sequence model for host sessions.
- Privacy-aware design: avoid relying on payload or user-sensitive content.
- Drift monitoring: browser/TLS ecosystem changes can break fingerprint assumptions.

**Expected deliverables**

- TLS metadata feature matrix.
- Evaluation report on known malware vs benign or suspicious vs normal traffic.
- Privacy and drift note.
- Triage guide explaining how an analyst would investigate a suspicious TLS flow.

**Project value**

High. Good bridge between network security and applied ML, but must avoid overclaiming because public labelled datasets can be messy.

---

### Project E: Cloud / VPC Flow Logs Detection Pipeline

**Short description**

Build a cloud network detection pipeline around VPC Flow Logs or equivalent flow telemetry, including scan detection, unusual egress, suspicious ports, and ML-based anomaly triage.

**Why this complements project 1**

Cloud security is an employable direction. This project converts NetFlow-style thinking into a modern cloud environment and adds infrastructure, monitoring, and detection-as-code.

**Possible data sources**

- Public AWS/Azure/GCP flow log examples.
- Simulated lab traffic in a small local/cloud lab.
- Synthetic VPC Flow Logs generated from controlled scenarios.

**Technical components**

- Flow log parser.
- Rule detections: port scan, unusual egress, new geo/ASN, denied connection spikes.
- ML anomaly model for source/destination behaviour.
- IaC or local simulation if real cloud use is not desired.
- Alert output compatible with SIEM-style JSON.

**Expected deliverables**

- Detection pipeline with config-driven rules.
- Example alerts and triage runbooks.
- Dashboard or notebook showing alert volume and false-positive assumptions.
- Optional Docker Compose / local generator.

**Project value**

High for employability. Less research depth, more engineering and cloud-security realism.

---

### Project F: IoT Device Fingerprinting and Unauthorized Device Detection

**Short description**

Profile devices from network behaviour and detect unknown or misbehaving devices using traffic metadata, DNS, protocol usage, periodicity, and behavioural fingerprints.

**Why this complements project 1**

It shifts from attack classification to asset and behaviour modelling, which is closer to enterprise network operations and Zero Trust/NAC use cases.

**Possible data sources**

- IoT-23.
- Public IoT device identification datasets.
- CICIoT/CICIoMT datasets if access and license are acceptable.

**Technical components**

- Device behavioural profile: ports, destinations, DNS patterns, flow timing, protocol mix.
- Classification of known device types.
- Open-set or anomaly detection for unknown devices.
- Drift: firmware updates and cloud endpoint changes.

**Expected deliverables**

- Device fingerprinting report.
- Unknown-device detection experiment.
- Operational notes: how this would support asset inventory or NAC.

**Project value**

Medium to high. Strong practical story if framed as asset security, weaker if it becomes just another IoT dataset classifier.

---

### Project G: Insider Threat / Lateral Movement Graph and Sequence Detection

**Short description**

Use authentication and host logs to detect suspicious user-host behaviour, lateral movement patterns, and insider-risk sequences.

**Why this complements project 1**

It adds identity, graph analytics, temporal sequences, and SIEM-style telemetry. It is less IP-network focused but highly relevant to security data science.

**Possible data sources**

- LANL authentication logs.
- CERT Insider Threat.
- Mordor / OTRF security datasets.
- Splunk BOTS-style data.

**Technical components**

- User-host graph construction.
- Temporal features: rare logon paths, privilege changes, fan-out, after-hours activity.
- Models: graph features + LightGBM, node embeddings, temporal graph model, sequence model.
- Evaluation with alert budget and analyst triage constraints.

**Expected deliverables**

- User-host graph pipeline.
- Suspicious path visualisation.
- ML triage model and rule baseline.
- Investigation notes for sample alerts.

**Project value**

High for SOC/security data science roles. Lower direct IP networking signal, but good complement after a network-heavy project.

---

### Project H: Adversarial Robustness for Network Detectors

**Short description**

Extend `01-honest-nids` by testing whether flow-based detectors can be evaded under realistic network constraints, then compare naive adversarial attacks with feasible attacker actions.

**Why this complements project 1**

It deepens the existing project rather than creating a new domain. It is useful if targeting adversarial ML or AI security roles.

**Possible data sources**

- Existing `01-honest-nids` NetFlow datasets.
- Malware/NIDS benchmark datasets already prepared.

**Technical components**

- Define realistic feature constraints: packet counts, byte counts, duration, directionality.
- Compare unconstrained perturbations vs physically plausible perturbations.
- Evaluate evasion success, detector robustness, and adversarial training.
- Discuss why many academic adversarial attacks are not operationally realistic.

**Expected deliverables**

- Threat model document.
- Evasion experiment notebook.
- Robustness matrix by model and feature group.
- Clear conclusion on what attacks are realistic.

**Project value**

Medium to high. Strong theory and rigor, but less helpful for fixing the "not deployable enough" weakness unless paired with a telemetry project.

---

## 3.5 网络纵深深挖：DNS vs BGP 谁当 first（2026-06-30 讨论纪要，已联网核实）

> 背景：先把「网络纵深」方向（净新增 B.DNS / C.BGP / D.TLS / F.IoT）的项目方向 + 实验数据定下来。E.VPC 因几乎无公开标注数据先出局。本节是 2026-06-30 联网核实 BGP 文献后的结论，**修正**了 §3 Project C 的 `data feasibility=3` 与早前「BGP 真值必须手工策展、拖死 MVP」的判断。

### 候选收敛

- 两个认真的 first 候选：**B. DNS（DGA/隧道）** 与 **C. BGP（RPKI-conflict 方向）**。D.TLS、F.IoT 排后（TLS 恶意标签脏、holdout 钩子弱；IoT 的 CIC-IoT2023 是 benchmark 虚高重灾区）。
- 共同硬约束：数据集名先当「待核候选」，锁方向后跑三件套（论文真实 + 可下载 + 许可允许）再锁死；每个项目挂方法学主轴（泄漏检查 + base-rate/alert-budget + drift）= 延续 honest-nids 签名。

### BGP 核实结论：两条可立项主线（honest audit / 控制面不足→数据面）

> ⚠️ 2026-06-30 二次核实修正：初稿曾把 arXiv 2507.20434 写成「严格 temporal 后跌到随机」——读 abstract 后确认那是**臆造**（honest-nids 思维定式的投射）。已改正，见下。BGP 文献其实给出**两条不同**的立项主线。

**虚高派（既是模板也是批判靶子）— Learning to Identify Conflicts in RPKI（AsiaCCS 2025, arXiv 2502.03378）：**
- 全公开可复现数据：RouteViews RIB + Routinator 取 RPKI-invalid；标签 = 「长寿命=良性」持久性启发式（一个月稳定的 9,223 条判 benign conflict）+ BGPmon 劫持（415 条）；特征 = CAIDA AS 关系 / IHR AS-hegemony / IRR / GeoIP（**正是普通 ML 候选不会的词**）。
- RF 拿 **98.8% F1**，却埋了 honest-nids 教科书级的雷：① 415 劫持「随机复制」过采样到 2000 = **重复样本泄漏进 train+test**（=项目一研究过的重复流泄漏）；② 持久性标签是**循环逻辑**（用稳定性定义良性再「发现」良性很稳定）；③ 220 个劫持事件**仅 10 个邮件人工确认**（96% 未核实）；④ 日常 base rate ≈ **79% 良性 / 21% 劫持**，却平衡到 1:1 评估。
- ⚠️ 这些「内部缺陷」细节出自全文 WebFetch，**建立「拆穿」叙事前必须精读 PDF 二次确认**（同样吃过 2507.20434 误述的亏），不能照搬本草稿。

**控制面脆弱性主线（修正后的 2507.20434 真实命题）— Is Crunching Public Data the Right Approach to Detect BGP Hijacks?：**
- 真实命题 = **投毒/规避**，不是 temporal-collapse：post-ROV 的 forged-origin 劫持检测器 **DFOH（NSDI'24）、BEAM（Sec'24）** 依赖全球 BGP monitor 的历史模式，但 monitor 本身能被对手注入伪造路由欺骗——「只需在真实劫持之外多发几条精心构造的宣告」即可同时绕过两者。
- 含义：**只啃 public 控制面数据是可投毒的脆弱面** → 指向「控制面 + 数据面融合」这条更强、更有记忆点的主线。它**不是** RPKI-conflict honest-audit 的靶子，别再当 temporal-collapse 引。

**数据面信号（支撑「控制面不足」论）：**
- Oscilloscope（arXiv 2301.12843）：用**数据面流量的非均匀变化**区分劫持 vs 合法事件（劫持只偏转部分 prefix/流量，合法重配是齐变），过滤控制面误报。
- HiDe（arXiv 2507.14842）：用**传播时延突增**检测 long-distance 劫持，「**86% 受害-攻击国家对，攻击中时延比攻击前高 ≥25%**」，line-rate、always-on。
- 两篇坐实「控制面会被骗 → 加数据面物理约束（流量/时延骗不了）」，是 RPKI 主线 Research-grade 档的天然扩展。

**弱标签证据 — Classification & false alarm of RPKI-invalid prefixes（arXiv 1903.06860）：** RPKI-invalid 多为误配非劫持，六类成因（load-balancing / fail-to-aggregate / multihoming / singlehoming / provider / transfer）→「invalid ≠ 恶意」+ 高误报成本，正好喂 base-rate 叙事。

### BGP 可立项形态（推荐：单主线分档，不要拆成多个项目）

**推荐主线 =「为什么只啃 public 控制面数据不够」（单项目，分档交付）：**
- **MVP = 诚实 RPKI-conflict 审计**：复现 2502.03378 的 98.8%，去随机复制过采样 / 上真 temporal / 持久性标签换可核实子集 / 按 21% 真 base rate 报 PR-AUC；输出 **block / allow / investigate** 三档，且**不确定时主动 abstain 到 investigate**——诚实优先于准确，避开「可用三档风险工具」的 overclaim。差异化 = 目前**无人放出 RPKI-conflict 分类器的可复现 honest-audit 工件**（2507.20434 是投毒命题、未占这块）。
- **Research-grade = 控制面 + 数据面融合**：由 2507.20434（控制面可投毒）+ Oscilloscope/HiDe（数据面物理约束）驱动，加时延/可达性信号。叙事「只看 public BGP feed 会被骗，融合才接近真实防御」——最强记忆点，但数据工程最重（主动测量/RIPE Atlas），故放 Research 档不进 MVP。

**备选形态（非主线，按 JD 需要再抽）：** ① AS 声誉 / serial-hijacker 复现（Testart IMC'19 + 2024 复现）；② route-leak（ANSSI `route_leaks` 开源）。

### 修正后的 DNS vs BGP 取舍

- **纠错（如实报告）**：早前「BGP 真值必须手工策展、拖死 MVP」只对**通用劫持检测**成立；**RPKI-conflict 子问题有可规模化弱标签**（RouteViews + Routinator + CAIDA + IHR），不需手工考古，故 §3 Project C 的 data-feasibility 应从 3 上调（≈4）。
- BGP 因此从「天花板高但当第二个」升为「**与 DNS 并列的 first 候选**」。剩余差距：(a) BGP 数据工程更重（BGPStream/MRT 解析、RPKI validator、多源 join）；(b) BGP 的 honest-audit 角度**未被现成论文占位**（2507.20434 是投毒命题、非 temporal-collapse），可复现 honest-audit 工件仍是空白 → 差异化反而更好。DNS 的 family-holdout 角度也少人系统做，但 DNS 整体新颖性低（已有 CNN/LLM/xLSTM 刷接近满分），卖点只能押「公开 benchmark 的泛化/泄漏审计」。
- **去工程风险的前置动作**：BGP-first 前先做 **1 天数据可行性 spike**——能否 (a) 拉到 RPKI-invalid 路由、(b) 算出 CAIDA AS-rel + IHR hegemony 特征、(c) 拿到事件标签（BGPStream/Qrator）。能在一天内 join 通 → BGP-first 安全；否则回落 DNS。把「数据工程风险」从嘴上争论变成可测闸门。
- **未决（下一步）**：first = DNS（数据工程轻 + 快赢）还是 BGP-RPKI（信号最稀缺 + honest-audit 空白）。下一步把两者各写成同规格一页 MVP 提案（数据源清单 + 三件套核实 + 评估协议 + 差异化）再拍。

### 待核源清单（已联网核实「存在 + 可下载」；venue/许可正式进 `references.bib` 前二次确认，知识截止 2026-01）

- arXiv 2502.03378 — Learning to Identify Conflicts in RPKI（AsiaCCS 2025）— **RPKI-conflict 模板 + 批判靶子**
- arXiv 2507.20434 — Is Crunching Public Data the Right Approach to Detect BGP Hijacks? — **投毒/规避命题**（攻击 DFOH/BEAM 的 monitor），**非** temporal-collapse（初稿已纠错）
- arXiv 1903.06860 — Classification & false alarm of RPKI-invalid prefixes — invalid≠恶意 / base-rate
- Testart et al. IMC 2019 — Profiling BGP Serial Hijackers；2024 复现研究（RIPE Labs / APNIC / SIDN）
- ANSSI-FR/route_leaks（GitHub）— route-leak SVM + 2014–16 数据
- MDPI Electronics 13(20):4072 — route leak via graph features
- arXiv 2301.12843（Oscilloscope）、arXiv 2507.14842（HiDe）— **数据面信号**（流量非均匀 / 时延突增），控制+数据面融合主线
- DFOH（NSDI'24）、BEAM（USENIX Security'24）— 被 2507.20434 投毒的 post-ROV 检测器（待补 arXiv 号）
- ARTEMIS（arXiv 1801.01085）、HEAP（arXiv 1607.00096）— 运营商视角检测对照
- 数据/工具基础设施：BGPStream（CAIDA）、RouteViews、RIPE RIS、Qrator Radar、Cloudflare Radar、Atlantic Council BGP incident data

---

## 4. Initial Prioritisation Matrix

Scoring scale: 1 = weak, 5 = strong.

| Candidate | Network depth | ML/DL depth | Security engineering realism | Data feasibility | Project distinctiveness | Implementation risk | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|
| A. Zeek + ATT&CK Detection Lab | 5 | 4 | 5 | 4 | 5 | 3 | 5 |
| B. DNS Tunneling / DGA | 4 | 5 | 4 | 4 | 4 | 2 | 4 |
| C. BGP RPKI Honest Audit | 5 | 4 | 4 | 4 | 5 | 4 | 4 |
| D. TLS Metadata Detection | 4 | 4 | 4 | 3 | 4 | 3 | 4 |
| E. Cloud / VPC Flow Logs | 4 | 3 | 5 | 3 | 4 | 3 | 4 |
| F. IoT Fingerprinting | 4 | 4 | 4 | 4 | 3 | 3 | 3 |
| G. Insider / Lateral Movement | 3 | 5 | 5 | 4 | 4 | 4 | 4 |
| H. Adversarial NIDS Robustness | 3 | 5 | 3 | 5 | 4 | 3 | 3 |

> **⚠️ 本表是初稿粗排，其「推荐」结论已被 §3.5/§5/§6 取代，勿据此决策。** 留作打分留痕。真正口径：主线 = v2.1 四项目（§5）；网络纵深**只单选一个 = C. BGP RPKI Honest Audit**（§6），受 §8 的 1 天数据可行性 spike 把关，失败回落 B. DNS honest-audit。下方旧 interpretation 仅供对照，**不再代表当前推荐**。

Interpretation（superseded by §3.5/§5/§6 — 历史留痕，勿用）:

- ~~Best immediate next project: **A. Zeek + ATT&CK**~~ → §5 已否：Zeek 视为主线 ③ SIEM 的实现选型，不另开，也不做平台。
- Best ML/DL-heavy fallback: **B. DNS（仅 honest-audit 形态）** —— spike 失败时的回落。
- Best IP networking differentiator（当前唯一主动推进）：**C. BGP RPKI Honest Audit**。
- Best employability/cloud angle: **E. Cloud / VPC Flow Logs** —— 无公开标注数据，暂搁。

> 2026-06-30 修订：上表 C 已从「BGP Anomaly Monitor」改为「BGP RPKI Honest Audit」并重打分——`Data feasibility` 3→4（RPKI-conflict 子问题有可规模化弱标签）、`Implementation risk` 5→4（子问题聚焦，数据工程仍重故不降到 3）。C 与 B 升为并列 first 候选，C 为首选（honest-audit 角度无现成论文占位）。

---

## 5. Recommended Project Shape

> **对齐 §0/§3.5（2026-06-30）：主线仍是 v2.1 四项目，本候选池至多再加「一个」网络纵深项目。** 已废弃初稿那套「Honest NIDS → Zeek → DNS → BGP」四件套——它与主线打架（缺 ②LLM/③SIEM/④AML），且违背 §0「不全建候选」。

### 主线不变（v2.1，优先级最高）

1. **① 诚实 NIDS** — 已在 Reference-grade 推进中。
2. **② LLM 注入防御**。
3. **③ SIEM/SOC** — 候选 **A. Zeek+ATT&CK**、**G. 内部威胁(LANL)** 视为它的实现选型，不另开项目。
4. **④ AML-GNN** — 伦敦金融命中率最高，是网络纵深项目之外的**下一个主攻**，优先级高于本候选池任何项。

### 网络纵深增项（本候选池，单选一个，不堆叠）

- **首选 = BGP 单主线**（详见 §3.5、§6）：MVP 诚实 RPKI-conflict 审计 → Research 控制+数据面融合。Message：「比普通 ML 候选更懂 IP 网络，且把诚实评估签名搬到路由安全」。**受 1 天数据可行性 spike 把关**；spike 失败回落 DNS honest-audit。
- **Backlog（不主动建，JD 驱动再抽）**：B. DNS（仅 honest-audit 形态）、D. TLS、F. IoT；H. 对抗鲁棒性 = 项目 ②/④ 的扩展；E. VPC 因无公开数据暂搁。
- **明确不做平台**：不把 Zeek 包装成「检测工作台平台」——只有一个 use case 的平台就是该 use case 加一层抽象（过早平台化陷阱）。第二个 use case 真出现前不抽象。

---

## 6. Recommended Network-Depth Project: RPKI Risk Triage — Honest ML for Invalid Routes（控制面诚实审计 → 控制+数据面融合）

> 这是本候选池里**唯一**主动推进的网络纵深项目（单主线分档），不是「下一个项目」——主线里 **④ AML-GNN 优先级仍更高**，本项目与之竞争时间，按 JD 信号取舍。**立项受 §8 的 1 天数据可行性 spike 把关**；spike 失败则回落 DNS honest-audit。理由见 §3.5：BGP 论证强于初稿默认的 Zeek，且 honest-audit 角度尚无现成论文占位。

### Proposed working title

- 对外/叙事标题（首选）：**RPKI Risk Triage: Honest ML for Invalid Routes**（产品感 + 点出 triage 与 honest 两个签名词）。
- 备选：*BGP Trust-but-Verify: Auditing RPKI Conflict Classifiers* / *From Invalid Routes to Investigations: Honest RPKI Triage*。
- repo slug：`NN-bgp-rpki-honest-audit`（编号待定：01 = honest-nids，②③④ 主线占位后再编）。

### MVP scope（控制面诚实审计）

- **先做 1 天数据可行性 spike**（见 §8），通过才进入下列步骤。
- 复现 2502.03378 的 RPKI-conflict 分类器（声称 ~98.8% F1）作为「乐观 baseline」。
- 逐一拆穿（**叙事落地前精读 2502.03378 PDF 坐实这些缺陷**）：去随机复制过采样 / 上真 temporal split / 持久性启发式标签换可核实子集 / 按真实 ~21% 攻击 base rate 报 **PR-AUC**。
- 输出 **block / allow / investigate** 三档，且**不确定时主动 abstain 到 investigate**（诚实优先于准确，避免 overclaim 成「可用风险工具」）。
- Alert budget：运营商每天能复核多少 invalid conflicts。

### 评估即「决策策略」，不是分类（核心评估轴）

模型的目的不是预测真相，而是**分配有限的人工复核资源**。评估指标据此设计，比裸 PR-AUC 更贴运营商现实：

- **investigate budget**：每天 N 条可人工复核 → 在该预算下的指标。
- **unsafe allow rate**：被判 allow 实为劫持的比例（漏放，最贵）。
- **unnecessary block rate**：被判 block 实为良性误配的比例（误杀，运营摩擦）。
- **coverage @ abstention rate**：弃权率给定时，自动决策覆盖了多少流量、剩多少进 investigate 队列。

> ⚠️ **honest-eval 警告（复用项目一 §2.1 教训）**：以上四个都是**操作点指标**，与项目一证伪过的 `recall@0.5` 同类——随阈值/采样剧烈漂移。故**报曲线不报单点**：unsafe-allow vs unnecessary-block 的权衡曲线、coverage-vs-abstention 曲线。**阈值无关的 PR-AUC 仍保留**作模型对比骨架；决策指标是叠加的运营层，不是替换。这条「曲线 vs 单点」正是 honest-nids 的签名。

### RPKI Conflict Decision Card（把复现实验变成分诊工具）

每条 alert 输出一张可解释卡片，让项目从「论文复现」升级为「可用分诊工件」：

- prefix / origin AS / ROA mismatch 类型（六类成因之一，引 1903.06860）；
- AS relationship（CAIDA AS-rel）、AS-hegemony（IHR）、IRR / GeoIP 一致性；
- 该 prefix/origin 历史出现次数与持久性；
- model score + **校准后置信度**；
- decision：allow / block / **investigate**；
- **why not confident**：触发弃权的具体原因（标签来源弱、特征缺失、分布外、持久性证据不足）。

### 标签审计层（label provenance leakage —— honest-nids 的自然升级）

不只审计模型，**也审计标签来源**。这是从「feature leakage」走到「label provenance leakage」的升级，是本项目相对项目一最有辨识度的方法学增量：

- 持久性「良性」标签是否**循环逻辑**（用稳定性定义良性，再「发现」良性很稳定）；
- BGPmon/事件「劫持」标签是否**重复或时间泄漏**（呼应项目一的重复流泄漏：2502.03378 把 415 劫持随机复制到 2000）；
- 同一 prefix/origin 是否**跨 split 泄漏**；
- 是否应按 **ASN / prefix family 做 group split**（防同族泄漏，类比 DNS family-holdout）；
- 输出一份**标签可信度分级**，喂回 Decision Card 的 abstain 逻辑（标签弱 → 倾向 investigate）。

### Research-grade extension（控制+数据面融合）

- 由 2507.20434（public 控制面可投毒，绕过 DFOH/BEAM）+ Oscilloscope/HiDe（数据面物理约束骗不了）驱动。
- **calibrated abstention / conformal prediction**：用 conformal 给「不确定就 investigate」一个形式化保证——不声称模型可靠，而是声称「在标签噪声与低基率下显式管理不确定性」。⚠️ **诚实陷阱**：conformal 的覆盖保证依赖 exchangeability，而本项目恰在做 temporal/cross-distribution split → 边际覆盖率在 drift 下会破。故用 **group/Mondrian-conditional** 变体，或干脆把「marginal coverage 崩了多少」当成一个 finding 报出来，不假装 90% 覆盖在 shift 下还成立。
- **数据面信号先做最小受控模拟，不一上来接 RIPE Atlas**：给若干已知事件**注入合成 latency shift / reachability change**，验证「控制面分数 + 数据面异常」如何改变 triage 优先级。⚠️ **框定为 pipeline/机制演示，不是检测力评估**——自己注入信号再检测到它是循环论证（项目一 §1「自造可分性」陷阱）；真实检测力须留给真实主动测量。
- 真实测量（RIPE Atlas/traceroute + 受控实验）数据工程重，**只放 Research 档；MVP 必须能独立成立**。

### What makes it strong

- 先讲诚实结论：自动化分诊在哪里必须让位给人工，以及为什么（校准 + 弃权，不押高分）。
- 用真实 base rate、alert budget、误报成本解读，而非裸 accuracy。
- 把稀缺的 IP 网络词汇做对（AS 关系 / AS-hegemony / ROA / MOAS / RPKI 有效性）。
- 对数据/标签局限据实写明，并说清生产环境会有何不同。

---

## 7. Source Leads to Verify

These are useful starting points for formal citations and implementation research. Each should be checked again before final project documentation.

> BGP / RPKI 主线的专门论文与数据源（2502.03378、2507.20434、Oscilloscope/HiDe、BGPStream/Qrator 等）见 §3.5「待核源清单」，不在此重复。

- NIST Cybersecurity Framework 2.0: https://www.nist.gov/cyberframework
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- MITRE ATT&CK Detection Strategies: https://attack.mitre.org/detectionstrategies/
- MITRE ATT&CK Network Traffic data source: https://attack.mitre.org/datasources/DS0029/
- Zeek logs documentation: https://docs.zeek.org/en/current/logs/index.html
- Malware-Traffic-Analysis.net: https://www.malware-traffic-analysis.net/
- Stratosphere IPS datasets: https://www.stratosphereips.org/datasets-overview
- RouteViews: https://www.routeviews.org/
- RIPE RIS: https://ris.ripe.net/
- LANL cyber security datasets: https://csr.lanl.gov/data/
- OTRF Security Datasets / Mordor: https://github.com/OTRF/Security-Datasets

---

## 8. Immediate Next Actions

> 注：网络纵深增项的优先级**低于主线 ④ AML-GNN**；以下是「若启动网络纵深」的动作序列。真正的胜负手是数据工程能否 join 通——那要跑、不是写，故 spike 优先于写提案。

1. **1 天 BGP 数据可行性 spike**（把风险前置）：
   - (a) 能否拉到 RPKI-invalid 路由（RouteViews/RIPE RIS + Routinator）；
   - (b) 能否算出 CAIDA AS-rel + IHR AS-hegemony + IRR/GeoIP 特征；
   - (c) 能否取到事件标签（BGPStream / Qrator Radar）；
   - 同时**精读 2502.03378 PDF**，查其代码/特征是否开源、缺陷是否如草稿所述。
   - **判定闸门（写死，不再凭感觉争论）**：一天内同时满足 ——
     (a) join 出 **≥100 条 RPKI-invalid 样本**（带 prefix/origin/ROA mismatch）；
     (b) 至少 **3 类核心特征**各算通（AS-rel / AS-hegemony / IRR 或 GeoIP）；
     (c) 至少 **1 个事件标签来源**接上（弱标签亦可，但须记录 provenance）。
     **三条全过 → 继续 BGP；任一不过 → 当天回落 DNS honest-audit，不拖延。**
2. **spike 过 → 只写一份提案**：「BGP 控制面诚实审计（MVP）→ 控制+数据面融合（Research）」，DNS honest-audit 作为「spike 失败时的回落」写进同一份的风险节。
3. **spike 不过 → 回落写 DNS honest-audit 提案**（family/tool/time holdout + host aggregation + alert budget）。
4. 提案模板（同规格）：problem statement / telemetry source / data sources（+ 三件套核实状态）/ MVP deliverables / evaluation plan（切分协议 + base-rate 基线）/ expected limitations / 差异化。
5. 建最小阅读清单（只放启动必需），创建项目目录 + 第一条可复现管线。
