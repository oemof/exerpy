from typing import Any

from exerpy.logger import logger
from exerpy.parser import STATE_CHECK_STEP
from exerpy.parser import state_between
from exerpy.units import convert_to_SI

from .ebsilon_config import unit_id_to_string
from .utils import require_ebsilon


@require_ebsilon
def calc_X_from_PT(app: Any, pipe: Any, property: str, pressure: float, temperature: float) -> float | None:
    """
    Calculate the enthalpy or entropy of a stream at a given pressure and temperature.

    The calculation uses the stream's own fluid data, so the composition and the property data of the
    model (steam table, gas table, real gas correction) are those Ebsilon uses for the stream itself.

    Parameters
    ----------
    app : Ebsilon application instance
        The Ebsilon application.
    pipe : Stream object
        The stream whose fluid is evaluated.
    property : str
        The thermodynamic property to calculate, either 'H' for enthalpy or 'S' for entropy.
    pressure : float
        The pressure value (in Pa).
    temperature : float
        The temperature value (in K).

    Returns
    -------
    float
        The calculated value of the specified property (in J/kg for enthalpy, J/kgK for entropy).
        Returns None if an invalid property is specified or an error occurs during calculation.

    Raises
    ------
    ValueError
        If Ebsilon returns the sentinel value -999.0 indicating a failed calculation.
    Exception
        Logs an error and returns None if any other exception occurs during property calculation.
    """
    if property not in ["S", "H"]:
        logger.error('Invalid property selected. You can choose between "H" (enthalpy) and "S" (entropy).')
        return None

    fd = pipe.FluidData()

    try:
        # Calculate the property based on the input property type
        if property == "S":  # Entropy
            res = fd.PropertyS_OF_PT(pressure * 1e-5, temperature - 273.15)  # Ebsilon works with °C and bar
            res_SI = res * 1e3  # Convert kJ/kgK to J/kgK
        elif property == "H":  # Enthalpy
            res = fd.PropertyH_OF_PT(pressure * 1e-5, temperature - 273.15)  # Ebsilon works with °C and bar
            res_SI = res * 1e3  # Convert kJ/kg to J/kg

        if res == -999.0:
            raise ValueError(
                f"Calculation with Ebsilon property failed: {property} = -999.0 "
                f"for fluid {fd.Medium} at p={pressure} Pa and T={temperature} K. "
                f"It may helpful to set split_physical_exergy=False in the ExergyAnalysis constructor."
            )

        return res_SI

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        logger.error(f"An error occurred during property calculation: {e}")
        return None


@require_ebsilon
def calc_eT(app: Any, pipe: Any, pressure: float, Tamb: float, pamb: float) -> float:
    """
    Calculate the thermal component of physical exergy.

    Parameters
    ----------
    app : Ebsilon application instance
        The Ebsilon application instance.
    pipe : Stream object
        The stream object containing thermodynamic properties.
    pressure : float
        The pressure value (in bar).
    Tamb : float
        The ambient temperature (in K).
    pamb : float
        The ambient pressure (in Pa).

    Returns
    -------
    float
        The thermal exergy component (in J/kg).
    """
    h_i = convert_to_SI("h", pipe.H.Value, unit_id_to_string.get(pipe.H.Dimension, "Unknown"))  # in SI unit [J / kg]
    s_i = convert_to_SI("s", pipe.S.Value, unit_id_to_string.get(pipe.S.Dimension, "Unknown"))  # in SI unit [J / kgK]
    h_A = calc_X_from_PT(app, pipe, "H", pressure, Tamb)  # in SI unit [J / kg]
    s_A = calc_X_from_PT(app, pipe, "S", pressure, Tamb)  # in SI unit [J / kgK]
    eT = h_i - h_A - Tamb * (s_i - s_A)  # in SI unit [J / kg]

    return eT


