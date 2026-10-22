"""
Sizes of the components and their purchased equipment costs from the correlations of OpenPyTEA :cite:`Tamarona2026`.

A cost function takes one or more sizes of a component. :func:`sizes` returns all that the model
determines, in SI units: the power, mass flow, inlet volume flow and pressure ratio of a
turbomachine, the power of a motor or a generator, and the heat flow, heat transfer capacity, logarithmic
mean temperature difference and area of a heat exchanger, and the heat flow and live steam mass flow of a
steam generator. A user-defined cost equation takes the ones it needs; :func:`estimate` takes the one a correlation of OpenPyTEA is based on and converts it into the
units of the correlation.

The area of a heat exchanger follows from its sections: the exchanger is taken as counter-flow and
cut at every phase change of either stream, and the area is the sum of
:math:`\\dot{Q}_i / (U_i \\, \\Delta T_{\\mathrm{lm},i})`. Every section takes the overall heat transfer
coefficient given as ``U`` or, without one, the default of its comparable cell in :data:`U_CELLS`:
the exchanger type and the fluid group and phase of each stream. A default is the median of the
published values of its cell, read from ``data/heat_transfer_coefficients.json``; a section without
a cell asks for ``U``.

The correlations of OpenPyTEA come from the process-industry literature. A size outside the range
of a correlation is reported as such, and the cost is then extrapolated from the nearest bound with a
scaling exponent, split into parallel units as OpenPyTEA does, or replaced by a value given by the user.
OpenPyTEA is an optional dependency, ``pip install exerpy[costs]`` or ``pip install openpytea``. Its
costs are in US dollars.
"""

import contextlib
import json
import math
import os
import re

import CoolProp.CoolProp as CP
import pandas as pd

from exerpy import __datapath__
from exerpy.logger import logger

HP = 745.69987  # W
FT2 = 0.09290304  # m^2
BTU_PER_HOUR = 0.29307107  # W
GALLON = 0.003785411784  # m^3
FT3 = 0.028316846592  # m^3
LB = 0.45359237  # kg

EXPONENT = 0.6

LIQUID, TWO_PHASE, GAS, SUPERCRITICAL = 0, 1, 2, 3
PHASES = {LIQUID: "liquid", TWO_PHASE: "two-phase", GAS: "gas", SUPERCRITICAL: "supercritical"}
PHASES_INDEX = {name: index for index, name in PHASES.items()}

# Overall heat transfer coefficients in W/m²K per comparable cell, with their sources; see the data file.
with open(os.path.join(__datapath__, "heat_transfer_coefficients.json"), encoding="utf-8") as file:
    _HEAT_TRANSFER = json.load(file)
U_SOURCES = _HEAT_TRANSFER["sources"]
U_CELLS = _HEAT_TRANSFER["cells"]
EXCHANGER_TYPES = _HEAT_TRANSFER["exchanger_types"]
U_DEFAULTS = {
    (cell["exchanger_type"], cell["hot"], cell["cold"], cell["hot_fluid"], cell["cold_fluid"]): cell
    for cell in U_CELLS
    if cell["default"]
}

# The sizes the model determines per component class; a cost function takes the ones it needs.
QUANTITIES = {
    "Compressor": ("power", "mass_flow", "volume_flow", "pressure_ratio"),
    "Pump": ("power", "mass_flow", "volume_flow", "pressure_ratio"),
    "Turbine": ("power", "mass_flow", "volume_flow", "pressure_ratio"),
    "Generator": ("power",),
    "Motor": ("power",),
    "HeatExchanger": ("heat", "kA", "dT_lm", "area"),
    "SimpleHeatExchanger": ("heat",),
    "SteamGenerator": ("heat", "mass_flow"),
}

# The OpenPyTEA categories that cost a component class.
CATEGORIES = {
    "Compressor": ["Compressors, fans, & blowers", "Compressors & blowers"],
    "Pump": ["Pumps"],
    "Turbine": ["Turbines"],
    "Generator": ["Motors & generators"],
    "Motor": ["Motors & generators"],
    "HeatExchanger": ["Heat exchangers"],
    "SimpleHeatExchanger": ["Heat exchangers", "Boilers, heaters, & furnaces"],
    "SteamGenerator": ["Boilers, heaters, & furnaces"],
    "CombustionChamber": ["Boilers, heaters, & furnaces"],
    "Drum": ["Pressure vessels"],
    "Deaerator": ["Pressure vessels"],
    "FlashTank": ["Pressure vessels"],
    "Storage": ["Tanks", "Pressure vessels"],
}

# Correlations quoting a purchased cost over a wide size range, chosen when nothing else is.
DEFAULTS = {
    "Compressor": "centrifugal_compressor_towler_2010",
    "Pump": "centrifugal_pump_turton_2001",
    "Turbine": "axial_gas_turbine_ulrich_2003",
    "Motor": "totally_enclosed_motor_ulrich_2003",
    "HeatExchanger": "u_shell_tube_hx_towler_2010",
    "SteamGenerator": "steam_boiler_turton_2001",
}
STEAM_TURBINE = "condensing_steam_turbine_towler_2010"

UNITS = {
    "power": "W",
    "heat": "W",
    "mass_flow": "kg/s",
    "volume_flow": "m³/s",
    "pressure_ratio": "-",
    "kA": "W/K",
    "dT_lm": "K",
    "area": "m²",
    "volume": "m³",
}
# The dimension of each size, as dimension() reads it from the units of a correlation.
DIMENSIONS = {
    "power": "rate",
    "heat": "rate",
    "area": "area",
    "volume": "volume",
    "volume_flow": "volume_flow",
    "mass_flow": "mass_flow",
}

CURRENCY = "USD"

