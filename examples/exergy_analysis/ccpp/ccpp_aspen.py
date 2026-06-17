import logging
import os

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

from exerpy import ExergyAnalysis

# ----------------------------------------------------------------------------------------------------------------------
# 1. Import model from Aspen
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ccpp.bkp"))

# ----------------------------------------------------------------------------------------------------------------------
# 2. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_aspen(model_path, chemExLib="Ahrendts", split_physical_exergy=False)

fuel = {"inputs": ["1", "3"], "outputs": []}
product = {"inputs": ["ETOT", "HC_HEAT"], "outputs": []}
loss = {"inputs": ["8", "15"], "outputs": ["14"]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()
ean.export_to_json("examples/exergy_analysis/ccpp/ccpp_aspen.json")
