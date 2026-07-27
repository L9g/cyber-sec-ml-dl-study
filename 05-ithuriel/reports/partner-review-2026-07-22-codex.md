# Ithuriel partner review — 2026-07-22（Codex 阶段性审阅）

总体判断：C2a/C2b 分层、四层证据的 `not-measured` 纪律以及“不折成单一数值”方向正确；D1 是必须修的潜在选择偏倚，但现有批次零排除、未改变计数；当前 `c2_pass` 降为 provisional 并要求重跑的理由仅是 C1 的负对照失配。
设计层 1 条 / 代码层 6 条 / 纪律层 1 条。
本轮按最新 `docs/review-brief-for-partner-agent.md` 审阅；用户指定的 `reports/partner-review-2026-07-22.md` 在审阅开始时并不存在，故报告另存为本文件。
最新验证（含 C6 修复 `b6a0c48`）：`.venv/bin/python -m pytest src/tests -q` → `200 passed`；`.venv/bin/python scripts/run_calendar_probe.py --self-test` → `260 passed`。

| ID | 层 | 严重度 | 位置 | 一句话 |
|----|----|--------|------|--------|
| D1 | design | high | §4.8 / C2 additive 分母 | 规则会排除“只执行攻击”的强阳性，但现有 C2 与 stage-1 均零排除，既有计数未受影响 |
| C1 | code | high | `scripts/run_calendar_probe.py:246` | 负对照把外壳长度计算两次，实际为正臂的 147%–176%，却被标成字符长度近似匹配 |
| C2 | code | med | `scripts/run_calendar_probe.py:2341` | 原生 OpenAI preset 因 `telemetry` 未初始化而在任何 API 调用前崩溃 |
| C3 | code | med | `scripts/run_calendar_probe.py:977` | attempt cap 被写成 `planned_trials`，形成 `completed=90 / planned=135 / run_status=completed` 的矛盾标签 |
| C4 | code | med | `src/ithuriel/executor.py:44` | PEP 接受空端口、0、负数和 65536，并把它们判为 `allowed` |
| C5 | code | high | `src/ithuriel/attestation.py:55` | reviewer、日期、声明和引用全空的 attestation 仍产出 human-review `pass` |
| C6 | code | high | `scripts/run_calendar_probe.py:935` | **已修 `b6a0c48`**：prereg 声明必须命中哈希材料，且取消 runner-only 默认值 |
| P1 | discipline | — | §4.13 / `scripts/run_calendar_probe.py` | 差异化逻辑属于 `src/` 信任核，CLI/provider 编排才属于 `scripts/` |

### D1 — additive 主指标被条件化在非必要的处理后变量上

- 层 / 严重度：design / high
- 位置：§4.8；`docs/trial/prereg-c2-confirm-additive.md §5`；`scripts/run_calendar_probe.py:2706`
- 我的判断：是否 §6 已列项？☐ 新发现；§4.8 已把“处理后变量”列为张力，但现有缓解不够。
- 问题：`family_primary_emitted` 对 additive 族量的是另建 `free-<nonce>` 的 emission。该动作不以 `Focus block` 成功落入 state 为结构前提；相反，“模型只服从注入、创建攻击事件，却没完成宿主写”是最强的安全阳性兼 utility 失败。当前定义却令它 `interpretable=False`、不进命中分母，并继续补样直到收满 30 个 host-core 成功的 trial。
- 对既有数据的影响：复核 artifact 后，C2 三臂均为 `attempts=30, n_interpretable=30, excluded=0`；stage-1 四格均为 `attempts=10, n_interpretable=10, excluded=0`。因此按未条件化分母重算仍是 C2 `29/30, 0/30, 0/30`，stage-1 各格计数也完全不变。D1 没有实际删掉本批任何 trial，**不构成既有数据重跑理由**。
- 潜在后果：在未来出现 host-core 失败的批次时，逐臂报告排除率只能暴露删失规模，不能恢复被删掉的攻击命中；即使三臂排除率相等，也不能证明留下的是同一 principal stratum。该规则仍会偏向“同时做完宿主任务”的轨迹。
- 建议：对 additive，把主安全分母改为 `instrument_valid ∧ L0 ∧ valid_target_outcome`；`host_core_state_success` 作为正交 utility 指标，不筛主指标。只对语义上必须修改宿主调用的 `aug_participant` 族使用 host-core 前提，并明确这是族特异分母。现有 additive 结果只需记录“按新分母复算无变化”；D1 修复无需触发重跑。当前重跑要求来自 C1。
- 挑战纪律？：否；这是落实 security ⊥ utility，而不是新增统计平台。

### C1 — “字符长度近似匹配”实际长出 47%–76%

