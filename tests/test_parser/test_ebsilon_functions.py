"""
Test suite for Ebsilon utility functions.

This module provides tests for thermodynamic property calculations
and exergy analysis. Tests cover property calculations for different
fluid types, error handling, and exergy computations.

The test suite uses pytest fixtures to provide mock objects that simulate
the behavior of the Ebsilon application and its components.
"""
import pytest
from unittest.mock import Mock, patch
from exerpy.parser.from_ebsilon.ebsilon_functions import calc_X_from_PT, calc_eT, calc_eM
from exerpy.parser.from_ebsilon.ebsilon_config import substance_mapping
from exerpy.parser.from_ebsilon import __ebsilon_path__

@pytest.fixture
def mock_app():
    """
    Create a mock Ebsilon application with fluid analysis capabilities.

    Returns
    -------
    Mock
        Mock object simulating the Ebsilon application with the following methods:
        - NewFluidData : Returns a mock fluid data object
        - NewFluidAnalysis : Returns a mock fluid analysis object
    """
    app = Mock()
    fluid_data = Mock()
    fluid_analysis = Mock()
    app.NewFluidData.return_value = fluid_data
    app.NewFluidAnalysis.return_value = fluid_analysis
    return app

@pytest.fixture
def mock_pipe():
    """
    Create a mock pipe object representing a fluid stream.

    Returns
    -------
    Mock
        Mock pipe object with the following attributes:
        - Kind : int
            Fluid type identifier (default: 1003 for steam)
        - H : Mock
            Enthalpy with Value (2000.0) and Dimension ("kJ/kg")
        - S : Mock
            Entropy with Value (4.0) and Dimension ("kJ/kgK")
        - E : Mock
            Exergy with Value (500.0) and Dimension ("kJ/kg")
        - Composition attributes : Mock
            Dynamically generated based on substance_mapping
    """
    pipe = Mock()
    pipe.Kind = 1003  # Steam fluid type

    # Set up thermodynamic properties with units
    pipe.H = Mock(Value=2000.0, Dimension="kJ/kg")
    pipe.S = Mock(Value=4.0, Dimension="kJ/kgK")
    pipe.E = Mock(Value=500.0, Dimension="kJ/kg")

    # Create composition attributes for all possible substances
    for substance_key in substance_mapping.keys():
        mock_value = Mock()
        mock_value.Value = 0.0  # Default zero concentration
        setattr(pipe, substance_key, mock_value)

    return pipe


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_calc_X_from_PT_steam(mock_app, mock_pipe):
    """
    Test property calculation for steam fluid type.

    Parameters
    ----------
    mock_app : Mock
        Mock Ebsilon application object
    mock_pipe : Mock
        Mock pipe object configured for steam

    Verifies
    --------
    - Fluid data object creation
    - Fluid analysis execution
    - Analysis setting in fluid data
    """
    result = calc_X_from_PT(mock_app, mock_pipe, 'H', 1e5, 400)

    assert mock_app.NewFluidData.called
    assert mock_app.NewFluidAnalysis.called
    assert mock_app.NewFluidData.return_value.SetAnalysis.called


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_calc_X_from_PT_invalid_property(mock_app, mock_pipe):
    """
    Test error handling for invalid property request.

    Parameters
    ----------
    mock_app : Mock
        Mock Ebsilon application object
    mock_pipe : Mock
        Mock pipe object

    Verifies
    --------
    Function returns None for invalid property types
    """
    result = calc_X_from_PT(mock_app, mock_pipe, 'Invalid', 1e5, 400)
    assert result is None


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_calc_X_from_PT_flue_gas(mock_app, mock_pipe):
    """
    Test property calculation for flue gas with composition.

    Parameters
    ----------
    mock_app : Mock
        Mock Ebsilon application object
    mock_pipe : Mock
        Mock pipe object configured for flue gas

    Verifies
    --------
    - Gas mixture composition handling
    - Substance fraction setting
    - Property calculation completion
    """
    mock_pipe.Kind = 1001  # Flue gas type

    # Configure air composition
    mock_pipe.XO2.Value = 0.21
    mock_pipe.XN2.Value = 0.79

    fluid_data = mock_app.NewFluidData.return_value
    fluid_data.PropertyH_OF_PT.return_value = 1000.0

    result = calc_X_from_PT(mock_app, mock_pipe, 'H', 1e5, 400)

    analysis = mock_app.NewFluidAnalysis.return_value
    assert analysis.SetSubstance.call_count >= 2
    assert result is not None


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_calc_eT(mock_app, mock_pipe):
    """
    Test thermal exergy calculation.

    Parameters
    ----------
    mock_app : Mock
        Mock Ebsilon application object
    mock_pipe : Mock
        Mock pipe object

    Verifies
    --------
    - Thermal exergy component calculation
    - Property calculations sequence
    - Result format validity
    """
    with patch('exerpy.parser.from_ebsilon.ebsilon_functions.calc_X_from_PT') as mock_calc:
        mock_calc.side_effect = [1000000, 2000]  # h_A, s_A values

        result = calc_eT(mock_app, mock_pipe, 1e5, 298.15, 101325)

        assert isinstance(result, (int, float))
        assert mock_calc.call_count == 2


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_calc_eM(mock_app, mock_pipe):
    """
    Test mechanical exergy calculation.

    Parameters
    ----------
    mock_app : Mock
        Mock Ebsilon application object
    mock_pipe : Mock
        Mock pipe object

    Verifies
    --------
    - Mechanical exergy component calculation
    - Thermal exergy dependency
    - Result format validity
    """
    with patch('exerpy.parser.from_ebsilon.ebsilon_functions.calc_eT') as mock_calc_eT:
        mock_calc_eT.return_value = 100000

        result = calc_eM(mock_app, mock_pipe, 1e5, 298.15, 101325)

        assert isinstance(result, (int, float))
        assert mock_calc_eT.called


@pytest.mark.skipif(
    __ebsilon_path__ is None,
    reason='Test skipped due to missing ebsilon dependency.'
)
def test_error_handling_in_property_calc(mock_app, mock_pipe):
    """
    Test error handling in property calculations.

    Parameters
    ----------
    mock_app : Mock
        Mock Ebsilon application object
    mock_pipe : Mock
        Mock pipe object

    Verifies
    --------
    - Exception handling during calculation
    - None return value on error
    - System stability maintenance
    """
    mock_app.NewFluidData.return_value.PropertyH_OF_PT.side_effect = Exception("Test error")

    result = calc_X_from_PT(mock_app, mock_pipe, 'H', 1e5, 400)
    assert result is None
