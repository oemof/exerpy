import json
import logging
import math
import os
import sys

import CoolProp.CoolProp as CP

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
    for fraction in molar_fractions.keys():
        try:
            molar_masses[fraction] = CP.PropsSI('M', fraction)
        except Exception as e:
            # print(f"Warning: Could not retrieve molar mass for {fraction} ({fraction}). Error: {e}")
            continue  # Skip this fraction if there's an issue

    # Step 2: Check if we have valid molar masses
    if not molar_masses:
        raise ValueError("No valid molar masses were retrieved. Exiting...")

    # Step 3: Calculate total mass in the mixture
    total_mass = sum(molar_fractions[comp] * molar_masses[comp] for comp in molar_masses)

    # Step 4: Calculate mass fractions
    for component in molar_masses.keys():
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
    logging.info(f"Starting chemical exergy calculation with Tamb={Tamb}, pamb={pamb}")

    try:
        # Check if molar fractions already exist
        if 'molar_composition' in stream_data:
            molar_fractions = stream_data['molar_composition']
            logging.info("Molar fractions found in stream.")
        else:
            # If not, convert mass composition to molar fractions
            molar_fractions = mass_to_molar_fractions(stream_data['mass_composition'])
            logging.info(f"Converted mass composition to molar fractions: {molar_fractions}")

        try:
            # Load chemical exergy data
            chem_ex_file = os.path.join(__datapath__, f'{chemExLib}.json')
            with open(chem_ex_file, 'r') as file:
                chem_ex_data = json.load(file)  # data in J/kmol
                logging.info("Chemical exergy data loaded successfully.")
        except FileNotFoundError:
            error_msg = f"Chemical exergy data file '{chemExLib}.json' not found. Please ensure the file exists or set chemExLib to 'Ahrendts'."
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)


        R = 8.314  # Universal gas constant in J/(molK)
        aliases_water = CP.get_aliases('H2O')

        # Handle pure substance (Case A)
        if len(molar_fractions) == 1:
            logging.info("Handling pure substance case (Case A).")
            substance = next(iter(molar_fractions))  # Get the single key
            aliases = CP.get_aliases(substance)

            if set(aliases) & set(aliases_water):
                eCH = chem_ex_data['WATER'][2] / CP.PropsSI('M', 'H2O')  # liquid water, in J/kg
                logging.info(f"Pure water detected. Chemical exergy: {eCH} J/kg")
            else:
                for alias in aliases:
                    if alias.upper() in chem_ex_data:
                        eCH = chem_ex_data[alias.upper()][3] / CP.PropsSI('M', substance)  # in J/kg
                        logging.info(f"Found exergy data for {substance}. Chemical exergy: {eCH} J/kg")
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
                pH2O_sat = CP.PropsSI('P', 'T', Tamb, 'Q', 1, 'Water')  # Saturation pressure of water in bar
                pH2O = molar_fractions[water_alias] * pamb  # Partial pressure of water

                if pH2O > pH2O_sat:  # Case B: Water condenses
                    logging.info(f"Condensation occurs in the mixture.")
                    x_dry = sum(fraction for comp, fraction in molar_fractions.items() if comp != water_alias)
                    x_H2O_gas = x_dry / (pamb/pH2O_sat - 1)  # Vaporous water fraction in the total mixture
                    x_H2O_liquid = molar_fractions[water_alias] - x_H2O_gas  # Liquid water fraction
                    x_total_gas = 1 - x_H2O_liquid  # Total gas phase fraction

                    eCH_liquid_mol = x_H2O_liquid * (chem_ex_data['WATER'][2])  # Liquid phase contribution, in J/mol

                    for substance, fraction in molar_fractions.items():
                        if substance == water_alias:
                            molar_fractions_gas[substance] = x_H2O_gas / x_total_gas
                        else:
                            molar_fractions_gas[substance] = molar_fractions[substance] / x_total_gas

                    for substance, fraction in molar_fractions_gas.items():
                        aliases = CP.get_aliases(substance)
                        for alias in aliases:
                            if alias.upper() in chem_ex_data:
                                eCH_gas_mol += fraction * (chem_ex_data[alias.upper()][3]) # Exergy is in J/mol
                                break
                        else:
                            logging.error(f"No matching alias found for {substance}")
                            raise KeyError(f"No matching alias found for {substance}")

                        if fraction > 0:  # Avoid log(0)
                            entropy_mixing += fraction * math.log(fraction)

                    eCH_gas_mol += R * Tamb * entropy_mixing
                    eCH_mol = eCH_gas_mol + eCH_liquid_mol
                    logging.info(f"Condensed phase chemical exergy: {eCH_mol} J/kmol")

                else:  # Case C: Water doesn't condense
                    logging.info(f"Water does not condense.")
                    eCH_mol = 0
                    for substance, fraction in molar_fractions.items():
                        aliases = CP.get_aliases(substance)
                        for alias in aliases:
                            if alias.upper() in chem_ex_data:
                                eCH_mol += fraction * (chem_ex_data[alias.upper()][3])  # Exergy in J/kmol
                                break
                        else:
                            logging.error(f"No matching alias found for {substance}")
                            raise KeyError(f"No matching alias found for {substance}")

                        if fraction > 0:  # Avoid log(0)
                            entropy_mixing += fraction * math.log(fraction)

                    eCH_mol += R * Tamb * entropy_mixing

            else:  # Case C: No water present
                logging.info(f"No water present in the mixture.")
                eCH_mol = 0
                for substance, fraction in molar_fractions.items():
                    aliases = CP.get_aliases(substance)
                    for alias in aliases:
                        if alias.upper() in chem_ex_data:
                            eCH_mol += fraction * (chem_ex_data[alias.upper()][3])  # Exergy in J/kmol
                            break
                    else:
                        logging.error(f"No matching alias found for {substance}")
                        raise KeyError(f"No matching alias found for {substance}")

                    if fraction > 0:  # Avoid log(0)
                        entropy_mixing += fraction * math.log(fraction)

                eCH_mol += R * Tamb * entropy_mixing

            eCH = eCH_mol / total_molar_mass  # Divide molar exergy by molar mass of mixture
            logging.info(f"Chemical exergy: {eCH} kJ/kg")

        return eCH

    except Exception as e:
        logging.error(f"Error in calc_chemical_exergy: {e}")
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
        raise ValueError("Ambient temperature (Tamb) and pressure (pamb) are required for chemical exergy calculation. "
                         "Please ensure they are included in the JSON or passed as arguments.")

    # Iterate over each material connection with kind == 'material'
    for conn_name, conn_data in my_json['connections'].items():
        if conn_data['kind'] == 'material':
            # Prefer molar composition if available, otherwise use mass composition
            molar_composition = conn_data.get('molar_composition', {})
            mass_composition = conn_data.get('mass_composition', {})

            # Prepare stream data for exergy calculation, prioritizing molar composition
            if molar_composition:
                stream_data = {'molar_composition': molar_composition}
                logging.info(f"Using molar composition for connection {conn_name}")
            else:
                stream_data = {'mass_composition': mass_composition}
                logging.info(f"Using mass composition for connection {conn_name}")

            # Add the chemical exergy value
            conn_data['e_CH'] = calc_chemical_exergy(stream_data, Tamb, pamb, chemExLib)
            conn_data['e_CH_unit'] = fluid_property_data['e']['SI_unit']
            logging.info(f"Added chemical exergy to connection {conn_name}: {conn_data['e_CH']} kJ/kg")
        else:
            logging.info(f"Skipped chemical exergy calculation for non-material connection {conn_name} ({conn_data['kind']})")

    return my_json


