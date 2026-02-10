import logging
import os

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

from exerpy import ExergyAnalysis

# ----------------------------------------------------------------------------------------------------------------------
# 1. Import model from JSON
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ccpp_ebs.json"))

# ----------------------------------------------------------------------------------------------------------------------
# 2. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_json(model_path, chemExLib="Ahrendts", split_physical_exergy=False)

fuel = {"inputs": ["1", "3"], "outputs": []}
product = {"inputs": ["ETOT", "H1"], "outputs": []}
loss = {"inputs": ["8", "15"], "outputs": ["14"]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()
