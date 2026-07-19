# ADR 0017 — 内部试用报告 view：coverage×warrant/fidelity 二维矩阵 + 选项 A（security 轴覆盖 + 联合裁定警示）

日期：2026-07-14 · 状态：accepted（用户拍板选项 A；安全哲学立场经一轮深追问共识） · 关联：`0016`（Claim Deriver / confidence_basis，本 view 的直接消费对象）、`0014`（CoverageLedger；本 view 是它当年标的「第 4 个消费场景」）、`0005`（bare ASR=0→inconclusive、D2 测量上下文）、`docs/architecture-seams-D8.md`（seams #4/#6/#8）、`docs/DESIGN.md`「附：检测到注入就中止任务算不算安全」（本 ADR 决策的哲学依据）

## 背景与 forcing

试用里程碑定案（内部试用可用的「有边界报告 view」）后动手：让 `0016` 落的 Claim 层与 `0014` 的 CoverageLedger **第一次被一个真实报告消费者读出来**，对一批真实 report（AI 会话 + 确定性切片）产出可读、诚实、带边界的报告，答操作者三问「能说什么 / 凭什么 / 不能说什么」。

**为何现在建这个 consumer 不算「自导自演逼字段」**：它回答一个真实用户问题（一份报告能说什么、凭什么、不能说什么），逼出 schema 摩擦是副产品而非目的（搭档 2026-07-14 路线图的纠正）。**护栏**：纯函数、只投影不重算；**不建** Engine/ExperimentManager/PlanCompiler；**不产单一置信度档/总分**（会把 fixture 的 det/bit 误读成对真实目标高信心 = 重造绿）；呈现为 **coverage × warrant/fidelity 二维矩阵**，非总分。

## Step 0 grounding（不写码）

摸遍 `models.py` / `claim.py` / `ledger.py` 真实字段 + AI/config 报告结构，落「三问→源字段」映射表，坐实 **G1 无缺字段**：三问全能从现有对象答出，是「组装」非「加 schema」。**实操发现**：选项 A 多目标 raw 单文件覆盖式、gitignored → 验收 demo 的 AI 侧改用**已冻结入库 fixture**（`d8_run_detector.json` 等）以满足 G5 离线可复现。

## Step 1 撞出的两处摩擦

| # | 摩擦 | 处置 |
|---|---|---|
| **#1** | 矩阵要 coverage×fidelity，但**无对象把二者配对**：coverage 在 `CoverageLedger.axes`，fidelity 埋在每条 `Claim.confidence_basis`。 | **view 内 re-walk reports、按 domain 归并 Claim 的 fidelity/reproducibility 再挂回 ledger 轴**（Claim×Ledger 组合）。确认是**组装 join、非 schema 缺口**；单位对齐到「控制」（每 report 贡献一个计数，与 coverage 分母同口径，回归测试 `test_friction1_...` 守）。**不升成对象**（无第二消费者逼出）。 |
| **#2** | ledger 取 defended 单臂 `Finding.status=pass`，但 `ComparisonSpec.joint_verdict` 可能 `utility_failed`（防御靠「检到注入即 abort」牺牲可用性）→ 顶线覆盖率单读会误导。 | = `0014` 明确留给「第 4 个消费场景」定的语义，现在到了。见下「选项 A」。 |

## 选项 A（用户拍板）+ 安全哲学依据

摩擦 #2 的三个候选处置：

- **选项 B（报告降级：`utility_failed` 不算 passed）**——**否决**。它偷偷替部署方做了「可用性丢失 = 不安全」的价值判断，且报告层与 ledger 会各算各的覆盖率（两套口径）。
- **选项 C（只在控制层摊、矩阵不动）**——**否决**。顶线覆盖率单读仍误导，等于默许「系统安全」的过度声称，未堵 G3。
- **选项 A（security 轴覆盖照实 + 联合裁定警示常驻）**——**采纳**，且经安全哲学论证是**唯一站得住**的。

