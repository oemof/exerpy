"""
Test suite for the functions module of exerpy.

This module provides comprehensive testing for:
- Unit conversions
- Fraction conversions (mass/molar)
- Chemical exergy calculations
- Total exergy flow calculations

Uses both basic test cases and realistic process data from Ebsilon simulations.
"""

import json

import pytest

from exerpy.functions import add_chemical_exergy
from exerpy.functions import add_total_exergy_flow
from exerpy.functions import calc_chemical_exergy
from exerpy.functions import mass_to_molar_fractions
from exerpy.functions import molar_to_mass_fractions


@pytest.fixture
def realistic_json_data():
    """
    Create realistic JSON data structure mimicking Ebsilon output.

    Returns
    -------
    dict
        Full process simulation data including components and connections with
        realistic values from an actual gas turbine simulation.
    """
    return {
        "connections": {
            "1": {
                "kind": "material",
                "name": "air_inlet",
                "mass_composition": {
                    "CO2": 0.0004608513064147323,
                    "H2O": 0.011947794691685262,
                    "N2": 0.757615006428111,
                    "O2": 0.22997634757378901,
                },
                "m": 90.956080037409,
                "m_unit": "kg / s",
                "T": 298.15,
                "T_unit": "K",
                "p": 101325,
                "p_unit": "Pa",
                "h": 25544.62052481137,
                "h_unit": "J / kg",
                "s": 6959.011766195539,
                "s_unit": "J / kgK",
                "e_PH": 302994.8669085477,
                "e_PH_unit": "J / kg",
            },
            "2": {"kind": "power", "name": "turbine_power", "energy_flow": 29659713.796092745, "energy_flow_unit": "W"},
            "3": {
                "kind": "heat",
                "name": "heat_exchanger",
                "energy_flow": 23960872.88824695,
                "energy_flow_unit": "W",
                "source_component": "APH",
            },
            "4": {
                "kind": "material",
                "name": "flue_gas",
                "mass_composition": {
                    "CO2": 0.049166137858945996,
                    "H2O": 0.051617334069659,
                    "N2": 0.7441619127802009,
                    "O2": 0.1550546152911942,
                },
                "m": 92.60040050259295,
                "m_unit": "kg / s",
                "T": 1520.0,
                "T_unit": "K",
                "p": 914200,
                "p_unit": "Pa",
                "h": 1476468.2085478688,
                "h_unit": "J / kg",
                "s": 8327.149152086387,
                "s_unit": "J / kgK",
                "e_PH": 1086825.2014474052,
                "e_PH_unit": "J / kg",
            },
        },
        "components": {
            "APH": {
                "name": "APH",
                "type": "Air Preheater",
                "type_index": 25,
                "Q": 23960872.88824695,
                "Q_unit": "W",
                "kA": 139.40552769938202,
                "kA_unit": "W / K",
            },
            "CC": {"name": "CC", "type": "Combustion Chamber", "type_index": 90, "lamb": 1.2, "Q": 0.0, "Q_unit": "W"},
            "GT": {
                "name": "GT",
                "type": "Gas Turbine",
                "type_index": 23,
                "eta_s": 0.86,
                "eta_mech": 1.0,
                "P": 59659712.79310835,
                "P_unit": "W",
            },
        },
        "ambient_conditions": {"Tamb": 298.15, "Tamb_unit": "K", "pamb": 101325, "pamb_unit": "Pa"},
    }


@pytest.fixture
def basic_stream_data():
    """
    Create basic stream data for simple tests.

    Returns
    -------
    dict
        Dictionary with basic mass composition data for air
    """
    return {"mass_composition": {"O2": 0.21, "N2": 0.79}}


@pytest.fixture
def air_composition():
    """
    Create realistic air composition data.

    Returns
    -------
    dict
        Standard air composition in mass fractions
    """
    return {
        "mass_composition": {
            "N2": 0.757615006428111,
            "O2": 0.22997634757378901,
            "CO2": 0.0004608513064147323,
            "H2O": 0.011947794691685262,
        }
    }


@pytest.fixture
def flue_gas_composition():
    """
    Create realistic flue gas composition data.

    Returns
    -------
    dict
        Typical flue gas composition in mass fractions from combustion process
    """
    return {
        "mass_composition": {
            "CO2": 0.049166137858945996,
            "H2O": 0.051617334069659,
            "N2": 0.7441619127802009,
            "O2": 0.1550546152911942,
        }
    }


# Basic Conversion Tests
def test_basic_mass_to_molar_conversion():
    """
    Test basic mass to molar fraction conversion.

    Verifies
    --------
    - Basic conversion functionality
    - Sum of fractions equals 1
    - No loss of components
    """
    mass_fractions = {"O2": 0.21, "N2": 0.79}
    molar_fractions = mass_to_molar_fractions(mass_fractions)

    assert isinstance(molar_fractions, dict)
    assert abs(sum(molar_fractions.values()) - 1.0) < 1e-6
    assert "O2" in molar_fractions
    assert "N2" in molar_fractions


