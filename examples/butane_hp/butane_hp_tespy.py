import numpy as np
from CoolProp.CoolProp import PropsSI as PSI
from tespy.components import (
    Compressor,
    CycleCloser,
    HeatExchanger,
    Merge,
    Motor,
    MovingBoundaryHeatExchanger,
    PowerSource,
    Sink,
    Source,
    Splitter,
    Valve,
)
from tespy.connections import Connection, PowerConnection
from tespy.networks import Network

# "Bus" Parameters
# Heat source
T_ev_in = 25
T_ev_out = 15
p_ev = 1
# Water/steam side
T_co_in = 45
T_co_out = 105
p_co = 1
# T_co_out = 65
# p_co = 0.2

# Default component parameters
td_pinch = 5
td_dew = 5
eta_s = 0.8

wf = "Butane"

# Preliminary calculations, actually optimization variables...
p_ev_wf = PSI("P", "Q", 1, "T", T_ev_out - td_pinch + 273.15, wf) * 1e-5
# p_co_wf = PSI('P', 'Q', 0, 'T', PSI('T', 'Q', 1, 'P', p_co * 1e5, 'water') + td_pinch, wf) * 1e-5
p_co_wf = (
    PSI("P", "Q", 0, "T", PSI("T", "Q", 1, "P", p_co * 1e5, "water") + td_pinch + td_dew, wf) * 1e-5
)  # hier müsste der Druck wirklich sukzessive gesenkt werden...
pr_tot = p_co_wf / p_ev_wf
pr_per_stage = np.power(pr_tot, 1 / 2)
p_mid_wf = p_ev_wf * pr_per_stage

# Create the network
nw = Network(T_unit="C", p_unit="bar", h_unit="kJ / kg", m_unit="t / h", iterinfo=False)

# Create the components
# Ammonia cycle
compressor_1 = Compressor("Compressor 1")
compressor_2 = Compressor("Compressor 2")
evaporator = HeatExchanger("Evaporator")
expansion_valve_1 = Valve("Expansion Valve 1")
expansion_valve_2 = Valve("Expansion Valve 2")
cycle_closer = CycleCloser("Cycle Closer")
condenser = MovingBoundaryHeatExchanger("Condenser")
splitter = Splitter("Splitter")
merge = Merge("Merge")
economizer = MovingBoundaryHeatExchanger("Economizer")

# Water/steam side
water_in = Source("Water In")
steam_out = Sink("Steam Out")

# Heat source
heat_source_in = Source("Heat Source In")
heat_source_out = Sink("Heat Source Out")

motor_1 = Motor("Motor 1")
motor_2 = Motor("Motor 2")
grid_1 = PowerSource("Grid 1")
grid_2 = PowerSource("Grid 2")

# Create connections
# Ammonia cycle
c1 = Connection(cycle_closer, "out1", compressor_1, "in1", label="01")
c2 = Connection(compressor_1, "out1", merge, "in1", label="02")
c3 = Connection(merge, "out1", compressor_2, "in1", label="03")
c4 = Connection(compressor_2, "out1", condenser, "in1", label="04")
c5 = Connection(condenser, "out1", splitter, "in1", label="05")
c5a = Connection(splitter, "out1", economizer, "in1", label="05a")
c6 = Connection(economizer, "out1", expansion_valve_1, "in1", label="06")
c7 = Connection(expansion_valve_1, "out1", evaporator, "in2", label="07")
c0cc = Connection(evaporator, "out2", cycle_closer, "in1", label="07cc")
c5b = Connection(splitter, "out2", expansion_valve_2, "in1", label="05b")
c8 = Connection(expansion_valve_2, "out1", economizer, "in2", label="08")
c9 = Connection(economizer, "out2", merge, "in2", label="09")

# Water/steam side
c10 = Connection(water_in, "out1", condenser, "in2", label="10")
c11 = Connection(condenser, "out2", steam_out, "in1", label="11")

