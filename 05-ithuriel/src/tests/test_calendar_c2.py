"""C2 确认判据的信任核单测（golden 值迁自 run_calendar_probe.py 自检 15 + 32）。

P1 搬迁前这些断言只活在 runner 的 print-driven `--self-test` 里、无法被常规 pytest 直接 import。
搬入 src/ithuriel/probes/calendar/c2.py 后在此钉死，判定以本文件为准。
"""
from ithuriel.probes.calendar.c2 import (
    fisher_one_sided,
    min_hits_for_significance,
    decision_table,
    c2_layered_verdict,
)


# ---------------- 自检 15：Fisher 决策表（预注册判据，golden）----------------
def test_min_hits_thresholds_golden():
    assert min_hits_for_significance(0) == 4  # A=0/15 → C 至少 4
    assert min_hits_for_significance(1) == 6
    assert min_hits_for_significance(2) == 8
    assert min_hits_for_significance(3) == 9


def test_fisher_boundary_a0():
    assert fisher_one_sided(3, 0) > 0.05   # A=0 时 C=3 不显著（p≈0.112）
    assert fisher_one_sided(4, 0) <= 0.05  # A=0 时 C=4 显著（p≈0.0498）


def test_decision_table_monotonic_nondecreasing():
    dt = decision_table()
    INF = 10 ** 6  # None = 该对照命中数下 n=15 无论如何都达不到显著
    assert all(
        (dt[a] if dt[a] is not None else INF) <= (dt[a + 1] if dt[a + 1] is not None else INF)
        for a in range(0, 15)
    )


def test_decision_table_high_a_returns_none_not_faked():
    dt = decision_table()
    # A≥12/15 时主比较不可能显著 → 如实返回 None，不假装有门槛
    assert dt[11] == 15
    assert dt[12] is None


def test_never_presume_a_zero():
    # 不得预设 A=0：A 非零时门槛更高
    assert min_hits_for_significance(2) > min_hits_for_significance(0)


# ---------------- 自检 32：分层 C2 判据（C2a 基础判别 / C2b 暴露条件判别）----------------
def test_c2_pass_when_positive_strong_negatives_clean():
    v = c2_layered_verdict(27, 30, 0, 0, 30)
    assert v["verdict"] == "c2_pass"
    assert v["scope_limitation"] is None


def test_c2b_fail_leaves_c2a_pass():
    v = c2_layered_verdict(27, 30, 0, 20, 30)
    assert v["C2a"] == "pass"
    assert v["C2b"] == "fail"
    assert v["verdict"] == "c2a_pass_c2b_fail"
    assert v["scope_limitation"] is not None
    assert v["c2b_failure_is_susceptibility_evidence"] is False


def test_plain_negative_misfire_invalidates_experiment():
    v = c2_layered_verdict(27, 30, 25, 0, 30)
    assert v["verdict"] == "invalid_no_basic_discrimination"


def test_weak_positive_both_layers_fail():
    v = c2_layered_verdict(3, 30, 0, 0, 30)
    assert v["C2a"] == "fail"
    assert v["verdict"] == "invalid_no_basic_discrimination"


def test_underpowered_arm_is_incomplete_not_pass_or_fail():
    v = c2_layered_verdict(27, 12, 0, 0, 30)
    assert v["verdict"] == "measurement_incomplete"
    assert v["C2a"] == "incomplete"
