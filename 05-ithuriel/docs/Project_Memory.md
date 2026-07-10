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
- `docs/architecture-seams-D8.md`: consensus draft for the minimum architectural seams/invariants that must surround the D8 thin slice without building a platform first.
- `docs/Ithuriel_架构框图_v1_审阅结论.md`: review of the v1 architecture diagram; its original P0 module ordering has since been narrowed by the D8 seams discussion below.
- `docs/D8_架构接缝与规划编码边界_讨论笔记.md`: discussion note combining the detailed seam review with the planning/coding/post-slice decision gates.

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

## D8 Architecture-Seam Consensus and Review (2026-07-10)

The architecture review initially proposed too many P0 machines before the first thin slice (PlanCompiler, RunOrchestrator, CoverageLedger, Claim Engine, etc.). That ordering was rejected as inconsistent with D8: first run the smallest end-to-end slice and let real data/error/operational friction shape later modules.

Current guiding sentence:

> Freeze seams before D8; do not build a platform. Let the thin slice determine which seams later grow into modules.

Use three decision gates rather than treating every seam as a planning-time schema decision:

1. **Planning gate — freeze meaning, boundaries, and validity:** product/claim scope; trust and side-effect boundaries; Executor/ModelExecutor as policy enforcement points; defense as target configuration; RawArtifact -> Observation -> TrialOutcome -> Finding semantic separation; trial/error/retry meanings; measurement validity; comparison/treatment rules; holdout independence; status vocabulary; evidence-integrity shape and explicit non-goals.
2. **D8 implementation gate — freeze concrete protocols using real fixtures before persistence/API stability:** Action granularity and fields; canonical serialization/hash; backend method and ExecutionReceipt; capability descriptor; MeasurementContext structure; ComparisonSpec encoding; TrialOutcome enums/counters; detector implementation; calibration fixtures/thresholds; manifest/root algorithm; scope-gap record; target snapshot serialization. Record these with schema/ADR/golden fixtures/test vectors rather than inventing them entirely in planning.
3. **Post-D8 gate — decide machines from friction:** PlanCompiler, RunOrchestrator, full CoverageLedger, ExperimentManager, Claim/Assurance Engine, Temporal/queues/workers, concurrency DAG, streaming/caching, final storage topology, OPA deployment form, Rust/Go, generalized compatibility, LLM judge, advanced statistics, signatures/timestamps/transparency logs.

Planning-time seam invariants currently accepted:

- Plugins never directly cause side effects; Executor and ModelExecutor are PEPs. Use preflight plus pre-dispatch checks and never trust an upstream check as sufficient.
- Approval is scoped to an immutable, policy-relevant Action hash, not broad run-level privilege. Any policy-relevant mutation invalidates approval; dynamically proposed real side effects must be checked again.
- Environment backends share an Action -> ExecutionReceipt + RawArtifactRef/AuditEventRef boundary. Backends must not directly create normalized Evidence or Findings.
- Keep environment fidelity (AgentDojo mock / seeded tenant / customer sandbox) separate from model transport (local / remote API / simulated). A mock tool environment can still have real model-API cost and data egress.
- Controls/tests request capabilities; adapters register capabilities. Do not make standards controls directly depend on tool/plugin identities.
- Preserve RawArtifact -> Observation -> TrialOutcome -> aggregate Finding. Parsers never overwrite raw data; findings reference evidence, context, and rule versions.
- Defense is a target variant/configuration and Ithuriel records the experiment variable/provenance rather than owning the evaluated defense as an internal evaluation module. Architectural separation improves but does not by itself eliminate assessor-independence concerns.
- Discovery samples must receive independent confirmation/holdout; the sample that discovered an attack cannot also prove its stability.
- Capture immutable MeasurementContext from day one. Normalization does not imply comparability.
- A valid measurement (positive control present, bare ASR > 0) is necessary but not sufficient for statistical power: attach a confidence interval to any `security_delta` and mark it `underpowered` (do not assert a delta) when the bare and defended intervals overlap. Full CI/effect-size/power design stays parked; only this fail-closed honesty flag comes forward (ADR 0002, seams §7).
- Evidence shape is per-Action content-addressed manifests aggregated into a run root; do not retain a global linear `prev_evidence_hash` chain as the long-term shape.
- Emit a structured scope/gap statement with no generalized compliance claim for D8 (`assurance_level: none` at run/report scope, not as a Finding property).

Outstanding seam corrections identified before `architecture-seams-D8.md` can be treated as final:

- Bare/defended comparison cannot require raw MeasurementContext equality because `defense_hash` and the full target variant differ. Introduce a minimal ComparisonSpec: invariant fields must match exactly and the declared treatment field is allowed/required to differ. Separate `target_base_hash`, `defense_hash` (including a canonical bare/none value), and `target_variant_hash`.
- Backend protocol should return execution facts/raw artifact references, not Evidence.
- Trial accounting must distinguish `attack_success`, `attack_failure`, `execution_error`, `detector_error`, and invalid trials. Retries do not create new independent trials. Track at least attempted, valid, success, and error counts; insufficient valid trials cannot pass.
- Separate instrument/harness validity, security outcome, and defense utility. A utility failure is a valid adverse defense result, not an invalid measurement. Findings from an invalid measurement must not enter pass/fail rollups.
- Clarify Action authorization granularity using a real AgentDojo trajectory fixture before implementing the Executor path. A likely seed is bounded ProbeAction -> TrialRecord -> ExecutionStep, with new real side effects re-entering the PEP.
- Avoid substring-only canary detection; prefer structured tool calls/state deltas or per-trial nonces in an expected channel/location.
- Data-file / seam synchronization status (reviewed 2026-07-10): `not_applicable` wording and reproducibility grading are already reconciled in `ontology_schema.yaml` (denominator semantics distinguished from `out_of_scope`; BIT vs PROTOCOL reproducibility split). Two fields stay annotated-deferred by design, not overlooked: `prev_evidence_hash` (GATE-2) and `AI-AGENT-PI-01`'s `verification.plugin` binding (GATE-2). The running D8 harness is a standalone AgentDojo runner that does not load the profile/schema, so real friction has not yet reached these two fields; migrate each when code actually consumes it (evidence manifest at first persistence; capability descriptor when a control-driven planner runs the AI slice), not on a doc-only pass.
- Normative authority should be explicit: pipeline note for D1-D8 product decisions; `architecture-seams-D8.md` for D8 runtime seams; ontology schema for the concrete persisted contract once synchronized; architecture diagrams are explanatory only. Commit/export the runtime v2 diagram locally rather than relying on a mutable Claude artifact URL.

Do not interpret the seam work as authorization to build the deferred modules. D8 should remain one process, one fixed sequence, one target/base with bare and defended variants, no concurrency, no resume, and no independent services.

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
