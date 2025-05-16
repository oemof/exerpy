from tespy.components import Compressor, Source, Sink, CycleCloser, HeatExchanger, Pump, Valve
from tespy.connections import Connection, Ref, Bus
from tespy.networks import Network
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis


nw = Network(T_unit="C", p_unit="bar", h_unit="kJ / kg", m_unit="kg / s", iterinfo=False)

air_in = Source("air inlet")
air_out = Sink("air outlet")

water_in = Source("water inlet")
water_out = Sink("water outlet")

air_hx = HeatExchanger("AIR_HX")
comp1 = Compressor("COMP1")
valve1 = Valve("VAL1")
cc1 = CycleCloser("cc")

ihx = HeatExchanger("IHX")

steam_gen = HeatExchanger("STEAM_GEN")
comp2 = Compressor("COMP2")
valve2 = Valve("VAL2")
cc2 = CycleCloser("cc2")

c11 = Connection(air_in, "out1", air_hx, "in1", label="11")
c12 = Connection(air_hx, "out1", air_out, "in1", label="12")

c21 = Connection(air_hx, "out2", comp1, "in1", label="21")
c22 = Connection(comp1, "out1", ihx, "in1", label="22")
c22c = Connection(ihx, "out1", cc1, "in1", label="22c")
c23 = Connection(cc1, "out1", valve1, "in1", label="23")
c24 = Connection(valve1, "out1", air_hx, "in2", label="24")

c31 = Connection(ihx, "out2", comp2, "in1", label="31")
c32 = Connection(comp2, "out1", steam_gen, "in1", label="32")
c32c = Connection(steam_gen, "out1", cc2, "in1", label="32c")
c33 = Connection(cc2, "out1", valve2, "in1", label="33")
c34 = Connection(valve2, "out1", ihx, "in2", label="34")

c41 = Connection(water_in, "out1", steam_gen, "in2", label="41")
c42 = Connection(steam_gen, "out2", water_out, "in1", label="42")

nw.add_conns(c21, c22, c22c, c23, c24)
nw.add_conns(c11, c12)
nw.add_conns(c31, c32, c32c, c33, c34)
nw.add_conns(c41, c42)

c11.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=20, p=1.013)
c12.set_attr(T=15)

c21.set_attr(fluid={"R245FA": 1}, h=417)
c22.set_attr(p=6.4)
c23.set_attr(h=290)
c24.set_attr(p=0.823)

c31.set_attr(fluid={"R1233zdE": 1}, h=451)
c32.set_attr(p=17.5)
c33.set_attr(h=364)
c34.set_attr(p=4.1)

c41.set_attr(fluid={"water": 1}, T=120, p=2, m=1)
c42.set_attr(h=2706)

comp1.set_attr(eta_s=0.8)
comp2.set_attr(eta_s=0.8)

steam_gen.set_attr(pr1=1, pr2=1)
air_hx.set_attr(pr1=1, pr2=1)
ihx.set_attr(pr1=1, pr2=1)

nw.solve("design")

c21.set_attr(h=None, Td_bp=5)
c23.set_attr(h=None)
c24.set_attr(p=None)
c31.set_attr(h=None, Td_bp=5)
c33.set_attr(h=None)
c42.set_attr(h=None, x=1)

air_hx.set_attr(ttd_l=5)
ihx.set_attr(ttd_l=5)
steam_gen.set_attr(ttd_l=5)

power_input = Bus("power input")
power_input.add_comps(
    {"comp": comp1, "base": "bus", "char": 0.985},
    {"comp": comp2, "base": "bus", "char": 0.985}
)

nw.add_busses(power_input)

nw.solve("design")
nw.print_results()

Q_out = c42.m.val * (c42.h.val - c41.h.val)
COP2 = c42.m.val * (c42.h.val - c41.h.val) / (comp2.P.val*1e-3)
COP1 = c31.m.val * (c31.h.val - c34.h.val) / (comp1.P.val*1e-3)
COP = c42.m.val * (c42.h.val - c41.h.val) / (power_input.P.val*1e-3)

print("Q = ", round(Q_out, 1), "kW")
print("COP = ", round(COP, 3))
print("COP1 = ", round(COP1, 3))
print("COP2 = ", round(COP2, 3))

# assert convergence of calculation
nw._convergence_check()

# %%[tespy_model_section_end]
p0 = c11.T.val * 1e5
T0 = c11.p.val + 273.15

ean = ExergyAnalysis.from_tespy(nw, T0, p0, split_physical_exergy=True)
# %%[exergy_analysis_setup]
fuel = {
    "inputs": [
        'power input__motor_of_COMP1',
        'power input__motor_of_COMP2'
    ],
    "outputs": []
}

product = {
    "inputs": ['42'],
    "outputs": ['41']
}

loss = {
    "inputs": ['12'],
    "outputs": ['11']
}
# %%[exergy_analysis_flows]
ean.analyse(E_F=fuel, E_P=product, E_L=loss)
df_component_results, _, _ = ean.exergy_results()
ean.export_to_json("examples/hightemp_hp/hp_cascade_tespy.json")