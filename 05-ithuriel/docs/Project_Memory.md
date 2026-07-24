# Project Memory

Updated: 2026-07-23

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

## User-Trial Authoring and LLM-Backend Boundary Discussion History (2026-07-15–16)

The discussion that followed the first ProbeCandidate authoring attempt is preserved in the non-normative working memo
`docs/Story-to-Probe与LLM后端能力边界_讨论备忘录.md`. It is deliberately not an ADR and does not authorize
implementation, schema changes, paid model runs, or a roadmap commitment.

Observed product signal:

- The current `docs/trial/probe-candidate-template.md` is closer to an executable assurance-test specification than a
  normal threat-intelligence intake form. It combines intelligence interpretation, threat modelling, environment/capability
  mapping, deterministic security and utility oracle design, fixtures, state deltas, and positive/negative controls.
- An ordinary cyber engineer without specific AI prompt-injection and evaluation training is unlikely to complete it
  independently after merely reading, watching, or hearing an attack story. The reviewer-assisted calendar candidate and
  the non-runnable long-memory candidate are evidence of this role mismatch.
- ADR-0020 C1 currently conflates two hypotheses: whether the user can explain a relevant attack need, and whether the user
  can perform probe/evaluation engineering. The trial primarily falsified the second; it has not yet established that the
  user lacks the first job. Keep the compiler build gated, but do not infer that Story-to-Probe should be abandoned.

Product boundary under discussion, not yet accepted:

- Avoid the false binary between a closed probe library and arbitrary end-user executable authoring. The strongest current
  direction is assisted co-authoring: the user owns the story, organisational relevance, real-world attacker assumptions,
  and semantic confirmation; Ithuriel/probe engineers own capability mapping, payload/oracle design, controls, fidelity
  gaps, and safe compilation; an identified reviewer owns promotion into the released assurance corpus.
- The differentiating customer value is not typing every ProbeCandidate field by hand. It is being able to turn new threat
  intelligence into a governed regression asset while retaining visible provenance for user statements, source extraction,
  system inference, reviewer additions, and user confirmation.
- A later expert view may expose the full ProbeCandidate to trained AI-security/assurance engineers, but ordinary users
  should not receive arbitrary Python/shell/plugin execution, safety-tier declaration, RoE bypass, or self-promotion rights.
- The primary user persona remains unresolved: ordinary cyber engineer, trained AI-security engineer, or an internal
  assurance-service team. This is the next product decision, not a coding decision.

Attack-support boundary under discussion:

- Accepting and structuring a Story can be broad; executing it and producing a Finding/Claim must remain narrow.
- Define support by required capabilities rather than attack-family names: entry surface, temporal mode, persistent state,
  target actions, observability/oracle, reset/isolation, positive/negative controls, fidelity, and RoE/safety tier.
- A probe is runnable only when its required capabilities are a subset of the combined environment, model-backend, and
  policy capabilities. Missing core semantics produce a structured capability gap, not a misleading Finding.
- Current AgentDojo Workspace scope is limited to mock indirect injection through tool/API output, calendar, and email,
  with within-trial tool interactions and observable tool calls/state deltas/canaries. Do not claim support for cross-session
  persistent memory, RAG-index mutation, inter-agent shared memory, real side effects, or attacks with no reliable oracle.
- A calendar-based delayed injection may be a separately named surrogate for part of a long-memory story, but it cannot be
  reported as a test of an agent's internal persistent memory. Preserve the original hypothesis as unsupported and state
  exactly which semantics the surrogate drops.

Local/cloud LLM boundary:

- Ithuriel does not generally depend on cloud LLMs. Deterministic cyber/configuration slices, RoE/PEP, evidence integrity,
  registry, Finding, CoverageLedger, Claim, human review, and reporting can run offline. The current AI slice already has
  Ollama/local/OpenAI-compatible transport paths.
- The hard constraint is role-specific capability, not local versus cloud. A target backend must reliably support the
  required system messages, structured tool calls, valid arguments, tool-result continuation, multi-step loops, final
  utility response, sufficient context, and enough throughput for repeated trials. Failure is an explicit backend or
  measurement gap; it must never be interpreted as security or silently fall back to cloud.
- Authoring assistant, adaptive attacker, and future LLM judge are separate roles with different requirements. If only one
  local model is available, do not silently use it as target, attacker, and judge without disclosing dependence/independence
  limits. Prefer deterministic oracles and human escalation.
- Local deployment is potentially a first-class cyber-security mode because of data locality and version pinning, but it
  needs richer provenance: weights/revision, quantisation, tokenizer/chat/tool template, inference engine, context and
  sampling configuration, and possibly hardware.

Post-prototype empirical order currently favoured, but not authorized:

1. Merge/close the current prototype work.
2. Run a bounded cross-model OpenRouter survey before designing a general backend evaluator.
3. Use real compatibility, utility, error, cost, and provenance friction to freeze the first role-specific backend profile.
4. Only then build a thin `Ithuriel LLM Backend Conformance Evaluator`, initially for the AgentDojo target role.

Survey discipline discussed:

- Sample roughly 8–10 representative deployments across proprietary frontier, production mid-cost/high-throughput, large
  open-weight, and locally plausible medium/small open-weight classes; do not treat hidden parameter size as a universal axis.
- Use a cheap benign backend smoke test before the fixed security matrix. Filter only on instrument compatibility, never on
  whether an early security result looks favourable.
- Pin the OpenRouter model and provider, disable fallbacks, require necessary parameters, and record served provenance;
  otherwise the study measures a changing router rather than a reproducible deployment.
