"""
Ebsilon Model Parser

This module defines the EbsilonModelParser class, which is used to parse Ebsilon models,
simulate them, extract data about components and connections, and write the data to a JSON file.
"""

import json
import logging
import os
from typing import Any

from exerpy.functions import convert_to_SI, fluid_property_data

from . import __ebsilon_available__, is_ebsilon_available
from .ebsilon_functions import calc_eph_from_min
from .utils import EpCalculationResultStatus2Stub, EpFluidTypeStub, EpGasTableStub, EpSteamTableStub, require_ebsilon

# Import Ebsilon classes if available
if __ebsilon_available__:
    from EbsOpen import EpCalculationResultStatus2, EpFluidType, EpGasTable, EpSteamTable, EpThermoLiquidType
    from win32com.client import Dispatch
else:
    EpFluidType = EpFluidTypeStub
    EpSteamTable = EpSteamTableStub
    EpGasTable = EpGasTableStub
    EpCalculationResultStatus2 = EpCalculationResultStatus2Stub
    EpThermoLiquidType = None

from .ebsilon_config import (
    composition_params,
    connector_mapping,
    ebs_objects,
    fluid_type_index,
    grouped_components,
    non_thermodynamic_unit_operators,
    two_phase_fluids_mapping,
    unit_id_to_string,
)

# Configure logging to display info-level messages
logging.basicConfig(level=logging.ERROR)


def _thermoliquid_name(pipe_cast):
    """
    Return the specific thermal-liquid name of a pipe (e.g. "Therminol VP1").

    Ebsilon stores a thermal liquid as a type index rather than a name; this reads that
    index from the pipe's fluid data and maps it via the EpThermoLiquidType enum. Falls
    back to "ThermoLiquid" when the name cannot be determined.
    """
    try:
        type_index = pipe_cast.FluidData().ThermoliquidExtension.ThermoLiquidType
        name = EpThermoLiquidType(type_index).name.replace("epThermoLiquidType", "")
        return name.replace("_", " ").strip() or "ThermoLiquid"
    except Exception:
        return "ThermoLiquid"


