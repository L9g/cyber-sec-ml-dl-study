# Ithuriel（项目五）· 外部审核说明 —— 给搭档的 review agent

日期：2026-07-22（上一版 2026-07-12，已整体重写）· 供第三方 agent 冷启动审核**设计思路**与**代码**用

> 这份文档是**自足**的：读它的 agent 没有我们的对话历史与 auto-memory。它给出审核所需的
> 最小充分上下文与**审核边界**（这个项目有三条硬纪律，不内化就会给出与方向冲突的建议）。
> 冲突时，权威顺序：本文 §2 纪律 > `docs/architecture-seams-D8.md`（编码接缝契约）> 各 ADR > 代码注释。

---

## 1. 项目一句话与当前落地范围

**可审计、可复现的保证结论 + 对陌生系统的对抗性故障发现。**
卖点**不是**再造一个安全扫描平台，而是把借来的探测、攻击、防御工具的原始输出，归一化成
**带溯源、带统计功效判定、带范围声明的结构化保证结论**。

两半都已落地，但成熟度不同：

- **保证结论层（成熟）**：四条端到端切片跨四种裁定形状验证过（非确定 AI、确定性配置读取、
  主动探测带执行授权机、人工复核声明式证据），其上又落了 Claim 层、内部报告 view、
  AssessmentManifest 分母、Cyber Essentials area rollup 轴。
- **对抗性故障发现（新，正是本轮最需要审的部分）**：一条日历间接提示注入探针，从情报编译成
  可复跑测量，2026-07-22 首次让它的 security oracle 通过判别性检验（正对照 29/30、
  两个同族匹配负对照各 0/30）。`assurance_level` 仍是 `none`，保真度仍在 mock。

**审核重心建议**：结论层已被审过两轮（ADR-0009、ADR-0010 记录了那两批），本轮最值得投入的是
**探针 runner 与它引入的测量方法学**，见 §3 表格中标 ⭐⭐ 的两行。

---

## 2. 三条构建纪律（审核前必须内化）

审核这个项目时，**很多「标准最佳实践」建议是反纪律的**。以下三条决定哪些建议有用、哪些会把项目带偏。

### 2.1 两层模型：Base 等于借，Differentiator 等于建

- **Base（借，不自建）**：执行机制、进程间通信、调度、扫描与探测工具（AgentDojo、nmap、
  未来的 nuclei/garak/PyRIT）、已发表的防御。
- **Differentiator（建）**：**只有**标准到 ontology 的蒸馏，以及证据、Finding、保证层。
- **两处必须精确的边界修正**（旧版 brief 在这两处不准，请以本节为准）：
  1. 借的是执行**机制**；把执行**接缝**建成强制执行点（`executor.py` 作为 PEP，负责 RoE 授权、
     两阶段校验、命令白名单）**是自建的差异化层**，不算借。
  2. **`scripts/run_calendar_probe.py` 已经不是薄封装**。它现在 3376 行，比整个 `src/` 还大，
     内含 oracle、证据分层、授权硬门、攻击族分类——这些是差异化层逻辑，**请按自建代码审**，
     不要按「借来的 runner 的薄封装」审。**这条本身就是我们想被 challenge 的地方**：差异化层
     逻辑长在 `scripts/` 里是否是个错误的归属，见 §4.13。
- **审核含义**：不要建议重写或增强扫描器、自研防御、把 AgentDojo 换成自建 harness、建平台化功能。
  护栏是「minimal base 不等于 toy base」——底座借到领域内行点头为止，不多建一分。

### 2.2 thin-slice：先跑最薄切片、据真实摩擦定 schema

- 字段**只在**形状不可逆且 advisory-only 时才提前定；否则等真实摩擦逼出来再加。「便宜」不是加字段的理由。
- `docs/ontology_schema.yaml`（v0.6）是**冻结**的权威 schema。**成绩数据**：它最后一次改动发生在
  差异化层落码之前，此后 69 个 commit、四种裁定形状、四个上层对象全程零改，新枚举一律走 pydantic advisory。
- **审核含义**：不要建议照 OWASP、NIST 或论文补齐字段，也不要建议把明确 parked 的字段现在加上。
  可以质疑：某个**已加**的字段是否真被真实数据逼出来、形状是否真不可逆、是否本可延后。

### 2.3 结论不得被折成单一数值

