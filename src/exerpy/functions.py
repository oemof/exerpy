import CoolProp.CoolProp as CP
import math
import json
import os
import logging
from exerpy import __datapath__

def mass_to_molar_fractions(mass_fractions):
    """
    Convert mass fractions to molar fractions.
    
    Parameters:
    - mass_fractions: Dictionary with component names as keys and mass fractions as values.
    
    Returns:
    - molar_fractions: Dictionary with component names as keys and molar fractions as values.
    """
    molar_masses = {}
    molar_fractions = {}
    
    # Step 1: Get the molar masses for each component
    for fraction in mass_fractions.keys():
        try:
            molar_masses[fraction] = CP.PropsSI('M', fraction)
        except Exception as e:
           #  print(f"Warning: Could not retrieve molar mass for {fraction} ({fraction}). Error: {e}")
            continue  # Skip this fraction if there's an issue

    # Step 2: Check if we have valid molar masses
    if not molar_masses:
        raise ValueError("No valid molar masses were retrieved. Exiting...")

    # Step 3: Calculate total moles in the mixture
    total_moles = sum(mass_fractions[comp] / molar_masses[comp] for comp in molar_masses)

    # Step 4: Calculate molar fractions
    for component in molar_masses.keys():
        molar_fractions[component] = (mass_fractions[component] / molar_masses[component]) / total_moles

    # Step 5: Check if molar fractions sum to approximately 1
    molar_sum = sum(molar_fractions.values())
    if abs(molar_sum - 1.0) > 1e-6:
        raise ValueError(f"Error: Molar fractions do not sum to 1. Sum is {molar_sum}")

    return molar_fractions


