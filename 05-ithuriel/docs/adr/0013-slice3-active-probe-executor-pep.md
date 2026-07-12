# ADR 0013 — 第三条切片：主动探测 + 执行/授权机器（executor=PEP，CE-UK-FW-01）

日期：2026-07-13 · 状态：accepted（三方共识：我 + 搭档 review + 用户拍板） · 关联：`0011`（D8 v1 baseline、跨域 provisional）、`0012`（slice 2 确定性 config）、`docs/architecture-seams-D8.md` #1（executor=PEP）/#2（execution-fact）/#3（capability）、`0008`（plugin 不透明）

## 背景
slice 1（非确定 AI + mock exec）、slice 2（确定性 config + read-only 本地证据）**都回避执行副作用**。slice 3 引入**唯一新变量 = 带副作用动作的执行/授权机器**（seams #1 executor=PEP + #2 execution-fact）。按 slice 1/2 一贯纪律 **fixture-first + mock dispatch**：授权/执行-fact 机器做**真逻辑**，dispatch 挂 mock 返回冻结 nmap 输出（**零真实网络 I/O**）。控制 = CE-UK-FW-01（automated_test、severity Medium、standards Cyber Essentials + NIST CSF 2.0）。

## 切片范围（搭档 review 收敛的一句话）
> 在**完全无真实网络 I/O** 下，证明一个结构化主动探测 Action **只有**经过两阶段 PEP + 命令文法白名单 + target-scoped RoE 授权才能抵达 mock backend；backend 只返回 **execution facts / raw artifact**，由 Ithuriel **独立解释**成 Observation/Finding。

## 关键决策（搭档 review 8 处 refinement，全采纳）
- **授权三分**：① RoE authorization（目标/动作/范围**事先授权**，每动作必需）② just-in-time human approval（FW-01 **不需要**）③ `verification.requires_approval=False` 只免第 ②、**不免第 ①**。→ slice 3 验证**授权机器**；**不为凑 seams#1 给 FW-01 硬造人工审批**。`ApprovalGrant` 数据结构等首个真需人工审批的动作再由摩擦定形。
- **语义化 Action，非 `binary+argv`**：`NetworkPortScanAction{target_ip, ports, scan_profile}`；`-iL`/`--script`/夹带额外 target/输出副作用**在类型层不可表达**（argv 由 `compile_argv` **固定模板**生成、禁 shell、dispatch 收 argv list）。白名单 = 语义类型本身 + 运行时 target/ports/profile 策略。
- **两阶段 PEP 不信 preflight**：preflight 产 `PolicyDecision`（绑 action_hash + roe_version）；pre-dispatch **重算 hash + 核对 roe_version + 独立重跑策略**（非只信 `preflight_passed`）。action_hash 只覆盖**策略字段**（展示字段 `label` 变不改 hash）。
- **RoE 拒绝 ≠ unsupported**：工具**有能力**、只是目标未授权 → **`out_of_scope`**（≠ unsupported[工具无能力] / inconclusive[测了但证据不足] / not_applicable[控制真不适用]）。**不产 Finding、不调 backend**，产覆盖缺口。
- **mock 边界机器可读**：`ExecutionReceipt{dispatch_performed, external_side_effects_performed=False, fixture_ref, backend="mock"}`；RFC 5737 地址 `192.0.2.10`；MockBackend **绝不调 subprocess/socket**。报告声明无真实网络 I/O、Finding 只裁定 synthetic target、**不对 fixture 地址作现实安全声明**、assurance_level=none。
- **ExecutionReceipt ≠ Evidence**（seams #2）：receipt 只陈述**执行事实**（哪个 Action/backend/是否 dispatch/返回码/raw 在哪/有无副作用），**不携带 Finding/status**；Ithuriel 侧 parser 独立解释 raw→Observation→Finding。

