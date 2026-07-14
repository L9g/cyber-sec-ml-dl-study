# Ithuriel: how it works, and how it is built

> The name comes from the angel in Milton's *Paradise Lost* whose spear, at a single touch, forces anything false back into its true shape. This project sets out to do the same to software: to make the hidden failures of AI systems and conventional systems reveal themselves, and then to set those findings down as conclusions that survive scrutiny.
>
> This document is written for outsiders. It assumes you have read none of the repository's architecture decision records or internal discussions. By the end you should be able to answer three questions: why the project exists, what its central discipline is, and how the code is organised around that discipline.
>
> A Chinese edition of this document lives alongside it at `docs/DESIGN.md`.

---

## 0. In a line: what it is, and what it is not

**What it is.** A security-and-compliance agent built around a single purpose: assurance, and the adversarial discovery of failure. It distils security standards into a machine-readable ontology, drives off-the-shelf scanning and probing tools against a target system, and then condenses the raw output of those tools into a conclusion that is auditable, reproducible, and honest about its own boundaries.

**What it is not.** It is not another security-scanning platform. Every scanning and probing capability is borrowed from mature tools. The project builds only two things of its own: the distillation of standards into an ontology, and the layer that carries evidence, findings, and assurance conclusions. The value sits in the conclusion, not the plumbing; the plumbing is merely the thing under audit and the means of execution.

That boundary governs every design choice that follows, which is why it comes first.

---

## 1. The missing layer

In agentic security and AI assurance, the scarcest thing today is not tools. It is the layer that carries you from "a tool was run" to "here is a bounded, reproducible, auditable conclusion about an unfamiliar system."

Several signals from the field bear this out. Security benchmarks are badly fragmented; a great many results are run only once, with no reproducible measurement context, so a change of seed or a change of image is enough to move the score. A recurring finding in the literature is that model alignment does not, on its own, make an agent safe, which means evaluation has to be designed from an assume-breach posture. Put plainly, a heap of scanners and red-team tools is not sufficient. What is genuinely rare is the procedure that turns their output into a conclusion: under what measurement conditions the conclusion holds, whether its evidence can be replayed by someone else, and precisely what it does, and does not, claim.

That layer is what Ithuriel exists to supply. Borrow the tools; build the conclusion.

---

## 2. Two layers: borrow the base, build the difference

One discipline governs the whole project. Grasp it, and every module's design trade-off falls into place.

**The base is borrowed.** Execution mechanisms, inter-process communication, scheduling, and every scanning and probing tool are taken from mature implementations. If it can be borrowed, it is not built. Injection probing borrows AgentDojo and published defences; port scanning borrows nmap; firewall-configuration reading borrows the system's own `ufw`; injection detection borrows an off-the-shelf prompt-injection classifier from the `transformers` ecosystem. To this project, these things are simply trustworthy objects-under-audit or means of execution. Rewriting them would serve no purpose. The boundary wants drawing precisely, though: what is borrowed is the execution mechanism, whereas turning the execution seam into an enforcement point is the project's own work. Any side-effecting action passes through the two-phase policy enforcement point in `executor.py`, which enforces Rules of Engagement authorisation, a command allowlist, and an independent pre-dispatch re-check. Those safety and assurance semantics are built, not borrowed.

**The difference is built.** The project invests deliberately in exactly two places. The first is distilling standards into an ontology: turning bodies of rules such as Cyber Essentials, the NIST Cybersecurity Framework, and the OWASP LLM Top 10 into a machine-readable, code-consumable registry of controls and standards. The second is the evidence, finding, and assurance layer, which is the set of objects described in section 3.

**Plugins are thin adapters.** A plugin's only job is to call an existing tool and normalise its output into the common evidence schema. It never hand-rolls bespoke scanning logic for a particular control. A control with no tool to run it is not forced through; it is recorded, honestly, as a coverage gap.

One guard-rail deserves emphasis: a minimal base is not a toy base. The base is borrowed up to the point where a practitioner in the field would nod, no further and no less. The discipline is restraint, not corner-cutting.

---

## 3. The objects that do the work

This section describes what the "built" half actually builds. Every object is defined in `src/ithuriel/models.py`, written with pydantic v2, and its field shape was reverse-engineered from the real friction of real runs rather than designed all at once from a paper.

