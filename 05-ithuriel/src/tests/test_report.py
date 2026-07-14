"""内部试用报告 view 代码契约（试用里程碑 Step 4，ADR-0017）——确定性、与模型无关。

用真实 producer 产 report（AI PI-01 冻结 fixture + config-FW03 ufw fixture），验：
  - G2  矩阵无单一总分/标量 score 字段、fidelity 显式在场（不可折成标量）；
  - 选项 A  security 轴覆盖 + joint_caveats 常驻（passed 但 joint≠acceptable 被标出）；
  - friction 1  fidelity/reproducibility 从 Claim join 到 domain 轴，单位=控制、与 coverage 分母一致；
  - G3  fail-closed 与不可评估如实穿透到呈现；
  - G5  render_report/to_json bit 可复现；审计闭环 standards 出现在呈现物。
全部离线、无 key、无网络（沿用冻结 fixture）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ithuriel.config_inspection import build_report as fw03_report
from ithuriel.derive import derive
from ithuriel.models import (
    AssuranceReport,
    AutomaticRuleProvenance,
    EvidenceManifest,
    Finding,
    ScopeStatement,
)
from ithuriel.report import (
    MatrixRow,
    Report,
    render_report,
    to_json,
    to_markdown,
)

FX = Path(__file__).parent / "fixtures"


# ── 真实 report 工厂（冻结 fixture，确定性）─────────────────────────────────────
def _ai(fixture="d8_run_detector.json") -> AssuranceReport:
    # detector 格：bare fail / defended pass（security 轴），joint_verdict=utility_failed。
    return derive(json.loads((FX / fixture).read_text()))


def _fw03(fixture: str, host_id: str) -> AssuranceReport:
    return fw03_report((FX / "ufw" / fixture).read_text(), host_id=host_id)


@pytest.fixture
def demo() -> Report:
    # 跨两裁定形状：AI（统计）+ config（确定性），config 两主机（deny pass / allow fail）。
    return render_report([_ai(), _fw03("deny_active.txt", "host-01"), _fw03("allow_active.txt", "host-02")])


# ── G2：无单一总分；矩阵是二维、fidelity 显式在场 ────────────────────────────────
def test_g2_report_has_no_scalar_score_field():
    # 硬断言：Report 与 MatrixRow 都不得出现任何 overall/total/单一 score/grade 字段。
    banned = ("overall", "total_score", "score", "grade", "rating")
    for model in (Report, MatrixRow):
        for name in model.model_fields:
            assert not any(b in name for b in banned), f"{model.__name__}.{name} 疑似单一评分字段（违反 G2）"


def test_g2_matrix_surfaces_fidelity_alongside_coverage(demo):
    for row in demo.matrix:
        # 每个有覆盖的域必须同时带 fidelity 分布——coverage 不可脱离 fidelity 单独呈现。
        if row.applicable > 0:
            assert row.fidelity_mix, f"{row.domain} 有覆盖却无 fidelity 分布（G2：不可折成标量）"


# ── 选项 A：security 轴覆盖 + joint_caveats 常驻 ─────────────────────────────────
def test_option_a_utility_failed_flagged_beside_passing_coverage(demo):
    ai = next(r for r in demo.matrix if r.domain == "ai_agent_security")
    # detector 防御靠中止任务挡注入 → defended security-pass（覆盖 1.0）但 joint=utility_failed。
    assert ai.coverage == 1.0                       # security 轴覆盖照实（不重算 ledger）
    assert ai.joint_caveats.get("utility_failed") == 1  # 但警示常驻，读不成「系统安全」


def test_option_a_no_caveat_when_no_joint_disagreement(demo):
    net = next(r for r in demo.matrix if r.domain == "network_security")
    assert net.joint_caveats == {}                  # config 无 defense delta → 无联合裁定分歧


def test_markdown_never_reads_as_system_safe(demo):
    md = to_markdown(demo)
    # 顶线覆盖 1.0 的域旁必须出现联合裁定警示词与「不可…读作系统安全」的护栏句。
    assert "utility_failed" in md
    assert "不可单独读作" in md or "读不成" in md
    assert "不产单一安全总分" in md                  # G2 护栏句在场


# ── friction 1：fidelity join 单位=控制、与 coverage 分母一致 ───────────────────
def test_friction1_fidelity_counts_align_with_coverage_denominator(demo):
    for row in demo.matrix:
        counted = sum(row.fidelity_mix.values()) + row.unassessable
        assert counted == row.applicable, (
            f"{row.domain}: fidelity+unassessable={counted} 应等于 applicable={row.applicable}"
            "（friction 1：join 单位必须=控制，与 coverage 分母一致）")


# ── G3：fail-closed / 不可评估如实穿透 ──────────────────────────────────────────
def test_g3_unassessable_finding_surfaces_not_dropped():
    # 缺 verdict_provenance 的 Finding → Claim fail-closed → 报告控制层如实标不可评估、不静默丢。
    f = Finding(control_id="C", target_ref={"defense": "none"}, status="pass",
                verdict_mode="automatic", assessed_at="t", evidence_refs=["e"])  # 无 provenance
    mctx = {"control_id": "C", "execution_backend": "agentdojo-mock"}
    rep = AssuranceReport(
        generated_from="t", measurement_context=mctx,
        evidence_manifest=EvidenceManifest(run_root="run:x", measurement_context=mctx,
                                           artifacts={}, index={}),
        findings=[f], comparisons=[],
        scope=ScopeStatement(claim="c", in_scope={}, not_covered=[],
                             measurement_valid=True, underpowered=None))
    view = render_report([rep]).controls[0]
    assert view.warrants == []                       # 无凭据
    assert view.unassessable_reasons                 # 但不可评估被如实记，未静默丢
    assert "不可评估" in to_markdown(render_report([rep]))


# ── G5：bit 可复现 + 审计闭环 ───────────────────────────────────────────────────
def test_g5_render_is_bit_reproducible(demo):
    a = render_report([_ai(), _fw03("deny_active.txt", "host-01"), _fw03("allow_active.txt", "host-02")])
    b = render_report([_ai(), _fw03("deny_active.txt", "host-01"), _fw03("allow_active.txt", "host-02")])
    assert to_json(a) == to_json(b)                  # 相同输入 → 相同 JSON（纯函数、无时间戳/随机）
    assert to_markdown(a) == to_markdown(b)


def test_g5_json_valid_and_audit_standards_present(demo):
    j = json.loads(to_json(demo))                    # 合法 JSON
    assert set(j.keys()) == {"generated_from", "matrix", "controls"}
    all_standards = [s for c in j["controls"] for s in c["standards"]]
    assert any("OWASP" in s for s in all_standards)  # AI 控制审计闭环
    assert any("Cyber Essentials" in s for s in all_standards)  # config 控制审计闭环


def test_empty_input_yields_empty_report_no_positive_claim():
    rep = render_report([])                          # 0 report → 空报告，不静默产结论
    assert rep.matrix == [] and rep.controls == []