def add_total_exergy_flow(my_json, split_physical_exergy):
    """
    Adds the total exergy flow to each connection in the JSON data based on its kind.

    - For 'material' connections, the exergy is calculated as before.
    - For 'power' connections, the energy flow value is used directly.
    - For 'heat' connections, if the associated component is of class
      SimpleHeatExchanger, the thermal exergy difference is computed as:

      ..math::

          E = (e^\text{T}_\text{in} \cdot \dot m_\text{in})
          - (e^\text{T}_\text{out} \cdot \dot m_\text{out})

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
    for conn_name, conn_data in my_json['connections'].items():
        try:
            if conn_data['kind'] == 'material':
                # For material connections: E = m * (e^PH + e^CH)
                conn_data['E_PH'] = conn_data['m'] * conn_data['e_PH']
                if conn_data.get('e_CH') is not None:
                    conn_data['E_CH'] = conn_data['m'] * conn_data['e_CH']
                    conn_data['E'] = conn_data['E_PH'] + conn_data['E_CH']
                else:
                    conn_data['E'] = conn_data['E_PH']
                    logging.info(f"Missing chemical exergy for connection {conn_name}. Using only physical exergy.")
                if split_physical_exergy:
                    if conn_data.get('e_T') is not None:
                        conn_data['E_T'] = conn_data['m'] * conn_data['e_T']
                    else:
                        msg = f"Missing thermal exergy for connection {conn_name}."
                        logging.error(msg)
                        raise KeyError(msg)
                    if conn_data.get('e_M') is not None:
                        conn_data['E_M'] = conn_data['m'] * conn_data['e_M']
                    else:
                        msg = f"Missing mechanical exergy for connection {conn_name}."
                        logging.error(msg)
                        raise KeyError(msg)
            elif conn_data['kind'] == 'power':
                # For power connections, use the energy flow value directly.
                conn_data['E'] = conn_data['energy_flow']
            elif conn_data['kind'] == 'heat':
                # For heat connections, attempt the new calculation.
                # Identify the associated component (either source or target)
                comp_name = conn_data['source_component'] or conn_data['target_component']
                # Check if the component is either a SimpleHeatExchanger or a SteamGenerator.
                if ("SimpleHeatExchanger" in my_json['components'] and
                        comp_name in my_json['components']["SimpleHeatExchanger"]):
                    # Retrieve the inlet material streams: those with this component as target.
                    inlet_conns = [c for c in my_json['connections'].values()
                                if c.get('target_component') == comp_name and c.get('kind') == 'material']
                    # Retrieve the outlet material streams: those with this component as source.
                    outlet_conns = [c for c in my_json['connections'].values()
                                    if c.get('source_component') == comp_name and c.get('kind') == 'material']
                    # Determine which exergy key to use based on the flag.
                    exergy_key = 'e_T' if split_physical_exergy else 'e_PH'

                    if inlet_conns and outlet_conns:
                        # For simplicity, take the first inlet and first outlet.
                        inlet = inlet_conns[0]
                        outlet = outlet_conns[0]
                        # Calculate the heat exergy difference using the selected key:
                        conn_data['E'] = inlet.get(exergy_key, 0) * inlet.get('m', 0) - outlet.get(exergy_key, 0) * outlet.get('m', 0)
                    else:
                        conn_data['E'] = None
                        logging.warning(f"Not enough material connections for heat exchanger {comp_name} for heat exergy calculation.")
                elif ("SteamGenerator" in my_json['components'] and
                    comp_name in my_json['components']["SteamGenerator"]):
                    # Retrieve material connections for the steam generator.
                    inlet_conns = [c for c in my_json['connections'].values()
                                if c.get('target_component') == comp_name and c.get('kind') == 'material']
                    outlet_conns = [c for c in my_json['connections'].values()
                                    if c.get('source_component') == comp_name and c.get('kind') == 'material']
                    if inlet_conns and outlet_conns:
                        # For the steam generator, group the material connections as follows:
                        feed_water   = inlet_conns[0]                      # inl[0]: Feed water inlet (HP)
                        steam_inlet  = inlet_conns[1] if len(inlet_conns) > 1 else {}  # inl[1]: Steam inlet (IP)
                        superheated_HP = outlet_conns[0]                    # outl[0]: Superheated steam outlet (HP)
                        superheated_IP = outlet_conns[1] if len(outlet_conns) > 1 else {}  # outl[1]: Superheated steam outlet (IP)
                        water_inj_HP = inlet_conns[2] if len(inlet_conns) > 2 else {}  # inl[2]: Water injection (HP)
                        water_inj_IP = inlet_conns[3] if len(inlet_conns) > 3 else {}  # inl[3]: Water injection (IP)

                        exergy_type = 'e_T' if split_physical_exergy else 'e_PH'
                        # Calculate the contributions based on the new E_F definition:
                        E_F_HP = superheated_HP.get('m', 0) * superheated_HP.get(exergy_type, 0) - \
                                feed_water.get('m', 0) * feed_water.get(exergy_type, 0)
                        E_F_IP = (superheated_IP.get('m', 0) * superheated_IP.get(exergy_type, 0) -
                                steam_inlet.get('m', 0) * steam_inlet.get(exergy_type, 0))
                        E_F_w_inj = (water_inj_HP.get('m', 0) * water_inj_HP.get(exergy_type, 0) +
                                    water_inj_IP.get('m', 0) * water_inj_IP.get(exergy_type, 0))
                        # Total exergy flow for the heat input (E_TOT) is taken as the exergy fuel E_F:
                        E_TOT = E_F_HP + E_F_IP - E_F_w_inj
                        conn_data['E'] = E_TOT
                    else:
                        conn_data['E'] = None
                        logging.warning(f"Not enough material connections for steam generator {comp_name} for heat exergy calculation.")
                else:
                    conn_data['E'] = None
                    logging.warning(f"Heat connection {conn_name} is not associated with a recognized heat exchanger component.")
            elif conn_data['kind'] == 'other':
                # No exergy flow calculation for 'other' kind.
                pass
            else:
                logging.warning(f"Unknown connection kind: {conn_data['kind']} for connection {conn_name}. Skipping exergy flow calculation.")
                conn_data['E'] = None

            # Assign the exergy unit (assuming fluid_property_data is defined elsewhere)
            conn_data['E_unit'] = fluid_property_data['power']['SI_unit']

        except Exception as e:
            logging.error(f"Error calculating total exergy flow for connection {conn_name}: {e}")
            conn_data['E'] = None

    return my_json



def convert_to_SI(property, value, unit):
    r"""
    Convert a value to its SI value.

    Parameters
    ----------
    property : str
        Fluid property to convert.

    value : float
        Value to convert.

    unit : str
        Unit of the value.

    Returns
    -------
    SI_value : float
        Specified fluid property in SI value.

    Raises
    ------
    ValueError: If the property or unit is invalid or conversion is not possible.
    """
    # Check if value is None
    if value is None:
        logging.warning(f"Value is None for property '{property}', cannot convert.")
        return None

    # Check if the property is valid and exists in fluid_property_data
    if property not in fluid_property_data:
        logging.warning(f"Unrecognized property: '{property}'. Returning original value.")
        return value

    # Check if the unit is valid
    if unit == 'Unknown':
        logging.warning(f"Unrecognized unit for property '{property}'. Returning original value.")
        return value

    try:
        # Handle temperature conversions separately
        if property == 'T':
            if unit not in fluid_property_data['T']['units']:
                raise ValueError(f"Invalid unit '{unit}' for temperature. Unit not found.")
            converters = fluid_property_data['T']['units'][unit]
            return (value + converters[0]) * converters[1]

        # Handle all other property conversions
        else:
            if unit not in fluid_property_data[property]['units']:
                raise ValueError(f"Invalid unit '{unit}' for property '{property}'. Unit not found.")
            conversion_factor = fluid_property_data[property]['units'][unit]
            return value * conversion_factor

    except KeyError as e:
        raise ValueError(f"Conversion error: {e}")
    except Exception as e:
        raise ValueError(f"An error occurred during the unit conversion: {e}")



fluid_property_data = {
    'm': {
        'text': 'mass flow',
        'SI_unit': 'kg / s',
        'units': {
            'kg / s': 1, 'kg / min': 1 / 60, 'kg / h': 1 / 3.6e3, 'kg/s': 1, 'kg/min': 1 / 60, 'kg/h': 1 / 3.6e3,
            'kg / sec': 1, 'kg/sec': 1,
            't / h': 1 / 3.6, 'g / s': 1e-3, 't/h': 1 / 3.6, 'g/s': 1e-3,
            'g / sec': 1e-3, 'g/sec': 1e-3,
        },
        'latex_eq': r'0 = \dot{m} - \dot{m}_\mathrm{spec}',
        'documentation': {'float_fmt': '{:,.3f}'}
    },
    'n': {
        'text': 'molar flow',
        'SI_unit': 'mol / s',
        'units': {
            'mol / s': 1, 'mol / min': 1 / 60, 'mol / h': 1 / 3.6e3, 'mol/s': 1, 'mol/min': 1 / 60, 'mol/h': 1 / 3.6e3,
            'kmol / s': 1e3, 'kmol / min': 1 / 60e3, 'kmol / h': 1 / 3.6e6, 'kmol/s': 1e3, 'kmol/min': 1 / 60e3, 'kmol/h': 1 / 3.6e6,
            'mol / sec': 1, 'mol/sec': 1, 'kmol / sec': 1e3, 'kmol/sec': 1e3,
        },
        'latex_eq': r'0 = \dot{n} - \dot{n}_\mathrm{spec}',
        'documentation': {'float_fmt': '{:,.3f}'}
    },
    'v': {
        'text': 'volumetric flow',
        'SI_unit': 'm3 / s',
        'units': {
            'm3 / s': 1, 'm3 / min': 1 / 60, 'm3 / h': 1 / 3.6e3,
            'l / s': 1 / 1e3, 'l / min': 1 / 60e3, 'l / h': 1 / 3.6e6
        },
        'latex_eq': (
            r'0 = \dot{m} \cdot v \left(p,h\right)- \dot{V}_\mathrm{spec}'),
        'documentation': {'float_fmt': '{:,.3f}'}
    },
    'p': {
        'text': 'pressure',
        'SI_unit': 'Pa',
        'units': {
            'Pa': 1, 'kPa': 1e3, 'psi': 6.8948e3,
            'bar': 1e5, 'atm': 1.01325e5, 'MPa': 1e6
        },
        'latex_eq': r'0 = p - p_\mathrm{spec}',
        'documentation': {'float_fmt': '{:,.3f}'}
    },
    'h': {
        'text': 'enthalpy',
        'SI_unit': 'J / kg',
        'SI_unit_molar:': 'J / mol',
        'units': {
            'J / kg': 1, 'kJ / kg': 1e3, 'MJ / kg': 1e6, 'J/kg': 1, 'kJ/kg': 1e3, 'MJ/kg': 1e6,
            'cal / kg': 4.184, 'kcal / kg': 4.184e3, 'cal/kg': 4.184, 'kcal/kg': 4.184e3,
            'Wh / kg': 3.6e3, 'kWh / kg': 3.6e6, 'Wh/kg': 3.6e3, 'kWh kg': 3.6e6,
            'J / mol': 1, 'kJ / mol': 1e3, 'MJ / mol': 1e6, 'J/mol': 1, 'kJ/mol': 1e3, 'MJ/mol': 1e6,
            'J / kmol': 1e-3, 'kJ / kmol': 1, 'MJ / kmol': 1e3, 'J/kmol': 1e-3, 'kJ/kmol': 1, 'MJ/kmol': 1e3
        },
        'latex_eq': r'0 = h - h_\mathrm{spec}',
        'documentation': {'float_fmt': '{:,.3f}'}
    },
    'e': {
        'text': 'exergy',
        'SI_unit': 'J / kg',
        'SI_unit_molar:': 'J / mol',
        'units': {
            'J / kg': 1, 'kJ / kg': 1e3, 'MJ / kg': 1e6, 'J/kg': 1, 'kJ/kg': 1e3, 'MJ/kg': 1e6,
            'cal / kg': 4.184, 'kcal / kg': 4.184e3, 'cal/kg': 4.184, 'kcal/kg': 4.184e3,
            'Wh / kg': 3.6e3, 'kWh / kg': 3.6e6, 'Wh/kg': 3.6e3, 'kWh kg': 3.6e6,
            'J / mol': 1, 'kJ / mol': 1e3, 'MJ / mol': 1e6, 'J/mol': 1, 'kJ/mol': 1e3, 'MJ/mol': 1e6,
            'J / kmol': 1e-3, 'kJ / kmol': 1, 'MJ / kmol': 1e3, 'J/kmol': 1e-3, 'kJ/kmol': 1, 'MJ/kmol': 1e3
        },
        'latex_eq': r'0 = h - h_\mathrm{spec}',
        'documentation': {'float_fmt': '{:,.3f}'}
    },
    'T': {
        'text': 'temperature',
        'SI_unit': 'K',
        'units': {
            'K': [0, 1], 'R': [0, 5 / 9],
            'C': [273.15, 1], 'F': [459.67, 5 / 9]
        },
        'latex_eq': r'0 = T \left(p, h \right) - T_\mathrm{spec}',
        'documentation': {'float_fmt': '{:,.1f}'}
    },
    'Td_bp': {
        'text': 'temperature difference to boiling point',
        'SI_unit': 'K',
        'units': {
            'K': 1, 'R': 5 / 9, 'C': 1, 'F': 5 / 9
        },
        'latex_eq': r'0 = \Delta T_\mathrm{spec}- T_\mathrm{sat}\left(p\right)',
        'documentation': {'float_fmt': '{:,.1f}'}
    },
    'vol': {
        'text': 'specific volume',
        'SI_unit': 'm3 / kg',
        'units': {'m3 / kg': 1, 'l / kg': 1e-3},
        'latex_eq': (
            r'0 = v\left(p,h\right) \cdot \dot{m} - \dot{V}_\mathrm{spec}'),
        'documentation': {'float_fmt': '{:,.3f}'}
    },
    'x': {
        'text': 'vapor mass fraction',
        'SI_unit': '-',
        'units': {'1': 1, '-': 1, '%': 1e-2, 'ppm': 1e-6},
        'latex_eq': r'0 = h - h\left(p, x_\mathrm{spec}\right)',
        'documentation': {'float_fmt': '{:,.2f}'}
    },
    's': {
        'text': 'entropy',
        'SI_unit': 'J / kgK',
        'SI_unit_molar:': 'J / molK',
        'units': {
            'J / kgK': 1, 'kJ / kgK': 1e3, 'MJ / kgK': 1e6, 'J/kgK': 1, 'kJ/kgK': 1e3, 'MJ/kgK': 1e6,
            'J / kg-K': 1, 'kJ / kg-K': 1e3, 'MJ / kg-K': 1e6, 'J/kg-K': 1, 'kJ/kg-K': 1e3, 'MJ/kg-K': 1e6,
            'J / molK': 1, 'kJ / molK': 1e3, 'MJ / molK': 1e6, 'J/molK': 1, 'kJ/molK': 1e3, 'MJ/molK': 1e6,
            'J / mol-K': 1, 'kJ / mol-K': 1e3, 'MJ / mol-K': 1e6, 'J/mol-K': 1, 'kJ/mol-K': 1e3, 'MJ/mol-K': 1e6,
            'J / kmolK': 1e-3, 'kJ / kmolK': 1, 'MJ / kmolK': 1e3, 'J/kmolK': 1e-3, 'kJ/kmolK': 1, 'MJ/kmolK': 1e3,
            'J / kmol-K': 1e-3, 'kJ / kmol-K': 1, 'MJ / kmol-K': 1e3, 'J/kmol-K': 1e-3, 'kJ/kmol-K': 1, 'MJ/kmol-K': 1e3
            },
        'latex_eq': r'0 = s_\mathrm{spec} - s\left(p, h \right)',
        'documentation': {'float_fmt': '{:,.2f}'}
    },
    'power': {
        'text': 'power',
        'SI_unit': 'W',
        'units': {'W': 1, 'kW': 1e3, 'MW': 1e6},
    },
    'heat': {
        'text': 'heat',
        'SI_unit': 'W',
        'units': {'W': 1, 'kW': 1e3, 'MW': 1e6},
    },
    'kA': {
        'text': 'kA',
        'SI_unit': 'W / K',
        'units': {
            'W / K': 1, 'kW / K': 1e3, 'MW / K': 1e6,
            'W/K': 1, 'kW/K': 1e3, 'MW/K': 1e6},
    },
    'A': {
        'text': 'area',
        'SI_unit': 'm2',
        'units': {'m2': 1, 'cm2': 1e-4, 'mm2': 1e-6,
                  'm²': 1, 'cm²': 1e-4, 'mm²': 1e-6},
    },
    'VM': {
        'text': 'volume flow',
        'SI_unit': 'm3 / s',
        'units': {'m3 / s': 1, 'l / s': 1e-3, 'l/s': 1e-3,
                  'm³/s': 1, 'l/min': 1 / 60e3, 'l/h': 1 / 3.6e6},
    }
}
