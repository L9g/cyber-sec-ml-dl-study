"""差异化层的 schema 模型（pydantic v2）。

**只取 `docs/ontology_schema.yaml` v0.6 required + 本真跑数据真用到的字段**，冻结/parked 字段不加
（remediation / threat_model / fidelity_gap / llm_judge …）。字段形状据 results/d8_*.json 反推。

三正交概念（守 CLAUDE.md schema 不变量）：
  - Finding.status 四态：pass / fail(需 rationale+severity) / not_applicable / inconclusive
  - verdict_mode：automatic | llm_judge | human_review（D8 强制 automatic=确定性 detector）
  - AiRunRecord：AI 探针非确定 → 每个 Finding 带 run 统计
delta 不是一条 Finding，是跨两条 Finding 的 ComparisonSpec（seams #5）。
scope/assurance_level 挂 report 层、**非 Finding 字段**（seams #8 / 治理笔记 4.3）。
"""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

FindingStatus = Literal["pass", "fail", "not_applicable", "inconclusive"]
VerdictMode = Literal["automatic", "llm_judge", "human_review"]
# 证据保真度（据本会话真实摩擦反推，2026-07-11）：单文件覆盖式 → runs 1–4 raw 已丢，
# 只余汇总。汇总级 Finding 是**更弱**的保证 artifact（无 per-trial evidence_refs/manifest），
# 不许冒充全证据。见 ADR-0005 步骤 6。
EvidenceCompleteness = Literal["per_trial", "summary_only"]
# defense delta 不可断言的正交子因（反推自 5 跑）：measurement_valid=False 有两个截然不同的
# 子因——正对照缺失(bare ASR=0) vs 配额截断(n_valid 大幅 < n_trials)；underpowered=CI 重叠、
# 但正对照在；tooling_unsupported=harness 根本没执行（如 OpenRouter 路由 404 无 tool use）。
InvalidityReason = Literal[
    "no_positive_control", "quota_truncated", "underpowered", "tooling_unsupported",
    # 差分删失（partner review D1/C1，2026-07-12）：bare/defended 的 n_valid 差过大 → delta 被
    # 删失污染。seams §7 早有此语义（散文），此前只写 note、未进闸门 → 现并入 ¬assertable 子因。
    "differential_attrition",
    # 两臂 context 不变量漂移（partner review D2/C3，2026-07-12，第二批）：treatment(defense) 外的
    # served_model/fingerprint/温度/语料/库 在 bare↔defended 间不等 = 未声明差异 → delta invalid。
    "context_invariant_mismatch",
]
# root_cause_enum（schema v0.6，advisory-only，无序集合，≥1，不设 primary）
RootCause = Literal["P1", "P2", "P3", "P4", "P5", "P6", "OTHER", "UNDETERMINED"]
# 防御的 security⊗utility tradeoff 类（advisory，据档 1 真跑反推，2026-07-11，ADR-0006）：
# 只装**真实防御行为**三值；「归不了类」不塞进来，改由 tradeoff_unclassified_reason 承载（正交）。
# blocks_preserving_utility 当前**未观测**（AgentDojo 无 sanitize-continue 防御、只有 abort 型）——
# 定义留位、如实标 gap，不为它编 fixture。见 ADR-0006「明确延后」。
TradeoffClass = Literal[
    "ineffective",               # 强正对照下 ASR 未可断言下降（防御啥也没做）；spotlighting 1.0→1.0
    "blocks_by_refusing",        # ASR 可断言↓ 但 defended under-attack utility 低（检到即 abort，不救活任务）
    "blocks_preserving_utility",  # ASR 可断言↓ 且 defended utility 高（sanitize-continue）——未观测，定义留位
]
# tradeoff_class=None 时的原因（正交、非防御行为）：与 InvalidityReason 值有重叠是刻意（语义一致），
# 但 utility_confounded 是**新**子因——security_delta 本身可断言(如 gpt-4o-mini −0.30)、confound 纯在
# utility/tradeoff 轴（目标 under-attack 几乎不工作），故不并进 InvalidityReason（那只解释 security_delta）。
TradeoffUnclassified = Literal[
    "no_positive_control", "utility_confounded", "underpowered",
    # defended utility 未测量（partner review C2，2026-07-12）：None ≠ 低 utility。此前 None 被
    # 当 <BLOCK_UTIL 直接判 blocks_by_refusing（未知当低效用）→ 现单列，只有实测 util 才分类。
    "utility_unmeasured",
]

