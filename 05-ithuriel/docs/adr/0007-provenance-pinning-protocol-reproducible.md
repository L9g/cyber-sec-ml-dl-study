# ADR 0007 — provenance 钉死（protocol-reproducible，档 2）

日期：2026-07-11 · 状态：draft（供讨论） · 关联：`0004-first-structured-finding-differentiator-layer.md`（§延后 2）、`0006-tradeoff-class-security-utility-closure.md`（§延后）、`docs/architecture-seams-D8.md` §5（MeasurementContext）、ADR-0001（reproducible 分 bit/protocol）

## 背景
ADR-0004 把 `AiRunRecord.model_version/temperature/seed` 与 MeasurementContext 的 seams §5 六字段标为 harness 未捕获的 gap（如实 None、不编造）。**被坑过的实证**：detector fixture 用滚动别名 `mistral-small-latest`，别名背后的快照会变 → 该跑**永久不可复现**（真快照未知）。档 2 让 harness **钉死溯源**达到 **protocol-reproducible**（能复现同协议，区别于 bit-reproducible）。守 thin-slice + 不动 `ontology_schema.yaml`。

## 捕获什么（`meta.provenance`，`ithuriel.provenance` 归一化）
薄适配器原则：harness（借层）调 `ithuriel.provenance`（建层）把溯源填进 evidence schema 单一真相，不各写各的。
- **`served_model`** = `response.model`（首个成功 response）← **治别名核心**；加 `system_fingerprint`（后端指纹）、`requested_model`（别名）三者并列。
- **`temperature` = {config_intent, on_wire}**：诚实记 `0.0 → 省略`——AgentDojo 发 `temperature or NOT_GIVEN`，默认 0.0 是 falsy → 实际发成 NOT_GIVEN（省略）→ 用 provider 默认。config_intent(0.0) ≠ on_wire("omitted")，二者都记。
- **库/语料版本**：`libs{agentdojo,openai,transformers}`、`corpus{agentdojo_version,suite_family:v1,suite}`、`detector{defense,transformers_version}`、`aggregate_rule_version:"wilson-ci-v1"`（自有聚合口径版本）、`adaptive_level:"static"`。
- **`seed`**：只记录（`on_wire`，AgentDojo 不发 → None）。

## 三个锁定决策（用户拍板 2026-07-11）
- **D1｜验证=离线 stub 够**：provenance 逻辑确定性 → 纯函数喂 stub response 测（无 key/无网络）；真跑验证可选。已离线 smoke 确认 harness 把 static provenance 落进 `meta.provenance`（served_* 待首个成功 response，调用失败则如实 None）。
- **D2｜seed 只记录、不注入**：seed 非 `-latest` 痛点；主动注入 per-trial seed schedule（best-effort、provider 常忽略）留后续 → `seed_schedule` 恒 absent（honest）。
- **D3｜接受 snapshot 质量 provider-dependent**：记录 provider 给什么就是什么、如实标——OpenAI 官方回 dated snapshot（`gpt-4o-mini-2024-07-18`）；OpenRouter 常回请求 slug、真实 upstream 靠 `system_fingerprint`。不强求所有 provider 回快照（`snapshot_quality_note` 写进 provenance）。

## 落地形状
- `src/ithuriel/provenance.py`（新）：`static_provenance()` + `record_response()`（幂等、首个成功 response 填 served_*；`_is_not_given` 靠类名判 NOT_GIVEN/Omit/None 哨兵）。**纯函数**。
- `scripts/run_bare_vs_defended.py`：`sys.path` 引 src → import provenance；client wrapper 从**有条件**（仅 compat 端点改 developer→system）升成**无条件**（所有 openai kind 都装以捕获 provenance）；`PROV` 建于 DEFENSE_EFF 后；`meta.provenance` 输出；summary 打印 served/fingerprint/temp。
- `src/ithuriel/derive.py`：`build_measurement_context` 从 `meta.provenance` 填 model.version/corpus/detector/aggregate_rule_version/adaptive_level + `sampling_plan.temperature`；`_absent_seams5()` 据 provenance 现况算仍缺项（**7→1**，只剩 seed_schedule）；`AiRunRecord.model_version` = served snapshot。**缺 provenance 的历史跑优雅退化=全 absent、model_version=None、不崩**。
- `derive_session.py`：summary 路径同填 model_version。
- 测试 `test_provenance.py`（8 条，全离线）：static 钉 transformers 版本 · record_response 记 served+`0.0→omitted`+真 temperature+幂等 · mctx 线程 + `_absent` 收缩到 `[seed_schedule]` · **旧 meta 无 provenance 优雅退化**（回归）· served_model 进 run_record。**47/47 全过**。

## 明确延后（不在本切片）
- **seed 注入**（per-trial seed schedule，让 seed_schedule 落地）——best-effort，provider 支持参差，非 `-latest` 痛点。
- **bit-reproducible**（固定 seed+温度+快照下逐 bit 复现）——provider 默认温度不可控时不可达；protocol-reproducible 已够 D8。
- **anthropic/cohere kind 的 served provenance**——那两 path 未用过，现只记 honest gap（served_model=None）。
- **回填历史 7 跑**：不可能（真快照未知）——正是档 2 要防的未来复现；历史 fixture 保持其 gap，如实。
- **不动 `ontology_schema.yaml`**（守冻结；provenance 先落 meta + pydantic 既有字段，据摩擦稳定后再议迁 schema）。

## 验证
`pytest src/tests/` = **47/47**（39 档1 + 8 档2）。离线 harness smoke（groq fake key，n=1，调用失败）→ `meta.provenance` 落 requested_model/libs/corpus/detector/aggregate_rule_version/adaptive_level，served_model=null（无成功 response，honest）。真跑一次（有 key）即会填 served_model+system_fingerprint。