**Three grades of evidence: Raw, Observation, Finding.** The raw text a tool emits is Raw. Parsing that into a structured reading is an Observation. Only the adjudicated result of one control against one target is a Finding. The three are never flattened into one, because their trustworthiness and their reproducibility requirements differ.

**A Finding has four states.** A Finding's `status` may take exactly four values, each with a strict meaning:

- `pass`: the control is satisfied.
- `fail`: the control is not satisfied. This state must carry both a `rationale` and a `severity`, or construction raises an error outright.
- `not_applicable`: the control does not apply to this target. It is removed from the coverage denominator, and it too must carry a rationale explaining why it does not apply.
- `inconclusive`: the evidence is insufficient to adjudicate. It calls for a re-run or escalation to a human, and it must carry a rationale.

These are not gentlemen's agreements written into documentation. They are hard rules inside a pydantic validator. Construct a `fail` with no rationale and the program throws on the spot.

**Three verdict modes.** How an adjudication is reached is orthogonal to the result itself. `automatic` means a deterministic detector, `llm_judge` means a large model acting as referee, and `human_review` means a person. These are three distinct sources of a verdict.

**AiRunRecord.** An AI probe is non-deterministic; the same attack run ten times may give ten different outcomes. So every AI Finding carries a run record: the model identifier, a version snapshot, the temperature, the seed, the number of attempts, the number of valid trials, the number of execution errors, the number of successes, the success rate, and a Wilson confidence interval. A deterministic check has no such record, and there `run_record` is simply `None`. As we will see, that `None` carries a great deal of meaning.

**ComparisonSpec: a delta is not a Finding.** The measure of a defence's effect, such as how far injection success drops once a detector is added, is at heart a comparison across two Findings, one bare and one defended. So it is modelled separately as a `ComparisonSpec`, not stuffed into a single Finding. That comparison object carries only the delta; it never re-adjudicates. It is also obliged to report the security and the utility axes as a pair, never the security axis alone.

**joint_verdict: adjudicating security and utility together.** A defence may well suppress the injection, at the price of destroying the target's ordinary ability to do its job. A Finding that looks only at the security axis would misreport that case as a pass. So the comparison layer carries a joint verdict field, always populated, taking one of `acceptable`, `security_failed`, `utility_failed`, or `inconclusive`. It is computed independently from raw inputs, and it deliberately declines to read the trade-off classification, whose thresholds shift with experiment. The point is to keep an unstable taxonomy from steering the verdict backwards.

**EvidenceManifest: a content-addressed record.** Each trial's raw record is addressed by its content hash, and those gather into a single run-root hash. Raw evidence cannot be overwritten and cannot be flattened. Identical inputs yield an identical run root, which is the contract for bit-level reproducibility.

**ScopeStatement: writing the boundary into the structure.** Every report carries a scope statement, and pinned inside it is the line `assurance_level: none`. Its purpose is to stop a demonstration being misread as a compliance pass. The scope statement also lists what entered the coverage denominator and what went uncovered, and it seeds the CoverageLedger described later.

**Registry: giving a schema invariant teeth.** A control cites a standard, say a control that cites OWASP LLM01, and every cited standard source must be genuinely declared in the profile's standards registry. When the registry loads, a validator checks exactly this, and a dangling reference raises an error. The schema invariant thereby grows teeth, rather than remaining a line of prose.

The outermost envelope is the `AssuranceReport`, which packages the whole of one run's "built" output: the measurement context, the evidence manifest, the Findings, the comparisons, the scope statement, and the resolved control together with the standards it cites. A whole session spanning many measurement conditions packages up one level further, into a `SessionReport`.