@require_ebsilon
def calc_eM(app: Any, pipe: Any, pressure: float, Tamb: float, pamb: float) -> float:
    """
    Calculate the mechanical component of physical exergy.

    Parameters
    ----------
    app : Ebsilon application instance
        The Ebsilon application instance.
    pipe : Stream object
        The stream object containing thermodynamic properties.
    pressure : float
        The pressure value (in bar).
    Tamb : float
        The ambient temperature (in K).
    pamb : float
        The ambient pressure (in Pa).

    Returns
    -------
    float
        The mechanical exergy component (in J/kg).
    """
    eM = convert_to_SI("e_PH", pipe.E.Value, unit_id_to_string.get(pipe.E.Dimension, "Unknown")) - calc_eT(
        app, pipe, pressure, Tamb, pamb
    )

    return eM


@require_ebsilon
def state_reproduced(app: Any, pipe: Any, pressure: float, temperature: float) -> bool:
    """
    Check that :func:`calc_X_from_PT` reproduces the enthalpy and entropy of the stream at its own state.

    Parameters
    ----------
    app : Ebsilon application instance
        The Ebsilon application.
    pipe : Stream object
        The stream to check.
    pressure : float
        The stream's pressure (in Pa).
    temperature : float
        The stream's temperature (in K).

    Returns
    -------
    bool
        Whether the stream's enthalpy and entropy lie between their values at its pressure and its
        temperature minus and plus :data:`exerpy.parser.STATE_CHECK_STEP`, see :func:`exerpy.parser.state_between`.
    """
    h = convert_to_SI("h", pipe.H.Value, unit_id_to_string.get(pipe.H.Dimension, "Unknown"))
    s = convert_to_SI("s", pipe.S.Value, unit_id_to_string.get(pipe.S.Dimension, "Unknown"))
    below, above = (
        tuple(calc_X_from_PT(app, pipe, prop, pressure, T) for prop in ("H", "S"))
        for T in (temperature - STATE_CHECK_STEP, temperature + STATE_CHECK_STEP)
    )
    return state_between(h, s, below, above)


def calc_eph_from_min(pipe: Any, Tamb: float) -> float | None:
    """
    Calculate physical exergy using the minimum-valid-temperature reference state.

    Formula:
        e_PH = h - h_min - Tamb * (s - s_min)

    Parameters
    ----------
    pipe : Any
        The Ebsilon pipe object containing thermodynamic properties.
    Tamb : float
        Ambient (reference) temperature in K.

    Returns
    -------
    Optional[float]
        Physical exergy in J/kg, or None if calculation fails.

    Notes
    -----
    - This function accesses H_Min and S_Min from the ThermoliquidExtension.
    - The minimum state (h_min, s_min) represents the enthalpy and entropy at the
      lowest valid temperature for the fluid.
    - The ambient temperature Tamb is used as the reference temperature for the
      exergy calculation, while h_min and s_min provide the reference state properties.
    - This approach is for now only suitable for ThermoLiquid fluids where conventional
      dead state properties may not be available or valid.
    """

    try:
        # 1) Get current state from the pipe
        h_i = convert_to_SI("h", pipe.H.Value, unit_id_to_string.get(pipe.H.Dimension, "Unknown"))  # J/kg
        s_i = convert_to_SI("s", pipe.S.Value, unit_id_to_string.get(pipe.S.Dimension, "Unknown"))  # J/kgK

        # 2) Get minimum state from ThermoliquidExtension
        fluid_data = pipe.FluidData()
        tl_ext = fluid_data.ThermoliquidExtension

        # Get minimum values (assuming these are in Ebsilon's standard units)
        h_min = convert_to_SI("h", tl_ext.H_Min, unit_id_to_string.get(pipe.H.Dimension, "Unknown"))  # J/kg
        s_min = convert_to_SI("s", tl_ext.S_Min, unit_id_to_string.get(pipe.S.Dimension, "Unknown"))  # J/kgK
        t_min = convert_to_SI("T", tl_ext.T_Min, unit_id_to_string.get(pipe.T.Dimension, "Unknown"))  # K

        # 3) Calculate physical exergy using Tamb as reference temperature
        e_ph = h_i - h_min - Tamb * (s_i - s_min)

        logger.info(
            f"e_PH(min) for {getattr(pipe, 'Name', '<unknown>')}: "
            f"T_min={t_min-273.15:.2f} °C, h_min={h_min:.1f} J/kg, s_min={s_min:.3f} J/kgK, "
            f"Tamb={Tamb-273.15:.2f} °C, e_PH={e_ph:.1f} J/kg"
        )

        return e_ph

    except Exception as e:
        logger.error(f"Failed to calculate e_PH from min for {getattr(pipe, 'Name', '<unknown>')}: {e}")
        return None


