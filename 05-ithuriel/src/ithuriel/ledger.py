"""CoverageLedger（桶 B 最薄切片，ADR-0014）——跨控制 rollup + graded coverage/gating。

由**三条切片三控制**（PI-01 AI / FW-03 config / FW-01 probe）的真实摩擦挣来（搭档路线：多控制覆盖
出现再抽）。**实现 `ontology_schema.yaml` 冻结的 scoring 规则、不改 schema**：
  - coverage = 每轴「status==pass 的**适用**控制」占比（`scoring.coverage`）；
  - gating   = 任一 **High/Critical** fail → 该轴 `not_ready`（单个 fail 不清零轴，只降覆盖率）；
  - denominator = **适用**控制：`not_applicable` 排除；unsupported/out_of_scope/inconclusive/gap **进分母**算未 pass。

**只聚合、不重算裁定**（承载各 AssuranceReport 的 status）。ExperimentManager / Claim-Assurance
Engine / primary root-cause rollup / PlanCompiler 仍延后（桶 B、需更多摩擦）。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ithuriel.models import AssuranceReport

# rollup status：Finding 四态 + **gap**（rollup-only：0-Finding 覆盖缺口，进分母、非 pass）。
RollupStatus = Literal["pass", "fail", "inconclusive", "not_applicable", "gap"]
GATING_SEVERITIES = {"High", "Critical"}      # ontology scoring.gating


class ControlOutcome(BaseModel):
    """一个控制在一份 report 里归约出的 rollup 结果（多 Finding→defended、0 Finding→gap）。"""
    control_id: str
    domain: Optional[str] = None
    severity: Optional[str] = None            # control.severity_if_failed（gating 用）
    status: RollupStatus
    gap_kind: Optional[str] = None            # status==gap 时的子类（out_of_scope/unsupported/…）


class AxisCoverage(BaseModel):
    """某 rollup 轴（当前 domain）某 key 的 graded coverage + gating。"""
    axis: str                                 # "domain"
    key: str                                  # 如 "network_security"
    applicable: int                           # 分母（排除 not_applicable）
    passed: int
    coverage: float                           # passed / applicable（scoring.coverage）
    not_ready: bool                           # 任一 High/Critical fail（scoring.gating）
    gating_reason: Optional[str] = None       # 触发 not_ready 的控制


class CoverageLedger(BaseModel):
    """跨控制覆盖信封：per-control outcomes + per-axis graded coverage。"""
    outcomes: list[ControlOutcome]
    axes: list[AxisCoverage]
    generated_from: list[str] = Field(default_factory=list)


def _defended_finding(report: AssuranceReport):
    """多 Finding（bare/defended）→ 取 defended（**被保证的部署配置**）。

    FRICTION（ADR-0014）：rollup 取 defended Finding.status（security 轴）。defended 可能 security-pass
    而 ComparisonSpec.joint_verdict=utility_failed —— coverage 是否该看 joint_verdict 而非单臂 status，
    是真实摩擦；本切片先用 Finding.status，记录待第 4 个消费场景逼定。
    """
    defended = [f for f in report.findings if f.target_ref.get("defense") not in (None, "none")]
    return defended[0] if defended else report.findings[-1]


def control_outcome(report: AssuranceReport) -> ControlOutcome:
    """一份 AssuranceReport → 一个控制的 rollup 结果。**不重算**，读 report 已有裁定。"""
    ctrl = report.control
    control_id = ctrl.id if ctrl else report.measurement_context.get("control_id", "UNKNOWN")
    domain = ctrl.domain if ctrl else None
    severity = ctrl.severity_if_failed if ctrl else None

    if not report.findings:
        # 0 Finding = 覆盖缺口（进分母、非 pass）。gap 子类来自 scope/mctx。
        gap_kind = (report.measurement_context.get("gap_kind")
                    or (report.scope.invalidity_reasons[0] if report.scope.invalidity_reasons else "gap"))
        return ControlOutcome(control_id=control_id, domain=domain, severity=severity,
                              status="gap", gap_kind=gap_kind)
    finding = report.findings[0] if len(report.findings) == 1 else _defended_finding(report)
    return ControlOutcome(control_id=control_id, domain=domain, severity=severity,
                          status=finding.status)


def _rollup_axis(axis: str, keyed: dict[str, list[ControlOutcome]]) -> list[AxisCoverage]:
    axes: list[AxisCoverage] = []
    for key, outs in sorted(keyed.items()):
        applicable = [o for o in outs if o.status != "not_applicable"]   # not_applicable 出分母
        n = len(applicable)
        passed = sum(1 for o in applicable if o.status == "pass")
        gate = next((o for o in applicable
                     if o.status == "fail" and o.severity in GATING_SEVERITIES), None)
        axes.append(AxisCoverage(
            axis=axis, key=key, applicable=n, passed=passed,
            coverage=round(passed / n, 3) if n else 0.0,
            not_ready=gate is not None,
            gating_reason=(f"{gate.control_id} fail (severity {gate.severity})" if gate else None)))
    return axes


def build_ledger(reports: list[AssuranceReport],
                 generated_from: Optional[list[str]] = None) -> CoverageLedger:
    """N 份 AssuranceReport → CoverageLedger（当前按 domain 轴 rollup）。

    ce_area / csf2_function 两轴（schema 列出）需从 standards_refs 解析（cyber_essentials→ce_area、
    nist_csf→csf2_function）→ derivable-deferred（本切片只做 domain 轴，够验 rollup+gating）。
    """
    outcomes = [control_outcome(r) for r in reports]
    by_domain: dict[str, list[ControlOutcome]] = defaultdict(list)
    for o in outcomes:
        by_domain[o.domain or "unknown"].append(o)
    return CoverageLedger(outcomes=outcomes, axes=_rollup_axis("domain", by_domain),
                          generated_from=generated_from or [])
