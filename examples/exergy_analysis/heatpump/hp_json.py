import logging
import os

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

from exerpy import ExergyAnalysis

# ----------------------------------------------------------------------------------------------------------------------
# 1. Import model from JSON data
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "hp_ebs.json"))

# ----------------------------------------------------------------------------------------------------------------------
# 2. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_json(model_path, split_physical_exergy=False)

fuel = {"inputs": ["E1", "E2", "E3"], "outputs": []}
product = {"inputs": ["23"], "outputs": ["21"]}
loss = {"inputs": ["13"], "outputs": ["11"]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
