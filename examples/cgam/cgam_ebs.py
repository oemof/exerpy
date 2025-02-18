import os
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cgam.ebs'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

fuel = {
    "inputs": ['1', '10'],
    "outputs": []
}

product = {
    "inputs": ['E1', '9'],
    "outputs": ['8']
}

loss = {
    "inputs": ['7'],
    "outputs": []
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)

# ------------------ Exergoeconomic Analysis ------------------

Exe_Eco_Costs = {
    # Component Investment Costs (currency/h)
    "CC_Z": 68.0,  
    "AC_Z": 753.0,         
    "GEN_Z": 10.0,         
    "APH_Z": 181.0,
    "EV_Z": 159.0,
    "PH_Z": 100.0,         
    "EXP_Z": 753.0,

    # Connection Fixed Costs (currency/W)
    "1_c": 0.0,  # air input
    "10_c": 4.57,  # fuel input
    "8_c": 0.0,  # water inlet
}

exergoeco_analysis = ExergoeconomicAnalysis(ean)

# Run the exergoeconomic analysis with cost inputs
exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb, )
exergoeco_analysis.exergoeconomic_results()