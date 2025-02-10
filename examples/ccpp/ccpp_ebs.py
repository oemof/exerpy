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
    # Component investment costs (in €/h)
    "CC_Z":   2500000,   # Combustion Chamber 
    "COMP_Z": 2000000,   # Compressor 
    "COND_Z": 2500000,   # Condenser
    "DEA_Z":  1500000,   # Deaerator 
    "GEN1_Z": 1000000,   # Generator 1 
    "GEN2_Z": 1000000,   # Generator 2 
    "ECO_Z":  2000000,   # Economizer 
    "EVA_Z":  3000000,   # Evaporator 
    "SH_Z":   2500000,   # Super Heater
    "MIX_Z":   500000,   # Mixer 
    "MOT1_Z":  750000,   # Motor 1
    "MOT2_Z":  750000,   # Motor 2 
    "PUMP1_Z": 500000,   # Pump 1
    "PUMP2_Z": 500000,   # Pump 2
    "HC_Z":   1000000,   # Heat Consumer
    "GT_Z":   7000000,   # Gas Turbine 
    "ST1_Z":  4000000,   # Steam Turbine 1 
    "ST2_Z":  5000000,   # Steam Turbine 2

    # Connection costs (in €/GJ, to be converted later to €/J)
    "1_c":    1,         # Cost of air
    "3_c":    50,        # Cost of fuel
    "14_c":   2,         # Cost of cooling water
    "E3_c":   70,        # Cost of electricity (stream E3)
    "E4_c":   70,        # Cost of electricity (stream E4)
}


# Initialize Exergoeconomic Analysis with existing exergy analysis
exergoeco_analysis = ExergoeconomicAnalysis(ean)

# Run the exergoeconomic analysis with cost inputs
exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