**verdict_provenance, Claim, and confidence_basis: the upper half, from standards to conclusion.** The objects above carry the "evidence and Finding" half; the other half runs from evidence to conclusion. The source of a verdict is promoted to a typed field, `verdict_provenance`, which splits open the muddled `automatic` of `verdict_mode`. A statistical AI probe, a deterministic configuration rule, and a side-effecting active probe were all called `automatic` in the old model, yet their regimes of confidence are not the same, so a discriminated union tells them apart: an `AutomaticRuleProvenance` carrying a `measurement_kind` (statistical trials, or a deterministic observation), and a `HumanAttestationProvenance` pointing at the evidence and mapping version of a human verdict. Above that sits a pure-function Claim layer, `derive_claims` in `claim.py`, which consumes each Finding into a `Claim` that answers on what basis a conclusion holds and only for what scope. The warrant is not a flattened single confidence score but a multi-dimensional `confidence_basis`: adjudication mechanism, regime of uncertainty, grade of reproducibility, target fidelity, and an honest list of limitations. This step is deliberately fail-closed: a report with no Finding returns an empty list rather than a positive Claim, and a Finding lacking `verdict_provenance` is marked unassessable rather than given an optimistic grade. It is the thinnest possible upper half of the differentiator layer, a pure function and nothing more, no engine.

---

## 4. Teeth

If section 3 is "what the objects are," this section is "why they can be trusted." Each invariant below comes with a counter-example, a "what happens if you don't," because a counter-example is the clearest way to show why the rule exists.

**The honesty gate, `assertable`.** Whether a defence delta may be asserted at all is decided by one conjunction:

```
assertable = measurement_valid  and  (not underpowered)  and  (not confounded)
```

`measurement_valid` requires the measurement itself to be sound, for instance that a positive control exists and that quota did not truncate the run. `underpowered` requires the confidence intervals not to overlap so much that no difference can be seen. `confounded` requires that nothing differs between the two arms except the treatment, the defence, itself. Fail any one, and the harness refuses to report a delta and states the reason for invalidity instead. Without this gate, a run whose confidence intervals overlap heavily would still be reported as "defence effective, delta minus nought-point-one," and a reader would mistake pure noise for a conclusion.

**A bare success rate of zero should be inconclusive, not a pass.** This is the project's most counter-intuitive rule, and the one that best states its posture. If an injection attack scores zero on a bare target with no defence at all, the correct conclusion is "no verdict," not "the target is safe." A rate of zero may simply mean the attack variant was too weak, or that this target happens to be robust to this family of attacks; without a positive control, safety cannot be inferred. Treat a bare zero as a pass and a target that was never effectively attacked walks away with a false certificate of safety.

**`unsupported` differs from `not_applicable`, and they go in opposite directions.** A control with no tool to test it is `unsupported`; it enters the coverage denominator, recorded as a gap. A control that simply does not apply to this target is `not_applicable`; it leaves the denominator. Mislabel "no tool" as "not applicable" and a real coverage gap vanishes from the denominator, flattering the coverage figure.

**Security and utility must be adjudicated as a pair.** See `joint_verdict` in section 3. Report the security axis alone and a defence that "aborts the task the moment it detects an injection" looks perfect, when in fact it has traded away all usefulness and completed not a single task.

**Comparisons fail closed.** The moment the confidence intervals overlap, or the two arms' provenance drifts, for instance a rolling alias that points at a different model snapshot between runs, the harness refuses to assert. It marks the run underpowered, or flags a context-invariant mismatch, and never invents a delta. Leave provenance drift unchecked and you have subtracted the scores of two different models while claiming to measure a defence.

**Content-addressed, stable hashes.** A Finding's id is derived from the content of its adjudicating fields, and the evidence manifest's run root from the whole set of raw artefacts. Identical inputs give identical hashes, so a third party can replay and check a conclusion. Use a timestamp or an auto-incrementing number as the id, and two identical runs earn two different labels, and reproducible checking becomes impossible.

---

## 5. One model, four shapes, no schema change

The strongest argument for the built layer is that one set of objects carries four wildly different kinds of adjudication, without adding or altering a single schema field for any of them. The four end-to-end slices are these.

| Slice | Control | Shape of adjudication | Domain | Severity | Verdict mode |
|-------|---------|-----------------------|--------|----------|--------------|
| 1 | AI-AGENT-PI-01 | non-deterministic AI probe (mock environment) | ai_agent_security | High | automatic |
| 2 | CE-UK-FW-03 | deterministic config reading | network_security | Medium | automatic |
| 3 | CE-UK-FW-01 | active probe, with an execution and authorisation machine | network_security | Medium | automatic |
| 4 | CE-UK-SU-03 | human review, declarative evidence | security updates | Low | human_review |

