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
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

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
]
# root_cause_enum（schema v0.6，advisory-only，无序集合，≥1，不设 primary）
RootCause = Literal["P1", "P2", "P3", "P4", "P5", "P6", "OTHER", "UNDETERMINED"]


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
    n_runs: int                          # = n_valid（有效 trial，非尝试数）
    n_success: int                       # 攻击/失败条件触发的次数
    success_rate: float
    asr_ci95: Optional[tuple[float, float]] = None  # Wilson CI（harness 已算）


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


class AssuranceReport(BaseModel):
    """把一格真跑的『建』产物打成一个可审计信封。"""

    report_version: str = "0.1"
    generated_from: str
    measurement_context: dict[str, Any]
    evidence_manifest: EvidenceManifest
    findings: list[Finding]
    comparisons: list[ComparisonSpec]
    scope: ScopeStatement


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
