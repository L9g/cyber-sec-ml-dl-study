"""CE-UK-SU-03 human_review 切片代码契约（slice 4 / ADR-0015）。

压测第 4 形状：非 automatic 裁定（human_review）+ 声明式证据（非工具产出）能否被共享 Assurance
契约承载。断言全确定性。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ithuriel.attestation import (
    CONTROL_ID,
    ExceptionEntry,
    REGISTER_ADAPTER,
    ReviewAttestation,
    build_report,
)
from ithuriel.capability import AdapterDescriptor

FIX = Path(__file__).parent / "fixtures" / "attestation"


def _register(name="register_complete.json"):
    return [ExceptionEntry(**e) for e in json.loads((FIX / name).read_text())["entries"]]


def _attest(name):
    return ReviewAttestation(**json.loads((FIX / name).read_text()))


def _report(register="register_complete.json", attestation="attestation_conformant.json"):
    att = _attest(attestation) if attestation else None
    return build_report(register=_register(register), attestation=att, host_id="host-01")


# ── human_review 裁定矩阵：verdict 是 reviewer 的 ────────────────────────────
def test_conformant_attestation_pass_human_review():
    f = _report().findings[0]
    assert f.status == "pass"
    assert f.verdict_mode == "human_review"       # ⭐ 前三片都 automatic
    assert f.run_record is None
    assert "reviewer=j.smith" in f.rationale       # 承载人工裁定溯源


def test_non_conformant_attestation_fail_low_severity():
    f = _report(attestation="attestation_non_conformant.json").findings[0]
    assert f.status == "fail" and f.severity == "Low"   # 第三个 severity 档（前有 High/Medium）
    assert f.verdict_mode == "human_review" and f.rationale


def test_no_attestation_is_inconclusive_not_pass():
    # ⭐ 无 reviewer attestation → 无人工裁定可承载 → inconclusive（非 pass）。
    rep = _report(attestation=None)
    f = rep.findings[0]
    assert f.status == "inconclusive" and "无 reviewer attestation" in f.rationale
    assert rep.scope.measurement_valid is False    # 无裁定可承载 = 测量无效


# ── advisory：结构差异 surface、不 override 人工裁定 ─────────────────────────
def test_incomplete_register_surfaces_advisory_without_overriding():
    # reviewer 裁定 conformant，但登记有条目缺 justification → 仍 pass（承载人工裁定），rationale 带 advisory。
    # ⚠ attested_refs 必须解析到**本次**登记（partner review C5）。此处用 EXC-001/EXC-003
    # 与 register_incomplete 对齐，保持本测试原意：测的是「结构差异不 override 人工裁定」，
    # 而不是「引用挂不上这份 artifact」——后者是 measurement validity，另有测试覆盖。
    att = ReviewAttestation(**{**json.loads((FIX / "attestation_conformant.json").read_text()),
                               "attested_refs": ["EXC-001", "EXC-003"]})
    rep = build_report(register=_register("register_incomplete.json"),
                       attestation=att, host_id="h")
    f = rep.findings[0]
    assert f.status == "pass"                       # 不被结构差异 override
    assert "advisory" in f.rationale and "EXC-003" in f.rationale
    assert rep.measurement_context["register_completeness"]["unjustified_ids"] == ["EXC-003"]


# ── ⭐ verdict_source 摩擦：reviewer 溯源落 mctx（无 Finding typed review record）──────
def test_review_record_lands_in_measurement_context():
    mctx = _report().measurement_context
    assert mctx["verdict_mode"] == "human_review"
    assert mctx["review_record"]["reviewer"] == "j.smith (security lead)"
    assert mctx["review_record"]["decision"] == "conformant"
    assert mctx["attestation_mapping_version"] == "human-review-attestation/v1"
    # Finding 上无对应 typed review record（= verdict_source 候选摩擦，见 ADR-0015）。
    assert _report().findings[0].run_record is None


# ── 证据是声明记录（非工具产出）+ 审计闭环 ───────────────────────────────────
def test_declared_evidence_and_no_comparison(report_fixture=None):
    rep = _report()
    assert rep.comparisons == []                    # 非 bare/defended
    m = rep.evidence_manifest
    assert list(m.index.keys()) == ["attestation"] and len(m.index["attestation"]) == 2  # 登记 + attestation
    reg_hash = m.index["attestation"][0]
    assert reg_hash.startswith("reg:") and m.artifacts[reg_hash]["kind"] == "change-exception-register/v1"


def test_audit_closure_reused():
    refs = _report().referenced_standards
    assert refs and any("Cyber Essentials" in e.name for e in refs.values())
    assert _report().control.id == CONTROL_ID


def test_scope_declares_human_verdict_boundary():
    joined = " ".join(_report().scope.not_covered)
    assert "verdict 由 reviewer 出具" in joined


# ── capability 不匹配 → unsupported gap ──────────────────────────────────────
def test_capability_mismatch_unsupported_gap():
    wrong = AdapterDescriptor(adapter_id="nmap", provides={"host.network.port_scan"},
                              input_format="nmap-xml/v1")
    rep = build_report(register=_register(), attestation=_attest("attestation_conformant.json"),
                       host_id="h", adapter=wrong)
    assert rep.findings == [] and rep.scope.invalidity_reasons == ["tooling_unsupported"]


def test_run_root_bit_reproducible():
    assert _report().evidence_manifest.run_root == _report().evidence_manifest.run_root


# ── partner review 2026-07-22 C5：结构不完整的 attestation 不得产出保证层 pass ──
@pytest.mark.parametrize("kw,why", [
    (dict(reviewer="", review_date="2026-06-30", decision="conformant",
          statement="s", attested_refs=["EXC-001"]), "无可归责的人"),
    (dict(reviewer="r", review_date="2026-06-30", decision="conformant",
          statement="", attested_refs=["EXC-001"]), "无声明"),
    (dict(reviewer="r", review_date="last tuesday", decision="conformant",
          statement="s", attested_refs=["EXC-001"]), "日期不可解析"),
    (dict(reviewer="r", review_date="2026-06-30", decision="conformant",
          statement="s", attested_refs=[]), "下结论却未声明所审材料"),
])
def test_incomplete_attestation_refused_at_construction(kw, why):
    with pytest.raises(Exception):
        ReviewAttestation(**kw)


def test_insufficient_evidence_may_omit_refs():
    # 「证据不足」本身就可能意味着没有可引用的材料，不强制 attested_refs。
    a = ReviewAttestation(reviewer="r", review_date="2026-06-30",
                          decision="insufficient_evidence", statement="材料不足")
    assert a.attested_refs == []


def test_refs_not_resolvable_degrades_to_inconclusive_not_pass():
    # 引用挂不到本次登记 = reviewer 审的是另一份材料 → measurement validity 问题，
    # **不是** ADR-0015 说的「结构差异不 override 人工裁定」，故降 inconclusive 而非 pass。
    att = ReviewAttestation(**{**json.loads((FIX / "attestation_conformant.json").read_text()),
                               "attested_refs": ["EXC-999"]})
    rep = build_report(register=_register("register_complete.json"), attestation=att, host_id="h")
    f = rep.findings[0]
    assert f.status == "inconclusive"
    assert "EXC-999" in f.rationale and "无法解析" in f.rationale
