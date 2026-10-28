"""Units of the values in ExerPy's input, converted to SI with pint.

A value is stored next to its unit, as ``"T": 15.0, "T_unit": "degC"``. Before an analysis,
every key of :data:`SI_UNITS` is converted to its SI unit, wherever it appears: in the ambient
conditions, in a connection, in a component, its ``parameters`` or its ``exergy_results``, and in
the ``system_results``. A value without a unit is taken as SI. Keys ExerPy does not read keep their
value and unit. An export writes the unit of every value, in SI or in the units asked for.

Units are read by pint, e.g. ``"degC"``, ``"bar"``, ``"kJ / kg"``, ``"t / h"`` or
``"kilogram / second"``; ``"m2"``, ``"m3"``, ``"kgK"`` and ``"-"`` are understood as well.
:func:`convert` converts a value between any two units, :func:`convert_cost` a cost in the currency
of an exergoeconomic analysis.
"""

import copy
import functools
import numbers
import re

import pint

#: SI unit of each key ExerPy reads or writes.
SI_UNITS = {
    # ambient conditions
    "Tamb": "K",
    "pamb": "Pa",
    # streams
    "m": "kg / s",
    "n": "mol / s",
    "T": "K",
    "p": "Pa",
    "h": "J / kg",
    "s": "J / kgK",
    "v": "m3 / s",
    "VM": "m3 / s",
    "x": "dimensionless",
    "e_T": "J / kg",
    "e_M": "J / kg",
    "e_PH": "J / kg",
    "e_CH": "J / kg",
    "E": "W",
    "E_T": "W",
    "E_M": "W",
    "E_PH": "W",
    "E_CH": "W",
    "energy_flow": "W",
    # components
    "Q": "W",
    "P": "W",
    "Q_Solar": "W",
    "QEFF": "W",
    "RQINC": "W",
    "T_hot": "K",
    "T_cold": "K",
    "kA": "W / K",
    "A": "m2",
    "eta_s": "dimensionless",
    "eta_mech": "dimensionless",
    "eta_el": "dimensionless",
    "eta_cc": "dimensionless",
    "lamb": "dimensionless",
    # exergy results
    "E_F": "W",
    "E_P": "W",
    "E_D": "W",
    "E_L": "W",
    "epsilon": "dimensionless",
    "y": "dimensionless",
    "y_star": "dimensionless",
}

_ALIASES = {"-": "dimensionless"}


@functools.cache
def registry():
    """The pint unit registry, created on first use."""
    ureg = pint.UnitRegistry()
    for definition in ("m3 = m ** 3", "m2 = m ** 2", "kgK = kg * K", "molK = mol * K", "currency = [currency]"):
        ureg.define(definition)
    return ureg


@functools.cache
def _conversion(from_unit, to_unit):
    """Factor and offset that convert a value from ``from_unit`` to ``to_unit``."""
    from_unit = _ALIASES.get(from_unit, from_unit)
    to_unit = _ALIASES.get(to_unit, to_unit)
    if from_unit == to_unit:
        return 1.0, 0.0
    ureg = registry()
    for unit in (from_unit, to_unit):
        try:
            ureg.Unit(unit)
        except Exception:
            raise ValueError(f"unknown unit {unit!r}") from None
    try:
        offset = ureg.Quantity(0.0, from_unit).m_as(to_unit)
        # a large power of two keeps the division exact and the offset's round-off small
        probe = 2.0**20
        factor = (ureg.Quantity(probe, from_unit).m_as(to_unit) - offset) / probe
    except pint.DimensionalityError:
        is_temperature = ureg.Unit(to_unit).dimensionality == ureg.Unit("K").dimensionality
        hint = ", write 'degC' for degrees Celsius" if is_temperature else ""
        raise ValueError(f"unit {from_unit!r} cannot be converted to {to_unit!r}{hint}") from None
    return factor, offset


def check_unit(unit, to_unit):
    """Raise ``ValueError`` if ``unit`` is not a string, unknown or not convertible to ``to_unit``."""
    if not isinstance(unit, str):
        raise ValueError(f"unit must be a string, got {unit!r}")
    _conversion(unit, to_unit)


def convert(value, from_unit, to_unit):
    """Convert ``value`` from ``from_unit`` to ``to_unit``; raise ``ValueError`` for a bad unit.

    >>> round(convert(15.0, "degC", "K"), 2), convert(2e5, "Pa", "bar")
    (288.15, 2.0)
    """
    factor, offset = _conversion(from_unit, to_unit)
    return value * factor + offset


