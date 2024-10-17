"""
Ebsilon Configuration Data

This script contains the configuration data used by the Ebsilon model parser, 
including lists of component types, fluid types, fluid composition parameters, 
and groups for sorting components into functional categories.
"""

import sys 
import os 
import logging

ebs_path = os.getenv("EBS")
if not ebs_path:
    logging.error("Ebsilon path not found. Please set an environment variable named EBS with the path to your Ebsilon Python program files as the value. For example: 'C:\\Program Files\\Ebsilon\\EBSILONProfessional 17\\Data\\Python'")
    sys.exit(1)

sys.path.append(ebs_path)
from EbsOpen import EpSubstance

# Dictionary mapping Ebsilon component numbers to their label
ebs_objects = {
    1: "Boundary Input Value",
    2: "Throttle",
    3: "Mixer with Throttle",
    4: "Splitter (Mass defined)",
    5: "Steam Generator (Boiler)",
    6: "Steam Turbine / General expander",
    7: "Steam Turbine Condenser",
    8: "Pump (fixed speed)",
    9: "Feed Water Container / De Aerator",
    10: "Feed Water Preheater / Heating Condenser",
    11: "Generator",
    12: "Controller (with external default value)",
    13: "Piping",
    14: "Control Valve",
    15: "Heat Extraction",
    16: "Heat Injection",
    17: "Splitter (with characteristic line)",
    18: "Splitter with ratio specification",
    19: "Drain",
    20: "Steam Drum",
    21: "Combustion Chamber with Heat Output",
    22: "Combustion Chamber of Gas Turbine",
    23: "Gas turbine (Turbine only)",
    24: "Compressor / Fan",
    25: "Air Preheater",
    26: "Economizer / Evaporator / Super Heater (with characteristic lines)",
    27: "Aftercooler",
    28: "Tank (mixing point)",
    29: "Motor",
    30: "Difference Meter",
    31: "Power Summarizer",
    32: "Efficiency Meter",
    33: "Start Value",
    34: "Expander",
    35: "Heat Consumer",
    36: "Value Transmitter",
    37: "Simple Mixer",
    38: "Water Injection",
    39: "Controller (Type 2: internal set value)",
    40: "Gas Turbine (Macro, simple characteristic lines)",
    41: "Duct Burner (for waste-heat boiler)",
    42: "Condensate Valve",
    43: "Desuperheater",
    44: "Extraction Pump",
    45: "Value Indicator",
    46: "Value Input (Measuring Point)",
    47: "Wet Cooling Tower (with Klenke coefficients)",
    48: "Value Transmitter Switch",
    49: "Three Way Valve",
    50: "Coal Gasifier",
    51: "High Temperature Heat Exchanger",
    52: "Selective Splitter (Filter)",
    53: "Water Saturizer of Gas Streams",
    54: "Drain of Gas Streams",
    55: "Universal Heat Exchanger",
    56: "Steam Turbine (extended)",
    57: "Gas Turbine (detailed characteristic field)",
    58: "Governing Stage (nozzle section control)",
    59: "Control Valve (Ffed pressure limit)",
    60: "General Mixer",
    61: "Economizer/Evaporator/Superheater (with exponents)",
    62: "DUPLEX Heat Exchanger",
    63: "Feed Water Tank / Deaerator (extended)",
    64: "Debug Switch - outdated!",
    65: "Programmable Component",
    66: "Feed Water Preheater with Measurement Input- outdated!",
    67: "Condenser with Measurement Input- outdated!",
    68: "Control Valve (external pressure limit)",
    69: "Controller (external set value and switch)",
    70: "Evaporator with Steam Drum",
    71: "Heat Exchanger (once through boiler)",
    72: "Gas Turbine with Warranty Calculation- outdated!",
    73: "Economizer/Evaporator/Superheater (finned tubes)",
    74: "Block Heating Power Plant (BHPP)",
    75: "Air Cooled Condenser (with polynomial)",
    76: "Alstom Reheat Gas Turbine (DLL required)",
    77: "Calculator",
    78: "Natural Draft Cooling Tower (with characteristic field)",
    79: "Forced Draft Cooling Tower (with characteristic field)",
    80: "Separator (logical)",
    81: "Pipe Coupling",
    82: "Fuel Cell",
    83: "Pump (variable speed)",
    84: "Coal Dehumidifier",
    85: "Electrostatic Precipitator",
    86: "SCR-DeNOX-Plant (NOX-removal)",
    87: "Boiler Efficiency Meter according to DIN EN 12952-15 8.4",
    88: "Flue Gas Zone of Steam Generator",
    89: "Main Heating Surface of Steam Generator",
    90: "Reaction Zone of Steam Generator",
    91: "Auxiliary Heating Surface of Steam Generator",
    92: "Desalination - MSF-Stage",
    93: "Kernel Scripting",
    94: "Compressor or Fan (with characteristic field)",
    95: "Reformer / Shift Reactor",
    96: "Extended Coal Gasifier",
    97: "Extended Saturizer",
    98: "Evaporator for Binary Mixtures",
    99: "Separator for Binary Mixtures",
    100: "Fluid Converter",
    101: "Fluid Reconverter",
    102: "Mixer with Specified Concentration",
    103: "Absorber",
    104: "Coupled Rectifying Column",
    105: "Library Specification",
    106: "ENEXSA Gas Turbine (OEM GT)",
    107: "Condenser for Binary Mixtures",
    108: "Elementary Analyzer",
    109: "Selective Splitter for Universal Fluid",
    110: "Mass Multiplier",
    111: "Natural Draft Cooling Tower (Merkel)",
    112: "Forced Draft Cooling Tower (Merkel)",
    113: "Line Focusing Solar Collector",
    114: "Distributing Header",
    115: "Collecting Header",
    116: "Solar Field",
    117: "The Sun (environmental data)",
    118: "Direct Storage",
    119: "Indirect Storage",
    120: "Solar Tower Receiver",
    121: "Heliostat Field",
    122: "Steam Turbine (SCC)",
    123: "Shaft Sealing",
    124: "Heat Exchanger with Phase Transition",
    125: "Diesel / Gas Motor (reciprocating engine)",
    126: "Transient Heat Exchanger",
    127: "Air Cooled Condenser / Air-Cooled Fluid Cooler",
    128: "Hard Coal Mill",
    129: "Lignite Mill",
    130: "PID-Controller",
    131: "Transient Separator",
    132: "Automatic Connector",
    133: "Control Valve with Flow Coefficient KV",
    134: "Gibbs Reactor (equilibrium calculation)",
    135: "Stack",
    136: "Emission Display",
    137: "PV System",
    138: "Dynamic Piping",
    139: "Steam Generator with 2 Reheats",
    140: "Splitter with 3 Outlets",
    141: "Mixer with 3 Inlets",
    142: "Wind Data",
    143: "Wind Turbine",
    144: "Multivalue Transmitter",
    145: "Stratified Storage",
    146: "Gearbox/Bearing",
    147: "Limiter",
    148: "Header Admission",
    149: "Header Extraction",
    150: "Header Connecting Pipe",
    151: "Evaporative Cooler",
    152: "Electric Compression Chiller",
    153: "ENEXSA Reciprocating Engine (Library)",
    154: "Steam Jet Vacuum Pump",
    155: "Transformer",
    156: "Power Converter",
    157: "Phase Splitter (TREND)",
    158: "Battery",
    159: "Map Based Compressor",
    160: "Storage for Compressible Fluids",
    161: "Injection with Temperature Control",
    162: "Electric Boiler",
    163: "Fuel Cell",
    164: "Map Based Turbine",
    165: "Thermal Regenerator / Bulk Material Storage",
    166: "Phase Change Material Storage",
    167: "Electrolysis Cell",
    168: "Quantity Converter",
    169: "Biomass Gasifier"
}