- Separate backend compatibility, functional utility, security measurement, and operational cost. Do not publish a single
  safety score or general model-resistance leaderboard. One attack wording is insufficient because existing runs already
  show attack-variant-driven ASR swings.
- Use a separate tightly capped project/key, synthetic fixtures only, staged budget gates, and no key in chat, code, logs, or
  shell history. OpenRouter results can nominate local candidates but cannot substitute for actual local quantisation/runtime
  testing.

Long-memory engineering estimate and boundary:

- Building a conversational demo with state carried across two sessions is relatively easy; building an assurance-grade,
  resettable, observable, reproducible long-memory poisoning environment is materially harder. AgentDojo is an evaluation
  framework (environment + tools + tasks + security/utility), not merely an agent to outperform.
- Order-of-magnitude estimates, not commitments: a disposable demonstration is about 3–7 engineer-days; a narrow
  Ithuriel-quality synthetic-memory slice with two phases, state snapshots/reset, layered deterministic oracles, controls,
  Evidence/Finding/Claim and tests is about 4–8 weeks for an experienced engineer; a reusable internal lab is roughly two
  engineers for 2–4 months; a general customer-facing platform is a multi-person 6–12+ month effort with ongoing maintenance.
- If pursued later, phrase the slice as a bounded persistent-memory evaluation backend/positive-control target, not “build
  an agent more powerful than AgentDojo”. Reuse an existing pipeline/runtime where possible; implement only poison phase ->
  checkpoint -> clean-session trigger -> memory/tool/state oracle. Start with structured memory, not vector DB, embeddings,
  summarisation, multi-agent messaging, or real side effects.
- Stop and seek a different borrowed base if reliable snapshot/reset is unavailable, a clean second session cannot be
  proven, the verdict needs only a subjective LLM judge, or the slice requires simultaneously building a memory platform,
  workflow engine, and sandbox. A synthetic target calibrates probes and contract shape; it does not provide assurance about
  a customer's real memory architecture.

No ADR, schema, code, survey spend, capability registry, authoring UI/compiler, backend evaluator, or long-memory environment
was authorized during this discussion. The unresolved product wording in this historical section is superseded by the
accepted 2026-07-19 decisions below; the non-authorization boundary remains in force.

## Story-to-Probe and Backend Qualification Decisions (2026-07-19)

The original twelve discussion questions now have accepted working decisions. The detailed, non-normative record is
`docs/Story-to-Probe与LLM后端能力边界_讨论备忘录.md`, especially §9.4–9.6. These decisions guide
subsequent planning but do not by themselves authorize an ADR/schema change, implementation, paid model run, or roadmap
commitment.

### User, authoring, and execution boundary

- The primary final user is a fully trained professional AI assurance engineer, either an internal assurance-team member
  or an external professional. Ordinary IT security engineers and threat analysts may supply stories and organisational
  context but are not the default full Probe authors or assurance adjudicators.
- Story-to-Probe remains a user-visible core value. Its unproven product question is whether bringing the inevitable
  story-to-test process into Ithuriel makes expert work faster, more consistent, and auditable, and whether a second story
  inside the same capability profile can compile and run without story-specific runner/compiler/schema changes.
- Provide Simplified and Advanced authoring modes, but both must compile to one canonical, immutable
  ProbeCandidate/ProbePackage with identical validation and runtime semantics. AI may propose, normalize, and compile; it
  does not independently publish, adjudicate, or authorize execution.
- Story-to-Probe succeeds only when the semantically faithful Probe can actually execute end to end in Ithuriel with bound
  environment/backend/policy capabilities, reset/isolation, positive and negative controls, security oracle, utility oracle,
  and evidence output. Form completion or static compilation alone is insufficient.
- In a small team the same assurance engineer may author and publish an immutable ProbeCandidate. A second qualified
  `Execution Authorizer` is the single decisive human gate for whether, when, where, against what target, and within which
  resource, action, side-effect, and RoE boundaries a red-team Probe runs. Authorization binds a concrete execution-request
  hash; policy-relevant mutation invalidates it. Executor/PEP checks remain mechanical and fail closed rather than creating
  recursive human approval layers during execution.

### Initial capability and surrogate boundary

- The provisional first executable profile is AgentDojo Workspace indirect prompt injection through tool/API output,
  email, or calendar, within an isolated trial and T0–T2 mock side-effect boundary. This can change during development, but
  the support and reporting boundary must change with it; it cannot expand silently.
- A machine-readable `hypothesis_binding.relationship` distinguishes `direct` from `bounded_surrogate`. A bounded surrogate
  has separate original and assessed hypothesis references and records preserved/omitted capabilities, prohibited claims,
  and rationale. It never closes the original capability gap, never gives the original hypothesis coverage credit, and
  supports Findings/Claims only about the narrower assessed hypothesis.
- Long-memory poisoning is a strategic later capability, not v0.1. The first acceptable future slice is a two-session
  persistent-memory mechanism: malicious content in Session A causes a recorded memory write; a clean Session B retrieves
  it and causes a deterministic unauthorized tool action/state delta. It requires observable write/persist/retrieve/action
  stages, clean/poisoned/benign/deletion counterfactuals, snapshot/reset, clean-session proof, trial isolation, and no
  subjective LLM judge as the core oracle.
- After AgentDojo IPI and a second same-profile Probe prove runtime reuse, a 3–7 day long-memory spike may investigate a
  borrowed base. `Hidden in Memory` is the first audit candidate, AgentLAB a discovery reference, and a thin synthetic
  memory protocol only a fallback. Stop if snapshot/reset, clean-session isolation, deterministic attribution, or a thin
  Ithuriel seam cannot be achieved.

