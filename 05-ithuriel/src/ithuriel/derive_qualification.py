"""instrument qualification 的 loader glue：字节层 + provenance 闭合 → 调纯函数派生器 → 三件产物。

判定逻辑一概在 `probes/calendar/qualification.py`（纯函数、吃已解析 dict）。本模块只做它**按设计
不做**的事：读文件、算字节 SHA-256、闭合 artifact↔receipt↔request 的哈希绑定、按授权时冻结的引用
取回 `prefix_gate_record`，然后调派生器；**派生逻辑不塞回 runner、也不复制进本模块**。

git 层（三方哈希、commit 祖先、批准窗口、campaign 块与前缀门的授权核验）**不在这里**——那是
`governance/execution_authorization.py` 的**跑前**授权门。本模块是**跑后离线**派生：无网络、无模型、
无计费、不需要 git。两侧的唯一接口是授权门写进 artifact.meta 并由 receipt 回显的 `qualification_campaign`
块（预注册 §7/§9）。

三件产物：
1. **qualification report**（数据，`reports/` gitignore）：派生器完整输出 + 各输入哈希。
2. **committed 审计锚**（§9 P1-6）：report hash + 各输入 hash + deriver hash + rule version + verdict；
   即便 report 本身不入 git，verdict 也有 committed 锚。
3. **committed `prefix_gate_record`**（仅 `in_progress` ∧ `next_window_authorizable`）：下一窗口
   Hat A 要绑的那份，字段形状由授权门 `_verify_prefix_gate_record` 钉死。终局状态**拒绝**产出前缀门。

退出码：0 = in_progress / full_qualified；6 = 终局（not_qualified / inconclusive）；4 = 输入不可信
（哈希/绑定/形态 fail-closed）。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
from typing import Any, Optional

from ithuriel.probes.calendar import qualification as q
from ithuriel.probes.calendar.oracle import _sha

# <root>/src/ithuriel/derive_qualification.py → 上溯三级 = 项目根（含 scripts/ 与 docs/trial/）。
# ⚠ 文件深度一变必须重钉（见 P1 搬迁教训），故有单测断言它仍解析到含 scripts/ 的目录。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPORT_KIND = "qualification_report/v1"
ANCHOR_KIND = "qualification_report_anchor/v1"


class QualificationLoadError(ValueError):
    """输入字节/绑定不可信 → fail-closed（内容寻址只证「是什么」，绑定才证「来自获批的那次运行」）。"""


def _file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load_json(path: str, label: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise QualificationLoadError(f"无法读取{label} {path}：{exc}") from exc


def _jsonable(obj: Any) -> Any:
    """派生器输出里有 set（provenance.fingerprints）→ 转排序 list，使 report 可内容寻址。"""
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(_jsonable(v) for v in obj if v is not None)
    return obj


def deriver_sha256() -> str:
    """**实际被 import 的**那份 `qualification.py` 的字节哈希。

    刻意不按路径去 repo 里另读一份：报告是这份模块实例算出来的，锚就必须锚它本身
    （核产物本身、不从同名权威路径推断）。授权门那边把同一路径列进受管辖材料并三方哈希，
    两侧对上即闭合。
    """
    return _file_sha256(os.path.abspath(q.__file__))


def normalize_manifest(manifest: dict) -> dict:
    """campaign manifest 的 windows 键在 JSON 里是字符串，派生器按 int 索引 → 归一。"""
    out = dict(manifest or {})
    raw = out.get("windows")
    if isinstance(raw, dict):
        keyed = {}
        for key, val in raw.items():
            try:
                keyed[int(key)] = val
            except (TypeError, ValueError) as exc:
                raise QualificationLoadError(f"manifest.windows 键非整数：{key!r}") from exc
        out["windows"] = keyed
    return out


def load_window(index: int, artifact_path: str, receipt_path: str, request_path: str,
                repo_root: Optional[str] = None) -> tuple[dict, dict]:
    """读一个窗口的三份文件 + 按授权引用取回前缀门；返回 (派生器窗口 dict, 输入哈希 dict)。

    fail-closed 的字节绑定（派生器是纯函数、拿不到原始字节，故必须在这一层做）：
    artifact 字节 SHA == receipt 记录值；request 文件自洽（`_sha(request) == execution_request_hash`）；
    receipt 与 artifact.meta 的 request hash / request_commit / approval_commit 一致；
    receipt 回显的 deriver 哈希 == 当前派生器字节。
    """
    repo_root = repo_root or _PROJECT_ROOT
    artifact = _load_json(artifact_path, "artifact")
    receipt = _load_json(receipt_path, "receipt")
    req_doc = _load_json(request_path, "execution request")
    request = req_doc.get("request")
    if not isinstance(request, dict):
        raise QualificationLoadError(f"execution request {request_path} 缺 request 对象")

    artifact_sha = _file_sha256(artifact_path)
    receipt_sha = _file_sha256(receipt_path)
    request_sha = _file_sha256(request_path)
    meta = artifact.get("meta") or {}
    request_hash = _sha(request)
    checks = {
        "artifact_sha_matches_receipt": artifact_sha == receipt.get("artifact_sha256"),
        "request_file_self_consistent": req_doc.get("execution_request_hash") == request_hash,
        "receipt_request_hash_consistent": receipt.get("execution_request_hash") == request_hash,
        "artifact_request_hash_consistent": meta.get("execution_request_hash") == request_hash,
        "request_commit_consistent": meta.get("request_commit") == receipt.get("request_commit"),
        "approval_commit_consistent": meta.get("approval_commit") == receipt.get("approval_commit"),
    }
    broken = [k for k, ok in checks.items() if not ok]
    if broken:
        raise QualificationLoadError(
            f"窗口 {index} 的 artifact/receipt/request 绑定不一致（fail-closed）：{', '.join(broken)}")

    echo = receipt.get("qualification_campaign")
    if not isinstance(echo, dict):
        raise QualificationLoadError(
            f"窗口 {index} 的 receipt 无 qualification_campaign 回显 —— 它不是本 campaign 的授权窗口")
    declared_deriver = (echo.get("deriver") or {}).get("sha256")
    current_deriver = deriver_sha256()
    if declared_deriver != current_deriver:
        raise QualificationLoadError(
            f"窗口 {index} 授权时冻结的派生器 {str(declared_deriver)[:8]} 与当前派生器 "
            f"{current_deriver[:8]} 不是同一份 —— 拒绝用另一版派生器出资格结论")

    gate = None
    gate_sha = None
    if index >= 2:
        ref = (request.get("qualification_campaign") or {}).get("prefix_gate_record")
        if not isinstance(ref, dict) or not ref.get("path") or not ref.get("sha256"):
            raise QualificationLoadError(f"窗口 {index} 的 request 未绑定 prefix_gate_record 引用")
        gate_path = os.path.join(repo_root, ref["path"])
        gate_sha = _file_sha256(gate_path)
        if gate_sha != ref["sha256"]:
            raise QualificationLoadError(
                f"窗口 {index} 的 prefix_gate_record 字节与授权时声明不符"
                f"（当前 {gate_sha[:8]} / 声明 {str(ref['sha256'])[:8]}）")
        gate = _load_json(gate_path, "prefix_gate_record")

    window = {"index": index, "artifact": artifact, "receipt": receipt, "request": request,
              "prefix_gate_record": gate}
    hashes = {"artifact_sha256": artifact_sha, "receipt_sha256": receipt_sha,
              "request_sha256": request_sha, "execution_request_hash": request_hash,
              "prefix_gate_sha256": gate_sha}
    return window, hashes


def derive_campaign(manifest_path: str, window_specs, closure_path: Optional[str] = None,
                    repo_root: Optional[str] = None) -> dict:
    """读全部输入 → 调派生器 → 组装 report（未写盘）。window_specs = [(index, art, rec, req), ...]。"""
    repo_root = repo_root or _PROJECT_ROOT
    manifest = normalize_manifest(_load_json(manifest_path, "campaign manifest"))
    windows, inputs = [], {}
    for index, art_p, rec_p, req_p in window_specs:
        window, hashes = load_window(index, art_p, rec_p, req_p, repo_root=repo_root)
        windows.append(window)
        inputs[str(index)] = {**hashes, "artifact_path": art_p, "receipt_path": rec_p,
                              "request_path": req_p}
    closure = _load_json(closure_path, "campaign closure record") if closure_path else None
    try:
        result = q.derive_qualification(manifest, windows, closure_record=closure)
    except q.QualificationInputError as exc:
        # 畸形输入形态（中间缺口 / terminal 后运行 / 非终止窗口非 c2_pass / deadline 缺 closure）
        # 一律 fail-closed：不产 verdict，比产一个说不清的 verdict 安全。
        raise QualificationLoadError(f"派生器拒绝该输入形态（fail-closed）：{exc}") from exc
    return {
        "kind": REPORT_KIND,
        "campaign_id": manifest.get("campaign_id"),
        "rule_version": q.RULE_VERSION,
        "deriver_sha256": deriver_sha256(),
        "manifest_path": manifest_path,
        "manifest_sha256": _file_sha256(manifest_path),
        "closure_record_path": closure_path,
        "closure_record_sha256": _file_sha256(closure_path) if closure_path else None,
        "window_inputs": inputs,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "result": _jsonable(result),
    }


def build_prefix_gate_record(report: dict) -> dict:
    """in_progress 时产出下一窗口 Hat A 要绑的 committed 前缀门；终局状态**拒绝**产出。

    字段形状由授权门 `execution_authorization._verify_prefix_gate_record` 钉死（改这里必须同时改那里，
    两侧各有测试）。
    """
    result = report["result"]
    status = result.get("campaign_status")
    if status != "in_progress" or result.get("next_window_authorizable") is not True:
        raise QualificationLoadError(
            f"campaign_status={status!r} 非 in_progress 或不可授权 —— 拒绝产出前缀门"
            "（预注册提前停止：终局后不应再花钱跑后续窗口）")
    covers = sorted(int(i) for i in report["window_inputs"])
    return {
        "kind": "prefix_gate_record/v1",
        "campaign_id": report["campaign_id"],
        "rule_version": report["rule_version"],
        "deriver_sha256": report["deriver_sha256"],
        "campaign_status": status,
        "next_window_authorizable": True,
        "covers": covers,
        "window_inputs": {str(i): {"artifact_sha256": report["window_inputs"][str(i)]["artifact_sha256"],
                                   "receipt_sha256": report["window_inputs"][str(i)]["receipt_sha256"]}
                          for i in covers},
        "report_sha256": report.get("report_sha256"),
        "generated_at_utc": report["generated_at_utc"],
    }


def build_anchor(report: dict, report_path: str, report_sha256: str) -> dict:
    """committed 审计锚（§9 P1-6）：report 数据不入 git，verdict 仍有 committed 内容寻址锚。"""
    result = report["result"]
    return {
        "kind": ANCHOR_KIND,
        "campaign_id": report["campaign_id"],
        "rule_version": report["rule_version"],
        "deriver_sha256": report["deriver_sha256"],
        "campaign_status": result.get("campaign_status"),
        "verdict": result.get("verdict"),
        "next_window_authorizable": result.get("next_window_authorizable"),
        "windows_covered": sorted(int(i) for i in report["window_inputs"]),
        "window_statuses": {str(w.get("index")): w.get("status") for w in result.get("windows") or []},
        "report_path": report_path,
        "report_sha256": report_sha256,
        "manifest_sha256": report["manifest_sha256"],
        "closure_record_sha256": report["closure_record_sha256"],
        "window_inputs": {k: {kk: vv for kk, vv in v.items() if kk.endswith("sha256")
                              or kk == "execution_request_hash"}
                          for k, v in report["window_inputs"].items()},
        "generated_at_utc": report["generated_at_utc"],
        "boundary": ("instrument qualification only；不是 target Finding、不是合规 Claim；"
                     "assurance_level 仍 none"),
    }


def _write_json(path: str, obj: dict) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    blob = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(blob)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _parse_window(values):
    idx, art, rec, req = values
    try:
        index = int(idx)
    except ValueError as exc:
        raise QualificationLoadError(f"window index 非整数：{idx!r}") from exc
    return index, art, rec, req


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="instrument qualification：窗口输入 → 派生器 → report + 审计锚 + 前缀门")
    ap.add_argument("--manifest", required=True, help="campaign manifest JSON（Hat A 预声明）")
    ap.add_argument("--window", nargs=4, action="append", default=[],
                    metavar=("INDEX", "ARTIFACT", "RECEIPT", "REQUEST"),
                    help="一个窗口的四元组，可重复（须是 1..j 连续前缀）")
    ap.add_argument("--closure", help="campaign closure record（deadline 形态用）")
    ap.add_argument("-o", "--output", default="reports/qualification_report.json")
    ap.add_argument("--emit-anchor", help="committed 审计锚输出路径")
    ap.add_argument("--emit-gate", help="committed prefix_gate_record 输出路径（仅 in_progress）")
    ap.add_argument("--repo-root", default=_PROJECT_ROOT)
    args = ap.parse_args(argv)

    try:
        specs = [_parse_window(v) for v in args.window]
        report = derive_campaign(args.manifest, specs, closure_path=args.closure,
                                 repo_root=args.repo_root)
        report_sha = _write_json(args.output, report)
        report["report_sha256"] = report_sha
        if args.emit_anchor:
            _write_json(args.emit_anchor, build_anchor(report, args.output, report_sha))
    except QualificationLoadError as exc:
        print(f"[qualification] 输入不可信，拒绝派生：{exc}", file=sys.stderr)
        return 4

    gate_written = False
    if args.emit_gate:
        # 终局状态下拒发前缀门是**正常结果**、不是派生失败：report 与审计锚照常产出，只是没有
        # 下一窗口的授权前置。故不吞掉终局退出码、也不把它降级成输入错误。
        try:
            _write_json(args.emit_gate, build_prefix_gate_record(report))
            gate_written = True
        except QualificationLoadError as exc:
            print(f"[qualification] 未产出前缀门：{exc}", file=sys.stderr)

    result = report["result"]
    status, verdict = result.get("campaign_status"), result.get("verdict")
    print(f"[qualification] campaign={report['campaign_id']} windows={len(args.window)} → {args.output}")
    print(f"  campaign_status={status} verdict={verdict} "
          f"next_window_authorizable={result.get('next_window_authorizable')}")
    for win in result.get("windows") or []:
        print(f"  window {win.get('index')}: {win.get('status')}"
              + (f" — {win.get('reason')}" if win.get("reason") else ""))
    if args.emit_anchor:
        print(f"  审计锚 → {args.emit_anchor}（report_sha256={report_sha[:12]}…）")
    if gate_written:
        print(f"  前缀门 → {args.emit_gate}（下一窗口 Hat A 须绑定其哈希）")
    # 终局 ≠ 派生失败：报告已产出，但操作上「不应再花钱跑后续窗口」，故用非零码让脚本/人看见。
    return 0 if status in ("in_progress", "full_qualified") else 6


if __name__ == "__main__":
    sys.exit(main())