def convert_cost(value, from_unit, to_unit, currency):
    """Convert a cost between two units in ``currency``, e.g. from ``"EUR / MWh"`` to ``"EUR / GJ"``.

    Only the part per time or per energy is converted, never one currency into another. A cost per
    day or longer is not converted, since a cost rate per operating hour depends on the operating
    hours.

    >>> convert_cost(36.0, "EUR / MWh", "EUR / GJ", "EUR")
    10.0
    """
    ureg = registry()
    code = re.compile(rf"{re.escape(currency)}(?![A-Za-z])")
    if not code.search(from_unit):
        raise ValueError(f"cost unit {from_unit!r} is not in {currency}, the currency of the analysis")
    from_unit, to_unit = (code.sub("currency", unit) for unit in (from_unit, to_unit))
    try:
        parts = ureg.Quantity(1.0, from_unit).unit_items()
    except Exception:
        raise ValueError(f"unknown unit {from_unit.replace('currency', currency)!r}") from None
    for name, exponent in parts:
        is_time = ureg.Unit(name).dimensionality == ureg.Unit("h").dimensionality
        if exponent < 0 and is_time and ureg.Quantity(1.0, name).m_as("h") >= 24:
            raise ValueError(
                f"a cost per {name} depends on the operating hours; give it per hour, or derive it "
                f"from the annual costs with EconomicAnalysis"
            )
    try:
        return convert(value, from_unit, to_unit)
    except ValueError as exc:
        raise ValueError(str(exc).replace("currency", currency)) from None


def _is_number(value):
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _dicts(section):
    return (
        [(key, value) for key, value in section.items() if isinstance(value, dict)] if isinstance(section, dict) else []
    )


def entries(data):
    """Yield every dictionary of values in a document, with its JSONPath-like path."""
    if isinstance(data.get("ambient_conditions"), dict):
        yield data["ambient_conditions"], "$.ambient_conditions"
    for name, conn in _dicts(data.get("connections")):
        yield conn, f"$.connections[{name!r}]"
    for ctype, instances in _dicts(data.get("components")):
        for name, comp in _dicts(instances):
            path = f"$.components[{ctype!r}][{name!r}]"
            yield comp, path
            for section in ("parameters", "exergy_results", "exergoeconomic_results"):
                if isinstance(comp.get(section), dict):
                    yield comp[section], f"{path}.{section}"
    for section in ("system_results", "system_costs"):
        if isinstance(data.get(section), dict):
            yield data[section], f"$.{section}"


def _convert_entry(entry, path, problems):
    for key, si in SI_UNITS.items():
        if key not in entry:
            continue
        unit = entry.get(f"{key}_unit")
        value = entry[key]
        if unit is not None:
            if not isinstance(unit, str):
                problems.append((f"{path}.{key}_unit", f"unit must be a string, got {unit!r}"))
                continue
            if _is_number(value):
                try:
                    entry[key] = convert(value, unit, si)
                except ValueError as exc:
                    problems.append((f"{path}.{key}_unit", str(exc)))
                    continue
        entry[f"{key}_unit"] = si


def to_SI(data):
    """Return a copy of an input document with the values of :data:`SI_UNITS` in SI units.

    Returns
    -------
    tuple
        The converted document and a list of ``(path, message)`` for every unit that is unknown
        or of the wrong kind.
    """
    problems = []
    if not isinstance(data, dict):
        return data, problems
    data = copy.deepcopy(data)
    for entry, path in entries(data):
        _convert_entry(entry, path, problems)
    return data, problems


def add_units(data):
    """Return a copy of a document in SI units in which every value of :data:`SI_UNITS` has its unit."""
    data = copy.deepcopy(data)
    for entry, _ in entries(data):
        for key, si in SI_UNITS.items():
            if key in entry and entry.get(f"{key}_unit") is None:
                entry[f"{key}_unit"] = si
    return data


def from_SI(data, units):
    """Return a copy of a document in SI units with the keys of ``units`` in the units given.

    Parameters
    ----------
    data : dict
        A document in SI units, as :meth:`exerpy.ExergyAnalysis.export_to_json` writes it.
    units : dict
        Unit of each key, e.g. ``{"T": "degC", "p": "bar", "E_D": "kW"}``; the keys are those of
        :data:`SI_UNITS`.

    Raises
    ------
    ValueError
        If a key has no SI unit, or a unit is unknown or of the wrong kind.
    """
    for key, unit in units.items():
        if key not in SI_UNITS:
            raise ValueError(f"no unit is known for {key!r}; the keys with a unit are {sorted(SI_UNITS)}")
        try:
            _conversion(SI_UNITS[key], unit)
        except ValueError as exc:
            raise ValueError(f"unit of {key!r}: {exc}") from None
    data = add_units(data)
    for entry, _ in entries(data):
        for key, unit in units.items():
            if key in entry:
                if _is_number(entry[key]):
                    entry[key] = convert(entry[key], SI_UNITS[key], unit)
                entry[f"{key}_unit"] = unit
    return data
