import os
import logging
import win32com.client as win32
import json

class AspenModelParser:
    """
    A class to parse Aspen Plus models, simulate them, extract data, and write to JSON.
    """
    def __init__(self, model_path):
        """
        Initializes the parser with the given model path.
        
        Parameters:
            model_path (str): Path to the Aspen Plus model file.
        """
        self.model_path = model_path
        self.aspen = None  # Aspen Plus application instance
        self.components_data = {}  # Dictionary to store component data
        self.connections_data = {}  # Dictionary to store connection data

    def initialize_model(self):
        """
        Initializes the Aspen Plus application and opens the specified model.
        """
        try:
            # Start Aspen Plus application via COM Dispatch
            self.aspen = win32.Dispatch('Apwn.Document')
            # Load the Aspen model file
            self.aspen.InitFromArchive2(self.model_path)
            logging.info(f"Model opened successfully: {self.model_path}")
        except Exception as e:
            logging.error(f"Failed to initialize the model: {e}")
            raise

    def parse_model(self):
        """
        Parses the components and connections from the Aspen model.
        """
        try:
            # Parse streams (connections)
            self.parse_streams()
            
            # Parse blocks (components)
            self.parse_blocks()

        except Exception as e:
            logging.error(f"Error while parsing the model: {e}")
            raise

    def parse_streams(self):
        """
        Parses the streams (connections) in the Aspen model.
        """
        # Get the stream nodes and their names
        stream_nodes = self.aspen.Tree.FindNode(r'\Data\Streams').Elements
        stream_names = [stream_node.Name for stream_node in stream_nodes]
        
        # Process each stream
        for stream_name in stream_names:
            stream_node = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}')
            connection_data = {
                'name': stream_name,
                'kind': "material",  # Default kind is material unless power/heat is found
                'source_component': None,
                'source_connector': None,
                'target_component': None,
                'target_connector': None,
                'fluid_type': None,
                'parameters': {}
            }

            # Check if the stream is a power or heat stream
            if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Input\WORK') is not None:
                connection_data['kind'] = 'power'
                connection_data['parameters']['power'] = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\POWER_OUT').Value
            elif self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Input\HEAT') is not None:
                connection_data['kind'] = 'heat'
                connection_data['parameters']['heat'] = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\QCALC').Value
            else:
                # Assume it's a material stream and retrieve additional properties
                connection_data['parameters'].update({
                    'temp': self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TEMP_OUT\MIXED').Value,
                    'pres': self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\PRES_OUT\MIXED').Value,
                    'enthalpy': self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\HMX\MIXED').Value,
                    'entropy': self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\SMX\MIXED').Value,
                    'mass_flow': self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MASSFLMX\MIXED').Value,
                })

            # Find the source and target components
            source_port_node = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\SOURCE')
            if source_port_node is not None and source_port_node.Elements.Count > 0:
                connection_data["source_component"] = source_port_node.Elements(0).Name

            destination_port_node = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\DEST')
            if destination_port_node is not None and destination_port_node.Elements.Count > 0:
                connection_data["target_component"] = destination_port_node.Elements(0).Name

            # Store connection data
            self.connections_data[stream_name] = connection_data

    def parse_blocks(self):
        """
        Parses the blocks (components) in the Aspen model.
        """
        block_nodes = self.aspen.Tree.FindNode(r'\Data\Blocks').Elements
        block_names = [block_node.Name for block_node in block_nodes]

        # Process each block
        for block_name in block_names:
            block_node = self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}')
            component_data = {
                'name': block_name,
                'type': None,
                'parameters': {}
            }

            # Check for different block types and store relevant parameters
            if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE') is not None:
                model_type = self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE').Value
                if model_type == "COMPRESSOR":
                    component_data['type'] = "Compressor"
                    component_data['parameters']['power'] = self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value
                elif model_type == "TURBINE":
                    component_data['type'] = "Turbine"
                    component_data['parameters']['power'] = self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value
                elif model_type == "PUMP":
                    component_data['type'] = "Pump"
                    component_data['parameters']['power'] = self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value
                # Add handling for additional block types as needed

            # Store component data
            self.components_data[block_name] = component_data

    def get_sorted_data(self):
        """
        Sorts the component and connection data alphabetically by name.

        Returns:
            dict: A dictionary containing sorted 'components', 'connections', and ambient conditions data.
        """
        sorted_components = {comp_name: self.components_data[comp_name] for comp_name in sorted(self.components_data)}
        sorted_connections = {conn_name: self.connections_data[conn_name] for conn_name in sorted(self.connections_data)}
        return {'components': sorted_components, 'connections': sorted_connections}

    def write_to_json(self, output_path):
        """
        Writes the parsed and sorted data to a JSON file.
        
        Parameters:
            output_path (str): Path where the JSON file will be saved.
        """
        data = self.get_sorted_data()
        try:
            with open(output_path, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            logging.info(f"Data successfully written to {output_path}")
        except Exception as e:
            logging.error(f"Failed to write data to JSON: {e}")
            raise

def run_aspen(model_path, output_dir=None):
    """
    Main function to process the Aspen model and return parsed data. 
    Optionally writes the parsed data to a JSON file.
    
    Parameters:
        model_path (str): Path to the Aspen model file.
        output_dir (str): Optional path where the parsed data should be saved as a JSON file.
    
    Returns:
        dict: Parsed data in dictionary format.
    """
    if not os.path.exists(model_path):
        error_msg = f"Model file not found at: {model_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)

    parser = AspenModelParser(model_path)

    try:
        parser.initialize_model()
        parser.parse_model()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise RuntimeError(f"An error occurred: {e}")

    parsed_data = parser.get_sorted_data()

    if output_dir is not None:
        try:
            parser.write_to_json(output_dir)
        except Exception as e:
            logging.error(f"Failed to write output file: {e}")
            raise RuntimeError(f"Failed to write output file: {e}")

    return parsed_data
