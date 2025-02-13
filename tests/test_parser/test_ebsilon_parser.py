"""
Test suite for the EbsilonModelParser class.

This module provides comprehensive testing for the EbsilonModelParser functionality,
including initialization, simulation, parsing, and data export. It uses pytest
fixtures to provide mock objects that simulate Ebsilon components and behavior.

The test suite verifies:
- Model initialization and COM interface setup
- Simulation execution and error handling
- Component and connection parsing
- Data sorting and JSON export functionality
"""

import pytest
from unittest.mock import Mock, patch
import json
from exerpy.parser.from_ebsilon.ebsilon_parser import EbsilonModelParser, run_ebsilon
from exerpy.parser.from_ebsilon import __ebsilon_path__

class MockEpFluidType:
    """Mock class simulating Ebsilon's EpFluidType enumeration."""
    pass

class MockEpCalculationResultStatus2:
    """Mock class simulating Ebsilon's calculation result status enumeration."""
    pass

@pytest.fixture(autouse=True)
def mock_imports():
    """
    Mock Ebsilon-specific imports automatically for all tests.

    This fixture patches system modules to provide mock versions of Ebsilon
    dependencies that might not be available during testing.

    Yields
    ------
    None
        Yields control back to the test after setting up the mock imports.
    """
    modules = {
        'EbsOpen': Mock(),
        'EbsOpen.EpFluidType': MockEpFluidType,
        'EbsOpen.EpCalculationResultStatus2': MockEpCalculationResultStatus2
    }
    with patch.dict('sys.modules', modules):
        yield

@pytest.fixture
def mock_ebsilon_app():
    """
    Create a mock Ebsilon application object.

    Returns
    -------
    Mock
        Mock object with the following attributes:
        - Open : Method returning a mock model
        - ObjectCaster : Mock object for type casting
    """
    mock_app = Mock()
    mock_model = Mock()
    mock_app.Open.return_value = mock_model
    mock_app.ObjectCaster = Mock()
    return mock_app

@pytest.fixture
def mock_component():
    """
    Create a mock Ebsilon component for testing.

    Returns
    -------
    Mock
        Mock component with the following attributes:
        - Name : str
            Component identifier
        - Kind : int
            Component type (10046 for measuring point)
        - FTYP : Mock
            Type identifier with Value attribute
        - MEASM : Mock
            Measurement value with Value and Dimension attributes
    """
    mock_comp = Mock()
    mock_comp.Name = "TestComponent"
    mock_comp.Kind = 10046  # Component type 46 (measuring point)

    # Setup measurement properties
    mock_comp.FTYP = Mock()
    mock_comp.FTYP.Value = 26  # Temperature measurement type
    mock_comp.MEASM = Mock()
    mock_comp.MEASM.Value = 298.15  # Kelvin
    mock_comp.MEASM.Dimension = "K"

    return mock_comp

@pytest.fixture
def mock_pipe():
    """
    Create a mock Ebsilon pipe with thermodynamic properties.

    Returns
    -------
    Mock
        Mock pipe with the following attributes:
        - Name : str
            Pipe identifier
        - Kind : int
            Fluid type identifier
        - FluidType : int
            Specific fluid type
        - Thermodynamic properties : Mock
            M, T, P, H, S, E, X, Q with Value and Dimension
        - Connection methods : Mock
            HasComp, Comp, Link
    """
    mock_pipe = Mock()
    mock_pipe.Name = "TestPipe"
    mock_pipe.Kind = 1013  # Logic fluid type
    mock_pipe.FluidType = 1  # Steam/water

    # Setup thermodynamic properties
    properties = {
        'M': (10.0, "kg/s"),     # Mass flow
        'T': (400.0, "K"),       # Temperature
        'P': (10.0, "bar"),      # Pressure
        'H': (2000.0, "kJ/kg"),  # Enthalpy
        'S': (4.0, "kJ/kgK"),    # Entropy
        'E': (500.0, "kJ/kg"),   # Exergy
        'X': (1.0, "-"),         # Quality
        'Q': (1000.0, "kW")      # Heat flow
    }

    for prop, (value, dim) in properties.items():
        setattr(mock_pipe, prop, Mock(Value=value, Dimension=dim))

    # Setup connection methods
    mock_pipe.HasComp = Mock(return_value=True)
    mock_pipe.Comp = Mock()
    mock_pipe.Link = Mock()

    return mock_pipe

@pytest.fixture
def parser():
    """
    Create a parser instance with mocked Ebsilon application.

    Returns
    -------
    EbsilonModelParser
        Parser instance with the following mocked attributes:
        - app : Mock
            Mocked Ebsilon application
        - model : Mock
            Mocked Ebsilon model
        - oc : Mock
            Mocked ObjectCaster
    """
    with patch('win32com.client.Dispatch') as mock_dispatch:
        mock_app = Mock()
        mock_model = Mock()
        mock_oc = Mock()

        mock_app.Open.return_value = mock_model
        mock_app.ObjectCaster = mock_oc
        mock_dispatch.return_value = mock_app

        parser = EbsilonModelParser("dummy_path.ebs")
        parser.app = mock_app
        parser.model = mock_model
        parser.oc = mock_oc
        return parser

