"""
Test suite for the AspenModelParser class.

This module provides comprehensive testing for the AspenModelParser functionality,
including model initialization, ambient conditions extraction, stream and block parsing,
connector assignments, component grouping, data sorting, and JSON export.
It uses pytest fixtures and unittest.mock to simulate the Aspen COM interface and its behavior.

The test suite verifies:
- Model initialization and COM interface setup
- Ambient conditions extraction from the Aspen model
- Parsing of streams (connections) for power, heat, and material streams
- Parsing of blocks (components), including special handling for Heater, Mult, and Pump types
- Connector assignment for Mixer, Splitter, Combustion Chamber, and generic components
- Component grouping and overall sorted data output
- Complete Aspen model processing workflow via run_aspen
- Splitting of the physical exergy with Generic property analyses
- Error handling for a missing model file
"""

import math
from unittest.mock import Mock
from unittest.mock import patch

import pytest

import exerpy.parser.from_aspen.aspen_parser as ap
from exerpy.parser import STATE_CHECK_STEP
from exerpy.parser.from_aspen.aspen_parser import AspenModelParser
from exerpy.parser.from_aspen.aspen_parser import run_aspen

# --- DummyCollection class to simulate COM collection behavior ---


class DummyCollection(list):
    @property
    def Count(self):
        return len(self)

    def __call__(self, index):
        return self[index]


# --- Dummy COM Node and Tree Classes to simulate Aspen structure ---


class DummyNode:
    """
    Dummy node simulating a node in the Aspen model tree.

    Attributes
    ----------
    Name : str
        Name of the node.
    Value : any
        Value of the node.
    UnitString : str
        Unit of the node value.
    Elements : DummyCollection
        Collection of child nodes.
    """

    def __init__(self, name="", value=None, unit=""):
        self.Name = name
        self.Value = value
        self.UnitString = unit
        self.Elements = DummyCollection()


class DummyTree:
    """
    Dummy tree simulating the Aspen model tree.

    Attributes
    ----------
    nodes : dict
        Dictionary mapping node paths to DummyNode instances.
    """

    def __init__(self, nodes):
        self.nodes = nodes

    def FindNode(self, path):
        """
        Find and return a dummy node by its path.

        Parameters
        ----------
        path : str
            The path of the node to find.

        Returns
        -------
        DummyNode or None
            The found node or None if not found.
        """
        return self.nodes.get(path, None)


class DummyAspen:
    """
    Dummy Aspen application simulating the COM interface.

    Attributes
    ----------
    Tree : DummyTree
        The dummy tree structure of the Aspen model.
    """

    def __init__(self, tree):
        self.Tree = tree

    def InitFromArchive2(self, model_path):
        """
        Simulate model initialization from an archive.

        Parameters
        ----------
        model_path : str
            Path to the model file.
        """
        self.model_path = model_path


# --- Helper class for block nodes ---


class DummyBlockNode(DummyNode):
    """
    Dummy node for blocks that provides an AttributeValue method.

    Parameters
    ----------
    attr_value : any
        The value to return for AttributeValue(6).
    """

    def __init__(self, name, value, attr_value):
        super().__init__(name, value)
        self._attr_value = attr_value

    def AttributeValue(self, index):
        if index == 6:
            return self._attr_value
        return None


# --- Fixtures for dummy conversion and fluid property data ---


@pytest.fixture
def dummy_convert_to_SI(monkeypatch):
    """
    Dummy conversion function to bypass unit conversion complexity, patched into the parser for one test.

    Returns
    -------
    function
        A function that returns the numeric value without conversion.
    """

    def dummy(phys, value, unit_str):
        return value

    monkeypatch.setattr(ap, "convert_to_SI", dummy)
    return dummy


# --- Fixture to setup a parser with a dummy Aspen COM object (ambient only) ---


@pytest.fixture
def parser_with_dummy_aspen(dummy_convert_to_SI):
    """
    Fixture that returns an AspenModelParser instance with a dummy Aspen COM object.

    The dummy Aspen object simulates the minimal tree structure required for
    ambient conditions extraction.

    Returns
    -------
    AspenModelParser
        Parser instance with injected dummy Aspen object.
    """
    nodes = {
        r"\Data\Setup\Sim-Options\Input\REF_TEMP": DummyNode("REF_TEMP", 300, "K"),
        r"\Data\Setup\Sim-Options\Input\REF_PRES": DummyNode("REF_PRES", 101325, "Pa"),
        r"\Data\Streams": DummyNode("Streams"),
        r"\Data\Blocks": DummyNode("Blocks"),
    }
    tree = DummyTree(nodes)
    dummy_aspen = DummyAspen(tree)

    parser = AspenModelParser("dummy_model.apw")
    parser.aspen = dummy_aspen
    return parser


