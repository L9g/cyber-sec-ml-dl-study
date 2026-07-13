# 05 · Ithuriel — 安全 + 合规 Agent（红队 / 保证 anchor）

> 名字取自弥尔顿《失乐园》里那杆一触即现原形的矛 Ithuriel。项目做的正是同一件事：用探测让 AI 系统与传统系统里隐藏的失败现形。

## 这是什么

一个以保证（assurance）与对抗性故障发现为主线的安全合规 Agent。它把安全标准蒸馏成机器可读的 ontology，驱动现成工具去测一个目标系统，再把工具的原始输出凝成一份可审计、可复现、带明确边界的结论。平台本身只是底座，价值在结论层。

想快速理解设计原理与代码组织，读 `docs/DESIGN.md`。

两条产品线共享同一内核（ontology、Region Profile、RoE、插件接口、证据模型、报告）：

- **Pack A，网络与 IT 系统安全**：以 Cyber Essentials 就绪度审计为主体，附一层授权红队切片。
- **Pack B，AI Agent 风险检测**：对陌生 AI Agent 冷启动地探测其隐私、安全、合规、越界失败模式。当前切片跑在 AgentDojo 的 mock 场景上；真实部署的 OSS agent（例如 RAGFlow）是后期高保真度档的靶标，不是本项目本身。

## 核心原则：两层模型（借底座，建差异化）

- **Base 等于借**：执行器、IPC、调度、以及所有扫描与探测工具，能借就不自建。如今已借入 AgentDojo（AI 注入探测）、`transformers` 生态的注入检测器、系统自带的 `ufw`（防火墙配置读取）、nmap（端口探测）；未来还会借 nuclei、garak、PyRIT，乃至一个 Rust 可信核心。它们只是可信的被审计对象与执行手段。
- **Differentiator 等于建**：只有两样自己投入。第一是把标准蒸馏成 ontology。第二是证据、Finding 与保证层，包括四态 Finding、AI 探针的运行统计 `ai_run_record`、内容寻址的证据清单 `EvidenceManifest`，以及跨控制的覆盖率 rollup `CoverageLedger`。

Base 层遵循 Unix 式的极简与可组合，差异化层刻意重投入。插件是对现成工具的薄适配器，不是手搓专用扫描器。缺工具的控制不硬凑，如实留成覆盖缺口。

## 文档

- 设计原理与编码介绍：`docs/DESIGN.md`（英文版 `docs/DESIGN.en.md`）
- 编码接缝契约：`docs/architecture-seams-D8.md`
- 架构决策记录：`docs/adr/`（0001 到 0015 的完整决策弧）
- 设计草案：`docs/Cyber+AI_安全+合规Agent项目规划草案.md`
- 机器可读 UK profile 与 ontology schema：`docs/UK_Region_Profile_v0.2.yaml`、`docs/ontology_schema.yaml`

## 与项目 ② 的关系（待决）

Pack B 与项目 ②（LLM 注入防御，蓝队与 benchmark）在"LLM agent 注入"上重叠。三条路线尚未定夺：并行、替换、或合并。推荐合并，也就是先用红队切片跑出真实发现，再拿这些发现驱动项目 ② 的防御权衡。

## 状态

差异化层已经跨四种裁定形状、四个控制验证过跨域通用性，四条端到端切片全部合入主干，测试全绿：

- AI 注入探测 `AI-AGENT-PI-01`（非确定 AI，跑在 AgentDojo mock 上）
- 防火墙默认拒绝策略 `CE-UK-FW-03`（确定性配置读取）
- 端口探测 `CE-UK-FW-01`（主动探测，带执行与授权机器）
- 安全更新治理 `CE-UK-SU-03`（人工复核，声明式证据）

四条切片横跨三个域、三个严重度档、两种裁定模式，由同一套 Finding、Evidence、Assurance、CoverageLedger 承载，全程零 schema 改动。项目仍处切片验证阶段，验证的是这套结论层的形状与纪律站得住，而不是一个打磨完成的成品平台。
