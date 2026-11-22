"""Build the 24 Nov Phase 3 deck in the style of the 3 Nov progress deck.

Usage: uv run --with python-pptx --with pandas python tools/build_phase3_deck.py OUT.pptx
Reads simulation/results/sensitivity*.csv, so run moulding_sim.sensitivity first.
"""
import io
import sys
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

WS = Path(__file__).resolve().parents[1]
OLD = Presentation(WS / "Progress_Presentation_Gerresheimer_Pfreimd.pptx")
LOGO = next(sh.image.blob for sh in OLD.slides[1].shapes if sh.shape_type == 13)
SENS = pd.read_csv(WS / "simulation/results/sensitivity.csv")

TEAL, NAVY, MUTED, LINE, CARD, WHITE = (RGBColor(0, 125, 131), RGBColor(24, 43, 75), RGBColor(94, 107, 126),
                                         RGBColor(0xDE, 0xE6, 0xEE), RGBColor(0xEF, 0xF5, 0xF8), RGBColor(255, 255, 255))
GREEN, RED = RGBColor(0x2E, 0x8B, 0x57), RGBColor(0xC0, 0x39, 0x2B)
IN = 914400
DATE = "24 NOV 2026  |  PHASE 3: METHODOLOGY & PROGRESS"

prs = Presentation()
prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
BLANK = prs.slide_layouts[6]
n_slide = 0


def box(s, x, y, w, h, color):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN)))
    r.fill.solid(); r.fill.fore_color.rgb = color; r.line.fill.background(); r.shadow.inherit = False
    return r