@require_ebsilon
def debug_substance_detection(app, pipe):
    """
    Debug helper to understand what substance/medium Ebsilon is using for a pipe.

    Parameters
    ----------
    app : IApplication
        Ebsilon application instance
    pipe : IPipe
        Pipe object to debug

    Returns
    -------
    dict
        Information about the substance detection
    """
    fluid_type_index = {
        1: "IAPWS-IF97 (Water/Steam)",
        3: "Ideal gas",
        4: "Real gas",
        6: "Numeric value",
        9: "Binary mixture",
        10: "Power/Mechanical",
        13: "Logic",
        20: "ThermoLiquid (substance 120)",
        1122: "Molten Salt (substance 122)",
    }

    result = {
        "pipe_name": pipe.Name,
        "fluid_type": pipe.FluidType,
        "fluid_type_name": fluid_type_index.get(pipe.FluidType, "Unknown"),
        "FMED": pipe.FMED.Value,
        "T": pipe.T.Value,
        "p": pipe.P.Value,
        "substance_attempts": {},
    }

    # Try to get substance properties
    try:
        # Try substance 120 (default for ThermoLiquid)
        sub120 = app.GetSubstance(120)
        result["substance_attempts"]["120"] = {
            "exists": True,
            "name": sub120.Name if hasattr(sub120, "Name") else "N/A",
        }
    except Exception as e:
        result["substance_attempts"]["120"] = {"exists": False, "error": str(e)}

    try:
        # Try substance 122 (Molten Salt)
        sub122 = app.GetSubstance(122)
        result["substance_attempts"]["122"] = {
            "exists": True,
            "name": sub122.Name if hasattr(sub122, "Name") else "N/A",
        }
    except Exception as e:
        result["substance_attempts"]["122"] = {"exists": False, "error": str(e)}

    # Try to change FMED and see what happens
    try:
        original_fmed = pipe.FMED.Value
        pipe.FMED.Value = 122  # Try to set to molten salt
        result["fmed_change_test"] = {
            "original": original_fmed,
            "attempted": 122,
            "success": pipe.FMED.Value == 122,
            "actual_value": pipe.FMED.Value,
        }
        # Restore original
        pipe.FMED.Value = original_fmed
    except Exception as e:
        result["fmed_change_test"] = {"error": str(e)}

    return result


def _get_stream_properties(pipe, T0, p0):
    """
    Get thermodynamic properties from an Ebsilon pipe.
    For molten salt and other ThermoLiquid, use Ebsilon's calculated values.
    """
    properties = {}

    # Get current state from pipe
    properties["T"] = pipe.T.Value  # °C
    properties["p"] = pipe.P.Value  # bar
    properties["m"] = pipe.M.Value  # kg/s

    # For ThermoLiquid (molten salt, thermoil, etc.), Ebsilon calculates h and s
    if pipe.FluidType == 20:
        # Use Ebsilon's enthalpy and entropy directly
        properties["h"] = pipe.H.Value  # kJ/kg
        properties["s"] = pipe.S.Value  # kJ/kgK

        # Reference state properties - need to be calculated at T0, p0
        # We'll handle this separately

    elif pipe.FluidType == 1:  # Water/Steam
        properties["h"] = pipe.H.Value
        properties["s"] = pipe.S.Value

    return properties
