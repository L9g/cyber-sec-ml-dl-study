"""执行/授权机器代码契约（slice 3 / ADR-0013）——两阶段 PEP + RoE + 命令文法 + mock backend。

seams #1/#2：结构化 Action 只有过两阶段授权才到 mock backend；backend 只产 execution facts。
断言全确定性；**无真实网络 I/O**（MockBackend 不调 subprocess/socket）。
"""
from __future__ import annotations

import pytest

from ithuriel.executor import (
    ExecutionDenied,
    ExecutionReceipt,
    MockBackend,
    NetworkPortScanAction,
    RoEAuthorization,
    execute,
    pre_dispatch,
    preflight,
)


def _action(target="192.0.2.10", ports=(22, 443), label=""):
    return NetworkPortScanAction(target_ip=target, ports=ports, label=label)


def _roe(targets=("192.0.2.0/24",), version="roe-v1"):
    return RoEAuthorization(roe_version=version, allowed_targets=list(targets))


# ── Action hash：策略字段进、展示字段不进 ────────────────────────────────────
def test_policy_field_change_changes_hash():
    assert _action(ports=(22, 443)).action_hash != _action(ports=(22, 80)).action_hash
    assert _action(target="192.0.2.10").action_hash != _action(target="192.0.2.11").action_hash


def test_presentation_field_change_preserves_hash():
    # label（展示字段）变不改 hash；ports 顺序不影响（规范排序）。
    assert _action(label="scan A").action_hash == _action(label="scan B").action_hash
    assert _action(ports=(443, 22)).action_hash == _action(ports=(22, 443)).action_hash


# ── 命令文法：固定模板、无任意 argv、target 严格一致 ─────────────────────────
def test_compiled_argv_fixed_template_single_target():
    argv = _action(target="192.0.2.10", ports=(22, 443)).compile_argv()
    assert argv == ["nmap", "-sT", "-Pn", "-p", "22,443", "-oX", "-", "--", "192.0.2.10"]
    # 结构化 target 与 argv 中 target 严格一致、且仅一个 target。
    assert argv[-1] == "192.0.2.10" and argv.count("192.0.2.10") == 1


def test_no_iL_or_script_expressible():
    # -iL / --script / 额外 target / 输出路径无法由 Action 表达（类型层不可表达 → argv 不含）。
    argv = _action().compile_argv()
    for forbidden in ("-iL", "--script", "-oN", "|", ";", "&&"):
        assert forbidden not in argv


# ── 两阶段 PEP：pre-dispatch 不信 preflight ──────────────────────────────────
def test_pre_dispatch_rejects_action_hash_mismatch():
    # 计划后 target/ports 被改（到达 dispatch 的 action ≠ 被 preflight 的）→ hash 不一致拒绝。
    a1, roe = _action(ports=(22, 443)), _roe()
    decision = preflight(a1, roe)
    assert decision.allowed
    a2 = _action(ports=(22, 443, 8080))        # 篡改后
    ok, reason = pre_dispatch(a2, roe, decision)
    assert ok is False and reason == "action_hash_mismatch"


def test_pre_dispatch_rejects_roe_version_change():
    a = _action()
    decision = preflight(a, _roe(version="roe-v1"))
    ok, reason = pre_dispatch(a, _roe(version="roe-v2"), decision)   # 两阶段间 RoE 变了
    assert ok is False and reason == "roe_version_changed"


def test_pre_dispatch_reruns_policy_not_trusting_preflight():
    # pre-dispatch 独立重跑策略：preflight 通过后把 RoE 换成不授权该 target 的（同 version）→ 仍拒绝。
    a = _action(target="192.0.2.10")
    decision = preflight(a, _roe(targets=("192.0.2.0/24",), version="roe-v1"))
    assert decision.allowed
    revoked = RoEAuthorization(roe_version="roe-v1", allowed_targets=["10.0.0.0/8"])  # 不含 192.0.2.10
    ok, reason = pre_dispatch(a, revoked, decision)
    assert ok is False and reason == "target_not_authorized"


# ── RoE 授权：默认拒绝、literal IP、CIDR ─────────────────────────────────────
def test_empty_allowed_targets_default_deny():
    ok, reason = execute_denial(_action(), RoEAuthorization(roe_version="v", allowed_targets=[]))
    assert reason == "allowed_targets_empty"


def test_target_not_authorized_denied():
    ok, reason = execute_denial(_action(target="203.0.113.5"), _roe(targets=("192.0.2.0/24",)))
    assert reason == "target_not_authorized"


def execute_denial(action, roe):
    with pytest.raises(ExecutionDenied) as ei:
        execute(action, roe, fixture_text="<x/>", fixture_ref="fixture:x")
    return False, ei.value.reason


# ── MockBackend：不调用、无副作用、只产执行事实 ─────────────────────────────
class _SpyBackend(MockBackend):
    def __init__(self):
        self.dispatched = False

    def dispatch(self, action, fixture_text, fixture_ref):
        self.dispatched = True
        return super().dispatch(action, fixture_text, fixture_ref)


def test_denial_does_not_call_backend():
    spy = _SpyBackend()
    with pytest.raises(ExecutionDenied):
        execute(_action(target="203.0.113.5"), _roe(), fixture_text="<x/>",
                fixture_ref="fixture:x", backend=spy)
    assert spy.dispatched is False        # RoE 拒绝 → backend 从未被调


def test_receipt_is_execution_fact_only():
    receipt = execute(_action(), _roe(), fixture_text="<nmaprun/>", fixture_ref="fixture:nmap-1")
    assert isinstance(receipt, ExecutionReceipt)
    assert receipt.backend == "mock" and receipt.dispatch_performed is True
    assert receipt.external_side_effects_performed is False   # ⭐ 无真实网络 I/O
    assert receipt.exit_code == 0 and receipt.raw_artifact_ref.kind == "nmap-xml/v1"
    # receipt 不携带 Finding/status（execution fact only）。
    assert not any(k in receipt.model_dump() for k in ("status", "finding", "verdict"))
