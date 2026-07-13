# ADR 0016 — typed `verdict_provenance` + Claim 层收窄 warrant（confidence_basis）

日期：2026-07-13 · 状态：accepted（用户拍板「收窄 warrant」；搭档 review 三点采纳、一处我异议被采纳） · 关联：`0015`（**预言了本步**：verdict_source 作下一个刻意 schema 演进、forcing trigger=Claim/Assurance 消费者）、`0004`（finding_id 十一哈希契约）、`0005`（bare ASR=0→inconclusive、D2 测量上下文可比）、`docs/architecture-seams-D8.md`（seams #4/#6/#8）、`reports/partner-review-2026-07-12.md`（本轮搭档 review 另附）

## 背景与 forcing 论证
`0015` 记下：四形状（AI probe / config-read / active-probe / human-review）各有不同裁定溯源，只有 AI 有 Finding 上的 typed 家（`ai_run_record`），另三塞 `measurement_context` free dict；信号四次确认但**无 consumer 因此断裂**，故不 reactive 加、建议作下一个刻意演进。本 ADR 建那个 consumer 并落字段。

**为何 `verdict_mode` 不够**（核心）：`verdict_mode=automatic` 把**三种置信度体制**压成一值——AI 探针（统计、非确定、受 n_runs/CI 限）、config 规则（确定性、bit 可复现）、active probe（确定性规则作用于**mock 执行**观察、受保真度限）。要「按裁定**怎么得来**赋不同 confidence」的 consumer 读 `verdict_mode` 分不出这三片。

**Step 1 spike 撞出的真实摩擦**（scratchpad、不入 repo；故意写 free-dict key-sniff 提取）：

| # | 摩擦 | 含义 |
|---|---|---|
| **#A** | probe 与 config **共用 `rule_version` key** → 提取须先判 `execution_receipt` 再判 `rule_version`，否则 probe **静默误判成 config** | typed 自描述 provenance 的头号动因；flat enum 暴露不出 |
| #B | `review_record` key 在、值为 None（无 attestation）→ presence-of-key ≠ value | |
| #C | key 改名/新 shape → 落 UNKNOWN，除非显式 fail-close | fail-open 风险 |
| #D | confidence 输入散三处（AiRunRecord / execution_receipt+backend / review_record）无统一家 | |
| #E | `verdict_mode` 对拆分无用（AI+config+probe 全 automatic） | 坐实需新轴 |

## 搭档 review + 收窄 warrant 决策
搭档 review（另附报告）三点采纳、一处我实质异议被用户采纳：

1. **弃 flat 四值 `verdict_source` 枚举**（`0015` 原预想）——搭档指出**不正交**：AI/config/probe 的**裁定机制同为「确定性规则」**，真区分轴是**测量体制**（statistical_trials vs deterministic_observation）；只 human 是另一裁定**权威**。改 **typed union**（两变体）。
2. **consumer = 纯函数 `Claim Deriver` 非 Engine**，`derive_claims(report)->list[Claim]` 只吐 **Finding-backed** claim（原 `derive_claim(report)->Claim` 欠定义：AI report 有 bare/defended/comparison 三 Finding）。
3. **Claim 输出结构化 `confidence_basis`（多维 warrant）非单一 confidence 档**——reframe：Claim 答「**凭什么成立** + **只对什么范围**」，非「属哪种 automatic」。单档留 consumer 未来 weakest-link 派生。
4. **我的异议（用户采纳）= 收窄 warrant，不搭档六维全建**。过尺纪律「2+ fixture 给 2+ 值才升 typed 轴」：`adjudication` / `uncertainty` / `reproducibility` 三轴全值被 4 fixture 逼出（Literal）；`target_fidelity` 的 `real` **未观测** → str（不冻未观测值）；`authority`（只 slice4 单值 unverified）**不设轴、入 limitations**。`uncertainty`/`reproducibility` 与 `measurement_kind` **共变** → 在 Claim 层**派生、不在 Finding 上新存**（单一真相源，防 None-vs-0.0 族冗余漂移）。

## 三决策（用户拍板）
1. consumer 走纯函数 Claim Deriver——**不建** Engine/ExperimentManager/PlanCompiler。
2. `verdict_provenance` 挂 **Finding**、**带默认 None 不进 `finding_id` 哈希**（守 `0004`：finding_id 只哈希 control_id/target_ref/status/evidence_refs）、历史 Finding None → consumer **fail-closed**。
3. `ScopeGap` **暂不收**——但 API 诚实封口：**0-Finding → 返回空 list（Unassessed）、绝不静默产正向 Claim**。正因**不**对所有 report 强制返回结论，ScopeGap 才得以继续延后（搭档逻辑：若强制返回则 ScopeGap 已被逼出）。

