# Agentic Cyber + AI Safety + Compliance Reading List

> Updated: 2026-07-09
>
> Scope: agent-driven cybersecurity, AI agent security, AI assurance, and compliance references for the Cyber + AI security/compliance Agent project.
>
> **法规条目用途纪律（决策 D6，2026-07-10）**：清单里的法规/标准分两种角色——
> `understand`（overview / 二手解读，只用于理解领域，**不得**作 control mapping 的锚）
> vs `anchor`（法规原文条款 / 正式标准，**才可**作 `standards_refs.source`，因 source 不得悬空）。
> 当前 #10 NIST RMF、#12 GOV.UK assurance、#13 EU AI Act overview 页均为 `understand`；
> 建 control mapping 前须取其**原文条款 / Annex / ISO·NIST clause** 作 `anchor`。#11 NIST AI 600-1 PDF 可直接作 `anchor`。

## P0 - Must Read

1. [LLM agents security duality: a comprehensive survey of self-security and empowered cybersecurity](https://arxiv.org/abs/2606.28450)  
   Latest survey covering both agent self-security and agent-enabled cybersecurity. Useful for the project's high-level taxonomy and positioning.

2. [A Survey on Agentic Security: Applications, Threats and Defenses](https://arxiv.org/abs/2510.06445)  
   Broad survey across applications, threats, and defenses. Useful for structuring the project's agentic security ontology.

3. [The Evolution of Agentic AI in Cybersecurity](https://arxiv.org/abs/2512.06659)  
   Tracks the shift from single LLM helpers to multi-agent and semi-autonomous cyber pipelines. Useful for architecture and roadmap framing.

4. [Cybench: A Framework for Evaluating Cybersecurity Capabilities and Risks of Language Models](https://arxiv.org/abs/2408.08926)  
   Important benchmark for cyber agents. Especially relevant for task, subtask, environment, and agent scaffold design.

5. [CYBERSECEVAL 3: Advancing the Evaluation of Cybersecurity Risks and Capabilities in Large Language Models](https://arxiv.org/abs/2408.01605)  
   Meta's cybersecurity risk evaluation suite for LLMs, including autonomous offensive cyber operation evaluation.

6. [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352)  
   Directly relevant to `AI-AGENT-PI-01` and `AI-AGENT-TOOL-01`; focuses on tool-using agents over untrusted data.

7. [InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents](https://arxiv.org/abs/2403.02691)  
   Useful for indirect prompt injection scenarios involving tools, external content, and private data exfiltration.

8. [Identifying the Risks of LM Agents with an LM-Emulated Sandbox](https://arxiv.org/abs/2309.15817)  
   Introduces ToolEmu. Useful for testing risky agent behavior without connecting real high-risk tools in the MVP.

9. [SAGA: A Security Architecture for Governing AI Agentic Systems](https://arxiv.org/abs/2504.21034)  
   Useful for agent identity, authorization, delegation, and policy enforcement design.

10. [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)  
    Primary AI risk management backbone for GOVERN / MAP / MEASURE / MANAGE mapping.

11. [NIST AI 600-1: Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)  
    Generative AI profile for NIST AI RMF. Useful for AI risk controls, measurement, documentation, and governance evidence.

12. [GOV.UK Introduction to AI assurance](https://www.gov.uk/government/publications/introduction-to-ai-assurance)  
    Core UK-first assurance reference. Useful for the project's assurance layer and evidence model.

13. [EU AI Act official overview](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)  
    Official source for EU AI Act risk tiers, obligations, and implementation timeline.

## P1 - Should Read

14. [SoK: DARPA's AI Cyber Challenge (AIxCC): Competition Design, Architectures, and Lessons Learned](https://arxiv.org/abs/2602.07666)  
    Useful for autonomous vulnerability discovery and remediation architecture lessons.

15. [Cybersecurity AI Benchmark (CAIBench): A Meta-Benchmark for Evaluating Cybersecurity AI Agents](https://arxiv.org/abs/2510.24317)  
    Useful for thinking beyond single-task scanning toward broader labor-relevant cyber capability evaluation.

16. [CTFusion: A CTF-based Benchmark for LLM Agent Evaluation](https://arxiv.org/abs/2605.11504)  
    Discusses data contamination and live CTF evaluation. Useful for future robust benchmark design.

17. [Towards Effective Offensive Security LLM Agents](https://arxiv.org/abs/2508.05674)  
    Includes CTFJudge, CTFTiny, LLM-as-judge, and hyperparameter findings. Useful for `llm_judge` and `ai_run_record`.

18. [AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents](https://arxiv.org/abs/2410.09024)  
    Useful for defining harmful multi-step agent behavior and refusal/evasion testing.

19. [AgentHazard: A Benchmark for Evaluating Harmful Behavior in Computer-Use Agents](https://arxiv.org/abs/2604.02947)  
    Useful for testing multi-step accumulated harm where each individual action may appear locally acceptable.

20. [Formalizing the Safety, Security, and Functional Properties of Agentic AI Systems](https://arxiv.org/abs/2510.14133)  
    Useful for formalizing RoE, ActionPlan, task lifecycle, approval states, and multi-agent coordination properties.

21. [Indirect Prompt Injections: Are Firewalls All You Need, or Stronger Benchmarks?](https://arxiv.org/abs/2510.05244)  
    Important reminder that simple defenses can saturate weak benchmarks; useful for designing adaptive attack corpora.

22. [Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection](https://arxiv.org/abs/2302.12173)  
    Foundational indirect prompt injection paper. Still useful background for RAG and tool-output threat modeling.

23. [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/)  
    Primary source for first-pass LLM application security mapping.

24. [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)  
    Primary source for agent-layer security controls beyond generic LLM application risks.

25. [MITRE ATLAS](https://atlas.mitre.org/)  
    Useful for AI red-team TTP tagging, similar to how MITRE ATT&CK is used for traditional cyber activity.

## P2 - Track

26. [AgentSOC: A Multi-Layer Agentic AI Framework for Security Operations Automation](https://arxiv.org/abs/2604.20134)  
    Useful SOC automation reference, but likely too broad for the MVP.

27. [Agentic AI for Cyber Resilience: A New Security Paradigm and Its System-Theoretic Foundations](https://arxiv.org/abs/2512.22883)  
    Useful for long-term cyber resilience framing and system-theoretic language.

28. [AgentDyn: A Dynamic Open-Ended Benchmark for Evaluating Prompt Injection Attacks of Real-World Agent Security System](https://arxiv.org/abs/2602.03117)  
    Useful for later upgrading the attack scenario corpus to dynamic, open-ended tasks.

29. [Which Defense Closes Which Threat? Attributing OWASP-LLM-Top-10 Coverage and Its Brittleness Under Paraphrasing](https://arxiv.org/abs/2606.02822)  
    Useful for mapping defense families to OWASP LLM risks and testing paraphrase brittleness.

## Community News And Industry Articles

30. [Microsoft injects AI agents into security tools](https://www.axios.com/2025/03/24/microsoft-ai-agents-cybersecurity)  
    Industry signal for Security Copilot-style agent workflows in security operations.

31. [Inside the U.S. competition to create AI security tools](https://www.axios.com/2024/08/13/darpa-ai-cyber-challenge-def-con)  
    Industry coverage of AIxCC. Read alongside the AIxCC SoK paper.

32. [Generative AI's Biggest Security Flaw Is Not Easy to Fix](https://www.wired.com/story/generative-ai-prompt-injection-hacking)  
    Good non-academic explanation of why indirect prompt injection is hard to eliminate.

33. [Prompt injection attacks might 'never be properly mitigated' UK NCSC warns](https://www.techradar.com/pro/security/prompt-injection-attacks-might-never-be-properly-mitigated-uk-ncsc-warns)  
    Useful industry-facing support for conservative trust boundaries and defense-in-depth.

34. [CrowdStrike snaps up Pangea to boost AI security](https://www.techradar.com/pro/security/crowdstrike-snaps-up-pangea-to-boost-ai-security)  
    Market signal for AI Detection and Response as an emerging product category.

35. [Cybersecurity firm says it found 'the first documented case' of AI agentic ransomware](https://www.businessinsider.com/ai-ransomware-attack-sysdig-jade-puffer-2026-7)  
    Treat as a threat signal, not academic evidence. Useful for tracking mainstream discussion of agentic cyber abuse.

## Suggested Reading Order

1. Read first: LLM agents security duality, AgentDojo, Cybench, NIST AI 600-1, and GOV.UK Introduction to AI assurance.
2. Apply immediately: update `AI-AGENT-PI-01` executable fields, RoE decision table, and evidence grading.
3. Read next: SAGA, ToolEmu, InjecAgent, and AIxCC SoK.
4. Apply next: design the first AI probe adapter and attack corpus governance model.

---

## Download Report (2026-07-09)

以下 PDF 已下载至 `./docs/papers/`：

**arXiv 论文 (22 篇)** — 以 arxiv ID 命名：

| # | ID | 标题 |
|---|-----|------|
| 1 | `2606.28450` | LLM agents security duality |
| 2 | `2510.06445` | Survey on Agentic Security |
| 3 | `2512.06659` | Evolution of Agentic AI in Cybersecurity |
| 4 | `2408.08926` | Cybench |
| 5 | `2408.01605` | CYBERSECEVAL 3 |
| 6 | `2406.13352` | AgentDojo |
| 7 | `2403.02691` | InjecAgent |
| 8 | `2309.15817` | ToolEmu |
| 9 | `2504.21034` | SAGA |
| 14 | `2602.07666` | AIxCC SoK |
| 15 | `2510.24317` | CAIBench |
| 16 | `2605.11504` | CTFusion |
| 17 | `2508.05674` | Towards Effective Offensive Security LLM Agents |
| 18 | `2410.09024` | AgentHarm |
| 19 | `2604.02947` | AgentHazard |
| 20 | `2510.14133` | Formalizing Agentic AI Properties |
| 21 | `2510.05244` | Indirect Prompt Injections |
| 22 | `2302.12173` | Not what you've signed up for |
| 26 | `2604.20134` | AgentSOC |
| 27 | `2512.22883` | Agentic AI for Cyber Resilience |
| 28 | `2602.03117` | AgentDyn |
| 29 | `2606.02822` | Which Defense Closes Which Threat |

**NIST**: `NIST.AI.600-1.pdf`

**纯网页（未下载，需浏览器打开）**：
- #10 NIST AI RMF — <https://www.nist.gov/itl/ai-risk-management-framework>
- #12 GOV.UK AI assurance — <https://www.gov.uk/government/publications/introduction-to-ai-assurance>
- #13 EU AI Act — <https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai>
- #23 OWASP LLM Top 10 2025 — <https://genai.owasp.org/llm-top-10/>
- #24 OWASP Agentic Top 10 2026 — <https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>
- #25 MITRE ATLAS — <https://atlas.mitre.org/>
- #30 ～ #35 新闻/行业文章 — 均为网页链接
