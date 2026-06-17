import os

script_dir = os.path.dirname(__file__)
model_path = os.path.abspath(os.path.join(script_dir, "parabolic.ebs"))

from exerpy import ExergyAnalysis

ean = ExergyAnalysis.from_ebsilon(model_path, split_physical_exergy=False)


fuel = {"inputs": ["PARAB"], "outputs": []}
product = {"inputs": ["ETOT"], "outputs": []}
loss = {"inputs": ["C2"], "outputs": ["C1"]}


ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()
ean.export_to_json("examples/exergy_analysis/solar_thermal/parabolic_ebs.json")
