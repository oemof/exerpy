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

# Perform the exergy analysis with the new ExergyAnalysis class
Tamb = 15+273.15  # Ambient temperature in K
pamb = 1.013e5    # Ambient pressure in Pa

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis(model_path)
ean.analyse(Tamb, pamb)
ean.exergy_results()