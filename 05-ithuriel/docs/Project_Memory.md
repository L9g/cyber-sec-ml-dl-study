# Project Memory

Updated: 2026-07-10

## Current Project

This repository is building a Cyber + AI security/compliance Agent project, targeting UK first and EU compatibility.

Core positioning:

- Do not build another generic scanner platform.
- Build an assurance-oriented Agent that converts standards/regulations into executable ontology, drives existing tools, and produces auditable findings and evidence.
- Use a two-layer model:
  - Base layer: borrow existing execution, IPC, scanner, model, and sandbox tooling where possible.
  - Differentiator layer: build standards-to-ontology distillation and the Evidence / Finding / assurance layer.

## Key Documents

- `docs/Cyber+AI_安全+合规Agent项目规划草案.md`: main planning draft.
- `docs/UK_Region_Profile_v0.2.yaml`: UK machine-readable region profile.
- `docs/ontology_schema.yaml`: extracted ontology/schema definition.
- `docs/papers/Agentic_Cyber_AI_Assurance_Reading_List.md`: curated reading list for agentic cyber, AI safety, and compliance.

## Current Architecture Direction

- MVP language: Python.
- Future trusted execution core in Rust/Go only after measured bottlenecks justify it.
- TypeScript only for frontend.
- Plugins must not directly execute shell, scanners, HTTP attacks, or model calls.
- Plugins should return `ActionPlan`; `CommandExecutor` and `ModelExecutor` enforce RoE, audit, budget, allowlists, and evidence integrity.
- Initial network slice: `CE-UK-FW-01` using `nmap`.
- Initial AI slice: `AI-AGENT-PI-01` using `garak` or `PyRIT`.

## Important Design Principles

- Cyber Essentials is mostly credentialed internal configuration assurance, not black-box red teaming.
- Red-team behavior is only a thin authorized slice.
- Finding status must be four-state: `pass`, `fail`, `not_applicable`, `inconclusive`.
- The current four-state schema is not sufficient for coverage gaps: a future revision must distinguish `not_tested`, `unsupported`, and `out_of_scope` from genuine `not_applicable` so untested surfaces cannot appear green.
- AI probes are non-deterministic and must carry `ai_run_record`.
- Evidence must be tamper-evident and reproducible.
- RoE must be conservative by default:
  - deny when `allowed_targets` is empty;
  - explicit target authorization required;
  - high-risk actions require approval;
  - command execution is allowlist-only.

## Recent Review Notes

The latest review found that the docs improved by adding:

- EU AI Act implementation timeline fields.
- OWASP Top 10 for Agentic Applications for 2026.
- A separate `ontology_schema.yaml`.

Remaining recommended next steps:

- Make `AI-AGENT-PI-01` fully executable in the profile with `severity_if_failed`, `target_types`, `evidence_requirements`, `plugins`, `min_runs`, `success_condition`, and `probe_suite`.
- Add a deterministic RoE decision matrix.
- Clarify `Control -> Test -> Adapter` so high-risk plugin options have explicit execution semantics.
- Add stronger evidence fields such as `run_root_hash`, `tool_db_version`, `template_hash`, `corpus_hash`, `execution_environment`, and `evidence_grade`.
- Structure EU AI Act applicability dates as a map rather than a long inline comment.

## Agentic Security Research Planning Decisions (2026-07-10)

- The four files under `docs/papers/` are preliminary research and development-planning documents, not a formal assurance specification, compliance opinion, or certification claim. Review them for whether they guide sound development decisions; defer production-grade assurance machinery until evidence from the first vertical slice justifies it.
- Organize the AI red-team pipeline as two connected loops rather than one linear fidelity ladder:
  - discovery: generative probes, ToolEmu, mutation, and adaptive attacks produce and triage candidate scenarios;
  - confirmation: frozen/versioned scenarios, AgentDojo/InjecAgent, and bare-vs-defended runs produce repeatable regression evidence.
- A customer scoped sandbox is not required for the MVP, but it is a later high-value, must-win product capability rather than an optional extra. Its role is to measure production-representative blast radius across real identity, permission, tool, data-flow, and recovery behavior. Every engagement remains gated by contract, RoE, approval, and documented sandbox-to-production fidelity gaps.
- Add lightweight P1-P6 mechanism tagging to Findings now; defer the larger taxonomy-governance system. Prefer `root_causes` as an enum array (`P1`-`P6`, `OTHER`, `UNDETERMINED`) so multi-causal findings do not require a later schema migration. Do not use these tags to determine verdicts or rollups yet.
- Normalized Evidence/Finding records provide cross-tool interoperability and traceability, not automatic cross-benchmark score comparability. Any later comparison or rollup requires compatible measurement semantics.
- Keep black-box adversarial evaluation as the first AI slice, not the permanent boundary of the assurance product; later methods may include configuration inspection, trajectory review, and governance evidence.

Deferred until after the first end-to-end AI slice:

- confidence intervals, effect sizes, and statistical-power machinery for ASR;
- signatures, trusted execution, and independent timestamping for stronger provenance;
- a complete machine-readable `measurement_contract`;
- rigorous defense-specific adaptive-attacker experimental design;
- confidence and version governance for the P1-P6 taxonomy (lightweight tags are not deferred);
- formal verification of the ActionPlan/task lifecycle state machine;
- certification-grade claim boundaries, assessor independence, and accreditation design.

## Reading Priority

Start with:

- LLM agents security duality survey.
- AgentDojo.
- Cybench.
- NIST AI 600-1.
- GOV.UK Introduction to AI assurance.

Then apply:

- `AI-AGENT-PI-01` executable fields.
- RoE decision table.
- Evidence grading.