# Heat source
c20 = Connection(heat_source_in, "out1", evaporator, "in1", label="20")
c21 = Connection(evaporator, "out1", heat_source_out, "in1", label="21")

# Power connections
e01 = PowerConnection(grid_1, "power", motor_1, "power_in", label="E1")
w01 = PowerConnection(motor_1, "power_out", compressor_1, "power", label="W1")
e02 = PowerConnection(grid_2, "power", motor_2, "power_in", label="E2")
w02 = PowerConnection(motor_2, "power_out", compressor_2, "power", label="W2")

# Add connections to network
nw.add_conns(c1, c2, c3, c4, c5, c5a, c5b, c6, c7, c8, c9, c0cc, c10, c11, c20, c21, e01, e02, w01, w02)

# Set component parameters
compressor_1.set_attr(eta_s=eta_s)
compressor_2.set_attr(eta_s=eta_s)
condenser.set_attr(pr1=1, pr2=1, td_pinch=td_pinch)
evaporator.set_attr(pr1=1, pr2=1, ttd_min=td_pinch)
economizer.set_attr(pr1=1, pr2=1, td_pinch=td_pinch)
motor_1.set_attr(eta=0.985)
motor_2.set_attr(eta=0.985)

# Set connection parameters
# Water/steam side
c10.set_attr(fluid={"water": 1}, p=p_co, T=T_co_in, m=1)  # Water inlet
c11.set_attr(T=T_co_out)  # Steam outlet

# Heat source
c20.set_attr(fluid={"air": 1}, p=p_ev, T=T_ev_in)  # Heat source inlet
c21.set_attr(T=T_ev_out)  # Heat source outlet

# Butane cycle
c7.set_attr(fluid={wf: 1})  # Pure butane
c1.set_attr(p=p_ev_wf)
c2.set_attr(p=p_mid_wf)
c4.set_attr(p=p_co_wf)

# Generate starting values
condenser.set_attr(td_pinch=None)
evaporator.set_attr(ttd_min=None)
economizer.set_attr(td_pinch=None)

c1.set_attr(T=T_ev_in - td_pinch)
c4.set_attr(td_dew=td_dew)
c5.set_attr(T=T_co_in + td_pinch)
c6.set_attr(T=T_co_in)
nw.solve("design")

# Solve real design
condenser.set_attr(td_pinch=td_pinch)  # For condenser
c5.set_attr(T=None)
evaporator.set_attr(ttd_min=td_pinch)
c1.set_attr(T=None)
economizer.set_attr(td_pinch=td_pinch)
c6.set_attr(T=None)

nw.solve("design")

# Exergy analysis via ExerPy
from exerpy import ExergyAnalysis

p0 = 1.000e5
T0 = 25 + 273.15

ean = ExergyAnalysis.from_tespy(nw, Tamb=T0, pamb=p0, split_physical_exergy=True)
fuel = {"inputs": ["E1", "E2"], "outputs": []}
product = {"inputs": ["11"], "outputs": ["10"]}
loss = {"inputs": ["21"], "outputs": ["20"]}
ean.analyse(E_F=fuel, E_P=product, E_L=loss)
df_component_results, df_material_connection_results, df_non_material_connection_results = ean.exergy_results(
    print_results=False
)

from exerpy import EconomicAnalysis, ExergoeconomicAnalysis

# Define the CEPCI values for cost correction.
CEPCI_2013 = 567.3
CEPCI_2023 = 797.9
CEPCI_factor = CEPCI_2023 / CEPCI_2013

# Define values for electricity price and full load hours.
elec_price_cent_kWh = 40.0  # cent/kWh
tau = 5500  # hours/year

# Define economic parameters.
r_n = 0.02  # Cost elevation rate
i_eff = 0.08  # Interest rate
n = 20  # Number of years
omc_relative = 0.03  # Relative operation and maintenance costs (compared to PEC)

import pandas as pd
from tabulate import tabulate

k_lookup = {"Evaporator": 100, "Economizer": 750, "Condenser": 1000}

