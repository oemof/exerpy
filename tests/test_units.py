"""Tests of the unit conversion of the input in exerpy.units."""

import copy
import json
import os

import pytest

from exerpy import EconomicAnalysis
from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis
from exerpy.schema import InputValidationError
from exerpy.units import SI_UNITS
from exerpy.units import add_units
from exerpy.units import convert
from exerpy.units import convert_cost
from exerpy.units import from_SI
from exerpy.units import registry
from exerpy.units import to_SI

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "exergy_analysis", "json_example", "example.json")
CGAM = os.path.join(os.path.dirname(__file__), "..", "examples", "exergoeconomic_analysis", "cgam", "cgam.json")
CGAM_COSTS = {
    "AC_Z": 56.99,
    "CC_Z": 4.40,
    "EXP_Z": 48.16,
    "APH_Z": 12.26,
    "EV_Z": 11.476,
    "PH_Z": 5.454,
    "GEN_Z": 0.0,
    "1_c": 0.0,
    "10_c": 3.8635,
    "8_c": 0.0,
}
FLOWS = {
    "E_F": {"inputs": ["1", "3"], "outputs": []},
    "E_P": {"inputs": ["E1"], "outputs": []},
    "E_L": {"inputs": ["5"], "outputs": []},
}
# Unit and conversion from SI of the values rewritten by in_other_units
OTHER_UNITS = {
    "Tamb": ("degC", lambda v: v - 273.15),
    "pamb": ("bar", lambda v: v / 1e5),
    "T": ("degC", lambda v: v - 273.15),
    "p": ("bar", lambda v: v / 1e5),
    "m": ("t / h", lambda v: v * 3.6),
    "h": ("kJ / kg", lambda v: v / 1e3),
    "s": ("kJ / kgK", lambda v: v / 1e3),
    "e_PH": ("kJ / kg", lambda v: v / 1e3),
    "e_CH": ("kJ / kg", lambda v: v / 1e3),
    "energy_flow": ("MW", lambda v: v / 1e6),
}


@pytest.fixture
def data():
    with open(EXAMPLE) as f:
        return json.load(f)


def in_other_units(data):
    data = copy.deepcopy(data)
    for entry in [data["ambient_conditions"], *data["connections"].values()]:
        for key, (unit, to_unit) in OTHER_UNITS.items():
            if isinstance(entry.get(key), float):
                entry[key] = to_unit(entry[key])
                entry[f"{key}_unit"] = unit
    return data


def analysed(data, path):
    path.write_text(json.dumps(data))
    ean = ExergyAnalysis.from_json(str(path), split_physical_exergy=False)
    ean.analyse(**FLOWS)
    return ean


