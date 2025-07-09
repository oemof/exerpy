from tespy.components import Compressor, Source, Sink, CycleCloser, Pump, Valve, PowerBus, PowerSource, Motor
from tespy.components import MovingBoundaryHeatExchanger as HeatExchanger
from tespy.connections import Connection, Ref, PowerConnection
from tespy.networks import Network
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis, EconomicAnalysis

import os
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = 'browser'
from tabulate import tabulate
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.patches as patches

import logging
logging.disable(logging.CRITICAL)

import matplotlib as mpl

mpl.rcParams['font.family'] = 'Aptos (body)'

mpl.rcParams['font.size'] = 14

mpl.rcParams['axes.titlesize']     = 16   # title text
mpl.rcParams['axes.labelsize']     = 14   # x/y axis labels
mpl.rcParams['xtick.labelsize']    = 12   # x-tick labels
mpl.rcParams['ytick.labelsize']    = 12   # y-tick labels
mpl.rcParams['legend.fontsize']    = 12   # legend text
mpl.rcParams['figure.titlesize']   = 18   # figure suptitle, if used

component_colors = {
    # compressors (blue tones)
    "COMP1":      "#118cff",
    "COMP2":      "#118cff",
    # motors (cyan tones)
    "MOT1":       "#ceb200",
    "MOT2":       "#ceb200",
    # valves (orange tones)
    "VAL1":       "#009c63",
    "VAL2":       "#009c63",
    # heat exchangers (green/red tones)
    "AIR_HX":     "#d3291d",
    "IHX":        "#e44f44",
    "STEAM_GEN":  "#ff7e7e",
}