# --- Tests for parse_streams ---


def test_parse_streams(dummy_convert_to_SI):
    """
    Test the parsing of streams (connections) from the Aspen model.

    Verifies
    --------
    - Power stream: detects WORK input and retrieves POWER_OUT value.
    - Heat stream: detects HEAT input and retrieves QCALC value.
    - Material stream: retrieves temperature, pressure, enthalpy, entropy, mass flow,
      energy flow, exergy, total flow, and fluid composition.
    """
    stream1 = DummyNode("Stream1")
    stream2 = DummyNode("Stream2")
    stream3 = DummyNode("Stream3")
    streams_parent = DummyNode("Streams")
    streams_parent.Elements = DummyCollection([stream1, stream2, stream3])

    source_elem = DummyNode("CompA")
    dest_elem = DummyNode("CompB")
    nodes = {
        r"\Data\Streams": streams_parent,
        r"\Data\Streams\Stream1": DummyNode("Stream1"),
        r"\Data\Streams\Stream1\Ports\SOURCE": DummyNode("SOURCE"),
        r"\Data\Streams\Stream1\Ports\DEST": DummyNode("DEST"),
        r"\Data\Streams\Stream1\Input\WORK": DummyNode("WORK"),
        r"\Data\Streams\Stream1\Output\POWER_OUT": DummyNode("POWER_OUT", 100, "W"),
        r"\Data\Streams\Stream2": DummyNode("Stream2"),
        r"\Data\Streams\Stream2\Input\HEAT": DummyNode("HEAT"),
        r"\Data\Streams\Stream2\Output\QCALC": DummyNode("QCALC", 200, "W"),
        r"\Data\Streams\Stream3": DummyNode("Stream3"),
        r"\Data\Streams\Stream3\Output\TEMP_OUT\MIXED": DummyNode("TEMP_OUT", 350, "K"),
        r"\Data\Streams\Stream3\Output\PRES_OUT\MIXED": DummyNode("PRES_OUT", 101325, "Pa"),
        r"\Data\Streams\Stream3\Output\HMX_MASS\MIXED": DummyNode("HMX_MASS", 1500, "J/kg"),
        r"\Data\Streams\Stream3\Output\SMX_MASS\MIXED": DummyNode("SMX_MASS", 3, "J/kgK"),
        r"\Data\Streams\Stream3\Output\MASSFLMX\MIXED": DummyNode("MASSFLMX", 5, "kg"),
        r"\Data\Streams\Stream3\Output\HMX_FLOW\MIXED": DummyNode("HMX_FLOW", 250, "W"),
        r"\Data\Streams\Stream3\Output\STRM_UPP\EXERGYMS\MIXED\TOTAL": DummyNode("EXERGYMS", 400, "J"),
        r"\Data\Streams\Stream3\Output\TOT_FLOW": DummyNode("TOT_FLOW", 10, "mol/s"),
        r"\Data\Streams\Stream3\Output\VOLFLMX\MIXED": DummyNode("VOLFLMX", 0.25, "cum/sec"),
        r"\Data\Streams\Stream3\Output\MASSVFRA": DummyNode("MASSVFRA", 0.4, ""),
    }
    nodes[r"\Data\Streams\Stream1\Ports\SOURCE"].Elements = DummyCollection([source_elem])
    nodes[r"\Data\Streams\Stream1\Ports\DEST"].Elements = DummyCollection([dest_elem])
    nodes[r"\Data\Streams\Stream2\Ports\SOURCE"] = DummyNode("SOURCE")
    nodes[r"\Data\Streams\Stream2\Ports\DEST"] = DummyNode("DEST")
    nodes[r"\Data\Streams\Stream2\Ports\SOURCE"].Elements = DummyCollection([DummyNode("CompC")])
    nodes[r"\Data\Streams\Stream2\Ports\DEST"].Elements = DummyCollection([DummyNode("CompD")])
    nodes[r"\Data\Streams\Stream3\Ports\SOURCE"] = DummyNode("SOURCE")
    nodes[r"\Data\Streams\Stream3\Ports\DEST"] = DummyNode("DEST")
    nodes[r"\Data\Streams\Stream3\Ports\SOURCE"].Elements = DummyCollection([DummyNode("CompE")])
    nodes[r"\Data\Streams\Stream3\Ports\DEST"].Elements = DummyCollection([DummyNode("CompF")])

    # Mole and mass fraction nodes.
    mole_frac_node = DummyNode("MOLEFRAC")
    mole_frac_node.Elements = DummyCollection([DummyNode("Water")])
    nodes[r"\Data\Streams\Stream3\Output\MOLEFRAC\MIXED"] = mole_frac_node
    nodes[r"\Data\Streams\Stream3\Output\MOLEFRAC\MIXED\Water"] = DummyNode("Water", 0.9)
    mass_frac_node = DummyNode("MASSFRAC")
    mass_frac_node.Elements = DummyCollection([DummyNode("Water")])
    nodes[r"\Data\Streams\Stream3\Output\MASSFRAC\MIXED"] = mass_frac_node
    nodes[r"\Data\Streams\Stream3\Output\MASSFRAC\MIXED\Water"] = DummyNode("Water", 0.8)

    tree = DummyTree(nodes)
    dummy_aspen = DummyAspen(tree)
    parser = AspenModelParser("dummy_model.apw")
    parser.aspen = dummy_aspen

    parser.parse_streams()

    conn1 = parser.connections_data.get("Stream1")
    assert conn1 is not None
    assert conn1["kind"] == "power"
    assert conn1["energy_flow"] == 100
    assert conn1["source_component"] == "CompA"
    assert conn1["target_component"] == "CompB"

    conn2 = parser.connections_data.get("Stream2")
    assert conn2 is not None
    assert conn2["kind"] == "heat"
    assert conn2["energy_flow"] == 200

    conn3 = parser.connections_data.get("Stream3")
    assert conn3 is not None
    assert conn3["kind"] == "material"
    assert conn3["T"] == 350
    assert conn3["p"] == 101325
    assert conn3["h"] == 1500
    assert conn3["s"] == 3
    assert conn3["m"] == 5
    assert conn3["energy_flow"] == 250
    assert conn3["e_PH"] == 400
    assert conn3["n"] == 10
    assert conn3["v"] == 0.25
    assert conn3["x"] == 0.4
    assert conn3["molar_composition"].get("Water") == 0.9
    assert conn3["mass_composition"].get("Water") == 0.8