class EbsilonModelParser:
    """
    A class to parse Ebsilon models, simulate them, extract data, and write to JSON.
    """

    def __init__(self, model_path: str, split_physical_exergy: bool = True):
        """
        Initializes the parser with the given model path.

        Parameters:
            model_path (str): Path to the Ebsilon model file.
            split_physical_exergy (bool): Flag to split physical exergy into thermal and mechanical components.

        Raises:
            RuntimeError: If Ebsilon is not available but is required for parsing.
        """
        # Check if Ebsilon is available
        if not is_ebsilon_available():
            logging.warning(
                "EbsilonModelParser initialized without Ebsilon support. "
                "EBS environment variable is not set or EbsOpen could not be imported; "
                "Ebsilon functionality will not be available."
            )
            # Raise an error since this parser specifically requires Ebsilon
            raise RuntimeError(
                "EbsilonModelParser requires Ebsilon to be available. "
                "Please set the EBS environment variable to your Ebsilon installation path."
            )

        self.model_path = model_path
        self.split_physical_exergy = split_physical_exergy
        self.app = None  # Ebsilon application instance
        self.model = None  # Opened Ebsilon model
        self.oc = None  # ObjectCaster for type casting
        self.components_data: dict[str, dict[str, dict[str, Any]]] = {}  # Dictionary to store component data
        self.connections_data: dict[str, dict[str, Any]] = {}  # Dictionary to store connection data
        self.Tamb: float | None = None  # Ambient temperature
        self.pamb: float | None = None  # Ambient pressure

        self._storages_to_postprocess: list[dict[str, Any]] = []
        self.heatflow_to_postprocess: list[dict[str, Any]] = []
        self._power_bus_mul_data: dict[str, dict[int, float]] = {}  # {comp_name: {connector_idx: MUL_value}}

    @require_ebsilon
    def initialize_model(self):
        """
        Initializes the Ebsilon application and opens the specified model.

        Raises:
            FileNotFoundError: If the model file cannot be opened.
            RuntimeError: If the COM server cannot be started or ObjectCaster cannot be obtained.
        """
        # 1) start the COM server
        try:
            self.app = Dispatch("EbsOpen.Application")
        except Exception as e:
            logging.error(f"Failed to start Ebsilon COM server: {e}")
            raise RuntimeError(f"Could not start Ebsilon COM server: {e}")

        # 2) try to open the .ebs model
        try:
            self.model = self.app.Open(self.model_path)
        except Exception as e:
            logging.error(f"Failed to open model file: {e}")
            raise FileNotFoundError(f"File not found at: {self.model_path}") from e

        # 3) grab the ObjectCaster
        try:
            self.oc = self.app.ObjectCaster
        except Exception as e:
            logging.error(f"Failed to obtain ObjectCaster: {e}")
            raise RuntimeError(f"Could not get ObjectCaster: {e}")

        logging.info(f"Model opened successfully: {self.model_path}")

    @require_ebsilon
    def simulate_model(self):
        """
        Simulates the Ebsilon model and logs any calculation errors.

        Raises:
            Exception: If model simulation fails.
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

    @require_ebsilon
    def parse_model(self):
        """
        Parses all objects in the Ebsilon model to extract component and connection data.

        Raises:
            ValueError: If ambient conditions are not set.
            Exception: If model parsing fails.
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

            # Reclassify Power Summarizer connections based on MUL signs
            self._reclassify_power_bus_connections()

            # After parsing all components and connections, create storage connections
            self._create_storage_connections()
            # Create synthetic heat connections for solar feat flow components (Heliostat / Parabolic Trough / Solar Tower)
            try:
                self._create_heatflow_connections()
            except Exception:
                logging.warning("_create_heatflow_connections failed; continuing without synthetic heat connections")

        except Exception as e:
            logging.error(f"Error while parsing the model: {e}")
            raise

    @require_ebsilon
    def parse_connection(self, obj: Any):
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
        logic_fluids = {13}  # Logic "fluids" for heat and power flows
        heat_components = {5, 15, 16, 35, 120, 121, 113}  # Components that handle with heat flows as input or output
        power_components = {31}  # Power-summerized with power flows ONLY as output

        # ALL EBSILON CONNECTIONS
        # Initialize connection data with the common fields
        connection_data = {
            "name": pipe_cast.Name,
            "kind": "other",  # it will be changed later ("material", "heat", "power") according to the fluid type
            "source_component": None,
            "source_component_type": None,
            "source_connector": None,
            "target_component": None,
            "target_component_type": None,
            "target_connector": None,
            "fluid_type": fluid_type_index.get(pipe_cast.FluidType, "Unknown"),
            "fluid_type_id": pipe_cast.FluidType,
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
            connection_data.update(
                {
                    "source_component": comp0.Name if comp0 else None,
                    "source_component_type": (comp0.Kind - 10000) if comp0 else None,
                    "source_connector": link0.Index if link0 else None,
                    "target_component": comp1.Name if comp1 else None,
                    "target_component_type": (comp1.Kind - 10000) if comp1 else None,
                    "target_connector": link1.Index if link1 else None,
                }
            )

            # MATERIAL CONNECTIONS
            if (pipe_cast.Kind - 1000) not in non_material_fluids:
                # Extract basic thermodynamic properties
                T_value = (
                    convert_to_SI("T", pipe_cast.T.Value, unit_id_to_string.get(pipe_cast.T.Dimension, "Unknown"))
                    if hasattr(pipe_cast, "T") and pipe_cast.T.Value is not None
                    else None
                )

                p_value = (
                    convert_to_SI("p", pipe_cast.P.Value, unit_id_to_string.get(pipe_cast.P.Dimension, "Unknown"))
                    if hasattr(pipe_cast, "P") and pipe_cast.P.Value is not None
                    else None
                )

                e_PH_value = (
                    convert_to_SI("e", pipe_cast.E.Value, unit_id_to_string.get(pipe_cast.E.Dimension, "Unknown"))
                    if hasattr(pipe_cast, "E") and pipe_cast.E.Value is not None
                    else None
                )

                # If e_PH is not available from Ebsilon, calculate using min-based formula
                if (
                    e_PH_value is None
                    and T_value is not None
                    and p_value is not None
                    and (
                        hasattr(pipe_cast, "H")
                        and pipe_cast.H.Value is not None
                        and hasattr(pipe_cast, "S")
                        and pipe_cast.S.Value is not None
                    )
                ):
                    try:
                        e_PH_value = calc_eph_from_min(pipe_cast, self.Tamb)
                        if e_PH_value is not None:
                            logging.info(
                                f"Physical exergy calculated using min-based formula for {pipe_cast.Name}: "
                                f"{e_PH_value:.2f} J/kg"
                            )
                    except ValueError as ve:
                        logging.error(f"Failed to calculate e_PH from min for {pipe_cast.Name}: {ve}")
                        e_PH_value = None

                connection_data.update(
                    {
                        "kind": "material",
                        "m": (
                            convert_to_SI(
                                "m", pipe_cast.M.Value, unit_id_to_string.get(pipe_cast.M.Dimension, "Unknown")
                            )
                            if hasattr(pipe_cast, "M") and pipe_cast.M.Value is not None
                            else None
                        ),
                        "m_unit": fluid_property_data["m"]["SI_unit"],
                        "T": T_value,
                        "T_unit": fluid_property_data["T"]["SI_unit"],
                        "p": p_value,
                        "p_unit": fluid_property_data["p"]["SI_unit"],
                        "h": (
                            convert_to_SI(
                                "h", pipe_cast.H.Value, unit_id_to_string.get(pipe_cast.H.Dimension, "Unknown")
                            )
                            if hasattr(pipe_cast, "H") and pipe_cast.H.Value is not None
                            else None
                        ),
                        "h_unit": fluid_property_data["h"]["SI_unit"],
                        "s": (
                            convert_to_SI(
                                "s", pipe_cast.S.Value, unit_id_to_string.get(pipe_cast.S.Dimension, "Unknown")
                            )
                            if hasattr(pipe_cast, "S") and pipe_cast.S.Value is not None
                            else None
                        ),
                        "s_unit": fluid_property_data["s"]["SI_unit"],
                        "e_PH": e_PH_value,
                        "e_PH_unit": fluid_property_data["e"]["SI_unit"],
                        "x": (
                            convert_to_SI(
                                "x", pipe_cast.X.Value, unit_id_to_string.get(pipe_cast.X.Dimension, "Unknown")
                            )
                            if hasattr(pipe_cast, "X") and pipe_cast.X.Value is not None
                            else None
                        ),
                        "x_unit": fluid_property_data["x"]["SI_unit"],
                        "VM": (
                            convert_to_SI(
                                "VM", pipe_cast.VM.Value, unit_id_to_string.get(pipe_cast.VM.Dimension, "Unknown")
                            )
                            if hasattr(pipe_cast, "VM") and pipe_cast.VM.Value is not None
                            else None
                        ),
                        "VM_unit": fluid_property_data["VM"]["SI_unit"],
                    }
                )

                # Add the mechanical and thermal specific exergies unless the flag is set to False
                if self.split_physical_exergy:
                    e_T_value = calc_eT(self.app, pipe_cast, connection_data["p"], self.Tamb, self.pamb)
                    e_M_value = calc_eM(self.app, pipe_cast, connection_data["p"], self.Tamb, self.pamb)

                    connection_data.update(
                        {
                            "e_T": e_T_value,
                            "e_T_unit": fluid_property_data["e"]["SI_unit"],
                            "e_M": e_M_value,
                            "e_M_unit": fluid_property_data["e"]["SI_unit"],
                        }
                    )

                # Handle mass composition logic for fluids
                if fluid_type_index.get(pipe_cast.FluidType, "Unknown") in ["Steam", "Water"]:
                    connection_data["mass_composition"] = {"H2O": 1}
                elif fluid_type_index.get(pipe_cast.FluidType, "Unknown") in ["2PhaseLiquid", "2PhaseGaseous"]:
                    # Get the FMED value to determine the substance
                    fmed_value = pipe_cast.FMED.Value if hasattr(pipe_cast, "FMED") else None
                    if fmed_value in two_phase_fluids_mapping:
                        connection_data["mass_composition"] = two_phase_fluids_mapping[fmed_value]
                    else:
                        connection_data["mass_composition"] = {}  # Default if no mapping found
                        logging.warning(
                            f"FMED value {fmed_value} not found in fluid_composition_mapping. Please add it."
                        )
                elif fluid_type_index.get(pipe_cast.FluidType, "Unknown") in ["ThermoLiquid"]:
                    # use the specific fluid name read from Ebsilon as the composition key.
                    # It may be a mixutre, but it is handled as a pure substance in ExerPy.
                    connection_data["mass_composition"] = {_thermoliquid_name(pipe_cast): 1}
                else:
                    connection_data["mass_composition"] = {
                        param.lstrip("X"): getattr(pipe_cast, param).Value
                        for param in composition_params
                        if hasattr(pipe_cast, param) and getattr(pipe_cast, param).Value not in [0, None]
                    }

            # HEAT AND POWER CONNECTIONS from Logic "fluids"
            if (pipe_cast.Kind - 1000) in logic_fluids:
                if (comp0 is not None and comp0.Kind is not None and comp0.Kind - 10000 in heat_components) or (
                    comp1 is not None and comp1.Kind is not None and comp1.Kind - 10000 in heat_components
                ):
                    connection_data.update(
                        {
                            "kind": "heat",
                            "energy_flow": (
                                convert_to_SI(
                                    "heat", pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")
                                )
                                if hasattr(pipe_cast, "Q") and pipe_cast.Q.Value is not None
                                else None
                            ),
                            "energy_flow_unit": fluid_property_data["heat"]["SI_unit"],
                            "E": None,
                            "E_unit": fluid_property_data["power"]["SI_unit"],
                        }
                    )
                if (comp0 is not None and comp0.Kind is not None and comp0.Kind - 10000 in power_components) or (
                    comp1 is not None and comp1.Kind is not None and comp1.Kind - 10000 in power_components
                ):
                    connection_data.update(
                        {
                            "kind": "power",
                            "energy_flow": (
                                convert_to_SI(
                                    "power", pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")
                                )
                                if hasattr(pipe_cast, "Q") and pipe_cast.Q.Value is not None
                                else None
                            ),
                            "energy_flow_unit": fluid_property_data["power"]["SI_unit"],
                            "E": (
                                convert_to_SI(
                                    "power", pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")
                                )
                                if hasattr(pipe_cast, "Q") and pipe_cast.Q.Value is not None
                                else None
                            ),
                            "E_unit": fluid_property_data["power"]["SI_unit"],
                        }
                    )

            # POWER CONNECTIONS from power "fluids"
            if (pipe_cast.Kind - 1000) in power_fluids:
                connection_data.update(
                    {
                        "kind": "power",
                        "energy_flow": (
                            convert_to_SI(
                                "power", pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")
                            )
                            if hasattr(pipe_cast, "Q") and pipe_cast.Q.Value is not None
                            else None
                        ),
                        "energy_flow_unit": fluid_property_data["power"]["SI_unit"],
                        "E": (
                            convert_to_SI(
                                "power", pipe_cast.Q.Value, unit_id_to_string.get(pipe_cast.Q.Dimension, "Unknown")
                            )
                            if hasattr(pipe_cast, "Q") and pipe_cast.Q.Value is not None
                            else None
                        ),
                        "E_unit": fluid_property_data["power"]["SI_unit"],
                    }
                )

            # Convert the connector numbers to selected standard values for each component
            if (
                connection_data["source_component_type"] in connector_mapping
                and connection_data["source_connector"] in connector_mapping[connection_data["source_component_type"]]
            ):
                connection_data["source_connector"] = connector_mapping[connection_data["source_component_type"]][
                    connection_data["source_connector"]
                ]

            if (
                connection_data["target_component_type"] in connector_mapping
                and connection_data["target_connector"] in connector_mapping[connection_data["target_component_type"]]
            ):
                connection_data["target_connector"] = connector_mapping[connection_data["target_component_type"]][
                    connection_data["target_connector"]
                ]

            # Store the connection data
            self.connections_data[obj.Name] = connection_data

        else:
            logging.info(f"Skipping non-energetic connection: {pipe_cast.Name}")

    @require_ebsilon
    def parse_component(self, obj: Any):
        """
        Parses data from a component, including its type and various properties.

        Parameters:
            obj: The Ebsilon component object to parse.
        """
        # Cast the component to get its type index
        comp_cast = self.oc.CastToComp(obj)
        type_index = comp_cast.Kind - 10000

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
                "name": comp_cast.Name,
                "type": type_name,
                "type_index": type_index,
                "eta_s": (
                    comp_cast.ETAIN.Value if hasattr(comp_cast, "ETAIN") and comp_cast.ETAIN.Value is not None else None
                ),
                "eta_mech": (
                    comp_cast.ETAMN.Value if hasattr(comp_cast, "ETAMN") and comp_cast.ETAMN.Value is not None else None
                ),
                "eta_el": (
                    comp_cast.ETAEN.Value if hasattr(comp_cast, "ETAEN") and comp_cast.ETAEN.Value is not None else None
                ),
                "eta_cc": (
                    comp_cast.ETAB.Value if hasattr(comp_cast, "ETAB") and comp_cast.ETAB.Value is not None else None
                ),
                "lamb": (
                    comp_cast.ALAMN.Value if hasattr(comp_cast, "ALAMN") and comp_cast.ALAMN.Value is not None else None
                ),
                "Q": (
                    convert_to_SI("heat", comp_cast.QT.Value, unit_id_to_string.get(comp_cast.QT.Dimension, "Unknown"))
                    if hasattr(comp_cast, "QT") and comp_cast.QT.Value is not None
                    else None
                ),
                "Q_unit": fluid_property_data["heat"]["SI_unit"],
                "P": (
                    convert_to_SI(
                        "power", comp_cast.QSHAFT.Value, unit_id_to_string.get(comp_cast.QSHAFT.Dimension, "Unknown")
                    )
                    if hasattr(comp_cast, "QSHAFT") and comp_cast.QSHAFT.Value is not None
                    else None
                ),
                "P_unit": fluid_property_data["power"]["SI_unit"],
                "kA": (comp_cast.KA.Value if hasattr(comp_cast, "KA") and comp_cast.KA.Value is not None else None),
                "kA_unit": fluid_property_data["kA"]["SI_unit"],
                "A": (comp_cast.A.Value if hasattr(comp_cast, "A") and comp_cast.A.Value is not None else None),
                "A_unit": fluid_property_data["A"]["SI_unit"],
                "mass_flow_1": (
                    convert_to_SI("m", comp_cast.M1N.Value, unit_id_to_string.get(comp_cast.M1N.Dimension, "Unknown"))
                    if hasattr(comp_cast, "M1N") and comp_cast.M1N.Value is not None
                    else None
                ),
                "mass_flow_1_unit": fluid_property_data["m"]["SI_unit"],
                "mass_flow_3": (
                    convert_to_SI("m", comp_cast.M3N.Value, unit_id_to_string.get(comp_cast.M3N.Dimension, "Unknown"))
                    if hasattr(comp_cast, "M3N") and comp_cast.M3N.Value is not None
                    else None
                ),
                "mass_flow_3_unit": fluid_property_data["m"]["SI_unit"],
                "energy_flow_1": (
                    convert_to_SI(
                        "heat", comp_cast.Q1N.Value, unit_id_to_string.get(comp_cast.Q1N.Dimension, "Unknown")
                    )
                    if hasattr(comp_cast, "Q1N") and comp_cast.Q1N.Value is not None
                    else None
                ),
                "energy_flow_1_unit": fluid_property_data["heat"]["SI_unit"],
                "Q_Solar": (
                    convert_to_SI(
                        "heat", comp_cast.QSOLAR.Value, unit_id_to_string.get(comp_cast.QSOLAR.Dimension, "Unknown")
                    )
                    if hasattr(comp_cast, "QSOLAR") and comp_cast.QSOLAR.Value is not None
                    else None
                ),
                "QEFF": (
                    convert_to_SI(
                        "heat", comp_cast.QEFF.Value, unit_id_to_string.get(comp_cast.QEFF.Dimension, "Unknown")
                    )
                    if hasattr(comp_cast, "QEFF") and comp_cast.QEFF.Value is not None
                    else None
                ),
                "RQINC": (
                    convert_to_SI(
                        "heat", comp_cast.RQINC.Value, unit_id_to_string.get(comp_cast.RQINC.Dimension, "Unknown")
                    )
                    if hasattr(comp_cast, "RQINC") and comp_cast.RQINC.Value is not None
                    else None
                ),
                # Number of parallel branches a header/collector stands for (from Ebsilon
                # NBRANCH, rounded RNBRANCH as fallback); stored under a parser-agnostic name.
                "num_branches": (
                    comp_cast.NBRANCH.Value
                    if hasattr(comp_cast, "NBRANCH")
                    and hasattr(comp_cast.NBRANCH, "Value")
                    and comp_cast.NBRANCH.Value is not None
                    else (
                        comp_cast.RNBRANCH.Value
                        if hasattr(comp_cast, "RNBRANCH")
                        and hasattr(comp_cast.RNBRANCH, "Value")
                        and comp_cast.RNBRANCH.Value is not None
                        else None
                    )
                ),
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
                self.Tamb = convert_to_SI(
                    "T", comp46.MEASM.Value, unit_id_to_string.get(comp46.MEASM.Dimension, "Unknown")
                )
                logging.info(f"Set ambient temperature (Tamb) to {self.Tamb} K from component {comp_cast.Name}")
            elif comp46.FTYP.Value == 13:
                self.pamb = convert_to_SI(
                    "p", comp46.MEASM.Value, unit_id_to_string.get(comp46.MEASM.Dimension, "Unknown")
                )
                logging.info(f"Set ambient pressure (pamb) to {self.pamb} Pa from component {comp_cast.Name}")

        if type_index == 31:
            comp31 = self.oc.CastToComp31(obj)
            mul_signs = {}
            for i in range(1, 11):
                mul_attr = f"MUL{i}"
                if hasattr(comp31, mul_attr):
                    mul_value = getattr(comp31, mul_attr).Value
                    mul_signs[connector_mapping[31][i]] = mul_value
            self._power_bus_mul_data[comp31.Name] = mul_signs
            # Also store in component_data so it persists to JSON
            if "PowerBus" in self.components_data and comp31.Name in self.components_data["PowerBus"]:
                self.components_data["PowerBus"][comp31.Name]["mul_signs"] = mul_signs

        if type_index == 118:
            storage = self.oc.CastToComp118(obj)
            self._storages_to_postprocess.append(
                {
                    "name": storage.Name,
                    "kind": storage.Kind,
                    "m_flow_load": storage.MLD.Value,
                    "m_flow_load_unit": unit_id_to_string.get(storage.MLD.Dimension, "Unknown"),
                    "m_flow_unload": storage.MUNLD.Value,
                    "m_flow_unload_unit": unit_id_to_string.get(storage.MUNLD.Dimension, "Unknown"),
                    "T_storage": storage.TNEW.Value,
                    "T_storage_unit": unit_id_to_string.get(storage.TNEW.Dimension, "Unknown"),
                    "p_storage": storage.PNEW.Value,
                    "p_storage_unit": unit_id_to_string.get(storage.PNEW.Dimension, "Unknown"),
                    "h_storage": storage.HNEW.Value,
                    "h_storage_unit": unit_id_to_string.get(storage.HNEW.Dimension, "Unknown"),
                }
            )

        # Handle heliostat field (121) and parabolic trough (113) for solar feat flow extraction
        if type_index in (121, 113):
            heatflow = None
            try:
                if type_index == 121:
                    heatflow = self.oc.CastToComp121(obj)
                elif type_index == 113:
                    heatflow = self.oc.CastToComp113(obj)
            except Exception as e:
                logging.warning(f"Failed to cast component to type {type_index}: {e}")
                heatflow = None

            # Append only when cast succeeded and QSOLAR is available
            if (
                heatflow is not None
                and hasattr(heatflow, "QSOLAR")
                and heatflow.QSOLAR is not None
                and getattr(heatflow.QSOLAR, "Value", None) is not None
            ):
                q_solar_val = convert_to_SI(
                    "heat",
                    heatflow.QSOLAR.Value,
                    unit_id_to_string.get(heatflow.QSOLAR.Dimension, "Unknown"),
                )
                q_solar_unit = fluid_property_data["heat"]["SI_unit"]

                self.heatflow_to_postprocess.append(
                    {
                        "name": heatflow.Name,
                        "kind": heatflow.Kind,
                        "Q_Solar": q_solar_val,
                        "Q_Solar_unit": q_solar_unit,
                    }
                )

    def _create_storage_connections(self):
        """
        Create fictive charging/discharging connections for storage components.

        After all real connections are parsed, uses stored storage parameters
        and existing connections_data to generate and insert material connections.

        Returns
        -------
        None
        """
        for raw in self._storages_to_postprocess:
            name = raw["name"]
            m_load = raw["m_flow_load"]
            m_unload = raw["m_flow_unload"]
            sign = "charging" if m_load >= m_unload else "discharging"
            delta_m = abs(m_load - m_unload)
            prefix = f"{name}_{sign}"
            new_conn = {
                "name": prefix,
                "kind": "material",
                "source_component": name if sign == "charging" else None,
                "target_component": name if sign == "discharging" else None,
                "source_component_type": (raw["kind"] - 10000) if sign == "charging" else None,
                "target_component_type": (raw["kind"] - 10000) if sign == "discharging" else None,
                "source_connector": None,
                "target_connector": None,
                "m": convert_to_SI("m", delta_m, raw["m_flow_load_unit"]),
                "m_unit": fluid_property_data["m"]["SI_unit"],
                "T": convert_to_SI("T", raw["T_storage"], raw["T_storage_unit"]),
                "T_unit": fluid_property_data["T"]["SI_unit"],
                "p": convert_to_SI("p", raw["p_storage"], raw["p_storage_unit"]),
                "p_unit": fluid_property_data["p"]["SI_unit"],
                "h": convert_to_SI("h", raw["h_storage"], raw["h_storage_unit"]),
                "h_unit": fluid_property_data["h"]["SI_unit"],
                "s": next(
                    (
                        c["s"]
                        for c in self.connections_data.values()
                        if c.get("source_component") == name and c.get("source_connector") == connector_mapping[118][2]
                    ),
                    None,
                ),
                "s_unit": fluid_property_data["s"]["SI_unit"],
                "e_PH": next(
                    (
                        c["e_PH"]
                        for c in self.connections_data.values()
                        if c.get("source_component") == name and c.get("source_connector") == connector_mapping[118][2]
                    ),
                    None,
                ),
                "e_PH_unit": fluid_property_data["e"]["SI_unit"],
                "mass_composition": next(
                    (
                        c["mass_composition"]
                        for c in self.connections_data.values()
                        if c.get("source_component") == name and c.get("source_connector") == connector_mapping[118][2]
                    ),
                    None,
                ),
            }
            self.connections_data[prefix] = new_conn

    def _create_heatflow_connections(self):
        """
        Create fictive heat flow connections for solar feat flow components
        (Heliostat Field, Parabolic Trough, Solar Tower).

        After all real connections are parsed, uses stored feat flow parameters
        and existing connections_data to generate and insert heat connections.

        For parabolic trough (type_index 113), retrieves num_branches from the connected
        distributing/collecting node (type 114 or 115).

        Returns
        -------
        None
        """
        for raw in self.heatflow_to_postprocess:
            name = raw.get("name")
            q_raw = raw.get("Q_Solar")
            q_unit = raw.get("Q_Solar_unit")
            kind = raw.get("kind")
            type_index = kind - 10000 if kind is not None else None
            # Name the synthetic solar heat connection after its component with a "_Q"
            # suffix (e.g. component "Collector" -> connection "Collector_Q"), so the heat
            # input is clearly distinguishable from the component itself.
            prefix = f"{name}_Q"

            # Retrieve num_branches from the connected node (114/115) for parabolic trough (113)
            nbranch = None
            if type_index == 113:
                # Find connections that have this parabolic trough as source or target
                for conn_name, conn_data in self.connections_data.items():
                    if conn_data.get("source_component") == name or conn_data.get("target_component") == name:
                        # Find the connected component (header)
                        connected_comp = (
                            conn_data.get("target_component")
                            if conn_data.get("source_component") == name
                            else conn_data.get("source_component")
                        )
                        connected_type = (
                            conn_data.get("target_component_type")
                            if conn_data.get("source_component") == name
                            else conn_data.get("source_component_type")
                        )

                        # Check if the connected component is a header (114 or 115)
                        if connected_type in (114, 115):
                            for group in self.components_data.values():
                                comp = group.get(connected_comp)
                                if comp and comp.get("num_branches") is not None:
                                    nbranch = comp["num_branches"]
                                    break
                            if nbranch is not None:
                                break

            # Try to convert provided Q_Solar to SI; fall back to the raw value on failure.
            energy_flow = None
            if q_raw is not None:
                try:
                    energy_flow = convert_to_SI("heat", q_raw, q_unit)
                    # For parabolic trough (type_index 113), multiply by num_branches if available
                    if type_index == 113 and nbranch is not None:
                        energy_flow = energy_flow * nbranch
                except Exception as e:
                    logging.warning(f"Exception during energy_flow calculation for '{name}': {e}")
                    energy_flow = q_raw

            # Compute exergy for concentrated solar heat if ambient temperature is known
            # alpha = 1 - (4/3 * Tamb / Tsun)  (Petela / Ahrendts)
            computed_exergy = None
            if energy_flow is not None and self.Tamb is not None:
                T_SUN = 5778  # Sun's surface temperature in K
                alpha = 1.0 - (4.0 / 3.0) * (self.Tamb / T_SUN)
                computed_exergy = energy_flow * alpha

            new_conn = {
                "name": prefix,
                "kind": "heat",
                "source_component": name,
                "target_component": None,
                "source_component_type": type_index,
                "target_component_type": None,
                "source_connector": None,
                "target_connector": None,
                "energy_flow": energy_flow,
                "energy_flow_unit": fluid_property_data["heat"]["SI_unit"],
                "E": computed_exergy,
                "E_unit": fluid_property_data["power"]["SI_unit"],
                "num_branches": nbranch,
            }
            self.connections_data[prefix] = new_conn

            # For parabolic trough (type_index 113), also update component data with num_branches
            if type_index == 113 and nbranch is not None:
                for group in self.components_data.values():
                    if name in group:
                        group[name]["num_branches"] = nbranch
                        break

    def _reclassify_power_bus_connections(self):
        """
        Link Power Summarizer (type 31) logic connections to their corresponding
        power connections (Electric/Shaft) by matching energy_flow values.

        In Ebsilon, power flows (Electric/Shaft) are connected to the Power Summarizer
        via intermediate Logic connections that carry the same energy_flow value.
        All 10 Logic connections target the PowerBus regardless of MUL sign.
        The MUL sign determines the linking direction:
        - MUL >= 0 (inlet): the power connection's free target is linked to POWER
        - MUL < 0 (outlet): the power connection's free source is linked to POWER

        This method:
        1. Finds Logic connections targeting type 31 components
        2. Uses MUL signs to determine if the connection is an inlet or outlet
        3. Matches them to power connections (Electric/Shaft) with equal energy_flow
        4. Updates the power connection to point to/from the PowerBus directly
        5. Removes the now-redundant Logic connection

        Logic connections with no matching power connection (e.g. the net output ETOT)
        are left unchanged.
        """
        logic_conns_to_remove = []

        for conn_name, conn_data in list(self.connections_data.items()):
            # Only process Logic fluid connections connected to type 31
            if conn_data.get("fluid_type_id") != 13:
                continue

            # Handle logic connections targeting POWER (all 10 inputs in Ebsilon)
            if conn_data.get("target_component_type") == 31:
                comp_name = conn_data["target_component"]
                connector_idx = conn_data["target_connector"]

                logic_energy = conn_data.get("energy_flow")
                if logic_energy is None:
                    continue

                # Determine direction from MUL sign
                mul_value = self._power_bus_mul_data.get(comp_name, {}).get(connector_idx, 1.0)
                is_power_inlet = mul_value >= 0  # positive MUL = power flows into POWER

                # Find matching power connection (Electric/Shaft) by energy_flow
                matched_power_name = None
                for power_name, power_data in self.connections_data.items():
                    if power_name == conn_name:
                        continue
                    if power_data.get("fluid_type_id") not in {9, 10}:  # Electric, Shaft
                        continue
                    power_energy = power_data.get("energy_flow")
                    if power_energy is None:
                        continue
                    if abs(power_energy - logic_energy) < 1e-6 and (
                        is_power_inlet
                        and power_data.get("target_component") is None
                        or not is_power_inlet
                        and power_data.get("source_component") is None
                    ):
                        matched_power_name = power_name
                        break

                if matched_power_name is None:
                    continue

                matched_power_data = self.connections_data[matched_power_name]

                if is_power_inlet:
                    # Positive MUL: power flows into POWER → link power target to POWER
                    matched_power_data["target_component"] = comp_name
                    matched_power_data["target_component_type"] = 31
                    matched_power_data["target_connector"] = connector_idx
                    logging.info(
                        f"Linked power connection {matched_power_name} to PowerBus "
                        f"{comp_name} (inlet, connector {connector_idx})"
                    )
                else:
                    # Negative MUL: power flows out of POWER → link power source to POWER
                    matched_power_data["source_component"] = comp_name
                    matched_power_data["source_component_type"] = 31
                    matched_power_data["source_connector"] = connector_idx
                    logging.info(
                        f"Linked power connection {matched_power_name} to PowerBus "
                        f"{comp_name} (outlet, connector {connector_idx})"
                    )

                logic_conns_to_remove.append(conn_name)

            # Handle logic connections sourced from POWER (e.g. already-directed outlets)
            elif conn_data.get("source_component_type") == 31:
                comp_name = conn_data["source_component"]
                connector_idx = conn_data["source_connector"]

                logic_energy = conn_data.get("energy_flow")
                if logic_energy is None:
                    continue

                # Find matching power connection with free source
                matched_power_name = None
                for power_name, power_data in self.connections_data.items():
                    if power_name == conn_name:
                        continue
                    if power_data.get("fluid_type_id") not in {9, 10}:
                        continue
                    power_energy = power_data.get("energy_flow")
                    if power_energy is None:
                        continue
                    if abs(power_energy - logic_energy) < 1e-6 and power_data.get("source_component") is None:
                        matched_power_name = power_name
                        break

                if matched_power_name is None:
                    continue

                matched_power_data = self.connections_data[matched_power_name]
                matched_power_data["source_component"] = comp_name
                matched_power_data["source_component_type"] = 31
                matched_power_data["source_connector"] = connector_idx
                logging.info(
                    f"Linked power connection {matched_power_name} to PowerBus "
                    f"{comp_name} (outlet, connector {connector_idx})"
                )
                logic_conns_to_remove.append(conn_name)

        # Remove the matched Logic connections
        for name in logic_conns_to_remove:
            del self.connections_data[name]
            logging.info(f"Removed redundant Logic connection: {name}")

    def get_sorted_data(self) -> dict[str, Any]:
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
            "components": sorted_components,
            "connections": sorted_connections,
            "ambient_conditions": {
                "Tamb": self.Tamb,
                "Tamb_unit": fluid_property_data["T"]["SI_unit"],
                "pamb": self.pamb,
                "pamb_unit": fluid_property_data["p"]["SI_unit"],
            },
        }

    def write_to_json(self, output_path: str):
        """
        Writes the parsed and sorted data to a JSON file.

        Parameters:
            output_path (str): Path where the JSON file will be saved.

        Raises:
            Exception: If writing to JSON fails.
        """
        data = self.get_sorted_data()
        try:
            # Write the data to a JSON file with indentation for readability
            with open(output_path, "w") as json_file:
                json.dump(data, json_file, indent=4)
            logging.info(f"Data successfully written to {output_path}")
        except Exception as e:
            logging.error(f"Failed to write data to JSON: {e}")
            raise


