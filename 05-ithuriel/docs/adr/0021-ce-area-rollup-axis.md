# ADR 0021 — CoverageLedger 增 Cyber Essentials area 轴，报告按 framework 分区呈现

日期：2026-07-18 · 状态：accepted（thin-slice「ce_area 轴 + forcing consumer」；搭档审阅三处 P0 全采纳、三决策已拍板） · 关联：`0014`（CoverageLedger，本 ADR 加第二根 rollup 轴）、`0017`（内部报告 view，本 ADR 的 forcing consumer、`MatrixRow` 泛化在此）、`0019`（AssessmentManifest，本 ADR 的稀疏分母诚实框架复用它）、`docs/UK_Region_Profile_v0.2.yaml`（`ce_area`/`csf2` 一等字段的真相源）

## 背景与 forcing

`CoverageLedger`（`0014`）此前只按 `domain` 轴 rollup。domain（`ai_agent_security` / `network_security` / …）是本项目自造的内部分类，而一个 CE-UK 审核员按 **Cyber Essentials 五个 area**（firewalls / secure_configuration / user_access_control / malware_protection / security_updates）思考覆盖。内部报告 view（`0017`）已经在把覆盖投影给操作者与评估者，但只组织到 domain 轴，读者要按 CE 框架看覆盖时没有对应视图。这是一个真实的消费缺口，不是提前造平台：第二根真实轴已经在数据里，只是没被消费。

forcing consumer 因此是既有的报告 view。让它对审核员可读，就要求 ledger 按 ce_area 出一根 rollup 轴，而这又逼出下面这条真实摩擦链。

## Step 0 — grounding（现状溯源分布）

**四个已评估控制的 (ce_area, severity) 映射**（`ce_area` 与 `domain` 是不同字段，故 CE-area 视图与 domain 视图确会分歧）：

| 控制 | ce_area | domain | severity |
|------|---------|--------|----------|
| AI-AGENT-PI-01 | 无（planned_ai_controls，无此字段） | ai_agent_security | High |
| CE-UK-FW-01 | firewalls | network_security | Medium |
| CE-UK-FW-03 | firewalls | network_security | Medium |
| CE-UK-SU-03 | security_updates | vulnerability_management | Low |

**完整 18 个 CE 控制的 area 分布**：firewalls 4、secure_configuration 4、user_access_control 4、malware_protection 3、security_updates 3。

**字段名区分**：profile 的原字段名是 `csf2`；ontology 的 rollup 轴名是 `csf2_function`，两者不混写。18 个 CE 控制共 40 个 CSF2 membership、12 个不同子类，故 csf2 绝非「顺带白得」。

## Step 1 — 撞出的摩擦

1. **registry 丢字段**：`ce_area` 与 `csf2` 是控制的 profile 一等字段，但 `ControlDefinition` 以 `extra="ignore"` 把它们丢了（docstring 原文「csf2/plugins 等 extra 忽略」）。`ledger.py` 旧 docstring 里「ce_area 需从 standards_refs 解析」是不准的——字段直接在控制上，只是没读进读模型。
2. **report 硬编 domain**：`report._matrix` 遍历 `ledger.axes` 却把每根轴都当 domain，`MatrixRow` 只有 `domain: str` 字段，fidelity / reproducibility / joint caveat 全按 domain 聚合。直接加一根 ce_area 轴会产出字段名和 join 语义都错的行。
3. **CE 轴遇无映射的 AI 控制**：PI-01 没有 ce_area。若照抄 domain 轴的 `o.domain or "unknown"` 兜底，会造出一个名为 `not_mapped`、还带覆盖分的「假 area」，读起来像一个真实的 CE area。

## 决策

1. **只做 ce_area，明确延后 csf2_function。** `ce_area` 是标量（一控制一 area，rollup 干净）；`csf2` 是列表（一控制映射多个 CSF 子类，一控制进多个桶、分母重叠、语义不同）。延后触发条件：出现真实 NIST CSF 报告消费者，并明确决定多归属控制是完整重复计入、分数分摊、还是需 primary mapping 之后，才实现 `csf2_function` 轴。本刀只在本 ADR 的 grounding 表里记录原始 csf2 值，不把它读进 `ControlDefinition`。

2. **ledger 与 report 两处都消费。** 只加 ledger 轴而不接报告，就成了没人读的 rollup（正是纪律要避的反模式），报告 view 就是把它逼出来的 consumer。

