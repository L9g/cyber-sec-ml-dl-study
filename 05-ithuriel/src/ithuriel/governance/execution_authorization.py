"""ADR-0022 一人两帽开发期治理：执行授权校验 + git 顺序锚 + 运行收据（信任核）。

从 `scripts/run_calendar_probe.py` 原样搬入（P1）。fail-closed 授权链的全部逻辑：
Hat A 冻结的不可变 execution request、Hat B 后续独立 commit 的 approval、三方哈希一致校验
（request 声明 = 当前字节 = approval_commit 下的 blob）、request_commit 严格早于 approval_commit、
批准窗口 ≤24h、now+max_runtime ≤ valid_until、逐 trial deadline，缺任一环 AuthorizationError。

⚠ git 只是**顺序锚点、不是可信时间戳**（本地时间可回填、历史可重写）。授权门保证「冻结的那份
代码跑了」，**不保证「那份代码实现了冻结的那份设计」**——hash 管字节、管不了语义，语义只有测试能管。

纯逻辑 + 受控 subprocess(git) + 文件读；不碰 agentdojo、不调模型。_sha 从 oracle 复用
（证据完整性与执行请求哈希共用的内容寻址原语）。
"""
import os
import json
import subprocess
import datetime
import hashlib

from ithuriel.probes.calendar.oracle import _sha
from ithuriel.probes.calendar.payload import MEASUREMENT_SCHEMA_VERSION, CELLS

# 本模块从 scripts/run_calendar_probe.py 搬入 src/ithuriel/governance/ 后，默认 repo_root 须指向
# 项目根（含 scripts/ 与 docs/trial/ 的 05-ithuriel/）——即本文件上溯四级目录。原代码用 __file__
# 上溯两级是因为它当时住在 scripts/；搬迁后深度变了，故显式钉死。调用方仍可传 repo_root 覆盖。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


class AuthorizationError(ValueError):
    """执行授权缺失、失效或与当前 runtime 不匹配；调用方必须 fail closed。"""


def _utc(value):
    """严格读取带时区的 ISO-8601 时间。"""
    if not isinstance(value, str) or not value.strip():
        raise AuthorizationError("valid_from/valid_until 必须是带时区的 ISO-8601 时间")
    try:
        dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthorizationError(f"无效时间 {value!r}") from exc
    if dt.tzinfo is None:
        raise AuthorizationError(f"时间必须带时区：{value!r}")
    return dt.astimezone(datetime.timezone.utc)


# ---------------- ADR-0022 时间锚点：git 顺序锚（**非可信时间戳**）----------------
# ⚠ 本地 git 的 author/committer 时间可回填、历史可重写，故 commit **只证顺序、不证时刻**。
# artifact 因此固定标 `temporal_anchor: local_git_only`；要外部可信时序需 push 后由服务器侧
# CI 记录，本阶段不建。
MAX_APPROVAL_WINDOW_HOURS = 24


def _git(repo_root, *args, binary=False):
    p = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, check=False,
                       text=not binary)
    if p.returncode != 0:
        err = p.stderr if not binary else p.stderr.decode(errors="replace")
        raise AuthorizationError(f"git {' '.join(args)} 失败：{(err or '').strip()[:200]}")
    return p.stdout


def _git_prefix(repo_root):
    """cwd 相对**仓库根**的前缀。monorepo 里 05-ithuriel/ 就是这个前缀——
    `git show <commit>:<path>` 的路径必须相对仓库根，不能相对 cwd。"""
    return _git(repo_root, "rev-parse", "--show-prefix").strip()


def _blob_sha_at(repo_root, commit, path):
    """`git show <commit>:<path>` 的真实字节 SHA-256（路径自动补仓库根前缀）。"""
    full = f"{_git_prefix(repo_root)}{path}"
    return hashlib.sha256(_git(repo_root, "show", f"{commit}:{full}", binary=True)).hexdigest()


