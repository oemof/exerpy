def calc_X_from_PT(app, stream, property, pressure, temperature):
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

    # Add the directory containing EbsOpen.py to the system path
    sys.path.append(r"C:\Program Files\Ebsilon\EBSILONProfessional 17\Data\Python")
    from EbsOpen import EpFluidType, EpGasTable, EpSubstance, EpSteamTable
    
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

    # Create a new FluidData object
    fd = app.NewFluidData()

    # Retrieve the fluid type from the stream
    fd.FluidType = stream.FluidType

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
        
        # Iterate through the substance_mapping and get the corresponding value from the stream object
        for substance_key, ep_substance_id in substance_mapping.items():
            fraction = getattr(stream, substance_key).Value  # Dynamically access the fraction
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