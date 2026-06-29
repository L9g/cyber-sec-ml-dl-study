# Data Science / ML / DL × Cyber Security — 学习与项目实施计划

> 目标：在英国求职 Cyber Security + ML/DL/Data Science 相关岗位，通过 portfolio 项目积累实战经验。
>
> 版本说明（v2.1）：在 v2 基础上做了两处结构性改进——(1) 项目组合补齐了「金融犯罪/AML 图学习」和「对抗 ML」两个英国高需求但原先空缺的方向；(2) 数据集库从「偏最新但部分 gated」调整为「最新 + 经典确定可得」并行，并标注了真实性/可获取性核实状态。

---

## 一、英国目标岗位市场分析

### 1.1 典型岗位名称

| 岗位名称 | 侧重方向 | 本计划覆盖项目 |
|---|---|---|
| AI Security Architect | AI 系统安全设计与评估 | 项目二 |
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

英国雇主（尤其金融、关键基础设施、公共部门）在技术能力之外，普遍看重**数据治理、合规与可审计性**。把这些挂进 portfolio 叙事，比纯刷分更能打动 hiring manager：

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
> **重要原则**：portfolio 优先选「招聘方认得 + 拿得到 + 有参考 notebook」的数据集，其次才追最新。落地前务必确认「论文存在 + 数据可下载 + 许可允许」三件事。

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

### 项目一：诚实评估的网络入侵检测（NIDS）

**目标岗位**：ML Cyber Security Engineer、Network Security Data Scientist

**核心叙事**：这个领域 portfolio 高度饱和，单纯刷 CICIoT2023 到 99% 没有差异化。本项目的卖点不是分类器本身，而是**揭穿并避免 benchmark 虚高**——数据泄漏、随机切分过于乐观、跨环境泛化崩塌，这正是资深从业者最常吐槽的痛点。

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

#### 子模块：Graph Lateral Movement Detection
- 用 LANL 认证日志构建「用户-主机认证图」，做异常路径 / 社区 / GNN 节点分类检测横向移动。
- 评价：恶意认证边/路径的 precision/recall；与规则基线对比。

#### 加分：LLM 解释层
- 用 OpenSOC-AI（TinyLlama+LoRA）风格对告警生成自然语言解释，**仅辅助 analyst，不替代检测**。
- ⚠️ 评估陷阱：严格 regex parser 会把 LLM 评成 0%，需用 fuzzy parser（见 [arXiv:2605.07293](https://arxiv.org/abs/2605.07293)）。

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

#### 背景与问题

```
问题：在比特币交易网络中识别非法（洗钱）交易/地址。
数据：图结构——节点=交易/钱包地址，边=资金流向，部分节点有 illicit/licit 标签。
难点：极度不平衡、大量未标注节点（半监督）、时间演化、可解释性要求高（合规）。
```

#### 实施步骤

1. **EDA + 图理解**：节点/边规模、标签分布、时间步（Elliptic 含 49 个时间步）、illicit 占比。
2. **Temporal split（合规关键，避免未来信息泄漏）**：按时间步切分（如前 34 步训练、后 15 步测试），**绝不**用未来交易预测过去；明确说明 **transductive（测试节点在训练时已可见）vs inductive（测试节点完全未见）** 两种设定的差异和各自结论——这是 AML 模型最常被审计质疑的点。
3. **表格 baseline**：只用节点特征跑 LightGBM/XGBoost，建立非图基线（也是本项目的 **MVP 档**，无需 GNN 即可交付）。
4. **图模型**：GCN / GraphSAGE / GAT；对比「加了图结构」相比表格 baseline 的提升。
5. **时序图**：EvolveGCN 等，利用时间步演化。
6. **不平衡 + 半监督**：focal loss / 重采样；利用大量未标注节点。
7. **可解释性**：GNNExplainer / 子图重要性——向反洗钱合规团队解释「为什么这笔交易可疑」。

#### 评价指标（按真实 AML 工作方式，而非单纯 GNN F1）
- **precision@k / recall@k**：AML 团队按调查容量处理 top alerts，整体 F1 不如「前 k 个告警里有多少真命中」有意义。
- **Human review budget**：设定「每天只能调查 top 100 alerts」的约束，报告在该预算下的命中率与漏报——直接对应合规团队的实际产能。
- **illicit 类 precision/recall/F1、PR-AUC**：强调 recall（漏报洗钱代价高）。
- **False positive case study**：挑几个「模型判可疑但可能合法」的案例，解释为什么会误判、analyst 该如何复核——这比任何分数都更像真实金融犯罪检测工作。

#### 参考资源

| 资源 | 说明 |
|---|---|
| [Elliptic++ repo](https://github.com/git-disl/EllipticPlusPlus) | 数据 + 基线 |
| [Elliptic 原始论文 (Weber 2019)](https://arxiv.org/abs/1908.02591) | AML + GCN 奠基工作 |
| [EvolveGCN](https://github.com/IBM/EvolveGCN) | 时序图节点分类 |

#### 项目推荐标题

```
Graph-Based Anti-Money-Laundering: Detecting Illicit Bitcoin
Transactions with GNNs and Explainable Subgraphs
```

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
| **Portfolio-ready** | 4-6 周 | 可复现实验、错误/失败案例分析、评估指标完整、一个 demo | 加 data_card、model_card、threat_model、Makefile |
| **Research-grade** | +若干周 | drift 监控、GNN/时序图、LLM、在线部署 | 加 Dockerfile、CI、checksum；原始大数据不入库，只留下载说明 |

各项目的 MVP 锚点（确保 2-3 周能出货）：
- 项目一 MVP：随机切分 LightGBM baseline + 「乐观 vs 诚实」对比表。
- 项目二 MVP：AgentDojo 无防御 + tool filter 两组,出 utility/attack-success 对比。
- 项目三 MVP：Mordor/EVTX 上 Sigma 规则 + LightGBM 分类,出 ATT&CK 映射。
- 项目四 MVP：**纯表格 LightGBM**(不碰 GNN),建立 AML 非图基线——因此项目四可安全提前到 Phase 2-3,不会被图学习卡住。

> 注：完整的「统一仓库质量标准」（每个 repo 必备文件清单、按档位递增的门槛）见**第六章**。

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

| 文件 / 实践 | MVP | Portfolio-ready | Research-grade | 作用 |
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

> 这一章不必在写计划时就全部落地——它是每个项目**升到 Portfolio-ready 档时的 checklist**，按需勾选即可。

---

## 七、作品集（Portfolio）结构

```
cyber-ml-portfolio/
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

**项目四（AML 图学习）**
```
Developed an explainable graph-based anti-money-laundering model on the Elliptic++
Bitcoin dataset, benchmarking GNNs (GraphSAGE, EvolveGCN) against tabular baselines
under extreme class imbalance, with GNNExplainer subgraphs for compliance review.
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

核心叙事：
```
理解真实安全/金融犯罪场景
→ 选择适合的 ML/DL/LLM/GNN 方法
→ 构建完整检测/防御/合规 pipeline
→ 诚实评估 utility、security、false positive、泛化与 operational trade-off
→ 产出可解释、可部署的安全 AI 系统
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
