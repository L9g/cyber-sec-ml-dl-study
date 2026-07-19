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

from ithuriel.manifest import AssessmentManifest
from ithuriel.models import AssuranceReport
from ithuriel.registry import control

# rollup status：Finding 四态 + **gap**（rollup-only：0-Finding 覆盖缺口，进分母、非 pass）
# + **not_assessed**（ADR-0019：manifest 声明了却整条无 report，进分母、非 pass；与 gap 区分——
#   gap 是「report 在、0 Finding」，not_assessed 是「连 report 都没有」）。
RollupStatus = Literal["pass", "fail", "inconclusive", "not_applicable", "gap", "not_assessed"]
GATING_SEVERITIES = {"High", "Critical"}      # ontology scoring.gating


class ControlOutcome(BaseModel):
    """一个控制在一份 report 里归约出的 rollup 结果（多 Finding→defended、0 Finding→gap）。"""
    control_id: str
    domain: Optional[str] = None
    ce_area: Optional[str] = None             # Cyber Essentials area（ADR-0021）；None=无映射（如 AI 控制）
    severity: Optional[str] = None            # control.severity_if_failed（gating 用）
    status: RollupStatus
    gap_kind: Optional[str] = None            # status==gap 时的子类（out_of_scope/unsupported/…）


class AxisCoverage(BaseModel):
    """某 rollup 轴（domain / ce_area）某 key 的 graded coverage + gating。"""
    axis: str                                 # "domain" | "ce_area"（ADR-0021）
    key: str                                  # domain 如 "network_security"；ce_area 如 "firewalls"
    applicable: int                           # 分母（排除 not_applicable；含 not_assessed）
    passed: int
    coverage: float                           # passed / applicable（scoring.coverage）
    not_ready: bool                           # 任一 High/Critical fail（scoring.gating）
    gating_reason: Optional[str] = None       # 触发 not_ready 的控制
    # ADR-0019：本轴内被 manifest 声明、却整条无 report 的控制 id（进分母算未 pass，如实点名）。
    # 无 manifest → 空（分母=仅已评估，覆盖率此时可被输入选择做高，呈现层须如实标此局限）。
    not_assessed_controls: list[str] = Field(default_factory=list)


class CoverageLedger(BaseModel):
    """跨控制覆盖信封：per-control outcomes + per-axis graded coverage。"""
    outcomes: list[ControlOutcome]
    axes: list[AxisCoverage]
    generated_from: list[str] = Field(default_factory=list)
    # ADR-0021（R1）：某轴下无映射键的控制 id（当前只 ce_area：AI 控制无 ce_area）。**刻意不塞进带
    # coverage 分数的轴 key**（否则读成「一个覆盖率为 X 的 area」），改由此单列、呈现层显式点名不静默丢。
    unmapped: dict[str, list[str]] = Field(default_factory=dict)


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
    ce_area = ctrl.ce_area if ctrl else None
    severity = ctrl.severity_if_failed if ctrl else None

    if not report.findings:
        # 0 Finding = 覆盖缺口（进分母、非 pass）。gap 子类来自 scope/mctx。
        gap_kind = (report.measurement_context.get("gap_kind")
                    or (report.scope.invalidity_reasons[0] if report.scope.invalidity_reasons else "gap"))
        return ControlOutcome(control_id=control_id, domain=domain, ce_area=ce_area, severity=severity,
                              status="gap", gap_kind=gap_kind)
    finding = report.findings[0] if len(report.findings) == 1 else _defended_finding(report)
    return ControlOutcome(control_id=control_id, domain=domain, ce_area=ce_area, severity=severity,
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
            gating_reason=(f"{gate.control_id} fail (severity {gate.severity})" if gate else None),
            not_assessed_controls=sorted(o.control_id for o in outs if o.status == "not_assessed")))
    return axes


def _not_assessed_outcomes(manifest: AssessmentManifest,
                           reported_ids: set[str]) -> list[ControlOutcome]:
    """声明了却整条无 report 的控制 → not_assessed outcome（domain/severity 从 registry 解析）。

    声明控制必须在 registry 注册（非悬空声明）；未注册 → fail-closed 报错，不静默吞。
    """
    outs: list[ControlOutcome] = []
    for cid in sorted(manifest.control_ids() - reported_ids):
        try:
            ctrl = control(cid)
        except KeyError as exc:
            raise ValueError(
                f"manifest 声明控制 '{cid}' 未在 registry 注册（悬空声明，违反 registry 不变量）") from exc
        outs.append(ControlOutcome(control_id=cid, domain=ctrl.domain, ce_area=ctrl.ce_area,
                                   severity=ctrl.severity_if_failed,
                                   status="not_assessed", gap_kind="declared_not_assessed"))
    return outs


def build_ledger(reports: list[AssuranceReport],
                 manifest: Optional[AssessmentManifest] = None,
                 generated_from: Optional[list[str]] = None) -> CoverageLedger:
    """N 份 AssuranceReport → CoverageLedger（按 domain 轴 + Cyber Essentials area 轴 rollup）。

    `manifest` 在时（ADR-0019）：分母由声明控制集播种——声明了却无 report 的控制补成 not_assessed
    outcome（进分母、非 pass），覆盖率不再能靠少传 report 做高。无 manifest 则沿旧行为（分母=仅已评估，
    呈现层须如实标「可被输入选择做高」局限）。

    **ce_area 轴（ADR-0021）**：`ce_area` 是控制的 profile 一等字段（非从 standards_refs 解析）。无 ce_area
    的控制（如 AI 控制）**不进任何 CE-area 覆盖行**，改归 `unmapped["ce_area"]` 单列（R1：别把无映射伪装
    成一个带分数的 area）。同一控制的 outcome 同时计入其 domain 行与 ce_area 行（同轴各算分母，互不影响）。
    `csf2_function` 轴（多归属列表）仍延后——等真实 NIST CSF 消费者与「完整重复计入/分数分摊/primary
    mapping」计数决策逼出再实现（见 ADR-0021）。
    """
    outcomes = [control_outcome(r) for r in reports]
    if manifest is not None:
        outcomes = outcomes + _not_assessed_outcomes(manifest, {o.control_id for o in outcomes})
    by_domain: dict[str, list[ControlOutcome]] = defaultdict(list)
    by_ce_area: dict[str, list[ControlOutcome]] = defaultdict(list)
    unmapped_ce_area: list[str] = []
    for o in outcomes:
        by_domain[o.domain or "unknown"].append(o)
        if o.ce_area:
            by_ce_area[o.ce_area].append(o)
        else:
            unmapped_ce_area.append(o.control_id)   # R1：无 CE-area 归属 → 单列、不进覆盖行
    axes = _rollup_axis("domain", by_domain) + _rollup_axis("ce_area", by_ce_area)
    unmapped = {"ce_area": sorted(unmapped_ce_area)} if unmapped_ce_area else {}
    return CoverageLedger(outcomes=outcomes, axes=axes,
                          generated_from=generated_from or [], unmapped=unmapped)
