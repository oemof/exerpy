import os
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hp.bkp'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_aspen(model_path, split_physical_exergy=False)

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
ean.export_to_json("examples/heatpump/hp_aspen.json")