These four slices span three domains, three severity grades, and two verdict modes. They cover a non-deterministic statistical probe, a deterministic configuration read, an active probe with side effects, and a human declaration with no tool output at all. All four are carried by the same Finding, Evidence, Assurance, and CoverageLedger objects.

The telling observation is how gracefully the "empty" places are accommodated. A deterministic check has no AI run statistics, so `run_record` is `None`. A configuration read is not a defence experiment, so `comparisons` is an empty list. A human review's evidence is a structured declaration record, not tool text. Not one of these cases forced a new field, which is the sign that the model was pitched at the right level of abstraction.

That is the phrase to dwell on: **no schema change**. Four kinds of adjudication that feel, intuitively, very far apart, one a non-deterministic statistical probe, one a human's signature, with a deterministic config read and a side-effecting active probe in between, and yet when they land in the same objects, nothing has to be cut into the schema. That is where the real weight of this section lies.

It needs saying, equally, that this does not mean "the schema is now frozen forever." Quite the opposite. The project's discipline is to evolve the schema in step with real friction: when the friction arrives, the schema changes, and section 7 is devoted to that method. So read the achievement precisely. It is not that the schema is immutable; it is that these four adjudication shapes themselves forced no change at all. What did eventually force a change was building a consumer on top of them, the Claim layer, and section 7 tells that story: what forced the change, and how it was added within the discipline.

One point about fidelity deserves precision, too. The "mock environment" tagged against slice 1 in the table means the AgentDojo tool environment is a mock; it does not mean the model is a fake. Environment fidelity and model transport are two orthogonal axes, and a mock tool environment can perfectly well sit behind a real remote model API, with real token cost and real data egress to match. Section 8 returns to this when it covers running the tool.

---

## 6. A walk through the code

The "built" half is roughly two thousand lines of Python across twelve modules, ordered here most-central first:

- `models.py`: the body of the schema; every object and every invariant check lives here.
- `derive.py` and `derive_session.py`: turning the flat JSON of real AI runs into structured Findings and session reports.
- `registry.py` and `capability.py`: reading the controls and standards registry from the profile, and performing one capability match.
- four thin adapters, `config_inspection.py`, `port_scan.py`, `executor.py`, and `attestation.py`, one per shape of adjudication.
- `ledger.py` and `provenance.py`: coverage roll-up across controls, and the pinning of provenance.
- `claim.py`: the Claim layer, consuming Findings into assurance conclusions that carry a `confidence_basis` (a pure function, no engine).

What follows walks the full chain of slice 2, the firewall default-deny configuration read. It is chosen because it is deterministic, needs no API key, replays offline, and because its source is dense with `# FRICTION:` notes, which conveniently double as a preview of the method in section 7.

One thing needs saying plainly, to avoid a misreading. Slice 2 is chosen only because it teaches most cleanly; it is not the project's marquee. The project's real signature shape is the AI red-teaming probe from section 1: cold-starting against an unfamiliar AI agent and drawing out its injection flaws. The firewall read plays the part of a proof, showing that the same assurance layer carries even a deterministic check cleanly. The marquee draws attention; the assurance layer's generality across four shapes is what makes it stand up. The two should not be confused.

The chain is five steps, all strung together in `build_report` inside `config_inspection.py`.

**Step one: capability match.** The control `CE-UK-FW-03` declares that it needs one capability, `host.firewall.default_policy.inspect`, and the `ufw` adapter declares that it provides it. The match is a single test of set containment:

```python
def adapter_satisfies(control_id, adapter):
    reqs = required_capabilities(control_id)
    return bool(reqs) and reqs <= adapter.provides
```

This is deliberately not a planner. There is no ranking of candidates, no argument planning, no plugin registry. One control, one requirement, one adapter, one subset test, and no more. No match, and it returns a coverage-gap report and produces no Finding.

**Step two: parse Raw into an Observation.** `parse_ufw_status` is a pure function that reduces the raw text of `ufw status verbose` to three fields: whether the firewall is active, what the inbound default policy is, and whether the default-policy line is present. It reads only those two lines of core evidence and parses none of the remaining rule detail, because this slice adjudicates the default policy alone.