# security⊗utility 联合裁定（partner review D3(a) + 搭档二轮反调和，2026-07-12）：**非 advisory、恒有值**。
# 下游机器读**这个**判"防御实验能否形成可接受结论"，而非读 defended Finding.status（那只裁 security 轴、
# utility=0 时仍 pass 会误导）。**独立算 raw inputs、不读 advisory 的 tradeoff_class**（避免不稳定
# taxonomy 反向控制裁定）；两者只共享版本化 confound 判据、不互读输出。
# **语义边界（已批准）**：评价「防御效果的**可归因**结论」，非「整个 defended target 的部署可接受性」——
# 后者是未来 target-level 层，confound（靶机本就低效用）在此 fail-closed 为 inconclusive、不归罪于防御。
#   security_failed=defended 仍被注入 · utility_failed=security 达标但可归因 utility<门 ·
#   acceptable=两轴达标 · inconclusive=不可断言/未测/confound。
JointVerdict = Literal["acceptable", "security_failed", "utility_failed", "inconclusive"]


def canonical(obj: Any) -> bytes:
    """确定性 canonical JSON（内容寻址用）：sort_keys + 紧凑分隔 + 保留非 ASCII。"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_hash(obj: Any, prefix: str = "", n: int = 16) -> str:
    h = hashlib.sha256(canonical(obj)).hexdigest()[:n]
    return f"{prefix}{h}" if prefix else h


class AiRunRecord(BaseModel):
    """schema `ai_run_record`：AI 探针非确定 → 记 run 统计。

    真跑摩擦（deriver 步骤 3 暴露的缺口，见 ADR-0004）：harness 的 meta **未钉** model 快照串 /
    temperature / seed → 三者暂 None 并如实标 gap，不编造。此为「据真实摩擦定字段」的一次实证。
    """

    model_id: str                       # provider/model，如 mistral/mistral-small-latest
    model_version: Optional[str] = None  # 快照串；harness 未记 → None（gap）
    temperature: Optional[float] = None  # harness 未记 → None（gap）
    seed: Optional[int] = None           # provider 不支持或未记 → None
    n_runs: int                          # schema：total attempts（= n_attempted）
    # partner review C5（2026-07-12）：此前 n_runs 被塞成 n_valid → 违反 schema「n_runs=total attempts」
    # 且丢了 execution-error accounting（harness 一直在算）。现恢复 n_runs=总尝试，另列有效/错误计数。
    n_valid: Optional[int] = None        # 有 usable outcome 的 trial 数（= success_rate 分母）
    n_execution_error: Optional[int] = None  # 执行错误（畸形 tool call / 429 截断 / 协议错）的 trial 数
    n_success: int                       # 攻击/失败条件触发的次数
    # ⚠ success_rate 分母 = n_valid（**刻意偏离** schema 的 `n_success/n_runs`）：execution_error 不该
    # 稀释 ASR（把"没跑成"算成"攻击没成功"是错的）。诚实记 n_execution_error 补偿此偏离。见 ADR-0009。
    success_rate: float
    asr_ci95: Optional[tuple[float, float]] = None  # Wilson CI（harness 已算）
    utility_rate: Optional[float] = None  # under-attack utility（档 1：tradeoff 分类要读绝对 util，非 delta）


# ── verdict_provenance（typed，据 4 fixture 反推，2026-07-13，ADR-0016）──────────
# **收窄 warrant**（用户 2026-07-13 拍板，异议搭档六维全建）：typed union 只捕**两根被 2+ fixture
# 真逼出的轴**——adjudication（=kind）⊥ measurement_kind。过尺纪律=「2+ fixture 给 2+ 值才升 typed
# 轴」。reproducibility/target_fidelity 与 measurement_kind **共变** → Claim 层从既有 execution_backend
# **派生、不新存**（单一真相源，防 None-vs-0.0 族冗余漂移）；authority（只 slice4 单值）+ 未观测枚举值
# （target_fidelity=real / authority=independent）入 Claim.confidence_basis 的 limitations 自由列表，
# 等第二权威体制出现再升 typed 轴。**为何现在=Step 1 spike 撞出 free-dict key-sniff 的顺序依赖脆弱
# （probe/config 共用 rule_version、错序静默误判）+ verdict_mode 把 AI/config/probe 压成 automatic 分不开。**
# 挂 Finding、**带默认 None**（历史 Finding 优雅退化、consumer fail-closed）、**不进 finding_id 哈希**
# （守 ADR-0004 十一契约：finding_id 只哈希 control_id/target_ref/status/evidence_refs）。
MeasurementKind = Literal["statistical_trials", "deterministic_observation"]


class AutomaticRuleProvenance(BaseModel):
    """AI 探针 / config / active probe 共有的裁定机制：确定性规则作用于测量结果。

    三片**裁定机制同一**（Step 1 grounding 坐实：AI 的 status 规则、config 的 deny/allow、probe 的
    observed⊆justified 都是确定性 rule）；真区分轴 = measurement_kind——AI=statistical_trials
    （受 n_runs/CI 限），config/probe=deterministic_observation（bit 可复现）。config↔probe 的差异
    在 target_fidelity（frozen-fixture vs mock），由 Claim 层从 execution_backend 派生、不在此存。
    """
    kind: Literal["automatic_rule"] = "automatic_rule"
    rule_version: str                    # config: ufw-default-deny/v1 · probe: fw01-…/v1 · AI: status-rule 版本
    measurement_kind: MeasurementKind


class HumanAttestationProvenance(BaseModel):
    """人工裁定：裁定源是 reviewer 的 decision（非规则），唯一另一种裁定**权威**（Step 1 #E 坐实）。"""
    kind: Literal["human_attestation"] = "human_attestation"
    decision_evidence_ref: str           # 指向**已存** attestation artifact 的内容哈希（att:…；不复制第三份）
    mapping_version: str                  # decision→status 约定版本（ATTESTATION_MAPPING_VERSION）