**哲学依据**（详见 `docs/DESIGN.md`「附」节）：「检测到注入就中止任务算不算安全」不是一个能一个字回答的属性。中止在完整性与无害轴上是安全（拒绝了注入指令、未做坏事），在可用性轴上是不安全（攻击者用一段注入字符串就令其拒绝服务）；用 RAMS 语言，这是 **fail-safe 非 fail-operational**，够不够安全取决于「失去功能本身算不算危害」= **场景相关的风险判断、非技术事实**。因此**保证工具不该替部署方把它压成一个字**——压成标量本身就是最大的过度声称。选项 A 正是这条立场的落点：security 轴覆盖照实报（那是事实），联合裁定警示常驻其旁（让数字读不成「系统安全」），取舍摊开、决定权留给场景。

## 落地形状

- **`src/ithuriel/report.py`（新）= presentation DTO，非 ontology schema 扩展**（只重排既有字段，不给 Finding/Claim 加语义字段，守「先撞摩擦、不提前加字段」）。
  - `render_report(list[AssuranceReport]) -> Report`：纯函数，复用 `derive_claims` + `build_ledger`。空输入 → 空报告（不静默产正向结论）。
  - 视图模型：`WarrantView`（confidence_basis 全维 + 统计支撑，绝不折成一档）、`ControlView`（三问切片，security_statuses 与 joint_verdict 并列呈现——摩擦 #2 的控制层落点）、`MatrixRow`（coverage/not_ready 来自 ledger；`fidelity_mix`/`reproducibility_mix` 来自 Claim join；**`joint_caveats`** = 选项 A 的核心，记「被算作 passed 但 joint≠acceptable」的控制计数）、`Report`（**刻意无 overall_score/任何标量 score 字段**，G2）。
  - `to_json` / `to_markdown`：只格式化、不重算；渲染层唯一「加工」是把 coverage 标注成「安全轴覆盖」并常驻 ⚠ 警示句。
- **零改动**：未动 `ontology_schema.yaml` / profile / 任何 producer（derive/config_inspection/port_scan/attestation/ledger/claim/models 均未改）。coverage 数由 ledger 算、报告不重算。

## G6：被逼出的 schema 摩擦，如实记录（消费者驱动、非抢跑）

- **结构化 `ScopeGap`（第五次字符串承载）**——报告 view 把 `ScopeStatement.not_covered`（`list[str]`）原样渲染成「覆盖缺口」，**未按类别程序化分组**，故**未逼到必须结构化**。**暂不收**（`0016` 决策③一致）；等真有 consumer 需程序化读 gap 结构再升 typed。
- **`unassessable` 双-None（潜伏未触发）**——`Claim.assessable=False` 的 reason 是自由串，分不清「历史未回填」vs「本就无裁定事件」；但 demo 数据 Step 4 已全回填 → 全 assessable，本 view 未被逼区分。**暂不收**（区分需 producer 侧加信号、无 consumer 逼此）。

## 验收（试用里程碑六门）

demo = AI PI-01 冻结 fixture + config-FW03 两主机，跨两裁定形状。**G1** 三问齐全 · **G2** 无标量总分、fidelity 显式（`test_g2_*`）· **G3** utility_failed 常驻警示 + 不可评估如实穿透（`test_option_a_*` / `test_g3_*`）· **G4** 两形状 + 每 warrant 带保真度/非合规声明 · **G5** bit 可复现 + 审计闭环 standards 在呈现物（`test_g5_*`）· **G6** 见上，如实标未逼出。测试 150→**160**（`test_report.py` +10）。

## 待办

Step 2/3/4 已全落（渲染器 / demo / 测试+本 ADR）。**下一档**（带外部风险 pilot，非本里程碑）才需要：seeded tenant + reset oracle、`content_hash` 客户级证据完整性升级、ApprovalGrant、外部 claim contract。**英文版 DESIGN.en.md 的「附」节镜像**待补（本轮只更中文版）。

## 更新（2026-07-14，附注不改上文决策过程）

