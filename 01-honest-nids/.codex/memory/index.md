# Memory Index

Last updated: 2026-06-29

## Project

**Honest NIDS** is a portfolio project for roles at the intersection of IP
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

## How To Add Memory

Add concise dated entries to `current-context.md` or `decisions.md`.
If the memory is reader-facing and part of the portfolio story, also add or link
the relevant report under `reports/`.