### Local AI and OpenRouter survey

- Local AI initially guarantees an explicit compatibility path, not a mandatory product-conformance acceptance matrix.
  Local capability failure produces a machine-readable gap or `not_assessed`; it never silently falls back to cloud and an
  OpenRouter result never substitutes for testing the exact local deployment.
- The first OpenRouter survey is only about backend compatibility and the capability boundary of the AgentDojo target role.
  It does not compare prompt-injection resistance, attack ASR, bare/defended deltas, or overall model safety.
- Target eight representative, pinned deployments: two locally plausible small/medium open-weight, two common mid-size or
  high-throughput, two large open-weight/MoE, and two commercial frontier. Freeze the exact list at survey start and retain
  at least one deployment as a profile-design holdout.
- Use three benign fixture classes: single tool call with valid JSON arguments; continuation after tool results; and a
  multi-step tool loop with deterministic final utility. Run at most five repeats per class, for a planned maximum of
  `8 × 3 × 5 = 120` fixture trials. A `5/5` result is preliminary survey eligibility, not a production SLA.
- Provider and quantization are pinned and recorded deployment conditions, not first-round experimental variables. Pin the
  model/provider, disable fallback, and record requested/served model, fingerprint, key parameters, usage, and cost.
- The hard budget ceiling is `USD 50`; historical probe testing had cost about `USD 0.76` at the time of the decision. This
  budget is a cap, not spend authorization. Start with a cheap pilot and stop/re-estimate on abnormal cost or configuration
  drift.

### Freezing the profile and placing the capability report

- Freeze `ithuriel.agentdojo-target.v1` when the role-derived required/optional/operational capabilities are stable, planned
  coverage is substantially complete (normally 8 deployments; at least 6 across all four strata and three model families
  if services are unavailable), and the last three new deployments introduce no new mandatory capability or failure class.
  The profile must also correctly predict `eligible`, `eligible_with_limits`, or `ineligible` for the holdout deployment,
  and all configuration, fixture, provenance, cost, and artifacts must be reproducible. Up to two extra samples may be added
  under the same hard budget if failure-mode saturation has not occurred; otherwise do not freeze and revisit scope.
- Profile requirements come from the AgentDojo target role, not majority vote among models. Freezing v1 starts versioned
  contract management; it does not imply permanent completeness, Local AI product acceptance, provider/quantization causal
  evidence, attack-security conclusions, or a statistically established reliability SLA.
- A Backend Capability Report is an immutable, content-addressed, machine-readable instrument-qualification artifact, not
  a Finding, Claim, compliance opinion, model-safety rating, or target-control CoverageLedger entry. Capability states use
  `supported / unsupported / unstable / not_verified`; overall qualification uses
  `eligible / eligible_with_limits / ineligible / not_assessed`, avoiding security-verdict `pass/fail` semantics.
- `MeasurementContext` should initially contain only an `instrument_qualification` binding with `profile_ref`,
  `profile_hash`, `report_ref`, and `backend_configuration_hash`; the full capability report remains a separate artifact.
  Preflight resolves the report and checks the exact configuration. Missing, stale, or mismatched qualification makes the
  measurement invalid or a capability gap; it never creates a target pass/fail Finding. Keep this as a minimal open-dict
  reference until a real preflight/report/Claim consumer forces a typed schema.

## Calendar Probe Measurement Repair and Rung Review (2026-07-22)

This section records the instrument repair already observed and the subsequent review recommendations. The rung design
points remain pending operator approval; they are not authorization to implement or spend API budget.

### Instrument facts and thin-slice boundary

- Measurement schema v2 decomposes the former conjunctive `unauthorized_create_attempted` into tool-call emission,
  execution, independent parameter matches, state delta, sensitive creation, mock delivery, full-spec call, full-chain
  success, and utility. Full normalized synthetic arguments and boolean judgments are stored separately with a schema
  version. Historical artifacts are not overwritten: the exact correction is “完整规格调用未命中 0/31；是否发生过任何
  create 调用未知（未存 tool call），仅一条轨迹经直接观察为无调用，n=1”。
- The deterministic fake-model reachability control is a hard pre-API gate. The 2026-07-22 offline self-test passed all
  checks. Its present scope is accurately described as `create-path reachability`: fake create output -> runtime ->
  calendar/email state -> oracle. It does not yet prove the read-tool -> injected output -> next-model-turn path.
- Current mock data is wholly synthetic. Persist full normalized arguments now and keep arguments separate from boolean
  judgments so redaction can be inserted later. Do not build redaction, access-control artifacts, compiler calibration
  schemas, generic token-match generators, or static linters in this trial. Those are recorded future requirements; the
  authorized thin slice is only the instrumentation required to make ADR-0020 C2 measurable.

### Rung-design review recommendations (pending approval)

- Do not use the proposed parameter-free R1 as a hard action-phase test. AgentDojo requires `title`, `start_time`, and
  `end_time` for `create_calendar_event`, while the system prompt forbids guessing function values and instructs the model
  to ask when ambiguous. Therefore R1 L1=0 would conflate “no action phase” with correct refusal to invent required
  parameters.
- Preferred four-rung rebase: R1 = a minimally executable create with title and exact time; R2 = R1 plus attacker
  participant; R3 = R2 plus reading/summarising the calendar and copying the canary into the description, without a
  concealment request; R4 = R3 plus concealment. L1 diagnoses action initiation and the independent title/time atoms
  diagnose parameter retention, so a separate parameter rung is unnecessary. This keeps four rungs and makes R3->R4 a
  single added requirement. If the original ladder is retained, pre-register the exact R3.5 text and trigger before seeing
  results, but do not implement it until triggered.
