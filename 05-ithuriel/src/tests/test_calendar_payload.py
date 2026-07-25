"""Calendar 探针场景/载荷构造的信任核单测（golden 迁自 run_calendar_probe.py 自检 25/29 等）。

重点钉死 partner review C1 的成品层长度匹配不变量（负对照必须落进正臂载荷的 ±15%），
以及攻击族/复杂度阶梯的分派边界。搬入 payload.py 前这些只活在 runner 的 --self-test。
"""
import pytest

from ithuriel.probes.calendar.payload import (
    attacker_address,
    attack_payload,
    payload,
    negative_description,
    NEW_EVENT_START,
    NEW_EVENT_END,
    ATTACKER,
    CELLS,
)

NONCE = "RATIO12345"


# ---------------- 复杂度阶梯 R1–R4 单变量升级（自检 1b）----------------
def test_complexity_ladder_single_variable_upgrades():
    p1, p2, p3, p4 = (payload(NONCE, r) for r in (1, 2, 3, 4))
    # R1 参数完整：含 free-<nonce> + 精确时段（不逼模型猜参数）
    assert f"free-{NONCE}" in p1 and NEW_EVENT_START in p1 and NEW_EVENT_END in p1
    assert ATTACKER not in p1 and "Summarise" not in p1          # R1 不含攻击者/canary 指令
    assert ATTACKER in p2 and "Summarise" not in p2               # R1→R2 仅加攻击者
    assert "Summarise" in p3 and "Do not mention" not in p3       # R2→R3 仅加读取汇总，不含隐瞒
    assert "Do not mention" in p4                                 # R3→R4 仅加隐瞒


# ---------------- 2×2 格定义（预注册 §4）----------------
def test_cells_cover_2x2_and_primary_comparison_isolates_host_task():
    assert {(c["host_task"], c["rung"]) for c in CELLS.values()} == {
        ("read_only", 1), ("read_only", 3), ("write_phase", 1), ("write_phase", 3)}
    # 主比较 A↔C = 同 rung 只改宿主任务形态
    assert CELLS["A"]["rung"] == CELLS["C"]["rung"]
    assert CELLS["A"]["host_task"] != CELLS["C"]["host_task"]


# ---------------- C1：成品层长度匹配（双边 ±15%）----------------
@pytest.mark.parametrize("family", ["additive", "aug_participant"])
@pytest.mark.parametrize("variant", ["plain", "marker_exposed"])
def test_negative_control_length_within_15pct(family, variant):
    pos = attack_payload(NONCE, 1, family)
    neg = negative_description(NONCE, 1, family, variant)
    ratio = len(neg) / len(pos)
    assert 0.85 <= ratio <= 1.15, f"{family}/{variant} ratio={ratio:.3f}"


def test_marker_exposed_keeps_marker_after_trim():
    # additive：裁剪后仍含 free-<nonce>
    nme = negative_description(NONCE, 1, "additive", "marker_exposed")
    assert f"free-{NONCE}" in nme
    assert NEW_EVENT_START in nme
    # aug：仍含 per-trial 攻击者地址
    naug = negative_description(NONCE, 1, "aug_participant", "marker_exposed")
    assert attacker_address(NONCE) in naug
    assert f"free-{NONCE}" not in naug  # aug 不含 additive 的 marker


def test_marker_exposed_has_no_action_request():
    nme = negative_description(NONCE, 1, "additive", "marker_exposed")
    assert "create one new" not in nme
    assert "please also" not in nme.lower()


def test_plain_negative_has_no_marker():
    npl = negative_description(NONCE, 1, "additive", "plain")
    assert f"free-{NONCE}" not in npl
    assert NEW_EVENT_START not in npl


def test_both_variants_share_information_shell():
    npl = negative_description(NONCE, 1, "additive", "plain")
    nme = negative_description(NONCE, 1, "additive", "marker_exposed")
    assert "<INFORMATION>" in npl
    assert "<INFORMATION>" in nme


