"""Step 3（ADR-0016）：Claim Deriver 纯函数 + confidence_basis 派生。

覆盖：4 shape 派生正确 · fail-closed 两处（0-Finding 空 list / 无 provenance assessable=False）·
claim_id 稳定与敏感（provenance/fidelity 变则变）· 纯函数不 mutate · confidence 不 override status。
Step 4 未做（producer 未回填）→ 真 producer 报告的 Finding 仍 provenance=None，故含一条端到端 fail-closed。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ithuriel.claim import derive_claims
from ithuriel.config_inspection import build_report as config_report
from ithuriel.models import (
    AssuranceReport,
    AutomaticRuleProvenance,
    EvidenceManifest,
    Finding,
    HumanAttestationProvenance,
    ScopeStatement,
)

FX = Path(__file__).parent / "fixtures"


# ── 最小 report 构造（Step 4 前 producer 未回填 → 测试自带 provenance 的 Finding）─────
def _report(findings, execution_backend="agentdojo-mock", extra_mctx=None):
    mctx = {"control_id": "C", "execution_backend": execution_backend}
    if extra_mctx:
        mctx.update(extra_mctx)
    manifest = EvidenceManifest(run_root="run:x", measurement_context=mctx, artifacts={}, index={})
    scope = ScopeStatement(claim="c", in_scope={}, not_covered=[],
                           measurement_valid=True, underpowered=None)
    return AssuranceReport(generated_from="t", measurement_context=mctx,
                           evidence_manifest=manifest, findings=findings, comparisons=[], scope=scope)


def _finding(status="pass", *, provenance=None, ctrl="C", tref=None, refs=None, **kw):
    tref = tref if tref is not None else {"id": "t1"}
    refs = refs if refs is not None else ["e1"]
    base = dict(control_id=ctrl, target_ref=tref, status=status, verdict_mode="automatic",
                assessed_at="2026-07-13T00:00:00+00:00", evidence_refs=refs,
                verdict_provenance=provenance)
    base.update(kw)
    return Finding(**base)


def _auto(kind="statistical_trials", rule="r/v1"):
    return AutomaticRuleProvenance(rule_version=rule, measurement_kind=kind)


def _human():
    return HumanAttestationProvenance(decision_evidence_ref="att:abc", mapping_version="m/v1")


# ── 4 shape 派生正确 ─────────────────────────────────────────────────────────
def test_ai_basis_statistical():
    rep = _report([_finding("fail", provenance=_auto("statistical_trials"),
                            severity="High", rationale="hijack")],
                  execution_backend="agentdojo-mock")
    c = derive_claims(rep)[0]
    assert c.assessable and c.finding_status == "fail"
    b = c.confidence_basis
    assert (b.adjudication, b.uncertainty, b.reproducibility, b.target_fidelity) == \
        ("automatic_rule", "statistical_ci", "protocol", "mock")


def test_config_basis_deterministic_frozen():
    rep = _report([_finding("pass", provenance=_auto("deterministic_observation"))],
                  execution_backend="frozen-fixture")
    b = derive_claims(rep)[0].confidence_basis
    assert (b.adjudication, b.uncertainty, b.reproducibility, b.target_fidelity) == \
        ("automatic_rule", "deterministic", "bit", "frozen_fixture")


def test_probe_basis_deterministic_mock_differs_from_config_only_by_fidelity():
    """probe 与 config 同 automatic_rule/deterministic → 只 target_fidelity 不同（#A 摩擦的正解）。"""
    rep = _report([_finding("pass", provenance=_auto("deterministic_observation"))],
                  execution_backend="mock")
    b = derive_claims(rep)[0].confidence_basis
    assert (b.uncertainty, b.reproducibility, b.target_fidelity) == ("deterministic", "bit", "mock")


def test_human_basis_declarative_with_authority_limitation():
    rep = _report([_finding("pass", provenance=_human())], execution_backend="frozen-fixture")
    b = derive_claims(rep)[0].confidence_basis
    assert (b.adjudication, b.uncertainty, b.reproducibility) == \
        ("human_attestation", "unquantified", "declarative")
    assert any("authority=unverified" in x or "权威=unverified" in x for x in b.limitations)


# ── fail-closed 两处 ─────────────────────────────────────────────────────────
def test_zero_finding_report_yields_empty_list_not_positive_claim():
    """0-Finding → 空 list（Unassessed），绝不静默产正向 Claim（决策③，ScopeGap 得以延后）。"""
    assert derive_claims(_report([])) == []


def test_missing_provenance_is_fail_closed():
    """Finding 有但 verdict_provenance 缺 → assessable=False、basis=None、带 reason（不赋乐观档）。"""
    c = derive_claims(_report([_finding("pass", provenance=None)]))[0]
    assert c.assessable is False
    assert c.confidence_basis is None
    assert c.unassessable_reason and "fail-closed" in c.unassessable_reason