# Annual averages of the euro reference rate of the European Central Bank, in USD per EUR. The
# years before the euro carry the average of its predecessor, the ECU, which the Perry (1996) and
# ESDU (1997) correlations need. 2025 is the average of the full year.
USD_PER_EUR = {
    1996: 1.2698,
    1997: 1.1340,
    1998: 1.1206,
    1999: 1.0658,
    2000: 0.9236,
    2001: 0.8956,
    2002: 0.9456,
    2003: 1.1312,
    2004: 1.2439,
    2005: 1.2441,
    2006: 1.2556,
    2007: 1.3705,
    2008: 1.4708,
    2009: 1.3948,
    2010: 1.3257,
    2011: 1.3920,
    2012: 1.2848,
    2013: 1.3281,
    2014: 1.3285,
    2015: 1.1095,
    2016: 1.1069,
    2017: 1.1297,
    2018: 1.1810,
    2019: 1.1195,
    2020: 1.1422,
    2021: 1.1827,
    2022: 1.0530,
    2023: 1.0813,
    2024: 1.0824,
    2025: 1.1300,
}

# Names of water in the exports that CoolProp does not know.
WATER_NAMES = {"h2og", "h2ol", "l_h2o", "steam"}


def available():
    """Whether OpenPyTEA :cite:`Tamarona2026` is installed."""
    try:
        import openpytea  # noqa: F401
    except ImportError:
        return False
    return True


def _openpytea():
    try:
        from openpytea import equipment
    except ImportError:
        raise ImportError("Estimating purchased equipment costs needs OpenPyTEA: pip install openpytea") from None
    return equipment


def correlations(component_class=None):
    """
    Return the cost correlations of OpenPyTEA :cite:`Tamarona2026`, or the ones that cost a class of component.

    Parameters
    ----------
    component_class : str, optional
        Name of a component class, e.g. ``"Compressor"``. Without it, every correlation is returned.

    Returns
    -------
    pandas.DataFrame
        Columns ``key``, ``category``, ``type``, ``units``, ``s_lower``, ``s_upper``,
        ``reference_year``, ``material``, ``source`` and ``remarks``, one row per correlation. The
        correlations whose size cannot be derived from the units they state are included; they
        take a size given by hand.
    """
    df = _openpytea().COST_DB_DF.copy()
    df.columns = [column.strip().lower() for column in df.columns]
    df = df.rename(columns={"default material": "material", "cost_year": "reference_year"})
    if component_class is not None:
        wanted = [category.lower() for category in CATEGORIES.get(component_class, [])]
        df = df[df["category"].str.lower().isin(wanted)]
    columns = [
        "key",
        "category",
        "type",
        "units",
        "s_lower",
        "s_upper",
        "reference_year",
        "material",
        "source",
        "remarks",
    ]
    for column in columns:
        if column not in df.columns:
            df[column] = None
    return df[columns].reset_index(drop=True)


def correlation(key):
    """The row of :func:`correlations` with the given key, as a dictionary."""
    table = correlations()
    row = table[table["key"] == key]
    if row.empty:
        raise KeyError(f"OpenPyTEA has no correlation '{key}'.")
    return row.iloc[0].to_dict()


def dimension(units):
    """
    Read the dimension and the SI factor of the size units a correlation states.

    Parameters
    ----------
    units : str
        The ``units`` text of a correlation, e.g. ``"shaft power, kW"`` or ``"area, ft^2"``.

    Returns
    -------
    tuple or None
        ``(dimension, factor)`` with the dimension ``"rate"``, ``"area"``, ``"volume"``,
        ``"volume_flow"`` or ``"mass_flow"`` and the factor that turns the SI value (W, m², m³,
        m³/s, kg/s) into the units of the correlation. ``None`` for a size of another kind, a
        product of two sizes or a volume flow at standard conditions.
    """
    text = str(units or "")
    if re.search(r"\bx\b|sqrt|&|\^0\.|/\s*\(|\)\s*/|torr|\bSm\^?3", text, flags=re.IGNORECASE):
        return None
    # A unit followed by "/" is a flow, not a size.
    rules = [
        (r"\bACFM\b|\bft\^?3/min\b", "volume_flow", 60 / FT3),
        (r"\bft\^?3/hr?\b", "volume_flow", 3600 / FT3),
        (r"\bm\^?3/s\b", "volume_flow", 1.0),
        (r"\bm\^?3/h\b", "volume_flow", 3600.0),
        (r"\bL/s\b", "volume_flow", 1e3),
        (r"\bgal/min\b|\bgpm\b", "volume_flow", 60 / GALLON),
        (r"\bkg/s\b", "mass_flow", 1.0),
        (r"\bkg/h\b", "mass_flow", 3600.0),
        (r"\bt/h\b", "mass_flow", 3.6),
        (r"\blb/hr?\b", "mass_flow", 3600 / LB),
        (r"\blb/s\b", "mass_flow", 1 / LB),
        (r"\bMMBTU/h\b", "rate", 1e-6 / BTU_PER_HOUR),
        (r"\bBtu/hr?\b", "rate", 1 / BTU_PER_HOUR),
        (r"\bMWe?\b(?!/)", "rate", 1e-6),
        (r"\bkW\b(?!/)", "rate", 1e-3),
        (r"\b(hp|bhp|horsepower)\b(?!/)", "rate", 1 / HP),
        (r"\bft\^?2\b(?!/)|\bft²(?!/)", "area", 1 / FT2),
        (r"\bm\^?2\b(?!/)|\bm²(?!/)", "area", 1.0),
        (r"\bft\^?3\b(?!/)|\bft³(?!/)", "volume", 1 / FT3),
        (r"\bm\^?3\b(?!/)|\bm³(?!/)", "volume", 1.0),
        (r"\bgal\b(?!/)", "volume", 1 / GALLON),
    ]
    for pattern, kind, factor in rules:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return kind, factor
    return None


def quantities(component):
    """The sizes the model determines for a component, see :data:`QUANTITIES`; empty for any other class."""
    return QUANTITIES.get(type(component).__name__, ())


def _streams(component, kind="material"):
    inlets = [conn for conn in getattr(component, "inl", {}).values() if conn.get("kind", "material") == kind]
    outlets = [conn for conn in getattr(component, "outl", {}).values() if conn.get("kind", "material") == kind]
    return inlets, outlets


