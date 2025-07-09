# Define the component groups via AttributeValue(6) and other ways
grouped_components = {
    "Turbine": ['Compr'],
    "HeatExchanger": ['HeatX'],
    "CombustionChamber": ['RStoic'],
    "Valve": ['Valve'],
    "Pump": ['Pump'],
    "Compressor": ['Compr'],
    "SimpleHeatExchanger": ['Heater'],
    "Mixer": ['Mixer'],
    "Splitter": ['FSplit'],
    "Generator": ['Gen'],
    "Motor": ['Motor'],
}
"""
This is the mapping of component groups to their respective component IDs:

    - "Turbine": ['Compr'],
    - "HeatExchanger": ['HeatX'],
    - "CombustionChamber": ['RStoic'],
    - "Valve": ['Valve'],
    - "Pump": ['Pump'],
    - "Compressor": ['Compr'],
    - "SimpleHeatExchanger": ['Heater'],
    - "Mixer": ['Mixer'],
    - "Splitter": ['FSplit'],
    - "Generator": ['Gen'],
    - "Motor": ['Motor']

"""

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
        'C(IN)': 1,    # inlet cold stream
        'C(OUT)': 1,   # outlet cold stream
        'H(IN)': 0,    # inlet hot stream
        'H(OUT)': 0    # outlet hot stream
    },
    'Heater': {
        'F(IN)': 0,    # inlet stream
        'P(OUT)': 0,   # outlet stream
    },
    'Generator': {
        'WS(IN)': 0,    # inlet work flow
        'WS(OUT)': 0,   # outlet work flow
    },
    'Pump': {
        'F(IN)': 0,    # inlet work flow
        'P(OUT)': 0,   # outlet work flow
    },
    'Motor': {
        'WS(IN)': 0,    # inlet work flow
        'WS(OUT)': 0,   # outlet work flow
    },
    'Valve': {
        'F(IN)': 0,    # inlet stream
        'P(OUT)': 0,   # outlet stream
    },
# Following components need extra functions because they have multiple inputs/outputs:
# Splitter, 
# Combustion Chamber, 
# Deaerator 
}