# --- Tests for parse_blocks and component grouping ---


def test_parse_blocks_and_grouping(dummy_convert_to_SI, monkeypatch):
    """
    Test parsing of blocks (components) and grouping of components.

    This test simulates:
    - A Heater block that should create a heat connection.
    - A Mult block with factor < 1 (Generator scenario).
    - A Pump block that creates an associated Motor.
    - Grouping of components based on type using grouped_components.

    Verifies
    --------
    - Components are parsed and grouped.
    - Additional connections (like heater heat connection and pump motor connections) are created.
    """
    # Patch grouped_components and connector_mappings.
    dummy_grouped = {"GroupA": ["Heater", "Pump", "Mult", "Compressor", "Turbine"], "GroupB": ["Other"]}
    dummy_connector_mappings = {}
    monkeypatch.setattr(ap, "grouped_components", dummy_grouped)
    monkeypatch.setattr(ap, "connector_mappings", dummy_connector_mappings)

    blocks_parent = DummyNode("Blocks")
    # Heater block: Block1.
    block1 = DummyBlockNode("Block1", "dummy", "Heater")
    heater_output = DummyNode("QNET", 500, "W")
    # Mult block (Generator scenario): Block2.
    block2 = DummyBlockNode("Block2", "WORK", "Mult")
    factor_node = DummyNode("FACTOR", 0.8)
    # Pump block: Block3.
    block3 = DummyBlockNode("Block3", "Pump", "Pump")
    elec_power_node = DummyNode("ELEC_POWER", 120, "W")
    brake_power_node = DummyNode("BRAKE_POWER", 80, "W")
    eff_driv_node = DummyNode("EFF_DRIV", 0.95, "")

    blocks_parent.Elements = DummyCollection([block1, block2, block3])
    tree_nodes = {
        r"\Data\Blocks": blocks_parent,
        r"\Data\Blocks\Block1": block1,
        r"\Data\Blocks\Block1\Output\QNET": heater_output,
        r"\Data\Blocks\Block2": block2,
        r"\Data\Blocks\Block2\Input\FACTOR": factor_node,
        r"\Data\Blocks\Block3": block3,
        r"\Data\Blocks\Block3\Output\ELEC_POWER": elec_power_node,
        r"\Data\Blocks\Block3\Output\BRAKE_POWER": brake_power_node,
        r"\Data\Blocks\Block3\Output\EFF_DRIV": eff_driv_node,
    }
    dummy_tree = DummyTree(tree_nodes)
    dummy_aspen = DummyAspen(dummy_tree)
    parser = AspenModelParser("dummy_model.apw")
    parser.aspen = dummy_aspen
    parser.connections_data = {}  # start empty

    parser.parse_blocks()

    # Block1 is a Heater; expect it in "GroupA".
    assert "Block1" in parser.components_data.get("GroupA", {})
    # Block2, having been processed as a Mult block with factor < 1, becomes "Generator".
    assert "Block2" in parser.components_data.get("Generator", {})
    # Block3 is a Pump; expect it in "GroupA".
    assert "Block3" in parser.components_data.get("GroupA", {})
    # For Pump block, also expect a motor group created with name "Block3-MOTOR" in the Motor group.
    assert "Block3-MOTOR" in parser.components_data.get("Motor", {})

    # Check that heater connection is created.
    heater_conn_name = "Block1_HEAT"
    assert heater_conn_name in parser.connections_data
    # Check that pump motor connections are created.
    elec_conn_name = "Block3_ELEC"
    mech_conn_name = "Block3_MECH"
    assert elec_conn_name in parser.connections_data
    assert mech_conn_name in parser.connections_data


