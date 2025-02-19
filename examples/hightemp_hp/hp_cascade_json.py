import os
import logging
import pandas as pd
from tabulate import tabulate
import numpy as np

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import necessary modules and classes from exerpy.
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis, EconomicAnalysis
from exerpy.components import HeatExchanger, Compressor, Valve, Motor

# Define the path to the Ebsilon model file.
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hp_cascade_ebs.json'))

def run_exergoeco_analysis(elec_price_cent_kWh, tau):
    """
    Reload the exergy analysis from the JSON file, calculate PEC, run economic and
    exergoeconomic analyses using the given electricity price and full load hours.
    
    Returns the component results DataFrame from the exergoeconomic analysis.
    
    Parameters
    ----------
    elec_price_cent_kWh : float
        Electricity cost in cent/kWh.
    tau : float
        Full load hours (hours/year).
    """
    # Reload a virgin exergy analysis.
    ean = ExergyAnalysis.from_json(model_path)
    
    # Define exergy streams.
    fuel = {"inputs": ['E1', 'E2'], "outputs": []}
    product = {"inputs": ['22'], "outputs": ['21']}
    loss = {"inputs": ['12'], "outputs": ['11']}
    
    # Run the exergy analysis.
    ean.analyse(E_F=fuel, E_P=product, E_L=loss)
    ean.exergy_results(print_results=False)
    
    # ------------------------------
    # PEC Calculation Using Class-Based Correlations
    # ------------------------------
    PEC_computed = {}
    for comp in ean.components.values():
        name = comp.name
        # --- Heat Exchangers ---
        if isinstance(comp, HeatExchanger):
            A = comp.A  # surface area
            if A is not None:
                PEC = 15526 * (A / 42)**0.8
            else:
                PEC = 0.0
            PEC_computed[name] = PEC
        
        # --- Compressors (and Fans) ---
        elif isinstance(comp, Compressor):
            VM = None
            for conn in ean.connections.values():
                if conn.get("target_component") == name:
                    VM = conn.get("VM", None)
                    if VM is not None:
                        break
            if VM is None:
                VM = 279.8 / 3600  # Convert nominal value from m3/h to m3/s if needed.
            PEC = 19850 * ((VM * 3600) / 279.8)**0.73
            PEC_computed[name] = PEC
        
        # --- Valves ---
        elif isinstance(comp, Valve):
            PEC_computed[name] = 0.0
        
        # --- Other components ---
        else:
            PEC_computed[name] = 0.0
    
    # Process Motors separately (PEC = 10% of associated compressor/fan).
    for comp in ean.components.values():
        if isinstance(comp, Motor):
            name = comp.name
            associated_comp = None
            for conn in ean.connections.values():
                if conn.get("source_component") == name:
                    associated_comp = conn.get("target_component")
                    if associated_comp:
                        break
            if associated_comp:
                comp_PEC = PEC_computed.get(associated_comp, 0.0)
                PEC = 0.1 * comp_PEC
            else:
                PEC = 0.0
            PEC_computed[name] = PEC
    
    # ------------------------------
    # Economic Analysis
    # ------------------------------
    # Convert electricity price from cent/kWh to €/GJ.
    # 1 kWh = 3.6 MJ and 1 GJ = 277.78 kWh.
    elec_cost_eur_per_kWh = elec_price_cent_kWh / 100.0
    elec_cost_eur_per_GJ = elec_cost_eur_per_kWh * 277.78
    
    econ_pars = {
        'tau': tau,
        'i_eff': 0.08,
        'n': 30,
        'r_n': 0.02
    }
    components_order = list(PEC_computed.keys())
    PEC_list = [PEC_computed[comp] for comp in components_order]
    OMC_relative = [0.03 if pec > 0 else 0.0 for pec in PEC_list]
    
    econ_analysis = EconomicAnalysis(econ_pars)
    _, _, Z_total = econ_analysis.compute_component_costs(PEC_list, OMC_relative)
    
    # Build the exergoeconomic cost dictionary.
    Exe_Eco_Costs = {}
    for comp, z in zip(components_order, Z_total):
        Exe_Eco_Costs[f"{comp}_Z"] = z
    Exe_Eco_Costs["11_c"] = 0.0
    Exe_Eco_Costs["21_c"] = 0.0
    Exe_Eco_Costs["E1_c"] = elec_cost_eur_per_GJ
    
    # ------------------------------
    # Exergoeconomic Analysis
    # ------------------------------
    exergoeco_analysis = ExergoeconomicAnalysis(ean)
    exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
    # Unpack four DataFrames; we only use the component results.
    df_comp, df_mat1, df_mat2, df_non_mat = exergoeco_analysis.exergoeconomic_results()
    
    return df_comp

