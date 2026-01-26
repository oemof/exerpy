from tespy.components import CycleCloser, Motor, PowerSource, Pump, SimpleHeatExchanger, Turbine
from tespy.connections import Connection, PowerConnection
from tespy.networks import Network

from exerpy import ExergyAnalysis

nw = Network(T_unit="C", p_unit="bar", h_unit="kJ / kg", m_unit="kg / s")

pump = Pump("PUMP")
motor = Motor("MOTOR")
st = Turbine("ST")
cond = SimpleHeatExchanger("COND")
eva = SimpleHeatExchanger("EVA")

cc = CycleCloser("cc")

power_input = PowerSource("grid")

c1 = Connection(cc, "out1", pump, "in1", label="1")
c2 = Connection(pump, "out1", eva, "in1", label="2")
c3 = Connection(eva, "out1", st, "in1", label="3")
c4 = Connection(st, "out1", cond, "in1", label="4")
c5 = Connection(cond, "out1", cc, "in1", label="5")

e1 = PowerConnection(power_input, "power", motor, "power_in", label="e1")
e2 = PowerConnection(motor, "power_out", pump, "power", label="e2")

h1 = PowerConnection()

nw.add_conns(c1, c2, c3, c4, c5, e1, e2)

c1.set_attr(fluid={"water": 1}, p=0.2, x=0, m=100)
c3.set_attr(p=80, T=480)

pump.set_attr(eta_s=0.85)
st.set_attr(eta_s=0.90)
eva.set_attr(pr=0.95)
cond.set_attr(pr=0.95)

motor.set_attr(eta=0.985)

nw.solve("design")
nw.print_results()

p0 = 101300
T0 = 283.15

ean = ExergyAnalysis.from_tespy(nw, T0, p0, split_physical_exergy=True)
fuel = {"inputs": ["e1"], "outputs": []}
product = {"inputs": ["23"], "outputs": ["21"]}
loss = {"inputs": ["13"], "outputs": ["11"]}
ean.analyse(E_F=fuel, E_P=product, E_L=loss)
