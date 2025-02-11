import os
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hp.ebs'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path)

fuel = {
    "inputs": ['E1', 'E2', 'E3'],
    "outputs": []
}

product = {
    "inputs": ['23'],
    "outputs": ['21']
}

loss = {
    "inputs": ['13'],
    "outputs": ['11']
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()

component_costs = {
    "COMP": 500.0,  # in "Compressor": {"COMP": ...}
    "FAN": 400.0,   # in "Compressor": {"FAN": ...}
    "COND": 600.0,  # in "HeatExchanger": {"COND": ...}
    "EVA": 500.0,   # in "HeatExchanger": {"EVA": ...}
    "MOT1": 100.0,  # in "Motor": {"MOT1": ...}
    "MOT2": 100.0,  # in "Motor": {"MOT2": ...}
    "MOT3": 50.0,   # in "Motor": {"MOT3": ...}
    "PUMP": 200.0,  # in "Pump":   {"PUMP": ...}
    "VAL": 20.0     # in "Valve":  {"VAL":  ...}
    # add or change the cost rates as desired
}


'''eco = ExergoeconomicAnalysis(ean, component_costs)
eco.run()

df_results = eco.results()
print(df_results)'''