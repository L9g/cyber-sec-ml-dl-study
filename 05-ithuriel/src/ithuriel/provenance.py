"""provenance 捕获（档 2，ADR-0007）——薄适配器把真跑溯源归一化进 evidence schema。

harness（借层）调这里（建层）把 requested/served model、temperature 意图 vs 线上、库版本、
corpus/detector 版本钉进 `meta.provenance`；治滚动别名（`-latest`）不可复现坑（本项目被坑过：
detector fixture 用 `mistral-small-latest`，真快照永久未知）。**纯函数、可离线测**（无网络/无 key）。

决策（档 2 锁定）：seed 只记录不注入（AgentDojo 不发 seed → on_wire=None）；snapshot 粒度
provider-dependent、记录 provider 给什么就是什么、如实标（不强求所有 provider 回 dated snapshot）。
"""
from __future__ import annotations

from typing import Any

AGGREGATE_RULE_VERSION = "wilson-ci-v1"  # harness 聚合口径版本（我们自有、随口径变而升）
SNAPSHOT_QUALITY_NOTE = (
    "served_model=response.model；快照粒度 provider-dependent"
    "（OpenAI 官方回 dated snapshot 如 gpt-4o-mini-2024-07-18；"
    "OpenRouter 常回请求 slug、真实 upstream 靠 system_fingerprint）。"
)


def static_provenance(*, requested_model: str, transport: str, defense: str, suite: str,
                      lib_versions: dict[str, str | None],
                      temperature_intent: float | None) -> dict[str, Any]:
    """一次成型的静态溯源（无需一次 API 调用即知的部分）。served_* 待首个 response 填。"""
    is_detector = defense == "transformers_pi_detector"
    return {
        "requested_model": requested_model,     # 别名，如 mistral-small-latest
        "served_model": None,                   # response.model，首个成功 response 填（治别名核心）
        "system_fingerprint": None,             # 首个 response 填（provider 后端指纹）
        "transport": transport,
        "temperature": {"config_intent": temperature_intent, "on_wire": None},
        "seed": {"on_wire": None},              # AgentDojo 不发 → None（记录-only 决策）
        "libs": {k: v for k, v in lib_versions.items() if v is not None},
        "corpus": {"agentdojo_version": lib_versions.get("agentdojo"),
                   "suite_family": "v1", "suite": suite},
        "detector": {"defense": defense,
                     "transformers_version": lib_versions.get("transformers") if is_detector else None},
        "aggregate_rule_version": AGGREGATE_RULE_VERSION,
        "adaptive_level": "static",             # 攻击非自适应（固定语料）
        "snapshot_quality_note": SNAPSHOT_QUALITY_NOTE,
    }


def _is_not_given(v: Any) -> bool:
    # openai SDK 的 NOT_GIVEN/Omit 哨兵：类型名判定，避开哨兵怪异 __eq__；None=未传同样算省略。
    return v is None or type(v).__name__ in ("NotGiven", "Omit")


def record_response(prov: dict[str, Any], wire_kwargs: dict[str, Any], response: Any) -> dict[str, Any]:
    """首个成功 response 填 served_* + 线上 temperature/seed。幂等（已填则跳过）。

    关键诚实点：AgentDojo 发 `temperature=temperature or NOT_GIVEN`，而默认 0.0 是 falsy →
    实际发成 NOT_GIVEN（省略）→ 用 provider 默认。故 on_wire 记 "omitted" ≠ config_intent 0.0。
    """
    if prov.get("served_model") is not None:
        return prov
    prov["served_model"] = getattr(response, "model", None)
    prov["system_fingerprint"] = getattr(response, "system_fingerprint", None)
    t = wire_kwargs.get("temperature")
    prov["temperature"]["on_wire"] = (
        "omitted" if ("temperature" not in wire_kwargs or _is_not_given(t)) else t)
    s = wire_kwargs.get("seed")
    prov["seed"]["on_wire"] = None if _is_not_given(s) else s
    return prov
