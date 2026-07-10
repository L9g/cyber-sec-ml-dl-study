# 学习笔记：AI 红队 pipeline —— 你的直觉、那个关键误解、和更深的原理

> 产出 2026-07-09。触发 = 你读完 P0 后画出的四层 AI 红队 pipeline。
> 这篇不是"标准答案"，是一份**给你反复想**的学习笔记：先原样保留你的图，再逐层拆"哪里对、哪里弯、为什么"。
> 你自己说这是"整个项目最关键的一环"——我同意。因为它逼你回答项目的定生死问题：**你到底在卖什么，什么只是管道。**

---

## 0. 为什么这一环定生死

一个残酷的事实：garak / PyRIT / InjecAgent / ToolEmu / AgentDojo **全是公开的、别人也能 `pip install` 的**。如果你的项目 = "把这五个按顺序跑一遍"，那它没有护城河——任何人一个下午能搭一样的。

所以这一环真正在问的不是"用哪些工具、怎么排"，而是：**在这条全是借来的工具的链上，哪一部分是只有你在建、别人抄不走的？** 你的图把工具阶梯画得很好，但**恰恰没画出那个不可抄的部分**。这篇的一半篇幅在补它。

---

## 1. 你原本的图（原样保留）

四层 escalation ladder：

1. **模型/接口层红队**（garak、PyRIT）→ 攻击模式、易受攻击类别、基础安全指标。
2. **IPI 标准化基准评估**（InjecAgent）→ 裸 agent vs 加了防御的 agent，在 1000+ 用例上的成功率分布，按攻击目标（直接伤害 vs 数据外流）和工具类别找薄弱点。
3. **虚拟工具/环境仿真**（ToolEmu）→ 吃前两层的攻击模式，用 LM 仿真器生成"危险工具+模糊任务"组合，暴露长尾风险。
4. **真实/高保真红队**（AgentDojo 或客户真实沙盒）→ 合同/法规允许下，在真实工具调用链上评估实际危害（真实 API、真实资源变更、真实权限）。

**你的直觉对了三件大事**（先把功记下，这些不用改）：
- **escalation 的方向对**：便宜/宽 → 贵/真，把最有价值的攻击往后漏斗。这是红队和可靠性测试共同的正确姿势。
- **你已经隐约感到第 4 层不对**——所以你写"AgentDojo（**或**客户真实沙盒）"，把两个东西并列了。这个"或"字是你的直觉在报警，下面第 2 节就是顺着这个报警拆。
- **你在第 2 层塞进了"裸 vs 加防御"**——你可能没意识到，这一句是全图最值钱的一句（第 4 节细讲）。

---

## 2. 那个 load-bearing 误解：你把"保真度"当成了**一根**轴

这是全篇最重要的一处，因为纠正它会**重排你的图**。

### 事实先钉死（已回读 AgentDojo 原文 `2406.13352` v3 / NeurIPS'24 核实）
- **AgentDojo 是 mock 执行**：74 个工具 = **Python 函数读写内存里的 state 对象**（`WorkspaceEnvironment{inbox, calendar, cloud_drive}`），state 填 **dummy 数据**。datasheet 原话两次：**"We do not have any real data. Only dummy data."** utility 是**确定性二值函数**，查 environment state 的前后 mutation。97 realistic 任务 + 629 安全用例（已核实）。
- **论文自己画了这条线**（L107 决定性）：AgentDojo 按 formal utility check **over the environment state, "rather than relying on other LLMs to simulate an environment [50]"**——`[50]`=ToolEmu。即"**AgentDojo=确定性真 state / ToolEmu=LM 仿真**"是原文框架，不是我硬套。
- **ToolEmu 是 LM 仿真**：LM **生成**工具执行结果（连没实现的危险工具都能"假装"跑），配 LM 安全评判器，**非确定性、开放式**。
- 所以：**AgentDojo 和 ToolEmu 都在 mock 层，都无真实副作用。AgentDojo 不比 ToolEmu"更真实"。**

### 你弯在哪 —— 以及我也弯在哪（对称的错：都把 AgentDojo 的特殊性挂错了轴）
"realistic" 一词其实拆成**三件正交的事**，你我各中一枪：

