"""Tests of the msgspec input schema in exerpy.schema."""

import copy
import glob
import json
import os

import msgspec
import numpy as np
import pytest

from exerpy import ExergyAnalysis
from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.components.heat_exchanger.base import HeatExchanger
from exerpy.schema import ExerpyInput
from exerpy.schema import InputValidationError
from exerpy.schema import MaterialConnection
from exerpy.schema import PowerConnection
from exerpy.schema import check
from exerpy.schema import input_struct
from exerpy.schema import json_schema
from exerpy.schema import validate

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples", "exergy_analysis")
EXAMPLE_FILES = sorted(glob.glob(os.path.join(EXAMPLES, "**", "*.json"), recursive=True))
SIMPLE = os.path.join(EXAMPLES, "json_example", "example.json")


@pytest.fixture
def data():
    with open(SIMPLE) as f:
        return json.load(f)


def errors(data, **kwargs):
    """The (path, message) of every error found in ``data``."""
    model, issues = check(data, **kwargs)
    return [(i.path, i.message) for i in issues if i.severity == "error"]


def warnings(data, **kwargs):
    _, issues = check(data, **kwargs)
    return [(i.path, i.message) for i in issues if i.severity == "warning"]


def assert_error(data, path, fragment, **kwargs):
    found = errors(data, **kwargs)
    assert any(p == path and fragment in m for p, m in found), found


# --- valid input ---------------------------------------------------------------------


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=os.path.basename)
def test_examples_are_valid(path):
    with open(path, "rb") as f:
        model = validate(f.read(), log_warnings=False)
    assert isinstance(model, ExerpyInput)
    assert model.connections


def test_typed_model(data):
    model = validate(data)
    assert isinstance(model.connections["1"], MaterialConnection)
    assert isinstance(model.connections["E1"], PowerConnection)
    assert model.connections["1"].mass_composition["N2"] == pytest.approx(0.7505, abs=1e-4)
    assert model.ambient_conditions.Tamb == 288.15


def test_dict_with_numpy_scalars(data):
    data["connections"]["1"]["m"] = np.float64(10.0)
    data["connections"]["1"]["target_connector"] = np.int64(0)
    assert validate(data).connections["1"].m == 10.0


def test_ambient_override(data):
    del data["ambient_conditions"]["Tamb"]
    assert_error(data, "$.ambient_conditions", "Tamb is required")
    assert not errors(data, Tamb=298.15)


# --- structural errors (msgspec) -----------------------------------------------------


def test_missing_section(data):
    del data["connections"]
    assert_error(data, "$", "missing required field `connections`")


def test_unknown_kind(data):
    data["connections"]["1"]["kind"] = "steam"
    assert_error(data, "$.connections['1'].kind", "Invalid value 'steam'")


def test_wrong_type(data):
    data["connections"]["1"]["m"] = "637.9"
    assert_error(data, "$.connections['1'].m", "Expected `float`, got `str`")


def test_bool_is_not_a_number(data):
    data["connections"]["1"]["m"] = True
    assert_error(data, "$.connections['1'].m", "Expected `float`, got `bool`")


def test_negative_mass_flow(data):
    data["connections"]["1"]["m"] = -1.0
    assert_error(data, "$.connections['1'].m", ">= 0")


def test_material_stream_needs_exergy(data):
    del data["connections"]["1"]["e_PH"]
    assert_error(data, "$.connections['1']", "missing required field `e_PH`")


@pytest.mark.parametrize("field", ["m", "p", "h"])
def test_material_stream_needs_state(data, field):
    del data["connections"]["1"][field]
    assert_error(data, "$.connections['1']", f"missing required field `{field}`")


def test_power_needs_energy_flow(data):
    del data["connections"]["E1"]["energy_flow"]
    assert_error(data, "$.connections['E1']", "missing required field `energy_flow`")


def test_boundary_must_be_explicit(data):
    del data["connections"]["1"]["source_component"]
    assert_error(data, "$.connections['1']", "missing required field `source_component`")


