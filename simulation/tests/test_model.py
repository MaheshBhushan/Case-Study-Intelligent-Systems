import math

import numpy as np
import pytest

from moulding_sim.config import DAY, PRODUCTS, SCENARIOS, Scenario
from moulding_sim.model import Factory, make_jobs, simulate
from moulding_sim.policies import FCFS, SPT, Policy, Predictive, RulePM, SetupAware

BASE = SCENARIOS["base"]
P = {p.name: p for p in PRODUCTS}
NO_ORDERS = BASE.with_(interarrival=1e12)


class NeverRNF:
    """Stub rng so the 0.1 % random failure never fires in rule tests."""

    def random(self):
        return 1.0

    def uniform(self, a, b):
        return (a + b) / 2


def presses(f: Factory, cls: str):
    return [m for m in f.stations["moulding"].machines if m.cls.name == cls]


def job_for(f: Factory, product: str):
    return next(j for j in make_jobs(BASE, 0) if j.product.name == product)


# ---- common random numbers / reproducibility ------------------------------------------
def test_order_stream_depends_only_on_seed():
    key = lambda js: [(j.product.name, j.qty, j.arrival, j.due, j.perf) for j in js]
    assert key(make_jobs(BASE, 7)) == key(make_jobs(BASE, 7))
    assert key(make_jobs(BASE, 8)) != key(make_jobs(BASE, 7))


def test_policies_face_identical_scenario():
    fa, fb = Factory(BASE, FCFS(), 3), Factory(BASE, SPT(), 3)
    assert [(j.qty, j.arrival) for j in fa.jobs] == [(j.qty, j.arrival) for j in fb.jobs]


def test_simulation_is_deterministic_per_seed():
    assert simulate(SetupAware(), BASE, 5) == simulate(SetupAware(), BASE, 5)


# ---- flow conservation ------------------------------------------------------------------
def test_every_order_ships_and_counts_are_consistent():
    f = Factory(SCENARIOS["low"], SetupAware(), 1)
    k = f.run()
    assert k["unfinished"] == 0 and not f.wip
    for j in f.jobs:
        assert j.done is not None and j.done - j.arrival >= sum(j.proc.values()) - 1e-6
        assert 0 <= j.rejects + j.escaped <= j.qty
    assert 0 < k["oee"] <= k["availability"] <= 1


def test_qa_hold_shifts_release_without_touching_production():
    short = BASE.with_(qa_hold=(1440.0, 1e-6))
    long = BASE.with_(qa_hold=(4320.0, 1e-6))
    a, b = simulate(FCFS(), short, 2), simulate(FCFS(), long, 2)
    assert b["lead_time_h"] - a["lead_time_h"] == pytest.approx(48.0, abs=0.01)
    assert a["availability"] == b["availability"] and a["maintenance_h"] == b["maintenance_h"]


# ---- moulds, presses and changeovers ------------------------------------------------------
def test_mould_fits_only_compatible_press_classes():
    f = Factory(NO_ORDERS, FCFS(), 0)
    wheel = job_for(f, "counter_wheel")  # S-class mould only
    assert presses(f, "S")[0].eligible(wheel)
    assert not presses(f, "M")[0].eligible(wheel)


def test_each_mould_copy_is_on_at_most_one_press():
    f = Factory(NO_ORDERS, FCFS(), 0)
    s = presses(f, "S")
    wheel = job_for(f, "counter_wheel")  # 2 copies
    s[0].mount(wheel)
    s[1].mount(wheel)
    assert s[0].mould is not s[1].mould
    assert not s[2].eligible(wheel)  # both copies are in use
    assert s[0].eligible(wheel)  # its own copy stays usable


def test_sequence_dependent_setup_times():
    f = Factory(NO_ORDERS, FCFS(), 0)
    m, s = presses(f, "M")[0], BASE.setup
    full = s.line_clearance + s.mould_change + s.mould_heatup
    assert m.setup_time(P["housing_white"]) == full + s.purge  # empty press
    m.mount(job_for(f, "housing_white"))
    m.product = P["housing_white"]
    assert m.setup_time(P["housing_white"]) == 0
    assert m.setup_time(P["housing_blue"]) == s.line_clearance + s.purge  # colour change, same mould
    assert m.setup_time(P["pen_body"]) == full + s.purge  # new mould, ABS -> PC
    m2 = presses(f, "S")[0]
    m2.mount(job_for(f, "mouthpiece_cap"))
    m2.product = P["mouthpiece_cap"]
    assert m2.setup_time(P["pen_cap_white"]) == full  # new mould, same PP white: no purge
    assert m.needs_setter(P["housing_blue"])