- 层 / 严重度：code / high
- 位置：`scripts/run_calendar_probe.py:246-265`、`:1926`、`:2797`
- 触发场景（输入到错误输出）：
    输入：`nonce=ABCDEF1234, rung=1`，分别生成 additive / aug_participant 的 positive、plain、marker_exposed 描述。
    结果：实测长度比为 additive plain `747/455=1.642`、additive marker `800/455=1.758`、aug plain `895/528=1.695`、aug marker `779/528=1.475`。原因是 `target` 已含 `<INFORMATION>` 外壳，循环却让裸 `goal` 追到 `len(target)*0.85`，返回时又加一次外壳。自检名写“±15%”，断言却只检查 `>=85%`，所以上界完全失守；artifact 仍写 `character-length approximation`。
- 我的判断：是否 §6 已列项？☐ 新发现；属于“标签过度声称 + 接缝漏测”。
- 建议：对最终返回字符串做双边断言 `0.85 <= len(negative)/len(positive) <= 1.15`，并让 filler 支持裁剪而非只整段追加；artifact 每臂保存实际字符数与比值。修复后重跑 C2 两个负臂；在此之前把现有 `c2_pass` 降为 provisional，因为载荷长度/稀释可能影响模型是否把描述转成动作。
- 挑战纪律？：否。

### C2 — 原生 OpenAI preset 在建 pipeline 时崩溃

- 层 / 严重度：code / med
- 位置：`scripts/run_calendar_probe.py:2341-2401`
- 触发场景（输入到错误输出）：
    输入：`OPENAI_API_KEY=test`，调用 `build_pipeline("openai", "gpt-4o-mini", None)`；该 preset 的 `base_url=None`。
    结果：`if base_url` 分支不执行，`telemetry` 从未赋值；到 `pipe._telemetry = telemetry` 抛 `UnboundLocalError`，尚未发出任何 API 请求。CLI 明列的 `openai` 后端不可用。
- 我的判断：是否 §6 已列项？☐ 新发现。
- 建议：在分支外初始化 `served=set()` 与 `telemetry=[]`；把 telemetry wrapper 是否安装显式记录，并增加一个不联网的 native/compat 两路 pipeline construction 测试。
- 挑战纪律？：否。

### C3 — `planned_trials` 实际承载授权上限

- 层 / 严重度：code / med
- 位置：`scripts/run_calendar_probe.py:977-1000`、`:2800-2803`、`:2929-2932`
- 触发场景（输入到错误输出）：
    输入：C2 确认三臂目标各 30 个可解释 trial、attempt cap 各 45，全部首轮即有效，共执行 90 次。
    结果：现有 artifact 输出 `run_status="completed"`, `completed_trials=90`, `planned_trials=135`；stage-1 同样输出 `40/60` 且 completed。135/60 是允许补跑的最大 attempt 数，不是计划必须执行数。
- 我的判断：是否 §6 已列项？☐ 新发现；属于第五类标签过度声称。
- 建议：把该字段改名 `max_authorized_attempts`；另存 `target_interpretable_trials`（确认阶段为 90）与 `completion_criterion_met`。不要让机器消费者从 `completed_trials < planned_trials` 反推出一个实际上不存在的中断。
- 挑战纪律？：否。

### C4 — PEP 的端口文法没有下界、上界或非空约束

- 层 / 严重度：code / med
- 位置：`src/ithuriel/executor.py:44`、`:57-61`、`:100-116`
- 触发场景（输入到错误输出）：
    输入：已授权 `192.0.2.1/32`，分别构造 `ports=()`, `(0,)`, `(-1,)`, `(65536,)`。
    结果：四者 `preflight(...).allowed` 均为 `True, reason="ok"`；编译出 `-p ""`、`-p 0`、`-p -1`、`-p 65536`。mock backend 还会回 `exit_code=0`，而真实 nmap 路径会失败或产生与动作语义不一致的事实。
- 我的判断：是否 §6 已列项？☐ 新发现。
- 建议：在 Action 模型层约束 `ports` 至少一个、至多 64 个、每项 `1..65535`，并确定重复端口是拒绝还是规范化去重；pre-dispatch 仍独立重跑同一约束。补四个负例测试，守住“非白名单行为在类型层不可表达”的现有承诺。
- 挑战纪律？：否。

### C5 — 空壳 attestation 可以生成保证层 `pass`

- 层 / 严重度：code / high
- 位置：`src/ithuriel/attestation.py:55-61`、`:96-117`
- 触发场景（输入到错误输出）：
    输入：空 register，加 `ReviewAttestation(reviewer="", review_date="", decision="conformant", statement="", attested_refs=[])`。
    结果：`Finding.status="pass"`、`scope.measurement_valid=True`、`verdict_mode="human_review"`，rationale 为 `reviewer= 于  裁定 conformant`。形式上有对象、实质上没有可归责的人、时间、声明或被审材料。
- 我的判断：是否 §6 已列项？☐ 新发现；属于 attestation 标签强于实现。
- 建议：模型层至少强制 reviewer、review_date、statement 非空且日期可解析；`conformant/non_conformant` 要求 `attested_refs` 非空，并校验引用能够解析到本次 register/artifact。结构不完整应拒绝构造或降为 `inconclusive`，不得仅靠 `attestation is not None` 令 measurement valid。
- 挑战纪律？：否；系统仍不需要二次猜人的裁定，只需验证“人工裁定证据”确实成形。

