# Current Context

Last updated: 2026-06-29

## Objective

Build `01-honest-nids` as a portfolio project for IP networking, network
security, and ML/DL crossover roles.

The project should communicate engineering judgment: data governance, leakage
control, evaluation design, reproducibility, model risk, and operational
security metrics.

## Current Data Base

- NetFlow v3 unified datasets:
  - `NF-UNSW-NB15-v3`
  - `NF-ToN-IoT-v3`
  - `NF-CSE-CIC-IDS2018-v3`
- v3 contains real IP addresses, real per-flow timestamps, and duplicate flows.
- Raw data is excluded from git because real IP addresses are privacy-sensitive.
- Data provenance and validation are documented in `reports/data-prep-v3.md`.

## Current Experimental Story

1. `notebooks/01_optimistic_baseline.py`
   - Random split + all features, including IP/port.
   - Demonstrates inflated in-distribution performance.
2. `notebooks/02_ip_ablation.py`
   - Shows IP can be sufficient for memorisation in UNSW.
   - IP LODO values should be interpreted as identity-code semantic collapse,
     not as true cross-domain IP-only detection ability.
3. `notebooks/03_honest_temporal_split.py`
   - Drops IP/port and uses true temporal split.
   - UNSW still scores near-perfect, supporting the "synthetic benchmark is
     plainly separable" argument.
4. `notebooks/04_lodo_cross_dataset.py`
   - Cross-dataset LODO exposes generalisation collapse.
   - PR-AUC relative to target base rate is the headline metric; recall@0.5 is
     reported as auxiliary because it is sampling- and threshold-sensitive.

## Current Test Status

Verified with project venv on 2026-06-29:

```bash
.venv/bin/python -m pytest src/tests
```

Result: 17 passed.

Notebook tests must be invoked by explicit file path:

```bash
.venv/bin/python -m pytest notebooks/01_optimistic_baseline.py notebooks/02_ip_ablation.py notebooks/03_honest_temporal_split.py notebooks/04_lodo_cross_dataset.py
```

Previous run passed all notebook assertions, but took roughly 4-18 minutes per
notebook because marimo re-executes data loading and model training.

## Known Cleanup Items

- Keep README results synced with `reports/findings.md`.
- Keep `notebooks/README.md` aligned with the actual notebook list, including 02.
- Avoid saying LODO "FPR explodes" unless the current LODO table supports that.
- Prefer "recall@0.5 is fragile" over "threshold tuning cannot help" unless
  supported by recall-at-FPR or PR-curve analysis.