def test_mass_fraction_bounds(data):
    data["connections"]["1"]["mass_composition"]["N2"] = 1.5
    assert_error(data, "$.connections['1'].mass_composition['N2']", "<= 1")


def test_component_input_bounds(data):
    data["components"]["Splitter"] = {"SP": {"name": "SP", "num_branches": 0}}
    assert_error(data, "$.components['Splitter']['SP'].num_branches", "> 0")


def test_fields_exerpy_does_not_read_are_ignored(data):
    """Simulator output that ExerPy never reads is not validated, whatever its value."""
    comp = data["components"]["Turbine"]["GT"]
    comp.update({"eta_s": "not a number", "type_index": [], "P": -1e9, "mul_signs": None})
    conn = data["connections"]["1"]
    conn.update({"s": "n/a", "name": "other", "fluid_type_id": {}, "E": "?"})
    data["system_results"] = "anything"
    assert errors(data) == []
    assert warnings(data) == []


def test_component_fields_are_per_type(data):
    """A component is checked against its own class's Input, not every component's."""
    data["components"]["Turbine"]["GT"]["T_hot"] = "hot"  # Turbine does not read T_hot
    assert errors(data) == []
    data["components"]["SimpleHeatExchanger"] = {"SHX": {"name": "SHX", "T_hot": "hot"}}
    assert_error(data, "$.components['SimpleHeatExchanger']['SHX'].T_hot", "Expected `float | null`, got `str`")


def test_input_structs_inherit():
    assert issubclass(HeatExchanger.Input, Component.Input)
    assert input_struct("HeatExchanger") is HeatExchanger.Input
    assert input_struct("Condenser") is HeatExchanger.Input  # deprecated alias
    assert input_struct("Turbine") is Component.Input  # declares no further fields


def test_custom_component_input(data):
    """A registered component's Input is used without changes to the schema module."""

    class Custom(Component):
        class Input(Component.Input, kw_only=True):
            gain: float

    component_registry(Custom)
    try:
        data["components"]["Custom"] = {"X": {"name": "X"}}
        assert_error(data, "$.components['Custom']['X']", "missing required field `gain`")
        data["components"]["Custom"]["X"]["gain"] = 2.0
        assert errors(data) == []
        assert "CustomInput" in json_schema()["$defs"]
    finally:
        del component_registry.items["Custom"]


def test_unknown_chemexlib(data):
    data["settings"] = {"chemExLib": "Szargut"}
    assert_error(data, "$.settings.chemExLib", "Invalid enum value 'Szargut'")


def test_structural_errors_of_all_connections_reported(data):
    data["connections"]["1"]["m"] = -1.0
    data["connections"]["E1"]["energy_flow"] = "lots"
    data["components"]["HeatExchanger"] = {"HX": {"name": "HX", "dissipative": "yes"}}
    paths = {p for p, _ in errors(data)}
    assert paths == {
        "$.connections['1'].m",
        "$.connections['E1'].energy_flow",
        "$.components['HeatExchanger']['HX'].dissipative",
    }


def test_malformed_json():
    model, issues = check(b'{"components": {}, ')
    assert model is None and "malformed JSON" in issues[0].message


# --- semantic errors -----------------------------------------------------------------


def test_unknown_component_type(data):
    data["components"]["Compresor"] = data["components"].pop("Compressor")
    assert_error(data, "$.components['Compresor']", "unknown component type 'Compresor'")


def test_component_name_differs_from_key(data):
    data["components"]["Compressor"]["COMP"]["name"] = "C1"
    assert_error(data, "$.components['Compressor']['COMP'].name", "differs from its key")


def test_duplicate_component_name(data):
    data["components"]["Turbine"]["COMP"] = {"name": "COMP"}
    assert_error(data, "$.components['Turbine']['COMP']", "already used in section 'Compressor'")


def test_two_streams_into_one_inlet(data):
    data["connections"]["1b"] = copy.deepcopy(data["connections"]["1"])
    assert_error(data, "$.connections['1b'].target_connector", "inlet 0 of 'COMP' is already used by connection '1'")


