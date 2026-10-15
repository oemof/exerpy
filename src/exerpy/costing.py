"""
Purchase equipment costs of the components from the cost correlations of OpenPyTEA.

`OpenPyTEA <https://github.com/pbtamarona/OpenPyTEA>`__ collects published cost correlations of
process equipment, most of them a function of one size, each with the year its cost refers to and
the range of sizes it was fitted on. This module reads the size of a component from the model,
converts it to the units of a correlation, says how the size relates to the range of the
correlation and returns the purchase equipment cost at the correlation's year. That cost and that
year are what :class:`~exerpy.analyses.EconomicAnalysis` takes per component; the escalation to
the reference year stays with the plant cost index of the analysis.

The correlations come from the process-industry literature (Turton et al., Towler and Sinnott,
Seider et al., Perry's handbook, Ulrich). They cover pumps up to a few hundred kW, compressors up
to about 30 MW, steam turbines and gas expanders up to about 20 MW, heat exchangers up to about
1000 m², motors up to a few MW, fired heaters and boilers up to about 100 MW of duty, and vessels
and tanks by their volume. Large power plant equipment, a gas turbine of several hundred MW for
instance, lies outside every range; so do the smallest auxiliaries. A size outside the range is
reported as such, and the cost is then either extrapolated from the nearest bound with a scaling
exponent, split into parallel units as OpenPyTEA does, or replaced by a value of the user.

The area of a heat exchanger follows from its streams in two ways. Where both fluids are known to
CoolProp, the exchanger is cut into sections at every phase change of either stream, each section
gets the overall heat transfer coefficient of its pair of phases from :data:`U_PHASE` and the area
is the sum of :math:`\\dot{Q}_i / (U_i \\, \\Delta T_{\\mathrm{lm},i})`. Otherwise the area is
:math:`kA / U` with the heat transfer capacity of the simulation, or of
:math:`\\dot{Q} / \\Delta T_\\mathrm{lm}` when the model carries none, and one coefficient.

OpenPyTEA is an optional dependency, ``pip install exerpy[costs]`` or ``pip install openpytea``. Its
costs are in US dollars.
"""

import math
import re

import CoolProp.CoolProp as CP
import pandas as pd

HP = 745.69987  # W
FT2 = 0.09290304  # m^2
BTU_PER_HOUR = 0.29307107  # W
GALLON = 0.003785411784  # m^3
FT3 = 0.028316846592  # m^3

EXPONENT = 0.66

LIQUID, TWO_PHASE, GAS = 0, 1, 2
PHASES = {LIQUID: "liquid", TWO_PHASE: "two-phase", GAS: "gas"}
PHASES_INDEX = {name: index for index, name in PHASES.items()}

# Overall heat transfer coefficients in W/m²K by the phases of the hot and the cold stream. The
# pairs with a liquid on one side are the values of Ommen et al. (2015) for a heat pump; the others
# are assumptions in the same spirit.
U_PHASE = {
    (LIQUID, LIQUID): 1494.0,
    (LIQUID, TWO_PHASE): 1483.0,
    (LIQUID, GAS): 380.0,
    (TWO_PHASE, LIQUID): 3696.0,
    (TWO_PHASE, TWO_PHASE): 2500.0,
    (TWO_PHASE, GAS): 1000.0,
    (GAS, LIQUID): 466.0,
    (GAS, TWO_PHASE): 750.0,
    (GAS, GAS): 35.0,
}

