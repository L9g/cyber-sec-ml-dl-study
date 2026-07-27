"""ADR-0022 执行授权治理的信任核单测（golden 迁自 run_calendar_probe.py 自检 26）。

覆盖不需要真实 git 的纯逻辑：逐 trial deadline、run 级/trial 级完成与排除语义、
以及搬迁后 `_PROJECT_ROOT` 必须仍解析到含 scripts/ 的项目根（否则授权链哈希材料时会读错文件）。
git-backed 的 validate_execution_authorization 由 runner --self-test 端到端覆盖。
"""
import datetime
import os
import shutil

import pytest

from ithuriel.governance import execution_authorization as EA
from ithuriel.governance.execution_authorization import (
    deadline_exceeded,
    run_completion_status,
    verify_env_matches_lock,
    AuthorizationError,
    _PROJECT_ROOT,
)

FIXED_NOW = datetime.datetime(2026, 7, 22, 12, 0, tzinfo=datetime.timezone.utc)


# ---------------- 搬迁后路径解析（授权链读文件的前提）----------------
def test_project_root_still_points_at_dir_containing_runner():
    assert os.path.isfile(os.path.join(_PROJECT_ROOT, "scripts", "run_calendar_probe.py"))


# ---------------- 逐 trial deadline ----------------
def test_deadline_exceeded_past_and_future():
    assert deadline_exceeded("2026-07-22T11:59:00Z", now=FIXED_NOW) is True
    assert deadline_exceeded("2026-07-22T12:30:00Z", now=FIXED_NOW) is False


# ---------------- run 级 / trial 级完成与排除语义 ----------------
def test_pilot_not_overridden_by_incomplete_run():
    st = run_completion_status("pilot", True, 37, 60, "excluded")
    assert st["primary_verdict"] == "excluded_pilot"
    assert st["termination_reason"] == "authorization_deadline"


def test_main_interrupted_excludes_confirmatory_but_retains_evidence():
    st = run_completion_status("main", True, 37, 60, "preregistered")
    assert st["primary_verdict"] == "excluded_incomplete_run"
    assert st["confirmatory_analysis_eligibility"] == "excluded"
    assert st["descriptive_trial_evidence"] == "retained"
    assert (st["max_authorized_attempts"], st["completed_attempts"],
            st["last_completed_schedule_index"]) == (60, 37, 36)
    assert st["completed_trial_authorization"] == {"approved": 37, "lapsed": 0}
    assert st["authorization_coverage"] == "trial_atomic"
    assert st["resumable"] is False


def test_completion_criterion_uses_interpretable_not_attempt_cap():
    st = run_completion_status("main", False, 90, 135, "preregistered",
                               target_interpretable=90, interpretable_reached=90)
    assert st["completion_criterion_met"] is True
    assert st["completed_attempts"] == 90
    assert st["run_status"] == "completed"
    assert st["max_authorized_attempts"] == 135


def test_all_trials_done_before_deadline_is_completed_not_terminated():
    st = run_completion_status("main", False, 60, 60, "preregistered")
    assert st["run_status"] == "completed"
    assert st["confirmatory_analysis_eligibility"] == "preregistered"
    assert st["primary_verdict"] is None  # 交给预注册决策表，不在此覆盖


# ---------------- D1 preflight：已装版本 vs uv.lock（partner review 2026-07-24 + R2-D1 加固）--------
def test_pinned_versions_pass_on_current_repo():
    # 当前 .venv 与 uv.lock 的关键 pin 一致 → 返回 locked/installed 且相等（纯 pin 层，无 uv）。
    out = EA._verify_pinned_versions(_PROJECT_ROOT)
    assert set(out["locked"]) == {"agentdojo", "openai"}
    assert out["locked"] == out["installed"]


def test_pinned_versions_fail_closed_on_installed_drift(monkeypatch):
    # 已装 agentdojo 漂移 → fail closed（捕获 runtime 相等门抓不到的初始不一致）。
    real = EA._env_identity()
    monkeypatch.setattr(EA, "_env_identity", lambda: {**real, "agentdojo": "0.9.99-drifted"})
    with pytest.raises(AuthorizationError, match="uv.lock 不一致"):
        EA._verify_pinned_versions(_PROJECT_ROOT)