## ⭐ FW-01 的 `justified` 缺口（本切片最值得暴露的真实摩擦）
控制标题 = 「Internet-exposed services **identified and justified**」。**nmap 只给 observed open ports（= identified）、证明不了 justified**（服务是否经业务批准）。故**不能因"扫描成功解析出端口"就给 pass**。最小闭环需 target-scoped `DeclaredService{port, owner, justification_ref}` 清单：
- `observed ⊆ declared-and-justified → pass` · `存在未声明/未 justified 开放端口 → fail(Medium)` · **无 inventory → inconclusive**（非 pass）。
- **绝不在 parser 里偷偷写静态 allowed-port 列表**。profile 现有 `evidence_requirements`（target_scope/command_audit_log/parsed_open_ports）**不足以闭合 justified** —— 记为 slice 发现（需第二证据源=justification inventory），不硬凑。

## 落地形状
- `executor.py`（新）：`NetworkPortScanAction`（frozen、语义字段、`action_hash`/`compile_argv`）· `RoEAuthorization`（allowed_targets IP/CIDR、默认拒、仅 literal IP）· `preflight`/`pre_dispatch`（独立策略）· `PolicyDecision` · `ExecutionReceipt`/`RawArtifactRef`（execution-fact）· `MockBackend`（不调 subprocess/socket）· `execute`（两阶段→mock，拒绝抛 `ExecutionDenied` 不 dispatch）。
- `port_scan.py`（新）：nmap XML 解析（stdlib ElementTree）· `DeclaredService` · `evaluate_fw01`（RULE_VERSION `fw01-exposed-services-justified/v1`）· `build_report`（capability→执行→解析→Finding；RoE 拒绝→`_gap_report` out_of_scope）。
- `capability.py`：加 `CE-UK-FW-01 → host.network.port_scan`（code-local provisional bridge，不改 profile）。
- fixtures `src/tests/fixtures/nmap/`（open_22_443.xml + malformed.xml + README）。测试 `test_executor.py`（15）+ `test_port_scan.py`（15）。

## 跨域通用性：第三个数据点仍支撑（AI + config + active-probe）
三类裁定源（非确定 AI / 确定 config-read / 主动探测-execution）**同一套 Finding/Evidence/AssuranceReport 承载、零 schema 改动**：`run_record=None` 容纳、`comparisons=[]` 完整、审计闭环复用、EvidenceManifest 装 nmap 快照 + receipt（index=`{"probe":[...]}`）。

## 软摩擦（如实标、**不提前加字段**）
- **⭐ `verdict_source` 案例更强、仍未被逼出**：现三类裁定源，probe 概念上是**测量**（网络状态会变），但 probe-run 元数据（action_hash/backend/exit_code/argv）**找到了 `ExecutionReceipt` + `measurement_context` 的家**，未逼 Finding 新字段。三类仍由 `run_record==None` + mctx 执行事实**隐式**区分 → typed `verdict_source` 的理据更足，但**尚未被逼出**（隐式够用）。等第四个形状或真实消费歧义再加。
- **out_of_scope 无结构化 gap 模型**：用 `scope.not_covered` 字符串 + mctx `gap_kind/gap_reason` 承载；`invalidity_reasons` 是 AI 枚举无 out_of_scope 项 → 留空不借错义。结构化 `ScopeGap{kind, reason, action_hash}` 是候选、单实例暂不建。
- 沿用 slice 2 的 `per_trial`/`root_cause_enum`/`measurement_valid` AI 味（非阻塞）。
- **ApprovalGrant 未建**：FW-01 只需授权、不需人工审批 → 审批绑 Action hash 这条 seams#1 子句**未真验证**（如实标；不为凑而造）。

## 守纪律
**未动 `ontology_schema.yaml`/profile**；capability bridge code-local；plugin 不透明未参与匹配；**零真实网络 I/O**（MockBackend 无 subprocess/socket）；无 IPC/scheduler/planner（桶 B）。

## 验证
`pytest src/tests/` = **107/107**（82 + 25 slice-3）。`build_report` 端到端：FW-01 矩阵（all-justified→pass / undeclared→fail(Medium) / 无 inventory→inconclusive / malformed→inconclusive）；RoE 未授权→out_of_scope gap（findings=[]、不调 backend、invalidity_reasons=[]）；`no_real_network_io=True`、compiled_argv 固定模板、审计闭环 Cyber Essentials + NIST CSF 2.0；run_root bit-reproducible。