@pytest.mark.parametrize(
    "value, from_unit, to_unit, expected",
    [
        (15.0, "degC", "K", 288.15),
        (15.0, "°C", "K", 288.15),
        (59.0, "degF", "K", 288.15),
        (1.0, "bar", "Pa", 1e5),
        (3.6, "t / h", "kg / s", 1.0),
        (2.0, "kJ / kgK", "J / kgK", 2000.0),
        (2.0, "kilojoule / kilogram / kelvin", "J / kgK", 2000.0),
        (5.0, "kilowatt", "W", 5000.0),
        (1.0, "kW / K", "W / K", 1000.0),
        (1.0, "l / s", "m3 / s", 1e-3),
        (0.5, "-", "dimensionless", 0.5),
        (50.0, "%", "dimensionless", 0.5),
        (288.15, "K", "degC", 15.0),
        (2e5, "Pa", "bar", 2.0),
        (2000.0, "J / kgK", "kJ / kgK", 2.0),
        (0.5, "dimensionless", "%", 50.0),
        (1.0, "kg / s", "t / h", 3.6),
    ],
)
def test_convert(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize(
    "from_unit, to_unit, message",
    [
        ("K", "blorps", "unknown unit 'blorps'"),
        ("blorps", "K", "unknown unit 'blorps'"),
        ("K", "bar", "unit 'K' cannot be converted to 'bar'"),
        ("bar", "degC", "write 'degC' for degrees Celsius"),
    ],
)
def test_convert_bad_unit(from_unit, to_unit, message):
    with pytest.raises(ValueError, match=message):
        convert(1.0, from_unit, to_unit)


def test_si_units_are_readable():
    for si in SI_UNITS.values():
        registry().Unit(si)
        assert convert(1.0, si, si) == 1.0


def test_values_converted_everywhere():
    data = {
        "ambient_conditions": {"Tamb": 15.0, "Tamb_unit": "degC", "pamb": 1.013, "pamb_unit": "bar"},
        "connections": {"1": {"T": 100.0, "T_unit": "degree_Celsius", "m": 36.0, "m_unit": "t / h"}},
        "components": {
            "HeatExchanger": {
                "HX": {"name": "HX", "kA": 2.0, "kA_unit": "kW / K", "parameters": {"Q": 3.0, "Q_unit": "MW"}}
            }
        },
    }
    converted, problems = to_SI(data)
    assert problems == []
    assert converted["ambient_conditions"]["Tamb"] == pytest.approx(288.15)
    assert converted["ambient_conditions"]["pamb"] == pytest.approx(101300.0)
    assert converted["connections"]["1"]["T"] == pytest.approx(373.15)
    assert converted["connections"]["1"]["m"] == pytest.approx(10.0)
    assert converted["components"]["HeatExchanger"]["HX"]["kA"] == pytest.approx(2000.0)
    assert converted["components"]["HeatExchanger"]["HX"]["parameters"]["Q"] == pytest.approx(3e6)
    assert converted["connections"]["1"]["T_unit"] == "K"
    assert converted["components"]["HeatExchanger"]["HX"]["parameters"]["Q_unit"] == "W"
    assert data["connections"]["1"]["T"] == 100.0  # the input is left as it is


def test_value_without_unit_is_SI():
    converted, problems = to_SI({"connections": {"1": {"T": 300.0, "p": None}}})
    assert problems == []
    assert converted["connections"]["1"] == {"T": 300.0, "T_unit": "K", "p": None, "p_unit": "Pa"}


def test_keys_exerpy_does_not_read_keep_their_unit():
    data = {"components": {"Pump": {"P1": {"name": "P1", "parameters": {"dp": 0.5, "dp_unit": "bar"}}}}}
    converted, _ = to_SI(data)
    assert converted["components"]["Pump"]["P1"]["parameters"] == {"dp": 0.5, "dp_unit": "bar"}


@pytest.mark.parametrize(
    "unit, fragment",
    [
        ("Pa", "unit 'Pa' cannot be converted to 'K'"),
        ("C", "write 'degC' for degrees Celsius"),
        ("deg C", "write 'degC' for degrees Celsius"),
        ("blorps", "unknown unit 'blorps'"),
    ],
)
def test_bad_unit(data, unit, fragment):
    data["connections"]["1"]["T_unit"] = unit
    _, problems = to_SI(data)
    assert len(problems) == 1
    assert problems[0][0] == "$.connections['1'].T_unit"
    assert fragment in problems[0][1]


def test_all_bad_units_reported_together(data):
    data["ambient_conditions"]["Tamb_unit"] = "bar"
    data["connections"]["1"]["m_unit"] = "kg"
    data["connections"]["2"]["p_unit"] = 5
    _, problems = to_SI(data)
    assert {path for path, _ in problems} == {
        "$.ambient_conditions.Tamb_unit",
        "$.connections['1'].m_unit",
        "$.connections['2'].p_unit",
    }


def test_temperature_below_zero_celsius(tmp_path, data):
    """The analysis converts before it validates, so the bound T > 0 holds in K."""
    data["connections"]["1"].update({"T": -10.0, "T_unit": "degC"})
    path = tmp_path / "cold.json"
    path.write_text(json.dumps(data))
    ean = ExergyAnalysis.from_json(str(path), split_physical_exergy=False)
    assert ean.connections["1"]["T"] == pytest.approx(263.15)


def test_bad_unit_raises_without_validation(tmp_path, data):
    data["connections"]["1"]["p_unit"] = "K"
    path = tmp_path / "bad_unit.json"
    path.write_text(json.dumps(data))
    with pytest.raises(InputValidationError, match=r"\$\.connections\['1'\]\.p_unit"):
        ExergyAnalysis.from_json(str(path), validate=False)


def test_results_do_not_depend_on_units(tmp_path, data):
    si = analysed(data, tmp_path / "si.json")
    other = analysed(in_other_units(data), tmp_path / "other.json")
    assert other.Tamb == pytest.approx(si.Tamb)
    assert pytest.approx(si.E_F, rel=1e-9) == other.E_F
    assert pytest.approx(si.E_D, rel=1e-9) == other.E_D
    assert other.epsilon == pytest.approx(si.epsilon, rel=1e-9)
    for name, comp in si.components.items():
        assert pytest.approx(comp.E_D, rel=1e-9, abs=1e-6) == other.components[name].E_D


def test_export_is_in_SI(tmp_path, data):
    ean = analysed(in_other_units(data), tmp_path / "other.json")
    ean.export_to_json(str(tmp_path / "export.json"))
    exported = json.loads((tmp_path / "export.json").read_text())
    assert exported["ambient_conditions"]["Tamb"] == pytest.approx(288.15)
    assert exported["ambient_conditions"]["Tamb_unit"] == "K"
    conn = exported["connections"]["1"]
    assert conn["p"] == pytest.approx(data["connections"]["1"]["p"])
    assert (conn["p_unit"], conn["m_unit"], conn["s_unit"]) == ("Pa", "kg / s", "J / kgK")


def test_export_has_a_unit_for_every_value(tmp_path, data, values_without_unit):
    ean = analysed(data, tmp_path / "si.json")
    ean.export_to_json(str(tmp_path / "export.json"))
    exported = json.loads((tmp_path / "export.json").read_text())
    assert values_without_unit(exported) == []
    assert exported["components"]["Turbine"]["GT"]["exergy_results"]["epsilon_unit"] == "dimensionless"
    assert exported["system_results"]["E_D_unit"] == "W"
    assert exported["connections"]["1"]["E_PH_unit"] == "W"


def test_add_units_keeps_given_units():
    data = {"connections": {"1": {"T": 300.0, "p": 1.0, "p_unit": "bar", "label": 3}}}
    assert add_units(data)["connections"]["1"] == {"T": 300.0, "T_unit": "K", "p": 1.0, "p_unit": "bar", "label": 3}


def test_from_SI():
    data = {
        "ambient_conditions": {"Tamb": 288.15},
        "connections": {"1": {"T": 373.15, "p": 2e5, "m": 1.0}},
        "components": {"Turbine": {"GT": {"name": "GT", "exergy_results": {"E_D": 2e6, "E_P": None}}}},
        "system_results": {"E_D": 5e6},
    }
    converted = from_SI(data, {"T": "degC", "Tamb": "degC", "p": "bar", "E_D": "MW", "E_P": "MW"})
    assert converted["ambient_conditions"] == {"Tamb": pytest.approx(15.0), "Tamb_unit": "degC"}
    conn = converted["connections"]["1"]
    assert (conn["T"], conn["T_unit"], conn["p"], conn["p_unit"]) == (pytest.approx(100.0), "degC", 2.0, "bar")
    assert (conn["m"], conn["m_unit"]) == (1.0, "kg / s")
    results = converted["components"]["Turbine"]["GT"]["exergy_results"]
    assert results == {"E_D": 2.0, "E_D_unit": "MW", "E_P": None, "E_P_unit": "MW"}
    assert converted["system_results"]["E_D"] == 5.0
    assert data["connections"]["1"]["T"] == 373.15  # the input is left as it is


@pytest.mark.parametrize(
    "units, message",
    [({"temperature": "degC"}, "no unit is known for 'temperature'"), ({"T": "bar"}, "unit of 'T': unit 'K' cannot")],
)
def test_from_SI_bad_units(units, message):
    with pytest.raises(ValueError, match=message):
        from_SI({"connections": {}}, units)


def test_export_in_other_units_reads_back(tmp_path, data):
    si = analysed(data, tmp_path / "si.json")
    units = {"T": "degC", "Tamb": "degC", "p": "bar", "m": "t / h", "h": "kJ / kg", "E": "kW", "E_D": "kW"}
    si.export_to_json(str(tmp_path / "export.json"), units=units)
    exported = json.loads((tmp_path / "export.json").read_text())
    conn = exported["connections"]["1"]
    assert conn["T"] == pytest.approx(data["connections"]["1"]["T"] - 273.15)
    assert conn["T_unit"] == "degC"
    assert conn["m_unit"] == "t / h"
    assert exported["system_results"]["E_D"] == pytest.approx(si.E_D / 1e3)
    assert exported["system_results"]["E_D_unit"] == "kW"
    again = ExergyAnalysis.from_json(str(tmp_path / "export.json"))
    again.analyse(**FLOWS)
    assert pytest.approx(si.E_D, rel=1e-9) == again.E_D
    assert again.connections["1"]["T"] == pytest.approx(data["connections"]["1"]["T"])


def cgam_costs(costs):
    ean = ExergyAnalysis.from_json(CGAM)
    ean.analyse(
        E_F={"inputs": ["10", "1", "8"], "outputs": []},
        E_P={"inputs": ["E1", "9"], "outputs": []},
        E_L={"inputs": ["7"], "outputs": []},
    )
    eco = ExergoeconomicAnalysis(ean, currency="USD")
    eco.run(costs)
    return eco


@pytest.mark.parametrize(
    "value, from_unit, to_unit, expected",
    [(36.0, "EUR / MWh", "EUR / GJ", 10.0), (1.0, "kEUR / h", "EUR / h", 1000.0), (1.0, "EUR / s", "EUR / h", 3600.0)],
)
def test_convert_cost(value, from_unit, to_unit, expected):
    assert convert_cost(value, from_unit, to_unit, "EUR") == pytest.approx(expected)


@pytest.mark.parametrize(
    "from_unit, message",
    [
        ("USD / MWh", "cost unit 'USD / MWh' is not in EUR"),
        ("EUR / kg", "unit 'EUR / kg' cannot be converted to 'EUR / GJ'"),
        ("EUR / blorp", "unknown unit 'EUR / blorp'"),
        ("EUR / a", "a cost per year depends on the operating hours"),
    ],
)
def test_convert_cost_bad_unit(from_unit, message):
    with pytest.raises(ValueError, match=message):
        convert_cost(1.0, from_unit, "EUR / GJ", "EUR")


def test_cost_units_in_run():
    reference = cgam_costs(CGAM_COSTS).system_costs
    costs = dict(CGAM_COSTS, AC_Z=56.99 / 3600, AC_Z_unit="USD / s", **{"10_c": 3.8635 * 3.6, "10_c_unit": "USD / MWh"})
    converted = cgam_costs(costs).system_costs
    for key, value in reference.items():
        assert pytest.approx(value, rel=1e-12) == converted[key]


@pytest.mark.parametrize(
    "unit_key, unit, message",
    [
        ("10_c_unit", "EUR / MWh", "'10_c_unit': cost unit 'EUR / MWh' is not in USD"),
        ("AC_Z_unit", "USD / a", "per year"),
    ],
)
def test_bad_cost_unit_in_run(unit_key, unit, message):
    with pytest.raises(ValueError, match=message):
        cgam_costs(dict(CGAM_COSTS, **{unit_key: unit}))


def test_fuel_cost_unit_in_economic_analysis():
    assumptions = {"PEC": {"AC": 1e5}, "i_eff": 0.1, "n": 20, "tau": 8000, "f_tci": 1.0, "omc_share": 0.01}
    economic = EconomicAnalysis(**assumptions, fuel_costs={"10": {"c": 108.0, "c_unit": "EUR / MWh"}})
    assert economic.fuel_costs["10"] == {"c": pytest.approx(30.0)}
    with pytest.raises(ValueError, match="stream '10'.*not in EUR"):
        EconomicAnalysis(**assumptions, fuel_costs={"10": {"c": 108.0, "c_unit": "USD / MWh"}})


def test_exergoeconomic_export(tmp_path, values_without_unit):
    eco = cgam_costs(CGAM_COSTS)
    eco.export_to_json(str(tmp_path / "costs.json"), units={"E_D": "kW"})
    exported = json.loads((tmp_path / "costs.json").read_text())
    assert values_without_unit(exported) == []
    assert not any("CostVar_index" in conn for conn in exported["connections"].values())
    conn = exported["connections"]["10"]
    assert (conn["c_TOT"], conn["c_TOT_unit"], conn["C_TOT_unit"]) == (pytest.approx(3.8635), "USD / GJ", "USD / h")
    compressor = exported["components"]["Compressor"]["AC"]["exergoeconomic_results"]
    assert (compressor["Z"], compressor["Z_unit"], compressor["f_unit"]) == (
        pytest.approx(56.99),
        "USD / h",
        "dimensionless",
    )
    assert exported["components"]["Compressor"]["AC"]["exergy_results"]["E_D_unit"] == "kW"
    assert exported["system_costs"]["Z"] == pytest.approx(eco.system_costs["Z"])
    assert exported["system_costs"]["Z_unit"] == "USD / h"


def test_exergy_export_leaves_out_the_costs(tmp_path):
    eco = cgam_costs(CGAM_COSTS)
    eco.exergy_analysis.export_to_json(str(tmp_path / "exergy.json"))
    exported = json.loads((tmp_path / "exergy.json").read_text())
    assert not any(
        key in conn for conn in exported["connections"].values() for key in ("CostVar_index", "C_TOT", "c_T")
    )
