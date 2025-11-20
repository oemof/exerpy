import logging
import os

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "simple_steam_cycle.ebs"))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path, split_physical_exergy=True)

fuel = {"inputs": ["H1"], "outputs": []}

product = {"inputs": ["E1"], "outputs": ["E2"]}

loss = {"inputs": ["H2"], "outputs": []}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()

from exerpy import ExergoeconomicAnalysis

Exe_Eco_Costs = {
    "ST_Z": 5000.0,
    "PUMP_Z": 500.0,
    "EVA_Z": 2000.0,
    "COND_Z": 1500.0,
    "GEN_Z": 800.0,
    "MOT_Z": 300.0,
    "H1_c": 10.0,
}

exergoeco_analysis = ExergoeconomicAnalysis(ean)
exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
exergoeco_analysis.exergoeconomic_results()
