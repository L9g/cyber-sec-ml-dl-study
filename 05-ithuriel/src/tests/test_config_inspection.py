"""slice 2 代码契约（确定性、与模型无关）——CE-UK-FW-03 config-inspection（ADR-0012）。

压测「AI 切片模型能否承载确定性裁定」：Finding(run_record=None)/无 ComparisonSpec/审计闭环复用。
断言全是确定性结构契约（不随种子/模型漂移）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ithuriel.capability import AdapterDescriptor, adapter_satisfies
from ithuriel.config_inspection import (
    CONTROL_ID,
    RULE_VERSION,
    UFW_ADAPTER,
    build_report,
    evaluate_default_deny,
    parse_ufw_status,
)

FIX = Path(__file__).parent / "fixtures" / "ufw"


def _raw(name: str) -> str:
    return (FIX / name).read_text()


# ── 解析 + 规则（纯函数、测试矩阵）───────────────────────────────────────────
def test_parse_deny_active():
    obs = parse_ufw_status(_raw("deny_active.txt"))
    assert obs["status"] == "active" and obs["incoming_default"] == "deny"


def test_matrix_deny_active_pass():
    assert evaluate_default_deny(parse_ufw_status(_raw("deny_active.txt")))[0] == "pass"


def test_matrix_allow_active_fail():
    assert evaluate_default_deny(parse_ufw_status(_raw("allow_active.txt")))[0] == "fail"


def test_matrix_inactive_inconclusive_by_default():
    # ⭐ 认识论纪律：UFW inactive 推不出无 default-deny（可能 nftables 等在执行）→ inconclusive，非 fail。
    status, rationale = evaluate_default_deny(parse_ufw_status(_raw("inactive.txt")))
    assert status == "inconclusive" and "唯一权威执行面" in rationale


def test_matrix_inactive_fail_only_when_sole_authority():
    # 仅当 TargetSnapshot 声明 UFW 为唯一权威执行面 → inactive 才可判 fail。
    status, _ = evaluate_default_deny(parse_ufw_status(_raw("inactive.txt")), sole_authority=True)
    assert status == "fail"


def test_matrix_truncated_inconclusive():
    # active 但缺 Default 行（截断）→ 不可裁定。
    assert evaluate_default_deny(parse_ufw_status(_raw("truncated_active.txt")))[0] == "inconclusive"


def test_matrix_unknown_format_inconclusive():
    # 无 Status 行（格式未知）→ 不可裁定（不是 fail、不是 pass）。
    assert evaluate_default_deny(parse_ufw_status(_raw("unknown_format.txt")))[0] == "inconclusive"


# ── capability 匹配（seams #3 首实例）─────────────────────────────────────────
def test_capability_match_subset():
    assert adapter_satisfies(CONTROL_ID, UFW_ADAPTER) is True


def test_capability_mismatch_yields_unsupported_not_finding():
    # adapter 不提供所需 capability → 覆盖缺口（findings=[]，进分母），非 not_applicable/pass。
    wrong = AdapterDescriptor(adapter_id="nmap_probe", provides={"host.port.scan"},
                              input_format="nmap-xml/v1")
    rep = build_report(_raw("deny_active.txt"), host_id="h1", adapter=wrong)
    assert rep.findings == [] and rep.comparisons == []
    assert rep.scope.invalidity_reasons == ["tooling_unsupported"]
    assert any("unsupported" in g for g in rep.scope.not_covered)


# ── AssuranceReport 形状（复用 AI 切片模型，压测确定性容纳）───────────────────
@pytest.fixture
def pass_report():
    return build_report(_raw("deny_active.txt"), host_id="host-01")


@pytest.fixture
def fail_report():
    return build_report(_raw("allow_active.txt"), host_id="host-01")


def test_finding_deterministic_has_no_run_record(pass_report):
    # ⭐ 核心观察：确定性 Finding run_record=None，现有 Finding 自然容纳（无需 AI ai_run_record）。
    assert len(pass_report.findings) == 1
    f = pass_report.findings[0]
    assert f.status == "pass" and f.run_record is None
    assert f.verdict_mode == "automatic"      # registry：确定性 detector
    assert f.severity is None and f.root_causes is None  # pass 无 severity；root_cause_enum 是 AI 机理不适用


def test_fail_finding_medium_severity_and_rationale(fail_report):
    f = fail_report.findings[0]
    assert f.status == "fail"
    assert f.severity == "Medium"             # registry severity_if_failed（对比 PI-01 的 High）
    assert f.rationale and "default-deny" in f.rationale
    assert f.run_record is None               # fail 也无 AI run
    assert f.root_causes is None              # 防火墙失败无 P1–P6 机理


def test_no_comparison_spec_report_still_complete(pass_report):
    # ⭐ 无 bare/defended → comparisons=[]，AssuranceReport 仍语义完整（scope/control/standards 齐）。
    assert pass_report.comparisons == []
    assert pass_report.scope.assurance_level == "none"
    assert pass_report.control is not None and pass_report.control.id == CONTROL_ID


def test_audit_closure_reused(pass_report):
    # 审计闭环复用（档 3）：Finding.control_id → standards_refs → 注册表 source → StandardEntry。
    refs = pass_report.referenced_standards
    assert refs and all(e.name for e in refs.values())
    assert any("Cyber Essentials" in e.name for e in refs.values())


def test_evidence_manifest_carries_config_snapshot(pass_report):
    # EvidenceManifest 承载确定性配置快照（非 AI trial）：index 用 "config" 键、raw 内容寻址。
    m = pass_report.evidence_manifest
    assert list(m.index.keys()) == ["config"] and len(m.index["config"]) == 1
    h = m.index["config"][0]
    assert h.startswith("cfg:") and m.artifacts[h]["kind"] == "ufw-status-verbose/v1"
    assert pass_report.findings[0].evidence_refs == [h]


def test_measurement_context_discloses_provisional_bridge_and_opaque_plugin(pass_report):
    mctx = pass_report.measurement_context
    assert mctx["capability_required"] == ["host.firewall.default_policy.inspect"]
    assert mctx["capability_bridge"]["status"] == "provisional"   # 如实披露 code-local bridge
    assert mctx["legacy_plugin_opaque"] == "firewall_default_deny_check"  # plugin 不透明、不参与匹配
    assert mctx["rule_version"] == RULE_VERSION


def test_run_root_bit_reproducible():
    r1 = build_report(_raw("deny_active.txt"), host_id="h")
    r2 = build_report(_raw("deny_active.txt"), host_id="h")
    assert r1.evidence_manifest.run_root == r2.evidence_manifest.run_root
