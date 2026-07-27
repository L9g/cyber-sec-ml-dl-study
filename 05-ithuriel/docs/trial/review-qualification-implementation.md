# instrument qualification 实现的对抗性复核（预注册 §7 步骤④）

**定位**：`prereg-instrument-qualification-list-titles.md`（FROZEN）§7 把落码顺序钉成「冻结契约、实现派生器、
golden 覆盖全状态、对抗性复核、冻结 deriver 哈希、才开首窗口 Hat A」。本文件是其中第四步的记录。

**⚠ 独立性边界（先说清楚）**：这是 **AI 自审**，不是独立复核。写代码的和复核的是同一个作者，
`person_independence` 仍是 `none`，ADR-0022 的 `approval.adversarial_review` 若引用本文件只能记成 `ai_agent`，
不得读作 peer review。它能抓的是「实现与冻结契约不一致」和「门可被绕过」这类可机械论证的问题；抓不到的是
「契约本身设计错了」这类需要另一双眼睛的问题。前六轮 review 管的是契约，本轮只管实现。

## 1. 复核范围

复核对象是 commit `2e4f827` 之后、本轮修复之前的三份实现文件与两份测试：

| 文件 | 角色 |
|---|---|
| `src/ithuriel/probes/calendar/qualification.py` | 纯函数派生器（判定逻辑的单一真相源） |
| `src/ithuriel/governance/execution_authorization.py` | 跑前授权门的 qualification 扩展（campaign 块 + 前缀门） |
| `src/ithuriel/derive_qualification.py` | 跑后离线 loader（字节层 + 三件产物） |
| `src/tests/test_calendar_qualification.py` | 判定 golden |
| `src/tests/test_governance_authorization.py`、`src/tests/test_derive_qualification.py` | 授权门与字节层契约 |

## 2. 方法

两遍。第一遍**逐条拿契约的门去找调用点**：把 §5 到 §9 里每一句「必须核」「fail-closed」抽成清单，对每一条在代码里
找实际被执行到的位置，而不是找同名函数。第二遍**对每道已实现的门问「不这样做会怎样」**：设想一个想让不合格的
campaign 通过的操作员（或一个粗心的自己）能走哪条路，再看那条路上有没有机器拦。

第一遍的动机来自本项目已经踩过的坑：函数存在不等于门存在。事实上这一遍在上一步就抓到过两处
（`config_hash` 定义了从没被调用、campaign 归属根本没实现），已在 commit `314eca5` 修掉，不重复计入本轮发现。

## 3. 本轮发现与处置

**发现 ①（pre-spend 保护缺口，已修）**：request 里漏写 `qualification_campaign` 块时，跑前的授权门一句话都不说，
只有跑完之后派生器与 loader 才会因为缺 campaign 回显而拒绝。后果是钱花完了才发现这个窗口不能用。修复是把
「`prereg_ref` 指向本预注册就必须带 campaign 块」做成授权门的硬条件（`QUALIFICATION_PREREG_PATH`），
使遗漏在跑前就被拦下。回归测试 `test_qualification_prereg_without_campaign_block_is_rejected`。

**发现 ②（前缀门可被架空，已修）**：授权门在 Hat A 时能核前缀门的字节没被改、覆盖 1..w-1、由哪一版派生器产出，
但那一刻前几个窗口的 artifact 并不在 git 里（原始结果不入 git），所以它验不了门里的输入哈希指向的究竟是哪几份
artifact。于是存在这样一条路：窗口 1 跑完、拿到门、后来又重跑了一次窗口 1，然后用旧门配新 artifact 去派生，
仍能得到资格结论——「跑下一窗口前先验前缀」就被架空了。修复是在 loader 里补交叉核
（`_cross_check_prefix_gates`）：派生时所有字节都在手上，逐窗口比对门里记的 `artifact_sha256` 与 `receipt_sha256`
是否就是眼下这几份，并顺带核门的 campaign 归属、rule version 与派生器身份。回归测试
`test_gate_bound_to_rerun_window_is_rejected`、`test_gate_from_other_campaign_rejected`。

**发现 ③（证据被静默丢弃，已修）**：loader 把派生器输出里的 set 转成 JSON 时，为了排序方便把 `None` 过滤掉了。
但「某个 turn 根本没报 fingerprint」正是把 provenance 结论收窄成「pinned-route 观测重复性」的依据之一，
静默丢掉它等于报告在这一点上说了不实的话。修复是非空值排序在前、`null` 明确保留在末。回归测试
`test_missing_fingerprint_is_preserved_not_silently_dropped`。

**发现 ④（审计员无法重算比对，已修）**：报告文件的哈希里含 `generated_at_utc` 与本机绝对路径，任何人用同样的
输入重跑派生器都会得到不同的文件哈希，于是「拿同样输入重算、看结论是否一致」这个最基本的审计动作做不了。
修复是另算一个 `core_sha256`，只覆盖 rule 与派生器身份、各输入哈希、判定结果，与时刻和路径无关，并写进
committed 审计锚。回归测试 `test_core_hash_is_reproducible_while_file_hash_is_not`。

## 4. 契约条款到实现与测试的对照

