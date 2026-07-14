"""内部试用报告 view（试用里程碑 Step 1，ADR-0017 pending）= 让现有 Claim/Ledger 第一次被真实消费。

`render_report(reports) -> Report`：把一批 `AssuranceReport`（AI 会话拆开 + 确定性切片）投影成一份
**有边界的内部报告**，回答操作者/评估者三问——**能说什么 / 凭什么 / 不能说什么**。

**纯函数、只投影不重算**：复用 `derive_claims`（凭什么）+ `build_ledger`（能说什么的 rollup），把散在
Finding / Claim / ComparisonSpec / ScopeStatement 里的字段重新打包成人可读的视图。**不改任何裁定**。

**G2 硬纪律**：呈现为 coverage × (warrant, fidelity) 二维，**刻意不产任何单一总分/置信度档**——把覆盖率、
证据质量、目标保真度压成一个数字会重造「绿灯但没真测」。故 `Report`/`MatrixRow` 无 overall_score 字段。

**选项 A（ADR-0017，security⊗utility 呈现）**：矩阵 coverage 是 **security 轴**覆盖（取 defended 单臂
`Finding.status`，不重算 ledger）；被算作 passed 但 `joint_verdict` 并非 acceptable 的控制记进
`MatrixRow.joint_caveats`，让 security 覆盖数永远读不成「系统安全」。**报告不把 utility_failed 降级成
不通过**（那是替部署方拍价值判断），也**不把它藏进下钻**（那是默许过度声称），而是照实报 security 覆盖 +
常驻警示。哲学依据见 `docs/DESIGN.md`「附：检测到注入就中止任务算不算安全」。

**本层是 presentation DTO、非 ontology schema 扩展**：这些视图模型只重排既有字段（如 ledger.py 的
AxisCoverage），不给 Finding/Claim 加语义字段——守「先撞摩擦、不提前加字段」（试用里程碑 Step 1）。
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Optional

from pydantic import BaseModel, Field

from ithuriel.claim import derive_claims
from ithuriel.ledger import build_ledger, control_outcome
from ithuriel.models import AiRunRecord, AssuranceReport, Claim, Finding


def _stat_backing(rr: Optional[AiRunRecord]) -> Optional[str]:
    """AI 探针的统计支撑压成一行；确定性检查 run_record=None → 无统计支撑（如实 None）。"""
    if rr is None:
        return None
    ci = f", CI95={list(rr.asr_ci95)}" if rr.asr_ci95 else ""
    valid = f", n_valid={rr.n_valid}" if rr.n_valid is not None else ""
    return f"success_rate={rr.success_rate}{valid}, n_runs={rr.n_runs}{ci}"


class WarrantView(BaseModel):
    """『凭什么』的单 Finding 切片：confidence_basis 全维摊开 + 统计支撑，绝不折成一个档。"""
    finding_status: str                       # 被主张的裁定（是什么），与凭据正交
    adjudication: str                         # automatic_rule / human_attestation
    uncertainty: str                          # statistical_ci / deterministic / unquantified
    reproducibility: str                      # bit / protocol / declarative
    target_fidelity: str                      # mock / frozen_fixture / …（派生自 execution_backend）
    statistical_backing: Optional[str] = None  # AI: success_rate/CI；确定性: None
    limitations: list[str] = Field(default_factory=list)


class ControlView(BaseModel):
    """一个控制在报告里的三问切片。"""
    control_id: str
    title: Optional[str] = None
    domain: Optional[str] = None
    # ── 能说什么 ──
    outcome: str                              # rollup status（pass/fail/inconclusive/not_applicable/gap）
    severity: Optional[str] = None
    # FRICTION 2（grounding 预标）：security 轴单臂 status 与 security⊗utility 联合裁定并列呈现——
    # ledger 取 defended Finding.status，但 joint_verdict 可能 utility_failed；报告不替读者取舍，两个都摊。
    security_statuses: list[str] = Field(default_factory=list)  # 各 Finding.status（bare/defended）
    joint_verdict: Optional[str] = None       # ComparisonSpec.joint_verdict（有防御实验时）
    standards: list[str] = Field(default_factory=list)  # 审计闭环：control_id→standards_refs→registry
    # ── 凭什么 ──
    warrants: list[WarrantView] = Field(default_factory=list)
    # ── 不能说什么 ──
    unassessable_reasons: list[str] = Field(default_factory=list)  # Claim.assessable=False（fail-closed）
    fail_closed_reasons: list[str] = Field(default_factory=list)   # ComparisonSpec ¬assertable 的子因
    not_covered: list[str] = Field(default_factory=list)           # ScopeStatement.not_covered


class MatrixRow(BaseModel):
    """coverage × (warrant, fidelity) 二维矩阵一行（per domain 轴）。

    coverage/not_ready 直接来自 CoverageLedger.axes；fidelity/reproducibility 分布是把每个控制的
    confidence_basis 归并到轴上——**这一归并今天没有任何对象承载**（见 FRICTION 1）。
    单位对齐到「控制」：每份 report 贡献一个计数，与 coverage 分母同口径。
    """
    domain: str
    applicable: int                           # 分母（not_applicable 出分母）
    passed: int
    # ⭐ 选项 A（ADR-0017）：coverage 是 **security 轴** 覆盖，取 defended 单臂 Finding.status（不重算
    # ledger，守「只投影不重算」）。渲染层显式标「security 轴覆盖」，永远与下面的分布 + joint_caveats 并读。
    coverage: float                           # passed / applicable —— 单看会误导，见 joint_caveats
    not_ready: bool                           # 任一 High/Critical fail 否决本轴
    gating_reason: Optional[str] = None
    fidelity_mix: dict[str, int] = Field(default_factory=dict)         # {mock: n, frozen_fixture: m}
    reproducibility_mix: dict[str, int] = Field(default_factory=dict)  # {protocol: n, bit: m, declarative: k}
    unassessable: int = 0                     # 该轴内缺 provenance、无凭据的控制数
    # ⭐ 选项 A 的核心：被算作 passed、但 joint_verdict 并非 acceptable 的控制计数（{joint_verdict: n}）。
    # 例：一个防御「检到注入即 abort」→ security-pass 但 joint=utility_failed → 这里记 {utility_failed:1}，
    # 让 security 轴覆盖数永远读不成「系统安全」。哲学依据见 DESIGN「附：检测到注入就中止任务算不算安全」。
    joint_caveats: dict[str, int] = Field(default_factory=dict)


class Report(BaseModel):
    """内部试用报告：coverage×warrant/fidelity 矩阵 + per-control 三问视图。

    ⭐ G2：**刻意无 overall_score / 单一置信度字段**——矩阵不折成标量，fidelity 始终显式在场，
    读者不可能拿工程成熟度冒充环境真实性（见试用里程碑两轴正交论证）。
    """
    generated_from: list[str] = Field(default_factory=list)
    matrix: list[MatrixRow] = Field(default_factory=list)
    controls: list[ControlView] = Field(default_factory=list)


def _control_view(report: AssuranceReport) -> ControlView:
    ctrl = report.control
    claims = derive_claims(report)            # 与 report.findings 同序（每 Finding 一条）
    warrants: list[str] = []
    warrant_views: list[WarrantView] = []
    unassessable: list[str] = []
    # zip 对齐 claim↔finding（derive_claims 按 findings 顺序产出）：statistical_backing 需读 run_record。
    for claim, finding in zip(claims, report.findings):
        if claim.assessable and claim.confidence_basis is not None:
            cb = claim.confidence_basis
            warrant_views.append(WarrantView(
                finding_status=claim.finding_status,
                adjudication=cb.adjudication, uncertainty=cb.uncertainty,
                reproducibility=cb.reproducibility, target_fidelity=cb.target_fidelity,
                statistical_backing=_stat_backing(finding.run_record),
                limitations=cb.limitations))
        else:
            unassessable.append(claim.unassessable_reason or "unassessable（原因未记）")

    fail_closed: list[str] = []
    joint: Optional[str] = None
    for cmp in report.comparisons:
        joint = cmp.joint_verdict             # 单防御实验；多个时取最后（首版无多比较场景）
        if not cmp.assertable:
            fail_closed.extend(cmp.invalidity_reasons)

    return ControlView(
        control_id=(ctrl.id if ctrl else report.measurement_context.get("control_id", "UNKNOWN")),
        title=(ctrl.title if ctrl else None),
        domain=(ctrl.domain if ctrl else report.measurement_context.get("domain")),
        outcome=control_outcome(report).status,
        severity=(ctrl.severity_if_failed if ctrl else None),
        security_statuses=[f.status for f in report.findings],
        joint_verdict=joint,
        standards=[e.name for e in report.referenced_standards.values()],
        warrants=warrant_views,
        unassessable_reasons=unassessable,
        fail_closed_reasons=sorted(set(fail_closed)),
        not_covered=list(report.scope.not_covered),
    )


def _matrix(reports: list[AssuranceReport]) -> list[MatrixRow]:
    ledger = build_ledger(reports)
    # ── FRICTION 1（grounding 预标，Step 1 现形）──────────────────────────────
    # G2 要 coverage × fidelity 二维，但 CoverageLedger.axes 只带 coverage/not_ready，fidelity 埋在每条
    # Claim.confidence_basis 里。**没有任何对象把二者配对**——故此处重走 reports、按 domain 归并 Claim 的
    # fidelity/reproducibility 再挂回 ledger 轴。这是真实组装摩擦（Claim×Ledger 组合），本层靠 view 内
    # join 化解、不改 schema；是否值得升成对象留 ADR-0017 记录。
    fidelity_by_domain: dict[str, Counter] = defaultdict(Counter)
    repro_by_domain: dict[str, Counter] = defaultdict(Counter)
    unassessable_by_domain: dict[str, int] = defaultdict(int)
    caveat_by_domain: dict[str, Counter] = defaultdict(Counter)   # 选项 A：passed 但 joint≠acceptable
    for r in reports:
        domain = (r.control.domain if r.control else r.measurement_context.get("domain")) or "unknown"
        assessable = [c for c in derive_claims(r) if c.assessable and c.confidence_basis is not None]
        if assessable:
            # report 级保真度单值（同一 mctx.execution_backend）→ 取一条即可、单位=控制。
            cb = assessable[0].confidence_basis
            fidelity_by_domain[domain][cb.target_fidelity] += 1
            repro_by_domain[domain][cb.reproducibility] += 1
        else:
            unassessable_by_domain[domain] += 1
        # 选项 A：本控制被算作 passed（defended 单臂 security-pass），但联合裁定不是 acceptable → 记警示。
        # 只对 passed 控制记（未 pass 的控制其 outcome 已如实反映问题，无需再警示覆盖数）。
        if control_outcome(r).status == "pass":
            for cmp in r.comparisons:
                jv = cmp.joint_verdict
                if jv and jv != "acceptable":
                    caveat_by_domain[domain][jv] += 1

    rows: list[MatrixRow] = []
    for ax in ledger.axes:                    # ax.axis == "domain"
        rows.append(MatrixRow(
            domain=ax.key, applicable=ax.applicable, passed=ax.passed,
            coverage=ax.coverage, not_ready=ax.not_ready, gating_reason=ax.gating_reason,
            fidelity_mix=dict(fidelity_by_domain[ax.key]),
            reproducibility_mix=dict(repro_by_domain[ax.key]),
            unassessable=unassessable_by_domain[ax.key],
            joint_caveats=dict(caveat_by_domain[ax.key])))
    return rows


def render_report(reports: list[AssuranceReport],
                  generated_from: Optional[list[str]] = None) -> Report:
    """一批 AssuranceReport → 内部试用报告（纯函数）。

    输入可混合：AI 会话（`SessionReport.runs` 拆开）+ 确定性切片的单份 report。空输入 → 空报告
    （无控制、无矩阵；不静默产正向结论）。
    """
    return Report(
        generated_from=(generated_from or [r.generated_from for r in reports]),
        matrix=_matrix(reports),
        controls=[_control_view(r) for r in reports])


# ── 渲染器（Step 2）：只格式化 Report、不重算任何裁定 ─────────────────────────
# to_json：机器可读；to_markdown：人可读。二者同源（同一个 Report），渲染层唯一「加工」是
# 把 coverage 标注成「安全轴覆盖」并常驻 ⚠ 联合裁定警示（选项 A 的呈现落点，见 render_report 文档串）。

def _mix(d: dict[str, int]) -> str:
    return "、".join(f"{k}×{v}" for k, v in d.items()) if d else "—"


def to_json(report: Report, *, indent: int = 2) -> str:
    """Report → JSON 字符串（机器可读；字段即 Report 结构，无额外加工）。"""
    return report.model_dump_json(indent=indent)


def to_markdown(report: Report) -> str:
    """Report → 人可读 Markdown。**不产单一总分**（G2）；coverage 标「安全轴覆盖」+ ⚠ caveat（选项 A）。"""
    lines: list[str] = []
    lines.append("# 内部试用保证报告")
    lines.append("")
    lines.append("> 面向内部操作者与评估者。本报告**不产单一安全总分**：覆盖率、证据质量、"
                 "目标保真度是三件不同的事，压成一个数字会把 fixture 上的可复现误读成对真实目标的高信心。"
                 "所有结论 `assurance_level=none`，只对所测的 fixture 或 target variant 成立，非合规认证。")
    lines.append("")

    # ── 覆盖矩阵（安全轴覆盖 × 凭据/保真度）──
    lines.append("## 覆盖矩阵（安全轴覆盖 × 凭据 / 保真度）")
    lines.append("")
    lines.append("| 域 | 安全轴覆盖 | ⚠ 联合裁定 | 目标保真度 | 可复现 | 不可评估 | 门禁 |")
    lines.append("|----|-----------|-----------|-----------|--------|---------|------|")
    any_caveat = False
    for m in report.matrix:
        gating = f"⛔ {m.gating_reason}" if m.not_ready else "—"
        caveat = _mix(m.joint_caveats)
        if m.joint_caveats:
            any_caveat = True
        lines.append(f"| {m.domain} | {m.passed}/{m.applicable} = {m.coverage} | {caveat} "
                     f"| {_mix(m.fidelity_mix)} | {_mix(m.reproducibility_mix)} | {m.unassessable} | {gating} |")
    lines.append("")
    lines.append("> 「安全轴覆盖」只算 security 轴（defended 单臂裁定），**不可单独读作「系统安全」**。")
    if any_caveat:
        lines.append("> ⚠ 「联合裁定」列非空 = 该域有控制在 security 轴判 pass，但 security 与 utility 的"
                     "联合裁定并非 `acceptable`（典型：防御靠中止任务挡住注入，换来 `utility_failed`）。"
                     "「这算不算安全」是部署方的风险判断，本报告只如实并陈、不替你拍板。")
    lines.append("")

    # ── 控制详情（三问）──
    lines.append("## 控制详情")
    lines.append("")
    for c in report.controls:
        title = f" {c.title}" if c.title else ""
        lines.append(f"### [{c.control_id}]{title} — {c.domain or 'unknown'}")
        lines.append("")
        # 能说什么
        head = [f"结论 **{c.outcome}**"]
        if c.severity:
            head.append(f"severity {c.severity}")
        if c.joint_verdict:
            head.append(f"联合裁定 **{c.joint_verdict}**")
        lines.append(f"**能说什么**：{' ｜ '.join(head)}")
        if c.security_statuses:
            lines.append(f"- 各臂 security 裁定：{', '.join(c.security_statuses)}")
        if c.standards:
            lines.append(f"- 引用标准：{'；'.join(c.standards)}")
        lines.append("")
        # 凭什么
        lines.append("**凭什么**：")
        if c.warrants:
            for w in c.warrants:
                lines.append(f"- `[{w.finding_status}]` 裁定机制 {w.adjudication} ｜ 不确定性 {w.uncertainty} "
                             f"｜ 可复现 {w.reproducibility} ｜ 目标保真度 {w.target_fidelity}")
                if w.statistical_backing:
                    lines.append(f"  - 统计支撑：{w.statistical_backing}")
                for lim in w.limitations:
                    lines.append(f"  - 局限：{lim}")
        else:
            lines.append("- （无 Finding-backed 凭据）")
        lines.append("")
        # 不能说什么
        lines.append("**不能说什么**：")
        said_nothing = True
        if c.joint_verdict and c.joint_verdict != "acceptable":
            lines.append(f"- 联合裁定 {c.joint_verdict}：security 达标不代表系统整体安全，"
                         "可用性与部署可接受性未在此裁定。")
            said_nothing = False
        for r in c.unassessable_reasons:
            lines.append(f"- 不可评估：{r}")
            said_nothing = False
        for r in c.fail_closed_reasons:
            lines.append(f"- fail-closed（拒断言 delta）：{r}")
            said_nothing = False
        for nc in c.not_covered:
            lines.append(f"- 覆盖缺口：{nc}")
            said_nothing = False
        if said_nothing:
            lines.append("- （本控制无额外边界声明）")
        lines.append("")

    return "\n".join(lines)