# discriminated union（pydantic v2 按 `kind` 路由）；Claim 层据此赋不同 confidence_basis。
VerdictProvenance = Annotated[
    Union[AutomaticRuleProvenance, HumanAttestationProvenance],
    Field(discriminator="kind"),
]


class Finding(BaseModel):
    """schema `finding_schema`：control 对 target 判定的裁定结果。

    一格真跑的一个 target variant = 一条 Finding（bare→fail、defended→pass）。
    """

    control_id: str                      # D 抉择：暂硬编字符串，未建 control registry（桶 B）
    target_ref: dict[str, Any]           # 结构化 target variant（含 defense_hash / variant_hash）
    status: FindingStatus
    verdict_mode: VerdictMode
    assessed_at: str                     # ISO-8601（沿用 run meta.generated_at，确定性）
    evidence_refs: list[str]             # 支撑该 status 的 per-trial 内容哈希（seams #6）
    severity: Optional[str] = None       # schema：status==fail 时必填；pass 时语义为空 → None
    rationale: Optional[str] = None      # status fail/inconclusive 必填
    run_record: Optional[AiRunRecord] = None
    root_causes: Optional[list[RootCause]] = None  # advisory，只标 fail（真实失败机理）
    evidence_completeness: EvidenceCompleteness = "per_trial"  # summary_only=raw 已丢、仅汇总
    # typed 裁定溯源（ADR-0016，advisory）：细化 verdict_mode=automatic 的三义（AI 统计/config 确定/
    # probe 探测）+ 显式人工裁定。默认 None → 历史 Finding fail-closed、不进 finding_id 哈希。
    verdict_provenance: Optional[VerdictProvenance] = None
    finding_id: str = ""                 # 内容寻址派生，见 model_validator

    @model_validator(mode="after")
    def _checks_and_id(self) -> "Finding":
        if self.status == "fail":
            if not self.rationale:
                raise ValueError("status=fail 必须带 rationale（schema 不变量）")
            if not self.severity:
                raise ValueError("status=fail 必须带 severity（schema 不变量）")
        if self.status == "inconclusive" and not self.rationale:
            raise ValueError("status=inconclusive 必须带 rationale（schema 不变量）")
        # partner review C4（2026-07-12）：not_applicable **出分母**、必须说明为何不适用；此前无校验
        # 致 tooling_unsupported 静默产无理由 NA。（不适用 ≠ 未测到；后者是 unsupported，进分母。）
        if self.status == "not_applicable" and not self.rationale:
            raise ValueError("status=not_applicable 必须带 rationale（出分母需说明不适用理由）")
        if self.root_causes is not None and len(self.root_causes) < 1:
            raise ValueError("root_causes 是 ≥1 的无序集合（UNDETERMINED 为下限）")
        if not self.finding_id:
            # id 由裁定性字段内容派生 → 同输入稳定（bit-reproducible 契约）
            self.finding_id = content_hash(
                {"control_id": self.control_id, "target_ref": self.target_ref,
                 "status": self.status, "evidence_refs": self.evidence_refs},
                prefix="finding:",
            )
        return self


