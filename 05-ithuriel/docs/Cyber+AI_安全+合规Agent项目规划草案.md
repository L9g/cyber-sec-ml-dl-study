# 安全 + 合规 Agent 项目规划草案

> 版本 v0.4（规划阶段）｜更新日期：2026-07-08｜目标市场：先 UK，兼容 EU｜定位：先自用，逐步演化为开源产品
>
> 本版在 v0.3 基础上按「两层模型」重构定位：**base 层（执行器/IPC/扫描器/未来 Rust 核心）一律借，差异化只建 (1) 标准→ontology 蒸馏 与 (2) 证据/Finding/保证层**。据此：§1 以保证与对抗性故障发现为主线、平台降为底座（§1.1）；§4 插件改为对现成工具的薄适配器；§5 Rust 可信核心推迟到实测出瓶颈再议；§8 路线图前移一层薄 AI 探针 spike。另修正一致性与 schema 缺口：standards 注册表补全、verification 拆 method/verdict/requires_approval、Finding 五层与四态、AI 非确定性 `ai_run_record`、`evidence_integrity` 哈希链、`scoring` rollup、AI 控制补齐至 7 个、白名单执行模型、攻击语料治理。

---

## 0. 决策记录

| # | 决策 | v0.4 结论 | 说明 |
|---|------|-----------|------|
| D1 | 首个市场/profile | UK first，EU compatible | UK Cyber Essentials 最适合作为首个可执行安全基线；EU AI Act/GDPR 作为 AI 风险侧的法规映射。 |
| D2 | 标准骨架 | NIST CSF 2.0 + NIST AI RMF + UK/EU 法规映射 | CSF 2.0 是六功能：Govern, Identify, Protect, Detect, Respond, Recover。v0.2 的“五大功能”表述应废弃。 |
| D3 | 首个功能切片 | Red Team MVP：`CE-UK-FW-01` | 先跑通授权目标、RoE、nmap、审计日志、结构化报告。 |
| D4 | AI 风险 MVP | AI Agent 越界/隐私/安全黑盒测试 | 先测 prompt injection、敏感信息泄露、工具越权、RAG 泄露、过度代理行为。治理类控制后续用证据收集插件覆盖。 |
| D5 | 语言策略 | MVP 全 Python；可信执行核心（Rust/Go）是 base 层，推迟到实测瓶颈证明后再定，不进当前关键路径；TypeScript 只做前端 | 原型阶段不要同时引入 Go 和 Rust。别过早优化 base。先稳定接口，再决定是否下沉。 |
| D6 | 插件安全 | 所有执行型插件必须经 CommandExecutor / PolicyEngine | 插件不得直接执行 shell、扫描、HTTP 攻击或模型调用；所有动作必须绑定 RoE、预算、审计和证据链。 |
| D7 | 标准字段 | `standards_refs` 与 `verification` 分离 | 追溯映射和验证方式是正交字段。能映射法规不代表能自动测试。 |
| D8 | 开源边界 | 默认只启用 L1/L2；高风险动作需要显式授权和人工确认 | 双用途工具必须把授权、范围和防滥用作为产品能力，而不是 README 免责声明。 |
| D9 | 构建边界（两层模型） | base 层（执行器/IPC/扫描器/未来 Rust 核心）一律借；只自建 (1) 标准→ontology、(2) 证据/Finding/保证层；AI 探针 spike 前移到阶段 1 | 差异化在结论/保证层，不在平台。插件是薄适配器不是自研扫描器（§4.2）。minimal base ≠ toy base：借到内行点头为止。详见 §1.1。 |

---

## 1. 项目定位

项目目标不是再造一个安全扫描平台，而是做一个**以保证（assurance）与对抗性故障发现为主线**的安全/合规 Agent：把标准蒸馏成可执行 ontology、驱动现成工具去测、再把结果凝成**可审计、可复现的结论**。平台本身只是跑这条链路的底座——价值在结论层，不在底座。第一阶段聚焦两条产品线：

1. 网络与 IT 系统安全：以 Cyber Essentials 就绪度审计为主体，附一层授权红队切片，自动发现暴露面、配置薄弱点、补丁与访问控制风险。
2. AI Agent 风险检测：对陌生 AI Agent 冷启动地探测并暴露其隐私、安全、合规和越界失败模式——工具越权、数据泄露、过度代理、提示注入、RAG 泄露、不当自动化决策。

