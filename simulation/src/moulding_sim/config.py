"""Synthetic plant parameters for a medical injection-moulding plant (Gerresheimer Pfreimd reference).

All values are literature-informed assumptions (Rosato 2000 for materials and drying,
Thiriez & Gutowski 2006 for press energy by drive type, EU GMP Annex 1 for line clearance and
batch release). Gerresheimer publishes no operational data. Time unit: minutes.
"""

from dataclasses import dataclass, field, replace

STATIONS = ("drying", "moulding", "inspection", "assembly", "packaging")
DAY = 1440.0
WEEK = 7 * DAY


@dataclass(frozen=True)
class Material:
    name: str
    drying_min: float  # resin drying before moulding (0 = not hygroscopic)
    ai4i_type: str  # AI4I wear class L/M/H used by the failure model


MATERIALS = {
    "PP": Material("PP", 0.0, "L"),
    "ABS": Material("ABS", 180.0, "M"),
    "POM": Material("POM", 150.0, "M"),
    "PC": Material("PC", 240.0, "H"),
}


@dataclass(frozen=True)
class PressClass:
    name: str
    tonnage: int
    drive: str
    busy_kw: float
    idle_kw: float  # heaters on (+ pump for hydraulic drives)
    count: int


PRESS_CLASSES = (
    PressClass("S", 80, "all-electric", 14.0, 3.0, 4),
    PressClass("M", 150, "hybrid", 24.0, 8.0, 5),
    PressClass("L", 250, "hydraulic", 38.0, 16.0, 3),
)


@dataclass(frozen=True)
class Mould:
    name: str
    classes: tuple[str, ...]  # press classes the mould fits (clamp force, platen size)
    cavities: int
    cycle_s: float
    rpm: float  # nominal screw speed
    torque: float  # nominal screw torque [Nm]
    copies: int  # identical tools; each can be on one press at a time


MOULDS = {m.name: m for m in (
    Mould("inhaler_housing", ("M", "L"), 8, 22.0, 1450, 46, 3),
    Mould("mouthpiece_cap", ("S", "M"), 16, 14.0, 1550, 36, 2),
    Mould("counter_wheel", ("S",), 32, 12.0, 1700, 30, 2),
    Mould("pen_body", ("M", "L"), 8, 24.0, 1400, 50, 2),
    Mould("pen_cap", ("S", "M"), 16, 16.0, 1500, 38, 3),
    Mould("dose_knob", ("S", "M"), 16, 18.0, 1380, 44, 2),
    Mould("lancet_body", ("S",), 32, 12.0, 1650, 32, 2),
    Mould("lancing_housing", ("L",), 4, 28.0, 1360, 54, 2),
)}


@dataclass(frozen=True)
class Product:
    name: str
    mould: str
    material: str
    colour: str
    part_g: float
    lot_k: tuple[int, int]  # campaign lot size range, thousand parts

    @property
    def min_per_part(self) -> float:
        m = MOULDS[self.mould]
        return m.cycle_s / m.cavities / 60


PRODUCTS = (
    Product("housing_white", "inhaler_housing", "ABS", "white", 12.0, (50, 150)),
    Product("housing_blue", "inhaler_housing", "ABS", "blue", 12.0, (50, 150)),
    Product("mouthpiece_cap", "mouthpiece_cap", "PP", "white", 2.5, (150, 450)),
    Product("counter_wheel", "counter_wheel", "POM", "natural", 0.8, (300, 900)),
    Product("pen_body", "pen_body", "PC", "clear", 6.0, (40, 120)),
    Product("pen_cap_white", "pen_cap", "PP", "white", 3.0, (120, 360)),
    Product("pen_cap_grey", "pen_cap", "PP", "grey", 3.0, (120, 360)),
    Product("dose_knob", "dose_knob", "POM", "natural", 1.5, (100, 300)),
    Product("lancet_body", "lancet_body", "PP", "natural", 0.5, (300, 900)),
    Product("lancing_housing", "lancing_housing", "ABS", "grey", 20.0, (20, 60)),
)


@dataclass(frozen=True)
class Setup:
    line_clearance: float = 45.0  # GMP line clearance on every product change
    mould_change: float = 120.0  # unmount + mount
    mould_heatup: float = 45.0
    purge: float = 40.0  # barrel purge on material or colour change


