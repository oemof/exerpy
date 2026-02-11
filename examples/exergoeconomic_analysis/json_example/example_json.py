import logging
import os

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

from exerpy import ExergoeconomicAnalysis, ExergyAnalysis

# [exergy_analysis_section]
# ----------------------------------------------------------------------------------------------------------------------
# 1. Import model from JSON
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "example.json"))


# ----------------------------------------------------------------------------------------------------------------------
# 2. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_json(model_path)

fuel = {"inputs": ["10", "1", "8"], "outputs": []}
product = {"inputs": ["E1", "9"], "outputs": []}
loss = {"inputs": ["7"], "outputs": []}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()
# [exergoeconomic_setup]

# ----------------------------------------------------------------------------------------------------------------------
# 3. Exergoeconomic analysis
# ----------------------------------------------------------------------------------------------------------------------
exergoeco_analysis = ExergoeconomicAnalysis(ean)
all_costs = {
    # Component investment cost rates [EUR/h]
    "AC_Z": 80,  # Air compressor
    "CC_Z": 30,  # Combustion chamber
    "EXP_Z": 100,  # Gas turbine (expander)
    "GEN_Z": 40,  # Generator
    "APH_Z": 50,  # Air preheater
    "EV_Z": 60,  # Evaporator
    "PH_Z": 35,  # Preheater / economizer
    # Input stream specific costs [EUR/GJ]
    "1_c": 0.0,  # Ambient air (free)
    "10_c": 10.0,  # Natural gas fuel
    "8_c": 0.5,  # Feedwater
}
exergoeco_analysis.run(all_costs)
# [display_results]
exergoeco_analysis.exergoeconomic_results()
exergoeco_analysis.evaluate_results()
# [end]