def test_night_shift_leaves_one_setter():
    f = Factory(NO_ORDERS, FCFS(), 0)
    c = BASE.crew
    f.env.run(until=23 * 60)
    assert f.setters.count == c.setters_day - c.setters_night
    f.env.run(until=DAY + 12 * 60)
    assert f.setters.count == 0


# ---- energy ---------------------------------------------------------------------------------
def test_empty_plant_energy_is_hvac_plus_idle_load():
    from moulding_sim.config import PRESS_CLASSES
    k = Factory(NO_ORDERS, FCFS(), 0).run()
    pw = NO_ORDERS.power
    idle = (sum(c.idle_kw * c.count for c in PRESS_CLASSES) + pw.station_idle["drying"] * NO_ORDERS.dryers
            + sum(pw.station_idle[s] * n for s, n in NO_ORDERS.lines.items()))
    hours = (NO_ORDERS.horizon - NO_ORDERS.warmup) / 60
    assert k["energy_kwh"] == pytest.approx((pw.hvac + idle) * hours)


class ShutdownFCFS(FCFS):
    idle_off = 30.0


def test_idle_shutdown_saves_energy_when_plant_is_starved():
    sc = BASE.with_(interarrival=4000.0)
    assert simulate(ShutdownFCFS(), sc, 0)["energy_kwh"] < simulate(FCFS(), sc, 0)["energy_kwh"]


# ---- inspection ------------------------------------------------------------------------------
def test_perfect_camera_lets_no_defect_escape():
    perfect = SCENARIOS["low"].with_(camera_detect=1.0, camera_false_reject=0.0)
    blind = SCENARIOS["low"].with_(camera_detect=0.0, camera_false_reject=0.0)
    assert simulate(FCFS(), perfect, 0)["escaped_ppm"] == 0
    assert simulate(FCFS(), blind, 0)["escaped_ppm"] > 0


# ---- AI4I failure rules and repairs -----------------------------------------------------------
def moulder():
    m = presses(Factory(NO_ORDERS, FCFS(), 0), "M")[0]
    m.rng = NeverRNF()
    m.twf_at = 220.0
    return m


@pytest.mark.parametrize("reading, mode", [
    ([1, 300.0, 310.0, 1500.0, 40.0, 50.0], None),
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
    m.rng = np.random.default_rng(0)
    cases = [("TWF", 0, 1), ("HDF", 1, 0), ("PWF", 1, 1), ("MOULD", 1, 1), (None, 0, 0)]
    for mode, wear_left, fouling_left in cases:
        m.wear, m.fouling = 150.0, 1.5
        m.restore(mode)
        assert (m.wear > 0, m.fouling > 0) == (bool(wear_left), bool(fouling_left)), mode


# ---- policies ------------------------------------------------------------------------------------
class ConstRisk:
    def __init__(self, value):
        self.value = value

    def predict(self, rows):
        return np.full(len(rows), self.value)


def test_setup_aware_prefers_mounted_mould():
    f = Factory(NO_ORDERS, FCFS(), 0)
    m = presses(f, "M")[0]
    q = [job_for(f, "pen_body"), job_for(f, "housing_white"), job_for(f, "housing_blue")]
    m.mount(q[2])
    m.product = q[2].product
    assert SetupAware().select(q, m, 0.0) is q[2]
    assert FCFS().select(q, m, 0.0) is q[0]


def test_rule_pm_triggers_on_wear_or_fouling():
    m = moulder()
    job = job_for(m.f, "pen_body")
    rule = RulePM(wear_limit=180.0, fouling_limit=1.2)
    m.wear, m.fouling = 100.0, 0.0
    assert not rule.wants_pm(m, job)
    m.wear = 180.0
    assert rule.wants_pm(m, job)
    m.wear, m.fouling = 0.0, 1.2
    assert rule.wants_pm(m, job)


def test_predictive_due_weight_and_pm_threshold():
    m = moulder()
    q = [job_for(m.f, "pen_body"), job_for(m.f, "housing_white")]
    q[1].due = 0.0
    pol = Predictive(ConstRisk(0.3), w_due=1.0, w_setup=0, w_spt=0, w_risk=0, pm_threshold=0.5)
    assert pol.select(q, m, 0.0) is q[1]
    assert not pol.wants_pm(m, q[1])
    assert Predictive(ConstRisk(0.6), pm_threshold=0.5).wants_pm(m, q[1])


def test_baselines_never_shut_down_or_do_pm():
    assert all(math.isinf(p.idle_off) for p in (FCFS(), SPT(), SetupAware(), RulePM()))
    assert not Policy().wants_pm(None, None)
