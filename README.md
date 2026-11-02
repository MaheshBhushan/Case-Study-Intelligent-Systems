# AI-Driven Multi-Objective Optimization of a Medical Injection-Moulding Line

MDM2 Case Study: Intelligent Systems in Production (THD, WS 2026/27).
Team: Kuriakose Vettikattil Raju (team lead), Mahesh Koduri, Saurabhkumar Mahant.
Supervisor: Prof. Dr.-Ing. Hamidreza Heidari.

A simulated case study modelled on the Gerresheimer medical-plastics plant in Pfreimd. The project
compares fixed scheduling rules (FCFS, SPT, setup-aware) with a predictive, multi-objective policy
on a five-station line: drying, clean-room moulding, camera inspection, assembly and clean-room
packaging. The KPIs are lead time, energy, maintenance/downtime and scrap.

## Contents

| Path | What it is |
|---|---|
| `Proposal_Gerresheimer_Pfreimd.docx` | Phase 1 one-page proposal |
| `Presentation_Gerresheimer_Pfreimd.pptx` | Phase 1 concept presentation |
| `simulation/` | SimPy model, AI4I 2020 failure-risk model, Optuna NSGA-II tuning, experiments, tests ([details](simulation/README.md)) |

## Status

The simulation runs end to end and first results exist, but it is **work in progress**. Planned
improvements include:
- realistic lot sizes and more moulding machines;
- moulding-specific failure modes;
- datasheet-based energy and electricity tariffs;
- a benchmark against a non-ML maintenance rule;
- sensitivity analysis.

All plant parameters are synthetic and literature-based; Gerresheimer publishes no operational data.

```bash
cd simulation && uv sync && uv run pytest -q
```