# --- Tests for connector assignment routines ---


def test_assign_mixer_connectors():
    """
    Test the assign_mixer_connectors function for a Mixer component.

    Verifies
    --------
    - Inlet streams get assigned incremental target_connector numbers.
    - Outlet streams get assigned source_connector = 0.
    """
    inlet_elem = DummyNode("StreamIn")
    outlet_elem = DummyNode("StreamOut")
    port1 = DummyNode("InletPort")
    port1.Elements = DummyCollection([inlet_elem])
    port2 = DummyNode("OutletPort")
    port2.Elements = DummyCollection([outlet_elem])
    mixer_ports = DummyNode("Ports")
    mixer_ports.Elements = DummyCollection([port1, port2])
    dummy_tree = DummyTree(
        {
            r"\Data\Blocks\Mixer1\Ports": mixer_ports,
            r"\Data\Blocks\Mixer1\Ports\InletPort": port1,
            r"\Data\Blocks\Mixer1\Ports\OutletPort": port2,
        }
    )
    dummy_aspen = DummyAspen(dummy_tree)
    connections_data = {"StreamIn": {"target_component": "Mixer1"}, "StreamOut": {"source_component": "Mixer1"}}
    parser = AspenModelParser("dummy.apw")
    parser.assign_mixer_connectors("Mixer1", dummy_aspen, connections_data)
    assert connections_data["StreamIn"].get("target_connector") == 0
    assert connections_data["StreamOut"].get("source_connector") == 0


def test_assign_splitter_connectors():
    """
    Test the assign_splitter_connectors function for a Splitter component.

    Verifies
    --------
    - Inlet streams get assigned target_connector = 0.
    - Outlet streams get assigned source_connector numbers starting from 0.
    """
    inlet_elem = DummyNode("StreamIn")
    outlet_elem = DummyNode("StreamOut")
    inlet_port = DummyNode("Inlet")
    inlet_port.Elements = DummyCollection([inlet_elem])
    outlet_port = DummyNode("Outlet")
    outlet_port.Elements = DummyCollection([outlet_elem])
    splitter_ports = DummyNode("Ports")
    splitter_ports.Elements = DummyCollection([inlet_port, outlet_port])
    dummy_tree = DummyTree(
        {
            r"\Data\Blocks\Splitter1\Ports": splitter_ports,
            r"\Data\Blocks\Splitter1\Ports\Inlet": inlet_port,
            r"\Data\Blocks\Splitter1\Ports\Outlet": outlet_port,
        }
    )
    dummy_aspen = DummyAspen(dummy_tree)
    connections_data = {"StreamIn": {"target_component": "Splitter1"}, "StreamOut": {"source_component": "Splitter1"}}
    parser = AspenModelParser("dummy.apw")
    parser.assign_splitter_connectors("Splitter1", dummy_aspen, connections_data)
    assert connections_data["StreamIn"].get("target_connector") == 0
    assert connections_data["StreamOut"].get("source_connector") == 0


