# Data Science / ML / DL × Cyber Security — 学习与项目实施计划

> 目标：在英国求职 Cyber Security + ML/DL/Data Science 相关岗位，通过这些项目积累实战经验。
>
> 版本说明（v2.1）：在 v2 基础上做了两处结构性改进——(1) 项目组合补齐了「金融犯罪/AML 图学习」和「对抗 ML」两个英国高需求但原先空缺的方向；(2) 数据集库从「偏最新但部分 gated」调整为「最新 + 经典确定可得」并行，并标注了真实性/可获取性核实状态。

---

## 一、英国目标岗位市场分析

### 1.1 典型岗位名称

| 岗位名称 | 侧重方向 | 本计划覆盖项目 |
|---|---|---|
| AI Security Architect | AI 系统安全设计与评估；ML integrity / poisoning / provenance | 项目二（主）+ 项目一/四 integrity 线（见 §三.0 签名） |
| Machine Learning Security Engineer | ML 驱动的威胁检测系统 | 项目一、三 |
| AI / Cyber Threat Detection Engineer | 自动化威胁检测 | 项目一、三 |
| Security Data Scientist | 安全数据分析与建模 | 项目一、四 |
| Cyber Analytics Engineer | 日志与流量分析自动化 | 项目三 |
| Detection Engineer with ML | 检测规则 + ML 融合 | 项目三 |
| Threat Intelligence / OSINT Data Scientist | 威胁情报 | 项目三 |
| AI Red Team / Adversarial ML Researcher | AI 安全对抗研究 | 项目二、四（对抗扩展） |
| Fraud / Financial Crime ML Engineer | 金融安全风控 | 项目四 |

**市场信号**：英国 cyber 岗位自 2021 年增长约 194%，从业者约 84,000 人，技能短缺持续。伦敦金融体量使 Fraud / Financial Crime ML 成为最易投递的方向之一——这是 v2.1 新增项目四的核心动机。

### 1.2 JD 共性职责

1. **威胁检测与异常检测**：用 ML/DL 分析网络流量、endpoint logs、SIEM/云日志，识别恶意行为、C2 通信、横向移动。
2. **AI 驱动安全运营**：给 SOC/MDR/XDR 平台做自动 triage、告警富化、误报降低。
3. **LLM / GenAI 安全**：评估 prompt injection、RAG 数据泄露、jailbreak、模型滥用风险。
4. **网络技术与数据科学结合**：理解 TCP/IP、DNS、TLS、VPN、防火墙日志；不只会 sklearn，还要懂数据从哪里来。
5. **金融/保险/银行安全风控**：fraud detection、identity risk、transaction anomaly、AML（反洗钱）。

### 1.3 JD 技术栈要求

**编程与 ML**
- Python：pandas、numpy、scikit-learn、PyTorch、TensorFlow
- ML：classification、anomaly detection、clustering、time-series、**graph analytics（图分析，越来越被强调）**
- DL：LSTM / Transformer / Autoencoder / **GNN**（用于日志序列、流量序列、交易/认证图）

**安全工具**
- SIEM：Splunk、Elastic、Azure Sentinel
- 检测：Sigma、YARA、Suricata、Zeek、Wireshark
- Cloud：AWS / Azure / GCP security logs

**工程**
- Data engineering：SQL、Spark、Kafka、Airflow
- MLOps：Docker、Kubernetes、CI/CD、model monitoring、**drift detection（检测系统的概念漂移是真实痛点）**

**安全知识**
- TCP/IP、DNS、HTTP/TLS、VPN、firewall、proxy logs
- MITRE ATT&CK 框架
- SOC / SIEM / XDR 工作流
- Malware、phishing、C2、lateral movement 基础
- Identity：OAuth、SAML、Azure AD / Entra ID
- AI 安全：prompt injection、data poisoning、**adversarial examples / evasion**、AI governance

### 1.4 UK employer signals（治理与合规——英国岗位的隐性加分项）

英国雇主（尤其金融、关键基础设施、公共部门）在技术能力之外，普遍看重**数据治理、合规与可审计性**。把这些挂进项目叙事，比纯刷分更能打动 hiring manager：

| 信号 | 含义 | 最适合挂的项目 |
|---|---|---|
| **NCSC guidance** | 英国国家网络安全中心的检测/安全开发指南 | 项目一、三 |
| **GDPR / UK Data Protection Act** | 个人数据处理、最小化、再分发许可、数据驻留 | 全部（数据集许可叙事） |
| **NCSC AI / AISI（AI Safety Institute）** | LLM/agent 安全评测、red teaming 是英国国家级关注点 | 项目二 |
| **FCA + PRA SS1/23（Model Risk Management）** | 金融模型需有治理、验证、可解释、持续监控 | 项目四 |
| **Financial crime / AML compliance（POCA、MLR 2017）** | 反洗钱法规框架、SAR 上报、调查容量约束 | 项目四 |
| **Auditability / model risk** | 模型决策可解释、可追溯、可复现（model card、data card） | 全部 |
| **EU AI Act / UK pro-innovation AI 监管** | 高风险 AI 系统的透明度与风控义务 | 项目二、四 |

> 落地方式：不必长篇大论，只需在每个项目 README 的「合规/治理」小节用 2-3 句说明你考虑了哪些约束。例如项目四写明「按 PRA SS1/23 做了模型验证与可解释性，并以 human review budget 模拟 AML 团队的 SAR 调查容量」。

---

## 二、数据集参考库

> **核实状态图例**：✅ 已核实真实存在 ｜ 🔒 真实但需申请/填表获取 ｜ ⚠️ 需自行确认数据/代码是否已公开 ｜ ⭐ 强烈推荐（确定可得 + 广泛引用 + 参考资料多）
>
> **重要原则**：项目优先选「招聘方认得 + 拿得到 + 有参考 notebook」的数据集，其次才追最新。落地前务必确认「论文存在 + 数据可下载 + 许可允许」三件事。

### 2.1 经典基础数据集（确定可得，仍广泛使用）

