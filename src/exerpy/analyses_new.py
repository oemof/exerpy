import numpy as np
import pandas as pd
import json
from .components import component_registry
from .parser.from_ebsilon import ebsilon_parser as ebs_parser
from .functions import add_chemical_exergy
import os
import logging

class ExergyAnalysis:
    def __init__(self, path_of_simulation):
        """
        Constructor for ExergyAnalysis. It parses the provided simulation file and prepares it for exergy analysis.
        
        Parameters
        ----------
        path_of_simulation : str
            Path to the simulation file (e.g., "my_simulation.ebs" for Ebsilon models).
        """

        self.E_F = []
        self.E_P = []
        self.E_L = []

        # Detect file type and parse the simulation
        self.simulation_data = self._parse_simulation_file(path_of_simulation)

        # Convert the parsed data into components
        self.components = _construct_components(self.simulation_data)

    def _parse_simulation_file(self, path_of_simulation):
        """
        Parses the simulation file based on its format (currently supports .ebs for Ebsilon).
        
        Parameters
        ----------
        path_of_simulation : str
            Path to the simulation file (e.g., .ebs).
        
        Returns
        -------
        dict
            Parsed simulation data as a dictionary.
        """
        _, file_extension = os.path.splitext(path_of_simulation)

        # PARSING FROM EBSILON
        # TODO general function and if condition for simulation type in the parser functions?
        if file_extension == '.ebs':
            output_path = path_of_simulation.replace('.ebs', '_parsed.json')
            if os.path.exists(output_path):
                try:
                    with open(output_path, 'r') as json_file:
                        json_data = json.load(json_file)
                        return json_data
                except json.JSONDecodeError as e:
                    logging.error(f"JSON decoding error: {e}")
                    raise e  # Raise an error if the JSON format is invalid
            else:
                logging.info("Parsing the Ebsilon model and generating JSON data.")
                json_data = ebs_parser.run_ebsilon(path_of_simulation)

                # Save the generated JSON data
                with open(output_path, 'w') as json_file:
                    json.dump(json_data, json_file, indent=4)
                    logging.info(f"Parsed Ebsilon model and saved JSON data to {output_path}")

                if os.path.exists(output_path):
                    return json_data
                else:
                    logging.error("Ebsilon model parsing failed; JSON file not created.")
                    raise Exception("Ebsilon model parsing failed; JSON file not created.")
                
        else:
            raise ValueError(f"This format file has not implemented yet. Try with: {file_extension}")
        
    def analyse(self, Tamb, pamb):
        """Run the exergy analysis.

        Parameters
        ----------
        pamb : float
            Ambient pressure value for analysis, provide value in network's
            pressure unit.

        Tamb : float
            Ambient temperature value for analysis, provide value in network's
            temperature unit.
        """

        self.simulation_data = add_chemical_exergy(self.simulation_data, Tamb, pamb)

        # Perform exergy balance for each component
        for component_name, component in self.components.items():
            component.calc_exergy_balance(Tamb, pamb)

    def exergy_results(self, provide_csv=False):
        """
        Displays a table of exergy analysis results with columns for E_F, E_P, E_D, and epsilon
        for each component in the system.
        """
        # Create a dictionary to store results for each component
        results = {
            "Component": [],
            "E_F (Fuel Exergy)": [],
            "E_P (Product Exergy)": [],
            "E_D (Exergy Destruction)": [],
            "ε (Exergy Efficiency)": []
        }

        # Populate the dictionary with exergy analysis data from each component
        for component_name, component in self.components.items():
            results["Component"].append(component_name)
            results["E_F (Fuel Exergy)"].append(component.E_F)
            results["E_P (Product Exergy)"].append(component.E_P)
            results["E_D (Exergy Destruction)"].append(component.E_D)
            results["ε (Exergy Efficiency)"].append(component.epsilon)

        # Convert the dictionary into a pandas DataFrame
        df_results = pd.DataFrame(results)
        
        # Print the DataFrame in the console in a table format
        print("Exergy Analysis Results:")
        print(df_results.to_string(index=False))

        # Optionally, save the DataFrame to a CSV file
        if provide_csv:
            return df_results.to_csv('exergy_analysis_results.csv', index=False)

def _construct_components(data):
    component_data = data['components']
    connection_data = data['connections']  # Include connection data to link streams
    components = {}  # Initialize a dictionary to store created components

    # Loop over component types (e.g., 'Combustion Chamber', 'Compressor')
    for component_type, component_instances in component_data.items():
        for component_name, component_information in component_instances.items():
            # Fetch the corresponding class from the registry using the component type
            component_class = component_registry.items.get(component_type)

            if component_class is None:
                raise ValueError(f"Component type '{component_type}' is not registered.")

            # Instantiate the component with its attributes
            kwargs = component_information
            kwargs["label"] = component_name  # Use the component's name as the label
            component = component_class(**kwargs)

            # Initialize empty dictionaries for inlets and outlets
            component.inl = {}
            component.outl = {}

            # Assign streams to the components based on connection data
            for conn_id, conn_info in connection_data.items():
                # Assign inlet streams
                if conn_info['target_component'] == component_name:
                    target_connector_idx = conn_info['target_connector']  # Use 0-based indexing
                    component.inl[target_connector_idx] = conn_info  # Assign inlet stream
                
                # Assign outlet streams
                if conn_info['source_component'] == component_name:
                    source_connector_idx = conn_info['source_connector']  # Use 0-based indexing
                    component.outl[source_connector_idx] = conn_info  # Assign outlet stream

            # Store the component in the dictionary
            components[component_name] = component

    return components  # Return the dictionary of created components