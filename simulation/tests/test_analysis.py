import numpy as np
import pandas as pd
import pytest

from moulding_sim import morris, sensitivity
from moulding_sim.config import SCENARIOS


def test_sensitivity_levels_change_exactly_one_parameter():
    base = SCENARIOS["base"]
    lv = sensitivity.levels()
    assert len(lv) == 1 + 2 * len(sensitivity.PARAMS)
    for param, level, value, sc in lv[1:]:
        assert sc != base, f"{param} {level} left the scenario unchanged"


def test_morris_trajectory_moves_each_parameter_once_by_delta():
    traj = morris.trajectories(r=5, k=4, seed=3)
    assert traj.shape == (5, 5, 4)
    assert traj.min() >= 0 and traj.max() <= 1 + 1e-9
    for t in traj:
        steps = np.diff(t, axis=0)
        assert np.all((np.abs(steps) > 0).sum(axis=1) == 1)
        assert sorted(np.argmax(np.abs(steps), axis=1)) == list(range(4))
        assert np.allclose(steps.sum(axis=0), morris.DELTA)


def test_morris_box_corners_hit_low_and_high_values():
    k = len(sensitivity.PARAMS)
    lo, hi = morris.scenario(np.zeros(k)), morris.scenario(np.ones(k))
    assert (lo.interarrival, lo.crew.technicians, lo.repair_scale) == (540.0, 1, 0.5)
    assert (hi.interarrival, hi.crew.technicians, hi.repair_scale) == (430.0, 3, 1.5)


def test_morris_screen_recovers_linear_effects():
    """y = PRED-MO minus SETUP+PM; plant a linear effect 3*x0 only, so mu*(param0) = 3, others 0."""
    k = len(sensitivity.PARAMS)
    traj = morris.trajectories(r=4, k=k, seed=1)
    pts = traj.reshape(-1, k)
    rows = []
    for p, x in enumerate(pts):
        for pol, y in (("SETUP+PM", 0.0), ("PRED-MO", 3 * x[0])):
            rows.append({"point": p, "policy": pol, "seed": 0, **{c: y for c in morris.KPIS}})
    t = morris.screen(traj, pd.DataFrame(rows)).query("kpi == 'lead_time_h'").set_index("param")
    first = list(sensitivity.PARAMS)[0]
    assert t.loc[first, "mu_star"] == pytest.approx(3.0)
    assert t.loc[first, "sigma"] == pytest.approx(0.0, abs=1e-9)
    assert t.drop(first)["mu_star"].abs().max() == pytest.approx(0.0, abs=1e-9)
