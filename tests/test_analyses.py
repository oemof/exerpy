"""
Unit tests for the ExergyAnalysis class.

This file contains tests that verify the internal logic of the ExergyAnalysis class,
including component construction, connection handling, and exergy calculations using
in-memory and mock data. These tests run quickly and are independent of external files.
"""

import pytest
import pandas as pd
import numpy as np
import json
import os
from exerpy.analyses import ExergyAnalysis, _construct_components, _load_json
from exerpy.components.component import Component, component_registry
from exerpy.components.helpers.cycle_closer import CycleCloser
from exerpy.parser.from_ebsilon import __ebsilon_path__

# Basic component classes for testing
@component_registry
class MockTurbine(Component):
    def calc_exergy_balance(self, T0, p0, split_physical_exergy=True):
        self.E_F = 100000
        self.E_P = 85000
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.E_P / self.E_F

@component_registry
class MockCompressor(Component):
    def calc_exergy_balance(self, T0, p0, split_physical_exergy=True):
        self.E_F = 50000
        self.E_P = 40000
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.E_P / self.E_F

# Dummy CycleCloser (should be skipped in the analysis)
@component_registry
class DummyCycleCloser(CycleCloser):
    def calc_exergy_balance(self, T0, p0, split_physical_exergy=True):
        self.E_F = 0
        self.E_P = 0
        self.E_D = 0

# Dummy Valve to test dissipative logic
@component_registry
class DummyValve(Component):
    def calc_exergy_balance(self, T0, p0, split_physical_exergy=True):
        self.E_F = 0
        self.E_P = 0
        self.E_D = 0

# Test fixtures
@pytest.fixture
def mock_component_data():
    """Create mock component data."""
    return {
        "MockTurbine": {
            "T1": {
                "name": "T1",
                "type": "MockTurbine",
                "type_index": 23,
                "eta_s": 0.9
            }
        },
        "MockCompressor": {
            "C1": {
                "name": "C1",
                "type": "MockCompressor",
                "type_index": 24,
                "eta_s": 0.85
            }
        }
    }

@pytest.fixture
def mock_connection_data():
    """Create mock connection data with realistic structure."""
    return {
        "1": {
            "kind": "material",
            "source_component": None,
            "source_connector": None,
            "target_component": "C1",
            "target_connector": 0,
            "T": 298.15,
            "p": 101325,
            "m": 100,
            "E": 50000,
            "mass_composition": {  # Added composition
                "N2": 0.79,
                "O2": 0.21
            }
        },
        "2": {
            "kind": "material",
            "source_component": "C1",
            "source_connector": 0,
            "target_component": "T1",
            "target_connector": 0,
            "T": 500,
            "p": 500000,
            "m": 100,
            "E": 5000,
            "mass_composition": {  # Added composition
                "N2": 0.79,
                "O2": 0.21
            }
        },
        "3": {
            "kind": "power",
            "source_component": "T1",
            "source_connector": 1,
            "target_component": None,
            "target_connector": None,
            "energy_flow": 85000,
            "E": 35000
        }
    }

@pytest.fixture
def exergy_analysis(mock_component_data, mock_connection_data):
    """Create ExergyAnalysis instance."""
    return ExergyAnalysis(mock_component_data, mock_connection_data, 298.15, 101325)

# Test component construction
def test_component_construction(mock_component_data, mock_connection_data):
    """Test proper component construction and connection assignment."""
    Tamb = 298.15
    components = _construct_components(mock_component_data, mock_connection_data, Tamb)

    assert len(components) == 2
    assert isinstance(components["T1"], MockTurbine)
    assert isinstance(components["C1"], MockCompressor)

    # Check connections
    assert 0 in components["C1"].inl
    assert 0 in components["C1"].outl
    assert components["T1"].inl[0]["T"] == 500

def test_invalid_component_type():
    """Test handling of invalid component type."""
    invalid_data = {
        "InvalidType": {
            "X1": {"name": "X1", "type": "InvalidType"}
        }
    }
    components = _construct_components(invalid_data, {}, 298.15)
    # Expect that the invalid component is skipped, resulting in an empty dictionary.
    assert components == {}


