# Ithuriel（项目五）· 外部审核说明 —— 给搭档的 review agent

日期：2026-07-12 · 供第三方 agent 冷启动审核**设计思路**与**代码**用

> 这份文档是**自足**的：读它的 agent 没有我们的对话历史 / auto-memory。它给出审核所需的
> 最小充分上下文 + **审核边界**（这个项目有两条硬纪律，不内化就会给出与方向冲突的建议）。
> 冲突时，权威顺序：本文 §2 纪律 > `docs/architecture-seams-D8.md`（编码接缝契约）> 各 ADR > 代码注释。

---

## 1. 项目一句话

**可审计、可复现的保证结论 + 对陌生系统的对抗性故障发现。**
卖点**不是**再造一个安全扫描平台，而是把「借来的探测/攻击/防御工具」的原始输出，归一化成
**带溯源、带统计功效判定、带范围声明的结构化保证结论**。

当前落地范围（D8 第一条最薄端到端切片）：对一个 LLM agent target 跑 AgentDojo 的
prompt-injection 场景，bare vs defended 对照，产出结构化 `AssuranceReport` / `SessionReport`。

---

## 2. 两条最重要的构建纪律（审核前必须内化）

审核这个项目时，**很多"标准最佳实践"建议是反纪律的**。以下两条决定哪些建议有用、哪些会把项目带偏。

### 2.1 两层模型：Base=借，Differentiator=建

- **Base（借，不自建）**：执行器 / IPC / 调度 / 扫描探测工具（AgentDojo、nuclei、garak、PyRIT、
  LLM SDK）/ 已发表的防御。
- **Differentiator（建）**：**只有** (1) 标准→ontology 蒸馏，(2) 证据 / Finding / 保证层。
- **插件是薄适配器**：调现成工具、把输出归一化进 Evidence schema，**绝不重写扫描逻辑**；缺工具的
  控制留 `not_applicable` / 占位。
- **审核含义**：
  - ✅ 请审"建"的半边（`src/ithuriel/**`、Finding/证据/比较/注册表的语义与不变量）。
  - ❌ 不要建议"重写/增强扫描器、自研防御、把 AgentDojo 换成自建 harness、建平台化功能"。
    `scripts/run_bare_vs_defended.py` 是**借来的 AgentDojo runner 的薄封装**，按此定位审，不按
    "生产级扫描引擎"审。
  - 护栏：**minimal base ≠ toy base**——底座借到"领域内行点头"为止，不多建一分。

### 2.2 thin-slice：先跑最薄切片、据真实摩擦定 schema

- 字段**只在**"不可逆形状 + advisory-only"时才提前定；否则等真实摩擦逼出来再加。"便宜"不是加字段的理由。
- `docs/ontology_schema.yaml`（v0.6）是**冻结**的权威 schema。差异化层的 pydantic 模型
  （`src/ithuriel/models.py`）**只取** schema required 字段 + 真跑数据真用到的字段；新枚举先落
  pydantic **advisory**，**不冒进改 ontology_schema.yaml**。
- **审核含义**：
  - ❌ 不要建议"照 OWASP / NIST / 论文补齐字段"、"把 parked 字段（threat_model / fidelity_gap /
    llm_judge / remediation …）现在加上"。这些是**刻意延后**，不是遗漏。
  - ✅ 可以质疑：某个**已加**的字段是否真被真实数据逼出来、形状是否真不可逆、是否本可延后。

> 这两条纪律本身也欢迎被 challenge——但请**明说你在挑战纪律**，而不是默认它不存在。

---

## 3. 仓库地图 + 建议阅读顺序

`src/` 是"建"的半边（审核主战场，~1660 行）。`scripts/` 是"借"的半边（薄封装）。`docs/` 是设计权威。

