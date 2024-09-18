"""
Ebsilon Configuration Data

This script contains the configuration data used by the Ebsilon model parser, 
including lists of component types, fluid types, fluid composition parameters, 
and groups for sorting components into functional categories.
"""

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
    -1: "Undefined",      # undefined Value
    0: "Steam",           # No material composition required
    1: "Fluegas",         # Fluegas or Air
    2: "Gas",             # Gas
    3: "Coal",            # Coal
    4: "Crudegas",        # Crudegas
    5: "Oil",             # Oil
    6: "User",            # User
    7: "2Phase",          # 2phase
    8: "Saltwater",       # Saltwater
    9: "BinaryMixture",   # BinaryMixture
    10: "UniversalFluid", # UniversalFluid
    11: "ThermoLiquid",   # ThermoLiquid
    12: "HumidAir",       # HumidAir
    13: "NASA"            # NASA
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
    "CombustionChamber": [21, 22],
    "Valve": [2, 14, 39, 42, 59, 68, 133],
    "Pump": [8, 44, 83, 159],
    "Compressor": [24, 94],
    "Condenser": [7, 47, 78]
}

# Connector mapping rules for different component types
connector_mapping = {
    22: {  # Combustion Chamber of Gas Turbine
        1: 0,
        2: 0,
        3: 2,
        4: 1,
    },
    24: {  # Compressor / Fan
        1: 0,
        2: 0,
    },
    23: {  # Gas turbine (Turbine only)
        1: 0,
        2: 0,
    },
    55: {  # Universal Heat Exchanger
        1: 0,
        3: 1,
        2: 0,
        4: 1,
        5: 3,
    },
    # Add more mappings for other component types as needed
}
