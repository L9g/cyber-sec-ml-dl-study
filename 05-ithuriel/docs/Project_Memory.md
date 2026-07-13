# Project Memory

Updated: 2026-07-13

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

## Partner Project Review (2026-07-12)

- A design/architecture/code review was completed under the instructions in `docs/review-brief-for-partner-agent.md`.
- The full review is stored at `reports/partner-review-2026-07-12.md`.
- Baseline verification at review time: `.venv/bin/python -m pytest src/tests/ -q` reported `55 passed`.
- Review verdict: the Base=borrow / Differentiator=build boundary and thin-slice discipline are sound. The AgentDojo runner should remain a thin borrowed-layer wrapper; no deferred Bucket-B platform machinery was recommended.
- Explicitly confirmed as sound:
  - `bare ASR=0 -> inconclusive`, consistently applied in full-run and session paths;
  - separate `measurement_valid` and `underpowered` fields, with CI overlap failing closed in the basic case;
  - content-addressed manifests and stable canonical JSON rather than a global linear evidence chain;
  - retaining the unobserved `blocks_preserving_utility` definition without fabricating a fixture;
  - the registry audit path `Finding.control_id -> standards_refs -> registered source`.
- Review findings: 3 design, 5 code, 0 discipline findings.
- Issues identified at review time (the later development discussion states that D8 closure is now done; treat this list as review history, not the current implementation backlog):
  1. Differential attrition currently adds only a note; it can still leave `security_delta_assertable=true`. The frozen seam requires a confounded/inconclusive, fail-closed result.
  2. `ComparisonSpec.invariants` currently stores one shared MeasurementContext rather than comparing baseline and treatment contexts. It therefore cannot enforce “only defense_hash may differ”.
  3. A defended Finding can be `pass` solely because ASR is zero even when utility is zero. The security-utility joint verdict remains advisory rather than machine-enforced.
  4. Missing defended utility is classified as `blocks_by_refusing`; it should remain unclassified/utility-unmeasured.
  5. A run-global first-response provenance snapshot can hide served-model or fingerprint drift between bare and defended arms.
  6. `tooling_unsupported` is emitted as reasonless `not_applicable`, conflicting with the frozen ontology: unsupported is a coverage gap, while genuine not-applicable is outside the denominator and requires a reason.
  7. `AiRunRecord.n_runs` is populated with `n_valid`, although the frozen schema defines it as total attempts; summary reports can consequently lose execution-error accounting.
- These findings are not requests to build PlanCompiler, RunOrchestrator, CoverageLedger, ExperimentManager, Claim Engine, or other deferred machinery. Fixes should remain minimal extensions of the existing D8 seams.

## Post-D8 Slice Direction (2026-07-13)

Current status and contract posture:

- D8 closure is complete according to the subsequent project discussion. The next step is not another D8 clean-up pass.
- Synchronize ADRs, fixtures, reports, and documentation for consistency, but describe the result as **`D8 v1 AI-slice baseline`**.
- Do not claim that D8 is already a stable cross-domain contract. Its generality remains **provisional** until a deterministic config-inspection slice validates or breaks the current Finding/Evidence/Assurance shapes.
- `Finding.status` remains a single-control/security-axis verdict. A defended PI Finding may correctly be `pass` when ASR is zero even if utility is zero; consumers must not interpret that as a defense-level pass.
- The report/comparison layer owns the non-advisory security-utility joint verdict. `tradeoff_class` remains advisory and must not become the gating mechanism.
- Joint-verdict rules read raw comparison inputs independently of `tradeoff_class`. The highest-priority inconclusive gate includes measurement/comparison invalidity, underpower, differential attrition, required metrics unmeasured, and utility confounding. The confound predicate is `bare_utility <= U_FLOOR` together with an unsaturated/uncertain bare attack (`bare_asr_ci_low` absent or `< TAU`). This prevents target weakness from being misattributed to the defense.
- If a verdict is about attributable defense effect, utility confounding yields `inconclusive`. A future deployment-acceptability verdict is a different target-level concept and must not be mixed into `ComparisonSpec`.

### Slice 2 — Deterministic config inspection

- Slice 2 introduces exactly one new variable: can the existing Finding/registry/scope/assurance contract represent a deterministic `n=1`, no-CI config inspection?
- Selected control: **`CE-UK-FW-03`**, not active-probe `CE-UK-FW-01`. FW-03 checks that inbound traffic follows default-deny or explicitly justified allow rules.
- Selected input: frozen English `ufw status verbose` output. UFW is deliberately chosen for its thin line-oriented `Default: deny (incoming)` evidence; this slice tests the contract, not firewall ecosystem coverage.
- Record the normalized acquisition intent as `LC_ALL=C ufw status verbose`. Consume a fixture first; do not add privileged live execution to Slice 2.
- Minimal outcomes: active + incoming deny -> pass; active + incoming allow -> fail; missing/unknown/truncated format -> inconclusive. `Status: inactive` is inconclusive unless the TargetSnapshot explicitly establishes UFW as the sole authoritative enforcement plane.
- Capability is a code-local provisional bridge, not a reinterpretation of profile plugin identity:
  - control requirement: `CE-UK-FW-03 -> host.firewall.default_policy.inspect`;
  - adapter `ufw_status_verbose` provides that capability;
  - matching is a single set-inclusion check, with no planner, ranking, or registry service.