这条是从 ADR-0017 与 DESIGN 文末「附」节升上来的纪律。防御把注入成功率压到零、同时把 under-attack
的可用性也压到零（检到注入即中止），**在完整性轴上安全、在可用性轴上不安全**，攻击者赢得的是
注入触发的拒绝服务。保证工具**不该替部署方**把这两轴压成一个字。因此系统刻意不产 overall score、
不产单一置信度档、不产 readiness 单值；覆盖率与 warrant、fidelity 分列呈现。

- **审核含义**：不要建议加总分、加健康度评分、加 readiness 枚举、把 `confidence_basis` 折成一个数。
  可以质疑：某处呈现是否**事实上**已经等价于一个总分（这类漏口才是有价值的发现）。

> 三条纪律本身都欢迎被 challenge，但请**明说你在挑战纪律**，而不是默认它不存在。

---

## 3. 仓库地图与建议阅读顺序

`src/`（2971 行，15 模块）与探针 runner 都是「建」的半边。`docs/` 是设计权威。测试 185 个全绿。

| 顺序 | 路径 | 作用 | 优先级 |
|---|---|---|---|
| 1 | `docs/architecture-seams-D8.md` | 编码接缝契约（设计权威） | 先读 |
| 2 | `scripts/run_calendar_probe.py` (3376) | **探针 runner**：分层 oracle、四层证据、攻击族分类、ADR-0022 授权硬门、逐 turn 遥测。带 `--self-test`（255 项离线自检，不需 key） | ⭐⭐ 最高 |
| 3 | `docs/trial/prereg-*.md` (4 份) | 预注册：判据在看数据前写死，含 C2 分层判据、可解释 trial 定义、停止规则 | ⭐⭐ 最高 |
| 4 | `src/ithuriel/report.py` (501) | 内部报告 view：coverage 乘 warrant 与 fidelity 的二维矩阵，纯投影不重算 | ⭐ 高 |
| 5 | `src/ithuriel/models.py` (403) | pydantic schema 与各 advisory 枚举 | ⭐ 高 |
| 6 | `src/ithuriel/derive.py` (405) / `derive_session.py` (358) | flat run JSON 到 `AssuranceReport` 到 `SessionReport`（纯函数） | ⭐ 高 |
| 7 | `src/ithuriel/ledger.py` (160) / `manifest.py` (54) | 覆盖率 rollup 与**声明式分母**（防输入选择做高） | ⭐ 高 |
| 8 | `src/ithuriel/claim.py` (91) | Claim 层：多维 `confidence_basis`，不折单值 | 中 |
| 9 | `src/ithuriel/executor.py` (189) | **自建的** PEP：RoE 授权、两阶段校验、白名单 | 中 |
| 10 | `port_scan.py` (219) / `config_inspection.py` (200) / `attestation.py` (191) | 三种非 AI 裁定形状的插件 | 中 |
| 11 | `src/tests/**` (2244, 185 passed) | 代码契约级测试，看断言可反推设计意图 | 中 |
| 12 | `docs/adr/0001..0022` | 22 个决策记录，每个字段与决策的「为什么」都在这里 | 按需回查 |

**跑测试**：`.venv/bin/python -m pytest src/tests -q` 应为 `185 passed`；
`.venv/bin/python scripts/run_calendar_probe.py --self-test` 应为 255 项全过（离线、零花费）。

---

## 4. 设计审核：我们想被 challenge 的地方

前七条是结论层的老张力（已被审过，仍欢迎复议）；后六条是**本轮新引入、尚未被外部审过**的，
建议优先。

1. **`measurement_valid` 与 `underpowered` 正交**。只有两者同时成立才断言 defense delta，
   否则 fail-closed。请审这个二分是否真正交、有没有漏口。
2. **`bare ASR=0` 判 inconclusive 而非 pass**。正对照缺失不等于目标安全。请审一致性。
3. **security 与 utility 不可分对**：`TradeoffClass` 三值加正交 `TradeoffUnclassified`。
   阈值锚死于早期五跑，`blocks_preserving_utility` 至今未观测、留定义不留 fixture。
4. **内容寻址与哈希稳定性作为契约**：任何新字段必须带默认值才不进哈希、不破既有 id。
   附带一条已知延后项：`content_hash` 是 64-bit 截断，够做 id、**不够客户级证据完整性**。
5. **单一 treatment 的 fail-closed 比较**：未声明差异一律使 delta invalid。
6. **溯源的诚实退化**：历史无 provenance 的跑退化为全 absent 而非崩溃。
7. **注册表作为 schema 不变量的牙齿**：`standards_ref.source` 不得悬空。

