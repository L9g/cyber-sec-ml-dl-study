"""控制注册表代码契约（确定性）——档 3，ADR-0008。

两半：① `Registry` 加载真 profile + schema 不变量牙齿（standards_ref.source 悬空 → raise）；
② derive 接线（severity/verdict 从注册表解析、standards 挂报告层）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ithuriel.derive import derive
from ithuriel.models import Registry
from ithuriel.registry import default_control, load_registry, referenced_standards

FIXTURE = Path(__file__).parent / "fixtures" / "d8_run_detector.json"


# ── ① Registry 加载 + 不变量 ────────────────────────────────────────────────
def test_real_profile_loads_and_validates():
    r = load_registry()
    assert "AI-AGENT-PI-01" in r.controls and "CE-UK-FW-01" in r.controls
    assert "owasp_llm_top_10_2025" in r.standards


def test_dangling_standard_source_raises():
    # schema 不变量牙齿：standards_ref.source 不在 standards 注册表 → load 即 ValueError
    with pytest.raises(ValueError, match="悬空引用"):
        Registry(
            standards={"known": {"id": "known", "name": "Known"}},
            controls={"C-X": {"id": "C-X", "title": "t",
                              "standards_refs": [{"source": "ghost", "ref": "r"}],
                              "verification": {"method": "automated_test", "verdict": "automatic"}}},
        )


def test_pi01_resolves_severity_verdict_standards():
    c = default_control()
    assert c.id == "AI-AGENT-PI-01"
    assert c.severity_if_failed == "High"                 # ontology gating 用 High/Critical
    assert c.verification.verdict == "automatic"          # D8 确定性 detector 一致
    assert {r.source for r in c.standards_refs} == {"owasp_llm_top_10_2025", "nist_ai_rmf"}


def test_referenced_standards_resolves_names():
    s = referenced_standards("AI-AGENT-PI-01")
    assert s["owasp_llm_top_10_2025"].name.startswith("OWASP")
    assert s["nist_ai_rmf"].authority == "NIST"


# ── ② derive 接线：severity/verdict 从注册表、standards 挂报告层 ──────────────
@pytest.fixture
def report():
    return derive(json.loads(FIXTURE.read_text()))


def test_finding_severity_inherited_from_control(report):
    bare = report.findings[0]
    assert bare.status == "fail" and bare.severity == "High"   # 非占位 "high"
    assert bare.verdict_mode == "automatic"


def test_standards_on_report_layer_not_finding(report):
    # 范式化：standards 挂报告层（AssuranceReport.control），Finding 只 control_id
    assert report.control is not None and report.control.id == "AI-AGENT-PI-01"
    assert "owasp_llm_top_10_2025" in report.referenced_standards
    assert report.referenced_standards["owasp_llm_top_10_2025"].name.startswith("OWASP")
    # Finding 上没有 standards_refs 字段（只有 control_id 外键）
    assert not hasattr(report.findings[0], "standards_refs")


def test_control_not_in_finding_id_hash(report):
    # control/standards 挂报告层 → 不进 finding_id（身份哈希只 control_id/target_ref/status/evidence）
    r2 = derive(json.loads(FIXTURE.read_text()))
    assert {f.finding_id for f in report.findings} == {f.finding_id for f in r2.findings}
