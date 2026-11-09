import itertools
import json
import math
import os

from exerpy.logger import logger
from exerpy.parser import STATE_CHECK_STEP
from exerpy.parser import state_between
from exerpy.units import SI_UNITS
from exerpy.units import add_units
from exerpy.units import convert
from exerpy.units import convert_to_SI

from .aspen_config import connector_mappings
from .aspen_config import grouped_components


class AspenModelParser:
    """
    A class to parse Aspen Plus models, simulate them, extract data, and write to JSON.
    """

    def __init__(self, model_path, split_physical_exergy=True, Tamb=None, pamb=None):
        """
        Initializes the parser with the given model path.

        Parameters:
            model_path (str): Path to the Aspen Plus model file.
            split_physical_exergy (bool): Flag to split physical exergy into thermal and mechanical components.
            Tamb (float): Ambient temperature in K. Replaces REF_TEMP of the model, see
                :meth:`set_ambient_conditions`.
            pamb (float): Ambient pressure in Pa. Replaces REF_PRES of the model.
        """
        self.model_path = model_path
        self.split_physical_exergy = split_physical_exergy
        self.Tamb = Tamb
        self.pamb = pamb
        self.aspen = None  # Aspen Plus application instance
        self.components_data = {}  # Dictionary to store component data
        self.connections_data = {}  # Dictionary to store connection data

        # Dictionary to map component types to specific connector assignment functions
        self.connector_assignment_functions = {
            "Mixer": self.assign_mixer_connectors,
            "RStoic": self.assign_combustion_chamber_connectors,
            "FSplit": self.assign_splitter_connectors,
            "Turbine": self.assign_turbine_connectors,
        }

    def initialize_model(self):
        """
        Initializes the Aspen Plus application and opens the specified model.
        """
        from win32com.client import Dispatch

        try:
            # Start Aspen Plus application via COM Dispatch
            self.aspen = Dispatch("Apwn.Document")
            # Load the Aspen model file
            self.aspen.InitFromArchive2(self.model_path)
            logger.info(f"Model opened successfully: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to initialize the model: {e}")
            raise

    def parse_model(self):
        """
        Parses the components and connections from the Aspen model.
        """
        try:
            self.set_ambient_conditions()

            # Parse Tamb and pamb
            self.parse_ambient_conditions()

            # Parse streams (connections)
            self.parse_streams()

            # Parse blocks (components)
            self.parse_blocks()

            if self.split_physical_exergy:
                self.split_physical_exergy_of_streams()

        except Exception as e:
            logger.error(f"Error while parsing the model: {e}")
            raise

    def parse_streams(self):
        """
        Parses the streams (connections) in the Aspen model.
        """
        # Get the stream nodes and their names
        stream_nodes = self.aspen.Tree.FindNode(r"\Data\Streams").Elements
        stream_names = [stream_node.Name for stream_node in stream_nodes]

        # ALL ASPEN CONNECTIONS
        # Initialize connection data with the common fields
        for stream_name in stream_names:
            self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}")
            connection_data = {
                "name": stream_name,
                "kind": None,
                "source_component": None,
                "source_connector": None,
                "target_component": None,
                "target_connector": None,
            }

            # Find the source and target components
            source_port_node = self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Ports\SOURCE")
            if source_port_node is not None and source_port_node.Elements.Count > 0:
                connection_data["source_component"] = source_port_node.Elements(0).Name

            destination_port_node = self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Ports\DEST")
            if destination_port_node is not None and destination_port_node.Elements.Count > 0:
                connection_data["target_component"] = destination_port_node.Elements(0).Name

            # HEAT AND POWER STREAMS
            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Input\WORK") is not None:
                connection_data["kind"] = "power"
                power_node = self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\POWER_OUT")
                if power_node is not None:
                    raw_power = power_node.Value
                    connection_data["energy_flow"] = convert_to_SI("energy_flow", abs(raw_power), power_node.UnitString)
                    # Store the sign of the raw Aspen value for direction determination
                    # in custom connector assignment functions (e.g., Turbine)
                    connection_data["_aspen_power_sign"] = 1 if raw_power >= 0 else -1
                else:
                    connection_data["energy_flow"] = None
            elif self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Input\HEAT") is not None:
                connection_data["kind"] = "heat"
                connection_data["energy_flow"] = (
                    convert_to_SI(
                        "energy_flow",
                        abs(self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\QCALC").Value),
                        self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\QCALC").UnitString,
                    )
                    if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\QCALC") is not None
                    else None
                )

            # MATERIAL STREAMS
            else:
                # Assume it's a material stream and retrieve additional properties
                connection_data.update(
                    {
                        "kind": "material",
                        "T": (
                            convert_to_SI(
                                "T",
                                self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\TEMP_OUT\MIXED").Value,
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\TEMP_OUT\MIXED"
                                ).UnitString,
                            )
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\TEMP_OUT\MIXED")
                            is not None
                            else None
                        ),
                        "T_unit": SI_UNITS["T"],
                        "p": (
                            convert_to_SI(
                                "p",
                                self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\PRES_OUT\MIXED").Value,
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\PRES_OUT\MIXED"
                                ).UnitString,
                            )
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\PRES_OUT\MIXED")
                            is not None
                            else None
                        ),
                        "p_unit": SI_UNITS["p"],
                        "h": (
                            convert_to_SI(
                                "h",
                                self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\HMX_MASS\MIXED").Value,
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\HMX_MASS\MIXED"
                                ).UnitString,
                            )
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\HMX_MASS\MIXED")
                            is not None
                            else None
                        ),
                        "h_unit": SI_UNITS["h"],
                        "s": (
                            convert_to_SI(
                                "s",
                                self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\SMX_MASS\MIXED").Value,
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\SMX_MASS\MIXED"
                                ).UnitString,
                            )
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\SMX_MASS\MIXED")
                            is not None
                            else None
                        ),
                        "s_unit": SI_UNITS["s"],
                        "m": (
                            convert_to_SI(
                                "m",
                                self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\MASSFLMX\MIXED").Value,
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\MASSFLMX\MIXED"
                                ).UnitString,
                            )
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\MASSFLMX\MIXED")
                            is not None
                            else None
                        ),
                        "m_unit": SI_UNITS["m"],
                        "v": (
                            convert_to_SI(
                                "v",
                                self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\VOLFLMX\MIXED").Value,
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\VOLFLMX\MIXED"
                                ).UnitString,
                            )
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\VOLFLMX\MIXED")
                            is not None
                            else None
                        ),
                        "v_unit": SI_UNITS["v"],
                        # Vapour mass fraction; Aspen states it for mixtures as well.
                        "x": (
                            self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\MASSVFRA").Value
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\MASSVFRA") is not None
                            else None
                        ),
                        "x_unit": SI_UNITS["x"],
                        "energy_flow": (
                            convert_to_SI(
                                "energy_flow",
                                abs(
                                    self.aspen.Tree.FindNode(
                                        rf"\Data\Streams\{stream_name}\Output\HMX_FLOW\MIXED"
                                    ).Value
                                ),
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\HMX_FLOW\MIXED"
                                ).UnitString,
                            )
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\HMX_FLOW\MIXED")
                            is not None
                            else None
                        ),
                        "energy_flow_unit": SI_UNITS["energy_flow"],
                        "e_PH": (
                            convert_to_SI(
                                "e_PH",
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\STRM_UPP\EXERGYMS\MIXED\TOTAL"
                                ).Value,
                                self.aspen.Tree.FindNode(
                                    rf"\Data\Streams\{stream_name}\Output\STRM_UPP\EXERGYMS\MIXED\TOTAL"
                                ).UnitString,
                            )
                            if self.aspen.Tree.FindNode(
                                rf"\Data\Streams\{stream_name}\Output\STRM_UPP\EXERGYMS\MIXED\TOTAL"
                            )
                            is not None
                            else (logger.warning(f"e_PH node not found for stream {stream_name}"), None)[1]
                        ),
                        "e_PH_unit": SI_UNITS["e_PH"],
                        "n": (
                            convert_to_SI(
                                "n",
                                self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\TOT_FLOW").Value,
                                self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\TOT_FLOW").UnitString,
                            )
                            if self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\TOT_FLOW") is not None
                            else None
                        ),
                        "n_unit": SI_UNITS["n"],
                        "mass_composition": {},
                        "molar_composition": {},
                    }
                )
                # Retrieve the fluid names for the stream
                mole_frac_node = self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\MOLEFRAC\MIXED")
                if mole_frac_node is not None:
                    fluid_names = [fluid.Name for fluid in mole_frac_node.Elements]

                    # Retrieve the molar composition for each fluid
                    for fluid_name in fluid_names:
                        mole_frac = self.aspen.Tree.FindNode(
                            rf"\Data\Streams\{stream_name}\Output\MOLEFRAC\MIXED\{fluid_name}"
                        ).Value
                        if mole_frac not in [0, None]:  # Skip fluids with 0 or None as the fraction
                            connection_data["molar_composition"][fluid_name] = mole_frac

                mass_frac_node = self.aspen.Tree.FindNode(rf"\Data\Streams\{stream_name}\Output\MASSFRAC\MIXED")
                if mass_frac_node is not None:
                    # Retrieve the mass composition for each fluid
                    for fluid_name in [fluid.Name for fluid in mass_frac_node.Elements]:
                        mass_frac = self.aspen.Tree.FindNode(
                            rf"\Data\Streams\{stream_name}\Output\MASSFRAC\MIXED\{fluid_name}"
                        ).Value
                        if mass_frac not in [0, None]:  # Skip fluids with 0 or None as the fraction
                            connection_data["mass_composition"][fluid_name] = mass_frac

            # Store connection data
            self.connections_data[stream_name] = connection_data

    def split_physical_exergy_of_streams(self):
        """
        Splits the physical exergy of the material streams into a thermal part e_T and a mechanical part e_M.

        A Generic property analysis per stream flashes the stream's composition with the stream's property method
        at the ambient temperature T0 and the stream's pressure p. Then e_T = h - h(T0, p) - T0 * (s - s(T0, p))
        and e_M = e_PH - e_T. The analysis also evaluates the stream just below and above its own temperature, to
        check that these properties reproduce the stream's h and s. The analyses exist in memory only and take one
        run of the Aspen engine; the model file stays unchanged.
        """
        streams = [name for name, conn in self.connections_data.items() if conn["kind"] == "material"]
        if not streams:
            return
        try:
            analyses = self.add_ambient_temperature_analyses(streams)
            self.aspen.SuppressDialogs = 1
            self.aspen.Engine.Run2()
        except Exception as e:
            logger.warning(f"The physical exergy of the streams could not be split: {e}")
            return

        for stream, (analysis, rows) in analyses.items():
            conn = self.connections_data[stream]
            (T_A, h_A, s_A), *own_state = self.analysis_states(analysis, stream, rows)
            if None in (conn["h"], conn["s"], h_A, s_A):
                logger.warning(f"No thermal and mechanical exergy for stream {stream}.")
                continue
            if T_A is not None and abs(T_A - self.Tamb) > 1e-3:
                logger.warning(f"Aspen evaluated stream {stream} at {T_A} K instead of Tamb = {self.Tamb} K.")
                continue
            if own_state and not state_between(conn["h"], conn["s"], *(state[1:] for state in own_state)):
                logger.warning(
                    f"The thermal and mechanical exergy of stream {stream} may be wrong: the property data used for "
                    f"the split do not reproduce the stream's enthalpy and entropy."
                )
            conn["e_T"] = conn["h"] - h_A - self.Tamb * (conn["s"] - s_A)
            conn["e_T_unit"] = SI_UNITS["e_T"]
            if conn["e_PH"] is not None:
                conn["e_M"] = conn["e_PH"] - conn["e_T"]
                conn["e_M_unit"] = SI_UNITS["e_M"]

    def add_ambient_temperature_analyses(self, streams):
        """
        Adds a prop-set with h and s and, for each stream, a Generic analysis at the stream's pressure and at T0
        and the stream's temperature minus and plus :data:`exerpy.parser.STATE_CHECK_STEP`.

        Returns:
            dict: Name of the analysis and its number of temperatures for each stream.
        """
        tree = self.aspen.Tree
        prop_sets = tree.FindNode(r"\Data\Properties\Prop-Sets")
        prop_set = self.free_names(prop_sets, "EXPYHS", 1)[0]
        prop_sets.Elements.Add(prop_set)
        units = tree.FindNode(rf"\Data\Properties\Prop-Sets\{prop_set}\Input\UNITS")
        for i, prop in enumerate(("HMX", "SMX")):
            units.Elements.InsertRow(0, i)
            units.Elements.SetLabel(0, i, False, prop)
        self.set_rows(rf"\Data\Properties\Prop-Sets\{prop_set}\Input\PHASE", ["T"])

        folder = tree.FindNode(r"\Data\Properties\Analysis")
        ref_temp = tree.FindNode(r"\Data\Setup\Sim-Options\Input\REF_TEMP")
        analyses = {}
        for stream, name in zip(streams, self.free_names(folder, "EXPY", len(streams)), strict=True):
            folder.Elements.Add(f"{name}!GENERIC")
            base = rf"\Data\Properties\Analysis\{name}\Input"
            tree.FindNode(base + r"\OPT_COMP").Value = "STREAM"
            tree.FindNode(base + r"\SID").Value = stream
            self.set_rows(base + r"\VARNAME", ["TEMP"])
            # the temperature list takes the input unit of REF_TEMP; the results are checked against Tamb
            temperatures = [ref_temp.Value]
            T = self.connections_data[stream]["T"]
            if T is not None:
                temperatures += [
                    convert(T + step, SI_UNITS["T"], ref_temp.UnitString)
                    for step in (-STATE_CHECK_STEP, STATE_CHECK_STEP)
                ]
            self.set_rows(base + r"\LIST\#0", temperatures)
            pres = tree.FindNode(base + r"\PRES")
            p_out = tree.FindNode(rf"\Data\Streams\{stream}\Output\PRES_OUT\MIXED")
            if pres.UnitString == p_out.UnitString:
                pres.Value = p_out.Value
            else:
                pres.Value = convert(self.connections_data[stream]["p"], SI_UNITS["p"], pres.UnitString)
            self.set_rows(base + r"\PROPERTIES", [prop_set])
            analyses[stream] = (name, len(temperatures))
        return analyses

    def analysis_states(self, analysis, stream, rows):
        """
        Reads the temperature and h and s per kg of the first ``rows`` rows of the analysis of a stream.

        Returns:
            list: (T in K, h in J/kg, s in J/kgK) of each row; a value without a result in Aspen is None.
        """
        tree = self.aspen.Tree
        out = rf"\Data\Properties\Analysis\{analysis}\Output\PROP_DATA"
        mw = tree.FindNode(rf"\Data\Streams\{stream}\Output\MW")
        molar_mass = mw.Value * 1e-3 if mw is not None and mw.Value else None
        states = []
        for row in range(1, rows + 1):
            temp = tree.FindNode(out + rf"\TEMP\{row}")
            T = None if temp is None or temp.Value is None else convert_to_SI("T", temp.Value, temp.UnitString)
            h, s = (
                self.per_kg(out + rf"\{prop}\TOTAL\{row}", key, molar_mass)
                for prop, key in (("HMX", "h"), ("SMX", "s"))
            )
            states.append((T, h, s))
        return states

    def per_kg(self, path, key, molar_mass):
        """
        Reads a value per kg or per mol and returns it in the SI unit of ``key``, per kg.

        Parameters:
            molar_mass (float): Molar mass in kg/mol, to convert a value per mol.
        """
        node = self.aspen.Tree.FindNode(path)
        if node is None or node.Value is None:
            return None
        try:
            return convert_to_SI(key, node.Value, node.UnitString)
        except ValueError:
            if molar_mass is None:
                return None
            return convert(node.Value, node.UnitString, SI_UNITS[key].replace("kg", "mol")) / molar_mass

    def set_rows(self, path, values):
        """Inserts rows with ``values`` into the list at ``path``."""
        elements = self.aspen.Tree.FindNode(path).Elements
        for i, value in enumerate(values):
            elements.InsertRow(0, i)
            elements.Item(i).Value = value

    @staticmethod
    def free_names(folder, stem, count):
        """Returns ``count`` IDs ``stem1``, ``stem2``, ... that no element of ``folder`` uses yet."""
        taken = {element.Name for element in folder.Elements}
        return list(itertools.islice((f"{stem}{k}" for k in itertools.count(1) if f"{stem}{k}" not in taken), count))

    def parse_blocks(self):
        """
        Parses the blocks (components) in the Aspen model and ensures that all components, including motors created from pumps, are properly grouped.
        """
        block_nodes = self.aspen.Tree.FindNode(r"\Data\Blocks").Elements
        block_names = [block_node.Name for block_node in block_nodes]

        # Process each block
        for block_name in block_names:
            model_type_node = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Input\MODEL_TYPE")
            model_type = model_type_node.Value if model_type_node is not None else None

            component_type_node = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}")
            if component_type_node is None:
                continue
            component_type = component_type_node.AttributeValue(6)
            if component_type == "Mixer":
                mixer_value = component_type_node.Value
                if mixer_value in ["TRIANGLE", "HEAT"]:
                    logger.info(f"Ignoring Mixer {block_name} with value {mixer_value}.")
                    continue

            component_data = {
                "name": block_name,
                "type": component_type,
                "eta_s": (
                    self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\EFF_ISEN").Value
                    if self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\EFF_ISEN") is not None
                    else None
                ),
                "eta_mech": (
                    self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\EFF_MECH").Value
                    if self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\EFF_MECH") is not None
                    else None
                ),
                "Q": (
                    convert_to_SI(
                        "Q",
                        self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\QNET").Value,
                        self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\QNET").UnitString,
                    )
                    if self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\QNET") is not None
                    else None
                ),
                "Q_unit": SI_UNITS["Q"],
                "P": (
                    convert_to_SI(
                        "P",
                        abs(self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\BRAKE_POWER").Value),
                        self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\BRAKE_POWER").UnitString,
                    )
                    if self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\BRAKE_POWER") is not None
                    else None
                ),
                "P_unit": SI_UNITS["P"],
            }

            # Override component type based on model_type
            if model_type is not None:
                if model_type == "COMPRESSOR":
                    component_data["type"] = "Compressor"
                elif model_type == "TURBINE":
                    component_data["type"] = "Turbine"

            # Handle Generators & Motors (if not in a Pump) as multiplier blocks
            if component_type == "Mult":
                mult_value_node = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}")
                mult_value = mult_value_node.Value if mult_value_node is not None else None
                if mult_value == "WORK":
                    factor_node = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Input\FACTOR")
                    factor = factor_node.Value if factor_node is not None else None
                    if factor is not None:
                        if self.mult_block_type(block_name, factor) == "Generator":
                            component_data.update({"eta_el": factor, "type": "Generator"})
                        else:
                            component_data.update(
                                {
                                    "eta_el": 1 / factor,
                                    "multiplier factor": factor,
                                    "multiplier factor_unit": "dimensionless",
                                    "type": "Motor",
                                    "P_el": self.port_power(block_name, "WS(OUT)"),
                                    "P_el_unit": SI_UNITS["P"],
                                    "P_mech": self.port_power(block_name, "WS(IN)"),
                                    "P_mech_unit": SI_UNITS["P"],
                                }
                            )

            # Create a connection for the heat flows of the SimpleHeatExchanger blocks
            if component_type == "Heater":
                heat_connection_name = f"{block_name}_HEAT"
                heat_connection_data = {
                    "name": heat_connection_name,
                    "kind": "heat",
                    "source_component": block_name,
                    "source_connector": 1,  # 00 is reserved for the fluid streams
                    "target_component": None,  # Heat assumed to leave the system (not relevant for exergy analysis)
                    "target_connector": None,  # Heat assumed to leave the system (not relevant for exergy analysis)
                    "energy_flow": abs(
                        component_data["Q"]
                    ),  # the user defines in the balances if the heat flow is positive or negative
                    "energy_flow_unit": SI_UNITS["energy_flow"],
                }

                # Store the heat connection
                self.connections_data[heat_connection_name] = heat_connection_data

            # Group the component
            self.group_component(component_data, block_name)

            # Handle Pumps and their associated Motors
            if component_type == "Pump":
                motor_name = f"{block_name}-MOTOR"
                elec_power_node = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\ELEC_POWER")
                elec_power = (
                    abs(
                        convert_to_SI(
                            "P",
                            elec_power_node.Value,
                            elec_power_node.UnitString,
                        )
                    )
                    if elec_power_node is not None
                    else None
                )
                brake_power_node = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\BRAKE_POWER")
                brake_power = (
                    abs(
                        convert_to_SI(
                            "P",
                            brake_power_node.Value,
                            brake_power_node.UnitString,
                        )
                    )
                    if brake_power_node is not None
                    else None
                )
                eff_driv_node = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Output\EFF_DRIV")
                eff_driv = eff_driv_node.Value if eff_driv_node is not None else None

                motor_data = {
                    "name": motor_name,
                    "type": "Motor",
                    "P_el": elec_power,
                    "P_el_unit": SI_UNITS["P"],
                    "P_mech": brake_power,
                    "P_mech_unit": SI_UNITS["P"],
                    "eta_el": (eff_driv if eff_driv is not None else None),
                }

                # Group the motor
                self.group_component(motor_data, motor_name)

                # Create a new connection for the motor
                if elec_power is not None:
                    electr_connection_name = f"{block_name}_ELEC"
                    electr_connection_data = {
                        "name": electr_connection_name,
                        "kind": "power",
                        "source_component": None,  # Electrical power usually leaves the system
                        "source_connector": None,  # Electrical power usually leaves the system
                        "target_component": motor_name,
                        "target_connector": 0,
                        "energy_flow": motor_data["P_el"],
                        "energy_flow_unit": SI_UNITS["energy_flow"],
                    }

                    mech_connection_name = f"{block_name}_MECH"
                    mech_connection_data = {
                        "name": mech_connection_name,
                        "kind": "power",
                        "source_component": motor_name,
                        "source_connector": 0,
                        "target_component": block_name,
                        "target_connector": 1,
                        "energy_flow": motor_data["P_mech"],
                        "energy_flow_unit": SI_UNITS["energy_flow"],
                    }

                    # Store the motor connection
                    self.connections_data[electr_connection_name] = electr_connection_data
                    self.connections_data[mech_connection_name] = mech_connection_data

            # Assign connectors
            self.assign_connectors(component_data, block_name)

    def mult_block_type(self, block_name, factor):
        """
        Decides whether a multiplier block on work streams is a generator or a motor.

        The work stream entering the block comes from its machine. Aspen reports its power as negative if the
        machine produces it, as a turbine does for a generator, and as positive if the machine consumes it, as a
        compressor or a pump does for a motor. Without this sign, a factor below 1 means a generator and a
        factor above 1 a motor.

        Returns:
            str: "Generator" or "Motor".
        """
        port = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports\WS(IN)")
        signs = set()
        if port is not None:
            signs = {
                self.connections_data[element.Name].get("_aspen_power_sign")
                for element in port.Elements
                if element.Name in self.connections_data
            } - {None}
        if len(signs) == 1:
            block_type = "Generator" if signs.pop() < 0 else "Motor"
            if (block_type == "Generator" and factor > 1) or (block_type == "Motor" and factor < 1):
                logger.warning(
                    f"Multiplier block {block_name} is a {block_type.lower()} by the sign of its power, but its "
                    f"factor {factor} gives an efficiency above 1."
                )
            return block_type
        if factor == 1:
            logger.warning(
                f"Multiplier block {block_name} has the factor 1 and no inlet work stream with a known power, so "
                f"it is taken as a generator."
            )
        return "Generator" if factor <= 1 else "Motor"

    def port_power(self, block_name, port):
        """
        Returns the power of the first work stream at a port of a block, or None if there is none.
        """
        port_node = self.aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports\{port}")
        if port_node is None or port_node.Elements.Count == 0:
            logger.warning(f"No {port} port found for block {block_name}")
            return None
        stream_name = port_node.Elements(0).Name
        if stream_name not in self.connections_data:
            logger.warning(f"The work stream {stream_name} at the {port} port of block {block_name} is unknown")
            return None
        return abs(self.connections_data[stream_name]["energy_flow"])

    def assign_connectors(self, component_data, block_name):
        """
        Assigns connectors to streams for each component based on its type.
        """
        component_type = component_data["type"]

        # Check if there is a specific assignment function for this component type
        if component_type in self.connector_assignment_functions:
            # Call the specific function for the component type
            self.connector_assignment_functions[component_type](block_name, self.aspen, self.connections_data)
        else:
            # Fall back to the generic connector assignment logic
            self.assign_generic_connectors(
                block_name, component_type, self.aspen, self.connections_data, connector_mappings
            )

    def assign_mixer_connectors(self, block_name, aspen, connections_data):
        """
        Assign connectors for a Mixer by examining connected streams and their source/target components.
        """
        ports_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports")
        if ports_node is None:
            logger.warning(f"No Ports node found for Mixer block: {block_name}")
            return

        inlet_streams = []
        outlet_streams = []

        for port in ports_node.Elements:
            port_label = port.Name
            port_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports\{port_label}")
            if port_node is not None and port_node.Elements.Count > 0:
                for element in port_node.Elements:
                    stream_name = element.Name
                    if stream_name in connections_data:
                        stream_data = connections_data[stream_name]
                        if stream_data.get("target_component") == block_name:
                            inlet_streams.append((port_label, stream_name))
                        elif stream_data.get("source_component") == block_name:
                            outlet_streams.append((port_label, stream_name))
                        else:
                            logger.warning(
                                f"Stream {stream_name} connected to {block_name} but source/target components do not match."
                            )

        # Assign connectors to inlet streams
        for idx, (port_label, stream_name) in enumerate(inlet_streams):
            connections_data[stream_name]["target_connector"] = idx
            logger.debug(f"Assigned connector {idx} to inlet stream: {stream_name}")

        # Assign connector to outlet stream
        if outlet_streams:
            for idx, (port_label, stream_name) in enumerate(outlet_streams):
                connections_data[stream_name]["source_connector"] = 0  # Assuming single outlet for mixer
                logger.debug(f"Assigned connector 0 to outlet stream: {stream_name}")

    def assign_splitter_connectors(self, block_name, aspen, connections_data):
        """
        Assign connectors for a Splitter (FSplit) by examining connected streams and their source/target components.
        The inlet stream is assigned 'target_connector' = 0.
        The outlet streams are assigned 'source_connector' numbers starting from 0.
        """
        ports_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports")
        if ports_node is None:
            logger.warning(f"No Ports node found for Splitter block: {block_name}")
            return

        inlet_streams = []
        outlet_streams = []

        # Iterate over all ports connected to the splitter
        for port in ports_node.Elements:
            port_label = port.Name
            port_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports\{port_label}")
            if port_node is not None and port_node.Elements.Count > 0:
                for element in port_node.Elements:
                    stream_name = element.Name
                    if stream_name in connections_data:
                        stream_data = connections_data[stream_name]
                        # Determine if the stream is an inlet or outlet based on source and target components
                        if stream_data.get("target_component") == block_name:
                            inlet_streams.append((port_label, stream_name))
                        elif stream_data.get("source_component") == block_name:
                            outlet_streams.append((port_label, stream_name))
                        else:
                            logger.warning(
                                f"Stream {stream_name} connected to {block_name} but source/target components do not match."
                            )

        # Assign connector to inlet stream(s)
        for idx, (port_label, stream_name) in enumerate(inlet_streams):
            connections_data[stream_name]["target_connector"] = 0  # Assuming single inlet for splitter
            logger.debug(f"Assigned connector 0 to inlet stream: {stream_name}")

        # Assign connectors to outlet streams
        for idx, (port_label, stream_name) in enumerate(outlet_streams):
            connections_data[stream_name]["source_connector"] = idx
            logger.debug(f"Assigned connector {idx} to outlet stream: {stream_name}")

    def assign_turbine_connectors(self, block_name, aspen, connections_data):
        """
        Assign connectors for a Turbine (Compr with MODEL_TYPE=TURBINE).

        In Aspen, a gas turbine has up to one input and one output power connection:

        - F(IN): inlet gas flow → inlet connector 0
        - P(OUT): outlet gas flow → outlet connector 0
        - WS(OUT): power output → outlet connector 1
        - WS(IN): direction depends on the sign of the Aspen power value:

            - positive → power leaves the turbine → outlet connector 2 (source/target swapped)
            - negative → power enters the turbine → inlet connector 1 (kept as-is)

        The ``_aspen_power_sign`` field (set during ``parse_streams``) carries the sign
        of the raw Aspen POWER_OUT value.  ``energy_flow`` is always stored as a positive
        value because ExerPy does not work with negative values.
        """
        ports_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports")
        if ports_node is None:
            logger.warning(f"No Ports node found for Turbine block: {block_name}")
            return

        for port in ports_node.Elements:
            port_label = port.Name
            port_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports\{port_label}")
            if port_node is None or port_node.Elements.Count == 0:
                continue

            for element in port_node.Elements:
                stream_name = element.Name
                if stream_name not in connections_data:
                    continue

                stream = connections_data[stream_name]

                if port_label == "F(IN)":
                    if stream.get("target_component") == block_name:
                        stream["target_connector"] = 0
                elif port_label == "P(OUT)":
                    if stream.get("source_component") == block_name:
                        stream["source_connector"] = 0
                elif port_label == "WS(OUT)":
                    if stream.get("source_component") == block_name:
                        stream["source_connector"] = 1
                elif port_label == "WS(IN)":
                    if stream.get("kind") != "power":
                        continue
                    power_sign = stream.get("_aspen_power_sign", -1)
                    if power_sign >= 0:
                        # Positive value: power actually leaves the turbine (e.g., shaft to compressor).
                        # Swap source/target so the turbine becomes the source (outlet).
                        old_source = stream["source_component"]
                        old_source_connector = stream.get("source_connector")
                        stream["source_component"] = block_name
                        stream["source_connector"] = 2
                        stream["target_component"] = old_source
                        stream["target_connector"] = old_source_connector
                        logger.info(
                            f"Turbine {block_name}: WS(IN) power stream '{stream_name}' has positive "
                            f"value — swapped direction, turbine is now the source, "
                            f"'{old_source}' is the target."
                        )
                    else:
                        # Negative value: power truly enters the turbine (input).
                        # Keep direction as-is, assign inlet connector 1.
                        if stream.get("target_component") == block_name:
                            stream["target_connector"] = 1
                        logger.info(
                            f"Turbine {block_name}: WS(IN) power stream '{stream_name}' has negative "
                            f"value — kept as inlet (power enters turbine)."
                        )

    def assign_combustion_chamber_connectors(self, block_name, aspen, connections_data):
        """
        Assign connectors for a combustion chamber (RStoic), based on stream types (air, fuel, etc.).
        """
        ports_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports")
        if ports_node is None:
            logger.warning(f"No Ports node found for combustion chamber block: {block_name}")
            return

        # Iterate over all ports and assign connectors based on port labels
        for port in ports_node.Elements:
            port_label = port.Name

            # Handle inlet ports
            if "(IN)" in port_label:
                port_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports\{port_label}")
                if port_node is not None and port_node.Elements.Count > 0:
                    for element in port_node.Elements:
                        stream_name = element.Name
                        if stream_name in connections_data:
                            molar_composition = connections_data[stream_name].get("molar_composition", {})
                            if molar_composition.get("O2", 0) > 0.15:
                                connections_data[stream_name]["target_connector"] = 0  # Air inlet
                                logger.debug(f"Assigned connector 0 to air inlet stream: {stream_name}")
                            elif molar_composition.get("CH4", 0) > 0.15:
                                connections_data[stream_name]["target_connector"] = 1  # Fuel inlet
                                logger.debug(f"Assigned connector 1 to fuel inlet stream: {stream_name}")
                            else:
                                logger.warning(f"Stream {stream_name} in {block_name} has ambiguous composition.")

            # Handle outlet ports
            elif "(OUT)" in port_label:
                port_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports\{port_label}")
                if port_node is not None and port_node.Elements.Count > 0:
                    for element in port_node.Elements:
                        stream_name = element.Name
                        if stream_name in connections_data:
                            connections_data[stream_name]["source_connector"] = 0  # Outlet stream
                            logger.info(f"Assigned connector 0 to outlet stream: {stream_name}")

    def assign_generic_connectors(self, block_name, component_type, aspen, connections_data, connector_mappings):
        """
        Generic function for components with predefined connector mappings.
        """
        if component_type in connector_mappings:
            mapping = connector_mappings[component_type]

            # Access the ports of the component to find the connected streams
            for port_label, connector_num in mapping.items():
                port_node = aspen.Tree.FindNode(rf"\Data\Blocks\{block_name}\Ports\{port_label}")
                if port_node is not None and port_node.Elements.Count > 0:
                    for element in port_node.Elements:
                        stream_name = element.Name
                        # Assign the connector number to the appropriate stream in the connection data
                        if stream_name in connections_data:
                            if (
                                "source_component" in connections_data[stream_name]
                                and connections_data[stream_name]["source_component"] == block_name
                            ):
                                connections_data[stream_name]["source_connector"] = connector_num
                                logger.debug(f"Assigned connector {connector_num} to source stream: {stream_name}")
                            elif (
                                "target_component" in connections_data[stream_name]
                                and connections_data[stream_name]["target_component"] == block_name
                            ):
                                connections_data[stream_name]["target_connector"] = connector_num
                                logger.debug(f"Assigned connector {connector_num} to target stream: {stream_name}")
        else:
            logger.warning(f"No connector mapping defined for component type {component_type}.")

    def group_component(self, component_data, component_name):
        """
        Group the component based on its type into the correct group within components_data.

        Parameters:
        - component_data: The dictionary of component attributes.
        - component_name: The name of the component.
        """
        # Determine the group for the component based on its type
        group = None
        for group_name, type_list in grouped_components.items():
            if component_data["type"] in type_list:
                group = group_name
                break

        # If the component doesn't belong to any predefined group, use its type name
        if not group:
            group = component_data["type"]

        # Initialize the group in the components_data dictionary if not already present
        if group not in self.components_data:
            self.components_data[group] = {}

        # Store the component data in the appropriate group
        self.components_data[group][component_name] = component_data

    def set_ambient_conditions(self):
        """
        Writes the ambient state passed to the parser to REF_TEMP and REF_PRES and runs the model again, so that
        Aspen computes the exergies of the streams at it. Nothing happens if no value is passed or the model holds
        the passed values already. The change exists in memory only; the model file stays unchanged.

        Raises:
            ValueError: If the model has no REF_TEMP or REF_PRES node for a passed value.
        """
        changed = False
        for key, value, path in (
            ("Tamb", self.Tamb, r"\Data\Setup\Sim-Options\Input\REF_TEMP"),
            ("pamb", self.pamb, r"\Data\Setup\Sim-Options\Input\REF_PRES"),
        ):
            if value is None:
                continue
            node = self.aspen.Tree.FindNode(path)
            if node is None:
                raise ValueError(f"The Aspen model has no node {path} to set {key} = {value} {SI_UNITS[key]}.")
            if node.Value is not None and math.isclose(
                convert_to_SI(key, node.Value, node.UnitString), value, rel_tol=1e-6
            ):
                continue
            node.Value = convert(value, SI_UNITS[key], node.UnitString)
            changed = True
        if changed:
            logger.info("Running the model again at the ambient state passed to the parser.")
            self.aspen.SuppressDialogs = 1
            self.aspen.Engine.Run2()

    def parse_ambient_conditions(self):
        """
        Parses the ambient conditions from the Aspen model and stores them as class attributes.
        Raises an error if Tamb or pamb are not found or are set to None.
        """
        try:
            # Parse ambient temperature (Tamb)
            temp_node = self.aspen.Tree.FindNode(r"\Data\Setup\Sim-Options\Input\REF_TEMP")
            self.Tamb = convert_to_SI("Tamb", temp_node.Value, temp_node.UnitString) if temp_node is not None else None

            if self.Tamb is None:
                raise ValueError(
                    "Ambient temperature (Tamb) not found in the Aspen model. Please set it in Setup > Calculation Options."
                )

            # Parse ambient pressure (pamb)
            pres_node = self.aspen.Tree.FindNode(r"\Data\Setup\Sim-Options\Input\REF_PRES")
            self.pamb = convert_to_SI("pamb", pres_node.Value, pres_node.UnitString) if pres_node is not None else None

            if self.pamb is None:
                raise ValueError(
                    "Ambient pressure (pamb) not found in the Aspen model. Please set it in Setup > Calculation Options."
                )

            logger.info(f"Parsed ambient conditions: Tamb = {self.Tamb} K, pamb = {self.pamb} Pa")

        except Exception as e:
            logger.error(f"Error parsing ambient conditions: {e}")
            raise

    def get_sorted_data(self):
        """
        Sorts the component and connection data alphabetically by name.

        Returns:
            dict: A dictionary containing sorted 'components', 'connections', and ambient conditions data.
        """
        sorted_components = {comp_name: self.components_data[comp_name] for comp_name in sorted(self.components_data)}
        sorted_connections = {
            conn_name: self.connections_data[conn_name] for conn_name in sorted(self.connections_data)
        }
        ambient_conditions = {
            "Tamb": self.Tamb,
            "Tamb_unit": SI_UNITS["Tamb"],
            "pamb": self.pamb,
            "pamb_unit": SI_UNITS["pamb"],
        }
        return add_units(
            {
                "components": sorted_components,
                "connections": sorted_connections,
                "ambient_conditions": ambient_conditions,
            }
        )

    def write_to_json(self, output_path):
        """
        Writes the parsed and sorted data to a JSON file.

        Parameters:
            output_path (str): Path where the JSON file will be saved.
        """
        data = self.get_sorted_data()

        try:
            with open(output_path, "w") as json_file:
                json.dump(data, json_file, indent=4)
            logger.info(f"Data successfully written to {output_path}")
        except Exception as e:
            logger.error(f"Failed to write data to JSON: {e}")
            raise