class ComparisonSpec(BaseModel):
    """seams #5：defense delta = 跨两条 Finding 的比较，单一 treatment=defense_hash，fail-closed。

    delta 的可断言性由 harness 的 measurement_valid ∧ ¬underpowered 决定（seams v1.2 §7），
    这里只承载、不重算。security⊗utility 成对报告（seams §7 附），不许只报 security 轴。
    """

    kind: Literal["defense_delta"] = "defense_delta"
    treatment_field: Literal["defense_hash"] = "defense_hash"
    baseline_finding_id: str             # bare
    treatment_finding_id: str            # defended
    security_delta_ASR: Optional[float]
    utility_delta: Optional[float]
    assertable: bool                     # measurement_valid ∧ underpowered is False
    underpowered: Optional[bool]
    measurement_valid: bool
    invariants: dict[str, Any]           # treatment 外必须全等的字段（未声明差异→invalid）
    invalidity_reasons: list[InvalidityReason] = Field(default_factory=list)  # ¬assertable 的正交子因
    # 档 1（ADR-0006）：从成对 (security_delta, defended_utility) 反推的 tradeoff 类；
    # 归不了类时 tradeoff_class=None、reason 记原因（正交）。二者都 Optional 默认 → 不进任何哈希。
    tradeoff_class: Optional[TradeoffClass] = None
    tradeoff_unclassified_reason: Optional[TradeoffUnclassified] = None
    # partner review D3(a)（2026-07-12）：security⊗utility 联合裁定，**非 advisory、恒有值**——
    # 下游读它、不读 defended Finding.status（后者只裁 security 轴）。见 JointVerdict 定义。
    joint_verdict: JointVerdict = "inconclusive"
    # 裁定输入（可审计）：assertable/security_acceptable/utility_measured/utility_confounded/
    # defended_utility/utility_threshold/rule_version → 下游能复核裁定怎么得来。默认空 → 不进哈希。
    joint_verdict_inputs: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ScopeStatement(BaseModel):
    """seams #8：结构化 scope/gap，显式 `assurance_level: none`，防 demo 误读为合规通过。

    挂 report/run 层，**非 Finding 字段**（治理笔记 4.3）。= CoverageLedger 种子（桶 B）。
    """

    assurance_level: Literal["none"] = "none"
    claim: str
    in_scope: dict[str, Any]
    not_covered: list[str]               # 进覆盖分母的 gap（not_tested/unsupported/out_of_scope 类）
    measurement_valid: bool
    underpowered: Optional[bool]
    invalidity_reasons: list[InvalidityReason] = Field(default_factory=list)


class EvidenceManifest(BaseModel):
    """seams #6：per-trial 内容寻址 artifact → 聚合 run root。raw 不可覆盖、不压平。

    线性 prev_evidence_hash **不**作长期形状（schema 注记）；这里用 manifest+run_root。
    """

    run_root: str                        # = content_hash(artifacts ∪ index ∪ context)
    measurement_context: dict[str, Any]
    artifacts: dict[str, dict[str, Any]]  # trial_hash → 不可变 raw trial record
    index: dict[str, list[str]]          # config(bare/defended) → [trial_hash]


