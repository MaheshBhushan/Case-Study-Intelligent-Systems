"""Multi-objective tuning of the predictive policy with Optuna's NSGA-II sampler.

Objectives (all minimised, averaged over training seeds and scenarios):
mean lead time [h], energy per 1,000 good parts [kWh], maintenance time [h] =
unplanned repairs + planned preventive maintenance (so PM is never free).
Training seeds 0..N-1 are disjoint from the test seeds used in experiments.py.

Usage: python -m moulding_sim.optimize [--generations 10] [--population 16]
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import optuna
import pandas as pd

from .experiments import RESULTS, _init_worker, _run

OBJECTIVES = ("lead_time_h", "kwh_per_1000_good", "maintenance_h")
TRAIN_SCENARIOS = ("base", "high")
PARAMS = ("w_due", "w_setup", "w_spt", "w_risk", "idle_off", "pm_threshold")


def suggest(trial: optuna.Trial) -> dict:
    return {
        "w_due": trial.suggest_float("w_due", 0.0, 3.0),
        "w_setup": trial.suggest_float("w_setup", 0.0, 3.0),
        "w_spt": trial.suggest_float("w_spt", 0.0, 2.0),
        "w_risk": trial.suggest_float("w_risk", 0.0, 5.0),
        "idle_off": trial.suggest_float("idle_off", 10.0, 1440.0, log=True),
        "pm_threshold": trial.suggest_float("pm_threshold", 0.05, 1.0),
    }


def compromise(front: pd.DataFrame) -> pd.Series:
    """Pareto point closest to the ideal after min-max normalising each objective."""
    obj = front[list(OBJECTIVES)]
    span = (obj.max() - obj.min()).replace(0, 1)
    dist = np.sqrt((((obj - obj.min()) / span) ** 2).sum(axis=1))
    return front.loc[dist.idxmin()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=10)
    ap.add_argument("--population", type=int, default=16)
    ap.add_argument("--train-seeds", type=int, default=4)
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(directions=["minimize"] * len(OBJECTIVES),
                                sampler=optuna.samplers.NSGAIISampler(population_size=a.population,
                                                                      seed=0))
    # Seed the search with a hand-set default and a setup-aware-like corner.
    study.enqueue_trial({"w_due": 1.0, "w_setup": 1.0, "w_spt": 0.3, "w_risk": 1.0,
                         "idle_off": 120.0, "pm_threshold": 0.5})
    study.enqueue_trial({"w_due": 0.0, "w_setup": 3.0, "w_spt": 0.0, "w_risk": 0.0,
                         "idle_off": 1440.0, "pm_threshold": 1.0})
    seeds = range(a.train_seeds)
    with ProcessPoolExecutor(a.workers, initializer=_init_worker) as ex:
        for gen in range(a.generations):
            trials = [study.ask() for _ in range(a.population)]
            params = [suggest(t) for t in trials]
            jobs = [({"name": "PRED-MO", **p}, sc, s)
                    for p in params for sc in TRAIN_SCENARIOS for s in seeds]
            res = pd.DataFrame(list(ex.map(_run, jobs)))
            per = len(TRAIN_SCENARIOS) * len(seeds)
            for i, t in enumerate(trials):
                chunk = res.iloc[i * per:(i + 1) * per]
                study.tell(t, [float(chunk[o].mean()) for o in OBJECTIVES])
            front = len(study.best_trials)
            print(f"generation {gen + 1}/{a.generations}: {len(study.trials)} trials, "
                  f"Pareto front {front}", flush=True)

    rows = [{**t.params, **dict(zip(OBJECTIVES, t.values)), "trial": t.number}
            for t in study.best_trials]
    front = pd.DataFrame(rows).sort_values("lead_time_h")
    RESULTS.mkdir(exist_ok=True)
    front.to_csv(RESULTS / "pareto.csv", index=False)
    pd.DataFrame([{**t.params, **dict(zip(OBJECTIVES, t.values))} for t in study.trials]) \
        .to_csv(RESULTS / "trials.csv", index=False)
    best = compromise(front)
    tuned = {"params": {k: float(best[k]) for k in PARAMS},
             "train_objectives": {o: float(best[o]) for o in OBJECTIVES},
             "train_seeds": list(seeds), "train_scenarios": list(TRAIN_SCENARIOS),
             "trials": len(study.trials), "pareto_size": len(front)}
    (RESULTS / "tuned.json").write_text(json.dumps(tuned, indent=2))
    print(front.round(3).to_string(index=False))
    print("compromise:", json.dumps(tuned, indent=2))


if __name__ == "__main__":
    main()
