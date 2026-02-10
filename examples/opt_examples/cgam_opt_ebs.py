import logging
import os

from exerpy import ExergoeconomicAnalysis, ExergyAnalysis
from exerpy.cost_estimation.turton import TurtonCostEstimator

# Configure logging to show optimization errors
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logging.disable(logging.CRITICAL)

##################################################
# 1. Parse Ebsilon model
##################################################

model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cgam.ebs"))

##################################################
# 2. Exergy analysis
##################################################

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib="Ahrendts", split_physical_exergy=True)

fuel = {"inputs": ["1", "10"], "outputs": []}
product = {"inputs": ["E1", "9"], "outputs": ["8"]}
loss = {"inputs": ["7"], "outputs": []}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)

# Store baseline values
baseline_E_F = ean.E_F
baseline_E_P = ean.E_P
baseline_epsilon = ean.epsilon
baseline_E_D = ean.E_D

##################################################
# 3. Exergoeconomic Analysis
##################################################

# Create exergoeconomic analysis
exergoeco_analysis = ExergoeconomicAnalysis(ean)

# Create Turton cost estimator
cost_estimator = TurtonCostEstimator(exergoeco_analysis)

# Estimate component costs automatically
estimated_costs = cost_estimator.estimate_costs(
    cepci_year=2024,
    regional_factor=1.2,
    operating_hours=5500,
    custom_mappings={
        "EXP": "turbines.gas_turbine",
        "EV": "heat_exchangers.shell_and_tube_fixed_head",
        "PH": "heat_exchangers.shell_and_tube_fixed_head",
        "APH": "heat_exchangers.air_cooler",
    },
    custom_U_values={
        "PH": 1000,  # W/(m2K) - preheater
        "EV": 1500,  # W/(m2K) - evaporator
        "APH": 50,  # W/(m2K) - air preheater
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
all_costs = {**estimated_costs, "8_c": 1.0, "10_c": 25.0, "1_c": 0.0}  # currency/GJ
exergoeco_analysis.run(all_costs, Tamb=298.15)
exergoeco_analysis.exergoeconomic_results()


##################################################
# 4. Exergoeconomic Optimization with Dynamic Costs
##################################################
