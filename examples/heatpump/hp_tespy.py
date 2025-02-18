from tespy.components import Compressor, Source, Sink, CycleCloser, HeatExchanger, Pump, Valve
from tespy.connections import Connection, Ref, Bus
from tespy.networks import Network


nw = Network(T_unit="C", p_unit="bar")

air_in = Source("air inlet")
air_out = Sink("air outlet")
fan = Compressor("FAN")

water_in = Source("water inlet")
water_out = Sink("water outlet")
pump = Pump("PUMP")

evaporator = HeatExchanger("EVA")
condenser = HeatExchanger("COND")
compressor = Compressor("COMP")
valve = Valve("VAL")
cc = CycleCloser("cc")

a1 = Connection(air_in, "out1", fan, "in1", label="11")
a2 = Connection(fan, "out1", evaporator, "in1", label="12")
a3 = Connection(evaporator, "out1", air_out, "in1", label="13")

b1 = Connection(water_in, "out1", pump, "in1", label="21")
b2 = Connection(pump, "out1", condenser, "in2", label="22")
b3 = Connection(condenser, "out2", water_out, "in1", label="23")

c0 = Connection(condenser, "out1", cc, "in1", label="30")
c1 = Connection(cc, "out1", valve, "in1", label="31")
c2 = Connection(valve, "out1", evaporator, "in2", label="32")
c3 = Connection(evaporator, "out2", compressor, "in1", label="33")
c4 = Connection(compressor, "out1", condenser, "in1", label="34")

nw.add_conns(c0, c1, c2, c3, c4)
nw.add_conns(a1, a2, a3)
nw.add_conns(b1, b2, b3)

c3.set_attr(fluid={"R245FA": 1}, Td_bp=7.073)
c4.set_attr(p=23)
c0.set_attr(T=75)
c2.set_attr(p=0.6)

a1.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=10, p=1.013)
a2.set_attr()
a3.set_attr(T=8, p=1.013)
b1.set_attr(fluid={"water": 1}, T=70, p=5, m=10)
b2.set_attr()
b3.set_attr(T=120, p=5)

compressor.set_attr(eta_s=0.8)
fan.set_attr(eta_s=0.85)
pump.set_attr(eta_s=0.8)
evaporator.set_attr()
condenser.set_attr()

c3.set_attr(p=Ref(c2, 1, -0.05))
c0.set_attr(p=Ref(c4, 1, -0.05))

b3.set_attr(p=Ref(b2, 1, -0.05))
a3.set_attr(p=Ref(a2, 1, -0.03))

nw.solve("design")

c0.set_attr(T=None)
condenser.set_attr(ttd_l=5)
c3.set_attr(Td_bp=None)
evaporator.set_attr(ttd_u=5)

power_input = Bus("power input")
power_input.add_comps(
    {"comp": compressor, "base": "bus", "char": 0.985},
    {"comp": pump, "base": "bus", "char": 0.985},
    {"comp": fan, "base": "bus", "char": 0.985}
)

nw.add_busses(
    power_input
)

nw.solve("design")
nw.print_results()

p0 = 101300
T0 = 283.15

from exerpy import ExergyAnalysis, ExergoeconomicAnalysis


ean = ExergyAnalysis.from_tespy(nw, T0, p0)

# export of the results for validation
import json
from exerpy.parser.from_tespy.tespy_config import EXERPY_TESPY_MAPPINGS


json_export = nw.to_exerpy(T0, p0, EXERPY_TESPY_MAPPINGS)
with open("examples/heatpump/hp_tespy.json", "w", encoding="utf-8") as f:
    json.dump(json_export, f, indent=2)


fuel = {
    "inputs": [
        'power input__motor_of_COMP',
        'power input__motor_of_FAN',
        'power input__motor_of_PUMP'
    ],
    "outputs": []
}

product = {
    "inputs": ['23'],
    "outputs": ['21']
}

loss = {
    "inputs": ['13'],
    "outputs": ['11']
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
df_component_results, _, _ = ean.exergy_results()
ean.export_to_json("examples/heatpump/hp_tespy.json")
df_component_results.to_csv("examples/heatpump/hp_components_tespy.csv")

Exe_Eco_Costs = {
    "COMP_Z": 500.0,  
    "FAN_Z": 150.0,   
    "COND_Z": 600.0,  
    "EVA_Z": 500.0,   
    "motor_of_FAN_Z": 30.0,  
    "motor_of_COMP_Z": 30.0,  
    "motor_of_PUMP_Z": 4.0,  
    "PUMP_Z": 7.0, 
    "VAL_Z": 1.0,
    "11_c": 0.0,
    "21_c": 0.01,
    "power input__motor_of_COMP_c": 5.0,
}


# Initialize Exergoeconomic Analysis with existing exergy analysis
exergoeco_analysis = ExergoeconomicAnalysis(ean)

# Run the exergoeconomic analysis with cost inputs
exergoeco_analysis.run(Exe_Eco_Costs=Exe_Eco_Costs, Tamb=ean.Tamb)
exergoeco_analysis.exergoeconomic_results()