# The size a component class is costed by. A combustion chamber, a valve, a mixer and the solar
# components have none the streams determine.
QUANTITIES = {
    "Compressor": "power",
    "Pump": "power",
    "Turbine": "power",
    "Generator": "power",
    "Motor": "power",
    "HeatExchanger": "area",
    "SimpleHeatExchanger": "duty",
    "SteamGenerator": "duty",
    "Drum": "volume",
    "Deaerator": "volume",
    "FlashTank": "volume",
    "Storage": "volume",
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

UNITS = {"power": "kW", "duty": "kW", "area": "m²", "volume": "m³"}
DIMENSIONS = {"power": "rate", "duty": "rate", "area": "area", "volume": "volume"}

CURRENCY = "USD"

# Annual averages of the euro reference rate of the European Central Bank, in USD per EUR. The
# years before the euro carry the average of its predecessor, the ECU, which the Perry (1996) and
# ESDU (1997) correlations need. 2025 is the average of the year as it closed.
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
    """Whether OpenPyTEA is installed."""
    try:
        import openpytea  # noqa: F401
    except ImportError:
        return False
    return True


def _openpytea():
    try:
        from openpytea import equipment
    except ImportError:
        raise ImportError("Estimating purchase equipment costs needs OpenPyTEA: pip install openpytea") from None
    return equipment


def correlations(component_class=None):
    """
    Return the cost correlations of OpenPyTEA, or the ones that cost a class of component.

    Parameters
    ----------
    component_class : str, optional
        Name of a component class, e.g. ``"Compressor"``. Without it every correlation is returned.

    Returns
    -------
    pandas.DataFrame
        Columns ``key``, ``category``, ``type``, ``units``, ``s_lower``, ``s_upper``,
        ``cost_year``, ``material``, ``source`` and ``remarks``, one row per correlation. The
        correlations whose size cannot be derived from the units they state are included; they
        take a size given by hand.
    """
    df = _openpytea().COST_DB_DF.copy()
    df.columns = [column.strip().lower() for column in df.columns]
    df = df.rename(columns={"default material": "material"})
    if component_class is not None:
        wanted = [category.lower() for category in CATEGORIES.get(component_class, [])]
        df = df[df["category"].str.lower().isin(wanted)]
    columns = ["key", "category", "type", "units", "s_lower", "s_upper", "cost_year", "material", "source", "remarks"]
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
        ``(dimension, factor)`` with the dimension ``"rate"``, ``"area"`` or ``"volume"`` and the
        factor that turns the SI value (W, m², m³) into the units of the correlation. ``None``
        when the units are none of these: a mass flow, a volume flow, a shell mass.
    """
    text = str(units or "")
    # A unit followed by "/" is a flow, not a size.
    rules = [
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


def quantity(component):
    """The size a component is costed by, ``"power"``, ``"duty"``, ``"area"`` or ``"volume"``, or ``None``."""
    return QUANTITIES.get(type(component).__name__)


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


def _duty(component):
    inlets, outlets = _streams(component)
    if not inlets or not outlets:
        return None
    try:
        absorbed = sum(c["m"] * c["h"] for c in outlets) - sum(c["m"] * c["h"] for c in inlets)
    except (KeyError, TypeError):
        return None
    return abs(absorbed)


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
        ``Q`` is the duty in W; ``dT_lm`` the logarithmic mean temperature difference of the
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
        # An export may state the capacity in kW/K; the duty tells which it is.
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


def _specific_volume(conn):
    v = conn.get("v")
    if v is None and conn.get("VM") is not None and conn.get("m"):
        v = conn["VM"] / conn["m"]
    return v


class _Side:
    """One stream of a heat exchanger along the heat transferred, with its phases."""

    def __init__(self, inlet, outlet, Q, hot):
        self.m = inlet["m"]
        self.hot = hot
        self.T_in, self.T_out = inlet["T"], outlet["T"]
        self.p = 0.5 * (inlet["p"] + outlet["p"])
        self.fluid = _fluid(inlet)
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
        v = _specific_volume(inlet)
        self.single_phase = GAS if v is not None and v > 0.01 else LIQUID

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
            # Without a quality, the enthalpies of the export are taken as CoolProp's own, which
            # holds for a TESPy model; the saturation dome bounds them.
            h_in, h_out = inlet["h"], outlet["h"]
            margin = 0.02 * (self.h_V - self.h_L)
            if not all(self.h_L - margin <= h <= self.h_V + margin for h in (h_in, h_out)):
                raise ValueError("both ends of the stream are saturated and their quality is unknown")
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
            return GAS
        h = self.enthalpy(Q)
        if h <= self.h_L:
            return LIQUID
        if h >= self.h_V:
            return GAS
        return TWO_PHASE


def heat_exchanger_sections(component, U=None):
    """
    Area of a heat exchanger from its sections, each with the heat transfer coefficient of its phases.

    The exchanger is taken as counter-flow and cut at every point where one of the streams
    crosses a saturation line, so every section has one phase on each side. A stream of one fluid
    CoolProp knows is followed through its saturation enthalpies; a mixture or an unknown fluid is
    taken as single-phase with a temperature linear in the heat transferred, as a gas when its
    specific volume is above 0.01 m³/kg and as a liquid otherwise.

    Parameters
    ----------
    component : Component
        A heat exchanger with two streams in and two out.
    U : dict, optional
        Heat transfer coefficients in W/m²K by pair of phases, as :data:`U_PHASE`, which is the
        default.

    Returns
    -------
    dict or None
        ``area`` in m², ``Q`` in W and ``sections``, one entry per section with ``Q``, ``dT_lm``,
        ``hot`` and ``cold`` (the phases as words), ``U`` and ``area``; ``profile`` lists
        ``(Q, T_hot, T_cold)`` points along the exchanger in W and K. ``None`` when the streams
        do not allow it: a temperature cross, a saturated end whose quality is unknown, a stream
        state CoolProp does not accept.
    """
    U = U or U_PHASE
    sides = _sides(component)
    if sides is None:
        return None
    (hot_in, hot_out), (cold_in, cold_out) = sides
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
            pair = (hot.phase(middle), cold.phase(middle))
            coefficient = U[pair]
            sections.append(
                {
                    "Q": end - start,
                    "dT_lm": dT_lm,
                    "hot": PHASES[pair[0]],
                    "cold": PHASES[pair[1]],
                    "U": coefficient,
                    "area": (end - start) / (coefficient * dT_lm),
                }
            )
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    return {"area": sum(section["area"] for section in sections), "Q": Q, "sections": sections, "profile": profile}


def size(component, U=None, method="sections"):
    """
    Read the size of a component from the model.

    Parameters
    ----------
    component : Component
        A component of an analysed plant; the power of a turbomachine and the duty of a heat
        exchanger are known once the exergy balances are.
    U : float, optional
        Overall heat transfer coefficient of a heat exchanger in W/m²K for the ``"kA"`` method,
        :math:`A = kA / U`.
    method : str, optional
        How the area of a heat exchanger is found: ``"sections"`` (default) through
        :func:`heat_exchanger_sections`, falling back to ``"kA"`` where the sections cannot be
        formed, or ``"kA"`` through :func:`heat_exchanger` and ``U``.

    Returns
    -------
    dict or None
        ``{"quantity", "value", "unit", "details"}`` with the value in SI units (W, m², m³). For a
        heat exchanger ``details`` holds the result of :func:`heat_exchanger`, the ``method`` that
        gave the area and, with the sections, their list. ``None`` when the size does not follow
        from the model, as for the volume of a vessel.
    """
    what = quantity(component)
    if what == "power":
        value = _power(component)
        return None if not value else {"quantity": what, "value": value, "unit": "W", "details": {}}
    if what == "duty":
        value = _duty(component)
        return None if not value else {"quantity": what, "value": value, "unit": "W", "details": {}}
    if what == "area":
        design = heat_exchanger(component)
        if design is None:
            return None
        details = dict(design)
        if method == "sections":
            sections = heat_exchanger_sections(component)
            if sections is not None:
                details.update({"method": "sections", "sections": sections["sections"]})
                return {"quantity": what, "value": sections["area"], "unit": "m²", "details": details}
        details["method"] = "kA"
        if design["kA"] is None:
            return None
        if not U:
            return {"quantity": what, "value": None, "unit": "m²", "details": details}
        details["U"] = U
        return {"quantity": what, "value": design["kA"] / U, "unit": "m²", "details": details}
    return None


def convert(value, what, units):
    """
    Express a size given in SI units in the units of a correlation.

    Parameters
    ----------
    value : float
        The size in W, m² or m³.
    what : str
        ``"power"``, ``"duty"``, ``"area"`` or ``"volume"``.
    units : str
        The ``units`` text of the correlation.

    Returns
    -------
    float or None
        The size in the units of the correlation, or ``None`` when the correlation is based on
        another kind of size than the component provides.
    """
    found = dimension(units)
    if found is None or found[0] != DIMENSIONS.get(what):
        return None
    return value * found[1]


def default_correlation(component):
    """The correlation suggested for a component, or ``None`` when OpenPyTEA has none that fits."""
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
    Say how a size relates to the range a correlation was fitted on.

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
    Evaluate a correlation of OpenPyTEA, inside or outside its range.

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
        below the range is an error then.
    exponent : float, optional
        The scaling exponent :math:`n`. Default 0.66.

    Returns
    -------
    dict
        ``PEC`` is the cost in USD at ``cost_year``, the year of the correlation; ``units`` the
        number of parallel units; ``method`` is ``"correlation"``, ``"scaled"`` or ``"parallel"``;
        ``bound`` the bound the cost was scaled from, when it was.

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
        return {"PEC": cost, "cost_year": year, "units": 1, "method": "scaled", "bound": bound, "exponent": exponent}
    cost, units, year = db.evaluate(key, float(value))
    method = "parallel" if units > 1 else "correlation"
    return {"PEC": cost, "cost_year": year, "units": units, "method": method, "bound": None}


def estimate(component, key, U=None, value=None, outside="scale", exponent=EXPONENT, method="sections"):
    """
    Estimate the purchase equipment cost of a component with a correlation of OpenPyTEA.

    Parameters
    ----------
    component : Component
    key : str
        The correlation to use, see :func:`correlations`.
    U : float, optional
        Overall heat transfer coefficient in W/m²K for the area of a heat exchanger by ``kA``.
    value : float, optional
        The size in the units of the correlation, given by hand when the model does not determine
        it or when the correlation is based on another kind of size.
    outside, exponent
        See :func:`purchase_cost`.
    method : str, optional
        See :func:`size`.

    Returns
    -------
    dict
        The result of :func:`purchase_cost` together with ``size``, ``size_units``, ``key`` and
        ``fit`` (see :func:`fit`).

    Raises
    ------
    ValueError
        If the size is neither given nor derivable, or lies below the range of the correlation
        and parallel units were asked for.
    """
    row = correlation(key)
    units = row["units"]
    if value is None:
        read = size(component, U=U, method=method)
        if read is None or read["value"] is None:
            raise ValueError(f"The size of {component.name} does not follow from the model; give it in '{units}'.")
        value = convert(read["value"], read["quantity"], units)
        if value is None:
            raise ValueError(
                f"The correlation '{key}' is based on '{units}', which {component.name} does not provide; "
                f"give the size by hand."
            )
    result = purchase_cost(key, value, outside=outside, exponent=exponent)
    result.update({"size": float(value), "size_units": units, "key": key, "fit": fit(row, float(value))})
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
    """The plant cost index OpenPyTEA ships, as ``{year: value}``."""
    df = _openpytea().CEPCI_DF
    return {int(year): float(value) for year, value in df["cepci"].items() if pd.notna(value)}