def test_pinned_versions_fail_closed_on_missing_pin(monkeypatch):
    # ⭐ R2-D1 关键回归：解析器漏块 / lock 缺预期 pin **不得静默通过**。
    # 旧实现 mismatch 只遍历 locked，缺 openai 会返回 success；现强制 EXPECTED_PINS 全解析到。
    monkeypatch.setattr(EA, "_lock_versions",
                        lambda root, packages=EA._EXPECTED_PINS: {"agentdojo": "0.1.35"})
    with pytest.raises(AuthorizationError, match="未解析到必需 pin"):
        EA._verify_pinned_versions(_PROJECT_ROOT)


def test_lock_sync_fail_closed_when_uv_missing(monkeypatch):
    # uv 不在 PATH → fail closed（无法校验完整依赖同步，不静默放行）。
    monkeypatch.setattr(EA.shutil, "which", lambda _name: None)
    with pytest.raises(AuthorizationError, match="uv 不在 PATH"):
        EA._verify_lock_sync(_PROJECT_ROOT)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv 不在 PATH（本机跑跳过）")
def test_lock_sync_passes_when_env_in_sync():
    # 借 uv 校验完整必需依赖同步（含 transitive）；当前 .venv 与 lock 同步 → returncode 0。
    out = EA._verify_lock_sync(_PROJECT_ROOT)
    assert out["returncode"] == 0


def test_lock_versions_ignores_dependency_reference_lines():
    # tomllib 只取 [[package]] 块的 name/version，不被 dependencies 里的 `{ name = "openai" }` 误导。
    pins = EA._lock_versions(_PROJECT_ROOT)
    assert pins["agentdojo"] == EA._env_identity()["agentdojo"]
    assert pins["openai"] == EA._env_identity()["openai"]


def test_lock_versions_fail_closed_on_duplicate_block(tmp_path):
    # ⭐ R3-D1：同名 package 多块 → fail-closed（不静默后写覆盖）。
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "agentdojo"\nversion = "0.1.35"\n\n'
        '[[package]]\nname = "agentdojo"\nversion = "0.9.9"\n', encoding="utf-8")
    with pytest.raises(AuthorizationError, match="多个 package 块"):
        EA._lock_versions(str(tmp_path), ("agentdojo",))


# ---------------- R3-D1 / R4-D1：运行解释器 == 项目 .venv + import provenance ----------------
def test_running_interpreter_matches_project_venv_or_skip(monkeypatch):
    import sys
    monkeypatch.delenv("PYTHONPATH", raising=False)   # R4-D1：只测 prefix 逻辑，隔离 import-path
    monkeypatch.delenv("PYTHONHOME", raising=False)
    if os.path.realpath(sys.prefix) != os.path.realpath(os.path.join(_PROJECT_ROOT, ".venv")):
        pytest.skip("测试解释器非项目 .venv（本机跑法不同）")
    out = EA._verify_running_interpreter(_PROJECT_ROOT)
    assert out["sys_prefix"] == out["project_venv"]


def test_running_interpreter_fail_closed_on_mismatch(monkeypatch):
    monkeypatch.delenv("PYTHONPATH", raising=False)
    monkeypatch.delenv("PYTHONHOME", raising=False)
    monkeypatch.setattr(EA.sys, "prefix", "/tmp/some-other-venv")
    with pytest.raises(AuthorizationError, match="运行解释器不是项目 .venv"):
        EA._verify_running_interpreter(_PROJECT_ROOT)


def test_running_interpreter_fail_closed_on_pythonpath(monkeypatch):
    # ⭐ R4-D1：非空 PYTHONPATH 可 shadow 已装包、坏 import provenance → fail-closed（sys.prefix 不变）。
    monkeypatch.setenv("PYTHONPATH", "/tmp/evil")
    with pytest.raises(AuthorizationError, match="PYTHONPATH 非空"):
        EA._verify_running_interpreter(_PROJECT_ROOT)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv 不在 PATH（本机跑跳过）")
def test_lock_sync_ignores_malicious_uv_project_environment_override(monkeypatch):
    # ⭐ R4-D1：即使继承恶意 UV_PROJECT_ENVIRONMENT，_verify_lock_sync 也强制核 repo/.venv → 仍通过。
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "/tmp/evil-redirected-venv")
    monkeypatch.setenv("UV_PROJECT", "/tmp/evil-project")
    out = EA._verify_lock_sync(_PROJECT_ROOT)
    assert out["returncode"] == 0
    assert out["pinned_project_environment"] == os.path.realpath(os.path.join(_PROJECT_ROOT, ".venv"))