def test_split_physical_exergy_needs_e_t_e_m(data):
    assert_error(data, "$.connections['1']", "e_T or e_M is missing", split_physical_exergy=True)
    data["settings"] = {"split_physical_exergy": True}
    assert_error(data, "$.connections['1']", "e_T or e_M is missing")


def test_chemexlib_needs_composition(data):
    for conn in data["connections"].values():
        conn.pop("e_CH", None)
    del data["connections"]["1"]["mass_composition"]
    assert_error(data, "$.connections['1']", "needs mass_composition", chemExLib="Ahrendts")
    assert not errors(data)  # no chemical exergy wanted: fine


def test_all_semantic_errors_reported_together(data):
    data["components"]["Compressor"]["COMP"]["name"] = "C1"
    data["components"]["Compresor"] = {"X": {"name": "X"}}
    data["connections"]["1b"] = copy.deepcopy(data["connections"]["1"])
    with pytest.raises(InputValidationError) as exc:
        validate(data)
    assert len([i for i in exc.value.issues if i.severity == "error"]) == 3
    assert "3 error(s)" in str(exc.value)


# --- warnings ------------------------------------------------------------------------


def test_composition_sum(data):
    data["connections"]["1"]["mass_composition"]["N2"] += 0.05
    path = "$.connections['1'].mass_composition"
    assert (path, "fractions sum to 1.0500, not 1") in warnings(data)


def test_composition_sum_water_listed_twice(data):
    """EBSILON exports list water both as H2O and H2OG."""
    data["connections"]["1"]["mass_composition"]["H2OG"] = 0.0063
    assert any("H2O and H2OG are both listed" in m for _, m in warnings(data))


# --- JSON Schema and integration -----------------------------------------------------


def test_json_schema():
    schema = json_schema()
    msgspec.json.encode(schema)
    root = schema["$defs"]["ExerpyInput"]
    assert set(root["required"]) == {"components", "connections", "ambient_conditions"}
    types = root["properties"]["components"]["properties"]
    assert types["Compressor"]["additionalProperties"] == {"$ref": "#/$defs/ComponentInput"}
    assert types["Condenser"]["additionalProperties"] == {"$ref": "#/$defs/HeatExchangerInput"}
    assert {"name", "dissipative", "kA"} <= set(schema["$defs"]["HeatExchangerInput"]["properties"])
    material = schema["$defs"]["MaterialConnection"]
    assert {"m", "T", "e_PH", "source_component", "target_component"} <= set(material["required"])
    assert "eta_s" not in schema["$defs"]["ComponentInput"]["properties"]
    assert not any(name.endswith("_unit") for name in material["properties"])


def test_from_json_validates(tmp_path, data):
    data["connections"]["1"]["m"] = -1.0
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(InputValidationError, match=r"\$\.connections\['1'\]\.m"):
        ExergyAnalysis.from_json(str(path))
    # Opting out restores the old behaviour.
    ExergyAnalysis.from_json(str(path), validate=False)


def test_from_json_validation_error_is_value_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{}")
    with pytest.raises(ValueError):
        ExergyAnalysis.from_json(str(path))


def test_parser_output_is_validated(monkeypatch, data):
    """The models read from a simulator are checked like a JSON file."""
    from tespy.networks import Network

    from exerpy.parser.from_aspen import aspen_parser
    from exerpy.parser.from_ebsilon import ebsilon_parser
    from exerpy.parser.from_tespy import tespy_parser

    data["connections"]["1"]["m"] = -1.0
    parsed = lambda *args, **kwargs: copy.deepcopy(data)  # noqa: E731
    monkeypatch.setattr(aspen_parser, "run_aspen", parsed)
    monkeypatch.setattr(ebsilon_parser, "run_ebsilon", parsed)
    monkeypatch.setattr(tespy_parser, "to_exerpy", parsed)
    for factory, model in (
        (ExergyAnalysis.from_aspen, "model.bkp"),
        (ExergyAnalysis.from_ebsilon, "model.ebs"),
        (ExergyAnalysis.from_tespy, Network()),
    ):
        with pytest.raises(InputValidationError, match=r"\$\.connections\['1'\]\.m"):
            factory(model, split_physical_exergy=False)
