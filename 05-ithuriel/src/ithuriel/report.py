"""内部试用报告 view（试用里程碑 Step 1–2，ADR-0017 accepted）= 让现有 Claim/Ledger 第一次被真实消费。

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
from ithuriel.ledger import CoverageLedger, build_ledger, control_outcome
from ithuriel.manifest import AssessmentManifest
from ithuriel.models import AiRunRecord, AssuranceReport, Claim, Finding


def _stat_backing(rr: Optional[AiRunRecord]) -> Optional[str]:
    """AI 探针的统计支撑压成一行；确定性检查 run_record=None → 无统计支撑（如实 None）。"""
    if rr is None:
        return None
    ci = f", CI95={list(rr.asr_ci95)}" if rr.asr_ci95 else ""
    valid = f", n_valid={rr.n_valid}" if rr.n_valid is not None else ""
    return f"success_rate={rr.success_rate}{valid}, n_runs={rr.n_runs}{ci}"


# ③：从一组 target_ref 提炼供人读的目标标识（host_id / model / defense 变体），令跨主机的同名 control 可区分。
_TARGET_ID_KEYS = ("host_id", "model_id", "model", "target_variant_hash", "variant_hash")


def _target_label(targets: list[dict[str, Any]]) -> str:
    """把各臂 target_ref 压成一个稳定人读标识：优先 host_id/model，退到 variant hash。空→unknown。"""
    for key in _TARGET_ID_KEYS:
        vals = [str(t[key]) for t in targets if t.get(key)]
        if vals:
            uniq = sorted(set(vals))
            return uniq[0] if len(uniq) == 1 else "、".join(uniq)
    return "unknown-target"


# ②：把 ledger 的 not_ready（只反映 High/Critical 门禁）翻成如实的门禁/缺口陈述——**不造 readiness 档**，
# 「无门禁」绝不读成「就绪」，正向路径也只陈述事实并显式否定「系统 ready」。
def _gate_status(applicable: int, passed: int, not_ready: bool,
                 gating_reason: Optional[str]) -> tuple[str, Optional[str]]:
    if not_ready:
        return "blocked", (gating_reason or "存在 High/Critical fail")
    if applicable == 0:
        return "no_applicable_controls", "本轴无适用控制（不产就绪结论）"
    if passed < applicable:
        return "incomplete", (
            f"{applicable - passed}/{applicable} 个适用控制未 pass（Medium fail / inconclusive / 覆盖缺口 / "
            "未评估）——未触发 High/Critical 门禁，但**并非 ready**")
    return "all_applicable_passed", "全部适用控制 security 轴 pass（仍非系统级 ready 结论，见联合裁定与保真度）"


class WarrantView(BaseModel):
    """『凭什么』的单 Finding 切片：confidence_basis 全维摊开 + 统计支撑，绝不折成一个档。"""
    finding_status: str                       # 被主张的裁定（是什么），与凭据正交
    adjudication: str                         # automatic_rule / human_attestation
    uncertainty: str                          # statistical_ci / deterministic / unquantified
    reproducibility: str                      # bit / protocol / declarative
    target_fidelity: str                      # mock / frozen_fixture / …（派生自 execution_backend）
    statistical_backing: Optional[str] = None  # AI: success_rate/CI；确定性: None
    limitations: list[str] = Field(default_factory=list)
    # ③（搭档 P0，ADR-0017 §60）：Finding.rationale 曾被丢——fail 只显示 `[fail]` 不说为何，且
    # attestation 的 ADR-0015「conformant 但缺 justification」冲突警示藏在 rationale 里一并丢失。此处surface。
    rationale: Optional[str] = None           # 裁定理由（fail/inconclusive 必有；含 0015 attestation 冲突 note）
    advisory: list[str] = Field(default_factory=list)  # 结构化 advisory（root_causes P1–P6，只 fail 有）


class ControlView(BaseModel):
    """一个控制在报告里的三问切片。"""
    control_id: str
    title: Optional[str] = None
    domain: Optional[str] = None
    ce_area: Optional[str] = None             # ADR-0021：Cyber Essentials area 下钻（AI 控制 None）
    # ③（搭档 P0，ADR-0017 §60）：ControlView 曾丢 target 身份——两台 FW-03 主机渲染成同名段落无法区分。
    # target_label = 供人读的目标标识（host_id / model + defense 变体）；targets = 各 Finding 的原始
    # target_ref（机器可读，bare/defended 两臂各一）。同一 control 跨主机不再折成一段。
    target_label: str = "unknown-target"
    targets: list[dict[str, Any]] = Field(default_factory=list)
    # ── 能说什么 ──
    outcome: str                              # rollup status（pass/fail/inconclusive/not_applicable/gap）
    severity: Optional[str] = None
    # FRICTION 2（grounding 预标）：security 轴单臂 status 与 security⊗utility 联合裁定并列呈现——
    # ledger 取 defended Finding.status，但 joint_verdict 可能 utility_failed；报告不替读者取舍，两个都摊。
    security_statuses: list[str] = Field(default_factory=list)  # 各 Finding.status（bare/defended）
    joint_verdict: Optional[str] = None       # ComparisonSpec.joint_verdict（有防御实验时）
    # ④（搭档 P0，ADR-0017 §61）：无 comparison 的确定性检查 joint_verdict=None，曾被静默省略、读者
    # 无从分辨「未评估」与「评估过无分歧」。joint_evaluated 显式承载「是否做过 bare/defended 联合裁定」。
    joint_evaluated: bool = False
    standards: list[str] = Field(default_factory=list)  # 审计闭环：control_id→standards_refs→registry
    # ── 凭什么 ──
    warrants: list[WarrantView] = Field(default_factory=list)
    # ── 不能说什么 ──
    unassessable_reasons: list[str] = Field(default_factory=list)  # Claim.assessable=False（fail-closed）
    fail_closed_reasons: list[str] = Field(default_factory=list)   # ComparisonSpec ¬assertable 的子因
    not_covered: list[str] = Field(default_factory=list)           # ScopeStatement.not_covered


class MatrixRow(BaseModel):
    """coverage × (warrant, fidelity) 二维矩阵一行（per rollup 轴 key）。

    coverage/not_ready 直接来自 CoverageLedger.axes；fidelity/reproducibility 分布是把每个控制的
    confidence_basis 归并到轴上——**这一归并今天没有任何对象承载**（见 FRICTION 1）。
    单位对齐到「控制」：每份 report 贡献一个计数，与 coverage 分母同口径。

    ADR-0021（P0#1）：第二根真实轴（Cyber Essentials area）出现后，行从 `domain: str` 泛化为
    `axis` + `key`——domain 轴与 ce_area 轴共用同一行结构。domain 轴不被 ce_area 替换、两轴并存。
    """
    axis: str                                 # "domain" | "ce_area"
    key: str                                  # domain 如 "network_security"；ce_area 如 "firewalls"
    applicable: int                           # 分母（not_applicable 出分母）
    passed: int
    # ⭐ 选项 A（ADR-0017）：coverage 是 **security 轴** 覆盖，取 defended 单臂 Finding.status（不重算
    # ledger，守「只投影不重算」）。渲染层显式标「security 轴覆盖」，永远与下面的分布 + joint_caveats 并读。
    coverage: float                           # passed / applicable —— 单看会误导，见 joint_caveats
    not_ready: bool                           # 任一 High/Critical fail 否决本轴（ledger 原值，审计留存）
    gating_reason: Optional[str] = None
    # ②（搭档 P0，ADR-0017 §59）：`not_ready=False ≠ ready`——Medium fail / 部分覆盖 / 全 inconclusive
    # 都 not_ready=False，字段名诱导把「无 High/Critical 门禁」误读成「就绪」。**刻意不造 readiness 档**
    # （造一个正向就绪判读本身就是过度声称）；gate_status 只陈述门禁/缺口事实，正向路径也只说「全适用
    # pass」并显式否定「系统 ready」，never 断言就绪。见 _gate_status。
    gate_status: str = "unknown"              # blocked / incomplete / all_applicable_passed / no_applicable_controls
    gate_detail: Optional[str] = None         # 人可读理由（为何 blocked / 差几个未 pass / …）
    # ④：本轴是否做过 bare/defended 联合裁定（区分「未评估」与「评估过无分歧」，见 ControlView.joint_evaluated）。
    joint_evaluated: bool = False
    fidelity_mix: dict[str, int] = Field(default_factory=dict)         # {mock: n, frozen_fixture: m}
    reproducibility_mix: dict[str, int] = Field(default_factory=dict)  # {protocol: n, bit: m, declarative: k}
    unassessable: int = 0                     # 该轴内缺 provenance、无凭据的控制数
    # ⭐ 选项 A 的核心：被算作 passed、但 joint_verdict 并非 acceptable 的控制计数（{joint_verdict: n}）。
    # 例：一个防御「检到注入即 abort」→ security-pass 但 joint=utility_failed → 这里记 {utility_failed:1}，
    # 让 security 轴覆盖数永远读不成「系统安全」。哲学依据见 DESIGN「附：检测到注入就中止任务算不算安全」。
    joint_caveats: dict[str, int] = Field(default_factory=dict)
    # ADR-0019：本轴内被评估清单声明、却整条无 report 的控制（进 applicable 分母、非 pass）。coverage 因此
    # 对声明算、不再靠少传 report 做高。无 manifest → 空（此时 coverage=仅已评估，见 Report.manifest_hash 警示）。
    not_assessed_controls: list[str] = Field(default_factory=list)


class Report(BaseModel):
    """内部试用报告：coverage×warrant/fidelity 矩阵 + per-control 三问视图。

    ⭐ G2：**刻意无 overall_score / 单一置信度字段**——矩阵不折成标量，fidelity 始终显式在场，
    读者不可能拿工程成熟度冒充环境真实性（见试用里程碑两轴正交论证）。
    """
    generated_from: list[str] = Field(default_factory=list)
    matrix: list[MatrixRow] = Field(default_factory=list)
    controls: list[ControlView] = Field(default_factory=list)
    # ADR-0019：对照的评估清单（分母来源）。manifest_hash 在 = coverage 对声明算、可审计；
    # None = 未对照清单 → coverage 分母仅「已评估」、**可被输入选择做高**，呈现层须如实警示此局限。
    manifest_hash: Optional[str] = None
    declared_controls: list[str] = Field(default_factory=list)      # 清单声明的全部控制（跨域）
    not_assessed_controls: list[str] = Field(default_factory=list)  # 声明了却整条无 report（跨域汇总）
    undeclared_assessed: list[str] = Field(default_factory=list)    # 评估了但清单未声明（越界，如实点名）
    # ADR-0021（R1）：无 Cyber Essentials area 归属的控制（如 AI 控制）——不进 CE-area 覆盖行，此处单列
    # 点名，呈现层的 CE-area 视图须显式披露「这些控制不在任何 CE area、未从该视图消失」。
    ce_area_unmapped: list[str] = Field(default_factory=list)


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
                limitations=cb.limitations,
                # ③：把裁定理由与结构化 advisory surface 到凭据（fail 的原因、attestation 的 0015 冲突 note）。
                rationale=finding.rationale,
                advisory=list(finding.root_causes or [])))
        else:
            # ③：不可评估的 Finding 也别把它自己的 rationale 丢掉（若有）——附在不可评估原因后如实带出。
            reason = claim.unassessable_reason or "unassessable（原因未记）"
            if finding.rationale:
                reason = f"{reason}（Finding rationale：{finding.rationale}）"
            unassessable.append(reason)

    fail_closed: list[str] = []
    joint: Optional[str] = None
    for cmp in report.comparisons:
        joint = cmp.joint_verdict             # 单防御实验；多个时取最后（首版无多比较场景）
        if not cmp.assertable:
            fail_closed.extend(cmp.invalidity_reasons)

    targets = [f.target_ref for f in report.findings]
    return ControlView(
        control_id=(ctrl.id if ctrl else report.measurement_context.get("control_id", "UNKNOWN")),
        title=(ctrl.title if ctrl else None),
        domain=(ctrl.domain if ctrl else report.measurement_context.get("domain")),
        ce_area=(ctrl.ce_area if ctrl else None),
        target_label=_target_label(targets),
        targets=targets,
        outcome=control_outcome(report).status,
        severity=(ctrl.severity_if_failed if ctrl else None),
        security_statuses=[f.status for f in report.findings],
        joint_verdict=joint,
        joint_evaluated=bool(report.comparisons),   # ④：无 comparison → 未做联合裁定（非「无分歧」）
        standards=[e.name for e in report.referenced_standards.values()],
        warrants=warrant_views,
        unassessable_reasons=unassessable,
        fail_closed_reasons=sorted(set(fail_closed)),
        not_covered=list(report.scope.not_covered),
    )


def _axis_keys(r: AssuranceReport) -> list[tuple[str, str]]:
    """一份 report 归属的 (轴, key) 对。domain 恒有（缺→unknown）；ce_area 仅当控制有映射才加——
    无 ce_area 的控制（如 AI 控制）不进 CE-area 覆盖行，改由 ledger.unmapped 单列（R1，ADR-0021）。"""
    pairs: list[tuple[str, str]] = []
    domain = (r.control.domain if r.control else r.measurement_context.get("domain")) or "unknown"
    pairs.append(("domain", domain))
    ce_area = r.control.ce_area if r.control else None
    if ce_area:
        pairs.append(("ce_area", ce_area))
    return pairs


def _matrix(reports: list[AssuranceReport], ledger: "CoverageLedger") -> list[MatrixRow]:
    # ── FRICTION 1（grounding 预标；R2/ADR-0021 泛化）──────────────────────────
    # G2 要 coverage × fidelity 二维，但 CoverageLedger.axes 只带 coverage/not_ready，fidelity 埋在每条
    # Claim.confidence_basis 里。**没有任何对象把二者配对**——故此处重走 reports、把 Claim 的
    # fidelity/reproducibility 归并回 ledger 轴。第二根真实轴（ce_area）出现后，join 从 per-domain 泛化到
    # per-(axis,key)：同一控制的 fidelity 同时计入其 domain 行与 ce_area 行。**泛化 join 循环、不复制两份**；
    # FRICTION 1「是否升成承载对象」压力随第二轴变大——本刀仍不建对象、只记录加压（见 ADR-0021）。
    fidelity: dict[tuple[str, str], Counter] = defaultdict(Counter)
    repro: dict[tuple[str, str], Counter] = defaultdict(Counter)
    unassessable: dict[tuple[str, str], int] = defaultdict(int)
    caveat: dict[tuple[str, str], Counter] = defaultdict(Counter)   # 选项 A：passed 但 joint≠acceptable
    joint_evaluated: dict[tuple[str, str], bool] = defaultdict(bool)  # ④：本轴 key 是否做过联合裁定
    for r in reports:
        assessable = [c for c in derive_claims(r) if c.assessable and c.confidence_basis is not None]
        # report 级保真度单值（同一 mctx.execution_backend）→ 取一条即可、单位=控制。
        cb = assessable[0].confidence_basis if assessable else None
        is_pass = control_outcome(r).status == "pass"
        for ak in _axis_keys(r):              # 同一 report 同时贡献其 domain 行与 ce_area 行
            if r.comparisons:
                joint_evaluated[ak] = True
            if cb is not None:
                fidelity[ak][cb.target_fidelity] += 1
                repro[ak][cb.reproducibility] += 1
            else:
                unassessable[ak] += 1
            # 选项 A：本控制被算作 passed（defended 单臂 security-pass），但联合裁定不是 acceptable → 记警示。
            # 只对 passed 控制记（未 pass 的控制其 outcome 已如实反映问题，无需再警示覆盖数）。
            if is_pass:
                for cmp in r.comparisons:
                    jv = cmp.joint_verdict
                    if jv and jv != "acceptable":
                        caveat[ak][jv] += 1

    rows: list[MatrixRow] = []
    for ax in ledger.axes:                    # ax.axis ∈ {"domain", "ce_area"}
        k = (ax.axis, ax.key)
        gate_status, gate_detail = _gate_status(ax.applicable, ax.passed, ax.not_ready, ax.gating_reason)
        rows.append(MatrixRow(
            axis=ax.axis, key=ax.key, applicable=ax.applicable, passed=ax.passed,
            coverage=ax.coverage, not_ready=ax.not_ready, gating_reason=ax.gating_reason,
            gate_status=gate_status, gate_detail=gate_detail,
            joint_evaluated=joint_evaluated[k],
            fidelity_mix=dict(fidelity[k]),
            reproducibility_mix=dict(repro[k]),
            unassessable=unassessable[k],
            joint_caveats=dict(caveat[k]),
            not_assessed_controls=list(ax.not_assessed_controls)))
    return rows


def render_report(reports: list[AssuranceReport],
                  generated_from: Optional[list[str]] = None,
                  manifest: Optional[AssessmentManifest] = None) -> Report:
    """一批 AssuranceReport → 内部试用报告（纯函数）。

    输入可混合：AI 会话（`SessionReport.runs` 拆开）+ 确定性切片的单份 report。空输入 → 空报告
    （无控制、无矩阵；不静默产正向结论）。

    `manifest`（ADR-0019）在时：覆盖率对**声明控制集**算，声明了却无 report 的控制显式 not_assessed、
    不再隐形；越界评估（清单未声明）也如实点名。None 时覆盖率分母仅「已评估」、可被输入选择做高——
    渲染层如实标此局限（见 to_markdown 顶部警示）。
    """
    ledger = build_ledger(reports, manifest=manifest)
    matrix = _matrix(reports, ledger)
    reported_ids = sorted({control_outcome(r).control_id for r in reports})
    # not_assessed 跨域汇总只从 domain 轴取（ce_area 轴会把同一 not_assessed 控制重复列，去重靠 domain 轴）。
    not_assessed = sorted({cid for row in matrix if row.axis == "domain"
                           for cid in row.not_assessed_controls})
    undeclared = (sorted(set(reported_ids) - manifest.control_ids()) if manifest else [])
    return Report(
        generated_from=(generated_from or [r.generated_from for r in reports]),
        matrix=matrix,
        controls=[_control_view(r) for r in reports],
        manifest_hash=(manifest.manifest_hash if manifest else None),
        declared_controls=(sorted(manifest.control_ids()) if manifest else []),
        not_assessed_controls=not_assessed,
        undeclared_assessed=undeclared,
        ce_area_unmapped=ledger.unmapped.get("ce_area", []))


# ── 渲染器（Step 2）：只格式化 Report、不重算任何裁定 ─────────────────────────
# to_json：机器可读；to_markdown：人可读。二者同源（同一个 Report），渲染层唯一「加工」是
# 把 coverage 标注成「安全轴覆盖」并常驻 ⚠ 联合裁定警示（选项 A 的呈现落点，见 render_report 文档串）。

def _mix(d: dict[str, int]) -> str:
    return "、".join(f"{k}×{v}" for k, v in d.items()) if d else "—"


# ②：把 gate_status 枚举翻成表格单元——「无门禁」绝不渲染成裸「—」（会读成清白）。
_GATE_CELL = {
    "blocked": "⛔ blocked",
    "incomplete": "⚠ incomplete",
    "all_applicable_passed": "✔ 全适用 pass（非系统 ready）",
    "no_applicable_controls": "— 无适用控制",
}


def _gate_cell(m: "MatrixRow") -> str:
    head = _GATE_CELL.get(m.gate_status, m.gate_status)
    cell = f"{head}：{m.gate_detail}" if m.gate_detail and m.gate_status in ("blocked", "incomplete") else head
    if m.not_assessed_controls:               # ADR-0019：点名本域声明却未评估的控制
        cell += f"｜未评估：{'、'.join(m.not_assessed_controls)}"
    return cell


# ④：联合裁定列——区分「未评估（无防御实验）」与「评估过、无分歧」，二者曾都渲染成裸「—」。
def _joint_cell(m: "MatrixRow") -> str:
    if m.joint_caveats:
        return _mix(m.joint_caveats)
    return "✔ 已评估无分歧" if m.joint_evaluated else "未评估（无防御实验）"


# ADR-0021（P0#1）：一个轴的覆盖表渲染成独立区段（domain 视图 / CE area 视图共用）。返回本区段是否
# 出现联合裁定警示（供顶层决定是否附 caveat 图例）。空区段（无该轴的行）如实标注、不留空白被误读。
def _matrix_section(lines: list[str], rows: list["MatrixRow"], title: str, key_header: str) -> bool:
    lines.append(title)
    lines.append("")
    if not rows:
        lines.append(f"> （本报告无 {key_header} 轴的覆盖行。）")
        lines.append("")
        return False
    lines.append(f"| {key_header} | 安全轴覆盖 | 门禁 / 缺口 | ⚠ 联合裁定 | 目标保真度 | 可复现 | 不可评估 |")
    lines.append("|----|-----------|-----------|-----------|-----------|--------|---------|")
    any_caveat = False
    for m in rows:
        if m.joint_caveats:
            any_caveat = True
        lines.append(f"| {m.key} | {m.passed}/{m.applicable} = {m.coverage} | {_gate_cell(m)} "
                     f"| {_joint_cell(m)} | {_mix(m.fidelity_mix)} | {_mix(m.reproducibility_mix)} "
                     f"| {m.unassessable} |")
    lines.append("")
    return any_caveat


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

    # ── 评估清单披露（ADR-0019）：覆盖率分母对什么算、有没有被输入选择做高的空间 ──
    if report.manifest_hash:
        lines.append(f"> **对照评估清单** `manifest_hash={report.manifest_hash}`：声明 "
                     f"{len(report.declared_controls)} 个控制。覆盖率对**声明控制集**算——声明了却整条未评估的"
                     "控制显式列出并计入分母，**无法靠少传 report 做高**。")
        if report.not_assessed_controls:
            lines.append(f"> ⚠ 声明但**未评估**（进分母、非 pass）：{'、'.join(report.not_assessed_controls)}。")
        if report.undeclared_assessed:
            lines.append(f"> ⚠ **越界评估**（清单未声明却跑了）：{'、'.join(report.undeclared_assessed)}——"
                         "范围外结果，不计入声明覆盖率分母。")
    else:
        lines.append("> ⚠ **未对照评估清单**：覆盖率分母仅含**已评估**控制，可被输入选择做高（少传一份 report，"
                     "未评估的控制就从分母消失、覆盖率虚高）。要让覆盖率对固定声明成立，需提供 "
                     "`AssessmentManifest`（ADR-0019）。")
    lines.append("")

    # ── 覆盖矩阵：按 domain 轴 + Cyber Essentials area 轴分区呈现（ADR-0021 P0#1）──
    # 两轴并存、domain 不被 ce_area 替换。每个 area 的覆盖数命名「声明范围内 security 轴覆盖」，
    # 绝不简称「Firewalls coverage」（那会把稀疏分母读成「防火墙已覆盖」）。
    lines.append("## 覆盖矩阵（安全轴覆盖 × 凭据 / 保真度）")
    lines.append("")
    domain_rows = [m for m in report.matrix if m.axis == "domain"]
    ce_rows = [m for m in report.matrix if m.axis == "ce_area"]
    any_caveat = _matrix_section(lines, domain_rows, "### Domain 视图", "域")
    any_caveat = _matrix_section(lines, ce_rows, "### Cyber Essentials area 视图", "CE area") or any_caveat
    # R1（ADR-0021）：无 CE-area 归属的控制显式披露，绝不从 CE-area 视图静默消失，也不伪装成一个带分数的 area。
    if report.ce_area_unmapped:
        lines.append(f"> ⚠ **不在任何 Cyber Essentials area**（如 AI 控制）：{'、'.join(report.ce_area_unmapped)}"
                     "——这些控制不映射到 CE area，故不出现在上表任何行；它们的裁定见下方控制详情与 Domain 视图，"
                     "**未从报告消失，只是 CE 框架无对应 area**。")
        lines.append("")
    lines.append("> 「安全轴覆盖」只算 security 轴（defended 单臂裁定），**不可单独读作「系统安全」**。")
    lines.append("> 覆盖分母的单位是**每份 report 一个 outcome**（外加清单声明却未评估的控制），"
                 "**不是**严格的「一控制一票」：同一控制跑在多台 target 上会计多个 outcome（例：FW-03 两台主机"
                 "= 两个 outcome）。跨 target 的控制级归约是 ADR-0019 已知边界，本报告不做归约、只如实披露。")
    lines.append("> 「门禁 / 缺口」**刻意不产就绪档**：**无 High/Critical 门禁 ≠ ready**——Medium fail / 部分覆盖 / "
                 "全 inconclusive 都不触发门禁却仍非就绪，故 `incomplete` 明标未 pass 数；即便全适用 pass 也只标"
                 "「非系统 ready 结论」，不越权替部署方下整体就绪判断。")
    lines.append("> 「联合裁定」列的 `未评估（无防御实验）` 指该域只做了确定性 security 检查、未跑 bare/defended "
                 "对比，**不等于**「已评估、无分歧」（后者显示 `✔ 已评估无分歧`）——空白不读作无问题。")
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
        # ③：target_label 进标题——两台 FW-03 主机不再折成同名段落。
        target = f" @ {c.target_label}" if c.target_label and c.target_label != "unknown-target" else ""
        # ADR-0021：CE area 进详情供下钻回具体控制（无映射的 AI 控制显式标「无 CE area」，不留空）。
        ce = f" · CE area {c.ce_area}" if c.ce_area else " · 无 CE area"
        lines.append(f"### [{c.control_id}]{title}{target} — {c.domain or 'unknown'}{ce}")
        lines.append("")
        # 能说什么
        head = [f"结论 **{c.outcome}**"]
        if c.severity:
            head.append(f"severity {c.severity}")
        if c.joint_verdict:
            head.append(f"联合裁定 **{c.joint_verdict}**")
        elif not c.joint_evaluated:
            # ④：确定性检查无 bare/defended 对比 → 如实标未评估，不留空让读者误读成无问题。
            head.append("联合裁定 **未评估**（无 bare/defended 对比）")
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
                # ③：裁定理由 + 结构化 advisory surface（fail 为何失败、attestation 的 0015 冲突 note）。
                if w.rationale:
                    lines.append(f"  - 裁定理由：{w.rationale}")
                if w.advisory:
                    lines.append(f"  - advisory（root_causes）：{'、'.join(w.advisory)}")
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