def test_basic_molar_to_mass_conversion():
    """
    Test basic molar to mass fraction conversion.

    Verifies
    --------
    - Basic conversion functionality
    - Sum of fractions equals 1
    - No loss of components
    """
    molar_fractions = {"O2": 0.21, "N2": 0.79}
    mass_fractions = molar_to_mass_fractions(molar_fractions)

    assert isinstance(mass_fractions, dict)
    assert abs(sum(mass_fractions.values()) - 1.0) < 1e-6
    assert "O2" in mass_fractions
    assert "N2" in mass_fractions


# Complex Conversion Tests
def test_mass_to_molar_fractions_air(air_composition):
    """
    Test mass to molar fraction conversion for air mixture.

    Parameters
    ----------
    air_composition : dict
        Fixture providing standard air composition

    Verifies
    --------
    - Conversion accuracy
    - Sum of molar fractions equals 1
    - Component preservation
    - Physical reasonableness of results
    """
    molar_fractions = mass_to_molar_fractions(air_composition["mass_composition"])

    assert isinstance(molar_fractions, dict)
    assert abs(sum(molar_fractions.values()) - 1.0) < 1e-6
    assert set(molar_fractions.keys()) == set(air_composition["mass_composition"].keys())
    assert abs(molar_fractions["N2"] / molar_fractions["O2"] - 3.76) < 0.1


def test_mass_to_molar_fractions_flue_gas(flue_gas_composition):
    """
    Test mass to molar fraction conversion for flue gas mixture.

    Parameters
    ----------
    flue_gas_composition : dict
        Fixture providing typical flue gas composition

    Verifies
    --------
    - Conversion accuracy
    - Sum of molar fractions equals 1
    - Reasonable CO2 content
    """
    molar_fractions = mass_to_molar_fractions(flue_gas_composition["mass_composition"])

    assert isinstance(molar_fractions, dict)
    assert abs(sum(molar_fractions.values()) - 1.0) < 1e-6
    assert abs(molar_fractions["CO2"] - 0.031565) < 1e-6


def test_fraction_conversion_invalid_substance():
    """
    Test error handling for invalid substances.

    Verifies
    --------
    - ValueError raised for invalid substances
    - Proper error messages
    """
    with pytest.raises(ValueError):
        mass_to_molar_fractions({"InvalidSubstance1": 0.5, "InvaludeSubstance2": 0.5})

    with pytest.raises(ValueError):
        molar_to_mass_fractions({"InvalidSubstance1": 0.5, "InvaludeSubstance2": 0.5})


def test_mass_to_molar_fractions_names_unknown_species():
    """A species CoolProp has no molar mass for is named in the error instead of being dropped."""
    with pytest.raises(ValueError, match="no molar mass for Kr in"):
        mass_to_molar_fractions({"CH4": 0.7, "Kr": 0.3})

    with pytest.raises(ValueError, match="no molar mass for Kr, NO2 in"):
        mass_to_molar_fractions({"CH4": 0.5, "Kr": 0.3, "NO2": 0.2})


def test_mass_to_molar_fractions_ignores_zero_fractions():
    """Species with a zero mass fraction are left out, whether CoolProp knows them or not."""
    molar_fractions = mass_to_molar_fractions({"CH4": 0.7, "Krypton": 0.3, "Kr": 0.0, "N2": 0.0})

    n_CH4, n_Kr = 0.7 / 16.043e-3, 0.3 / 83.798e-3
    expected = {"CH4": n_CH4 / (n_CH4 + n_Kr), "Krypton": n_Kr / (n_CH4 + n_Kr)}
    assert molar_fractions == pytest.approx(expected, rel=1e-4)

    assert mass_to_molar_fractions({"Therminol VP1": 1.0, "H2O": 0.0}) == {"Therminol VP1": 1.0}


def test_mass_to_molar_fractions_rejects_an_empty_composition():
    """A stream without mass fractions, e.g. an EBSILON binary mixture, raises a clear error."""
    with pytest.raises(ValueError, match="mass composition is empty"):
        mass_to_molar_fractions({})


@pytest.mark.parametrize(
    "path", ["examples/exergy_analysis/cgam/cgam_ebs.json", "examples/exergoeconomic_analysis/cgam/cgam.json"]
)
def test_stored_ebsilon_compositions_are_mass_fractions(path):
    """The stored EBSILON exports name CoolProp species only and their mass fractions sum to 1."""
    with open(path, encoding="utf-8") as f:
        connections = json.load(f)["connections"]
    for name, conn in connections.items():
        composition = conn.get("mass_composition")
        if composition and len(composition) > 1:
            assert sum(composition.values()) == pytest.approx(1.0, abs=1e-6), name
            mass_to_molar_fractions(composition)


# Chemical Exergy Tests
def test_calc_chemical_exergy_basic(basic_stream_data):
    """
    Test chemical exergy calculation for a simple mixture.

    Parameters
    ----------
    basic_stream_data : dict
        Fixture providing basic stream data
    """
    result = calc_chemical_exergy(basic_stream_data, 298.15, 1.01325, "Ahrendts")
    assert isinstance(result, float)
    assert result == pytest.approx(2203, abs=1)  # based on Ahrendts' model and selected substance


