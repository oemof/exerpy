import json
import math
import os

import CoolProp.CoolProp as CP

from exerpy import __datapath__
from exerpy.logger import logger
from exerpy.units import SI_UNITS


def mass_to_molar_fractions(mass_fractions):
    """
    Convert mass fractions to molar fractions.

    Parameters:
    - mass_fractions: Dictionary with component names as keys and mass fractions as values.

    Returns:
    - molar_fractions: Dictionary with component names as keys and molar fractions as values.
    """
    molar_fractions = {}

    if len(mass_fractions.values()) == 1:
        molar_fractions = {comp: 1.0 for comp in mass_fractions}

    else:
        molar_masses = {}

        # Step 1: Get the molar masses for each component
        for fraction in mass_fractions:
            try:
                molar_masses[fraction] = CP.PropsSI("M", fraction)
            except Exception:
                #  print(f"Warning: Could not retrieve molar mass for {fraction} ({fraction}). Error: {e}")
                continue  # Skip this fraction if there's an issue

        # Step 2: Check if we have valid molar masses
        if not molar_masses:
            raise ValueError(f"No valid molar masses were retrieved for substances {list(mass_fractions.keys())}")

        else:

            # Step 3: Calculate total moles in the mixture
            total_moles = sum(mass_fractions[comp] / molar_masses[comp] for comp in molar_masses)

            # Step 4: Calculate molar fractions
            for component in molar_masses:
                molar_fractions[component] = (mass_fractions[component] / molar_masses[component]) / total_moles

            # Step 5: Check if molar fractions sum to approximately 1
            molar_sum = sum(molar_fractions.values())
            if abs(molar_sum - 1.0) > 1e-6:
                raise ValueError(f"Error: Molar fractions do not sum to 1. Sum is {molar_sum}")

    return molar_fractions


def molar_to_mass_fractions(molar_fractions):
    """
    Convert molar fractions to mass fractions.

    Parameters:
    - molar_fractions: Dictionary with component names as keys and molar fractions as values.

    Returns:
    - mass_fractions: Dictionary with component names as keys and mass fractions as values.
    """
    molar_masses = {}
    mass_fractions = {}

    # Step 1: Get the molar masses for each component
    for fraction in molar_fractions:
        try:
            molar_masses[fraction] = CP.PropsSI("M", fraction)
        except Exception:
            # print(f"Warning: Could not retrieve molar mass for {fraction} ({fraction}). Error: {e}")
            continue  # Skip this fraction if there's an issue

    # Step 2: Check if we have valid molar masses
    if not molar_masses:
        raise ValueError("No valid molar masses were retrieved. Exiting...")

    # Step 3: Calculate total mass in the mixture
    total_mass = sum(molar_fractions[comp] * molar_masses[comp] for comp in molar_masses)

    # Step 4: Calculate mass fractions
    for component in molar_masses:
        mass_fractions[component] = (molar_fractions[component] * molar_masses[component]) / total_mass

    # Step 5: Check if mass fractions sum to approximately 1
    mass_sum = sum(mass_fractions.values())
    if abs(mass_sum - 1.0) > 1e-6:
        raise ValueError(f"Error: Mass fractions do not sum to 1. Sum is {mass_sum}")

    return mass_fractions


def _library_entry(substance, chem_ex_data):
    """Return the entry of a substance in the chemical exergy library, or None if it has no value."""
    try:
        aliases = CP.get_aliases(substance)
    except ValueError:
        aliases = [substance]
    for alias in aliases:
        entry = chem_ex_data.get(alias.upper())
        if entry is not None:
            return None if entry[4] == "NaN" else entry
    return None