def _power(component):
    if getattr(component, "P", None):
        return abs(component.P)
    powers = [
        abs(conn.get("energy_flow") or 0) for conn in _streams(component, "power")[0] + _streams(component, "power")[1]
    ]
    return max(powers) if powers else None


def _heat(component):
    inlets, outlets = _streams(component)
    if not inlets or not outlets:
        return None
    try:
        absorbed = sum(c["m"] * c["h"] for c in outlets) - sum(c["m"] * c["h"] for c in inlets)
    except (KeyError, TypeError):
        return None
    return abs(absorbed)


def _material(connections):
    return [conn for _, conn in sorted(connections.items()) if conn.get("kind", "material") == "material"]


def _inlet(component):
    inlets = _material(getattr(component, "inl", {}))
    return inlets[0] if inlets else None


def _mass_flow(component):
    # A steam generator is sized by the live steam it raises, its first outlet.
    if type(component).__name__ == "SteamGenerator":
        outlets = _material(getattr(component, "outl", {}))
        return outlets[0].get("m") if outlets else None
    inlet = _inlet(component)
    return None if inlet is None else inlet.get("m")


def _volume_flow(component):
    """The volume flow at the inlet in m³/s, from the specific volume of the export or from CoolProp."""
    inlet = _inlet(component)
    if inlet is None or not inlet.get("m"):
        return None
    v = _specific_volume(inlet)
    if v is None and _fluid(inlet) is not None:
        with contextlib.suppress(KeyError, ValueError):
            v = 1 / CP.PropsSI("D", "T", inlet["T"], "P", inlet["p"], _fluid(inlet))
    return None if v is None else inlet["m"] * v


def _pressure_ratio(component):
    inlet, outlets = _inlet(component), _material(getattr(component, "outl", {}))
    try:
        ratio = outlets[0]["p"] / inlet["p"]
    except (IndexError, KeyError, TypeError, ZeroDivisionError):
        return None
    return max(ratio, 1 / ratio) if ratio > 0 else None


# ----------------------------------------------------------------------------------------------
# Heat exchangers
# ----------------------------------------------------------------------------------------------


def _sides(component):
    """The hot and the cold stream pair of a heat exchanger, each as ``(inlet, outlet)``, or ``None``."""
    inl, outl = getattr(component, "inl", {}), getattr(component, "outl", {})
    pairs = sorted((idx, inl[idx], outl[idx]) for idx in inl if idx in outl)[:2]
    if len(pairs) < 2:
        return None
    try:
        hot, cold = sorted(pairs, key=lambda pair: pair[1]["T"], reverse=True)
        return (hot[1], hot[2]), (cold[1], cold[2])
    except (KeyError, TypeError):
        return None


def _phase_change(inlet, outlet):
    """Whether a stream changes phase between its inlet and its outlet."""
    x_in, x_out = inlet.get("x"), outlet.get("x")
    known = x_in is not None and x_out is not None and not (math.isnan(x_in) or math.isnan(x_out))
    if known and (abs(x_in - x_out) > 1e-3 or 0 < x_in < 1 or 0 < x_out < 1):
        return True
    try:
        return abs(inlet["T"] - outlet["T"]) < 0.5 and abs(inlet["h"] - outlet["h"]) > 1e3
    except (KeyError, TypeError):
        return False


def _simulated_kA(component):
    kA = getattr(component, "kA", None)
    if kA is None:
        kA = (getattr(component, "parameters", None) or {}).get("kA")
    try:
        kA = float(kA)
    except (TypeError, ValueError):
        return None
    return kA if kA > 0 and not math.isnan(kA) else None


def heat_exchanger(component):
    """
    Duty, temperature difference and heat transfer capacity of a heat exchanger with two streams.

    Returns
    -------
    dict or None
        ``Q`` is the heat flow in W; ``dT_lm`` the logarithmic mean temperature difference of the
        counter-flow arrangement in K, ``None`` on a temperature cross; ``kA`` the heat transfer
        capacity in W/K, taken from the simulation where the model carries it and from
        :math:`\\dot{Q} / \\Delta T_\\mathrm{lm}` otherwise, with ``kA_source`` saying which;
        ``phase_change`` lists the sides, ``"hot"`` and ``"cold"``, on which a stream changes phase.
        ``None`` when the component does not have two streams in and out.
    """
    sides = _sides(component)
    if sides is None:
        return None
    (hot_in, hot_out), (cold_in, cold_out) = sides
    try:
        Q = hot_in["m"] * (hot_in["h"] - hot_out["h"])
        dT_1 = hot_in["T"] - cold_out["T"]
        dT_2 = hot_out["T"] - cold_in["T"]
    except (KeyError, TypeError):
        return None
    if Q <= 0:
        return None
    dT_lm = None
    if dT_1 > 0 and dT_2 > 0:
        dT_lm = dT_1 if math.isclose(dT_1, dT_2, rel_tol=1e-9) else (dT_1 - dT_2) / math.log(dT_1 / dT_2)
    phases = [side for side, pair in (("hot", sides[0]), ("cold", sides[1])) if _phase_change(*pair)]

    kA, source = _simulated_kA(component), "simulation"
    if kA is not None and dT_lm:
        # An export may state the capacity in kW/K; the heat flow tells which it is.
        kA = min((kA, kA * 1e3), key=lambda value: abs(math.log(value / (Q / dT_lm))))
    if kA is None and dT_lm:
        kA, source = Q / dT_lm, "Q/dT_lm"
    if kA is None:
        source = None
    return {"Q": Q, "dT_lm": dT_lm, "kA": kA, "kA_source": source, "phase_change": phases}