def _file_sha(repo_root, path):
    with open(os.path.join(repo_root, path), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _last_commit_touching(repo_root, path):
    out = _git(repo_root, "log", "-1", "--format=%H", "--", path).strip()
    if not out:
        raise AuthorizationError(f"{path} 未进入 git 历史（未 commit 即不构成冻结）")
    return out


def _assert_tracked_and_clean(repo_root, paths):
    """**只检查受管辖材料**，不用全局 `git diff --quiet`：后者会被无关草稿阻塞，
    且默认看不见未跟踪文件。"""
    for path in paths:
        try:
            _git(repo_root, "ls-files", "--error-unmatch", "--", path)
        except AuthorizationError as exc:
            raise AuthorizationError(f"受管辖材料未被 git 跟踪：{path}") from exc
    dirty = _git(repo_root, "diff", "HEAD", "--name-only", "--", *paths).split()
    if dirty:
        raise AuthorizationError(f"受管辖材料有未提交改动：{', '.join(sorted(set(dirty)))}")


def _assert_strict_ancestor(repo_root, older, newer, label):
    """严格祖先：**必须是不同 commit**。同一个 commit 只能证明「跑之前存在一份批准包」，
    证不出 Hat A → Freeze → Hat B 的先后过程。"""
    if older == newer:
        raise AuthorizationError(f"{label}：request 与 approval 在同一个 commit，角色切换未进入证据链")
    p = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer],
                       cwd=repo_root, capture_output=True, check=False)
    if p.returncode != 0:
        raise AuthorizationError(f"{label}：{older[:8]} 不是 {newer[:8]} 的祖先")


def _governed_materials_env():
    """受管辖材料清单。**没有安全的默认值**（partner review 2026-07-22 C6）。

    此前缺省只有 runner；漏列 prereg 时，request 与 runtime 会**双双**用同一个不安全默认值、
    因而彼此匹配，于是 prereg 根本不进三方哈希，改了它仍能跑出
    `authorization_status=approved` 与 `analysis_eligibility=preregistered`。
    安全关键集合不交给「忘了设就有默认」的环境变量，未设即拒。
    """
    raw = os.environ.get("CAL_GOVERNED_MATERIALS", "").strip()
    mats = [m.strip() for m in raw.split(",") if m.strip()] if raw else []
    if not mats:
        raise AuthorizationError(
            "缺 CAL_GOVERNED_MATERIALS：受管辖材料必须显式声明（至少 runner 与本轮 prereg）")
    return mats


def _max_runtime_env():
    raw = os.environ.get("CAL_MAX_RUNTIME_MINUTES", "").strip()
    if not raw:
        raise AuthorizationError("缺少 CAL_MAX_RUNTIME_MINUTES（deadline 预检与逐 trial 检查需要）")
    return float(raw)


def write_run_receipt(artifact_path, meta, primary, started_at, out_dir="docs/trial/receipts"):
    """运行后 receipt（可入库的小文件）。含 artifact 的 SHA-256，故**不可能早于 artifact 存在**，
    从而把「运行发生在批准之后」也接进 git 顺序链。原始结果 JSON 仍保持 gitignore。"""
    os.makedirs(out_dir, exist_ok=True)
    with open(artifact_path, "rb") as f:
        art_sha = hashlib.sha256(f.read()).hexdigest()
    receipt = {
        "artifact": os.path.basename(artifact_path),
        "artifact_sha256": art_sha,
        "execution_request_hash": meta.get("execution_request_hash"),
        "request_commit": meta.get("request_commit"),
        "approval_commit": meta.get("approval_commit"),
        "temporal_anchor": meta.get("temporal_anchor"),
        "authorization_status": meta.get("authorization_status"),
        "analysis_eligibility": meta.get("analysis_eligibility"),
        "run_level_analysis_eligibility": meta.get("run_level_analysis_eligibility"),
        # started_at 必须是**真实运行起点**；事后补生成 receipt 时不得用当下时间冒充，
        # 应传 None 并另记重建值（见 2026-07-22 receipt correction）。
        "started_at": started_at,
        "artifact_generated_at": meta.get("generated_at"),
        "receipt_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verdict": primary.get("verdict"),
    }
    p = os.path.join(out_dir, os.path.basename(artifact_path).replace(".json", ".receipt.json"))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=1)
    return p


