# moulding-sim

Discrete-event simulation of a five-station medical injection-moulding line, using the
Gerresheimer plant in Pfreimd as a public reference case. It compares fixed dispatching rules
with an AI policy that combines a failure-risk model (Random Forest on AI4I 2020) and
multi-objective tuning (Optuna NSGA-II).

All plant parameters are synthetic and literature-based. Gerresheimer publishes no operational
data, so results are relative comparisons between policies, not predictions for the real plant.

## Quick start

```bash
uv sync                                  # Python >= 3.12
uv run pytest -q                         # 22 tests
uv run python -m moulding_sim.risk       # train risk model (auto-downloads AI4I 2020)
uv run python -m moulding_sim.optimize   # NSGA-II tuning, ~15 min on 8 cores -> results/tuned.json
uv run python -m moulding_sim.experiments  # held-out comparison -> results/summary.md
```

`experiments` options: `--seeds 100-119 --scenarios base,high --workers 8`.

## Model

```
drying (2 dryers) -> moulding (2 machines) -> camera inspection -> assembly -> clean-room packaging
```

| Part | What is modelled |
|---|---|
| Orders | Poisson arrivals, 6 products on 3 moulds, lots of 2,000–6,000, 15 % rush orders |
| Changeovers | 0 min (same product), 65 min (same mould), 165 min (mould change + GMP line clearance + heat-up) |
| Energy | Per-station power states (busy, idle, setup, off, warm-up), optional idle shutdown of moulding machines, fixed 60 kW clean-room HVAC |
| Failures | Tool wear and cooling fouling build up with use. Ground truth follows the five AI4I 2020 failure rules (TWF, HDF, PWF, OSF, RNF). Lognormal repair, mean 4 h. A repair fixes only the failed component; preventive maintenance (1 h) restores everything. |
| Quality | Start-up scrap after changeovers, purge scrap after breakdowns, wear-dependent inspection rejects |
| Reproducibility | Separate seeded random streams for orders, sensors, repairs and inspection, so every policy faces identical demand (common random numbers) |

KPIs are measured from day 2 to day 14; released orders get 4 extra days to finish.
Scenarios: `low` / `base` / `high` demand (mean order gap 135 / 115 / 100 min), and `harsh`
(faster wear and fouling at base demand).

## Policies

| Policy | Rule |
|---|---|
| FCFS | First come, first served |
| SPT | Shortest processing time |
| SETUP | Fewest changeover minutes first (mould grouping) |
| PRED-MO | Lowest score of `w_due*slack + w_setup*setup + w_spt*proc + w_risk*risk`, idle shutdown after `idle_off` minutes, preventive maintenance when predicted failure risk ≥ `pm_threshold` |

The risk is the Random Forest's failure probability for the job on that machine, averaged over
16 fixed sensor-noise draws. Engineered features (ΔT, power, strain) raise held-out AI4I F1 from
0.69 to 0.88 (ROC-AUC 0.97); inside the simulation, ROC-AUC is 0.88.

## Results (held-out seeds 100–119)

PRED-MO was tuned on seeds 0–2 (`base` and `high` only). It never saw the test seeds or the
`harsh` scenario. Objectives: lead time, kWh per 1,000 good parts, and total maintenance hours
(unplanned repairs + planned PM).

Means ± 95 % CI over 20 replications (from `results/summary.md`):

| Scenario | Policy | Lead time (h) | On time | kWh / 1,000 good | Maintenance (h) |
|---|---|---|---|---|---|
| base | FCFS | 20.4 ± 3.3 | 91.4 % | 72.5 | 25.4 |
| base | SETUP | 14.1 ± 0.7 | 96.8 % | 70.7 | 25.5 |
| base | PRED-MO | 13.7 ± 0.6 | 98.5 % | 69.7 | 14.2 |
| high | FCFS | 36.3 ± 6.4 | 77.5 % | 69.8 | 26.1 |
| high | SETUP | 18.1 ± 1.8 | 93.3 % | 64.3 | 29.6 |
| high | PRED-MO | 16.8 ± 1.5 | 97.9 % | 63.6 | 14.5 |
| harsh | SETUP | 14.5 ± 0.8 | 96.2 % | 70.6 | 36.1 |
| harsh | PRED-MO | 13.8 ± 0.7 | 98.5 % | 69.7 | 16.7 |

Compared with the best baseline (SETUP), with paired tests on common seeds:
- maintenance time is 35–54 % lower (p < 0.002);
- lead time is 1–7 % lower;
- energy per good part is 1–2.5 % lower.

Mean time to clear orders disrupted by a breakdown is longer at high demand (25.7 h vs 21.0 h).

Ablation (`results/ablation_summary.csv`): the maintenance gain comes from the risk-triggered PM
(removing it brings maintenance back to 23–34 h). Adding risk to the dispatch score has no
measurable effect. The lead-time and on-time gains come from the tuned dispatch weights.

## Limitations

- No real plant data; AI4I 2020 is a milling dataset used as a failure-signal proxy.
- Lot sizes are small and there are only 2 moulding machines, so changeovers dominate machine time.
- PM is not yet compared with a non-ML rule (e.g. wear-based PM), so the ML model's added value
  over a simple threshold rule is still open.
- Energy differences are small because clean-room HVAC is a fixed load.

## Layout

```
src/moulding_sim/
  config.py       plant parameters and scenarios
  model.py        SimPy line, energy, failures, KPIs
  policies.py     FCFS, SPT, SETUP, PRED-MO
  risk.py         AI4I download, features, Random Forest
  experiments.py  replications, confidence intervals, paired tests
  optimize.py     Optuna NSGA-II tuning, Pareto front
tests/            invariants: CRN, flow conservation, setups, energy, AI4I rules, dispatching
results/          tuned.json, pareto.csv, summary.md, paired_tests.csv, ablation_summary.csv
```