def _fluid(conn):
    """The CoolProp name of a stream of one species, or ``None`` for a mixture or an unknown fluid."""
    composition = conn.get("mass_composition") or {}
    species = [(x, name) for name, x in composition.items() if x and x > 0.005]
    if len(species) != 1 or species[0][0] < 0.995:
        return None
    name = species[0][1].strip()
    if name.lower() in WATER_NAMES or name.lower() in ("water", "h2o"):
        return "Water"
    try:
        CP.PropsSI("M", name)
    except ValueError:
        return None
    return name


# Names of the species of a fluid group of :data:`U_CELLS`, as the exports and CoolProp spell them, and
# parts of the names of the incompressible fluids.
_GROUP_NAMES = {
    "water/steam": {"WATER", "H2O", "R718", *(name.upper() for name in WATER_NAMES)},
    "ammonia": {"AMMONIA", "NH3", "R717"},
    "CO2": {"CO2", "CARBONDIOXIDE", "R744"},
    "hydrogen": {"HYDROGEN", "H2", "PARAHYDROGEN", "ORTHOHYDROGEN"},
    "natural gas": {"METHANE", "CH4", "R50"},
    "hydrocarbon refrigerants": {
        "ETHANE",
        "C2H6",
        "R170",
        "PROPANE",
        "C3H8",
        "R290",
        "PROPYLENE",
        "PROPENE",
        "C3H6",
        "R1270",
        "BUTANE",
        "N-BUTANE",
        "NBUTANE",
        "C4H10",
        "R600",
        "ISOBUTANE",
        "IBUTANE",
        "R600A",
        "PENTANE",
        "N-PENTANE",
        "NPENTANE",
        "R601",
        "ISOPENTANE",
        "IPENTANE",
        "R601A",
        "CYCLOPENTANE",
        "HEXANE",
        "N-HEXANE",
        "NHEXANE",
    },
    "siloxanes": {"MM", "MDM", "MD2M", "MD3M", "MD4M", "D4", "D5", "D6", "HEXAMETHYLDISILOXANE"},
    "toluene/aromatics": {"TOLUENE", "BENZENE", "ETHYLBENZENE", "M-XYLENE", "O-XYLENE", "P-XYLENE"},
}
_GROUP_PARTS = {
    "thermal oil": ("THERMINOL", "DOWTHERM", "SYLTHERM", "TVP1", "THERMAL OIL", "THERMALOIL"),
    "molten salt": ("SALT", "NITRATE", "HITEC", "KNO3"),
    "glycol/brine": ("GLYCOL", "BRINE", "MEG", "MPG", "CACL2", "NACL"),
}


def fluid_group(conn):
    """
    The fluid group of :data:`U_CELLS` a stream belongs to, from its mass composition.

    A stream of one species is placed by its name: water/steam, ammonia, CO2, hydrogen, natural gas
    (methane), hydrocarbon refrigerants, siloxanes, toluene/aromatics, HFC/HFO (the other
    refrigerants named R...), thermal oil, molten salt or glycol/brine. A mixture of ammonia and
    water is an absorption mixture, one of nitrogen and oxygen is air, one that also carries carbon
    dioxide from combustion is flue gas, and one of mostly methane is natural gas.

    Returns
    -------
    str or None
        The group, or ``None`` for a stream no group describes.
    """
    composition = {}
    raw = conn.get("mass_composition") or {}
    # EBSILON states the gaseous part of the water again as H2OG, next to the total as H2O.
    duplicate = "H2OG" if any(str(name).split("::")[-1].strip().upper() == "H2O" for name in raw) else None
    for name, x in raw.items():
        species = str(name).split("::")[-1].strip().upper()
        if x and x > 0.005 and species != duplicate:
            species = "H2O" if species == "H2OG" else species
            composition[species] = composition.get(species, 0.0) + x
    if len(composition) == 1:
        (name,) = composition
        for group, names in _GROUP_NAMES.items():
            if name in names:
                return group
        for group, parts in _GROUP_PARTS.items():
            if any(part in name for part in parts):
                return group
        return "HFC/HFO" if re.fullmatch(r"R\d{2,4}[A-Z]*(\([EZ]\))?", name) else None
    total = sum(composition.values())
    if not total:
        return None

    def share(*names):
        return sum(composition.get(name, 0.0) for name in names) / total

    ammonia, water = ("NH3", "AMMONIA", "R717"), ("H2O", "WATER", "R718")
    if share(*ammonia, *water) >= 0.99 and share(*ammonia) > 0 and share(*water) > 0:
        return "ammonia-water (absorption)"
    if share("CH4", "METHANE") >= 0.7:
        return "natural gas"
    gas = ("N2", "NITROGEN", "O2", "OXYGEN", "AR", "ARGON", "CO2", "CARBONDIOXIDE", "H2O", "WATER")
    if share(*gas) >= 0.99 and share("N2", "NITROGEN") >= 0.5:
        return "flue gas" if share("CO2", "CARBONDIOXIDE") >= 0.01 else "air"
    return None


def _specific_volume(conn):
    """Specific volume in m³/kg from the volume flow of the export (``v`` of TESPy and Aspen, ``VM`` of EBSILON)."""
    flow = conn.get("v")
    flow = conn.get("VM") if flow is None else flow
    return flow / conn["m"] if flow is not None and conn.get("m") else None


_GAS_GROUPS = ("air", "flue gas", "natural gas", "hydrogen")
_LIQUID_GROUPS = ("thermal oil", "molten salt", "glycol/brine")


def _single_phase(conn):
    """Gas or liquid for a stream not followed through CoolProp: by its specific volume, else by its fluid group."""
    v = _specific_volume(conn)
    if v is not None:
        return GAS if v > 0.01 else LIQUID
    group = fluid_group(conn)
    if group in _GAS_GROUPS:
        return GAS
    if group in _LIQUID_GROUPS:
        return LIQUID
    raise ValueError(f"the phase of stream '{conn.get('name')}' is unknown: the export has no volume flow")


