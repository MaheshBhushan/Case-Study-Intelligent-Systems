"""Live demo: one randomised 12-week scenario, all five policies, KPI table in under a minute.

  python -m moulding_sim.demo                      # base demand, seed 100
  python -m moulding_sim.demo --scenario high --seed 123 --trace 5

--trace N prints the first N press dispatch decisions of PRED-MO with every candidate's score
terms, so the weighted multi-objective rule can be explained on real numbers.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter

from .config import FAILURE_LABEL, SCENARIOS
from .experiments import RESULTS, build_policy
from .model import Factory
from .policies import Predictive

COLS = [("lead_time_h", "lead time h", "{:.1f}"), ("on_time_rate", "on time", "{:.1%}"),
        ("kwh_per_1000_good", "kWh/1k good", "{:.2f}"), ("eur_per_1000_good", "EUR/1k good", "{:.3f}"),
        ("oee", "OEE", "{:.3f}"), ("escaped_ppm", "escaped ppm", "{:.0f}"),
        ("failures", "failures", "{:.0f}"), ("pm_events", "PM stops", "{:.0f}"),
        ("maintenance_h", "maint. h", "{:.0f}")]


class TracedPredictive(Predictive):
    """PRED-MO that prints its first `limit` press dispatch decisions."""

    def __init__(self, *a, limit: int = 0, **kw):
        super().__init__(*a, **kw)
        self.limit = limit

    def select(self, queue, m, now):
        job = super().select(queue, m, now)
        if self.limit and m.moulding and len(queue) > 1:
            self.limit -= 1
            st = m.st.name
            risk = self.risks(m, queue) if self.w_risk else [0.0] * len(queue)
            mould = m.mould.name if m.mould else "none"
            print(f"\nday {now / 1440:5.1f}  {m.name} (mould {mould}) chooses among {len(queue)} orders:")
            print(f"  {'product':<16}{'slack d':>9}{'setup min':>11}{'proc d':>8}{'risk':>7}{'score':>8}")
            for j, r in zip(queue, risk):
                slack = (j.due - now - j.remaining_work(st)) / 1440
                setup = m.setup_time(j.product)
                score = (self.w_due * slack + self.w_setup * setup / 255
                         + self.w_spt * j.proc[st] / 1440 + self.w_risk * r)
                mark = "  <- chosen" if j is job else ""
                print(f"  {j.product.name:<16}{slack:9.1f}{setup:11.0f}{j.proc[st] / 1440:8.2f}"
                      f"{r:7.3f}{score:8.3f}{mark}")
        return job


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="base", choices=list(SCENARIOS))
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--trace", type=int, default=0)
    a = ap.parse_args()
    sc = SCENARIOS[a.scenario]
    rule = json.loads((RESULTS / "rule.json").read_text())["params"]
    tuned = json.loads((RESULTS / "tuned.json").read_text())["params"]
    specs = [{"name": "FCFS"}, {"name": "SPT"}, {"name": "SETUP"}, {"name": "SETUP+PM", **rule}]
    print(f"Scenario '{a.scenario}', seed {a.seed}: orders every {sc.interarrival:.0f} min on average, "
          f"KPIs from week {sc.warmup / 10080:.0f} to week {sc.horizon / 10080:.0f}.")
    print("PRED-MO tuned settings: " + ", ".join(f"{k}={v:.3g}" for k, v in tuned.items()))

    results = []
    for spec in specs + [{"name": "PRED-MO", **tuned}]:
        t = time.perf_counter()
        if spec["name"] == "PRED-MO":
            pol = TracedPredictive(build_policy(spec).risk_model, limit=a.trace, **tuned)
        else:
            pol = build_policy(spec)
        f = Factory(sc, pol, a.seed)
        k = f.run()
        modes = Counter(x.mode for x in f.failures if sc.warmup <= x.time <= sc.horizon)
        results.append((spec["name"], k, modes, time.perf_counter() - t))

    w = 11
    print("\n" + f"{'policy':<10}" + "".join(f"{h:>{w + 2}}" for _, h, _ in COLS) + f"{'run s':>8}")
    for name, k, _, secs in results:
        print(f"{name:<10}" + "".join(f"{fmt.format(k[c]):>{w + 2}}" for c, _, fmt in COLS) + f"{secs:8.1f}")

    print("\nBreakdowns by failure mode (KPI window):")
    for name, _, modes, _ in results:
        print(f"  {name:<10}" + ", ".join(f"{FAILURE_LABEL[m]} {n}" for m, n in modes.most_common()))
    print("\nOne seed is one scenario; the claims in results/summary.md use 100 held-out seeds and paired tests.")


if __name__ == "__main__":
    main()