| 顺序 | 路径 | 作用 | 审核优先级 |
|---|---|---|---|
| 1 | `docs/architecture-seams-D8.md` | **编码接缝契约（设计权威）**：桶 A 8 条现在定的不变量 + 桶 B 明确延后的机器 | 先读，理解设计意图 |
| 2 | `src/ithuriel/models.py` (263) | pydantic schema：Finding / ComparisonSpec / ScopeStatement / EvidenceManifest / Registry / AssuranceReport / SessionReport + 各 advisory 枚举 | ⭐ 高 |
| 3 | `src/ithuriel/derive.py` (328) | flat run JSON → `AssuranceReport`（纯函数）。含 `derive_tradeoff_class` 反推逻辑、内容寻址 manifest、cfg-aware status | ⭐ 高 |
| 4 | `src/ithuriel/derive_session.py` (330) | 多跑 → `SessionReport`：混合保真度、invalid 子因、跨条件横向观察（只聚合不重算） | ⭐ 高 |
| 5 | `src/ithuriel/provenance.py` (65) | 溯源钉死（served model snapshot 治 `-latest` 别名坑），薄适配器 | 中 |
| 6 | `src/ithuriel/registry.py` (52) + profile | 从 `docs/UK_Region_Profile_v0.2.yaml` 只读加载控制/标准注册表，强制"standards_ref.source 不悬空" | 中 |
| 7 | `src/tests/**` (619) | 55 个测试（代码契约级，确定性）。看断言就能反推设计意图 | 中 |
| 8 | `scripts/run_bare_vs_defended.py` (296) | **借来的** AgentDojo runner 封装（provider 无关、Wilson CI、underpowered gate、429 退避）。按"薄适配器"审 | 低（非自建逻辑） |
| — | `docs/adr/0001..0008` | 8 个决策记录（**每个字段/决策的"为什么"都在这里**，代码注释里 `见 ADR-000x` 指向它们） | 按需回查 |

证据/数据：`results/d8_bare_vs_defended.json`（单文件覆盖式，只留最后一跑）、`results/experiments.csv`
（逻辑键 upsert）、`src/tests/fixtures/**`（冻结的真跑快照，reviewer 可用它们复现 deriver 行为）。

**跑测试**：`.venv/bin/python -m pytest src/tests/ -q` → 应 `55 passed`。

---

## 4. 设计审核：我们想被 challenge 的地方

这些是项目独特的设计张力，比"通用架构评审"更值得搭档的判断力。

1. **`measurement_valid` ⊥ `underpowered`（方法学核心）**。harness 分两道正交闸门：
   `measurement_valid`（有正对照、target 确实可被注入 = bare ASR>0）与 `underpowered`
   （bare/defended 的 Wilson CI 重叠 → delta 分辨不出）。**只有 `valid ∧ ¬underpowered` 才断言
   defense delta**，否则 fail-closed 不声称。这是项目的诚实性支柱。请审：这个二分是否真正交？
   fail-closed 有没有漏口？（见 ADR-0002/0003、seams §7 附）
2. **`bare ASR=0 → inconclusive 而非 pass`**（ADR-0005 D2）。正对照缺失 ≠ 目标安全。这个语义决策
   贯穿 `derive.build_finding` 与 `derive_session._summary_status`。请审一致性。
3. **security⊗utility 不可分对**。防御把 ASR 压到 0 但 under-attack utility 也归零（检到即 abort），
   **不是纯 security 满分**。`TradeoffClass` 三值 + 正交 `TradeoffUnclassified` 就是为编码这点。
   请审 `derive_tradeoff_class`（derive.py:33-60）的分类逻辑与阈值（τ=0.5 / U_FLOOR=0.1 /
   BLOCK_UTIL=0.5，锚死档 1 五跑、标注"后续按实验修正"）。**`blocks_preserving_utility` 当前未观测**
   （AgentDojo 只有 abort 型防御），定义留位、如实标 gap——这个"为观测不到的类留定义不留 fixture"的
   取舍值得评。（ADR-0006）
