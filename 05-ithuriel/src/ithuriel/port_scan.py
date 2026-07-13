"""主动探测切片（slice 3 / ADR-0013）：CE-UK-FW-01「Internet-exposed services identified **and
justified**」。链路：capability → 结构化 Action → **两阶段 PEP + RoE**（executor.py）→ MockBackend
→ ExecutionReceipt + RawArtifact → 解析 nmap XML → Observation → 确定性规则 → Finding →
AssuranceReport。**零真实网络 I/O**（fixture-first）。

⭐ **FW-01 的 justified 缺口（搭档 review 暴露的真实摩擦）**：nmap 只给 **observed open ports**
（= `identified`），**证明不了 `justified`**（服务是否经业务批准）。故**不能**因"扫描成功解析出端口"
就给 pass。最小闭环需 target-scoped `DeclaredService` 清单；**绝不在 parser 里偷偷写静态 allowed-port
列表**。profile 现有 evidence_requirements（target_scope/command_audit_log/parsed_open_ports）不足以
闭合 `justified` —— 记为 slice 发现（ADR-0013），不硬凑。
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Optional

from pydantic import BaseModel

from ithuriel.capability import (
    CAPABILITY_BRIDGE_PROVENANCE,
    AdapterDescriptor,
    adapter_satisfies,
    required_capabilities,
)
from ithuriel.executor import (
    ExecutionDenied,
    MockBackend,
    NetworkPortScanAction,
    RoEAuthorization,
    execute,
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

CONTROL_ID = "CE-UK-FW-01"
RULE_VERSION = "fw01-exposed-services-justified/v1"
INPUT_FORMAT = "nmap-xml/v1"

NMAP_ADAPTER = AdapterDescriptor(
    adapter_id="nmap_port_scan", provides={"host.network.port_scan"}, input_format=INPUT_FORMAT)

# RoE 授权原因（authorization / integrity）——区分"未授权"vs"两阶段间被篡改"。
_AUTHORIZATION_DENIALS = {"target_not_authorized", "allowed_targets_empty", "target_not_ip"}


class DeclaredService(BaseModel):
    """target-scoped 服务声明（justification inventory 一条）。`justified` = justification_ref 非空。"""
    port: int
    protocol: str = "tcp"
    owner: str
    justification_ref: str = ""       # change/ADR/ticket 引用；空 = 已声明但未 justified


# ── 解析 nmap XML → Observation（stdlib，无第三方）─────────────────────────────
def parse_nmap_open_ports(xml_text: str) -> dict[str, Any]:
    """nmap `-oX` → {open_ports:[{port,protocol,service}], parse_ok}。解析失败 → parse_ok=False。"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {"open_ports": [], "parse_ok": False}
    open_ports = []
    for port in root.iter("port"):
        state = port.find("state")
        if state is not None and state.get("state") == "open":
            svc = port.find("service")
            open_ports.append({"port": int(port.get("portid")), "protocol": port.get("protocol"),
                               "service": svc.get("name") if svc is not None else None})
    return {"open_ports": sorted(open_ports, key=lambda p: p["port"]), "parse_ok": True}


# ── 确定性规则：Observation × justification inventory → (status, rationale) ─────
def evaluate_fw01(obs: dict[str, Any],
                  declared: Optional[list[DeclaredService]]) -> tuple[str, str]:
    """CE-UK-FW-01 裁定（RULE_VERSION）。⭐ identified ≠ justified：无 inventory → inconclusive。"""
    if not obs["parse_ok"]:
        return "inconclusive", "nmap XML 解析失败（格式未知/截断）→ 不可裁定，需重采。"
    observed = {p["port"] for p in obs["open_ports"]}
    if declared is None:
        return "inconclusive", (
            f"扫描成功、observed 开放端口 {sorted(observed)}（= identified）；但**无 justification "
            "inventory** → 不能裁定这些服务是否经业务批准（justified）。identified≠justified，不给 pass。")
    justified = {d.port for d in declared if d.justification_ref}
    undeclared = observed - justified
    if undeclared:
        return "fail", (
            f"存在未声明/未 justified 的开放端口 {sorted(undeclared)}（observed 但不在 justified "
            f"inventory）→ 违反 FW-01（internet-exposed 但未 justified）。observed={sorted(observed)}、"
            f"justified={sorted(justified)}。")
    return "pass", (
        f"全部 observed 开放端口 {sorted(observed)} 均已声明并 justified（⊆ inventory）→ 满足 FW-01。")


