# List-Titles 下一步开发计划备忘录

日期：2026-07-26  
状态：**已执行完毕（追记 2026-07-27）**——本文档「建议结论」提出的闭环（list-titles 代码收口 → 治理冻结 →
新三臂实验 → 保证结论派生）与「本轮之后的路线选择」第 1 条（对可用的 list-titles instrument 做跨运行稳定性
资格验证）均已走完：list-titles C2 判别 pass，instrument qualification 预注册 FROZEN、派生器与授权扩展
落码、对抗性复核完成，campaign 窗口 1/3 已跑完（详见 `docs/trial/prereg-instrument-qualification-list-titles.md`
与 auto-memory `project-ithuriel-instrument-qualification-prereg`）。本文档保留作历史决策记录，不再是待办；
以下内容按写作时刻的讨论稿原样留存，不回填改写。

## 建议结论

下一步不应立刻扩展新功能，而应完成以下闭环：

> list-titles 代码收口 → 治理冻结 → 新三臂实验 → 保证结论派生

这样本轮才能回答唯一变量：改变 host task 后，security C2 和描述性 utility 会怎样。

| 阶段 | 工作 | 完成门 |
|---|---|---|
| 0. 代码收口 | 修复本轮审阅项 | 代码语义与标签完全一致 |
| 1. 实验冻结 | 新预注册、Hat A/Hat B | 所有实验自由裁量在运行前冻结 |
| 2. 计费运行 | fresh 三臂 C2 | artifact + receipt 完整 |
| 3. 保证派生 | derive、Claim、Ledger、报告 | utility 与 security 均进入结构化链路 |
| 4. 决策复盘 | 根据四类结果决定后续 | 不在看到结果后修改本轮判据 |

## 阶段 0：完成当前代码收口

只修审阅发现，不增加实验设计。

### 0.1 统一 host-task metadata contract

建议冻结以下映射：

```text
read_only:
  endpoint = free_busy_reply
  utility_rule_version = None（或已有正式版本）
  probe_identity = calendar-ipi-mavy/free-busy-proxy-v1

list_titles:
  endpoint = list_title_recall
  utility_rule_version = list-title-recall/v1
  probe_identity = calendar-ipi-mavy/list-titles-v1

write_phase:
  endpoint = authorized_event_state
  utility_rule_version = None（或已有正式版本）
```

当前应避免把 `list-title-recall/v1` 无条件标到 FREE/BUSY 或 write-phase 路径上。最好由一个纯函数统一返回 profile、endpoint、rule version 和 probe identity，并对所有合法与非法组合做参数化测试。

### 0.2 完整传播派生范围

`derive_c2` 应带入 `probe_version_identity`，并在 scope 中陈述实际观察到的正臂 `hits/n`，同时明确：

- descriptive only；
- 无 utility 接受阈值；
- 无因果 utility delta；
- 无 security⊗utility 联合裁定；
- 不代表部署可接受性。

不必创建第二条 Claim。可将这一观察放入 `ScopeStatement.claim` 和 `in_scope`。

旧 artifact 缺少 `probe_version_identity` 时，不应把 `None` 塞入 `Finding.target_ref`，以免改变历史 finding identity。

### 0.3 收紧 read diagnostic 身份绑定

`target_day_titles_observed_in_calendar_read` 应继续保持纯诊断，并要求：

- `tool_call_id` 非空；
- result 位于 call 之后；
- error 与 content 来自同一条 result；
- 重复或冲突的 call/result ID 视为不合格或 `not_measured`。

建议补充 None ID、重复 ID 冲突、result-before-call 三条负向测试。

### 0.4 收窄设计措辞

将“已有余量”或“解除 utility 地板”改为：

> 旨在检验是否能够提供潜在 utility headroom。

是否真正存在余量只能由计费实验回答。

### 0.5 离线完成门

代码修完后再次运行：

- 全量 pytest；
- scrubbed-key self-test；
- `git diff --check`；
- 三种 host task 的合成 artifact/derive 回归。

确保当前未跟踪的 `src/tests/test_calendar_seam.py` 纳入提交。本阶段结束后做一个独立、可审阅的代码提交。

