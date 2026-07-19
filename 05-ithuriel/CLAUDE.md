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

规划阶段，未编码。skeleton 目录已建，先落阶段 1 的两条最薄端到端切片再谈横向扩展。
