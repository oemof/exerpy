import os
import logging
import win32com.client as win32
import json

from exerpy.functions import convert_to_SI, fluid_property_data

from .aspen_config import (
    grouped_components,
)

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

            # Parse Tamb and pamb
            self.parse_ambient_conditions()	

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
        
        # ALL ASPEN CONNECTIONS
        # Initialize connection data with the common fields
        for stream_name in stream_names:
            stream_node = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}')
            connection_data = {
                'name': stream_name,
                'kind': None,
                'source_component': None,
                'source_connector': None,
                'target_component': None,
                'target_connector': None,
            }

            # Find the source and target components
            source_port_node = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\SOURCE')
            if source_port_node is not None and source_port_node.Elements.Count > 0:
                connection_data["source_component"] = source_port_node.Elements(0).Name

            destination_port_node = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Ports\DEST')
            if destination_port_node is not None and destination_port_node.Elements.Count > 0:
                connection_data["target_component"] = destination_port_node.Elements(0).Name

            # HEAT AND POWER STREAMS
            if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Input\WORK') is not None:
                connection_data['kind'] = 'power'
                connection_data['energy_flow'] = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\POWER_OUT').Value
            elif self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Input\HEAT') is not None:
                connection_data['kind'] = 'heat'
                connection_data['energy_flow'] = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\QCALC').Value
            
            # MATERIAL STREAMS
            else:
                # Assume it's a material stream and retrieve additional properties
                connection_data.update({
                    'kind': 'material',
                    'T': (
                        convert_to_SI(
                            'T',
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TEMP_OUT\MIXED').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TEMP_OUT\MIXED').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TEMP_OUT\MIXED') is not None else None
                    ),
                    'T_unit': fluid_property_data['T']['SI_unit'],
                    'p': (
                        convert_to_SI(
                            'p',
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\PRES_OUT\MIXED').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\PRES_OUT\MIXED').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\PRES_OUT\MIXED') is not None else None
                    ),
                    'p_unit': fluid_property_data['p']['SI_unit'],
                    'h': (
                        convert_to_SI(
                            'h',
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\HMX_MASS\MIXED').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\HMX_MASS\MIXED').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\HMX_MASS\MIXED') is not None else None
                    ),
                    'h_unit': fluid_property_data['h']['SI_unit'],
                    's': (
                        convert_to_SI(
                            's',
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\SMX_MASS\MIXED').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\SMX_MASS\MIXED').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\SMX_MASS\MIXED') is not None else None
                    ),
                    's_unit': fluid_property_data['s']['SI_unit'],
                    'm': (
                        convert_to_SI(
                            'm',
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MASSFLMX\MIXED').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MASSFLMX\MIXED').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MASSFLMX\MIXED') is not None else None
                    ),
                    'm_unit': fluid_property_data['m']['SI_unit'],
                    'e_PH': (
                        convert_to_SI(
                            'e',
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\STRM_UPP\EXERGYMS\MIXED\TOTAL').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\STRM_UPP\EXERGYMS\MIXED\TOTAL').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\STRM_UPP\EXERGYMS\MIXED\TOTAL') is not None else None
                    ),
                    'e_PH_unit': fluid_property_data['e']['SI_unit'],
                    'n': (
                        convert_to_SI(
                            'n',
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TOT_FLOW').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TOT_FLOW').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\TOT_FLOW') is not None else None
                    ),
                    'n_unit': fluid_property_data['n']['SI_unit'],
                    'mass_composition': {},
                    'molar_composition': {},
                })
                
                # Retrieve the fluid names for the stream
                fluid_names = [fluid.Name for fluid in self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MOLEFRAC\MIXED').Elements]
                
                # Retrieve the molar composition for each fluid
                for fluid_name in fluid_names:
                    mole_frac = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MOLEFRAC\MIXED\{fluid_name}').Value
                    if mole_frac not in [0, None]:  # Skip fluids with 0 or None as the fraction
                        connection_data["molar_composition"][fluid_name] = mole_frac

                # Retrieve the mass composition for each fluid
                for fluid_name in fluid_names:
                    mass_frac = self.aspen.Tree.FindNode(fr'\Data\Streams\{stream_name}\Output\MASSFRAC\MIXED\{fluid_name}').Value
                    if mass_frac not in [0, None]:  # Skip fluids with 0 or None as the fraction
                        connection_data["mass_composition"][fluid_name] = mass_frac

            # Store connection data
            self.connections_data[stream_name] = connection_data


    def parse_blocks(self):
        """
        Parses the blocks (components) in the Aspen model and ensures that all components, including motors created from pumps, are properly grouped.
        """
        block_nodes = self.aspen.Tree.FindNode(r'\Data\Blocks').Elements
        block_names = [block_node.Name for block_node in block_nodes]

        # Process each block
        for block_name in block_names:
            model_type = self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\MODEL_TYPE')
            component_data = {
                'name': block_name,
                'type': self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}').AttributeValue(6),
                'eta_s': (
                    self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\EFF_ISEN').Value
                    if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\EFF_ISEN') is not None else None
                ),
                'eta_mech': (
                    self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\EFF_MECH').Value
                    if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\EFF_MECH') is not None else None
                ),
                'Q': (
                    convert_to_SI(
                        'heat',
                        self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\QNET').Value,
                        self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\QNET').UnitString,
                    ) if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\QNET') is not None else None
                ),
                'Q_unit': fluid_property_data['heat']['SI_unit'],
                'P': (
                    convert_to_SI(
                        'power',
                        self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value,
                        self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').UnitString,
                    ) if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER') is not None else None
                ),
                'P_unit': fluid_property_data['power']['SI_unit'],
            }

            # Compressors and turbines are both handled as "Compr": check whether the block is a compressor or turbine
            if model_type is not None:
                if model_type.Value == "COMPRESSOR":
                    component_data['type'] = "Compressor"
                elif model_type.Value == "TURBINE":
                    component_data['type'] = "Turbine"

            # Generators are handled as multiplier blocks
            if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}').AttributeValue(6) == 'Mult':
                if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}').Value == 'WORK':
                    component_data.update({
                        'eta_el': (
                            self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\FACTOR').Value
                            if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Input\FACTOR') is not None else None
                        ),
                        'type': 'Generator'
                    })

            # Group other components such as pumps, compressors, turbines, and generators
            self._group_component(component_data, block_name)

            # Handle pumps and their associated motors
            if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}').AttributeValue(6) == 'Pump':
                # Create a corresponding Motor component
                motor_name = f"{block_name}-MOTOR"
                motor_data = {
                    'name': motor_name,
                    'type': 'Motor',
                    'P_el': (
                        convert_to_SI(
                            'power',
                            self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\ELEC_POWER').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\ELEC_POWER').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\ELEC_POWER') is not None else None
                    ),
                    'P_el_unit': fluid_property_data['power']['SI_unit'],
                    'P_mech': (
                        convert_to_SI(
                            'power',
                            self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').Value,
                            self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER').UnitString
                        ) if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\BRAKE_POWER') is not None else None
                    ),
                    'P_mech_unit': fluid_property_data['power']['SI_unit'],
                    'eta_el': (
                        self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\EFF_DRIV').Value
                        if self.aspen.Tree.FindNode(fr'\Data\Blocks\{block_name}\Output\EFF_DRIV') is not None else None
                    ),
                }

                # Group the motor using the same method
                self._group_component(motor_data, motor_name)

    def _group_component(self, component_data, component_name):
        """
        Group the component based on its type into the correct group within components_data.

        Parameters:
        - component_data: The dictionary of component attributes.
        - component_name: The name of the component.
        """
        # Determine the group for the component based on its type
        group = None
        for group_name, type_list in grouped_components.items():
            if component_data['type'] in type_list:
                group = group_name
                break

        # If the component doesn't belong to any predefined group, use its type name
        if not group:
            group = component_data['type']

        # Initialize the group in the components_data dictionary if not already present
        if group not in self.components_data:
            self.components_data[group] = {}

        # Store the component data in the appropriate group
        self.components_data[group][component_name] = component_data


    def parse_ambient_conditions(self):
        """
        Parses the ambient conditions from the Aspen model and stores them as class attributes.
        Raises an error if Tamb or pamb are not found or are set to None.
        """
        try:
            # Parse ambient temperature (Tamb)
            self.Tamb = convert_to_SI(
                'T',
                self.aspen.Tree.FindNode("\Data\Setup\Sim-Options\Input\REF_TEMP").Value,
                self.aspen.Tree.FindNode("\Data\Setup\Sim-Options\Input\REF_TEMP").UnitString
                ) if self.aspen.Tree.FindNode("\Data\Setup\Sim-Options\Input\REF_TEMP") is not None else None            
            
            if self.Tamb is None:
                raise ValueError("Ambient temperature (Tamb) not found in the Aspen model. Please set it in Setup > Calculation Options.")

            # Parse ambient pressure (pamb)
            self.pamb = convert_to_SI(
                'p',
                self.aspen.Tree.FindNode("\Data\Setup\Sim-Options\Input\REF_PRES").Value,
                self.aspen.Tree.FindNode("\Data\Setup\Sim-Options\Input\REF_PRES").UnitString
                ) if self.aspen.Tree.FindNode("\Data\Setup\Sim-Options\Input\REF_PRES") is not None else None            
            
            if self.pamb is None:
                raise ValueError("Ambient pressure (pamb) not found in the Aspen model. Please set it in Setup > Calculation Options.")

            logging.info(f"Parsed ambient conditions: Tamb = {self.Tamb} K, pamb = {self.pamb} Pa")

        except Exception as e:
            logging.error(f"Error parsing ambient conditions: {e}")
            raise


    def get_sorted_data(self):
        """
        Sorts the component and connection data alphabetically by name.

        Returns:
            dict: A dictionary containing sorted 'components', 'connections', and ambient conditions data.
        """
        sorted_components = {comp_name: self.components_data[comp_name] for comp_name in sorted(self.components_data)}
        sorted_connections = {conn_name: self.connections_data[conn_name] for conn_name in sorted(self.connections_data)}
        ambient_conditions = {
            'Tamb': self.Tamb,
            'Tamb_unit': fluid_property_data['T']['SI_unit'],
            'pamb': self.pamb,
            'pamb_unit': fluid_property_data['p']['SI_unit']
        }
        return {'components': sorted_components, 'connections': sorted_connections, 'ambient_conditions': ambient_conditions}


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
