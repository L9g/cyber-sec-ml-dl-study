"""第四条切片（slice 4 / ADR-0015）：**非 automatic 裁定**——CE-UK-SU-03「Update exceptions and
remediation actions are tracked」，method=document_review、verdict=**human_review**、severity=Low。

**唯一新变量 = 人工裁定（human_review）+ 声明式/attestation 证据（非工具产出）**。前三片全是
`verdict_mode=automatic`（AI run / 确定性 rule / 主动探测）。本片证据是**声明记录**（变更/例外登记 +
reviewer attestation），不是工具输出；**verdict 是人的、系统不第二次猜**（不拿确定性 rule 冒充裁定）。

⭐ 观察点（ADR-0015，不提前设计）：reviewer/date/attestation_ref **没有 Finding 上的 typed 家**
（AI 有 ai_run_record、这里没有对应的 review record）→ 现落 measurement_context free dict → 这是
**最可能逼出 `verdict_source` + `ReviewRecord`** 的地方。结构完整性（每条 exception 有 justification）
作 **advisory 观察、surface 不 override 人工裁定**。
"""
from __future__ import annotations

from typing import Any, Literal, Optional

import datetime

from pydantic import BaseModel, field_validator, model_validator

from ithuriel.capability import (
    CAPABILITY_BRIDGE_PROVENANCE,
    AdapterDescriptor,
    adapter_satisfies,
    required_capabilities,
)
from ithuriel.models import (
    AssuranceReport,
    EvidenceManifest,
    Finding,
    HumanAttestationProvenance,
    ScopeStatement,
    content_hash,
)
from ithuriel.registry import control, referenced_standards

CONTROL_ID = "CE-UK-SU-03"
ATTESTATION_MAPPING_VERSION = "human-review-attestation/v1"   # attestation.decision → Finding.status 约定版本
INPUT_FORMAT = "change-exception-register/v1"

REGISTER_ADAPTER = AdapterDescriptor(
    adapter_id="change_register_reader", provides={"governance.change_register.review"},
    input_format=INPUT_FORMAT)

# 人工裁定 → Finding 四态（**约定映射**，非确定性 rule 产生裁定；裁定源是 reviewer 的 decision）。
_DECISION_TO_STATUS = {"conformant": "pass", "non_conformant": "fail",
                       "insufficient_evidence": "inconclusive"}


class ExceptionEntry(BaseModel):
    exception_id: str
    justification_ref: str = ""        # 空 = 已登记但未 justified
    review_date: str = ""
    remediation_action: str = ""


class ReviewAttestation(BaseModel):
    """reviewer 对登记的人工裁定（fixture-first：冻结的人工决定）。**这是裁定源**。

    ⭐ 结构完整性在类型层强制（partner review 2026-07-22 C5）：此前 reviewer、日期、声明、
    引用全空的 attestation 仍能产出 human-review `pass` 且 `measurement_valid=True`，
    rationale 退化成「reviewer= 于  裁定 conformant」——形式上有对象、实质上没有可归责的人、
    时间、声明或被审材料。系统仍不第二次猜人的裁定，只验证「人工裁定证据确实成形」。
    """
    reviewer: str
    review_date: str
    decision: Literal["conformant", "non_conformant", "insufficient_evidence"]
    statement: str
    attested_refs: list[str] = []      # reviewer 检视的登记 id / 文档引用

    @field_validator("reviewer", "statement")
    @classmethod
    def _non_empty(cls, v: str, info) -> str:
        if not (v or "").strip():
            raise ValueError(f"{info.field_name}_empty：无可归责的人或声明，不构成人工裁定证据")
        return v.strip()

    @field_validator("review_date")
    @classmethod
    def _parseable_date(cls, v: str) -> str:
        try:
            datetime.date.fromisoformat((v or "").strip()[:10])
        except ValueError as exc:
            raise ValueError(f"review_date_unparseable: {v!r}") from exc
        return v.strip()

    @model_validator(mode="after")
    def _refs_required_for_decisive(self):
        # 下结论（conformant / non_conformant）必须说明审了什么；insufficient_evidence 例外，
        # 因为「证据不足」本身就可能意味着没有可引用的材料。
        if self.decision in ("conformant", "non_conformant") and not self.attested_refs:
            raise ValueError("attested_refs_empty：裁定 "
                             f"{self.decision} 必须声明所审材料")
        return self


