# ADR 0012 — 第二条切片：确定性 config-inspection（CE-UK-FW-03），跨域通用性验证

日期：2026-07-12 · 状态：accepted（三方共识） · 关联：`0011`（D8 v1 baseline、跨域 provisional——**本切片验证之**）、`0008`（控制注册表/plugin 不透明）、`docs/architecture-seams-D8.md` #3（capability）/#4（证据边界）/#8（scope-gap）、`reports/partner-review-2026-07-12.md`

## 背景
D8 slice 1 只验证了差异化层的 **AI/非确定性半边**（bare/defended prompt-injection）。ADR-0011 把跨域通用性标 provisional。本切片（slice 2）用一个**确定性 config-inspection** 控制**验证或推翻**：同一套 ontology/证据/保证语义能否承载确定性安全检查。**一次只引入一个新变量**（确定性裁定 + read-only 本地证据；active probe + RoE/PEP 留 slice 3）。

## 控制选择 CE-UK-FW-03（搭档拍板，优于 CE-UK-SC-01）
default-deny 裁定**窄、易成确定性布尔**；CE-UK-SC-01 软件清单会牵出批准基线/版本生命周期/资产范围/例外软件 → 第二条切片膨胀成供应链/资产治理。CE-UK-FW-03 在 profile 现成（method=config_inspection、verdict=automatic、severity=Medium、standards=Cyber Essentials Firewalls + NIST CSF 2.0），registry 审计闭环开箱即用。

## 落地形状（fixture-first、最小链路）
`control requirement → capability 匹配 → 冻结 ufw RawArtifact → DefaultPolicyObservation → 确定性版本化规则 → Finding → AssuranceReport + scope/gap`
- `capability.py`（新）：`CONTROL_CAPABILITY_REQUIREMENTS`（**code-local provisional bridge**：`CE-UK-FW-03 → host.firewall.default_policy.inspect`，不改冻结 profile）+ `AdapterDescriptor(provides, input_format)` + `adapter_satisfies = requirements ⊆ provides`。**非 planner**（一控制一 adapter 一子集判定）。profile 的 `verification.plugin` 继续**不透明 legacy metadata**、报告如实披露、**不参与匹配**（守 seams #3「control 不直接绑工具」）。
- `config_inspection.py`（新）：`parse_ufw_status`（行式，只认 `Status:`/`Default:(incoming)`）+ `evaluate_default_deny`（确定性规则 `RULE_VERSION=ufw-default-deny/v1`）+ `build_report`。**fixture-first**：不实现 `sudo ufw`（特权读取 + 授权 = slice 3）；规范化调用意图 `LC_ALL=C ufw status verbose` 钉进 evidence。
- `registry.control(id)`（新 accessor）；derive.py 的 AI 路径不动。
- fixtures `src/tests/fixtures/ufw/`（5 个冻结输出 + README 溯源）。测试 `test_config_inspection.py`（16 条）。

## 裁定矩阵（含认识论纪律）
| 输入 | 裁定 |
|---|---|
| active + deny/reject incoming | **pass** |
| active + allow incoming | **fail**（severity Medium） |
| **inactive** | **inconclusive**（`sole_authority=True` → fail） |
| active 缺 Default 行 / 无 Status 行 / 截断 | **inconclusive** |

**`inactive→inconclusive` 非 fail**：UFW 未激活**推不出**主机无 default-deny（可能 nftables/iptables/云 SG 执行）；仅当 TargetSnapshot 声明 UFW 为唯一权威执行面才可判 fail。**与 AI 切片「bare ASR=0→inconclusive 非 pass」同源**（缺正信号 ≠ 反结论）。

## ⭐ 结论：跨域通用性**基本验证通过**（ADR-0011 provisional → 大体成立）
**AI 切片的模型 `Finding`/`EvidenceManifest`/`AssuranceReport`/`ScopeStatement` 承载了确定性检查、零 schema 改动、无字段被逼加。** 逐条回答 ADR-0011 的观察问题：
- **Finding 容纳确定性裁定？✅** `run_record=None` 自然容纳（schema 早已 Optional）；`verdict_mode=automatic` 够用。
- **无 ComparisonSpec 时 AssuranceReport 完整？✅** `comparisons=[]` 语义完整（findings + scope + control + standards 齐）；AssuranceReport 不强依赖比较。
- **EvidenceManifest 兼容确定性快照？✅** `index={"config":[hash]}`（AI 用 bare/defended）通用；内容寻址/run_root 复用、bit-reproducible。
- **control→capability→adapter 最小形状？✅** 一 requirement + 一 provides + 子集判定足矣；capability 不匹配 → 覆盖缺口（findings=[]，对齐 C4 unsupported≠not_applicable）。
- **审计闭环复用？✅** control_id→standards_refs→注册表→StandardEntry（Cyber Essentials + NIST CSF 2.0）零改动复用。

## 软摩擦（如实标 `# FRICTION:`，**不提前加字段**）
均为 **AI-flavored 词汇/语义**渗漏，非结构阻塞——记录、暂不动：
- `evidence_completeness="per_trial"`：单确定性快照非 "trial"，词汇 AI 味；
- `root_cause_enum`（P1–P6）是 AI 机理，对防火墙不适用 → fail 也 `root_causes=None`；
- `measurement_valid`（AI=有正对照）复用为"artifact 可解析到可裁定"，语义拉伸；`underpowered=None`（确定性无功效概念）；
- `target_ref` AI 是 model/defense_hash、host 是 host_id/config——用平行最小形状，未抽象共同 target 契约；
- `rule_version` 现挂 `measurement_context` free dict（与 AI 的 aggregate_rule_version 同处），非 typed 字段。

**最可能的下一个抽象 = `verdict_source`**（AI run vs deterministic rule 现由 `run_record==None` **隐式**区分）——但**尚未被逼出**（隐式信号够用）。**只有第三个裁定类型（如 llm_judge 自带 record）出现才加**，不提前建对称抽象。

## 守纪律
**未动 `ontology_schema.yaml`**；capability bridge code-local、**未改冻结 profile**；plugin 不透明未参与匹配；无真实主机执行/无 RoE（slice 3）；无 planner。

## 验证
`pytest src/tests/` = **82/82**（66 + 16 slice-2）。`build_report` 端到端跑 5 冻结 fixture、裁定矩阵如上；run_root bit-reproducible；审计闭环解析 Cyber Essentials + NIST CSF 2.0。