def test_calc_chemical_exergy_pure_substance():
    """
    Test chemical exergy calculation for a pure substance.

    Verifies
    --------
    - Pure substance handling
    - Reasonable result value
    """
    stream_data = {"mass_composition": {"O2": 1.0}}
    result = calc_chemical_exergy(stream_data, 298.15, 1.01325, "Ahrendts")
    assert isinstance(result, float)
    assert result == pytest.approx(123473, abs=1)  # based on Ahrendts' model and selected substance


def test_calc_chemical_exergy_air(air_composition):
    """
    Test chemical exergy calculation for air mixture.

    Parameters
    ----------
    air_composition : dict
        Fixture providing standard air composition

    Verifies
    --------
    - Result is within physical limits for air
    - Units are consistent
    """
    result = calc_chemical_exergy(air_composition, 298.15, 1.01325, "Ahrendts")
    assert isinstance(result, float)
    assert result == pytest.approx(-432, abs=1)  # based on Ahrendts' model and selected substance


def test_calc_chemical_exergy_invalid_substance():
    """
    Test error handling for invalid substance in chemical exergy calculation.
    """
    stream_data = {"mass_composition": {"InvalidSubstance": 0.5, "AnotherInvalid": 0.5}}
    with pytest.raises(ValueError, match="no molar mass for InvalidSubstance, AnotherInvalid"):
        calc_chemical_exergy(stream_data, 298.15, 1.01325, "Ahrendts")


# Exergy Addition Tests with Realistic Data
def test_add_chemical_exergy_realistic(realistic_json_data):
    """
    Test addition of chemical exergy to realistic process data.

    Parameters
    ----------
    realistic_json_data : dict
        Fixture providing complete process data

    Verifies
    --------
    - Chemical exergy added correctly to material streams
    - Units maintained
    - Power and heat streams unaffected
    """
    result = add_chemical_exergy(realistic_json_data, 298.15, 1.01325, "Ahrendts")

    # Check material connection
    air_conn = result["connections"]["1"]
    assert "e_CH" in air_conn
    assert "e_CH_unit" in air_conn
    assert isinstance(air_conn["e_CH"], float)

    # Check flue gas connection
    flue_gas_conn = result["connections"]["4"]
    assert "e_CH" in flue_gas_conn
    assert isinstance(flue_gas_conn["e_CH"], float)

    # Check power connection (shouldn't have chemical exergy)
    power_conn = result["connections"]["2"]
    assert "e_CH" not in power_conn


def test_chemical_exergy_zero_fractions():
    """
    Test handling of zero mass fractions.

    Verifies
    --------
    - Zero mass fractions are handled correctly
    - Result is a valid float
    """
    stream_data = {"mass_composition": {"N2": 0.0, "O2": 1.0}}
    result = calc_chemical_exergy(stream_data, 298.15, 1.01325, "Ahrendts")
    assert isinstance(result, float)


def test_add_chemical_exergy_missing_ambient(realistic_json_data):
    """
    Test error handling for missing ambient conditions.

    Parameters
    ----------
    realistic_json_data : dict
        Fixture providing complete process data

    Verifies
    --------
    - ValueError raised when ambient conditions are missing
    - Clear error message provided
    """
    # Create a copy and remove ambient conditions
    data = dict(realistic_json_data)
    data.pop("ambient_conditions")

    with pytest.raises(ValueError, match="Ambient temperature .* and pressure .* are required"):
        add_chemical_exergy(data, None, None, "Ahrendts")


def test_calc_chemical_exergy_invalid_library():
    """
    Test error handling for invalid chemical exergy library.

    Verifies
    --------
    - FileNotFoundError raised for non-existent library
    - Error message contains expected guidance
    """
    stream_data = {"mass_composition": {"O2": 1.0}}
    with pytest.raises(FileNotFoundError, match="Please ensure the file exists or set chemExLib to 'Ahrendts'"):
        calc_chemical_exergy(stream_data, 298.15, 1.01325, "InvalidLibrary")


def test_add_total_exergy_flow_realistic(realistic_json_data):
    """
    Test addition of total exergy flow with realistic process data.

    Parameters
    ----------
    realistic_json_data : dict
        Fixture providing complete process data

    Verifies
    --------
    - Total exergy calculation for all stream types
    - Proper handling of different connection kinds
    - Units consistency
    """
    result = add_total_exergy_flow(realistic_json_data, split_physical_exergy=False)

    # Check material streams
    air_conn = result["connections"]["1"]
    flue_gas_conn = result["connections"]["4"]
    assert "E" in air_conn and "E_unit" in air_conn
    assert "E" in flue_gas_conn and "E_unit" in flue_gas_conn

    # Check power stream
    power_conn = result["connections"]["2"]
    assert power_conn["E"] == power_conn["energy_flow"]

    # Check heat stream
    heat_conn = result["connections"]["3"]
    assert "E" in heat_conn