def test_assign_combustion_chamber_connectors():
    """
    Test the assign_combustion_chamber_connectors function for a combustion chamber component.

    Verifies
    --------
    - Inlet streams with high O2 molar composition are assigned target_connector = 0.
    - Outlet streams are assigned source_connector = 0.
    """
    inlet_elem = DummyNode("StreamAir")
    outlet_elem = DummyNode("StreamExhaust")
    inlet_port = DummyNode("Air(IN)")
    inlet_port.Elements = DummyCollection([inlet_elem])
    outlet_port = DummyNode("Exhaust(OUT)")
    outlet_port.Elements = DummyCollection([outlet_elem])
    ports_node = DummyNode("Ports")
    ports_node.Elements = DummyCollection([inlet_port, outlet_port])
    dummy_tree = DummyTree(
        {
            r"\Data\Blocks\Combustion1\Ports": ports_node,
            r"\Data\Blocks\Combustion1\Ports\Air(IN)": inlet_port,
            r"\Data\Blocks\Combustion1\Ports\Exhaust(OUT)": outlet_port,
        }
    )
    dummy_aspen = DummyAspen(dummy_tree)
    connections_data = {"StreamAir": {"molar_composition": {"O2": 0.2}}, "StreamExhaust": {}}
    parser = AspenModelParser("dummy.apw")
    parser.assign_combustion_chamber_connectors("Combustion1", dummy_aspen, connections_data)
    assert connections_data["StreamAir"].get("target_connector") == 0
    assert connections_data["StreamExhaust"].get("source_connector") == 0


def test_assign_generic_connectors():
    """
    Test the assign_generic_connectors function for components with predefined connector mappings.

    Verifies
    --------
    - The connector number is assigned correctly to the stream connected to the component.
    """
    # Provide a mapping keyed by component type.
    dummy_mapping = {"GenericType": {"PortX": 5}}
    port_node = DummyNode("PortX")
    port_node.Elements = DummyCollection([DummyNode("StreamGeneric")])
    dummy_tree = DummyTree({r"\Data\Blocks\Generic1\Ports\PortX": port_node})
    dummy_aspen = DummyAspen(dummy_tree)
    connections_data = {"StreamGeneric": {"target_component": "Generic1"}}
    parser = AspenModelParser("dummy.apw")
    parser.assign_generic_connectors("Generic1", "GenericType", dummy_aspen, connections_data, dummy_mapping)
    assert connections_data["StreamGeneric"].get("target_connector") == 5


def test_group_component(monkeypatch):
    """
    Test the group_component function for proper grouping of components.

    Verifies
    --------
    - The component is stored under the correct group based on its type.
    """
    dummy_grouped = {"GroupA": ["TypeA"], "GroupB": ["TypeB"]}
    monkeypatch.setattr(ap, "grouped_components", dummy_grouped)
    parser = AspenModelParser("dummy.apw")
    component_data = {"name": "Comp1", "type": "TypeA"}
    parser.group_component(component_data, "Comp1")
    assert "Comp1" in parser.components_data.get("GroupA", {})


# --- Tests for multiplier blocks ---


def mult_block_parser(factor, inlet_power=None):
    """
    A parser with the multiplier block M1 between the work stream W1 of a machine and the work stream E1.

    ``inlet_power`` is the power of W1 as Aspen reports it, negative if the machine produces it. Without it,
    M1 has no work streams.
    """
    block = DummyBlockNode("M1", "WORK", "Mult")
    blocks = DummyNode("Blocks")
    blocks.Elements = DummyCollection([block])
    nodes = {
        r"\Data\Blocks": blocks,
        r"\Data\Blocks\M1": block,
        r"\Data\Blocks\M1\Input\FACTOR": DummyNode("FACTOR", factor),
    }
    parser = AspenModelParser("dummy_model.bkp")
    parser.connections_data = {}
    if inlet_power is not None:
        for port, stream, power in (("WS(IN)", "W1", inlet_power), ("WS(OUT)", "E1", inlet_power * factor)):
            nodes[rf"\Data\Blocks\M1\Ports\{port}"] = DummyNode(port)
            nodes[rf"\Data\Blocks\M1\Ports\{port}"].Elements = DummyCollection([DummyNode(stream)])
            parser.connections_data[stream] = {
                "kind": "power",
                "energy_flow": abs(power),
                "_aspen_power_sign": 1 if power >= 0 else -1,
            }
    parser.aspen = DummyAspen(DummyTree(nodes))
    return parser


def parsed_mult_block(parser):
    parser.parse_blocks()
    return next(comp for group in parser.components_data.values() for name, comp in group.items() if name == "M1")


@pytest.mark.parametrize(
    "factor, inlet_power, block_type",
    [(1.0, -30e6, "Generator"), (0.985, -2.5e8, "Generator"), (1.015, 7e5, "Motor"), (1.0, 7e5, "Motor")],
)
def test_mult_block_type_from_power_sign(factor, inlet_power, block_type, caplog):
    """
    Test that the sign of the inlet power decides whether a multiplier block is a generator or a motor.

    The first three cases are those of the examples: the CGAM generator with the factor 1, the CCPP
    generators and the heat pump motors.
    """
    comp = parsed_mult_block(mult_block_parser(factor, inlet_power))

    assert comp["type"] == block_type
    if block_type == "Generator":
        assert comp["eta_el"] == pytest.approx(factor)
    else:
        assert comp["eta_el"] == pytest.approx(1 / factor)
        assert comp["P_mech"] == pytest.approx(abs(inlet_power))
        assert comp["P_el"] == pytest.approx(abs(inlet_power) * factor)
    assert caplog.text == ""