def text(s, x, y, w, h, lines, size=14, color=NAVY, bold=False, align=None):
    tb = s.shapes.add_textbox(Emu(int(x * IN)), Emu(int(y * IN)), Emu(int(w * IN)), Emu(int(h * IN)))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, ln in enumerate([lines] if isinstance(lines, str) else lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if isinstance(ln, tuple):
            ln, kw = ln
        else:
            kw = {}
        r = p.add_run(); r.text = ln
        r.font.name = "Aptos"; r.font.size = Pt(kw.get("size", size)); r.font.bold = kw.get("bold", bold)
        r.font.color.rgb = kw.get("color", color)
        p.space_after = Pt(kw.get("after", 4))
        if align: p.alignment = align
    return tb


def slide(title):
    global n_slide
    n_slide += 1
    s = prs.slides.add_slide(BLANK)
    box(s, 0.62, 0.42, 0.09, 0.62, TEAL)
    text(s, 0.85, 0.42, 9.9, 0.75, title, 28, NAVY, True)
    box(s, 0.62, 1.15, 12.0, 0.025, LINE)
    s.shapes.add_picture(io.BytesIO(LOGO), Emu(9966960), Emu(274320), height=Emu(415777))
    text(s, 0.67, 7.07, 3.6, 0.25, DATE, 9, MUTED)
    text(s, 4.4, 7.07, 6, 0.25, "MDM2  •  Intelligent Systems in Production  •  Group 7", 9, MUTED)
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


# ---------------------------------------------------------------- data from the sensitivity run
def rel(param, level, kpi):
    r = SENS[(SENS.param == param) & (SENS.level == level) & (SENS.kpi == kpi)].iloc[0]
    return r["rel_%"], r["p"]


PARAMS = [p for p in SENS.param.unique() if p != "baseline"]
LABEL = {"demand": "Demand ±10 %", "wear_rate": "Screw wear ×0.5 / ×1.5", "repair_time": "Repair time ×0.5 / ×1.5",
         "technicians": "Technicians 1 / 3", "setters": "Day setters 2 / 4", "mould_change": "Mould change 90 / 180 min",
         "pm_duration": "PM duration 60 / 240 min", "qa_hold": "QA hold 24 / 72 h", "hvac": "HVAC 60 / 180 kW",
         "camera": "Camera detect 95 / 99.5 %"}
n_seeds = int(pd.read_csv(WS / "simulation/results/sensitivity_runs.csv").seed.nunique())
KP = ["lead_time_h", "kwh_per_1000_good", "maintenance_h", "on_time_rate"]
levels = [("baseline", "base")] + [(p, l) for p in PARAMS for l in ("low", "high")]
better = {k: sum((rel(p, l, k)[0] > 0) == (k == "on_time_rate") for p, l in levels) for k in KP}
sig_better = {k: sum(((rel(p, l, k)[0] > 0) == (k == "on_time_rate")) and rel(p, l, k)[1] < 0.05 for p, l in levels)
              for k in KP}
sig_worse = {k: sum(((rel(p, l, k)[0] > 0) != (k == "on_time_rate")) and rel(p, l, k)[1] < 0.05 for p, l in levels)
             for k in KP}
N_LV = len(levels)
base_lt, _ = rel("baseline", "base", "lead_time_h")
lt = {(p, l): rel(p, l, "lead_time_h")[0] for p, l in levels}
en = {(p, l): rel(p, l, "kwh_per_1000_good")[0] for p, l in levels}
worst_lt = max(lt, key=lt.get)

# ---------------------------------------------------------------- 1 title
s = prs.slides.add_slide(BLANK); n_slide += 1
box(s, 0.62, 0.55, 0.09, 1.0, TEAL)
text(s, 0.85, 0.5, 9.5, 1.2, ["AI-Driven Multi-Objective Optimization", "of a Medical Injection-Moulding Line"], 30, NAVY, True)
s.shapes.add_picture(io.BytesIO(LOGO), Emu(9966960), Emu(274320), height=Emu(415777))
text(s, 0.85, 2.0, 11, 0.4, "Phase 3: methodology, feature progress, tests/CI and issues board", 18, MUTED)
text(s, 0.85, 2.45, 11, 0.4, "Simulated case study: Gerresheimer medical-plastics plant, Pfreimd (Bavaria)", 15, TEAL, True)
for i, (h, b) in enumerate([("✓  METHODOLOGY", "Data sources, assumptions and evaluation design locked"),
                            ("✓  NEW FEATURE", f"Sensitivity analysis: 10 parameters × 2 levels × {n_seeds} scenarios"),
                            ("✓  TESTS · CI · BOARD", "29 tests green on GitHub Actions; 10 issues on 4 milestones")]):
    card(s, 0.85 + i * 3.85, 3.05, 3.6, 1.35, h, b)
text(s, 0.85, 4.85, 11, 0.4, "MDM2 Case Study: Intelligent Systems in Production  |  24 Nov 2026", 15, TEAL, True)
text(s, 0.85, 5.3, 11, 0.6, "Supervised by Hamidreza Heidari, PhD  •  Team: Kuriakose Vettikattil Raju (Team Lead), "
     "Mahesh Koduri, Saurabhkumar Mahant", 12, NAVY)

# ---------------------------------------------------------------- 2 methodology
s = slide("Methodology and Evaluation Design")
steps = [("1 Data", "AI4I 2020 failures\n+ literature plant\nparameters"),
         ("2 Model", "SimPy discrete-event\n12 presses, 5 stations"),
         ("3 Policies", "4 fixed rules vs\nPRED-MO (ML + tuned)"),
         ("4 Tuning", "NSGA-II on seeds 0–2\n(base + high demand)"),
         ("5 Evaluation", "100 unseen seeds\npaired t-tests, 95 % CI"),
         ("6 Robustness", "One-at-a-time\nsensitivity (NEW)")]
for i, (h, b) in enumerate(steps):
    x = 0.75 + i * 2.0
    card(s, x, 1.45, 1.8, 1.45, h, b, dark=i == 5, hsize=13, bsize=11)
    if i < 5:
        text(s, x + 1.8, 1.95, 0.2, 0.3, "→", 16, MUTED, True)
text(s, 0.75, 3.15, 6, 0.35, "Design rules that make the comparison fair", 15, TEAL, True)
text(s, 0.75, 3.55, 5.9, 2.8, [
    "•  Common random numbers: every policy sees the same orders, sensor noise and repair draws per seed",
    "•  Strict train/test split: tuning seeds 0–2, evaluation seeds 100–199, 'harsh' scenario never tuned on",
    "•  Warm-up (3 weeks) excluded from KPIs; 12-week order release, 6-week drain",
    "•  Non-ML baseline (SETUP+PM wear rule) tuned with the same budget, so ML must earn its place"], 12)
text(s, 7.0, 3.15, 5.5, 0.35, "KPIs (four objectives)", 15, TEAL, True)
table(s, 7.0, 3.6, 5.5, [["KPI", "Unit", "Better"],
                         ["Lead time (order → QA release)", "h", "lower"],
                         ["Energy", "kWh / 1,000 good parts", "lower"],
                         ["Maintenance time", "h", "lower"],
                         ["Escaped defects · OEE", "ppm · ratio", "lower · higher"]], [2.6, 1.9, 1.0], 11)

# ---------------------------------------------------------------- 3 data sources
s = slide("Data Sources and Locked Assumptions")
table(s, 0.75, 1.4, 11.8, [
    ["Input", "Value in the model", "Source", "Type"],
    ["Failure behaviour", "AI4I 2020 rules (TWF, HDF, PWF, OSF, RNF), RF risk model", "UCI AI4I 2020 (Matzka 2020)", "real data (proxy)"],
    ["Presses & energy", "4×80 t electric, 5×150 t hybrid, 3×250 t hydraulic; 14–38 kW busy", "Thiriez & Gutowski 2006", "literature"],
    ["Resin drying", "PP 0, POM 150, ABS 180, PC 240 min", "Rosato 2000", "literature"],
    ["Changeovers", "45 min GMP clearance + 165 min mould change / 40 min purge", "EU GMP Annex 1; industry practice", "assumption"],
    ["Crews", "3 setters day / 1 night, 2 technicians, 2 toolmakers", "team assumption", "assumption → tested"],
    ["Repairs", "3–24 h lognormal per failure mode", "team assumption", "assumption → tested"],
    ["QA release", "48 h mean batch-release hold", "EU GMP Annex 16", "assumption → tested"],
    ["Clean-room HVAC", "120 kW fixed load", "team assumption", "assumption → tested"],
], [2.0, 5.0, 2.9, 1.9], 11, 0.4)
text(s, 0.75, 5.3, 11.8, 0.9, [
    ("Gerresheimer publishes no operational data. Every 'assumption' row is now covered by the sensitivity analysis, "
     "so a wrong guess shows up as a changed conclusion instead of staying hidden.", {"color": NAVY}),
    ("Risk: AI4I is a milling dataset, not moulding. We use it only as a failure signal and report it as a limitation.",
     {"color": MUTED, "size": 11})], 12)

# ---------------------------------------------------------------- 4 feature progress
s = slide("Feature Progress Since 3 November")
card(s, 0.75, 1.45, 3.85, 4.6, "DONE", [
    "•  Model v2: 12 presses, 8 moulds with copies",
    "•  Setter + technician crews, night shift",
    "•  Press failure modes mapped from AI4I",
    "•  Energy by drive type, OEE",
    "•  Camera errors, 48 h GMP QA release",
    "•  Non-ML wear-rule baseline (SETUP+PM)",
    "•  Re-tuned + 100 held-out scenarios",
    "•  Sensitivity analysis module (NEW)"], bsize=12)
card(s, 4.8, 1.45, 3.85, 4.6, "IN PROGRESS  →  8 DEC", [
    "•  Time-of-day electricity prices (#4)",
    "•  More tests: energy cost, crews (#5)",
    "•  Morris screening for interactions (#6)"], bsize=12)
card(s, 8.85, 1.45, 3.75, 4.6, "NEXT  →  22 DEC / 12 JAN", [
    "•  Dashboard: press Gantt, queues, KPIs (#7)",
    "•  Demo video + run instructions (#8)",
    "•  Real figures from datasheets (#9)",
    "•  IEEE final report (#10)"], dark=True, bsize=12)
text(s, 0.75, 6.25, 11.8, 0.4, "Issue numbers refer to the GitHub issues board (slide 8).", 11, MUTED)

# ---------------------------------------------------------------- 5 sensitivity chart
s = slide("Sensitivity: Does PRED-MO Hold Up?")
cd = CategoryChartData()
cats = [LABEL[p] for p in PARAMS][::-1]
cd.categories = cats
for lvl, name in (("low", "low value"), ("high", "high value")):
    cd.add_series(name, [round(lt[(p, lvl)], 2) for p in PARAMS][::-1])
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Emu(int(0.6 * IN)), Emu(int(1.35 * IN)),
                        Emu(int(7.4 * IN)), Emu(int(5.5 * IN)), cd)
