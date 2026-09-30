from tespy.connections import Connection
from tespy.connections import PowerConnection
from tespy.networks import Network

from exerpy.logger import logger
from exerpy.parser.from_tespy.tespy_config import EXERPY_TESPY_MAPPINGS


def to_exerpy(nw: Network, Tamb: float, pamb: float) -> dict:
    """Export the network to exerpy

    Parameters
    ----------
    nw : tespy.networks.network.Network
        Network to ber parsed
    Tamb : float
        Ambient temperature.
    pamb : float
        Ambient pressure.

    Returns
    -------
    dict
        exerpy compatible input dictionary
    """
    component_results = nw._save_components()
    component_json = {}
    for comp_type in nw.comps["comp_type"].unique():
        if comp_type not in EXERPY_TESPY_MAPPINGS:
            continue

        key = EXERPY_TESPY_MAPPINGS[comp_type]
        if key not in component_json:
            component_json[key] = {}

        result = component_results[comp_type].dropna(axis=1)

        for c in nw.comps.loc[nw.comps["comp_type"] == comp_type, "object"]:
            parameters = {}
            if c.label in result.index and not result.loc[c.label].dropna().empty:
                parameters = result.loc[c.label].dropna().to_dict()
            component = {"name": c.label, "type": comp_type, "parameters": parameters}
            if key == "ParabolicTrough":
                component["Q_Solar"] = _incident_radiation(c)
                component["num_branches"] = 1
            component_json[key][c.label] = component

    connection_json = {}
    for c in nw.conns["object"]:
        if isinstance(c, Connection):
            connection_json.update(_connection_to_exerpy(c, pamb, Tamb))
        else:
            connection_json.update(_powerconnection_to_exerpy(c, pamb, Tamb))

    connection_json.update(_solar_heat_to_exerpy(component_json.get("ParabolicTrough", {})))

    return {
        "components": component_json,
        "connections": connection_json,
        "ambient_conditions": {"Tamb": Tamb, "Tamb_unit": "K", "pamb": pamb, "pamb_unit": "Pa"},
    }


def _connection_to_exerpy(c: Connection, pamb: float, Tamb: float) -> dict:
    """Serialize a tespy Connection to exerpy

    Parameters
    ----------
    c : tespy.connections.connection.Connection
        Connection object
    Tamb : float
        Ambient temperature.
    pamb : float
        Ambient pressure.

    Returns
    -------
    dict
        Serialization of connection data
    """
    connection_json = {}

    c._get_physical_exergy(pamb, Tamb)

    connection_json[c.label] = {
        "source_component": c.source.label,
        "source_connector": int(c.source_id.removeprefix("out")) - 1,
        "target_component": c.target.label,
        "target_connector": int(c.target_id.removeprefix("in")) - 1,
    }
    connection_json[c.label].update({"mass_composition": c.fluid.val})
    connection_json[c.label].update({"kind": "material"})
    for param in ["m", "T", "p", "h", "s", "v"]:
        connection_json[c.label].update({param: c.get_attr(param).val_SI})
    connection_json[c.label].update({"e_T": c.ex_therm, "e_M": c.ex_mech, "e_PH": c.ex_physical})

    return connection_json


def _powerconnection_to_exerpy(c: PowerConnection, pamb: float, Tamb: float) -> dict:
    """Serialize a tespy PowerConnection to exerpy

    Parameters
    ----------
    c : tespy.connections.powerconnection.PowerConnection
        Connection object
    Tamb : float
        Ambient temperature.
    pamb : float
        Ambient pressure.

    Returns
    -------
    dict
        Serialization of connection data
    """
    connection_json = {}

    if c.source.__class__.__name__ in ["Motor", "Generator"]:
        source_connector = 0
    elif c.source.__class__.__name__ in ["Turbine"] or c.source.__class__.__name__ in ["SimpleHeatExchanger"]:
        source_connector = 1
    elif c.source.__class__.__name__ in ["PowerBus"]:
        if c.source_id.startswith("power_out"):
            s_id = c.source_id.removeprefix("power_out")
            source_connector = 0 if s_id == "" else int(s_id) - 1
        elif c.source_id.startswith("power_in"):
            s_id = c.source_id.removeprefix("power_in")
            source_connector = 0 if s_id == "" else int(s_id) - 1
    else:
        source_connector = 999

    if c.target.__class__.__name__ in ["Motor", "Generator"]:
        target_connector = 0
    elif c.target.__class__.__name__ in ["Compressor", "Pump"] or c.target.__class__.__name__ in [
        "SimpleHeatExchanger"
    ]:
        target_connector = 1
    elif c.target.__class__.__name__ in ["PowerBus"]:
        if c.target_id.startswith("power_in"):
            t_id = c.target_id.removeprefix("power_in")
            target_connector = 0 if t_id == "" else int(t_id) - 1
        elif c.target_id.startswith("power_out"):
            t_id = c.target_id.removeprefix("power_out")
            target_connector = 0 if t_id == "" else int(t_id) - 1
    else:
        target_connector = 999

    connection_json[c.label] = {
        "source_component": c.source.label,
        "source_connector": source_connector,
        "target_component": c.target.label,
        "target_connector": target_connector,
    }
    kind = "heat" if c.source_id == "heat" or c.target_id == "heat" else "power"

    connection_json[c.label].update({"kind": kind, "energy_flow": c.E.val_SI})

    return connection_json


def _incident_radiation(c) -> float:
    """Return the solar radiation incident on the aperture of a collector in W.

    The exergy fuel of a concentrating collector is the incoming radiation, not the heat it
    transfers to the fluid, so the optical and thermal losses show up as exergy destruction.
    """
    if c.E.is_set and c.A.is_set:
        return c.E.val_SI * c.A.val_SI

    msg = (
        f"Collector '{c.label}' specifies neither its irradiance E nor its aperture area A, so "
        f"the incoming solar radiation is unknown and its heat transfer Q is used instead. The "
        f"optical and thermal losses are then missing from the exergy destruction."
    )
    logger.warning(msg)
    return c.Q.val_SI


def _solar_heat_to_exerpy(collectors: dict) -> dict:
    """Serialize the incoming solar radiation of every collector as a heat connection.

    The radiation crosses the system boundary without a connection of its own in TESPy. Naming
    it after the collector with a "_Q" suffix matches the other parsers, so the same fuel
    definition works whichever simulator the model comes from.
    """
    connection_json = {}
    for label, component in collectors.items():
        connection_json[f"{label}_Q"] = {
            "name": f"{label}_Q",
            "kind": "heat",
            "source_component": None,
            "target_component": label,
            "source_component_type": None,
            "target_component_type": component["type"],
            "source_connector": None,
            "target_connector": None,
            "energy_flow": component["Q_Solar"] * component["num_branches"],
            "energy_flow_unit": "W",
            "E": None,
            "E_unit": "W",
            "num_branches": component["num_branches"],
        }
    return connection_json