# Test exergy analysis
def test_analyse_basic(exergy_analysis):
    """Test basic exergy analysis calculation."""
    E_F = {"inputs": ["1"]}  # Fuel input: 50000
    E_P = {"inputs": ["3"]}  # Product input: 35000

    exergy_analysis.analyse(E_F, E_P)

    assert exergy_analysis.E_F == 50000
    assert exergy_analysis.E_P == 35000
    assert exergy_analysis.epsilon == pytest.approx(0.7, rel=1e-2)

def test_analyse_with_losses(exergy_analysis):
    """Test exergy analysis with loss accounting."""
    E_F = {"inputs": ["1"]}
    E_P = {"inputs": ["3"]}
    E_L = {"inputs": ["2"]}

    exergy_analysis.analyse(E_F, E_P, E_L)

    assert exergy_analysis.E_L == 5000
    assert exergy_analysis.E_D == exergy_analysis.E_F - exergy_analysis.E_P - exergy_analysis.E_L

def test_component_exergy_balance(exergy_analysis):
    """Test individual component exergy balance calculations."""
    E_F = {"inputs": ["1"]}
    E_P = {"outputs": ["3"]}

    exergy_analysis.analyse(E_F, E_P)

    comp = exergy_analysis.components["C1"]
    assert comp.E_F == 50000
    assert comp.E_P == 40000
    assert comp.E_D == 10000
    assert comp.y == pytest.approx(0.2, rel=1e-2)

# Test results generation
def test_exergy_results(exergy_analysis):
    """Test generation of results tables."""
    E_F = {"inputs": ["1"]}
    E_P = {"outputs": ["3"]}
    exergy_analysis.analyse(E_F, E_P)

    comp_results, material_results, non_material_results = exergy_analysis.exergy_results()

    # Check component results
    assert isinstance(comp_results, pd.DataFrame)
    assert "E_F [kW]" in comp_results.columns
    assert "ε [%]" in comp_results.columns
    assert len(comp_results) == 3  # Two components plus total

    # Check connection results
    assert isinstance(material_results, pd.DataFrame)
    assert isinstance(non_material_results, pd.DataFrame)
    assert "T [°C]" in material_results.columns
    assert "Energy Flow [kW]" in non_material_results.columns


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_from_ebsilon(tmp_path):
    """Test creating instance from Ebsilon file."""
    test_file = tmp_path / "test.ebs"
    test_file.write_text("")

    with pytest.raises(FileNotFoundError, match="File not found"):
        ExergyAnalysis.from_ebsilon(str(test_file))


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_from_ebsilon_load_existing_json(tmp_path):
    """
    Test that the from_ebsilon() method can load existing JSON data when simulate=False.
    """
    # Setup
    ebsilon_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples', 'cgam', 'cgam.ebs'))
    parsed_json_file = ebsilon_file.replace(".ebs", "_ebs.json")

    # Call the method and verify the output
    analysis = ExergyAnalysis.from_ebsilon(ebsilon_file, Tamb=None, pamb=None)
    assert isinstance(analysis, ExergyAnalysis)
    assert abs(analysis.Tamb - 298.15) < 1e-5    # Allow small floating-point tolerance
    assert abs(analysis.pamb - 101300) < 1e-5    # Allow small floating-point tolerance
    assert len(analysis.components) > 0
    assert "CC" in analysis.components

def test_ebsilon_invalid_format(tmp_path):
    """Test handling of invalid file format."""
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("")

    with pytest.raises(ValueError, match="Unsupported file format"):
        ExergyAnalysis.from_ebsilon(str(invalid_file))

@pytest.fixture
def mock_json_data(mock_component_data, mock_connection_data):
    """Provide mock JSON data for testing."""
    return {
        "components": mock_component_data,
        "connections": mock_connection_data,
        "ambient_conditions": {
            "Tamb": 298.15,
            "Tamb_unit": "K",
            "pamb": 101325,
            "pamb_unit": "Pa"
        }
    }

@pytest.fixture
def json_file(tmp_path, mock_json_data):
    """Create temporary JSON file with mock data."""
    json_path = tmp_path / "test.json"
    with open(json_path, 'w') as f:
        json.dump(mock_json_data, f)
    return json_path