ch = gf.chart
ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
ch.legend.font.size = Pt(10)
ch.has_title = True; ch.chart_title.text_frame.text = "PRED-MO vs SETUP+PM: lead-time change (%)"
ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
ch.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = NAVY
for ser, col in zip(ch.series, (TEAL, NAVY)):
    ser.invert_if_negative = False
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = col
from pptx.enum.chart import XL_TICK_LABEL_POSITION
ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
ch.category_axis.tick_labels.font.size = Pt(10)
ch.value_axis.tick_labels.font.size = Pt(10)
ch.value_axis.has_major_gridlines = False
text(s, 8.25, 1.45, 4.4, 0.35, "Setup", 15, TEAL, True)
text(s, 8.25, 1.85, 4.4, 2.2, [
    "•  10 assumed parameters, each moved to a low and a high value",
    "•  All other parameters stay at base demand",
    f"•  FCFS, SETUP+PM, PRED-MO on the same {n_seeds} seeds per level ({N_LV} levels)",
    "•  Tuned settings frozen: no re-tuning per level"], 11)
text(s, 8.25, 4.15, 4.4, 0.35, "Reading the chart", 15, TEAL, True)
text(s, 8.25, 4.55, 4.4, 1.8, [
    "Bars left of zero: PRED-MO delivers faster than the tuned wear rule.",
    f"Baseline (all parameters at base): {base_lt:+.1f} %."], 11)