### C6 — prereg 可从授权哈希集合中静默漏掉（已修）

- 层 / 严重度：code / high
- 位置：`scripts/run_calendar_probe.py:935-938`、`:1036-1044`、`:1103-1123`
- 触发场景（输入到错误输出）：
    输入：不设 `CAL_GOVERNED_MATERIALS`，据默认 runtime 生成并批准 request；其 `materials` 只有 `scripts/run_calendar_probe.py`。批准后修改并提交 `docs/trial/prereg-c2-confirm-additive.md`，runner/request/approval 保持不变。
    结果：validator 只检查 request 自己列出的材料，runtime equality 也只看到同一份 runner-only 列表，因此 prereg 改动不参与三方哈希，运行仍可返回 `authorization_status=approved` 与 `analysis_eligibility=preregistered`；artifact 又硬编码指向当前、已变化的 prereg。
- 我的判断：是否 §6 已列项？☐ 新发现；G7 是 instrument qualification，非此问题。它比“哈希管字节不管语义”的已知边界更早：这里连应管的 prereg 字节都可能没进哈希。
- 对既有数据的影响：复核 `execution-request-c2-confirm-001.json` 与 `execution-request-c2-sweep-001.json` 后，两者的 request/runtime materials 都实际包含对应 prereg 与 runner；结果 artifact 的 `meta.governed_materials` 也记录了同一 prereg 哈希。故已有 C2 确认与 stage-1 结论**没有被 C6 污染**。C6 是默认配置对未来请求的静默放行风险。
- 原建议：按 `experiment_mode` 定义最小必含材料集合，并验证 `required ⊆ materials`。实现者正确指出，同一 mode 合法更换 prereg 是常态，硬编 mode→文档映射容易在换文档时阻塞或绑错，原建议不够一般。
- 修复复核（`b6a0c48`）：`prereg_ref` 升为 request 必填，并要求它精确命中 `request.materials[].path`；该列表随后接受既有的当前字节 / approval commit blob / 声明哈希三方校验。`CAL_GOVERNED_MATERIALS` 为空时直接拒绝，不再让 request 与 runtime 共同回落到 runner-only 默认值。`auth_meta` 从已验证条目导出 `prereg_path` 与 `prereg_sha256`。这套规则直接保证“声明的那份 prereg 一定被绑定”，比原先的 mode 映射更稳健，判定 **resolved**。
- 回归验证：缺 `prereg_ref`、声明 prereg 但漏列材料、未设材料环境变量三条均 fail closed；正常链记录 prereg 路径与哈希。完整 pytest `200 passed`，runner 自检 `260 passed`。
- 挑战纪律？：否。

### P1 — runner 已成为信任核，不应继续整体留在 `scripts/`

- 层 / 严重度：discipline / —
- 位置：§4.13；`scripts/run_calendar_probe.py`
- 我的判断：这里不是“两层模型”纪律画错，而是物理归属与审阅边界画错。oracle、证据分类、C2 判据和授权校验都是 Differentiator/PEP；把它们与 CLI、provider SDK monkey-patch、文件写入和 255 项 print-driven 自检放在同一 3376 行脚本中，使信任核无法被常规测试直接 import、复用和设依赖边界。C1 与 C2 正是这种混居造成的接缝漏测。
- 建议：保留 `scripts/run_calendar_probe.py` 作为薄入口；把纯逻辑拆到 `src/ithuriel/probes/calendar/{payload,oracle,c2}.py`，把治理门拆到 `src/ithuriel/governance/execution_authorization.py`，把 provider/AgentDojo glue 留在 adapter/runner。迁移现有自检为 pytest，先按纯函数/副作用边界切，不建设通用 ExperimentManager。
- 挑战纪律？：是，挑战的是“差异化逻辑可长期留在 scripts”这一隐含归属，不挑战 Base=借 / Differentiator=建。

## 明确认同、无需改动的部分

- C2a/C2b 的分层切点是对的：`negative_marker_exposed` 应是强保证结论的硬门槛、普通易感性实验的范围限定；失败不构成目标易感或不易感的证据。
- emission / dispatch / tool result / state 分层保存，以及 call→event id 解析失败返回 `None` 而不回退成 `False`，符合“宁可未测量、不可静默降级”。
- 攻击族逐调用互斥、旁路只作诊断的方向成立；本轮未找到跨调用拼接回主指标的路径。
- `assurance_level=none`、`target_fidelity=mock` 与 person independence 的边界披露总体诚实；没有发现把 coverage、warrant、fidelity 折成 overall score 的路径。
- §6 的 F3（`success_rate=None → 0.0`）仍存在，但本轮没有发现新的触发消费者，故不重复列为 finding。
