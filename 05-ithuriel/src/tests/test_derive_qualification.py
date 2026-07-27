"""qualification loader glue 的契约测试（全离线：真文件字节 + 真派生器，无 git、无模型、无计费）。

loader 负责的正是纯函数派生器**拿不到**的那层：文件字节 SHA、artifact↔receipt↔request 绑定、
按授权引用取回 prefix_gate_record、三件产物。故这里必须写真文件，不能 mock 掉 I/O。
判定逻辑的 golden 在 test_calendar_qualification.py（单一真相源），本文件只测字节层与产物形状。
"""
import copy
import json
import os

import pytest

from ithuriel import derive_qualification as DQ
from ithuriel.probes.calendar import qualification as q
from ithuriel.probes.calendar.oracle import _sha

from test_calendar_qualification import make_window, make_manifest, CAMPAIGN_ID

GATE_REL = "docs/trial/qualification/prefix-gate.json"


def _dump(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return path


def write_window(root, index, *, gate_rel=None, camp_over=None, art_sha_override=None,
                 request_hash_override=None, deriver_sha_override=None, suffix="", **win_kw):
    """把一个 golden 窗口落成三份真文件（哈希彼此闭合）。返回 (index, art_p, rec_p, req_p)。"""
    w = make_window(index, camp_over=camp_over, **win_kw)
    art, rec, req = w["artifact"], w["receipt"], w["request"]

    if index >= 2:
        req["qualification_campaign"] = {"prefix_gate_record": {
            "path": gate_rel, "sha256": DQ._file_sha256(os.path.join(root, gate_rel))}}
    request_hash = request_hash_override or _sha(req)
    camp = copy.deepcopy(rec["qualification_campaign"])
    camp["deriver"] = {"path": "src/ithuriel/probes/calendar/qualification.py",
                       "sha256": deriver_sha_override or DQ.deriver_sha256()}
    art["meta"]["qualification_campaign"] = copy.deepcopy(camp)
    rec["qualification_campaign"] = copy.deepcopy(camp)
    art["meta"].update(execution_request_hash=request_hash, request_commit="c1",
                       approval_commit="c2")
    rec.update(execution_request_hash=request_hash, request_commit="c1", approval_commit="c2")

    art_p = _dump(os.path.join(root, f"results/artifact-w{index}{suffix}.json"), art)
    rec["artifact_sha256"] = art_sha_override or DQ._file_sha256(art_p)
    rec_p = _dump(os.path.join(root, f"docs/trial/receipts/w{index}{suffix}.receipt.json"), rec)
    req_p = _dump(os.path.join(root, f"docs/trial/execution-request-w{index}{suffix}.json"),
                  {"request": req, "execution_request_hash": request_hash})
    return index, art_p, rec_p, req_p


def write_manifest(root):
    return _dump(os.path.join(root, "docs/trial/qualification/campaign.manifest.json"),
                 {**make_manifest(), "windows": {str(i): v
                                                 for i, v in make_manifest()["windows"].items()}})


def _run(root, specs, *, emit_gate=True, extra=()):
    argv = ["--manifest", write_manifest(root), "--repo-root", root,
            "-o", os.path.join(root, "reports/qualification_report.json"),
            "--emit-anchor", os.path.join(root, "docs/trial/qualification/anchor.json")]
    for index, art_p, rec_p, req_p in specs:
        argv += ["--window", str(index), art_p, rec_p, req_p]
    if emit_gate:
        argv += ["--emit-gate", os.path.join(root, GATE_REL)]
    argv += list(extra)
    return DQ.main(argv)


def _read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return json.load(f)


# ---------------- 路径锚（文件深度一变必须重钉）----------------
def test_project_root_still_points_at_repo_root():
    assert os.path.isfile(os.path.join(DQ._PROJECT_ROOT, "scripts", "run_calendar_probe.py"))


def test_deriver_sha_is_of_the_imported_module_bytes():
    assert DQ.deriver_sha256() == DQ._file_sha256(os.path.abspath(q.__file__))


# ---------------- 正路：窗口 1 → in_progress + 三件产物 ----------------
def test_window1_in_progress_emits_report_anchor_and_gate(tmp_path):
    root = str(tmp_path)
    rc = _run(root, [write_window(root, 1)])
    assert rc == 0
    report = _read(root, "reports/qualification_report.json")
    anchor = _read(root, "docs/trial/qualification/anchor.json")
    gate = _read(root, GATE_REL)
    assert report["result"]["campaign_status"] == "in_progress"
    assert report["result"]["verdict"] is None
    # 审计锚的 report_sha256 必须就是 report 文件字节的哈希（内容寻址锚，不是自说自话）
    assert anchor["report_sha256"] == DQ._file_sha256(
        os.path.join(root, "reports/qualification_report.json"))
    assert anchor["campaign_id"] == CAMPAIGN_ID and anchor["verdict"] is None
    assert anchor["windows_covered"] == [1] and anchor["window_statuses"] == {"1": q.VALID_C2_PASS}
    # 前缀门 = 授权门要的那套字段
    assert gate["covers"] == [1] and gate["next_window_authorizable"] is True
    assert gate["campaign_status"] == "in_progress" and gate["campaign_id"] == CAMPAIGN_ID
    assert gate["deriver_sha256"] == DQ.deriver_sha256()
    assert set(gate["window_inputs"]["1"]) == {"artifact_sha256", "receipt_sha256"}


def test_report_is_json_serialisable_no_sets(tmp_path):
    # 派生器 provenance 带 set（fingerprints）→ 必须转排序 list，否则 report 写不出、也无法内容寻址。
    root = str(tmp_path)
    assert _run(root, [write_window(root, 1)]) == 0
    prov = _read(root, "reports/qualification_report.json")["result"]["windows"][0]["provenance"]
    assert prov["fingerprints"] == ["fp_a"] and prov["fingerprint_scope"] == "observed_fingerprint"


# ---------------- 端到端：窗口 1 产出的前缀门被窗口 2 绑定 ----------------
def test_window2_binds_gate_emitted_by_window1(tmp_path):
    root = str(tmp_path)
    w1 = write_window(root, 1)
    assert _run(root, [w1]) == 0                       # 产出 GATE_REL
    w2 = write_window(root, 2, gate_rel=GATE_REL)      # 窗口 2 的 request 绑定它的字节哈希
    assert _run(root, [w1, w2]) == 0
    report = _read(root, "reports/qualification_report.json")
    assert report["result"]["campaign_status"] == "in_progress"
    assert [w["status"] for w in report["result"]["windows"]] == [q.VALID_C2_PASS] * 2
    assert _read(root, GATE_REL)["covers"] == [1, 2]   # 门已推进到覆盖 1..2


def test_gate_bytes_diverging_from_declaration_fails_closed(tmp_path):
    root = str(tmp_path)
    w1 = write_window(root, 1)
    assert _run(root, [w1]) == 0
    w2 = write_window(root, 2, gate_rel=GATE_REL)
    # 窗口 2 冻结引用之后前缀门被改（哪怕内容仍"合法"）→ 拒绝派生
    gate = _read(root, GATE_REL)
    gate["covers"] = [1]
    _dump(os.path.join(root, GATE_REL), {**gate, "note": "tampered"})
    assert _run(root, [w1, w2]) == 4


# ---------------- 字节绑定 fail-closed ----------------
def test_artifact_sha_mismatch_fails_closed(tmp_path):
    root = str(tmp_path)
    assert _run(root, [write_window(root, 1, art_sha_override="0" * 64)]) == 4


def test_request_hash_mismatch_fails_closed(tmp_path):
    root = str(tmp_path)
    assert _run(root, [write_window(root, 1, request_hash_override="1" * 64)]) == 4


def test_deriver_identity_mismatch_fails_closed(tmp_path):
    # 授权时冻结的派生器 ≠ 当前这份 → 拒绝用另一版派生器出资格结论。
    root = str(tmp_path)
    assert _run(root, [write_window(root, 1, deriver_sha_override="2" * 64)]) == 4


def test_missing_campaign_echo_fails_closed(tmp_path):
    root = str(tmp_path)
    index, art_p, rec_p, req_p = write_window(root, 1)
    rec = _read(root, "docs/trial/receipts/w1.receipt.json")
    del rec["qualification_campaign"]
    _dump(rec_p, rec)
    # receipt 改了 → artifact sha 仍对得上，但回显没了 → 不是本 campaign 的授权窗口
    assert _run(root, [(index, art_p, rec_p, req_p)]) == 4


def test_malformed_prefix_shape_fails_closed(tmp_path):
    # 中间缺口（1,3）→ 派生器拒绝出 verdict，loader 转成 exit 4，不产半吊子报告。
    root = str(tmp_path)
    w1 = write_window(root, 1)
    assert _run(root, [w1]) == 0
    w3 = write_window(root, 3, gate_rel=GATE_REL)
    assert _run(root, [w1, w3]) == 4


# ---------------- 终局：报告照出，前缀门拒发 ----------------
def test_terminal_not_qualified_refuses_gate_and_exits_6(tmp_path):
    root = str(tmp_path)
    rc = _run(root, [write_window(root, 1, pos=7)])       # 正臂 7/30 → 有效窗口 C2-fail
    assert rc == 6
    report = _read(root, "reports/qualification_report.json")
    assert report["result"]["campaign_status"] == "terminal_not_qualified"
    assert report["result"]["verdict"] == "not_qualified_discrimination"
    assert _read(root, "docs/trial/qualification/anchor.json")["verdict"] == "not_qualified_discrimination"
    assert not os.path.exists(os.path.join(root, GATE_REL))   # 终局后不得再授权下一窗口


def test_terminal_inconclusive_refuses_gate(tmp_path):
    root = str(tmp_path)
    rc = _run(root, [write_window(root, 1, instrument_errors=4)])   # 每臂 4 > 上限 3
    assert rc == 6
    assert _read(root, "reports/qualification_report.json")["result"]["verdict"] == "inconclusive"
    assert not os.path.exists(os.path.join(root, GATE_REL))


def test_build_prefix_gate_record_refuses_terminal_report():
    with pytest.raises(DQ.QualificationLoadError, match="拒绝产出前缀门"):
        DQ.build_prefix_gate_record({"result": {"campaign_status": "full_qualified",
                                                "next_window_authorizable": False},
                                     "window_inputs": {}, "campaign_id": "c",
                                     "rule_version": q.RULE_VERSION, "deriver_sha256": "x",
                                     "generated_at_utc": "2026-08-01T00:00:00+00:00"})


# ---------------- deadline 形态（0 artifact + committed closure record）----------------
def test_deadline_inconclusive_from_closure_record(tmp_path):
    root = str(tmp_path)
    closure = _dump(os.path.join(root, "docs/trial/qualification/closure.json"),
                    {"campaign_id": CAMPAIGN_ID, "closed_at_utc": "2026-08-15T01:00:00+00:00",
                     "campaign_deadline_utc": "2026-08-15T00:00:00+00:00",
                     "slots": {"1": "not_started", "2": "not_started", "3": "not_started"}})
    rc = _run(root, [], extra=["--closure", closure])
    assert rc == 6
    report = _read(root, "reports/qualification_report.json")
    assert report["result"]["campaign_status"] == "deadline_inconclusive"
    assert report["closure_record_sha256"] == DQ._file_sha256(closure)
    assert not os.path.exists(os.path.join(root, GATE_REL))


# ---------------- 自我对抗性复核补的门（发现 ②③；发现 ① 在 test_governance_authorization.py）----------------
def test_gate_bound_to_rerun_window_is_rejected(tmp_path):
    # ⭐ 发现 ②：窗口 1 被**重跑**（新 artifact 字节）后拿旧前缀门配新 artifact —— 授权门在 Hat A 时
    # 验不了这个（artifact 不入 git），必须在派生的字节层闭合，否则「先验前缀」被架空。
    root = str(tmp_path)
    w1 = write_window(root, 1)
    assert _run(root, [w1]) == 0                        # 门绑的是这一版 artifact
    w2 = write_window(root, 2, gate_rel=GATE_REL)
    w1_rerun = write_window(root, 1, pos=27, suffix="-rerun")   # 重跑：仍 c2_pass，但字节变了
    assert _run(root, [w1_rerun, w2]) == 4
    assert _run(root, [w1, w2]) == 0                    # 用门实际覆盖的那批仍然通过


def test_gate_from_other_campaign_rejected(tmp_path):
    root = str(tmp_path)
    w1 = write_window(root, 1)
    assert _run(root, [w1]) == 0
    w2 = write_window(root, 2, gate_rel=GATE_REL)
    gate = _read(root, GATE_REL)
    gate["campaign_id"] = "other-campaign"
    _dump(os.path.join(root, GATE_REL), gate)
    # 门被改 → 先撞字节门；把 request 的声明也改成新字节，才测到 campaign 归属这一层
    req_p = os.path.join(root, "docs/trial/execution-request-w2.json")
    doc = _read(root, "docs/trial/execution-request-w2.json")
    doc["request"]["qualification_campaign"]["prefix_gate_record"]["sha256"] = \
        DQ._file_sha256(os.path.join(root, GATE_REL))
    doc["execution_request_hash"] = _sha(doc["request"])
    _dump(req_p, doc)
    rec = _read(root, "docs/trial/receipts/w2.receipt.json")
    rec["execution_request_hash"] = doc["execution_request_hash"]
    _dump(os.path.join(root, "docs/trial/receipts/w2.receipt.json"), rec)
    art = _read(root, "results/artifact-w2.json")
    art["meta"]["execution_request_hash"] = doc["execution_request_hash"]
    art_p = _dump(os.path.join(root, "results/artifact-w2.json"), art)
    rec["artifact_sha256"] = DQ._file_sha256(art_p)
    rec_p = _dump(os.path.join(root, "docs/trial/receipts/w2.receipt.json"), rec)
    assert _run(root, [w1, (2, art_p, rec_p, req_p)]) == 4


def test_missing_fingerprint_is_preserved_not_silently_dropped(tmp_path):
    # ⭐ 发现 ③：「某 turn 没报 fingerprint」正是收窄到 pinned-route 观测重复性的依据，
    # 序列化时不得静默丢掉 None。
    root = str(tmp_path)
    assert _run(root, [write_window(root, 1, fps=("fp_a", None))]) == 0
    prov = _read(root, "reports/qualification_report.json")["result"]["windows"][0]["provenance"]
    assert prov["fingerprints"] == ["fp_a", None]
    assert prov["fingerprint_scope"] == "pinned_route_repeatability"


def test_core_hash_is_reproducible_while_file_hash_is_not(tmp_path):
    # ⭐ 发现 ④：report_sha256 含 generated_at_utc 与本机路径 → 审计员重算必不同；core_sha256
    # 只含 rule/deriver 身份 + 输入哈希 + 判定结果，同输入同派生器必然相同（可「重算比对」）。
    root = str(tmp_path)
    w1 = write_window(root, 1)
    assert _run(root, [w1]) == 0
    first = _read(root, "docs/trial/qualification/anchor.json")
    assert _run(root, [w1]) == 0
    second = _read(root, "docs/trial/qualification/anchor.json")
    assert first["core_sha256"] == second["core_sha256"]
    assert first["report_sha256"] != second["report_sha256"]      # 时刻不同 → 文件哈希不同
    assert second["core_sha256"] == DQ.core_sha256(
        _read(root, "reports/qualification_report.json"))
