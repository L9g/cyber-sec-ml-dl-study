"""ADR-0022 执行授权治理的信任核单测（golden 迁自 run_calendar_probe.py 自检 26）。

覆盖不需要真实 git 的纯逻辑：逐 trial deadline、run 级/trial 级完成与排除语义、
以及搬迁后 `_PROJECT_ROOT` 必须仍解析到含 scripts/ 的项目根（否则授权链哈希材料时会读错文件）。
项目仓库上的 git-backed validate_execution_authorization 由 runner --self-test 端到端覆盖；
**instrument qualification campaign / 前缀门**（预注册 §7/§9）另在**临时 git 仓库**上端到端覆盖
（见文末一节）——那些门的要害恰是字节 + commit 顺序，纯 mock 证不出来。
"""
import datetime
import json
import os
import shutil
import subprocess

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


# =========== instrument qualification campaign + 前缀门（预注册 §7/§9，落码步骤③）===========
# 全部跑在 **临时 git 仓库**上：这些门保证的就是「字节一致 + commit 顺序」，用 mock 证不出来。
# 无网络、无模型、无计费。

QUAL_NOW = datetime.datetime(2026, 8, 3, 12, 0, tzinfo=datetime.timezone.utc)
CAMPAIGN_ID = "qual-list-titles-001"
DERIVER_PATH = "src/ithuriel/probes/calendar/qualification.py"
PREREG_PATH = "docs/trial/prereg-instrument-qualification-list-titles.md"
GATE_PATH = "docs/trial/qualification/prefix-gate-001-w1.json"
REQ_PATH = "docs/trial/execution-request-qual-001-w2.json"
APR_PATH = "docs/trial/approval-qual-001-w2.json"