def run_ebsilon(model_path: str, output_dir: str | None = None, split_physical_exergy: bool = True) -> dict[str, Any]:
    """
    Main function to process the Ebsilon model and return parsed data.
    Optionally writes the parsed data to a JSON file.

    Parameters:
        model_path (str): Path to the Ebsilon model file.
        output_dir (str): Optional path where the parsed data should be saved as a JSON file.
        split_physical_exergy (bool): Flag to split physical exergy into thermal and mechanical components.

    Returns:
        dict: Parsed data in dictionary format.

    Raises:
        FileNotFoundError: If the model file is not found at the specified path.
        RuntimeError: For any error during model initialization, simulation, parsing, or writing.
    """
    # Check if Ebsilon is available
    if not is_ebsilon_available():
        raise RuntimeError(
            "Ebsilon functionality is required for running this function. "
            "Please set the EBS environment variable to your Ebsilon installation path."
        )

    # Check if the model file exists at the specified path
    if not os.path.exists(model_path):
        error_msg = f"Model file not found at: {model_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Initialize the Ebsilon model parser with the model file path
    try:
        parser = EbsilonModelParser(model_path, split_physical_exergy=split_physical_exergy)
    except RuntimeError as e:
        # This will catch the RuntimeError raised in __init__ if Ebsilon is not available
        logging.error(f"Failed to initialize EbsilonModelParser: {e}")
        raise

    try:
        # Initialize the Ebsilon model within the parser
        parser.initialize_model()
    except FileNotFoundError:
        # allow an invalid/corrupt‐model file to bubble up as FileNotFoundError
        raise
    except Exception:
        # other COM/server errors should still be RuntimeErrors
        error_msg = f"File not found: {model_path}"
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