def calc_chemical_exergy(stream_data, Tamb, pamb, chemExLib):
    r"""
    Calculate the specific chemical exergy of a stream.

    A pure substance gets the value of its reference phase. A pure substance without a value in the
    library gets 0, which is only valid if it does not react. A mixture is an ideal gas mixture. If
    water condenses at the ambient state, the liquid water forms a separate phase
    (Bejan et al., 1996, p. 138):

    .. math::

        \bar{e}^\mathrm{CH} = x_\mathrm{g} \left( \sum_k y_k \bar{e}^\mathrm{CH}_k
        + \bar{R} T_0 \sum_k y_k \ln y_k \right)
        + x_\mathrm{H_2O,l} \, \bar{e}^\mathrm{CH}_\mathrm{H_2O,l}

    with the molar fraction of the gas phase :math:`x_\mathrm{g}` and the molar fractions
    :math:`y_k` within the gas phase.

    Parameters
    ----------
    stream_data : dict
        ``molar_composition`` or ``mass_composition`` of the stream.
    Tamb : float
        Ambient temperature in K.
    pamb : float
        Ambient pressure in Pa.
    chemExLib : str
        Name of the chemical exergy library, e.g. ``'Ahrendts'``.

    Returns
    -------
    float
        Specific chemical exergy in J/kg.

    Raises
    ------
    ValueError
        If the library has no value for a substance of a mixture.
    """
    logger.info(f"Calculating the chemical exergy of {stream_data} at Tamb={Tamb} K and pamb={pamb} Pa")

    try:
        if "molar_composition" in stream_data:
            molar_fractions = stream_data["molar_composition"]
        else:
            molar_fractions = mass_to_molar_fractions(stream_data["mass_composition"])
        try:
            chem_ex_file = os.path.join(__datapath__, f"{chemExLib}.json")
            with open(chem_ex_file) as file:
                chem_ex_data = json.load(file)  # in J/mol
        except FileNotFoundError:
            error_msg = f"Chemical exergy data file '{chemExLib}.json' not found. Please ensure the file exists or set chemExLib to 'Ahrendts'."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        R = 8.314  # in J/(mol K)
        molar_fractions = {key: value for key, value in molar_fractions.items() if value > 1e-6}

        if len(molar_fractions) == 1:
            substance = next(iter(molar_fractions))
            entry = _library_entry(substance, chem_ex_data)
            if entry is None:
                logger.warning(
                    f"{chemExLib} has no chemical exergy for {substance}. It is set to 0, which is only valid "
                    f"if {substance} does not react."
                )
                return 0.0
            eCH = entry[entry[4]] / CP.PropsSI("M", substance)
            logger.info(f"Chemical exergy of pure {substance}: {eCH} J/kg")
            return eCH

        eCH_gas = {}  # in J/mol
        for substance in molar_fractions:
            entry = _library_entry(substance, chem_ex_data)
            if entry is None or entry[3] == "NaN":
                error_msg = f"{chemExLib} has no chemical exergy for {substance} in the gas phase."
                logger.error(error_msg)
                raise ValueError(error_msg)
            eCH_gas[substance] = entry[3]

        molar_mass = sum(x * CP.PropsSI("M", substance) for substance, x in molar_fractions.items())  # in kg/mol

        gas_fractions = dict(molar_fractions)
        x_gas = 1
        eCH_liquid_mol = 0
        aliases_water = CP.get_aliases("H2O")
        water = next((substance for substance in molar_fractions if substance in aliases_water), None)
        if water is not None:
            pH2O_sat = CP.PropsSI("P", "T", Tamb, "Q", 1, "Water")
            if molar_fractions[water] * pamb > pH2O_sat:
                x_dry = sum(x for substance, x in molar_fractions.items() if substance != water)
                x_H2O_gas = x_dry / (pamb / pH2O_sat - 1)
                x_H2O_liquid = molar_fractions[water] - x_H2O_gas
                x_gas = 1 - x_H2O_liquid
                gas_fractions[water] = x_H2O_gas
                eCH_liquid_mol = x_H2O_liquid * chem_ex_data["WATER"][2]
                logger.info(f"Water condenses: {x_H2O_liquid} mol of liquid per mol of mixture")

        y = {substance: x / x_gas for substance, x in gas_fractions.items()}
        eCH_gas_mol = sum(y[substance] * eCH_gas[substance] for substance in y)
        eCH_gas_mol += R * Tamb * sum(y_k * math.log(y_k) for y_k in y.values() if y_k > 0)
        eCH = (x_gas * eCH_gas_mol + eCH_liquid_mol) / molar_mass
        logger.info(f"Chemical exergy of the mixture: {eCH} J/kg")
        return eCH

    except Exception as e:
        logger.error(f"Error in calc_chemical_exergy: {e}")
        raise


