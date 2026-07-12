"""provenance 钉死代码契约（确定性、离线、无 key）——档 2，ADR-0007。

两半：① `ithuriel.provenance` 纯函数（static + record_response，喂 stub response）；
② `derive.build_measurement_context` 线程 + 向后兼容（缺 provenance 的历史跑优雅退化）。
"""
from __future__ import annotations

import json
from pathlib import Path

from ithuriel.derive import SEAMS5_EXPECTED, build_measurement_context, derive
from ithuriel.provenance import invariant_mismatch, record_response, static_provenance

FIXTURE = Path(__file__).parent / "fixtures" / "d8_run_detector.json"


# ── stub（离线，无 openai SDK/网络）─────────────────────────────────────────
class _Resp:
    def __init__(self, model, fingerprint=None):
        self.model = model
        self.system_fingerprint = fingerprint


class NotGiven:  # 摹 openai SDK 的 NOT_GIVEN 哨兵（类名须与真哨兵一致，_is_not_given 靠类名判定）
    pass


# ── ① provenance 纯函数 ─────────────────────────────────────────────────────
def _static(defense="transformers_pi_detector"):
    return static_provenance(
        requested_model="mistral-small-latest", transport="openai", defense=defense,
        suite="workspace",
        lib_versions={"agentdojo": "0.1.35", "openai": "2.45.0", "transformers": "5.13.0"},
        temperature_intent=0.0)


def test_static_detector_pins_transformers_version():
    p = _static("transformers_pi_detector")
    assert p["detector"] == {"defense": "transformers_pi_detector", "transformers_version": "5.13.0"}
    assert p["corpus"]["suite_family"] == "v1" and p["corpus"]["agentdojo_version"] == "0.1.35"
    assert p["aggregate_rule_version"] == "wilson-ci-v1" and p["adaptive_level"] == "static"
    assert p["served_model"] is None  # 待 response 填


# ── 两臂不变量比较（partner review D2/C3，第二批；离线纯函数）───────────────
def test_invariant_mismatch_treatment_excluded():
    # 两臂仅 defense 侧不同（bare=none / defended=detector）+ served_model 相同 → **无** mismatch
    # （defense/detector 是 treatment、故意排除）。这是"防御合法不同、不误报"的正对照。
    bare, defended = _static("none"), _static("transformers_pi_detector")
    r = record_response(bare, {}, _Resp("mistral-small-2506", "fp_A"))
    d = record_response(defended, {}, _Resp("mistral-small-2506", "fp_A"))
    mismatch, fields = invariant_mismatch(r, d)
    assert mismatch is False and fields == {}


def test_invariant_mismatch_served_model_drift():
    # provider 在两臂间滚动部署 → served_model 漂移（C3 的核心场景）→ mismatch，列出差异值。
    bare, defended = _static("none"), _static("transformers_pi_detector")
    r = record_response(bare, {}, _Resp("mistral-small-2506", "fp_A"))
    d = record_response(defended, {}, _Resp("mistral-small-2509", "fp_B"))  # 漂移
    mismatch, fields = invariant_mismatch(r, d)
    assert mismatch is True
    assert fields["served_model"] == {"bare": "mistral-small-2506", "defended": "mistral-small-2509"}
    assert "system_fingerprint" in fields


def test_static_non_detector_no_transformers_version():
    p = _static("spotlighting_with_delimiting")
    assert p["detector"]["transformers_version"] is None
    # libs 只留非 None：transformers 装了就在 libs（与 detector_version 不同轴），此处仍在
    assert "transformers" in p["libs"]


def test_record_response_pins_served_and_omitted_temperature():
    # AgentDojo 发 temperature=NOT_GIVEN（0.0 falsy→省略）→ on_wire="omitted" ≠ intent 0.0
    p = _static()
    record_response(p, {"temperature": NotGiven(), "messages": []}, _Resp("mistral-small-2506", "fp_x"))
    assert p["served_model"] == "mistral-small-2506" and p["system_fingerprint"] == "fp_x"
    assert p["temperature"] == {"config_intent": 0.0, "on_wire": "omitted"}
    assert p["seed"]["on_wire"] is None  # 未发 seed


def test_record_response_records_real_temperature():
    p = _static()
    record_response(p, {"temperature": 0.7, "seed": 42}, _Resp("m"))
    assert p["temperature"]["on_wire"] == 0.7 and p["seed"]["on_wire"] == 42


def test_record_response_idempotent_first_success_wins():
    p = _static()
    record_response(p, {}, _Resp("first"))
    record_response(p, {}, _Resp("second"))
    assert p["served_model"] == "first"


# ── ② derive 线程 + 向后兼容 ────────────────────────────────────────────────
def _meta_with_prov():
    p = _static()
    record_response(p, {"temperature": NotGiven()}, _Resp("mistral-small-2506", "fp_x"))
    return {"provider": "openrouter", "model": "mistralai/mistral-small-latest",
            "model_transport": "openai", "scenario": "workspace/user_task_0+injection_task_0",
            "attack": "important_instructions_no_names", "n_trials_per_config": 40,
            "order_policy": "interleaved", "harness": "scripts/run_bare_vs_defended.py",
            "provenance": p}


def test_provenance_fills_mctx_and_shrinks_absent():
    mctx = build_measurement_context(_meta_with_prov())
    assert mctx["model"]["version"] == "mistral-small-2506"          # served snapshot（治别名核心）
    assert mctx["model"]["requested_alias"] == "mistral-small-latest"
    assert mctx["model"]["system_fingerprint"] == "fp_x"
    assert mctx["scenario"]["version"] == "v1"
    assert mctx["aggregate_rule_version"] == "wilson-ci-v1"
    assert mctx["sampling_plan"]["temperature"] == {"config_intent": 0.0, "on_wire": "omitted"}
    # 档 2 后只剩 seed_schedule（记录-only 决策）
    assert mctx["_absent_seams5_fields"] == ["seed_schedule"]


def test_old_meta_without_provenance_degrades_gracefully():
    # 历史跑无 provenance → 全 absent、model.version=None、不崩（向后兼容回归）
    meta = {"provider": "mistral", "model": "mistral-small-latest", "model_transport": "openai",
            "scenario": "workspace/user_task_0+injection_task_0", "attack": "important_instructions_no_names",
            "n_trials_per_config": 40, "order_policy": "interleaved", "harness": "h"}
    mctx = build_measurement_context(meta)
    assert mctx["model"]["version"] is None
    assert set(mctx["_absent_seams5_fields"]) == set(SEAMS5_EXPECTED)


def test_served_model_flows_into_run_record():
    # AiRunRecord.model_version（ADR-0004 标 gap）现由 served snapshot 填
    data = json.loads(FIXTURE.read_text())
    data["meta"]["provenance"] = _meta_with_prov()["provenance"]
    rep = derive(data)
    assert rep.findings[0].run_record.model_version == "mistral-small-2506"
    assert rep.findings[1].run_record.model_version == "mistral-small-2506"