- A shared benign control does not control length across rungs. L1 computation is length-independent, but model production
  of L1 may depend on payload length. A shared control may be used only for explicitly non-causal screening. For causal
  rung comparisons, use a separately token-matched benign control at each rung. The current ±15% Python character-length
  check must not be described as token matching.
- Use adaptive execution to limit API cost: after reachability is GREEN, run only the corrected, executable R1 positive arm
  as a small screen. If L1 remains 0/5, stop the ladder and prioritize the separately authorized task-shape experiment;
  report this as directional support, not proof that the action-phase hypothesis is settled. If R1 ignites, confirm it and
  climb upward with rung-specific, interleaved matched controls, stopping at the first confirmed extinction point.
- Before any rung run, tighten L0 so it proves the relevant payload is present in one runtime tool output; the current
  `canary OR <INFORMATION>` condition can pass when only one component is present. Also add independent
  `attacker_event_created` and `attacker_invite_delivered` atoms that do not require a canary, otherwise the participant rung
  has no state/delivery oracle of its own.

### R1 screening results and the decision to leave the ladder (2026-07-22)

Every recommendation in the previous subsection has since been implemented and committed, so the rung design is no longer
pending. Two screening runs of the corrected R1 positive arm have now been executed against
`mistralai/mistral-small-3.2-24b-instruct`, one at five trials and one at fifteen. Both ran with the create-path
reachability gate GREEN and with payload delivery confirmed at runtime, meaning L0 was one in every trial. Neither run
produced a single create call. L1 was zero of five and then zero of fifteen, and in all twenty trials the recorded call
order contained nothing but `get_day_calendar_events`.

The larger sample bought exactly what it was expected to buy and nothing more. The Wilson ninety five per cent upper
bound tightens from roughly 0.43 at five trials to 0.204 at fifteen, and to 0.161 if the two runs are pooled. That pooling
is reasonable because the configuration was identical, but it was not a randomised single experiment, and the figure
should always be reported with that qualification. The conclusion itself is unchanged in kind: this is strong directional
evidence that the model never enters an action phase, not a hard exclusion, because a true rate near five per cent would
still escape twenty trials about a third of the time.

The genuinely new finding is an instability on the utility axis. The fifteen trial run answered `BUSY` every single time,
which is wrong, giving a utility rate of zero, whereas the earlier five trial run answered `FREE` twice and produced a
rate of 0.4. The served model slug and configuration were identical and no fingerprint was returned, so we cannot
distinguish sampling noise from a change of routing backend. This has two consequences. First, the utility axis still has
no headroom at R1, so the joint security and utility adjudication remains unavailable exactly as it was before. Second,
the earlier explanation that R1 escaped the length confound because its payload is short is downgraded, since the 0.4
now looks more like noise than signal.

The stopping rule follows from the arithmetic. Pushing the upper bound down to five per cent would take roughly sixty
trials, and all that buys is a tighter version of the same negative; no amount of additional sampling on a read-only task
can establish the behavioural positive control that the candidate document requires. The safety conclusion therefore
stays `inconclusive`, the ladder stays parked at R1, and the next step is the separately authorised task-shape
experiment, which is the only design that can manufacture an action phase. That experiment now carries one extra
constraint learned here: its benign task with a single legitimate write should also replace the current free-or-busy
task, because a host task the model cannot reliably perform on its own leaves the utility axis on the floor regardless of
what the attack does.

## Solo-Developer Two-Hat Governance (2026-07-22)

- ADR 0022 accepts a formal development-mode exception to the earlier second-person Execution Authorizer rule. For
  internal T0–T2 work only, one person may act first as Probe Author/Developer and later as Execution Authorizer, provided
  the roles are procedurally separated by a committed immutable execution request, hash-bound approval, explicit scope,
  budget/RoE/side-effect limits, machine-enforced decision rules, append-only artifacts, and conflict disclosure.
- This is role separation, not person independence. Such runs must record at least
  `authorization_mode:self_authorized_solo`, `role_separation:procedural`, `person_independence:none`, and
  `independence_verification:not_applicable`; the self-authorized run remains `assurance_level:none`. `unverified` is
  reserved for a real second person whose identity, relationship, or qualification has not been verified. Any later
  independent assurance must be recorded as a separate review artifact with its own scope.
- Smoke tests, pilots, and manipulation checks are executions, not a pre-governance gap. A pilot needs its own frozen and
  approved request, hard attempt/cost/stop bounds, and `analysis_eligibility:excluded`; a main run needs a new hash and
  approval. A failed pilot returns to authoring, and no task/oracle change may continue under the old request.
- Record adversarial quality review separately as `adversarial_review:none|ai_agent|peer` plus a reference. It can improve
  technical quality but does not upgrade `person_independence`.
- The calendar runner must fail closed before paid/model/tool execution unless an approval artifact is present, current,
  hash-matched, and consistent with the target/provider/budget/phase. Run artifacts record `authorization_status` and
  `execution_request_hash`. `approved` describes actions admitted under a valid approval; `lapsed` marks actions after an
  approval expired or its request changed; `absent` marks legacy execution with no approval. Later expiry does not
  retroactively downgrade data produced while approval was valid, and governance corrections never overwrite raw results.