def add_chemical_exergy(my_json, Tamb, pamb, chemExLib):
    """
    Adds the chemical exergy to each connection in the JSON data, prioritizing molar composition if available.

    Parameters:
    - my_json: The JSON object containing the components and connections.
    - Tamb: Ambient temperature in K.
    - pamb: Ambient pressure in Pa.

    Returns:
    - The modified JSON object with added chemical exergy for each connection.
    """
    # Check if Tamb and pamb are provided and not None
    if Tamb is None or pamb is None:
        raise ValueError(
            "Ambient temperature (Tamb) and pressure (pamb) are required for chemical exergy calculation. "
            "Please ensure they are included in the JSON or passed as arguments."
        )

    # Iterate over each material connection with kind == 'material'
    for conn_name, conn_data in my_json["connections"].items():
        if conn_data["kind"] == "material":
            # Prefer molar composition if available, otherwise use mass composition
            molar_composition = conn_data.get("molar_composition", {})
            mass_composition = conn_data.get("mass_composition", {})

            # Prepare stream data for exergy calculation, prioritizing molar composition
            if molar_composition:
                stream_data = {"molar_composition": molar_composition}
                logger.info(f"Using molar composition for connection {conn_name}")
            elif mass_composition:
                stream_data = {"mass_composition": mass_composition}
                logger.info(f"Using mass composition for connection {conn_name}")
            else:
                # Like a substance without a value in the library.
                logger.warning(
                    f"Connection {conn_name} has no composition. Its chemical exergy is set to 0, which is only "
                    "valid if it does not react."
                )
                conn_data["e_CH"] = 0.0
                conn_data["e_CH_unit"] = SI_UNITS["e_CH"]
                continue

            # Add the chemical exergy value
            conn_data["e_CH"] = calc_chemical_exergy(stream_data, Tamb, pamb, chemExLib)
            conn_data["e_CH_unit"] = SI_UNITS["e_CH"]
            logger.info(f"Added chemical exergy to connection {conn_name}: {conn_data['e_CH']} J/kg")
        else:
            logger.info(
                f"Skipped chemical exergy calculation for non-material connection {conn_name} ({conn_data['kind']})"
            )

    return my_json


