import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'simple_test.ebs'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path)

fuel = {
    "inputs": ['1', '3'],
    "outputs": []
}


product = {
    "inputs": ['E1', 'E2'],
    "outputs": []
}

loss = {
    "inputs": ['6'],
    "outputs": []
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()