- **场景真实度**（toy 模板 ↔ 真实多步工作流）：AgentDojo **高**（"navigate an e-banking website"）。← **这诱骗了你**：场景像真的 → 以为执行是真的。
- **执行真实度**（mock 内存 state ↔ 真实 API/副作用）：AgentDojo **低**（fake bank / dummy data）。
- **静态 ↔ 可扩展/自适应**（固定语料 ↔ 造新攻击的框架）：AgentDojo **高**——原文："not a static test suite, but rather an extensible environment for designing and evaluating new agent tasks, defenses, and **adaptive attacks**"。← **这诱骗了我**：我上一版把它和 InjecAgent 一起当"静态回归语料"，低估了它。**AgentDojo 恰是第 5 节要的"自适应攻击"的 designed home**（Firewalls 那篇正是在 AgentDojo 上打补丁加 adaptive attack）。

**核心教训**：别把"从假到真"想成一根轴。它至少是三根，"场景真实 ≠ 执行真实 ≠ 可扩展"。拆开后五个工具落位：

| 工具 | 场景真实度 | 执行 mock↔real | 静态↔可扩展 | 真正职能 |
|---|---|---|---|---|
| garak / PyRIT | 低（接口层探针） | mock | 生成式 | **产攻击语料** |
| ToolEmu | 中（危险工具/模糊任务） | mock（LM 假装） | 开放/生成 | **发现**长尾风险 |
| InjecAgent | 中（IPI 用例集） | mock | 偏静态语料 | 标准化 IPI 回归 |
| **AgentDojo** | **高**（多步真实工作流） | **mock（dummy state）** | **高（自适应攻击框架）** | **可复现回归数 + adaptive 攻击工作台** |
| 客户真实 scoped sandbox | 高 | **real（真实副作用）** | bespoke | **量真实爆炸半径** |

**重排结论**：
- 你第 4 层"真实 API / 真实权限 / 真实资源变更"的**概念完全正确、是整条链最值钱的一层**——但**实现它的不是 AgentDojo**（原文证实是 dummy data），是你薄封装的**客户真实沙盒插件**，由 `requires_approval` + 合同 + RoE 三重闸门 gated。
- **AgentDojo 降到第 2/3 层**当 base，但它**身兼两职**：既出可复现的回归数字（确定性 utility），又是掺入自适应/二阶攻击的**工作台**（可扩展框架）。别再把它当"只是个静态基准"——那是我上一版的错。
- 真实执行层**只留**那个 bespoke 沙盒。

### 这座桥让它扣上你的老本行
把上面三根轴收成你 RAMS/可靠性里早就有的语言：

- **执行真实度（mock↔real）= 你的 SIL → HIL → 场试（field trial）阶梯**。软件在环、硬件在环、真实工况——保真度逐级升、成本逐级升、每级往上漏斗最值得测的工况。ToolEmu/AgentDojo≈SIL（纯软/内存，无真实副作用）、真实沙盒≈HIL/场试。
- **场景真实度 = 你的"试验工况代表性"**。一个 SIL 台架也可以喂**高度代表现场的工况谱**（AgentDojo 的多步真实工作流），但它**仍然是 SIL**——工况像现场，不等于在真设备上跑。**这正是你踩的点：把"工况代表性高"读成了"在真设备上"。**
- **静态↔可扩展 = 固定验收剖面 vs 可编程试验台**。AgentDojo 更像后者（能编新载荷谱/自适应攻击），不是一份冻结的验收清单。

你当初弯，是因为可靠性里"更真的台架"*恰好*常常也"工况更代表、也更贵"，三者**经验上相关**，于是被脑子压成一根。但它们**逻辑上正交**——一个 mock 台架可以工况极代表且极可复现（AgentDojo）。**把三根轴拆开，是这一环最大的认知升级。**

---

## 3. 看不见的那根脊柱：工具是 commodity，证据层才是产品

回到第 0 节的残酷事实。你的四层**全是借来的 base**。那不可抄的部分在哪？——在**横贯四层的一根脊柱**，你的图里没画它：