def _git_run(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _write(repo, rel, text):
    p = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def _write_json(repo, rel, obj):
    return _write(repo, rel, json.dumps(obj, ensure_ascii=False, indent=1))


def _commit(repo, paths, msg):
    _git_run(repo, "add", "--", *paths)
    _git_run(repo, "commit", "-m", msg, "--no-gpg-sign")


def _gate_record(**over):
    rec = {"campaign_id": CAMPAIGN_ID, "rule_version": EA.QUAL_RULE_VERSION,
           "deriver_sha256": None,           # 由 builder 填成实际派生器材料哈希
           "campaign_status": "in_progress", "next_window_authorizable": True,
           "covers": [1],
           "window_inputs": {"1": {"artifact_sha256": "a" * 64, "receipt_sha256": "r" * 64}}}
    rec.update(over)
    return rec


def _build_qual_repo(tmp_path, *, window_index=2, campaign_over=None, gate_over=None,
                     drop_campaign=False, gate_after_request=False, budget=3.0,
                     declared_gate_sha=None, campaign_del=()):
    """临时仓库 + 完整 Hat A→Hat B 链；默认 = 窗口 2、带合法前缀门。返回 (repo, req, apr, runtime)。"""
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _git_run(repo, "init", "-q")
    _git_run(repo, "config", "user.email", "test@example.invalid")
    _git_run(repo, "config", "user.name", "test")

    _write(repo, "scripts/run_calendar_probe.py", "# dummy runner\n")
    _write(repo, PREREG_PATH, "# dummy prereg (FROZEN)\n")
    _write(repo, DERIVER_PATH, "# dummy deriver\n")
    mats = ["scripts/run_calendar_probe.py", PREREG_PATH, DERIVER_PATH]
    materials = [{"path": p, "sha256": EA._file_sha(repo, p)} for p in sorted(mats)]
    deriver_sha = EA._file_sha(repo, DERIVER_PATH)

    gate = _gate_record(**(gate_over or {}))
    if gate.get("deriver_sha256") is None:
        gate["deriver_sha256"] = deriver_sha
    _write_json(repo, GATE_PATH, gate)

    if gate_after_request:
        _commit(repo, mats, "materials")          # 前缀门先不进历史
    else:
        _commit(repo, mats + [GATE_PATH], "materials + prefix gate")

    runtime = {"runner": "scripts/run_calendar_probe.py", "materials": materials,
               "max_runtime_minutes": 90.0, "measurement_schema_version": 4,
               "experiment_mode": "confirm", "phase": "main",
               "analysis_eligibility": "preregistered", "target": "agentdojo-workspace-mock",
               "target_fidelity": "mock", "provider": "openrouter", "model": "openai/gpt-4o-mini",
               "pinned_provider": "OpenAI", "budget_cap_usd": budget}
    campaign = {
        "qualification_campaign_id": CAMPAIGN_ID,
        "prereg_sha256": EA._file_sha(repo, PREREG_PATH),
        "window_index": window_index, "k_windows": 3,
        "campaign_start_utc": "2026-08-01T00:00:00+00:00",
        "windows": {"1": {"allowed_start_utc": "2026-08-01T00:00:00+00:00",
                          "allowed_end_utc": "2026-08-01T23:59:59+00:00"},
                    "2": {"allowed_start_utc": "2026-08-03T00:00:00+00:00",
                          "allowed_end_utc": "2026-08-03T23:59:59+00:00"},
                    "3": {"allowed_start_utc": "2026-08-05T00:00:00+00:00",
                          "allowed_end_utc": "2026-08-05T23:59:59+00:00"}},
        "rule_version": EA.QUAL_RULE_VERSION,
        "deriver": {"path": DERIVER_PATH, "sha256": deriver_sha},
        "qualification_config_hash": "c" * 64,
    }
    if window_index >= 2:
        campaign["prefix_gate_record"] = {
            "path": GATE_PATH, "sha256": declared_gate_sha or EA._file_sha(repo, GATE_PATH)}
    campaign.update(campaign_over or {})
    for key in campaign_del:
        campaign.pop(key, None)

    request = {"request_id": "qual-001-w2", "runtime": runtime, "materials": materials,
               "allowed_side_effects": ["mock state"], "prohibited_side_effects": ["real delivery"],
               "roe_or_policy_ref": "docs/adr/0022-solo-developer-two-hat-governance.md",
               "prereg_ref": PREREG_PATH}
    if not drop_campaign:
        request["qualification_campaign"] = campaign
    req_hash = EA._sha(request)
    _write_json(repo, REQ_PATH, {"request": request, "execution_request_hash": req_hash})
    if gate_after_request:
        _commit(repo, [REQ_PATH], "hat A request")
        _commit(repo, [GATE_PATH], "prefix gate (LATE — 冻结之后才产出)")
    else:
        _commit(repo, [REQ_PATH], "hat A request")

    approval = {"decision": "approve", "authorization_mode": "self_authorized_solo",
                "role_separation": "procedural", "person_independence": "none",
                "independence_verification": "not_applicable",
                "conflict_of_interest": "self_review",
                "approval_scope": "internal_t0_t2_development",
                "approved_by": "l9g", "approval_role": "execution_authorizer",
                "approved_target": runtime["target"], "approved_provider": runtime["provider"],
                "budget_cap_usd": budget, "adversarial_review": "none",
                "execution_request_hash": req_hash,
                "valid_from": "2026-08-03T11:00:00+00:00",
                "valid_until": "2026-08-03T20:00:00+00:00"}
    _write_json(repo, APR_PATH, {"approval": approval})
    _commit(repo, [APR_PATH], "hat B approval")
    return repo, os.path.join(repo, REQ_PATH), os.path.join(repo, APR_PATH), runtime


def _validate(tmp_path, **kw):
    repo, req, apr, rt = _build_qual_repo(tmp_path, **kw)
    return EA.validate_execution_authorization(req, apr, rt, now=QUAL_NOW, repo_root=repo)


# ---------------- 正路：窗口 2 带合法前缀门 → 通过并回显 campaign ----------------
def test_qualification_window2_passes_and_echoes_campaign(tmp_path):
    meta = _validate(tmp_path)
    camp = meta["qualification_campaign"]
    assert camp["qualification_campaign_id"] == CAMPAIGN_ID
    assert (camp["window_index"], camp["k_windows"]) == (2, 3)
    assert camp["campaign_deadline_utc"] == "2026-08-15T00:00:00+00:00"   # start + 14d，机械算
    assert camp["prefix_gate_record"]["covers"] == [1]
    assert camp["prefix_gate_record"]["path"] == GATE_PATH


def test_receipt_echoes_qualification_campaign(tmp_path):
    art = tmp_path / "run.json"
    art.write_text('{"x":1}', encoding="utf-8")
    camp = {"qualification_campaign_id": CAMPAIGN_ID, "window_index": 2}
    p = EA.write_run_receipt(str(art), {"qualification_campaign": camp}, {"verdict": "c2_pass"},
                             "2026-08-03T12:00:00Z", out_dir=str(tmp_path / "receipts"))
    assert json.loads(open(p, encoding="utf-8").read())["qualification_campaign"] == camp


def test_request_without_campaign_is_backward_compatible(tmp_path):
    # 既有 C2/sweep/pilot 的 request 不含该块 → 行为不变、字段为 None（不臆造）。
    meta = _validate(tmp_path, window_index=1, drop_campaign=True)
    assert meta["qualification_campaign"] is None
    assert meta["authorization_status"] == "approved"


def test_window1_needs_no_prefix_gate(tmp_path):
    meta = _validate(tmp_path, window_index=1,
                     campaign_over={"windows": {  # 窗口 1 区间挪到 now 所在日，其余不变
                         "1": {"allowed_start_utc": "2026-08-03T00:00:00+00:00",
                               "allowed_end_utc": "2026-08-03T23:59:59+00:00"},
                         "2": {"allowed_start_utc": "2026-08-05T00:00:00+00:00",
                               "allowed_end_utc": "2026-08-05T23:59:59+00:00"},
                         "3": {"allowed_start_utc": "2026-08-07T00:00:00+00:00",
                               "allowed_end_utc": "2026-08-07T23:59:59+00:00"}}})
    assert meta["qualification_campaign"]["prefix_gate_record"] is None


def test_window1_must_not_bind_prefix_gate(tmp_path):
    with pytest.raises(AuthorizationError, match="窗口 1 不得绑定 prefix_gate_record"):
        _validate(tmp_path, window_index=1,
                  campaign_over={"prefix_gate_record": {"path": GATE_PATH, "sha256": "x" * 64},
                                 "windows": {
                                     "1": {"allowed_start_utc": "2026-08-03T00:00:00+00:00",
                                           "allowed_end_utc": "2026-08-03T23:59:59+00:00"},
                                     "2": {"allowed_start_utc": "2026-08-05T00:00:00+00:00",
                                           "allowed_end_utc": "2026-08-05T23:59:59+00:00"},
                                     "3": {"allowed_start_utc": "2026-08-07T00:00:00+00:00",
                                           "allowed_end_utc": "2026-08-07T23:59:59+00:00"}}})


# ---------------- 前缀门：缺失 / 不可授权 / 覆盖不符 / 终局 / 字节 / 顺序 ----------------
def test_missing_prefix_gate_rejects_window2(tmp_path):
    with pytest.raises(AuthorizationError, match="缺 prefix_gate_record"):
        _validate(tmp_path, campaign_del=("prefix_gate_record",))


def test_prefix_gate_not_authorizable_rejects(tmp_path):
    with pytest.raises(AuthorizationError, match="next_window_authorizable"):
        _validate(tmp_path, gate_over={"next_window_authorizable": False})


def test_prefix_gate_terminal_status_rejects(tmp_path):
    # 前缀已终局（如 terminal_not_qualified）→ 预注册提前停止：不得再花钱跑后续窗口。
    with pytest.raises(AuthorizationError, match="campaign_status"):
        _validate(tmp_path, gate_over={"campaign_status": "terminal_not_qualified"})


def test_prefix_gate_covers_must_be_exactly_1_to_w_minus_1(tmp_path):
    with pytest.raises(AuthorizationError, match="covers"):
        _validate(tmp_path, gate_over={"covers": [1, 2],
                                       "window_inputs": {
                                           "1": {"artifact_sha256": "a" * 64, "receipt_sha256": "r" * 64},
                                           "2": {"artifact_sha256": "b" * 64, "receipt_sha256": "s" * 64}}})


def test_prefix_gate_window_inputs_must_carry_hashes(tmp_path):
    with pytest.raises(AuthorizationError, match="缺输入哈希"):
        _validate(tmp_path, gate_over={"window_inputs": {"1": {"artifact_sha256": "a" * 64}}})


def test_prefix_gate_declared_hash_mismatch_rejects(tmp_path):
    with pytest.raises(AuthorizationError, match="三方哈希不一致"):
        _validate(tmp_path, declared_gate_sha="d" * 64)


def test_prefix_gate_from_other_deriver_rejects(tmp_path):
    with pytest.raises(AuthorizationError, match="另一版派生器"):
        _validate(tmp_path, gate_over={"deriver_sha256": "e" * 64})


def test_prefix_gate_campaign_id_mismatch_rejects(tmp_path):
    with pytest.raises(AuthorizationError, match="campaign_id 与本窗口 campaign 不符"):
        _validate(tmp_path, gate_over={"campaign_id": "other-campaign"})


def test_prefix_gate_must_be_committed_before_hat_a_freeze(tmp_path):
    # ⭐ 要害：前缀验证必须**先于**本窗口 Hat A 冻结发生；事后补一份记录不算门。
    with pytest.raises(AuthorizationError, match="prefix_gate → 窗口 2 Hat A request"):
        _validate(tmp_path, gate_after_request=True)


# ---------------- campaign 块自身的机械门 ----------------
def test_deriver_must_be_governed_material(tmp_path):
    with pytest.raises(AuthorizationError, match="未列入受管辖材料"):
        _validate(tmp_path, campaign_over={"deriver": {"path": "src/ithuriel/probes/calendar/c2.py",
                                                       "sha256": "f" * 64}})


def test_deriver_sha_must_match_material_declaration(tmp_path):
    with pytest.raises(AuthorizationError, match="deriver.sha256 与受管辖材料声明不一致"):
        _validate(tmp_path, campaign_over={"deriver": {"path": DERIVER_PATH, "sha256": "f" * 64}})


def test_prereg_sha_must_match_governed_prereg(tmp_path):
    with pytest.raises(AuthorizationError, match="prereg_sha256 与受管辖 prereg 哈希不符"):
        _validate(tmp_path, campaign_over={"prereg_sha256": "9" * 64})


def test_k_windows_frozen_at_three(tmp_path):
    with pytest.raises(AuthorizationError, match="k_windows"):
        _validate(tmp_path, campaign_over={"k_windows": 2})


def test_window_index_out_of_range_rejects(tmp_path):
    with pytest.raises(AuthorizationError, match="window_index"):
        _validate(tmp_path, campaign_over={"window_index": 4})


def test_windows_must_cover_exactly_1_to_k(tmp_path):
    with pytest.raises(AuthorizationError, match="必须精确覆盖 1..3"):
        _validate(tmp_path, campaign_over={"windows": {
            "1": {"allowed_start_utc": "2026-08-01T00:00:00+00:00",
                  "allowed_end_utc": "2026-08-01T23:59:59+00:00"},
            "2": {"allowed_start_utc": "2026-08-03T00:00:00+00:00",
                  "allowed_end_utc": "2026-08-03T23:59:59+00:00"}}})


def test_declared_interval_outside_campaign_validity_rejects(tmp_path):
    with pytest.raises(AuthorizationError, match="越出 campaign 有效期"):
        _validate(tmp_path, campaign_over={"windows": {
            "1": {"allowed_start_utc": "2026-08-01T00:00:00+00:00",
                  "allowed_end_utc": "2026-08-01T23:59:59+00:00"},
            "2": {"allowed_start_utc": "2026-08-03T00:00:00+00:00",
                  "allowed_end_utc": "2026-08-03T23:59:59+00:00"},
            "3": {"allowed_start_utc": "2026-08-20T00:00:00+00:00",       # > start + 14d
                  "allowed_end_utc": "2026-08-20T23:59:59+00:00"}}})


def test_now_outside_declared_window_interval_rejects(tmp_path):
    # 跑前门：当前时刻不在本窗口预声明区间 → 拒开窗口（派生器事后再按 started_at 重核）。
    with pytest.raises(AuthorizationError, match="不在窗口 2 的预声明区间"):
        _validate(tmp_path, campaign_over={"windows": {
            "1": {"allowed_start_utc": "2026-08-01T00:00:00+00:00",
                  "allowed_end_utc": "2026-08-01T23:59:59+00:00"},
            "2": {"allowed_start_utc": "2026-08-04T00:00:00+00:00",       # now=08-03 落在外
                  "allowed_end_utc": "2026-08-04T23:59:59+00:00"},
            "3": {"allowed_start_utc": "2026-08-05T00:00:00+00:00",
                  "allowed_end_utc": "2026-08-05T23:59:59+00:00"}}})


def test_budget_predicate_enforced_at_authorization(tmp_path):
    # 每窗口 $3（=300 分）；$5 的 request 在授权门就被拒，不必等到事后派生。
    with pytest.raises(AuthorizationError, match="预算谓词不符"):
        _validate(tmp_path, budget=5.0)


def test_missing_campaign_field_fails_closed(tmp_path):
    with pytest.raises(AuthorizationError, match="缺必填字段"):
        _validate(tmp_path, campaign_del=("qualification_config_hash",))


def test_rule_version_must_match_frozen_deriver(tmp_path):
    with pytest.raises(AuthorizationError, match="rule_version"):
        _validate(tmp_path, campaign_over={"rule_version": "qualification/v0"})
