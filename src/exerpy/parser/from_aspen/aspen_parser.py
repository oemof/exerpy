import os
import json
import win32com.client as win32

# Initialize Aspen Plus
aspen = win32.Dispatch('Apwn.Document')
aspen.InitFromArchive2(os.path.abspath(r'.\simulation\1-simple_test\simple_test.bkp'))

# Get the connection (stream) nodes and their actual names
stream_nodes = aspen.Tree.FindNode(r'\Data\Streams').Elements
stream_names = [stream_node.Name for stream_node in stream_nodes]

# Get the fluid names dynamically
fluid_names_node = aspen.Tree.FindNode(r"\Data\Components\Specifications\Input\ANAME")
fluid_names = [fluid_name.Name for fluid_name in fluid_names_node.Elements]

stream_type = {}
connections_data = {}
busses_data = {}

# Process each stream
for stream_name in stream_names:
    stream_node = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}')
    
    # Retrieve stream data
    if aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Input\WORK') is not None:
        stream_type[stream_name] = "WORK"
        
        busses_data[stream_name] = {
            "name": stream_name,
            "type": stream_type[stream_name],
            "source_component": None,
            "target_component": None,
        }
        
        # Check for source and destination of the stream
        source_port_node = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\SOURCE')
        if source_port_node is not None and source_port_node.Elements.Count > 0:
            # Assuming there is only one source
            busses_data[stream_name]["source_component"] = source_port_node.Elements(0).Name

        destination_port_node = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\DEST')
        if destination_port_node is not None and destination_port_node.Elements.Count > 0:
            # Assuming there is only one destination
            busses_data[stream_name]["target_component"] = destination_port_node.Elements(0).Name
            
        busses_data[stream_name]["parameters"] = {
            "power": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\POWER_OUT').Value,
        }
        
        
    elif aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Input\HEAT') is not None:
        stream_type[stream_name] = "HEAT"
        
        busses_data[stream_name] = {
            "name": stream_name,
            "type": stream_type[stream_name],
            "source_component": None,
            "target_component": None,
        }
        
        # Check for source and destination of the stream
        source_port_node = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\SOURCE')
        if source_port_node is not None and source_port_node.Elements.Count > 0:
            # Assuming there is only one source
            busses_data[stream_name]["source_component"] = source_port_node.Elements(0).Name

        destination_port_node = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\DEST')
        if destination_port_node is not None and destination_port_node.Elements.Count > 0:
            # Assuming there is only one destination
            busses_data[stream_name]["target_component"] = destination_port_node.Elements(0).Name
            
        busses_data[stream_name]["parameters"] = {
            "heat": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\QCALC').Value,
        }
        
    elif aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Input\PRES') is not None:
        stream_type[stream_name] = "MATERIAL"
        
        connections_data[stream_name] = {
            "name": stream_name,
            "source_component": None,
            "source_connector": 0,  # Default value
            "target_component": None,
            "target_connector": 0   # Default value
            }

        # Check for source and destination of the stream
        source_port_node = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\SOURCE')
        if source_port_node is not None and source_port_node.Elements.Count > 0:
            # Assuming there is only one source
            connections_data[stream_name]["source_component"] = source_port_node.Elements(0).Name

        destination_port_node = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\DEST')
        if destination_port_node is not None and destination_port_node.Elements.Count > 0:
            # Assuming there is only one destination
            connections_data[stream_name]["target_component"] = destination_port_node.Elements(0).Name
            
        connections_data[stream_name]["parameters"] = {
            "temp": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TEMP_OUT\MIXED').Value,
            "pres": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\PRES_OUT\MIXED').Value,
            "enthalpy": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\HMX\MIXED').Value, # kJ/kmol
            "entropy": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\SMX\MIXED').Value, # kJ/kmolK
            "exergy": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\STRM_UPP\EXERGYML\MIXED\TOTAL').Value, # kJ/kmol
            "mass_flow": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MASSFLMX\MIXED').Value,
            "mole_flow": aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TOT_FLOW').Value,
            "mole_flow_comp": {},
            "compos": {},
        }
        
        for fluid_name in fluid_names:
            connections_data[stream_name]["parameters"]["mole_flow_comp"][fluid_name] = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MOLEFLOW\MIXED\{fluid_name}').Value
            connections_data[stream_name]["parameters"]["compos"][fluid_name] = aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MOLEFRAC\MIXED\{fluid_name}').Value
    
    