```
把四层异构的输出，统一归一化进 Evidence schema（钉 tool_version + invocation_params）
      → 每个 AI Finding 带 ai_run_record（n_runs / n_success / success_rate）
      → 打 P1–P6 机理根因标签
      → 按轴 rollup 出覆盖度
      → 出一份可复现、可审计、可追溯到具体语料版本的保证结论
```

**没有这根脊柱**：你有的是"五个工具各吐各的 JSON"——一个扫描器聚合器。
**有了这根脊柱**：五个各说各话的工具收敛成**一个可签字的裁定**。这正是 survey 说领域最缺的东西（benchmark 碎片化：85% 基准只被用过一次、两个防御无法跨论文比较）。**别人建工具，你建让工具们可比、可复现、可审计的那层。**

画图时的动作：**把这根脊柱画成贯穿四层的横条，不是第五个盒子。** 它是底盘，不是下一站。

---

## 4. 被你埋掉的头条：assure-the-defense 才是护城河

你在第 2 层写了一句"裸 agent vs 加了我的防御（sandbox / content firewall / 多 agent 审计）的 agent"。你把它当附注。**它其实是全图最不拥挤、最值钱的角度，应该拎出来当一条贯穿全链的评估模式。**

为什么：
- **红队扫描器市场很挤**（人人能跑 garak）。但"**你部署的这个防御到底管不管用、关掉了哪个威胁**"是公开缺口——`Which-Defense`(2606.02822) 证明现有 BAS 只报**一个聚合覆盖数**，掩盖了"哪个防御族关哪个威胁"，还测出 refusal 过滤器**一改写（paraphrase）就崩**。
- 你的做法（**同一套语料**，裸 agent vs 每种防御配置，报**按威胁类型/工具类别的 delta + coverage 曲线**，而非一个总分）正好填这个洞。
- 而且——这就是你 portfolio 里反复出现的 **same-pipeline-for-deltas** 模具（同一管线只换一个变量，量净增益）。你在项目一/四已经用过：把它迁到这里几乎是本能。

**动作**：把"bare vs defended 差分评估"从第 2 层的附注，升为**第 2/3/4 层每层都能开的一个评估开关**。你的产品一句话从"我帮你测有没有漏洞"变成"**我给你一份可复现的证据，证明你的防御在自适应攻击下真的关掉了这些威胁、且没崩在改写上**"。后一句在市场上稀有得多。

---

## 5. 一个会毁掉整条链的陷阱：借来的"通过"不是保证

你第 2–4 层都建立在"在 InjecAgent/AgentDojo 上的成功率"之上。**这里有个能让整个保证结论作废的坑**：

`Firewalls`(2510.05244) 证明——一个**简单**的双 firewall 就把 AgentDojo / InjecAgent / ASB / τ-Bench **全刷到"完美安全"**。结论不是"防御解决了 IPI"，而是"**这些基准太弱、开箱即被饱和**"（弱攻击、度量有缺陷、有实现 bug）。

对你的含义，用你听得懂的话：**这等于在标定工况、名义载荷下跑了一遍台架就签"可靠"——而现场的失效恰恰发生在你没施加的那个载荷谱上。** 借来的基准的"pass"是**名义工况下的 pass**，不是保证。

**动作**：每一层都必须掺入**自适应 / 二阶攻击**（那篇的三段级联：标准注入 → 二阶 → 自适应），并且 `ai_run_record` 要记录**攻击强度等级**。否则你交付的"防御有效"经不起对手改一版 payload。**保证结论的可信度 = 你施加的最强攻击的强度，不是基准自带的那批。** 好消息：**AgentDojo 本就是为此设计的**（原文"extensible environment for … adaptive attacks"），自适应攻击不必另起炉灶，就在 AgentDojo 框架里扩——这也是为什么它比 InjecAgent 更值得当主 base。

---

## 6. 诚实的边界（别丢，写进报告的 not_applicable）

