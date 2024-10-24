# Define the component groups via AttributeValue(6) and other ways
grouped_components = {
    "Turbine": ['Compr'],
    "HeatExchanger": ['HeatX'],
    "CombustionChamber": ['RStoic'],
    # "Valve": [],
    "Pump": ['Pump'],
    "Compressor": ['Compr'],
    # "Condenser": [],
    # "Deaerator": [],
    "SimpleHeatExchanger": ['Heater'],
    "Mixer": ['Mixer'],
    "Splitter": ['FSplit'],
    "Generator": ['Gen'],
    "Motor": ['Motor'],
}

connector_mappings = {
    'Turbine': {
        'F(IN)': 0,    # inlet gas flow
        'P(OUT)': 0,   # outlet gas flow
        'WS(IN)': 1,   # inlet work flow (e.g. from compressor)
        'WS(OUT)': 1,  # outlet work flow
    },
    'Compressor': {
        'F(IN)': 0,    # inlet gas flow
        'P(OUT)': 0,   # outlet gas flow
        'WS(OUT)': 1   # outlet work flow
    },
    'HeatX': {
        'C(IN)': 1,    # inlet cold strean
        'C(OUT)': 1,   # outlet cold strean
        'H(IN)': 0,    # inlet hot strean
        'H(OUT)': 0    # outlet hot strean
    },
    'Heater': {
        'F(IN)': 0,    # inlet strean
        'P(OUT)': 0,   # outlet strean
    },
    'Generator': {
        'WS(IN)': 0,    # inlet work flow
        'WS(OUT)': 0,   # outlet work flow
    },
    'Pump': {
        'F(IN)': 0,    # inlet work flow
        'P(OUT)': 0,   # outlet work flow
    },
# Following components need extra functions because they have multiple inputs/outputs:
# Splitter, 
# Combustion Chamber, 
# Deaerator 
}

