"""SimPy discrete-event model of a medical injection-moulding plant.

Flow per campaign order: drying -> moulding (12 presses, 3 tonnage classes) -> camera inspection
-> assembly -> clean-room packaging -> GMP QA release.

Moulding detail: each mould exists once and fits only some press classes; changeovers need a
setter (3 on day shifts, 1 at night); presses degrade with use and are checked once per shift
against the AI4I 2020 failure rules; repairs need a maintenance technician, mould damage and
mould service need the toolroom.

Common random numbers: orders, sensor noise, repairs and inspection use separate seeded random
streams, so every policy faces the same randomised scenario for a given seed (Law 2015).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import simpy

from .config import (DAY, MATERIALS, MOULDS, OSF_LIMIT, PRESS_CLASSES, PRODUCTS, REPAIR, STATIONS,
                     TYPE_WEAR, PressClass, Product, Scenario)

TYPE_CODE = {"L": 0, "M": 1, "H": 2}
# Sensor noise sd (air K, process K, rpm, torque Nm); known to the planner from sensor specs.
NOISE_SD = np.array([0.5, 0.5, 50.0, 5.0])
# Fixed noise draws for risk estimation: deterministic, so CRN streams stay intact.
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
    rejects: int = 0  # removed at inspection (true defects + false rejects)
    escaped: int = 0  # defects the camera missed
    wear_frac: float = 0.0  # screw wear when moulded; drives the defect rate
    perf: float = 1.0  # share of ideal moulding speed this campaign achieves (OEE performance)
    moulded: float | None = None
    done: float | None = None  # QA release

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
        qty = int(rng.integers(p.lot_k[0], p.lot_k[1] + 1)) * 1000
        rush = bool(rng.random() < sc.rush_share)
        lo, hi = sc.rush_due_days if rush else sc.due_days
        due = t + DAY * rng.uniform(lo, hi)
        perf = float(rng.uniform(*sc.performance))
        proc = {"drying": MATERIALS[p.material].drying_min, "moulding": qty * p.min_per_part / perf,
                **{s: qty / sc.rates[s] for s in ("inspection", "assembly", "packaging")}}
        jobs.append(Job(len(jobs), p, qty, t, due, rush, proc, perf=perf))


@dataclass
class Failure:
    time: float
    machine: str
    mode: str
    ttr: float = 0.0  # time to restore incl. waiting for a technician / toolmaker


@dataclass(eq=False)
class MouldState:
    name: str
    copy: int = 0
    location: object = "rack"  # "rack", "toolroom" or the Press it is mounted on
    shots_since_service: float = 0.0


def _lognormal(rng, mean: float, sd: float) -> float:
    s2 = math.log(1 + (sd / mean) ** 2)
    return float(rng.lognormal(math.log(mean) - s2 / 2, math.sqrt(s2)))


class Station:
    def __init__(self, factory: Factory, name: str):
        self.f, self.name = factory, name
        self.queue: list[Job] = []
        self.wake = factory.env.event()
        self.machines: list[Machine] = []

    def put(self, job: Job) -> None:
        self.queue.append(job)
        self.notify()

    def notify(self) -> None:
        old, self.wake = self.wake, self.f.env.event()
        old.succeed()


class Machine:
    """Single-server line (dryer, camera, assembly, packaging)."""

    moulding = False

    def __init__(self, factory: Factory, station: Station, idx: int):
        self.f, self.st, self.idx = factory, station, idx
        self.name = f"{station.name}{idx}"
        self.state, self.since = "idle", 0.0
        station.machines.append(self)
        factory.env.process(self.run())

    def set_state(self, state: str) -> None:
        now = self.f.env.now
        self.f.account(self, self.state, self.since, now)
        self.state, self.since = state, now

    def power(self, state: str) -> float:
        p = self.f.sc.power
        return p.station_busy[self.st.name] if state == "busy" else p.station_idle[self.st.name]

    def setup_time(self, product: Product) -> float:
        return 0.0

    def run(self):
        env, st, pol = self.f.env, self.st, self.f.policy
        while True:
            if not st.queue:
                self.set_state("idle")
                yield st.wake
                continue
            job = pol.select(st.queue, self, env.now)
            st.queue.remove(job)
            self.set_state("busy")
            yield env.timeout(job.proc[st.name])
            if st.name == "inspection":
                self.f.inspect(job)
            self.f.forward(job, st.name)


class Press(Machine):
    moulding = True

    def __init__(self, factory: Factory, station: Station, idx: int, cls: PressClass):
        self.cls = cls
        self.product: Product | None = None
        self.mould: MouldState | None = None
        self.rng = np.random.default_rng([factory.seed, 2, idx])
        self.wear = self.fouling = 0.0
        self.twf_at = self.rng.uniform(200, 240)
        super().__init__(factory, station, idx)
        self.name = f"press{idx}-{cls.name}"

    def power(self, state: str) -> float:
        p, c = self.f.sc.power, self.cls
        return {"busy": c.busy_kw, "warmup": p.warmup_frac * c.busy_kw,
                "off": p.press_off}.get(state, c.idle_kw)  # idle, setup, wait, down, pm

    # ---- moulds and changeovers ----------------------------------------------------------
    def eligible(self, job: Job) -> bool:
        if self.cls.name not in MOULDS[job.product.mould].classes:
            return False
        return any(c.location is self or c.location == "rack" for c in self.f.moulds[job.product.mould])

    def setup_time(self, product: Product) -> float:
        if self.product is product:
            return 0.0
        s = self.f.sc.setup
        t = s.line_clearance
        if self.mould is None or self.mould.name != product.mould:
            t += s.mould_change + s.mould_heatup
        if self.product is None or (self.product.material, self.product.colour) != (
                product.material, product.colour):
            t += s.purge
        return t

    def needs_setter(self, product: Product) -> bool:
        return self.setup_time(product) > self.f.sc.setup.line_clearance

    # ---- degradation in AI4I feature space -----------------------------------------------
    def ai4i_type(self, product: Product) -> str:
        return MATERIALS[product.material].ai4i_type

    def wear_increment(self, product: Product, minutes: float) -> float:
        return minutes * self.f.sc.wear_per_min * TYPE_WEAR[self.ai4i_type(product)] / 3

    def air_temp(self) -> float:
        return 300.0 + 2.0 * math.sin(2 * math.pi * self.f.env.now / DAY)

    def risk_readings(self, job: Job, minutes: float | None = None) -> np.ndarray:
        """Rows the predictor sees for the next block of this job: state + nominals + noise draws."""
        minutes = self.f.sc.block_min if minutes is None else minutes
        p, m = job.product, MOULDS[job.product.mould]
        air = self.air_temp()
        base = np.array([TYPE_CODE[self.ai4i_type(p)], air, air + 10 - self.fouling, m.rpm, m.torque,
                         self.wear + self.wear_increment(p, minutes)])
        rows = np.tile(base, (len(RISK_DRAWS), 1))
        rows[:, 1] += RISK_DRAWS[:, 0]
        rows[:, 2] += RISK_DRAWS[:, 0] + RISK_DRAWS[:, 1]
        rows[:, 3:5] += RISK_DRAWS[:, 2:4]
        return rows

    def actual_reading(self, product: Product, minutes: float) -> list[float]:
        e = self.rng.standard_normal(4) * NOISE_SD
        m = MOULDS[product.mould]
        air = self.air_temp() + e[0]
        return [TYPE_CODE[self.ai4i_type(product)], air, air + 10 - self.fouling + e[1],
                m.rpm + e[2], m.torque + e[3], self.wear + self.wear_increment(product, minutes)]

    def failure_mode(self, reading: list[float], ai4i_type: str) -> str | None:
        """Ground truth = AI4I 2020 failure rules (Matzka 2020), mapped to press components."""
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

    # ---- process ---------------------------------------------------------------------------
    def run(self):
        env, st, pol = self.f.env, self.st, self.f.policy
        while True:
            cands = [j for j in st.queue if self.eligible(j)]
            if not cands:
                self.set_state("idle")
                wake = st.wake
                if math.isinf(pol.idle_off):
                    yield wake
                    continue
                yield wake | env.timeout(pol.idle_off)
                if not wake.triggered:
                    self.set_state("off")
                    while not any(self.eligible(j) for j in st.queue):
                        yield st.wake
                    self.set_state("warmup")
                    yield env.timeout(self.f.sc.power.warmup_min)
                continue
            job = pol.select(cands, self, env.now)
            st.queue.remove(job)
            yield from self.mould_job(job)
            self.f.forward(job, "moulding")

    def mount(self, job: Job) -> None:
        """Claim a copy of the job's mould before any yield so no other press can take it."""
        if self.mould is not None and self.mould.name == job.product.mould:
            return
        if self.mould is not None:
            self.mould.location = "rack"
        m = next(c for c in self.f.moulds[job.product.mould] if c.location == "rack")
        m.location, self.mould = self, m

    def mould_job(self, job: Job):
        env, sc, pol, f = self.f.env, self.f.sc, self.f.policy, self.f
        setup = self.setup_time(job.product)
        setter = self.needs_setter(job.product)
        self.mount(job)
        if setup:
            req = None
            if setter:
                self.set_state("wait")
                req = f.setters.request(priority=0)
                yield req
            self.set_state("setup")
            yield env.timeout(setup)
            if req is not None:
                f.setters.release(req)
            self.product = job.product
            job.extra_scrap += sc.startup_scrap_units
        p, mould = job.product, MOULDS[job.product.mould]
        remaining = job.proc["moulding"]
        while remaining > 1e-9:
            if pol.wants_pm(self, job):
                yield from self.maintain()
            block = min(sc.block_min, remaining)
            reading = self.actual_reading(p, block)
            mode = self.failure_mode(reading, self.ai4i_type(p))
            shots = block * job.perf * 60 / mould.cycle_s
            if mode is None and self.rng.random() < shots / sc.mould_damage_shots:
                mode = "MOULD"
            f.readings.append((*reading, int(mode is not None)))
            job.wear_frac = max(job.wear_frac, min(reading[5] / 240, 1.0))
            run = block if mode is None else self.rng.uniform() * block
            self.set_state("busy")
            yield env.timeout(run)
            self.wear += self.wear_increment(p, run)
            self.fouling += run * sc.fouling_per_min
            self.f.moulded(job, run)
            remaining -= run
            if mode is not None:
                yield from self.repair(mode)
                job.extra_scrap += sc.restart_scrap_units
        m = self.mould
        m.shots_since_service += job.proc["moulding"] * job.perf * 60 / mould.cycle_s
        if m.shots_since_service >= sc.mould_service_shots:
            m.location, self.mould, self.product = "toolroom", None, None
            env.process(f.service_mould(m))
        job.moulded = env.now

    def repair(self, mode: str):
        env, f = self.f.env, self.f
        failure = Failure(env.now, self.name, mode)
        f.failures.append(failure)
        self.set_state("down")
        crew = f.toolroom if mode == "MOULD" else f.technicians
        with crew.request() as req:
            yield req
            yield env.timeout(_lognormal(f.repair_rng, *REPAIR[mode]))
        self.restore(mode)
        failure.ttr = env.now - failure.time

    def maintain(self):
        env, f = self.f.env, self.f
        self.set_state("pm")
        with f.technicians.request() as req:
            yield req
            yield env.timeout(f.sc.pm_duration)
        self.restore()
        f.pm_times.append(env.now)