# ------------------------------------------------------------------------------
# Sensitivity Analysis Execution
# ------------------------------------------------------------------------------
# Sensitivity ranges: electricity prices [30, 40, 50] cent/kWh and tau values [4000, 5500, 7000] hours/year.
electricity_prices = [30.0, 40.0, 50.0]
tau_values = [4000, 5500, 7000]

# Prepare dictionaries to store the comparison results for:
#   - Combined cost rate (Z+C_D [EUR/h])
#   - Exergoeconomic factor (f [%])
#   - Product-specific cost (c_P [EUR/GJ]) from the TOT row.
results_ZCD = {}
results_f = {}
results_CP = {}

# Also store the complete component DataFrame for each case.
df_comp_all = {}

for elec_price in electricity_prices:
    for tau in tau_values:
        case_label = f"Price={elec_price}, tau={tau}"
        print(f"\n\n\nRunning analysis for electricity price = {elec_price} cent/kWh and tau = {tau} hours/year\n")
        df_comp = run_exergoeco_analysis(elec_price, tau)
        # Ensure there is a "Component" column; if not, use the index.
        if "Component" not in df_comp.columns:
            df_comp = df_comp.reset_index().rename(columns={"index": "Component"})
        df_comp_all[case_label] = df_comp.copy()
        # We assume that the df_comp includes columns "C_D+Z [EUR/h]" and "f [%]"
        results_ZCD[case_label] = df_comp[["Component", "C_D+Z [EUR/h]"]].set_index("Component")
        results_f[case_label] = df_comp[["Component", "f [%]"]].set_index("Component")
        # Extract product-specific cost from the TOT row; here we assume the column "c_P [EUR/GJ]" exists.
        if "TOT" in df_comp["Component"].values:
            cp_val = df_comp.loc[df_comp["Component"]=="TOT", "c_P [EUR/GJ]"].values[0]
        else:
            cp_val = np.nan
        results_CP[case_label] = cp_val

# ------------------------------------------------------------------------------
# Combine the results into comparison DataFrames.
# ------------------------------------------------------------------------------
all_components = sorted({comp for res in results_ZCD.values() for comp in res.index})

ZCD_df = pd.DataFrame(index=all_components)
f_df = pd.DataFrame(index=all_components)

for case, res in results_ZCD.items():
    for comp in all_components:
        ZCD_df.loc[comp, case] = res.loc[comp, "C_D+Z [EUR/h]"] if comp in res.index else np.nan

for case, res in results_f.items():
    for comp in all_components:
        f_df.loc[comp, case] = res.loc[comp, "f [%]"] if comp in res.index else np.nan

# Build a DataFrame for product-specific cost.
CP_df = pd.DataFrame.from_dict(results_CP, orient='index', columns=["c_P [EUR/GJ]"])
CP_df.index.name = "Case"

# ------------------------------------------------------------------------------
# Print the Comparison Tables using tabulate.
# ------------------------------------------------------------------------------
print("\nExergoeconomic Analysis - Comparison of Combined Cost Rates (C_D+Z) [EUR/h]:")
print(tabulate(ZCD_df.reset_index(), headers="keys", tablefmt="psql", floatfmt=".3f"))

print("\nExergoeconomic Analysis - Comparison of Exergoeconomic Factor (f) [%]:")
print(tabulate(f_df.reset_index(), headers="keys", tablefmt="psql", floatfmt=".3f"))

print("\nExergoeconomic Analysis - Comparison of Product Specific Costs (c_P) [EUR/GJ]:")
print(tabulate(CP_df.reset_index(), headers="keys", tablefmt="psql", floatfmt=".3f"))
