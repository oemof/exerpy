import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ccpp_tespy.json'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_json(model_path, chemExLib='Ahrendts')

fuel = {
    "inputs": ['1', '3'],
    "outputs": []
}

product = {
    "inputs": [
        'generator_of_GT__net power',
        'generator_of_ST1__net power',
        'generator_of_ST2__net power',
        'HC__generator_of_HC'
    ],
    "outputs": [
        'net power__motor_of_PUMP2',
        'net power__motor_of_drum pump',
        'net power__motor_of_PUMP1',
        'net power__motor_of_COMP',
    ]
}

loss = {
    "inputs": ['8', '15'],
    "outputs": ['14']
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
df_component_results, _, _ = ean.exergy_results()