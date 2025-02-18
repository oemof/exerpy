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
ean.export_to_json('examples/heatpump/hp_ebs.json')

Exe_Eco_Costs = {
    "COMP_Z": 500.0,  
    "FAN_Z": 400.0,   
    "COND_Z": 600.0,  
    "EVA_Z": 500.0,   
    "MOT1_Z": 100.0,  
    "MOT2_Z": 100.0,  
    "MOT3_Z": 50.0,  
    "PUMP_Z": 200.0, 
    "VAL_Z": 1.0,
    "11_c": 0.0,
    "21_c": 0.01,
    "E1_c": 5.0,
}

# Initialize Exergoeconomic Analysis with existing exergy analysis
exergoeco_analysis = ExergoeconomicAnalysis(ean)

# Run the exergoeconomic analysis with cost inputs
exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
exergoeco_analysis.exergoeconomic_results()