- 这条链**全是单轮 IPI-through-tools**。它**继承了 AgentDojo/InjecAgent 不测 memory / reflection 的盲区**，也没有 `AgentHazard`（Claude Code+Qwen3 **ASR 73.63%**）那种**逐步局部合法、累积成害**的多步危害，也没多 agent。MVP 不做可以，但要在报告里**明确标 `not_applicable`**——四层跑绿**不等于**覆盖了这些面。这是你"如实报告"纪律的直接应用：**绿不等于真测过。**
- 整张图是项目的**安全红队半边**（"破/诊断"）。**合规/对标准保证**那半边（NIST RMF / GOV.UK assurance / EU AI Act 映射）是**正交的另一根轴**，不归约成注入红队。现在聚焦安全半边没错（这正是路线图前移的那条切片），只是别让它悄悄把"项目 = 注入红队"坐实了。

---

## 7. 修正后的整图（一张图看全）

```
                        探索/发现  ←─────────────────────→  可复现/回归
                        ┌───────────────┬──────────────────────────┐
   mock (无真实副作用)   │ garak/PyRIT   │  InjecAgent (静态IPI回归) │
                        │  (产语料)     │                           │
                        │  ToolEmu      │  AgentDojo ★双职:        │
                        │  (发现长尾)   │  可复现回归数 + adaptive   │
                        │               │  攻击工作台(可扩展框架)    │
                        ├───────────────┴──────────────────────────┤
   real (有真实副作用)   │   客户真实 scoped sandbox（bespoke 插件）  │  ← gated:
                        │   量真实爆炸半径 · 真实权限/资源变更        │  合同+RoE+approval
                        └──────────────────────────────────────────┘
   注:纵轴=执行真实度(mock↔real);横轴=可扩展/探索↔可复现。
   AgentDojo 场景真实度高但执行仍 mock(dummy state),故留 mock 层。

   ══════════════════════ 贯穿全部：差异化脊柱 ══════════════════════
   Evidence 归一化(钉 tool_version+params) → ai_run_record(success_rate+攻击强度)
   → P1–P6 根因标签 → 覆盖度 rollup → 可复现/可审计保证结论
   ─────────────────── 贯穿全部：bare-vs-defended 差分评估开关 ───────
   每一格都能开：裸 agent vs 各防御配置，报按威胁/工具类别的 delta + 曲线
   ─────────────────── 贯穿全部：自适应/二阶攻击注入（防基准饱和）────
```

三个动作一句话记住：
1. **AgentDojo 降级**：从"真实层"降到"可复现 mock 基准层"；真实层只留 gated 客户沙盒。
2. **画出脊柱**：Evidence/Finding/根因/保证是横贯四层的底盘，不是第五个盒子。
3. **升格差分评估 + 掺自适应攻击**：把最值钱的"证明防御有效"从附注变成贯穿全链的模式，并用自适应攻击兜住"过基准≠安全"。

---

## 8. 提炼出的原理（可迁移到项目别处）

1. **"保真度"不是一根轴——至少三根。** 排"从假到真"的阶梯前先拆：**场景真实度**（工况代表性）× **执行真实度**（有无真实副作用）× **静态↔可扩展**。三者经验上常相关、逻辑上正交；不拆开就会像 AgentDojo 那样被"场景像真的"骗成"执行是真的"。（这个错你我在同一篇论文上各犯一次、犯在不同轴——最好的提醒。）
2. **在一个全是借来工具的领域，产品 = 让工具们可比/可复现/可审计的那一层，不是工具本身。** 别把底盘画成下一个盒子。
3. **红队是拥挤的，"保证防御有效"是稀缺的。** 同一管线只换一个变量量净增益（same-pipeline-for-deltas）——你在别的项目已经会，这里照搬。
4. **借来的"通过"是名义工况下的通过。** 保证的可信度 = 你施加的最强攻击的强度。这条和你 RAMS 里"台架 pass ≠ 现场可靠"是同一句话。
5. **绿不等于真测过。** 没测的面要写成 `not_tested`（不是 `not_applicable`！后者出分母、会虚高覆盖度），把范围声明和覆盖度模型做成同一个对象。

---

## 9. 留给你想的问题（这几个会真正塑造架构）

