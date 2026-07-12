# 变更/例外登记 + reviewer attestation fixtures（slice 4 / ADR-0015）

CE-UK-SU-03「Update exceptions and remediation actions are tracked」，method=document_review、
verdict=**human_review**。证据是**声明记录**（变更/例外登记 + reviewer 的人工裁定），**非工具产出**——
故这里冻结的是**结构化 JSON 记录**（对比 slice 2/3 冻结的是 ufw/nmap 工具文本输出）。

| fixture | 内容 |
|---|---|
| `register_complete.json` | 2 条例外，均有 justification_ref + remediation_action |
| `register_incomplete.json` | 1 条完整 + 1 条缺 justification_ref（触发 advisory 结构差异） |
| `attestation_conformant.json` | reviewer 裁定 `conformant` → pass |
| `attestation_non_conformant.json` | reviewer 裁定 `non_conformant` → fail(Low) |

**纪律**：verdict 是 reviewer 的（human_review），系统**承载不第二次猜**；登记结构完整性作 advisory
观察、**surface 不 override** 人工裁定。无 attestation → inconclusive（无裁定可承载、非 pass）。
