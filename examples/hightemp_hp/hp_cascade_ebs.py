import os
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hp_cascade.ebs'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path)

fuel = {
    "inputs": ['E1', 'E2'],
    "outputs": []
}

product = {
    "inputs": ['42'],
    "outputs": ['41']
}

loss = {
    "inputs": ['12'],
    "outputs": ['11']
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.export_to_json('examples/hightemp_hp/hp_cascade_ebs.json')
ean.exergy_results()

# Exergoeconomic Analysis in the hp_cascade_ebs.py script