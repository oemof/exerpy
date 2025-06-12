from tespy.components import Compressor, Source, Sink, CycleCloser, Pump, Valve
from tespy.components import MovingBoundaryHeatExchanger as HeatExchanger
from tespy.connections import Connection, Ref, Bus
from tespy.networks import Network
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis, EconomicAnalysis

import os
import logging
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
    "COMP1":      "#98c4ec",
    "COMP2":      "#4198c7",
    # motors (cyan tones)
    "MOT1":       "#ebd543",
    "MOT2":       "#d4bf35",
    # valves (orange tones)
    "VAL1":       "#35886a",
    "VAL2":       "#63be9c",
    # heat exchangers (green/red tones)
    "AIR_HX":     "#f47051",
    "IHX":        "#d45e43",
    "STEAM_GEN":  "#b14c36",
}


def run_exergoeco_analysis(elec_price_cent_kWh, tau, i_eff, print_results=False, **kwargs):
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
    Exe_Eco_Costs["power input__motor_of_COMP1_c"] = elec_cost_eur_per_GJ

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

# Simulation with starting values

c11.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=20, p=1.013)
c12.set_attr(T=Ref(c11, 1, -5))

c21.set_attr(fluid={"R245FA": 1}, h=417)
c22.set_attr(p=6.4)
c23.set_attr(h=290)
c24.set_attr(p=0.823)

c31.set_attr(fluid={"R1233zdE": 1}, h=451)
c32.set_attr(p=17.5)
c33.set_attr(h=364)
c34.set_attr(p=4.1)

c41.set_attr(fluid={"water": 1}, p=2, x=0, m=1)
c42.set_attr(h=2706)

comp1.set_attr(eta_s=0.8)
comp2.set_attr(eta_s=0.8)

steam_gen.set_attr(pr1=0.95, pr2=1)
air_hx.set_attr(pr1=1, pr2=0.95)
ihx.set_attr(pr1=0.95, pr2=0.95)

nw.solve("design")

# Simulation with fixed values

c21.set_attr(h=None, Td_bp=5)
c22.set_attr(p=None)
c23.set_attr(h=None, Td_bp=-5)
c24.set_attr(p=None)

c31.set_attr(h=None, Td_bp=5)
c32.set_attr(p=None)
c33.set_attr(h=None, x=0)
c34.set_attr(p=None, T=60)

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

# ambient conditions
p0 = c11.p.val * 1e5
T0 = c11.T.val + 273.15

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

####################################################
#  2. Sensitivity Analysis & Exergoeconomic Analysis
####################################################

# define range of evaporator outlet temperatures T34 [°C]
SENS_VAR    = 'T34' # e.g. 'T34', 'tau', 'i_eff', 'elec_price', 'ambient temperature'
SENS_VALUES = np.arange(50, 81, 2)  # the array of values you want to sweep

def apply_sensitivity(var_name, value):
    if var_name == 'T34':
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
            i_eff=i_eff
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
        COP   = c42.m.val * (c42.h.val - c41.h.val) / (power_input.P.val * 1e-3)
        COP2  = c42.m.val * (c42.h.val - c41.h.val) / (comp2.P.val     * 1e-3)
        COP1  = c31.m.val * (c31.h.val - c34.h.val) / (comp1.P.val     * 1e-3)
        ean   = ExergyAnalysis.from_tespy(nw, T0, p0, split_physical_exergy=True)
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
        for lbl, row in nw.conns.iterrows():
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

    return pd.DataFrame.from_dict(results, orient='index')

df = run_sensitivity_analysis(SENS_VAR, SENS_VALUES)


#####################
# 3. Plots of Results
#####################

