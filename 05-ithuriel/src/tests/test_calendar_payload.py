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
