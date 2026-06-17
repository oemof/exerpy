# Define the component groups via AttributeValue(6) and other ways
grouped_components = {
    "Turbine": ["Compr"],
    "HeatExchanger": ["HeatX"],
    "CombustionChamber": ["RStoic"],
    "Valve": ["Valve"],
    "Pump": ["Pump"],
    "Compressor": ["Compr"],
    "SimpleHeatExchanger": ["Heater"],
    "Mixer": ["Mixer"],
    "Splitter": ["FSplit"],
    "Generator": ["Gen"],
    "Motor": ["Motor"],
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
    # Turbine uses a custom connector assignment function (assign_turbine_connectors).
    # WS(IN) direction depends on the sign of the Aspen POWER_OUT value:
    #   positive → power leaves turbine → swapped to outlet connector 2
    #   negative → power enters turbine → kept as inlet connector 1
    "Turbine": {
        "F(IN)": 0,  # inlet gas flow
        "P(OUT)": 0,  # outlet gas flow
        "WS(OUT)": 1,  # power outlet (e.g. to generator)
        "WS(IN)": 2,  # outlet if positive (swapped), inlet 1 if negative (kept)
    },
    "Compressor": {"F(IN)": 0, "P(OUT)": 0, "WS(OUT)": 1},  # inlet gas flow  # outlet gas flow  # outlet work flow
    "HeatX": {
        "C(IN)": 1,  # inlet cold stream
        "C(OUT)": 1,  # outlet cold stream
        "H(IN)": 0,  # inlet hot stream
        "H(OUT)": 0,  # outlet hot stream
    },
    "Heater": {
        "F(IN)": 0,  # inlet stream
        "P(OUT)": 0,  # outlet stream
    },
    "Generator": {
        "WS(IN)": 0,  # inlet work flow
        "WS(OUT)": 0,  # outlet work flow
    },
    "Pump": {
        "F(IN)": 0,  # inlet work flow
        "P(OUT)": 0,  # outlet work flow
    },
    "Motor": {
        "WS(IN)": 0,  # inlet work flow
        "WS(OUT)": 0,  # outlet work flow
    },
    "Valve": {
        "F(IN)": 0,  # inlet stream
        "P(OUT)": 0,  # outlet stream
    },
    # Following components need extra functions because they have multiple inputs/outputs:
    # Splitter,
    # Combustion Chamber,
    # Deaerator
}