def _target_ref(host_id: str, action: NetworkPortScanAction, raw_hash: str) -> dict[str, Any]:
    return {"host_id": host_id, "target_ip": action.target_ip, "config_source": INPUT_FORMAT,
            "artifact_hash": raw_hash, "action_hash": action.action_hash,
            "target_variant_hash": content_hash({"host": host_id, "raw": raw_hash}, prefix="hv:")}


def build_report(*, action: NetworkPortScanAction, roe: RoEAuthorization, nmap_xml: str,
                 fixture_ref: str, host_id: str,
                 declared_services: Optional[list[DeclaredService]] = None,
                 adapter: AdapterDescriptor = NMAP_ADAPTER,
                 assessed_at: str = "2026-07-13T00:00:00+00:00",
                 generated_from: str = "fixture:nmap") -> AssuranceReport:
    """冻结 nmap 输出 + RoE + justification inventory → AssuranceReport。

    capability 不匹配 → unsupported gap；**RoE/PEP 拒绝 → out_of_scope gap**（工具有能力、目标未授权，
    ≠ unsupported/inconclusive/not_applicable；不产 Finding、不调 backend）。
    """
    ctrl = control(CONTROL_ID)
    if not adapter_satisfies(CONTROL_ID, adapter):
        return _gap_report(host_id, "unsupported", "无满足 capability 需求的 adapter",
                           action_hash=action.action_hash, assessed_at=assessed_at,
                           generated_from=generated_from)

    # 两阶段 PEP + RoE + 命令白名单 → mock dispatch。拒绝 → out_of_scope gap（不产 Finding、不调 backend）。
    try:
        receipt = execute(action, roe, fixture_text=nmap_xml, fixture_ref=fixture_ref,
                          backend=MockBackend())
    except ExecutionDenied as e:
        kind = "out_of_scope" if e.reason in _AUTHORIZATION_DENIALS else "execution_integrity"
        return _gap_report(host_id, kind, f"{e.phase}:{e.reason}",
                           action_hash=action.action_hash, assessed_at=assessed_at,
                           generated_from=generated_from)

    obs = parse_nmap_open_ports(nmap_xml)
    status, rationale = evaluate_fw01(obs, declared_services)
    raw_hash = receipt.raw_artifact_ref.artifact_hash

    artifacts = {raw_hash: {"kind": INPUT_FORMAT, "nmap_xml": nmap_xml, "observation": obs,
                            "execution_receipt": receipt.model_dump()}}  # receipt 是执行事实、非 Evidence
    index = {"probe": [raw_hash]}
    mctx = _measurement_context(ctrl, action, roe, receipt, obs)
    manifest = EvidenceManifest(
        run_root=content_hash({"artifacts": artifacts, "index": index, "measurement_context": mctx},
                              prefix="run:"),
        measurement_context=mctx, artifacts=artifacts, index=index)

    finding = Finding(
        control_id=CONTROL_ID, target_ref=_target_ref(host_id, action, raw_hash),
        status=status, verdict_mode=ctrl.verification.verdict, assessed_at=assessed_at,
        evidence_refs=[raw_hash],
        severity=ctrl.severity_if_failed if status == "fail" else None,   # Medium
        rationale=rationale,
        run_record=None,          # FRICTION（同 slice 2）：探测无 AI run；但探测是**测量**（见下 verdict_source）
        root_causes=None, evidence_completeness="per_trial",
        # Step 4（ADR-0016）：确定性规则作用于（mock）执行观察 → automatic_rule + deterministic_observation；
        # 与 config 同变体，差异=target_fidelity（mock vs frozen-fixture），Claim 层从 execution_backend 派。
        verdict_provenance=AutomaticRuleProvenance(
            rule_version=RULE_VERSION, measurement_kind="deterministic_observation"),
    )
    scope = ScopeStatement(
        claim="CE-UK-FW-01 exposed-services 单主机主动探测（**mock backend、零真实网络 I/O**）；非合规通过。",
        in_scope={"control": CONTROL_ID, "host": host_id, "target_ip": action.target_ip,
                  "ports_scanned": sorted(action.ports), "rule_version": RULE_VERSION,
                  "action_hash": action.action_hash},
        not_covered=[
            "真实网络探测（fixture-first；MockBackend 无 subprocess/socket）→ Finding 只裁定 synthetic "
            "target/fixture，**不对 fixture 中地址作现实安全声明**",
            "justified 的完整闭环受限于 justification inventory 是否提供（无则 inconclusive）",
            "真实主机执行 + just-in-time human approval（本切片只验授权机器；approval 留后续）",
            "其它 exposed 面（UDP/IPv6/云 SG）——仅 tcp-connect + 给定端口集",
        ],
        measurement_valid=obs["parse_ok"], underpowered=None, invalidity_reasons=[],
    )
    return AssuranceReport(
        generated_from=generated_from, measurement_context=mctx, evidence_manifest=manifest,
        findings=[finding], comparisons=[], scope=scope,
        control=ctrl, referenced_standards=referenced_standards(CONTROL_ID))