@dataclass(frozen=True)
class Crew:
    setters_day: int = 3  # 06:00-22:00
    setters_night: int = 1
    technicians: int = 2  # maintenance, 24/7
    toolmakers: int = 2  # toolroom for mould repair and service


@dataclass(frozen=True)
class Power:
    """kW. Press busy/idle power comes from PRESS_CLASSES."""

    station_busy: dict = field(default_factory=lambda: {
        "drying": 6.0, "inspection": 4.0, "assembly": 10.0, "packaging": 8.0})
    station_idle: dict = field(default_factory=lambda: {
        "drying": 1.0, "inspection": 1.0, "assembly": 3.0, "packaging": 2.0})
    press_off: float = 0.5
    warmup_frac: float = 0.8  # barrel re-heat draws 80 % of busy power
    warmup_min: float = 45.0
    hvac: float = 120.0  # ISO 8 moulding hall + ISO 7 packaging clean room


# Repair time (lognormal mean, sd in minutes) per failure mode, and what a repair restores.
REPAIR = {
    "TWF": (480.0, 120.0),  # screw/barrel wear
    "HDF": (180.0, 60.0),  # heater band / cooling
    "PWF": (360.0, 120.0),  # drive / hydraulic overload
    "OSF": (360.0, 120.0),  # screw overstrain
    "RNF": (240.0, 90.0),  # random fault
    "MOULD": (1440.0, 360.0),  # mould damage, toolroom repair
}
FAILURE_LABEL = {"TWF": "screw/barrel wear", "HDF": "heater/cooling", "PWF": "drive overload",
                 "OSF": "screw overstrain", "RNF": "random fault", "MOULD": "mould damage"}
TYPE_WEAR = {"L": 2.0, "M": 3.0, "H": 5.0}  # AI4I wear increments per type, normalised by /3
OSF_LIMIT = {"L": 11000.0, "M": 12000.0, "H": 13000.0}


@dataclass(frozen=True)
class Scenario:
    name: str = "base"
    interarrival: float = 480.0  # mean minutes between campaign orders (Poisson)
    performance: tuple[float, float] = (0.85, 0.95)  # share of ideal speed per campaign (OEE P)
    rush_share: float = 0.10
    due_days: tuple[float, float] = (14.0, 28.0)
    rush_due_days: tuple[float, float] = (7.0, 10.0)
    horizon: float = 12 * WEEK  # order release window
    warmup: float = 3 * WEEK  # excluded from KPIs
    drain: float = 6 * WEEK  # time for released orders to finish
    dryers: int = 4
    lines: dict = field(default_factory=lambda: {"inspection": 3, "assembly": 3, "packaging": 2})
    rates: dict = field(default_factory=lambda: {  # parts / min per line
        "inspection": 400.0, "assembly": 300.0, "packaging": 500.0})
    block_min: float = 480.0  # sensor reading + maintenance decision every shift
    wear_per_min: float = 0.008  # AI4I tool-wear minutes per running minute (type-scaled)
    fouling_per_min: float = 0.00015  # K of heat-dissipation margin lost per running minute
    mould_damage_shots: float = 4e6  # mean shots between mould damage events
    mould_service_shots: float = 1.5e6  # planned mould service interval
    mould_service_min: float = 720.0
    pm_duration: float = 120.0
    qa_hold: tuple[float, float] = (2880.0, 960.0)  # GMP batch release, lognormal mean/sd
    base_defect: float = 0.005
    wear_defect: float = 0.03  # extra defect rate at full screw wear
    camera_detect: float = 0.98
    camera_false_reject: float = 0.003
    startup_scrap_units: int = 500  # first-article scrap after a changeover
    restart_scrap_units: int = 800  # purge after a breakdown
    setup: Setup = field(default_factory=Setup)
    crew: Crew = field(default_factory=Crew)
    power: Power = field(default_factory=Power)

    def with_(self, **kw) -> "Scenario":
        return replace(self, **kw)


SCENARIOS = {
    "low": Scenario(name="low", interarrival=560.0),
    "base": Scenario(name="base"),
    "high": Scenario(name="high", interarrival=420.0),
    "harsh": Scenario(name="harsh", wear_per_min=0.012, fouling_per_min=0.00025),
}
