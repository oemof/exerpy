"""
Ebsilon Model Parser

This module defines the EbsilonModelParser class, which is used to parse Ebsilon models,
simulate them, extract data about components and connections, and write the data to a JSON file.
"""

import os
import sys
import logging
from win32com.client import Dispatch
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from ebsilon_config import (
    ebs_objects,
    non_thermodynamic_unit_operators,
    fluid_type_index,
    composition_params,
    grouped_components
)

# Configure logging to display info-level messages
logging.basicConfig(level=logging.INFO)


class EbsilonModelParser:
    """
    A class to parse Ebsilon models, simulate them, extract data, and write to JSON.
    """
    def __init__(self, model_path):
        """
        Initializes the parser with the given model path.
        
        Parameters:
            model_path (str): Path to the Ebsilon model file.
        """
        self.model_path = model_path
        self.app = None  # Ebsilon application instance
        self.model = None  # Opened Ebsilon model
        self.oc = None  # ObjectCaster for type casting
        self.components_data = {}  # Dictionary to store component data
        self.connections_data = {}  # Dictionary to store connection data

    def initialize_model(self):
        """
        Initializes the Ebsilon application and opens the specified model.
        """
        try:
            # Start Ebsilon application via COM Dispatch
            self.app = Dispatch("EbsOpen.Application")
            # Open the model file
            self.model = self.app.Open(self.model_path)
            # Get the ObjectCaster for type conversions
            self.oc = self.app.ObjectCaster
            logging.info(f"Model opened successfully: {self.model_path}")
        except Exception as e:
            logging.error(f"Failed to initialize the model: {e}")
            raise

    def simulate_model(self):
        """
        Simulates the Ebsilon model and logs any calculation errors.
        """
        try:
            # Prepare to collect calculation errors
            calc_errors = self.model.CalculationErrors
            # Run the simulation
            self.model.Simulate(calc_errors)
            error_count = calc_errors.Count
            logging.info(f"Simulation has {error_count} error(s)")
            # Log each error if any exist
            if error_count > 0:
                for i in range(1, error_count + 1):
                    error = calc_errors.Item(i)
                    logging.warning(f"Error {i}: {error.Description}")
        except Exception as e:
            logging.error(f"Failed during simulation: {e}")
            raise

    def parse_model(self):
        """
        Parses all objects in the Ebsilon model to extract component and connection data.
        """
        try:
            total_objects = self.model.Objects.Count
            logging.info(f"Parsing {total_objects} objects from the model")
            # Iterate over all objects in the model
            for j in range(1, total_objects + 1):
                obj = self.model.Objects.item(j)
                # Check if the object is a component (epObjectKindComp = 10)
                if obj.IsKindOf(10):
                    self.parse_component(obj)
        except Exception as e:
            logging.error(f"Error while parsing the model: {e}")
            raise

    def parse_component(self, obj):
        """
        Parses an individual component and its connections.
        
        Parameters:
            obj: The Ebsilon component object to parse.
        """
        # Parse connections associated with the component
        self.parse_connections(obj)
        # Parse the component's own data
        self.parse_component_data(obj)

    def parse_connections(self, obj):
        """
        Parses the connections (pipes) associated with a component.
        
        Parameters:
            obj: The Ebsilon component object whose connections are to be parsed.
        """
        # Iterate over all links (connectors) of the component
        for i in range(1, obj.Links.Count + 1):
            link = obj.Links.item(i)
            # Check if the link has an associated pipe (connection)
            if link.HasPipe:
                pipe = link.Pipe
                # Check if the pipe is connected to components at either end
                if pipe.HasComp(0) or pipe.HasComp(1):
                    # Get the components at both ends of the pipe
                    comp0 = pipe.Comp(0) if pipe.HasComp(0) else None
                    comp1 = pipe.Comp(1) if pipe.HasComp(1) else None
                    # Get the connectors (links) at both ends of the pipe
                    link0 = pipe.Link(0) if pipe.HasComp(0) else None
                    link1 = pipe.Link(1) if pipe.HasComp(1) else None
                    # Cast the pipe to the correct type
                    pipe_cast = self.oc.CastToPipe(pipe)

                    # Collect connection data
                    connection_data = {
                        'name': pipe.Name,
                        'source_component': comp0.Name if comp0 else None,
                        'source_connector': link0.Index if link0 else None,
                        'target_component': comp1.Name if comp1 else None,
                        'target_connector': link1.Index if link1 else None,
                        'fluid_type': fluid_type_index.get(pipe_cast.FluidType, "Unknown"),
                        'fluid_properties': {
                            'mass_flow': pipe_cast.M.Value if hasattr(pipe_cast, 'M') else 0,
                            'temperature': pipe_cast.T.Value if hasattr(pipe_cast, 'T') else 0,
                            'pressure': pipe_cast.P.Value if hasattr(pipe_cast, 'P') else 0,
                            'enthalpy': pipe_cast.H.Value if hasattr(pipe_cast, 'H') else 0,
                            'entropy': pipe_cast.S.Value if hasattr(pipe_cast, 'S') else 0,
                            'physical_exergy': pipe_cast.E.Value if hasattr(pipe_cast, 'E') else 0,
                            'vapour_content': pipe_cast.X.Value if hasattr(pipe_cast, 'X') else 0,
                            'energy_flow': pipe_cast.Q.Value if hasattr(pipe_cast, 'Q') else 0
                        },
                        # Collect fluid composition parameters
                        'composition': {
                            param: getattr(pipe_cast, param).Value if hasattr(pipe_cast, param) else 0
                            for param in composition_params
                        }
                    }
                    # Store the connection data using the pipe's name as the key
                    self.connections_data[pipe.Name] = connection_data

    def parse_component_data(self, obj):
        """
        Parses data from a component, including its type and various properties.
        
        Parameters:
            obj: The Ebsilon component object to parse.
        """
        type_index = obj.TypeIndex
        # Get the human-readable type name of the component
        type_name = ebs_objects.get(type_index, f"Unknown Type {type_index}")
        # Exclude certain types of components that are not thermodynamic unit operators
        if type_index not in non_thermodynamic_unit_operators:
            # Cast the component to the correct type
            comp_cast = self.oc.CastToComp(obj)
            # Collect component data
            component_data = {
                'name': comp_cast.Name,
                'type': type_name,
                'eta_s': comp_cast.ETAIN.Value if hasattr(comp_cast, 'ETAIN') else None,
                'eta_mech': comp_cast.ETAMN.Value if hasattr(comp_cast, 'ETAMN') else None,
                'eta_cc': comp_cast.ETAB.Value if hasattr(comp_cast, 'ETAB') else None,
                'lambda': comp_cast.ALAMN.Value if hasattr(comp_cast, 'ALAMN') else None,
                'Q': comp_cast.QT.Value if hasattr(comp_cast, 'QT') else None,
                'kA': comp_cast.KA.Value if hasattr(comp_cast, 'KA') else None,
                'P': comp_cast.P.Value if hasattr(comp_cast, 'P') else None,
            }

            # Determine the group for the component based on its type
            group = None
            for group_name, type_list in grouped_components.items():
                if type_index in type_list:
                    group = group_name
                    break
            # If the component type doesn't belong to any predefined group, use its type name
            if not group:
                group = type_name

            # Initialize the group in the components_data dictionary if not already present
            if group not in self.components_data:
                self.components_data[group] = {}
            # Store the component data using the component's name as the key
            self.components_data[group][comp_cast.Name] = component_data

    def get_sorted_data(self):
        """
        Sorts the component and connection data alphabetically by name.
        
        Returns:
            dict: A dictionary containing sorted 'components' and 'connections' data.
        """
        # Sort components within each group by component name
        sorted_components = {
            comp_type: dict(sorted(self.components_data[comp_type].items()))
            for comp_type in sorted(self.components_data)
        }
        # Sort connections by their names
        sorted_connections = dict(sorted(self.connections_data.items()))
        return {
            'components': sorted_components,
            'connections': sorted_connections
        }

    def write_to_json(self, output_path):
        """
        Writes the parsed and sorted data to a JSON file.
        
        Parameters:
            output_path (str): Path where the JSON file will be saved.
        """
        data = self.get_sorted_data()
        try:
            # Write the data to a JSON file with indentation for readability
            with open(output_path, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            logging.info(f"Data successfully written to {output_path}")
        except Exception as e:
            logging.error(f"Failed to write data to JSON: {e}")
            raise


def run_ebsilon(model_path, output_dir):
    """
    Main function to process the Ebsilon model and write data to a JSON file.
    """

    # Check if the model file exists at the specified path
    if not os.path.exists(model_path):
        logging.error(f"Model file not found at: {model_path}")
        return

    # Initialize the Ebsilon model parser with the model file path
    parser = EbsilonModelParser(model_path)

    try:
        # Initialize the Ebsilon model within the parser
        parser.initialize_model()

        # Simulate the Ebsilon model
        parser.simulate_model()

        # Parse data from the simulated model
        parser.parse_model()
    except Exception as e:
        # Log any exceptions that occur during model processing
        logging.error(f"An error occurred during model processing: {e}")
        return

    try:
        # Write the parsed data to the JSON file
        parser.write_to_json(output_dir)
    except Exception as e:
        # Log any exceptions that occur during writing the output file
        logging.error(f"An error occurred while writing the output file: {e}")
        return