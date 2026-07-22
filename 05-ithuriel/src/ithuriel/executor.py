"""执行/授权机器（seams #1 executor=PEP + #2 execution-fact，slice 3 / ADR-0013）。

**唯一新变量**：一个结构化主动探测 Action，**只有经过两阶段 PEP + 命令文法白名单 + target-scoped
RoE 授权**才能抵达 mock backend；backend 只返回 **execution facts / raw artifact**，由 Ithuriel 侧
独立解释成 Observation/Finding。**全程零真实网络 I/O**（MockBackend 绝不调 subprocess/socket）。

**授权三分（搭档 review 拍板）**：
  1. RoE authorization —— 目标/动作/范围是否**事先授权**；**每个动作必需**。
  2. just-in-time human approval —— 高风险动作是否还需人工逐次批准；FW-01 **不需要**。
  3. `verification.requires_approval=False`（profile）—— 只免第 2 类，**不免第 1 类**。
slice 3 验证的是**授权机器**；**不为凑 seams#1 给 FW-01 硬造人工审批**（ApprovalGrant 等首个真需
人工审批的动作再由摩擦定形）。Action hash 仍有用：PolicyDecision 绑 hash，pre-dispatch 重算核对。

**命令白名单 = 语义 Action 类型本身**（非白名单二进制/参数在类型层**不可表达**，强于运行时二进制名
检查）+ 运行时 target/ports/profile 策略。executor 用**固定模板**编译 argv、不接受插件传入任意 argv、
**禁 shell**、dispatch 始终收 argv list。
"""
from __future__ import annotations

import ipaddress
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from ithuriel.models import content_hash

# ── 命令文法白名单（动作类型 + 参数文法）─────────────────────────────────────
ALLOWED_SCAN_PROFILES = {"tcp-connect": "-sT"}   # profile → nmap 扫描类型 flag
MAX_PORTS = 64                                    # 端口数上界（防超大扫描）
HARD_DENIED_BINARIES = {"bash", "sh", "zsh", "python", "perl", "ruby", "nc", "ncat"}  # 兜底


