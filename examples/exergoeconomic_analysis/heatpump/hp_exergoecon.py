import logging
import os

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

from exerpy import ExergoeconomicAnalysis, ExergyAnalysis
from exerpy.cost_estimation.turton import TurtonCostEstimator

# ----------------------------------------------------------------------------------------------------------------------
# 1. Import model from JSON data (from Ebsilon)
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "hp_exergoecon.json"))


# ----------------------------------------------------------------------------------------------------------------------
# 2. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_json(model_path, split_physical_exergy=True)

fuel = {"inputs": ["E1", "E2", "E3"], "outputs": []}
product = {"inputs": ["23"], "outputs": ["21"]}
loss = {"inputs": ["13"], "outputs": ["11"]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)


# ----------------------------------------------------------------------------------------------------------------------
# 3. Exergoeconomic analysis
# ----------------------------------------------------------------------------------------------------------------------
exergoeco_analysis = ExergoeconomicAnalysis(ean)

cost_estimator = TurtonCostEstimator(exergoeco_analysis)

# Estimate component costs automatically
estimated_costs = cost_estimator.estimate_costs(
    cepci_year=2024,
    regional_factor=1.2,
    operating_hours=5500,
    custom_mappings={"FAN": "compressors.centrifugal_fan", "EVA": "heat_exchangers.air_cooler"},
    custom_U_values={
        "COND": 1200,  # W/(m2K)
        "EVA": 50,  # W/(m2K)
    },
    equipment_lifetime=20,
    interest_rate=0.10,
    escalation_rate=0.02,
    maintenance_factor=0.03,  # % of capital cost per year
)

# Print cost breakdown
cost_estimator.print_estimated_costs()

# Add boundary stream costs and run analysis
# Cost keys must match connection names exactly: "<connection_name>_c"
all_costs = {**estimated_costs, "E1_c": 100.0, "11_c": 20.0, "21_c": 0.0}  # currency/GJ
exergoeco_analysis.run(all_costs)
exergoeco_analysis.exergoeconomic_results()
