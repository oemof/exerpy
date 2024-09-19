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
        molar_masses[component] = CP.PropsSI('M', clean_component)
    
    # Step 2: Calculate total moles in the mixture
    total_moles = sum(mass_fractions[comp] / molar_masses[comp] for comp in mass_fractions)
    
    # Step 3: Calculate molar fractions
    for component in mass_fractions.keys():
        molar_fractions[component] = (mass_fractions[component] / molar_masses[component]) / total_moles
    
    return molar_fractions