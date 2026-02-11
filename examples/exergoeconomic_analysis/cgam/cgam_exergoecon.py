import logging
import os

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

from exerpy import ExergoeconomicAnalysis, ExergyAnalysis
from exerpy.cost_estimation.turton import TurtonCostEstimator

# ----------------------------------------------------------------------------------------------------------------------
# 1. Import model from JSON data (from Ebsilon)
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cgam_exergoecon.json"))


# ----------------------------------------------------------------------------------------------------------------------
# 2. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_json(model_path, chemExLib="Ahrendts", split_physical_exergy=True)

fuel = {"inputs": ["1", "10"], "outputs": []}
product = {"inputs": ["E1", "9"], "outputs": ["8"]}
loss = {"inputs": ["7"], "outputs": []}

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
    custom_mappings={"EXP": "turbines.steam_axial"},
    custom_U_values={
        "APH": 35,  # W/(m2K)
        "PH": 70,  # W/(m2K)
        "EV": 70,  # W/(m2K)
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
all_costs = {**estimated_costs, "1_c": 0.0, "10_c": 25.0, "8_c": 0.0}  # currency/GJ
exergoeco_analysis.run(all_costs)
exergoeco_analysis.exergoeconomic_results()
exergoeco_analysis.print_dependency_report()