@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_initialize_model():
    """
    Test Ebsilon model initialization.

    Verifies
    --------
    - COM interface initialization
    - Model opening
    - ObjectCaster setup
    """
    mock_app = Mock()
    mock_model = Mock()
    mock_oc = Mock()
    mock_app.Open.return_value = mock_model
    mock_app.ObjectCaster = mock_oc

    with patch('exerpy.parser.from_ebsilon.ebsilon_parser.Dispatch', return_value=mock_app) as mocked_dispatch:
        parser = EbsilonModelParser("dummy_path.ebs")
        parser.initialize_model()

        mocked_dispatch.assert_called_once()
        assert parser.app == mock_app
        assert parser.model == mock_model
        assert parser.oc == mock_oc


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_simulate_model(parser):
    """
    Test model simulation execution.

    Parameters
    ----------
    parser : EbsilonModelParser
        Configured parser instance with mocked components

    Verifies
    --------
    - Simulation execution
    - Error collection handling
    """
    mock_calc_errors = Mock()
    mock_calc_errors.Count = 0
    parser.model = Mock()
    parser.model.CalculationErrors = mock_calc_errors

    parser.simulate_model()
    parser.model.SimulateNew.assert_called_once()


def test_parse_component(parser, mock_component):
    """
    Test component parsing functionality.

    Parameters
    ----------
    parser : EbsilonModelParser
        Configured parser instance
    mock_component : Mock
        Mock component with temperature measurement capabilities

    Verifies
    --------
    - Component type casting
    - Ambient temperature extraction
    - Data type validation
    """
    parser.oc = Mock()
    parser.oc.CastToComp = Mock(return_value=mock_component)
    parser.oc.CastToComp46 = Mock(return_value=mock_component)

    parser.parse_component(mock_component)

    assert parser.Tamb is not None
    assert isinstance(parser.Tamb, (int, float))


def test_parse_connection(parser, mock_pipe):
    """
    Test connection parsing functionality.

    Parameters
    ----------
    parser : EbsilonModelParser
        Configured parser instance
    mock_pipe : Mock
        Mock pipe with fluid properties

    Verifies
    --------
    - Pipe type casting
    - Connection data extraction
    - Component linking
    - Fluid type identification
    """
    parser.Tamb = 298.15
    parser.pamb = 101325
    parser.oc = Mock()
    parser.oc.CastToPipe = Mock(return_value=mock_pipe)

    # Configure source and target components
    mock_comp0 = Mock()
    mock_comp0.Kind = 10046  # Source component
    mock_comp1 = Mock()
    mock_comp1.Kind = 10031  # Target component

    mock_pipe.Comp.side_effect = [mock_comp0, mock_comp1]

    parser.parse_connection(mock_pipe)

    assert mock_pipe.Name in parser.connections_data
    connection_data = parser.connections_data[mock_pipe.Name]
    assert 'kind' in connection_data
    assert 'fluid_type' in connection_data


def test_get_sorted_data(parser):
    """
    Test data sorting functionality.

    Parameters
    ----------
    parser : EbsilonModelParser
        Configured parser instance with test data

    Verifies
    --------
    - Component grouping
    - Alphabetical sorting
    - Data structure integrity
    - Ambient condition inclusion
    """
    # Setup test data
    parser.components_data = {
        'group1': {'comp2': {}, 'comp1': {}},
        'group2': {'comp4': {}, 'comp3': {}}
    }
    parser.connections_data = {
        'conn2': {},
        'conn1': {}
    }
    parser.Tamb = 298.15
    parser.pamb = 101325

    sorted_data = parser.get_sorted_data()

    assert 'components' in sorted_data
    assert 'connections' in sorted_data
    assert 'ambient_conditions' in sorted_data
    assert list(sorted_data['components']['group1'].keys()) == ['comp1', 'comp2']
    assert list(sorted_data['connections'].keys()) == ['conn1', 'conn2']


def test_write_to_json(parser, tmp_path):
    """
    Test JSON file creation and data persistence.

    Parameters
    ----------
    parser : EbsilonModelParser
        Configured parser instance
    tmp_path : Path
        Pytest fixture providing temporary directory path

    Verifies
    --------
    - File creation
    - Data structure preservation
    - JSON formatting
    """
    test_data = {
        'components': {'group1': {'comp1': {}}},
        'connections': {'conn1': {}},
        'ambient_conditions': {'Tamb': 298.15, 'pamb': 101325}
    }

    output_file = tmp_path / "test_output.json"

    with patch.object(parser, 'get_sorted_data', return_value=test_data):
        parser.write_to_json(str(output_file))

    assert output_file.exists()
    with open(output_file) as f:
        loaded_data = json.load(f)
    assert loaded_data == test_data


@patch('win32com.client.Dispatch')
def test_run_ebsilon(mock_dispatch, tmp_path):
    """
    Test complete Ebsilon model processing workflow.

    Parameters
    ----------
    mock_dispatch : Mock
        Mocked COM dispatch
    tmp_path : Path
        Pytest fixture providing temporary directory path

    Verifies
    --------
    - Model initialization
    - Simulation execution
    - Data parsing
    - JSON export
    - Function return value
    """
    mock_parser = Mock()
    mock_parser.get_sorted_data.return_value = {'test': 'data'}

    with patch('os.path.exists', return_value=True), \
         patch('exerpy.parser.from_ebsilon.ebsilon_parser.EbsilonModelParser', return_value=mock_parser):

        result = run_ebsilon("test.ebs", str(tmp_path / "output.json"))

        assert result == {'test': 'data'}
        mock_parser.initialize_model.assert_called_once()
        mock_parser.simulate_model.assert_called_once()
        mock_parser.parse_model.assert_called_once()
        mock_parser.write_to_json.assert_called_once()


def test_run_ebsilon_file_not_found():
    """
    Test error handling for missing model file.

    Verifies
    --------
    - FileNotFoundError raising
    - Error message clarity
    """
    with pytest.raises(FileNotFoundError):
        run_ebsilon("nonexistent.ebs")
