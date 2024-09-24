import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the parent directory to the system path to import modules from the project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary modules and functions from exerpy
from src.exerpy.analyses_new import ExergyAnalysis

# Define the path to the Ebsilon model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'simple_test.ebs'))

# Perform the exergy analysis with the new ExergyAnalysis class
T0 = 15      # Ambient temperature in °C
p0 = 1.013   # Ambient pressure in bar

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis(model_path)
ean.analyse(T0, p0)
ean.exergy_results()