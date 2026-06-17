import logging
import os

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

from exerpy import ExergyAnalysis

# ----------------------------------------------------------------------------------------------------------------------
# 1. Import model from Aspeng
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cgam.bkp"))

# ----------------------------------------------------------------------------------------------------------------------
# 2. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_aspen(model_path, chemExLib="Ahrendts", split_physical_exergy=False)

fuel = {"inputs": ["1", "10"], "outputs": []}
product = {"inputs": ["E1", "9"], "outputs": ["8"]}
loss = {"inputs": ["7"], "outputs": []}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()
ean.export_to_json("examples/exergy_analysis/cgam/cgam_aspen.json")
