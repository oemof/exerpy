import sys
import os
import logging

from CoolProp.CoolProp import PropsSI as CP

ebs_path = os.getenv("EBS")
if not ebs_path:
    logging.error("Ebsilon path not found. Please set an environment variable named EBS with the path to your Ebsilon Python program files as the value. For example: 'C:\\Program Files\\Ebsilon\\EBSILONProfessional 17\\Data\\Python'")

else:
    sys.path.append(ebs_path)
    from EbsOpen import EpSteamTable, EpGasTable

from exerpy.functions import convert_to_SI
from .ebsilon_config import unit_id_to_string, substance_mapping


def calc_X_from_PT(app, pipe, property, pressure, temperature):
    """
    Calculate a thermodynamic property (enthalpy or entropy) for a given stream based on pressure and temperature.

    This method takes pressure and temperature values and calculates the specified property for any fluid stream. 
    It automatically handles the composition of the stream by setting up appropriate fluid properties and analysis
    parameters based on the stream's fluid type and composition.

    Parameters
    ----------
    app : Ebsilon application instance
        The Ebsilon application used for creating fluid and analysis objects.
    pipe : Stream object
        The stream object containing fluid and composition information.
    property : str
        The thermodynamic property to calculate, either 'H' for enthalpy or 'S' for entropy.
    pressure : float
        The pressure value (in bar).
    temperature : float
        The temperature value (in °C).

    Returns
    -------
    float
        The calculated value of the specified property (in J/kg for enthalpy, J/kgK for entropy).
        Returns None if an invalid property is specified or an error occurs during calculation.

    Raises
    ------
    Exception
        Logs an error and returns None if any exception occurs during property calculation.
    """

    # Create a new FluidData object
    fd = app.NewFluidData()

    # Retrieve the fluid type from the stream
    fd.FluidType = (pipe.Kind-1000)

    if fd.FluidType == 3 or fd.FluidType == 4:  # steam or water
            t_sat = CP('T', 'P', pressure, 'Q', 0, 'water')
            if temperature > t_sat:
                fd.FluidType = 3  # steam
                fd.SteamTable = EpSteamTable.epSteamTableFromSuperiorModel
                fdAnalysis = app.NewFluidAnalysis()
            else:
                fd.FluidType == 4  # water
                fdAnalysis = app.NewFluidAnalysis()

    elif fd.FluidType == 15:  # 2PhaseLiquid
        fd.Medium = pipe.FMED.Value
        fdAnalysis = app.NewFluidAnalysis()

    elif fd.FluidType == 16:  # 2PhaseGaseous
        fd.Medium = pipe.FMED.Value
        fdAnalysis = app.NewFluidAnalysis()

    else:  # flue gas, air etc.
        fd.GasTable = EpGasTable.epGasTableFromSuperiorModel

        # Set up the fluid analysis based on stream composition
        fdAnalysis = app.NewFluidAnalysis()

        # Iterate through the substance_mapping and get the corresponding value from the pipe
        for substance_key, ep_substance_id in substance_mapping.items():
            fraction = getattr(pipe, substance_key).Value  # Dynamically access the fraction
            if fraction > 0:  # Only set substances with non-zero fractions
                fdAnalysis.SetSubstance(ep_substance_id, fraction)

    # Set the analysis in the FluidData object
    fd.SetAnalysis(fdAnalysis)

    # Validate property input
    if property not in ['S', 'H']:
        logging.error('Invalid property selected. You can choose between "H" (enthalpy) and "S" (entropy).')
        return None

    try:
        # Calculate the property based on the input property type
        if property == 'S':  # Entropy
            res = fd.PropertyS_OF_PT(pressure * 1e-5, temperature - 273.15)  # Ebsilon works with °C and bar
            res_SI = res * 1e3  # Convert kJ/kgK to J/kgK
        elif property == 'H':  # Enthalpy
            res = fd.PropertyH_OF_PT(pressure * 1e-5, temperature - 273.15)  # Ebsilon works with °C and bar
            res_SI = res * 1e3  # Convert kJ/kg to J/kg

        return res_SI

    except Exception as e:
        logging.error(f"An error occurred during property calculation: {e}")
        return None



def calc_eT(app, pipe, pressure, Tamb, pamb):
    h_i = convert_to_SI('h', pipe.H.Value, unit_id_to_string.get(pipe.H.Dimension, "Unknown"))  # in SI unit [J / kg]
    s_i = convert_to_SI('s', pipe.S.Value, unit_id_to_string.get(pipe.S.Dimension, "Unknown"))  # in SI unit [J / kgK]
    h_A = calc_X_from_PT(app, pipe, 'H', pressure, Tamb)  # in SI unit [J / kg]
    s_A = calc_X_from_PT(app, pipe, 'S', pressure, Tamb)  # in SI unit [J / kgK]
    eT = h_i - h_A - Tamb * (s_i - s_A)  # in SI unit [J / kg]

    return eT

def calc_eM(app, pipe, pressure, Tamb, pamb):
    eM = convert_to_SI('e', pipe.E.Value, unit_id_to_string.get(pipe.E.Dimension, "Unknown")) - calc_eT(app, pipe, pressure, Tamb, pamb)

    return eM