def test_lock_sync_strips_all_inherited_uv_vars_allowlist(monkeypatch):
    # ⭐ R5-D1：UV_ONLY_INSTALL_LOCAL=1 让 uv 只校验 0 个远端依赖、近乎空过（已复现绕过）。受控 env 必须
    # 清掉**全部**继承 UV_*（allowlist：逐个 blocklist 会漏新变量），只留显式设的 UV_PROJECT_ENVIRONMENT。
    monkeypatch.setenv("UV_ONLY_INSTALL_LOCAL", "1")
    monkeypatch.setenv("UV_INDEX_URL", "http://evil")
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "/tmp/evil-inherited")
    captured = {}

    class _Proc:
        returncode, stdout, stderr = 0, "", ""

    def _fake_run(cmd, **kw):
        captured["env"], captured["cmd"] = kw.get("env"), cmd
        return _Proc()

    monkeypatch.setattr(EA.shutil, "which", lambda _n: "/usr/bin/uv")
    monkeypatch.setattr(EA.subprocess, "run", _fake_run)
    EA._verify_lock_sync(_PROJECT_ROOT)
    uv_keys = {k for k in captured["env"] if k.startswith("UV_")}
    assert uv_keys == {"UV_PROJECT_ENVIRONMENT"}          # 全部继承 UV_* 被清、只留显式一个
    assert captured["env"]["UV_PROJECT_ENVIRONMENT"] == \
        os.path.realpath(os.path.join(_PROJECT_ROOT, ".venv"))
    assert "--no-config" in captured["cmd"] and "--project" in captured["cmd"]


# ---------------- R3-D2 / R4-D2：provider budget cap 可执行契约 ----------------
def _cap_rule(**over):
    r = {"provider": "OpenRouter", "required": True, "cap_scope": "account",
         "max_allowed_cap_usd": 10, "approval_attestation_field": "provider_cap_attestation",
         "required_attestation_keys": ["cap_configured", "cap_usd", "scope", "attested_by", "observed_at"]}
    r.update(over)
    return r


def _past_iso(hours=1):
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=hours)).isoformat()


def _cap_att(**over):
    a = {"cap_configured": True, "cap_usd": 5, "scope": "account",
         "attested_by": "l9g", "observed_at": _past_iso()}
    a.update(over)
    return a


def test_provider_cap_pass():
    out = EA._enforce_provider_budget_cap(
        {"external_budget_control": _cap_rule()},
        {"provider_cap_attestation": _cap_att()})
    assert out["cap_usd"] == 5 and out["scope"] == "account" and out["required"] is True


def test_provider_cap_fail_closed_on_nan_and_inf():
    # ⭐ R4-D2：NaN/inf 绕过 `<=0`/`>ceiling` 朴素比较，必须 math.isfinite 显式拒。
    for bad in (float("nan"), float("inf")):
        with pytest.raises(AuthorizationError, match="有限正数"):
            EA._enforce_provider_budget_cap(
                {"external_budget_control": _cap_rule()},
                {"provider_cap_attestation": _cap_att(cap_usd=bad)})


def test_provider_cap_fail_closed_on_illegal_ceiling():
    # ⭐ R4-D2：required 规则自身 ceiling 非法 → 规则不可执行 → 拒。
    with pytest.raises(AuthorizationError, match="max_allowed_cap_usd 非合法有限正数"):
        EA._enforce_provider_budget_cap(
            {"external_budget_control": _cap_rule(max_allowed_cap_usd=float("nan"))},
            {"provider_cap_attestation": _cap_att()})


def test_provider_cap_fail_closed_on_illegal_observed_at():
    # ⭐ R4-D2：observed_at 只非空不够，须严格可解析。
    with pytest.raises(AuthorizationError, match="observed_at 非合法时间"):
        EA._enforce_provider_budget_cap(
            {"external_budget_control": _cap_rule()},
            {"provider_cap_attestation": _cap_att(observed_at="not-a-time")})


