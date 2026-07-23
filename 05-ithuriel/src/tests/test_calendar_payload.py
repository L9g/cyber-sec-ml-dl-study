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
)

NONCE = "RATIO12345"


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