| 数据集 | 方向 | 特点 |
|---|---|---|
| ⭐ NetFlow 统一系列（NF-UNSW-NB15-v2 / NF-BoT-IoT / NF-ToN-IoT / NF-CSE-CIC-IDS2018 / NF-UQ-NIDS-v2） | 网络入侵检测 | UQ 出品，统一 NetFlow 特征格式，**专为跨数据集泛化设计**——比单数据集刷分更有说服力 |
| ⭐ CICIDS2017（含修正版 Engelen 2021 / Lanvin 2022） | 网络入侵检测 | 原版有标注/处理 bug；用「修正版」本身体现研究成熟度 |
| UNSW-NB15 | 现代网络入侵检测 | 类别不平衡与类别重叠问题明显，适合学习现实难点 |
| CTU-13 | Botnet 流量 | 经典 botnet benchmark，适合 PR-AUC、极度不平衡评估 |
| ⭐ EMBER / EMBER2024 | 恶意软件静态检测 | PE 文件特征，LightGBM；对抗 ML 的标准底座 |
| BODMAS / SOREL-20M | 恶意软件检测 | BODMAS 含家族标签；SOREL-20M 由 Sophos/ReversingLabs 出（Sophos 是英国公司，加分） |

### 2.2 近期数据集（2023-2026，差异化用）

**网络 / IoT / IIoT**

| 数据集 | 年份 | 状态 | 场景 | 特色 |
|---|---|---|---|---|
| CICIoT2023 | 2023 | 🔒 | 通用 IoT 入侵检测 | 105 设备、33 种攻击、7 大类；含 PCAP + CSV + example notebook；如用 Kaggle/HF 镜像，需先确认其许可证、来源与再分发权限（数据治理意识在英国岗位是加分项） |
| CICIoMT2024 | 2024 | 🔒 | 医疗物联网安全 | 40 IoMT 设备、18 种攻击、Wi-Fi/MQTT/BLE；含设备生命周期 profiling |
| DataSense IIoT 2025 | 2025 | 🔒 | 工业物联网 | 同步 sensor time-series + network traffic；50 种攻击 |
| CICAPT-IIoT 2024 | 2024 | 🔒 | IIoT APT 检测 | APT29 行为、provenance logs + network traffic；20+ 攻击技术 |
| CIC-YNU-IoTMal 2026 | 2026 | ✅🔒 | IoT 恶意软件 | 10,000 样本；ARM/MIPS/x86；PCAP+STRACE+SAR；**含开源 sandbox（可复现）** |

**Phishing / URL / DNS**

| 数据集 | 年份 | 状态 | 说明 |
|---|---|---|---|
| ⭐ PhishTank / OpenPhish（实时 feed） | — | ✅ | 实时钓鱼 URL，永远「新鲜」，适合做实时检测 demo |
| DeepURLBench | 2024/2025 | ⚠️ | 多分类恶意 URL：benign、phishing、malicious |
| PhreshPhish | 2025 | ⚠️ | 大规模 phishing website，减少 leakage，提升真实 base rate |
| MalURLBench | 2026 | ⚠️ | 面向 LLM agent 的 malicious URL；61,845 攻击实例 |

**LLM / Agent 安全**

| 数据集 / Benchmark | 年份 | 状态 | 说明 |
|---|---|---|---|
| ⭐ AgentDojo | 2024 | ✅ | 97 agent tasks，629 安全测试；工具调用 + 间接 prompt injection；NeurIPS D&B |
| AgentDyn | 2026 | ✅ | AgentDojo 升级版；60 开放任务，560 injection cases；官方实现 `SaFo-Lab/AgentDyn` |
| ⭐ Meta CyberSecEval（PurpleLlama） | 2024+ | ✅ | 大厂维护的 LLM 安全评测；含 prompt injection + 不安全代码生成；权威度高 |
| ⭐ HackAPrompt 数据集 | 2023 | ✅ | ~60 万真实对抗 prompt（竞赛产出）；训练 injection detector 的优质料 |
| JailbreakBench | 2024 | ✅ | 100 类有害行为 + 标准化 jailbreak 评估 |
| Lakera PINT / Gandalf | 2024+ | ✅ | 演示性强的 prompt injection 评测/靶场 |
| CyberMetric | 2024 | ✅ | Cyber 安全 Q&A benchmark；80/500/2000/10000 题 |

> 配套框架背书：**OWASP LLM Top 10** 作为威胁分类骨架；**garak**（NVIDIA 的 LLM 漏洞扫描工具）做自动化探测。

**SIEM / SOC / 日志**

| 数据集 | 年份 | 状态 | 说明 |
|---|---|---|---|
| ⭐ LANL Comprehensive / Unified Host-Network | 2015/2018 | ✅ | 认证日志 + 横向移动**金标准**，海量论文使用；做 lateral movement / 认证图必选 |
| ⭐ Loghub（HDFS / BGL / Thunderbird 等） | — | ✅ | 日志异常检测的事实标准；原 v2 遗漏，强烈建议补上 |
| DARPA OpTC | 2019 | ✅ | 大规模 host telemetry；APT 检测常用 |
| CERT Insider Threat（CMU） | — | ✅ | 内部威胁，差异化好 |
| Multi-Source Cybersecurity Logs | 2026 | ✅⚠️ | 870 sessions，2.3M events；Windows+network+browser；12 tactics/53 techniques；需定位数据下载点 |
| OpenSOC-AI | 2026 | ✅ | SOC 日志分类+ATT&CK+severity；TinyLlama LoRA；**权重/数据/pipeline 已公开** |
| Smart-SIEM / Wazuh Web Attack | 2026 | ⚠️ | 46,454 条 Wazuh events；行为上下文感知检测 |
| LMDG | 2025 | ⚠️ | 横向移动检测；25 天 944GB 日志；process-tree 标注 + ATT&CK TTPs |
| Mordor / OTRF Security Datasets | — | ✅ | Windows/Sysmon 日志 + ATT&CK 映射；Sigma rule testing 经典 |
| EVTX-ATTACK-SAMPLES | — | ✅ | Windows EVTX 攻击样本；适合 detection engineering |
| Splunk BOTS | — | ✅ | SOC analyst 训练数据；贴近 SOC 工作流 |

**金融犯罪 / Fraud / AML（v2.1 新增，对应项目四）**

| 数据集 | 状态 | 说明 |
|---|---|---|
| ⭐ Elliptic / Elliptic++ | ✅ | 比特币交易/地址图，含 graph 结构 + 标签；GNN + AML 极佳；`git-disl/EllipticPlusPlus`，参考 repo 丰富 |
| IEEE-CIS Fraud Detection (Kaggle) | ✅ | 大规模信用卡欺诈表格数据；特征工程经典 |
| PaySim | ✅ | 移动支付欺诈模拟数据；适合不平衡 + 反欺诈 pipeline |
| ULB Credit Card Fraud | ✅ | 极度不平衡（0.17% 正例）经典 benchmark |

---

## 三、核心项目组合

