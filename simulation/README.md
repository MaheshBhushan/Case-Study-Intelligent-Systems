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

`experiments` options: `--seeds 100-199 --scenarios base,high --workers 8`.

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
| Randomness | Each seed is one randomised two-week scenario: orders, sensor noise, repairs and inspection, drawn from separate random streams. Every policy runs on the same set of scenarios (common random numbers), so differences come from the policy, not from luck. |

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

## Results (100 held-out scenarios)

PRED-MO was tuned on 3 training scenarios (seeds 0–2, `base` and `high` demand only). It was then
tested on 100 new randomised scenarios (seeds 100–199) that it never saw, plus the unseen `harsh`
setting. Objectives: lead time, kWh per 1,000 good parts, and total maintenance hours
(unplanned repairs + planned PM).

Means ± 95 % CI over 100 scenarios (from `results/summary.md`):

| Scenario | Policy | Lead time (h) | On time | kWh / 1,000 good | Maintenance (h) |
|---|---|---|---|---|---|
| base | FCFS | 23.1 ± 1.7 | 88.9 % | 72.3 | 27.3 |
| base | SETUP | 15.0 ± 0.5 | 95.6 % | 70.2 | 28.1 |
| base | PRED-MO | 14.3 ± 0.4 | 98.4 % | 69.2 | 14.1 |
| high | FCFS | 41.0 ± 2.9 | 71.4 % | 70.4 | 28.6 |
| high | SETUP | 19.4 ± 1.0 | 92.1 % | 64.4 | 31.4 |
| high | PRED-MO | 17.8 ± 0.8 | 97.5 % | 63.6 | 16.1 |
| harsh | SETUP | 15.3 ± 0.5 | 95.4 % | 70.2 | 37.9 |
| harsh | PRED-MO | 14.4 ± 0.4 | 98.3 % | 69.1 | 18.7 |

Compared with the best baseline (SETUP), using paired tests over the shared scenarios
(all p < 0.001):
- maintenance time is 43–51 % lower;
- lead time is 2–9 % lower;
- energy per good part is 1–2.5 % lower.

Mean time to clear orders disrupted by a breakdown is longer at high demand (28.3 h vs 22.3 h).

Ablation over the same 100 scenarios (`results/ablation_summary.csv`): the maintenance gain comes
from the risk-triggered PM (removing it brings maintenance back to 27–37 h). Adding risk to the
dispatch score has no measurable effect. The lead-time and on-time gains come from the tuned
dispatch weights.

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
