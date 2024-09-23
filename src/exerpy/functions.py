import CoolProp.CoolProp as CP
import math
import json
import os

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
        # Strip off the "X" prefix to match fraction names in CoolProp
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


def calc_chemical_exergy(stream, tamb, pamb):
    """
    Calculate the chemical exergy of a stream based on the molar fractions and chemical exergy data.
    
    Parameters:
    - stream: Dictionary containing 'mass_composition' of the stream.
    - tamb: Ambient temperature in Celsius.
    - pamb: Ambient pressure in bar.
    
    Returns:
    - eCH: Chemical exergy in kJ/kg.
    """
    
    molar_fractions = mass_to_molar_fractions(stream['mass_composition'])
    print(molar_fractions)
    ahrendts = 'src\\data\\Ahrendts.json'
    
    # Check if file exists and is not empty
    if not os.path.exists(ahrendts):
        raise FileNotFoundError(f"The file {ahrendts} does not exist.")
    if os.path.getsize(ahrendts) == 0:
        raise ValueError(f"The file {ahrendts} is empty.")
    
    with open(ahrendts, 'r') as file:
        ahrendts_data = json.load(file)  # data in J/kmol

    # Initialize variables
    eCH_mol = 0
    entropy_mixing = 0
    R = 8.314  # Universal gas constant in kJ/(kmolK)
    T0 = tamb + 273.15  # Reference temperature in K

    # Handle pure materials
    if len(molar_fractions) == 1:  # Pure material case
        formula = next(iter(molar_fractions))  # Get the single key
        if formula == 'H2O':
            eCH = ahrendts_data['WATER'][2] / CP.PropsSI('M', 'H2O')  # liquid water, in kJ/kg
        else:
            # Get aliases for the chemical
            aliases = CP.get_aliases(formula)
            for alias in aliases:
                if alias.upper() in ahrendts_data:
                    eCH = ahrendts_data[alias.upper()][3] / CP.PropsSI('M', formula)
                    break
            else:
                raise KeyError(f"No matching alias found for {formula}")

    # Handle mixtures
    else:
        total_molar_mass = 0  # To compute the molar mass of the mixture
        eCH_gas_mol = 0
        eCH_liquid_mol = 0
        molar_fractions_gas = {}
        
        # Condensation test and calculation of the fractions in the new gas phase
        if "H2O" in molar_fractions.keys():
            pH2O_sat = CP.PropsSI('P', 'T', T0, 'Q', 1, 'Water') * 1e-5  # in bar
            pH2O = molar_fractions['H2O'] * pamb
            if pH2O > pH2O_sat:
                
                x_dry = sum(fraction for comp, fraction in molar_fractions.items() if comp != 'H2O')

                x_H2O_gas = x_dry / (pamb/pH2O_sat -1)
                x_H2O_liquid = molar_fractions['H2O'] - x_H2O_gas  # Part of the liquid phase over the total mixture

                x_total_gas = 1-x_H2O_liquid  # Part of the gas phase over the total mixture

                # The composition of the new gas phase is calculated
                for element, fraction in molar_fractions.items():
                    if element == "H2O":
                        molar_fractions_gas[element] = x_H2O_gas / x_total_gas
                    else:
                        molar_fractions_gas[element] = molar_fractions[element] / x_total_gas

                for element, fraction in molar_fractions_gas.items():

                    molar_mass = CP.PropsSI('M', element)  # Molar mass in kg/mol
                    total_molar_mass += fraction * molar_mass  # Weighted sum for molar mass

                    aliases = CP.get_aliases(element)
                    for alias in aliases:
                        if alias.upper() in ahrendts_data:
                            # Add contribution of each component's pure chemical exergy (in J/kmol)
                            eCH_gas_mol += fraction * (ahrendts_data[alias.upper()][3])  # Exergy is in J/kmol
                            break
                        else:
                            raise KeyError(f"No matching alias found for {element}")
                        
                    # Add contribution from the entropy of mixing term (for ideal mixtures)
                    if fraction > 0:  # Avoid log(0)
                        entropy_mixing += fraction * math.log(fraction)

                # Add the mixing term contribution to the total chemical exergy of the gas phase
                eCH_gas_mol += R * T0 * 1e-3 * entropy_mixing  # Gas phase contribution

                eCH_liquid_mol = x_H2O_liquid * (ahrendts_data['WATER'][2])  # Liquid phase contribution

                eCH_mol = eCH_gas_mol + eCH_liquid_mol

                # Convert the molar chemical exergy to mass-specific chemical exergy (in kJ/kg)
                eCH = eCH_mol / total_molar_mass  # Divide molar exergy by molar mass of mixture

                # Convert from J/kg to kJ/kg (since CoolProp returns in SI units by default)
                eCH /= 1000

        else:
            for element, fraction in molar_fractions.items():

                molar_mass = CP.PropsSI('M', element)  # Molar mass in kg/mol
                total_molar_mass += fraction * molar_mass  # Weighted sum for molar mass

                aliases = CP.get_aliases(element)
                for alias in aliases:
                    if alias.upper() in ahrendts_data:
                        # Add contribution of each component's pure chemical exergy (in J/kmol)
                        eCH_mol += fraction * (ahrendts_data[alias.upper()][3])  # Exergy is in J/kmol
                        break
                    else:
                        raise KeyError(f"No matching alias found for {element}")
                    
                # Add contribution from the entropy of mixing term (for ideal mixtures)
                if molar_fractions > 0:  # Avoid log(0)
                    entropy_mixing += molar_fractions * math.log(fraction)

            # Add the mixing term contribution to the total chemical exergy of the gas phase
            eCH_mol += R * T0 * 1e-3 * entropy_mixing  # Gas phase contribution

            # Convert the molar chemical exergy to mass-specific chemical exergy (in kJ/kg)
            eCH = eCH_mol / total_molar_mass  # Divide molar exergy by molar mass of mixture

            # Convert from J/kg to kJ/kg (since CoolProp returns in SI units by default)
            eCH /= 1000


    return eCH
