# ADR 0008 — 控制注册表（桶 B 最薄切片，档 3）

日期：2026-07-12 · 状态：draft（供讨论） · 关联：`0004-first-structured-finding-differentiator-layer.md`（control_id 硬编占位）、`docs/UK_Region_Profile_v0.2.yaml`（GATE-2 plugin→capability）、`docs/ontology_schema.yaml`（finding_schema/scoring）、CLAUDE.md schema 不变量

## 背景
档 1/档 2 都在差异化层的**证据/Finding 半边**。档 3 首次碰**另一半**——「标准→ontology 蒸馏」。关键洞察：控制 `AI-AGENT-PI-01` 在 profile 的 `planned_ai_controls` 里**已全声明**（severity_if_failed: High、standards_refs→OWASP LLM01 + NIST AI RMF、verification.verdict: automatic）；缺的是**读它的码**——`derive.py` 硬编 `CONTROL_ID` 字符串 + 占位 `severity="high"`。档 3 把这条接上，并落地 schema 不变量的牙齿。守 thin-slice + 只读消费、不改 profile/ontology YAML。

## 三个决策（用户拍板 2026-07-12，均取「保守」倾向）
- **D1｜severity 用注册表的 `"High"`（替占位 `"high"`）**。不是大小写洁癖：ontology scoring 的**否决门**是 `∃ fail 且 severity ∈ {High, Critical} → axis not_ready`（`ontology_schema.yaml:95`），字符串精确匹配。若 Finding 带 `"high"`，`"high" ∈ {"High","Critical"}` = False → 高危失败**静默漏过门**。让 Finding 携带的 token = 门测试的 token。代价=改 2 条测试断言。
- **D2｜standards 挂报告层（范式化）、非 Finding 字段**。standards_refs 由 `control_id` 函数决定（bare/defended 两条 Finding 的 standards 恒等），塞 Finding 是传递依赖冗余 + 更新异常。ontology 自己也这么定（finding_schema 有 control_id、无 standards_refs）。→ `AssuranceReport.control`（解析后 ControlDefinition）+ `referenced_standards`（source→StandardEntry）。附带：不进 `finding_id` 身份哈希（保持最小输入）。
- **D3｜只 load+校验+解析，不建 capability/plugin 匹配**。profile 顶部 GATE-2 明确 defer plugin→capability（作者自己分期：PI-01「AI 切片开始时」迁、其余各自切片迁）。我们只 1 控制 1 de-facto 工具（AgentDojo harness）→ 给 1:1 造二部匹配器是纯开销（YAGNI）。`verification.plugin` 当**不透明元数据**消费。

## 落地形状
- `src/ithuriel/models.py`：新 schema —— `StandardRef` / `Verification`（method⊥verdict⊥requires_approval 三正交）/ `ControlDefinition`（`extra="ignore"` 丢 probe_suite/csf2/plugins 等未消费字段）/ `StandardEntry` / **`Registry`**（`model_validator` 强制 **standards_ref.source 不悬空**，违反 → ValueError）。`AssuranceReport` 加 `control` + `referenced_standards`（默认可空 → 不破旧构造）。
- `src/ithuriel/registry.py`（新）：`load_registry()` 读 profile YAML（standards 在 `profile:` 下、controls/planned_ai_controls 顶层，合并）；`default_control()`/`referenced_standards()` 缓存（profile 静态）；路径锚定到文件非 CWD。
- `derive.py` / `derive_session.py`：`severity` ← `control.severity_if_failed`（仅 fail）、`verdict_mode` ← `control.verification.verdict`（=automatic，与 D8 确定性 detector 一致）；`AssuranceReport` 挂 control + referenced_standards（含 not_applicable / summary 路径）。
- `pyproject.toml`：`pyyaml>=6` 显式声明（此前仅 agentdojo transitive）；`uv.lock` 更新。
- 测试 `test_registry.py`（7 条）：真 profile 加载+校验 · **悬空 source raise**（不变量牙齿）· PI-01 解析 severity High/verdict automatic/两 standards · referenced_standards 解析名字/authority · Finding.severity=High · **standards 挂报告层非 Finding** · control 不进 finding_id 哈希。**54/54 全过**。

## 审计闭环（= 卖点落地）
`Finding.control_id=AI-AGENT-PI-01 → control.standards_refs → source ∈ standards 注册表 → StandardEntry{name, authority, url}`。报告现能说清「此 Finding 针对 AI-AGENT-PI-01（Prompt injection…）→ OWASP LLM01 Prompt Injection [OWASP] + NIST AI RMF MEASURE [NIST]」，source 悬空在加载时就被拦。

## 明确延后（不在本切片）
- **capability/plugin 匹配层**（PlanCompiler：控制声明 need⊆能力、插件注册 provides、planner argmin 挑候选 + RoE `policy_decision_matrix` 耦合）——GATE-2，独立更大切片。
- **CoverageLedger / 跨控制 rollup / scoring 落码**（多控制才有意义；本切片单控制单格）。
- **profile→schema 迁移**：`ontology_schema.yaml` 无独立 control_schema 块；本切片用 pydantic 反映 profile 实际结构，未回填 ontology。**不动 profile/ontology YAML**（只读消费；守冻结）。
- 其余 AI 控制（AI-AGENT-SD/TOOL/RAG/…）在 profile 里 severity/probe 稀疏——各自切片开始时补，不现在填。

## 验证
`pytest src/tests/` = **54/54**（47 档1+档2 + 7 档3）。`load_registry()` 真 profile → 10 standards / 25 controls、不变量校验干净；PI-01 → severity High / verdict automatic / OWASP LLM01 + NIST AI RMF MEASURE。