# Neglected components
non_thermodynamic_unit_operators = [
    1,   # Boundary Input Value
    12,  # Controller (with external default value)
    30,  # Difference Meter
    31,  # Power Summarizer
    32,  # Efficiency Meter
    33,  # Start Value
    36,  # Value Transmitter
    39,  # Controller (Type 2: internal set value)
    45,  # Value Indicator
    46,  # Value Input (Measuring Point)
    48,  # Value Transmitter Switch
    64,  # Debug Switch - outdated!
    65,  # Programmable Component
    66,  # Feed Water Preheater with Measurement Input- outdated!
    67,  # Condenser with Measurement Input- outdated!
    69,  # Controller (external set value and switch)
    77,  # Calculator
    80,  # Separator (logical)
    93,  # Kernel Scripting
    105, # Library Specification
    108, # Elementary Analyzer
    110, # Mass Multiplier
    117, # The Sun (environmental data)
    130, # PID-Controller
    132, # Automatic Connector
    136, # Emission Display
    142, # Wind Data
    144, # Multivalue Transmitter
    147, # Limiter
    168  # Quantity Converter
]

# Fluid types of Ebsilon
fluid_type_index = {
    0: "None",                  # epFluidTypeNONE
    1: "Air",                   # epFluidTypeAir
    2: "Fluegas",               # epFluidTypeFluegas
    3: "Steam",                 # epFluidTypeSteam
    4: "Water",                 # epFluidTypeWater
    5: "Scheduled",             # epFluidTypeScheduled
    6: "Actual",                # epFluidTypeActual
    7: "Crudegas",              # epFluidTypeCrudegas
    8: "Oil",                   # epFluidTypeOil
    9: "Electric",              # epFluidTypeElectric
    10: "Shaft",                # epFluidTypeShaft
    11: "Coal",                 # epFluidTypeCoal
    12: "Gas",                  # epFluidTypeGas
    13: "Logic",                # epFluidTypeLogic
    14: "User",                 # epFluidTypeUser
    15: "2PhaseLiquid",         # epFluidType2PhaseLiquid
    16: "2PhaseGaseous",        # epFluidType2PhaseGaseous
    17: "Saltwater",            # epFluidTypeSaltwater
    18: "UniversalFluid",       # epFluidTypeUniversalFluid
    19: "BinaryMixture",        # epFluidTypeBinaryMixture
    20: "ThermoLiquid",         # epFluidTypeThermoLiquid
    21: "HumidAir",             # epFluidTypeHumidAir
    22: "NASA"                  # epFluidTypeNASA
}