# Get the component (block) nodes and their actual names
block_nodes = aspen.Tree.FindNode(r'\Data\Blocks').Elements
block_names = [block_node.Name for block_node in block_nodes]

block_type = {}
components_data = {}

# Process each block
for block_name in block_names:
    block_node = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}')

    # Retrieve block data
    if aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE') is not None and aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE').Value == "COMPRESSOR":
        block_type[block_name] = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE').Value
        
        components_data[block_name] = {
            "name": block_name,
            "type": "Compressor",
            "power": aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value,
        }
        
    elif aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE') is not None and aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE').Value == "TURBINE":
        block_type[block_name] = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE').Value
        
        components_data[block_name] = {
            "name": block_name,
            "type": "Turbine",
            "power": aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value,
        }
        
    elif aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\PUMP_TYPE') is not None and aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\PUMP_TYPE').Value == "PUMP":
        block_type[block_name] = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\PUMP_TYPE').Value
        
        components_data[block_name] = {
            "name": block_name,
            "type": "Pump",
            "power": aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value,
        }
        
        if aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\DEFF').Value < 1:
        
            block_name_motor = block_name + "-MOTOR"
        
            components_data[block_name_motor] = {
                "name": block_name_motor,
                "type": "Motor",
                "power": aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\WNET').Value,
            }
        
    elif aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\PUMP_TYPE') is not None and aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\PUMP_TYPE').Value == "TURBINE":
        block_type[block_name] = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\PUMP_TYPE').Value
        
        components_data[block_name] = {
            "name": block_name,
            "type": "LiquidTurbine",
            "power": aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value,
        }
        
    elif aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\TUBE_TYPE') is not None:
        block_type[block_name] = "HeatX"
        
        components_data[block_name] = {
            "name": block_name,
            "type": "HeatExchanger"
        }
        
        hot_in = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Ports\H(IN)').Elements(0).Name
        hot_out = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Ports\H(OUT)').Elements(0).Name
        cold_in = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Ports\C(IN)').Elements(0).Name
        cold_out = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Ports\C(OUT)').Elements(0).Name
        
        # Update connections_data with source_connector values for the streams
        if hot_in in connections_data:
            connections_data[hot_in]["source_connector"] = 0
            
        if hot_out in connections_data:
            connections_data[hot_out]["source_connector"] = 0
               
        if cold_in in connections_data:
            connections_data[cold_in]["target_connector"] = 1

        if cold_out in connections_data:
            connections_data[cold_out]["target_connector"] = 1
            
    elif aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\COMBUSTION') is not None:
        block_type[block_name] = "RStoic"
        
        components_data[block_name] = {
            "name": block_name,
            "type": "CombustionChamber",
            "temperature": aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\B_TEMP').Value,
        }
        
    elif aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\FACTOR') is not None:
        block_type[block_name] = "Mult"
        
        # Get the name of the stream from the block's port WS(OUT)
        power_out = aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Ports\WS(OUT)').Elements(0).Name

        # Check if the stream name exists in busses_data and retrieve the "power" value
        if power_out in busses_data and "power" in busses_data[power_out]["parameters"]:
            power_value = busses_data[power_out]["parameters"]["power"]
        else:
            power_value = None  # Handle the case where the power data is missing
                
        # Insert the retrieved "power" value into components_data
        components_data[block_name] = {
            "name": block_name,
            "type": "Generator",
            "power": power_value,  # Insert the power value retrieved from busses_data
        }
        
    elif aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\VALVE_DIA') is not None:
        block_type[block_name] = "Valve"
        
        components_data[block_name] = {
            "name": block_name,
            "type": "Valve",
            "output pressure": aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\P_OUT_OUT').Value,
        }

# Write data to JSON file
with open('connections_data.json', 'w') as connections:
    json.dump(connections_data, connections, indent=4)
    
with open('busses_data.json', 'w') as busses:
    json.dump(busses_data, busses, indent=4)
    
with open('components_data.json', 'w') as components:
    json.dump(components_data, components, indent=4)