class Factory:
    def __init__(self, sc: Scenario, policy, seed: int):
        self.sc, self.policy, self.seed = sc, policy, seed
        self.env = simpy.Environment()
        self.insp_rng = np.random.default_rng([seed, 3])
        self.repair_rng = np.random.default_rng([seed, 4])
        self.qa_rng = np.random.default_rng([seed, 5])
        self.energy_kwh = self.press_kwh = self.moulded_kg = self.ideal_min = 0.0
        self.state_min: dict[str, float] = {}
        self.wip: set[Job] = set()
        self.failures: list[Failure] = []
        self.readings: list[tuple] = []
        self.pm_times: list[float] = []
        self.jobs = make_jobs(sc, seed)
        self.moulds = {n: [MouldState(n, i) for i in range(m.copies)] for n, m in MOULDS.items()}
        c = sc.crew
        self.setters = simpy.PriorityResource(self.env, capacity=c.setters_day)
        self.technicians = simpy.Resource(self.env, capacity=c.technicians)
        self.toolroom = simpy.Resource(self.env, capacity=c.toolmakers)
        self.stations = {s: Station(self, s) for s in STATIONS}
        idx = 0
        for cls in PRESS_CLASSES:
            for _ in range(cls.count):
                Press(self, self.stations["moulding"], idx, cls)
                idx += 1
        for i in range(sc.dryers):
            Machine(self, self.stations["drying"], i)
        for s, n in sc.lines.items():
            for i in range(n):
                Machine(self, self.stations[s], i)
        self.env.process(self.release())
        self.env.process(self.night_shift())

    # ---- accounting (KPI window only) ------------------------------------------------------
    def _overlap(self, a: float, b: float) -> float:
        return max(0.0, min(b, self.sc.horizon) - max(a, self.sc.warmup))

    def account(self, m: Machine, state: str, a: float, b: float) -> None:
        dt = self._overlap(a, b)
        if dt <= 0:
            return
        kwh = m.power(state) * dt / 60
        self.energy_kwh += kwh
        if m.moulding:
            self.press_kwh += kwh
            self.state_min[state] = self.state_min.get(state, 0.0) + dt

    def moulded(self, job: Job, run: float) -> None:
        """Book output of `run` busy minutes: ideal-speed minutes (OEE) and kg moulded."""
        dt = self._overlap(self.env.now - run, self.env.now)
        self.ideal_min += dt * job.perf
        self.moulded_kg += dt * job.perf / job.product.min_per_part * job.product.part_g / 1000

    # ---- shared resources --------------------------------------------------------------------
    def night_shift(self):
        """Between 22:00 and 06:00 only setters_night setters are available."""
        c, env = self.sc.crew, self.env
        off = c.setters_day - c.setters_night
        while off > 0:
            yield env.timeout((22 * 60 - env.now % DAY) % DAY)
            reqs = [self.setters.request(priority=-1) for _ in range(off)]
            yield simpy.AllOf(env, reqs)
            t = env.now % DAY
            if t >= 22 * 60 or t < 6 * 60:  # still night: hold until 06:00
                yield env.timeout((6 * 60 - t) % DAY)
            for r in reqs:
                self.setters.release(r)

    def service_mould(self, m: MouldState):
        with self.toolroom.request() as req:
            yield req
            yield self.env.timeout(self.sc.mould_service_min)
        m.location, m.shots_since_service = "rack", 0.0
        self.stations["moulding"].notify()

    # ---- flow -----------------------------------------------------------------------------------
    def release(self):
        for job in self.jobs:
            yield self.env.timeout(job.arrival - self.env.now)
            self.wip.add(job)
            self.forward(job, None)

    def forward(self, job: Job, station: str | None) -> None:
        i = -1 if station is None else STATIONS.index(station)
        if station == "moulding":
            self.stations["moulding"].notify()  # a mould may have returned to the rack
        for nxt in STATIONS[i + 1:]:
            if job.proc[nxt] > 0:
                self.stations[nxt].put(job)
                return
        self.env.process(self.qa_release(job))

    def qa_release(self, job: Job):
        yield self.env.timeout(_lognormal(self.qa_rng, *self.sc.qa_hold))
        job.done = self.env.now
        self.wip.discard(job)

    def inspect(self, job: Job) -> None:
        sc, r = self.sc, self.insp_rng
        p_def = min(sc.base_defect + sc.wear_defect * job.wear_frac, 1.0)
        defects = int(r.binomial(job.qty, p_def))
        caught = int(r.binomial(defects, sc.camera_detect))
        false_rej = int(r.binomial(job.qty - defects, sc.camera_false_reject))
        job.rejects, job.escaped = caught + false_rej, defects - caught

    # ---- run + KPIs -----------------------------------------------------------------------------
    def run(self) -> dict:
        sc = self.sc
        end = sc.horizon + sc.drain
        self.env.run(until=end)
        for st in self.stations.values():
            for m in st.machines:
                m.set_state(m.state)  # flush accounting
        self.energy_kwh += sc.power.hvac * (sc.horizon - sc.warmup) / 60
        return self.kpis(end)

    def kpis(self, end: float) -> dict:
        sc = self.sc
        w0, w1 = sc.warmup, sc.horizon
        hours = (w1 - w0) / 60
        released = [j for j in self.jobs if w0 <= j.arrival <= w1]
        shipped = [j for j in self.jobs if j.done is not None and w0 <= j.done <= w1]
        good = sum(j.qty - j.rejects for j in shipped)
        made = sum(j.qty + j.extra_scrap for j in shipped)
        lead = [((j.done if j.done is not None else end) - j.arrival) / 60 for j in released]
        on_time = [j.done is not None and j.done <= j.due for j in released]
        fails = [f for f in self.failures if w0 <= f.time <= w1]
        pms = [t for t in self.pm_times if w0 <= t <= w1]
        s = self.state_min
        loaded = sum(v for k, v in s.items() if k not in ("idle", "off"))
        press_total = sum(s.values())
        down_h = sum(f.ttr for f in fails) / 60
        pm_h = s.get("pm", 0.0) / 60
        scrap = 1 - good / made if made else 0.0
        return {
            "throughput_uph": good / hours,
            "lead_time_h": float(np.mean(lead)) if lead else 0.0,
            "on_time_rate": float(np.mean(on_time)) if on_time else 1.0,
            "energy_kwh": self.energy_kwh,
            "kwh_per_1000_good": 1000 * self.energy_kwh / good if good else math.inf,
            "press_kwh_per_kg": self.press_kwh / self.moulded_kg if self.moulded_kg else math.inf,
            "scrap_rate": scrap,
            "escaped_ppm": 1e6 * sum(j.escaped for j in shipped) / good if good else 0.0,
            "failures": len(fails),
            "pm_events": len(pms),
            "downtime_h": down_h,
            "pm_h": pm_h,
            "maintenance_h": down_h + pm_h,
            "mttr_h": float(np.mean([f.ttr for f in fails])) / 60 if fails else 0.0,
            "setup_h": s.get("setup", 0.0) / 60,
            "setter_wait_h": s.get("wait", 0.0) / 60,
            "press_util": s.get("busy", 0.0) / press_total if press_total else 0.0,
            "availability": s.get("busy", 0.0) / loaded if loaded else 0.0,
            "oee": (self.ideal_min / loaded) * (1 - scrap) if loaded else 0.0,
            "unfinished": sum(j.done is None for j in released),
        }


def simulate(policy, scenario: Scenario, seed: int) -> dict:
    return Factory(scenario, policy, seed).run()
