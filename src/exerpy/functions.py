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

    Species with a zero mass fraction are left out. A stream of a single species gets the molar
    fraction 1 without its molar mass.

    Parameters
    ----------
    mass_fractions : dict
        Mass fractions by species name. The names have to be known to CoolProp.

    Returns
    -------
    dict
        Molar fractions by species name.

    Raises
    ------
    ValueError
        If CoolProp has no molar mass for a species with a nonzero mass fraction.
    """
    species = {comp: fraction for comp, fraction in mass_fractions.items() if fraction}

    if not species:
        raise ValueError("The mass composition is empty, so the molar fractions cannot be computed.")
    if len(species) == 1:
        return {comp: 1.0 for comp in species}

    molar_masses = {}
    unknown = []
    for comp in species:
        try:
            molar_masses[comp] = CP.PropsSI("M", comp)
        except Exception:
            unknown.append(comp)

    if unknown:
        raise ValueError(
            f"CoolProp has no molar mass for {', '.join(unknown)} in the mass composition {mass_fractions}. "
            "Name all species of the composition as CoolProp does."
        )
    if not molar_masses:
        raise ValueError(f"No valid molar masses were retrieved for substances {list(mass_fractions.keys())}")

    total_moles = sum(species[comp] / molar_masses[comp] for comp in molar_masses)
    molar_fractions = {comp: (species[comp] / molar_masses[comp]) / total_moles for comp in molar_masses}

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


def calc_chemical_exergy(stream_data, Tamb, pamb, chemExLib):
    """
    Calculate the chemical exergy of a stream based on the molar fractions and chemical exergy data. There are three cases:
    - Case A: Handle pure substance.
    - Case B: If water condenses, handle the liquid and gas phases separately.
    - Case C: If water doesn't condense or if water is not present, handle the mixture using the standard approach (ideal mixture).

    Parameters:
    - stream_data: Dictionary containing 'mass_composition' of the stream.
    - Tamb: Ambient temperature in Celsius.
    - pamb: Ambient pressure in bar.

    Returns:
    - eCH: Chemical exergy in kJ/kg.
    """
    logger.info(
        f"Starting chemical exergy of stream of composition {stream_data} calculation with Tamb={Tamb}, pamb={pamb}"
    )

    try:
        # Check if molar fractions already exist
        if "molar_composition" in stream_data:
            molar_fractions = stream_data["molar_composition"]
        else:
            # If not, convert mass composition to molar fractions
            molar_fractions = mass_to_molar_fractions(stream_data["mass_composition"])
        try:
            # Load chemical exergy data
            chem_ex_file = os.path.join(__datapath__, f"{chemExLib}.json")
            with open(chem_ex_file) as file:
                chem_ex_data = json.load(file)  # data in J/kmol
        except FileNotFoundError:
            error_msg = f"Chemical exergy data file '{chemExLib}.json' not found. Please ensure the file exists or set chemExLib to 'Ahrendts'."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        R = 8.314  # Universal gas constant in J/(molK)
        aliases_water = CP.get_aliases("H2O")

        # Handle pure substance (Case A)
        molar_fractions = {key: value for key, value in molar_fractions.items() if value > 1e-6}
        if len(molar_fractions) == 1:
            logger.info("Handling pure substance case (Case A).")
            substance = next(iter(molar_fractions))  # Get the single key

            try:
                aliases = CP.get_aliases(substance)

                if set(aliases) & set(aliases_water):
                    eCH = chem_ex_data["WATER"][2] / CP.PropsSI("M", "H2O")  # liquid water, in J/kg
                    logger.info(f"Pure water detected. Chemical exergy: {eCH} J/kg")
                else:
                    for alias in aliases:
                        if alias.upper() in chem_ex_data:
                            eCH = chem_ex_data[alias.upper()][3] / CP.PropsSI("M", substance)  # in J/kg
                            logger.info(f"Found exergy data for {substance}. Chemical exergy: {eCH} J/kg")
                            break
                    else:
                        logger.error(f"No matching alias found for {substance}")
                        raise KeyError(f"No matching alias found for {substance}")

            except Exception:
                eCH = 0  # If no aliases found, set chemical exergy to 0
                logger.warning(f"No CoolProp aliases found for {substance}. Setting chemical exergy to 0 J/kg.")

        # Handle mixtures (Case B or C)
        else:
            logger.info("Handling mixture case (Case B or C).")
            total_molar_mass = 0  # To compute the molar mass of the mixture
            eCH_gas_mol = 0  # Molar chemical exergy of the gas phase if condensation
            eCH_liquid_mol = 0  # Molar chemical exergy of the liquid phase if condensation
            molar_fractions_gas = {}  # Molar fractions within the gas phase if condensation
            entropy_mixing = 0  # Entropy of mixing of ideal mixtures

            # Calculate the total molar mass of the mixture
            for substance, fraction in molar_fractions.items():
                molar_mass = CP.PropsSI("M", substance)  # Molar mass in kg/mol
                total_molar_mass += fraction * molar_mass  # Weighted sum for molar mass in kg/mol
            logger.info(f"Total molar mass of the mixture: {total_molar_mass} kg/mol")

            water_present = any(alias in molar_fractions for alias in aliases_water)

            if water_present:
                water_alias = next(alias for alias in aliases_water if alias in molar_fractions)
                pH2O_sat = CP.PropsSI("P", "T", Tamb, "Q", 1, "Water")  # Saturation pressure of water in bar
                pH2O = molar_fractions[water_alias] * pamb  # Partial pressure of water

                if pH2O > pH2O_sat:  # Case B: Water condenses
                    logger.info("Condensation occurs in the mixture.")
                    x_dry = sum(fraction for comp, fraction in molar_fractions.items() if comp != water_alias)
                    x_H2O_gas = x_dry / (pamb / pH2O_sat - 1)  # Vaporous water fraction in the total mixture
                    x_H2O_liquid = molar_fractions[water_alias] - x_H2O_gas  # Liquid water fraction
                    x_total_gas = 1 - x_H2O_liquid  # Total gas phase fraction

                    eCH_liquid_mol = x_H2O_liquid * (chem_ex_data["WATER"][2])  # Liquid phase contribution, in J/mol

                    for substance, fraction in molar_fractions.items():
                        if substance == water_alias:
                            molar_fractions_gas[substance] = x_H2O_gas / x_total_gas
                        else:
                            molar_fractions_gas[substance] = molar_fractions[substance] / x_total_gas

                    for substance, fraction in molar_fractions_gas.items():
                        aliases = CP.get_aliases(substance)
                        for alias in aliases:
                            if alias.upper() in chem_ex_data:
                                eCH_gas_mol += fraction * (chem_ex_data[alias.upper()][3])  # Exergy is in J/mol
                                break
                        else:
                            logger.error(f"No matching alias found for {substance}")
                            raise KeyError(f"No matching alias found for {substance}")

                        if fraction > 0:  # Avoid log(0)
                            entropy_mixing += fraction * math.log(fraction)

                    eCH_gas_mol += R * Tamb * entropy_mixing
                    eCH_mol = eCH_gas_mol + eCH_liquid_mol
                    logger.info(f"Condensed phase chemical exergy: {eCH_mol} J/kmol")

                else:  # Case C: Water doesn't condense
                    logger.info("Water does not condense.")
                    eCH_mol = 0
                    for substance, fraction in molar_fractions.items():
                        aliases = CP.get_aliases(substance)
                        for alias in aliases:
                            if alias.upper() in chem_ex_data:
                                eCH_mol += fraction * (chem_ex_data[alias.upper()][3])  # Exergy in J/kmol
                                break
                        else:
                            logger.error(f"No matching alias found for {substance}")
                            raise KeyError(f"No matching alias found for {substance}")

                        if fraction > 0:  # Avoid log(0)
                            entropy_mixing += fraction * math.log(fraction)

                    eCH_mol += R * Tamb * entropy_mixing

            else:  # Case C: No water present
                logger.info("No water present in the mixture.")
                eCH_mol = 0
                for substance, fraction in molar_fractions.items():
                    aliases = CP.get_aliases(substance)
                    for alias in aliases:
                        if alias.upper() in chem_ex_data:
                            eCH_mol += fraction * (chem_ex_data[alias.upper()][3])  # Exergy in J/kmol
                            break
                    else:
                        logger.error(f"No matching alias found for {substance}")
                        raise KeyError(f"No matching alias found for {substance}")

                    if fraction > 0:  # Avoid log(0)
                        entropy_mixing += fraction * math.log(fraction)

                eCH_mol += R * Tamb * entropy_mixing

            eCH = eCH_mol / total_molar_mass  # Divide molar exergy by molar mass of mixture
            logger.info(f"Chemical exergy: {eCH} kJ/kg")

        return eCH

    except Exception as e:
        logger.error(f"Error in calc_chemical_exergy: {e}")
        raise


def add_chemical_exergy(my_json, Tamb, pamb, chemExLib):
    """
    Adds the chemical exergy to each connection in the JSON data, prioritizing molar composition if available.

    Parameters:
    - my_json: The JSON object containing the components and connections.
    - Tamb: Ambient temperature in Celsius.
    - pamb: Ambient pressure in bar.

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
            else:
                stream_data = {"mass_composition": mass_composition}
                logger.info(f"Using mass composition for connection {conn_name}")

            # Add the chemical exergy value
            conn_data["e_CH"] = calc_chemical_exergy(stream_data, Tamb, pamb, chemExLib)
            conn_data["e_CH_unit"] = SI_UNITS["e_CH"]
            logger.info(f"Added chemical exergy to connection {conn_name}: {conn_data['e_CH']} kJ/kg")
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