def run_completion_status(phase, terminated_on_deadline, completed_attempts,
                          max_authorized_attempts, auth_analysis_eligibility,
                          target_interpretable=None, interpretable_reached=None):
    """run 级排除语义（纯函数，供自检钉死）。三条边界：

    ① 到期只阻止**启动下一个 trial**；已开始的 trial 由其起始授权覆盖（`trial_atomic`）。
    ② **全部 trial 在期限内跑完、只是聚合或写 artifact 时过期，不算 terminated**——deadline
       管的是执行授权，不管离线计算。故本函数只看 `terminated_on_deadline`（该标志仅在
       循环内、启动下一个 trial 之前置位），不看当前时钟。
    ③ pilot 本来就 `excluded_pilot`，到期只附加 `termination_reason`，**不被
       `excluded_incomplete_run` 顶掉**；后者只用于本来可分析的 main run。

    ⭐ 字段命名（partner review 2026-07-22 C3）：此前叫 `planned_trials` 的量在有 attempt-cap
    的模式（confirm/sweep）里其实是**授权上限**，于是 `completed<planned` 被机器消费者误读成
    「中断」，而实际是「补样冗余没用完」。改名 `max_authorized_attempts`，
    另存 `target_interpretable_trials` 与 `completion_criterion_met` 表达真正的完成判据。
    """
    reached = (interpretable_reached if interpretable_reached is not None else completed_attempts)
    status = {
        "run_status": "terminated_on_deadline" if terminated_on_deadline else "completed",
        "termination_reason": "authorization_deadline" if terminated_on_deadline else None,
        "confirmatory_analysis_eligibility": (
            "excluded" if (terminated_on_deadline or auth_analysis_eligibility == "excluded")
            else "preregistered"),
        # 不完整的 run 答不了确认性问题，但已闭合的存在性证据仍然有效，不得一并抹掉
        "descriptive_trial_evidence": "retained",
        "max_authorized_attempts": max_authorized_attempts,
        "completed_attempts": completed_attempts,
        "target_interpretable_trials": target_interpretable,
        "interpretable_reached": interpretable_reached,
        # 完成判据 = 是否达到目标可解释数（无 target 时退回「未因到期中断」）
        "completion_criterion_met": (
            (reached >= target_interpretable) if target_interpretable is not None
            else (not terminated_on_deadline)),
        "last_completed_schedule_index": completed_attempts - 1 if completed_attempts else None,
        "completed_trial_authorization": {"approved": completed_attempts, "lapsed": 0},
        "authorization_coverage": "trial_atomic",
        "resumable": False,
    }
    if phase == "pilot":
        status["primary_verdict"] = "excluded_pilot"
    elif terminated_on_deadline:
        status["primary_verdict"] = "excluded_incomplete_run"
    else:
        status["primary_verdict"] = None      # 由预注册决策表给出，不在此覆盖
    return status


def deadline_exceeded(deadline_iso, now=None):
    """逐 trial 边界检查。**不深入 AgentDojo 内部做逐 tool-call 熔断**，
    故 artifact 固定标 authorization_check_granularity=per_trial，不冒充更细粒度。"""
    now = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
    return now >= _utc(deadline_iso)


def execution_runtime(mode, phase, provider, model, pinned_provider, n, budget_cap_usd,
                      *, arms=None, rung=None, defense=None, host_task="read_only",
                      materials=None, max_runtime_minutes=None, repo_root=None):
    """把会改变执行范围、成本或测量语义的 runtime 参数规范化为 hash-bound 对象。"""
    if phase not in ("pilot", "main"):
        raise AuthorizationError("CAL_PHASE 必须是 pilot 或 main")
    if not isinstance(budget_cap_usd, (int, float)) or isinstance(budget_cap_usd, bool) \
            or budget_cap_usd <= 0:
        raise AuthorizationError("CAL_BUDGET_CAP_USD 必须是正数硬上限")
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise AuthorizationError("CAL_N_TRIALS 必须是正整数")
    if not isinstance(max_runtime_minutes, (int, float)) or isinstance(max_runtime_minutes, bool) \
            or max_runtime_minutes <= 0:
        raise AuthorizationError("max_runtime_minutes 必须是正数（供 deadline 预检与逐 trial 检查）")
    repo_root = repo_root or _PROJECT_ROOT
    runner_sha256 = _file_sha(repo_root, "scripts/run_calendar_probe.py")
    # 受管辖材料：不只 runner —— 预注册、fixture 等测量材料在批准后同样不得变动
    mats = list(materials or ["scripts/run_calendar_probe.py"])
    if "scripts/run_calendar_probe.py" not in mats:
        raise AuthorizationError("受管辖材料必须包含 runner 自身")
    base = {
        "runner": "scripts/run_calendar_probe.py",
        "runner_sha256": runner_sha256,
        "materials": [{"path": m, "sha256": _file_sha(repo_root, m)} for m in sorted(mats)],
        "max_runtime_minutes": float(max_runtime_minutes),
        "measurement_schema_version": MEASUREMENT_SCHEMA_VERSION,
        "experiment_mode": mode,
        "phase": phase,
        "analysis_eligibility": "excluded" if phase == "pilot" else "preregistered",
        "target": "agentdojo-workspace-mock",
        "target_fidelity": "mock",
        "provider": provider,
        "model": model,
        "pinned_provider": pinned_provider or None,
        "budget_cap_usd": float(budget_cap_usd),
    }
    if mode == "matrix":
        base.update(n_per_cell=n, cells=CELLS, max_trials=n * len(CELLS),
                    defense="none (bare pipeline; positive-arm screening)")
    else:
        arms = list(arms or [])
        if arms not in (["positive"], ["positive", "negative"]):
            raise AuthorizationError("CAL_ARMS 必须是 positive 或 positive,negative（顺序固定）")
        extra_defense_arm = 0 if arms == ["positive"] else 1
        base.update(n_per_arm=n, arms=arms, rung=rung, defense=defense,
                    host_task=host_task,
                    max_trials=n * (len(arms) + extra_defense_arm))
    return base