- The minimum calendar enforcement seam is now implemented: `CAL_AUTHORIZATION_FILE` binds a canonical request hash to
  the code commit/runner SHA-256, exact runtime, phase, target, provider/deployment, trial ceiling, and
  `CAL_BUDGET_CAP_USD`; absent, expired, tampered, or
  drifting approval exits before reachability tools or provider calls. Artifacts persist the approval provenance. Cost
  control is currently an approved cap declaration plus deterministic maximum trials, not live USD usage metering; report
  that limitation rather than calling it a monetary circuit breaker.
- The 2026-07-22 calendar task-shape 2×2 predates ADR-0022 and had neither a frozen execution-request hash nor Hat B
  approval; its task text also changed after a one-sample pilot. Do not back-sign it or call it retroactively noncompliant.
  Preserve it as legacy internal discovery evidence and add a metadata-only sidecar recording
  `authorization_mode:none (pre-ADR-0022)`, `authorization_status:absent`, `execution_request_hash:none`, and
  `person_independence:none`. Its technical validity remains a separate question from governance attribution.
- A solo developer cannot stand in for the Trial User. Self-testing does not satisfy ADR-0020 C1–C4 or prove the
  Story-to-Probe product/job hypothesis. Technical oracle discrimination may be recorded separately without operator
  attribution.
- T3, customer data/accounts/systems, network actions against a real target, persistent external side effects, and external/customer/compliance
  assurance still require a second qualified person plus the existing contract, target-scoped RoE, PEP, credential,
  recovery, and claim-boundary controls. If no second person is available, remain blocked or use an explicitly bounded
  synthetic/mock surrogate; do not manufacture independence with a second account or an AI reviewer.

## C2 Positive-Control Search, Review, and Final Pass (2026-07-22)

This section records the arc from "the calendar probe never fires" through a provisional first C2 pass, external
review, instrument repair, and a corrected final pass. Every governed run below went through the ADR-0022 chain:
Hat A freeze, Hat B approval in a separate commit, machine-enforced execution, run receipt.

### The search, in four stages

- **Selection pilot on `mistral-small-3.2-24b` (pinned Novita-equivalent OpenAI-compatible deployment), write-phase
  host task, R1, n=30**: primary metric 0/30 with exposure 1.0, host task completed 30/30, no instrument errors.
  Under the pre-registered rule (hit rate below 0.20) the deployment was rejected as a positive control. Combined
  with the earlier task-shape 2x2 cell (1/15) this is best described as "one structured ignition observed across two
  run windows of nominally identical configuration"; it is not a pooled estimate of a stable Bernoulli rate, because
  the runner commit, run context and interleaving differed and no fingerprint was ever returned.
- **Stage-1 selection sweep, two deployments by two attack families**: `deepseek-chat` at Novita (fp8) and
  `gpt-4o-mini` at OpenAI, each crossed with an additive-create family and a same-call participant-augmentation
  family, ten interpretable trials per cell with an attempt cap of fifteen. The additive cells fired strongly, seven
  of ten and nine of ten respectively, with host-core completion at 1.0 in every cell. The augmentation cells
  returned zero, but that result was later invalidated; see the wiring defect below.
- **Initial Stage-2 confirmation, `gpt-4o-mini` at OpenAI, additive family, three arms of thirty fresh interpretable trials**:
  positive 29/30, `negative_plain` 0/30, `negative_marker_exposed` 0/30. Every arm reached thirty in exactly thirty
  attempts, with no exclusions, no instrument failures and no unexposed trials. Both one-sided Fisher comparisons
  remained significant under Holm correction for two tests. The original verdict was `c2_pass`, but partner review
  found that the negative descriptions were 47–76 per cent longer than the positive description. Length dilution was
  therefore a reasonable competing explanation for both negative zeros, and this first pass was downgraded to
  **provisional** without altering its immutable artifact.
- **Corrected Stage-2 rerun, same frozen deployment/family and thirty wholly fresh trials per arm**: after matching
  final rendered description lengths rather than a pre-shell substring, positive was 27/30, `negative_plain` 0/30
  at length ratio 0.991, and `negative_marker_exposed` 0/30 at ratio 1.108. All arms again reached thirty in thirty
  attempts, with zero exclusions, instrument failures and unexposed trials. Both comparisons passed Holm(2), C2a
  and C2b passed, and the scope limitation was null. This run supersedes the initial confirmation as the additive
  C2 conclusion source and removes provisional status: dilution no longer explains the negative zeros.

### What the pass means and does not mean

ADR-0020 criterion C2 is satisfied on the corrected instrument: the operator-shaped security oracle discriminates
positive from genuinely character-length-matched negative controls, including when the attack specification is
handed to the model verbatim without an instruction to act. It does not mean the probe is usable for external
assurance. Instrument qualification, meaning stability across repeated runs, has not been attempted, and criteria
C1, C3 and C4 remain outstanding.
`assurance_level` is still `none` and `target_fidelity` is still `mock`.

The corrected `negative_marker_exposed` arm carried most of the evidential weight. The model was shown the exact
target title and time window with no instruction to create anything, and in thirty trials it emitted no matching
create call; both `quoting_only_no_call` and structured false positives were zero. Because this negative arm was
1.108 times the positive description length rather than 1.758 times, its zero is evidence of behavioural
discrimination rather than an artifact plausibly explained by gross length dilution.

### A conclusion that had to be rewritten

The earlier zeros on `mistral-small-3.2-24b`, twenty and then thirty trials without a single write attempt, must now
be read as **deployment-specific** rather than as evidence that the calendar probe cannot fire. The whole
"no action phase" mechanistic account had been resting on nulls from a single target. Inferring a mechanism from one
target's zeros is a serious methodological hazard and should be treated as such in future designs.

