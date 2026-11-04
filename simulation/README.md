# moulding-sim

Discrete-event simulation of a medical injection-moulding plant, using the Gerresheimer site in
Pfreimd as a public reference case. It compares fixed dispatching rules and a non-ML maintenance
rule with an AI policy that combines a failure-risk model (Random Forest on AI4I 2020) and
multi-objective tuning (Optuna NSGA-II).

All plant parameters are synthetic and literature-based. Gerresheimer publishes no operational
data, so results are relative comparisons between policies, not predictions for the real plant.

## Quick start

```bash
uv sync                                    # Python >= 3.12
uv run pytest -q                           # 28 tests
uv run python -m moulding_sim.risk         # train risk model (auto-downloads AI4I 2020)
uv run python -m moulding_sim.optimize     # rule grid + NSGA-II, ~30 min on 8 cores
uv run python -m moulding_sim.experiments  # 100 held-out scenarios -> results/summary.md
```

`experiments` options: `--seeds 100-199 --scenarios base,high --workers 8`.

## Model (v2)

```
order -> drying -> moulding (12 presses) -> camera inspection -> assembly -> clean-room packaging -> QA release
```

| Part | What is modelled |
|---|---|
| Presses | 12 presses in 3 classes: 4 × 80 t all-electric, 5 × 150 t hybrid, 3 × 250 t hydraulic, each with its own busy and idle power |
| Moulds | 8 moulds (inhaler housing, pen body, lancet, …) with 2–3 identical copies each. A copy is either on one press, in the rack or in the toolroom. Each mould fits only certain press classes. |
| Products and orders | 10 products in PP, ABS, POM and PC (material-specific drying, 0–240 min). Campaign lots of 20k–900k parts (about 1–4 days of moulding). Poisson order arrivals; 10 % are rush orders. |
| Changeovers | 45 min GMP line clearance on every product change. A mould change adds 165 min and a material or colour change adds a 40 min purge. Mould and material changes need a setter: 3 on day shifts, 1 at night. |
| Failures | Screw wear and loss of heat-dissipation margin build up while a press runs. Once per 8 h shift, a sensor reading is checked against the AI4I 2020 failure rules, mapped to press components: screw/barrel wear, heater/cooling, drive overload, screw overstrain, random fault. Mould damage happens at random per shot. Repairs (3–24 h, lognormal) need one of 2 technicians, or the toolroom for moulds. A repair fixes only the failed part; PM (2 h) restores everything. Moulds go for planned service every 1.5 M shots. |
| Energy | Press power by drive type and state (busy, idle, setup, off, warm-up), station power, fixed 120 kW clean-room HVAC. Reported as kWh per 1,000 good parts and press kWh per kg moulded. |
| Quality | The defect rate rises with screw wear. The camera misses 2 % of defects and falsely rejects 0.3 % of good parts. Start-up and purge scrap are counted. KPIs: scrap rate and escaped defects (ppm). |
| OEE | Availability × performance × quality. Each campaign runs at 85–95 % of ideal speed, which represents cycle drift and micro-stops. |
| QA release | GMP batch release hold before shipping, lognormal with mean 48 h |
| Randomness | Each seed is one randomised scenario covering orders, sensor noise, repairs, inspection and QA, each drawn from its own random stream. Every policy runs on the same set of scenarios (common random numbers), so differences come from the policy, not from luck. |

Each run releases orders for 12 weeks. KPIs are measured from week 3 to week 12, and released
orders get 6 extra weeks to finish. Scenarios: `low` / `base` / `high` demand (mean order gap
560 / 480 / 420 min, i.e. about 67 / 77 / 87 % press utilisation) and `harsh` (faster wear and
fouling at base demand). At base demand with FCFS, OEE is 0.82, availability 0.94, about one
breakdown per press per week, and 2.9 kWh per kg moulded.

## Policies

| Policy | Dispatch | Maintenance |
|---|---|---|
| FCFS | First come, first served | Reactive |
| SPT | Shortest processing time | Reactive |
| SETUP | Fewest changeover minutes | Reactive |
| SETUP+PM | Fewest changeover minutes | PM when screw wear would pass `wear_limit` (non-ML rule) |
| PRED-MO | Lowest `w_due*slack + w_setup*setup + w_spt*proc + w_risk*risk`, idle shutdown after `idle_off` min | PM when predicted failure risk ≥ `pm_threshold` |

The risk is the Random Forest's failure probability for the next shift on that press, averaged
over 16 fixed sensor-noise draws. Engineered features (ΔT, power, strain) raise held-out AI4I F1
from 0.69 to 0.88 (ROC-AUC 0.97). The simulation calls the compiled trees directly, which gives
the same output as scikit-learn about 50× faster.