- Keep `verification.plugin=firewall_default_deny_check` as opaque legacy/profile metadata. Do not use the plugin id as the capability key and do not modify the frozen profile merely for this first instance.
- Let the slice reveal whether a general `verdict_source`, deterministic rule record, or other schema is actually needed. Start with `run_record=None`, `comparisons=[]`, and real RawArtifact -> Observation -> versioned rule -> Finding friction.

### Slice 3 — Side-effect authorization/Executor PEP

- Slice 3 introduces exactly one new variable: authorization and execution-fact handling for a side-effect-capable action. It reuses the contract tested by Slices 1 and 2.
- Use `CE-UK-FW-01` with a code-local provisional requirement `host.network.port_scan` and a thin nmap adapter.
- Build real PEP/policy logic but use fixture-first **MockBackend dispatch**. No subprocess, socket, real network egress, or blast radius occurs in this slice. Real nmap execution is a separate later validation step.
- The minimum path is: structured Action -> canonical policy-relevant hash -> preflight policy check -> pre-dispatch independent re-check -> MockBackend -> ExecutionReceipt + RawArtifactRef -> Ithuriel parser -> Observation -> rule -> Finding.
- Do not accept arbitrary `binary + args` as the policy surface. Prefer a structured `NetworkPortScanAction` (literal target IP, ports, scan profile) and compile a fixed argv template inside the Executor. The allowlist governs action type and argument grammar, not only the binary name; never invoke a shell.
- Restrict this slice to literal IP targets (prefer RFC 5737 test space such as `192.0.2.10`); hostname resolution/DNS rebinding is outside this slice.
- RoE target authorization is mandatory and orthogonal to `verification.requires_approval`. For FW-01:
  - target-scoped RoE authorization is always required;
  - `requires_approval=false` means no additional just-in-time human approval is required;
  - therefore Slice 3 validates authorization and Action-hash-bound policy decisions, not a fabricated human approval flow. Build `ApprovalGrant` only when a genuinely approval-requiring action appears.
- Empty allowed-target scope denies by default. Target outside the authorized host/CIDR, Action mutation after preflight, RoE/policy version change, or disallowed action/parameters must fail before backend dispatch.
- A RoE denial is **`out_of_scope` / `authorization_missing`**, not `unsupported`, `not_applicable`, or `inconclusive`. Prefer no Finding plus a structured coverage gap; until that type exists, record it in `scope.not_covered` without borrowing an incorrect Finding status.
- Mock receipts must state `backend=mock` and `external_side_effects_performed=false`, reference the frozen fixture, and never imply a real target was scanned. Reports remain `assurance_level:none` and apply only to the synthetic fixture target.
- `ExecutionReceipt` is execution fact, not normalized Evidence and never a Finding. Backend output flows through RawArtifactRef and is interpreted only by the Ithuriel parser/rule layer.
- Prefer nmap XML for a machine-consumed fixture if no fixture format is already committed; grepable output is acceptable for a deliberately narrow existing fixture.
- `CE-UK-FW-01` means exposed services are both **identified and justified**. Nmap only identifies open services. Passing the control additionally requires a target-scoped declared/justified service inventory. Observed but undeclared ports -> fail; scan succeeds but no justification inventory -> inconclusive; all observed services declared and justified -> pass. Do not hide a static allowed-port list inside the parser.
- Key Slice 3 tests include: Action hash stability and mutation invalidation; empty/unauthorized target denial; preflight-to-dispatch RoE revocation; no mock dispatch on denial; fixed argv/target consistency; mock receipt honesty; denial recorded as out-of-scope gap; ExecutionReceipt carrying no verdict; and the three service-justification outcomes above.

These slice plans preserve the project discipline: one new variable per slice, fixture-first, build only differentiating contracts/policy semantics, and do not introduce scheduler, IPC, planner, CoverageLedger, or other Bucket-B machines prematurely.

### Verdict provenance and the Claim layer (ADR 0016, merged)