def test_from_json_missing_composition(tmp_path):
    """Test error handling for material streams without composition."""
    data = {
        "components": {
            "MockTurbine": {
                "T1": {
                    "name": "T1",
                    "type": "MockTurbine",
                    "type_index": 23,
                    "eta_s": 0.9
                }
            }
        },
        "connections": {
            "1": {
                "kind": "material",
                "source_component": None,
                "target_component": "T1",
                "T": 298.15,
                "p": 101325
            }
        },
        "ambient_conditions": {"Tamb": 298.15, "pamb": 101325}
    }
    json_path = tmp_path / "missing_comp.json"
    with open(json_path, 'w') as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Material stream '1' missing mass_composition"):
        ExergyAnalysis.from_json(str(json_path), chemExLib='Ahrendts')

def test_from_json_basic(json_file):
    """Test basic JSON file loading."""
    analysis = ExergyAnalysis.from_json(str(json_file))
    assert isinstance(analysis, ExergyAnalysis)
    assert len(analysis.components) == 2
    assert "T1" in analysis.components
    assert "C1" in analysis.components
    assert abs(analysis.Tamb - 298.15) < 1e-5
    assert abs(analysis.pamb - 101325) < 1e-5

def test_from_json_override_ambient(json_file):
    """Test overriding ambient conditions."""
    analysis = ExergyAnalysis.from_json(str(json_file), Tamb=300, pamb=100000)
    assert abs(analysis.Tamb - 300) < 1e-5
    assert abs(analysis.pamb - 100000) < 1e-5

def test_from_json_missing_sections(tmp_path):
    """Test error handling for missing required sections."""
    incomplete_data = {"components": {}}
    json_path = tmp_path / "incomplete.json"
    with open(json_path, 'w') as f:
        json.dump(incomplete_data, f)

    with pytest.raises(ValueError, match="Missing required sections"):
        ExergyAnalysis.from_json(str(json_path))

def test_from_json_invalid_component_structure(tmp_path):
    """Test error handling for invalid component structure."""
    invalid_data = {
        "components": {"InvalidComponent": []},  # Should be dict
        "connections": {},
        "ambient_conditions": {"Tamb": 298.15, "pamb": 101325}
    }
    json_path = tmp_path / "invalid.json"
    with open(json_path, 'w') as f:
        json.dump(invalid_data, f)

    with pytest.raises(ValueError, match="must contain dictionary"):
        ExergyAnalysis.from_json(str(json_path))

def test_from_json_with_chemical_exergy(json_file):
    """Test JSON loading with chemical exergy calculation."""
    analysis = ExergyAnalysis.from_json(str(json_file), chemExLib='Ahrendts')
    assert 'e_CH' in next(iter(analysis.connections.values()))

def test_from_json_invalid_file():
    """Test error handling for non-existent file."""
    with pytest.raises(FileNotFoundError):
        ExergyAnalysis.from_json("nonexistent.json")

def test_zero_fuel_exergy(exergy_analysis, mock_connection_data, monkeypatch):
    """
    Test that if the fuel connections have E=0, then E_F is zero and epsilon is None.
    """
    # Modify connection "1" (used for fuel) so that its E becomes 0.
    mock_connection_data["1"]["E"] = 0
    # Patch logging.info in the analyses module to prevent formatting of None.
    monkeypatch.setattr("exerpy.analyses.logging.info", lambda msg: None)
    # Create a fresh analysis with the modified connection data.
    analysis = ExergyAnalysis(
        exergy_analysis._component_data, mock_connection_data, 298.15, 101325
    )
    fuel = {"inputs": ["1"]}
    product = {"inputs": ["3"]}
    analysis.analyse(fuel, product)
    assert analysis.E_F == 0.0
    assert analysis.epsilon is None

def test_invalid_connection_reference(exergy_analysis):
    """
    Test that referencing a connection that does not exist raises a ValueError.
    """
    fuel = {"inputs": ["nonexistent"]}
    product = {"inputs": ["3"]}
    with pytest.raises(ValueError, match="The connection nonexistent is not part of the plant's connections."):
        exergy_analysis.analyse(fuel, product)

