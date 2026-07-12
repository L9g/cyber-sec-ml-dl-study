# ADR 0010 — 搭档审阅第二批：per-arm provenance + 两臂 context 不变量比较（D2+C3）

日期：2026-07-12 · 状态：draft（已实现，测试 63/63） · 关联：`0009-partner-review-honest-gate-closures.md`（第一批，同一审阅）、`reports/partner-review-2026-07-12.md`（C3/D2 源）、`0007-provenance-pinning-protocol-reproducible.md`（provenance 溯源）、`docs/architecture-seams-D8.md` §5（ComparisonSpec fail-closed / MeasurementContext）

## 背景
搭档审阅第二批（面更大、ADR-0009 已延后的两条）：**C3** = `record_response` 幂等写**全局单** `PROV`，bare 首个响应赢 → defended 的 `served_model` 漂移被隐藏；**D2** = `ComparisonSpec.invariants` 是**单份共享快照**，只能声明"两臂应相等"、不能证明成立（seams #5 承诺的 fail-closed 两臂 equality 从未真正执行）。二者是**同一工作项**：单进程一次跑本就产单份 meta，D2 的 equality check 必须先有 C3 的 per-arm provenance 才有东西可比。

## 决策
- **C3｜per-arm provenance**。harness `PROV` 从单 dict 改 `{"bare":…, "defended":…}`（defense 侧本就不同=treatment）；`make_llm(prov)` 闭包绑**本臂** dict → 各臂 `record_response` 独立填 `served_model`/`system_fingerprint`。provider 在两臂间滚动部署时漂移**可见**（此前被首值幂等吞掉）。
- **D2｜两臂 canonical equality → fail-closed**。新纯函数 `provenance.invariant_mismatch(bare, defended)` 比较**非-treatment 不变量**（`served_model`/`system_fingerprint`/`temperature.on_wire`/`corpus`/`libs`/`adaptive_level`/`aggregate_rule_version`）；**treatment 侧（defense/detector）故意排除**——那正是 ComparisonSpec 的 treatment、合法不同。任一漂移 → `provenance_invariant_mismatch=True` + `provenance_mismatch_fields{field:{bare,defended}}`。
- **折进闸门**：`security_delta_assertable = valid ∧ ¬underpowered ∧ ¬attrition_confounded ∧ ¬provenance_invariant_mismatch`；derive 层 belt-and-suspenders 再折一次 + 显式列子因 `context_invariant_mismatch`（新 InvalidityReason）。
- **归档取舍（保守）**：`meta.provenance` = `PROV["bare"]`（共享不变量的 canonical；两臂已验证全等，否则 mismatch）。全等时 bare 无损代表 defended（省重复）；**漂移时** `provenance_mismatch_fields` 归档两臂差异值。→ `build_measurement_context` **零改动**（仍读 flat provenance）、历史 fixture run_root **bit 不变**（已验证 `run:04d4ad41…` 一致）。

## 诚实级联（端到端验证）
构造两臂 `served_model` 漂移（m-2506 vs m-2509）跑 derive：`assertable True→False` → `derive_tradeoff_class` 无 assertable → `tradeoff_class=None` → `joint_verdict=inconclusive`（不再声称 `pass_utility_sacrificed`），`invalidity_reasons=[context_invariant_mismatch]`。**未声明的 treatment 外漂移贯穿作废整个 delta 声明**，正是 seams #5 fail-closed 的落地。

## 守纪律
- 两臂比较逻辑抽成 `provenance.py` **纯函数**（薄适配器层）→ **离线可测**（无 key/无网络，stub response）。harness 只调、不含比较逻辑。
- `invariants` 字段保留（现由两臂 equality **真验证**、非仅声明）；未加 per-arm context hash（YAGNI：布尔 + 差异字段已足够 fail-closed，单进程无并发写需求）。
- **未动 `ontology_schema.yaml`**；新 InvalidityReason 落 pydantic advisory。harness 改的是自有诚实闸门/溯源捕获、非 AgentDojo 扫描逻辑。

## 明确延后（仍未做）
- 一臂**内部**多值 served_model（同臂内 provider 中途滚动）：当前只记首值。reviewer C3 提"记录集合"——留待真实观测到再做（记录-only 决策的延伸）。
- code-review 潜伏项 **F2/F3/F4/F5**（batch 未纳入；F2 与 C2 同族相邻）。下次可单独收。

## 验证
`pytest src/tests/` = **63/63**（60 + 3 新：invariant_mismatch treatment-excluded 正对照 / served_model 漂移检出 / derive 折进 context_invariant_mismatch）。`derive` 对旧 flat-provenance fixture run_root bit 不变；mismatch 场景端到端级联如上。harness `py_compile` 通过（无 API key 不便真跑，per-arm 捕获逻辑经纯函数单测覆盖）。
