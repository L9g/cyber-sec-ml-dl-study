# Current Context

Last updated: 2026-06-30

## Objective

Build `01-honest-nids` as a project for IP networking, network
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

Verified with project venv on 2026-06-30:

```bash
./01-honest-nids/.venv/bin/python -m pytest 01-honest-nids/src/tests -q
```

Result: 17 passed.

Notebook tests must be invoked by explicit file path:

```bash
.venv/bin/python -m pytest notebooks/01_optimistic_baseline.py notebooks/02_ip_ablation.py notebooks/03_honest_temporal_split.py notebooks/04_lodo_cross_dataset.py
```

Previous run passed all notebook assertions, but took roughly 4-18 minutes per
notebook because marimo re-executes data loading and model training.

On 2026-06-30, `pytest 01-honest-nids/notebooks --collect-only -q` still
collected 0 tests because notebook filenames start with digits. This is expected
and already documented; invoke notebook files explicitly.

## Known Cleanup Items

- Keep README results synced with `reports/findings.md`.
- Keep `notebooks/README.md` aligned with the actual notebook list, including 02.
- Avoid saying LODO "FPR explodes" unless the current LODO table supports that.
- Prefer "recall@0.5 is fragile" over "threshold tuning cannot help" unless
  supported by recall-at-FPR or PR-curve analysis.
- Fix `reports/findings.md` where it says LODO FPR is only `0.001-0.023`; the
  current table includes FPR values around `0.064-0.105`.
- Avoid saying "threshold tuning cannot help" or "调阈值救不回" based only on
  positive probabilities not being in `[0.4, 0.5)`. The defensible statement is:
  lowering the threshold is not a free fix; evaluate recall at fixed FPR,
  precision at alert budget, or full PR-curve operating points.
- Narrow "all models collapse together" wording. The stable claim is that model
  family changes do not recover in-distribution performance; the exact PR-AUC
  still varies by dataset direction, cap, and model.
- Do not commit stale `notebooks/__marimo__/session/*.json` outputs unless they
  are regenerated. Current tracked session cache contains old v2 narrative
  (`NF-UNSW-NB15-v2`, `3.8% vs 72.6%`, old `4/6 below random`, old FPR text).