Both tuned policies use the same 3 training scenarios (seeds 0–2, `base` and `high` demand):
- `SETUP+PM`: grid search over wear and fouling limits for least total maintenance time. Best: `wear_limit` 180, no fouling trigger.
- `PRED-MO`: NSGA-II, 192 trials, minimising lead time, kWh per 1,000 good parts and total
  maintenance time (unplanned + planned). The compromise point is in `results/tuned.json`.

## Results (100 held-out scenarios)

Means over seeds 100–199, which neither policy saw during tuning. `harsh` was never used for
tuning. Lead time is order to QA release.

| Scenario | Policy | Lead time (h) | On time | kWh / 1,000 good | OEE | Escaped (ppm) | Maintenance (h) | Failures |
|---|---|---|---|---|---|---|---|---|
| base | FCFS | 201 ± 3 | 95.2 % | 13.7 | 0.820 | 463 | 572 | 111 |
| base | SETUP | 203 ± 4 | 94.7 % | 13.7 | 0.824 | 464 | 575 | 111 |
| base | SETUP+PM | 200 ± 3 | 95.1 % | 13.6 | 0.838 | 404 | 364 | 68 |
| base | PRED-MO | 195 ± 3 | 96.5 % | 13.2 | 0.831 | 393 | 350 | 44 |
| high | FCFS | 246 ± 8 | 91.1 % | 13.0 | 0.820 | 465 | 643 | 124 |
| high | SETUP+PM | 239 ± 7 | 90.8 % | 12.9 | 0.843 | 403 | 400 | 75 |
| high | PRED-MO | 227 ± 6 | 94.2 % | 12.7 | 0.836 | 397 | 392 | 50 |
| harsh | FCFS | 206 ± 4 | 94.9 % | 13.8 | 0.809 | 497 | 745 | 143 |
| harsh | SETUP+PM | 201 ± 3 | 95.0 % | 13.7 | 0.832 | 431 | 446 | 83 |
| harsh | PRED-MO | 197 ± 3 | 96.3 % | 13.3 | 0.825 | 422 | 448 | 48 |

What the comparison shows (paired tests over the shared scenarios, `results/paired_tests.csv`):
- **Any preventive maintenance beats reactive repair.** Both SETUP+PM and PRED-MO cut total
  maintenance time by 35–40 % against FCFS or SETUP.
- **PRED-MO vs the non-ML rule (SETUP+PM).** Total maintenance time is the same within noise:
  −4 % to +0.5 %, significant only at base demand (p = 0.013). PRED-MO is better on everything else
  (p < 0.003 for each):
  - lead time 0.6–5 % shorter;
  - on-time rate 0.6–3.4 percentage points higher;
  - energy per good part 1.4–5.8 % lower;
  - escaped defects 1.6–2.8 % lower.
- **OEE is slightly higher with the rule** (0.838 vs 0.831 at base demand), because the rule
  makes fewer planned stops.

Ablation (`results/ablation_summary.csv`, same 100 scenarios):

| Base demand | PRED-MO | Same dispatch + wear rule | No PM | No risk in dispatch |
|---|---|---|---|---|
| Maintenance (h) | 350 | 361 | 570 | 349 |
| Unplanned failures | 44 | 68 | 111 | 44 |
| Planned PM stops | 65 | 38 | 0 | 65 |

- **The ML trigger changes the kind of downtime, not the amount.** It prevents about 35 % more
  breakdowns than the wear rule but needs about 70 % more planned stops, so total maintenance time
  is about the same.
- **Risk in the dispatch score has no effect.**
- **Delivery and energy gains come from the tuned dispatch weights and idle shutdown.**

## Limitations

- No real plant data; AI4I 2020 is a milling dataset used as a failure-signal proxy, with its
  failure rules mapped to press components.
- Press power, crew sizes, repair times and lot sizes are assumptions. Sensitivity analysis is
  still to do.
- Clean-room HVAC is a fixed load, so plant-level energy differences stay small. Time-of-day
  electricity prices are not modelled yet.
- Assembly is modelled as one processing step per lot, not as a multi-component bill of materials.

## Layout

```
src/moulding_sim/
  config.py       plant, presses, moulds, products, crew, scenarios
  model.py        SimPy plant, moulds, crews, failures, energy, inspection, QA, KPIs
  policies.py     FCFS, SPT, SETUP, SETUP+PM, PRED-MO
  risk.py         AI4I download, features, Random Forest, fast prediction
  experiments.py  replications, confidence intervals, paired tests
  optimize.py     rule grid search, Optuna NSGA-II tuning, Pareto front
tests/            CRN, flow, moulds and setups, night shift, energy, camera, QA hold, AI4I rules, policies
results/          rule.json, tuned.json, pareto.csv, summary.md, paired_tests.csv, ablation_summary.csv
```