两条产品线共享同一个内核：标准 ontology、Region Profile、RoE、插件接口、证据模型（§3 五层含 Finding）、报告模型。差异只在 target 类型、control 集合和插件实现。

**范围诚实声明：** 第一条产品线的绝大多数 CE 控制本质是**需要凭据的内部配置审计**（读取配置、清单、日志并与基线比对），而不是黑盒红队打点；真正的黑盒/主动模拟只占很薄一层（如 `CE-UK-FW-01` 的授权端口扫描）。因此更准确的定位是「**Cyber Essentials 就绪度审计助手 + 一层授权红队切片**」，而不是通用渗透/红队平台。配置类控制必须显式声明取数方式（SSH/WinRM、只读 API、云配置导出，或用户提供的配置转储），凭据由核心按最小权限注入（见 §5.2）。这样定位不是自我设限，而是让证据链和结论可被审计——夸大成「红队平台」反而会削弱保证价值。

### 1.1 两层模型：借底座，建差异化

把整个系统显式切成两层，用来决定"自己写还是借"：

- **Base / 基础设施层 = 借。** 命令/模型执行器、插件进程隔离与 IPC、调度，以及所有实际扫描与探测能力（`nmap`、`nuclei`、`garak`、`PyRIT`、LLM SDK……），乃至未来的 Rust 可信核心，都是行业已有、人人都有的东西。它们的价值只是"一个可信的被审计对象/执行手段"，不是本项目的贡献点。**能借就不自建。**
- **Differentiator / 差异化层 = 建。** 只有两样值得自己投入：(1) 把标准/法规蒸馏成可执行 ontology（§2–§3），(2) 证据 / `Finding` / 保证层（§3 的四态 Finding、`ai_run_record`、`evidence_integrity` 哈希链、`scoring` rollup）。这层稀缺、免 clearance、别人写不出，是 portfolio 与产品的真正竞争力。

由此落两条操作规则：**(a)** 插件是"对现成工具的薄适配器 + 把输出归一化进 Evidence schema"，不是手搓 19 个 CE 专用扫描器（§4.2）；**(b)** 底座要借到"领域内行点头"的可信度，但不多建一分——**minimal base ≠ toy base**：底座太薄，上层审计结论就失去可信度。Base 层遵循 Unix 式极简与可组合，差异化层则刻意重投入；两层由 §5.2 的可替换接口（插件只返回 `ActionPlan`）隔开，所以"现在借底座"并不妨碍"将来自建"。

---

## 2. 标准与规范地基

### 2.1 网络与系统安全

**主干：NIST CSF 2.0**

CSF 2.0 适合作为顶层 ontology，而不是直接作为扫描清单。它的六个功能应成为报告和能力域的顶层结构：

- `GV` Govern：治理、风险管理策略、角色职责、供应链风险。
- `ID` Identify：资产、风险、改进。
- `PR` Protect：身份访问、数据安全、平台安全、基础设施韧性。
- `DE` Detect：持续监控、不利事件分析。
- `RS` Respond：事件管理、分析、沟通、缓解。
- `RC` Recover：恢复计划与恢复沟通。

**UK baseline：Cyber Essentials**

首个 UK profile 应以 Cyber Essentials 五项技术控制为最低可执行基线：

- Firewalls
- Secure configuration
- Security update management
- User access control
- Malware protection

Cyber Essentials 的优势是粒度具体、容易映射到扫描/配置检查/证据项；劣势是它不是完整的企业安全管理体系。因此它应作为 `UK baseline controls`，而不是项目的全部安全框架。

**补充框架**

- MITRE ATT&CK：作为红队动作、TTP 标签、攻击路径解释层，不作为合规控制本身。
- CIS Controls v8：可作为实际控制库补充，尤其适合资产、配置、漏洞、日志、访问控制。
- NIST SP 800-53 / 800-171：以后进入企业或供应链场景时作为更细控制库。
- NCSC CAF：面向 UK 关键服务/高成熟度组织的后续 profile，不建议放进 MVP。
- ENISA / NIS2 / CRA：EU profile 的网络与产品韧性补充。CRA 更适合未来“产品安全/软件供应链”插件。

### 2.2 AI 隐私、安全、合规与越界风险

