"""Exergoeconomic analysis of the heat pump with the cost rates derived from the equipment costs.

The other exergoeconomic examples take the cost rate of every component as an input. Here only the
purchase equipment costs are given, in a JSON file, and the total revenue requirement method turns
them into the cost rates the exergoeconomic analysis needs.

Two files describe the same plant, and either can be used:

``hp_costs_simple.json``
    Everything the components have in common is written once. Every quote comes from the same year,
    every component carries the same installation factor and the same maintenance share, so the
    components are plain numbers and no cost index is needed.

``hp_costs_detailed.json``
    What the components do not have in common is written per component. The quotes come from 2021,
    2023 and 2024 and are carried to 2025 with a plant cost index, the installation factor of a heat
    exchanger differs from that of a motor, and the rotating machines need more maintenance. A
    component still falls back to the value given for the whole plant for anything it does not name.

In both, the electricity is bought and escalates over the lifetime of the plant, so its cost is
levelized alongside the investment. Every cost figure in both files is a placeholder, the cost index
included (revise later with a proper cost estimation). The point of the example is the workflow from
the equipment cost to the cost of the product.
"""

import logging
import os

from exerpy import EconomicAnalysis
from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

# [exergy_analysis]
here = os.path.dirname(__file__)
ean = ExergyAnalysis.from_json(os.path.abspath(os.path.join(here, "hp.json")))

fuel = {"inputs": ["e1"], "outputs": []}
product = {"inputs": ["23"], "outputs": ["21"]}
loss = {"inputs": ["13"], "outputs": ["11"]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()

# [economic_setup]
# Swap in "hp_costs_simple.json" for the same plant costed with one set of assumptions throughout.
eco_analysis = EconomicAnalysis.from_json(os.path.abspath(os.path.join(here, "hp_costs_detailed.json")))

# [economic_results]
eco_analysis.economic_results(ean)

# [exergoeconomic_run]
exergoeco_analysis = ExergoeconomicAnalysis(ean, currency="EUR")
exergoeco_analysis.run(eco_analysis.compute_costs(ean))

# [display_results]
exergoeco_analysis.exergoeconomic_results()
exergoeco_analysis.evaluate_results()
# [end]
