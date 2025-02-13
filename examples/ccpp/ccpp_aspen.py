import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Import the necessary modules and functions from exerpy
from exerpy import ExergyAnalysis

# Define the path to the Aspen model file
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ccpp.bkp'))

# Initialize the exergy analysis with the simulation path
ean = ExergyAnalysis.from_aspen(model_path, chemExLib='Ahrendts')

fuel = {
    "inputs": ['1', '3'],
    "outputs": []
}

product = {
    "inputs": ['ETOT', 'HC_HEAT'],
    "outputs": ['PUMP1_ELEC', 'PUMP2_ELEC']
}

loss = {
    "inputs": ['8', '15'],
    "outputs": ['14']
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()

# TODO
# Open simulation with InitFromArchive2:
'''
import win32com.client as win32
import json

model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ccpp.apw'))
aspen = win32.gencache.EnsureDispatch('Apwn.Document')
aspen.InitFromArchive2(model_path)
aspen.Engine.Run2()

print(aspen.Tree.FindNode(r'\Data\Streams').Elements)'''