> v2.1 调整：项目一从「又一个 IoT 分类器」重定位为「诚实评估 NIDS」；项目三加入图视角；**新增项目四（AML 图学习）填补金融方向**；并加入一条贯穿所有项目的 MLOps/drift + live demo 加分项。
>
> **跨项目加分项（不单列）**：至少在一个项目里加入 concept drift 监控（数据按时间分片，观察模型性能衰减），并为 1-2 个项目做 Streamlit / Hugging Face Space 在线 demo——recruiter 极吃 live demo。

### 0. 贯穿四项目的签名：脏标签 / 漂移 / 投毒下的可信度（2026-06-30 重框）

> 这是把四个项目从「四个孤岛 + 方法论可迁移」升级成**一个论点**的主线。原签名「诚实评估」太窄，只覆盖项目一的泄漏/切分；真正贯穿全部的更硬主线是：**当标签脏、只在被调查过的样本上有标签（选择性标注）、分布随时间漂移、且输入/标签可被对手投毒时，模型还可信吗？** 这正是 AI Security / Model Risk 岗（如 MI6 AI Security Architect 要的 ML integrity / poisoning / provenance / misuse）逐字想听的故事。

| 威胁面 | 在四项目里的落点 |
|---|---|
| **特征泄漏 + 跨分布崩塌** | 项目一（IP/重复流泄漏、LODO 跨数据集、真 temporal split） |
| **标签来源泄漏（label provenance）** | 项目四（AML 选择性标注 unknown≠benign / 钱包标签=交易标签 guilt-by-association 传播、非独立监督）—— honest-nids 从「特征泄漏」到「标签泄漏」的升级 |
| **对抗输入完整性** | 项目二（prompt injection：把不可信数据当系统指令） |
| **数据/模型投毒** | 项目二（HackAPrompt 对抗料）+ 可选对抗 ML 扩展（EMBER evasion）+ 路由安全 backlog（公开 BGP monitor 可投毒） |
| **操作点脆弱性（阈值/采样/预算下指标漂移）** | 全部——用曲线（PR-AUC、coverage-vs-abstention）不用单点 accuracy |

**定位后果（影响投递排序）**：把签名定义成「可信度」而非窄义「诚实评估」后，**AI Security / Model Risk 池从第三升到与 cyber 并列第二**——因为项目二天然在此，项目一/四的 integrity 线也落在此，三个项目共同支撑这条线，比单一 LLM 项目更有说服力。对外报告（每个 README/narrative）都应显式挂这条主线，而不是各讲各的分数。

### 项目一：诚实评估的网络入侵检测（NIDS）

**目标岗位**：ML Cyber Security Engineer、Network Security Data Scientist

**核心叙事**：这个领域的公开项目高度饱和，单纯刷 CICIoT2023 到 99% 没有差异化。本项目的卖点不是分类器本身，而是**揭穿并避免 benchmark 虚高**——数据泄漏、随机切分过于乐观、跨环境泛化崩塌，这正是资深从业者最常吐槽的痛点。

**数据集**：
- 主：**NetFlow 统一系列**（NF-UNSW-NB15-v2 / NF-ToN-IoT / NF-CSE-CIC-IDS2018）——天然支持 leave-one-dataset-out 跨数据集实验。
- 辅：**修正版 CICIDS2017**（用 Engelen/Lanvin 修正版而非原始有 bug 版）。
- 差异化扩展：CICIoT2023 / CICIoMT2024（IoT/医疗场景）。

#### 实施步骤

**Step 1：复现「乐观 baseline」并故意暴露问题**
- 随机切分 + 全特征训练，得到虚高的 99% accuracy。
- 显式分析：哪些特征是「环境泄漏」（如 IP、端口、时间戳直接泄露标签）。

**Step 2：诚实重做**
- 按时间 / 按攻击活动切分（temporal split），杜绝同一攻击会话同时进训练和测试。
- 移除泄漏特征，只保留可泛化的 flow 统计特征。
- 对比「乐观」与「诚实」两套数字，这张对比表就是项目核心卖点。

**Step 3：跨数据集泛化（LODO）**
- 在数据集 A 训练，数据集 B 测试（NetFlow 统一格式让这一步可行）。
- 量化 F1 跌幅，讨论为什么模型学到的是数据集特征而非攻击本质。

**Step 4：建模与不平衡**
- LightGBM / XGBoost / CatBoost baseline；class_weight / SMOTE / Balanced RF。
- 评价：macro-F1、PR-AUC、per-class recall（不看裸 accuracy）。

**Step 5：可解释性**
- SHAP global + per-attack 解释（DDoS 靠 packet size uniformity、Recon 靠 flow behaviour 等）。

**Step 6（加分）：concept drift 监控**
- 把数据按时间分片，画出模型性能随时间衰减曲线，引出「检测模型需要持续再训练」的运维结论。

#### 参考资源

