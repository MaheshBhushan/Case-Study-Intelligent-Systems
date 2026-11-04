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
| `Progress_Presentation_Gerresheimer_Pfreimd.pptx` | Phase 2 progress presentation (Phase 1 → Phase 2) |
| `simulation/` | SimPy model, AI4I 2020 failure-risk model, Optuna NSGA-II tuning, experiments, tests ([details](simulation/README.md)) |

## Status

The simulation is at **model v2**. It has:
- 12 presses in 3 tonnage classes and 8 moulds with limited copies;
- campaign lots, setter and maintenance crews, and press failure modes;
- energy by press drive type, OEE, camera inspection errors and GMP QA release;
- a non-ML maintenance-rule baseline.

Still open:
- sensitivity analysis on the assumed parameters;
- time-of-day electricity prices;
- the dashboard and demo video.

All plant parameters are synthetic and literature-based; Gerresheimer publishes no operational data.

```bash
cd simulation && uv sync && uv run pytest -q
```