def run_exergoeco_analysis(elec_price_cent_kWh, tau, i_eff, Tamb, print_results=False, **kwargs):
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
    ean = ExergyAnalysis.from_tespy(nw, Tamb+273.15, pamb*1e5, split_physical_exergy=True)

    # Define exergy streams.

    fuel = {
        "inputs": [
            'e1', 'e4'
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
    ean.exergy_results(print_results=print_results)

    # 1) Seed with every Exerpy component at zero cost
    PEC_computed = { comp.name: 0.0 for comp in ean.components.values() }

    # 2) Build a lookup of TESPy objects by label for quick access
    tespy_by_label = nw.comps["object"].to_dict()

    # 3) Heat‐exchanger k‐values
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
        if comp.__class__.__name__ == "HeatExchanger" or comp.__class__.__name__ == "MovingBoundaryHeatExchanger":
            UA = comp.UA.val if hasattr(comp.UA, "val") else getattr(comp, "UA", 0.0)
            if UA:
                k = k_lookup.get(name)
                if k is None:
                    raise KeyError(f"No k-value defined for heat exchanger '{name}'")
                A = UA / k
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

    # Process Motors using the specific correlation for electrical input power.
    for comp in ean.components.values():
        if comp.__class__.__name__ == "Motor":
            name = comp.name
            # Retrieve the electrical input power X from the attribute "energy_flow_1"
            X = getattr(comp, 'E_F', None)
            if X is not None:
                PEC = 10710 * (X / 250000)**0.65
                PEC *= CEPCI_factor  # Adjust PEC cost.
            else:
                PEC = 0.0
            PEC_computed[name] = PEC

    # Economic Analysis
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

    if print_results:
        # Print the component costs table without separators
        print("\nComponent Investment Costs (Year 2023):")
        print(tabulate(component_costs_df, headers="keys", tablefmt="psql", floatfmt=".2f"))

    # Build the exergoeconomic cost dictionary.
    Exe_Eco_Costs = {}
    for comp, z in zip(components_order, Z_total):
        Exe_Eco_Costs[f"{comp}_Z"] = z
    Exe_Eco_Costs["11_c"] = 0.0
    Exe_Eco_Costs["41_c"] = 0.0
    Exe_Eco_Costs["e1_c"] = elec_cost_eur_per_GJ

    # Exergoeconomic Analysis
    exergoeco_analysis = ExergoeconomicAnalysis(ean)
    exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
    # Unpack four DataFrames; we only use the component results.
    df_comp, df_mat1, df_mat2, df_non_mat = exergoeco_analysis.exergoeconomic_results(print_results=True)

    return df_comp, df_mat1, df_mat2, df_non_mat, PEC_list, TCI_list, components_order

# Main script starts here

##################################################
# 1. TESPy Simulation of High-Temperature Heat Pump
##################################################

nw = Network(T_unit="C", p_unit="bar", h_unit="kJ / kg", m_unit="kg / s")

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

power_input1 = PowerSource("grid1")
power_input2 = PowerSource("grid2")
distribution = PowerBus("electricity distribution", num_in=1, num_out=2)
motor1 = Motor("MOT1")
motor2 = Motor("MOT2")

e1 = PowerConnection(power_input1, "power", motor1, "power_in", label="e1")
# e2 = PowerConnection(distribution, "power_out1", motor1, "power_in", label="e2")
e3 = PowerConnection(motor1, "power_out", comp1, "power", label="e3")
e4 = PowerConnection(power_input2, "power", motor2, "power_in", label="e4")
e5 = PowerConnection(motor2, "power_out", comp2, "power", label="e5")

nw.add_conns(e1, e3, e4, e5)

# Simulation with starting values

c11.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=20, p=1.013)
c12.set_attr(T=Ref(c11, 1, -5))

c21.set_attr(fluid={"R245FA": 1}, Td_bp=5)
c22.set_attr(p=6.4)
c23.set_attr(Td_bp=-5)
c24.set_attr(p=0.823)

c31.set_attr(fluid={"R1233zdE": 1}, Td_bp=5)
c32.set_attr(p=17.5)
c33.set_attr(x=0)
c34.set_attr(T=60)

c41.set_attr(fluid={"water": 1}, p=2, x=0, m=1)
c42.set_attr(x=1)

comp1.set_attr(eta_s=0.8)
comp2.set_attr(eta_s=0.8)

steam_gen.set_attr(pr1=0.95, pr2=1)
air_hx.set_attr(pr1=1, pr2=0.95)
ihx.set_attr(pr1=0.95, pr2=0.95)

motor1.set_attr(eta=0.985)
motor2.set_attr(eta=0.985)

# Simulation with fixed values

nw.solve("design")

c22.set_attr(p=None)
c24.set_attr(p=None)
c32.set_attr(p=None)

air_hx.set_attr(ttd_l=5)
ihx.set_attr(ttd_l=5)
steam_gen.set_attr(ttd_l=5)

nw.solve("design")
nw.print_results()

Q_out = c42.m.val * (c42.h.val - c41.h.val)
COP2 = c42.m.val * (c42.h.val - c41.h.val) / (comp2.P.val*1e-3)
COP1 = c31.m.val * (c31.h.val - c34.h.val) / (comp1.P.val*1e-3)
COP = c42.m.val * (c42.h.val - c41.h.val) / (e1.E.val*1e-3 + e4.E.val*1e-3)

print("Q = ", round(Q_out, 1), "kW")
print("COP = ", round(COP, 3))
print("COP1 = ", round(COP1, 3))
print("COP2 = ", round(COP2, 3))

# assert convergence of calculation
# nw._convergence_check()

# ambient conditions
pamb = c11.p.val
Tamb = c11.T.val

# economic parameters
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

fuel = {
    "inputs": [
        'e1', 'e4',
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

####################################################
#  2. Sensitivity Analysis & Exergoeconomic Analysis
####################################################

# define range of evaporator outlet temperatures T34 [°C]
SENS_VAR    = r'$T_{34}$' # e.g. f'T_{34}', 'tau', 'i_eff', 'elec_price', 'ambient temperature'
SENS_VAR_savefig = 'T34'  # e.g. 'T34', 'tau', 'i_eff', 'elec_price', 'ambient temperature'
SENS_VALUES = np.arange(50, 81, 2)  # the array of values you want to sweep

def apply_sensitivity(var_name, value):
    if var_name == r'$T_{34}$':
        c34.set_attr(T=value)
    elif var_name == 'ambient temperature':
        c11.set_attr(T=value)
    elif var_name == 'tau':
        return {'tau': value}
    elif var_name == 'i_eff':
        return {'i_eff': value/100}
    elif var_name == 'elec_price':
        return {'elec_price': value}
    else:
        raise ValueError(f"Unknown sensitivity var {var_name!r}")


def run_sensitivity_analysis(var_name, values):
    results = {}
    for v in values:
        # 1) apply the change and collect any overrides
        extra_pars = apply_sensitivity(var_name, v) or {}

        # 2) merge defaults with overrides
        pars = dict(
            elec_price_cent_kWh=default_elec_price,
            tau=default_tau,
            n=n,
            i_eff=i_eff,
            Tamb=Tamb,
        )
        # map our sensitivity keys to function args
        if 'elec_price' in extra_pars:
            pars['elec_price_cent_kWh'] = extra_pars['elec_price']
        if 'tau' in extra_pars:
            pars['tau'] = extra_pars['tau']
        if 'i_eff' in extra_pars:
            pars['i_eff'] = extra_pars['i_eff']

        # 3) re-solve
        nw.solve('design')

        # 4) collect network‐level metrics
        COP   = c42.m.val * (c42.h.val - c41.h.val) / (e1.E.val * 1e-3 + e4.E.val * 1e-3)
        COP2  = c42.m.val * (c42.h.val - c41.h.val) / (comp2.P.val     * 1e-3)
        COP1  = c31.m.val * (c31.h.val - c34.h.val) / (comp1.P.val     * 1e-3)
        ean   = ExergyAnalysis.from_tespy(nw, Tamb+273.15, pamb*1e5, split_physical_exergy=True)
        ean.analyse(E_F=fuel, E_P=product, E_L=loss)
        eps   = ean.epsilon
        EF_tot, EP_tot, EL_tot = ean.E_F, ean.E_P, ean.E_L
        ED_tot = EF_tot - EP_tot - EL_tot

        # 5) run exergo-economic with all parameters
        df_comp, df_mat1, df_mat2, df_non_mat, PEC_list, TCI_list, comps = \
            run_exergoeco_analysis(**pars, print_results=False)

        # 6) extract system-level costs
        cP_tot = df_comp.loc[df_comp['Component']=='TOT','c_P [EUR/GJ]'].iloc[0]
        Z_tot  = df_comp.loc[df_comp['Component']=='TOT','Z [EUR/h]'].iloc[0]

        # 7) seed result dict with global metrics
        res = {
            'COP': COP,
            'COP1': COP1,
            'COP2': COP2,
            'epsilon': eps,
            'c_P': cP_tot,
            'Z_tot': Z_tot,
            'EP_tot': EP_tot,
            'ED_tot': ED_tot,
        }

        # 8) add module costs (TCI) and network connections, component-level econ
        for comp, tci in zip(comps, TCI_list):
            res[f"TCI_{comp}"] = tci
        res['TCI_total'] = sum(TCI_list)
        for lbl, row in nw.conns.loc[nw.conns["conn_type"] == "Connection"].iterrows():
            conn = row['object']
            res[f"m_{lbl}"] = conn.m.val
            res[f"p_{lbl}"] = conn.p.val
            res[f"T_{lbl}"] = conn.h.val
        for _, row in df_comp.iterrows():
            comp = row['Component']
            for col in df_comp.columns:
                if col == 'Component': continue
                key = f"{col}_{comp}".replace(' ', '_').replace('[','').replace(']','').replace('/','per')
                res[key] = row[col]

        results[v] = res

        # put the non-material DataFrame onto its Connection index
        non_mat = df_non_mat.set_index('Connection')

        # extract the total cost rates for the two electricity streams
        res['Ctot_e1'] = non_mat.loc['e1', 'C^TOT [EUR/h]']
        res['Ctot_e4'] = non_mat.loc['e4', 'C^TOT [EUR/h]']

    return pd.DataFrame.from_dict(results, orient='index')

df = run_sensitivity_analysis(SENS_VAR, SENS_VALUES)


#####################
# 3. Plots of Results
#####################

unit = {r'$T_{34}$':'[°C]', 'ambient temperature':'[°C]', 'tau':'[h/a]', 'i_eff':'[%/a]', 'elec_price':'[cent/kWh]'}[SENS_VAR]

# 1. Interactive Plotly Line Chart

'''fig = go.Figure()
for i, col in enumerate(df.columns):
    fig.add_trace(go.Scatter(
        x=df.index, y=df[col],
        name=col,
        visible=(i == 0)
    ))

# create dropdown buttons to toggle each metric
buttons = []
for i, col in enumerate(df.columns):
    vis = [False]*len(df.columns)
    vis[i] = True
    buttons.append(dict(
        method='update',
        label=col,
        args=[{'visible': vis},
              {'title': f'{col} vs. T34', 'yaxis': {'title': col}}]
    ))

fig.update_layout(
    updatemenus=[dict(
        active=0,
        buttons=buttons,
        x=0.0, y=1.15,
        xanchor='left', yanchor='top'
    )],
    title=f'{df.columns[0]} vs. T34',
    xaxis_title=f"{SENS_VAR} {unit}",
    yaxis_title=df.columns[0]
)
fig.show()'''


# 2. Normalized Scatter Plot

# plot Z_tot/EP_tot vs. ED_tot/EP_tot
x = df['ED_tot'] / df['EP_tot']
y = df['Z_tot'] / df['EP_tot'] / 3600 * 1e9

ax = plt.gca()   # get current Axes
ax.yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('%.1f'))

plt.figure(figsize=(8,4))
plt.scatter(x, y, marker='o', color='black', s=50, linewidth=0.5)
plt.xlabel(r'$E_{D,\text{tot}}/E_{P,\text{tot}}$ [-]')
plt.ylabel(r'$\dot{Z}_{\text{tot}}/E_{P,\text{tot}}$ [€/GJ$_\mathrm{ex}$]')
plt.title('Normalized investmenet costs and exergy destruction')
plt.grid(True)
plt.tight_layout()
plt.savefig(f"examples/hightemp_hp/plots/plot_normalized_scatter_{SENS_VAR_savefig}.png", dpi=300)


# 3. Stacked Bar Chart: Z per Component + COP Overlay

# select Z columns, exclude totals and valves
prefix = "Z_EURperh_"
z_cols = [
    c for c in df.columns
    if c.startswith(prefix)
    and not any(x in c for x in ("_TOT", "VAL1", "VAL2"))
]
# rename motors, strip prefix from others
rename_map = {}
for col in z_cols:
    rename_map[col] = col.replace(prefix, "")

plot_df = df[z_cols].rename(columns=rename_map)

fig, ax1 = plt.subplots(figsize=(8,4))
# 1) plot stacked bars
bar_width = 0.8
x = np.arange(len(plot_df))
plot_df.plot(
    kind="bar",
    stacked=True,
    ax=ax1,
    width=bar_width,
    color=[component_colors[c] for c in plot_df.columns],
    legend=False,
    zorder=1
)
ax1.set_xlabel(f"{SENS_VAR} {unit}")
ax1.set_ylabel(r"$\dot{Z}$ [€/h]")
ax1.set_ylim(0, plot_df.sum(axis=1).max() * 1.3)
ax1.tick_params(axis="x", rotation=0)
ax1.set_xticks(x)
ax1.set_xticklabels(plot_df.index.astype(str))

# 2) overlay COP on secondary y-axis
ax2 = ax1.twinx()
ax2.plot(
    x,
    df["COP"],
    marker="o",
    linestyle="-",
    linewidth=2,
    color='black',
    zorder=10
)
ax2.set_ylabel(r"COP [-]")
ax2.set_ylim(0, df["COP"].max()*1.1)

# 3) combined legend
bars_handles, bars_labels = ax1.get_legend_handles_labels()
line_handle, line_label  = ax2.get_legend_handles_labels()
ax1.legend(
    bars_handles + line_handle,
    bars_labels + line_label,
    title=r"Component",
    bbox_to_anchor=(1.13, 1),
    loc="upper left"
)

plt.tight_layout()
plt.savefig(f"examples/hightemp_hp/plots/plot_investment_columns_{SENS_VAR_savefig}.png", dpi=300)


# 4. 5×1 Vertical Multipanel: TCI & Metrics

t       = df.index.astype(int)
tci1    = df["TCI_COMP1"]*1e-6
tci2    = df["TCI_COMP2"]*1e-6
tci_tot = df["TCI_total"]*1e-6
cop = df["COP"]
cop1 = df["COP1"]
cop2 = df["COP2"]
cP_tot  = df["c_P"]
zdz_tot = df["C_D+Z_EURperh_TOT"]  # combined Z + cost destruction
epsilon = df["epsilon"]

fig, axs = plt.subplots(5, 1, sharex=True, figsize=(5, 14))

# (1) Total investment cost
axs[0].plot(t, tci_tot, marker="o", color='black')
axs[0].set_ylabel("TCI [M€]")
axs[0].set_title("Total capital investment")
axs[0].set_ylim(tci_tot.min() * 0.99, tci_tot.max() * 1.01)
axs[0].grid(True)

# (2) Investment costs of compressors
axs[1].plot(t, tci1, marker="o", label="COMP1", color=component_colors["COMP1"])
axs[1].plot(t, tci2, marker="s", label="COMP2", color=component_colors["COMP2"])
axs[1].set_ylabel("TCI [M€]")
axs[1].set_title("Investment costs of the compressors")
axs[1].legend(loc="best")
min_val = min(tci1.min(), tci2.min())
max_val = max(tci1.max(), tci2.max())
axs[1].set_ylim(min_val * 0.95, max_val * 1.05)
axs[1].grid(True)

# (3) Exergetic efficiency (%)
axs[2].plot(t, cop1, marker="o", label=r"COP$_\text{upper cycle}$", color='blue')
axs[2].plot(t, cop2, marker="s", label=r"COP$_\text{lower cycle}$", color='red')
axs[2].plot(t, cop, marker="o", label=r"COP$_\text{tot}$", color='black')
axs[2].set_ylim(1.5, 7.0)
axs[2].set_ylabel("COP [-]")
axs[2].set_title("COP")
axs[2].yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('%.1f'))
axs[2].legend(loc="best", ncol=2)
axs[2].grid(True)

# (4) Product cost c_P [€/GJ]
axs[3].plot(t, cP_tot, marker="o", color='black')
axs[3].set_ylabel(r"$c_P$ [€/GJ$_\mathrm{ex}$]")
axs[3].set_title("Specific product cost")
axs[3].grid(True)

# (5) epsilon
axs[4].plot(t, epsilon*100, marker="o", color='black')
axs[4].set_ylabel(r"$\varepsilon$ [%]")
axs[4].set_title(r"Exergetic efficiency")
axs[4].grid(True)

# shared x-axis label with LaTeX subscript and degree symbol
axs[4].set_xlabel(f"{SENS_VAR} {unit}")
axs[4].tick_params(axis="x", rotation=0)

plt.tight_layout()
plt.savefig(f"examples/hightemp_hp/plots/plot_multiplot_{SENS_VAR_savefig}.png", dpi=300)


# 5. Bar Chart of Exergy Destruction + ε Overlay

# select Z columns, exclude totals and valves
prefix = "E_D_kW_"
ed_cols = [
    c for c in df.columns
    if c.startswith(prefix) and not c.endswith("_TOT")
]
# rename motors, strip prefix from others
rename_map = {}
for col in ed_cols:
    rename_map[col] = col.replace(prefix, "")

plot_df = df[ed_cols].rename(columns=rename_map)

fig, ax1 = plt.subplots(figsize=(8,4))
bar_width = 0.8
x = np.arange(len(plot_df))

# 1) plot stacked bars
plot_df.plot(
    kind="bar",
    stacked=True,
    ax=ax1,
    width=bar_width,
    color=[component_colors[c] for c in plot_df.columns],
    legend=False,
    zorder=1
)
ax1.set_xlabel(f"{SENS_VAR} {unit}")
ax1.set_ylabel(r"Exergy destruction $\dot{E}_D$ [kW]")
ax1.set_ylim(0, plot_df.sum(axis=1).max() * 1.3)
ax1.tick_params(axis="x", rotation=0)
ax1.set_xticks(x)
ax1.set_xticklabels(plot_df.index.astype(str))

# 2) overlay ε on secondary y-axis
ax2 = ax1.twinx()
ax2.plot(
    x,
    df["epsilon"]*100,
    marker="o",
    linestyle="-",
    linewidth=2,
    color='black',
    zorder=10
)
ax2.set_ylabel(r"Exergetic efficiency $\varepsilon$ [%]")
ax2.set_ylim(df["epsilon"].min()*100*0.3, df["epsilon"].max()*100*1.1)

# 3) combined legend
bars_handles, bars_labels = ax1.get_legend_handles_labels()
line_handle, line_label  = ax2.get_legend_handles_labels()
ax1.legend(
    bars_handles + line_handle,
    bars_labels + line_label,
    title="Component",
    bbox_to_anchor=(1.13, 1),
    loc="upper left"
)

plt.tight_layout()
plt.savefig(f"examples/hightemp_hp/plots/plot_ed_columns_{SENS_VAR_savefig}.png", dpi=300)


'''# 6. Double‐Variable Sensitivity: ambient temperature vs. T34 c_P

# define the two ranges (you can adjust the step or limits as desired)
amb_range  = np.arange(1, 26, 2)   # ambient temperature [°C]
t34_range  = np.arange(50, 87, 2)   # T34 [°C]

double_results = []
for Tamb in amb_range:
    for T34_val in t34_range:
        # 1) apply both changes
        c11.set_attr(T=Tamb)
        c34.set_attr(T=T34_val)

        # 2) re‐solve the network
        nw.solve('design')

        # 3) run exergo‐economic analysis with default econ params
        pars = dict(
            elec_price_cent_kWh=default_elec_price,
            tau=default_tau,
            n=n,
            i_eff=i_eff,
            Tamb=Tamb
        )
        df_comp, *_ = run_exergoeco_analysis(**pars, print_results=False)

        # 4) extract the total specific product cost [€/GJ]
        mask = df_comp['Component'].isin(['TOTAL', 'TOT'])
        if mask.any():
            cP_tot = df_comp.loc[mask, 'c_P [EUR/GJ]'].iloc[0]
        else:
            cP_tot = df_comp['c_P [EUR/GJ]'].iloc[-1]

        # 5) record
        double_results.append({
            'ambient_temp':  Tamb,
            'T34':           T34_val,
            'c_P':           cP_tot,
            'epsilon':       df_comp.loc[df_comp['Component']=='TOT', 'ε [%]'].iloc[0]
        })

# assemble into a DataFrame
df_double = pd.DataFrame(double_results)

# pivot into a matrix for plotting
pivot = df_double.pivot(index='T34', columns='ambient_temp', values='c_P')

# 6) heatmap via pcolormesh
X, Y = np.meshgrid(pivot.columns.values, pivot.index.values)
Z     = pivot.values

fig, ax = plt.subplots(figsize=(5,4))
pcm = ax.pcolormesh(X, Y, Z, shading='auto')
plt.colorbar(pcm, label=r"$c_P$ [€/GJ$_{ex}$]", pad=0.02)

# find the index of the min in each column
min_row_indices = np.nanargmin(Z, axis=0)

# compute one cell's width & height
cell_width  = pivot.columns.values[1] - pivot.columns.values[0]
cell_height = pivot.index.values[1]   - pivot.index.values[0]

# draw a rectangle around each minimal cell
for col_idx, row_idx in enumerate(min_row_indices):
    # lower-left corner of that cell
    x0 = pivot.columns.values[col_idx] - cell_width/2
    y0 = pivot.index.values[row_idx]   - cell_height/2

    rect = patches.Rectangle(
        (x0, y0),
        cell_width, cell_height,
        fill=False,
        edgecolor='black',
        linewidth=2
    )
    ax.add_patch(rect)

ax.set_title('Specific product cost')
ax.set_xlabel('Ambient temperature [°C]')
ax.set_ylabel(r'$T_{34}$ [°C]')

plt.tight_layout()
plt.savefig("examples/hightemp_hp/plots/heatmap_double_sensitivity_with_minima.png", dpi=300)

# --- Build epsilon‐pivot ---
# (make sure you collected 'epsilon' for each (Tamb, T34) in double_results)
pivot_eps = df_double.pivot(index='T34', columns='ambient_temp', values='epsilon')

# Meshgrid for plotting
X_eps, Y_eps = np.meshgrid(pivot_eps.columns.values, pivot_eps.index.values)
Z_eps     = pivot_eps.values   # convert to percent

# --- Plot ε heatmap ---
fig, ax = plt.subplots(figsize=(5,4))
pcm = ax.pcolormesh(X_eps, Y_eps, Z_eps, shading='auto')
cbar = plt.colorbar(pcm, ax=ax, pad=0.02)

# find the index of the max in each column
max_row_indices = np.nanargmax(Z_eps, axis=0)

# compute one cell's width & height
cell_width  = pivot_eps.columns.values[1] - pivot_eps.columns.values[0]
cell_height = pivot_eps.index.values[1]   - pivot_eps.index.values[0]

# draw a rectangle around each maximal cell
for col_idx, row_idx in enumerate(max_row_indices):
    # lower-left corner of that cell
    x0 = pivot_eps.columns.values[col_idx] - cell_width/2
    y0 = pivot_eps.index.values[row_idx]   - cell_height/2

    rect = patches.Rectangle(
        (x0, y0),
        cell_width, cell_height,
        fill=False,
        edgecolor='black',
        linewidth=2
    )
    ax.add_patch(rect)

cbar.set_label(r"$\varepsilon$ [%]")

ax.set_title('Exergetic efficiency')
ax.set_xlabel('Ambient temperature [°C]')
ax.set_ylabel(r'$T_{34}$ [°C]')

plt.tight_layout()
plt.savefig("examples/hightemp_hp/plots/heatmap_double_sensitivity_epsilon.png", dpi=300)'''

# 7. Combined Figure: Z + Exergy Destruction + Efficiencies

# Z per component
prefix_z = "Z_EURperh_"
z_cols = [
    c for c in df.columns
    if c.startswith(prefix_z) and not any(x in c for x in ("_TOT", "VAL1", "VAL2"))
]
rename_map_z = {}
for col in z_cols:
    rename_map_z[col] = col.replace(prefix_z, "")
plot_df_z = df[z_cols].rename(columns=rename_map_z)

# Exergy destruction per component
prefix_ed = "E_D_kW_"
ed_cols = [
    c for c in df.columns
    if c.startswith(prefix_ed) and not c.endswith("_TOT")
]
rename_map_ed = {}
for col in ed_cols:
    rename_map_ed[col] = col.replace(prefix_ed, "")
plot_df_ed = df[ed_cols].rename(columns=rename_map_ed)

# === Reorder stacks from bottom to top ===
desired_order = [
    "AIR_HX", "COMP1", "MOT1", "VAL1", "IHX",
    "COMP2", "MOT2", "VAL2", "STEAM_GEN"
]
# Filter to columns that exist
order_z = [c for c in desired_order if c in plot_df_z.columns]
order_ed = [c for c in desired_order if c in plot_df_ed.columns]

plot_df_z = plot_df_z[order_z]
plot_df_ed = plot_df_ed[order_ed]

# === Build combined figure ===
fig, (ax_z, ax_ed) = plt.subplots(
    2, 1,
    figsize=(7, 7),
    sharex=True,
    gridspec_kw={"height_ratios": [1, 1]}
)
fig.suptitle("Capital cost and exergy destruction of the components", fontsize=14)
plt.tight_layout(rect=[0, 0, 1, 0.95])

x = np.arange(len(plot_df_z))
bar_width = 0.8

# Top: Z stacked bars
plot_df_z.plot(
    kind="bar", stacked=True,
    ax=ax_z, width=bar_width,
    color=[component_colors[c] for c in plot_df_z.columns],
    legend=False, zorder=1
)
ax_z.set_ylabel(r"$\dot{Z}$ [€/h]")

# Bottom: Exergy destruction stacked bars
plot_df_ed.plot(
    kind="bar", stacked=True,
    ax=ax_ed, width=bar_width,
    color=[component_colors[c] for c in plot_df_ed.columns],
    legend=False, zorder=1
)
ax_ed.set_xlabel(f"{SENS_VAR} {unit}")
ax_ed.set_ylabel(r"$\dot{E}_D$ [kW]")

ax_ed.set_xticks(x)
ax_ed.set_xticklabels(plot_df_z.index.astype(str), rotation=0)

# Hatch patterns for cycle highlighting
pattern_map = {
    'AIR_HX': '///', 'COMP1': '///', 'MOT1': '///', 'VAL1': '///',
    'COMP2': '...', 'MOT2': '...', 'VAL2': '...', 'STEAM_GEN': '...'
}

# Apply hatches on top plot
n_z = len(plot_df_z)
for i, comp in enumerate(plot_df_z.columns):
    hatch = pattern_map.get(comp, '')
    for j in range(n_z):
        ax_z.patches[i * n_z + j].set_hatch(hatch)

# Apply hatches on bottom plot
n_ed = len(plot_df_ed)
for i, comp in enumerate(plot_df_ed.columns):
    hatch = pattern_map.get(comp, '')
    for j in range(n_ed):
        ax_ed.patches[i * n_ed + j].set_hatch(hatch)

# Legend (from bottom, reversed)
handles, labels = ax_ed.get_legend_handles_labels()
ax_z.legend(
    handles[::-1], labels[::-1],
    title="Component",
    bbox_to_anchor=(1.01, 0.5),
    loc="center left"
)

plt.tight_layout()
plt.savefig(f"examples/hightemp_hp/plots/combined_Z_ED_{SENS_VAR_savefig}.png", dpi=300)


# data series
z   = df['Z_tot']        # [EUR/h]
c1  = df['Ctot_e1']      # [EUR/h]
c4  = df['Ctot_e4']      # [EUR/h]
cp  = df['c_P']          # [EUR/GJ]  for coloring
sv  = df.index.values    # sensitivity var, T34

x = c1 + c4

plt.figure(figsize=(7,5))
sc = plt.scatter(x, z,
                 c=cp,
                 cmap='viridis',
                 s=80,
                 edgecolor='k',
                 marker='o')

# annotate each point with its T34
for xi, zi, tval in zip(x, z, sv):
    plt.text(xi + 0.3, zi, f"{tval:.0f}°C", fontsize=9, color='black')

plt.xlabel(r'$\dot C_{\mathrm{F,TOT}}$ [EUR/h]')
plt.ylabel(r'$\dot{Z}_{\mathrm{TOT}}$ [EUR/h]')
plt.title(r'Investment costs vs. fuel costs at varying $T_{34}$')
plt.grid(True)

# colorbar shows c_P
cbar = plt.colorbar(sc)
cbar.set_label(r'$c_P$ [EUR/GJ]')

plt.tight_layout()
plt.savefig(f"examples/hightemp_hp/plots/plot_fuel_invest_costs_{SENS_VAR_savefig}.png", dpi=300)
