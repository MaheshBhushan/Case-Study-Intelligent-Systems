"""SimPy discrete-event model of the five-station moulding line.

Flow: drying -> moulding (sequence-dependent setups, AI4I-rule failures, idle shutdown)
-> camera inspection -> assembly -> clean-room packaging.

Common random numbers: orders, sensor noise, repairs and inspection draw from separate
seeded streams, so every policy faces the same demand for a given seed (Law 2015).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import simpy

from .config import OSF_LIMIT, PRODUCTS, STATIONS, TYPE_WEAR, Product, Scenario

TYPE_CODE = {"L": 0, "M": 1, "H": 2}
# Sensor noise sd (air K, process K, rpm, torque Nm); known to the planner from sensor specs.
NOISE_SD = np.array([0.5, 0.5, 50.0, 5.0])
# Fixed quasi-random noise draws for risk estimation: deterministic, so CRN streams stay intact.
RISK_DRAWS = np.random.default_rng(12345).standard_normal((16, 4)) * NOISE_SD


@dataclass(eq=False)
class Job:
    id: int
    product: Product
    qty: int
    arrival: float
    due: float
    rush: bool
    proc: dict[str, float]
    extra_scrap: int = 0  # start-up / purge shots
    rejects: int = 0
    wear_frac: float = 0.0  # machine wear when moulded; drives inspection rejects
    done: float | None = None

    def remaining_work(self, station: str) -> float:
        return sum(self.proc[s] for s in STATIONS[STATIONS.index(station):])


def make_jobs(sc: Scenario, seed: int) -> list[Job]:
    rng = np.random.default_rng([seed, 1])
    jobs, t = [], 0.0
    while True:
        t += rng.exponential(sc.interarrival)
        if t > sc.horizon:
            return jobs
        p = PRODUCTS[rng.integers(len(PRODUCTS))]
        qty = int(rng.integers(sc.lot_min, sc.lot_max + 1)) // 100 * 100
        rush = bool(rng.random() < sc.rush_share)
        due = t + 60 * (rng.uniform(12, 24) if rush else rng.uniform(36, 96))
        proc = {
            "drying": p.drying_min,
            "moulding": qty / p.cavities * p.cycle_s / 60,
            **{s: qty / sc.rates[s] for s in ("inspection", "assembly", "packaging")},
        }
        jobs.append(Job(len(jobs), p, qty, t, due, rush, proc))


@dataclass
class Failure:
    time: float
    machine: str
    mode: str
    repair: float
    disrupted: list[Job] = field(default_factory=list)


class Station:
    def __init__(self, factory: Factory, name: str, n: int):
        self.f, self.name = factory, name
        self.queue: list[Job] = []
        self.wake = factory.env.event()
        self.machines = [Machine(factory, self, i) for i in range(n)]

    def put(self, job: Job) -> None:
        self.queue.append(job)
        old, self.wake = self.wake, self.f.env.event()
        old.succeed()


class Machine:
    def __init__(self, factory: Factory, station: Station, idx: int):
        self.f, self.st, self.idx = factory, station, idx
        self.name = f"{station.name}{idx}"
        self.state, self.since = "idle", 0.0
        self.product: Product | None = None
        self.moulding = station.name == "moulding"
        self.rng = np.random.default_rng([factory.seed, 2, STATIONS.index(station.name), idx])
        self.wear = self.fouling = 0.0
        self.twf_at = self.rng.uniform(200, 240)
        self.busy_min = 0.0
        factory.env.process(self.run())

    # ---- energy -------------------------------------------------------------
    def set_state(self, state: str) -> None:
        now = self.f.env.now
        self.f.add_energy(self.power(), self.since, now)
        if self.state == "busy":
            self.busy_min += now - self.since
        self.state, self.since = state, now

    def power(self) -> float:
        p = self.f.sc.power
        return {
            "busy": p.busy[self.st.name], "idle": p.idle[self.st.name], "setup": p.setup,
            "down": p.setup, "off": p.off, "warmup": p.warmup,
        }[self.state]

    # ---- changeovers ----------------------------------------------------------
    def setup_time(self, product: Product) -> float:
        if not self.moulding or self.product is product:
            return 0.0
        s = self.f.sc.setup
        if self.product is not None and self.product.mould == product.mould:
            return s.line_clearance + s.insert_change
        return s.line_clearance + s.mould_change + s.mould_heatup

    # ---- degradation (AI4I feature space) --------------------------------------
    def wear_increment(self, job: Job) -> float:
        return job.proc["moulding"] * self.f.sc.wear_per_min * TYPE_WEAR[job.product.ai4i_type] / 3

    def air_temp(self) -> float:
        return 300.0 + 2.0 * math.sin(2 * math.pi * self.f.env.now / 1440)

    def risk_readings(self, job: Job) -> np.ndarray:
        """Feature rows the predictor sees: current state + job nominals over sensor-noise draws."""
        air = self.air_temp()
        p = job.product
        base = np.array([TYPE_CODE[p.ai4i_type], air, air + 10 - self.fouling, p.rpm, p.torque,
                         self.wear + self.wear_increment(job)])
        rows = np.tile(base, (len(RISK_DRAWS), 1))
        rows[:, 1] += RISK_DRAWS[:, 0]
        rows[:, 2] += RISK_DRAWS[:, 0] + RISK_DRAWS[:, 1]
        rows[:, 3:5] += RISK_DRAWS[:, 2:4]
        return rows

    def actual_reading(self, job: Job) -> list[float]:
        e = self.rng.standard_normal(4) * NOISE_SD
        air = self.air_temp() + e[0]
        p = job.product
        return [TYPE_CODE[p.ai4i_type], air, air + 10 - self.fouling + e[1],
                p.rpm + e[2], p.torque + e[3], self.wear + self.wear_increment(job)]

    def failure_mode(self, reading: list[float], ai4i_type: str) -> str | None:
        """Ground truth = AI4I 2020 failure rules (Matzka 2020)."""
        _, air, proc_t, rpm, torque, wear = reading
        if wear >= self.twf_at:
            return "TWF"
        if proc_t - air < 8.6 and rpm < 1380:
            return "HDF"
        watts = torque * rpm * 2 * math.pi / 60
        if watts < 3500 or watts > 9000:
            return "PWF"
        if wear * torque > OSF_LIMIT[ai4i_type]:
            return "OSF"
        if self.rng.random() < 0.001:
            return "RNF"
        return None

    def restore(self, mode: str | None = None) -> None:
        """PM (mode=None) restores everything; a repair fixes only the failed component."""
        if mode in (None, "TWF", "OSF"):
            self.wear = 0.0
            self.twf_at = self.rng.uniform(200, 240)
        if mode in (None, "HDF"):
            self.fouling = 0.0

    # ---- process ----------------------------------------------------------------
    def run(self):
        env, st, pol = self.f.env, self.st, self.f.policy
        idle_off = pol.idle_off if self.moulding else math.inf
        while True:
            if not st.queue:
                self.set_state("idle")
                wake = st.wake
                if math.isinf(idle_off):
                    yield wake
                    continue
                yield wake | env.timeout(idle_off)
                if not wake.triggered:
                    self.set_state("off")
                    while not st.queue:
                        yield st.wake
                    self.set_state("warmup")
                    yield env.timeout(self.f.sc.power.warmup_min)
                continue
            job = pol.select(st.queue, self, env.now)
            st.queue.remove(job)
            if self.moulding:
                yield from self.mould(job)
            else:
                self.set_state("busy")
                yield env.timeout(job.proc[st.name])
                if st.name == "inspection":
                    p = self.f.sc.base_scrap + 0.03 * job.wear_frac
                    job.rejects = int(self.f.insp_rng.binomial(job.qty, min(p, 1.0)))
            self.f.forward(job, st.name)

    def mould(self, job: Job):
        env, sc, pol = self.f.env, self.f.sc, self.f.policy
        if pol.wants_pm(self, job):
            self.set_state("setup")
            yield env.timeout(sc.pm_duration)
            self.restore()
            self.f.pm_times.append(env.now)
        setup = self.setup_time(job.product)
        if setup:
            self.set_state("setup")
            yield env.timeout(setup)
            self.product = job.product
            job.extra_scrap += sc.startup_scrap_units
            self.f.setup_min += setup
        reading = self.actual_reading(job)
        mode = self.failure_mode(reading, job.product.ai4i_type)
        self.f.readings.append((*reading, int(mode is not None)))
        job.wear_frac = min(reading[5] / 240, 1.0)
        self.set_state("busy")
        proc = job.proc["moulding"]
        if mode is None:
            yield env.timeout(proc)
            self.wear += self.wear_increment(job)
            self.fouling += proc * sc.fouling_per_min
            return
        u = self.rng.uniform()
        yield env.timeout(u * proc)
        repair = float(self.f.repair_rng.lognormal(*_lognormal_params(sc.repair_mean, sc.repair_sd)))
        self.f.failures.append(Failure(env.now, self.name, mode, repair, list(self.f.wip)))
        self.set_state("down")
        yield env.timeout(repair)
        self.restore(mode)
        job.extra_scrap += sc.restart_scrap_units
        self.set_state("busy")
        yield env.timeout((1 - u) * proc)
        self.wear += (1 - u) * self.wear_increment(job)
        self.fouling += (1 - u) * proc * sc.fouling_per_min


def _lognormal_params(mean: float, sd: float) -> tuple[float, float]:
    s2 = math.log(1 + (sd / mean) ** 2)
    return math.log(mean) - s2 / 2, math.sqrt(s2)


class Factory:
    def __init__(self, sc: Scenario, policy, seed: int):
        self.sc, self.policy, self.seed = sc, policy, seed
        self.env = simpy.Environment()
        self.insp_rng = np.random.default_rng([seed, 3])
        self.repair_rng = np.random.default_rng([seed, 4])
        self.energy_kwh = 0.0
        self.wip: set[Job] = set()
        self.failures: list[Failure] = []
        self.readings: list[tuple] = []
        self.pm_times: list[float] = []
        self.setup_min = 0.0
        self.jobs = make_jobs(sc, seed)
        n = {"drying": sc.dryer_capacity, "moulding": sc.moulding_machines}
        self.stations = {s: Station(self, s, n.get(s, 1)) for s in STATIONS}
        self.env.process(self.release())

    def add_energy(self, kw: float, a: float, b: float) -> None:
        overlap = min(b, self.sc.horizon) - max(a, self.sc.warmup)
        if overlap > 0:
            self.energy_kwh += kw * overlap / 60

    def release(self):
        for job in self.jobs:
            yield self.env.timeout(job.arrival - self.env.now)
            self.wip.add(job)
            self.stations["drying"].put(job)

    def forward(self, job: Job, station: str) -> None:
        i = STATIONS.index(station)
        if i + 1 < len(STATIONS):
            self.stations[STATIONS[i + 1]].put(job)
        else:
            job.done = self.env.now
            self.wip.discard(job)

    def run(self) -> dict:
        sc = self.sc
        end = sc.horizon + sc.drain
        self.env.run(until=end)
        for st in self.stations.values():
            for m in st.machines:
                m.set_state(m.state)  # flush energy
        self.add_energy(sc.power.hvac, 0.0, end)
        return self.kpis(end)

    def kpis(self, end: float) -> dict:
        sc = self.sc
        w0, w1 = sc.warmup, sc.horizon
        hours = (w1 - w0) / 60
        released = [j for j in self.jobs if w0 <= j.arrival <= w1]
        finished = [j for j in self.jobs if j.done is not None and w0 <= j.done <= w1]
        good = sum(j.qty - j.rejects for j in finished)
        made = sum(j.qty + j.extra_scrap for j in finished)
        lead = [((j.done if j.done is not None else end) - j.arrival) / 60 for j in released]
        on_time = [j.done is not None and j.done <= j.due for j in released]
        fails = [f for f in self.failures if w0 <= f.time <= w1]
        pms = [t for t in self.pm_times if w0 <= t <= w1]
        recov = [(max((j.done if j.done is not None else end) for j in f.disrupted) - f.time) / 60
                 for f in fails if f.disrupted]
        moulders = self.stations["moulding"].machines
        return {
            "throughput_uph": good / hours,
            "lead_time_h": float(np.mean(lead)) if lead else 0.0,
            "on_time_rate": float(np.mean(on_time)) if on_time else 1.0,
            "energy_kwh": self.energy_kwh,
            "kwh_per_1000_good": 1000 * self.energy_kwh / good if good else math.inf,
            "scrap_rate": 1 - good / made if made else 0.0,
            "failures": len(fails),
            "pm_events": len(pms),
            "downtime_h": sum(f.repair for f in fails) / 60,  # unplanned repairs only
            "pm_h": len(pms) * sc.pm_duration / 60,
            "maintenance_h": (sum(f.repair for f in fails) + len(pms) * sc.pm_duration) / 60,
            "recovery_h": float(np.mean(recov)) if recov else 0.0,
            "setup_h": self.setup_min / 60,
            "moulding_util": sum(m.busy_min for m in moulders) / (len(moulders) * end),
            "unfinished": sum(j.done is None for j in released),
        }


def simulate(policy, scenario: Scenario, seed: int) -> dict:
    return Factory(scenario, policy, seed).run()
