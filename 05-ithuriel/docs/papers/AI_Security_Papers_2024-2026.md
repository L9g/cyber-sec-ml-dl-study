# AI Security 论文分类阅读列表

> 面向具备工具调用、MCP/skills、外部内容处理和安全分析能力的 AI Agent。优先级：**P0** 为架构前必读，**P1** 为实现/评测阶段必读，**P2** 为按功能选读。预印本尚未完成同行评审。

## 1. Agent 安全基础与总体威胁模型

### P0

- **[Security of AI Agents](https://arxiv.org/abs/2406.08689)**（2024，预印本）  
  记忆、规划、工具、感知、多 Agent 协作的攻击面全景。用于产出 Ithuriel 的风险登记册和设计评审清单。

- **[NIST: Adversarial Machine Learning—A Taxonomy and Terminology of Attacks and Mitigations](https://doi.org/10.6028/NIST.AI.100-2e2025)**（2025）  
  用统一术语界定 evasion、poisoning、privacy、misuse 和 supply-chain 风险，并分配控制责任。

## 2. 提示注入与不可信外部内容

### P0

- **[AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352)**（2024，预印本）  
  工具型 Agent 的动态提示注入测试环境。用于建立高权限工具调用的安全回归测试。

- **[How Vulnerable Are AI Agents to Indirect Prompt Injections? Insights from a Large-Scale Public Competition](https://arxiv.org/abs/2603.15714)**（2026，预印本）  
  说明攻击可在最终回复正常的情况下成功执行；评测须记录 tool call、数据流和副作用，而不能仅检查输出文本。

### P1

- **[AI Agents May Always Fall for Prompt Injections](https://arxiv.org/abs/2605.17634)**（2026，预印本）  
  解释为什么纯粹依赖“数据—指令分隔”的防御不足。高风险操作应由确定性权限检查、来源标记和用户确认把关。

## 3. MCP、Tools、Skills 与供应链安全

### P0

- **[TRUSTDESC: Preventing Tool Poisoning in LLM Applications via Trusted Description Generation](https://arxiv.org/abs/2604.07536)**（2026，预印本）  
  将工具描述视作不可信供应链输入。用于设计 MCP/tool/skill 的来源信任、审查、规范化和最小暴露策略。

### P1

- **[From Component Manipulation to System Compromise: Understanding and Detecting Malicious MCP Servers](https://arxiv.org/abs/2604.01905)**（2026，预印本）  
  研究恶意 MCP 组件如何从局部操纵扩大到系统妥协；适合补全第三方 server 的接入审核要求。

- **[SkillAttack: Automated Red Teaming of Agent Skills through Attack Path Refinement](https://arxiv.org/abs/2604.04989)**（2026，预印本）  
  适合为 Ithuriel 的 skills 建立自动化攻击路径测试与发布前验证。

## 4. 长期记忆、资源控制与运行时边界

### P0

- **[Autonomy Comes with Costs: Detecting Denial-of-Service Vulnerabilities Caused by Resource Abusing in LLM-based Agents](https://www.usenix.org/conference/usenixsecurity26/presentation/luo)**（USENIX Security 2026，预发表）  
  关注循环、子 Agent、浏览器/沙箱等资源生命周期导致的 DoS。实现 token、递归、并发、执行时间和外部请求的硬预算与熔断。

### P1

- **[A-MemGuard: A Proactive Defense Framework for LLM-Based Agent Memory](https://openreview.net/forum?id=udqe7UZUZ6&noteId=FebXAZI65c)**（ICML 2026）  
  解决条件触发的 memory poisoning。记忆需保存来源、TTL 与作用域，并可审计、撤销，且不自动拥有指令权或权限提升。

## 5. AI 辅助防守与 SOC 能力边界

### P1

- **[Cyber Defense Benchmark: Agentic Threat Hunting Evaluation for LLMs in SecOps](https://arxiv.org/abs/2604.19533)**（2026，预印本）  
  在无引导 Windows 日志中做威胁狩猎，显示当前模型在开放式证据推理上的局限。Ithuriel 应定位为可审计的人机协作，而非无监督自动处置。

- **[Cloak, Honey, Trap: Proactive Defenses Against LLM Agents](https://www.usenix.org/conference/usenixsecurity25/presentation/ayzenshteyn)**（USENIX Security 2025）  
  从蜜标、欺骗和陷阱角度抵御恶意 Agent。仅在实验或授权蜜罐环境中用于主动防御研究。

## 6. 模型选择、发布前评测与治理

### P1

- **[CYBERSECEVAL 3: Advancing the Evaluation of Cybersecurity Risks and Capabilities in Large Language Models](https://arxiv.org/abs/2408.01605)**（2024，预印本）  
  建立模型能力、第三方风险和缓解措施前后差异的评测语言。每次模型或 Agent 更新都应保存模型、prompt、权限、工具和缓解策略的组合结果。

## 最小必读路径

1. *Security of AI Agents*
2. *AgentDojo*
3. 2026 Prompt-Injection Public Competition
4. *TRUSTDESC*
5. *AgentDoS*
6. *Cyber Defense Benchmark*
7. NIST AML Taxonomy

## 配套开源项目

- [NIST CAISI Cyber Evals](https://github.com/usnistgov/caisi-cyber-evals)：CyBench/CVE-Bench 的容器化评测环境。
- [Snyk Agent Scan](https://github.com/snyk/agent-scan)：扫描 Agent、MCP server 和 skills 的注入与工具投毒风险；扫描不可信 MCP 配置应在隔离环境中进行。
- [Tencent AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard)：覆盖 Agent、skills、MCP、基础设施和 jailbreak evaluation 的 AI 红队平台。

---

## Ithuriel 路线图采用建议（2026-07-23）

> 本节记录基于当前项目状态的阶段性建议，供后续讨论；它不是已批准的实施计划。上文 P0/P1 表示阅读优先级，不直接等同于开发优先级。

### 总体判断

不把论文和开源项目逐项转成内部模块。Ithuriel 继续坚持“执行与扫描能力借用，Evidence/Finding/Claim 与保证边界自建”。近期真正值得进入路线图的是三条能力线：

1. MCP/tool/skill 组件供应链接入保证；
2. Agent 运行时资源滥用保证；
3. 模型、prompt、权限、工具和防御更新后的发布资格判定。

当前 calendar probe 的 corrected C2 已通过，但 instrument qualification、ADR-0020 C1/C3/C4、独立外部操作员检验和 mock 之外的环境保真度仍未完成；runner 中的信任核逻辑拆分也仍是开放项。因此，在这些门槛关闭前不扩建新的通用评测平台。

### 论文采用决策

| 方向 | 采用方式 | 路线图位置 |
|---|---|---|
| 2026 Prompt-Injection Public Competition、*AI Agents May Always Fall for Prompt Injections* | 吸收到测量方法：最终回复不能代表执行安全；继续保存 tool call、tool result、副作用和 state；高风险动作依靠确定性 PEP、来源和授权，不依赖纯文本分隔 | 立即采用，不另建模块 |
| *AgentDojo* | 继续作为间接注入确认层的 borrowed base；用独立 holdout、正负对照和攻击强度治理防止基准饱和被误读为安全 | 已采用，继续加固 |
| *TRUSTDESC*、恶意 MCP Server、*SkillAttack* | 共同构成“组件接入保证”的威胁与测量基础：描述来源、实现—描述偏差、多组件攻击链、良性 skill 的可利用漏洞 | 当前里程碑后的第一条新纵切片 |
| *AgentDoS* | 作为所有新执行后端的横切不变量；记录并强制 token、tool call、wall clock、递归、子进程、并发、网络出站和费用预算 | 现在冻结约束；真实多工具/子 Agent runtime 出现后形成独立切片 |
| *CYBERSECEVAL 3* | 借鉴风险分类和“有/无缓解”的版本化比较语言，不把完整 offensive benchmark 当作近期产品主线 | 最小发布回归门近期采用，广泛 benchmark 长期接入 |
| *A-MemGuard* | 借鉴 memory provenance、TTL、scope、撤销和条件触发投毒测试 | 仅在真实持久记忆后触发 |
| *Security of AI Agents*、NIST AML Taxonomy | 用于风险登记册、术语和控制责任 crosswalk | 阅读/治理输入，不据此扩建框架 |
| Cyber Defense Benchmark | 用于校准产品边界：开放式证据推理仍需可审计的人机协作 | 阅读参考，不建设自动化 SOC |
| *Cloak, Honey, Trap* | 仅用于授权实验环境中的主动防御研究 | 可选研究项，不进生产主线 |

### 建议新增的第一条纵切片

暂定名：`Agent Component Intake Assurance`。

实施顺序：

1. 先支持纯静态 skill 扫描，不执行任何第三方组件；
2. 再支持 MCP 配置扫描，但任何 server 启动或命令执行必须进入一次性沙箱，并经过 Action 哈希批准、RoE 和两阶段 PEP；
3. borrowed scanner 只产生 RawArtifact/Observation，Ithuriel 独立产生 Finding 和范围声明。

最小证据要求：

- 被测组件内容哈希、来源、声明能力和实际暴露能力；
- scanner、规则库、模型和 adapter 版本；
- 是否执行组件、执行的命令、权限、网络出站和数据去向；
- 原始扫描 artifact，以及从 artifact 到 Observation/Finding 的规则版本；
- 恶意、良性和独立 holdout fixtures；
- 未覆盖项、`inconclusive` 和 coverage gap，不产生单一 overall safety score。

最低验收条件：恶意 fixture 能触发预期 Finding，良性负对照不过度告警，未授权组件不会因“扫描”而被执行，且 scanner 结论与 Ithuriel 的保证裁定严格分层。

### 开源项目取舍

#### Snyk Agent Scan：首选薄适配器候选

- 优点：范围集中在 Agent、MCP server 和 skills，适合最小纵切片。
- 边界：官方说明 CLI 输出仍可能变化，产品 schema 不得绑定其当前字段；adapter 必须保存原始输出、工具版本并允许版本化解析。
- 风险：扫描 MCP 配置可能启动其中定义的命令；不得直接对不可信配置运行，必须经过沙箱和 Ithuriel 批准链。
- 其他约束：涉及 Snyk token/API 的模式需记录数据出站和第三方处理边界。

#### Tencent AI-Infra-Guard：对照后端，不作为核心平台依赖

- 可借鉴其 MCP/skill 风险分类、fixture、规则覆盖和独立 `aig-skill-scan`。
- 整体平台覆盖 Agent、MCP、skill、AI 基础设施、CVE 和 jailbreak，超出当前薄切片范围。
- 官方 README 说明平台当前缺少身份认证，不应暴露到公网；生产评估不得采用 `curl | bash` 一键安装路径，应使用钉死版本和摘要的隔离构建。
- 适合与 Snyk 在同一组冻结 fixtures 上做第二意见比较，而不是嵌入 Ithuriel 核心。

#### NIST CAISI Cyber Evals：长期外部评测后端

- 适合借用 CyBench/CVE-Bench 的容器化执行和资源限制机制。
- 不适合作为近期保证结论层；Ithuriel 应适配其执行结果，而不是重建或内嵌整套 benchmark 平台。
- 当前 GitHub 仓库没有明确显示许可证，任何 vendoring 或代码复用须先完成许可核验。

#### 建议补入清单：Inspect AI

- [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) 是 UK AI Security Institute 的 MIT 许可评测框架，支持工具调用、多轮对话、模型评分和扩展包；CAISI Cyber Evals 也以它为执行基础。
- 长期应优先研究面向 Inspect 稳定抽象的 adapter，再按需接入 CAISI 的具体 benchmark，避免把 Ithuriel 绑定到单个评测集。

### 暂定开发顺序

1. 关闭当前 calendar probe 的 instrument qualification、独立外部操作员 C3/C4，以及 runner 信任核拆分。
2. 实施 `Agent Component Intake Assurance` 薄切片。
3. 把 AgentDoS 预算和 receipt 要求应用到所有后续执行后端。
4. 建立轻量模型/Agent 更新回归门；出现第二种评测后端或明确用户需求时再接 Inspect/CAISI。
5. 只有真实持久记忆落地后才启动 memory assurance。
6. 不建设通用红队平台、无监督自动化 SOC 或生产蜜罐系统。

### 原型阶段的开发者/操作者分离原则（待讨论）

阶段性结论：**角色早分，人员晚分；独立性不足时降低结论，不伪造独立性。**

原型阶段没有必要把“开发者”和“操作者”一律强制为两个不同的人。开发者可以兼任操作者，用于验证 runner、Action/审批/执行链、Evidence/Finding 闭环、探针基本判别力和故障记录机制。过早要求两套人员、账户或服务会减慢反馈循环，也可能制造只有形式、没有实质的独立性。

但角色边界仍应从原型期开始明确，因为开发者与操作者拥有不同的输入、权限、知识和错误责任。人员是否必须分离，应由本轮希望支持的结论决定：

| 要回答的问题 | 同一人是否足够 | 可支持的结论边界 |
|---|---|---|
| 代码、runner 和执行链能否工作 | 是 | 内部工程验证 |
| 冻结输入后能否按规则复现 | 是，但须披露 | 内部流程可复现，不构成独立复核 |
| 安全 oracle 能否区分冻结的正负对照 | 可用于 instrument development | 不证明陌生操作者也能正确使用 |
| 普通操作者能否理解、纠正编译出的 probe | 否 | 需要未参与该功能设计的人 |
| 操作者是否会过度解读报告或错误处置 | 否 | 需要人员独立的 disposition 测试 |
| 高风险真实副作用的批准是否构成独立监督 | 否 | 需要独立操作者或审批者 |
| 系统是否可用于对外保证或客户环境 | 否 | 需要与结论强度相匹配的人员独立性 |

对当前 Ithuriel 的含义：

- C2 主要验证 instrument 的行为判别能力，可以由参与开发的人运行，但结论限于 instrument development/qualification，并记录实际人员关系；
- C3/C4 测试人的理解、纠错和 disposition，参与设计的人已经知道正确答案，不能提供有效证据，必须由未参与设计的人完成；
- Hat A/Hat B 的冻结、提交顺序和哈希绑定仍有控制事后修改与实验污染的价值，但同一人戴两顶帽子不产生人员独立性，也不得描述成“独立批准”；
- 原型内部运行可记录 `person_independence=none`；工作流/可用性验证使用未参与设计的内部人员；真实副作用、高风险审批和对外保证则要求明确的独立操作者或审批者。

因此暂不删除开发者/操作者的结构性角色区分，也不在原型期建设双账户、独立服务或强制任务队列。后续需要决定的是人员分离的风险触发条件，以及不同 `person_independence` 等级允许支持哪些 claim。

### 下次讨论待决事项

1. 是否确认“组件接入保证”为当前里程碑后的第一条新纵切片；
2. 首轮 spike 是只比较静态 skill 扫描，还是同时包含一个经沙箱批准的 MCP fixture；
3. Snyk Agent Scan 是否作为主 adapter、`aig-skill-scan` 是否只作为对照；
4. Inspect AI 的接入触发条件采用“出现第二种评测后端”，还是“首次模型升级即触发”；
5. 是否采纳“角色早分、人员晚分”的原则，并为真实副作用、人员 disposition 和对外保证分别定义人员独立性触发条件；
6. 以上建议批准后，应进入哪一份权威 roadmap/ADR，而不只留在阅读清单中。
