"""Morris elementary-effects screening of the assumed plant parameters (Morris 1991).

The one-at-a-time sweep in `sensitivity` moves one parameter while the rest stay at base. Morris
moves all parameters along random trajectories through the low-high box, so an effect that depends
on other parameters shows up as a large spread (sigma) of the elementary effects.

Output per parameter and KPI, for y = PRED-MO minus SETUP+PM on common seeds:
  mu_star  mean |elementary effect|: how much the parameter moves PRED-MO's advantage
  sigma    sd of the elementary effects: non-linearity or interaction with other parameters

Usage: python -m moulding_sim.morris [--trajectories 10] [--seeds 100-103] [--workers 8]
Writes results/morris_runs.csv, results/morris.csv and results/morris.md.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from . import experiments as ex
from .config import SCENARIOS, Scenario
from .model import simulate
from .sensitivity import PARAMS

LEVELS = 4
DELTA = LEVELS / (2 * (LEVELS - 1))  # 2/3: standard Morris step for 4 grid levels
KPIS = ("lead_time_h", "kwh_per_1000_good", "eur_per_1000_good", "maintenance_h")
INTEGER = {"technicians", "setters"}


def trajectories(r: int, k: int, seed: int = 0) -> np.ndarray:
    """r trajectories of k+1 points in [0, 1]^k; step j moves one coordinate up by DELTA."""
    rng = np.random.default_rng(seed)
    grid = np.arange(LEVELS) / (LEVELS - 1)
    out = np.empty((r, k + 1, k))
    for t in range(r):
        x = rng.choice(grid[grid + DELTA <= 1 + 1e-9], size=k)
        out[t, 0] = x
        for step, i in enumerate(rng.permutation(k), start=1):
            x = x.copy()
            x[i] += DELTA
            out[t, step] = x
    return out


def scenario(x: np.ndarray) -> Scenario:
    """Map a point of the unit box to a scenario between each parameter's low and high value."""
    sc = SCENARIOS["base"]
    for xi, (name, (_, lo, hi, build)) in zip(x, PARAMS.items()):
        v = lo + xi * (hi - lo)
        sc = build(sc, round(v) if name in INTEGER else v)
    return sc


def _run(args) -> dict:
    spec, point, x, seed = args
    k = simulate(ex.build_policy(spec), scenario(x), seed)
    return {"point": point, "policy": spec["name"], "seed": seed, **{c: k[c] for c in KPIS}}


def screen(traj: np.ndarray, runs: pd.DataFrame) -> pd.DataFrame:
    """mu*, sigma per parameter and KPI from the per-point mean PRED-MO minus SETUP+PM difference."""
    m = runs.groupby(["point", "policy"])[list(KPIS)].mean()
    y = (m.xs("PRED-MO", level="policy") - m.xs("SETUP+PM", level="policy")).sort_index()
    r, n, _ = traj.shape
    names = list(PARAMS)
    rows = []
    for kpi in KPIS:
        yy = y[kpi].to_numpy().reshape(r, n)
        effects = {nm: [] for nm in names}
        for t in range(r):
            for s in range(1, n):
                i = int(np.flatnonzero(traj[t, s] != traj[t, s - 1])[0])
                effects[names[i]].append((yy[t, s] - yy[t, s - 1]) / DELTA)
        for nm in names:
            e = np.array(effects[nm])
            rows.append({"kpi": kpi, "param": nm, "mu_star": np.abs(e).mean(), "mu": e.mean(),
                         "sigma": e.std(ddof=1), "base_diff": y[kpi].mean()})
    return pd.DataFrame(rows)


def markdown(t: pd.DataFrame) -> str:
    out = []
    for kpi, g in t.groupby("kpi", sort=False):
        g = g.sort_values("mu_star", ascending=False)
        out += [f"### {kpi}  (mean PRED-MO minus SETUP+PM over all points: {g.base_diff.iloc[0]:+.3g})", "",
                "| parameter | mu* | mu | sigma | sigma/mu* |", "|---|---|---|---|---|"]
        out += [f"| {r.param} | {r.mu_star:.3g} | {r.mu:+.3g} | {r.sigma:.3g} | "
                f"{r.sigma / r.mu_star if r.mu_star else float('nan'):.2f} |" for r in g.itertuples()]
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectories", type=int, default=10)
    ap.add_argument("--seeds", type=ex._seeds, default=range(100, 104))
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    specs = [{"name": "SETUP+PM", **json.loads((ex.RESULTS / "rule.json").read_text())["params"]},
             {"name": "PRED-MO", **json.loads((ex.RESULTS / "tuned.json").read_text())["params"]}]
    traj = trajectories(a.trajectories, len(PARAMS))
    pts = traj.reshape(-1, len(PARAMS))
    jobs = [(sp, p, x, s) for p, x in enumerate(pts) for sp in specs for s in a.seeds]
    with ProcessPoolExecutor(a.workers, initializer=ex._init_worker) as pool:
        runs = pd.DataFrame(list(pool.map(_run, jobs, chunksize=4)))
    runs.to_csv(ex.RESULTS / "morris_runs.csv", index=False)
    t = screen(traj, runs)
    t.to_csv(ex.RESULTS / "morris.csv", index=False)
    md = markdown(t)
    (ex.RESULTS / "morris.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
