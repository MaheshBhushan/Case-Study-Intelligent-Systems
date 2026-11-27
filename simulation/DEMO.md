# 8 Dec live demo: runbook and Q&A

The 8 Dec session asks each group to run the code live, explain its structure and algorithms, justify models and parameter values, discuss preliminary results and challenges, and answer technical questions. Every team member should be able to answer every question below.

## Runbook (about 3 minutes)

Run once the evening before, so the risk model and AI4I data are cached in `models/` and `data/`.

```bash
cd simulation
uv sync --locked
uv run pytest -q                                   # 35 tests, a few seconds
uv run python -m moulding_sim.demo --trace 2       # one 12-week scenario, 5 policies, under 30 s
uv run python -m moulding_sim.demo --scenario high --seed 123   # second scenario if asked
```

What to point at in the demo output:

1. **The trace.** For each candidate order, PRED-MO computes `score = w_due·slack + w_setup·setup/255 + w_spt·proc + w_risk·risk` and picks the lowest score. In the base-scenario trace, `lancet_body` wins because its mould is already mounted (0 setup minutes) and its slack is only 1.7 days.
2. **The KPI table.** Both maintenance policies (SETUP+PM and PRED-MO) roughly halve breakdowns compared with the reactive rules. PRED-MO has the shortest lead time and the lowest energy use and cost. SETUP+PM has slightly higher OEE and less maintenance time in this seed.
3. **The breakdown list.** PRED-MO almost removes screw-wear failures. Most of its remaining failures are drive overloads, which the AI4I rules cannot foresee from wear.
4. **The caveat.** One seed is only an anecdote. The claims come from 100 held-out seeds with paired tests (`results/summary.md`).

Do not run `experiments`, `sensitivity`, `morris` or `optimize` live. They take 10 to 30 minutes on 8 cores. Show their committed outputs in `results/` instead.

## Code structure

| Module | Role | Key function |
|---|---|---|
| `config.py` | All parameters as frozen dataclasses: presses, moulds, products, crews, power and price profile, scenarios | `Scenario.with_()` |
| `model.py` | SimPy plant. Each machine is a process. Presses mount moulds, wear and fail, and request setters and technicians | `Factory.run()`, `Press.run()`, `Factory.kpis()` |
| `policies.py` | Dispatching and maintenance rules: FCFS, SPT, SETUP, SETUP+PM, PRED-MO | `select()`, `wants_pm()` |
| `risk.py` | Random Forest on AI4I 2020, with a fast tree evaluation | `RiskModel.predict()` |
| `optimize.py` | Grid search for the wear rule and NSGA-II for PRED-MO's 6 settings | `tune_rule()`, `main()` |
| `experiments.py` | 100 held-out seeds, 95 % confidence intervals and paired t-tests | `run_grid()`, `paired_vs()` |
| `sensitivity.py` | One-at-a-time sweep of 10 assumed parameters | `levels()`, `paired()` |
| `morris.py` | Morris elementary-effects screening over the same 10 parameters | `trajectories()`, `screen()` |
| `demo.py` | Live demo with a decision trace | `TracedPredictive` |

**One order through the model:** the order arrives (Poisson) → the resin is dried (0–240 min by material) → it queues at moulding, where the policy picks it for a free press that fits its mould → setup (line clearance, plus a mould change or a purge, and it needs a setter) → moulding at the cavity cycle time. Wear builds up during moulding, and the AI4I failure rules are checked once per 8-hour shift → camera inspection → assembly → packaging → a 48-hour QA hold → done.

## Why these choices

| Question | Answer |
|---|---|
| Why discrete-event simulation (SimPy)? | The line is queues, shared crews and random breakdowns. DES models those exactly and lets every policy run on identical random events. SimPy is plain Python, so the ML model plugs in directly. |
| Why a Random Forest? | It works on tabular sensor data, needs no feature scaling, handles the 3.4 % failure class with `class_weight="balanced_subsample"` and gives probabilities. Held-out F1 is 0.88 and ROC-AUC 0.97 with the physics features ΔT, power and strain. |
| Why AI4I 2020? | It is the only public labelled machine-failure dataset with wear, torque, speed and temperatures. It comes from milling, so we use it as a stand-in failure signal and say so in the limitations. |
| Why NSGA-II (Optuna)? | Three objectives conflict: lead time, energy and maintenance time. NSGA-II returns a Pareto front instead of a single weighted optimum, and we pick the point closest to the ideal after normalising each objective. |
| Why is `pm_threshold` only 0.068? | The RF is calibrated to AI4I's base rate of about 3 % failures, so a predicted risk of 7 % per shift is already double the average. NSGA-II found this value. It was not set by hand. |
| Why tune a non-ML wear rule too? | So the ML has to beat a fair rule-based opponent. Both are tuned on the same seeds 0–2. |
| Why common random numbers and paired t-tests? | Each seed fixes the orders, sensor noise and repair draws. Comparing policies on the same seed removes scenario noise, so smaller real differences become significant. |
| Why 3-week warm-up and 12-week horizon? | The plant starts empty. Weeks 0–3 are excluded so KPIs measure steady state. |
| Where do the parameter values come from? | Press power: Thiriez & Gutowski 2006. Drying: Rosato 2000. Line clearance and QA release: EU GMP Annex 1 and 16. Crews, repair times and lot sizes are team assumptions, tested in the sensitivity analysis. |
| Why time-of-day prices? | Clean-room plants run around the clock. A dynamic tariff shows whether idle shutdown or dispatch shifts load to cheap hours. The hourly profile is stylised on the German day-ahead market. |

## Preliminary results

Sources: `results/summary.md` (100 held-out seeds), `results/sensitivity.md` and `results/morris.md`. PRED-MO compared with the tuned wear rule (SETUP+PM) at base demand:

| KPI | Change | p |
|---|---|---|
| Lead time | −2.5 % | < 0.001 |
| Energy per 1,000 good parts | −3.0 % | < 0.001 |
| Energy cost per 1,000 good parts | −3.0 % | < 0.001 |
| Maintenance time | −3.8 % | 0.013 |
| OEE | 0.831 vs 0.838 | wear rule better |

- **Time-of-day prices.** All policies pay about 102 EUR/MWh on average, so cost follows energy. No policy moves load to cheap hours yet.
- **Sensitivity (one at a time).** PRED-MO keeps its lead in lead time and energy at all 21 parameter levels. Whether it also needs less maintenance depends on repair time and PM duration.
- **Morris (10 trajectories, 4 seeds).** Averaged over the whole parameter box, PRED-MO is 5.5 h faster. Demand has the largest effect on that gap, and higher demand widens it. PM duration and repair time decide the maintenance comparison. For most parameters σ/μ* > 1, so the effects interact. With only 4 seeds per point, part of σ is seed noise.

## Technical challenges and how we handled them

- **No plant data.** All parameters are literature values or assumptions. The sensitivity analysis and the Morris screening test whether the conclusions survive when those assumptions change.
- **Speed.** Calling scikit-learn's `predict_proba` per shift block was the bottleneck. `RiskModel.predict` calls the compiled trees directly, which is about 50 times faster for small batches.
- **Overfitting the tuning.** PRED-MO is tuned on 3 seeds and evaluated on 100 other seeds plus the never-tuned `harsh` scenario.
- **Fair baseline.** The first version compared PRED-MO only with reactive rules, which made it look better than it is. The tuned wear rule showed that the ML maintenance trigger alone does not reduce maintenance time.
- **Risk in dispatch did nothing.** The ablation showed that `w_risk` has no measurable effect. The gains come from the dispatch weights and idle shutdown.
