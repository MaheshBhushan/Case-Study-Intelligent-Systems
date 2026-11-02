"""Synthetic plant parameters for the five-station medical moulding line.

All values are literature-informed assumptions (Rosato 2000, Thiriez & Gutowski 2006,
EU GMP Annex 1); Gerresheimer publishes no operational data. Time unit: minutes.
"""

from dataclasses import dataclass, field, replace

STATIONS = ("drying", "moulding", "inspection", "assembly", "packaging")


@dataclass(frozen=True)
class Product:
    name: str
    mould: str
    ai4i_type: str  # AI4I quality variant L/M/H: drives wear rate and OSF limit
    cavities: int
    cycle_s: float  # injection cycle per shot
    drying_min: float  # resin drying per lot
    rpm: float  # nominal screw speed
    torque: float  # nominal screw torque [Nm]


PRODUCTS = (
    Product("inhaler_housing", "A", "L", 8, 18.0, 180, 1500, 40),
    Product("inhaler_cap", "A", "L", 16, 14.0, 180, 1450, 44),
    Product("pen_body", "B", "M", 8, 22.0, 240, 1400, 48),
    Product("pen_clip", "B", "M", 16, 15.0, 240, 1550, 38),
    Product("lancet_body", "C", "H", 32, 12.0, 120, 1700, 32),
    Product("lancet_cap", "C", "H", 16, 20.0, 120, 1380, 52),
)


@dataclass(frozen=True)
class Setup:
    line_clearance: float = 45.0  # GMP line clearance on every product change
    insert_change: float = 20.0  # same mould, different cavity insert
    mould_change: float = 90.0  # unmount + mount mould
    mould_heatup: float = 30.0


@dataclass(frozen=True)
class Power:
    """kW per station state. HVAC is a constant clean-room load."""

    busy: dict = field(default_factory=lambda: {
        "drying": 12.0, "moulding": 45.0, "inspection": 3.0, "assembly": 8.0, "packaging": 6.0})
    idle: dict = field(default_factory=lambda: {
        "drying": 4.0, "moulding": 15.0, "inspection": 1.0, "assembly": 2.0, "packaging": 2.0})
    setup: float = 10.0  # moulding machine during changeover / maintenance
    off: float = 1.0
    warmup: float = 40.0  # barrel re-heat after shutdown
    warmup_min: float = 30.0
    hvac: float = 60.0  # ISO 7 clean rooms for moulding + packaging


@dataclass(frozen=True)
class Scenario:
    name: str = "base"
    interarrival: float = 115.0  # mean minutes between orders (Poisson)
    lot_min: int = 2000
    lot_max: int = 6000
    rush_share: float = 0.15
    horizon: float = 14 * 1440.0  # order release window
    warmup: float = 2 * 1440.0  # excluded from KPIs
    drain: float = 4 * 1440.0  # extra time to let released orders finish
    moulding_machines: int = 2
    dryer_capacity: int = 2
    rates: dict = field(default_factory=lambda: {  # units / min
        "inspection": 80.0, "assembly": 60.0, "packaging": 60.0})
    wear_per_min: float = 0.035  # AI4I tool-wear minutes per moulding minute (scaled by type)
    fouling_per_min: float = 0.0004  # K lost in heat dissipation per moulding minute
    repair_mean: float = 240.0  # unplanned repair, lognormal
    repair_sd: float = 90.0
    pm_duration: float = 60.0  # planned preventive maintenance
    base_scrap: float = 0.01
    startup_scrap_units: int = 150  # first-article scrap after mould/product change
    restart_scrap_units: int = 300  # purge after a breakdown
    setup: Setup = field(default_factory=Setup)
    power: Power = field(default_factory=Power)

    def with_(self, **kw) -> "Scenario":
        return replace(self, **kw)


SCENARIOS = {
    "low": Scenario(name="low", interarrival=135.0),
    "base": Scenario(name="base"),
    "high": Scenario(name="high", interarrival=100.0),
    "harsh": Scenario(name="harsh", wear_per_min=0.05, fouling_per_min=0.0007),
}

TYPE_WEAR = {"L": 2.0, "M": 3.0, "H": 5.0}  # AI4I wear increments per type, normalised below
OSF_LIMIT = {"L": 11000.0, "M": 12000.0, "H": 13000.0}