unit = {'T34':'[°C]', 'ambient temperature':'[°C]', 'tau':'[h/a]', 'i_eff':'[%/a]', 'elec_price':'[cent/kWh]'}[SENS_VAR]

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
plt.savefig(f"examples/hightemp_hp/plots/plot_normalized_scatter_{SENS_VAR}.png", dpi=300)


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
    if "motor_of_COMP1" in col:
        rename_map[col] = "MOT1"
    elif "motor_of_COMP2" in col:
        rename_map[col] = "MOT2"
    else:
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
plt.savefig(f"examples/hightemp_hp/plots/plot_investment_columns_{SENS_VAR}.png", dpi=300)


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

fig, axs = plt.subplots(5, 1, sharex=True, figsize=(5, 12))

# (1) Investment costs of compressors
axs[0].plot(t, tci1, marker="o", label="COMP1", color=component_colors["COMP1"])
axs[0].plot(t, tci2, marker="s", label="COMP2", color=component_colors["COMP2"])
axs[0].set_ylabel("TCI [M€]")
axs[0].set_title("Investment costs of the compressors")
axs[0].legend(loc="best")
min_val = min(tci1.min(), tci2.min())
max_val = max(tci1.max(), tci2.max())
axs[0].set_ylim(min_val * 0.95, max_val * 1.05)
axs[0].grid(True)

# (2) Total investment cost
axs[1].plot(t, tci_tot, marker="o", color='black')
axs[1].set_ylabel("TCI [M€]")
axs[1].set_title("Total capital investment")
axs[1].set_ylim(tci_tot.min() * 0.99, tci_tot.max() * 1.01)
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

# (5) Combined Z + cost destruction
axs[4].plot(t, zdz_tot, marker="o", color='black')
axs[4].set_ylabel(r"$\dot{Z} + \dot{C}_D$ [€/h]")
axs[4].set_title(r"$\dot{Z} + \dot{C}_D$ of the system")
axs[4].grid(True)

# shared x-axis label with LaTeX subscript and degree symbol
axs[4].set_xlabel(f"{SENS_VAR} {unit}")
axs[4].tick_params(axis="x", rotation=0)

plt.tight_layout()
plt.savefig(f"examples/hightemp_hp/plots/plot_multiplot_{SENS_VAR}.png", dpi=300)


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
    if "motor_of_COMP1" in col:
        rename_map[col] = "MOT1"
    elif "motor_of_COMP2" in col:
        rename_map[col] = "MOT2"
    else:
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
plt.savefig(f"examples/hightemp_hp/plots/plot_ed_columns_{SENS_VAR}.png", dpi=300)


'''# 6. Double‐Variable Sensitivity: ambient temperature vs. T34 c_P

# define the two ranges (you can adjust the step or limits as desired)
amb_range  = np.arange(0, 25, 2)   # ambient temperature [°C]
t34_range  = np.arange(50, 87, 2)   # T34 [°C]

double_results = []
for T_amb in amb_range:
    for T34_val in t34_range:
        # 1) apply both changes
        c11.set_attr(T=T_amb)
        c34.set_attr(T=T34_val)

        # 2) re‐solve the network
        nw.solve('design')

        # 3) run exergo‐economic analysis with default econ params
        pars = dict(
            elec_price_cent_kWh=default_elec_price,
            tau=default_tau,
            n=n,
            i_eff=i_eff
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
            'ambient_temp': T_amb,
            'T34':           T34_val,
            'c_P':           cP_tot
        })

# assemble into a DataFrame
df_double = pd.DataFrame(double_results)

# pivot into a matrix for plotting
pivot = df_double.pivot(index='T34', columns='ambient_temp', values='c_P')

# 6) heatmap via pcolormesh
X, Y = np.meshgrid(pivot.columns.values, pivot.index.values)
Z     = pivot.values

fig, ax = plt.subplots(figsize=(5,5))
pcm = ax.pcolormesh(X, Y, Z, shading='auto')
plt.colorbar(pcm, label=r"$c_P$ [€/GJ$_\mathrm{ex}$]", pad=0.02)

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
plt.savefig("examples/hightemp_hp/plots/heatmap_double_sensitivity_with_minima.png", dpi=300)'''