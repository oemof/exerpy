import os
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cgam.bkp'))

# Initialize the exergy analysis with the simulation pathG
ean = ExergyAnalysis.from_aspen(model_path, chemExLib='Ahrendts', split_physical_exergy=False)

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
ean.export_to_json("examples/cgam/cgam_aspen.json")