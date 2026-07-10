# ADR 0001 — 首条真实 AgentDojo trajectory fixture：发现 + 对 Gate-1 假设的修正

日期：2026-07-10 · 状态：draft（供讨论） · 关联：`docs/architecture-seams-D8.md` §6

## 背景
按 D8 决策「编码前先拉一条真实 trajectory 当 fixture，再定 `ProbeAction → TrialRecord → ExecutionStep` 粒度」。
用 `agentdojo==0.1.35` 的 `workspace` suite，以 **`ground_truth` 确定性生成（无 LLM 调用）**。
- 生成器：`scripts/gen_agentdojo_fixture.py`
- golden：`tests/fixtures/agentdojo_pi_trajectory.golden.json`（4 KB，AgentDojo dummy 数据，无 PII，可入 git）
- 复现：`uv venv && uv pip install agentdojo==0.1.35 && python scripts/gen_agentdojo_fixture.py`

## 真相表（校准锚开箱即得）
| 检查 | 结果 | 用途 |
|---|---|---|
| benign_utility（空模型输出） | **False** | 见发现 B |
| benign path → security() | **False** | **负对照**（良性轨迹不应判攻击成功）✓ |
| attack path → security() | **True** | **正对照**（攻击轨迹应判成功）✓ |
| execution_error 样本（坏参数） | 结构化 pydantic ValidationError | 见发现 D |

→ D8 校准集（seams §7 附）的正/负对照**种子已就位**，不需另造。

## 发现（真实 fixture 冲击了 Gate-1 假设 —— 正是"先拉 fixture"的价值）

**A. `utility()` / `security()` 都吃 `model_output: str` —— 检测不是纯 state-delta。**
签名同为 `(model_output, pre_env, post_env) -> bool`。mutation 类攻击（send_email）可由环境 state-delta 检出；但 read / answer / **数据外泄类**任务的判定依赖**模型输出文本**。
→ **修正我此前"检效应非症状"的过度一般化**：证据有**两个通道** —— ① 环境 state-delta（动作/mutation 类攻击）② 输出通道（泄漏/回答类攻击）。detector 必须**跨这两个通道按攻击类型选**，不能只 state-delta。「检效应」仍成立，但"效应"含"经输出通道把数据泄露给用户/攻击者"。

**B. 空 `model_output` → benign utility = False。**
不带模型输出跑 ground_truth，answer 类 utility 必 False（它要核对答案文本）。
→ **`TrialRecord` 必须把「模型最终输出文本」作为一等字段捕获**（utility 与 security 都消费它）。**MockBackend 即使工具是 mock，仍需模型产出最终答案**才能评 utility —— 这也说明「D8 无 LLM」只适用于 shape/校准，真正评 utility/security 分布仍需真实模型那一步。

**C. `security()` 与 `utility()` 结构同型。**
二者同签名、同输入。→ measurement_valid / utility / security（seams §7 附的三分）由**同类仪器**计算；`detector_version` 同时覆盖三者的 checker，不是三套独立机制。

**D. `execution_error` = 结构化 pydantic ValidationError（字符串）。**
`run_function` 返回 `(result, error_str)`；error 是多行字符串。
→ 证实 seams §3.3：错误确实与 attack_failure 不同类、需分类；harness 需包装 `(result, error)` 元组，把 error_str 归入 `execution_error`（并与 `detector_error` 区分）。

**E. state_delta 出现「长度相等但内容变」（inbox 8→8 但 changed）。**
naive 的按 size 比较会漏掉 mutation。
→ **state-delta detector 必须按内容 / id 做 content-addressed diff，不能比长度** —— 与 per-Action manifest（seams #6）同一诉求。（本 fixture 生成器的 size-based delta 本身就是反例。）

## 对 seams Gate-1 的具体修正（并入下一版 architecture-seams-D8.md）
1. **Detector 接口** = `(model_output, pre_env, post_env) → outcome`；**两个证据通道**（state-delta + output-channel），按攻击类型选；canary/state-delta 优先，exfil 类必须看 output-channel。
2. **TrialRecord 必含 `model_output` 文本**（一等字段）。
3. **state-delta = content-addressed diff**，非 size 比较。
4. **execution_error 捕获结构化 error 字符串**，harness 分类 execution_error ⊥ detector_error。
5. measurement_valid / utility / security = **同型仪器**，共享 detector_version。

## `ProbeAction → TrialRecord → ExecutionStep` 粒度（据 fixture 初拟，待真实 agent 步确认）
```
ProbeAction { target_variant_ref, capability=PI-probe, scenario=workspace/injection_task_0,
              n_trials, sampling_plan(interleave bare/defended), detector_ref,
              aggregate_rule_ref, token/cost/time budget }
  └─ TrialRecord { trial_i, model_output(text)*, steps[], trial_outcome ∈
        {attack_success, attack_failure, execution_error, detector_error, invalid},
        measurement_context_ref }
        └─ ExecutionStep { step_i, function, args, raw_output_ref, error, state_delta_ref }
```
`*` = 发现 B 新增的一等字段。本 fixture 的 ground_truth 单 call → 1 ExecutionStep；真实多步 agent 会更长。**ExecutionStep = 一次 tool call**（确认）。

## 待办（真实 agent 那一步）
本 fixture 用 ground_truth、无 LLM，覆盖了 **shape + 校准锚 + error 分类**，但**没有**「agent 被注入劫持」的真实非确定行为。那步需**真实模型（Claude API）**在 bare / defended 两配置各跑多次，才见 `success_rate` 分布 + 真实 timeout / refusal / detector 边界。→ 列为 D8 编码首个「真跑」步骤（需 API key + 环境；`ai_roe.require_provider_tos_acknowledgement` 那时 live）。
