# Memory Index

Last updated: 2026-06-30

## Project

**Honest NIDS** is a project for roles at the intersection of IP
networking, network security, machine learning, and deep learning.

The project is not a classifier leaderboard. Its purpose is to expose and avoid
inflated public NIDS benchmark results caused by leakage, optimistic splitting,
identity shortcuts, and poor cross-dataset generalisation.

## Canonical Context Files

| Topic | File |
|---|---|
| Project-specific agent rules | `CLAUDE.md` |
| Main findings and limitations | `reports/findings.md` |
| NetFlow v3 data provenance and validation | `reports/data-prep-v3.md` |
| Related work and narrative angles | `reports/related-work-perspectives.md` |
| Model choice decision | `reports/model-selection-decision.md` |
| Notebook order and test commands | `notebooks/README.md` |
| Network-depth candidate backlog | `../docs/network-detection-candidates-draft.md` |

## Current High-Signal Decisions

1. Main data base is NetFlow v3, not the old v2 mirror.
2. Main model is LightGBM for pragmatic engineering reasons, not because it is
   claimed to be theoretically superior to XGBoost or CatBoost.
3. Main story: single-dataset scores can be meaningless even under honest
   temporal split; cross-dataset LODO is the real stress test.
4. IP/port are environment identity features. They are useful for demonstrating
   shortcut learning, but they are not valid deployable detection evidence.
5. Absolute timestamps are for temporal splitting and audit only; they should
   not be used as inference features in honest or LODO evaluations.
6. Post-review wording boundary: keep LODO/PR-AUC as the main stress-test
   story, but do not overclaim FPR, threshold tuning, or model-invariant
   collapse beyond what the tables support.
7. Network-depth backlog: add at most one extra network-depth project. Current
   preferred candidate is BGP/RPKI honest audit, gated by a one-day data
   feasibility spike; DNS honest-audit is the fallback.

## How To Add Memory

Add concise dated entries to `current-context.md` or `decisions.md`.
If the memory is reader-facing and part of the project story, also add or link
the relevant report under `reports/`.
