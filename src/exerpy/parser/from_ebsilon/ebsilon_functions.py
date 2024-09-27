import sys 
import logging

sys.path.append(r"C:/Program Files/Ebsilon/EBSILONProfessional 17/Data/Python")

# Now you can import the required components from EbsOpen
from EbsOpen import EpSteamTable, EpGasTable

from exerpy.functions import convert_to_SI
from .ebsilon_config import unit_id_to_string, substance_mapping


def calc_X_from_PT(app, pipe, property, pressure, temperature):
    """
    General method to calculate enthalpy or entropy for any stream based on pressure and temperature.
    Automatically handles the composition of the stream.

    :param app: The Ebsilon application instance
    :param stream: The stream object
    :param property: The name of the property that is calculated
    :param pressure: Pressure (in bar)
    :param temperature: Temperature (in °C)
    :return: The value of the calculated property
    """

    # Create a new FluidData object
    fd = app.NewFluidData()

    # Retrieve the fluid type from the stream
    fd.FluidType = (pipe.Kind-1000)

    if fd.FluidType == 3:  # steam
        fd.SteamTable = EpSteamTable.epSteamTableIAPWS_IF97      # IF97 steamtable
        fdAnalysis = app.NewFluidAnalysis()

    elif fd.FluidType == 4:  # water
        fdAnalysis = app.NewFluidAnalysis()

    else:  # flue gas, air etc.
        # Get the data for flue gases from FDBR gas table
        fd.GasTable = EpGasTable.epGasTableFDBR

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