以下六条是新的：

8. **⭐ 可解释 trial 的分母，条件化在处理后变量上**。探针的主指标分母排除了
   `host_core_state_success` 为假的 trial（宿主任务没进入写相位时，攻击结构上无法被测量）。
   但 `host_core` **是处理后变量**：注入本身可能损害宿主任务。缓解措施是排除规则事前冻结、
   逐臂报告排除率、两臂差异视为 utility 损害发现而非噪声。**请审这个缓解是否够**，
   以及在确认阶段（有负对照时）它会不会引入实质偏倚。
9. **⭐ 分层 C2a 与 C2b**。C2a 是基础判别性（未暴露攻击规格的阴性对照不得产生目标事件，
   失败即整轮无效）；C2b 是暴露条件判别性（把攻击规格原样交给模型但不下指令，仍不得被判为执行，
   失败只缩小结论范围、**不构成目标易感或不易感的证据**）。请审这个分层是否切在正确的地方。
10. **⭐ 四层证据与 not-measured 语义**。emission、dispatch、tool result、state 四层分开保存，
    attempted 类原子只读 emission。state 层靠 call 到 event 的 id 强绑定；**解析失败返回
    not-measured 而非 false**，弱的存在性 fallback 记录但不得替代主原子。请审这个「宁可未测量、
    不可静默降级」的取舍在别处是否也应推广。
11. **⭐ 攻击族逐调用互斥分类**。两个族分开记分、不池化、不互相回填；旁路观察（例如在增补族里
    另建攻击者事件）只作诊断并列呈现。请审互斥规则有没有让某类真实攻击落进无人认领的缝隙。
12. **⭐ 一人两帽治理的边界（ADR-0022）**。角色分离但非人员独立；Hat A 冻结、Hat B 独立 commit
    批准、机器执行、留回执。**已实测到的边界**：授权门保证冻结的那份代码跑了，
    **不保证那份代码实现了冻结的那份设计**（哈希管字节、不管语义）；git commit 只是顺序锚点、
    不是可信时间戳。请审还有哪些它看起来能保证、实际不能保证的东西。
13. **⭐ 差异化层逻辑长在 `scripts/` 里的归属问题**。探针 runner 3376 行比整个 `src/` 还大，
    里面有 oracle、授权门、证据分层。这是纪律画错了，还是探针本就该有独立的第三层归属？
    **我们自己没有定论，这是最想听到判断的一条。**

---

## 5. 代码审核：请重点看的不变量

- **纯函数边界**：`derive.py`、`derive_session.py`、`claim.py`、`report.py` 应读 dict 出 dict、无副作用。
  `report.py` 额外守「只投影不重算」。
- **哈希稳定性**：新字段默认值、canonical 序列化是否给出确定性字节。
- **向后兼容**：历史 fixture 能否优雅退化，测试里有回归锚点。
- **`None` 与 `0.0` 混淆**（本项目最容易出的 bug 类）：把未测量当成测得 0 会污染 status、delta、
  摆动检测与聚合率。见 §6 的 F3，**已识别、别重复报**，除非你判断触发条件已到。
- **⭐ 标签过度声称（本项目复发四次的失败类型，请专门找这一类）**：字段名声称的语义强于实现。
  已发现并修复的四例是：筛查模式把未施加的防御写进 runtime 与 artifact；artifact 硬编
  `host_task_profile: read_only` 而实际是 write_phase；`authorization_conformant_state_success`
  不检查是否多出未授权事件；correction sidecar 的路径按 `/` 盲切导致 `recorded_value` 静默记成 null。
  **请假定还有第五例没被发现。**
- **⭐ 接缝漏测**：已发生过一次——载荷生成器与分类器各有单测，但两者之间的接线
  （`build_env` 从未接收 family 参数）无测，导致整整两格实验跑了错误的载荷、零结果被误记成有效结论。
  **请专门找「两端各有单测、中间无测」的形状**，不只找单个函数的缺陷。
- **状态机四态一致性**：`pass`、`fail`（需 rationale 与 severity）、`not_applicable`、`inconclusive`
  在各构造点是否处处守住。

---

## 6. 已知延后项（**已识别，别当新发现重复报**）

**上一版的 F1 到 F5，现状**：F1、F2、F4、F5 **已修**；**F3 仍在**——
`src/ithuriel/derive.py:238` 把未测的 `success_rate` 记成 `0.0`（`status` 已正确判 inconclusive，
但该记录字段仍可能污染下游摆动检测）。若你认为触发条件已到，请给场景。

