# Codex Memory System

This directory is the project-local memory system for Codex sessions.

It is not platform memory. It is a durable repo-level context store that future
Codex sessions should read before making project decisions.

## Read Order

When starting work in this project, read these files in order:

1. `CLAUDE.md`
2. `.codex/memory/index.md`
3. `.codex/memory/current-context.md`
4. `.codex/memory/decisions.md`
5. Task-specific reports under `reports/`

## Write Protocol

When the user says one of the following:

- `存记忆`
- `保存上下文`
- `把这个结论存进项目上下文`
- `make this persistent for future Codex sessions`

Codex should update the relevant memory file:

| Content type | File |
|---|---|
| Stable project facts / current state | `current-context.md` |
| Architecture, methodology, model, data decisions | `decisions.md` |
| Short note that points to formal project docs | `index.md` |
| Reader-facing technical explanation | `reports/*.md` |

Do not store raw data, secrets, credentials, private tokens, or copied paper text.

## Memory Style

- Keep entries short, factual, and dated.
- Prefer links to canonical files instead of duplicating long explanations.
- Separate facts from open questions.
- Mark superseded decisions instead of deleting them unless the user asks for cleanup.

## Canonical Commands

Use the project virtual environment:

```bash
.venv/bin/python -m pytest src/tests
.venv/bin/python -m pytest notebooks/01_optimistic_baseline.py notebooks/02_ip_ablation.py notebooks/03_honest_temporal_split.py notebooks/04_lodo_cross_dataset.py
```

`pytest notebooks` alone does not collect the marimo notebook tests because the
files are named `01_*.py`, `02_*.py`, etc., not `test_*.py`.
