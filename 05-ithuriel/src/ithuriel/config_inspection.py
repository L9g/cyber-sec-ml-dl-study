"""确定性 config-inspection 切片（slice 2 / ADR-0012）：CE-UK-FW-03 default-deny。

链路：capability 匹配 → 冻结 `ufw status verbose` RawArtifact → DefaultPolicyObservation →
确定性版本化规则 → Finding（**run_record=None、无 ComparisonSpec**）→ AssuranceReport + scope/gap。

**fixture-first**：只消费冻结 artifact，**不实现真实 `sudo ufw` 调用**（特权读取 + 执行授权 = slice 3）。
规范化调用意图 = `LC_ALL=C ufw status verbose`（钉进证据；避免本地化输出破坏解析）。

**本切片是「跨域通用性」的验证器**（ADR-0011）：复用 AI 切片的 Finding/Evidence/Assurance 模型，
观察确定性裁定是否被自然容纳——`# FRICTION:` 注记标出硌手处（据真实摩擦决定是否加字段，不提前设计）。
"""
from __future__ import annotations

import re
from typing import Any

from ithuriel.capability import (
    CAPABILITY_BRIDGE_PROVENANCE,
    AdapterDescriptor,
    adapter_satisfies,
    required_capabilities,
)
from ithuriel.models import (
    AssuranceReport,
    AutomaticRuleProvenance,
    EvidenceManifest,
    Finding,
    ScopeStatement,
    content_hash,
)
from ithuriel.registry import control, referenced_standards

CONTROL_ID = "CE-UK-FW-03"
RULE_VERSION = "ufw-default-deny/v1"     # 确定性裁定规则版本（随口径变而升）
INPUT_FORMAT = "ufw-status-verbose/v1"
NORMALIZED_INVOCATION = "LC_ALL=C ufw status verbose"

# slice 2 唯一 adapter（一格式、无多发行版抽象）。
UFW_ADAPTER = AdapterDescriptor(
    adapter_id="ufw_status_verbose",
    provides={"host.firewall.default_policy.inspect"},
    input_format=INPUT_FORMAT,
)


# ── 解析：raw text → DefaultPolicyObservation ────────────────────────────────
def parse_ufw_status(text: str) -> dict[str, Any]:
    """`ufw status verbose` → {status, incoming_default, default_line_present}。纯函数。

    只认两行核心证据（其余规则明细不解析——slice 2 只裁默认策略）：
      Status: active|inactive
      Default: deny (incoming), allow (outgoing), disabled (routed)
    """
    status = None
    m = re.search(r"(?m)^\s*Status:\s*(\S+)", text)
    if m:
        status = m.group(1).strip().lower()
    incoming = None
    dm = re.search(r"(?m)^\s*Default:\s*(.+)$", text)
    if dm:
        for part in dm.group(1).split(","):
            if "(incoming)" in part:
                incoming = part.strip().split()[0].lower()   # deny / allow / reject
    return {"status": status, "incoming_default": incoming,
            "default_line_present": dm is not None}


# ── 确定性规则：Observation → (status, rationale) ────────────────────────────
def evaluate_default_deny(obs: dict[str, Any], *, sole_authority: bool = False) -> tuple[str, str]:
    """CE-UK-FW-03 裁定规则（确定性、版本化 = RULE_VERSION）。四态：pass/fail/inconclusive。

    **认识论纪律（= AI 切片『bare ASR=0→inconclusive 非 pass』同源）**：UFW inactive **推不出**
    主机无 default-deny（可能 nftables/iptables/云 SG 在执行）→ inconclusive，**除非** TargetSnapshot
    声明 UFW 为唯一权威执行面（`sole_authority=True`）才可判 fail。缺正信号 ≠ 反结论。
    """
    st, inc = obs["status"], obs["incoming_default"]
    if st is None:
        return "inconclusive", "未识别 UFW `Status:` 行（格式未知/截断）→ 不可裁定，需重采规范化输出。"
    if st == "inactive":
        if sole_authority:
            return "fail", ("UFW inactive 且 TargetSnapshot 声明 UFW 为唯一权威执行面 → "
                            "无 default-deny 生效。")
        return "inconclusive", ("UFW inactive → 不能据此断言主机无 default-deny（可能由 "
                                "nftables/iptables/云 SG 执行）；仅当 TargetSnapshot 声明 UFW "
                                "为唯一权威执行面时才可判 fail。")
    if st != "active":
        return "inconclusive", f"UFW `Status: {st}` 非 active/inactive（未知状态）→ 不可裁定。"
    if inc is None:
        return "inconclusive", "UFW active 但未解析到 `Default: ...(incoming)` 策略（行缺失/截断）→ 不可裁定。"
    if inc in ("deny", "reject"):
        return "pass", f"UFW active 且 incoming 默认 `{inc}` → 满足 default-deny（CE-UK-FW-03）。"
    return "fail", f"UFW active 但 incoming 默认 `{inc}`（非 deny/reject）→ 违反 default-deny。"