def add_total_exergy_flow(my_json, split_physical_exergy):
    r"""
    Adds the total exergy flow to each connection in the JSON data based on its kind.

    - For 'material' connections, the exergy is calculated as before.
    - For 'power' connections, the energy flow value is used directly.
    - For 'heat' connections, if the associated component is of class
      SimpleHeatExchanger, the thermal exergy difference is computed as:

      .. math::

          E = (e^\mathrm{T}_\mathrm{in} \cdot \dot m_\mathrm{in})
          - (e^\mathrm{T}_\mathrm{out} \cdot \dot m_\mathrm{out})

    Otherwise, a warning is logged and E is set to None.

    Parameters
    ----------
    my_json : dict
        The JSON object containing the components and connections.
    split_physical_exergy : bool
        Split physical exergy in mechanical and thermal shares.

    Returns
    -------
    dict
        The modified JSON object with added total exergy flow for each
        connection.
    """
    for conn_name, conn_data in my_json["connections"].items():
        try:
            if conn_data["kind"] == "material":
                # For material connections: E = m * (e^PH + e^CH)
                conn_data["E_PH"] = conn_data["m"] * conn_data["e_PH"]
                if conn_data.get("e_CH") is not None:
                    conn_data["E_CH"] = conn_data["m"] * conn_data["e_CH"]
                    conn_data["E"] = conn_data["E_PH"] + conn_data["E_CH"]
                else:
                    conn_data["E"] = conn_data["E_PH"]
                    logger.info(f"Missing chemical exergy for connection {conn_name}. Using only physical exergy.")
                if split_physical_exergy:
                    if conn_data.get("e_T") is not None:
                        conn_data["E_T"] = conn_data["m"] * conn_data["e_T"]
                    else:
                        msg = f"Missing thermal exergy for connection {conn_name}."
                        logger.error(msg)
                        raise KeyError(msg)
                    if conn_data.get("e_M") is not None:
                        conn_data["E_M"] = conn_data["m"] * conn_data["e_M"]
                    else:
                        msg = f"Missing mechanical exergy for connection {conn_name}."
                        logger.error(msg)
                        raise KeyError(msg)
            elif conn_data["kind"] == "power":
                # For power connections, use the energy flow value directly.
                conn_data["E"] = conn_data["energy_flow"]
            elif conn_data["kind"] == "heat":
                # For heat connections, find the heat exchanger component on either end.
                # The other end is typically a HeatSource/HeatSink which is not in our component dict.
                source_component = conn_data["source_component"]
                target_component = conn_data["target_component"]
                she_comps = my_json["components"].get("SimpleHeatExchanger", {})
                comp_name = source_component if source_component in she_comps else target_component
                # Check if the component is either a SimpleHeatExchanger or a SteamGenerator.
                if (
                    "SimpleHeatExchanger" in my_json["components"]
                    and comp_name in my_json["components"]["SimpleHeatExchanger"]
                ):
                    # Retrieve the inlet material streams: those with this component as target.
                    inlet_conns = [
                        c
                        for c in my_json["connections"].values()
                        if c.get("target_component") == comp_name and c.get("kind") == "material"
                    ]
                    # Retrieve the outlet material streams: those with this component as source.
                    outlet_conns = [
                        c
                        for c in my_json["connections"].values()
                        if c.get("source_component") == comp_name and c.get("kind") == "material"
                    ]
                    # Determine which exergy key to use based on the flag.
                    exergy_key = "e_T" if split_physical_exergy else "e_PH"

                    if inlet_conns and outlet_conns:
                        # For simplicity, take the first inlet and first outlet.
                        inlet = inlet_conns[0]
                        outlet = outlet_conns[0]
                        # Calculate the heat exergy difference using the selected key:
                        conn_data["E"] = abs(
                            inlet.get(exergy_key, 0) * inlet.get("m", 0)
                            - outlet.get(exergy_key, 0) * outlet.get("m", 0)
                        )
                    else:
                        conn_data["E"] = None
                        logger.warning(
                            f"Not enough material connections for heat exchanger {comp_name} for heat exergy calculation."
                        )
                elif "SteamGenerator" in my_json["components"] and comp_name in my_json["components"]["SteamGenerator"]:
                    # Retrieve material connections for the steam generator.
                    inlet_conns = [
                        c
                        for c in my_json["connections"].values()
                        if c.get("target_component") == comp_name and c.get("kind") == "material"
                    ]
                    outlet_conns = [
                        c
                        for c in my_json["connections"].values()
                        if c.get("source_component") == comp_name and c.get("kind") == "material"
                    ]
                    if inlet_conns and outlet_conns:
                        # For the steam generator, group the material connections as follows:
                        feed_water = inlet_conns[0]  # inl[0]: Feed water inlet (HP)
                        steam_inlet = inlet_conns[1] if len(inlet_conns) > 1 else {}  # inl[1]: Steam inlet (IP)
                        superheated_HP = outlet_conns[0]  # outl[0]: Superheated steam outlet (HP)
                        superheated_IP = (
                            outlet_conns[1] if len(outlet_conns) > 1 else {}
                        )  # outl[1]: Superheated steam outlet (IP)
                        water_inj_HP = inlet_conns[2] if len(inlet_conns) > 2 else {}  # inl[2]: Water injection (HP)
                        water_inj_IP = inlet_conns[3] if len(inlet_conns) > 3 else {}  # inl[3]: Water injection (IP)

                        exergy_type = "e_T" if split_physical_exergy else "e_PH"
                        # Calculate the contributions based on the new E_F definition:
                        E_F_HP = superheated_HP.get("m", 0) * superheated_HP.get(exergy_type, 0) - feed_water.get(
                            "m", 0
                        ) * feed_water.get(exergy_type, 0)
                        E_F_IP = superheated_IP.get("m", 0) * superheated_IP.get(exergy_type, 0) - steam_inlet.get(
                            "m", 0
                        ) * steam_inlet.get(exergy_type, 0)
                        E_F_w_inj = water_inj_HP.get("m", 0) * water_inj_HP.get(exergy_type, 0) + water_inj_IP.get(
                            "m", 0
                        ) * water_inj_IP.get(exergy_type, 0)
                        # Total exergy flow for the heat input (E_TOT) is taken as the exergy fuel E_F:
                        E_TOT = E_F_HP + E_F_IP - E_F_w_inj
                        conn_data["E"] = E_TOT
                    else:
                        conn_data["E"] = None
                        logger.warning(
                            f"Not enough material connections for steam generator {comp_name} for heat exergy calculation."
                        )
                else:
                    conn_data["E"] = None
                    # Solar-thermal components compute the exergy of their own heat
                    # connections during the exergy balance, so they are not heat
                    # exchangers and must not trigger this warning.
                    solar_comps = set()
                    for solar_type in ("Heliostatfield", "SolarTower", "ParabolicTrough"):
                        solar_comps.update(my_json["components"].get(solar_type, {}))
                    if source_component not in solar_comps and target_component not in solar_comps:
                        logger.warning(
                            f"Heat connection {conn_name} is not associated with a recognized heat exchanger component."
                        )
            elif conn_data["kind"] == "other":
                # No exergy flow calculation for 'other' kind.
                pass
            else:
                logger.warning(
                    f"Unknown connection kind: {conn_data['kind']} for connection {conn_name}. Skipping exergy flow calculation."
                )
                conn_data["E"] = None

            conn_data["E_unit"] = SI_UNITS["E"]

        except Exception as e:
            logger.error(f"Error calculating total exergy flow for connection {conn_name}: {e}")
            conn_data["E"] = None

    return my_json