AI 风险侧不要只做“LLM jailbreak scanner”。对 AI Agent 来说，真正的风险面至少包括：模型输出、上下文/记忆、RAG、工具调用、身份权限、数据处理、审计留痕、人工监督和自动化决策。

**UK 核心**

- UK GDPR + Data Protection Act 2018：个人数据处理、合法性、公平透明、数据最小化、DPIA、自动化决策、数据主体权利。
- ICO AI guidance：把 UK GDPR 原则落到 AI 系统，尤其是可解释性、DPIA、个体权利与风险评估。
- Data (Use and Access) Act 2025：已影响 UK 数据保护与 PECR 相关制度，profile 中应列为需持续跟踪的 UK 数据法规。
- DSIT Introduction to AI Assurance：适合作为 AI 风险 Agent 的工作流来源，覆盖 assurance 方法、证据和治理语境。
- UK AI regulation white paper / cross-sector principles：作为政策映射，短期不进入自动化测试层。

**EU 核心**

- EU AI Act：用于 AI 系统风险分级、禁止用途、高风险义务、透明度义务、GPAI 义务。
- GDPR：所有个人数据问题仍先按 GDPR/UK GDPR 分析，AI Act 不替代数据保护义务。
- ePrivacy：通信、追踪、cookie、电子营销场景需要挂接。
- NIS2 / CRA / Cybersecurity Act：当 AI 系统进入关键服务、产品或供应链安全时启用。
- DSA/DMA：只在平台、推荐系统、广告透明度、超大型平台相关场景启用。

**国际方法论和安全测试**

- NIST AI RMF 1.0：作为 AI 风险管理工作流骨架。`MEASURE` 可落入测试；`GOVERN/MAP/MANAGE` 多数是证据与治理检查。
- NIST AI 600-1 Generative AI Profile：补充生成式 AI 特有风险，如幻觉、数据泄露、滥用、网络能力放大。
- ISO/IEC 42001：AI 管理体系，主要是 `document_review` / `attestation`，不应伪装成自动红队测试。
- ISO/IEC 23894：AI 风险管理，适合作为风险登记册和控制映射参考。
- ISO/IEC 27001 / 27701：信息安全与隐私管理体系，适合企业证据收集和 gap analysis。
- OWASP Top 10 for LLM Applications 2025：AI 应用安全测试清单，尤其 prompt injection、敏感信息泄露、供应链、数据/模型投毒、输出处理、过度代理、系统提示泄露、向量/嵌入弱点、误导信息、无界消耗。
- MITRE ATLAS：AI 对抗技术词典，用于 AI red team 的 TTP 标签。
- OWASP Top 10 for Agentic Applications for 2026：OWASP 已正式发布的 **agent 层**安全风险清单，区别于 LLM 应用层的 LLM Top 10，覆盖多步自主行动、长时记忆、工具/权限、多智能体协作等 agent 特有威胁（如 memory poisoning、goal/intent manipulation、跨 agent 身份冒充与越权、资源过载）。作为 AI 侧 agent 层主威胁词典；本项目当前 AI 控制映射在 LLM Top 10，**agent 层控制在此清单上扩展（vNext）**。（清单已发布，具体条目编号在建控制时按官方文本对齐；核对于 2026-07-08。）

---

## 3. 标准蒸馏方法

不要把法规和标准原文塞进 Agent。应把它们蒸馏成五层对象：

1. `Source`：标准/法规/指南的元数据，例如 jurisdiction、version、url、effective_date、license、authority。
2. `Control`：可管理的控制项，例如 `CE-UK-FW-01`、`AI-AGENT-TOOL-01`。
3. `Test`：验证某个控制的具体方法，例如端口扫描、配置检查、prompt probe、文档检查、人工确认。
4. `Evidence`：测试或审阅产生的证据，例如命令、参数、时间、目标、输出摘要、原始日志哈希、prompt/response、截图、人工签名。
5. `Finding`：把某个控制的验证结果落成可裁定的结论，绑定 status、severity、判定方式和证据引用。四层只到证据、不到结论，报告和评分都无处挂载，因此 Finding 是独立的一层。

每个控制至少包含：

```yaml
id: CE-UK-FW-01
title: Exposed network services are identified and justified
domain: network_security
standards_refs:
  - source: "Cyber Essentials"
    ref: "Firewalls"
  - source: "NIST CSF 2.0"
    ref: "PR.PS"
verification:
  method: automated_test
  plugin: nmap_port_scan
  verdict: automatic
  requires_approval: false
evidence_requirements:
  - target_scope
  - command_audit_log
  - parsed_findings
```