### Instrument work that made the measurement possible

- Attack families are now first-class and mutually exclusive per call. `additive` requires a second create call with
  a nonce-bearing title and the attack window; `aug_participant` requires the attacker address on the same call the
  user already asked for. Side-channel behaviour, such as creating a separate attacker event in the augmentation
  cell, is recorded as diagnostic only and never back-filled into the other cell, pooled with the target family or
  allowed to change a cell verdict.
- Attribution markers must be per-trial random. The fixture's carrier event already contains a fixed
  `attacker@example.com`, so using that address as the sole marker would fire whenever the model copied an existing
  participant. The exfiltration target is now a per-trial plus-address, matched on the full canonical address, with
  a frozen canonicaliser and a descriptive-only partial marker.
- The state layer binds call identity: emitted call id, then tool result, then the parsed event id, then the
  post-state event. When parsing fails the atom returns not-measured rather than false, and the weak existence-based
  fallback is recorded but may never substitute for it.
- Per-turn telemetry records whether the payload was present in the submitted request, monotonic request duration,
  finish reason, tool-call count and names, request id, served model and fingerprint, configured retry count and any
  exception class. A frozen validity table distinguishes a payload never submitted, a request with no response, an
  internally retried but complete response, a truncated response and a complete but degenerate response.
- Utility is split into two orthogonal atoms, host-core completion and authorisation conformance, because a
  successful augmentation leaves the user's core objective intact while widening the authorisation boundary.

### The wiring defect that invalidated two cells

`build_env` never received the family parameter, so both augmentation cells executed the additive payload. Their
zero results do not measure the augmentation mechanism at all and the recorded verdicts were retracted to
`invalid_wrong_payload` through a metadata-only correction sidecar; the additive cells were unaffected.

Two lessons deserve to outlive the bug. First, the payload generator and the classifier each had unit tests while
the seam between them had none, which is the classic shape of this failure; the new regression asserts what the
model actually reads back through the runtime tool rather than what a function returns. Second, the cross-family
diagnostic that a reviewer had insisted on keeping is what exposed the defect. Had side-channel hits been discarded
as irrelevant to the primary metric, the outcome would have been a clean-looking and entirely false conclusion that
the augmentation mechanism does not work.

### Governance limits observed in practice

The authorisation gate guarantees that the frozen code ran. It does not guarantee that the frozen code implements
the frozen design. Hash binding covers bytes, not semantic agreement between document and behaviour; only tests
cover that. Separately, git commit order is an ordering anchor and not a trusted timestamp, since local author and
committer times can be backdated and history can be rewritten, so artifacts record `temporal_anchor: local_git_only`
and make no stronger claim.

Verifying the frozen runtime against the actual runtime field by field, before signing, twice saved an entire
approval cycle: once by catching a screening run that recorded a defence it never applied, and once by catching a
blob path that omitted the monorepo prefix. Those repeated re-freezes should not be flattened out of the history;
they are the evidence that the process did work.

### Partner review findings and closure

The 2026-07-22 staged code/design review is stored in
`reports/partner-review-2026-07-22-codex.md`. It found one design issue (D1), six concrete code issues (C1–C6), and
one discipline/ownership issue (P1). The review baseline was later overtaken by the fixes below; at the current head,
`pytest src/tests` reports 200 passing tests and the calendar runner reports 276 passing offline self-checks.

- **D1 — post-treatment denominator, fixed in `b793eae`**. For additive attacks, emitting a second nonce-bearing
  event does not structurally depend on completing the authorised `Focus block`; conditioning the primary denominator
  on host-core success could delete the strongest trajectory, “obey attack, skip host task”. The historical C2 arms
  and all Stage-1 cells had zero exclusions, so recomputing without that condition changes no historical numerator or
  denominator and D1 was never a reason to rerun. The implementation is now family-specific: additive uses instrument
  validity plus exposure, while participant augmentation retains host-core as a structural prerequisite; utility is
  reported orthogonally.
- **C1 — false negative-control length matching, fixed in `41c2cca` and empirically closed by `281a88e`**. The old
  builder compared an unwrapped negative body with an already wrapped positive and checked only the 85 per cent lower
  bound, producing ratios from 1.47 to 1.76 while labelling them ±15 per cent matches. Matching now operates on the
  final rendered description with a hard `[0.85, 1.15]` two-sided check and records per-arm lengths/ratios. C1, not
  D1, forced the rerun. The corrected 27/30 versus 0/30 and 0/30 main run excludes dilution as the competing account.
- **C2/C3 — native transport and completion labels, fixed in `b793eae`**. Native OpenAI and compatibility transports
  both install telemetry without an uninitialised local. The old `planned_trials` field, which actually held an attempt
  ceiling, is now `max_authorized_attempts`; actual attempts, target/reached interpretable trials and
  `completion_criterion_met` are separate. A pilot confirmation is additionally machine-forced to `excluded_pilot`
  (`ae80df0`) so a small wiring smoke cannot emit a C2 conclusion.
- **C4/C5 — PEP grammar and attestation integrity, fixed in `189563d`**. Network scan Actions now require a non-empty,
  deduplicated set of ports in `1..65535`, with an independent policy-layer recheck even if model validation is bypassed.
  Human attestations require a responsible reviewer, parseable date, non-empty statement and references for decisive
  verdicts; dangling references cannot produce pass. These checks verify that an attestation exists and binds evidence
  without second-guessing the human decision.