# ---------------------------------------------------------------- 6 sensitivity findings
s = slide("Sensitivity Results")
rows = [["KPI (PRED-MO vs SETUP+PM)", "Better in", "Significantly better", "Significantly worse"]]
names = {"lead_time_h": "Lead time", "kwh_per_1000_good": "Energy / 1,000 good", "maintenance_h": "Maintenance time",
         "on_time_rate": "On-time rate"}
for k in KP:
    rows.append([names[k], f"{better[k]} / {N_LV} levels", f"{sig_better[k]}", f"{sig_worse[k]}"])
table(s, 0.75, 1.45, 7.0, rows, [2.6, 1.5, 1.6, 1.3], 12, 0.42)
text(s, 0.75, 3.85, 7.0, 0.3, f"p < 0.05, paired t-test over {n_seeds} common seeds per level.", 10, MUTED)
lt_range = (min(lt.values()), max(lt.values()))
en_range = (min(en.values()), max(en.values()))
text(s, 8.1, 1.45, 4.5, 0.35, "Findings", 15, TEAL, True)
text(s, 8.1, 1.85, 4.5, 4.4, [
    f"•  Lead time: PRED-MO faster at all {N_LV} levels ({lt_range[0]:+.1f} % to {lt_range[1]:+.1f} %); "
    "gap grows with demand, vanishes at low demand",
    f"•  Energy: lower at all levels ({en_range[0]:+.1f} % to {en_range[1]:+.1f} %)",
    "•  Maintenance time flips sign: worse when repairs are short (×0.5) or PM is long (240 min), "
    "better when repairs are long or PM is short. The ML trigger pays off only when breakdowns are expensive",
    "•  Escaped defects worse only at high wear; OEE always ~1 % lower (more planned stops)"], 12)
text(s, 0.75, 4.35, 7.0, 2.0, [
    ("Why one-at-a-time first", {"color": TEAL, "bold": True, "size": 14}),
    "OAT is cheap and readable (21 levels × 3 policies). It cannot show interactions, e.g. high demand together with "
    "a small repair crew. Morris screening (#6) covers that before 8 Dec."], 12)

