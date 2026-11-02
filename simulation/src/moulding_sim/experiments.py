"""Policy comparison with common random numbers, replications and 95 % confidence intervals.

Usage: python -m moulding_sim.experiments [--seeds 100-119] [--scenarios base,high] [--tuned results/tuned.json]
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from .config import SCENARIOS
from .model import simulate
from .policies import FCFS, SPT, Predictive, SetupAware
from .risk import ROOT, RiskModel

RESULTS = ROOT / "results"
TEST_SEEDS = range(100, 120)  # held out: never used for tuning
KPIS = ["throughput_uph", "lead_time_h", "on_time_rate", "kwh_per_1000_good", "scrap_rate",
        "failures", "pm_events", "downtime_h", "pm_h", "maintenance_h", "recovery_h", "setup_h"]

_risk: RiskModel | None = None


def _init_worker() -> None:
    global _risk
    _risk = RiskModel()


def build_policy(spec: dict):
    """spec = {"name": "FCFS"} or {"name": "PRED-MO", **Predictive params}."""
    name = spec["name"]
    if name == "FCFS":
        return FCFS()
    if name == "SPT":
        return SPT()
    if name == "SETUP":
        return SetupAware()
    params = {k: v for k, v in spec.items() if k != "name"}
    return Predictive(_risk or RiskModel(), name=name, **params)


def _run(args: tuple[dict, str, int]) -> dict:
    spec, scenario, seed = args
    k = simulate(build_policy(spec), SCENARIOS[scenario], seed)
    return {"policy": spec["name"], "scenario": scenario, "seed": seed, **k}


def run_grid(specs: list[dict], scenarios: list[str], seeds, workers: int | None = None) -> pd.DataFrame:
    jobs = [(sp, sc, s) for sp in specs for sc in scenarios for s in seeds]
    with ProcessPoolExecutor(workers, initializer=_init_worker) as ex:
        return pd.DataFrame(list(ex.map(_run, jobs)))


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """Mean and 95 % t-interval half-width per policy x scenario."""
    def ci(x):
        return stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
    g = df.groupby(["scenario", "policy"], sort=False)[KPIS]
    return g.mean().join(g.agg(ci).add_suffix("_ci"))


def paired_vs(df: pd.DataFrame, baseline: str, policy: str, kpi: str) -> pd.DataFrame:
    """Paired difference (policy - baseline) on common seeds, with 95 % CI and p-value."""
    rows = []
    for sc, d in df.groupby("scenario", sort=False):
        a = d[d.policy == baseline].set_index("seed")[kpi]
        b = d[d.policy == policy].set_index("seed")[kpi]
        diff = (b - a).dropna()
        half = stats.t.ppf(0.975, len(diff) - 1) * diff.std(ddof=1) / np.sqrt(len(diff))
        rows.append({"scenario": sc, "kpi": kpi, "baseline": baseline, "policy": policy,
                     "mean_diff": diff.mean(), "ci": half, "rel_change_%": 100 * diff.mean() / a.mean(),
                     "p_value": stats.ttest_rel(b.loc[diff.index], a.loc[diff.index]).pvalue})
    return pd.DataFrame(rows)


def markdown(summary: pd.DataFrame, cols=("throughput_uph", "lead_time_h", "on_time_rate",
                                          "kwh_per_1000_good", "scrap_rate", "maintenance_h",
                                          "recovery_h")) -> str:
    out = ["| scenario | policy | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for (sc, pol), r in summary.iterrows():
        cells = [f"{r[c]:.3g} ± {r[c + '_ci']:.2g}" for c in cols]
        out.append(f"| {sc} | {pol} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def _seeds(s: str):
    a, b = s.split("-")
    return range(int(a), int(b) + 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=_seeds, default=TEST_SEEDS)
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--tuned", type=Path, default=RESULTS / "tuned.json")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    specs = [{"name": "FCFS"}, {"name": "SPT"}, {"name": "SETUP"}]
    if a.tuned.exists():
        specs.append({"name": "PRED-MO", **json.loads(a.tuned.read_text())["params"]})
    else:
        print(f"no tuned policy at {a.tuned}; running baselines only")
    df = run_grid(specs, a.scenarios.split(","), a.seeds, a.workers)
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / "runs.csv", index=False)
    summary = summarise(df)
    summary.to_csv(RESULTS / "summary.csv")
    md = [markdown(summary)]
    if "PRED-MO" in df.policy.values:
        tests = pd.concat([paired_vs(df, base, "PRED-MO", k) for base in ("FCFS", "SETUP")
                           for k in ("lead_time_h", "on_time_rate", "kwh_per_1000_good",
                                     "maintenance_h")])
        tests.to_csv(RESULTS / "paired_tests.csv", index=False)
        md.append(tests.round(4).to_markdown(index=False))
    (RESULTS / "summary.md").write_text("\n\n".join(md) + "\n")
    print("\n\n".join(md))


if __name__ == "__main__":
    main()
