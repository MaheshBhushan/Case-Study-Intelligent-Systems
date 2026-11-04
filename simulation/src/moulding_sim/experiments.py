"""Policy comparison over many randomised scenarios with 95 % confidence intervals.

Each seed is one randomised two-week scenario (orders, sensor noise, repairs). Every policy is
run on the same set of scenarios (common random numbers), so differences come from the policy.

Usage: python -m moulding_sim.experiments [--seeds 100-199] [--scenarios base,high] [--tuned results/tuned.json]
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
from .policies import FCFS, SPT, Predictive, RulePM, SetupAware
from .risk import ROOT, RiskModel

RESULTS = ROOT / "results"
TEST_SEEDS = range(100, 200)  # 100 held-out scenarios, never used for tuning
KPIS = ["throughput_uph", "lead_time_h", "on_time_rate", "kwh_per_1000_good", "press_kwh_per_kg",
        "scrap_rate", "escaped_ppm", "failures", "pm_events", "downtime_h", "pm_h", "maintenance_h",
        "mttr_h", "setup_h", "setter_wait_h", "press_util", "availability", "oee"]

_risk: RiskModel | None = None


def _init_worker() -> None:
    global _risk
    _risk = RiskModel()


def build_policy(spec: dict):
    """spec = {"name": "FCFS"}, {"name": "SETUP+PM", **RulePM params} or {"name": "PRED-MO", ...}."""
    name = spec["name"]
    params = {k: v for k, v in spec.items() if k != "name"}
    if name == "FCFS":
        return FCFS()
    if name == "SPT":
        return SPT()
    if name == "SETUP":
        return SetupAware()
    if name == "SETUP+PM":
        return RulePM(**params)
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


def markdown(summary: pd.DataFrame, cols=("lead_time_h", "on_time_rate", "kwh_per_1000_good",
                                          "oee", "escaped_ppm", "maintenance_h",
                                          "mttr_h")) -> str:
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
    ap.add_argument("--rule", type=Path, default=RESULTS / "rule.json")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    specs = [{"name": "FCFS"}, {"name": "SPT"}, {"name": "SETUP"}]
    for path, name in ((a.rule, "SETUP+PM"), (a.tuned, "PRED-MO")):
        if path.exists():
            specs.append({"name": name, **json.loads(path.read_text())["params"]})
        else:
            print(f"no {name} parameters at {path}; skipping it")
    df = run_grid(specs, a.scenarios.split(","), a.seeds, a.workers)
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / "runs.csv", index=False)
    summary = summarise(df)
    summary.to_csv(RESULTS / "summary.csv")
    md = [markdown(summary)]
    if "PRED-MO" in df.policy.values:
        tests = pd.concat([paired_vs(df, base, "PRED-MO", k)
                           for base in ("FCFS", "SETUP", "SETUP+PM") if base in df.policy.values
                           for k in ("lead_time_h", "on_time_rate", "kwh_per_1000_good",
                                     "maintenance_h", "escaped_ppm")])
        tests.to_csv(RESULTS / "paired_tests.csv", index=False)
        md.append(tests.round(4).to_markdown(index=False))
    (RESULTS / "summary.md").write_text("\n\n".join(md) + "\n")
    print("\n\n".join(md))


if __name__ == "__main__":
    main()