**本轮新增的已知延后项**：

- **G1** `content_hash` 是 64-bit 截断，够做 id、不够客户级证据完整性；进 pilot 前重估。
- **G2** 结构化 `ScopeGap` 与 unassessable 子因：至今无程序化消费者逼出，刻意不建。
- **G3** `measurement_provenance` 与 `adjudication_provenance` 的正交拆分：等三种混合形状出现才拆。
- **G4** 预算上限是 hash 绑定的声明加最大 trial 数，**没有实时 USD 计量**，artifact 已如实标注，
  不冒充成本熔断。
- **G5** 逐 turn 遥测记录 completion 级耗时与 finish reason，**不拆 SDK 内部 retry**；
  已知一批约 121 秒的慢调用无法排除内部重试，如实留作未决。
- **G6** `aug_participant` 攻击族因载荷漏接（已修）尚未取得有效数据，须另轮重跑。
- **G7** instrument qualification（重复运行稳定性）尚未设计，C2 通过不等于探针可用。

**桶 B（架构上明确延后的机器）**：PlanCompiler、RunOrchestrator、ExperimentManager、
完整 Assurance Engine、真实执行后端。**别建议现在建**——纪律是让切片产生的真实摩擦决定它们何时长出来。
可以评「某接缝现在的形状会不会让将来长出桶 B 时很痛」。

---

## 7. 我们最想要的审核输出

按优先级：

1. **设计层**：§4 的十三条张力里，哪一条的语义或取舍**是错的或有漏口**。
   最想听 §4.8（处理后变量做分母）、§4.12（治理边界还有哪些假保证）、§4.13（归属问题）。
2. **代码层**：§5 不变量里**真能被具体输入打破**的，尤其是第五例标签过度声称，
   以及还没被发现的接缝漏测。给出触发输入到错误输出，而非风格意见。
3. **纪律层**：如果你认为 §2 三条纪律在某处**画错了**，明说，但要落到具体字段或模块。

**不需要的**：通用 lint、风格、建议加类型注解或 docstring、建议换框架、补齐 CI-CD。
这是研究阶段的切片验证，不是生产平台。

---

## 8. 统一输出格式（**请务必按此落地**）

请把审核结果**写成仓库里一个文件**，路径固定为 `reports/partner-review-YYYY-MM-DD.md`（用审核当天日期）。
格式是一段 verdict 加一张汇总表，再加每条 finding 一个结构块。

### 8.1 顶部 verdict（不超过五行）

一句话总判断，加三个数：设计层 N 条、代码层 N 条、纪律层 N 条。若你认同某条纪律或某个张力
「设计是对的」，也在这里点名——**确认这里没问题和挑毛病一样有价值**。

### 8.2 汇总表

| ID | 层 | 严重度 | 位置 | 一句话 |
|----|----|--------|------|--------|
| D1 | design | high | §4.8 处理后变量分母 | 确认阶段会引入 X 偏倚 |
| C1 | code | med | `derive.py:238` | sr=None 当 0.0 污染摆动检测 |
| P1 | discipline | — | §4.13 归属 @ scripts/ | 我认为这里画错了，理由… |

层分 `design`、`code`、`discipline`；严重度 `high`、`med`、`low`，纪律层可留空；
代码层必给 `file:line`，设计与纪律层给章节号或模块名。

### 8.3 每条 finding 结构块

```markdown
### C1 — sr=None 被当成测得 0
- 层 / 严重度：code / med
- 位置：src/ithuriel/derive.py:238
- 触发场景（代码层必填，输入到错误输出）：
    输入：某 config 的 aggregate.attack_success_rate 为 null（该臂无有效样本）
    结果：success_rate 记 0.0，下游摆动检测把未测算进 Δ，报出假摆动
- 我的判断：是否 §6 已列项？☑ 是 F3（但我认为触发条件已到，因为…）／☐ 新发现
- 建议（落到具体字段或行为，非「考虑重构」）：sr 为 None 时 success_rate 也置 None，摆动检测跳过该臂
- 挑战纪律？：否
```

两条硬约束：**代码层每条必须给出触发输入到错误输出**，给不出的归到 design 层当设计存疑；
**每条标注是否属于 §6 已知延后项**，若是且你认为该现在修，请给出触发条件已到的场景。