# Mapping fluid types to categories
connection_kinds = {
    "Air": "material",
    "Fluegas": "material",
    "Steam": "material",
    "Water": "material",
    "Crudegas": "material",
    "Oil": "material",
    "Coal": "material",
    "Gas": "material",
    "2PhaseLiquid": "material",
    "2PhaseGaseous": "material",
    "Saltwater": "material",
    "UniversalFluid": "material",
    "BinaryMixture": "material",
    "ThermoLiquid": "material",
    "HumidAir": "material",
    "Electric": "power",
    "Shaft": "power",
    "Logic": "heat"
}

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


unit_id_to_string = {
    0: "INVALID",
    1: "NONE",
    2: "1",
    3: "bar",
    4: "C",
    5: "kJ / kg",
    6: "kg / s",
    7: "kW",
    8: "m3 / kg",
    9: "m3 / s",
    12: "K",
    13: "kmol / kmol",
    14: "kg / kg",
    15: "kW / K",
    16: "W / m2K",
    17: "1 / min",
    18: "kJ / kWh",
    21: "kJ / m3",
    22: "kJ / m3K",
    23: "kg / m3",
    24: "m",
    26: "kJ / kgK",
    27: "m2",
    28: "kJ / kgK",
    29: "kg / kg",
    30: "kg / kg",
    31: "kg / kmol",
    32: "kJ / kg",
    33: "m / s",
    34: "kg / kg",
    35: "FTYP_8",
    36: "FTYP_9",
    37: "mg / Nm3",
    38: "EUR / h",
    39: "kW / kg",
    40: "1 / m6",
    41: "A",
    42: "EUR / kWh",
    43: "EUR / kg",
    44: "V",
    45: "m3 / m3",
    46: "kg",
    47: "EUR",
    48: "m3",
    49: "ph",
    51: "m2K / W",
    52: "W / m2",
    53: "TEXT",
    54: "Grd",
    55: "kVA",
    56: "kVAr",
    57: "kg / ms",
    58: "W / mK",
    59: "m / geopot",
    60: "1 / Grd",
    61: "1 / Grd2",
    62: "1 / Grd3",
    63: "1 / Grd4",
    64: "1 / Grd5",
    65: "1 / K",
    66: "1 / K2",
    67: "1 / K3",
    68: "1 / K4",
    69: "W / m",
    70: "s",
    71: "K / m",
    72: "kJ / kgm",
    73: "datetime",
    74: "kW / kgK",
    75: "bar / m",
    76: "mN / m",
    77: "W / mK2",
    78: "W / mK3",
    79: "W / mK4",
    80: "m / K",
    81: "m / K2",
    82: "m2 / s",
    83: "kJ",
    84: "Nm3 / s",
    85: "kg / m3K",
    86: "kJ / kgK2",
    87: "kg2 / kJs",
    88: "INTEGRAL",
    89: "W / mC",
    90: "W / mC2",
    91: "W / mC3",
    92: "W / mC4",
    93: "m / C",
    94: "m / C2",
    95: "bars / kg",
    96: "barkg / kJ",
    97: "barK / kW",
    98: "N",
    99: "1 / m",
    100: "m2 / W",
    101: "kJ / Nm3",
    102: "PATH",
    103: "FOLDER",
    104: "KERNELEXPRESSION",
    105: "kJ / mol",
    106: "mSQRT / K / W",
    107: "A / K",
    108: "V / K",
    109: "Ohm",
    110: "Farad",
    111: "Henry",
    112: "Nm",
    113: "kJ / m2",
    114: "W / m3",
    115: "1 / W",
    116: "1 / V",
    117: "STRING",
    118: "Coul",
    119: "A / Ah",
    120: "mol / s",
    121: "m3 / K",
    122: "1 / Coul",
    123: "1 / J",
    124: "1 / s",
    125: "kW / A",
    126: "S / m",
    127: "S / m2",
    128: "A / m2",
    129: "SK / m",
    130: "m2 / kg",
    131: "SK / m2",
    132: "m2 / s",
    133: "VARIANT",
    134: "kJ / kmolK",
    135: "kJ / kgK",
    136: "mol",
    137: "K / bar",
    138: "kg / m2"
}


