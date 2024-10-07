import numpy as np
import pandas as pd
import json
from tabulate import tabulate
from .components import component_registry
from .parser.from_ebsilon import ebsilon_parser as ebs_parser
from .functions import add_chemical_exergy
import os
import logging


class ExergyAnalysis:
    def __init__(self, component_data, connection_data, Tamb, pamb) -> None:
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

        self.Tamb = Tamb
        self.pamb = pamb

        # Convert the parsed data into components
        self.components = _construct_components(component_data, connection_data)
        self.connections = connection_data
        

    def analyse(self) -> None:
        """Run the exergy analysis.

        Parameters
        ----------
        Tamb : float, optional
            Ambient temperature for analysis. If not provided, uses the value from the simulation data.

        pamb : float, optional
            Ambient pressure for analysis. If not provided, uses the value from the simulation data.
        """

        # Perform exergy balance for each component
        for component_name, component in self.components.items():
            component.calc_exergy_balance(self.Tamb, self.pamb)

    
    @classmethod
    def from_tespy(cls, nw, T0, p0, chemExLib, E_F, E_P, E_L):
        # WORK IN PROGRESS -------------------------------------------
        # calc_all_stream_exergies(nw, T0, p0, chemExLib)
        # tespy_result = parse_nw_exergy_results(nw)

        # component_data = tespy_result["Components"]
        # connection_data = tespy_result["Connections"]
        # return cls(component_data, connection_data)
        pass


    @classmethod
    def from_ebsilon(cls, path, Tamb=None, pamb=None, simulate=True):
        """
        Create an instance of the ExergyAnalysis class from an Ebsilon model file.

        Parameters
        ----------
        path : str
            Path to the Ebsilon file (.ebs format).
        Tamb : float, optional
            Ambient temperature for analysis, default is None.
        pamb : float, optional
            Ambient pressure for analysis, default is None.
        simulate : bool, optional
            If True, run the simulation. If False, load existing data from '_parsed.json' file, default is True.

        Returns
        -------
        ExergyAnalysis
            An instance of the ExergyAnalysis class with parsed Ebsilon data.
        """
        # Check if the file is an Ebsilon file
        _, file_extension = os.path.splitext(path)
        if file_extension == '.ebs':
            output_path = path.replace('.ebs', '_parsed.json')

            # If simulate is set to False, try to load the existing JSON data
            if not simulate:
                try:
                    if os.path.exists(output_path):
                        # Load the previously saved parsed JSON data
                        with open(output_path, 'r') as json_file:
                            ebsilon_data = json.load(json_file)
                            logging.info(f"Successfully loaded existing Ebsilon data from {output_path}.")
                    else:
                        logging.error(
                            'Skipping the simulation requires a pre-existing file with the ending "_parsed.json". '
                            f'File not found at {output_path}.'
                        )
                        raise FileNotFoundError(f'File not found: {output_path}')
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logging.error(f"Failed to load or decode existing JSON file: {e}")
                    raise

            # If simulation is requested, run the simulation
            else:
                logging.info("Running Ebsilon simulation and generating JSON data.")
                ebsilon_data = ebs_parser.run_ebsilon(path)
                logging.info("Simulation completed successfully.")

        else:
            # If the file format is not supported
            raise ValueError(f"Unsupported file format: {file_extension}. Please provide an Ebsilon (.ebs) file.")

        # Retrieve the ambient conditions from the simulation or use provided values
        Tamb = ebsilon_data.get('Tamb', Tamb)
        pamb = ebsilon_data.get('pamb', pamb)

        # Add chemical exergy values
        try:
            ebsilon_data = add_chemical_exergy(ebsilon_data, Tamb, pamb)
            logging.info("Chemical exergy values successfully added to the Ebsilon data.")
        except Exception as e:
            logging.error(f"Failed to add chemical exergy values: {e}")
            raise

        # Save the generated JSON data
        try:
            with open(output_path, 'w') as json_file:
                json.dump(ebsilon_data, json_file, indent=4)
                logging.info(f"Parsed Ebsilon model and saved JSON data to {output_path}.")
        except Exception as e:
            logging.error(f"Failed to save parsed JSON data: {e}")
            raise

        # Extract component and connection data
        component_data = ebsilon_data.get("components", {})
        connection_data = ebsilon_data.get("connections", {})

        # Validate that required data is present
        if not component_data or not connection_data:
            logging.error("Component or connection data is missing or improperly formatted.")
            raise ValueError("Parsed Ebsilon data is missing required components or connections.")

        return cls(component_data, connection_data, Tamb, pamb)


    def exergy_results(self, provide_csv=False):
        """
        Displays a table of exergy analysis results with columns for E_F, E_P, E_D, and epsilon for each component,
        and additional information for material and non-material connections.
        
        Parameters
        ----------
        provide_csv : bool, optional
            If True, saves the results as CSV files, default is False.
        """
        # Create a dictionary to store results for each component
        component_results = {
            "Component": [],
            "E_F [kW]": [],
            "E_P [kW]": [],
            "E_D [kW]": [],
            "ε [%]": []
        }

        # Populate the dictionary with exergy analysis data from each component
        for component_name, component in self.components.items():
            component_results["Component"].append(component_name)
            # Convert E_F, E_P, E_D from W to kW and epsilon to percentage
            component_results["E_F [kW]"].append(component.E_F / 1000 if component.E_F is not None else None)
            component_results["E_P [kW]"].append(component.E_P / 1000 if component.E_P is not None else None)
            component_results["E_D [kW]"].append(component.E_D / 1000 if component.E_D is not None else None)
            component_results["ε [%]"].append(component.epsilon * 100 if component.epsilon is not None else None)

        # Convert the component dictionary into a pandas DataFrame
        df_component_results = pd.DataFrame(component_results)
        
        # Create a dictionary to store results for material connections
        material_connection_results = {
            "Connection": [],
            "m [kg/s]": [],
            "T [K]": [],
            "p [Pa]": [],
            "h [J/kg]": [],
            "s [J/kgK]": [],
            "e^PH [J/kg]": [],
            "e^T [J/kg]": [],
            "e^M [J/kg]": [],
            "e^CH [J/kg]": []
        }

        # Create a dictionary to store results for non-material connections (e.g., electric, shaft)
        non_material_connection_results = {
            "Connection": [],
            "Energy Flow [kW]": []
        }

        # Populate the dictionaries with exergy analysis data for each connection
        for conn_name, conn_data in self.connections.items():
            # Separate material and non-material connections based on fluid type
            fluid_type = conn_data.get("fluid_type_id", None)
            
            # Check if the connection is a non-material type (e.g., electric, shaft)
            if fluid_type in [9, 10]:  # Assuming 9 is Electric, 10 is Shaft
                # Non-material connections: only record energy flow, converted to kW
                non_material_connection_results["Connection"].append(conn_name)
                non_material_connection_results["Energy Flow [kW]"].append(conn_data.get("energy_flow", 0) / 1000)
            else:
                # Material connections: record full data
                material_connection_results["Connection"].append(conn_name)
                material_connection_results["m [kg/s]"].append(conn_data.get('m'))
                material_connection_results["T [K]"].append(conn_data.get('T'))
                material_connection_results["p [Pa]"].append(conn_data.get('p'))
                material_connection_results["h [J/kg]"].append(conn_data.get('h'))
                material_connection_results["s [J/kgK]"].append(conn_data.get('s'))
                material_connection_results["e^PH [J/kg]"].append(conn_data.get('e_PH'))
                material_connection_results["e^T [J/kg]"].append(conn_data.get('e_T'))
                material_connection_results["e^M [J/kg]"].append(conn_data.get('e_M'))
                material_connection_results["e^CH [J/kg]"].append(conn_data.get('e_CH'))

        # Convert the material and non-material connection dictionaries into DataFrames
        df_material_connection_results = pd.DataFrame(material_connection_results)
        df_non_material_connection_results = pd.DataFrame(non_material_connection_results)

        # Print the component results DataFrame in the console in a table format
        print("\nComponent Exergy Analysis Results:")
        print(tabulate(df_component_results, headers='keys', tablefmt='psql', floatfmt='.3e'))

        # Print the material connection results DataFrame in the console in a table format
        print("\nMaterial Connection Exergy Analysis Results:")
        print(tabulate(df_material_connection_results, headers='keys', tablefmt='psql', floatfmt='.3e'))

        # Print the non-material connection results DataFrame in the console in a table format
        print("\nNon-Material Connection Exergy Analysis Results:")
        print(tabulate(df_non_material_connection_results, headers='keys', tablefmt='psql', floatfmt='.3e'))

        # Optionally, save all DataFrames to CSV files if requested
        if provide_csv:
            df_component_results.to_csv('exergy_analysis_component_results.csv', index=False)
            df_material_connection_results.to_csv('exergy_analysis_material_connection_results.csv', index=False)
            df_non_material_connection_results.to_csv('exergy_analysis_non_material_connection_results.csv', index=False)



def _construct_components(component_data, connection_data):
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