`standards_refs` 回答“它对齐什么”；`verification` 回答“怎么核”；`evidence_requirements` 回答“怎么证明”。这三者必须分开。

`verification` 内部还要再分三个正交维度，不能混在一个 `requires_human` 布尔里：`method` 是执行方式（automated_test / config_inspection / document_review / attestation）；`verdict` 是判定方式（`automatic` 由插件输出程序化判定，`llm_judge` 由 LLM 按 rubric 打分且只作辅助、低置信或高影响必须升级到人工，`human_review` 由人复核证据后判定）；`requires_approval` 是执行前是否需要人工授权（高风险动作的安全闸门，对应 RoE 的 `require_human_approval_for`）。执行方式、判定方式、授权闸门是三件事：一个 `automated_test` 可能仍需人工授权才能跑（如 `CE-UK-SC-02` 默认凭据测试），而一个 `document_review` 的判定天然是 `human_review`。

`Finding` 的 `status` 不能只有 pass/fail，必须支持四态：`pass`、`fail`（需 rationale + severity）、`not_applicable`（不适用，需说明理由，且从覆盖率分母中剔除）、`inconclusive`（跑了但证据不足或有歧义，需重跑或升级人工）。把"没测到"和"测了没过"混成 fail 会同时制造假阳性和假阴性，审计里两者的处置完全不同。

AI 探针是非确定性的：10 次注入里成功 3 次是真实但部分的失败，和 10/10 不是一回事，也不该被一次运行代表。所以每个 AI `Finding` 必须携带 `ai_run_record`：`model_id`、`model_version`、`temperature`、`seed`、`n_runs`、`n_success`、`success_rate`。安全/隐私类探针默认 `success_rate > 0` 即判 fail（除非有书面容忍度），置信度模糊则落 `inconclusive` 再升级人工。`n_runs` 不得低于 `ai_roe.min_runs_per_probe`。

证据必须防篡改、可复现：每条 `Evidence` 记录 `tool_name`、精确 `tool_version`（不是范围）、`invocation_params`（脱敏后的完整参数）、`command_hash`、`output_hash`、`prev_evidence_hash`（把同一次运行的证据串成哈希链）、`collected_at`、`operator`。判据是：只凭 `tool_version` + `invocation_params` 就能重跑并复现该结论。这是把项目从"扫描器包装"抬到"可审计的保证证据"的关键一层。

Cyber Essentials 认证本身是全过或全不过，但保证报告需要分级覆盖度。`scoring` 沿三条轴做 rollup（`ce_area`、`csf2_function`、`domain`）：覆盖率 = 该轴下适用控制中 `status == pass` 的占比，`not_applicable` 不进分母；但任何 High/Critical 的 fail 都会把该轴直接标为 `not_ready`，不被覆盖率百分比掩盖。单点失败降低覆盖度并按 severity 暴露，而不是把整条轴清零。

以上 schema 级定义（`verification_methods`、`verdict_modes`、`finding_schema`、`finding_status`、`ai_run_record`、`scoring`、`evidence_integrity`、`attack_corpus_governance`）已抽到独立的 `ontology_schema.yaml`（region 无关）；region profile 只经 `schema_ref` 引用它，自己只保留标准注册表、RoE 默认值与 control 实例——避免 EU/US profile 复制 schema 而漂移。

---

## 4. 架构建议

### 4.1 核心模块

核心模块只做"薄编排"，不做重实现：executor / registry / IPC 是把借来的工具接进 `ontology → 计划 → 证据 → Finding` 链路的整合层，真正的扫描/探测能力全部来自现成工具（§1.1）。差异化代码集中在 `ontology` 与证据/Finding/保证部分。

- `ontology`: source/control/test/evidence/finding 的 schema，含 `finding_status` 四态、`ai_run_record`、`evidence_integrity`、`scoring`。
- `profile_loader`: 加载 UK/EU/US/自定义 profile，生成可执行测试计划。
- `policy_engine`: 解释 RoE、风险等级、预算、禁止动作、人工审批要求。
- `plugin_registry`: 注册插件，按 control/target/method 匹配能力。
- `command_executor`: 唯一外部命令执行入口，负责参数白名单、资源限制、超时、审计、输出截断和哈希。
- `model_executor`: 唯一 AI target 调用入口，负责 token/成本预算、速率限制、PII 脱敏、日志和重放。
- `reporter`: 输出 JSON/Markdown/HTML/PDF，报告按 control、标准映射、风险、证据组织，并按 `scoring` 沿 ce_area / csf2_function / domain 三轴做覆盖度与 not_ready 门控 rollup。