def _register_completeness(entries: list[ExceptionEntry]) -> dict[str, Any]:
    """结构完整性 = **advisory 观察**（surface、不 override 人工裁定）。"""
    n = len(entries)
    justified = sum(1 for e in entries if e.justification_ref)
    return {"n_entries": n, "n_justified": justified,
            "completeness": round(justified / n, 3) if n else None,
            "unjustified_ids": [e.exception_id for e in entries if not e.justification_ref]}


def build_report(*, register: list[ExceptionEntry],
                 attestation: Optional[ReviewAttestation], host_id: str,
                 adapter: AdapterDescriptor = REGISTER_ADAPTER,
                 assessed_at: str = "2026-07-13T00:00:00+00:00",
                 generated_from: str = "fixture:change-register") -> AssuranceReport:
    """变更/例外登记 + reviewer attestation → AssuranceReport（human_review）。

    无 attestation → inconclusive（**没有人工裁定可承载**，非 pass）。capability 不匹配 → unsupported gap。
    """
    ctrl = control(CONTROL_ID)
    if not adapter_satisfies(CONTROL_ID, adapter):
        return _gap_report(host_id, "无满足 capability 需求的 adapter", assessed_at, generated_from)

    completeness = _register_completeness(register)
    # 证据 = 声明记录（登记 + attestation），**非工具产出**。内容寻址、不可变。
    reg_payload = {"kind": INPUT_FORMAT, "entries": [e.model_dump() for e in register]}
    reg_hash = content_hash(reg_payload, prefix="reg:")
    artifacts: dict[str, dict[str, Any]] = {reg_hash: reg_payload}
    evidence_refs = [reg_hash]
    # Step 4（ADR-0016）：裁定源=reviewer 的 decision → human_attestation provenance。
    # decision_evidence_ref **引用已存 att: 哈希、不复制第三份**（att_payload 已进 artifacts）。
    # 无 attestation → 无裁定事件 → provenance=None（Claim 层 fail-closed，诚实：无人工决定可承载）。
    verdict_prov = None
    if attestation is not None:
        att_payload = {"kind": "review-attestation/v1", **attestation.model_dump()}
        att_hash = content_hash(att_payload, prefix="att:")
        artifacts[att_hash] = att_payload
        evidence_refs.append(att_hash)
        verdict_prov = HumanAttestationProvenance(
            decision_evidence_ref=att_hash, mapping_version=ATTESTATION_MAPPING_VERSION)

    if attestation is None:
        status, rationale = "inconclusive", (
            "变更/例外登记已收集，但**无 reviewer attestation** → 无人工裁定可承载（human_review），"
            "不给 pass。需 reviewer 出具 attestation。")
    else:
        status = _DECISION_TO_STATUS[attestation.decision]
        note = ""
        # ⭐ 引用必须解析得到本次 register/artifact：引用不到的材料等于没审（C5）。
        known_refs = {e.exception_id for e in register} | set(artifacts)
        dangling = [r for r in attestation.attested_refs if r not in known_refs]
        if dangling and status == "pass":
            status = "inconclusive"
            note = (f"（⚠ attested_refs {dangling} 无法解析到本次登记或 artifact —— "
                    "所审材料不可核验，降为 inconclusive、不给 pass）")
        # advisory：人工裁定 conformant 但登记结构不全 → **surface 差异、不 override**。
        if status == "pass" and completeness["unjustified_ids"]:
            note = (f"（⚠ advisory：reviewer 裁定 conformant，但登记中 "
                    f"{completeness['unjustified_ids']} 缺 justification_ref —— 结构差异已 surface、"
                    "不 override 人工裁定，见 ADR-0015 摩擦）")
        rationale = (f"human_review：reviewer={attestation.reviewer} 于 {attestation.review_date} "
                     f"裁定 `{attestation.decision}` → {status}。“{attestation.statement}”{note}")

    mctx = _measurement_context(ctrl, attestation, completeness)
    index = {"attestation": evidence_refs}
    manifest = EvidenceManifest(
        run_root=content_hash({"artifacts": artifacts, "index": index, "measurement_context": mctx},
                              prefix="run:"),
        measurement_context=mctx, artifacts=artifacts, index=index)

    finding = Finding(
        control_id=CONTROL_ID, target_ref={"host_id": host_id, "config_source": INPUT_FORMAT,
                                           "artifact_hash": reg_hash,
                                           "target_variant_hash": content_hash(
                                               {"host": host_id, "reg": reg_hash}, prefix="hv:")},
        status=status,
        verdict_mode=ctrl.verification.verdict,   # ⭐ human_review（前三片都 automatic）
        assessed_at=assessed_at, evidence_refs=evidence_refs,
        severity=ctrl.severity_if_failed if status == "fail" else None,   # Low
        rationale=rationale,
        run_record=None,          # ⭐ 无 AI run；ADR-0015 曾把 reviewer 溯源落 mctx（无 typed 家）——
                                  # Step 4（ADR-0016）已补 typed 家=verdict_provenance（下），mctx.review_record 仍留作证据。
        root_causes=None, evidence_completeness="per_trial",
        verdict_provenance=verdict_prov,   # 有 attestation→human_attestation；无→None（fail-closed）
    )
    scope = ScopeStatement(
        claim="CE-UK-SU-03 变更/例外登记 human_review（声明式证据、非工具探测）；非合规通过。",
        in_scope={"control": CONTROL_ID, "host": host_id, "input_format": adapter.input_format,
                  "attestation_mapping_version": ATTESTATION_MAPPING_VERSION,
                  "reviewer": attestation.reviewer if attestation else None},
        not_covered=[
            "自动化确定性校验（本控制 method=document_review，verdict 由 reviewer 出具、非工具裁定）",
            "reviewer attestation 的真实性/独立性（承载其决定、不第二次核）",
            "登记数据源真实采集（fixture-first；声明记录、非工具产出）",
        ],
        measurement_valid=(attestation is not None),   # 有人工裁定可承载 = 测量有效
        underpowered=None, invalidity_reasons=[],
    )
    return AssuranceReport(
        generated_from=generated_from, measurement_context=mctx, evidence_manifest=manifest,
        findings=[finding], comparisons=[], scope=scope,
        control=ctrl, referenced_standards=referenced_standards(CONTROL_ID))