def test_provider_cap_fail_closed_on_future_observed_at():
    future = (datetime.datetime.now(datetime.timezone.utc)
              + datetime.timedelta(hours=2)).isoformat()
    with pytest.raises(AuthorizationError, match="observed_at 在未来"):
        EA._enforce_provider_budget_cap(
            {"external_budget_control": _cap_rule()},
            {"provider_cap_attestation": _cap_att(observed_at=future)})


def test_provider_cap_fail_closed_on_provider_mismatch():
    # ⭐ R4-D2：cap 规则 provider 须适用于实际 provider（approval.approved_provider）。
    with pytest.raises(AuthorizationError, match="cap 规则须适用于实际 provider"):
        EA._enforce_provider_budget_cap(
            {"external_budget_control": _cap_rule(provider="OpenRouter")},
            {"approved_provider": "anthropic", "provider_cap_attestation": _cap_att()})


def test_provider_cap_provider_match_normalized_passes():
    out = EA._enforce_provider_budget_cap(
        {"external_budget_control": _cap_rule(provider="OpenRouter")},
        {"approved_provider": "openrouter", "provider_cap_attestation": _cap_att()})
    assert out["cap_usd"] == 5


# ---------------- R4-C1：receipt 回显 provider_budget_cap ----------------
def test_receipt_echoes_provider_budget_cap(tmp_path):
    art = tmp_path / "run.json"
    art.write_text('{"x":1}', encoding="utf-8")
    meta = {"execution_request_hash": "h", "request_commit": "c1", "approval_commit": "c2",
            "authorization_status": "approved", "approved_budget_cap_usd": 3.0,
            "budget_enforcement": "hash-bound preflight plus max_trials; no live USD metering",
            "provider_budget_cap": {"provider": "OpenRouter", "cap_usd": 8, "scope": "account"},
            "deadline_utc": "2026-07-24T02:00:00Z", "run_status": "completed"}
    p = EA.write_run_receipt(str(art), meta, {"verdict": "c2_pass"}, "2026-07-24T00:00:00Z",
                             out_dir=str(tmp_path / "receipts"))
    import json as _json
    rec = _json.loads(open(p, encoding="utf-8").read())
    assert rec["provider_budget_cap"] == meta["provider_budget_cap"]
    assert rec["approved_budget_cap_usd"] == 3.0 and "no live USD metering" in rec["budget_enforcement"]
    assert rec["deadline_utc"] == "2026-07-24T02:00:00Z" and rec["run_status"] == "completed"
    assert rec["termination_reason"] is None   # 缺则 None、不臆造


def test_provider_cap_not_required_is_backward_compatible():
    assert EA._enforce_provider_budget_cap({}, {}) is None
    assert EA._enforce_provider_budget_cap(
        {"external_budget_control": _cap_rule(required=False)}, {}) is None


def test_provider_cap_fail_closed_when_attestation_missing():
    with pytest.raises(AuthorizationError, match="approval 缺"):
        EA._enforce_provider_budget_cap({"external_budget_control": _cap_rule()}, {})


def test_provider_cap_fail_closed_when_not_configured():
    with pytest.raises(AuthorizationError, match="cap_configured 必须为 true"):
        EA._enforce_provider_budget_cap(
            {"external_budget_control": _cap_rule()},
            {"provider_cap_attestation": _cap_att(cap_configured=False)})


def test_provider_cap_fail_closed_over_max_allowed():
    with pytest.raises(AuthorizationError, match="超过 request 允许上限"):
        EA._enforce_provider_budget_cap(
            {"external_budget_control": _cap_rule(max_allowed_cap_usd=10)},
            {"provider_cap_attestation": _cap_att(cap_usd=25)})


def test_provider_cap_fail_closed_on_scope_mismatch():
    with pytest.raises(AuthorizationError, match="scope"):
        EA._enforce_provider_budget_cap(
            {"external_budget_control": _cap_rule(cap_scope="account")},
            {"provider_cap_attestation": _cap_att(scope="key")})


def test_provider_cap_fail_closed_on_missing_required_key():
    with pytest.raises(AuthorizationError, match="缺必填 attestation 字段"):
        EA._enforce_provider_budget_cap(
            {"external_budget_control": _cap_rule()},
            {"provider_cap_attestation": _cap_att(observed_at="")})
