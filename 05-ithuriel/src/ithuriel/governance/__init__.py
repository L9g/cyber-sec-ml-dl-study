"""Ithuriel 开发期治理信任核（ADR-0022 一人两帽）。

执行授权链（Hat A 冻结 request → Hat B 独立 commit approval → 机器验证 → receipt）、
git 顺序锚、三方哈希 fail-closed、逐 trial deadline 从 `scripts/run_calendar_probe.py`
搬入此处（P1，见 reports/partner-review-2026-07-22-codex.md）。CLI 编排仍留 `scripts/`。
"""