**Step three: a deterministic, versioned rule adjudicates.** `evaluate_default_deny` maps the Observation to a status and a rationale. Here the same discipline from section 4 shows through. If UFW is inactive, the function returns `inconclusive`, not `fail`, because an inactive UFW does not prove the host has no default-deny policy; nftables or a cloud security group may well be enforcing one. Only when the target snapshot explicitly declares UFW to be the sole authoritative enforcement surface does it return `fail`. The absence of a positive signal is not a negative conclusion, which is the very same epistemic rule as the AI slice's "a bare success rate of zero yields inconclusive."

**Step four: assemble the Finding, and watch whether `None` is accommodated.** The crux is a single line:

```python
finding = Finding(
    ...,
    run_record=None,   # a deterministic check has no AI run
    root_causes=None,  # root causes are an AI-mechanism enum, and do not apply to a firewall
)
```

A model designed for an AI probe, reused by a deterministic check, accommodates the case naturally with `run_record=None` and forces out no new field. This is the micro-level evidence for the cross-domain argument in section 5.

**Step five: package the AssuranceReport and write the scope statement.** Because this is not a defence experiment, `comparisons` is an empty list, and the semantics are complete. The report also carries the resolved control and the standards it cites, Cyber Essentials and the NIST Cybersecurity Framework, so the audit loop closes: from the Finding's `control_id`, to the control's `standards_refs`, to each source's genuine entry in the registry.

**A note on testing.** The project has two layers of tests, deliberately kept apart. Deterministic code contracts use pytest unit tests, pinned to exact values and boundaries. Narrative regressions, which depend on model scores, use only directional assertions with a margin, and hard thresholds are forbidden, because scores drift with seed, version, and image. There are 150 test functions in all, and the deterministic-slice portion runs entirely offline, with no external dependency.

---

## 7. Let friction decide the schema

The project holds one discipline throughout its schema design: run the thinnest possible end-to-end slice first, let the real friction of a real run decide what fields to add, and never lay out every field in advance from a paper.

The reason is that a field designed in advance is wrong nine times in ten. The shape of real data, the real difficulty of scoring, the real problem of reproducing a result: these surface only after one slice is running. So `models.py` states at the top that it takes only the ontology schema's required fields plus the fields a real run genuinely used, and that the frozen or parked fields, such as threat model, fidelity gap, and llm-judge, are left out entirely.

One case shows the force of this discipline better than any other, and it concerns a single field: the source of a verdict. It was held back deliberately for a long time, and then forced out, at the right moment, by a real consumer. The two phases together say more about the method than either would alone.

The background runs as follows. Section 3 noted three sources of a verdict: a deterministic rule, an AI run, and a human review. By the fourth slice a pattern was plain. Each shape of adjudication stashes its verdict source in a different place. Only the AI slice has a typed home for it, namely `ai_run_record`; the other three, a rule-version string, an execution receipt, and a review record, are all tipped into the free-form `measurement_context` dictionary. A unified field for verdict source all but demanded to be written, and the signal had been confirmed, four slices over, four times.

The habit of many projects would be to abstract the moment a signal is that strong. At the time it was deliberately not added. The reason: back then, not one downstream consumer had broken for want of the field. The CoverageLedger reads only `status`, `verdict_mode`, and `severity`, and all four shapes run through it. The discipline of letting friction decide the schema demands exactly this restraint: however strong the signal, so long as no real consumer has been driven to the point of needing to tell verdict sources apart, the field is not added.

The consumer duly arrived, the field went in, and the manner of its going in was itself a demonstration of the discipline. What forced it was the Claim layer from the end of section 3: a consumer that has to assign different warrant according to how a verdict was reached, and without the structure it had no choice but to rummage through the free-form dictionary under a different key for each shape, an extraction brittle enough to break on contact. (A real instance of the trap: the active probe and the configuration read share one key, so recognising them by rummaging is order-dependent, and a step out of order reads a probe as a configuration check.) That was the real friction that forced the field. Two choices at the moment of adding it were deliberate. First, not a flat four-value enumeration but a typed discriminated union, `verdict_provenance`, because the four candidate values are not orthogonal: the adjudication mechanism of the AI, config, and probe shapes is in every case "a deterministic rule acting on a measurement," and what truly differs is the measurement regime beneath; only human review is a genuinely different adjudication authority. Second, the warrant the consumer produces is not a flattened single confidence grade but a multi-dimensional profile, because collapsing coverage, evidence quality, and target fidelity into one number recreates the very "green light but nothing really tested" problem. The whole change lands in pydantic's advisory layer, and the read-only ontology schema has still, to this day, not had a single field altered.