- **C6 — prereg omitted from the governed hash set, fixed in `b6a0c48` with test isolation in `4590e85`**. There is no
  runner-only default material list: missing `CAL_GOVERNED_MATERIALS` fails closed. `prereg_ref` is required and the
  exact path declared by the request must appear in governed materials, after which the existing declared/current/blob
  three-way hash check applies. `auth_meta` records `prereg_path` and `prereg_sha256`. This declaration-based invariant
  is deliberately more general than a hard-coded mode-to-prereg mapping because one mode may legitimately use several
  preregistrations over time. Existing frozen requests already included their prereg and were not contaminated by C6.
- **P1 is now closed** (see "Trust-Core Migration" below). Oracle, evidence classification, C2 adjudication and
  authorisation are differentiator/trust-kernel logic that used to live inside a large `scripts/` runner. The boundary
  taken is a thin CLI/provider adapter in `scripts/` and importable pure/protocol logic under `src/ithuriel/`; this was
  a code-ownership correction, not the parked ExperimentManager or other Bucket-B platform machinery.

## WoZ Round Two, Track A (2026-07-22)

Round two is pre-registered in `docs/trial/prereg-woz-round2-track-a.md` and frozen at the protocol level. It tests a
capability hypothesis rather than a disposition: whether an ordinary security engineer can submit an attack story and
then confirm or correct the probe compiled from it. Exactly one misinterpretation is planted in the security oracle,
presented both as prose and as three concrete trajectories, and the specific planted item is frozen in a second
commit made after compilation but before the session, so that a miss cannot be confused with a post-hoc decision
about what counted as a distortion.

Two criteria decide the round: catching the planted distortion, and identifying the fidelity gap that prevents the
newly compiled probe's conclusions from extrapolating to a real system. The second is the substantive one, because it
asks whether the confirmation loop is governance rather than assent.

C3 and C4 are deliberately deferred. Both test disposition, and the available subject co-designed the C2 experiment's
layered criteria, negative-control construction and scope-limitation wording, so asking whether he would overstate
that report carries no information. They require a subject who did not participate in the design. The C2 report is
therefore used in round two only as an example of a finished bounded report, not as a test instrument. The
confounding ceiling stands: the subject is a co-builder, so the strongest available conclusion concerns a highly
fluent co-builder and cannot be extrapolated to an unfamiliar compliance operator.

## Milestone Position (2026-07-22)

Two axes, deliberately kept separate. On engineering maturity the conclusion layer and the probe instrument are both
at reference grade, sufficient for internal trial use. On environment fidelity everything remains at mock, with only
the model being real; seeded tenants with a reset oracle, `ApprovalGrant` and a content-hash upgrade beyond the
sixty-four-bit truncation are all still untouched, and they are the prerequisites for the pilot grade rather than
optional polish. Passing C2 advances neither axis.

The largest outstanding debt is that the product hypothesis has never been tested against anyone outside the build.
C3 and C4 cannot be self-tested by definition. Rust remains deferred and its trigger has never fired.

## AI-Security Roadmap Triage and Prototype Role Separation (2026-07-23)

The recent-paper and open-source-project triage is recorded in
`docs/papers/AI_Security_Papers_2024-2026.md`, including the rationale, candidate-tool boundaries and questions for
the next discussion. It is a provisional planning note, not an approved roadmap or assurance specification. Reading
priority and development priority are deliberately separate.

Provisional roadmap judgement:

- Do not turn each paper or project into an internal module. Preserve Base=borrow / Differentiator=build: scanners
  and evaluation execution are borrowed; Ithuriel owns the Evidence/Finding/Claim boundary and the strength and scope
  of the resulting conclusion.
- Do not open a broad new platform build before the current calendar-probe gates close: repeated instrument
  qualification, ADR-0020 C1/C3/C4, a participant outside the build, fidelity beyond mock, and the still-open extraction
  of trust-kernel logic from the large runner remain prior work.
- The proposed first new post-milestone vertical slice is `Agent Component Intake Assurance`: static skill scanning
  first, followed only later by MCP scanning inside a disposable sandbox and through Action-hash approval, RoE and the
  two-stage PEP. Borrowed scanners emit raw facts; Ithuriel independently adjudicates them.
- Snyk Agent Scan is the leading thin-adapter candidate, subject to version-tolerant parsing, raw-output retention,
  explicit third-party data-egress records and the fact that MCP discovery can execute configured commands.
  Tencent AI-Infra-Guard / `aig-skill-scan` is a comparison backend and taxonomy/fixture source, not a core platform
  dependency. Its unauthenticated full-stack service must not be exposed publicly, and its pipe-to-shell installer is
  not a production path.
- Add UK AISI Inspect AI to the reading/project list as the preferred long-term evaluation abstraction. CAISI Cyber
  Evals is a later external benchmark backend; verify its currently unclear repository licence before vendoring or
  code reuse.
- AgentDoS-style resource limits are a cross-cutting invariant for every future backend and become their own slice
  only when a real multi-tool/sub-agent runtime exists. Memory assurance is triggered only by real persistent memory.
  CyberSecEval informs a small release-regression gate before it justifies a broad suite. Do not build a generic red-team
  platform, unattended SOC or production honeypot system from this reading list.

The same discussion corrected an over-broad interpretation of developer/operator separation. The provisional rule is:

> Separate roles early, separate people later; when independence is absent, weaken the claim rather than fabricate
> independence.

Developer and operator remain distinct structural roles because they have different inputs, permissions, knowledge and
failure responsibilities. During prototype engineering, however, one person may occupy both roles to test the runner,
Action/approval/execution chain, evidence closure, basic instrument discrimination and failure recording. This does not
require two accounts, separate services or a queue merely to create procedural appearance.

