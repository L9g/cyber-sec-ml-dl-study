# ADR 0015 — 第四条切片：非 automatic 裁定（human_review + 声明式证据，CE-UK-SU-03）

日期：2026-07-13 · 状态：accepted（用户拍板选 SU-03 human_review） · 关联：`0011`（D8 v1 baseline、跨域 provisional）、`0012`/`0013`（前两确定性/主动探测切片）、`0014`（CoverageLedger）、`docs/ontology_schema.yaml`（verdict 轴 automatic/llm_judge/human_review）

## 背景
前三切片全是 `verdict_mode=automatic`（AI run / 确定性 rule / 主动探测），且证据都是**工具产出**。第 4 形状切片刻意选**裁定形状最不同**的控制，压测共享契约、看能否逼出 `verdict_source` / 结构化 `ScopeGap`。profile 里只有两个非 automatic 裁定：CE-UK-SU-03（document_review / **human_review** / Low）与 AI-AGENT-COMP-01（llm_judge）。**选 SU-03**（单一新变量最干净：人工裁定 + 声明式证据，不引 LLM 依赖/judge 非确定性；severity Low = 第三档）。

## 唯一新变量 = 人工裁定 + 声明式证据
- **verdict 是 reviewer 的**（human_review）：`ReviewAttestation{reviewer, review_date, decision, statement}` 的 decision（conformant/non_conformant/insufficient_evidence）→ Finding.status（pass/fail/inconclusive，约定 `attestation_mapping_version`）。**不拿确定性 rule 冒充裁定**；系统承载、不第二次猜。
- **证据是声明记录、非工具产出**：变更/例外登记 + attestation 是结构化 JSON（对比 slice 2/3 的 ufw/nmap 工具文本）。
- **advisory 不 override**：登记结构完整性（每条 exception 有 justification）作 advisory 观察 surface，**不推翻人工裁定**（reviewer 裁 conformant 而登记缺 justification → 仍 pass、rationale 带 advisory + mctx 记 unjustified_ids）。
- **无 attestation → inconclusive**（无人工裁定可承载、非 pass；`measurement_valid=False`）。

## 落地形状
- `attestation.py`（新）：`ExceptionEntry` · `ReviewAttestation` · `build_report`（capability→收集声明证据→承载人工裁定→Finding(verdict_mode=human_review, run_record=None)）。
- `capability.py`：加 `CE-UK-SU-03 → governance.change_register.review`（code-local bridge）。
- fixtures `src/tests/fixtures/attestation/`（register_complete/incomplete + attestation_conformant/non_conformant + README）。测试 `test_attestation.py`（10）+ `test_ledger.py` 补 3（human_review 进 rollup、Low fail 不 gate、四形状全在一 ledger）。

## 跨域通用性：第四个数据点仍支撑（更宽了）
四形状（**AI probe / 确定性 config-read / 主动探测-execution / 人工 review**）**同一套 Finding/Evidence/AssuranceReport/CoverageLedger 承载、零 schema 改动**，跨 **3 域**（ai_agent_security / network_security / vulnerability_management）、**3 severity 档**（High/Medium/Low）、**2 verdict_mode**（automatic / human_review）。`verdict_mode=human_review` 早在 schema、首次真用即容纳；`run_record=None` 容纳；`comparisons=[]` 完整；审计闭环复用。

## ⭐ 关键发现：`verdict_source` + 裁定溯源 record 的信号已**四次确认**（但仍未被 consumer 逼断）
四形状各有**不同的裁定溯源**，只有 AI 那个有 Finding 上的 **typed 家**（`ai_run_record`）：

| 切片 | verdict_mode | 裁定溯源 | 落在哪 |
|---|---|---|---|
| AI probe | automatic | `ai_run_record`（model/n_runs/CI） | **Finding.run_record（typed）** |
| config-read | automatic | `rule_version` | mctx free dict |
| active-probe | automatic | `execution_receipt` + rule_version | mctx free dict |
| human_review | human_review | `review_record`（reviewer/date/decision） | mctx free dict |

**四次都把非-AI 的裁定溯源塞进 `measurement_context` free dict** —— 这是**迄今最强的“下一个抽象”信号**：`verdict_source`（automatic-rule / ai-probe / active-probe / human-attestation …）+ 一个 typed 裁定溯源 union（`ai_run_record` 只是其一）应成为 Finding 的一等结构。

**但诚实纪律**：**尚无 consumer 因此断裂**——CoverageLedger 只读 `status`/`verdict_mode`/`severity`，四形状全跑通。故**本切片不加**（不 reactive）。**建议**：把 `verdict_source` 作**下一个刻意的 schema 演进**（据真实摩擦定 schema 的**正当时机已到**——现有**四个真实形状 fixture** 可反推 union，而非早先 1–2 形状时的猜测）。其**forcing trigger** = 需跨形状程序化区分/校验裁定来源的 consumer（如 **Claim/Assurance Engine**，对 human-attestation vs 确定性-rule vs AI-probe 赋不同 confidence）。同理 **结构化 `ScopeGap`** 已三次（slice3 out_of_scope + ledger gap + slice4 unsupported）字符串承载、信号成熟、未逼断。

## 软摩擦（沿用）
`per_trial`/`root_cause_enum`（AI 味）仍非阻塞；human_review 的 `evidence_completeness` 用 per_trial 更牵强（无 trial 概念）——并入 verdict_source 那轮一起想。

## 守纪律
**未动 `ontology_schema.yaml`/profile**；capability bridge code-local；plugin（change_management_check）不透明未参与匹配；不引 LLM；fixture-first；verdict 是人的、不伪造 rule。

## 验证
`pytest src/tests/` = **128/128**（115 + 10 attestation + 3 ledger）。端到端：human_review 裁定矩阵（conformant→pass / non_conformant→fail(Low) / 无 attestation→inconclusive / 结构 advisory 不 override）；四形状全在一个 CoverageLedger、跨 3 域 rollup、Low fail 不 gate；审计闭环 Cyber Essentials + NIST CSF 2.0。
