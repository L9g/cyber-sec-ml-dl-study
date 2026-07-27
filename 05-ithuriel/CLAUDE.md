# Rules — 05-ithuriel（项目五：安全+合规 Agent，红队/保证 anchor）

继承工作区根 `../CLAUDE.md` 通用约束。本文件只列项目五特定规则。

卖点 = **可审计、可复现的保证结论 + 对陌生系统的对抗性故障发现**，
不是再造一个安全扫描平台。详见 `README.md` 与 `docs/Cyber+AI_安全+合规Agent项目规划草案.md`（v0.4）。

## 两层模型（唯一最重要的构建纪律，见规划文档 §1.1 / 决策 D9）

- **Base = 借，不自建**：执行器 / IPC / 调度 / 扫描探测工具（nmap、nuclei、garak、PyRIT、LLM SDK）/ 未来 Rust 核心。
- **Differentiator = 建**：只有 (1) 标准→ontology 蒸馏，(2) 证据/Finding/保证层。
- **插件是薄适配器**：调用现成工具并把输出归一化进 Evidence schema，绝不重写扫描逻辑，
  不为每个 CE 控制手搓专用扫描器；缺工具的控制留 `not_applicable`/占位。
- **minimal base ≠ toy base**：底座借到"领域内行点头"为止，不多建一分。
- **Rust 推迟**：全程 Python，直到**实测**出可信执行瓶颈才议下沉，不进当前关键路径。

## Schema 不变量（差异化层的核心，实现时须守）

- `standards_refs.source` 不得悬空——必须在 profile 的 `standards:` 注册表里声明。
- `verification` 三正交维：`method`（执行）⊥ `verdict`（automatic/llm_judge/human_review，判定）⊥ `requires_approval`（执行前授权闸门）。
- `Finding.status` 四态：`pass` / `fail`(需 rationale+severity) / `not_applicable`(出分母) / `inconclusive`(重跑或升级人工)。
- AI 探针非确定性：每个 AI Finding 带 `ai_run_record`（model_id/version/temp/seed/n_runs/n_success/success_rate），`n_runs ≥ ai_roe.min_runs_per_probe`。
- 证据可复现：`evidence_integrity` 哈希链，钉死 `tool_version` + `invocation_params`。
- 命令执行 = **白名单模型**；`hard_denied_binaries` 只是兜底，不是主控制。

## 动机纪律

作者引擎 = 冷启动诊断陌生系统的故障（break/diagnose，非 build）。
路线图已把薄 AI 探针 spike 前移到阶段 1——保持"好玩的破的部分前置"，别把它压回最后。

## 状态

早已过了规划/未编码阶段：差异化层已跨 4 种裁定形状、4 个控制验证过跨域通用性（AI-AGENT-PI-01/CE-UK-FW-03/
CE-UK-FW-01/CE-UK-SU-03），四条端到端切片合入 main，零 schema 改动；其上落了 verdict_provenance/Claim
层（ADR-0016）、内部报告 view（ADR-0017）、CoverageLedger、AssessmentManifest、ce_area rollup（ADR-0019/
0021）。红队一侧的 calendar 探针（AI-AGENT-PI-01 的日历间接提示注入变体）已多轮计费真跑，list-titles 变体
C2 判别已 pass；instrument qualification（跨运行复现资格）预注册已 FROZEN，纯逻辑派生器、campaign/前缀门
授权扩展、loader glue 均已落码并经对抗性复核，campaign 跑窗口 1/3 已完成（valid_c2_pass）。计费运行一律走
ADR-0022「一人两帽」执行链。测试 445 项 + runner 自检 196 项全过，纯离线。详见 `README.md`「状态」节与
auto-memory `project-ithuriel-papers-status`（全程状态权威记录）。