def _measurement_context(ctrl, action: NetworkPortScanAction, roe: RoEAuthorization,
                         receipt, obs: dict[str, Any]) -> dict[str, Any]:
    return {
        "control_id": CONTROL_ID, "domain": ctrl.domain,
        "verification_method": ctrl.verification.method,   # automated_test
        "capability_required": sorted(required_capabilities(CONTROL_ID)),
        "capability_bridge": CAPABILITY_BRIDGE_PROVENANCE,
        "adapter": {"id": NMAP_ADAPTER.adapter_id, "input_format": NMAP_ADAPTER.input_format},
        "rule_version": RULE_VERSION,
        "action": action._policy_fields(), "action_hash": action.action_hash,
        "compiled_argv": action.compile_argv(),            # 固定模板结果，可审计
        "roe_version": roe.roe_version,
        "execution_backend": receipt.backend,              # mock
        "no_real_network_io": not receipt.external_side_effects_performed,   # ⭐ 机器可读 mock 边界
        "execution_receipt": receipt.model_dump(),         # 执行事实（seams #2；非已解释 Evidence）
        "legacy_plugin_opaque": ctrl.verification.plugin,  # nmap_port_scan，不参与匹配（ADR-0008）
        "observation": obs,
    }


def _gap_report(host_id: str, kind: str, reason: str, *, action_hash: str,
                assessed_at: str, generated_from: str) -> AssuranceReport:
    """覆盖缺口（**不产 Finding**）。RoE 拒绝 = out_of_scope（工具有能力、目标未授权），**非** unsupported/
    inconclusive/not_applicable（搭档 review）。无结构化 ScopeGap 模型 → 进 scope.not_covered（FRICTION）。"""
    ctrl = control(CONTROL_ID)
    mctx = {"control_id": CONTROL_ID, "gap_kind": kind, "gap_reason": reason, "action_hash": action_hash}
    scope = ScopeStatement(
        claim=f"CE-UK-FW-01 未评（{kind}: {reason}）→ 覆盖缺口，不产 Finding、不调 backend。",
        in_scope={"control": CONTROL_ID, "host": host_id, "action_hash": action_hash},
        not_covered=[f"{kind}（进覆盖分母）：{host_id} action_hash={action_hash} — {reason}"
                     + ("；工具有能力、仅目标未授权（≠ unsupported）" if kind == "out_of_scope" else "")],
        measurement_valid=False, underpowered=None,
        # ⚠ invalidity_reasons 是 AI 定义的枚举、无 out_of_scope 项 → 留空、不借错义（FRICTION：需结构化 gap 模型）。
        invalidity_reasons=[],
    )
    empty = EvidenceManifest(run_root=content_hash({"gap": action_hash}, prefix="run:"),
                             measurement_context=mctx, artifacts={}, index={"probe": []})
    return AssuranceReport(
        generated_from=generated_from, measurement_context=mctx, evidence_manifest=empty,
        findings=[], comparisons=[], scope=scope,
        control=ctrl, referenced_standards=referenced_standards(CONTROL_ID))