def test_cyclecloser_skipped(mock_component_data, mock_connection_data, caplog):
    """
    Test that a CycleCloser component is skipped in the exergy analysis calculations,
    and that a warning is logged if the sum of non-CycleCloser component destructions does not match
    the overall system destruction.
    """
    # Add a dummy CycleCloser component.
    mock_component_data["CycleCloser"] = {
        "CC": {"name": "CC", "type": "DummyCycleCloser", "type_index": 999}
    }
    # Add a connection for the CycleCloser (this connection should be ignored)
    mock_connection_data["99"] = {
        "kind": "material",
        "source_component": "CC",
        "source_connector": 0,
        "target_component": None,
        "target_connector": None,
        "T": 298.15,
        "p": 101325,
        "m": 100,
        "E": 1000,
        "mass_composition": {"N2": 0.79, "O2": 0.21}
    }
    analysis = ExergyAnalysis(mock_component_data, mock_connection_data, 298.15, 101325)
    fuel = {"inputs": ["1"]}
    product = {"inputs": ["3"]}
    with caplog.at_level("WARNING"):
        analysis.analyse(fuel, product)
    # Verify that the CycleCloser component "CC" is present
    assert "CC" in analysis.components
    # Sum of component destruction for non-CycleCloser components:
    total_component_E_D = sum(comp.E_D for name, comp in analysis.components.items()
                                if comp.__class__.__name__ != "CycleCloser")
    # Overall system destruction calculated from connections:
    overall_E_D = analysis.E_F - analysis.E_P - analysis.E_L
    # They are not equal, so a warning should be logged.
    assert not np.isclose(total_component_E_D, overall_E_D, rtol=1e-5)
    assert "does not match overall system exergy destruction" in caplog.text

def test_valve_dissipative():
    """
    Test that a Valve component with inlet and outlet temperatures above ambient is marked as dissipative.
    """
    component_data = {
        "Valve": {
            "V1": {"name": "V1", "type": "DummyValve", "type_index": 101}
        }
    }
    # Create connection data for the valve:
    connection_data = {
        "1": {
            "kind": "material",
            "source_component": None,
            "source_connector": None,
            "target_component": "V1",
            "target_connector": 0,
            "T": 350,  # above ambient
            "p": 101325,
            "m": 100,
            "E": 1000,
            "mass_composition": {"N2": 0.79, "O2": 0.21}
        },
        "2": {
            "kind": "material",
            "source_component": "V1",
            "source_connector": 0,
            "target_component": None,
            "target_connector": None,
            "T": 360,  # above ambient
            "p": 101325,
            "m": 100,
            "E": 1000,
            "mass_composition": {"N2": 0.79, "O2": 0.21}
        }
    }
    # Use an ambient temperature lower than the connection temperatures.
    analysis = ExergyAnalysis(component_data, connection_data, 300, 101325)
    components = _construct_components(component_data, connection_data, 300)
    valve = components["V1"]
    assert valve.is_dissipative is True

def test_multiple_inputs_outputs(mock_component_data):
    """
    Test analysis when multiple fuel and product streams (both inputs and outputs) are present.
    """
    # Extend the connection data by copying the original and adding extra connections.
    connection_data = {
        "1": {  # existing fuel connection
            "kind": "material",
            "source_component": None,
            "source_connector": None,
            "target_component": "C1",
            "target_connector": 0,
            "T": 298.15,
            "p": 101325,
            "m": 100,
            "E": 50000,
            "mass_composition": {"N2": 0.79, "O2": 0.21}
        },
        "2": {  # existing product connection from C1 to T1
            "kind": "material",
            "source_component": "C1",
            "source_connector": 0,
            "target_component": "T1",
            "target_connector": 0,
            "T": 500,
            "p": 500000,
            "m": 100,
            "E": 5000,
            "mass_composition": {"N2": 0.79, "O2": 0.21}
        },
        "3": {  # existing power connection from T1
            "kind": "power",
            "source_component": "T1",
            "source_connector": 1,
            "target_component": None,
            "target_connector": None,
            "energy_flow": 85000,
            "E": 35000
        },
        "4": {  # additional fuel connection to C1
            "kind": "material",
            "source_component": None,
            "source_connector": None,
            "target_component": "C1",
            "target_connector": 1,
            "T": 298.15,
            "p": 101325,
            "m": 100,
            "E": 30000,
            "mass_composition": {"N2": 0.79, "O2": 0.21}
        },
        "5": {  # additional product connection from T1 (power stream)
            "kind": "power",
            "source_component": "T1",
            "source_connector": 2,
            "target_component": None,
            "target_connector": None,
            "energy_flow": 50000,
            "E": 20000
        }
    }
    # Use the original component data fixture function to get components.
    analysis = ExergyAnalysis(mock_component_data, connection_data, 298.15, 101325)
    fuel = {"inputs": ["1", "4"], "outputs": []}
    product = {"inputs": ["3", "5"], "outputs": []}
    analysis.analyse(fuel, product)
    # Expect E_F = 50000 + 30000 = 80000, and E_P = 35000 + 20000 = 55000.
    assert analysis.E_F == 80000
    assert analysis.E_P == 55000

