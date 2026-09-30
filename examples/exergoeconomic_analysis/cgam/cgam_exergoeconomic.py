"""Exergoeconomic analysis of the CGAM process with given investment and stream costs."""

import logging
import os

from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# [exergy_analysis_section]
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cgam.json"))

ean = ExergyAnalysis.from_json(model_path)

fuel = {"inputs": ["10", "1", "8"], "outputs": []}
product = {"inputs": ["E1", "9"], "outputs": []}
loss = {"inputs": ["7"], "outputs": []}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()
# [exergoeconomic_setup]
exergoeco_analysis = ExergoeconomicAnalysis(ean, currency="USD")

all_costs = {
    "AC_Z": 56.99,
    "CC_Z": 4.40,
    "EXP_Z": 48.16,
    "APH_Z": 12.26,
    "EV_Z": 11.476,
    "PH_Z": 5.454,
    "GEN_Z": 0.0,
    "1_c": 0.0,
    "10_c": 3.8635,
    "8_c": 0.0,
}

exergoeco_analysis.run(all_costs)
# [display_results]
exergoeco_analysis.exergoeconomic_results()
exergoeco_analysis.evaluate_results()
# [end]
