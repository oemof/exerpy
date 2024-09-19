import CoolProp.CoolProp as CP

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
    for component in mass_fractions.keys():
        # Strip off the "X" prefix to match component names in CoolProp
        clean_component = component[1:]  # Remove 'X' prefix
        try:
            molar_masses[component] = CP.PropsSI('M', clean_component)
        except Exception as e:
           #  print(f"Warning: Could not retrieve molar mass for {component} ({clean_component}). Error: {e}")
            continue  # Skip this component if there's an issue

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
