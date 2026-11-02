import math

import pytest

from moulding_sim.config import PRODUCTS, SCENARIOS, Scenario
from moulding_sim.model import Factory, make_jobs, simulate
from moulding_sim.policies import FCFS, SPT, Policy, Predictive, SetupAware

BASE = SCENARIOS["base"]
P = {p.name: p for p in PRODUCTS}


class NeverRNF:
    """Stub rng so the 0.1 % random failure never fires in rule tests."""

    def random(self):
        return 1.0

    def uniform(self, a, b):
        return (a + b) / 2


def moulder(sc: Scenario = BASE):
    m = Factory(sc, FCFS(), seed=0).stations["moulding"].machines[0]
    m.rng = NeverRNF()
    m.twf_at = 220.0
    return m


# ---- common random numbers / reproducibility ---------------------------------------
def test_order_stream_depends_only_on_seed():
    a, b = make_jobs(BASE, 7), make_jobs(BASE, 7)
    assert [(j.product.name, j.qty, j.arrival, j.due) for j in a] == \
           [(j.product.name, j.qty, j.arrival, j.due) for j in b]
    assert [j.arrival for j in make_jobs(BASE, 8)] != [j.arrival for j in a]


def test_policies_face_identical_demand():
    fa, fb = Factory(BASE, FCFS(), 3), Factory(BASE, SPT(), 3)
    assert [(j.qty, j.arrival) for j in fa.jobs] == [(j.qty, j.arrival) for j in fb.jobs]


def test_simulation_is_deterministic_per_seed():
    assert simulate(SetupAware(), BASE, 5) == simulate(SetupAware(), BASE, 5)


# ---- flow conservation ----------------------------------------------------------------
def test_every_order_finishes_and_output_never_exceeds_input():
    f = Factory(SCENARIOS["low"], SetupAware(), 1)
    k = f.run()
    assert all(j.done is not None and j.done >= j.arrival for j in f.jobs)
    assert not f.wip and k["unfinished"] == 0
    assert all(0 <= j.rejects <= j.qty for j in f.jobs)
    assert 0 < k["scrap_rate"] < 1 and 0 <= k["on_time_rate"] <= 1


def test_jobs_visit_stations_in_line_order():
    f = Factory(SCENARIOS["low"], FCFS(), 2)
    f.run()
    for j in f.jobs:  # lead time cannot beat the pure processing time
        assert j.done - j.arrival >= sum(j.proc.values()) - 1e-6


# ---- changeovers ------------------------------------------------------------------------
def test_sequence_dependent_setup_times():
    m, s = moulder(), BASE.setup
    full = s.line_clearance + s.mould_change + s.mould_heatup
    assert m.setup_time(P["pen_body"]) == full  # nothing mounted yet
    m.product = P["pen_body"]
    assert m.setup_time(P["pen_body"]) == 0
    assert m.setup_time(P["pen_clip"]) == s.line_clearance + s.insert_change  # same mould B
    assert m.setup_time(P["lancet_cap"]) == full


# ---- energy -------------------------------------------------------------------------------
def test_empty_plant_energy_is_hvac_plus_idle_load():
    sc = BASE.with_(interarrival=1e12)  # no orders arrive
    k = Factory(sc, FCFS(), 0).run()
    pw = sc.power
    idle_kw = (pw.idle["drying"] * sc.dryer_capacity + pw.idle["moulding"] * sc.moulding_machines
               + pw.idle["inspection"] + pw.idle["assembly"] + pw.idle["packaging"])
    hours = (sc.horizon - sc.warmup) / 60
    assert k["energy_kwh"] == pytest.approx((pw.hvac + idle_kw) * hours)


class ShutdownFCFS(FCFS):
    idle_off = 30.0


def test_idle_shutdown_saves_energy_when_line_is_starved():
    sc = SCENARIOS["base"].with_(interarrival=1500.0)
    on, off = simulate(FCFS(), sc, 0), simulate(ShutdownFCFS(), sc, 0)
    assert off["energy_kwh"] < on["energy_kwh"]


# ---- AI4I failure rules and repairs -------------------------------------------------------
HEALTHY = [1, 300.0, 310.0, 1500.0, 40.0, 50.0]


@pytest.mark.parametrize("reading, mode", [
    (HEALTHY, None),
    ([1, 300.0, 310.0, 1500.0, 40.0, 225.0], "TWF"),  # wear past threshold 220
    ([1, 300.0, 308.4, 1350.0, 40.0, 50.0], "HDF"),  # dT < 8.6 K and rpm < 1380
    ([1, 300.0, 308.4, 1450.0, 40.0, 50.0], None),  # dT low but rpm high enough
    ([1, 300.0, 310.0, 1500.0, 60.0, 50.0], "PWF"),  # 9.4 kW > 9 kW
    ([1, 300.0, 310.0, 1700.0, 18.0, 50.0], "PWF"),  # 3.2 kW < 3.5 kW
    ([0, 300.0, 310.0, 1400.0, 55.0, 205.0], "OSF"),  # 11275 > 11000 (type L)
    ([2, 300.0, 310.0, 1400.0, 55.0, 205.0], None),  # type H tolerates 13000
])
def test_ai4i_failure_rules(reading, mode):
    t = {0: "L", 1: "M", 2: "H"}[reading[0]]
    assert moulder().failure_mode(reading, t) == mode


def test_repair_fixes_only_failed_component_and_pm_fixes_all():
    m = moulder()
    m.rng = __import__("numpy").random.default_rng(0)
    for mode, wear_left, fouling_left in [("TWF", 0, 1), ("HDF", 1, 0), ("PWF", 1, 1), (None, 0, 0)]:
        m.wear, m.fouling = 150.0, 1.5
        m.restore(mode)
        assert (m.wear > 0, m.fouling > 0) == (bool(wear_left), bool(fouling_left)), mode


# ---- dispatching rules --------------------------------------------------------------------
def _queue():
    jobs = make_jobs(BASE, 0)
    return [next(j for j in jobs if j.product.mould == mould) for mould in "ABC"]


def test_setup_aware_prefers_mounted_mould_and_spt_shortest():
    m = moulder()
    q = _queue()
    m.product = q[2].product
    assert SetupAware().select(q, m, 0.0) is q[2]
    assert SPT().select(q, m, 0.0) is min(q, key=lambda j: j.proc["moulding"])
    assert FCFS().select(q, m, 0.0) is q[0]


class ConstRisk:
    def __init__(self, value):
        self.value = value

    def predict(self, rows):
        import numpy as np
        return np.full(len(rows), self.value)


def test_predictive_due_weight_picks_least_slack_and_pm_threshold():
    m = moulder()
    q = _queue()
    urgent = q[1]
    urgent.due = 0.0
    pol = Predictive(ConstRisk(0.3), w_due=1.0, w_setup=0, w_spt=0, w_risk=0, pm_threshold=0.5)
    assert pol.select(q, m, 0.0) is urgent
    assert not pol.wants_pm(m, urgent)
    assert Predictive(ConstRisk(0.6), pm_threshold=0.5).wants_pm(m, urgent)


def test_baselines_never_shut_down_or_do_pm():
    assert all(math.isinf(p.idle_off) for p in (FCFS(), SPT(), SetupAware()))
    assert not Policy().wants_pm(None, None)
