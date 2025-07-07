import os
import logging

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

from exerpy import ExergyAnalysis, ExergoeconomicAnalysis

model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'example.json'))

ean = ExergyAnalysis.from_json(model_path, split_physical_exergy=False)

fuel = {
    "inputs": ['1', '3'],
    "outputs": []
}

product = {
    "inputs": ['E1'],
    "outputs": []
}

loss = {
    "inputs": ['5'],
    "outputs": []
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()