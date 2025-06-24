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

# Define the CEPCI values for cost correction.
CEPCI_2013 = 567.3
CEPCI_2023 = 797.9
CEPCI_factor = CEPCI_2023 / CEPCI_2013

# Define default values for electricity price and full load hours.
default_elec_price = 40.0   # cent/kWh
default_tau = 5500          # hours/year

# Define economic parameters.
r_n = 0.02                  # Cost elevation rate
i_eff = 0.08                # Interest rate
n = 20                      # Number of years
omc_relative = 0.03         # Relative operation and maintenance costs (compared to PEC)

# Boolean flag to decide if sensitivity analysis should be performed.
perform_sensitivity_analysis = False  # Set to False to run a single default case.

def run_exergoeco_analysis(elec_price_cent_kWh, tau):
    """
    Reload the exergy analysis from the JSON file, calculate PEC (with cost correction),
    multiply PEC by 6.32 to obtain the Total Capital Investment (TCI), and run economic
    and exergoeconomic analyses using the given electricity price and full load hours.
    
    Returns the component results DataFrame and other result DataFrames from the exergoeconomic analysis.
    
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
    product = {"inputs": ['42'], "outputs": ['41']}
    loss = {"inputs": ['12'], "outputs": ['11']}
    
    # Run the exergy analysis.
    ean.analyse(E_F=fuel, E_P=product, E_L=loss)
    ean.exergy_results(print_results=True)
    
    # ------------------------------
    # PEC Calculation Using Class-Based Correlations with cost correction
    # ------------------------------
    PEC_computed = {}
    for comp in ean.components.values():
        name = comp.name
        PEC = 0.0  # Default PEC
        # --- Heat Exchangers ---
        if isinstance(comp, HeatExchanger):
            A = comp.A  # surface area
            if A is not None:
                PEC = 15526 * (A / 42)**0.8
            else:
                PEC = 0.0
            # Adjust PEC from 2013 to 2023 costs.
            PEC *= CEPCI_factor
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
            PEC *= CEPCI_factor  # Adjust PEC cost.
            PEC_computed[name] = PEC
        
        # --- Valves ---
        elif isinstance(comp, Valve):
            PEC_computed[name] = 0.0
        
        # --- Other components ---
        else:
            PEC_computed[name] = 0.0
    
    # Process Motors using the specific correlation for electrical input power.
    for comp in ean.components.values():
        if isinstance(comp, Motor):
            name = comp.name
            # Retrieve the electrical input power X from the attribute "energy_flow_1"
            X = getattr(comp, 'energy_flow_1', None)
            if X is not None:
                PEC = 10710 * (X / 250000)**0.65
                PEC *= CEPCI_factor  # Adjust PEC cost.
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
        'i_eff': i_eff,
        'n': n,
        'r_n': r_n
    }
    components_order = list(PEC_computed.keys())
    PEC_list = [PEC_computed[comp] for comp in components_order]
    # Multiply each PEC by 6.32 to obtain TCI.
    TCI_list = [pec * 6.32 for pec in PEC_list]
    OMC_relative = [omc_relative if pec > 0 else 0.0 for pec in TCI_list]
    
    econ_analysis = EconomicAnalysis(econ_pars)
    Z_CC, Z_OMC, Z_total = econ_analysis.compute_component_costs(TCI_list, OMC_relative)

    # Create a DataFrame to display PEC, TCI, annual OMC, and Z for each component
    component_costs_df = pd.DataFrame({
        'Component': components_order,
        'PEC [EUR]': [round(pec, 2) for pec in PEC_list],
        'CC [EUR]': [round(tci, 2) for tci in TCI_list],
        'Z_CC [EUR/h]': [round(z_cc, 2) for z_cc in Z_CC],
        'Z_OMC [EUR/h]': [round(omc, 2) for omc in Z_OMC],
        'Z [EUR/h]': [round(z, 2) for z in Z_total]
    })

    # Calculate totals
    total_pec = sum(PEC_list)
    total_tci = sum(TCI_list)
    total_z_cc = sum(Z_CC)
    total_z_omc = sum(Z_OMC)
    total_z = sum(Z_total)

    # Add a total row
    component_costs_df.loc[len(component_costs_df)] = [
        'TOTAL', 
        round(total_pec, 2), 
        round(total_tci, 2), 
        round(total_z_cc, 2), 
        round(total_z_omc, 2),
        round(total_z, 2)
    ]

    # Print the component costs table without separators
    print("\nComponent Investment Costs (Year 2023):")
    print(tabulate(component_costs_df, headers="keys", tablefmt="psql", floatfmt=".2f"))

    # Build the exergoeconomic cost dictionary.
    Exe_Eco_Costs = {}
    for comp, z in zip(components_order, Z_total):
        Exe_Eco_Costs[f"{comp}_Z"] = z
    Exe_Eco_Costs["11_c"] = 0.0
    Exe_Eco_Costs["41_c"] = 0.0
    Exe_Eco_Costs["E1_c"] = elec_cost_eur_per_GJ
    
    # ------------------------------
    # Exergoeconomic Analysis
    # ------------------------------
    exergoeco_analysis = ExergoeconomicAnalysis(ean)
    exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
    # Unpack four DataFrames; we only use the component results.
    df_comp, df_mat1, df_mat2, df_non_mat = exergoeco_analysis.exergoeconomic_results()
    
    return df_comp, df_mat1, df_mat2, df_non_mat

# ------------------------------------------------------------------------------
# Sensitivity Analysis Execution
# ------------------------------------------------------------------------------
if perform_sensitivity_analysis:
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
            df_comp, _, _, _ = run_exergoeco_analysis(elec_price, tau)
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
else:
    # If sensitivity analysis is disabled, run the analysis for a single default case.
    print(f"\n --- Exergoeconomic analysis for the case with electricity price = {default_elec_price} cent/kWh and tau = {default_tau} hours/year --- \n")
    df_comp, df_mat1, df_mat2, df_non_mat = run_exergoeco_analysis(default_elec_price, default_tau)
    
    # Ensure there is a "Component" column; if not, use the index.
    if "Component" not in df_comp.columns:
        df_comp = df_comp.reset_index().rename(columns={"index": "Component"})
    
    # Extract the total Z costs from the "TOT" row.
    total_Z_cost = (df_comp.loc[df_comp["Component"] == "TOT", "Z [EUR/h]"].values[0]
                    if "TOT" in df_comp["Component"].values else np.nan)
    
    # Sum the costs for the inlet power flows (components "E1" and "E2").
    inlet_cost = df_non_mat[df_non_mat["Connection"].isin(["E1", "E2"])]["C^TOT [EUR/h]"].sum()
    
    # Extract the product-specific cost (assumed available in the "TOT" row, column "C_P [EUR/h]").
    product_cost = (df_comp.loc[df_comp["Component"] == "TOT", "C_P [EUR/h]"].values[0]
                    if "TOT" in df_comp["Component"].values else np.nan)
        
    # Print the extracted values.
    print("Investment costs (Z) [EUR/h]:", round(total_Z_cost, 2))
    print("Fuel costs (E1+E2) [EUR/h]:", round(inlet_cost, 2))
    print("Product cost (C_P) [EUR/h]:", round(product_cost, 2))

import matplotlib.pyplot as plt

# ---- before plotting, drop all valves by name ----
df_plot = df_comp[~df_comp['Component'].str.contains('VAL2')].copy()
df_plot = df_plot[~df_plot['Component'].str.contains('VAL1')].copy()

# Extract data
components = df_plot['Component']
ε_vals      = df_plot['ε [%]']
f_vals      = df_plot['f [%]']
Z_vals      = df_plot['Z [EUR/h]']

# Compute marker areas and per-point radii
max_marker_area = 600    # points^2
areas = (Z_vals / Z_vals.max()) * max_marker_area
radii = np.sqrt(areas / np.pi)    # radius in points

# Plot
plt.figure(figsize=(12, 6))
plt.scatter(ε_vals, f_vals, s=areas, edgecolors='w',  color='#BE2528')

# Annotate each point to the NE, offset by its radius + a small margin
for x, y, label, r in zip(ε_vals, f_vals, components, radii):
    offset = r + 2   # 2 points padding
    plt.annotate(
        label,
        xy=(x, y),
        xytext=(offset, -offset),
        textcoords='offset points',
        ha='left',
        va='bottom',
        fontsize=10
    )

plt.xlabel('Exergetic efficiency [%]')
plt.ylabel('Exergoeconomic Factor [%]')
plt.title('Component‐wise Exergoeconomic Analysis')
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.xlim(0, 100)
plt.ylim(0, 100)

component_colors = {
    # compressors (blue tones)
    "COMP1":      "#118cff",
    "COMP2":      "#4aa7fd",
    # motors (cyan tones)
    "MOT1":       "#ceb200",
    "MOT2":       "#f5da2d",
    # valves (orange tones)
    "VAL1":       "#009c63",
    "VAL2":       "#2ae09d",
    # heat exchangers (green/red tones)
    "AIR_HX":     "#d3291d",
    "IHX":        "#e44f44",
    "STEAM_GEN":  "#ff7e7e",
    # TOTAL if you ever include it
    "TOT":        "#000000",
}

# 1) Drop TOTAL once for both
df_base = df_comp[df_comp['Component'] != 'TOT']

# 2) Compute sort order by descending ED
sort_order = (
    df_base
      .sort_values('E_D [kW]', ascending=False)['Component']
      .tolist()
)

# 3) ED‐plot: all components, in ED‐order
df_ed_plot = (
    df_base
      .set_index('Component')
      .loc[sort_order]         # use bracket-list here
      .reset_index()
)

# 4) Z‐plot: drop VAL1/VAL2, then apply same order minus valves
keep_for_z = [c for c in sort_order if c not in ('VAL1','VAL2')]
df_z_plot = (
    df_base[~df_base['Component'].str.contains('VAL1|VAL2')]
      .set_index('Component')
      .loc[keep_for_z]        # <<< brackets, not parentheses
      .reset_index()
)

# 5) Extract and color
comp_ed = df_ed_plot['Component']
ED_vals = df_ed_plot['E_D [kW]']
colors_ed = [component_colors[c] for c in comp_ed]

comp_z = df_z_plot['Component']
Z_vals  = df_z_plot['Z [EUR/h]']
colors_z  = [component_colors[c] for c in comp_z]

# 6) Plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

ax1.bar(comp_ed, ED_vals, color=colors_ed)
ax1.set_xlabel('Component')
ax1.set_ylabel(r'$\dot{E}_D$ [kW]')
ax1.set_title(r'Exergy Destruction $\dot{E}_D$')
ax1.tick_params(axis='x', labelrotation=45)
plt.setp(ax1.get_xticklabels(), ha='right')
ax1.grid(True, linestyle='--', alpha=0.5)

ax2.bar(comp_z, Z_vals, color=colors_z)
ax2.set_xlabel('Component')
ax2.set_ylabel(r'$\dot{Z}$ [EUR/h]')
ax2.set_title(r'Cost Rate $\dot{Z}$')
ax2.tick_params(axis='x', labelrotation=45)
plt.setp(ax2.get_xticklabels(), ha='right')
ax2.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig("examples/hightemp_hp/plots/ebsilon_combined_Z_ED.png", dpi=300)