# ── 控制注册表（档 3，ADR-0008）= 差异化层「标准→ontology」半边 ──────────────
# profile（UK_Region_Profile_v0.2.yaml）里已声明的**只读**消费：控制元数据 + standards 注册表。
# 不建 capability/plugin 匹配（GATE-2 defer）、不改 profile/ontology YAML。
Severity = Literal["Low", "Medium", "High", "Critical"]  # 配 ontology scoring gating（High/Critical 否决）
VerificationMethod = Literal["automated_test", "config_inspection", "document_review", "attestation"]


class StandardRef(BaseModel):
    """控制→标准的引用；source 必须在 profile standards 注册表声明（不变量，见 Registry 校验）。"""
    model_config = ConfigDict(extra="ignore")
    source: str                          # 标准 id，如 owasp_llm_top_10_2025
    ref: str                             # 标准内定位，如 "LLM01 Prompt Injection"


class Verification(BaseModel):
    """三正交维之一体：method（执行）+ verdict（判定）+ requires_approval（授权闸门）。"""
    model_config = ConfigDict(extra="ignore")
    method: VerificationMethod
    verdict: VerdictMode                  # automatic/llm_judge/human_review
    requires_approval: bool = False
    plugin: Optional[str] = None          # GATE-2 直接绑定，当**不透明元数据**消费（不做匹配）


class ControlDefinition(BaseModel):
    """profile 控制实例（只取本层消费的字段；probe_suite/csf2/plugins 等 extra 忽略）。"""
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    domain: Optional[str] = None
    severity_if_failed: Optional[Severity] = None  # Finding.severity 于 fail 时继承此值
    standards_refs: list[StandardRef]
    verification: Verification


class StandardEntry(BaseModel):
    """standards 注册表一条：id → 权威/角色/链接（source 悬空校验的真相源）。"""
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    authority: Optional[str] = None
    role: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None          # planned / (在用无此字段)


class Registry(BaseModel):
    """control + standards 注册表，加载时强制 schema 不变量：standards_ref.source 不得悬空。"""
    standards: dict[str, StandardEntry]
    controls: dict[str, ControlDefinition]

    @model_validator(mode="after")
    def _no_dangling_standard_source(self) -> "Registry":
        for cid, c in self.controls.items():
            for r in c.standards_refs:
                if r.source not in self.standards:
                    raise ValueError(
                        f"control {cid}: standards_ref.source '{r.source}' "
                        "未在 profile standards 注册表声明（悬空引用，违反 schema 不变量）")
        return self

    def referenced_standards(self, control_id: str) -> dict[str, StandardEntry]:
        """某控制引用到的 standards 子集（source → 解析后的 StandardEntry）；审计闭环用。"""
        return {r.source: self.standards[r.source]
                for r in self.controls[control_id].standards_refs}


class AssuranceReport(BaseModel):
    """把一格真跑的『建』产物打成一个可审计信封。"""

    report_version: str = "0.1"
    generated_from: str
    measurement_context: dict[str, Any]
    evidence_manifest: EvidenceManifest
    findings: list[Finding]
    comparisons: list[ComparisonSpec]
    scope: ScopeStatement
    # 档 3：解析后的控制（带 standards_refs）+ 引用到的 standards，挂**报告层**（范式化，
    # 非 Finding 字段——Finding 只 control_id，standards 由 control_id 函数决定）。默认可空 → 不破旧构造。
    control: Optional[ControlDefinition] = None
    referenced_standards: dict[str, StandardEntry] = Field(default_factory=dict)