def run_aspen(model_path, output_dir=None, split_physical_exergy=True, Tamb=None, pamb=None):
    """
    Main function to process the Aspen model and return parsed data.
    Optionally writes the parsed data to a JSON file.

    Parameters:
        model_path (str): Path to the Aspen model file.
        output_dir (str): Optional path where the parsed data should be saved as a JSON file.
        split_physical_exergy (bool): Flag to split physical exergy into thermal and mechanical components.
        Tamb (float): Ambient temperature in K. Defaults to REF_TEMP of the model. A value passed here
            replaces REF_TEMP and the model is run again, so all exergies are computed at it. The model
            file stays unchanged.
        pamb (float): Ambient pressure in Pa, like ``Tamb`` for REF_PRES.

    Returns:
        dict: Parsed data in dictionary format. Its ``ambient_conditions`` hold the ambient state
        the exergies were computed at.
    """
    if not os.path.exists(model_path):
        error_msg = f"Model file not found at: {model_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    parser = AspenModelParser(model_path, split_physical_exergy=split_physical_exergy, Tamb=Tamb, pamb=pamb)

    try:
        parser.initialize_model()
        parser.parse_model()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise RuntimeError(f"An error occurred: {e}")

    parsed_data = parser.get_sorted_data()

    if output_dir is not None:
        try:
            parser.write_to_json(output_dir)
        except Exception as e:
            logger.error(f"Failed to write output file: {e}")
            raise RuntimeError(f"Failed to write output file: {e}")

    return parsed_data