def calc_chemical_exergy(stream, Tamb, pamb):
    """
    Calculate the chemical exergy of a stream based on the molar fractions and chemical exergy data. There are three cases:
    - Case A: Handle pure substance.
    - Case B: If water condenses, handle the liquid and gas phases separately.
    - Case C: If water doesn't condense or if water is not present, handle the mixture using the standard approach (ideal mixture).
    
    Parameters:
    - stream: Dictionary containing 'mass_composition' of the stream.
    - Tamb: Ambient temperature in Celsius.
    - pamb: Ambient pressure in bar.
    
    Returns:
    - eCH: Chemical exergy in kJ/kg.
    """
    logging.info(f"Starting chemical exergy calculation with Tamb={Tamb}, pamb={pamb}")
    
    try:
        molar_fractions = mass_to_molar_fractions(stream['mass_composition'])
        logging.info(f"Molar fractions: {molar_fractions}")
        
        ahrendts = os.path.join(__datapath__, 'Ahrendts.json')
    
        # Check if file exists and is not empty
        if not os.path.exists(ahrendts):
            logging.error(f"The file {ahrendts} does not exist.")
            raise FileNotFoundError(f"The file {ahrendts} does not exist.")
        if os.path.getsize(ahrendts) == 0:
            logging.error(f"The file {ahrendts} is empty.")
            raise ValueError(f"The file {ahrendts} is empty.")
        
        with open(ahrendts, 'r') as file:
            ahrendts_data = json.load(file)  # data in J/kmol
            logging.info("Loaded Ahrendts data successfully.")

        R = 8.314  # Universal gas constant in kJ/(kmolK)
        T0 = Tamb + 273.15  # Reference temperature in K
        aliases_water = CP.get_aliases('H2O')

        # Handle pure substance (Case A)
        if len(molar_fractions) == 1:
            logging.info("Handling pure substance case (Case A).")
            substance = next(iter(molar_fractions))  # Get the single key
            aliases = CP.get_aliases(substance)

            if set(aliases) & set(aliases_water):
                eCH = ahrendts_data['WATER'][2] / CP.PropsSI('M', 'H2O')  # liquid water, in kJ/kg
                logging.info(f"Pure water detected. Chemical exergy: {eCH} kJ/kg")
            else:
                for alias in aliases:
                    if alias.upper() in ahrendts_data:
                        eCH = ahrendts_data[alias.upper()][3] / CP.PropsSI('M', substance)
                        logging.info(f"Found exergy data for {substance}. Chemical exergy: {eCH} kJ/kg")
                        break
                else:
                    logging.error(f"No matching alias found for {substance}")
                    raise KeyError(f"No matching alias found for {substance}")

        # Handle mixtures (Case B or C)
        else:
            logging.info("Handling mixture case (Case B or C).")
            total_molar_mass = 0  # To compute the molar mass of the mixture
            eCH_gas_mol = 0  # Molar chemical exergy of the gas phase if condensation
            eCH_liquid_mol = 0  # Molar chemical exergy of the liquid phase if condensation
            molar_fractions_gas = {}  # Molar fractions within the gas phase if condensation
            entropy_mixing = 0  # Entropy of mixing of ideal mixtures

            # Calculate the total molar mass of the mixture
            for substance, fraction in molar_fractions.items():
                molar_mass = CP.PropsSI('M', substance)  # Molar mass in kg/mol
                total_molar_mass += fraction * molar_mass  # Weighted sum for molar mass in kg/mol
            logging.info(f"Total molar mass of the mixture: {total_molar_mass} kg/mol")

            water_present = any(alias in molar_fractions.keys() for alias in aliases_water)

            if water_present:
                water_alias = next(alias for alias in aliases_water if alias in molar_fractions.keys())
                pH2O_sat = CP.PropsSI('P', 'T', T0, 'Q', 1, 'Water') * 1e-5  # Saturation pressure of water in bar
                pH2O = molar_fractions[water_alias] * pamb  # Partial pressure of water

                if pH2O > pH2O_sat:  # Case B: Water condenses
                    logging.info(f"Condensation occurs in the mixture.")
                    x_dry = sum(fraction for comp, fraction in molar_fractions.items() if comp != water_alias)
                    x_H2O_gas = x_dry / (pamb/pH2O_sat - 1)  # Vaporous water fraction in the total mixture
                    x_H2O_liquid = molar_fractions[water_alias] - x_H2O_gas  # Liquid water fraction
                    x_total_gas = 1 - x_H2O_liquid  # Total gas phase fraction

                    eCH_liquid_mol = x_H2O_liquid * (ahrendts_data['WATER'][2])  # Liquid phase contribution

                    for substance, fraction in molar_fractions.items():
                        if substance == water_alias:
                            molar_fractions_gas[substance] = x_H2O_gas / x_total_gas
                        else:
                            molar_fractions_gas[substance] = molar_fractions[substance] / x_total_gas

                    for substance, fraction in molar_fractions_gas.items():
                        aliases = CP.get_aliases(substance)
                        for alias in aliases:
                            if alias.upper() in ahrendts_data:
                                eCH_gas_mol += fraction * (ahrendts_data[alias.upper()][3])  # Exergy is in J/kmol
                                break
                        else:
                            logging.error(f"No matching alias found for {substance}")
                            raise KeyError(f"No matching alias found for {substance}")
                        
                        if fraction > 0:  # Avoid log(0)
                            entropy_mixing += fraction * math.log(fraction)

                    eCH_gas_mol += R * T0 * 1e-3 * entropy_mixing
                    eCH_mol = eCH_gas_mol + eCH_liquid_mol
                    logging.info(f"Condensed phase chemical exergy: {eCH_mol} J/kmol")

                else:  # Case C: Water doesn't condense
                    logging.info(f"Water does not condense.")
                    eCH_mol = 0
                    for substance, fraction in molar_fractions.items():
                        aliases = CP.get_aliases(substance)
                        for alias in aliases:
                            if alias.upper() in ahrendts_data:
                                eCH_mol += fraction * (ahrendts_data[alias.upper()][3])  # Exergy in J/kmol
                                break
                        else:
                            logging.error(f"No matching alias found for {substance}")
                            raise KeyError(f"No matching alias found for {substance}")
                        
                        if fraction > 0:  # Avoid log(0)
                            entropy_mixing += fraction * math.log(fraction)

                    eCH_mol += R * T0 * 1e-3 * entropy_mixing

            else:  # Case C: No water present
                logging.info(f"No water present in the mixture.")
                eCH_mol = 0
                for substance, fraction in molar_fractions.items():
                    aliases = CP.get_aliases(substance)
                    for alias in aliases:
                        if alias.upper() in ahrendts_data:
                            eCH_mol += fraction * (ahrendts_data[alias.upper()][3])  # Exergy in J/kmol
                            break
                    else:
                        logging.error(f"No matching alias found for {substance}")
                        raise KeyError(f"No matching alias found for {substance}")
                    
                    if fraction > 0:  # Avoid log(0)
                        entropy_mixing += fraction * math.log(fraction)

                eCH_mol += R * T0 * 1e-3 * entropy_mixing

            eCH = eCH_mol / total_molar_mass  # Divide molar exergy by molar mass of mixture
            logging.info(f"Final chemical exergy: {eCH} kJ/kg")

        return eCH
    
    except Exception as e:
        logging.error(f"Error in calc_chemical_exergy: {e}")
        raise


def add_chemical_exergy(my_json, Tamb, pamb):
    """
    Adds the chemical exergy to each connection in the JSON data, excluding Shaft and Electric connections.
    
    Parameters:
    - my_json: The JSON object containing the components and connections.
    - Tamb: Ambient temperature in Celsius.
    - pamb: Ambient pressure in bar.
    
    Returns:
    - The modified JSON object with added chemical exergy for each connection.
    """
    # Define non-material fluid types (e.g., Shaft and Electric) to exclude from chemical exergy calculation
    non_material_fluids = {"Shaft", "Electric"}

    # Iterate over each connection
    for conn_name, conn_data in my_json['connections'].items():
        # Check if the connection's fluid type is not in the non-material fluids list
        if conn_data['fluid_type'] not in non_material_fluids:
            try:
                # Calculate the chemical exergy for each connection using the provided mass_composition
                mass_composition = conn_data.get('mass_composition', {})
                stream_data = {'mass_composition': mass_composition}
                conn_data['e_CH'] = calc_chemical_exergy(stream_data, Tamb, pamb)  # Add the chemical exergy value
                logging.info(f"Added chemical exergy to connection {conn_name}: {conn_data['e_CH']} kJ/kg")
            except Exception as e:
                logging.error(f"Error calculating chemical exergy for connection {conn_name}: {e}")
        else:
            logging.info(f"Skipped chemical exergy calculation for non-material connection {conn_name} ({conn_data['fluid_type']})")
    
    return my_json