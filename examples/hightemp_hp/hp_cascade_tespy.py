from tespy.components import Compressor, Source, Sink, CycleCloser, HeatExchanger, Pump, Valve
from tespy.connections import Connection, Ref, Bus
from tespy.networks import Network
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis, EconomicAnalysis

import os
import logging
import pandas as pd
from tabulate import tabulate
import numpy as np

nw = Network(T_unit="C", p_unit="bar", h_unit="kJ / kg", m_unit="kg / s", iterinfo=False)

air_in = Source("air inlet")
air_out = Sink("air outlet")

water_in = Source("water inlet")
water_out = Sink("water outlet")

air_hx = HeatExchanger("AIR_HX")
comp1 = Compressor("COMP1")
valve1 = Valve("VAL1")
cc1 = CycleCloser("cc")

ihx = HeatExchanger("IHX")

steam_gen = HeatExchanger("STEAM_GEN")
comp2 = Compressor("COMP2")
valve2 = Valve("VAL2")
cc2 = CycleCloser("cc2")

c11 = Connection(air_in, "out1", air_hx, "in1", label="11")
c12 = Connection(air_hx, "out1", air_out, "in1", label="12")

c21 = Connection(air_hx, "out2", comp1, "in1", label="21")
c22 = Connection(comp1, "out1", ihx, "in1", label="22")
c22c = Connection(ihx, "out1", cc1, "in1", label="22c")
c23 = Connection(cc1, "out1", valve1, "in1", label="23")
c24 = Connection(valve1, "out1", air_hx, "in2", label="24")

c31 = Connection(ihx, "out2", comp2, "in1", label="31")
c32 = Connection(comp2, "out1", steam_gen, "in1", label="32")
c32c = Connection(steam_gen, "out1", cc2, "in1", label="32c")
c33 = Connection(cc2, "out1", valve2, "in1", label="33")
c34 = Connection(valve2, "out1", ihx, "in2", label="34")

c41 = Connection(water_in, "out1", steam_gen, "in2", label="41")
c42 = Connection(steam_gen, "out2", water_out, "in1", label="42")

nw.add_conns(c21, c22, c22c, c23, c24)
nw.add_conns(c11, c12)
nw.add_conns(c31, c32, c32c, c33, c34)
nw.add_conns(c41, c42)

c11.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=20, p=1.013)
c12.set_attr(T=15)

c21.set_attr(fluid={"R245FA": 1}, h=417)
c22.set_attr(p=6.4)
c23.set_attr(h=290)
c24.set_attr(p=0.823)

c31.set_attr(fluid={"R1233zdE": 1}, h=451)
c32.set_attr(p=17.5)
c33.set_attr(h=364)
c34.set_attr(p=4.1)

c41.set_attr(fluid={"water": 1}, T=120, p=2, m=1)
c42.set_attr(h=2706)

comp1.set_attr(eta_s=0.8)
comp2.set_attr(eta_s=0.8)

steam_gen.set_attr(pr1=1, pr2=1)
air_hx.set_attr(pr1=1, pr2=1)
ihx.set_attr(pr1=1, pr2=1)

nw.solve("design")

c21.set_attr(h=None, Td_bp=5)
c23.set_attr(h=None)
c24.set_attr(p=None)
c31.set_attr(h=None, Td_bp=5)
c33.set_attr(h=None)
c42.set_attr(h=None, x=1)

air_hx.set_attr(ttd_l=5)
ihx.set_attr(ttd_l=5)
steam_gen.set_attr(ttd_l=5)

power_input = Bus("power input")
power_input.add_comps(
    {"comp": comp1, "base": "bus", "char": 0.985},
    {"comp": comp2, "base": "bus", "char": 0.985}
)

nw.add_busses(power_input)

nw.solve("design")
nw.print_results()