PEC_computed = {}
for comp in nw.comps["object"]:
    name = comp.label
    PEC = 0.0  # Default PEC
    # --- Heat Exchangers ---
    if isinstance(comp, (HeatExchanger, MovingBoundaryHeatExchanger)):
        kA = getattr(comp.kA, "val", 0.0)
        if kA:
            k = k_lookup.get(name)
            if k is None:
                raise KeyError(f"No k-value defined for heat exchanger '{name}'")
            A = kA / k
            PEC = 15526 * (A / 42) ** 0.8 * CEPCI_factor
        else:
            PEC = 0.0
        PEC_computed[name] = PEC

    # --- Compressors (and Fans) ---
    elif isinstance(comp, Compressor):
        VM = getattr(comp.inl[0].v, "val", 0.0)
        PEC = 19850 * ((VM * 3600) / 279.8) ** 0.73
        PEC *= CEPCI_factor  # Adjust PEC cost.
        PEC_computed[name] = PEC

    # --- Other components ---
    else:
        PEC_computed[name] = 0.0


for comp in ean.components.values():
    if comp.__class__.__name__ == "Motor":
        name = comp.name
        # Retrieve the electrical input power X from the attribute "energy_flow_1"
        X = getattr(comp, "E_F", None)
        if X is not None:
            PEC = 10710 * (X / 250000) ** 0.65
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

econ_pars = {"tau": tau, "i_eff": i_eff, "n": n, "r_n": r_n}
components_order = list(PEC_computed.keys())
PEC_list = [PEC_computed[comp] for comp in components_order]
# Multiply each PEC by 6.32 to obtain TCI.
TCI_list = [pec * 6.32 for pec in PEC_list]
OMC_relative = [omc_relative if pec > 0 else 0.0 for pec in TCI_list]

econ_analysis = EconomicAnalysis(econ_pars)
Z_CC, Z_OMC, Z_total = econ_analysis.compute_component_costs(TCI_list, OMC_relative)

# Create a DataFrame to display PEC, TCI, annual OMC, and Z for each component
component_costs_df = pd.DataFrame(
    {
        "Component": components_order,
        "PEC [EUR]": [round(pec, 2) for pec in PEC_list],
        "CC [EUR]": [round(tci, 2) for tci in TCI_list],
        "Z_CC [EUR/h]": [round(z_cc, 2) for z_cc in Z_CC],
        "Z_OMC [EUR/h]": [round(omc, 2) for omc in Z_OMC],
        "Z [EUR/h]": [round(z, 2) for z in Z_total],
    }
)

# Calculate totals
total_pec = sum(PEC_list)
total_tci = sum(TCI_list)
total_z_cc = sum(Z_CC)
total_z_omc = sum(Z_OMC)
total_z = sum(Z_total)

# Add a total row
component_costs_df.loc[len(component_costs_df)] = [
    "TOTAL",
    round(total_pec, 2),
    round(total_tci, 2),
    round(total_z_cc, 2),
    round(total_z_omc, 2),
    round(total_z, 2),
]

# Print the component costs table without separators
print("\nComponent Investment Costs (Year 2023):")
print(tabulate(component_costs_df, headers="keys", tablefmt="psql", floatfmt=".2f"))

# Build the exergoeconomic cost dictionary.
Exe_Eco_Costs = {}
for comp, z in zip(components_order, Z_total, strict=False):
    Exe_Eco_Costs[f"{comp}_Z"] = z
Exe_Eco_Costs["10_c"] = 0.0
Exe_Eco_Costs["20_c"] = 0.0
Exe_Eco_Costs["E2_c"] = elec_cost_eur_per_GJ

# ------------------------------
# Exergoeconomic Analysis
# ------------------------------
exergoeco_analysis = ExergoeconomicAnalysis(ean)
exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
# Unpack four DataFrames; we only use the component results.
df_comp, df_mat1, df_mat2, df_non_mat = exergoeco_analysis.exergoeconomic_results()
