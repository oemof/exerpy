"""Exergoeconomic analysis of the CGAM process with given investment and stream costs.

The model is read from a JSON export of the plant. The component investment cost rates and the
specific costs of the streams entering the system boundary are given directly, so the example runs
without any cost correlation. They are the costs of the CGAM problem (Valero et al., Energy 19(3),
279-286, 1994).
"""

import logging
import os

from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# [exergy_analysis_section]
# ----------------------------------------------------------------------------------------------------------------------
# 1. Import model from JSON
# ----------------------------------------------------------------------------------------------------------------------
model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cgam.json"))


# ----------------------------------------------------------------------------------------------------------------------
# 2. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_json(model_path)

fuel = {"inputs": ["10", "1", "8"], "outputs": []}
product = {"inputs": ["E1", "9"], "outputs": []}
loss = {"inputs": ["7"], "outputs": []}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()
# [exergoeconomic_setup]

# ----------------------------------------------------------------------------------------------------------------------
# 3. Exergoeconomic analysis
# ----------------------------------------------------------------------------------------------------------------------
exergoeco_analysis = ExergoeconomicAnalysis(ean, currency="USD")
# Investment cost rates [USD/h]: the purchase costs of Table 1 of Valero et al. (1994), evaluated
# at the operating point of this model and annualized with Z = PEC * CRF * phi / N, using the
# CRF = 0.182, phi = 1.06 and N = 8000 h/yr of the paper. The paper gives one purchase cost for the
# heat recovery steam generator (724,508 USD here); it is split over the two components of the
# model, the evaporator keeping the steam flow term and the gas side term shared equally.
all_costs = {
    "AC_Z": 49.874,  # Air compressor, PEC 2,068,162 USD
    "CC_Z": 4.508,  # Combustion chamber, PEC 186,948 USD
    "EXP_Z": 49.911,  # Gas turbine, PEC 2,069,709 USD
    "APH_Z": 11.899,  # Air preheater, PEC 493,446 USD
    "EV_Z": 11.843,  # Evaporator, PEC 491,094 USD
    "PH_Z": 5.629,  # Economizer, PEC 233,414 USD
    "GEN_Z": 0.0,  # The paper has no cost equation for the generator
    # Specific cost of the streams entering the system boundary [USD/GJ of exergy]
    "1_c": 0.0,  # Ambient air
    "10_c": 3.8635,  # Natural gas, 4.0 USD/GJ on the LHV of the paper
    "8_c": 0.0,  # Feedwater
}
exergoeco_analysis.run(all_costs)
# [display_results]
exergoeco_analysis.exergoeconomic_results()
exergoeco_analysis.evaluate_results()
# [end]