# ---------------------------------------------------------------- 7 tests & CI
s = slide("Unit Tests and CI Status")
for i, (h, b) in enumerate([("29", "test cases\n(22 test functions)"), ("~20 s", "full suite\nruntime"),
                            ("green", "GitHub Actions on\nevery push + PR"), ("uv.lock", "pinned versions,\nreproducible")]):
    box(s, 0.75 + i * 3.0, 1.45, 2.8, 1.45, CARD)
    text(s, 0.87 + i * 3.0, 1.52, 2.6, 0.6, h, 28, TEAL, True)
    text(s, 0.87 + i * 3.0, 2.15, 2.6, 0.7, b, 12, NAVY)
table(s, 0.75, 3.2, 7.2, [
    ["Area", "What the tests check"],
    ["Reproducibility", "same seed → same orders and KPIs; policies face identical scenarios"],
    ["Flow conservation", "every order ships; rejects + escapes ≤ quantity; OEE ≤ availability"],
    ["Moulds & setups", "mould fits only its press classes; each copy on one press; setup-aware choice"],
    ["Failures & repair", "AI4I failure rules; repair fixes only the failed part; repair_scale (NEW)"],
    ["Energy & quality", "idle shutdown saves energy; perfect camera lets no defect escape; QA hold"],
    ["Risk model", "physical features; ranks failures above healthy; fast predict = sklearn"],
], [1.8, 5.4], 10, 0.36)
text(s, 8.25, 3.2, 4.3, 0.35, "Pipeline", 15, TEAL, True)
text(s, 8.25, 3.6, 4.3, 2.6, [
    "push / PR → checkout → uv sync --locked → pytest -q",
    "",
    "Workflow: .github/workflows/ci.yml",
    "Badge in simulation/README.md",
    "",
    ("Rule: every new feature lands with a test that fails without it.", {"bold": True})], 11)

# ---------------------------------------------------------------- 8 issues board
s = slide("Issues Board and Milestones")
table(s, 0.75, 1.4, 11.8, [
    ["#", "Issue", "Label", "Milestone"],
    ["1", "Sensitivity analysis on assumed plant parameters", "experiment", "24 Nov"],
    ["2", "Issues board and milestones for Phase 3–5", "docs", "24 Nov"],
    ["3", "24 Nov progress presentation", "presentation", "24 Nov"],
    ["4", "Time-of-day electricity prices in the energy KPI", "feature", "8 Dec"],
    ["5", "Extend tests: sensitivity, energy cost, crew limits", "testing", "8 Dec"],
    ["6", "Global sensitivity (Morris) if OAT shows interactions", "experiment", "8 Dec"],
    ["7", "Dashboard for a simulation run", "feature", "22 Dec"],
    ["8", "Demo video + run instructions", "presentation", "22 Dec"],
    ["9", "Real figures from Gerresheimer or press datasheets", "data", "12 Jan"],
    ["10", "Final report (IEEE) and final presentation", "docs", "12 Jan"],
], [0.6, 7.0, 2.0, 2.2], 11, 0.38)
text(s, 0.75, 5.75, 11.8, 0.4, "github.com/MaheshBhushan/Case-Study-Intelligent-Systems/issues", 13, TEAL, True)

# ---------------------------------------------------------------- 9 risks, ethics, next
s = slide("Risks, Ethics and Next Steps")
card(s, 0.75, 1.45, 3.85, 4.6, "RISKS", [
    "•  No real plant data: results compare policies, they do not predict Pfreimd",
    "•  AI4I is milling data used as a proxy",
    "•  Policies tuned on 3 seeds may overfit (mitigated by 100 unseen seeds)",
    "•  OAT misses interactions → Morris (#6)"], bsize=12)
card(s, 4.8, 1.45, 3.85, 4.6, "ETHICS", [
    "•  Only public data; no personal or company-confidential data",
    "•  Company named only as a public reference case",
    "•  Workforce: crews modelled as capacity, not individual performance",
    "•  Medical-device safety: AI advises maintenance, humans keep GMP release"], bsize=12)
card(s, 8.85, 1.45, 3.75, 4.6, "BY 8 DEC", [
    "•  Time-of-day energy prices + tests",
    "•  Morris screening",
    "•  Dashboard prototype",
    "•  Datasheet values for press power"], dark=True, bsize=12)

out = Path(sys.argv[1])
prs.save(out)
print("saved", out)