3. **稀疏分母靠机器可见的诚实、不靠一句警示。** 4 个控制下 CE-area 轴天然稀疏，验的是**机制**、覆盖数字是 toy。守三条：(一) 用显式 `AssessmentManifest`（`0019`）；(二) 验收 demo 声明全部 18 个 CE 控制、只给 4 个提供 report，让未跑的自然成为 `not_assessed`，覆盖数命名「声明范围内 security 轴覆盖」而非「Firewalls coverage」；(三) 继续披露分母单位是「每份 report 一个 outcome 外加未评估声明控制」，非严格一控制一票（同控制多 target 计多票，`0019` 已知边界）。

## 落地形状（本切片实建）

- **`models.py`**：`ControlDefinition` 增 `ce_area: Optional[str] = None`——**只是不再 `ignore` 一个 profile 里已有的字段，非扩 ontology schema**。`csf2` 仍 `extra` 忽略。
- **`ledger.py`**：`ControlOutcome` 增 `ce_area`（`control_outcome` 与 `_not_assessed_outcomes` 两处回填）。`build_ledger` 生成 domain 与 ce_area 两组 `AxisCoverage`（复用 `_rollup_axis` 通用逻辑、gating/分母/not_assessed 语义全复用）。**R1**：无 ce_area 的控制不进任何 CE-area 覆盖行，改归 `CoverageLedger.unmapped["ce_area"]` 单列——不塞进带覆盖分的轴 key。
- **`report.py`（P0#1 泛化）**：`MatrixRow.domain: str` 泛化为 `axis` + `key`，domain 轴与 ce_area 轴共用同一行结构、domain 不被替换、两轴并存。**R2**：fidelity / reproducibility / caveat / joint 的 Claim×Ledger join 从 per-domain 泛化到 per-(axis, key)——同一控制的 fidelity 同时计入其 domain 行与 ce_area 行，泛化 join 循环、不复制两份。`ControlView` 增 `ce_area` 供下钻，`Report` 增 `ce_area_unmapped`。markdown 分「Domain 视图」与「Cyber Essentials area 视图」两区段，无映射控制显式披露，跨 target 混合分母限制常驻披露。
- **P0#3 的 gating 测试**：4 个真实控制里唯一 High 是 PI-01（无 ce_area），故它们验不了 CE-area gating。用注册表里的 High firewalls 控制 CE-UK-FW-02 合成一个 fail outcome，验证 High fail 落到 firewalls 轴、触发 `not_ready`。**此测试验的是 rollup 路由，不宣称 CE-UK-FW-02 已有真实评估能力**（它尚无 builder）。

## 边界（本切片刻意不建）

- **csf2_function 轴**：见决策 1，等真实 NIST CSF 消费者与多归属计数决策逼出。
- **FRICTION 1 的承载对象**：`0017` 已记 Claim×Ledger 的 fidelity join 今天没有对象承载、靠 view 内 join 化解。第二根真实轴出现后这个摩擦压力变大（join 现在要 per-(axis, key) 算），但本刀仍不建承载对象、只记录加压——升不升对象等它真正卡住某个消费者再定。
- **CE area 视图里 joint_caveats 通常为空**：`0017` 选项 A 的 security⊗utility / joint_verdict caveat 机制是 AI 控制专属（有 bare/defended 分臂）；firewalls、security_updates 这些 area 装的是确定性控制、没有分臂，故其 joint 列基本为空。这是对的、不是漏渲染。
- **跨 target 控制级归约**：同控制多 target 计多 outcome，本刀不做归约、只如实披露（沿 `0019` 边界）。

## 守纪律

未动 `ontology_schema.yaml` / profile / 任何 producer——`ce_area` 是读 profile 已有的一等字段，非扩 schema；新字段全落 pydantic 差异化层，同 ledger/report/claim/manifest 的建法。R3 边界：`MatrixRow.domain → axis+key` 只为 domain 与 ce_area 这两根**已存在**的真实轴服务，不引入 N 轴注册表或配置驱动的轴发现。测试 176→**185**（`test_ledger.py` +5：ce_area 与 domain 分组分歧、四真实控制的 area 覆盖、AI 控制只进 unmapped、High fail 路由 gating、Low fail 不 gate；`test_report.py` +4：两轴并存、AI 控制作 unmapped 而非假 area、声明全 18 使 firewalls 读作 1/4 而非 2/2、跨 target 混合分母披露）。

## 后果与取舍

覆盖现在能按审核员母语（CE area）组织，直接服务「可审计的保证结论」这半卖点、接 UK 治理（NCSC Cyber Essentials）叙事。诚实框定：本刀验证的是「rollup 沿 framework 轴能跑、报告对审核员可读」的**机制**，4 控制下覆盖数字本身是 toy 分母；它不运动「对抗性故障发现」那半卖点。稀疏是真实的评估欠账、不是工具缺陷——demo 里 firewalls 读作 1/4 而非 2/2，正是这层诚实的落点。
