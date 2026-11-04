"""Dispatching and maintenance policies.

`select` receives only jobs the machine can run (for presses: compatible mould that is free).
Baselines run reactive maintenance and never switch presses off.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .model import Job, Machine


class Policy:
    name = "base"
    idle_off = math.inf  # minutes idle before a press is switched off

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
    """Least changeover first, FCFS on ties (Allahverdi et al. 2008)."""

    name = "SETUP"

    def select(self, queue, m, now):
        return min(queue, key=lambda j: m.setup_time(j.product))


@dataclass
class RulePM(SetupAware):
    """Setup-aware dispatch + rule-based preventive maintenance without ML.

    PM before the next shift block when screw wear would pass `wear_limit` (AI4I tool-wear
    minutes) or heat-dissipation margin loss reaches `fouling_limit` (K).
    """

    wear_limit: float = 180.0
    fouling_limit: float = 1.2
    name: str = "SETUP+PM"

    def wants_pm(self, m, job):
        nxt = m.wear + m.wear_increment(job.product, m.f.sc.block_min)
        return nxt >= self.wear_limit or m.fouling >= self.fouling_limit


@dataclass
class Predictive(Policy):
    """Weighted multi-objective dispatch + RF failure risk + idle shutdown + predictive PM.

    score = w_due*slack_days + w_setup*setup/255 + w_spt*proc_days + w_risk*risk; lowest wins.
    PM is triggered before a shift block when predicted failure risk >= pm_threshold.
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
        """Failure probability per job for the next block on machine m (noise-averaged)."""
        rows = np.concatenate([m.risk_readings(j) for j in jobs])
        return self.risk_model.predict(rows).reshape(len(jobs), -1).mean(axis=1)

    def select(self, queue, m, now):
        st = m.st.name
        risk = self.risks(m, queue) if m.moulding and self.w_risk else np.zeros(len(queue))

        def score(i: int) -> float:
            j = queue[i]
            slack = (j.due - now - j.remaining_work(st)) / 1440
            return (self.w_due * slack + self.w_setup * m.setup_time(j.product) / 255
                    + self.w_spt * j.proc[st] / 1440 + self.w_risk * risk[i])

        return queue[min(range(len(queue)), key=score)]

    def wants_pm(self, m, job):
        return self.risks(m, [job])[0] >= self.pm_threshold