Writing both halves into a design document, first "we saw a strong signal and still held fire," then "we moved only once a real consumer forced it, and even then we held the shape and the restraint," is meant to show the reader that this method is not a slogan. The project's sixteen architecture decision records, 0001 through 0016, form one continuous arc of decisions, recording at each step what friction was in play and what field was, or was not, added. They are the traceable evidence for the discipline.

---

## 8. Status, and how to run it

**Where it stands.** All four slices are merged into the mainline and the tests are green, 150 test functions in all. The built layer has demonstrated its cross-domain generality across four shapes of adjudication and four controls, and the cross-control CoverageLedger has begun. On top of that, the upper half, from standards to conclusion, has landed its thinnest layer: a typed `verdict_provenance` and a pure-function Claim layer producing a multi-dimensional warrant (sections 3 and 7). That layer has also been exercised against real models once: across a multi-target run, the system refused to read a bare zero success rate as "safe" where no positive control existed, and refused to assert a defence delta where the two arms' provenance fingerprints had drifted, failing closed in both cases rather than fabricating a conclusion. It bears saying clearly that the project is still at the slice-validation stage. What it has validated is that the shape and the discipline of this conclusion layer hold up, not that it is a finished, polished platform. What has landed is the thinnest pure-function Claim layer; a full Claim and Assurance engine, which must handle applicability, claim subject, time validity, and assessor independence rather than merely rolling up several Findings, together with fanning out across more controls, scenarios, and attack families, remains on the road ahead.

**Environment.** Dependencies are managed with `uv`, and Python 3.11 or later is required. Once the environment is synced, the tests run:

```bash
uv sync
.venv/bin/pytest
```

The deterministic slices, config reading, port scanning, and human review, run wholly offline, need no external service, and consume the frozen fixtures in the repository directly.

**The AI slice.** The non-deterministic injection-probe slice needs a large model capable of tool calls, that is, function calling. The harness is provider-agnostic: choose a provider through the `D8_PROVIDER` environment variable, then place that provider's key in the environment variable it expects. Presets ship for OpenAI, Gemini, Groq, OpenRouter, DeepSeek, Together, Mistral, Anthropic, and Cohere, and local models and any compatible endpoint are supported too.

The general pattern is "choose a provider, give it a key, name a model":

```bash
# General form: swap D8_PROVIDER and its matching <PROVIDER>_API_KEY
D8_PROVIDER=<provider> <PROVIDER>_API_KEY=<key> D8_MODEL=<model> \
  .venv/bin/python scripts/run_bare_vs_defended.py

# Example: an aggregator endpoint
D8_PROVIDER=openrouter OPENROUTER_API_KEY=<key> D8_MODEL=<model-slug> ...

# Example: a local model, no key at all
D8_PROVIDER=ollama D8_MODEL=llama3.1 ...   # run ollama serve first

# Example: any OpenAI-compatible endpoint
D8_PROVIDER=custom D8_BASE_URL=<url> D8_API_KEY=<key> D8_MODEL=<model> ...
```

If a known provider's key is already present in the environment, the script will auto-detect and use it, and `D8_PROVIDER` may be omitted. The one hard requirement when choosing a model is that it can perform tool calls reliably, because AgentDojo's agent loop depends on function calling.

Once running, it performs one grid of bare-target against defended-target, emits flat JSON, and lets `derive.py` reverse-engineer that into structured Findings and comparisons. The thing to watch is that the harness reports, at every step, whether the measurement is valid, and never fabricates a number to manufacture a flattering delta. That is exactly where the invariants of section 4 come to ground in a real run.

---

## Further reading

- `README.md`: the project's positioning and its two product lines.
- `docs/architecture-seams-D8.md`: the coding-seam contract, the authoritative division of "which interfaces are fixed now, and which wait for friction."
- `docs/adr/`: the complete arc of decisions, 0001 through 0016.
- `docs/ontology_schema.yaml` and `docs/UK_Region_Profile_v0.2.yaml`: the schema and machine-readable profile that the built layer consumes read-only.
- `docs/DESIGN.md`: the Chinese edition of this document.