def _measurement_context(ctrl, attestation: Optional[ReviewAttestation],
                         completeness: dict[str, Any]) -> dict[str, Any]:
    return {
        "control_id": CONTROL_ID, "domain": ctrl.domain,
        "verification_method": ctrl.verification.method,   # document_review
        "verdict_mode": ctrl.verification.verdict,          # human_review
        "capability_required": sorted(required_capabilities(CONTROL_ID)),
        "capability_bridge": CAPABILITY_BRIDGE_PROVENANCE,
        "adapter": {"id": REGISTER_ADAPTER.adapter_id, "input_format": REGISTER_ADAPTER.input_format},
        "attestation_mapping_version": ATTESTATION_MAPPING_VERSION,
        "execution_backend": "frozen-fixture",
        # ⭐ FRICTION：reviewer 裁定溯源现落这里（无 Finding typed review record）——verdict_source 候选。
        "review_record": (attestation.model_dump() if attestation else None),
        "register_completeness": completeness,              # advisory
        "legacy_plugin_opaque": ctrl.verification.plugin,   # change_management_check（不参与匹配）
    }


def _gap_report(host_id: str, reason: str, assessed_at: str, generated_from: str) -> AssuranceReport:
    ctrl = control(CONTROL_ID)
    mctx = {"control_id": CONTROL_ID, "gap_kind": "unsupported", "gap_reason": reason}
    scope = ScopeStatement(
        claim=f"CE-UK-SU-03 未评（unsupported: {reason}）→ 覆盖缺口，不产 Finding。",
        in_scope={"control": CONTROL_ID, "host": host_id},
        not_covered=[f"unsupported（进覆盖分母）：{host_id} — {reason}"],
        measurement_valid=False, underpowered=None, invalidity_reasons=["tooling_unsupported"])
    empty = EvidenceManifest(run_root=content_hash({"gap": CONTROL_ID}, prefix="run:"),
                             measurement_context=mctx, artifacts={}, index={"attestation": []})
    return AssuranceReport(
        generated_from=generated_from, measurement_context=mctx, evidence_manifest=empty,
        findings=[], comparisons=[], scope=scope,
        control=ctrl, referenced_standards=referenced_standards(CONTROL_ID))