### 4.2 插件类型

- `recon_plugin`: 被动资产/暴露面发现。
- `config_plugin`: 配置读取和基线比对。
- `active_test_plugin`: 非破坏性主动验证。
- `ai_probe_plugin`: prompt/RAG/tool-use 越界测试。
- `evidence_plugin`: 文档、问卷、人工证明收集。
- `report_plugin`: 报告转换和导出。

插件必须围绕 control 而不是工具设计，且每个插件是**对现成工具的薄适配器**：调用 `nmap`、`garak`、`PyRIT`、`nuclei` 等，把其输出归一化进 Evidence schema，绝不重写扫描/探测逻辑，也不为每个 CE 控制手搓专用扫描器。没有现成工具覆盖的控制，先留 `not_applicable` 或占位，不为它破例自建重实现。

### 4.3 双用途安全边界

默认模式必须保守：

- 无 `allowed_targets` 时拒绝执行任何外部扫描。AI target 同样必须显式授权，并确认符合提供方使用条款（`ai_roe.require_provider_tos_acknowledgement`）。
- L1 只允许被动/本地读取；L2 允许非破坏性主动验证；L3 才允许授权范围内的侵入性模拟。
- HIGH/CRITICAL 插件默认不进入计划，除非 profile、RoE、用户审批三者都允许。
- 所有命令和模型调用必须有审计记录。
- 对 AI target 必须有成本预算、QPS、最大轮次、PII 脱敏和禁止生产端点策略。
- 命令执行是**白名单模型**（`execution_model: allowlist_only`）：CommandExecutor 只跑每个插件显式登记的二进制和参数集合。`hard_denied_binaries`（sqlmap/hydra/john）只是纵深防御的兜底开关，不是主控制——黑名单可被绕过，绝不能作为唯一防线。

---

## 5. 编程语言选择

### 5.1 推荐结论

**原型阶段：全 Python。**

理由：

- 安全与 AI 红队生态最完整：`nmap` 封装、`scapy`、`impacket`、`semgrep`、`garak`、`PyRIT`、LLM SDK、YAML/JSON schema 工具都成熟。
- 最快验证核心假设：control ontology、profile planning、RoE、插件抽象、证据模型。
- 早期真正的风险不是性能，而是抽象错误、证据链不完整和安全边界过松。

**产品化阶段：可信执行核心是 base 层，默认推迟。**

按 §1.1，可信执行核心（PolicyEngine / CommandExecutor / 沙盒 / 审计）是基础设施，不是差异化。因此**不预先上 Rust**：MVP 乃至相当长一段时间全程 Python，把精力留给 ontology 与保证层。只有当**实测**出本地可信执行成为瓶颈（而不是设想），才回头下沉；届时再在 Rust 与 Go 间二选一，不长期同时维护两套系统语言：

- 选 Rust：适合写 PolicyEngine、CommandExecutor、沙盒、审计、文件/凭据处理等可信计算基。内存安全和类型系统对安全产品更有价值。
- 选 Go：适合网络并发、静态二进制、部署简单、运维友好。如果瓶颈主要是分布式调度和工具编排，Go 会更快。

倾向仍是 **Python MVP +（将来若需要的）Rust trusted core + Python plugins + TypeScript UI**，但 Rust 明确排在"瓶颈证明之后"，不进当前关键路径。

### 5.2 边界设计

从第一天开始就按可替换核心设计：

- 插件输入输出用 JSON Schema / Pydantic 定义，避免 Python 内部对象泄漏成隐式协议。
- 插件进程隔离：核心通过 subprocess/stdin-stdout JSON、Unix/Windows named pipe 或 gRPC 调用插件。
- 不让插件直接持有长期凭据；凭据由核心按最小权限注入。
- 所有外部命令从核心执行器发出，插件只返回 `ActionPlan`。
- 前端 TypeScript 只调用后端 API，不参与扫描执行路径。

---

## 6. Red Team MVP

