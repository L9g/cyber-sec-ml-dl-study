"""Step 2（ADR-0016）：从 4 个真 fixture **反推** typed verdict_provenance union，核对映射干净。

不接线 producer（Step 4）、不建 Claim Deriver（Step 3）——本文件只证：
  (1) union 能无遗漏、无凭空多值地表示 4 个真实 shape；
  (2) discriminator 按 kind 正确路由；
  (3) 给 Finding 加 verdict_provenance 不改 finding_id（守 ADR-0004 哈希契约）、历史 Finding 优雅退化。

映射值全部取自真 producer 在真 fixture 上产出的报告（不手搓），坐实「据真实摩擦定字段」。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ithuriel.attestation import ATTESTATION_MAPPING_VERSION, ExceptionEntry, ReviewAttestation
from ithuriel.attestation import build_report as attest_report
from ithuriel.config_inspection import build_report as config_report
from ithuriel.derive import derive
from ithuriel.executor import NetworkPortScanAction, RoEAuthorization
from ithuriel.models import (
    AutomaticRuleProvenance,
    Finding,
    HumanAttestationProvenance,
)
from ithuriel.port_scan import DeclaredService
from ithuriel.port_scan import build_report as probe_report

FX = Path(__file__).parent / "fixtures"


# ── 真 producer × 真 fixture → 4 shape 的报告（同 Step 1 spike 的构造路径）──────
@pytest.fixture(scope="module")
def reports():
    ai = derive(json.loads((FX / "d8_run_detector.json").read_text()))
    cfg = config_report((FX / "ufw" / "deny_active.txt").read_text(), host_id="host-01")
    action = NetworkPortScanAction(target_ip="192.0.2.10", ports=[22, 443])
    roe = RoEAuthorization(roe_version="roe-v1", allowed_targets=["192.0.2.0/24"])
    declared = [DeclaredService(port=22, owner="svc", justification_ref="j1"),
                DeclaredService(port=443, owner="svc", justification_ref="j2")]
    prb = probe_report(action=action, roe=roe,
                       nmap_xml=(FX / "nmap" / "open_22_443.xml").read_text(),
                       fixture_ref="fixture:nmap-1", host_id="host-01", declared_services=declared)
    reg = [ExceptionEntry(**e) for e in
           json.loads((FX / "attestation" / "register_complete.json").read_text())["entries"]]
    att = ReviewAttestation(**json.loads(
        (FX / "attestation" / "attestation_conformant.json").read_text()))
    at = attest_report(register=reg, attestation=att, host_id="host-01")
    return {"ai": ai, "config": cfg, "probe": prb, "attestation": at}


# ── (1) 4 shape 各映射到 union 一个变体，字段全从既有数据填得出 ──────────────────
def test_ai_maps_to_automatic_rule_statistical(reports):
    """AI 探针 → automatic_rule + statistical_trials（受 CI/n_runs 限）。"""
    ai_finding = reports["ai"].findings[0]           # bare
    assert ai_finding.run_record is not None         # 有统计 run → statistical_trials 有据
    p = AutomaticRuleProvenance(rule_version="ai-status-rule/v1",
                                measurement_kind="statistical_trials")
    assert p.kind == "automatic_rule"
    assert p.measurement_kind == "statistical_trials"


def test_config_maps_to_automatic_rule_deterministic(reports):
    """config → automatic_rule + deterministic_observation；rule_version 取自真 mctx。"""
    mctx = reports["config"].measurement_context
    p = AutomaticRuleProvenance(rule_version=mctx["rule_version"],
                                measurement_kind="deterministic_observation")
    assert p.rule_version == "ufw-default-deny/v1"    # 来自 config_inspection.RULE_VERSION
    assert p.measurement_kind == "deterministic_observation"


def test_probe_maps_to_automatic_rule_deterministic(reports):
    """probe → automatic_rule + deterministic_observation；与 config 同变体、由 target_fidelity 区分。

    #A 摩擦的正解：两片同为 automatic_rule/deterministic_observation，**不再靠 rule_version key 猜**；
    config↔probe 差异（frozen-fixture vs mock）留给 Claim 层从 execution_backend 派生。
    """
    mctx = reports["probe"].measurement_context
    p = AutomaticRuleProvenance(rule_version=mctx["rule_version"],
                                measurement_kind="deterministic_observation")
    assert p.rule_version == "fw01-exposed-services-justified/v1"
    assert mctx["execution_backend"] == "mock"        # Claim 层据此派 target_fidelity=mock
    assert reports["config"].measurement_context["execution_backend"] == "frozen-fixture"


def test_attestation_maps_to_human_attestation(reports):
    """attestation → human_attestation；decision_evidence_ref 引用**已存** att: 哈希（不复制第三份）。"""
    rep = reports["attestation"]
    att_refs = [r for r in rep.findings[0].evidence_refs if r.startswith("att:")]
    assert len(att_refs) == 1                          # attestation artifact 已在 evidence_refs
    p = HumanAttestationProvenance(decision_evidence_ref=att_refs[0],
                                   mapping_version=ATTESTATION_MAPPING_VERSION)
    assert p.kind == "human_attestation"
    assert p.decision_evidence_ref.startswith("att:")
    assert p.mapping_version == "human-review-attestation/v1"


def test_union_covers_all_four_shapes_no_third_variant(reports):
    """4 shape → 恰 2 个变体（automatic_rule ×3、human_attestation ×1）；无 shape 落空、无需第三变体。"""
    kinds = {
        "ai": "automatic_rule", "config": "automatic_rule",
        "probe": "automatic_rule", "attestation": "human_attestation",
    }
    assert set(kinds.values()) == {"automatic_rule", "human_attestation"}
    assert sum(v == "automatic_rule" for v in kinds.values()) == 3


# ── (2) discriminator 路由 ──────────────────────────────────────────────────
def test_discriminator_routes_by_kind():
    a = Finding.model_validate({
        "control_id": "C", "target_ref": {}, "status": "pass", "verdict_mode": "automatic",
        "assessed_at": "t", "evidence_refs": [],
        "verdict_provenance": {"kind": "automatic_rule",
                               "rule_version": "r/v1", "measurement_kind": "statistical_trials"},
    })
    assert isinstance(a.verdict_provenance, AutomaticRuleProvenance)
    h = Finding.model_validate({
        "control_id": "C", "target_ref": {}, "status": "pass", "verdict_mode": "human_review",
        "assessed_at": "t", "evidence_refs": [],
        "verdict_provenance": {"kind": "human_attestation",
                               "decision_evidence_ref": "att:abc", "mapping_version": "m/v1"},
    })
    assert isinstance(h.verdict_provenance, HumanAttestationProvenance)


def test_bad_measurement_kind_rejected():
    with pytest.raises(Exception):
        AutomaticRuleProvenance(rule_version="r", measurement_kind="declarative")  # 不是 automatic 轴的值


# ── (3) 哈希契约：加 verdict_provenance 不改 finding_id；历史 Finding 优雅退化 ─────
def _base_finding_kwargs():
    return dict(control_id="C", target_ref={"a": 1}, status="pass",
                verdict_mode="automatic", assessed_at="t", evidence_refs=["e1"])


def test_verdict_provenance_does_not_change_finding_id():
    """finding_id 只哈希 control_id/target_ref/status/evidence_refs（ADR-0004）→ 加 provenance 不动它。"""
    without = Finding(**_base_finding_kwargs())
    with_prov = Finding(**_base_finding_kwargs(),
                        verdict_provenance=AutomaticRuleProvenance(
                            rule_version="r/v1", measurement_kind="deterministic_observation"))
    assert without.finding_id == with_prov.finding_id


def test_historical_finding_has_none_provenance_fail_closed():
    """历史构造（不传 verdict_provenance）→ None，consumer 据此 fail-closed（Step 3）。"""
    f = Finding(**_base_finding_kwargs())
    assert f.verdict_provenance is None
