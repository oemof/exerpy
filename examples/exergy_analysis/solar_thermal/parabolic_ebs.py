import os

script_dir = os.path.dirname(__file__)
model_path = os.path.abspath(os.path.join(script_dir, "parabolic.ebs"))

from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis

ean = ExergyAnalysis.from_ebsilon(model_path, split_physical_exergy=False)


fuel = {"inputs": ["PARAB"], "outputs": []}
product = {"inputs": ["ETOT"], "outputs": []}
loss = {"inputs": ["C2"], "outputs": ["C1"]}


ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()
ean.export_to_json("examples/exergy_analysis/solar_thermal/parabolic_ebs.json")

# The same placeholder investment cost rates as parabolic_tespy.py, so the two models of this
# plant can be compared; revise later with a proper cost estimation.
eco = ExergoeconomicAnalysis(ean, currency="EUR")

all_costs = {
    "PARAB_Z": 2000.0,
    # The header of the solar field; the TESPy model has one trough carrying the whole flow.
    "SF_MRG_Z": 0.0,
    "PUMP_SF_Z": 5.0,
    "SH_Z": 40.0,
    "EV_Z": 60.0,
    "ECO_Z": 30.0,
    "HPST_Z": 120.0,
    "IPST_Z": 90.0,
    "LPST_Z": 80.0,
    "COND_Z": 25.0,
    "PUMP_COND_Z": 2.0,
    "DEA_Z": 5.0,
    "PUMP_FW_Z": 15.0,
    "AFTCOOL_Z": 4.0,
    "FWPH_Z": 10.0,
    "THR_Z": 0.0,
    "GEN_Z": 50.0,
    "MOT_PUMP_COND_Z": 1.0,
    "MOT_PUMP_FW_Z": 3.0,
    "MOT_PUMP_SF_Z": 2.0,
    # The solar radiation and the cooling water enter free of charge.
    "PARAB_Q_c": 0.0,
    "C1_c": 0.0,
    # A99 is the empty second leg of the solar field header.
    "A99_c": 0.0,
}

eco.run(all_costs)
eco.exergoeconomic_results()
eco.evaluate_results()