| 契约条款 | 实现 | 测试 |
|---|---|---|
| §5.1 measurement validity（三臂各 30、error-cap） | `qualification.measurement_validity` | 边界 3/4 golden |
| §5.2 逐窗口判据 = 重放 `c2_layered_verdict` | `qualification.replay_c2` | 26/30 pass、7/30 fail |
| §5.4 instrument-error 决策表与 provenance 协调 | `_instrument_error_count`、`provenance_check` | error trial 无 telemetry 不双罚 |
| §6 Option A 全合取 + 五态状态机 + well-formedness | `derive_qualification` | 五态 + 三类畸形拒绝 |
| §7 治理绑定与预算谓词 | `governance_ok`、`budget_ok`、授权门同判据 | 两侧各有 |
| §7 campaign 归属 | `campaign_ok`（回显对 manifest） | 四例 |
| §7 时间约束 | `time_ok`（跑后）、授权门区间检查（跑前） | 同日、出区间、出有效期 |
| §7 config projection 与哈希重算 | 两套 extractor、`tier1_matches`、`config_hash` 与声明值比对 | per-arm 换算、缺臂、声明不符 |
| §7 provenance 逐 trial 逐 turn | `provenance_check` | served_model 不符、fingerprint 非唯一收窄 |
| §7 前缀门（procedure 落成 machine） | 授权门 `_verify_prefix_gate_record` + loader `_cross_check_prefix_gates` | 缺失、不可授权、终局、覆盖不符、字节、commit 顺序、重跑 |
| §9 Hat A campaign 字段 | `validate_qualification_campaign` | 缺字段、k、window_index、派生器与 prereg 哈希 |
| §9 committed 审计锚 | `build_anchor` | report/core 哈希锚定 |
| §9 closure record 与 deadline 形态 | `derive_qualification` deadline 分支 | closed_at 早于 deadline 被拒 |

## 5. 残余限制（不修，及理由）

**授权门管字节不管语义**。三方哈希只能证明「被批准的那份字节跑了」，证明不了「那份代码实现了冻结的那份设计」。
本轮加的所有门都在这条边界之内，设计一致性靠的是上面那张对照表加 golden 测试，不是靠哈希。

**git 只是顺序锚点**。本地 commit 时间可回填、历史可重写，所以前缀门早于 Hat A 这一条证的是顺序不是时刻，
artifact 继续标 `temporal_anchor: local_git_only`。

**预声明区间允许重叠**。契约绑的是 `started_at` 落在区间内，没有绑区间本身互不重叠；跨窗口至少 24 小时且不同
UTC 日的约束由派生器按 receipt 事后核。这里刻意不加严：比 FROZEN 契约更严的门会拒掉契约允许的运行，
那等于偷改冻结设计。

**审计锚与前缀门要进 git 靠流程**。前缀门在下一个窗口的 Hat A 会被 `_assert_tracked_and_clean` 强制要求已跟踪
且干净，所以它实际上跑不掉；审计锚没有下游消费者，committed 与否目前只能靠流程约束。

**进程内篡改不在威胁模型内**。loader 核的是当前被 import 的 `qualification.py` 的文件字节，能挡「换一版派生器
出结论」，挡不住同一进程里运行时被 monkeypatch。自授权的 T0 到 T2 阶段接受这条。

**这份复核本身不独立**（见开头）。

## 6. 结论与步骤⑤ 的冻结哈希

实现与 FROZEN 契约一致，四处发现已全部修复并有回归测试；全量 `pytest` 445 项通过，
`run_calendar_probe.py --self-test` 全部通过，全程离线、无计费。可以进入步骤⑤。

冻结时刻的受管辖材料哈希（Hat A 写进 campaign manifest 时必须与此一致，否则授权门会拒）：

| 路径 | SHA-256 |
|---|---|
| `src/ithuriel/probes/calendar/qualification.py`（派生器） | 见本次 commit 后重算，campaign manifest 以 Hat A 当刻为准 |
| `src/ithuriel/derive_qualification.py`（loader） | 同上 |
| `src/ithuriel/governance/execution_authorization.py`（授权门） | 同上 |

哈希不写死在本文件里，是因为本文件一旦提交、上述文件再有任何改动，写死的值就会变成一份过期的谎。
Hat A 的 campaign manifest 用当刻实际字节重算，授权门在跑前逐份比对，那才是权威。

**本节写作时尚未授权任何计费运行**；下一步是首窗口 Hat A：由操作员预声明 `campaign_start_utc`、三个窗口的
`allowed_start_utc` 与 `allowed_end_utc`、设置 OpenRouter 账户消费上限并在 Hat B 里 attest，然后本人独立
commit 批准。

## 7. 事后追记（2026-07-27，窗口 1 已跑完）

首窗口 Hat A `bb403a2` → Hat B `76b09f7`（用户签、cap $3 已 attest）→ 跑（started 18:02:51Z）→ 派生
`5892357`。结果：positive 30/30、两负臂各 0/30、`c2_pass`、Holm 双显著；`campaign_status=in_progress`、
`next_window_authorizable=true`（不构成 qualification 结论，仍需三窗口全合取）。本节第 6 节的结论与冻结哈希
均按跑前状态成立，不因此追记而改写；此段只标注「当前状态已超越本文写作时刻」，避免读者把上面的
「尚未授权」当作最新事实。窗口 2/3 进度见 [[project-ithuriel-instrument-qualification-prereg]]（auto-memory）。
