import numpy as np
import pandas as pd
import json
from tabulate import tabulate
from .components.component import component_registry
from .parser.from_ebsilon import ebsilon_parser as ebs_parser
from .parser.from_aspen import aspen_parser
from .functions import add_chemical_exergy, add_total_exergy_flow
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

        self.E_F = {
            'inputs': [],
            'outputs': []
        }
        self.E_P = {
            'inputs': [],
            'outputs': []
        }
        self.E_L = {
            'inputs': [],
            'outputs': []
        }

        self.Tamb = Tamb
        self.pamb = pamb

        # Convert the parsed data into components
        self.components = _construct_components(component_data, connection_data)
        self.connections = connection_data
        

    def analyse(self, E_F, E_P, E_L={}) -> None:
        """
        Run the exergy analysis for the entire system and calculate overall exergy efficiency.

        Parameters
        ----------
        E_F : dict
            Dictionary containing input connections for fuel exergy (e.g., {"inputs": ["1", "2"]}).
        E_P : dict
            Dictionary containing input and output connections for product exergy (e.g., {"inputs": ["E1"], "outputs": ["T1", "T2"]}).
        E_L : dict, optional
            Dictionary containing input and output connections for loss exergy (default is {}).
        """
        # Initialize class attributes for the exergy value of the total system
        self.E_F = 0.0
        self.E_P = 0.0
        self.E_L = 0.0

        # Calculate total fuel exergy (E_F) by summing up all specified input connections
        if "inputs" in E_F:
            self.E_F += sum(
                self.connections[conn]['E']
                for conn in E_F["inputs"]
                if conn in self.connections and self.connections[conn]['E'] is not None
            )

        if "outputs" in E_F:
            self.E_F -= sum(
                self.connections[conn]['E']
                for conn in E_F["outputs"]
                if conn in self.connections and self.connections[conn]['E'] is not None
            )

        # Calculate total product exergy (E_P) by summing up all specified input and output connections
        if "inputs" in E_P:
            self.E_P += sum(
                self.connections[conn]['E']
                for conn in E_P["inputs"]
                if conn in self.connections and self.connections[conn]['E'] is not None
            )
        if "outputs" in E_P:
            self.E_P -= sum(
                self.connections[conn]['E']
                for conn in E_P["outputs"]
                if conn in self.connections and self.connections[conn]['E'] is not None
            )

        # Calculate total loss exergy (E_L) by summing up all specified input and output connections
        if "inputs" in E_L:
            self.E_L += sum(
                self.connections[conn]['E']
                for conn in E_L["inputs"]
                if conn in self.connections and self.connections[conn]['E'] is not None
            )
        if "outputs" in E_L:
            self.E_L -= sum(
                self.connections[conn]['E']
                for conn in E_L["outputs"]
                if conn in self.connections and self.connections[conn]['E'] is not None
            )

        # Calculate overall exergy efficiency epsilon = E_P / E_F
        self.epsilon = self.E_P / self.E_F if self.E_F != 0 else None

        # The rest is counted as total exergy destruction with all components of the system
        self.E_D = self.E_F - self.E_P - self.E_L

        logging.info(f"Overall exergy analysis completed: E_F = {self.E_F:.2f} kW, E_P = {self.E_P:.2f} kW, E_L = {self.E_L:.2f} kW, Efficiency = {self.epsilon:.2%}")

        # Perform exergy balance for each individual component in the system
        total_component_E_D = 0.0
        for component_name, component in self.components.items():
            # Calculate E_F, E_D, E_P
            component.calc_exergy_balance(self.Tamb, self.pamb)
            # Calculate y and y* for each component
            component.y = component.E_D / self.E_F if component.E_D is not None else None
            component.y_star = component.E_D / self.E_D if component.E_D is not None else None
            # Calculate the total exergy destruction with the system based on components' E_D
            if component.E_D is not None:
                total_component_E_D += component.E_D

        # Check if the sum of all component exergy destructions matches the overall system exergy destruction
        if not np.isclose(total_component_E_D, self.E_D, rtol=1e-5):
            logging.warning(f"Sum of component exergy destructions ({total_component_E_D:.2f} W) "
                            f"does not match overall system exergy destruction ({self.E_D:.2f} W).")
        else:
            logging.info(f"Exergy destruction check passed: Sum of component E_D matches overall E_D.")


    
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
    def from_aspen(cls, path, simulate=True, Tamb=None, pamb=None, chemExLib=None):
        """
        Create an instance of the ExergyAnalysis class from an Aspen model file.

        Parameters
        ----------
        path : str
            Path to the Aspen file (.bkp format).
        Tamb : float, optional
            Ambient temperature for analysis, default is None.
        pamb : float, optional
            Ambient pressure for analysis, default is None.
        simulate : bool, optional
            If True, run the simulation. If False, load existing data from '_parsed.json' file, default is True.

        Returns
        -------
        ExergyAnalysis
            An instance of the ExergyAnalysis class with parsed Aspen data.
        """
        # Check if the file is an Aspen file
        _, file_extension = os.path.splitext(path)
        if file_extension == '.bkp':
            output_path = path.replace('.bkp', '_parsed.json')

            # If simulate is set to False, try to load the existing JSON data
            if not simulate:
                try:
                    if os.path.exists(output_path):
                        # Load the previously saved parsed JSON data
                        with open(output_path, 'r') as json_file:
                            aspen_data = json.load(json_file)
                            logging.info(f"Successfully loaded existing Aspen data from {output_path}.")
                    else:
                        logging.error(
                            'Skipping the simulation requires a pre-existing file with the ending "_parsed.json". '
                            f'File not found at {output_path}.'
                        )
                        raise FileNotFoundError(f'File not found: {output_path}')
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logging.error(f"Failed to load or decode existing JSON file: {e}")
                    raise

            # If simulation is requested, run the Aspen parser
            else:
                logging.info("Running Aspen simulation and generating JSON data.")
                aspen_data = aspen_parser.run_aspen(path)
                logging.info("Simulation completed successfully.")

        else:
            # If the file format is not supported
            raise ValueError(f"Unsupported file format: {file_extension}. Please provide an Aspen (.bkp) file.")

        # Retrieve the ambient conditions from the simulation or use provided values
        Tamb = aspen_data['ambient_conditions'].get('Tamb', Tamb)
        pamb = aspen_data['ambient_conditions'].get('pamb', pamb)

        # Add chemical exergy values
        try:
            if chemExLib is not None:
                aspen_data = add_chemical_exergy(aspen_data, Tamb, pamb, chemExLib)
                logging.info("Chemical exergy values successfully added to the Aspen data.")
            else:
                logging.info("Chemical exergy values not added: No chemical exergy library provided.")
        except Exception as e:
            logging.error(f"Failed to add chemical exergy values: {e}")
            raise

        # Calculate the total exergy flow of each component
        try:
            aspen_data = add_total_exergy_flow(aspen_data)
            logging.info("Total exergy flows successfully added to the Aspen data.")
        except Exception as e:
            logging.error(f"Failed to add total exergy flows: {e}")
            raise

        # Save the generated JSON data
        try:
            with open(output_path, 'w') as json_file:
                json.dump(aspen_data, json_file, indent=4)
                logging.info(f"Parsed Aspen model and saved JSON data to {output_path}.")
        except Exception as e:
            logging.error(f"Failed to save parsed JSON data: {e}")
            raise

        # Extract component and connection data
        component_data = aspen_data.get("components", {})
        connection_data = aspen_data.get("connections", {})

        # Validate that required data is present
        if not component_data or not connection_data:
            logging.error("Component or connection data is missing or improperly formatted.")
            raise ValueError("Parsed Aspen data is missing required components or connections.")

        return cls(component_data, connection_data, Tamb, pamb)


    @classmethod
    def from_ebsilon(cls, path, simulate=True, Tamb=None, pamb=None, chemExLib=None):
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
        Tamb = ebsilon_data['ambient_conditions'].get('Tamb', Tamb)
        pamb = ebsilon_data['ambient_conditions'].get('pamb', pamb)

        # Add chemical exergy values
        try:
            if chemExLib is not None:
                ebsilon_data = add_chemical_exergy(ebsilon_data, Tamb, pamb, chemExLib)
                logging.info("Chemical exergy values successfully added to the EbsilonProfessional data.")
            else:
                logging.info("Chemical exergy values not added: No chemical exergy library provided.")
        except Exception as e:
            logging.error(f"Failed to add chemical exergy values: {e}")
            raise

        # Calculate the total exergy flow of each component
        try:
            ebsilon_data = add_total_exergy_flow(ebsilon_data)
            logging.info("Total exergy flows successfully added to the Ebsilon data.")
        except Exception as e:
            logging.error(f"Failed to add total exergy flows: {e}")
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
    

    @classmethod
    def from_json(cls, json_path: str, Tamb=None, pamb=None, chemExLib=None):
        """
        Create an ExergyAnalysis instance from a JSON file.

        Parameters
        ----------
        json_path : str
            Path to JSON file containing component and connection data.
        Tamb : float, optional
            Ambient temperature in K. If None, extracted from JSON.
        pamb : float, optional
            Ambient pressure in Pa. If None, extracted from JSON.
        chemExLib : str, optional
            Name of chemical exergy library to use. Default is None.

        Returns
        -------
        ExergyAnalysis
            Configured instance with data from JSON file.

        Raises
        ------
        FileNotFoundError
            If JSON file does not exist.
        ValueError
            If JSON structure is invalid or missing required data.
        JSONDecodeError
            If JSON file is malformed.
        """
        try:
            # Check file existence and extension
            if not os.path.exists(json_path):
                raise FileNotFoundError(f"File not found: {json_path}")
            
            if not json_path.endswith('.json'):
                raise ValueError("File must have .json extension")

            # Load and validate JSON
            with open(json_path, 'r') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON format: {e}")
                    raise

            # Validate required sections
            required_sections = ['components', 'connections', 'ambient_conditions']
            missing_sections = [s for s in required_sections if s not in data]
            if missing_sections:
                raise ValueError(f"Missing required sections: {missing_sections}")

            # Check for mass_composition in material streams if chemical exergy is requested
            if chemExLib:
                for conn_name, conn_data in data['connections'].items():
                    if conn_data.get('kind') == 'material' and 'mass_composition' not in conn_data:
                        raise ValueError(f"Material stream '{conn_name}' missing mass_composition")

            # Extract or use provided ambient conditions
            Tamb = Tamb or data['ambient_conditions'].get('Tamb')
            pamb = pamb or data['ambient_conditions'].get('pamb')

            if Tamb is None or pamb is None:
                raise ValueError("Ambient conditions (Tamb, pamb) must be provided either in JSON or as parameters")

            # Validate component data structure
            if not isinstance(data['components'], dict):
                raise ValueError("Components section must be a dictionary")
            
            for comp_type, components in data['components'].items():
                if not isinstance(components, dict):
                    raise ValueError(f"Component type '{comp_type}' must contain dictionary of components")
                
                for comp_name, comp_data in components.items():
                    required_comp_fields = ['name', 'type', 'type_index']
                    missing_fields = [f for f in required_comp_fields if f not in comp_data]
                    if missing_fields:
                        raise ValueError(f"Component '{comp_name}' missing required fields: {missing_fields}")

            # Validate connection data structure
            for conn_name, conn_data in data['connections'].items():
                required_conn_fields = ['kind', 'source_component', 'target_component']
                missing_fields = [f for f in required_conn_fields if f not in conn_data]
                if missing_fields:
                    raise ValueError(f"Connection '{conn_name}' missing required fields: {missing_fields}")

            # Add chemical exergy if library provided
            if chemExLib:
                data = add_chemical_exergy(data, Tamb, pamb, chemExLib)
                logging.info("Added chemical exergy values")

            # Calculate total exergy flows
            data = add_total_exergy_flow(data)
            logging.info("Added total exergy flows")

            return cls(data['components'], data['connections'], Tamb, pamb)

        except Exception as e:
            logging.error(f"Error processing JSON file: {e}")
            raise


    def exergy_results(self):
        """
        Displays a table of exergy analysis results with columns for E_F, E_P, E_D, and epsilon for each component,
        and additional information for material and non-material connections.
        
        Parameters
        ----------
        provide_csv : bool, optional
            If True, saves the results as CSV files, default is False.
        """
        # Define the lambda function for safe multiplication
        convert = lambda x, factor: x * factor if x is not None else None

        # COMPONENTS
        component_results = {
            "Component": [],
            "E_F [kW]": [],
            "E_P [kW]": [],
            "E_D [kW]": [],
            "E_L [kW]": [],
            "ε [%]": [],
            "y [%]": [],
            "y* [%]": []
        }

        # Populate the dictionary with exergy analysis data from each component
        for component_name, component in self.components.items():
            component_results["Component"].append(component_name)
            # Convert E_F, E_P, E_D, E_L from W to kW and epsilon to percentage using the lambda
            E_F_kW = convert(component.E_F, 1e-3)
            E_P_kW = convert(component.E_P, 1e-3)
            E_D_kW = convert(component.E_D, 1e-3)
            E_L_kW = convert(getattr(component, 'E_L', None), 1e-3) if getattr(component, 'E_L', None) is not None else 0
            epsilon_percent = convert(component.epsilon, 1e2)

            component_results["E_F [kW]"].append(E_F_kW)
            component_results["E_P [kW]"].append(E_P_kW)
            component_results["E_D [kW]"].append(E_D_kW)
            component_results["E_L [kW]"].append(E_L_kW)
            component_results["ε [%]"].append(epsilon_percent)
            component_results["y [%]"].append(convert(component.y, 1e2))
            component_results["y* [%]"].append(convert(component.y_star, 1e2))

        # Convert the component dictionary into a pandas DataFrame
        df_component_results = pd.DataFrame(component_results)

        # Sort the DataFrame by the "Component" column
        df_component_results = df_component_results.sort_values(by="Component")

        # Add the overall results to the components as dummy component "TOT"
        df_component_results.loc["TOT", "E_F [kW]"] = convert(self.E_F, 1e-3)
        df_component_results.loc["TOT", "Component"] = 'TOT'
        df_component_results.loc["TOT", "E_L [kW]"] = convert(self.E_L, 1e-3)
        df_component_results.loc["TOT", "E_P [kW]"] = convert(self.E_P, 1e-3)
        df_component_results.loc["TOT", "E_D [kW]"] = convert(self.E_D, 1e-3)
        df_component_results.loc["TOT", "ε [%]"] = convert(self.epsilon, 1e2)
        # Calculate the total y [%] and y* [%] as the sum of the values for all components
        df_component_results.loc["TOT", "y [%]"] = df_component_results["y [%]"].sum()
        df_component_results.loc["TOT", "y* [%]"] = df_component_results["y* [%]"].sum()
        
        # MATERIAL CONNECTIONS
        material_connection_results = {
            "Connection": [],
            "m [kg/s]": [],
            "T [°C]": [],
            "p [bar]": [],
            "h [kJ/kg]": [],
            "s [J/kgK]": [],
            "E [kW]": [],
            "e^PH [kJ/kg]": [],
            "e^T [kJ/kg]": [],
            "e^M [kJ/kg]": [],
            "e^CH [kJ/kg]": []
        }

        # NON-MATERIAL CONNECTIONS
        non_material_connection_results = {
            "Connection": [],
            "Kind": [],
            "Energy Flow [kW]": [],
            "Exergy Flow [kW]": []
        }

        # Populate the dictionaries with exergy analysis data for each connection
        for conn_name, conn_data in self.connections.items():
            # Separate material and non-material connections based on fluid type
            kind = conn_data.get("kind", None)
            
            # Check if the connection is a non-material energy flow type
            if kind in {'power', 'heat'}:
                # Non-material connections: only record energy flow, converted to kW using lambda
                non_material_connection_results["Connection"].append(conn_name)
                non_material_connection_results["Kind"].append(kind)
                non_material_connection_results["Energy Flow [kW]"].append(convert(conn_data.get("energy_flow"), 1e-3))
                non_material_connection_results["Exergy Flow [kW]"].append(convert(conn_data.get("E"), 1e-3))
            elif kind == 'material':
                # Material connections: record full data with conversions using lambda
                material_connection_results["Connection"].append(conn_name)
                material_connection_results["m [kg/s]"].append(conn_data.get('m', None))
                material_connection_results["T [°C]"].append(conn_data.get('T') - 273.15)  # Convert to °C
                material_connection_results["p [bar]"].append(convert(conn_data.get('p'), 1e-5))  # Convert bar to bar
                material_connection_results["h [kJ/kg]"].append(convert(conn_data.get('h'), 1e-3))  # Convert to kJ/kg
                material_connection_results["s [J/kgK]"].append(conn_data.get('s', None))
                material_connection_results["e^PH [kJ/kg]"].append(convert(conn_data.get('e_PH'), 1e-3))  # Convert to kJ/kg
                material_connection_results["e^T [kJ/kg]"].append(convert(conn_data.get('e_T'), 1e-3))    # Convert to kJ/kg
                material_connection_results["e^M [kJ/kg]"].append(convert(conn_data.get('e_M'), 1e-3))    # Convert to kJ/kg
                material_connection_results["e^CH [kJ/kg]"].append(convert(conn_data.get('e_CH'), 1e-3))  # Convert to kJ/kg
                material_connection_results["E [kW]"].append(convert(conn_data.get("E"), 1e-3))          # Convert to kW

        # Convert the material and non-material connection dictionaries into DataFrames
        df_material_connection_results = pd.DataFrame(material_connection_results)
        df_non_material_connection_results = pd.DataFrame(non_material_connection_results)

        # Sort the DataFrame by the "Connection" column
        df_material_connection_results = df_material_connection_results.sort_values(by="Connection")
        df_non_material_connection_results = df_non_material_connection_results.sort_values(by="Connection")

        # Print the material connection results DataFrame in the console in a table format
        print("\nMaterial Connection Exergy Analysis Results:")
        print(tabulate(df_material_connection_results.reset_index(drop=True), headers='keys', tablefmt='psql', floatfmt='.3f'))

        # Print the non-material connection results DataFrame in the console in a table format
        print("\nNon-Material Connection Exergy Analysis Results:")
        print(tabulate(df_non_material_connection_results.reset_index(drop=True), headers='keys', tablefmt='psql', floatfmt='.3f'))
        
        # Print the component results DataFrame in the console in a table format
        print("\nComponent Exergy Analysis Results:")
        print(tabulate(df_component_results.reset_index(drop=True), headers='keys', tablefmt='psql', floatfmt='.3f'))

        return df_component_results, df_material_connection_results, df_non_material_connection_results