class NetworkPortScanAction(BaseModel):
    """语义化 Action（非 binary+argv）：策略相关字段进 hash，展示字段不进。frozen=不可变。

    非白名单行为（`-iL`/`--script`/夹带额外 target/自定义输出路径）**在类型层无法表达** —— argv 由
    `compile_argv` 固定模板生成，插件拿不到 argv 注入点。
    """
    model_config = ConfigDict(frozen=True)

    kind: Literal["network.port_scan"] = "network.port_scan"
    tool: Literal["nmap"] = "nmap"
    target_ip: str                                # 仅 literal IP（不接受 hostname，避开 DNS/rebinding）
    # ⭐ 端口文法在**类型层**约束（partner review 2026-07-22 C4）：此前只有数量上限，
    # 空端口集、0、负数、65536 都会被判 allowed 并编进 `-p ""` / `-p 0` / `-p -1` / `-p 65536`。
    # 承诺是「非白名单行为在类型层不可表达」，端口越界属于该承诺覆盖范围。
    ports: tuple[int, ...]
    scan_profile: Literal["tcp-connect"] = "tcp-connect"
    label: str = ""                               # ⭐ 展示字段：**不进 action_hash**

    @field_validator("ports")
    @classmethod
    def _validate_ports(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if not v:
            raise ValueError("ports_empty：至少一个端口（空集会编出 `-p \"\"`，语义不明）")
        if len(v) > MAX_PORTS:
            raise ValueError(f"too_many_ports：至多 {MAX_PORTS} 个")
        bad = [p for p in v if not isinstance(p, int) or isinstance(p, bool) or not 1 <= p <= 65535]
        if bad:
            raise ValueError(f"port_out_of_range：{bad[:5]} 不在 1..65535")
        # 重复端口**规范化去重**（而非拒绝）：`-p 80,80` 与 `-p 80` 语义相同，
        # 去重后 action_hash 也随之唯一，避免同一动作有多个 hash。
        return tuple(sorted(set(v)))

    def _policy_fields(self) -> dict:
        # 只含策略相关字段（ports 规范排序）→ 展示字段变不改 hash、策略字段变必改 hash。
        return {"kind": self.kind, "tool": self.tool, "target_ip": self.target_ip,
                "ports": sorted(self.ports), "scan_profile": self.scan_profile}

    @property
    def action_hash(self) -> str:
        return content_hash(self._policy_fields(), prefix="act:")

    def compile_argv(self) -> list[str]:
        """固定模板 → argv list（**禁 shell**、无任意 argv 注入）。target 在 `--` 后严格单值。"""
        flag = ALLOWED_SCAN_PROFILES[self.scan_profile]
        ports = ",".join(str(p) for p in sorted(self.ports))
        return ["nmap", flag, "-Pn", "-p", ports, "-oX", "-", "--", self.target_ip]


class RoEAuthorization(BaseModel):
    """交战规则：哪些 target 事先获授权探测。空 allowed_targets = 默认全拒。仅 literal IP/CIDR。"""
    roe_version: str
    allowed_targets: list[str] = []               # IP 或 CIDR 字面量

    def authorizes(self, target_ip: str) -> bool:
        if not self.allowed_targets:
            return False                          # 默认拒绝（allowed_targets=[]）
        try:
            ip = ipaddress.ip_address(target_ip)  # literal only；hostname → ValueError → 不授权
        except ValueError:
            return False
        for t in self.allowed_targets:
            try:
                if ip in ipaddress.ip_network(t, strict=False):
                    return True
            except ValueError:
                continue
        return False


DenyReason = Literal[
    "allowed_targets_empty", "target_not_ip", "target_not_authorized",
    "hard_denied_binary", "scan_profile_not_allowed", "too_many_ports",
    "action_hash_mismatch", "roe_version_changed",
]


class PolicyDecision(BaseModel):
    """preflight 产出，绑 action_hash + roe_version；pre-dispatch 重算核对（不信 preflight_passed）。"""
    action_hash: str
    roe_version: str
    allowed: bool
    reason: str


def _policy_check(action: NetworkPortScanAction, roe: RoEAuthorization) -> tuple[bool, str]:
    """纯策略判定（preflight 与 pre-dispatch **各自独立调用**）。"""
    if action.tool in HARD_DENIED_BINARIES:
        return False, "hard_denied_binary"
    if action.scan_profile not in ALLOWED_SCAN_PROFILES:
        return False, "scan_profile_not_allowed"
    # ⭐ pre-dispatch 与 preflight **各自独立**重跑端口文法，不依赖模型层已挡住
    #（模型可能被 model_construct 绕过校验，或将来放宽）。
    if not action.ports:
        return False, "ports_empty"
    if len(action.ports) > MAX_PORTS:
        return False, "too_many_ports"
    if any(not 1 <= p <= 65535 for p in action.ports):
        return False, "port_out_of_range"
    if not roe.allowed_targets:
        return False, "allowed_targets_empty"
    try:
        ipaddress.ip_address(action.target_ip)
    except ValueError:
        return False, "target_not_ip"
    if not roe.authorizes(action.target_ip):
        return False, "target_not_authorized"
    return True, "ok"


def preflight(action: NetworkPortScanAction, roe: RoEAuthorization) -> PolicyDecision:
    ok, reason = _policy_check(action, roe)
    return PolicyDecision(action_hash=action.action_hash, roe_version=roe.roe_version,
                          allowed=ok, reason=reason)


def pre_dispatch(action: NetworkPortScanAction, roe: RoEAuthorization,
                 decision: PolicyDecision) -> tuple[bool, str]:
    """执行前再判——**不信 preflight**：重算 hash + 核对 roe_version + 独立重跑策略。"""
    if action.action_hash != decision.action_hash:
        return False, "action_hash_mismatch"       # 计划后 target/ports 被改
    if roe.roe_version != decision.roe_version:
        return False, "roe_version_changed"         # 两阶段之间 RoE 变了
    return _policy_check(action, roe)               # 独立重跑（非只信 decision.allowed）


# ── execution-fact（seams #2）：backend 产事实、不产 Evidence ────────────────
class RawArtifactRef(BaseModel):
    artifact_hash: str
    kind: str                                       # "nmap-xml/v1"
    fixture_ref: str                                # "fixture:nmap-..."


class ExecutionReceipt(BaseModel):
    """执行**事实**（seams #2）：哪个 Action、哪个 backend、是否 dispatch、返回码、raw 在哪、有无副作用。

    **不携带 Finding/status**、不声称端口是否违规/控制是否通过/fixture 是否代表现实。Evidence 由
    Ithuriel 侧解释、可引用本 receipt，但 receipt 本身不是已解释的 Evidence。
    """
    action_hash: str
    backend: Literal["mock"] = "mock"
    dispatch_performed: bool
    external_side_effects_performed: bool = False   # ⭐ mock 边界机器可读：无真实网络 I/O
    fixture_ref: str
    exit_code: int
    raw_artifact_ref: RawArtifactRef


class MockBackend:
    """返回 execution facts + raw artifact 引用。**绝不调用 subprocess/socket**（无真实 egress）。"""

    def dispatch(self, action: NetworkPortScanAction, fixture_text: str,
                 fixture_ref: str) -> ExecutionReceipt:
        raw_hash = content_hash({"raw": fixture_text, "argv": action.compile_argv()}, prefix="raw:")
        return ExecutionReceipt(
            action_hash=action.action_hash, backend="mock", dispatch_performed=True,
            external_side_effects_performed=False, fixture_ref=fixture_ref, exit_code=0,
            raw_artifact_ref=RawArtifactRef(artifact_hash=raw_hash, kind="nmap-xml/v1",
                                            fixture_ref=fixture_ref))


class ExecutionDenied(Exception):
    """两阶段 PEP 任一阶段拒绝 → 抛出、**不调用 backend**（RoE 拒绝不产假结果）。"""
    def __init__(self, reason: str, phase: str):
        self.reason = reason
        self.phase = phase
        super().__init__(f"{phase}: {reason}")


def execute(action: NetworkPortScanAction, roe: RoEAuthorization, *,
            fixture_text: str, fixture_ref: str,
            backend: Optional[MockBackend] = None) -> ExecutionReceipt:
    """两阶段 PEP → mock dispatch。任一阶段拒绝 → ExecutionDenied（不 dispatch、无 receipt）。"""
    backend = backend or MockBackend()
    decision = preflight(action, roe)
    if not decision.allowed:
        raise ExecutionDenied(decision.reason, phase="preflight")
    ok, reason = pre_dispatch(action, roe, decision)
    if not ok:
        raise ExecutionDenied(reason, phase="pre_dispatch")
    return backend.dispatch(action, fixture_text, fixture_ref)
