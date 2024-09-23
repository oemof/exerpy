import sys 

sys.path.append(r"C:/Program Files/Ebsilon/EBSILONProfessional 17/Data/Python")

# Now you can import the required components from EbsOpen
from EbsOpen import EpSteamTable, EpGasTable, EpSubstance

# Dictionary mapping stream substance names to EpSubstance identifiers
substance_mapping = {
    "XN2": EpSubstance.epSubstanceN2,
    "XO2": EpSubstance.epSubstanceO2,
    "XCO2": EpSubstance.epSubstanceCO2,
    "XH2O": EpSubstance.epSubstanceH2O,
    "XAR": EpSubstance.epSubstanceAR,
    "XSO2": EpSubstance.epSubstanceSO2,
    "XCO": EpSubstance.epSubstanceCO,
    "XCH4": EpSubstance.epSubstanceCH4,
    "XH2S": EpSubstance.epSubstanceH2S,
    "XH2": EpSubstance.epSubstanceH2,
    "XNH3": EpSubstance.epSubstanceNH3,
    "XNO": EpSubstance.epSubstanceNO,
    "XNO2": EpSubstance.epSubstanceNO2,
    "XC": EpSubstance.epSubstanceC,
    "XS": EpSubstance.epSubstanceS,
    "XCL": EpSubstance.epSubstanceCL,
    "XASH": EpSubstance.epSubstanceASH,
    "XLIME": EpSubstance.epSubstanceLIME,
    "XCA": EpSubstance.epSubstanceCA,
    "XCAO": EpSubstance.epSubstanceCAO,
    "XCACO3": EpSubstance.epSubstanceCACO3,
    "XCASO4": EpSubstance.epSubstanceCASO4,
    "XMG": EpSubstance.epSubstanceMG,
    "XMGO": EpSubstance.epSubstanceMGO,
    "XMGCO3": EpSubstance.epSubstanceMGCO3,
    "XHCL": EpSubstance.epSubstanceHCL,
    "XHCN": EpSubstance.epSubstanceHCN,
    "XCS2": EpSubstance.epSubstanceCS2,
    "XH2OB": EpSubstance.epSubstanceH2OB,
    "XN2O": EpSubstance.epSubstanceN2O,
    "XHE": EpSubstance.epSubstanceHE,
    "XNE": EpSubstance.epSubstanceNE,
    "XKR": EpSubstance.epSubstanceKR,
    "XXE": EpSubstance.epSubstanceXE,
    "XASHG": EpSubstance.epSubstanceASHG,
    "XACET": EpSubstance.epSubstanceACET,
    "XBENZ": EpSubstance.epSubstanceBENZ,
    "XC2BUTEN": EpSubstance.epSubstanceC2BUTEN,
    "XCYCPENT": EpSubstance.epSubstanceCYCPENT,
    "XDEC": EpSubstance.epSubstanceDEC,
    "XEBENZ": EpSubstance.epSubstanceEBENZ,
    "XETH": EpSubstance.epSubstanceETH,
    "XETHL": EpSubstance.epSubstanceETHL,
    "XH": EpSubstance.epSubstanceH,
    "XO": EpSubstance.epSubstanceO,
    "XMETHL": EpSubstance.epSubstanceMETHL,
    "XNEOPENT": EpSubstance.epSubstanceNEOPENT,
    "XTOLUEN": EpSubstance.epSubstanceTOLUEN,
    "XIBUT": EpSubstance.epSubstanceIBUT,
    "XIPENT": EpSubstance.epSubstanceIPENT,
    "XIBUTEN": EpSubstance.epSubstanceIBUTEN,
    "X1BUTEN": EpSubstance.epSubstance1BUTEN,
    "X3MPENT": EpSubstance.epSubstance3MPENT,
    "XPROP": EpSubstance.epSubstancePROP,
    "XPROPEN": EpSubstance.epSubstancePROPEN,
    "XHEX": EpSubstance.epSubstanceHEX,
    "XHEPT": EpSubstance.epSubstanceHEPT,
    "XOXYLEN": EpSubstance.epSubstanceOXYLEN,
    "XTDECALIN": EpSubstance.epSubstanceTDECALIN,
    "XT2BUTEN": EpSubstance.epSubstanceT2BUTEN
}

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
    fd.FluidType = pipe.Kind-1000

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
    
    # Calculate property at the given pressure and temperature
    if property == 'S':
        res = fd.PropertyS_OF_PT(pressure, temperature)
    elif property == 'H':
        res = fd.PropertyH_OF_PT(pressure, temperature)
    else:
        print('Wrong property. You can choose between "H" (enthalpy) and "S" (entropy)')
        res = None
    return res


def calc_eT(app, pipe, pressure):
    hA = calc_X_from_PT(app, pipe, 'H', pressure, 15)
    sA = calc_X_from_PT(app, pipe, 'S', pressure, 15)
    eT = pipe.H - hA - (15+273.15) * (pipe.S - sA)

    return eT

def calc_eM(app, pipe, pressure):
    eM = pipe.E - calc_eT(app, pipe, pressure)

    return eM

def add_eT_eM_to_stream(app, json_data):
    """
    Adds e_M and e_T to all material connections in the provided JSON data.
    
    :param app: The Ebsilon application instance
    :param json_data: The JSON data containing connections and their properties
    :return: Updated JSON data with added e_M and e_T properties for each connection
    """
    # Define fluid types that are considered non-material
    non_material_fluids = {5, 6, 9, 10, 13}  # Scheduled, Actual, Electric, Shaft, Logic

    # Loop over all connections in the JSON data
    for connection_name, connection_data in json_data['connections'].items():
        try:
            # Check if the fluid_type_id is not in the non-material fluids
            if connection_data['fluid_type_id'] not in non_material_fluids:
                # Retrieve eT and eM values using the calc_eT and calc_eM functions
                e_T = calc_eT(app, connection_data, connection_data['p'])  # Assuming 'p' is available in the connection data
                e_M = calc_eM(app, connection_data, connection_data['p'])  # Assuming 'p' is available in the connection data

                # Add these values to the connection's data
                connection_data['e_T'] = e_T
                connection_data['e_M'] = e_M

        except Exception as e:
            # Log any errors encountered while processing a connection
            print(f"Error processing connection {connection_name}: {e}")
    
    return json_data

'''def calc_chemical_exergy(stream, chem_ex_model):
    
    from src.exerpy.functions import mass_to_molar_fractions

    molar_fractions = mass_to_molar_fractions(stream['composition'])
    if molar_fractions['XH2O'] > 0:
        x_liquid = molar_fractions['XH2O']
        x_gas = 1 - x_liquid
    else:
        pass'''