def test_ambient_conditions_propagation(mock_component_data, mock_connection_data):
    """
    Test that ambient conditions (Tamb, pamb) provided to ExergyAnalysis are correctly stored.
    """
    analysis = ExergyAnalysis(mock_component_data, mock_connection_data, 310, 90000)
    assert analysis.Tamb == 310
    assert analysis.pamb == 90000

def test_exergy_destruction_warning(exergy_analysis, caplog):
    """
    Test that if the sum of component exergy destructions does not match the overall system E_D,
    a warning is logged.
    """
    # Monkey-patch one component's calc_exergy_balance to artificially alter its E_D.
    comp = exergy_analysis.components["C1"]
    orig_calc = comp.calc_exergy_balance
    def fake_calc(T0, p0, split_physical_exergy=True):
        orig_calc(T0, p0, split_physical_exergy)
        # Artificially add an error to the destruction value.
        comp.E_D += 1000
    comp.calc_exergy_balance = fake_calc

    fuel = {"inputs": ["1"]}
    product = {"inputs": ["3"]}
    exergy_analysis.analyse(fuel, product)
    # Check that a warning message is logged.
    assert "does not match overall system exergy destruction" in caplog.text

def test_export_to_json(tmp_path, mock_component_data, mock_connection_data):
    """
    Test that the export_to_json method correctly serializes the analysis data.
    """
    # Create an analysis instance using mock data.
    analysis = ExergyAnalysis(mock_component_data, mock_connection_data, 298.15, 101325)

    # Export the analysis to a temporary JSON file.
    output_file = tmp_path / "exported_analysis.json"
    analysis.export_to_json(str(output_file))

    # Load the exported JSON data.
    with open(output_file, "r") as f:
        data = json.load(f)

    # Check that required keys are present.
    assert "components" in data
    assert "connections" in data
    assert "ambient_conditions" in data

    # Verify that ambient conditions match.
    ambient = data["ambient_conditions"]
    assert ambient["Tamb"] == 298.15
    assert ambient["pamb"] == 101325

    # Optionally, verify that the components and connections match the original inputs.
    assert data["components"] == mock_component_data
    assert data["connections"] == mock_connection_data


def test_from_json_with_chemical_exergy(json_file, monkeypatch):
    """
    Test that when a chemical exergy library is provided, the from_json method adds the
    chemical exergy field (e_CH) to at least one material connection.
    """
    # Define a dummy add_chemical_exergy function that adds 'e_CH' to each material connection.
    def dummy_add_chemical_exergy(data, Tamb, pamb, chemExLib):
        for conn in data['connections'].values():
            if conn.get("kind") == "material":
                conn["e_CH"] = 123  # dummy chemical exergy value
        return data

    # Patch the add_chemical_exergy function in the analyses module.
    monkeypatch.setattr("exerpy.analyses.add_chemical_exergy", dummy_add_chemical_exergy)

    # Load the analysis with the dummy chemExLib parameter.
    analysis = ExergyAnalysis.from_json(str(json_file), chemExLib='DummyChemLib')
    # Check that for at least one connection of kind 'material', the key 'e_CH' is present.
    material_connections = [conn for conn in analysis.connections.values() if conn.get("kind") == "material"]
    assert any("e_CH" in conn for conn in material_connections)

