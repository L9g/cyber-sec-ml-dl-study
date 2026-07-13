"""Claim Deriver（Step 3，ADR-0016）= 差异化层「标准→保证结论」上半边的最薄纯函数切片。

`derive_claims(report) -> list[Claim]`：每条 Finding → 一条 Finding-backed Claim，承载
『凭什么成立(confidence_basis) + 只对什么范围(claim_scope)』。**纯函数**：只读 report、不改任何裁定
（Finding.status / ComparisonSpec.joint_verdict 都不碰）；confidence 是叠加 advisory。

**不建 Engine/ExperimentManager/PlanCompiler**（三决策①）。首版只 Finding-backed，不产 Comparison/
控制总体/合规 claim。**fail-closed 两处**：0-Finding → 空 list（Unassessed，绝不静默产正向 Claim，
借此让 ScopeGap 继续诚实延后，决策③）；Finding 有但 verdict_provenance 缺失 → assessable=False、
confidence_basis=None（历史/未回填 Finding 不赋乐观档）。

confidence_basis 全部**派生**自 `finding.verdict_provenance` + `report.measurement_context`——
reproducibility/uncertainty 从 measurement_kind 派、target_fidelity 从 execution_backend 派
（单一真相源，不新存到 Finding）。收窄 warrant：authority 未升轴、入 limitations（见 models.py）。
"""
from __future__ import annotations

from typing import Any, Optional

from ithuriel.models import (
    AssuranceReport,
    AutomaticRuleProvenance,
    Claim,
    ConfidenceBasis,
    Finding,
    VerdictProvenance,
)

CONFIDENCE_RULE_VERSION = "confidence-basis/v1"   # basis 派生规则版本（口径变则升）

# execution_backend → target_fidelity（收窄：只映**已观测**值；`real` 未观测故不预设枚举）。
_FIDELITY = {"mock": "mock", "agentdojo-mock": "mock", "frozen-fixture": "frozen_fixture"}


def _target_fidelity(backend: Optional[str]) -> str:
    return _FIDELITY.get(backend or "", backend or "unknown")


def _confidence_basis(prov: VerdictProvenance, mctx: dict[str, Any]) -> ConfidenceBasis:
    fidelity = _target_fidelity(mctx.get("execution_backend"))
    limitations = [
        "assurance_level=none：针对限定 fixture/target variant 的证据结论，非控制合规声明。",
    ]
    if fidelity in ("mock", "frozen_fixture"):
        limitations.append(f"target 保真度={fidelity}：不对真实生产主机/网络作安全声明。")

    if isinstance(prov, AutomaticRuleProvenance):
        if prov.measurement_kind == "statistical_trials":
            uncertainty, reproducibility = "statistical_ci", "protocol"
            limitations.append("统计探针：结论受 n_runs 与 CI 宽度限；场景代表性仍有限。")
        else:  # deterministic_observation
            uncertainty, reproducibility = "deterministic", "bit"
        return ConfidenceBasis(adjudication="automatic_rule", uncertainty=uncertainty,
                               reproducibility=reproducibility, target_fidelity=fidelity,
                               limitations=limitations)

    # HumanAttestationProvenance：authority 只单值 unverified → 入 limitations（收窄 warrant）。
    limitations.append(
        "人工裁定权威=unverified：确认『某 reviewer 作出此决定』，但其身份/独立性/判断正确性未二次核实。")
    return ConfidenceBasis(adjudication="human_attestation", uncertainty="unquantified",
                           reproducibility="declarative", target_fidelity=fidelity,
                           limitations=limitations)


def _claim_scope(finding: Finding, mctx: dict[str, Any]) -> dict[str, Any]:
    measured = {k: mctx.get(k) for k in ("control_id", "execution_backend", "rule_version") if k in mctx}
    return {"assurance_level": "none", "control_id": finding.control_id,
            "target_ref": finding.target_ref, "measurement": measured,
            "confidence_rule_version": CONFIDENCE_RULE_VERSION}


def _claim_for_finding(finding: Finding, mctx: dict[str, Any]) -> Claim:
    scope = _claim_scope(finding, mctx)
    if finding.verdict_provenance is None:
        # fail-closed：缺 provenance 不赋 confidence（历史/未回填 Finding）。
        return Claim(control_id=finding.control_id, finding_id=finding.finding_id,
                     finding_status=finding.status, verdict_provenance=None,
                     confidence_basis=None, claim_scope=scope, assessable=False,
                     unassessable_reason=(
                         "verdict_provenance 缺失（历史/未回填 Finding）→ 无法确立 confidence 依据，"
                         "fail-closed，不赋乐观档。"))
    basis = _confidence_basis(finding.verdict_provenance, mctx)
    return Claim(control_id=finding.control_id, finding_id=finding.finding_id,
                 finding_status=finding.status, verdict_provenance=finding.verdict_provenance,
                 confidence_basis=basis, claim_scope=scope, assessable=True)


def derive_claims(report: AssuranceReport) -> list[Claim]:
    """report → Finding-backed Claim 列表。0-Finding → 空 list（Unassessed，绝不静默产正向 Claim）。"""
    mctx = report.measurement_context
    return [_claim_for_finding(f, mctx) for f in report.findings]
