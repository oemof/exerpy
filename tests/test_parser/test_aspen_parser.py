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
- Error handling for a missing model file
"""

import os
import json
import pytest
from unittest.mock import Mock, patch
from exerpy.parser.from_aspen.aspen_parser import AspenModelParser, run_aspen

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
def dummy_convert_to_SI():
    """
    Dummy conversion function to bypass unit conversion complexity.

    Returns
    -------
    function
        A lambda function that returns the numeric value without conversion.
    """
    return lambda phys, value, unit_str: value

@pytest.fixture
def dummy_fluid_property_data():
    """
    Dummy fluid property data for testing.

    Returns
    -------
    dict
        Dictionary mapping fluid property keys to their SI unit representation.
    """
    return {
        'T': {'SI_unit': 'K'},
        'p': {'SI_unit': 'Pa'},
        'h': {'SI_unit': 'J/kg'},
        's': {'SI_unit': 'J/kgK'},
        'm': {'SI_unit': 'kg'},
        'power': {'SI_unit': 'W'},
        'heat': {'SI_unit': 'W'},
        'e': {'SI_unit': 'J'},
        'n': {'SI_unit': 'mol/s'}
    }

# --- Fixture to setup a parser with a dummy Aspen COM object (ambient only) ---

@pytest.fixture
def parser_with_dummy_aspen(dummy_convert_to_SI, dummy_fluid_property_data):
    """
    Fixture that returns an AspenModelParser instance with a dummy Aspen COM object.

    The dummy Aspen object simulates the minimal tree structure required for
    ambient conditions extraction.

    Returns
    -------
    AspenModelParser
        Parser instance with injected dummy Aspen object.
    """
    import exerpy.parser.from_aspen.aspen_parser as ap
    ap.convert_to_SI = dummy_convert_to_SI
    ap.fluid_property_data = dummy_fluid_property_data

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

def test_parse_streams(dummy_convert_to_SI, dummy_fluid_property_data):
    """
    Test the parsing of streams (connections) from the Aspen model.

    Verifies
    --------
    - Power stream: detects WORK input and retrieves POWER_OUT value.
    - Heat stream: detects HEAT input and retrieves QCALC value.
    - Material stream: retrieves temperature, pressure, enthalpy, entropy, mass flow,
      energy flow, exergy, total flow, and fluid composition.
    """
    import exerpy.parser.from_aspen.aspen_parser as ap
    ap.convert_to_SI = dummy_convert_to_SI
    ap.fluid_property_data = dummy_fluid_property_data

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
    assert conn1['kind'] == 'power'
    assert conn1['energy_flow'] == 100
    assert conn1['source_component'] == "CompA"
    assert conn1['target_component'] == "CompB"

    conn2 = parser.connections_data.get("Stream2")
    assert conn2 is not None
    assert conn2['kind'] == 'heat'
    assert conn2['energy_flow'] == 200

    conn3 = parser.connections_data.get("Stream3")
    assert conn3 is not None
    assert conn3['kind'] == 'material'
    assert conn3['T'] == 350
    assert conn3['p'] == 101325
    assert conn3['h'] == 1500
    assert conn3['s'] == 3
    assert conn3['m'] == 5
    assert conn3['energy_flow'] == 250
    assert conn3['e_PH'] == 400
    assert conn3['n'] == 10
    assert conn3['molar_composition'].get("Water") == 0.9
    assert conn3['mass_composition'].get("Water") == 0.8

# --- Tests for parse_blocks and component grouping ---

def test_parse_blocks_and_grouping(dummy_convert_to_SI, dummy_fluid_property_data):
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
    import exerpy.parser.from_aspen.aspen_parser as ap
    ap.convert_to_SI = dummy_convert_to_SI
    ap.fluid_property_data = dummy_fluid_property_data

    # Patch grouped_components and connector_mappings.
    dummy_grouped = {"GroupA": ["Heater", "Pump", "Mult", "Compressor", "Turbine"], "GroupB": ["Other"]}
    dummy_connector_mappings = {}
    ap.grouped_components = dummy_grouped
    ap.connector_mappings = dummy_connector_mappings

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
    dummy_tree = DummyTree({
        r"\Data\Blocks\Mixer1\Ports": mixer_ports,
        r"\Data\Blocks\Mixer1\Ports\InletPort": port1,
        r"\Data\Blocks\Mixer1\Ports\OutletPort": port2,
    })
    dummy_aspen = DummyAspen(dummy_tree)
    connections_data = {
        "StreamIn": {"target_component": "Mixer1"},
        "StreamOut": {"source_component": "Mixer1"}
    }
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
    dummy_tree = DummyTree({
        r"\Data\Blocks\Splitter1\Ports": splitter_ports,
        r"\Data\Blocks\Splitter1\Ports\Inlet": inlet_port,
        r"\Data\Blocks\Splitter1\Ports\Outlet": outlet_port,
    })
    dummy_aspen = DummyAspen(dummy_tree)
    connections_data = {
        "StreamIn": {"target_component": "Splitter1"},
        "StreamOut": {"source_component": "Splitter1"}
    }
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
    dummy_tree = DummyTree({
        r"\Data\Blocks\Combustion1\Ports": ports_node,
        r"\Data\Blocks\Combustion1\Ports\Air(IN)": inlet_port,
        r"\Data\Blocks\Combustion1\Ports\Exhaust(OUT)": outlet_port,
    })
    dummy_aspen = DummyAspen(dummy_tree)
    connections_data = {
        "StreamAir": {"molar_composition": {"O2": 0.2}},
        "StreamExhaust": {}
    }
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
    dummy_tree = DummyTree({
        r"\Data\Blocks\Generic1\Ports\PortX": port_node
    })
    dummy_aspen = DummyAspen(dummy_tree)
    connections_data = {
        "StreamGeneric": {"target_component": "Generic1"}
    }
    parser = AspenModelParser("dummy.apw")
    parser.assign_generic_connectors("Generic1", "GenericType", dummy_aspen, connections_data, dummy_mapping)
    assert connections_data["StreamGeneric"].get("target_connector") == 5

def test_group_component():
    """
    Test the group_component function for proper grouping of components.

    Verifies
    --------
    - The component is stored under the correct group based on its type.
    """
    dummy_grouped = {"GroupA": ["TypeA"], "GroupB": ["TypeB"]}
    import exerpy.parser.from_aspen.aspen_parser as ap
    ap.grouped_components = dummy_grouped
    parser = AspenModelParser("dummy.apw")
    component_data = {"name": "Comp1", "type": "TypeA"}
    parser.group_component(component_data, "Comp1")
    assert "Comp1" in parser.components_data.get("GroupA", {})

# --- Integration Test for parse_model ---

def test_parse_model_integration(dummy_convert_to_SI, dummy_fluid_property_data):
    """
    Test the full parse_model function integration.

    This test simulates an Aspen tree that includes ambient conditions, streams, and blocks.
    Verifies that parse_model correctly calls ambient, stream, and block parsing.
    """
    import exerpy.parser.from_aspen.aspen_parser as ap
    ap.convert_to_SI = dummy_convert_to_SI
    ap.fluid_property_data = dummy_fluid_property_data

    nodes = {
        r"\Data\Setup\Sim-Options\Input\REF_TEMP": DummyNode("REF_TEMP", 290, "K"),
        r"\Data\Setup\Sim-Options\Input\REF_PRES": DummyNode("REF_PRES", 100000, "Pa")
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
    parser = AspenModelParser("dummy_model.apw")
    parser.aspen = dummy_aspen

    parser.parse_model()

    assert parser.Tamb == 290
    assert parser.pamb == 100000
    assert "StreamX" in parser.connections_data

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
    with patch('os.path.exists', return_value=False):
        with pytest.raises(FileNotFoundError, match="Model file not found"):
            run_aspen("nonexistent.apw", str(tmp_path / "output.json"))
