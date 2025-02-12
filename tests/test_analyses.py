"""
Test suite for ExergyAnalysis class.
Tests component construction, connection handling, and exergy calculations.
"""

import pytest
import pandas as pd
import json
import os
from exerpy.analyses import ExergyAnalysis, _construct_components
from exerpy.components.component import Component, component_registry

# Basic component classes for testing
@component_registry
class MockTurbine(Component):
    def calc_exergy_balance(self, T0, p0):
        self.E_F = 100000
        self.E_P = 85000
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.E_P / self.E_F

@component_registry
class MockCompressor(Component):
    def calc_exergy_balance(self, T0, p0):
        self.E_F = 50000
        self.E_P = 40000
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.E_P / self.E_F

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
    components = _construct_components(mock_component_data, mock_connection_data)

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
    with pytest.raises(ValueError, match="Component type 'InvalidType' is not registered"):
        _construct_components(invalid_data, {})

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

def test_from_ebsilon(tmp_path):
    """Test creating instance from Ebsilon file."""
    test_file = tmp_path / "test.ebs"
    test_file.write_text("")

    with pytest.raises(FileNotFoundError, match="File not found"):
        ExergyAnalysis.from_ebsilon(str(test_file), simulate=False)

def test_from_ebsilon_load_existing_json(tmp_path):
    """
    Test that the from_ebsilon() method can load existing JSON data when simulate=False.
    """
    # Setup
    ebsilon_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples', 'cgam', 'cgam.ebs'))
    parsed_json_file = ebsilon_file.replace(".ebs", "_parsed.json")

    # Call the method and verify the output
    analysis = ExergyAnalysis.from_ebsilon(ebsilon_file, simulate=False, Tamb=None, pamb=None)
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

def test_from_json_missing_type_index(tmp_path):
    """Test error handling for missing type_index in components."""
    invalid_data = {
        "components": {
            "MockTurbine": {
                "T1": {
                    "name": "T1",
                    "type": "MockTurbine"
                }
            }
        },
        "connections": {},
        "ambient_conditions": {"Tamb": 298.15, "pamb": 101325}
    }
    json_path = tmp_path / "invalid.json"
    with open(json_path, 'w') as f:
        json.dump(invalid_data, f)

    with pytest.raises(ValueError, match="missing required fields: \\['type_index'\\]"):
        ExergyAnalysis.from_json(str(json_path))

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