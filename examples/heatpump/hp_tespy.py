from tespy.components import Compressor, Source, Sink, CycleCloser, HeatExchanger, Pump, Valve, PowerBus, PowerSource, Motor
from tespy.connections import Connection, Ref, PowerConnection
from tespy.networks import Network
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis


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

c3.set_attr(fluid={"R245FA": 1})
c4.set_attr(p=23)
c2.set_attr(p=0.6)

a1.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=10, p=1.013)
a3.set_attr(T=8, p=1.013)
b1.set_attr(fluid={"water": 1}, T=70, p=5, m=10)
b3.set_attr(T=120, p=5)

compressor.set_attr(eta_s=0.8)
fan.set_attr(eta_s=0.85)
pump.set_attr(eta_s=0.8)
evaporator.set_attr(dp1=0.03, dp2=0.05)
condenser.set_attr(dp1=0.05, dp2=0.05)

condenser.set_attr(ttd_l=5)
evaporator.set_attr(ttd_u=5)

power_input = PowerSource("grid")
distribution = PowerBus("electricity distribution", num_in=1, num_out=3)
motor1 = Motor("motor 1")
motor2 = Motor("motor 2")
motor3 = Motor("motor 3")

e1 = PowerConnection(power_input, "power", distribution, "power_in1", label="e1")
e2 = PowerConnection(distribution, "power_out1", motor1, "power_in", label="e2")
e3 = PowerConnection(motor1, "power_out", pump, "power", label="e3")
e4 = PowerConnection(distribution, "power_out2", motor2, "power_in", label="e4")
e5 = PowerConnection(motor2, "power_out", fan, "power", label="e5")
e6 = PowerConnection(distribution, "power_out3", motor3, "power_in", label="e6")
e7 = PowerConnection(motor3, "power_out", compressor, "power", label="e7")

nw.add_conns(e1, e2, e3, e4, e5, e6, e7)

motor1.set_attr(eta=0.985)
motor2.set_attr(eta=0.985)
motor3.set_attr(eta=0.985)

nw.solve("design")

# assert convergence of calculation
nw.assert_convergence()

nw.print_results()
# %%[tespy_model_section_end]
p0 = 101300
T0 = 283.15

ean = ExergyAnalysis.from_tespy(nw, T0, p0, split_physical_exergy=False)
# %%[exergy_analysis_setup]
fuel = {
    "inputs": ['e1'],
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
# %%[exergy_analysis_flows]
ean.analyse(E_F=fuel, E_P=product, E_L=loss)
df_component_results, _, _ = ean.exergy_results()
ean.export_to_json("examples/heatpump/hp_tespy.json")
df_component_results.to_csv("examples/heatpump/hp_components_tespy.csv")
# %%[exergy_analysis_results]