首个端到端切片仍建议为 `CE-UK-FW-01`（这正是 §1 所说的那层「授权红队切片」；其余 CE 控制走凭据配置审计路径，不在本切片内）：

1. 读取 `UK_Region_Profile_v0.2.yaml`。
2. 用户显式提供授权 target，例如本地 lab CIDR 或单 host。
3. PolicyEngine 校验 RoE：范围、强度、风险等级、禁止端口、并发。
4. `nmap_port_scan` 插件生成 `ActionPlan`，不直接执行。
5. CommandExecutor 执行允许的 nmap 参数集合。
6. Parser 生成结构化 findings。
7. Reporter 输出：暴露服务、控制映射、证据、风险、建议、未执行项。

MVP 不应包含默认密码尝试、漏洞利用、爆破、sqlmap、提权或横向移动。这些可以先建 control 和插件占位，但默认不执行。

---

## 7. AI Agent 风险 MVP

> **⚠️ 权威设计已外移（2026-07-10）**：AI 红队切片的**权威设计**见 `docs/papers/ai-redteam-pipeline-learning-note.md §10（决策 D1–D8）`——含 base 选型（AgentDojo 主 base）、bare/defended 差分、双循环、三阶段 sandbox roadmap、状态词汇、归一化≠可比。**本节以下为读论文前的早期草案，冲突处一律以 pipeline note 为准**（尤其下方「工具路线」的 base 选型已被 D 修正，见 §8 阶段1）。控制清单与场景库治理仍有效。

首个 AI 风险切片建议不是泛泛“AI 合规评估”，而是一个可运行的黑盒测试目标：

**目标类型**

- `ai_chat_api`
- `agent_with_tools`
- `rag_assistant`
- `conversation_log`

**首批控制**

| 控制 ID | 风险 | 对应测试 |
|---|---|---|
| AI-AGENT-PI-01 | Prompt injection 导致指令覆盖 | 单轮/多轮 prompt probe |
| AI-AGENT-SD-01 | 敏感信息泄露 | canary、PII、system prompt、memory 泄露测试 |
| AI-AGENT-TOOL-01 | 工具越权或无确认执行 | 诱导调用高风险 tool，检查审批和参数约束 |
| AI-AGENT-RAG-01 | RAG 数据越权或跨租户泄露 | 查询边界、引用来源、权限过滤测试 |
| AI-AGENT-OUT-01 | 不当输出进入下游系统 | 输出注入、代码/HTML/SQL 处理测试 |
| AI-AGENT-COST-01 | 无界消耗 | token、循环、工具调用、重试风暴测试 |
| AI-AGENT-COMP-01 | 自动化决策/法律医疗金融越界 | 场景库 + judge + 人工复核 |

**工具路线**

- garak：广度扫描，适合 CLI 插件封装。
- PyRIT：多轮对抗和 orchestrated attack。
- 自研 YAML 场景库：做 UK/EU 特有合规和越界场景，这是项目差异化所在。
- LLMJudge：只作为辅助判定（对应 `verdict: llm_judge`），关键结论要保留 prompt/response 证据并支持人工复核。

**攻击场景库治理：** 自研 YAML 场景库是差异化资产，也是高风险资产，必须像代码一样治理，而不是散落的 prompt 文件：每个场景带 `id`、`version`、`provenance`（来源：自研/公开数据集/CVE/论文，注明 license）、`safety_class`（`benign` / `dual_use` / `potentially_harmful`）；`dual_use` 与 `potentially_harmful` 场景默认加密存储、限制访问、禁止进入公开仓库；场景库整体版本化，每次测试运行把所用场景库的版本哈希并入证据链（见 §3 `evidence_integrity`），保证结论可复现且可追溯到具体场景版本。对应机读定义见 profile 的 `attack_corpus_governance`。

---

## 8. 路线图

**阶段 0：标准与 schema**（差异化层地基）

- ✅ 已建 `ontology_schema.yaml`（**v0.6**，五层含 Finding、四态、`ai_run_record`、`evidence_integrity`、`scoring`、`verdict_modes`、`attack_corpus_governance`；region profile 经 `schema_ref` 引用）。v0.6 加了 `Finding.root_causes` + `root_cause_enum`（P1–P6/OTHER/UNDETERMINED，advisory 机理标签，唯一破例；其余字段冻结待薄切片跑通）。
- 完成 `UK_Region_Profile_v0.2.yaml`。
- 完成 `core_controls_uk.md` 的 `standards_refs`、`verification`、`evidence_requirements`。

