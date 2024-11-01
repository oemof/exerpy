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
    EpSubstance = None

else:
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
if EpSubstance is not None:
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

# ebsilon_config.py

# Mapping dictionary for fluid types to their mass composition.
two_phase_fluids_mapping = {
    -1: {"NH3": 1},  # LIBNH3_NH3
    -2: {"H2O": 1},  # LIBICE_H2O
    -3: {"CO2": 1},  # LIBCO2_CO2
    -4: {"N-Butane": 1},  # LIBBUTAN_N_NBUTAN
    -5: {"Iso-Butane": 1},  # LIBBUTAN_ISO_IBUT
    -6: {"Methanol": 1},  # LIBCH3OH_METHL
    -7: {"Ethanol": 1},  # LIBC2H5OH_ETHL
    -8: {"D4": 1},  # LIBD4_D4
    -9: {"D5": 1},  # LIBD5_D5
    -10: {"D6": 1},  # LIBD6_D6
    -11: {"H2": 1},  # LIBH2_H2
    -12: {"Parahydrogen": 1},  # LIBH2_PARAHYD
    -13: {"HE": 1},  # LIBHE_HE
    -14: {"MDM": 1},  # LIBMDM_MDM
    -15: {"MD2M": 1},  # LIBMD2M_MD2M
    -16: {"MD3M": 1},  # LIBMD3M_MD3M
    -17: {"MD4M": 1},  # LIBMD4M_MD4M
    -18: {"MM": 1},  # LIBMM_MM
    -19: {"N2": 1},  # LIBN2_N2
    -20: {"Propane": 1},  # LIBPROPAN_PROP
    -21: {"R134a": 1},  # LIBR134A_R134A
    -22: {"Air": 1},  # LIBREALAIR_AIR_Lemmon
    -23: {"Acetone": 1},  # LIBC3H6O_ACETONE
    -24: {"Cyclopentane": 1},  # LIBC5H10_CYCPENT
    -25: {"Iso-Pentane": 1},  # LIBC5H12_ISO_IPENT
    -26: {"Neopentane": 1},  # LIBC5H12_NEO_NEOPENT
    -27: {"Iso-Hexane": 1},  # LIBC6H14_IHEX
    -28: {"Toluene": 1},  # LIBC7H8_TOLUEN
    -29: {"Nonane": 1},  # LIBC9H20_NON
    -30: {"Decane": 1},  # LIBC10H22_DEC
    -31: {"CO": 1},  # LIBCO_CO
    -32: {"COS": 1},  # LIBCOS_COS
    -33: {"H2S": 1},  # LIBH2S_H2S
    -34: {"N2O": 1},  # LIBN2O_N2O
    -35: {"SO2": 1},  # LIBSO2_SO2
    -36: {"H2O": 1},  # LIBIF97_H2O
    -37: {"H2O": 1},  # IFC67_H2O
    -38: {"H2O": 1},  # LIBIF97_SBTL_H2O
    -39: {"O2": 1},  # LIBO2_O2
    -1000: {"1-Butene": 1},  # REFPROP_1BUTEN
    -1001: {"Acetone": 1},  # REFPROP_ACETONE
    -1002: {"Air": 1},  # REFPROP_AIR_Lemmon
    -1003: {"NH3": 1},  # REFPROP_NH3
    -1004: {"Ar": 1},  # REFPROP_AR
    -1005: {"Benzene": 1},  # REFPROP_BENZENE
    -1006: {"Butane": 1},  # REFPROP_BUT
    -1007: {"Dodecane": 1},  # REFPROP_DODEC
    -1008: {"2-Butene": 1},  # REFPROP_C2BUTEN
    -1009: {"C4F10": 1},  # REFPROP_C4F10
    -1010: {"C5F12": 1},  # REFPROP_C5F12
    -1011: {"CF3I": 1},  # REFPROP_CF3I
    -1012: {"CO": 1},  # REFPROP_CO
    -1013: {"CO2": 1},  # REFPROP_CO2
    -1014: {"COS": 1},  # REFPROP_COS
    -1015: {"Cyclohexane": 1},  # REFPROP_CYCHEX
    -1016: {"Cyclopropane": 1},  # REFPROP_CYCPRO
    -1017: {"D2": 1},  # REFPROP_D2
    -1018: {"D2O": 1},  # REFPROP_D2O
    -1019: {"Decane": 1},  # REFPROP_DEC
    -1020: {"DME": 1},  # REFPROP_DME
    -1021: {"Ethane": 1},  # REFPROP_ETH
    -1022: {"Ethanol": 1},  # REFPROP_ETHL
    -1023: {"Ethene": 1},  # REFPROP_ETHEN
    -1024: {"Fluorine": 1},  # REFPROP_FLUORINE
    -1025: {"H2S": 1},  # REFPROP_H2S
    -1026: {"HE": 1},  # REFPROP_HE
    -1027: {"Heptane": 1},  # REFPROP_HEPT
    -1028: {"Hexane": 1},  # REFPROP_HEX
    -1029: {"H2": 1},  # REFPROP_H2
    -1030: {"Iso-Butene": 1},  # REFPROP_IBUTEN
    -1031: {"Iso-Hexane": 1},  # REFPROP_IHEX
    -1032: {"Iso-Pentane": 1},  # REFPROP_IPENT
    -1033: {"Iso-Butane": 1},  # REFPROP_IBUT
    -1034: {"Kr": 1},  # REFPROP_KR
    -1035: {"CH4": 1},  # REFPROP_CH4
    -1036: {"Methanol": 1},  # REFPROP_METHL
    -1037: {"N2O": 1},  # REFPROP_N2O
    -1038: {"NE": 1},  # REFPROP_NE
    -1039: {"Neopentane": 1},  # REFPROP_NEOPENT
    -1040: {"NF3": 1},  # REFPROP_NF3
    -1041: {"N2": 1},  # REFPROP_N2
    -1042: {"Nonane": 1},  # REFPROP_NON
    -1043: {"Octane": 1},  # REFPROP_OCT
    -1044: {"O2": 1},  # REFPROP_O2
    -1045: {"Parahydrogen": 1},  # REFPROP_PARAHYD
    -1046: {"Pentane": 1},  # REFPROP_PENT
    -1047: {"Propane": 1},  # REFPROP_PROP
    -1048: {"Propene": 1},  # REFPROP_PROPEN
    -1049: {"Propyne": 1},  # REFPROP_PROPYNE
    -1050: {"R11": 1},  # REFPROP_R11
    -1051: {"R113": 1},  # REFPROP_R113
    -1052: {"R114": 1},  # REFPROP_R114
    -1053: {"R115": 1},  # REFPROP_R115
    -1054: {"R116": 1},  # REFPROP_R116
    -1055: {"R12": 1},  # REFPROP_R12
    -1056: {"R123": 1},  # REFPROP_R123
    -1057: {"R124": 1},  # REFPROP_R124
    -1058: {"R125": 1},  # REFPROP_R125
    -1059: {"R13": 1},  # REFPROP_R13
    -1060: {"R134a": 1},  # REFPROP_R134A
    -1061: {"R14": 1},  # REFPROP_R14
    -1062: {"R141b": 1},  # REFPROP_R141B
    -1063: {"R142B": 1},  # REFPROP_R142B
    -1064: {"R143A": 1},  # REFPROP_R143A
    -1065: {"R152A": 1},  # REFPROP_R152A
    -1066: {"R21": 1},     # REFPROP_R21
    -1067: {"R218": 1},    # REFPROP_R218
    -1068: {"R22": 1},     # REFPROP_R22
    -1069: {"R227EA": 1},  # REFPROP_R227EA
    -1070: {"R23": 1},     # REFPROP_R23
    -1071: {"R236EA": 1},  # REFPROP_R236EA
    -1072: {"R236FA": 1},  # REFPROP_R236FA
    -1073: {"R245CA": 1},  # REFPROP_R245CA
    -1074: {"R245FA": 1},  # REFPROP_R245FA
    -1075: {"R32": 1},     # REFPROP_R32
    -1076: {"R365MFC": 1}, # REFPROP_R365MFC
    -1077: {"R404A": 1},   # REFPROP_R404A
    -1078: {"R407C": 1},   # REFPROP_R407C
    -1079: {"R41": 1},     # REFPROP_R41
    -1080: {"R410A": 1},   # REFPROP_R410A
    -1081: {"R507A": 1},   # REFPROP_R507A
    -1082: {"RC318": 1},   # REFPROP_RC318
    -1083: {"SF6": 1},     # REFPROP_SF6
    -1084: {"SO2": 1},     # REFPROP_SO2
    -1085: {"T2Butene": 1},# REFPROP_T2BUTEN
    -1086: {"Toluene": 1}, # REFPROP_TOLUEN
    -1087: {"H2O": 1},     # REFPROP_H2O
    -1088: {"XE": 1},      # REFPROP_XE
    -1090: {"MCyclohex": 1}, # REFPROP_MCYCHEX
    -1091: {"C3CC6": 1},   # REFPROP_C3CC6
    -1092: {"Cyclopentane": 1}, # REFPROP_CYCPENT
    -1093: {"D4": 1},      # REFPROP_D4
    -1094: {"D5": 1},      # REFPROP_D5
    -1095: {"D6": 1},      # REFPROP_D6
    -1096: {"DMC": 1},     # REFPROP_DMC
    -1097: {"MD2M": 1},    # REFPROP_MD2M
    -1098: {"MD3M": 1},    # REFPROP_MD3M
    -1099: {"MD4M": 1},    # REFPROP_MD4M
    -1100: {"MDM": 1},     # REFPROP_MDM
    -1101: {"MLinolea": 1},# REFPROP_MLINOLEA
    -1102: {"MLinolEN": 1},# REFPROP_MLINOLEN
    -1103: {"MM": 1},      # REFPROP_MM
    -1104: {"Moleate": 1}, # REFPROP_MOLEATE
    -1105: {"MPalmita": 1},# REFPROP_MPALMITA
    -1106: {"MStearat": 1},# REFPROP_MSTEARAT
    -1107: {"OrthoHyd": 1}, # REFPROP_ORTHOHYD
    -1108: {"R1234YF": 1}, # REFPROP_R1234YF
    -1109: {"R1234ZE": 1}, # REFPROP_R1234ZE
    -1110: {"R161": 1},    # REFPROP_R161
    -1111: {"UD_01": 1}, # REFPROP_REFPROP_UD_01
    -1112: {"UD_02": 1}, # REFPROP_REFPROP_UD_02
    -1113: {"UD_03": 1}, # REFPROP_REFPROP_UD_03
    -1114: {"UD_04": 1}, # REFPROP_REFPROP_UD_04
    -1115: {"UD_05": 1}, # REFPROP_REFPROP_UD_05
    -1116: {"UD_06": 1}, # REFPROP_REFPROP_UD_06
    -1117: {"UD_07": 1}, # REFPROP_REFPROP_UD_07
    -1118: {"UD_08": 1}, # REFPROP_REFPROP_UD_08
    -1119: {"UD_09": 1}, # REFPROP_REFPROP_UD_09
    -1120: {"UD_10": 1}, # REFPROP_REFPROP_UD_10
    -1121: {"UD_11": 1}, # REFPROP_REFPROP_UD_11
    -1122: {"UD_12": 1}, # REFPROP_REFPROP_UD_12
    -1123: {"UD_13": 1}, # REFPROP_REFPROP_UD_13
    -1124: {"UD_14": 1}, # REFPROP_REFPROP_UD_14
    -1125: {"UD_15": 1}, # REFPROP_REFPROP_UD_15
    -1126: {"UD_16": 1}, # REFPROP_REFPROP_UD_16
    -1127: {"UD_17": 1}, # REFPROP_REFPROP_UD_17
    -1128: {"UD_18": 1}, # REFPROP_REFPROP_UD_18
    -1129: {"UD_19": 1}, # REFPROP_REFPROP_UD_19
    -1130: {"UD_20": 1}, # REFPROP_REFPROP_UD_20
    -1131: {"C11": 1},    # REFPROP_C11
    -1132: {"DEE": 1},    # REFPROP_DEE
    -1133: {"EBenzene": 1}, # REFPROP_EBENZ
    -1134: {"HCL": 1},    # REFPROP_HCL
    -1135: {"IOctane": 1}, # REFPROP_IOCTANE
    -1136: {"MXYlene": 1}, # REFPROP_MXYLENE
    -1137: {"Novec649": 1}, # REFPROP_NOVEC649
    -1138: {"Oxylene": 1}, # REFPROP_OXYLEN
    -1139: {"PXylene": 1}, # REFPROP_PXYLENE
    -1140: {"R1216": 1},  # REFPROP_R1216
    -1141: {"R1233ZD": 1}, # REFPROP_R1233ZD
    -1142: {"R40": 1},    # REFPROP_R40
    -1143: {"RE143A": 1}, # REFPROP_RE143A
    -1144: {"RE245CB2": 1}, # REFPROP_RE245CB2
    -1145: {"RE245FA2": 1}, # REFPROP_RE245FA2
    -1146: {"RE347MCC": 1}, # REFPROP_RE347MCC
    -1147: {"EthyleneOxide": 1}, # REFPROP_EthyleneOxide
    -1148: {"13Butadien": 1}, # REFPROP_13BUTADIEN
    -1149: {"1-Butyne": 1}, # REFPROP_1BUTYNE
    -1150: {"1Penten": 1}, # REFPROP_1PENTEN
    -1151: {"22DMBut": 1}, # REFPROP_22DMBUT
    -1152: {"23DMBut": 1}, # REFPROP_23DMBUT
    -1153: {"3MPent": 1},  # REFPROP_3MPENT
    -1154: {"Acet": 1},    # REFPROP_ACET
    -1155: {"C16": 1},      # REFPROP_C16
    -1156: {"C22": 1},      # REFPROP_C22
    -1157: {"C6F14": 1},    # REFPROP_C6F14
    -1158: {"Chlorine": 1}, # REFPROP_CHLORINE
    -1159: {"Chlorobenzene": 1}, # REFPROP_CHLOROBENZENE
    -1160: {"Cyclobutene": 1}, # REFPROP_CYCLOBUTENE
    -1161: {"Propadien": 1},  # REFPROP_PROPADIEN
    -1162: {"PropyleneOxide": 1}, # REFPROP_PROPYLENEOXIDE
    -1163: {"R1123": 1},    # REFPROP_R1123
    -1164: {"R1224YDZ": 1},  # REFPROP_R1224YDZ
    -1165: {"R1234zeZ": 1},  # REFPROP_R1234zeZ
    -1166: {"R1243ZF": 1},    # REFPROP_R1243ZF
    -1167: {"R1336MZZZ": 1},  # REFPROP_R1336MZZZ
    -1168: {"Dichloroethane": 1}, # REFPROP_Dichloroethane
    -1169: {"Vinylchloride": 1},  # REFPROP_VINYLCHLORIDE
    -1170: {"Diethanolamine": 1}, # REFPROP_DIETHANOLAMINE
    -1171: {"Ethylene_glycol": 1}, # REFPROP_Ethylene_glycol
    -1172: {"Monoethanolamine": 1}, # REFPROP_MONOETHANOLAMINE
    -2000: {"AIR_dry": 1},  # REFPROPMIXTURE_AIR_dry
    -2001: {"R401A": 1},  # REFPROPMIXTURE_R401A
    -2002: {"R401B": 1},  # REFPROPMIXTURE_R401B
    -2003: {"R401C": 1},  # REFPROPMIXTURE_R401C
    -2004: {"R402A": 1},  # REFPROPMIXTURE_R402A
    -2005: {"R402B": 1},  # REFPROPMIXTURE_R402B
    -2006: {"R403A": 1},  # REFPROPMIXTURE_R403A
    -2007: {"R403B": 1},  # REFPROPMIXTURE_R403B
    -2008: {"R404A": 1},  # REFPROPMIXTURE_R404A
    -2009: {"R405A": 1},  # REFPROPMIXTURE_R405A
    -2010: {"R406A": 1},  # REFPROPMIXTURE_R406A
    -2011: {"R407A": 1},  # REFPROPMIXTURE_R407A
    -2012: {"R407B": 1},  # REFPROPMIXTURE_R407B
    -2013: {"R407C": 1},  # REFPROPMIXTURE_R407C
    -2014: {"R407D": 1},  # REFPROPMIXTURE_R407D
    -2015: {"R407E": 1},  # REFPROPMIXTURE_R407E
    -2016: {"R408A": 1},  # REFPROPMIXTURE_R408A
    -2017: {"R409A": 1},  # REFPROPMIXTURE_R409A
    -2018: {"R409B": 1},  # REFPROPMIXTURE_R409B
    -2019: {"R410A": 1},  # REFPROPMIXTURE_R410A
    -2020: {"R410B": 1},  # REFPROPMIXTURE_R410B
    -2021: {"R411A": 1},  # REFPROPMIXTURE_R411A
    -2022: {"R411B": 1},  # REFPROPMIXTURE_R411B
    -2023: {"R412A": 1},  # REFPROPMIXTURE_R412A
    -2024: {"R413A": 1},  # REFPROPMIXTURE_R413A
    -2025: {"R414A": 1},  # REFPROPMIXTURE_R414A
    -2026: {"R414B": 1},  # REFPROPMIXTURE_R414B
    -2027: {"R415A": 1},  # REFPROPMIXTURE_R415A
    -2028: {"R415B": 1},  # REFPROPMIXTURE_R415B
    -2029: {"R416A": 1},  # REFPROPMIXTURE_R416A
    -2030: {"R417A": 1},  # REFPROPMIXTURE_R417A
    -2031: {"R418A": 1},  # REFPROPMIXTURE_R418A
    -2032: {"R419A": 1},  # REFPROPMIXTURE_R419A
    -2033: {"R420A": 1},  # REFPROPMIXTURE_R420A
    -2034: {"R421A": 1},  # REFPROPMIXTURE_R421A
    -2035: {"R421B": 1},  # REFPROPMIXTURE_R421B
    -2036: {"R422A": 1},  # REFPROPMIXTURE_R422A
    -2037: {"R422B": 1},  # REFPROPMIXTURE_R422B
    -2038: {"R422C": 1},  # REFPROPMIXTURE_R422C
    -2039: {"R422D": 1},  # REFPROPMIXTURE_R422D
    -2040: {"R423A": 1},  # REFPROPMIXTURE_R423A
    -2041: {"R424A": 1},  # REFPROPMIXTURE_R424A
    -2042: {"R425A": 1},  # REFPROPMIXTURE_R425A
    -2043: {"R426A": 1},  # REFPROPMIXTURE_R426A
    -2044: {"R427A": 1},  # REFPROPMIXTURE_R427A
    -2045: {"R428A": 1},  # REFPROPMIXTURE_R428A
    -2046: {"R500": 1},   # REFPROPMIXTURE_R500
    -2047: {"R501": 1},   # REFPROPMIXTURE_R501
    -2048: {"R502": 1},   # REFPROPMIXTURE_R502
    -2049: {"R503": 1},   # REFPROPMIXTURE_R503
    -2050: {"R504": 1},   # REFPROPMIXTURE_R504
    -2051: {"R507A": 1},  # REFPROPMIXTURE_R507A
    -2052: {"R508A": 1},  # REFPROPMIXTURE_R508A
    -2053: {"R508B": 1},  # REFPROPMIXTURE_R508B
    -2054: {"R509A": 1},  # REFPROPMIXTURE_R509A
    -2055: {"AMARILLO": 1},  # REFPROPMIXTURE_AMARILLO
    -2056: {"EKOFISK": 1},   # REFPROPMIXTURE_EKOFISK
    -2057: {"GLFCOAST": 1},   # REFPROPMIXTURE_GLFCOAST
    -2058: {"HIGHCO2": 1},    # REFPROPMIXTURE_HIGHCO2
    -2059: {"HIGHN2": 1},     # REFPROPMIXTURE_HIGHN2
    -2060: {"R429A": 1},      # REFPROPMIXTURE_R429A
    -2061: {"R430A": 1},      # REFPROPMIXTURE_R430A
    -2062: {"R431A": 1},      # REFPROPMIXTURE_R431A
    -2063: {"R432A": 1},      # REFPROPMIXTURE_R432A
    -2064: {"R433A": 1},      # REFPROPMIXTURE_R433A
    -2065: {"R434A": 1},      # REFPROPMIXTURE_R434A
    -2066: {"R438A": 1},      # REFPROPMIXTURE_R438A
    -2067: {"R435A": 1},      # REFPROPMIXTURE_R435A
    -2068: {"R436A": 1},      # REFPROPMIXTURE_R436A
    -2069: {"R436B": 1},      # REFPROPMIXTURE_R436B
    -2070: {"R437A": 1},      # REFPROPMIXTURE_R437A
    -2071: {"R510A": 1},      # REFPROPMIXTURE_R510A
    -2072: {"NGSAMPLE": 1},   # REFPROPMIXTURE_NGSAMPLE
    -2073: {"R407F": 1},      # REFPROPMIXTURE_R407F
    -2074: {"R441A": 1},      # REFPROPMIXTURE_R441A
    -2075: {"R442A": 1},      # REFPROPMIXTURE_R442A
    -2076: {"R443A": 1},      # REFPROPMIXTURE_R443A
    -2077: {"R444A": 1},      # REFPROPMIXTURE_R444A
    -2078: {"R512A": 1},      # REFPROPMIXTURE_R512A
    -2079: {"R407G": 1},      # REFPROPMIXTURE_R407G
    -2080: {"R407H": 1},      # REFPROPMIXTURE_R407H
    -2081: {"R417B": 1},      # REFPROPMIXTURE_R417B
    -2082: {"R417C": 1},      # REFPROPMIXTURE_R417C
    -2083: {"R419B": 1},      # REFPROPMIXTURE_R419B
    -2084: {"R422E": 1},      # REFPROPMIXTURE_R422E
    -2085: {"R433B": 1},      # REFPROPMIXTURE_R433B
    -2086: {"R433C": 1},      # REFPROPMIXTURE_R433C
    -2087: {"R439A": 1},      # REFPROPMIXTURE_R439A
    -2088: {"R440A": 1},      # REFPROPMIXTURE_R440A
    -2089: {"R444B": 1},      # REFPROPMIXTURE_R444B
    -2090: {"R445A": 1},      # REFPROPMIXTURE_R445A
    -2091: {"R446A": 1},      # REFPROPMIXTURE_R446A
    -2092: {"R447A": 1},      # REFPROPMIXTURE_R447A
    -2093: {"R447B": 1},      # REFPROPMIXTURE_R447B
    -2094: {"R448A": 1},      # REFPROPMIXTURE_R448A
    -2095: {"R449A": 1},      # REFPROPMIXTURE_R449A
    -2096: {"R449B": 1},      # REFPROPMIXTURE_R449B
    -2097: {"R449C": 1},      # REFPROPMIXTURE_R449C
    -2098: {"R450A": 1},      # REFPROPMIXTURE_R450A
    -2099: {"R451A": 1},      # REFPROPMIXTURE_R451A
    -2100: {"R451B": 1},      # REFPROPMIXTURE_R451B
    -2101: {"R452A": 1},      # REFPROPMIXTURE_R452A
    -2102: {"R452B": 1},      # REFPROPMIXTURE_R452B
    -2103: {"R452C": 1},      # REFPROPMIXTURE_R452C
    -2104: {"R453A": 1},      # REFPROPMIXTURE_R453A
    -2105: {"R454A": 1},      # REFPROPMIXTURE_R454A
    -2106: {"R454B": 1},      # REFPROPMIXTURE_R454B
    -2107: {"R454C": 1},      # REFPROPMIXTURE_R454C
    -2108: {"R455A": 1},      # REFPROPMIXTURE_R455A
    -2109: {"R456A": 1},      # REFPROPMIXTURE_R456A
    -2110: {"R457A": 1},      # REFPROPMIXTURE_R457A
    -2111: {"R458A": 1},      # REFPROPMIXTURE_R458A
    -2112: {"R459A": 1},      # REFPROPMIXTURE_R459A
    -2113: {"R459B": 1},      # REFPROPMIXTURE_R459B
    -2114: {"R460A": 1},      # REFPROPMIXTURE_R460A
    -2115: {"R460B": 1},      # REFPROPMIXTURE_R460B
    -2116: {"R511A": 1},      # REFPROPMIXTURE_R511A
    -2117: {"R513A": 1},      # REFPROPMIXTURE_R513A
    -2118: {"R513B": 1},      # REFPROPMIXTURE_R513B
    -2119: {"R515A": 1},      # REFPROPMIXTURE_R515A
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
    27: {  # Aftercooler / Superheater
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
    },
    14: {  # Control valve
        1: 0,  # Inlet
        2: 0,  # Outlet
    },
    # ...
    # ...
    # Add more mappings for other component types as needed
    # ...
    # ...
}
