from tespy.components import Compressor, Source, Sink, CycleCloser, HeatExchanger, Pump, Valve
from tespy.connections import Connection, Ref
from tespy.networks import Network


nw = Network(T_unit="C", p_unit="bar")

air_in = Source("air inlet")
air_out = Sink("air outlet")
fan = Compressor("air fan")

water_in = Source("water inlet")
water_out = Sink("water outlet")
pump = Pump("water pump")

evaporator = HeatExchanger("evaporator")
condenser = HeatExchanger("condenser")
compressor = Compressor("compressor")
valve = Valve("valve")
cc = CycleCloser("cc")

a1 = Connection(air_in, "out1", fan, "in1", label="a1")
a2 = Connection(fan, "out1", evaporator, "in1", label="a2")
a3 = Connection(evaporator, "out1", air_out, "in1", label="a3")

b1 = Connection(water_in, "out1", pump, "in1", label="b1")
b2 = Connection(pump, "out1", condenser, "in2", label="b2")
b3 = Connection(condenser, "out2", water_out, "in1", label="b3")

c1 = Connection(evaporator, "out2", compressor, "in1", label="c1")
c2 = Connection(compressor, "out1", condenser, "in1", label="c2")
c3 = Connection(condenser, "out1", valve, "in1", label="c3")
c4 = Connection(valve, "out1", cc, "in1", label="c4")
c0 = Connection(cc, "out1", evaporator, "in2", label="c0")

nw.add_conns(c0, c1, c2, c3, c4)
nw.add_conns(a1, a2, a3)
nw.add_conns(b1, b2, b3)

c1.set_attr(fluid={"R245FA": 1}, Td_bp=7.073)
c2.set_attr(p=23)
c3.set_attr(T=75)
c4.set_attr(p=0.6)

a1.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=10, p=1.013)
a2.set_attr()
a3.set_attr(T=3, p=1.013)
b1.set_attr(fluid={"water": 1}, T=70, p=5, m=10)
b2.set_attr()
b3.set_attr(T=120, p=5)

compressor.set_attr(eta_s=0.8)
fan.set_attr(eta_s=0.85)
pump.set_attr(eta_s=0.8)
evaporator.set_attr()
condenser.set_attr()

c1.set_attr(p=Ref(c4, 1, -0.05))
c3.set_attr(p=Ref(c2, 1, -0.05))
b3.set_attr(p=Ref(b2, 1, -0.05))
a3.set_attr(p=Ref(a2, 1, -0.03))

nw.solve("design")

c3.set_attr(T=None)
condenser.set_attr(ttd_l=5)
c1.set_attr(Td_bp=None)
evaporator.set_attr(ttd_u=5)

nw.print_results()


component_json = {}
for comp_type in nw.comps["comp_type"].unique():
    component_json[comp_type] = {}
    for c in nw.comps.loc[nw.comps["comp_type"] == comp_type, "object"]:
        component_json[comp_type][c.label] = {}

connection_json = {}
for c in nw.conns["object"]:
    connection_json[c.label] = {
        "source_component": c.source.label,
        "source_connector": int(c.source_id.removeprefix("out")) - 1,
        "target_component": c.target.label,
        "target_connector": int(c.target_id.removeprefix("in")) - 1
    }
    connection_json[c.label].update({param: c.get_attr(param).val for param in ["m", "T", "p", "h", "s"]})
    connection_json[c.label].update({f"{param}_unit": c.get_attr(param).unit for param in ["m", "T", "p", "h", "s"]})
    connection_json[c.label].update({f"mass_composition": c.fluid.val})