1. **真实层的闸门到底谁来扳？** 客户真实沙盒那层，`requires_approval` 是人工一次一批准，还是按 RoE 策略自动放行低风险动作？你在可靠性里怎么界定"允许在真设备上做的破坏性试验"——那套授权模型能直接搬吗？
2. **脊柱的"可复现"对 ToolEmu 这种非确定层意味着什么？** LM 仿真每次结果不同——你 `ai_run_record` 的 `n_runs/success_rate` 是不是就是为这层设计的？确定性层（AgentDojo）和非确定层（ToolEmu）在你的 Finding 四态里应该落不同状态吗（回归=pass/fail，发现=inconclusive/需重跑）？
3. **差分评估的"防御"是客户给的、还是你提出的？** 如果是你提出的（sandbox/firewall/多 agent 审计），你就同时是**卖防御的人**和**验防御的人**——这在合规叙事上是利益冲突还是一体化优势？怎么讲才诚实？
4. **哪条切片先落地？** 修正后，最薄的端到端 = garak/PyRIT 产语料 → InjecAgent 回归 → 脊柱归一化出一份 Finding 报告（全 mock、无真实副作用、无需闸门）。真实沙盒层要不要**推迟到有真实客户合同**才建？
5. **这条链和"合规半边"在哪里汇合？** 有没有一个点，安全红队的 Finding 直接变成对某条标准（NIST RMF / GOV.UK assurance）的证据？如果有，那才是"安全+合规 Agent"真正合体的地方——现在它还是两张皮。

---

## 10. 规划决策（本轮定稿 2026-07-10，供后续开发遵循）

用户审阅后拍板；这些在**规划阶段**就约定，不必马上改 `ontology_schema.yaml`。

**D1 · 状态词汇要分家**（防覆盖度虚高）：约定 `not_applicable`（target 真不适用，**出**分母）/ `not_tested`（适用但没测，**进**分母、记 gap，比照 `inconclusive`）/ `unsupported`（适用但无工具/适配器，进分母）/ `out_of_scope`（本次授权范围外）四者边界。范围声明 = 这张结构化清单，与覆盖度模型**同一个对象**。

**D2 · 归一化 ≠ 可比**：产品目标写成——「**统一收集、追溯和解释不同评估工具的证据，并在测量条件兼容时支持比较**」。不提前承诺所有 ASR/评分可直接汇总。**证据从第一天捕获测量上下文**（corpus_version / target_id / attack_strength / run_params），契约（measurement_contract）以后再建。

**D3 · 保真度四维**：场景真实度 × 执行真实度（mock↔real 副作用）× 静态↔可扩展 × **环境语义保真度**（确定性 state vs LM 仿真的自洽性）。AgentDojo = 高场景/mock 执行/可扩展/高语义保真 → 确认循环主 base；ToolEmu = LM 仿真、语义保真低 → 探索循环。

**D4 · 不过早锁死纯黑盒**：定位为「**以黑盒对抗评估为第一切片，逐步扩展到配置检查、轨迹审计和治理证据**」。现 schema 的 `verification_methods` 已含 `config_inspection/document_review/attestation`，广度本就在，别叙事上写没。

**D5 · pipeline = 两个循环，不是单向阶梯**：
- **探索循环**：garak/PyRIT/ToolEmu/自适应攻击 → 发现（Finding 落 inconclusive/需重跑）。
- **确认循环**：AgentDojo/InjecAgent/冻结语料 → 回归 + defense delta（Finding 落 pass/fail）。
- **毕业闸门**：探索循环里稳定命中（≥k/n）的攻击 → **冻结+版本化**进确认循环语料。这既是语料治理跑起来的样子，也防确认循环被静态语料饱和。
- 客户 sandbox 是**后期验证环境**，不是必经的最后一级。

**D6 · 法规原文作最终锚**：overview 用于理解，**法规原文/正式标准用于建 control mapping**（`standards_refs.source` 不得悬空）。阅读清单每条法规标 `understand` / `anchor` 角色。

**D7 · 真实执行层三阶段 roadmap**（客户 sandbox 非 optional，是后期高价值必争层）：
> MVP：公开 mock benchmark + 统一证据/Finding
> → 中期：客户配置复刻的 seeded test tenant / digital twin（**workhorse 主力**：高配置保真、避开生产不可逆副作用）
> → 后期：gated 客户 scoped sandbox（**gated 例外**，验证生产代表性 blast radius）
>
> 客户 scoped sandbox 不属于 MVP 的最薄闭环，但属于咨询/保证产品的后期高价值必争层。公开 benchmark 主要证明标准场景下的行为；生产代表性 sandbox 用于验证真实身份、权限、工具链、数据流、控制配置和可恢复副作用下的实际影响范围。是否进入该层由合同、RoE、审批和环境条件决定。