class _Side:
    """One stream of a heat exchanger along the heat transferred, with its phases."""

    def __init__(self, inlet, outlet, Q, hot):
        self.m = inlet["m"]
        self.hot = hot
        self.T_in, self.T_out = inlet["T"], outlet["T"]
        self.p = 0.5 * (inlet["p"] + outlet["p"])
        self.fluid = _fluid(inlet)
        self.supercritical = False
        if self.fluid is not None:
            with contextlib.suppress(ValueError):
                self.supercritical = self.p >= CP.PropsSI("Pcrit", self.fluid)
        self.h_L = self.h_V = None
        if self.fluid is not None:
            try:
                self.h_L = CP.PropsSI("H", "P", self.p, "Q", 0, self.fluid)
                self.h_V = CP.PropsSI("H", "P", self.p, "Q", 1, self.fluid)
            except ValueError:
                self.fluid, self.h_L, self.h_V = self.fluid, None, None
        # Enthalpy in the frame of CoolProp at the end where the hot stream enters (Q = 0), where
        # a counter-flow cold stream leaves; both enthalpies fall along Q.
        self.slope = -1.0 / self.m
        self.h0 = None
        if self.fluid is not None:
            h_in, h_out = self._coolprop_enthalpies(inlet, outlet)
            self.h0 = h_in if hot else h_out
        self.Q = Q
        self.single_phase = None if self.h0 is not None else _single_phase(inlet)

    def _coolprop_enthalpies(self, inlet, outlet):
        """Inlet and outlet enthalpy in the frame of CoolProp; a saturated end follows the other through the stream."""
        values = []
        for conn in (inlet, outlet):
            x = conn.get("x")
            h = None
            if x is not None and not math.isnan(x) and 0 < x < 1:
                h = CP.PropsSI("H", "P", self.p, "Q", x, self.fluid)
            else:
                try:
                    T_sat = CP.PropsSI("T", "P", self.p, "Q", 0, self.fluid)
                except ValueError:
                    T_sat = None
                if T_sat is None or abs(conn["T"] - T_sat) > 0.05:
                    h = CP.PropsSI("H", "P", self.p, "T", conn["T"], self.fluid)
                elif x is not None and not math.isnan(x):
                    h = CP.PropsSI("H", "P", self.p, "Q", x, self.fluid)
            values.append(h)
        h_in, h_out = values
        if h_in is None and h_out is None:
            # Both ends are saturated and their quality is unknown, so the stream stays inside the
            # dome. The enthalpies of the export are kept where they lie in it, as with the reference
            # of CoolProp; with another reference the stream is placed at the middle of the dome.
            h_in, h_out = inlet["h"], outlet["h"]
            margin = 0.02 * (self.h_V - self.h_L)
            if not all(self.h_L - margin <= h <= self.h_V + margin for h in (h_in, h_out)):
                dh = h_in - h_out
                if abs(dh) > self.h_V - self.h_L + 2 * margin:
                    raise ValueError("both ends of the stream are saturated and their quality is unknown")
                h_mid = 0.5 * (self.h_L + self.h_V)
                h_in, h_out = h_mid + 0.5 * dh, h_mid - 0.5 * dh
        if h_in is None:
            h_in = h_out + (inlet["h"] - outlet["h"])
        if h_out is None:
            h_out = h_in - (inlet["h"] - outlet["h"])
        return h_in, h_out

    def breakpoints(self):
        """Positions along Q where the stream crosses a saturation line."""
        if self.h0 is None or self.h_L is None:
            return []
        points = []
        for h_sat in (self.h_L, self.h_V):
            Q = (h_sat - self.h0) / self.slope
            if 1e-6 * self.Q < Q < self.Q * (1 - 1e-6):
                points.append(Q)
        return points

    def enthalpy(self, Q):
        return self.h0 + self.slope * Q

    def temperature(self, Q):
        if self.fluid is None or self.h0 is None:
            T_at_zero = self.T_in if self.hot else self.T_out
            T_at_end = self.T_out if self.hot else self.T_in
            return T_at_zero + (T_at_end - T_at_zero) * Q / self.Q
        return CP.PropsSI("T", "P", self.p, "H", self.enthalpy(Q), self.fluid)

    def phase(self, Q):
        if self.fluid is None or self.h0 is None:
            return self.single_phase
        if self.h_L is None:
            return SUPERCRITICAL if self.supercritical else GAS
        h = self.enthalpy(Q)
        if h <= self.h_L:
            return LIQUID
        if h >= self.h_V:
            return GAS
        return TWO_PHASE


def _coefficient(pair, fluids, U, exchanger_type):
    """The coefficient of a section and its cell: given by the user (cell ``None``), the default of its cell, or ``None``."""
    if U is not None and not isinstance(U, dict):
        return float(U), None
    given = {(PHASES.get(hot, hot), PHASES.get(cold, cold)): value for (hot, cold), value in (U or {}).items()}
    if pair in given:
        return float(given[pair]), None
    cell = U_DEFAULTS.get((exchanger_type, *pair, *fluids))
    return None if cell is None else (cell["U"], cell)


def exchanger_type_of(key):
    """The type in :data:`U_DEFAULTS` that a heat exchanger correlation of OpenPyTEA :cite:`Tamarona2026` describes."""
    kind = str(correlation(key)["type"]).lower()
    if "air" in kind:
        return "air_cooled"
    if "pipe" in kind:
        return "double_pipe"
    if "spiral" in kind:
        return "other"
    if "plate & fin" in kind:
        return "plate_fin"
    if "plate" in kind:
        return "plate"
    return "shell_and_tube"


