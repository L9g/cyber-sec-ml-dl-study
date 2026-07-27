# ADR-0023：派生结构化结论的语义守恒律

状态：Accepted（2026-07-24）
适用范围：差异化层全部 deriver（`derive.py` D8 defense-delta、`derive_c2.py` calendar C2、未来任何
flat artifact → 结构化 `AssuranceReport` 的路径）。

## 背景

把扁平 artifact 升成结构化结论（`Finding.status`/`severity`/`finding_id`/`EvidenceManifest`/`Claim`/
ledger）不是「整理信息」，而是**给信息授予机器可传播的权威**。扁平文本里的 over-claim 通常只是某句话
写得太满；一旦进入结构化层，它会被自动**汇总、展示、比较、甚至触发门禁**——错误从一句话升级成系统行为。

`derive_c2.py`（exfil main C2 → AssuranceReport）落码时的 7 条修订（partner review 2026-07-24）暴露出：
「结构化」这一步是 over-claim 最容易被悄悄放大的地方。本 ADR 把当时的取舍提炼成一条横切**语义守恒律**
与配套纪律，约束所有 deriver。

## 决策：语义守恒律

> **派生后的结构化结论，不得比【预注册规则 ∩ 原始证据 ∩ provenance】三者共同支持的最窄交集更强；
> 遇到不对称、缺失或歧义时，只允许缩小范围（narrow scope），不允许自动补全意义（auto-complete meaning）。**

推论（实现 deriver 时守）：

### 1. 三层分离（Evidence ⊥ Measurement assessment ⊥ Finding）

- **Evidence**：实际观察到什么（如正臂 30/30 未授权发信）。
- **Measurement assessment**：这些观察是否有判别力（C2a/C2b）。
- **Finding**：在测量闸门与范围约束下，控制结论是什么。

即使 measurement assessment 无效（如 C2a fail），**原始证据不得消失**——只是暂不升级成可断言的目标
结论。deriver 须在 `EvidenceManifest` 与 `measurement_context` 里保留 raw 观察，即便 `Finding.status`
降为 `inconclusive`。

### 2. provenance 证来源、不证真实性；三维正交

`receipt` 能证「artifact 来自哪次获批运行、字节是否一致」，**不能证**：oracle 正确、attestation 真实、
mock 代表生产、root cause 成立。故三个维度**必须正交，不得因 receipt 完整而抬高结论置信**：

- **provenance**（来源/字节一致：SHA、request/approval hash & commit、verdict 一致）
- **measurement validity**（判别力：C2a/C2b）
- **target fidelity**（mock ↔ real）

`provenance verified` 不得写入 `measurement_valid`，也不得缩短 `not_covered`（mock 仍在范围外）。

### 3. Finding 是「一次有证据的裁定实例」，Issue 是跨运行聚合对象

三臂全部进 `evidence_refs` 使 `finding_id` 成为**本次裁定的内容地址**：任一臂 trial 变化，裁定依据即变、
`finding_id` **理应变**。这是正确的、不得弱化。

未来若需把多次复跑识别成「同一个长期漏洞」，**不要弱化 `finding_id`**，而应**另建独立的 Issue identity**
（如 `control_id + target family + attack family` 派生）。Finding = 一次有证据的裁定；Issue = 跨运行聚合。
**当前无真实消费需求 → 推迟建（thin-slice），但概念上别混。**

### 4. 负向契约与正向契约同为一等公民

结构化测试不能只查「字段是否存在」（`c2_pass → fail Finding`），**还须钉「禁止产生什么」**——这类负向
契约比存在性测试更能挡未来回归：

- C2b fail **不得**变成「目标不易感」
- receipt verified **不得**变成「独立审计」
- severity=High **不得**被描述成统计结果（是注册表政策级继承）
- P1/P3 **不得**被描述成已完成因果证明（是 advisory 机理归因）
- mock **不得**被渲染成真实 Gmail/Google
- measurement_valid **不得**被渲染成 instrument qualified（是 run-local control discrimination validity）

## 后果

- 所有 deriver 的测试套件**必须包含负向契约测试**（见 `test_derive_c2.py`）。
- 新 deriver 遇不对称/缺失/歧义**默认缩范围**、不补全——宁可 `inconclusive` + scope 注记，不可静默升级。
- 本 ADR 不新增 pydantic 字段、不改 ontology schema（守冻结）；它是**行为纪律**，由 deriver 实现与
  测试兑现，非新数据结构。
- Issue identity、cross-run 聚合明确**推迟**（桶 B），待真实消费需求逼出。

## 关联

`derive_c2.py`（首个据此实现的 deriver）、[[project-ithuriel-probe-authoring-trial]]（exfil C2 pass 全链条）、
ADR-0022（授权门 = provenance 半边）、seams #6/#8（内容寻址 + scope）。