# ── 组装：raw → AssuranceReport（复用 AI 切片模型，标 FRICTION）───────────────
def _host_target_ref(host_id: str, raw_hash: str) -> dict[str, Any]:
    # FRICTION: AI 切片 target_ref 是 model_id/transport/defense_hash 形状；确定性主机是 host+config。
    # 现用最小 host 形状，未抽象共同 target 契约（等第二个确定性 adapter 再看是否值得）。
    return {"host_id": host_id, "config_source": INPUT_FORMAT, "artifact_hash": raw_hash,
            "target_variant_hash": content_hash({"host": host_id, "cfg": raw_hash}, prefix="hv:")}


def build_report(raw_text: str, *, host_id: str, sole_authority: bool = False,
                 adapter: AdapterDescriptor = UFW_ADAPTER,
                 assessed_at: str = "2026-07-12T00:00:00+00:00",
                 generated_from: str = "fixture:ufw") -> AssuranceReport:
    """一份冻结 ufw 输出 → 结构化 AssuranceReport。capability 不匹配 → 覆盖缺口（不产 Finding）。"""
    ctrl = control(CONTROL_ID)

    # seams #3：control requirement ⊆ adapter.provides（一次子集判定、非 planner）。
    if not adapter_satisfies(CONTROL_ID, adapter):
        return _unsupported_report(host_id, adapter, assessed_at, generated_from,
                                   note="无满足 capability 需求的 adapter")

    obs = parse_ufw_status(raw_text)
    status, rationale = evaluate_default_deny(obs, sole_authority=sole_authority)

    raw_hash = content_hash({"raw": raw_text, "invocation": NORMALIZED_INVOCATION}, prefix="cfg:")
    artifacts = {raw_hash: {"kind": INPUT_FORMAT, "normalized_invocation": NORMALIZED_INVOCATION,
                            "text": raw_text, "observation": obs}}
    index = {"config": [raw_hash]}                       # 复用 index dict（AI 用 bare/defended）
    mctx = _measurement_context(ctrl, obs, sole_authority)
    manifest = EvidenceManifest(
        run_root=content_hash({"artifacts": artifacts, "index": index, "measurement_context": mctx},
                              prefix="run:"),
        measurement_context=mctx, artifacts=artifacts, index=index)

    finding = Finding(
        control_id=CONTROL_ID, target_ref=_host_target_ref(host_id, raw_hash),
        status=status, verdict_mode=ctrl.verification.verdict,   # automatic（registry）
        assessed_at=assessed_at, evidence_refs=[raw_hash],
        severity=ctrl.severity_if_failed if status == "fail" else None,  # Medium（registry）
        rationale=rationale,
        run_record=None,          # ⭐ FRICTION 观察点：确定性检查无 AI run → Finding 是否自然容纳？
        root_causes=None,         # FRICTION: root_cause_enum 是 AI 机理 P1–P6，对防火墙不适用 → fail 也 None
        evidence_completeness="per_trial",  # FRICTION: 词汇 AI-shaped（"trial"）；单确定性快照勉强套
        # Step 4（ADR-0016）：确定性规则作用于确定性观察 → automatic_rule + deterministic_observation
        # （与 probe 同变体；config↔probe 差异=target_fidelity，由 Claim 层从 execution_backend 派）。
        verdict_provenance=AutomaticRuleProvenance(
            rule_version=RULE_VERSION, measurement_kind="deterministic_observation"),
    )

    scope = ScopeStatement(
        claim="CE-UK-FW-03 default-deny 单主机 config-inspection（确定性、read-only 冻结证据）；非合规通过。",
        in_scope={"control": CONTROL_ID, "host": host_id, "input_format": adapter.input_format,
                  "rule_version": RULE_VERSION, "sole_authority": sole_authority},
        not_covered=[
            "真实主机执行（fixture-first；sudo ufw 特权读取 + 授权 = slice 3）",
            "其它防火墙执行面（nftables/iptables/云 SG）——UFW inactive 时不可反推",
            "多发行版/多输入格式（仅 ufw-status-verbose/v1）",
            "active probe（CE-UK-FW-01 automated_test = slice 3）",
        ],
        # FRICTION: measurement_valid 在 AI 切片=有正对照；这里复用为"artifact 可解析到可裁定"。
        measurement_valid=(obs["status"] is not None),
        underpowered=None,        # FRICTION: 确定性检查无统计功效概念（字段 AI-shaped）
        invalidity_reasons=[],
    )

    return AssuranceReport(
        generated_from=generated_from, measurement_context=mctx, evidence_manifest=manifest,
        findings=[finding], comparisons=[],     # ⭐ 非 bare/defended 实验 → 无 ComparisonSpec
        scope=scope, control=ctrl, referenced_standards=referenced_standards(CONTROL_ID),
    )