4. **内容寻址 & 哈希稳定性作为契约**。`finding_id` / `run_root` 由裁定性字段内容派生
   （models.py:97-115、derive.py:`build_target_ref`）。**不变量：任何新字段必须带默认值，才不进哈希、
   不破既有 id**（每个 ADR 都复核这条）。请审：哪些字段进了哈希、进得对不对；重构会不会悄悄改 id。
5. **单一 treatment 的 fail-closed 比较**（seams #5）。`ComparisonSpec` 声明 `treatment_field=defense_hash`，
   其余 invariant **默认全等、任何未声明差异 → delta invalid**。请审 `build_comparison` 的 `invariants`
   构造是否真能挡住"未声明漂移造出假 delta"。
6. **溯源的诚实退化**（档 2）。`served_model = response.model`（治滚动别名）；`temperature` 记
   `{config_intent, on_wire}`（AgentDojo 把 0.0 当"省略"发）；`seed` 只记录不注入；历史无 provenance
   的跑**优雅退化**为全 absent 而非崩溃。请审 `_absent_seams5` 的 gap 计算是否如实、有没有"把没测的当测了"。
7. **注册表作为 schema 不变量的牙齿**（档 3）。`Registry` 加载时强制 `standards_ref.source` 不悬空
   （models.py:220-228），审计闭环 = Finding.control_id → standards_refs → source ∈ 注册表。请审这个
   闭环是否真闭、`extra="ignore"` 会不会吞掉本该报错的畸形 profile。

---

## 5. 代码审核：请重点看的不变量

- **纯函数边界**：`derive.py` / `derive_session.py` 应"读 dict → emit dict、无副作用"（只有 `main` 落盘）。
  请查有没有隐藏副作用 / 全局状态。
- **哈希稳定性**（同 §4.4）：新字段默认值、`canonical()` 的 sort_keys/紧凑分隔/`ensure_ascii=False`
  是否真给出确定性字节。
- **向后兼容**：历史 fixture（无 provenance / 无某些聚合字段）能否优雅退化。测试里有回归锚点。
- **`None` vs `0.0` 混淆**（这是本项目最容易出的 bug 类）：把"未测量"当成"测得 0"会污染
  status/delta/横向摆动检测。**见 §6 已知延后项 F2/F3——已识别，别重复报，除非你判断触发条件已到。**
- **状态机四态一致性**：`pass / fail(需 rationale+severity) / not_applicable / inconclusive` 的
  校验（models.py:97-115）与各构造点是否处处守住。

---

## 6. 已知延后项（**已识别，别当新发现重复报**）

本地 `/code-review high`（2026-07-12，覆盖差异化层全 diff）报了 5 项，F1 已修（commit `6489493`：
`build_finding` bare 分支改成 status-aware + `bare ASR=0→inconclusive`）。F2–F5 **判为潜伏、非当前触发**，
刻意延后：

- **F2** `derive_session.py` ~L205：`utility_delta` 只守 bare 的 `None`，defended 用 `or 0.0` 把
  "未测" 当 0.0 → 可能造出 `-bare_util` 假 delta。
- **F3** `derive.py` ~L183：`sr is None` 时 `success_rate` 记 `0.0`（未测当测得 0）→ 可能污染
  `cross_condition_notes` 的摆动检测。
- **F4** `scripts/run_bare_vs_defended.py` ~L158：`temperature_intent` 硬编 `0.0`，未读 `llm.temperature`。
- **F5** `derive.py:62`：`SEAMS5_EXPECTED` 常量排版（E305 / 远离顶部常量区）。

> 如果你**认为哪个触发条件其实已经到了**（例如横向铺 target 引入 bare ASR=0 的鲁棒模型会激活 F3
> 路径），请明说并给出场景——这正是有价值的审核输出。但请把它标成"我认为 Fx 该现在修，因为…"，
> 而不是当成未知缺陷报。