# List of fluid composition materials to include in the JSON file
composition_params = [
    'X12BUTADIEN', 'X13BUTADIEN', 'X1BUTEN', 'X1PENTEN', 'X22DMBUT',
    'X23DMBUT', 'X3MPENT', 'XACET', 'XAIR', 'XAR', 'XASH', 'XASHG',
    'XBENZ', 'XBUT', 'XC', 'XC2BUTEN', 'XCA', 'XCACO3', 'XCAO', 'XCASO4',
    'XCDECALIN', 'XCH3SH', 'XCH4', 'XCL', 'XCO', 'XCO2', 'XCOS', 'XCS2',
    'XCYCHEX', 'XCYCPENT', 'XDEC', 'XDODEC', 'XEBENZ', 'XECYCHEX',
    'XECYCPENT', 'XETH', 'XETHEN', 'XETHL', 'XH', 'XH2', 'XH2O', 'XH2OB',
    'XH2OG', 'XH2OL', 'XH2S', 'XHCL', 'XHCN', 'XHE', 'XHEPT', 'XHEX',
    'XI', 'XIBUT', 'XIBUTEN', 'XIHEX', 'XIPENT', 'XKR', 'XLIME', 'XL_CO2',
    'XL_H2O', 'XL_NH3', 'XMCYCHEX', 'XMCYCPENT', 'XMETHL', 'XMG',
    'XMGCO3', 'XMGO', 'XN', 'XN2', 'XN2O', 'XNE', 'XNEOPENT', 'XNH3',
    'XNO', 'XNO2', 'XNON', 'XO', 'XO2', 'XOCT', 'XOXYLEN', 'XPENT',
    'XPROP', 'XPROPADIEN', 'XPROPEN', 'XS', 'XSO2', 'XT2BUTEN',
    'XTDECALIN', 'XTOLUEN', 'XXE'
]

# Define the component groups via unique labels
grouped_components = {
    "Turbine": [6, 23, 34, 56, 57, 122],
    "HeatExchanger": [5, 10, 15, 16, 25, 26, 27, 43, 51, 55, 61, 62, 70, 71, 124, 126],
    "CombustionChamber": [21, 22, 90],
    "Valve": [2, 14, 39, 42, 59, 68, 133],
    "Pump": [8, 44, 83, 159],
    "Compressor": [24, 94],
    "Condenser": [7, 47, 78],
    "Deaerator": [9, 63],
    "SimpleHeatExchanger": [35],
    "Mixer": [3, 37, 38, 49, 60, 102, 141, 161]
}