## 落地形状
- **`models.py`**：`AutomaticRuleProvenance{kind, rule_version, measurement_kind}` + `HumanAttestationProvenance{kind, decision_evidence_ref, mapping_version}`，discriminated union 按 `kind` 路由；`Finding.verdict_provenance: Optional[VerdictProvenance]=None`；`ConfidenceBasis{adjudication, uncertainty, reproducibility, target_fidelity, limitations}`；`Claim{control_id, finding_id, finding_status, verdict_provenance, confidence_basis, claim_scope, assessable, unassessable_reason, claim_id}`。
- **`claim.py`（新）**：`derive_claims`（纯函数、只读 report、不 mutate、不 override status/joint_verdict）；`_confidence_basis` 从 provenance+mctx **派生**（reproducibility/uncertainty 从 measurement_kind、target_fidelity 从 execution_backend）；authority 入 limitations。
- **回填六个 Finding 构造点**：derive.py bare+defended（AI，新薄常量 `STATUS_RULE_VERSION="ai-status-rule/v1"`——此前只有 comparison 层的 `JOINT_RULE_VERSION`、单 finding status 规则无版本）· config_inspection.py · port_scan.py · attestation.py（`decision_evidence_ref`=**引用已存 `att:` 哈希、不复制第三份**；无 attestation→None→fail-closed）· derive_session.py 汇总 AI（守 uniform，避免单跑 assessable/session fail-closed 分裂）。

**四形状映射（恰 2 变体、无遗漏无凭空多值；#A 摩擦被溶解）**：

| 形状 | 变体 | measurement_kind | Claim 派生 basis |
|---|---|---|---|
| AI probe | automatic_rule | statistical_trials | statistical_ci / protocol / mock |
| config-read | automatic_rule | deterministic_observation | deterministic / bit / frozen_fixture |
| active-probe | automatic_rule | deterministic_observation | deterministic / bit / mock |
| human-review | human_attestation | —（声明式） | unquantified / declarative / +authority=unverified limitation |

config 与 probe **同变体**——不再靠 sniff `rule_version` key 区分（#A 正解），差异（frozen_fixture vs mock）下移 Claim 层从 `execution_backend` 派 `target_fidelity`。

## claim_id 哈希契约 + fail-closed
- `claim_id = content_hash(finding_id + verdict_provenance + confidence_basis + claim_scope)`：provenance 变 → claim_id 变，**不让同 id 承载不同置信度**（搭档要求）。`finding_id` v1 不动。
- **fail-closed 两处**：0-Finding → 空 list；Finding 有但 provenance 缺 → `assessable=False` + `confidence_basis=None` + `unassessable_reason`（不赋乐观档）。`Claim` validator 强制 assessable=False 时 basis 必 None + reason 必填。

## 诚实观测 / 软摩擦（记下、非阻塞）
- **attestation=None 的 fail-closed reason 现用通用「历史/未回填」串**——对「无人工决定可承载」这一具体子因略泛。可后续细化 `unassessable_reason` 为枚举（no_provenance / no_adjudication_event …），未逼到必做。
- **`target_fidelity=real`、`authority=independent` 等未观测值**沿用收窄纪律：str/limitations 承载、不预设枚举，第二个真实值出现再升 typed 轴（同 `0006` 的 `blocks_preserving_utility` 留位不造 fixture）。
- **结构化 `ScopeGap` 仍延后**——本切片 0-Finding 走空 list（非结构化 gap 对象），信号成熟未逼断。

## 守纪律
**未动 `ontology_schema.yaml`/profile**（新枚举全 pydantic advisory）；Claim Deriver 纯函数最薄切片、不建子系统；confidence **不 override** 任何现有裁定（纯叠加）；attestation 引用已存 evidence hash 不复制第三份。

## 验证
`pytest src/tests/` = **150/150**（128 baseline + 9 `test_verdict_provenance.py` + 13 `test_claim.py`）。三关键测试全覆盖：历史 unspecified fail-closed ✓、0-Finding 不产正向 Claim ✓、同 Finding 不同 fidelity/provenance → claim_id 与 basis 不同 ✓。端到端四 producer 真报告全 assessable、basis 各对（`test_all_four_producers_assessable_end_to_end`）；哈希稳定性（加字段不改 finding_id、bit-reproducible run_root 全绿）。