**桶 B（架构上明确延后的机器，seams 已声明，不是缺失）**：PlanCompiler / RunOrchestrator /
CoverageLedger / ExperimentManager / Claim-Assurance Engine / 真实执行后端。**别建议现在建它们**——
纪律是"让切片产生的真实摩擦决定它们何时长出来"。可以评"某接缝现在的形状会不会让将来长出桶 B 时很痛"。

---

## 7. 我们最想要的审核输出

按优先级：
1. **设计层**：§2 两条纪律、§4 七个张力里，哪个的**语义/取舍是错的或有漏口**（尤其 §4.1 的
   valid⊥underpowered 二分、§4.3 的 tradeoff 阈值与"未观测类留定义"取舍）。
2. **代码层**：§5 不变量里**真能被具体输入打破**的（给出触发输入 → 错误输出，而非风格意见）。
3. **纪律层**：如果你认为 §2 的"借 vs 建"边界或 schema 冻结在某处**画错了**，明说——但要落到具体字段/模块。

**不需要的**：通用 lint / 风格 / "建议加类型注解或 docstring" / "考虑用框架 X" / "补齐 CI-CD"——
这是研究阶段的最薄切片，不是生产平台。

---

## 8. 统一输出格式（**请务必按此落地**）

搭档在 VM 里直接读仓库；请把审核结果**写成仓库里一个文件**，路径固定：

```
reports/partner-review-2026-07-12.md      （日期用审核当天）
```

这样我这边直接读文件接结果，不必粘贴。格式 = **一段 verdict + 一张汇总表 + 每条 finding 一个结构块**。

### 8.1 顶部 verdict（≤5 行）

一句话总判断 + 三个数：`设计层 N 条 / 代码层 N 条 / 纪律层 N 条`。若你认同某条 §2 纪律或
§4 张力"设计是对的"，也在这里明确点名——**确认"这里没问题"和挑毛病一样有价值**。

### 8.2 汇总表

| ID | 层 | 严重度 | 位置 | 一句话 |
|----|----|--------|------|--------|
| D1 | design | high | §4.1 valid⊥underpowered | 二分在 X 情形有漏口 |
| C1 | code | med | `derive.py:183` | sr=None 当 0.0 污染摆动检测 |
| P1 | discipline | — | 借vs建边界 @ registry.py | 我认为这里画错了，理由… |

- **层**：`design`（§4 张力/语义取舍）/ `code`（§5 可被输入打破的 bug）/ `discipline`（§2 纪律边界画错）。
- **严重度**：`high / med / low`；纪律层可留 `—`。
- **位置**：代码层必给 `file:line`；设计/纪律层给"§编号"或"模块名 @ 概念"。

### 8.3 每条 finding 结构块

每条一个块，字段固定（缺的填 `n/a`）：

```markdown
### C1 — sr=None 被当成测得 0
- 层 / 严重度：code / med
- 位置：src/ithuriel/derive.py:183
- 触发场景（代码层必填，输入→错误输出）：
    输入：某 config 的 aggregate.attack_success_rate = null（该臂未产生有效样本）
    结果：success_rate 记 0.0 → cross_condition_notes 把"未测"算进摆动 Δ，报出假摆动
- 我的判断：这是否 §6 已列的 F3？☑ 是（但我认为触发条件已到，因为…）／☐ 新发现
- 建议（要落到具体字段/行为，非"考虑重构"）：sr=None 时 success_rate 也置 None，摆动检测跳过该臂
- 挑战纪律？：否
```

两条硬约束，**请遵守**：
1. **代码层每条必须给"触发输入 → 错误输出"**。给不出具体触发场景的，归到 design 层当"设计存疑"，
   别混进 code 层当 bug。
2. **每条标注是否属于 §6 已知延后项（F2–F5）**。若是、且你认为该现在修，请给"触发条件已到"的场景；
   若只是复述我们已识别的，可省略（我已知道）。

（如果你的 agent 更方便输出 JSON，用同样的字段名给一个 `reports/partner-review-2026-07-12.json`
数组也行，二选一即可——Markdown 优先。）
