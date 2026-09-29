"""Exergoeconomic analysis of the CGAM process with and without split physical exergy."""

import logging
import os

import pandas as pd

from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# [setup]
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cgam.json"))

fuel = {"inputs": ["10", "1", "8"], "outputs": []}
product = {"inputs": ["E1", "9"], "outputs": []}
loss = {"inputs": ["7"], "outputs": []}

all_costs = {
    "AC_Z": 56.99,
    "CC_Z": 4.40,
    "EXP_Z": 48.16,
    "APH_Z": 12.26,
    "EV_Z": 11.476,
    "PH_Z": 5.454,
    "GEN_Z": 0.0,
    "1_c": 0.0,
    "10_c": 3.8635,
    "8_c": 0.0,
}


# [run_both]
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
def results(eco):
    """Exergoeconomic results of every component of one run."""
    rows = {}
    for name, comp in eco.components.items():
        Z = comp.Z_costs * 3600
        C_D = comp.C_D * 3600
        rows[name] = {
            "C_F": comp.C_F * 3600,
            "C_P": comp.C_P * 3600,
            "C_D": C_D,
            "Z": Z,
            "C_D+Z": C_D + Z,
            "c_F": comp.c_F * 1e9,
            "c_P": comp.c_P * 1e9,
            "f": comp.f * 100,
            "r": comp.r * 100,
        }
    return pd.DataFrame(rows).T


def compare(metrics):
    """The given metrics of both runs, side by side."""
    both = pd.concat({"split": results(split), "no split": results(no_split)}, axis=1).swaplevel(axis=1)
    return both[[(metric, mode) for metric in metrics for mode in ("split", "no split")]]


print("\nCost rates of the components in USD/h:")
print((compare(["C_F", "C_P", "C_D", "Z", "C_D+Z"]).round(2) + 0.0).to_string())

print("\nSpecific costs in USD/GJ and exergoeconomic indicators in %:")
print((compare(["c_F", "c_P", "f", "r"]).round(3) + 0.0).to_string())

# [system]
df_sys = pd.DataFrame(
    {"split": split.system_costs, "no split": no_split.system_costs},
    index=["C_F", "C_P", "Z"],
)
print("\nSystem costs [USD/h]:")
print(df_sys.round(3).to_string())
# [end]
