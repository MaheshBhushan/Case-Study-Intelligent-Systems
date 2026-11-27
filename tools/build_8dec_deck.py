"""Build the 8 Dec deck (modelling, algorithms, implementation, live demo) in the house style.

Usage: uv run --with python-pptx --with pandas --with matplotlib python tools/build_8dec_deck.py OUT.pptx
Reads simulation/results/{summary,paired_tests,morris,sensitivity}.csv and tuned.json.
"""
import io
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Pt

WS = Path(__file__).resolve().parents[1]
RES = WS / "simulation/results"
OLD = Presentation(WS / "Progress_Presentation_Gerresheimer_Pfreimd.pptx")
LOGO = next(sh.image.blob for sh in OLD.slides[1].shapes if sh.shape_type == 13)
SUM = pd.read_csv(RES / "summary.csv").set_index(["scenario", "policy"])
PAIR = pd.read_csv(RES / "paired_tests.csv")
MOR = pd.read_csv(RES / "morris.csv")
TUNED = json.loads((RES / "tuned.json").read_text())["params"]
N_TESTS = 35

TEAL, NAVY, MUTED, LINE, CARD, WHITE = (RGBColor(0, 125, 131), RGBColor(24, 43, 75), RGBColor(94, 107, 126),
                                         RGBColor(0xDE, 0xE6, 0xEE), RGBColor(0xEF, 0xF5, 0xF8), RGBColor(255, 255, 255))
HEX = {"teal": "#007D83", "navy": "#182B4B", "muted": "#5E6B7E", "line": "#DEE6EE"}
IN = 914400
DATE = "08 DEC 2026  |  MODELLING, ALGORITHMS & IMPLEMENTATION"

prs = Presentation()
prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
BLANK = prs.slide_layouts[6]
n_slide = 0


def box(s, x, y, w, h, color):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN)))
    r.fill.solid(); r.fill.fore_color.rgb = color; r.line.fill.background(); r.shadow.inherit = False
    return r