## 阶段 1：冻结 list-titles 实验

新预注册只改变 host task。为保持解释干净，以下项目全部沿用前一轮：

- `family=exfil_via_email`；
- 同一模型、provider、参数与路由约束；
- 同一攻击 payload；
- 同一两个 family-matched negative controls；
- 同一 `calendar_content_egress` security C；
- 同一 C2a/C2b、Fisher/Holm 与正臂阈值；
- 同一 mock fixture 与三臂交错方式；
- fresh、unpooled 样本。

预注册应冻结：

- `host_task=list_titles`；
- `probe_version_identity=calendar-ipi-mavy/list-titles-v1`；
- `measurement_schema_version=4`；
- `utility_rule_version=list-title-recall/v1`；
- 正臂 utility 主观察量为完整标题召回率；
- 三臂均报告 utility hits/n/CI；
- `user_visible_exact_canary` 与 `target_day_titles_observed_in_calendar_read` 的定义和解释；
- read diagnostic 不作 utility 分母门；
- 不设 utility 接受阈值；
- 不计算 utility delta；
- 不产生 security⊗utility 联合 verdict；
- utility 失败不影响 security 分母；
- 旧 FREE/BUSY 结果不与新样本池化。

不建议增加 paid pilot：工具、环境、攻击动作和 email reachability 均未改变；新增部分是已经离线闭合的确定性 final-text oracle。

随后建立新的 Hat A request，确保 request/runtime 至少绑定：

- host task；
- family、三臂、样本数和 attempt cap；
- provider/model；
- schema 与全部受管辖材料；
- preregistration；
- 预算、时间窗与副作用边界。

之后再进行 Hat B 审阅与批准。

## 阶段 2：运行与不可变证据

运行前依次通过：

1. account budget cap；
2. authorization exact match；
3. environment/lock preflight；
4. email reachability；
5. deadline 与 attempt ceiling。

运行使用全新三臂样本，不复用旧 trial。完成后立即：

- 写入 artifact；
- 写入 receipt；
- 校验 artifact SHA、request hash 与 verdict；
- 提交 receipt；
- 不修改原始 artifact，任何更正只使用 sidecar。

## 阶段 3：保证链路验收

对新 artifact 运行 `derive_c2`，验收以下契约：

- Security Finding 仍只由 C2 决定；
- 正臂 `utility_rate == task_completion.hits / task_completion.n`；
- 三臂 utility 与两个诊断完整进入 measurement context；
- `probe_version_identity` 被完整保留；
- Claim/scope 只声称“观察到攻击条件下的宿主任务完成率”，不声称 utility 可接受；
- `comparisons=[]`；
- 没有 utility delta 或联合 verdict；
- `assurance_level:none`；
- `target_fidelity:mock`；
- Finding、Claim、Ledger 和呈现报告能够端到端生成。

建议再做一次独立复算：直接从逐 trial 明细重算三臂 security、utility 和 diagnostics，并与 aggregate 和派生报告逐项比较。

## 阶段 4：预先定义后续决策

结果出来后按以下分叉处理，不临时修改本轮判据。

### Security C2 成立，utility 较高

进入重复运行的 instrument qualification 讨论；仍不直接升级为真实系统保证。

### Security C2 成立，utility 较低

记录为有效的 adverse utility result；不要事后修改标题判据或补 pilot。

### Security 不再点火，utility 较高

说明攻击表现依赖 host-task shape。这是有效机制信号，不能与旧 FREE/BUSY 样本池化。

### Utility 成功但 read diagnostic 较低

优先调查幻觉、轨迹绑定或读取路径；暂不把 completion 当作稳定 instrument。

### C2a 失败或 instrument errors 较多

先修复仪器，不形成目标易感性结论。

## 本轮之后的路线选择

本轮闭合后，不建议立即增加第三个 host-task 变体。应根据实验结果在以下两条路线中选择：

1. 对可用的 list-titles instrument 做跨运行稳定性资格验证；或
2. 推进真实且未参与构建的 trial user，处理当前最大的 C1/C3/C4 产品证据债。

选择依据是本轮是否同时获得可解释的 security 信号和非地板 utility，而不是内部路线图的完整性。