def test_mult_block_factor_contradicts_power_sign(caplog):
    """
    Test the warning for a multiplier block on consumed power whose factor gives an efficiency above 1.
    """
    comp = parsed_mult_block(mult_block_parser(0.985, 7e5))

    assert comp["type"] == "Motor"
    assert "efficiency above 1" in caplog.text


@pytest.mark.parametrize("factor, block_type", [(0.985, "Generator"), (1.015, "Motor"), (1.0, "Generator")])
def test_mult_block_type_without_inlet_power(factor, block_type, caplog):
    """
    Test that the factor decides for a multiplier block without work streams, and a factor of 1 gives a warning.
    """
    comp = parsed_mult_block(mult_block_parser(factor))

    assert comp["type"] == block_type
    assert ("taken as a generator" in caplog.text) == (factor == 1.0)


# --- Integration Test for parse_model ---


@pytest.mark.parametrize("split", [True, False])
def test_parse_model_integration(dummy_convert_to_SI, split):
    """
    Test the full parse_model function integration.

    This test simulates an Aspen tree that includes ambient conditions, streams, and blocks.
    Verifies that parse_model correctly calls ambient, stream, and block parsing, and splits
    the physical exergy only if asked to.
    """
    nodes = {
        r"\Data\Setup\Sim-Options\Input\REF_TEMP": DummyNode("REF_TEMP", 290, "K"),
        r"\Data\Setup\Sim-Options\Input\REF_PRES": DummyNode("REF_PRES", 100000, "Pa"),
    }
    stream = DummyNode("StreamX")
    streams_parent = DummyNode("Streams")
    streams_parent.Elements = DummyCollection([stream])
    nodes[r"\Data\Streams"] = streams_parent
    nodes[r"\Data\Streams\StreamX"] = DummyNode("StreamX")
    nodes[r"\Data\Streams\StreamX\Input\WORK"] = DummyNode("WORK")
    nodes[r"\Data\Streams\StreamX\Output\POWER_OUT"] = DummyNode("POWER_OUT", 150, "W")
    blocks_parent = DummyNode("Blocks")
    blocks_parent.Elements = DummyCollection([])
    nodes[r"\Data\Blocks"] = blocks_parent

    tree = DummyTree(nodes)
    dummy_aspen = DummyAspen(tree)
    parser = AspenModelParser("dummy_model.apw", split_physical_exergy=split)
    parser.aspen = dummy_aspen

    with patch.object(AspenModelParser, "split_physical_exergy_of_streams") as split_streams:
        parser.parse_model()

    assert split_streams.called == split

    assert parser.Tamb == 290
    assert parser.pamb == 100000
    assert "StreamX" in parser.connections_data


# --- Tests for the ambient state passed to the parser ---

REF_TEMP = r"\Data\Setup\Sim-Options\Input\REF_TEMP"
REF_PRES = r"\Data\Setup\Sim-Options\Input\REF_PRES"


@pytest.mark.parametrize(
    "Tamb, pamb, runs, ref_temp, ref_pres",
    [
        (None, None, 0, 25.0, 1.013),
        (298.15, 101300.0, 0, 25.0, 1.013),
        (288.15, None, 1, 15.0, 1.013),
        (None, 1e5, 1, 25.0, 1.0),
    ],
)
def test_set_ambient_conditions(Tamb, pamb, runs, ref_temp, ref_pres):
    """
    Test that a passed ambient state replaces REF_TEMP and REF_PRES, in their units, and that the model is run
    again so that Aspen computes the exergies at it, unless the model holds this state already.
    """
    nodes = {REF_TEMP: DummyNode("REF_TEMP", 25.0, "C"), REF_PRES: DummyNode("REF_PRES", 1.013, "bar")}
    aspen = DummyAspen(DummyTree(nodes))
    aspen.Engine = Mock()
    parser = AspenModelParser("dummy_model.bkp", Tamb=Tamb, pamb=pamb)
    parser.aspen = aspen

    parser.set_ambient_conditions()
    parser.parse_ambient_conditions()

    assert nodes[REF_TEMP].Value == pytest.approx(ref_temp)
    assert nodes[REF_PRES].Value == pytest.approx(ref_pres)
    assert aspen.Engine.Run2.call_count == runs
    assert parser.Tamb == pytest.approx(ref_temp + 273.15)
    assert parser.pamb == pytest.approx(ref_pres * 1e5)


