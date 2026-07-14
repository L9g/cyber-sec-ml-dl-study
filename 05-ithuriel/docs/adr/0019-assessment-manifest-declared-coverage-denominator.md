# ADR 0019 — AssessmentManifest：覆盖率分母对「声明控制集」算，防输入选择做高

日期：2026-07-14 · 状态：accepted（搭档 milestone 审阅 P0 #1 的落地；分母来源经用户拍板=显式承诺清单） · 关联：`0014`（CoverageLedger，本 ADR 直接改其分母语义）、`0017`（内部报告 view，消费本层的 not_assessed）、`docs/architecture-seams-D8.md` #8（scope/gap 声明）、`docs/UK_Region_Profile_v0.2.yaml`（声明控制的注册真相源）

## 背景与 forcing

搭档 milestone 审阅四个 P0 里，`0017` 已落的呈现诚实三件（②③④）之外，剩下的 #1 是**分母问题**：`CoverageLedger` 的覆盖率分母来自**传入的 report 集合**，而非一份声明的控制全集。这意味着覆盖率可以被输入选择做高——少传一份 report，那个控制就从分母里消失，剩下的比值虚高。用 demo 坐实：network_security 只传两份 FW-03 report（host-01 pass、host-02 fail）时覆盖率是 1/2 = 0.5，但 profile 在这个域声明了 FW-01/02/03/04 四个控制，FW-01/02/04 从没被评估、却在覆盖率里完全隐形。

一个卖点是「可审计、带边界的保证结论」的工具，最不该让「测了多少」这个数字随「这次挑了哪几份 report」浮动。需要一个在结果之前就承诺、且钉死可审计的分母。

## 决策

引入 `AssessmentManifest`：评估之前承诺的**声明控制集**，当覆盖率分母。声明了却整条无 report 的控制归为新的 rollup 态 `not_assessed`（进分母、非 pass），不再隐形；覆盖率因此对固定声明算，删 report 抬不高它。

分母来源经用户拍板是**显式承诺清单**（而非「整个 profile 自动当分母」）：operator 提交一份 control（可选带 target）清单，`manifest_hash` 内容寻址把这份声明钉死在结果之前，事后调分母会改变 hash、暴露。选「显式清单」而非「整个 profile」，是因为后者会把二十多个当前无插件、只能 `unsupported` 的控制全灌进报告、淹没信号；而显式清单让分母是一份**有意的、可审计的评估范围声明**，恰是保证叙事想要的东西。

## 落地形状（本切片实建）

- **`src/ithuriel/manifest.py`（新，纯 pydantic 差异化层）**：`DeclaredControl{control_id, targets?}` + `AssessmentManifest{profile_id, declared, manifest_hash}`。validator 强制声明非空、control_id 不重复，并派生稳定 `manifest_hash`（声明集相同则同 hash，与顺序无关；改分母则改 hash）。
- **`ledger.py`**：`RollupStatus` 增 `not_assessed`（与 `gap` 区分——gap 是「report 在、0 Finding」，not_assessed 是「连 report 都没有」）。`build_ledger(reports, manifest=None, ...)` 在 manifest 在时，为声明了却无 report 的控制补 `not_assessed` outcome（domain/severity 从 registry 解析）。`AxisCoverage` 增 `not_assessed_controls`，如实点名本域未评估的控制。**声明的控制必须在 registry 注册**，未注册则 fail-closed 报错（echo `Registry` 的 standards_ref.source 不悬空不变量）。
- **`report.py`**：`render_report(reports, ..., manifest=None)` 把 manifest 串进矩阵；`MatrixRow` 与 `Report` 承载 `not_assessed_controls`、`declared_controls`、`undeclared_assessed`、`manifest_hash`。markdown 顶部披露对照的清单与未评估控制；矩阵单元点名本域未评估控制。**无 manifest 时如实警示**：覆盖率分母仅含已评估控制、可被输入选择做高——把这条局限本身摊在报告上，而不是假装 0.5 是对某声明的覆盖。

## 边界（本切片刻意不建）

- **target 级部分评估**（声明三台主机却只跑两台 → 那台算 not_assessed）需要 report↔target 匹配机器；守「一个切片一个新变量」，本切片只在**控制级**播种分母（某声明控制有 ≥1 report 即算已评估）。`DeclaredControl.targets` 留形不留逻辑，等真实摩擦逼出 target 级核对再接。
- **控制级跨 target rollup**（FW-03 在两台主机上一 pass 一 fail 该折成一个什么控制级状态）暂不做；沿用 ledger 既有的「每份 report 一个 outcome」单位，not_assessed 按未报告的声明控制补一个。分母因此是「每 outcome + 每未评估声明控制」的混合单位，够堵住输入选择做高这个被点名的洞；纯控制级 rollup 留作后续，如实记于此。
- **结构化 `ScopeGap`（第五次字符串承载）不在本切片升 typed**（用户拍板延后）。层次区分是关键：manifest 的 `not_assessed` 是**跨报告**的、已作 ledger 的 typed rollup 态，并不牵动 `ScopeStatement.not_covered` 这份**单报告内**的字符串。当前没有任何消费者按 gap 子类程序化分支（报告只把 not_covered 渲染成 bullet），故 typed 化的摩擦尚未出现。若接报告视图时发现需 string-parse not_covered 来分组 gap，那才是真摩擦、届时再 typed。与 `0016`/`0017` 决策③一致。

## 守纪律

未动 `ontology_schema.yaml` / profile / 任何 producer（derive/config_inspection/attestation/derive_session 均未改）——新对象与新枚举全落 pydantic 差异化层，同 ledger/report/claim 的建法。测试 169→**176**（`test_report.py` +7：反输入选择、not_assessed 点名、越界评估、无清单警示、悬空声明 fail-closed、hash 钉死、空/重复声明拒绝）。

## 后果与取舍

覆盖率从「碰巧传了什么」变成「声明要测什么」，是保证结论可审计性的实质一步；未评估的控制从隐形变成分母里的具名条目。代价是报告的顶线数字会显著变低（demo 的 network_security 从 0.5 掉到 0.2），但这正是诚实——低数字反映的是真实的评估欠账，不是工具变差。分母的混合单位与 target 级核对是已知、已记的后续摩擦，不是本切片的缺陷。