Q_out = c42.m.val * (c42.h.val - c41.h.val)
COP2 = c42.m.val * (c42.h.val - c41.h.val) / (comp2.P.val*1e-3)
COP1 = c31.m.val * (c31.h.val - c34.h.val) / (comp1.P.val*1e-3)
COP = c42.m.val * (c42.h.val - c41.h.val) / (power_input.P.val*1e-3)

print("Q = ", round(Q_out, 1), "kW")
print("COP = ", round(COP, 3))
print("COP1 = ", round(COP1, 3))
print("COP2 = ", round(COP2, 3))

# assert convergence of calculation
nw._convergence_check()

# %% ambient conditions
p0 = c11.T.val * 1e5
T0 = c11.p.val + 273.15

# %% economic parameters
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

# %% Exergoeconomic analysis
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
    ean = ExergyAnalysis.from_tespy(nw, T0, p0, split_physical_exergy=True)
    
    # Define exergy streams.
    fuel = {
        "inputs": [
            'power input__motor_of_COMP1',
            'power input__motor_of_COMP2'
        ],
        "outputs": []
    }

    product = {
        "inputs": ['42'],
        "outputs": ['41']
    }

    loss = {
        "inputs": ['12'],
        "outputs": ['11']
    }
    
    # Run the exergy analysis.
    ean.analyse(E_F=fuel, E_P=product, E_L=loss)
    ean.exergy_results(print_results=True)
    
    # 1) Seed with every Exerpy component at zero cost
    PEC_computed = { comp.name: 0.0 for comp in ean.components.values() }

    # 2) Build a lookup of TESPy objects by label for quick access
    tespy_by_label = nw.comps["object"].to_dict()

    # 3) Your heat‐exchanger k‐values
    k_lookup = {
        "AIR_HX":    48.387,
        "IHX":      750.000,
        "STEAM_GEN":1153.846
    }

    for name, comp in nw.comps["object"].items():
        if name not in PEC_computed:
            # this TESPy comp doesn't appear in the exerpy analysis → skip
            continue

        PEC = 0.0  # Default PEC
        # --- Heat Exchangers ---
        if comp.__class__.__name__ == "HeatExchanger":
            kA = comp.kA.val if hasattr(comp.kA, "val") else getattr(comp, "kA", 0.0)
            if kA:
                k = k_lookup.get(name)
                if k is None:
                    raise KeyError(f"No k-value defined for heat exchanger '{name}'")
                A = kA / k
                PEC = 15526 * (A / 42)**0.8 * CEPCI_factor
            else:
                PEC = 0.0
            PEC_computed[name] = PEC
        
        # --- Compressors (and Fans) ---
        elif comp.__class__.__name__ == "Compressor":
            VM = comp.inl[0].property_data['v'].val
            PEC = 19850 * ((VM * 3600) / 279.8)**0.73
            PEC *= CEPCI_factor  # Adjust PEC cost.
            PEC_computed[name] = PEC
        
        # --- Valves ---
        elif comp.__class__.__name__ == "Valve":
            PEC_computed[name] = 0.0
        
        # --- Other components ---
        else:
            PEC_computed[name] = 0.0
    
    '''# Process Motors using the specific correlation for electrical input power.
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
            PEC_computed[name] = PEC'''
    
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
    Exe_Eco_Costs["power input__motor_of_COMP1_c"] = elec_cost_eur_per_GJ
    
    # ------------------------------
    # Exergoeconomic Analysis
    # ------------------------------
    exergoeco_analysis = ExergoeconomicAnalysis(ean)
    exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
    # Unpack four DataFrames; we only use the component results.
    df_comp, df_mat1, df_mat2, df_non_mat = exergoeco_analysis.exergoeconomic_results()
    
    return df_comp, df_mat1, df_mat2, df_non_mat

print(f"\n --- Exergoeconomic analysis for the case with electricity price = {default_elec_price} cent/kWh and tau = {default_tau} hours/year --- \n")
df_comp, df_mat1, df_mat2, df_non_mat = run_exergoeco_analysis(default_elec_price, default_tau)