import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ccpp.ebs'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path, chemExLib='Ahrendts')

fuel = {
    "inputs": ['1', '3'],
    "outputs": []
}

product = {
    "inputs": ['ETOT', 'H1'],
    "outputs": []
}

loss = {
    "inputs": ['8', '15'],
    "outputs": ['14']
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()


Exe_Eco_Costs = {
    "CC_Z": 8000000, # Investment cost for Combustion Chamber in €/h
    "EVA_Z": 3000000, # Investment cost for Evaporator in €/h
    "ST1_Z": 4000000,  # Investment cost for Steam Turbine 1 in €/h
    "ST2_Z": 5000000,  # Investment cost for Steam Turbine 2 in €/h
    "1_c": 1,    # Cost of air in €/GJ (for air exergy stream)
    "3_c": 50,    # Cost of fuel in €/GJ (for fuel exergy stream)
    "14_c": 2,    # Cost of cooling water in €/GJ (for water exergy stream)
    "E3_c": 70, # Cost of electricity produced in €/GJ
    "E4_c": 70, # Cost of electricity produced in €/GJ
}

# Initialize Exergoeconomic Analysis with existing exergy analysis
exergoeco_analysis = ExergoeconomicAnalysis(ean)

# Run the exergoeconomic analysis with cost inputs
exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
