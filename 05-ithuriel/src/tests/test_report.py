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


def _row(rep, key, axis="domain"):
    """按 (轴, key) 取矩阵行（ADR-0021：矩阵含 domain + ce_area 两轴，选择器须指明轴）。"""
    return next(r for r in rep.matrix if r.axis == axis and r.key == key)


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
            assert row.fidelity_mix, f"{row.axis}:{row.key} 有覆盖却无 fidelity 分布（G2：不可折成标量）"


# ── 选项 A：security 轴覆盖 + joint_caveats 常驻 ─────────────────────────────────
def test_option_a_utility_failed_flagged_beside_passing_coverage(demo):
    ai = _row(demo, "ai_agent_security")
    # detector 防御靠中止任务挡注入 → defended security-pass（覆盖 1.0）但 joint=utility_failed。
    assert ai.coverage == 1.0                       # security 轴覆盖照实（不重算 ledger）
    assert ai.joint_caveats.get("utility_failed") == 1  # 但警示常驻，读不成「系统安全」


def test_option_a_no_caveat_when_no_joint_disagreement(demo):
    net = _row(demo, "network_security")
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
        # not_assessed（ADR-0019）进 applicable 但无 report → 不在 fidelity_mix/unassessable，单列补齐。
        counted = sum(row.fidelity_mix.values()) + row.unassessable + len(row.not_assessed_controls)
        assert counted == row.applicable, (
            f"{row.axis}:{row.key}: fidelity+unassessable+not_assessed={counted} 应等于 applicable={row.applicable}"
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
    assert set(j.keys()) == {"generated_from", "matrix", "controls",
                             "manifest_hash", "declared_controls",
                             "not_assessed_controls", "undeclared_assessed",
                             "ce_area_unmapped"}
    assert j["manifest_hash"] is None                # demo 无 manifest → 如实 None（覆盖率仅已评估）
    all_standards = [s for c in j["controls"] for s in c["standards"]]
    assert any("OWASP" in s for s in all_standards)  # AI 控制审计闭环
    assert any("Cyber Essentials" in s for s in all_standards)  # config 控制审计闭环


def test_empty_input_yields_empty_report_no_positive_claim():
    rep = render_report([])                          # 0 report → 空报告，不静默产结论
    assert rep.matrix == [] and rep.controls == []


# ── ②（搭档 P0，ADR-0017 §59）：not_ready=False ≠ ready；「无门禁」绝不读成「就绪」，不造 readiness 档 ──
def test_gate_status_incomplete_when_medium_fail_present(demo):
    # config 两主机 = deny pass + allow fail(Medium)；无 High/Critical → not_ready=False，
    # 但 1/2 未 pass → 门禁/缺口判读必须显式 incomplete、不得读成 ready/清白。
    net = _row(demo, "network_security")
    assert net.not_ready is False                    # ledger 原值：无 High/Critical 门禁
    assert net.gate_status == "incomplete"           # 但如实陈述：非就绪
    assert net.coverage < 1.0


def test_no_manufactured_readiness_verdict_field():
    # 不造 readiness 档：MatrixRow 不得出现名为 readiness/ready 的正向就绪判读字段。
    for name in MatrixRow.model_fields:
        assert "readiness" not in name and name != "ready", f"MatrixRow.{name} 疑似 readiness 档（②：不造）"


def test_gate_status_all_pass_still_not_system_ready(demo):
    ai = _row(demo, "ai_agent_security")
    assert ai.gate_status == "all_applicable_passed"  # 全适用 pass 是事实陈述、非就绪判读
    # 关键：全 pass 也不越权断言系统 ready——detail 显式否定「系统 ready」。
    assert "ready" in (ai.gate_detail or "") and "非系统级" in (ai.gate_detail or "")


def test_markdown_never_renders_absence_of_gate_as_clear(demo):
    md = to_markdown(demo)
    assert "incomplete" in md
    assert "并非 ready" in md
    assert "无 High/Critical 门禁 ≠ ready" in md      # 图例护栏句在场


# ── ③（搭档 P0，ADR-0017 §60）：target 身份 + rationale + 结构化 advisory 不丢 ──────────
def test_two_hosts_are_distinguishable(demo):
    fw = [c for c in demo.controls if c.control_id == "CE-UK-FW-03"]
    assert len(fw) == 2
    labels = {c.target_label for c in fw}
    assert labels == {"host-01", "host-02"}          # 两台主机不再折成同名段落
    md = to_markdown(demo)
    assert "@ host-01" in md and "@ host-02" in md


def test_fail_rationale_and_advisory_surface(demo):
    md = to_markdown(demo)
    assert "裁定理由" in md                            # fail 不再只显示 [fail] 而不说为何
    assert "违反 default-deny" in md                  # config fail 的真实理由穿透到 view
    assert "advisory（root_causes）" in md             # AI 的结构化 P1–P6 advisory 穿透
    # warrant 层确有 rationale 承载（非仅 markdown 拼接）
    fail_arm = next(w for c in demo.controls for w in c.warrants if w.finding_status == "fail")
    assert fail_arm.rationale


def test_attestation_0015_conflict_note_survives_to_view():
    # ADR-0015 冲突警示（reviewer conformant 但登记缺 justification）曾在最终 view 丢失——须穿透。
    from ithuriel.attestation import ExceptionEntry, ReviewAttestation
    from ithuriel.attestation import build_report as att_report
    reg = [ExceptionEntry(exception_id="EXC-001", justification_ref="CHG-2201", review_date="2026-06-01"),
           ExceptionEntry(exception_id="EXC-003", justification_ref="", review_date="2026-06-20")]
    att = ReviewAttestation(reviewer="j.smith", review_date="2026-06-30", decision="conformant",
                            statement="tracked", attested_refs=["EXC-001"])
    view = render_report([att_report(register=reg, attestation=att, host_id="host-att-01")])
    md = to_markdown(view)
    assert "ADR-0015" in md and "EXC-003" in md and "缺 justification_ref" in md


# ── ④（搭档 P0，ADR-0017 §61）：joint_verdict 未评估 ≠ 无问题；显式区分 ─────────────────
def test_deterministic_domain_marks_joint_not_evaluated(demo):
    net = _row(demo, "network_security")
    assert net.joint_evaluated is False              # 无 bare/defended 对比
    assert net.joint_caveats == {}
    ai = _row(demo, "ai_agent_security")
    assert ai.joint_evaluated is True                # 有防御实验


def test_markdown_distinguishes_not_evaluated_from_no_disagreement(demo):
    md = to_markdown(demo)
    assert "未评估（无防御实验）" in md                 # 确定性域不再留裸「—」被读成无问题
    # 控制详情也如实标未评估（无 comparison 的确定性检查）
    net_ctrl = next(c for c in demo.controls if c.control_id == "CE-UK-FW-03")
    assert net_ctrl.joint_evaluated is False


# ── AssessmentManifest（ADR-0019，搭档 P0 #1）：分母对声明控制集算、防输入选择做高 ──────────
from ithuriel.manifest import AssessmentManifest, DeclaredControl  # noqa: E402


def _net_manifest() -> AssessmentManifest:
    # 声明 network_security 全部四控制 + AI 控制；只跑其中一部分 → 未跑的须显式 not_assessed。
    return AssessmentManifest(profile_id="uk", declared=[
        DeclaredControl(control_id="AI-AGENT-PI-01"),
        DeclaredControl(control_id="CE-UK-FW-01"),
        DeclaredControl(control_id="CE-UK-FW-02"),
        DeclaredControl(control_id="CE-UK-FW-03"),
        DeclaredControl(control_id="CE-UK-FW-04"),
    ])


def test_coverage_cannot_be_inflated_by_dropping_reports():
    # 核心不变量：同一声明清单下，删掉那份 fail 的 report 不能把覆盖率抬到 1.0。
    reports = [_ai(), _fw03("deny_active.txt", "host-01"), _fw03("allow_active.txt", "host-02")]
    mfst = _net_manifest()
    with_fail = render_report(reports, manifest=mfst)
    dropped_fail = render_report(reports[:2], manifest=mfst)   # 去掉 host-02（allow=fail）
    net_a = _row(with_fail, "network_security")
    net_b = _row(dropped_fail, "network_security")
    assert net_a.coverage < 1.0 and net_b.coverage < 1.0       # 两种输入都读不成满覆盖
    # 对照：无 manifest 时删 report 确实虚高到 1.0——正是 manifest 要堵的洞。
    no_mfst = _row(render_report(reports[:2]), "network_security")
    assert no_mfst.coverage == 1.0


def test_declared_but_unreported_controls_surface_as_not_assessed():
    reports = [_ai(), _fw03("deny_active.txt", "host-01"), _fw03("allow_active.txt", "host-02")]
    view = render_report(reports, manifest=_net_manifest())
    net = _row(view, "network_security")
    assert net.not_assessed_controls == ["CE-UK-FW-01", "CE-UK-FW-02", "CE-UK-FW-04"]
    assert net.applicable == 5 and net.passed == 1 and net.coverage == 0.2   # FW-03 两主机 + 三未评估
    assert view.not_assessed_controls == ["CE-UK-FW-01", "CE-UK-FW-02", "CE-UK-FW-04"]
    md = to_markdown(view)
    assert view.manifest_hash and view.manifest_hash in md
    assert "声明但**未评估**" in md and "CE-UK-FW-04" in md


def test_undeclared_assessment_is_flagged():
    # 只声明 FW-03，却也跑了 AI 控制 → 越界评估如实点名（不静默计入声明分母）。
    mfst = AssessmentManifest(profile_id="uk", declared=[DeclaredControl(control_id="CE-UK-FW-03")])
    view = render_report([_ai(), _fw03("deny_active.txt", "host-01")], manifest=mfst)
    assert view.undeclared_assessed == ["AI-AGENT-PI-01"]
    assert "越界评估" in to_markdown(view)


def test_no_manifest_warns_coverage_is_input_selectable(demo):
    md = to_markdown(demo)
    assert demo.manifest_hash is None
    assert "未对照评估清单" in md and "可被输入选择做高" in md


def test_dangling_declaration_fails_closed():
    # 声明未注册的控制 → fail-closed 报错（echo registry 不悬空不变量），不静默吞。
    mfst = AssessmentManifest(profile_id="uk", declared=[DeclaredControl(control_id="NOT-A-REAL-CONTROL")])
    with pytest.raises(ValueError, match="未在 registry 注册"):
        render_report([_fw03("deny_active.txt", "host-01")], manifest=mfst)


def test_manifest_hash_pins_declaration():
    a = AssessmentManifest(profile_id="uk", declared=[
        DeclaredControl(control_id="CE-UK-FW-01"), DeclaredControl(control_id="CE-UK-FW-03")])
    reordered = AssessmentManifest(profile_id="uk", declared=[
        DeclaredControl(control_id="CE-UK-FW-03"), DeclaredControl(control_id="CE-UK-FW-01")])
    fewer = AssessmentManifest(profile_id="uk", declared=[DeclaredControl(control_id="CE-UK-FW-01")])
    assert a.manifest_hash == reordered.manifest_hash    # 声明集相同 → 同 hash（顺序无关）
    assert a.manifest_hash != fewer.manifest_hash        # 改分母 → 改 hash（事后调分母会暴露）


def test_empty_or_duplicate_declaration_rejected():
    with pytest.raises(ValueError, match="不得为空"):
        AssessmentManifest(profile_id="uk", declared=[])
    with pytest.raises(ValueError, match="重复"):
        AssessmentManifest(profile_id="uk", declared=[
            DeclaredControl(control_id="CE-UK-FW-01"), DeclaredControl(control_id="CE-UK-FW-01")])


# ── Cyber Essentials area 视图（ADR-0021）─────────────────────────────────────────
# profile 的 18 个 Cyber Essentials 控制（五 area 分布：firewalls/secure_config/user_access/malware/updates）。
_ALL_CE_CONTROLS = [
    "CE-UK-FW-01", "CE-UK-FW-02", "CE-UK-FW-03", "CE-UK-FW-04",
    "CE-UK-SC-01", "CE-UK-SC-02", "CE-UK-SC-03", "CE-UK-SC-04",
    "CE-UK-UA-01", "CE-UK-UA-02", "CE-UK-UA-03", "CE-UK-UA-04",
    "CE-UK-MW-01", "CE-UK-MW-02", "CE-UK-MW-03",
    "CE-UK-SU-01", "CE-UK-SU-02", "CE-UK-SU-03",
]


def test_matrix_carries_both_axes(demo):
    # 两轴并存：domain 不被 ce_area 替换。
    assert {r.axis for r in demo.matrix} == {"domain", "ce_area"}
    fw = _row(demo, "firewalls", axis="ce_area")   # FW-03 两主机聚到 firewalls area
    assert fw.applicable == 2                        # deny(pass) + allow(fail)
    assert _row(demo, "network_security").applicable == 2  # 同两份 report 也在 domain 轴


def test_ai_control_surfaced_as_unmapped_not_a_fake_area(demo):
    # R1：AI 控制无 ce_area → 进 ce_area_unmapped、不成为带覆盖分的 area key，也不静默消失。
    assert demo.ce_area_unmapped == ["AI-AGENT-PI-01"]
    assert all(r.key != "ai_agent_security" for r in demo.matrix if r.axis == "ce_area")
    md = to_markdown(demo)
    assert "不在任何 Cyber Essentials area" in md and "AI-AGENT-PI-01" in md
    assert "### Domain 视图" in md and "### Cyber Essentials area 视图" in md


def test_ce_area_declaring_all_18_prevents_firewalls_reading_as_covered():
    # P0#2：只跑 FW-03 却声明全部 18 CE 控制 → firewalls area 读作 1/4（三个未评估），
    # **不会**读成 2/2 或「Firewalls 已覆盖」；未触及的四个 area 全 not_assessed。
    reports = [_ai(), _fw03("deny_active.txt", "host-01")]
    mfst = AssessmentManifest(profile_id="uk", declared=[
        DeclaredControl(control_id="AI-AGENT-PI-01"),
        *[DeclaredControl(control_id=c) for c in _ALL_CE_CONTROLS]])
    view = render_report(reports, manifest=mfst)
    fw = _row(view, "firewalls", axis="ce_area")
    assert (fw.applicable, fw.passed, fw.coverage) == (4, 1, 0.25)
    assert fw.not_assessed_controls == ["CE-UK-FW-01", "CE-UK-FW-02", "CE-UK-FW-04"]
    # 未触及的 area 全部未评估（passed=0、全员 not_assessed）。
    for area in ("secure_configuration", "user_access_control", "malware_protection"):
        row = _row(view, area, axis="ce_area")
        assert row.passed == 0 and len(row.not_assessed_controls) == row.applicable
    # PI-01 assessed 但无 ce_area → 仍在 unmapped、不冒充 area。
    assert view.ce_area_unmapped == ["AI-AGENT-PI-01"]
    md = to_markdown(view)
    assert "1/4 = 0.25" in md                         # firewalls 覆盖数如实稀疏，非 100%


def test_cross_target_mixed_denominator_disclosed(demo):
    # 决策 3：报告须披露分母单位=每份 report 一个 outcome（同控制多 target 计多票），本刀不做跨 target 归约。
    md = to_markdown(demo)
    assert "每份 report 一个 outcome" in md
    assert "两个 outcome" in md and "ADR-0019 已知边界" in md