# Connector mapping rules for different component types
connector_mapping = {
    22: {  # Combustion Chamber of Gas Turbine
        1: 0,  # Inlet air
        2: 0,  # Outlet combustion gas
        3: 2,  # Inlet secondary air
        4: 1,  # Inlet fuel gas
    },
    24: {  # Compressor / Fan
        1: 0,  # Connector 1 in Ebsilon is inlet(0)
        2: 0,  # Connector 2 in Ebsilon is outlet(0)
    },
    8: {  # Pump
        1: 0,  # Connector 1 in Ebsilon is inlet(0)
        2: 0,  # Connector 2 in Ebsilon is outlet(0)
    },
    23: {  # Gas turbine (Turbine only)
        1: 0,  # Connector 1 in Ebsilon is inlet(0)
        2: 0,  # Connector 2 in Ebsilon is outlet(0)
    },
    6: {  # Steam turbine
        1: 0,  # Connector 1 in Ebsilon is inlet(0)
        2: 0,  # Connector 2 in Ebsilon is outlet(0)
        3: 1,  # Connector 3 in Ebsilon is outlet(1): 1st extraction
        4: 2,  # Connector 4 in Ebsilon is outlet(2): 2nd extraction
    },
    11: {  # Generator
        1: 0,  # Connector 1 in Ebsilon is inlet(0)
        2: 0,  # Connector 2 in Ebsilon is outlet(0)
    },
    29: {  # Motor
        1: 0,  # Connector 1 in Ebsilon is inlet(0)
        2: 0,  # Connector 2 in Ebsilon is outlet(0)
    },
    55: {  # Universal Heat Exchanger
        1: 1,  # Inlet cold stream
        2: 1,  # Outlet cold stream
        3: 0,  # Inlet hot stream
        4: 0,  # Outlet hot stream
        5: 2,  # Second outlet hot stream (if present)
    },
    25: {  # Air Preheater
        1: 1,  # Inlet cold stream
        2: 1,  # Outlet cold stream
        3: 0,  # Inlet hot stream
        4: 0,  # Outlet hot stream
    },
    7: {  # Condenser
        1: 1,  # Inlet cold stream
        2: 1,  # Outlet cold stream
        3: 0,  # Inlet hot stream
        4: 0,  # Outlet hot stream
        5: 2,  # Second outlet hot stream (if present)
    },
    9: {  # Feed Water Container / De Aerator
        1: 0,  # Inlet boiling water
        2: 0,  # Outlet condensate stream
        3: 1,  # Inlet steam
        4: 2,  # Inlet secondary condensate
        5: 1,  # Outlet steam losses (if present)
    },
    35: {  # Heat Consumer / Simple Heat Exchanger
        1: 0,  # Inlet (hot) stream
        2: 0,  # Outlet (cold) stream
        3: 1,  # Outlet heat flow
    },
    37: {  # Simple Mixer
        1: 0,  # Inlet 1
        2: 0,  # Outlet
        3: 1,  # Inlet 2
    },
    70: {  # Evaporator
        1: 1,  # Inlet cold stream
        2: 1,  # Outlet cold stream
        3: 0,  # Inlet hot stream
        4: 0,  # Outlet hot stream
        5: 2,  # Second outlet cold stream (if present)
    },
    26: {  # Economizer / Superheater
        1: 1,  # Inlet cold stream
        2: 1,  # Outlet cold stream
        3: 0,  # Inlet hot stream
        4: 0,  # Outlet hot stream
    },
    90: {  # Reaction Zone of Steam Generator
        1: 2,  # Inlet secondary flue gas
        2: 0,  # Outlet combustion gas
        3: 2,  # Wall heat losses
        4: 3,  # Inlet ashes
        5: 1,  # Outlet ashes
        6: 3,  # Irradiation losses above
        7: 4,  # Irradation losses below
        8: 0,  # Inlet air
        9: 1,  # Inlet fuel gas
    }
    # ...
    # ...
    # Add more mappings for other component types as needed
    # ...
    # ...
}
