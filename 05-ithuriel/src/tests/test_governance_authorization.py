"""ADR-0022 执行授权治理的信任核单测（golden 迁自 run_calendar_probe.py 自检 26）。

覆盖不需要真实 git 的纯逻辑：逐 trial deadline、run 级/trial 级完成与排除语义、
以及搬迁后 `_PROJECT_ROOT` 必须仍解析到含 scripts/ 的项目根（否则授权链哈希材料时会读错文件）。
git-backed 的 validate_execution_authorization 由 runner --self-test 端到端覆盖。
"""
import datetime
import os

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


# ---------------- D1 preflight：已装版本 vs uv.lock（partner review 2026-07-24）----------------
def test_env_lock_check_passes_on_current_repo():
    # 当前 .venv 与 uv.lock 一致 → 返回 locked/installed，且两者相等。
    out = verify_env_matches_lock()
    assert set(out["locked"]) == {"agentdojo", "openai"}
    assert out["locked"] == out["installed"]


def test_env_lock_check_fails_closed_on_installed_drift(monkeypatch):
    # 模拟已装 agentdojo 漂移到 lock 未声明的版本 → fail closed（捕获 runtime 相等门抓不到的初始不一致）。
    real = EA._env_identity()
    monkeypatch.setattr(EA, "_env_identity",
                        lambda: {**real, "agentdojo": "0.9.99-drifted"})
    with pytest.raises(AuthorizationError, match="uv.lock 不一致"):
        verify_env_matches_lock()


def test_lock_versions_ignores_dependency_reference_lines():
    # 解析只取顶层 package 块的 version，不被 `{ name = "openai" }` 依赖引用行误导。
    pins = EA._lock_versions(_PROJECT_ROOT)
    assert pins["agentdojo"] == EA._env_identity()["agentdojo"]
    assert pins["openai"] == EA._env_identity()["openai"]
