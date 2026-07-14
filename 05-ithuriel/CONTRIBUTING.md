# Contributing to Ithuriel

Thanks for your interest. Ithuriel is an assurance-oriented security and compliance Agent, and it is deliberately opinionated about what it builds and what it borrows. Reading `docs/DESIGN.md` (or `docs/DESIGN.en.md`) first will save you time, because most review feedback comes back to the disciplines below.

## Development setup

Dependencies are managed with `uv`, and Python 3.11 or newer is required.

```bash
uv sync
.venv/bin/pytest
```

The deterministic slices (config inspection, port scanning, human review) run fully offline against frozen fixtures and need no external services or API keys. Only the non-deterministic AI injection slice needs a tool-calling model; see the run instructions in `docs/DESIGN.md`.

## The disciplines we hold contributors to

These are not style preferences. They are the reasons the project exists, and a change that violates one will be sent back regardless of how well it is written.

- **Borrow the base, build the differentiator.** Execution mechanisms, scanners, and probing tools are borrowed from mature implementations. The project only builds two things: the distillation of standards into a machine-readable ontology, and the evidence, Finding, and assurance layer on top. Do not rewrite a scanner, and do not hand-roll a bespoke checker for a control when a thin adapter over an existing tool will do. Building the enforcement seams themselves (the executor as a policy enforcement point, the RoE semantics) is in scope; borrowing the raw dispatch mechanism underneath is not.
- **Thin slice before schema.** Fields are added when real friction from a running slice forces them, not because a paper or a future consumer suggests they might be useful. New enums land as pydantic advisory first; the read-only `ontology_schema.yaml` is not edited casually. If your change adds a field, the pull request should name the concrete consumer or friction that forces it.
- **Fail closed and stay honest.** The value of the project is that it refuses to over-claim. A measurement that is underpowered, confounded, or missing a positive control must not produce an asserted delta. A null result is not a pass. If your change relaxes one of these gates, expect a hard question about why.
- **Record decisions as ADRs.** Non-trivial design decisions go in `docs/adr/` as a numbered record: what friction prompted it, what was added or deliberately not added, and why. The existing arc from `0001` onward is the model to follow.

## Testing

There are two layers of tests, kept separate on purpose.

- Deterministic code contracts use `pytest` unit tests with exact expected values and boundaries.
- Score-dependent narrative regressions use directional assertions with a margin, never hard thresholds, because model scores drift across seeds, versions, and images.

Add tests in the layer that matches your change, and keep them deterministic and offline wherever the code under test is deterministic.

## Documentation prose

Documentation meant to be read as prose (README, DESIGN, ADR narrative) should read as flowing sentences, not as points strung together with arrows or other operator symbols. Reserve symbols such as arrows and inequality signs for code blocks and genuinely mathematical expressions.

## Secrets and data

Never commit credentials, and never pass a secret inline in a shell command, since a permission or shell-history mechanism can persist the whole command including the key. Read secrets from a file instead. Raw scan data and any personally identifiable information stay out of version control. See `SECURITY.md` for the authorized-use boundary that governs running the tool at all.