def heat_exchanger_sections(component, U=None, exchanger_type="shell_and_tube"):
    """
    Area of a heat exchanger from its sections, each with the heat transfer coefficient of its phases and fluids.

    The exchanger is taken as counter-flow and cut at every point where one of the streams
    crosses a saturation line, so every section has one phase on each side. A stream of one fluid
    CoolProp knows is followed through its saturation enthalpies, from the temperatures, pressures,
    qualities and enthalpy differences of the export, so the enthalpy reference of the simulator does
    not matter; a mixture or an unknown fluid is taken as single-phase with a temperature linear in
    the heat transferred, as a gas when its specific volume is above 0.01 m³/kg and as a liquid
    otherwise, or by its fluid group where the export has no volume flow.

    Parameters
    ----------
    component : Component
        A heat exchanger with two streams in and two out.
    U : float or dict, optional
        Overall heat transfer coefficient in W/m²K of every section, or per section by its pair of
        phases, the phase of the hot stream first, as ``{("gas", "liquid"): 450.0,
        ("two-phase", "liquid"): 2500.0}``. A section not
        given takes the default of its cell in :data:`U_CELLS`.
    exchanger_type : str, optional
        A key of :data:`EXCHANGER_TYPES`. Default is ``"shell_and_tube"``.

    Returns
    -------
    dict or None
        ``area`` in m², ``Q`` in W and ``sections``, one entry per section with ``Q``, ``dT_lm``,
        ``hot`` and ``cold`` (the phases as words), ``U``, ``U_scope`` (``"user"`` or
        ``"default"``), ``U_cell`` (the cell, ``None`` for a value given by the user), ``U_sources`` (keys
        of :data:`U_SOURCES`), ``U_n_sources`` and ``area``; ``fluids`` holds the groups of the hot
        and the cold stream, see :func:`fluid_group`; ``profile`` lists ``(Q, T_hot, T_cold)``
        points along the exchanger in W and K. ``None`` when the streams do not allow it: a
        temperature cross, a saturated end whose quality is unknown, or a stream state CoolProp does
        not accept.

    Raises
    ------
    ValueError
        If the exchanger type is unknown, or if a section has no comparable cell and ``U`` gives
        none.
    """
    if exchanger_type not in EXCHANGER_TYPES:
        raise ValueError(f"Unknown exchanger type '{exchanger_type}'; one of {list(EXCHANGER_TYPES)}.")
    missing = None
    sides = _sides(component)
    if sides is None:
        return None
    (hot_in, hot_out), (cold_in, cold_out) = sides
    fluids = (fluid_group(hot_in), fluid_group(cold_in))
    try:
        Q = hot_in["m"] * (hot_in["h"] - hot_out["h"])
        if Q <= 0:
            return None
        hot = _Side(hot_in, hot_out, Q, hot=True)
        cold = _Side(cold_in, cold_out, Q, hot=False)
        points = sorted({0.0, Q, *hot.breakpoints(), *cold.breakpoints()})
        profile = []
        for start, end in zip(points, points[1:], strict=False):
            for k in range(5):
                q = start + (end - start) * k / 5
                profile.append((q, hot.temperature(q), cold.temperature(q)))
        profile.append((Q, hot.temperature(Q), cold.temperature(Q)))
        sections = []
        for start, end in zip(points, points[1:], strict=False):
            dT_a = hot.temperature(start) - cold.temperature(start)
            dT_b = hot.temperature(end) - cold.temperature(end)
            if dT_a <= 0 or dT_b <= 0:
                return None
            dT_lm = dT_a if math.isclose(dT_a, dT_b, rel_tol=1e-6) else (dT_a - dT_b) / math.log(dT_a / dT_b)
            middle = 0.5 * (start + end)
            pair = (PHASES[hot.phase(middle)], PHASES[cold.phase(middle)])
            found = _coefficient(pair, fluids, U, exchanger_type)
            if found is None:
                missing = pair
                break
            coefficient, cell = found
            sections.append(
                {
                    "Q": end - start,
                    "dT_lm": dT_lm,
                    "hot": pair[0],
                    "cold": pair[1],
                    "U": coefficient,
                    "U_scope": "user" if cell is None else "default",
                    "U_cell": None if cell is None else cell["cell"],
                    "U_sources": [] if cell is None else list(cell["sources"]),
                    "U_n_sources": None if cell is None else cell["n_sources"],
                    "area": (end - start) / (coefficient * dT_lm),
                }
            )
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    if missing is not None:
        hot_fluid, cold_fluid = (fluid or "an unknown fluid" for fluid in fluids)
        raise ValueError(
            f"{component.name}: no comparable cell for {hot_fluid} ({missing[0]}) to {cold_fluid} ({missing[1]}) in a "
            f"{exchanger_type} exchanger; give it as U={{{missing!r}: value}} in W/m²K."
        )
    for section in sections:
        if section["U_scope"] == "default" and section["U_n_sources"] < 3:
            logger.warning(
                f"{component.name}: the U of the {section['hot']} to {section['cold']} section, "
                f"{section['U']:.0f} W/m²K, rests on {section['U_n_sources']} independent source(s) "
                f"(cell {section['U_cell']}); give the U of the actual exchanger for a design."
            )
    return {
        "area": sum(section["area"] for section in sections),
        "Q": Q,
        "sections": sections,
        "fluids": {"hot": fluids[0], "cold": fluids[1]},
        "profile": profile,
    }


def heat_exchanger_area(component, U=None, exchanger_type="shell_and_tube", method="sections"):
    """
    Area of a heat exchanger, by its sections or by its heat transfer capacity.

    Parameters
    ----------
    component : Component
        A heat exchanger with two streams in and two out.
    U : float or dict, optional
        Overall heat transfer coefficient in W/m²K. The sections take one value or one per pair of
        phases, see :func:`heat_exchanger_sections`; the ``"kA"`` method needs one value,
        :math:`A = kA / U`.
    exchanger_type : str, optional
        A key of :data:`EXCHANGER_TYPES`, for the defaults of the sections.
    method : str, optional
        ``"sections"`` (default), falling back to ``"kA"`` where the sections cannot be formed, or
        ``"kA"``.

    Returns
    -------
    dict or None
        ``area`` in m² (``None`` when ``"kA"`` has no single ``U``), ``method``, ``exchanger_type``,
        ``sections`` (the result of :func:`heat_exchanger_sections`, or ``None``) and ``U``.
        ``None`` when the component does not have two streams in and out.
    """
    design = heat_exchanger(component)
    if design is None:
        return None
    if method == "sections":
        sections = heat_exchanger_sections(component, U=U, exchanger_type=exchanger_type)
        if sections is not None:
            return {
                "area": sections["area"],
                "method": "sections",
                "exchanger_type": exchanger_type,
                "sections": sections,
                "U": U,
            }
    single = U if U and not isinstance(U, dict) else None
    area = design["kA"] / single if single and design["kA"] else None
    return {"area": area, "method": "kA", "exchanger_type": exchanger_type, "sections": None, "U": single}