| 资源 | 重点 |
|---|---|
| [CICIoT2023 原始论文](https://www.mdpi.com/1424-8220/23/13/5941) | 数据集构造与 baseline |
| [Engelen 2021: Troubleshooting CICIDS2017](https://ieeexplore.ieee.org/document/9474425) | CICIDS2017 标注/处理错误剖析 |
| [BRIDGE / TCH-Net](https://github.com/Ammar-ss/TCH-Net) | 统一特征 + LODO 跨数据集评估范式 |
| [Conditional SHAP Attack Attribution](https://arxiv.org/abs/2603.22771) | 按攻击类别的 SHAP 归因 |

#### 项目推荐标题

```
Honest NIDS: Exposing Data Leakage and Cross-Dataset Generalisation
Gaps in Network Intrusion Detection Benchmarks
```

---

### 项目二：LLM Agent Prompt Injection 防御

**目标岗位**：AI Security Engineer、AI Security Architect、LLM Red Team

**数据集 / Benchmark**：AgentDojo（主）+ AgentDyn（升级，官方实现 `SaFo-Lab/AgentDyn`）

#### 背景与威胁模型

这类项目不是 `CSV → label → train classifier`，而是：**在带工具的 LLM agent 模拟环境里，测试 agent 能否区分用户合法指令与外部数据中的恶意指令。**

```
用户：有合法任务（发邮件、查日历、下购物单）
Agent：能调用工具（email、calendar、drive、bank、shop）
工具返回内容：不可信（可被攻击者控制）
攻击者：在邮件正文、云盘文档、网页评论、issue 等位置植入恶意指令
风险：Agent 把不可信数据当作高优先级系统指令执行
后果：越权发送邮件、删除文件、转账、泄露凭证、创建恶意日历事件
```

#### AgentDojo 数据结构

```
user_task：用户合法任务（如"查找日历中某活动的参与者邮箱"）
injection_task：攻击者希望 agent 执行的恶意目标
injection_vector：注入位置（日历描述、邮件正文、云盘文档）
tools：search_calendar_events、send_email、delete_file …
evaluation：utility = 正常任务是否完成；security = 恶意目标是否被阻止
```

#### AgentDyn 购物场景样本

```
用户任务：购物车中只保留 electric toothbrush，删除其他商品并下单。
Agent 工具：view_cart / cart_remove_product / checkout_selected_cart
            / get_shopping_linked_unread_emails(←注入点) / verify_shopping_account
攻击路径：Agent 为完成 checkout 读取邮箱 OTP 时，邮箱中混入带恶意指令的邮件。
结果记录：utility: true（购物完成）  security: false（攻击被触发）
```

#### 参考资源

| 资源 | 说明 |
|---|---|
| [AgentDojo paper](https://arxiv.org/abs/2406.13352) / [GitHub](https://github.com/ethz-spylab/agentdojo) | 主 benchmark |
| [AgentDyn paper](https://arxiv.org/abs/2602.03117) / [GitHub](https://github.com/SaFo-Lab/AgentDyn) | 动态扩展版（官方实现） |
| [Meta CyberSecEval / PurpleLlama](https://github.com/meta-llama/PurpleLlama) | 大厂 LLM 安全评测，补充权威基线 |
| [HackAPrompt dataset](https://huggingface.co/datasets/hackaprompt/hackaprompt-dataset) | 60 万对抗 prompt，训练 detector |
| [StruQ](https://arxiv.org/abs/2402.06363) / [CaMeL](https://arxiv.org/abs/2503.18813) | 结构化/数据流分离防御思想 |
| [garak](https://github.com/NVIDIA/garak) | LLM 漏洞自动扫描工具 |

#### 实施步骤

1. **威胁建模**：画 agent 工具调用图，标注敏感操作与注入位置。
2. **Baseline（无防御）**：跑 benchmark，记录 Utility Rate、Attack Success Rate、Tool Misuse。
3. **防御对比**：system prompt warning / delimiter / tool filter / injection detector / detector+filter / CaMeL-style 数据流控制。
4. **ML 检测器**：输入 `tool_output + user_task + available_tools`，标签 benign/injected；TF-IDF+LR → embedding+LR → DeBERTa fine-tune；可用 HackAPrompt 增强训练数据。
5. **评价指标**：Utility Rate、Attack Success Rate、Security Pass Rate、Over-defense Rate、Tool Misuse Rate、Cost/latency。
6. **输出**：三维 trade-off 对比表（Utility×Security×Over-defense）+ 攻击 trace 分析 + 工具调用图。

#### 成本控制与复现策略（agent benchmark 是真实 LLM 调用，必须先规划）

- **固定模型清单**：明确三档并全程只用这三个，避免随手换模型导致结果不可比——
  - cheap API model（如便宜的 GPT/Claude 小模型）做主力跑量；
  - local open-weight model（如 Llama / Qwen 本地）做零成本复现与消融；
  - strong API model 只在最终对比时各跑一次，控制开销。
- **Trace replay（最重要的省钱手段）**：把每次运行的工具调用序列、LLM 输入/输出、injection 内容、最终 utility/security 判定**全部落盘成 JSON**。后续做防御对比、画图、改评估口径时直接 replay 已保存的 trace，**不重新调 LLM**。
- **预算表**：开跑前估算每轮 `tasks × cases × 模型 × 平均 token`，列出预计 token / cost / latency，设一个硬上限。
- **防御失败分类**：把每个失败 case 归到四类之一——`拒绝过度（over-defense）`、`攻击成功（attack success）`、`任务失败（utility loss）`、`工具误用（tool misuse）`——这张分类表比单一 ASR 数字更能讲清防御的代价。

> ⚠️ repo 待核实：AgentDyn 的官方仓库我查到 `SaFo-Lab/AgentDyn`（标为 official implementation）与 `leolee99/AgentDyn`（疑似作者镜像）两个，写进 README 前请最终确认 canonical 来源，避免引用错误 repo。

#### 项目推荐标题

```
Prompt Injection Defense Lab for Tool-Using LLM Agents:
Utility-Security Trade-offs on AgentDojo and AgentDyn
```

---

### 项目三：SIEM / SOC 日志智能分析（含图视角）

**目标岗位**：Cyber Analytics Engineer、Detection Engineer、SOC Automation Engineer

**数据集（主线锚经典、确定可得；2026 数据集只作 bonus validation）**：
- **主线（SOC 富化 + ATT&CK 映射）**：**Mordor / OTRF Security-Datasets + EVTX-ATTACK-SAMPLES + Splunk BOTS**——有 Sysmon / 进程 / 命令行细节和 ATT&CK 映射，最适合做 enrichment 主线。
- **图子模块（横向移动）**：**LANL Comprehensive**（认证图金标准；它高度匿名、缺 process/ATT&CK 标签，所以**只用于横向移动检测，不进 ATT&CK 主线**）；可选 DARPA OpTC。
- **独立小 demo（日志解析/异常检测）**：**Loghub**（HDFS/BGL）——属于另一类任务（非结构化日志异常），单独成一个小 notebook。
- **Bonus validation（新颖性加分）**：Multi-Source Logs 2026、OpenSOC-AI 2026——⚠️ 它们很新（OpenSOC-AI 实验仅 450 train / 50 holdout），只作锦上添花，不作主依赖。

> v2.1 调整（采纳第 5 条反馈）：把原来 5 层的庞大设计拆成**一主线 + 一图子模块 + 一加分**，避免范围失控，也更贴近 Detection Engineer / Cyber Analytics Engineer 的预期。**LLM 只做解释层，不作核心检测器。**
>
> **🔻 2026-06-30 范围正式收敛（避免 sprawl，与四项目深度分层一致，见 §五.0a）**：项目三定位为**小 MVP / 关键词补位**，不是第四个深项目——它在组合里的唯一不可替代角色是补 **SOC / SIEM / ATT&CK / Sigma / detection-engineering** 关键词（honest-nids、AML 都给不出）。据此：
> - **MVP 核心（唯一必做）= 单层告警富化**：日志标准化 → Sigma baseline → LightGBM 富化分类（threat class / technique / severity）→ ATT&CK 两级映射 → 结构化告警输出 + **alert reduction 曲线**。
> - **图子模块（横向移动）= 可选扩展**：GNN 主证据放项目四；此处复用其图代码作「图方法跨域（身份图≠交易图）」证据，**时间紧可不做**。
> - **LLM 解释层 = 砍 / 最后再说**：与项目二 LLM 重叠，仅投 LLM-SOC 岗时才补。
> - 执行序排**最后（Phase 4）**，优先级低于 honest-nids 封板与 AML 旗舰。

#### 主项目：SIEM Alert Enrichment Pipeline

```
输入：多源日志（host + network；Sysmon/EVTX/网络事件）
输出：mitre_tactic、mitre_technique、severity_score、evidence_events、
      analyst_recommendation、false_positive_reason
使用者：SOC analyst
```

实施步骤：
1. **接入与标准化**：timestamp/host/user/process/command_line/src_ip/dst_ip/event_id/parent_process/URL/log_source。
2. **安全增强**：ATT&CK tactic/technique 映射、severity、asset criticality、user risk、事件序列上下文。
3. **检测**：Sigma 规则 baseline → LightGBM/XGBoost 行为上下文分类（threat class / technique / severity）。
4. **SOC 输出**：上述结构化告警字段。
5. **评价**：threat accuracy、ATT&CK mapping F1（tactic+technique 两级）、severity accuracy、FP rate、alert reduction rate。

#### 子模块（可选扩展，非 MVP）：Graph Lateral Movement Detection
- 用 LANL 认证日志构建「用户-主机认证图」，做异常路径 / 社区 / GNN 节点分类检测横向移动。
- 评价：恶意认证边/路径的 precision/recall；与规则基线对比。
- **定位**：复用项目四的图代码，作「图方法跨域（身份图 ≠ 交易图）」证据；GNN 主证据在项目四，**时间紧时跳过不影响 MVP**。

#### 加分（砍 / 最后再说，非 MVP）：LLM 解释层
- 用 OpenSOC-AI（TinyLlama+LoRA）风格对告警生成自然语言解释，**仅辅助 analyst，不替代检测**。
- ⚠️ 评估陷阱：严格 regex parser 会把 LLM 评成 0%，需用 fuzzy parser（见 [arXiv:2605.07293](https://arxiv.org/abs/2605.07293)）。
- **定位**：与项目二 LLM 工作重叠，仅在投 LLM-SOC 岗位时才补；否则不做。

#### 参考资源

| 资源 | 说明 |
|---|---|
| [Multi-Source Logs 2026](https://arxiv.org/abs/2606.18190) | 多源 SOC 日志 + ATT&CK 细粒度标签 |
| [OpenSOC-AI 2026](https://arxiv.org/abs/2604.26217) | 轻量 LLM SOC 自动化（含 codebase + 权重） |
| [LANL Cyber Events](https://csr.lanl.gov/data/cyber1/) | 认证图 / 横向移动金标准 |
| [Loghub / LogPAI](https://github.com/logpai/loghub) | 日志异常检测标准数据 |
| [Mordor / OTRF](https://github.com/OTRF/Security-Datasets) | ATT&CK 场景日志 + Sigma 测试 |

#### 项目推荐标题

```
SIEM Log Intelligence Pipeline: Multi-Source Correlation,
Graph-Based Lateral Movement Detection, and LLM-Assisted SOC Triage
```

---

### 项目四（capstone）：金融犯罪 / AML 图学习

**目标岗位**：Fraud / Financial Crime ML Engineer、Security Data Scientist（伦敦金融市场命中率最高）

**为什么加这个**：原 v2 三项目全是「检测」且偏网络/系统侧，完全没覆盖英国体量最大的金融安全方向；图学习是稀缺技能，正好双重差异化。

**数据集**：**Elliptic++**（主，比特币交易+地址图）+ IEEE-CIS Fraud（辅，表格欺诈对照）。

#### 卖点：当 AML 队列不一致——是打分粒度还是标签来源？

> **When AML queues disagree: scoring granularity or label provenance?**

交易级打分和 actor/地址级调查队列往往不一致（Malik 2026 实证 Jaccard 低）。本项目**跨过**「两队列不重叠」这一步，把不一致**拆成来源**：scoring granularity（聚合损失）vs label provenance（交易标签体系 ≠ 地址标签体系）。**不是**「又一个 Elliptic GNN 刷 AUC」——表格 baseline 是「图是否真有用」的诚实对照（Weber 2019 自报 RF > 普通 GCN），GNN 退居 Reference 档附录（很可能证明「再复杂的模型也修不了标签口径错配」）。这把 honest-nids 的「特征泄漏」签名升级到「**标签体系先决定了哪些评估问题能被诚实回答**」。

#### 背景与已核实数据事实（Elliptic++）

```
问题：在比特币交易网络中识别非法（洗钱）交易/地址，并把交易级分数投影成 actor 调查队列。
数据：交易图 203,769 笔 / 49 时间步（illicit=已标注内 9.76%）+ 地址图 822,942。
     标签 1=illicit / 2=licit / 3=unknown（未标注 ≠ 良性）。
```

进入建模前，两条**确定性数据事实**（notebooks/03–04 实测，非文献转述）已重塑问题：
- **交易图按时间步完全断开**：全部 234,355 条边两端 Δ(Time step)=0，无跨期边 → 裸拓扑无跨期结构信号（解释此处 GNN 难有增益）。
- **钱包 illicit 标签 = 交易 illicit 标签的确定性传播**：`wallet-illicit ⟺ 地址参与过 ≥1 illicit 交易`，**14,266/14,266 双条件零例外** = guilt-by-association、事后/全局。→ actor 标签**不是独立监督**（是 tx 标签用 OR/max 抬到实体级），把「actor-level PR-AUC」当独立成绩报是误导。

#### 核心发现（MVP 薄切片已跑通，`results/experiments.csv` + `notebooks/01–04`）

> **3 条实腿 + 1 条明确推迟**。旗舰问句「granularity vs provenance」的诚实答案（当前）：**provenance 是操作轴；granularity 在 max 聚合下不存在，需 mean/sum 才谈得上**。

1. **【实】诚实表格 baseline 立住**：temporal LightGBM **PR-AUC 0.813**（随机基线 0.065）；node2vec / IsolationForest 近/劣于随机 → **判别力在工程特征、不在裸拓扑**（呼应 Weber/Deprez）。
2. **【实】label provenance = guilt-by-association**（见上双条件）：illicit 类上 tx 与 wallet 标签**构造上不可能冲突**，故队列不一致**不是** illicit 的 label-conflict。
3. **【实】unknown ≠ benign（错误示范，Setting C）**：把 69% unknown 当 benign → actor PR-AUC 0.736→**0.309**，但 **top 队列零 licit**——precision「崩塌」全来自 unknown 被误记 FP（selective-labeling coverage artifact，非模型退化）。详见 `reports/setting-c-unknown-not-benign.md`。
4. **【实】队列不一致归因（列联表，非加法）**：队列位置（input+output participation）× 钱包标签，每 actor 判唯一主导成因——**coverage-gap 主导**（unknown 在队 11,938@5%）> detection-miss（1,940）≫ label-conflict（193≈0）。
5. **【推迟】scoring granularity / 投影损失**：**max 下 ≡ 0**（transaction-first 与 actor-first 取到的地址集合相同，Jaccard=1）。§2 的 tx-yield vs actor-yield 差是**不同调查单元/分母的口径差、Δ 符号还随预算翻转**，**不是**投影损失。真正的投影损失要 mean/sum/top-k 聚合才非零 → Reference 档扇出再测。

#### 实施步骤（分档，先 MVP 再升档）

- **MVP（✅ 已完成）**：EDA → temporal split + **纯表格 LightGBM baseline**（不碰 GNN）→ 非 GNN 对照（node2vec / IsolationForest）→ **actor 投影（max，input+output participation）+ 两标签体系 yield 对照** → **标签来源审计（guilt-by-association 双条件）** → **Setting C 错误示范** → **归因表雏形**。切分口径统一 temporal；**transductive vs inductive** 两设定各自给结论（AML 最常被审计质疑的点）；Time step 只排序不进特征。
- **Reference-grade**：扇出聚合策略（mean / sum / top-k / time-decay——解除 max 退化、投影损失非零）；GraphSAGE / GAT / EvolveGCN，量化图相比表格 baseline 的**净增益来自结构还是时序**（不预设图会赢）。
- **Strong**：**AML Decision Card**（给调查员，不止给指标）——每条 top alert 输出：交易/地址 + 图证据子图（GNNExplainer）+ 校准后置信度 + 决策（escalate / clear / **investigate**，不确定主动 abstain）+ **why-not-confident**（标签弱/分布外/证据不足）。对标 Quantexa/ComplyAdvantage 的 case 分诊，与路由 backlog 的 RPKI Decision Card 同模具（`network-detection-candidates-draft.md` §6），建一次复用。
- **Research-grade**：Elliptic2 子图分类 / 有向多重图 GNN（Egressy）。

#### 评价指标（按真实 AML 工作方式，而非单纯 GNN F1）
- **precision@k / recall@k**：AML 团队按调查容量处理 top alerts，整体 F1 不如「前 k 个告警里有多少真命中」有意义。
- **Human review budget**：设定「每天只能调查 top 100 alerts」的约束，报告在该预算下的命中率与漏报——直接对应合规团队的实际产能。
- **illicit 类 precision/recall/F1、PR-AUC**：强调 recall（漏报洗钱代价高）。
- **False positive case study**：挑几个「模型判可疑但可能合法」的案例，解释为什么会误判、analyst 该如何复核——这比任何分数都更像真实金融犯罪检测工作。
- **coverage @ abstention 曲线**：给定弃权率，自动决策覆盖多少、剩多少进 investigate 队列。⚠️ precision@k / recall@k / review-budget 命中率都是**操作点指标**，随阈值/采样漂移（项目一 §2.1 已证 recall@0.5 不稳）——**报曲线不报单点**，阈值无关的 PR-AUC 留作模型对比骨架。

#### 参考资源

| 资源 | 说明 |
|---|---|
| [Elliptic++ repo](https://github.com/git-disl/EllipticPlusPlus) | 数据 + 基线 |
| [Elliptic 原始论文 (Weber 2019)](https://arxiv.org/abs/1908.02591) | AML + GCN 奠基工作 |
| [EvolveGCN](https://github.com/IBM/EvolveGCN) | 时序图节点分类 |

#### 项目推荐标题

```
When AML Queues Disagree: Scoring Granularity vs Label Provenance
in Bitcoin Transaction/Actor Networks (Elliptic++)
```
（旧标题「Graph-Based AML with GNNs and Explainable Subgraphs」= Strong/Research 档的子标题，非主线卖点。）

#### （可选）对抗 ML 扩展

若想同时打 **AI Red Team / Adversarial ML** 方向，可把项目四或项目一延伸：用 **EMBER** 训练 malware 分类器 → 做 evasion attack（扰动特征绕过检测）→ 加对抗训练防御。这条线把项目二（LLM 安全）和传统 ML 安全连成一条「攻防」主线，叙事完整。

---

## 四、学习路线

### 4.1 前置知识准备

**网络基础**：TCP/IP、DNS、HTTP/TLS、VPN；packet/flow/session 区别；DDoS/Brute Force/Recon/Botnet/C2/Lateral Movement 攻击原理。

**ML/DL 基础**：sklearn pipeline；imbalanced learning（class_weight/SMOTE/macro-F1/PR-AUC）；树模型；CNN/LSTM/Autoencoder/Transformer；**GNN（GCN/GraphSAGE/GAT，项目三、四需要）**；SHAP/LIME。

**安全工具基础**：MITRE ATT&CK；SIEM 概念（rule/alert/triage/enrichment）；Sigma 语法；Wireshark/Zeek 基础。

### 4.2 学习资源推荐

| 方向 | 资源 |
|---|---|
| 网络安全基础 | TryHackMe（SOC Level 1）、Hack The Box Academy |
| MITRE ATT&CK | attack.mitre.org；Navigator |
| 图学习 | PyTorch Geometric 官方教程；Elliptic 上的 GCN 入门 notebook |
| LLM 安全 | AgentDojo README；OWASP LLM Top 10；garak |
| SIEM 实践 | Splunk BOTS；Elastic Security |

---

## 五、执行顺序与时间规划

> 顺序按「先建基本盘 → 再差异化 → 再打金融市场 → 工程收尾」，比 v2 的「IoT→Agent→SIEM」更贴合英国岗位分布。

### 5.0 每个项目的三档交付（避免被单个过大计划拖住）

> 核心原则：**先把四个项目都推到 MVP，再回头逐个升档**。这样任何时间点你都有「四个能投的项目」，而不是「一个完美项目 + 三个空壳」。质量门槛也随档位递增，不要一开始就上重型脚手架。

| 档位 | 周期 | 交付内容 | 仓库质量门槛 |
|---|---|---|---|
| **MVP** | 2-3 周 | README + 核心 baseline + 3-5 张关键图表 + 一句话结论 | README、requirements.txt、固定随机种子、results.csv |
| **Reference-grade** | 4-6 周 | 可复现实验、错误/失败案例分析、评估指标完整、一个 demo | 加 data_card、model_card、threat_model、Makefile |
| **Research-grade** | +若干周 | drift 监控、GNN/时序图、LLM、在线部署 | 加 Dockerfile、CI、checksum；原始大数据不入库，只留下载说明 |

各项目的 MVP 锚点（确保 2-3 周能出货）：
- 项目一 MVP：随机切分 LightGBM baseline + 「乐观 vs 诚实」对比表。
- 项目二 MVP：AgentDojo 无防御 + tool filter 两组,出 utility/attack-success 对比。
- 项目三 MVP：Mordor/EVTX 上 Sigma 规则 + LightGBM 分类,出 ATT&CK 映射。
- 项目四 MVP：**纯表格 LightGBM**(不碰 GNN),建立 AML 非图基线——因此项目四可安全提前到 Phase 2-3,不会被图学习卡住。

> 注：完整的「统一仓库质量标准」（每个 repo 必备文件清单、按档位递增的门槛）见**第六章**。

### 5.0a 四项目的深度分层（2026-06-30 收敛：收敛的是「投入」不是「数量」）

> 原则：**先全推到 MVP（§5.0），再按下表分配升档投入**——不是四个都堆到同等深度。求职上「2 个深旗舰 + 1 精悍钩子 + 1 关键词补位」比「4 个半成品」更经得起深度面试。重叠信号去重：图的主证据在项目四、LLM 的主证据在项目二，其余项目对应层只标「复用、非原创深挖」。

| 项目 | 角色 | 目标档位 | 在组合里的不可替代信号 | 去重说明 |
|---|---|---|---|---|
| **① honest-nids** | 旗舰 | Reference→Research | 泄漏/跨分布崩塌/诚实评估**签名**；先封板（含受众分层报告）再开新项目 | — |
| **④ AML-GNN** | 旗舰 | Reference→Research | 金融/AML（伦敦命中率最高）+ 图 + label-provenance + Decision Card | **图 + Decision Card 主证据在此** |
| **② LLM 注入** | 钩子 | MVP+ | AI-security / agent 安全 / 对抗输入完整性 | **LLM 安全主证据在此** |
| **③ SIEM** | 关键词补位 | 单层小 MVP | SOC/SIEM/ATT&CK/Sigma/detection-engineering 关键词（①④给不出） | 图层/LLM 层复用①②④，标可选 |

> ⚠️ 何时真砍项目三：仅当目标 JD 完全不含「Detection Engineer / SOC / ATT&CK」时，才把项目三整体降为 backlog；否则保留其单层 MVP 以保关键词命中（撤回了早前「直接砍 SIEM」的提法，理由见决策记录）。

### Phase 1：诚实评估 NIDS（项目一）
EDA → 乐观 baseline → 暴露泄漏 → 诚实重做（temporal split）→ 跨数据集 LODO → SHAP → drift 曲线。
**里程碑**：一个带「乐观 vs 诚实」对比表和跨数据集泛化分析的 NIDS repo。

### Phase 2：AI Security 差异化（项目二）
阅读 AgentDojo → 无防御 baseline → 防御对比 → 自建 ML detector → 整合 AgentDyn。
**里程碑**：带三维 trade-off 表 + 攻击 trace 分析的 agent security repo。

### Phase 3：金融 AML 图学习（项目四）
Elliptic++ EDA → 表格 baseline → GNN → 时序图 → 可解释子图。
**里程碑**：表格 vs 图模型对比 + 可解释 AML demo（命中伦敦金融市场）。

### Phase 4：SOC 工程收尾（项目三）
日志标准化 + Sigma baseline → ML 分类 → LANL 认证图横向移动 → LLM 解释 → 端到端 pipeline。
**里程碑**：规则 + ML + 图 + LLM 多层 SIEM pipeline。

> 时间紧时的最小可投组合：**项目一 + 项目二 + 项目四**（覆盖网络检测、AI 安全、金融三大块，且项目四差异化最强）。项目三作为后续补充。

---

## 六、统一仓库质量标准

> 目的：让四个 repo 长得「像同一个工程师做的、可被审计、可复现」。这本身就是英国岗位看重的 data governance / model risk 信号（见 1.4）。
>
> **关键原则（呼应第五章三档）**：质量门槛随档位递增，不要在 MVP 阶段就上重型脚手架，否则会拖慢出货。

### 6.1 每个 repo 的文件清单（按档位递增）

| 文件 / 实践 | MVP | Reference-grade | Research-grade | 作用 |
|---|:---:|:---:|:---:|:---:|
| `README.md`（问题、数据、方法、结果、复现命令） | ✓ | ✓ | ✓ | 入口与叙事 |
| `requirements.txt` / `environment.yml` | ✓ | ✓ | ✓ | 环境可复现 |
| 固定 random seed | ✓ | ✓ | ✓ | 结果可复现 |
| `results/experiments.csv`（实验结果落盘） | ✓ | ✓ | ✓ | 可追溯、可对比 |
| `data_card.md`（来源、许可、再分发权限、字段、偏差） | | ✓ | ✓ | 数据治理 / GDPR 意识 |
| `model_card.md`（用途、限制、指标、风险） | | ✓ | ✓ | model risk / 可审计 |
| `threat_model.md`（攻击者、目标、风险、假设） | | ✓ | ✓ | 安全思维显性化 |
| `Makefile` / `justfile`（一键复现） | | ✓ | ✓ | 工程规范 |
| 合规/治理小节（挂 1.4 的相关信号） | | ✓ | ✓ | UK employer signal |
| `Dockerfile` | | | ✓ | 环境隔离与部署 |
| CI（lint + 冒烟测试） | | | ✓ | 工程成熟度 |
| 在线 demo（Streamlit / HF Space） | | | ✓ | recruiter 直观感受 |

### 6.2 数据治理硬规矩（所有档位都遵守）

- **绝不提交原始大数据**：仓库里只放**下载脚本/说明 + checksum（如 SHA-256）**，让他人能复现而不触碰许可与体积问题。
- **许可证可见**：`data_card.md` 写清每个数据集的 license、来源 URL、再分发权限；用镜像（Kaggle/HF）时确认其再分发合法。
- **不提交密钥/凭证**：API key 走环境变量；提供 `.env.example`。
- **PII / 敏感样本**：恶意软件、攻击样本、含个人数据的日志按各自数据集要求处理，必要时脱敏，并在 README 说明。

> 这一章不必在写计划时就全部落地——它是每个项目**升到 Reference-grade 档时的 checklist**，按需勾选即可。

---

## 七、项目集结构

```
cyber-ml-projects/
│
├── 01-honest-nids/
│   ├── notebooks/   (01_optimistic_baseline / 02_leakage_analysis /
│   │                 03_honest_temporal_split / 04_cross_dataset_lodo /
│   │                 05_shap / 06_drift_monitoring)
│   ├── src/         (feature_engineering.py, evaluation.py)
│   ├── reports/findings.md
│   └── README.md
│
├── 02-agent-prompt-injection-defense/
│   ├── notebooks/   (01_baseline_no_defense / 02_defense_comparison /
│   │                 03_injection_detector)
│   ├── defenses/    (tool_filter.py, pi_detector.py)
│   ├── traces/      (attack_trace_samples.json)
│   ├── experiments/results_table.csv
│   └── README.md
│
├── 03-siem-log-intelligence/
│   ├── notebooks/   (01_log_normalization / 02_attck_mapping /
│   │                 03_ml_classifier / 04_lateral_movement_graph /
│   │                 05_llm_triage)
│   ├── parsers/ rules/sigma_rules/ models/
│   └── README.md
│
└── 04-aml-graph-learning/
    ├── notebooks/   (01_eda / 02_tabular_baseline / 03_gnn /
    │                 04_temporal_gnn / 05_explainable_subgraph)
    ├── src/
    └── README.md
```

**每个项目 README 必含**：问题背景 → 数据集说明 → 威胁模型 → 方法与实验设计 → 评价指标及结果 → 错误/失败案例分析 → 可复现命令。
**加分**：1-2 个项目配 Streamlit / Hugging Face Space 在线 demo。

---

## 八、简历表达参考

**项目一（诚实 NIDS）**
```
Built a network intrusion detection study that quantifies the gap between
optimistic random-split benchmarks and honest temporal/cross-dataset evaluation
on NetFlow-unified and corrected CICIDS2017 datasets. Identified data-leakage
features, applied LODO cross-dataset testing, and used SHAP for attack attribution.
```

**项目二（Agent PI 防御）**
```
Evaluated prompt injection defenses for tool-using LLM agents on AgentDojo and
AgentDyn, comparing tool filtering, prompt-based defenses and ML detectors
(DeBERTa, PromptGuard2) across utility, attack-success and over-defense rates.
```

**项目四（AML 队列不一致 / 标签来源）**
```
Investigated why transaction-level scores and actor-level AML investigation queues
disagree on Elliptic++, separating scoring-granularity (projection loss) from label
provenance. Showed the wallet illicit label is a deterministic guilt-by-association
propagation of the transaction label (biconditional, no exceptions), so actor
evaluation is not independent supervision; demonstrated the unknown≠benign trap
(treating unlabelled actors as negative is a coverage artifact, not model error) via
temporal LightGBM baselines and a queue-disagreement attribution table. GNNs
(GraphSAGE/EvolveGCN) and GNNExplainer subgraphs reserved for the upgrade tier.
```

**项目三（SIEM）**
```
Designed a multi-layer SIEM log intelligence pipeline combining Sigma rules,
LightGBM classification, graph-based lateral-movement detection on LANL auth logs,
and LLM-assisted triage with MITRE ATT&CK mapping and severity scoring.
```

---

## 九、知识能力覆盖总结

| 能力维度 | 项目一 | 项目二 | 项目三 | 项目四 |
|---|:---:|:---:|:---:|:---:|
| 网络流量理解 | ✓ | | ✓ | |
| 多分类入侵检测 | ✓ | | ✓ | |
| 异常检测 | ✓ | | ✓ | |
| 类别不平衡处理 | ✓ | | ✓ | ✓ |
| 数据泄漏 / 诚实评估 | ✓ | | | |
| Cross-dataset 泛化 | ✓ | | | |
| LLM Agent 安全 | | ✓ | | |
| Prompt Injection 防御 | | ✓ | | |
| SIEM / SOC 工作流 | | | ✓ | |
| MITRE ATT&CK 映射 | | | ✓ | |
| 图学习 / GNN | | | ✓ | ✓ |
| 横向移动检测 | | | ✓ | |
| 金融犯罪 / AML | | | | ✓ |
| 可解释 AI（SHAP/GNNExplainer）| ✓ | | | ✓ |
| LLM 日志分析 | | ✓ | ✓ | |
| MLOps / drift / live demo | ✓ | | ✓ | |
| 对抗 ML（可选扩展） | ✓ | ✓ | | ✓ |

**最终目标**：展示「能把 ML/DL/LLM/GNN 放进真实 cyber defence 与金融风控流程」的工程能力，而非「模型 accuracy 很高」的 Kaggle 分数。

**统一签名（见 §三.0）**：四项目共享一条主线——**脏标签 / 选择性标注 / 分布漂移 / 投毒下的可信度**。这不只是「诚实评估」，是直接命中 AI Security / Model Risk 岗的 integrity / poisoning / provenance 关切，也让该岗位池升到与 cyber 并列第二。

核心叙事：
```
理解真实安全/金融犯罪场景
→ 选择适合的 ML/DL/LLM/GNN 方法
→ 构建完整检测/防御/合规 pipeline
→ 在脏标签 / 选择性标注 / 漂移 / 投毒下诚实评估可信度
  （utility、security、泛化、operating-point 脆弱性——报曲线不报单点）
→ 产出可解释、可部署、可分诊（Decision Card）的安全 AI 系统
```

---

## 附录：数据集核实状态（2026-06 核实）

| 数据集 | 核实结论 |
|---|---|
| Multi-Source Cybersecurity Logs 2026 (arXiv 2606.18190) | ✅ 论文真实，870 sessions / 2.3M events / 12 tactics·53 techniques，CC-BY；需定位数据下载位置 |
| OpenSOC-AI 2026 (arXiv 2604.26217) | ✅ 真实，adapter 权重 + 标注数据 + 评估 pipeline 已公开 |
| AgentDyn (arXiv 2602.03117) | ✅ 真实，官方实现 `SaFo-Lab/AgentDyn`（leolee99 为作者镜像） |
| CIC-YNU-IoTMal 2026 | ✅ 真实，UNB 页 + ScienceDirect 论文 + 开源 sandbox（`UNBCIC/CIC-YNU-IoTMal-Sandbox`） |
| Elliptic++ | ✅ 真实，`git-disl/EllipticPlusPlus`，822k 地址 + 200k 交易，GNN 参考 repo 丰富 |
| CIC 系列（CICIoT2023 等） | 🔒 真实但官方下载需填表；优先找 Kaggle 镜像 |
| DeepURLBench / PhreshPhish / MalURLBench / Smart-SIEM / LMDG | ⚠️ 论文存在，但落地前需各自确认数据/代码是否已公开可下载 |
| NetFlow 统一系列 / Loghub / LANL / EMBER / BODMAS / SOREL-20M / IEEE-CIS | ✅ 经典且确定可得，无需担心可获取性 |