术语订正：称「**生产代表性 blast radius**」而非无条件「真实 blast radius」——sandbox 与生产在权限/数据/网络/监控/依赖上可能有差，Finding 须挂 **`fidelity_gap` 注记**来 bound 那句 claim（= RAMS 的试验-现场 representativeness；字段以后建，概念现在定）。**护城河 = 在不造成不可接受损害的前提下设计/授权/执行/解释高保真测试，再转成有边界的保证结论——不是"接入真实 API"本身。**

**D8 · 第一切片（北极星，最薄端到端闭环）**：
一个明确的 agent target → 一套**版本化 IPI 场景** → **bare / defended 两配置**（defended 先用**已发表的借来防御**如 Firewalls tool-in/out 或 spotlighting，**不用自研**——绕开"既卖又验"利益冲突 + 顺带复现已知结果；自研防御留到有客户合同）→ 多次运行 → 原始轨迹和工具调用证据 → Finding → 结构化范围/未覆盖面声明（= D1 的清单）。**全 mock、无真实副作用、无需闸门。** 跑通后再据实际数据结构/评分困难/复现问题决定 schema，不提前按每篇论文设计所有字段。

**四文档定位与决策权**（治理纪律，防论文驱动功能膨胀）：
- Reading List → 接下来读什么、为哪个开发决策服务。
- Domain Map → 领域有哪些问题、项目覆盖/不覆盖哪里（**约束 pipeline 别缩成 PI scanner**）。
- Long-tail Summaries → 哪些思想可借、哪些工具可用、哪些暂不投入。
- **Pipeline Note（本文档）→ 最高决策权**：第一版产品怎样形成最薄端到端评估闭环。
- 规则：摘要/清单**只供证据，不反向驱动加功能**。

## 11. 后续测量设计问题（parked，不阻塞前期开发）

以下工程细节移到"以后再做"，前期不碰：
- ASR 置信区间、effect size、统计功效。（**部分前移 2026-07-10**：ADR 0002 首个真跑坐实「`measurement_valid=True` ≠ 有功效」，故把**最小诚实 flag**——`security_delta` 附 CI + bare/defended CI 重叠时标 `underpowered`、不断言 delta——前移进 `architecture-seams-D8.md` §7；**完整** CI/effect-size/功效设计仍 parked。）
- 签名 / 可信执行环境 / 独立时间戳等强 provenance。
- 完整 `measurement_contract` schema。
- defense-specific adaptive attacker 的严格实验设计。
- P1–P6 的置信度与版本化 taxonomy。（**✅ 已定 2026-07-10**：Finding 的 `root_causes` **枚举数组**标签**现在就加**——已落 `ontology_schema.yaml` v0.6 `root_cause_enum`，advisory-only、无序集合、≥1 项、`UNDETERMINED` 当地板、**不设 primary**。这是对 schema 冻结的**唯一破例**，理由=标量→数组不可逆迁移。要 defer 的只是：tag 置信度、taxonomy 版本化、root-cause rollup/mapping、primary 归因。）
- 形式化验证 ActionPlan 状态机（Formalizing `2510.14133` 的 11 态 + 时序逻辑属性留作后期）。
- 认证机构级别 claim 与独立性设计。

## 待核（进正式架构文档前）
- ✅ **已核实**（回读 `2406.13352` v3）：AgentDojo = **97 任务 + 629 安全用例 + 74 工具**，工具读写内存 state 对象、**dummy 数据、无真实副作用、确定性 utility**；且原文自称"extensible environment for … adaptive attacks"、非静态。→ 本篇第 2/5/7 节据此改定。
- InjecAgent(~1054) / ToolEmu(~144) 用例数仍凭印象，正式引用前回各自 PDF 核。
- Firewalls "完美安全" 是在其修正后的基准上，跨模型是否成立须看原文。