def size(component, quantity, U=None, exchanger_type="shell_and_tube", method="sections"):
    """
    Read one size of a component from the model, in SI units.

    Parameters
    ----------
    component : Component
        A component of an analysed plant.
    quantity : str
        One of :func:`quantities` of the component, see :data:`QUANTITIES`; the unit is in
        :data:`UNITS`.
    U, exchanger_type, method
        For the area of a heat exchanger, see :func:`heat_exchanger_area`.

    Returns
    -------
    float or None
        The size, or ``None`` when the model does not determine it.

    Raises
    ------
    ValueError
        If the component has no such size, or if a section of a heat exchanger has no coefficient.
    """
    if quantity not in quantities(component):
        raise ValueError(
            f"{component.name} has no size '{quantity}' from the model; it has {list(quantities(component))}."
        )
    if quantity == "power":
        return _power(component)
    if quantity == "mass_flow":
        return _mass_flow(component)
    if quantity == "volume_flow":
        return _volume_flow(component)
    if quantity == "pressure_ratio":
        return _pressure_ratio(component)
    if quantity == "area":
        found = heat_exchanger_area(component, U=U, exchanger_type=exchanger_type, method=method)
        return None if found is None else found["area"]
    if type(component).__name__ == "HeatExchanger":
        design = heat_exchanger(component)
        return None if design is None else design["Q" if quantity == "heat" else quantity]
    return _heat(component)


def sizes(component, U=None, exchanger_type="shell_and_tube", method="sections"):
    """
    Read all sizes the model determines for a component, in SI units.

    A cost function takes the ones it needs, for example ``sizes(compressor)["volume_flow"]``. The
    parameters are those of :func:`size`.

    Returns
    -------
    dict
        ``{quantity: value}`` for every one of :func:`quantities`, ``None`` where the model does
        not determine it; empty for a component the model gives no size for.
    """
    return {
        quantity: size(component, quantity, U=U, exchanger_type=exchanger_type, method=method)
        for quantity in quantities(component)
    }


def convert(value, what, units):
    """
    Express a size given in SI units in the units of a correlation.

    Parameters
    ----------
    value : float
        The size in SI units, see :data:`UNITS`.
    what : str
        A key of :data:`UNITS`.
    units : str
        The ``units`` text of the correlation.

    Returns
    -------
    float or None
        The size in the units of the correlation, or ``None`` when the correlation is based on
        a kind of size other than the one the component provides.
    """
    found = dimension(units)
    if found is None or found[0] != DIMENSIONS.get(what):
        return None
    return value * found[1]


def default_correlation(component):
    """The correlation suggested for a component, or ``None`` when OpenPyTEA :cite:`Tamarona2026` has none that fits."""
    name = type(component).__name__
    if name == "Turbine" and _is_steam(component):
        return STEAM_TURBINE
    return DEFAULTS.get(name)


def _is_steam(component):
    inlets, _ = _streams(component)
    composition = inlets[0].get("mass_composition") if inlets else None
    if not composition:
        return False
    water = sum(x for name, x in composition.items() if name.strip().lower() in ("h2o", "water", *WATER_NAMES))
    return water > 0.99


def fit(row, value):
    """
    Say how a size relates to the range a correlation was fitted over.

    Parameters
    ----------
    row : dict
        A correlation, as :func:`correlation` returns it.
    value : float or None
        The size in the units of the correlation.

    Returns
    -------
    dict
        ``status`` is ``"in range"``, ``"below"``, ``"above"``, ``"unbounded"`` (the correlation
        states no range) or ``"unknown"`` (no size); ``lower`` and ``upper`` are the bounds, and
        ``ratio`` the size over the bound it exceeds.
    """
    lower, upper = row.get("s_lower"), row.get("s_upper")
    lower = None if lower is None or pd.isna(lower) else float(lower)
    upper = None if upper is None or pd.isna(upper) else float(upper)
    result = {"lower": lower, "upper": upper, "ratio": None}
    if value is None:
        return {**result, "status": "unknown"}
    if lower is None and upper is None:
        return {**result, "status": "unbounded"}
    if lower is not None and value < lower:
        return {**result, "status": "below", "ratio": value / lower}
    if upper is not None and value > upper:
        return {**result, "status": "above", "ratio": value / upper}
    return {**result, "status": "in range"}


def purchase_cost(key, value, outside="scale", exponent=EXPONENT):
    """
    Evaluate a correlation of OpenPyTEA :cite:`Tamarona2026`, inside or outside its range.

    Parameters
    ----------
    key : str
        The ``key`` of the correlation.
    value : float
        The size in the units of the correlation.
    outside : str, optional
        What to do with a size outside the range of the correlation. ``"scale"`` (default)
        extrapolates from the nearest bound with the scaling exponent,
        :math:`C = C(S_\\mathrm{b}) \\, (S / S_\\mathrm{b})^{n}`, so the component stays one unit.
        ``"parallel"`` lets OpenPyTEA split a size above the range into identical units; a size
        below the range is then an error.
    exponent : float, optional
        The scaling exponent :math:`n`. Default 0.6.

    Returns
    -------
    dict
        ``PEC`` is the cost in USD of ``reference_year``, the year of the correlation; ``units`` the
        number of parallel units; ``method`` is ``"correlation"``, ``"scaled"`` or ``"parallel"``;
        ``bound`` the bound the cost was scaled from, if any.

    Raises
    ------
    KeyError
        If the key is unknown.
    ValueError
        If the size lies below the range and ``outside`` is ``"parallel"``.
    """
    db = _openpytea().CostCorrelationDB()
    where = fit(correlation(key), float(value))
    if where["status"] in ("below", "above") and outside == "scale":
        bound = where["lower"] if where["status"] == "below" else where["upper"]
        cost, units, year = db.evaluate(key, bound)
        cost = cost / units * (float(value) / bound) ** exponent
        return {
            "PEC": cost,
            "reference_year": year,
            "units": 1,
            "method": "scaled",
            "bound": bound,
            "exponent": exponent,
        }
    cost, units, year = db.evaluate(key, float(value))
    method = "parallel" if units > 1 else "correlation"
    return {"PEC": cost, "reference_year": year, "units": units, "method": method, "bound": None}


