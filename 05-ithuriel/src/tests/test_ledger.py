"""CoverageLedger 代码契约（桶 B，ADR-0014）——跨 3 真实控制 rollup + ontology gating。

用真实 builder 产 report（PI-01 AI / FW-03 config / FW-01 probe），验冻结 scoring 规则：
coverage=pass 占适用控制、High/Critical fail→not_ready、not_applicable 出分母、gap 进分母。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ithuriel.config_inspection import build_report as fw03_report
from ithuriel.derive import derive
from ithuriel.executor import NetworkPortScanAction, RoEAuthorization
from ithuriel.ledger import build_ledger, control_outcome
from ithuriel.models import (
    AssuranceReport,
    EvidenceManifest,
    Finding,
    ScopeStatement,
    content_hash,
)
from ithuriel.port_scan import DeclaredService
from ithuriel.port_scan import build_report as fw01_report
from ithuriel.registry import control, referenced_standards

FIXD = Path(__file__).parent / "fixtures"
UFW = FIXD / "ufw"
NMAP = FIXD / "nmap"


# ── 真实 report 工厂 ─────────────────────────────────────────────────────────
def _pi01(fixture="d8_run_detector.json"):  # detector→defended pass；spotlighting→defended fail
    return derive(json.loads((FIXD / fixture).read_text()))


def _fw03(fixture="deny_active.txt"):        # deny→pass；allow→fail(Medium)
    return fw03_report((UFW / fixture).read_text(), host_id="h")


def _fw01(status="pass"):
    a = NetworkPortScanAction(target_ip="192.0.2.10", ports=(22, 80, 443))
    roe = RoEAuthorization(roe_version="v", allowed_targets=["192.0.2.0/24"])
    xml = (NMAP / "open_22_443.xml").read_text()
    if status == "gap":
        roe = RoEAuthorization(roe_version="v", allowed_targets=["10.0.0.0/8"])  # 未授权→gap
        decl = None
    elif status == "fail":
        decl = [DeclaredService(port=443, owner="s", justification_ref="CHG")]   # 22 未声明→fail
    else:
        decl = [DeclaredService(port=22, owner="s", justification_ref="A"),
                DeclaredService(port=443, owner="s", justification_ref="B")]
    return fw01_report(action=a, roe=roe, nmap_xml=xml, fixture_ref="fx", host_id="h",
                       declared_services=decl)


def _axis(ledger, key):
    return next(a for a in ledger.axes if a.key == key)


# ── 归约 ─────────────────────────────────────────────────────────────────────
def test_multi_finding_reduces_to_defended():
    # PI-01 detector：bare fail + defended pass → rollup 取 defended → pass。
    o = control_outcome(_pi01())
    assert o.control_id == "AI-AGENT-PI-01" and o.domain == "ai_agent_security"
    assert o.severity == "High" and o.status == "pass"


def test_zero_finding_reduces_to_gap():
    o = control_outcome(_fw01("gap"))
    assert o.status == "gap" and o.gap_kind == "out_of_scope"


# ── rollup：全 pass ──────────────────────────────────────────────────────────
def test_all_pass_full_coverage():
    ledger = build_ledger([_pi01(), _fw03(), _fw01("pass")])
    ai = _axis(ledger, "ai_agent_security")
    net = _axis(ledger, "network_security")
    assert (ai.applicable, ai.passed, ai.coverage, ai.not_ready) == (1, 1, 1.0, False)
    assert (net.applicable, net.passed, net.coverage, net.not_ready) == (2, 2, 1.0, False)


# ── gating：High fail → not_ready；Medium fail 只降覆盖 ───────────────────────
def test_high_severity_fail_marks_axis_not_ready():
    # PI-01 spotlighting：defended fail、severity High → ai_agent_security not_ready。
    ledger = build_ledger([_pi01("d8_run_spotlighting.json"), _fw03(), _fw01("pass")])
    ai = _axis(ledger, "ai_agent_security")
    assert ai.not_ready is True and "AI-AGENT-PI-01" in ai.gating_reason
    assert ai.passed == 0 and ai.coverage == 0.0


def test_medium_fail_lowers_coverage_but_not_gating():
    # FW-01 fail（Medium）：network_security 覆盖降到 1/2，但 Medium 不 gate → 仍 ready。
    ledger = build_ledger([_fw03("deny_active.txt"), _fw01("fail")])
    net = _axis(ledger, "network_security")
    assert (net.applicable, net.passed, net.coverage) == (2, 1, 0.5)
    assert net.not_ready is False       # Medium fail 不触发 gating


# ── 分母语义：gap 进分母、not_applicable 出分母 ──────────────────────────────
def test_gap_counts_in_denominator_not_passed():
    # FW-01 gap（RoE 未授权）：进分母、非 pass → 覆盖 1/2。
    ledger = build_ledger([_fw03("deny_active.txt"), _fw01("gap")])
    net = _axis(ledger, "network_security")
    assert net.applicable == 2 and net.passed == 1 and net.coverage == 0.5


def _na_report(control_id="CE-UK-FW-03"):
    ctrl = control(control_id)
    na = Finding(control_id=control_id, target_ref={}, status="not_applicable",
                 verdict_mode="automatic", assessed_at="2026-07-13T00:00:00+00:00",
                 evidence_refs=[], rationale="genuinely inapplicable to this target")
    mctx = {"control_id": control_id}
    scope = ScopeStatement(claim="na", in_scope={}, not_covered=[], measurement_valid=False,
                           underpowered=None)
    return AssuranceReport(
        generated_from="test", measurement_context=mctx,
        evidence_manifest=EvidenceManifest(run_root=content_hash({"na": control_id}, prefix="run:"),
                                           measurement_context=mctx, artifacts={}, index={}),
        findings=[na], comparisons=[], scope=scope, control=ctrl, referenced_standards={})


def test_not_applicable_excluded_from_denominator():
    # NA 出分母：network_security 只算 FW-03（applicable=1），NA 的 FW 控制不进分母。
    ledger = build_ledger([_fw03("deny_active.txt"), _na_report("CE-UK-FW-01")])
    net = _axis(ledger, "network_security")
    assert net.applicable == 1 and net.passed == 1 and net.coverage == 1.0


def test_ledger_carries_all_outcomes():
    ledger = build_ledger([_pi01(), _fw03(), _fw01("pass")], generated_from=["a", "b"])
    assert len(ledger.outcomes) == 3
    assert {o.control_id for o in ledger.outcomes} == {"AI-AGENT-PI-01", "CE-UK-FW-03", "CE-UK-FW-01"}
    assert ledger.generated_from == ["a", "b"]
