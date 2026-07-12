"""能力匹配（seams #3 首实例，slice 2 / ADR-0012）：control 声明 capability requirement、
adapter 声明 provides，匹配 = 集合包含。**不是 planner**——一控制、一 requirement、一 adapter、
一次子集判定；无候选排序 / 参数规划 / 插件注册中心。

**关键边界（搭档 review 拍板）**：profile 的 `verification.plugin`（如 `firewall_default_deny_check`）
是**工具/实现身份**，继续作**不透明 legacy metadata**（ADR-0008）、**不参与**匹配——capability 描述
"控制需要什么能力"，复用 plugin 身份会违反 seams #3「control 不直接绑工具」。

映射本身标 **provisional / code-local**：不改冻结 profile。迁入 profile 的条件 = 第二个控制或
第二个 adapter 证明该 capability 语义可复用（否则一控制一能力 = YAGNI，别提前建 profile 字段）。
"""
from __future__ import annotations

from pydantic import BaseModel

# ── code-local provisional bridge ───────────────────────────────────────────
# control_id → 所需 capability 集合。**provisional、code-local**（不改 profile）。
CONTROL_CAPABILITY_REQUIREMENTS: dict[str, set[str]] = {
    "CE-UK-FW-03": {"host.firewall.default_policy.inspect"},
    "CE-UK-FW-01": {"host.network.port_scan"},          # slice 3（ADR-0013）
    "CE-UK-SU-03": {"governance.change_register.review"},  # slice 4（ADR-0015，human_review）
}
# 该 bridge 每条映射的溯源（如实披露进报告；标 provisional + 迁移条件）。
CAPABILITY_BRIDGE_PROVENANCE = {
    "source": "slice-2 code-local bridge",
    "status": "provisional",
    "promote_to_profile_when": "第二个控制或第二个 adapter 证明该 capability 语义可复用",
}


class AdapterDescriptor(BaseModel):
    """薄适配器的能力声明（最小字段——据真实摩擦增，不提前设计）。"""
    adapter_id: str
    provides: set[str]
    input_format: str            # 如 "ufw-status-verbose/v1"


def required_capabilities(control_id: str) -> set[str]:
    return set(CONTROL_CAPABILITY_REQUIREMENTS.get(control_id, set()))


def adapter_satisfies(control_id: str, adapter: AdapterDescriptor) -> bool:
    """seams #3 匹配：control 的 requirements ⊆ adapter.provides。缺映射 → 空集 ⊆ 任何 = True，
    但调用方应先确认控制**有**声明需求（空需求不代表"可测"）。"""
    reqs = required_capabilities(control_id)
    return bool(reqs) and reqs <= adapter.provides