def _quantity_of(component, kind):
    """The size of a component that has the dimension of a correlation, or ``None``."""
    found = [quantity for quantity in quantities(component) if DIMENSIONS.get(quantity) == kind]
    return found[0] if found else None


def estimate(
    component, key, U=None, value=None, outside="scale", exponent=EXPONENT, method="sections", exchanger_type=None
):
    """
    Estimate the purchased equipment cost of a component with a correlation of OpenPyTEA :cite:`Tamarona2026`.

    The size is the one of :func:`sizes` that has the dimension of the units of the correlation, a
    power or a heat flow, an area, a volume flow at the inlet or a mass flow, converted into those units.

    Parameters
    ----------
    component : Component
    key : str
        The correlation to use, see :func:`correlations`.
    U : float or dict, optional
        Overall heat transfer coefficient of a heat exchanger in W/m²K, see :func:`heat_exchanger_area`.
    value : float, optional
        The size in the units of the correlation, given by hand when the model does not determine
        it.
    outside, exponent
        See :func:`purchase_cost`.
    method : str, optional
        See :func:`heat_exchanger_area`.
    exchanger_type : str, optional
        A key of :data:`EXCHANGER_TYPES`; by default the one the correlation describes, see
        :func:`exchanger_type_of`.

    Returns
    -------
    dict
        The result of :func:`purchase_cost` together with ``size``, ``size_units``, ``quantity``
        (the size read from the model, ``None`` for one given by hand), ``key``, ``fit`` (see
        :func:`fit`) and ``sizing``, the result of :func:`heat_exchanger_area` for an area.

    Raises
    ------
    ValueError
        If the size is neither given nor derivable, or lies below the range of the correlation
        and parallel units were asked for.
    """
    row = correlation(key)
    units = row["units"]
    read = quantity = None
    if value is None:
        found = dimension(units)
        quantity = None if found is None else _quantity_of(component, found[0])
        if quantity is None:
            raise ValueError(
                f"The correlation '{key}' is based on '{units}', which the model does not give for "
                f"{component.name}; give the size in '{units}' as 'value'."
            )
        if quantity == "area":
            exchanger_type = exchanger_type or exchanger_type_of(key)
            read = heat_exchanger_area(component, U=U, exchanger_type=exchanger_type, method=method)
            si = None if read is None else read["area"]
        else:
            si = size(component, quantity)
        if si is None:
            raise ValueError(
                f"The {quantity} of {component.name} does not follow from the model; give it in '{units}'."
            )
        value = si * found[1]
    result = purchase_cost(key, value, outside=outside, exponent=exponent)
    result.update(
        {
            "size": float(value),
            "size_units": units,
            "quantity": quantity,
            "key": key,
            "fit": fit(row, float(value)),
            "sizing": read,
        }
    )
    return result


# Lower heating values in J/kg of the combustible species the exports name.
HEATING_VALUES = {
    "CH4": 50.0e6,
    "METHANE": 50.0e6,
    "C2H6": 47.5e6,
    "ETHANE": 47.5e6,
    "C3H8": 46.35e6,
    "PROPANE": 46.35e6,
    "C4H10": 45.75e6,
    "BUTANE": 45.75e6,
    "H2": 119.96e6,
    "HYDROGEN": 119.96e6,
    "CO": 10.1e6,
    "H2S": 15.2e6,
    "NH3": 18.6e6,
    "AMMONIA": 18.6e6,
    "CH3OH": 19.9e6,
    "METHANOL": 19.9e6,
}


def heating_value(conn):
    """
    The lower heating value of a stream in J/kg from its mass composition, ``None`` for a stream without fuel.

    Species the table does not name count as inert.
    """
    composition = conn.get("mass_composition") or {}
    value = sum(x * HEATING_VALUES.get(name.strip().upper(), 0.0) for name, x in composition.items() if x)
    return value if value > 0 else None


def energy_flow(conn):
    """
    The energy flow of a stream in W: the one the export states, or the heating value of a fuel stream.

    Returns ``None`` when neither is available.
    """
    if conn.get("energy_flow") is not None:
        return conn["energy_flow"]
    lhv = heating_value(conn)
    if lhv is None or not conn.get("m"):
        return None
    return conn["m"] * lhv


def per_dollar(currency, year):
    """
    How much of a currency one US dollar bought in a year, for the currencies the module knows.

    Parameters
    ----------
    currency : str
        ``"USD"`` or ``"EUR"``; anything else is unknown.
    year : int
        The year of the cost. A year outside the table takes the nearest year in it.

    Returns
    -------
    float or None
        Units of the currency per US dollar, ``None`` for a currency the module does not know.
    """
    code = str(currency or "").strip().upper()
    if code == CURRENCY:
        return 1.0
    if code == "EUR":
        nearest = min(USD_PER_EUR, key=lambda y: abs(y - int(year)))
        return 1.0 / USD_PER_EUR[nearest]
    return None


def cost_index():
    """The plant cost index OpenPyTEA :cite:`Tamarona2026` ships, as ``{year: value}``."""
    df = _openpytea().CEPCI_DF
    return {int(year): float(value) for year, value in df["cepci"].items() if pd.notna(value)}
