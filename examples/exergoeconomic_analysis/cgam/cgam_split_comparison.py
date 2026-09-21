"""Exergoeconomic analysis of the CGAM process with and without split physical exergy.

The same model, the same component investment costs and the same boundary stream costs are
analysed twice: once with the physical exergy split into a thermal and a mechanical share and
once with the physical exergy as a whole. The script prints the component results of both runs
side by side and the specific cost of every material stream.

The investment and fuel costs are the ones of the CGAM problem (Valero et al., Energy 19(3), 279-286,
1994).
"""

import logging
import os

import pandas as pd

from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# [setup]
# ----------------------------------------------------------------------------------------------------------------------
# 1. Model and cost specification, identical for both runs
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cgam.json"))

fuel = {"inputs": ["10", "1", "8"], "outputs": []}
product = {"inputs": ["E1", "9"], "outputs": []}
loss = {"inputs": ["7"], "outputs": []}

# Investment cost rates [USD/h]: the purchase costs of Table 1 of Valero et al. (1994), evaluated
# at the operating point of this model and annualized with Z = PEC * CRF * phi / N, using the
# CRF = 0.182, phi = 1.06 and N = 8000 h/yr of the paper. The paper gives one purchase cost for the
# heat recovery steam generator (724,508 USD here); it is split over the two components of the
# model, the evaporator keeping the steam flow term and the gas side term shared equally.
all_costs = {
    "AC_Z": 49.874,  # Air compressor, PEC 2,068,162 USD
    "CC_Z": 4.508,  # Combustion chamber, PEC 186,948 USD
    "EXP_Z": 49.911,  # Gas turbine, PEC 2,069,709 USD
    "APH_Z": 11.899,  # Air preheater, PEC 493,446 USD
    "EV_Z": 11.843,  # Evaporator, PEC 491,094 USD
    "PH_Z": 5.629,  # Economizer, PEC 233,414 USD
    "GEN_Z": 0.0,  # The paper has no cost equation for the generator
    # Specific cost of the streams entering the system boundary [USD/GJ of exergy]
    "1_c": 0.0,  # Ambient air
    "10_c": 3.8635,  # Natural gas, 4.0 USD/GJ on the LHV of the paper
    "8_c": 0.0,  # Feedwater
}


# [run_both]
# ----------------------------------------------------------------------------------------------------------------------
# 2. Run the analysis once with and once without the split
# ----------------------------------------------------------------------------------------------------------------------
def run(split_physical_exergy):
    """Return the exergoeconomic analysis of the CGAM process for the given split."""
    ean = ExergyAnalysis.from_json(model_path, split_physical_exergy=split_physical_exergy)
    ean.analyse(E_F=fuel, E_P=product, E_L=loss)
    eco = ExergoeconomicAnalysis(ean, currency="USD")
    eco.run(all_costs)
    return eco


split = run(True)
no_split = run(False)

# [compare_components]
# ----------------------------------------------------------------------------------------------------------------------
# 3. Component results side by side
# ----------------------------------------------------------------------------------------------------------------------
rows = []
for name, comp in split.components.items():
    other = no_split.components[name]
    rows.append(
        {
            "Component": name,
            "E_D [kW]": comp.E_D / 1e3,
            "c_F split": comp.c_F * 1e9,
            "c_F no split": other.c_F * 1e9,
            "c_P split": comp.c_P * 1e9,
            "c_P no split": other.c_P * 1e9,
            "C_D split": comp.C_D * 3600,
            "C_D no split": other.C_D * 3600,
        }
    )
df_comp = pd.DataFrame(rows).set_index("Component")
df_comp["dev. c_P [%]"] = (df_comp["c_P no split"] / df_comp["c_P split"] - 1) * 100
print("\nComponent results of the CGAM process, with and without split physical exergy")
print("(c in USD/GJ, C_D in USD/h):")
print((df_comp.round(3) + 0.0).to_string())

# [compare_connections]
# ----------------------------------------------------------------------------------------------------------------------
# 4. Specific cost of the material streams
# ----------------------------------------------------------------------------------------------------------------------
rows = []
for name, conn in split.connections.items():
    if conn.get("kind") != "material" or "c_TOT" not in conn:
        continue
    rows.append(
        {
            "Connection": name,
            "E [kW]": conn["E"] / 1e3,
            "c split [USD/GJ]": conn["c_TOT"] * 1e9,
            "c no split [USD/GJ]": no_split.connections[name]["c_TOT"] * 1e9,
        }
    )
df_conn = pd.DataFrame(rows).set_index("Connection")
# A stream whose exergy is almost zero has no meaningful specific cost to compare.
reference = df_conn["c split [USD/GJ]"].where(df_conn["c split [USD/GJ]"].abs() > 1e-6)
df_conn["deviation [%]"] = (df_conn["c no split [USD/GJ]"] / reference - 1) * 100
print("\nSpecific cost of the material streams:")
print((df_conn.round(3) + 0.0).to_string())

# [system]
# ----------------------------------------------------------------------------------------------------------------------
# 5. The cost of the system itself does not depend on the split
# ----------------------------------------------------------------------------------------------------------------------
df_sys = pd.DataFrame(
    {"split": split.system_costs, "no split": no_split.system_costs},
    index=["C_F", "C_P", "Z"],
)
print("\nSystem costs [USD/h]:")
print(df_sys.round(3).to_string())
# [end]