def test_set_ambient_conditions_without_node():
    """
    Test that a passed ambient state the model has no node for raises an error.
    """
    parser = AspenModelParser("dummy_model.bkp", Tamb=288.15)
    parser.aspen = DummyAspen(DummyTree({}))

    with pytest.raises(ValueError, match="REF_TEMP"):
        parser.set_ambient_conditions()


# --- Tests for the split of the physical exergy ---


class DummyRows(DummyCollection):
    """Rows of an Aspen folder or list node, with the methods the parser calls to add objects and rows."""

    def Add(self, name):
        self.append(DummyNode(name.split("!")[0]))

    def InsertRow(self, dimension, index):
        self.insert(index, DummyNode())

    def SetLabel(self, dimension, index, flag, label):
        self[index].Name = label

    def Item(self, index):
        return self[index]


class DummyModel:
    """
    Aspen model whose engine evaluates the Generic property analyses the parser adds.

    Each stream's fluid has h = h0 + cp * (T - 300 K) and s = s0 + cp * ln(T / 300 K) at every pressure.

    Parameters
    ----------
    nodes : dict
        Nodes of the model tree; the input nodes of the added prop-set and analyses are created on access.
    fluids : dict
        h0 in kJ/kmol, s0 and cp in kJ/kmol-K of each stream.
    pres_unit : str
        Unit of the pressure input of an analysis.
    """

    def __init__(self, nodes, fluids, pres_unit):
        self.nodes = nodes
        self.fluids = fluids
        self.pres_unit = pres_unit
        self.Tree = self
        self.Engine = self
        self.runs = 0

    def FindNode(self, path):
        if path not in self.nodes and r"\EXPY" in path and r"\Input" in path:
            self.nodes[path] = DummyNode(path.rsplit("\\", 1)[-1], unit=self.pres_unit if path.endswith("PRES") else "")
            self.nodes[path].Elements = DummyRows()
        return self.nodes.get(path)

    def Run2(self):
        self.runs += 1
        for analysis in self.nodes[r"\Data\Properties\Analysis"].Elements:
            base = rf"\Data\Properties\Analysis\{analysis.Name}"
            stream = self.FindNode(base + r"\Input\SID").Value
            if stream is None:
                continue
            h0, s0, cp = self.fluids[stream]
            out = base + r"\Output\PROP_DATA"
            for row, item in enumerate(self.FindNode(base + r"\Input\LIST\#0").Elements, start=1):
                T = item.Value
                self.nodes[out + rf"\TEMP\{row}"] = DummyNode(str(row), T, "K")
                self.nodes[out + rf"\HMX\TOTAL\{row}"] = DummyNode(str(row), h0 + cp * (T - 300.0), "kJ/kmol")
                self.nodes[out + rf"\SMX\TOTAL\{row}"] = DummyNode(str(row), s0 + cp * math.log(T / 300.0), "kJ/kmol-K")


# S1 at 400 K: h0 = 1800 kJ/kmol / 18 kg/kmol = 100 kJ/kg, s0 = 6.3 kJ/kmol-K / 18 kg/kmol = 350 J/kgK, cp = 1 kJ/kgK
H_S1 = 100e3 + 1e3 * (400.0 - 300.0)
S_S1 = 350.0 + 1e3 * math.log(400.0 / 300.0)


def split_model(pres_unit="bar", analyses=(), ref_temp=(300.0, "K"), h=H_S1, T=400.0):
    """A parser with one material stream S1 and one power stream, and its Aspen model."""
    prop_sets = DummyNode("Prop-Sets")
    prop_sets.Elements = DummyRows()
    folder = DummyNode("Analysis")
    folder.Elements = DummyRows(DummyNode(name) for name in analyses)
    nodes = {
        r"\Data\Properties\Prop-Sets": prop_sets,
        r"\Data\Properties\Analysis": folder,
        r"\Data\Setup\Sim-Options\Input\REF_TEMP": DummyNode("REF_TEMP", *ref_temp),
        r"\Data\Streams\S1\Output\PRES_OUT\MIXED": DummyNode("PRES_OUT", 2.0, "bar"),
        r"\Data\Streams\S1\Output\MW": DummyNode("MW", 18.0),
    }
    model = DummyModel(nodes, {"S1": (1800.0, 6.3, 18.0)}, pres_unit)
    parser = AspenModelParser("dummy_model.bkp")
    parser.aspen = model
    parser.Tamb = 300.0
    parser.connections_data = {
        "S1": {"kind": "material", "T": T, "p": 2e5, "h": h, "s": S_S1, "e_PH": 100e3},
        "W1": {"kind": "power", "energy_flow": 1e3},
    }
    return parser, model


