"""One-at-a-time sensitivity analysis of the assumed plant parameters.

Each parameter is moved to a low and a high value while the rest stay at `base`. At every level,
FCFS, SETUP+PM and PRED-MO run on the same seeds (common random numbers). The output answers one
question per parameter: does PRED-MO keep its lead over the tuned wear rule (SETUP+PM)?

Usage: python -m moulding_sim.sensitivity [--seeds 100-129] [--workers 8]
Writes results/sensitivity_runs.csv, results/sensitivity.csv and results/sensitivity.md.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import pandas as pd

from . import experiments as ex
from .config import SCENARIOS, Scenario
from .model import simulate

BASE = SCENARIOS["base"]

# name -> (description, low, high, builder(scenario, value) -> scenario)
PARAMS: dict[str, tuple[str, float, float, callable]] = {
    "demand": ("mean order interarrival [min] (base 480)", 540.0, 430.0,
               lambda s, v: s.with_(interarrival=v)),
    "wear_rate": ("screw wear per running min (base 0.008)", 0.004, 0.012,
                  lambda s, v: s.with_(wear_per_min=v)),
    "repair_time": ("repair time multiplier (base 1.0)", 0.5, 1.5,
                    lambda s, v: s.with_(repair_scale=v)),
    "technicians": ("maintenance technicians (base 2)", 1, 3,
                    lambda s, v: s.with_(crew=replace(s.crew, technicians=int(v)))),
    "setters": ("day-shift setters (base 3)", 2, 4,
                lambda s, v: s.with_(crew=replace(s.crew, setters_day=int(v)))),
    "mould_change": ("mould change [min] (base 120)", 90.0, 180.0,
                     lambda s, v: s.with_(setup=replace(s.setup, mould_change=v))),
    "pm_duration": ("planned maintenance [min] (base 120)", 60.0, 240.0,
                    lambda s, v: s.with_(pm_duration=v)),
    "qa_hold": ("QA release hold mean [min] (base 2880)", 1440.0, 4320.0,
                lambda s, v: s.with_(qa_hold=(v, s.qa_hold[1]))),
    "hvac": ("clean-room HVAC load [kW] (base 120)", 60.0, 180.0,
             lambda s, v: s.with_(power=replace(s.power, hvac=v))),
    "camera": ("camera defect detection (base 0.98)", 0.95, 0.995,
               lambda s, v: s.with_(camera_detect=v)),
}
KPIS = ("lead_time_h", "on_time_rate", "kwh_per_1000_good", "maintenance_h", "escaped_ppm", "oee")


def levels() -> list[tuple[str, str, float, Scenario]]:
    """(param, level, value, scenario) for the shared baseline plus a low and high per parameter."""
    out = [("baseline", "base", float("nan"), BASE)]
    for name, (_, lo, hi, build) in PARAMS.items():
        out += [(name, "low", lo, build(BASE, lo)), (name, "high", hi, build(BASE, hi))]
    return out


def _run(args) -> dict:
    spec, (param, level, value, sc), seed = args
    k = simulate(ex.build_policy(spec), sc, seed)
    return {"param": param, "level": level, "value": value, "policy": spec["name"], "seed": seed, **k}


def run(specs: list[dict], seeds, workers: int | None = None) -> pd.DataFrame:
    jobs = [(sp, lv, s) for lv in levels() for sp in specs for s in seeds]
    with ProcessPoolExecutor(workers, initializer=ex._init_worker) as pool:
        return pd.DataFrame(list(pool.map(_run, jobs, chunksize=4)))


def paired(df: pd.DataFrame, baseline: str = "SETUP+PM", policy: str = "PRED-MO") -> pd.DataFrame:
    """PRED-MO minus baseline per parameter level and KPI, with 95 % CI and p-value."""
    rows = []
    for (param, level), d in df.groupby(["param", "level"], sort=False):
        d = d.assign(scenario=f"{param}:{level}")
        for k in KPIS:
            r = ex.paired_vs(d, baseline, policy, k).iloc[0].to_dict()
            means = d.groupby("policy")[k].mean()
            rows.append({"param": param, "level": level, "value": d.value.iloc[0], "kpi": k,
                         f"{baseline}": means[baseline], f"{policy}": means[policy],
                         "diff": r["mean_diff"], "ci": r["ci"], "rel_%": r["rel_change_%"],
                         "p": r["p_value"]})
    return pd.DataFrame(rows)


# Direction in which PRED-MO counts as better (negative diff is better unless listed here).
HIGHER_IS_BETTER = {"on_time_rate", "oee"}


def markdown(t: pd.DataFrame) -> str:
    out = ["PRED-MO minus SETUP+PM (relative %, paired over common seeds; * = p < 0.05).", "",
           "| parameter | level | value | " + " | ".join(KPIS) + " |",
           "|---|---|---|" + "---|" * len(KPIS)]
    for (param, level), g in t.groupby(["param", "level"], sort=False):
        g = g.set_index("kpi")
        cells = [f"{g.loc[k, 'rel_%']:+.1f}{'*' if g.loc[k, 'p'] < 0.05 else ''}" for k in KPIS]
        val = "" if pd.isna(g["value"].iloc[0]) else f"{g['value'].iloc[0]:g}"
        out.append(f"| {param} | {level} | {val} | " + " | ".join(cells) + " |")
    out += ["", "Parameters:", ""] + [f"- `{n}`: {d}" for n, (d, *_) in PARAMS.items()]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=ex._seeds, default=range(100, 130))
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    specs = [{"name": "FCFS"},
             {"name": "SETUP+PM", **json.loads((ex.RESULTS / "rule.json").read_text())["params"]},
             {"name": "PRED-MO", **json.loads((ex.RESULTS / "tuned.json").read_text())["params"]}]
    df = run(specs, a.seeds, a.workers)
    df.to_csv(ex.RESULTS / "sensitivity_runs.csv", index=False)
    t = paired(df)
    t.to_csv(ex.RESULTS / "sensitivity.csv", index=False)
    md = markdown(t)
    (ex.RESULTS / "sensitivity.md").write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
