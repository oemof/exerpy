import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ccpp.ebs'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_ebsilon(model_path)

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