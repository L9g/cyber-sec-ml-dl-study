"""CE-UK-FW-01 主动探测切片代码契约（slice 3 / ADR-0013）。

压测：identified≠justified（无 inventory→inconclusive）、RoE 拒绝→out_of_scope gap（非 Finding）、
执行事实经 Ithuriel 解释成 Finding、复用 slice 2 已验证的 Assurance 契约。零真实网络 I/O。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ithuriel.executor import NetworkPortScanAction, RoEAuthorization
from ithuriel.port_scan import (
    CONTROL_ID,
    DeclaredService,
    build_report,
    evaluate_fw01,
    parse_nmap_open_ports,
)

FIX = Path(__file__).parent / "fixtures" / "nmap"


def _xml(name="open_22_443.xml"):
    return (FIX / name).read_text()


def _action(ports=(22, 80, 443)):
    return NetworkPortScanAction(target_ip="192.0.2.10", ports=ports)


def _roe():
    return RoEAuthorization(roe_version="roe-v1", allowed_targets=["192.0.2.0/24"])


def _declared(*specs):
    # specs: (port, justification_ref) —— justification_ref="" 表示已声明但未 justified
    return [DeclaredService(port=p, owner="svc", justification_ref=j) for p, j in specs]


# ── 解析 + 规则 ──────────────────────────────────────────────────────────────
def test_parse_open_ports_ignores_closed():
    obs = parse_nmap_open_ports(_xml())
    assert obs["parse_ok"] is True
    assert {p["port"] for p in obs["open_ports"]} == {22, 443}   # 80 closed 不计


def test_rule_pass_all_justified():
    obs = parse_nmap_open_ports(_xml())
    status, _ = evaluate_fw01(obs, _declared((22, "CHG-1"), (443, "CHG-2")))
    assert status == "pass"


def test_rule_fail_undeclared_open_port():
    # 443 justified、22 未声明 → 22 是未 justified 的 exposed 端口 → fail。
    obs = parse_nmap_open_ports(_xml())
    status, rationale = evaluate_fw01(obs, _declared((443, "CHG-2")))
    assert status == "fail" and "22" in rationale


def test_rule_declared_but_not_justified_counts_as_undeclared():
    # 22 声明了但 justification_ref 为空（未 justified）→ 仍算未 justified → fail。
    obs = parse_nmap_open_ports(_xml())
    status, _ = evaluate_fw01(obs, _declared((22, ""), (443, "CHG-2")))
    assert status == "fail"


def test_rule_no_inventory_is_inconclusive_not_pass():
    # ⭐ identified≠justified：扫描成功解析出端口，但无 justification inventory → inconclusive、非 pass。
    obs = parse_nmap_open_ports(_xml())
    status, rationale = evaluate_fw01(obs, None)
    assert status == "inconclusive" and "justified" in rationale


def test_rule_malformed_xml_inconclusive():
    obs = parse_nmap_open_ports(_xml("malformed.xml"))
    assert obs["parse_ok"] is False
    assert evaluate_fw01(obs, _declared((22, "x")))[0] == "inconclusive"


# ── 报告：happy path（复用 Assurance 契约）─────────────────────────────────────
@pytest.fixture
def pass_report():
    return build_report(action=_action(), roe=_roe(), nmap_xml=_xml(), fixture_ref="fixture:nmap-1",
                        host_id="host-01", declared_services=_declared((22, "CHG-1"), (443, "CHG-2")))


def test_pass_finding_shape(pass_report):
    assert len(pass_report.findings) == 1
    f = pass_report.findings[0]
    assert f.status == "pass" and f.run_record is None and f.verdict_mode == "automatic"
    assert pass_report.comparisons == []              # 非 bare/defended
    assert pass_report.scope.assurance_level == "none"


def test_fail_report_medium_severity():
    rep = build_report(action=_action(), roe=_roe(), nmap_xml=_xml(), fixture_ref="fixture:nmap-1",
                       host_id="h", declared_services=_declared((443, "CHG-2")))
    f = rep.findings[0]
    assert f.status == "fail" and f.severity == "Medium" and f.rationale


def test_execution_receipt_in_evidence_as_fact(pass_report):
    # ExecutionReceipt 进 evidence（执行事实），但 no_real_network_io 机器可读、Finding 由 Ithuriel 解释。
    mctx = pass_report.measurement_context
    assert mctx["no_real_network_io"] is True
    assert mctx["execution_receipt"]["external_side_effects_performed"] is False
    assert mctx["execution_receipt"]["backend"] == "mock"
    assert mctx["compiled_argv"][-1] == "192.0.2.10"       # argv 可审计、target 严格一致
    # receipt 不含 status/finding
    assert "status" not in mctx["execution_receipt"]


def test_audit_closure_reused(pass_report):
    refs = pass_report.referenced_standards
    assert refs and any("Cyber Essentials" in e.name for e in refs.values())
    assert pass_report.control.id == CONTROL_ID


def test_no_real_world_claim_in_scope(pass_report):
    joined = " ".join(pass_report.scope.not_covered)
    assert "不对 fixture 中地址作现实安全声明" in joined and "零真实网络" in pass_report.scope.claim


# ── RoE 拒绝 → out_of_scope gap（非 Finding、非 unsupported）───────────────────
def test_roe_denial_yields_out_of_scope_gap_not_finding():
    unauth = RoEAuthorization(roe_version="roe-v1", allowed_targets=["10.0.0.0/8"])  # 不含 192.0.2.10
    rep = build_report(action=_action(), roe=unauth, nmap_xml=_xml(), fixture_ref="fixture:nmap-1",
                       host_id="h")
    assert rep.findings == [] and rep.comparisons == []      # 不产 Finding
    assert rep.measurement_context["gap_kind"] == "out_of_scope"
    assert rep.measurement_context["gap_reason"].endswith("target_not_authorized")
    joined = " ".join(rep.scope.not_covered)
    assert "out_of_scope" in joined and "≠ unsupported" in joined
    # 不借错义：invalidity_reasons 不塞 tooling_unsupported（工具有能力）。
    assert rep.scope.invalidity_reasons == []


def test_roe_empty_targets_default_deny_gap():
    rep = build_report(action=_action(), roe=RoEAuthorization(roe_version="v", allowed_targets=[]),
                       nmap_xml=_xml(), fixture_ref="fixture:nmap-1", host_id="h")
    assert rep.findings == [] and rep.measurement_context["gap_kind"] == "out_of_scope"


def test_run_root_bit_reproducible():
    kw = dict(action=_action(), roe=_roe(), nmap_xml=_xml(), fixture_ref="fixture:nmap-1",
              host_id="h", declared_services=_declared((22, "x"), (443, "y")))
    assert build_report(**kw).evidence_manifest.run_root == build_report(**kw).evidence_manifest.run_root