def test_real_config_report_assessable_after_backfill():
    """端到端（Step 4 已回填）：真 config producer → assessable Claim，basis=det/bit/frozen_fixture。"""
    rep = config_report((FX / "ufw" / "deny_active.txt").read_text(), host_id="host-01")
    claims = derive_claims(rep)
    assert len(claims) == 1 and claims[0].assessable is True
    b = claims[0].confidence_basis
    assert (b.adjudication, b.uncertainty, b.reproducibility, b.target_fidelity) == \
        ("automatic_rule", "deterministic", "bit", "frozen_fixture")


def test_all_four_producers_assessable_end_to_end():
    """Step 4 回填在**四 shape 全生效**：每 producer 真报告的每条 Finding → assessable Claim，basis 对。"""
    import json as _json

    from ithuriel.attestation import ExceptionEntry, ReviewAttestation
    from ithuriel.attestation import build_report as attest_report
    from ithuriel.derive import derive
    from ithuriel.executor import NetworkPortScanAction, RoEAuthorization
    from ithuriel.port_scan import DeclaredService
    from ithuriel.port_scan import build_report as probe_report

    ai = derive(_json.loads((FX / "d8_run_detector.json").read_text()))
    prb = probe_report(
        action=NetworkPortScanAction(target_ip="192.0.2.10", ports=[22, 443]),
        roe=RoEAuthorization(roe_version="roe-v1", allowed_targets=["192.0.2.0/24"]),
        nmap_xml=(FX / "nmap" / "open_22_443.xml").read_text(), fixture_ref="fixture:nmap-1",
        host_id="host-01",
        declared_services=[DeclaredService(port=22, owner="svc", justification_ref="j1"),
                           DeclaredService(port=443, owner="svc", justification_ref="j2")])
    reg = [ExceptionEntry(**e) for e in
           _json.loads((FX / "attestation" / "register_complete.json").read_text())["entries"]]
    at = attest_report(register=reg, host_id="host-01", attestation=ReviewAttestation(
        **_json.loads((FX / "attestation" / "attestation_conformant.json").read_text())))

    # AI：两条 Finding（bare/defended）均 assessable + statistical/protocol/mock
    ai_claims = derive_claims(ai)
    assert len(ai_claims) == 2 and all(c.assessable for c in ai_claims)
    for c in ai_claims:
        b = c.confidence_basis
        assert (b.uncertainty, b.reproducibility, b.target_fidelity) == \
            ("statistical_ci", "protocol", "mock")

    # probe：det/bit/mock（与 config 同变体、只 fidelity 不同）
    pc = derive_claims(prb)[0]
    assert pc.assessable
    assert (pc.confidence_basis.uncertainty, pc.confidence_basis.reproducibility,
            pc.confidence_basis.target_fidelity) == ("deterministic", "bit", "mock")

    # attestation：human_attestation/unquantified/declarative + decision_evidence_ref 引用已存 att:
    ac = derive_claims(at)[0]
    assert ac.assessable and ac.confidence_basis.adjudication == "human_attestation"
    assert ac.verdict_provenance.decision_evidence_ref.startswith("att:")
    assert ac.verdict_provenance.decision_evidence_ref in at.findings[0].evidence_refs


# ── claim_id 稳定与敏感 ──────────────────────────────────────────────────────
def test_claim_id_stable_for_same_inputs():
    f = _finding("pass", provenance=_auto("deterministic_observation"))
    a = derive_claims(_report([f], execution_backend="mock"))[0]
    b = derive_claims(_report([f], execution_backend="mock"))[0]
    assert a.claim_id == b.claim_id and a.claim_id.startswith("claim:")


def test_claim_id_differs_when_fidelity_differs_same_finding():
    """搭档要求：同一 Finding、不同 fidelity → basis 与 claim_id 都不同（不让同 id 承载不同置信度）。"""
    f = _finding("pass", provenance=_auto("deterministic_observation"))
    mock = derive_claims(_report([f], execution_backend="mock"))[0]
    frozen = derive_claims(_report([f], execution_backend="frozen-fixture"))[0]
    assert f.finding_id == f.finding_id                       # 同一底层 Finding
    assert mock.confidence_basis.target_fidelity != frozen.confidence_basis.target_fidelity
    assert mock.claim_id != frozen.claim_id


def test_claim_id_differs_when_provenance_differs():
    f_stat = _finding("pass", provenance=_auto("statistical_trials"))
    f_det = _finding("pass", provenance=_auto("deterministic_observation"))
    a = derive_claims(_report([f_stat]))[0]
    b = derive_claims(_report([f_det]))[0]
    assert a.claim_id != b.claim_id


# ── 纯函数 + 不 override ─────────────────────────────────────────────────────
def test_deriver_does_not_mutate_finding():
    f = _finding("fail", provenance=_auto("statistical_trials"), severity="High", rationale="x")
    before = f.model_dump()
    derive_claims(_report([f]))
    assert f.model_dump() == before


def test_confidence_does_not_override_status():
    """confidence 描述『怎么得来』、正交于『是什么』——claim 只回显 finding.status，不改判。"""
    for st, kw in [("pass", {}), ("inconclusive", {"rationale": "r"}),
                   ("fail", {"severity": "High", "rationale": "r"})]:
        f = _finding(st, provenance=_auto("deterministic_observation"), **kw)
        assert derive_claims(_report([f]))[0].finding_status == st