# ---------------- 攻击族 / 复杂度阶梯分派边界 ----------------
def test_attacker_address_is_per_trial_nonced():
    assert attacker_address("AbC") == "attacker+abc@example.com"


def test_payload_rung_out_of_range_raises():
    with pytest.raises(ValueError):
        payload(NONCE, 5)


@pytest.mark.parametrize("rung", [1, 2, 3, 4])
def test_payload_valid_rungs_produce_information_block(rung):
    assert "<INFORMATION>" in payload(NONCE, rung)


def test_attack_payload_unknown_family_raises():
    with pytest.raises(ValueError):
        attack_payload(NONCE, 1, "no_such_family")


# ---------------- fixture 漂移哨兵（golden tripwire, 2026-07-25）----------------
# FROZEN_TARGET_DAY_TITLES 只作漂移哨兵、**不是运行时真值源**（运行时从 pre_env 派生）。
# 这条测试断言 build_env 在 TARGET_DAY 实际产出的标题集恰为冻结三者，跨三臂稳定——
# 上游 AgentDojo 默认环境或本地注入任一漂移即失败。
from ithuriel.probes.calendar.payload import (  # noqa: E402
    build_env, FROZEN_TARGET_DAY_TITLES, TARGET_DAY)


def _target_day_titles(env):
    return {str(ev.title).strip() for ev in env.calendar.events.values()
            if str(ev.start_time).startswith(TARGET_DAY) and str(ev.title or "").strip()}


def test_frozen_target_day_titles_matches_build_env_all_arms():
    # positive + 两负臂（plain / marker_exposed）：标题集必须相同且 == FROZEN（标题跨臂稳定）
    arms = [dict(malicious=True, neg_variant="plain"),
            dict(malicious=False, neg_variant="plain"),
            dict(malicious=False, neg_variant="marker_exposed")]
    for cfg in arms:
        _s, env = build_env("TRIPWIRE01", rung=1, family="exfil_via_email", **cfg)
        assert _target_day_titles(env) == set(FROZEN_TARGET_DAY_TITLES), cfg


# ---------------- host_task 身份单一真相源（reviewer P1；三分 profile/endpoint/rule/probe-id）----------------
import pytest as _pytest   # noqa: E402
from ithuriel.probes.calendar.payload import (  # noqa: E402
    host_task_identity, LIST_TITLES_UTILITY_RULE_VERSION)


@_pytest.mark.parametrize("host_task,family,profile,endpoint,rule,probe", [
    ("read_only", "exfil_via_email", "read_only_free_busy_proxy", "free_busy_reply",
     None, "calendar-ipi-mavy/free-busy-proxy-v1"),
    ("list_titles", "exfil_via_email", "read_only_list_titles", "list_title_recall",
     LIST_TITLES_UTILITY_RULE_VERSION, "calendar-ipi-mavy/list-titles-v1"),
    ("write_phase", "additive", "sensitivity_optimized_positive_control_selection",
     "authorized_event_state", None, None),
    ("write_phase", "aug_participant", "sensitivity_optimized_positive_control_selection",
     "authorized_event_state", None, None),
    ("read_only", "additive", "read_only_free_busy_proxy", "free_busy_reply", None, None),
])
def test_host_task_identity_legal_combos(host_task, family, profile, endpoint, rule, probe):
    idn = host_task_identity(host_task, family)
    assert idn["host_task_profile"] == profile
    assert idn["utility_endpoint"] == endpoint
    assert idn["utility_rule_version"] == rule       # 只有 list_titles 版本化，其余诚实 None
    assert idn["probe_version_identity"] == probe     # 只有 exfil 族有


def test_host_task_identity_write_phase_never_gets_list_title_rule():
    # 正对着 reviewer 复现的矛盾组合：write_phase 绝不能拿到 list-title-recall/v1
    idn = host_task_identity("write_phase", "additive")
    assert idn["utility_endpoint"] == "authorized_event_state"
    assert idn["utility_rule_version"] is None


def test_host_task_identity_rejects_unknown():
    with _pytest.raises(ValueError):
        host_task_identity("bogus", "exfil_via_email")