def test_round_trip_export_import(tmp_path, mock_component_data, mock_connection_data):
    """
    Create an analysis, export it to JSON, then reload it with from_json and verify that
    key parameters (ambient conditions and component data) remain consistent.
    """
    Tamb = 298.15
    pamb = 101325
    # Create an analysis instance
    analysis_original = ExergyAnalysis(mock_component_data, mock_connection_data, Tamb, pamb)

    # Export the analysis to a temporary JSON file.
    export_file = tmp_path / "roundtrip.json"
    analysis_original.export_to_json(str(export_file))

    # Reload the analysis from the exported JSON.
    analysis_loaded = ExergyAnalysis.from_json(str(export_file))

    # Verify that ambient conditions are preserved.
    assert analysis_loaded.Tamb == pytest.approx(Tamb, rel=1e-5)
    assert analysis_loaded.pamb == pytest.approx(pamb, rel=1e-5)

    # Verify that the component data is preserved.
    # (For simplicity, we check that keys match; a deeper check may be implemented if needed.)
    assert analysis_loaded._component_data.keys() == mock_component_data.keys()
    for comp_type in mock_component_data:
        assert analysis_loaded._component_data[comp_type].keys() == mock_component_data[comp_type].keys()

def test_malformed_json_raises(tmp_path):
    """
    Test that _load_json raises a JSONDecodeError when given a file with malformed JSON.
    """
    # Write a file with invalid JSON content.
    malformed_file = tmp_path / "malformed.json"
    malformed_file.write_text("this is not valid json")

    with pytest.raises(Exception) as excinfo:
        _load_json(str(malformed_file))
    # Depending on implementation, the error may be a JSONDecodeError or a custom error.
    assert "Invalid JSON format" in str(excinfo.value) or "Expecting value" in str(excinfo.value)

def test_results_numerical_conversion(tmp_path):
    """
    Test that numerical conversions (e.g., from W to kW) in the exergy results DataFrame are correct.
    We create a minimal analysis with known exergy values and check the converted values.
    """
    # Create minimal component and connection data with known values.
    # Use a registered component type ("MockTurbine") for the component.
    component_data = {
        "MockTurbine": {
            "Comp1": {
                "name": "Comp1",
                "type": "MockTurbine",
                "type_index": 1,
                "eta_s": 1.0
            }
        }
    }
    # Set connection E values in Watts.
    connection_data = {
        "1": {
            "kind": "material",
            "source_component": None,
            "source_connector": None,
            "target_component": "Comp1",
            "target_connector": 0,
            "T": 300,
            "p": 101325,
            "m": 10,
            "E": 100000,  # 100 kW when converted
            "mass_composition": {"N2": 0.79, "O2": 0.21}
        },
        "2": {
            "kind": "power",
            "source_component": "Comp1",
            "source_connector": 1,
            "target_component": None,
            "target_connector": None,
            "energy_flow": 50000,
            "E": 50000  # 50 kW when converted
        }
    }
    # Create analysis with these values.
    analysis = ExergyAnalysis(component_data, connection_data, 300, 101325)
    # Run a basic analysis: use connection "1" as fuel and connection "2" as product.
    E_F = {"inputs": ["1"]}
    E_P = {"inputs": ["2"]}
    analysis.analyse(E_F, E_P)

    # Call exergy_results to generate DataFrames.
    comp_results, mat_results, non_mat_results = analysis.exergy_results(print_results=False)

    # In the component results DataFrame, the fuel exergy should be converted from W to kW.
    # For our connection "1": 100000 W => 100 kW.
    comp_row = comp_results[comp_results["Component"] == "Comp1"]
    assert comp_row.shape[0] > 0, "No row for component 'Comp1' found in the results."
    # Verify that the converted fuel exergy (if present) is close to 100.
    assert np.isclose(comp_row["E_F [kW]"].values[0], 100, atol=0.01)

    # For non-material connections, check that the energy flow conversion works similarly.
    # For connection "2": 50000 W => 50 kW.
    non_mat_row = non_mat_results[non_mat_results["Connection"] == "2"]
    assert non_mat_row.shape[0] > 0, "No row for connection '2' found in non-material results."
    assert np.isclose(non_mat_row["Energy Flow [kW]"].values[0], 50, atol=0.01)