def _load_json(path, label):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationError(f"无法读取{label}：{exc}") from exc


def validate_execution_authorization(request_path, approval_path, expected_runtime, now=None,
                                     repo_root=None):
    """验证 ADR-0022 的 Hat A → Freeze → Hat B 证据链；任何缺口一律 fail closed。

    **必须是两个文件、两个 commit**：request 先提交（Hat A），approval 在其后的 commit 里提交
    （Hat B）。同一 commit 内同时出现只能证明「跑之前存在一份批准包」，证不出角色切换发生过。
    """
    if not request_path or not approval_path:
        raise AuthorizationError(
            "缺少 CAL_EXECUTION_REQUEST_FILE 或 CAL_APPROVAL_FILE（authorization_status=absent）")
    repo_root = repo_root or _PROJECT_ROOT
    rel_req = os.path.relpath(os.path.abspath(request_path), repo_root)
    rel_apr = os.path.relpath(os.path.abspath(approval_path), repo_root)

    req_doc = _load_json(request_path, "执行请求")
    apr_doc = _load_json(approval_path, "批准文件")
    request = req_doc.get("request")
    approval = apr_doc.get("approval")
    if not isinstance(request, dict) or not isinstance(approval, dict):
        raise AuthorizationError("request 文件需含 request 对象、approval 文件需含 approval 对象")
    request_hash = _sha(request)
    if req_doc.get("execution_request_hash") != request_hash \
            or approval.get("execution_request_hash") != request_hash:
        raise AuthorizationError("execution_request_hash 缺失或不匹配（authorization_status=lapsed）")

    # ① 受管辖材料 + 两份治理文件都必须已跟踪且无未提交改动
    governed = [m["path"] for m in request.get("materials", [])] + [rel_req, rel_apr]
    _assert_tracked_and_clean(repo_root, governed)
    # ② Hat A 先于 Hat B，且 Hat B 已进入当前 HEAD
    request_commit = _last_commit_touching(repo_root, rel_req)
    approval_commit = _last_commit_touching(repo_root, rel_apr)
    head = _git(repo_root, "rev-parse", "HEAD").strip()
    _assert_strict_ancestor(repo_root, request_commit, approval_commit, "Hat A → Hat B")
    if approval_commit != head:
        _assert_strict_ancestor(repo_root, approval_commit, head, "approval → HEAD")
    # ③ 三方哈希一致：request 声明 == 当前字节 == approval_commit 下的 blob
    #    代码与批准时不符**一律拒跑**，不只是标 dirty（freeze 的语义就是 fail closed）
    for m in request.get("materials", []):
        declared, cur = m.get("sha256"), _file_sha(repo_root, m["path"])
        blob = _blob_sha_at(repo_root, approval_commit, m["path"])
        if not (declared == cur == blob):
            raise AuthorizationError(
                f"受管辖材料 {m['path']} 三方哈希不一致（声明 {str(declared)[:8]} / "
                f"当前 {cur[:8]} / 批准时 {blob[:8]}）")
    if request.get("runtime") != expected_runtime:
        raise AuthorizationError("当前 runtime 与冻结 request 不匹配（authorization_status=lapsed）")
    required_request = ("allowed_side_effects", "prohibited_side_effects", "roe_or_policy_ref",
                        "prereg_ref")
    if any(k not in request or request[k] in (None, "", []) for k in required_request):
        raise AuthorizationError("request 未冻结 side-effect/RoE 边界或 prereg_ref")
    # ⭐ C6：**request 自己声明的 prereg 必须进受管辖材料**，否则它不参与三方哈希，
    # 批准后被改动也检不出来。这条不依赖调用方记得把 prereg 加进清单。
    material_paths = [m.get("path") for m in request.get("materials", [])]
    if request["prereg_ref"] not in material_paths:
        raise AuthorizationError(
            f"prereg_ref {request['prereg_ref']} 未列入受管辖材料 —— 它不会进三方哈希")
    fixed = {
        "decision": "approve",
        "authorization_mode": "self_authorized_solo",
        "role_separation": "procedural",
        "person_independence": "none",
        "independence_verification": "not_applicable",
        "conflict_of_interest": "self_review",
        "approval_scope": "internal_t0_t2_development",
    }
    bad = [k for k, v in fixed.items() if approval.get(k) != v]
    if bad:
        raise AuthorizationError("批准字段不符合 ADR-0022：" + ", ".join(bad))
    if not approval.get("approved_by") or approval.get("approval_role") != "execution_authorizer":
        raise AuthorizationError("批准必须记录 approved_by 与 execution_authorizer 角色")
    if approval.get("approved_target") != expected_runtime["target"] \
            or approval.get("approved_provider") != expected_runtime["provider"] \
            or approval.get("budget_cap_usd") != expected_runtime["budget_cap_usd"]:
        raise AuthorizationError("批准的 target/provider/budget 与当前 runtime 不匹配")
    if approval.get("adversarial_review") not in ("none", "ai_agent", "peer"):
        raise AuthorizationError("adversarial_review 必须是 none、ai_agent 或 peer")
    if approval.get("adversarial_review") != "none" and not approval.get("adversarial_review_ref"):
        raise AuthorizationError("发生对抗性复核时必须记录 adversarial_review_ref")
    if expected_runtime["phase"] == "pilot" \
            and expected_runtime["analysis_eligibility"] != "excluded":
        raise AuthorizationError("pilot 必须 analysis_eligibility=excluded")
    instant = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
    vfrom, vuntil = _utc(approval.get("valid_from")), _utc(approval.get("valid_until"))
    if vuntil - vfrom > datetime.timedelta(hours=MAX_APPROVAL_WINDOW_HOURS):
        raise AuthorizationError(f"批准窗口超过 {MAX_APPROVAL_WINDOW_HOURS} 小时上限（常设通行证）")
    if not (vfrom <= instant < vuntil):
        raise AuthorizationError("批准尚未生效或已经过期（authorization_status=lapsed）")
    # 启动即预检整段运行能否落在窗口内：否则「到期前一秒起跑」仍能跑完整个矩阵
    deadline = min(vuntil, instant + datetime.timedelta(minutes=expected_runtime["max_runtime_minutes"]))
    if instant + datetime.timedelta(minutes=expected_runtime["max_runtime_minutes"]) > vuntil:
        raise AuthorizationError("now + max_runtime 超出 valid_until：剩余窗口不足以跑完")
    return {
        "authorization_mode": approval["authorization_mode"],
        "authorization_status": "approved",
        "execution_request_hash": request_hash,
        "request_commit": request_commit,
        "approval_commit": approval_commit,
        "head_commit": head,
        "temporal_anchor": "local_git_only",   # git 只证顺序，不是可信时间戳
        "governed_materials": request.get("materials", []),
        "prereg_path": request["prereg_ref"],
        "prereg_sha256": next(m["sha256"] for m in request["materials"]
                              if m["path"] == request["prereg_ref"]),
        "deadline_utc": deadline.isoformat(),
        "authorization_check_granularity": "trial_boundary",   # 不假装做到逐 tool-call 熔断
        "role_separation": approval["role_separation"],
        "person_independence": approval["person_independence"],
        "independence_verification": approval["independence_verification"],
        "adversarial_review": approval["adversarial_review"],
        "adversarial_review_ref": approval.get("adversarial_review_ref"),
        "execution_request_artifact": rel_req,
        "approval_artifact": rel_apr,
        "approved_budget_cap_usd": expected_runtime["budget_cap_usd"],
        "budget_enforcement": "hash-bound preflight plus max_trials; no live USD metering",
        "phase": expected_runtime["phase"],
        "analysis_eligibility": expected_runtime["analysis_eligibility"],
    }