class SessionReport(BaseModel):
    """跨多个测量条件（一个会话的 N 跑）的保证信封。

    据本会话真实摩擦反推（2026-07-11，5 跑，见 ADR-0005）：单跑 AssuranceReport 不够——
    真实评估是一批条件（跨 model×attack×defense），其中掺杂 invalid 跑（无正对照/配额/无 tool use）
    与混合保真度（仅末跑存 per-trial，其余 raw 已覆盖）。session 层**只聚合与横向观察、不重算裁定**。
    """

    session_id: str
    generated_from: list[str]            # 溯源：全部输入文件（csv + 存活 json）
    runs: list[AssuranceReport]          # 每条测量条件一个（含 invalid/not_applicable 跑）
    cross_condition_notes: list[str] = Field(default_factory=list)  # 横向观察（如攻击变体摆动）


# ── Claim 层：confidence_basis（收窄 warrant）+ Finding-backed Claim（Step 3，ADR-0016）──────
# reframe（搭档 + 用户拍板）：Claim 答「**凭什么成立** + **只对什么范围成立**」，非「属哪种 automatic」。
# **多维依据保留、不产单一 confidence 档**（单档留 consumer 未来 weakest-link 派生）。维度过尺=「2+
# fixture 给 2+ 值才升 typed 轴」：adjudication/uncertainty/reproducibility 三轴全值被 4 fixture 逼出
# → Literal；target_fidelity 的 `real` 未观测 → **str**（不冻未观测值，守收窄纪律）；authority（只 slice4
# 单值 unverified）**不设轴、入 limitations**。uncertainty/reproducibility 与 measurement_kind 共变 →
# 在此**派生、不在 Finding 上新存**（单一真相源，防 None-vs-0.0 族冗余漂移）。
Uncertainty = Literal["statistical_ci", "deterministic", "unquantified"]
Reproducibility = Literal["bit", "protocol", "declarative"]


class ConfidenceBasis(BaseModel):
    """结论的多维 warrant（『凭什么』），非单一档。全部由 verdict_provenance + mctx 派生。"""
    adjudication: Literal["automatic_rule", "human_attestation"]   # = provenance.kind
    uncertainty: Uncertainty          # statistical→CI 限 · deterministic → bit 可复现 · 人工 → 未量化
    reproducibility: Reproducibility  # statistical_trials→protocol · deterministic→bit · 人工→declarative
    target_fidelity: str              # 派生自 execution_backend（mock/frozen_fixture）；`real` 未观测→str
    limitations: list[str] = Field(default_factory=list)  # authority=unverified、保真度、assurance none 等


class Claim(BaseModel):
    """Finding-backed 保证结论：承载『凭什么成立(confidence_basis) + 只对什么范围(claim_scope)』。

    首版**只吐 Finding-backed claim**（不产 Comparison/控制总体/合规 claim）。
    **fail-closed**：verdict_provenance 缺失 → assessable=False、confidence_basis=None（不默认乐观档）。
    confidence **不 override** 任何现有裁定（Finding.status / ComparisonSpec.joint_verdict）——纯叠加。
    """
    control_id: str
    finding_id: str
    finding_status: FindingStatus         # 被主张的裁定（confidence 描述『怎么得来』，与『是什么』正交）
    verdict_provenance: Optional[VerdictProvenance] = None
    confidence_basis: Optional[ConfidenceBasis] = None
    claim_scope: dict[str, Any]
    assessable: bool                      # provenance 在 → True；缺 → False（fail-closed）
    unassessable_reason: Optional[str] = None
    claim_id: str = ""                    # 内容寻址：finding_id + provenance + basis + scope（见 validator）

    @model_validator(mode="after")
    def _id(self) -> "Claim":
        if not self.assessable and self.confidence_basis is not None:
            raise ValueError("assessable=False 时 confidence_basis 必须为 None（fail-closed 不赋依据）")
        if not self.assessable and not self.unassessable_reason:
            raise ValueError("assessable=False 必须带 unassessable_reason")
        if not self.claim_id:
            # provenance 变 → claim_id 变（不让同 id 承载不同置信度，搭档哈希要求）。
            self.claim_id = content_hash({
                "finding_id": self.finding_id,
                "verdict_provenance": self.verdict_provenance.model_dump() if self.verdict_provenance else None,
                "confidence_basis": self.confidence_basis.model_dump() if self.confidence_basis else None,
                "claim_scope": self.claim_scope,
            }, prefix="claim:")
        return self
