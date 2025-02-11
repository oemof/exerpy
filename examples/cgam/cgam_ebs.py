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
ean.exergy_results()

'''# ------------------ Exergoeconomic Analysis ------------------

# Instantiate the ExergoeconomicAnalysis class with the existing ExergyAnalysis instance
exa = ExergoeconomicAnalysis(ean)

# Define plausible cost inputs (invented for this example)
# Investment costs (Z_costs) for components in currency/h
# Fixed costs (c) for connections in currency/W

cost_inputs = {
    # Component Investment Costs (currency/h)
    "CC_Z": 1000.0,  
    "AC_Z": 500.0,         
    "GEN_Z": 750.0,         
    "APH_Z": 600.0,
    "EV_Z": 800.0,
    "PH_Z": 900.0,         
    "EXP_Z": 1200.0,

    # Connection Fixed Costs (currency/W)
    "1_c": 0.01,  # air input
    "10_c": 15.0,  # fuel input
    "E1_c": 20.0,  # product output
    "9_c": 25.0,  # water outlet
    "8_c": 30.0,  # water inlet
    "7_c": 5.0,  # loss (flue gases)
}

# Run the exergoeconomic analysis with the defined costs and ambient temperature
T0 = ean.Tamb  # Retrieved from the ExergyAnalysis instance
exa.run(cost_dict=cost_inputs, T0=T0)

# Display the exergoeconomic analysis results
exa.print_results()'''