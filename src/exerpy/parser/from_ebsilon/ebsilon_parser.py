"""
Ebsilon Model Parser

This module defines the EbsilonModelParser class, which is used to parse Ebsilon models,
simulate them, extract data about components and connections, and write the data to a JSON file.
"""
import os
import logging
import json


from exerpy.functions import convert_to_SI, fluid_property_data
from . import __ebsilon_path__


if __ebsilon_path__ is not None:
    from EbsOpen import EpFluidType, EpSteamTable, EpGasTable, EpSubstance, EpCalculationResultStatus2
    from win32com.client import Dispatch


from .ebsilon_config import (
    ebs_objects,
    non_thermodynamic_unit_operators,
    fluid_type_index,
    composition_params,
    grouped_components,
    connector_mapping,
    unit_id_to_string,
    connection_kinds,
    two_phase_fluids_mapping
)

# Configure logging to display info-level messages
logging.basicConfig(level=logging.ERROR)


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
        # check here if ebsilon dependencies are available, raise error if not

        self.model_path = model_path
        self.app = None  # Ebsilon application instance
        self.model = None  # Opened Ebsilon model
        self.oc = None  # ObjectCaster for type casting
        self.components_data = {}  # Dictionary to store component data
        self.connections_data = {}  # Dictionary to store connection data
        self.Tamb = None  # Ambient temperature
        self.pamb = None  # Ambient pressure

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
            self.model.SimulateNew()
            error_count = calc_errors.Count
            logging.warning(f"Simulation has {error_count} warning(s).")
            # Log each error if any exist
            if error_count > 0:
                for i in range(1, error_count + 1):
                    error = calc_errors.Item(i)
                    logging.warning(f"Warning {i}: {error.Description}")
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
            # Iterate over all objects in the model and select the components
            for j in range(1, total_objects + 1):
                obj = self.model.Objects.Item(j)
                # Check if the object is a component (epObjectKindComp = 10)
                if obj.IsKindOf(10):
                    self.parse_component(obj)

            # After parsing all components, check if Tamb and pamb have been set
            if self.Tamb is None or self.pamb is None:
                error_msg = (
                    "Ambient temperature (Tamb) and/or ambient pressure (pamb) have not been set.\n"
                    "Please ensure that your Ebsilon model includes component(s) of type 46 (Measuring Point) "
                    "with a setting for the Ambient Temperature and the Ambient Pressure in MEASM."
                )
                logging.error(error_msg)
                raise ValueError(error_msg)

            # Iterate over all objects in the model and select the connections
            for j in range(1, total_objects + 1):
                obj = self.model.Objects.Item(j)
                # Check if the object is a pipe (epObjectKindPipe = 16)
                if obj.IsKindOf(16):
                    self.parse_connection(obj)

        except Exception as e:
            logging.error(f"Error while parsing the model: {e}")
            raise


    def parse_connection(self, obj):
        """
        Parses the connections (pipes) associated with a component.

        Parameters:
            obj: The Ebsilon component object whose connections are to be parsed.
        """
        from .ebsilon_functions import calc_eM, calc_eT

        # Cast the pipe to the correct type
        pipe_cast = self.oc.CastToPipe(obj)

        # Define fluid types that are considered non-material or non-energetic
        non_material_fluids = {5, 6, 9, 10, 13}  # Scheduled, Actual, Electric, Shaft, Logic
        non_energetic_fluids = {5, 6}  # Scheduled, Actual
        power_fluids = {9, 10}  # Electric, Shaft
        logic_fluids = 13  # Logic "fluids" for heat and power flows
        heat_components = {15, 16, 35}  # Components that handle with heat flows as input or output
        power_components = {31}  # Power-summerized with power flows ONLY as output

        # ALL EBSILON CONNECTIONS
        # Initialize connection data with the common fields
        connection_data = {
            'name': pipe_cast.Name,
            'kind': "other",  # it will be changed later ("material", "heat", "power") according to the fluid type
            'source_component': None,
            'source_component_type': None,
            'source_connector': None,
            'target_component': None,
            'target_component_type': None,
            'target_connector': None,
            'fluid_type': fluid_type_index.get(pipe_cast.FluidType, "Unknown"),
            'fluid_type_id': pipe_cast.FluidType,
        }

        # Check if the connection is is not in non-energetic fluids
        if (pipe_cast.Kind - 1000) not in non_energetic_fluids:
            # Get the components at both ends of the pipe
            comp0 = pipe_cast.Comp(0) if pipe_cast.HasComp(0) else None
            comp1 = pipe_cast.Comp(1) if pipe_cast.HasComp(1) else None
            # Get the connectors (links) at both ends of the pipe
            link0 = pipe_cast.Link(0) if pipe_cast.HasComp(0) else None
            link1 = pipe_cast.Link(1) if pipe_cast.HasComp(1) else None

            # GENERAL INFORMATION
            connection_data.update({
                'source_component': comp0.Name if comp0 else None,
                'source_component_type': (comp0.Kind - 10000) if comp0 else None,
                'source_connector': link0.Index if link0 else None,
                'target_component': comp1.Name if comp1 else None,
                'target_component_type': (comp1.Kind - 10000) if comp1 else None,
                'target_connector': link1.Index if link1 else None,
            })

            # MATERIAL CONNECTIONS
            if (pipe_cast.Kind - 1000) not in non_material_fluids:
                # Retrieve all data and convert them in SI units
                connection_data.update({
                    'kind': 'material',
                    'm': (
                        convert_to_SI(
                            'm',
                            pipe_cast.M.Value,
                            unit_id_to_string.get(pipe_cast.M.Dimension, "Unknown")
                        ) if hasattr(pipe_cast, 'M') and pipe_cast.M.Value is not None else None
                    ),
                    'm_unit': fluid_property_data['m']['SI_unit'],

                    'T': (
                        convert_to_SI(
                            'T',
                            pipe_cast.T.Value,
                            unit_id_to_string.get(pipe_cast.T.Dimension, "Unknown")
                        ) if hasattr(pipe_cast, 'T') and pipe_cast.T.Value is not None else None
                    ),
                    'T_unit': fluid_property_data['T']['SI_unit'],

                    'p': (
                        convert_to_SI(
                            'p',
                            pipe_cast.P.Value,
                            unit_id_to_string.get(pipe_cast.P.Dimension, "Unknown")
                        ) if hasattr(pipe_cast, 'P') and pipe_cast.P.Value is not None else None
                    ),
                    'p_unit': fluid_property_data['p']['SI_unit'],

                    'h': (
                        convert_to_SI(
                            'h',
                            pipe_cast.H.Value,
                            unit_id_to_string.get(pipe_cast.H.Dimension, "Unknown")
                        ) if hasattr(pipe_cast, 'H') and pipe_cast.H.Value is not None else None
                    ),
                    'h_unit': fluid_property_data['h']['SI_unit'],

                    's': (
                        convert_to_SI(
                            's',
                            pipe_cast.S.Value,
                            unit_id_to_string.get(pipe_cast.S.Dimension, "Unknown")
                        ) if hasattr(pipe_cast, 'S') and pipe_cast.S.Value is not None else None
                    ),
                    's_unit': fluid_property_data['s']['SI_unit'],

                    'e_PH': (
                        convert_to_SI(
                            'e',
                            pipe_cast.E.Value,
                            unit_id_to_string.get(pipe_cast.E.Dimension, "Unknown")
                        ) if hasattr(pipe_cast, 'E') and pipe_cast.E.Value is not None else None
                    ),
                    'e_PH_unit': fluid_property_data['e']['SI_unit'],

                    'x': (
                        convert_to_SI(
                            'x',
                            pipe_cast.X.Value,
                            unit_id_to_string.get(pipe_cast.X.Dimension, "Unknown")
                        ) if hasattr(pipe_cast, 'X') and pipe_cast.X.Value is not None else None
                    ),
                    'x_unit': fluid_property_data['x']['SI_unit'],
                })

                # Add the mechanical and thermal specific exergies
                e_T_value = calc_eT(self.app, pipe_cast, connection_data['p'], self.Tamb, self.pamb)
                e_M_value = calc_eM(self.app, pipe_cast, connection_data['p'], self.Tamb, self.pamb)

                connection_data.update({
                    'e_T': e_T_value,
                    'e_T_unit': fluid_property_data['e']['SI_unit'],
                    'e_M': e_M_value,
                    'e_M_unit': fluid_property_data['e']['SI_unit']
                })

                # Handle mass composition logic for fluids
                if fluid_type_index.get(pipe_cast.FluidType, "Unknown") in ['Steam', 'Water']:
                    connection_data['mass_composition'] = {'H2O': 1}
                elif fluid_type_index.get(pipe_cast.FluidType, "Unknown") in ['2PhaseLiquid', '2PhaseGaseous']:
                    # Get the FMED value to determine the substance
                    fmed_value = pipe_cast.FMED.Value if hasattr(pipe_cast, 'FMED') else None
                    if fmed_value in two_phase_fluids_mapping.keys():
                        connection_data['mass_composition'] = two_phase_fluids_mapping[fmed_value]
                    else:
                        connection_data['mass_composition'] = {}  # Default if no mapping found
                        logging.warning(f"FMED value {fmed_value} not found in fluid_composition_mapping. Please add it.")
                else:
                    connection_data['mass_composition'] = {
                        param.lstrip('X'): getattr(pipe_cast, param).Value
                        for param in composition_params
                        if hasattr(pipe_cast, param) and getattr(pipe_cast, param).Value not in [0, None]
                    }

            # HEAT AND POWER CONNECTIONS from Logic "fluids"
            if (pipe_cast.Kind - 1000) == logic_fluids:
                if (comp0 is not None and comp0.Kind is not None and comp0.Kind - 10000 in heat_components) or (comp1 is not None and comp1.Kind is not None and comp1.Kind - 10000 in heat_components):
                    connection_data.update({
                        'kind': "heat",
                        'energy_flow': convert_to_SI('heat', pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")) if hasattr(pipe_cast, 'Q') and pipe_cast.Q.Value is not None else None,
                        'energy_flow_unit': fluid_property_data['heat']['SI_unit'],
                        'E': None,
                        'E_unit': fluid_property_data['power']['SI_unit'],
                    })
                if (comp0 is not None and comp0.Kind is not None and comp0.Kind - 10000 in power_components):
                    connection_data.update({
                        'kind': "power",
                        'energy_flow': convert_to_SI('power', pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")) if hasattr(pipe_cast, 'Q') and pipe_cast.Q.Value is not None else None,
                        'energy_flow_unit': fluid_property_data['power']['SI_unit'],
                        'E': convert_to_SI('power', pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")) if hasattr(pipe_cast, 'Q') and pipe_cast.Q.Value is not None else None,
                        'E_unit': fluid_property_data['power']['SI_unit'],
                    })

            # POWER CONNECTIONS from power "fluids"
            if (pipe_cast.Kind - 1000) in power_fluids:
                connection_data.update({
                    'kind': "power",
                    'energy_flow': convert_to_SI('power', pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")) if hasattr(pipe_cast, 'Q') and pipe_cast.Q.Value is not None else None,
                    'energy_flow_unit': fluid_property_data['power']['SI_unit'],
                    'E': convert_to_SI('power', pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")) if hasattr(pipe_cast, 'Q') and pipe_cast.Q.Value is not None else None,
                    'E_unit': fluid_property_data['power']['SI_unit'],
                    })

            # Convert the connector numbers to selected standard values for each component
            if connection_data['source_component_type'] in connector_mapping and connection_data['source_connector'] in connector_mapping[connection_data['source_component_type']]:
                connection_data['source_connector'] = connector_mapping[connection_data['source_component_type']][connection_data['source_connector']]

            if connection_data['target_component_type'] in connector_mapping and connection_data['target_connector'] in connector_mapping[connection_data['target_component_type']]:
                connection_data['target_connector'] = connector_mapping[connection_data['target_component_type']][connection_data['target_connector']]

            # Store the connection data
            self.connections_data[obj.Name] = connection_data

        else:
            logging.info(f"Skipping non-energetic connection: {pipe_cast.Name}")


    def parse_component(self, obj):
        """
        Parses data from a component, including its type and various properties.

        Parameters:
            obj: The Ebsilon component object to parse.
        """
        # Cast the component to get its type index
        comp_cast = self.oc.CastToComp(obj)
        type_index = (comp_cast.Kind - 10000)

        # Dynamically call the specific CastToCompX method based on type_index
        cast_method_name = f"CastToComp{type_index}"

        # Check if the method exists and call it, otherwise fallback to general casting
        if hasattr(self.oc, cast_method_name):
            comp_cast = getattr(self.oc, cast_method_name)(obj)
            logging.info(f"Using method {cast_method_name} to cast the component.")
        else:
            logging.warning(f"No specific cast method for type_index {type_index}, using generic CastToComp.")
            comp_cast = self.oc.CastToComp(obj)

        # Get the human-readable type name of the component
        type_name = ebs_objects.get(type_index, f"Unknown Type {type_index}")

        # Exclude non-thermodynamic unit operators
        if type_index not in non_thermodynamic_unit_operators:
            # Collect component data
            component_data = {
                'name': comp_cast.Name,
                'type': type_name,
                'type_index': type_index,
                'eta_s': (
                    comp_cast.ETAIN.Value
                    if hasattr(comp_cast, 'ETAIN') and comp_cast.ETAIN.Value is not None else None
                ),
                'eta_mech': (
                    comp_cast.ETAMN.Value
                    if hasattr(comp_cast, 'ETAMN') and comp_cast.ETAMN.Value is not None else None
                ),
                'eta_el': (
                    comp_cast.ETAEN.Value
                    if hasattr(comp_cast, 'ETAEN') and comp_cast.ETAEN.Value is not None else None
                ),
                'eta_cc': (
                    comp_cast.ETAB.Value
                    if hasattr(comp_cast, 'ETAB') and comp_cast.ETAB.Value is not None else None
                ),
                'lamb': (
                    comp_cast.ALAMN.Value
                    if hasattr(comp_cast, 'ALAMN') and comp_cast.ALAMN.Value is not None else None
                ),
                'Q': (
                    convert_to_SI(
                        'heat',
                        comp_cast.QT.Value,
                        unit_id_to_string.get(comp_cast.QT.Dimension, "Unknown")
                    ) if hasattr(comp_cast, 'QT') and comp_cast.QT.Value is not None else None
                ),
                'Q_unit': fluid_property_data['heat']['SI_unit'],
                'P': (
                    convert_to_SI(
                        'power',
                        comp_cast.QSHAFT.Value,
                        unit_id_to_string.get(comp_cast.QSHAFT.Dimension, "Unknown")
                    ) if hasattr(comp_cast, 'QSHAFT') and comp_cast.QSHAFT.Value is not None else None
                ),
                'P_unit': fluid_property_data['power']['SI_unit'],
                'kA': (
                    comp_cast.KA.Value
                    if hasattr(comp_cast, 'KA') and comp_cast.KA.Value is not None else None
                ),
                'kA_unit': fluid_property_data['kA']['SI_unit'],
                'mass_flow_1': (
                    convert_to_SI(
                        'm',
                        comp_cast.M1N.Value,
                        unit_id_to_string.get(comp_cast.M1N.Dimension, "Unknown")
                    ) if hasattr(comp_cast, 'M1N') and comp_cast.M1N.Value is not None else None
                ),
                'mass_flow_1_unit': fluid_property_data['m']['SI_unit'],
                'mass_flow_3': (
                    convert_to_SI(
                        'm',
                        comp_cast.M3N.Value,
                        unit_id_to_string.get(comp_cast.M3N.Dimension, "Unknown")
                    ) if hasattr(comp_cast, 'M3N') and comp_cast.M3N.Value is not None else None
                ),
                'mass_flow_3_unit': fluid_property_data['m']['SI_unit'],
                'energy_flow_1': (
                    convert_to_SI(
                        'heat',
                        comp_cast.Q1N.Value,
                        unit_id_to_string.get(comp_cast.Q1N.Dimension, "Unknown")
                    ) if hasattr(comp_cast, 'Q1N') and comp_cast.Q1N.Value is not None else None
                ),
                'mass_flow_1_unit': fluid_property_data['heat']['SI_unit'],
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

        # For components of type 46, set ambient temperature and pressure
        elif type_index == 46:
            comp46 = self.oc.CastToComp46(obj)
            if comp46.FTYP.Value == 26:
                self.Tamb = convert_to_SI('T', comp46.MEASM.Value, unit_id_to_string.get(comp46.MEASM.Dimension, "Unknown"))
                logging.info(f"Set ambient temperature (Tamb) to {self.Tamb} K from component {comp_cast.Name}")
            elif comp46.FTYP.Value == 13:
                self.pamb = convert_to_SI('p', comp46.MEASM.Value, unit_id_to_string.get(comp46.MEASM.Dimension, "Unknown"))
                logging.info(f"Set ambient pressure (pamb) to {self.pamb} Pa from component {comp_cast.Name}")


    def get_sorted_data(self):
        """
        Sorts the component and connection data alphabetically by name.

        Returns:
            dict: A dictionary containing sorted 'components', 'connections', and ambient conditions data.
        """
        # Sort components within each group by component name
        sorted_components = {
            comp_type: dict(sorted(self.components_data[comp_type].items()))
            for comp_type in sorted(self.components_data)
        }
        # Sort connections by their names
        sorted_connections = dict(sorted(self.connections_data.items()))
        # Return data including ambient conditions
        return {
            'components': sorted_components,
            'connections': sorted_connections,
            'ambient_conditions': {
                'Tamb': self.Tamb,
                'Tamb_unit': fluid_property_data['T']['SI_unit'],
                'pamb': self.pamb,
                'pamb_unit': fluid_property_data['p']['SI_unit']
            }
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


def run_ebsilon(model_path, output_dir=None):
    """
    Main function to process the Ebsilon model and return parsed data.
    Optionally writes the parsed data to a JSON file.

    Parameters:
        model_path (str): Path to the Ebsilon model file.
        output_dir (str): Optional path where the parsed data should be saved as a JSON file.

    Returns:
        dict: Parsed data in dictionary format.

    Raises:
        FileNotFoundError: If the model file is not found at the specified path.
        RuntimeError: For any error during model initialization, simulation, parsing, or writing.
    """

    # Check if the model file exists at the specified path
    if not os.path.exists(model_path):
        error_msg = f"Model file not found at: {model_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Initialize the Ebsilon model parser with the model file path
    parser = EbsilonModelParser(model_path)

    try:
        # Initialize the Ebsilon model within the parser
        parser.initialize_model()
    except Exception as e:
        # Log and raise an error if something goes wrong during initialization
        error_msg = f"An error occurred during initializing: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        # Simulate the Ebsilon model
        parser.simulate_model()
    except Exception as e:
        # Log and raise an error if something goes wrong during simulation
        error_msg = f"An error occurred during model simulation: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        # Parse data from the simulated model
        parser.parse_model()
    except Exception as e:
        # Log and raise an error if something goes wrong during parsing
        error_msg = f"An error occurred during model parsing: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    # Get the parsed and sorted data
    parsed_data = parser.get_sorted_data()

    if output_dir is not None:
        try:
            # Write the parsed data to the JSON file
            parser.write_to_json(output_dir)
            logging.info(f"Data successfully written to {output_dir}")
        except Exception as e:
            # Log and raise an error if something goes wrong while writing the output file
            error_msg = f"An error occurred while writing the output file: {e}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    # Return the parsed data as a dictionary (not as a JSON string)
    return parsed_data