@pytest.mark.parametrize("pres_unit, pres", [("bar", 2.0), ("kPa", 200.0)])
def test_split_physical_exergy(pres_unit, pres, caplog):
    """
    Test the split of the physical exergy with a Generic analysis per material stream.

    Verifies
    --------
    - e_T = h - h(T0, p) - T0 * (s - s(T0, p)) from the analysis' molar results, and e_M = e_PH - e_T.
    - The prop-set and the analysis get IDs that the model does not use yet.
    - The analysis evaluates the stream at its pressure, in the unit of the pressure input, at T0 and just
      below and above the stream's temperature, and the stream passes this check.
    """
    parser, model = split_model(pres_unit, analyses=["EXPY1"])

    parser.split_physical_exergy_of_streams()

    conn = parser.connections_data["S1"]
    assert conn["e_T"] == pytest.approx(H_S1 - 100e3 - 300.0 * (S_S1 - 350.0))
    assert conn["e_M"] == pytest.approx(100e3 - conn["e_T"])
    assert conn["e_T_unit"] == conn["e_M_unit"] == "J / kg"
    assert "e_T" not in parser.connections_data["W1"]
    assert model.runs == 1
    assert "may be wrong" not in caplog.text

    prop_set = r"\Data\Properties\Prop-Sets\EXPYHS1\Input"
    assert [row.Name for row in model.nodes[prop_set + r"\UNITS"].Elements] == ["HMX", "SMX"]
    assert model.nodes[prop_set + r"\PHASE"].Elements.Item(0).Value == "T"
    analysis = r"\Data\Properties\Analysis\EXPY2\Input"
    assert model.nodes[analysis + r"\OPT_COMP"].Value == "STREAM"
    assert model.nodes[analysis + r"\SID"].Value == "S1"
    assert model.nodes[analysis + r"\VARNAME"].Elements.Item(0).Value == "TEMP"
    temperatures = [row.Value for row in model.nodes[analysis + r"\LIST\#0"].Elements]
    assert temperatures == pytest.approx([300.0, 400.0 - STATE_CHECK_STEP, 400.0 + STATE_CHECK_STEP])
    assert model.nodes[analysis + r"\PRES"].Value == pytest.approx(pres)
    assert model.nodes[analysis + r"\PROPERTIES"].Elements.Item(0).Value == "EXPYHS1"


def test_split_physical_exergy_state_not_reproduced(caplog):
    """
    Test the warning for a stream whose enthalpy the property data of the split do not reproduce.
    """
    parser, _ = split_model(h=H_S1 + 1e3)

    parser.split_physical_exergy_of_streams()

    assert "The thermal and mechanical exergy of stream S1 may be wrong" in caplog.text
    assert "e_T" in parser.connections_data["S1"]


def test_split_physical_exergy_without_temperature(caplog):
    """
    Test that a stream without a temperature is evaluated at T0 only and not checked.
    """
    parser, model = split_model(T=None)

    parser.split_physical_exergy_of_streams()

    assert len(model.nodes[r"\Data\Properties\Analysis\EXPY1\Input\LIST\#0"].Elements) == 1
    assert "e_T" in parser.connections_data["S1"]
    assert "may be wrong" not in caplog.text


def test_split_physical_exergy_wrong_temperature(caplog):
    """
    Test that a stream evaluated at another temperature than T0 gets no thermal and mechanical exergy.

    The temperature list of an analysis takes REF_TEMP's value; here Aspen reads it in another unit.
    """
    parser, _ = split_model(ref_temp=(26.85, "C"))

    parser.split_physical_exergy_of_streams()

    assert "e_T" not in parser.connections_data["S1"]
    assert "instead of Tamb" in caplog.text


def test_split_physical_exergy_engine_error(caplog):
    """
    Test that a failing engine run leaves the streams without split and logs the reason.
    """
    parser, model = split_model()
    model.Run2 = Mock(side_effect=RuntimeError("no license"))

    parser.split_physical_exergy_of_streams()

    assert "e_T" not in parser.connections_data["S1"]
    assert "could not be split: no license" in caplog.text


# --- run_aspen Tests ---


def test_run_aspen_file_not_found(tmp_path):
    """
    Test error handling in run_aspen when the model file is not found.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path provided by pytest.

    Verifies
    --------
    - FileNotFoundError is raised with an appropriate error message.
    """
    with patch("os.path.exists", return_value=False), pytest.raises(FileNotFoundError, match="Model file not found"):
        run_aspen("nonexistent.apw", str(tmp_path / "output.json"))