def _measurement_context(ctrl, obs: dict[str, Any], sole_authority: bool) -> dict[str, Any]:
    return {
        "control_id": CONTROL_ID, "domain": ctrl.domain,
        "verification_method": ctrl.verification.method,     # config_inspection
        "capability_required": sorted(required_capabilities(CONTROL_ID)),
        "capability_bridge": CAPABILITY_BRIDGE_PROVENANCE,   # 如实披露 provisional + 迁移条件
        "adapter": {"id": UFW_ADAPTER.adapter_id, "input_format": UFW_ADAPTER.input_format},
        "rule_version": RULE_VERSION,
        "normalized_invocation": NORMALIZED_INVOCATION,
        "execution_backend": "frozen-fixture",               # fixture-first（无真实主机执行）
        "sole_authority": sole_authority,
        # ADR-0008：plugin 是工具身份、**不透明 legacy metadata**，如实披露、不参与 capability 匹配。
        "legacy_plugin_opaque": ctrl.verification.plugin,
        "observation": obs,
    }


def _unsupported_report(host_id: str, adapter: AdapterDescriptor, assessed_at: str,
                        generated_from: str, note: str) -> AssuranceReport:
    """capability 不匹配 → 覆盖缺口、进分母，**不产 Finding**（对齐 C4：unsupported≠not_applicable）。"""
    ctrl = control(CONTROL_ID)
    mctx = {"control_id": CONTROL_ID, "adapter": adapter.adapter_id,
            "capability_required": sorted(required_capabilities(CONTROL_ID))}
    scope = ScopeStatement(
        claim=f"CE-UK-FW-03 未评（{note}）→ 覆盖缺口，不产 Finding。",
        in_scope={"control": CONTROL_ID, "host": host_id},
        not_covered=[f"unsupported（进覆盖分母）：{host_id} — {note}"],
        measurement_valid=False, underpowered=None, invalidity_reasons=["tooling_unsupported"],
    )
    empty = EvidenceManifest(run_root=content_hash({"empty": CONTROL_ID}, prefix="run:"),
                             measurement_context=mctx, artifacts={}, index={"config": []})
    return AssuranceReport(
        generated_from=generated_from, measurement_context=mctx, evidence_manifest=empty,
        findings=[], comparisons=[], scope=scope,
        control=ctrl, referenced_standards=referenced_standards(CONTROL_ID))
