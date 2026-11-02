"""Dispatching policies. Baselines run reactive maintenance and never switch machines off."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .model import Job, Machine


class Policy:
    name = "base"
    idle_off = math.inf  # minutes idle before a moulding machine is switched off

    def select(self, queue: list[Job], m: Machine, now: float) -> Job:
        raise NotImplementedError

    def wants_pm(self, m: Machine, job: Job) -> bool:
        return False


class FCFS(Policy):
    name = "FCFS"

    def select(self, queue, m, now):
        return queue[0]


class SPT(Policy):
    name = "SPT"

    def select(self, queue, m, now):
        return min(queue, key=lambda j: j.proc[m.st.name])


class SetupAware(Policy):
    """Mould grouping: least changeover first, FCFS on ties (Allahverdi et al. 2008)."""

    name = "SETUP"

    def select(self, queue, m, now):
        return min(queue, key=lambda j: m.setup_time(j.product))


@dataclass
class Predictive(Policy):
    """Weighted multi-objective dispatch + RF failure risk + idle shutdown + predictive PM.

    score = w_due*slack_days + w_setup*setup/165 + w_spt*proc/150 + w_risk*risk; lowest wins.
    PM is triggered before a job when its predicted failure risk on this machine >= pm_threshold.
    """

    risk_model: object
    w_due: float = 1.0
    w_setup: float = 1.0
    w_spt: float = 0.3
    w_risk: float = 1.0
    idle_off: float = 120.0
    pm_threshold: float = 0.5
    name: str = "PRED-MO"

    def risks(self, m: Machine, jobs: list[Job]) -> np.ndarray:
        """Failure probability per job on machine m, averaged over sensor-noise draws."""
        rows = np.concatenate([m.risk_readings(j) for j in jobs])
        return self.risk_model.predict(rows).reshape(len(jobs), -1).mean(axis=1)

    def select(self, queue, m, now):
        st = m.st.name
        # One RF call per moulding decision; the chosen job's risk is reused by wants_pm.
        risk = self.risks(m, queue) if m.moulding else np.zeros(len(queue))

        def score(i: int) -> float:
            j = queue[i]
            slack = (j.due - now - j.remaining_work(st)) / 1440
            return (self.w_due * slack + self.w_setup * m.setup_time(j.product) / 165
                    + self.w_spt * j.proc[st] / 150 + self.w_risk * risk[i])

        best = min(range(len(queue)), key=score)
        if m.moulding:
            self._chosen = (m, queue[best], float(risk[best]))
        return queue[best]

    def wants_pm(self, m, job):
        cached = getattr(self, "_chosen", None)
        r = cached[2] if cached and cached[0] is m and cached[1] is job else self.risks(m, [job])[0]
        return r >= self.pm_threshold