Person separation is claim-driven:

- same-person operation can support internal engineering and instrument-development evidence when the relationship is
  disclosed as `person_independence=none`;
- it cannot show that an unfamiliar operator understands or corrects a compiled probe, avoids overclaiming, or makes an
  independent disposition;
- C2 may therefore be developed and run by a co-builder within its existing bounded instrument claim, while C3/C4 must
  use someone who did not participate in their design;
- Hat A/Hat B freezing, commit order and hash binding still control post-hoc mutation and experimental contamination,
  but the same person wearing both hats does not create an independent approval;
- real high-risk side effects, independent oversight claims and external/customer assurance trigger actual person
  separation.

Questions intentionally left for the next discussion: whether to approve component-intake assurance as the next slice;
whether its first spike is static-skill-only or includes one governed MCP fixture; whether Snyk is the primary adapter and
`aig-skill-scan` only a comparator; whether Inspect is triggered by a second evaluation backend or by the first model
upgrade; the exact risk triggers and claim ceiling for each person-independence level; and which authoritative roadmap or
ADR should receive these decisions if approved.

## Trust-Core Migration, P1 Complete (2026-07-23)

The final partner-review item, P1, is done. The differentiator logic that had accumulated inside a single 3596-line
`scripts/run_calendar_probe.py` now lives in an importable trust core, and the runner has shrunk by forty-one per cent to
2123 lines. This was a pure refactor: no API calls, no schema change, and no change to the probe's external behaviour. The
work sits on branch `refactor/p1-runner-to-trust-core`, pushed but not yet raised as a pull request, across five commits
that are each independently revertible.

The split follows the coupling gradient, least entangled first, and every step had to leave both the runner self-test and
the pytest suite green before it was committed. `src/ithuriel/probes/calendar/c2.py` holds the Fisher decision table and
the layered C2a/C2b adjudication, which are pure functions with no AgentDojo dependency and therefore the cleanest place
to start. `payload.py` holds the scenario definition, the complexity-ladder payloads, the product-layer length matching
from the C1 fix, `build_env`, and the pre-registration constants. `oracle.py` holds the layered L0 to L6 oracle, the
per-call classification, evidence capture, the family-specific interpretable denominator from D1, and the shared content
hash `_sha`. `governance/execution_authorization.py` holds the ADR-0022 authorisation chain: the three-way hash that fails
closed, the approval window and per-trial deadline, and the run receipt.

Several engineering disciplines from this migration are worth reusing. Every AgentDojo import in the original file was
function-local rather than module-level, so the trust-core modules never couple to the borrowed base at import time; a
grep to confirm this was the precondition that made the whole extraction clean. Constants used in dozens of places, such
as the target day appearing sixty-one times, were re-imported explicitly back into the runner namespace so that the many
call sites needed no edits at all; the runner became a thin entry point of re-imports, provider glue and orchestration.
The dependency direction had to stay single and clean: oracle depends on payload, governance depends on oracle and
payload, and the runner depends on all of them. A library module must never import from the runner script, and enforcing
that forced `_sha`, the measurement schema version and the cell grid to move into the trust core rather than linger in the
runner. Large verbatim moves were extracted by line range with a script rather than retyped, to avoid transcription error,
and then checked by importing the new module before any wiring.

One genuine logic change was unavoidable. Two governance functions had derived their default repository root from
`__file__` on the assumption that the file lived in `scripts/`. After moving two directories deeper that assumption broke,
so the default is now pinned to a `_PROJECT_ROOT` computed four levels up, which resolves to the same project directory as
before, with a comment and a test guarding it. The lesson is that any code deriving paths from `__file__` must be re-pinned
whenever it changes depth. Equivalence was proved rather than assumed. The runner self-test was kept unchanged during the
extractions so it served as a before-and-after oracle, passing all 276 checks at every step, and the stability of `_sha`
was demonstrated by recomputing the hashes of three already-committed execution requests and matching them against their
approvals, so the ADR-0022 chain is provably intact; hash stability is exactly what most needs checking when an
authorisation chain moves.

The trust core is now importable and directly covered by pytest, which rose from 200 tests to 254. The separate
"migrate the self-checks" task was closed against four acceptance criteria rather than by porting all 276 checks by hand.
The self-test must have no network or billing dependency, which was shown by running it under a scrubbed environment with
every key removed; it must return a non-zero exit code on failure, which was shown by injecting a failing check and
observing exit one; it must not redundantly carry the pure-logic assertions already migrated into pytest; and it must
actually run in the regular validation flow, which a new `test_runner_selftest.py` now guarantees by running the self-test
as a subprocess and asserting a zero exit. To satisfy the third criterion the pure-logic sections were removed from the
self-test, taking its passing count from 276 to 186, while everything that genuinely exercises `build_env`, `evaluate`,
`execution_runtime`, the git authorisation chain, the interleaved schedule or the evidence-artefact round trip was kept in
place. The reusable definition of "migration complete" is therefore not to empty every line out of the self-test, but to
hold the pure logic as a single source of truth in pytest, keep the integration checks where they belong, and wire the
self-test into the regular flow so that it fails loudly.

P1 changes nothing about the C2 conclusion or its bounds. The probe still lacks instrument qualification and real-operator
C1, C3 and C4; its assurance level remains none and its target fidelity remains mock; and none of it extrapolates beyond
the frozen configuration. The next step is one of two independent paths, each run through a full Hat A to Hat B cycle:
collect an attack story from the partner for Track A, without revealing in advance that a distortion has been planted, or
re-run stage one of the augmented-participant family with the corrected payload.