def _construct_components(component_data, connection_data):
    components = {}  # Initialize a dictionary to store created components

    # Loop over component types (e.g., 'Combustion Chamber', 'Compressor')
    for component_type, component_instances in component_data.items():
        for component_name, component_information in component_instances.items():
            # Skip components of type 'Splitter'
            if component_type == "Splitter" or component_information.get('type') == "Splitter":
                logging.info(f"Skipping 'Splitter' component: {component_name}")
                continue  # Skip this component

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


class ExergoeconomicAnalysis:
    def __init__(self, exergy_analysis_instance):
        r"""
        Initialize the ExergoeconomicAnalysis with an existing ExergyAnalysis instance.

        Parameters
        ----------
        exergy_analysis_instance : ExergyAnalysis
            An instance of the ExergyAnalysis class containing components and connections.
        """
        self.exergy_analysis = exergy_analysis_instance
        self.connections = exergy_analysis_instance.connections
        self.components = exergy_analysis_instance.components
        self.num_variables = 0  # Track number of equations (or cost variables) for the matrix
        self.variables = {}  # New dictionary to map variable indices to names
        self.equations = {}  # New dictionary to map equation indices to kind of equation

    def initialize_cost_variables(self):
        """
        Assign unique indices to cost-related variables in the matrix system and build a dictionary
        that maps these indices to variable names.
        
        Material streams (kind "material") get three indices (thermal, mechanical, chemical),
        which are named as "<connection name>_c_eT", "<connection name>_c_eM", and "<connection name>_c_eCH".
        Non-material streams (e.g. "heat", "power") get one index, named as "<connection name>_c_tot".
        """
        col_number = 0

        # Process each connection (stream)
        for conn in self.connections.values():
            kind = conn.get("kind", "material")
            # For material streams, assign three indices.
            if kind == "material":
                conn["CostVar_index"] = {
                    "T": col_number,
                    "M": col_number + 1,
                    "CH": col_number + 2
                }
                # Create variable names for each of the three cost components.
                self.variables[str(col_number)]     = f"C_{conn['name']}_T"
                self.variables[str(col_number + 1)] = f"C_{conn['name']}_M"
                self.variables[str(col_number + 2)] = f"C_{conn['name']}_CH"
                col_number += 3
            # For non-material streams (e.g., heat, power), assign one index.
            elif kind in ("heat", "power"):
                conn["CostVar_index"] = {"exergy": col_number}
                self.variables[str(col_number)] = f"C_{conn['name']}_TOT"
                col_number += 1

        # Store the total number of cost variables for later use.
        self.num_variables = col_number



    def assign_user_costs(self, Exe_Eco_Costs):
        r"""
        Assign given component and connection costs from the user input dictionary.

        For components:
        - Look for a key "<component_name>_Z" and assign it (converted from €/h to €/s).
        If not provided, raise a ValueError.

        For connections:
        1) Only consider connections of accepted kinds.
        2) If the connection is an input (i.e. has no source_component) and no cost is provided
        in Exe_Eco_Costs, raise a ValueError.
        3) In all other cases (input connections with a provided cost and connections with a source_component 
        that have an assigned cost), assign the cost as follows:
        - For material connections, assign c_TOT and also assign cost breakdown (c_T, c_M, c_CH)
            and compute C_TOT as c_TOT * (e_T, e_M, e_CH * m).
        - For heat or power connections, only assign c_TOT and compute C_TOT as c_TOT times the energy flow E.
            
        Cost conversions:
        - For components: from €/h to €/s (divide by 3600).
        - For connections: from €/GJ to €/J (multiply by 1e-9).
        """
        # --- Component Costs ---
        for comp_name, comp in self.components.items():
            cost_key = f"{comp_name}_Z"
            if cost_key in Exe_Eco_Costs:
                comp.Z_costs = Exe_Eco_Costs[cost_key] / 3600  # Convert €/h to €/s
            else:
                raise ValueError(f"Cost for component '{comp_name}' is mandatory but not provided in Exe_Eco_Costs.")

        # --- Connection Costs ---
        accepted_kinds = {"material", "heat", "power"}
        for conn_name, conn in self.connections.items():
            kind = conn.get("kind", "material")

            # Only consider valid connection types
            if kind not in accepted_kinds:
                continue

            cost_key = f"{conn_name}_c"
            is_input = not conn.get("source_component")

            # If input connection and no cost is provided, raise an error.
            if is_input and cost_key not in Exe_Eco_Costs:
                raise ValueError(f"Cost for input connection '{conn_name}' is mandatory but not provided in Exe_Eco_Costs.")

            # Assign cost if provided.
            if cost_key in Exe_Eco_Costs:
                # Convert cost from €/GJ to €/J.
                c_TOT = Exe_Eco_Costs[cost_key] * 1e-9
                conn["c_TOT"] = c_TOT

                if kind == "material":
                    # Compute C_TOT based on exergy terms and mass flow.
                    conn["C_TOT"] = c_TOT * conn.get("E", 0)

                    # Assign cost breakdown for material streams.
                    exergy_terms = {"T": "e_T", "M": "e_M", "CH": "e_CH"}
                    for label, exergy_key in exergy_terms.items():
                        conn[f"c_{label}"] = c_TOT
                        conn[f"C_{label}"] = c_TOT * conn.get(exergy_key, 0) * conn.get("m", 0)

                elif kind in {"heat", "power"}:
                    # Ensure energy flow "E" is present before computing cost.
                    if "E" not in conn:
                        raise ValueError(f"Energy flow 'E' is missing for {kind} connection '{conn_name}'.")
                    
                    # Assign only the total cost for heat and power streams.
                    conn["C_TOT"] = c_TOT * conn["E"]



    def construct_matrix(self, Tamb):
        """
        Constructs the exergoeconomic cost matrix and vector.
        
        This function sets up two blocks of equations:
        1. For each productive component, the cost balance equation:
            (sum of inlet costs) - (sum of outlet costs) + Z_costs = 0.
        2. For each inlet connection, an equation to fix its cost variable
            to the provided cost (C_TOT or the cost breakdown for material streams).
        
        A connection is treated as an inlet stream if its source_component is either
        missing or not among the valid system components.
        """
        num_vars = self.num_variables
        A = np.zeros((num_vars, num_vars))
        b = np.zeros(num_vars)
        counter = 0

        # Get the set of valid component names.
        valid_components = {comp.name for comp in self.components.values()}

        # 1. Cost balance equations for productive components.
        for comp in self.components.values():
            for conn in self.connections.values():
                # Check if the connection is linked to a valid component.
                # If the connection's target is the component, it is an inlet (add +1).
                if conn.get("target_component") == comp.name:
                    for key, col in conn["CostVar_index"].items():
                        A[counter, col] = 1  # Incoming costs
                # If the connection's source is the component, it is an outlet (subtract -1).
                elif conn.get("source_component") == comp.name:
                    for key, col in conn["CostVar_index"].items():
                        A[counter, col] = -1  # Outgoing costs
                self.equations[counter] = f"Z_costs_{comp.name}"  # Store the equation name
            
            # Set the right-hand side to -Z_costs (investment costs)
            b[counter] = -getattr(comp, "Z_costs", 1)
            counter += 1

        # 2. Inlet stream equations.
        # For each connection that is considered an inlet stream, set the cost variable to the provided cost.
        for conn in self.connections.values():
            # A connection is treated as an inlet if its source_component is missing or not valid and is outlet is a system component.
            if not (conn.get("source_component") in valid_components) and (conn.get("target_component") in valid_components):
                kind = conn.get("kind", "material")
                if kind == "material":
                    # For material streams, we have three cost variables.
                    for label in ["T", "M", "CH"]:
                        idx = conn["CostVar_index"][label]
                        A[counter, idx] = 1  # Fix the cost variable to the provided cost.
                        # Use the breakdown cost if available; otherwise, use the overall C_TOT.
                        b[counter] = conn.get(f"C_{label}", conn.get("C_TOT", 0))
                        self.equations[counter] = f"boundary_stream_costs_{conn["name"]}_{label}"
                        counter += 1
                elif kind in {"heat", "power"}:
                    # For non-material streams, there is a single cost variable.
                    idx = conn["CostVar_index"]["exergy"]
                    A[counter, idx] = 1
                    b[counter] = conn.get("C_TOT", 0)
                    self.equations[counter] = f"boundary_stream_costs_{conn["name"]}_TOT"
                    counter += 1

        # 3. Auxiliary equations.
        # These equations are needed because we have more variables than components.
        # For each productive component call its auxiliary equation routine, if available.
        for comp in self.components.values():
            if hasattr(comp, "aux_eqs") and callable(comp.aux_eqs):
                # The aux_eqs function should accept the current matrix, vector, counter, and Tamb,
                # and return the updated (A, b, counter).
                A, b, counter, self.equations = comp.aux_eqs(A, b, counter, Tamb, self.equations)

        # Check that we have exactly as many equations as cost variables.
        # if counter != num_vars:
            # raise ValueError(f"Number of equations ({counter}) does not match number of variables ({num_vars}).")  # TODO: Enable this check

        return A, b


    def solve_exergoeconomic_analysis(self, Tamb):
        """
        Solve the exergoeconomic cost balance equations.
        """
        # Step 1: Construct the cost matrix
        exergy_cost_matrix, exergy_cost_vector = self.construct_matrix(Tamb)

        # Step 2: Solve the system of equations
        try:
            C_solution = np.linalg.solve(exergy_cost_matrix, exergy_cost_vector)
        except np.linalg.LinAlgError:
            raise ValueError("Exergoeconomic system is singular and cannot be solved.")

        # Step 3: Assign solutions to connections
        for conn_name, conn in self.connections.items():
            conn.C_therm = C_solution[conn.CostVar_index["therm"]]
            conn.C_mech = C_solution[conn.CostVar_index["mech"]]
            conn.C_chemical = C_solution[conn.CostVar_index["chemical"]]
            conn.C_tot = conn.C_therm + conn.C_mech + conn.C_chemical


    def run(self, Exe_Eco_Costs, Tamb):
        """
        Execute the full exergoeconomic analysis.

        Parameters
        ----------
        Exe_Eco_Costs : dict
            Dictionary containing cost assignments for components and connections.
        Tamb : float
            Ambient temperature in Kelvin.
        """
        self.initialize_cost_variables()
        self.assign_user_costs(Exe_Eco_Costs)
        self.solve_exergoeconomic_analysis(Tamb)
        print("Exergoeconomic analysis completed successfully.")