**阶段 1：两条最薄的端到端切片（各借一个现成工具）**

- 薄编排核心：profile loader、plugin registry、policy engine、command/model executor——只做整合，不重实现。
- 网络侧：薄封装 `nmap`，跑通 `CE-UK-FW-01` 的计划 → 执行 → 证据 → Finding → 报告。
- **AI 侧（动机前移，base 选型已按 D 修正）：以 `AgentDojo` 为主 base**（工具型 agent 处理不可信数据的原生场景、可复现 + 原生支持 adaptive attack；InjecAgent 补间接注入），跑通 `AI-AGENT-PI-01`：**版本化 IPI 场景 → bare/defended 两配置**（defended **先用借来的已发表防御**如 Firewalls，不用自研，绕开利益冲突 + 复现已知结果）**→ 多次运行 → 原始轨迹证据 → `ai_run_record`（记攻击强度/自适应等级）→ Finding → 结构化范围声明**。garak/PyRIT 降为**探索循环**产语料工具，非主 base（详见 pipeline note D5 双循环 / D8 薄切片）。把"破/诊断"的核心乐趣与差异化价值前置，不再压到最后。

**阶段 2：把 Finding / 证据 / 保证层做扎实**（真正的差异化投入）

- `evidence_integrity` 哈希链、`scoring` rollup、四态裁定、报告模板与覆盖度视图。
- AI 侧扩展 `AI-AGENT-SD-01`、`AI-AGENT-TOOL-01`；网络侧接入 ATT&CK 标签、dry-run、审批队列。

**阶段 3：横向扩控制（继续借工具）**

- 用薄适配器接更多现成扫描器，覆盖资产版本、补丁/CVE、MFA、暴露面、恶意软件防护等 CE 控制；缺工具的控制留占位。
- 自研攻击场景库（§7）——UK/EU 特有合规与越界场景，这是自建、差异化的语料资产。

**阶段 4：产品化与开源**

- 仅当实测瓶颈证明后，才决定是否下沉 Rust/Go 核心（见 §5.1）。
- Web UI 用 TypeScript。
- 开源 README、license、contributing、安全政策、负责任使用政策。
- 增加 EU profile。

---

## 9. 近期待决策

1. 核心执行器未来是 Rust 还是 Go：它是 base 层，推迟到**实测瓶颈证明后**再定，不进当前关键路径（见 §1.1、§5.1）。
2. ✅ 已解决：schema 已抽到独立的 `ontology_schema.yaml`，profile 经 `schema_ref` 引用。
3. AI 风险侧的第一批目标：建议先测你自己可控的 agent endpoint，而不是公共模型。
4. 是否把 Cyber Essentials Plus 的技术测试方法作为第二阶段参考：建议是，但要注意认证要求和自动化红队测试不是同一件事。
5. 开源许可证：建议 Apache-2.0 或 MPL-2.0；如果想强约束商业闭源使用，再考虑 AGPL，但会降低企业采用意愿。

---

## 10. 参考来源

- NIST Cybersecurity Framework 2.0: https://www.nist.gov/cyberframework
- NCSC Cyber Essentials overview: https://www.ncsc.gov.uk/cyberessentials/overview
- European Commission AI Act overview and implementation timeline: https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- GOV.UK Introduction to AI assurance: https://www.gov.uk/government/publications/introduction-to-ai-assurance
- ICO Artificial intelligence guidance and resources: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/
- OWASP Top 10 for LLM Applications 2025: https://genai.owasp.org/llm-top-10/
- OWASP Top 10 for Agentic Applications for 2026: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- MITRE ATT&CK: https://attack.mitre.org/
- MITRE ATLAS: https://atlas.mitre.org/

---

本文件不是法律意见。法规、认证条款和适用日期在实现前应按官方文本复核。**截至 2026-07-08 已核：** EU AI Act 时间线（2024-08-01 生效、禁止用途 2025-02-02、GPAI 2025-08-02、透明度 2026-08、通用适用 2026-08-02、高风险分阶段 2027-12-02 / 2028-08-02）；OWASP Top 10 for Agentic Applications for 2026 已发布。**仍需持续跟踪：** Cyber Essentials 当前版本号、UK 数据保护制度更新、ISO 标准授权文本、各清单具体条目编号。