def text(s, x, y, w, h, lines, size=14, color=NAVY, bold=False, font="Aptos"):
    tb = s.shapes.add_textbox(Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN)))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, ln in enumerate([lines] if isinstance(lines, str) else lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        ln, kw = ln if isinstance(ln, tuple) else (ln, {})
        r = p.add_run(); r.text = ln
        r.font.name = kw.get("font", font); r.font.size = Pt(kw.get("size", size))
        r.font.bold = kw.get("bold", bold); r.font.color.rgb = kw.get("color", color)
        p.space_after = Pt(kw.get("after", 4))
    return tb


def slide(title):
    global n_slide
    n_slide += 1
    s = prs.slides.add_slide(BLANK)
    box(s, 0.62, 0.42, 0.09, 0.62, TEAL)
    text(s, 0.85, 0.42, 9.9, 0.75, title, 28, NAVY, True)
    box(s, 0.62, 1.15, 12.0, 0.025, LINE)
    s.shapes.add_picture(io.BytesIO(LOGO), Emu(9966960), Emu(274320), height=Emu(415777))
    text(s, 0.67, 7.07, 4.2, 0.25, DATE, 9, MUTED)
    text(s, 5.0, 7.07, 6, 0.25, "MDM2  •  Intelligent Systems in Production  •  Group 7", 9, MUTED)
    text(s, 12.2, 7.03, 0.5, 0.25, f"{n_slide:02d}", 10, MUTED)
    return s


def card(s, x, y, w, h, head, body, dark=False, hsize=14, bsize=12):
    box(s, x, y, w, h, TEAL if dark else CARD)
    text(s, x + 0.12, y + 0.1, w - 0.24, 0.35, head, hsize, WHITE if dark else TEAL, True)
    text(s, x + 0.12, y + 0.48, w - 0.24, h - 0.55, body, bsize, WHITE if dark else NAVY)


def table(s, x, y, w, rows, widths, size=11, rh=0.32):
    t = s.shapes.add_table(len(rows), len(rows[0]), Emu(int(x * IN)), Emu(int(y * IN)),
                           Emu(int(w * IN)), Emu(int(rh * IN * len(rows)))).table
    for j, cw in enumerate(widths):
        t.columns[j].width = Emu(int(cw * IN))
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.text = str(v)
            c.fill.solid(); c.fill.fore_color.rgb = TEAL if i == 0 else (CARD if i % 2 else WHITE)
            c.margin_top = c.margin_bottom = Emu(30000)
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.name = "Aptos"; r.font.size = Pt(size); r.font.bold = i == 0
                    r.font.color.rgb = WHITE if i == 0 else NAVY
    return t


def picture(s, fig, x, y, w):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    s.shapes.add_picture(buf, Emu(int(x * IN)), Emu(int(y * IN)), width=Emu(int(w * IN)))


def pair(base, kpi, sc="base"):
    r = PAIR[(PAIR.baseline == base) & (PAIR.kpi == kpi) & (PAIR.scenario == sc)].iloc[0]
    return r["rel_change_%"], r["p_value"]


plt.rcParams.update({"font.family": ["Noto Sans", "DejaVu Sans"], "font.size": 9,
                     "axes.edgecolor": HEX["muted"], "axes.labelcolor": HEX["navy"],
                     "xtick.color": HEX["navy"], "ytick.color": HEX["navy"]})

# ---------------------------------------------------------------- 1 title
s = prs.slides.add_slide(BLANK); n_slide += 1
box(s, 0.62, 0.55, 0.09, 1.0, TEAL)
text(s, 0.85, 0.5, 9.5, 1.2, ["AI-Driven Multi-Objective Optimization", "of a Medical Injection-Moulding Line"], 30, NAVY, True)
s.shapes.add_picture(io.BytesIO(LOGO), Emu(9966960), Emu(274320), height=Emu(415777))
text(s, 0.85, 2.0, 11, 0.4, "Modelling, algorithm development and implementation, with a live demo", 18, MUTED)
text(s, 0.85, 2.45, 11, 0.4, "Simulated case study: Gerresheimer medical-plastics plant, Pfreimd (Bavaria)", 15, TEAL, True)
for i, (h, b) in enumerate([("✓  LIVE DEMO", "One 12-week scenario, five policies, decision trace"),
                            ("✓  NEW FEATURES", "Time-of-day energy prices; Morris screening"),
                            ("✓  TESTS · CI", f"{N_TESTS} tests green on GitHub Actions")]):
    card(s, 0.85 + i * 3.85, 3.05, 3.6, 1.35, h, b)
text(s, 0.85, 4.85, 11, 0.4, "MDM2 Case Study: Intelligent Systems in Production  |  8 Dec 2026", 15, TEAL, True)
text(s, 0.85, 5.3, 11, 0.6, "Supervised by Hamidreza Heidari, PhD  •  Team: Kuriakose Vettikattil Raju (Team Lead), "
     "Mahesh Koduri, Saurabhkumar Mahant", 12, NAVY)

# ---------------------------------------------------------------- 2 code structure
s = slide("Code Structure")
mods = [("config.py", "parameters as frozen\ndataclasses + scenarios"),
        ("model.py", "SimPy plant: presses,\nmoulds, crews, KPIs"),
        ("policies.py", "FCFS · SPT · SETUP\nSETUP+PM · PRED-MO"),
        ("risk.py", "Random Forest on\nAI4I 2020"),
        ("optimize.py", "grid search + NSGA-II\n→ rule.json, tuned.json")]
for i, (h, b) in enumerate(mods):
    card(s, 0.75 + i * 2.4, 1.45, 2.2, 1.35, h, b, dark=i == 1, hsize=13, bsize=11)
for i, (h, b) in enumerate([("experiments.py", "100 held-out seeds,\nCIs, paired t-tests"),
                            ("sensitivity.py", "one-at-a-time,\n10 parameters"),
                            ("morris.py", "elementary effects,\ninteractions (NEW)"),
                            ("demo.py", "live run + decision\ntrace (NEW)")]):
    card(s, 0.75 + i * 2.4, 3.0, 2.2, 1.25, h, b, hsize=13, bsize=11)
text(s, 10.4, 3.1, 2.2, 1.2, ["tests/", f"{N_TESTS} tests, CI on", "every push"], 12, TEAL, True)
text(s, 0.75, 4.5, 11.8, 0.35, "One order through model.py", 15, TEAL, True)
flow = ["Poisson\narrival", "resin\ndrying", "press queue\n→ policy.select()", "setup\n(needs setter)",
        "moulding\nwear + shift risk", "camera\ninspection", "assembly +\npackaging", "48 h QA\nrelease"]
for i, f in enumerate(flow):
    box(s, 0.75 + i * 1.48, 4.95, 1.38, 0.95, TEAL if i in (2, 4) else CARD)
    text(s, 0.82 + i * 1.48, 5.05, 1.25, 0.8, f, 10, WHITE if i in (2, 4) else NAVY, True)
text(s, 0.75, 6.1, 11.8, 0.5, "Each machine is a SimPy process; setters, technicians and toolmakers are shared "
     "SimPy resources. Policies only see select() and wants_pm(), so a new policy is one class.", 11, MUTED)

# ---------------------------------------------------------------- 3 algorithms
s = slide("Algorithms Inside PRED-MO")
card(s, 0.75, 1.45, 5.8, 2.35, "1  Dispatch: weighted score, lowest wins", [
    ("score = w_due·slack + w_setup·setup/255", {"font": "Consolas", "size": 12}),
    ("        + w_spt·proc + w_risk·risk", {"font": "Consolas", "size": 12}),
    "slack and proc in days; setup minutes / 255 (≈ longest changeover, 250 min)",
    "risk = RF failure probability for the next shift on this press"], bsize=11)
card(s, 6.8, 1.45, 5.8, 2.35, "2  Maintenance: predictive PM", [
    "Before every 8-h shift block, risk.py predicts P(failure) from wear, torque, speed and temperatures",
    f"PM when P ≥ pm_threshold = {TUNED['pm_threshold']:.3f}",
    "AI4I base rate is ~3 %, so 7 % already means double the average risk"], bsize=11)
card(s, 0.75, 4.0, 5.8, 2.35, "3  Energy: idle shutdown", [
    f"A press idle for idle_off = {TUNED['idle_off']:.0f} min switches off (0.5 kW)",
    "Restart costs a 45-min warm-up at 80 % of busy power",
    "Baselines never switch off"], bsize=11)
card(s, 6.8, 4.0, 5.8, 2.35, "4  Tuning: NSGA-II (Optuna)", [
    "6 settings: 4 weights, idle_off, pm_threshold",
    "3 objectives: lead time, kWh per 1,000 good parts, maintenance h",
    "Seeds 0–2 at base + high demand; Pareto point closest to the ideal",
    "Tuned: " + ", ".join(f"{k}={TUNED[k]:.2f}" for k in ("w_due", "w_setup", "w_spt", "w_risk"))],
     dark=True, bsize=11)

# ---------------------------------------------------------------- 4 justification
s = slide("Why These Models, Algorithms and Values")
table(s, 0.75, 1.4, 11.8, [
    ["Choice", "Why", "Alternative we rejected"],
    ["Discrete-event simulation (SimPy)", "queues, shared crews, random breakdowns; identical random events per policy",
     "spreadsheet / analytic queueing: no crews or failures"],
    ["Random Forest", "tabular sensors, no scaling, class weights for 3.4 % failures, gives probabilities; F1 0.88",
     "deep net: 10k rows too few; logistic regression: misses thresholds"],
    ["AI4I 2020 dataset", "only public labelled failure data with wear, torque, speed, temperatures",
     "no Gerresheimer data exists publicly"],
    ["NSGA-II", "3 conflicting objectives → Pareto front instead of one fixed weighting",
     "weighted sum: weights chosen before seeing trade-offs"],
    ["Tuned wear rule (SETUP+PM)", "fair non-ML opponent, same tuning seeds", "only reactive baselines: flatters the ML"],
    ["Common random numbers + paired t-test", "removes scenario noise from policy differences", "independent runs: wider CIs"],
    ["Parameter values", "press power: Thiriez & Gutowski 2006; drying: Rosato 2000; GMP: EU Annex 1/16",
     "crews, repairs, lot sizes: assumptions → sensitivity + Morris"],
], [2.6, 5.4, 3.8], 10, 0.5)

# ---------------------------------------------------------------- 5 live demo
s = slide("Live Demo")
box(s, 0.75, 1.45, 6.6, 2.2, NAVY)
text(s, 0.95, 1.6, 6.3, 2.0, [
    ("$ cd simulation", {"color": WHITE}),
    ("$ uv run pytest -q", {"color": WHITE}),
    ("$ uv run python -m moulding_sim.demo --trace 2", {"color": WHITE}),
    ("$ uv run python -m moulding_sim.demo --scenario high --seed 123", {"color": WHITE})],
     13, WHITE, font="Consolas")
text(s, 7.65, 1.45, 4.9, 0.35, "What to look at", 15, TEAL, True)
text(s, 7.65, 1.85, 4.9, 4.4, [
    "1  Trace: every candidate's slack, setup, processing time, risk and score; the lowest score wins",
    "2  KPI table: five policies on the same scenario (common random numbers)",
    "3  Breakdowns by failure mode: PM removes screw-wear failures; drive overloads remain",
    "4  One seed is an anecdote; claims come from 100 held-out seeds (next slide)"], 12)
text(s, 0.75, 3.95, 6.6, 0.35, "Backup if the live run fails", 15, TEAL, True)
text(s, 0.75, 4.35, 6.6, 2.0, [
    "results/summary.md, paired_tests.csv, sensitivity.md and morris.md are committed",
    "Runbook and Q&A: simulation/DEMO.md",
    "Not run live: experiments, sensitivity, morris, optimize (10–30 min on 8 cores)"], 12)

# ---------------------------------------------------------------- 6 preliminary results
s = slide("Preliminary Results: 100 Held-Out Scenarios")
pols = ["FCFS", "SETUP", "SETUP+PM", "PRED-MO"]
rows = [["Scenario", "Policy", "Lead time h", "On time", "kWh/1k good", "EUR/1k good", "OEE", "Maint. h"]]
for sc in ("base", "high", "harsh"):
    for p in pols:
        r = SUM.loc[(sc, p)]
        rows.append([sc if p == pols[0] else "", p, f"{r.lead_time_h:.0f} ± {r.lead_time_h_ci:.0f}",
                     f"{r.on_time_rate:.1%}", f"{r.kwh_per_1000_good:.2f}", f"{r.eur_per_1000_good:.3f}",
                     f"{r.oee:.3f}", f"{r.maintenance_h:.0f}"])
table(s, 0.75, 1.35, 8.0, rows, [0.9, 1.15, 1.2, 0.9, 1.1, 1.1, 0.75, 0.9], 10, 0.33)
text(s, 9.0, 1.4, 3.6, 0.35, "PRED-MO vs SETUP+PM (base)", 14, TEAL, True)
lines = []
for k, lab in (("lead_time_h", "Lead time"), ("kwh_per_1000_good", "Energy"), ("eur_per_1000_good", "Energy cost"),
               ("maintenance_h", "Maintenance")):
    v, p = pair("SETUP+PM", k)
    lines.append(f"{lab}: {v:+.1f} % (p {'< 0.001' if p < 0.001 else f'= {p:.3f}'})")
text(s, 9.0, 1.85, 3.6, 2.0, lines, 12)
text(s, 9.0, 3.6, 3.6, 2.6, [
    ("Reading", {"bold": True, "color": TEAL}),
    "± = 95 % CI. 'harsh' was never used for tuning.",
    "Gains come from dispatch weights and idle shutdown; the ML maintenance trigger changes the kind of "
    "downtime, not the amount."], 11)

# ---------------------------------------------------------------- 7 time-of-day prices
s = slide("New Feature: Time-of-Day Electricity Prices")
sys.path.insert(0, str(WS / "simulation/src"))
from moulding_sim.config import PRICE_PROFILE

fig, ax = plt.subplots(figsize=(6.2, 3.4), dpi=200)
ax.step(range(25), list(PRICE_PROFILE) + [PRICE_PROFILE[-1]], where="post", color=HEX["teal"], lw=2)
ax.set_xlim(0, 24); ax.set_xticks(range(0, 25, 3)); ax.set_xlabel("hour of day"); ax.set_ylabel("EUR/MWh")
ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Stylised day-ahead profile (German market shape)", color=HEX["navy"], fontsize=10)
picture(s, fig, 0.75, 1.4, 6.3)
base = SUM.xs("base")
rows = [["Policy", "EUR / 1,000 good", "Avg. press price EUR/MWh"]]
for p in pols:
    rows.append([p, f"{base.loc[p, 'eur_per_1000_good']:.3f}", f"{base.loc[p, 'press_eur_per_mwh']:.1f}"])
table(s, 7.4, 1.45, 5.2, rows, [1.6, 1.7, 1.9], 11, 0.38)
v, p = pair("SETUP+PM", "press_eur_per_mwh")
text(s, 7.4, 3.6, 5.2, 2.6, [
    "Every kW drawn is priced by its hour; HVAC runs 24/7.",
    f"Presses pay ~{base.loc['PRED-MO', 'press_eur_per_mwh']:.0f} EUR/MWh under every policy "
    f"(PRED-MO vs SETUP+PM {v:+.2f} %): nobody shifts load in time yet.",
    "No policy plans around prices yet, so cost follows energy. Next: price-aware idle shutdown "
    "and shifting PM to cheap hours."], 12)
text(s, 0.75, 5.3, 6.3, 0.8, "Level is an assumption; the shape (night low, solar dip, evening peak) "
     "follows the German day-ahead market.", 10, MUTED)

# ---------------------------------------------------------------- 8 Morris
s = slide("Morris Screening: Interactions")
names = {"demand": "demand", "wear_rate": "wear rate", "repair_time": "repair time", "technicians": "technicians",
         "setters": "setters", "mould_change": "mould change", "pm_duration": "PM duration", "qa_hold": "QA hold",
         "hvac": "HVAC", "camera": "camera"}
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0), dpi=200)
for ax, kpi, title in zip(axes, ("lead_time_h", "maintenance_h"),
                          ("lead-time gap (h)", "maintenance-time gap (h)")):
    g = MOR[(MOR.kpi == kpi) & (MOR.mu_star > 0)]
    ax.scatter(g.mu_star, g.sigma, color=HEX["teal"], s=28, zorder=3)
    for i, r in enumerate(g.sort_values("mu_star").itertuples()):
        ax.annotate(names[r.param], (r.mu_star, r.sigma), fontsize=8,
                    xytext=(5, 3) if i % 2 else (5, -10), textcoords="offset points")
    lim = max(g.mu_star.max(), g.sigma.max()) * 1.15
    ax.plot([0, lim], [0, lim], ls="--", color=HEX["muted"], lw=0.8)
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_xlabel("μ*  (mean |effect|)"); ax.set_ylabel("σ  (spread)")
    ax.set_title(f"PRED-MO minus SETUP+PM: {title}", color=HEX["navy"], fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
picture(s, fig, 0.6, 1.35, 8.4)
top = {k: MOR[MOR.kpi == k].sort_values("mu_star", ascending=False).iloc[0] for k in ("lead_time_h", "maintenance_h")}
n_traj = len(pd.read_csv(RES / "morris_runs.csv").point.unique()) // (len(names) + 1)
text(s, 9.25, 1.45, 3.4, 4.8, [
    ("Method", {"bold": True, "color": TEAL}),
    f"{n_traj} random trajectories through the low–high box of all 10 parameters; each step moves one parameter.",
    "Above the dashed line (σ > μ*): the effect depends on the other parameters (or on seed noise: 4 seeds).",
    ("Findings", {"bold": True, "color": TEAL}),
    "Lead time: PRED-MO is 5.5 h faster on average; demand matters most, and higher demand widens the gap.",
    "Maintenance: PM duration and repair time decide who wins (long PM hurts PRED-MO, long repairs help it).",
    "Most σ/μ* > 1: effects interact, so OAT alone was not enough."], 11)

# ---------------------------------------------------------------- 9 tests, CI, board
s = slide("Tests, CI and Issues Board")
for i, (h, b) in enumerate([(str(N_TESTS), "tests (29 on 24 Nov)"), ("green", "GitHub Actions on\nevery push + PR"),
                            ("6", "new tests: price clock,\nflat tariff, Morris, OAT")]):
    box(s, 0.75 + i * 3.0, 1.45, 2.8, 1.4, CARD)
    text(s, 0.87 + i * 3.0, 1.52, 2.6, 0.6, h, 28, TEAL, True)
    text(s, 0.87 + i * 3.0, 2.12, 2.6, 0.7, b, 12, NAVY)
table(s, 0.75, 3.15, 11.8, [
    ["#", "Issue", "Milestone", "Status"],
    ["4", "Time-of-day electricity prices in the energy KPI", "8 Dec", "done"],
    ["5", "Extend tests: sensitivity, energy cost", "8 Dec", "done"],
    ["6", "Morris screening for interactions", "8 Dec", "done"],
    ["7", "Dashboard for a simulation run", "22 Dec", "next"],
    ["8", "Demo video + run instructions", "22 Dec", "next"],
    ["9", "Real figures from press datasheets", "12 Jan", "open"],
    ["10", "Final report (IEEE) and presentation", "12 Jan", "open"],
], [0.6, 7.4, 1.9, 1.9], 11, 0.36)

# ---------------------------------------------------------------- 10 challenges
s = slide("Technical Challenges and Next Steps")
card(s, 0.75, 1.45, 3.85, 4.7, "CHALLENGES", [
    "•  No plant data → literature values, sensitivity + Morris",
    "•  AI4I is milling data → used only as a failure signal",
    "•  sklearn predict_proba too slow per shift → direct tree calls, ~50× faster",
    "•  Tuning on 3 seeds can overfit → 100 unseen seeds + never-tuned 'harsh' scenario"], bsize=12)
card(s, 4.8, 1.45, 3.85, 4.7, "WHAT WE LEARNED", [
    "•  Against reactive rules ML looked great; a tuned wear rule shows maintenance time is a tie",
    "•  Risk in the dispatch score has no measurable effect (ablation)",
    "•  Delivery, energy and cost gains hold across all 21 sensitivity levels"], bsize=12)
card(s, 8.85, 1.45, 3.75, 4.7, "NEXT → 22 DEC", [
    "•  Dashboard: press Gantt, queues, KPIs (#7)",
    "•  Demo video + run instructions (#8)",
    "•  Price-aware shutdown and PM timing",
    "•  Datasheet values for press power (#9)"], dark=True, bsize=12)

out = Path(sys.argv[1])
prs.save(out)
print("saved", out)