By this point four adjudication shapes are in `main` and validate the differentiator layer across domains: AI prompt-injection probing (non-deterministic), deterministic config inspection (`CE-UK-FW-03`), an active probe behind the Executor/PEP (`CE-UK-FW-01`), and human-review attestation (`CE-UK-SU-03`, ADR 0015), together with a cross-control CoverageLedger (ADR 0014). One Finding/Evidence/Assurance/Ledger shape carries all four with no `ontology_schema.yaml` change.

This slice adds the first code on the differentiator layer's standards-to-assurance-conclusion upper half; earlier slices built the evidence/Finding lower half. It introduces one new variable: a consumer that must assign confidence according to how a verdict was reached.

- **Forcing problem.** `verdict_mode=automatic` collapses three distinct confidence regimes: statistical AI trials bounded by run count and confidence interval, deterministic configuration rules that are bit-reproducible, and active probes that apply deterministic rules to mock execution and are bounded by fidelity. A consumer reading `verdict_mode` cannot tell them apart. Today only `run_record is None` separates AI from non-AI, and the three non-AI shapes bury their provenance under shape-specific keys in the `measurement_context` free dict. A throwaway spike made the brittleness concrete: probe and config both carry `rule_version`, so any key-sniffing extractor must test `execution_receipt` before `rule_version`, or a probe is silently misread as a configuration check.
- **Design reshaped by partner review.** A flat four-value `verdict_source` enum, which ADR 0015 had predicted, is not orthogonal: the adjudication mechanism for AI, config, and probe is the same deterministic rule, only the measurement regime differs, and only human attestation is a genuinely different adjudication authority. The result is a typed, discriminated `verdict_provenance` union with two variants: `AutomaticRuleProvenance` (carrying `rule_version` and a `measurement_kind` of either `statistical_trials` or `deterministic_observation`) and `HumanAttestationProvenance` (carrying `decision_evidence_ref` and `mapping_version`). This dissolves the `rule_version` ambiguity: probe and config map to the same variant and are later distinguished by target fidelity derived from `execution_backend`.
- **Confidence as a narrowed warrant, not a single tier.** A Claim states on what basis a conclusion holds and only for what scope, rather than which kind of automatic it is. `ConfidenceBasis` records `adjudication`, `uncertainty`, and `reproducibility` (each fully exercised by the four fixtures, so typed enums), `target_fidelity` (kept a free string because a `real` value is not yet observed), and free-form `limitations`. A dimension that only one fixture exercises at a single value, notably human-attestation authority which is only ever `unverified`, stays in `limitations` rather than becoming a premature typed axis. `uncertainty`, `reproducibility`, and `target_fidelity` are derived from `measurement_kind` and `execution_backend`, never stored redundantly on the Finding, to avoid the None-versus-zero drift that is this project's most common defect class.
- **A pure-function consumer, not the deferred engine.** `derive_claims(report) -> list[Claim]` only reads the report and never overrides `Finding.status` or `ComparisonSpec.joint_verdict`; it is the minimal Claim deriver, not the Claim/Assurance Engine machine deferred at the post-D8 gate. It fails closed twice: a report with no Finding returns an empty list, never a silent positive claim, which keeps a structured `ScopeGap` honestly deferred; and a Finding whose `verdict_provenance` is absent yields `assessable=false` with no confidence basis.
- **Identity and hashing.** `verdict_provenance` attaches to the Finding with a `None` default and stays out of `finding_id`, preserving the ADR 0004 hash contract. `claim_id` is content-addressed over the Finding id, the provenance, the confidence basis, and the claim scope, so a provenance change changes the claim id rather than silently altering a claim's stated confidence.
- **Discipline.** No change to `ontology_schema.yaml` or the profile; new enums are pydantic advisory only; all six Finding construction sites were backfilled; attestation references the already-stored `att:` evidence hash rather than copying a third record.

Merged as PR #8; tests grew from 128 to 150. Full detail is in ADR 0016.

## Next Discussion — User-Trial Milestone (2026-07-14)

- The previously exposed OpenRouter API key has been disabled. Treat the immediate credential-containment action as complete; any replacement key should use a separate, tightly capped project and must not be placed in chat, logs, or shell history.
- At the next project discussion, stop extending the roadmap from internal architecture alone. Work backward from the nearest milestone at which Ithuriel can be handed to real users for a bounded trial.
- The milestone discussion should define at least: intended trial user and job-to-be-done; the smallest usable workflow and output; installation/onboarding; safe target and RoE boundaries; fixture/mock versus real execution claims; data-egress and credential handling; report/Claim presentation; failure and support expectations; acceptance criteria; and explicit non-goals.
- Preserve the existing discipline while planning the trial: do not manufacture platform modules merely for completeness, do not collapse multidimensional warrant into a misleading single confidence score, and keep `assurance_level: none` until the evidence and fidelity genuinely justify a stronger claim.
- No further design or coding was authorized in this session; resume from the user-trial milestone discussion.
