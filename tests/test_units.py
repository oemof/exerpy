"""Tests of the unit conversion of the input in exerpy.units."""

import copy
import json
import os

import pytest

from exerpy import ExergyAnalysis
from exerpy.schema import InputValidationError
from exerpy.schema import check
from exerpy.units import SI_UNITS
from exerpy.units import convert
from exerpy.units import registry
from exerpy.units import to_SI

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "exergy_analysis", "json_example", "example.json")
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
        for key, (unit, from_SI) in OTHER_UNITS.items():
            if isinstance(entry.get(key), float):
                entry[key] = from_SI(entry[key])
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
    _, issues = check(data)
    assert {i.path for i in issues} == {
        "$.ambient_conditions.Tamb_unit",
        "$.connections['1'].m_unit",
        "$.connections['2'].p_unit",
    }


def test_validation_sees_SI_values(data):
    """A temperature below 0 °C is valid, since the schema checks it in K."""
    data["connections"]["1"].update({"T": -10.0, "T_unit": "degC"})
    model, issues = check(data)
    assert model is not None, issues
    assert pytest.approx(263.15) == model.connections["1"].T


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