- 上「待办」里的 **DESIGN.en.md「附」节镜像已完成**（commit `51e6024`，Economist 风格、英式拼写）。此条关闭。
- `src/ithuriel/report.py` 顶部 docstring 曾标 `ADR-0017 pending`，本 ADR 已 accepted 并合入 main（PR #11），docstring 同步为 accepted。
- **搭档 milestone 审阅回来了**（审 0013–0017 + 复跑 160 passed），认定 0013–0017 是**已实现的决策记录、非未来计划**，真正下一步应从内部架构验证转向「有界用户试用」。审出四个 P0 落在本 ADR 与 `0014`：
  ①覆盖率分母来自「传入的 report 集合」而非「声明的控制全集」，可被输入选择做高（需 `AssessmentManifest` 供分母）；
  ②`not_ready=False ≠ ready`（Medium fail / 50% gap / 全 inconclusive 都 not_ready=False，字段名诱导误读）；
  ③本报告 `ControlView` **丢了 target 身份 + Finding.rationale/结构化 advisory**——两台 FW-03 主机渲染成同名段落无法区分，且 `0015`「surface 不 override」的冲突警示（attestation.py 记的 conformant-但缺-justification）到最终 view 丢失；
  ④`joint_verdict` **未评估**（无 comparison 的确定性检查）在矩阵显示空白 `—`，易被读成「无问题」，应显式区分 not_evaluated/not_applicable。
  这四项连同结构化 `ScopeGap`（第五次字符串承载、被 `AssessmentManifest` 消费者逼出）+ provenance 再正交（`measurement_provenance ⊥ adjudication_provenance`，记为 forcing trigger、暂不重构）留下一里程碑处置，详见搭档审阅与后续 ADR。

## 更新（2026-07-14，呈现诚实三件落地：②③④ 关闭，① 延后）

搭档四个 P0 里 **②③④ 是纯呈现层的诚实修复**（都在 `report.py` view 内，重排既有字段、零 schema 改动），先落；**① 需新对象 `AssessmentManifest`**（覆盖率分母来自声明控制全集而非传入 report 集合）属结构性改动，留下一里程碑。三件均在 `report.py` 落地并各带回归测试（`test_report.py` 160→**169**）：

- **② `not_ready=False ≠ ready`**（**不造 readiness 档**）：`MatrixRow` 新增派生 `gate_status`（`blocked` / `incomplete` / `all_applicable_passed` / `no_applicable_controls`）+ `gate_detail`，保留 ledger 原值 `not_ready` 作审计。**刻意不叫也不产「readiness」判读**——造一个正向就绪档本身就是过度声称；`gate_status` 只陈述门禁/缺口事实。markdown「门禁 / 缺口」列取代旧「门禁」列：Medium fail / 部分覆盖 / 全 inconclusive 一律显式 `incomplete` 并标未 pass 数，**「无 High/Critical 门禁」不再渲染成裸「—」被读成清白**；即便全适用 pass 也只陈述事实并显式否定「系统 ready」，不越权替部署方下整体就绪判断。测试 `test_gate_status_*` / `test_no_manufactured_readiness_verdict_field` / `test_markdown_never_renders_absence_of_gate_as_clear`。
- **③ target 身份 + rationale + 结构化 advisory 不丢**：`ControlView` 新增 `target_label`（host_id / model + defense 变体）+ `targets`（各臂原始 target_ref）——**两台 FW-03 主机不再折成同名段落**（`@ host-01` / `@ host-02`）；`WarrantView` 新增 `rationale`（fail 为何失败）+ `advisory`（root_causes P1–P6），**ADR-0015「reviewer conformant 但登记缺 justification」的冲突警示（藏在 rationale 里）随之穿透到最终 view**。测试 `test_two_hosts_are_distinguishable` / `test_fail_rationale_and_advisory_surface` / `test_attestation_0015_conflict_note_survives_to_view`。
- **④ `joint_verdict` 未评估 ≠ 无问题**：`MatrixRow` / `ControlView` 新增 `joint_evaluated`（本轴/本控制是否做过 bare/defended 联合裁定）。matrix 联合裁定列显式区分 `未评估（无防御实验）` 与 `✔ 已评估无分歧`，控制详情标 `联合裁定 未评估（无 bare/defended 对比）`——**确定性域不再留裸「—」被读成无问题**。测试 `test_deterministic_domain_marks_joint_not_evaluated` / `test_markdown_distinguishes_not_evaluated_from_no_disagreement`。

**守纪律**：仍是 presentation DTO——只在 view 内重排/派生既有字段，未动 `ontology_schema.yaml` / profile / 任何 producer（derive/config_inspection/attestation/ledger/claim/models 均未改）。新字段名无 `overall/total/score/grade/rating`（`test_g2_*` 硬断言仍过）。**① `AssessmentManifest`（分母对象）+ 结构化 `ScopeGap` + provenance 再正交仍留下一里程碑。**
