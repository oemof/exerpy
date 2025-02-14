import os
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'simple.ebs'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path)

fuel = {
    "inputs": ['10'],
    "outputs": ['11']
}

product = {
    "inputs": ['W3', '5'],
    "outputs": ['W1', '1']
}

loss = {
    "inputs": [],
    "outputs": []
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)

Exe_Eco_Costs = {
    # Component Investment Costs (currency/h)
    "EVA_Z": 1000.0,  
    "PUMP_Z": 70.0,         
    "GEN_Z": 80.0,         
    "MOT_Z": 60.0,
    "ST1_Z": 1500.0,
    "ST2_Z": 2000.0,
# Connection Fixed Costs (currency/W)
    "1_c": 0.001,  # water input
    "10_c": 30.0,  # fuel input
}

# Initialize Exergoeconomic Analysis with existing exergy analysis
exergoeco_analysis = ExergoeconomicAnalysis(ean)

# Run the exergoeconomic analysis with cost inputs
exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
exergoeco_analysis.exergoeconomic_results()