"""Parabolic trough plant, modelled in TESPy after the EBSILON model of the same plant.

The topology and the design states follow ``parabolic_ebs.json``, so the two simulators can be
compared stream by stream. The solar field of the EBSILON model consists of parallel branches
behind a splitter and a merge; here it is one trough carrying the full mass flow, so the
connections inside the field (``A3``, ``A4``) have no counterpart.

The investment costs of the exergoeconomic analysis at the end are placeholders (revise later);
the purpose of this example is the workflow, not the cost figures.
"""

from tespy.components import Condenser
from tespy.components import CycleCloser
from tespy.components import Generator
from tespy.components import HeatExchanger
from tespy.components import Merge
from tespy.components import Motor
from tespy.components import ParabolicTrough
from tespy.components import PowerBus
from tespy.components import PowerSink
from tespy.components import Pump
from tespy.components import Sink
from tespy.components import Source
from tespy.components import Splitter
from tespy.components import Turbine
from tespy.components import Valve
from tespy.connections import Connection
from tespy.connections import PowerConnection
from tespy.networks import Network

from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis

# ----------------------------------------------------------------------------------------------------------------------
# 1. Create TESPy network and components
# ----------------------------------------------------------------------------------------------------------------------
nw = Network()
nw.units.set_defaults(
    temperature="degC",
    pressure="bar",
    pressure_difference="bar",
    enthalpy="kJ / kg",
    mass_flow="kg / s",
    heat="kW",
    power="kW",
)

# solar field (heat transfer fluid)
cc = CycleCloser("HTF cycle closer")
cc_steam = CycleCloser("steam cycle closer")
parab = ParabolicTrough("PARAB")
pump_sf = Pump("PUMP_SF")

# steam generator
sh = HeatExchanger("SH")
ev = HeatExchanger("EV")
eco = HeatExchanger("ECO")

# steam cycle
hpst = Turbine("HPST")
ipst = Turbine("IPST")
lpst = Turbine("LPST")
spl_hp = Splitter("HP extraction")
spl_ip = Splitter("IP extraction")
cond = Condenser("COND")
pump_cond = Pump("PUMP_COND")
dea = Merge("DEA", num_in=3)
pump_fw = Pump("PUMP_FW")
aftcool = HeatExchanger("AFTCOOL")
fwph = Condenser("FWPH")
thr = Valve("THR")

cw_in = Source("cooling water inlet")
cw_out = Sink("cooling water outlet")

# ----------------------------------------------------------------------------------------------------------------------
# 2. Connections, named after the EBSILON model
# ----------------------------------------------------------------------------------------------------------------------
a1 = Connection(eco, "out1", cc, "in1", label="A1")
a1c = Connection(cc, "out1", pump_sf, "in1", label="A1c")
a2 = Connection(pump_sf, "out1", parab, "in1", label="A2")
a5 = Connection(parab, "out1", sh, "in1", label="A5")
a6 = Connection(sh, "out1", ev, "in1", label="A6")
a7 = Connection(ev, "out1", eco, "in1", label="A7")
nw.add_conns(a1, a1c, a2, a5, a6, a7)

b09 = Connection(sh, "out2", cc_steam, "in1", label="B09")
b09c = Connection(cc_steam, "out1", hpst, "in1", label="B09c")
b10a = Connection(hpst, "out1", spl_hp, "in1", label="B10a")
b10 = Connection(spl_hp, "out1", ipst, "in1", label="B10")
b11 = Connection(spl_hp, "out2", fwph, "in1", label="B11")
b15a = Connection(ipst, "out1", spl_ip, "in1", label="B15a")
b15 = Connection(spl_ip, "out1", lpst, "in1", label="B15")
b16 = Connection(spl_ip, "out2", dea, "in3", label="B16")
b17 = Connection(lpst, "out1", cond, "in1", label="B17")
nw.add_conns(b09, b09c, b10a, b10, b11, b15a, b15, b16, b17)

b01 = Connection(cond, "out1", pump_cond, "in1", label="B01")
b02 = Connection(pump_cond, "out1", dea, "in1", label="B02")
b03 = Connection(dea, "out1", pump_fw, "in1", label="B03")
b04 = Connection(pump_fw, "out1", aftcool, "in2", label="B04")
b05 = Connection(aftcool, "out2", fwph, "in2", label="B05")
b06 = Connection(fwph, "out2", eco, "in2", label="B06")
b07 = Connection(eco, "out2", ev, "in2", label="B07")
b08 = Connection(ev, "out2", sh, "in2", label="B08")
nw.add_conns(b01, b02, b03, b04, b05, b06, b07, b08)

b12 = Connection(fwph, "out1", aftcool, "in1", label="B12")
b13 = Connection(aftcool, "out1", thr, "in1", label="B13")
# The EBSILON deaerator drops the pressure of the drain internally and reports B14 at
# 20 bar; the TESPy merge equalises the pressures of its inlets, so this stream is
# labelled differently and left out of the stream-by-stream comparison.
b14 = Connection(thr, "out1", dea, "in2", label="B14t")
nw.add_conns(b12, b13, b14)

c1 = Connection(cw_in, "out1", cond, "in2", label="C1")
c2 = Connection(cond, "out2", cw_out, "in1", label="C2")
nw.add_conns(c1, c2)

# ----------------------------------------------------------------------------------------------------------------------
# 3. Design specification, taken from the EBSILON model
# ----------------------------------------------------------------------------------------------------------------------
# The mass flow of the heat transfer fluid follows from the duty of the steam generator.
a1c.set_attr(T=290, fluid={"INCOMP::TVP1": 1})
a2.set_attr(p=15.1013)
a5.set_attr(T=392.99)
# a6.set_attr(T=377.7)  ->  follows from the duty of the superheater
# a7.set_attr(T=315.9)  ->  follows from the duty of the evaporator

b09.set_attr(T=387.99, m=33.116, fluid={"water": 1})
b10a.set_attr(p=30)
b15a.set_attr(p=2.1)
b17.set_attr(p=0.1)
b11.set_attr(m=6.0461)
b16.set_attr(m=3.8107)
b04.set_attr(p=100)
# b05.set_attr(T=143.3)  ->  follows from the duty of the aftercooler
# b06.set_attr(T=218.9)  ->  follows from the condensing drain of the preheater
# Saturation states inside the steam generator fix the split between the three sections.
# The EBSILON economizer already evaporates a few per cent of the feedwater.
b07.set_attr(x=0.031149)
b08.set_attr(x=1)
# FWPH is a Condenser: TESPy already fixes its drain outlet at saturation (subcooling=False)
b13.set_attr(T=128.205)

c1.set_attr(p=1.01325, T=20, m=500.3311, fluid={"water": 1})

# ExerPy takes the radiation on the aperture, E * A, as the exergy fuel of the collector, so
# the optical efficiency of the EBSILON field is kept and the aperture area is the unknown.
parab.set_attr(
    dp=0.1013,
    E=850,
    A="var",
    eta_opt=0.96364,
    c_1=0,
    c_2=0,
    iam_1=0,
    iam_2=0,
    aoi=0,
    doc=1,
    Tamb=20,
)
sh.set_attr(pr1=1, pr2=1)
ev.set_attr(pr1=1, pr2=1)
eco.set_attr(pr1=1, pr2=1)
hpst.set_attr(eta_s=0.88)
ipst.set_attr(eta_s=0.88)
lpst.set_attr(eta_s=0.88)
cond.set_attr(pr1=1, dp2=0.5)
fwph.set_attr(pr1=1, pr2=0.9995)
aftcool.set_attr(pr1=1, pr2=0.9995)
pump_cond.set_attr(eta_s=0.8033)
pump_fw.set_attr(eta_s=0.7992)
# The EBSILON model gives no isentropic efficiency for the solar field pump that can be read off
# its states, so it takes the one of the other pumps.
pump_sf.set_attr(eta_s=0.8)

# ----------------------------------------------------------------------------------------------------------------------
# 4. Power train
# ----------------------------------------------------------------------------------------------------------------------
gen = Generator("GEN")
# The turbine stages sit on one shaft; in TESPy each stage feeds its power into a bus.
shaft = PowerBus("SHAFT", num_in=3, num_out=1)
bus = PowerBus("SUM", num_in=1, num_out=4)
mot_cond = Motor("MOT_PUMP_COND")
mot_fw = Motor("MOT_PUMP_FW")
mot_sf = Motor("MOT_PUMP_SF")
grid = PowerSink("grid")

w1 = PowerConnection(hpst, "power", shaft, "power_in1", label="W1")
w2 = PowerConnection(ipst, "power", shaft, "power_in2", label="W2")
w3 = PowerConnection(lpst, "power", shaft, "power_in3", label="W3")
w_shaft = PowerConnection(shaft, "power_out1", gen, "power_in", label="W_shaft")
e1 = PowerConnection(gen, "power_out", bus, "power_in1", label="E1")
e2 = PowerConnection(bus, "power_out1", mot_cond, "power_in", label="E2")
e3 = PowerConnection(bus, "power_out2", mot_fw, "power_in", label="E3")
e4 = PowerConnection(bus, "power_out3", mot_sf, "power_in", label="E4")
etot = PowerConnection(bus, "power_out4", grid, "power", label="ETOT")
w4 = PowerConnection(mot_cond, "power_out", pump_cond, "power", label="W4")
w5 = PowerConnection(mot_fw, "power_out", pump_fw, "power", label="W5")
w6 = PowerConnection(mot_sf, "power_out", pump_sf, "power", label="W6")
nw.add_conns(w1, w2, w3, w_shaft, e1, e2, e3, e4, etot, w4, w5, w6)

gen.set_attr(eta=0.9856)
mot_cond.set_attr(eta=0.88)
mot_fw.set_attr(eta=0.88)
mot_sf.set_attr(eta=0.88)

nw.solve("design")
nw.assert_convergence()
nw.print_results()
# [tespy_model_section_end]

# ----------------------------------------------------------------------------------------------------------------------
# 5. Exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
p0 = 101325
T0 = 293.15

# The EBSILON export of this plant has no thermal/mechanical split, so the same setting is
# used here and the two models can be compared stream by stream.
ean = ExergyAnalysis.from_tespy(nw, T0, p0, split_physical_exergy=False)

fuel = {"inputs": ["PARAB"], "outputs": []}
product = {"inputs": ["ETOT"], "outputs": []}
loss = {"inputs": ["C2"], "outputs": ["C1"]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
df_component_results, _, _ = ean.exergy_results()
ean.export_to_json("examples/exergy_analysis/solar_thermal/parabolic_tespy.json")
df_component_results.to_csv("examples/exergy_analysis/solar_thermal/parabolic_components_tespy.csv")

# ----------------------------------------------------------------------------------------------------------------------
# 6. Exergoeconomic analysis
# ----------------------------------------------------------------------------------------------------------------------
# Placeholder investment cost rates in EUR/h; revise later with a proper cost estimation.
exergoeco_analysis = ExergoeconomicAnalysis(ean, currency="EUR")

all_costs = {
    "PARAB_Z": 2000.0,
    "PUMP_SF_Z": 5.0,
    "SH_Z": 40.0,
    "EV_Z": 60.0,
    "ECO_Z": 30.0,
    "HPST_Z": 120.0,
    "IPST_Z": 90.0,
    "LPST_Z": 80.0,
    "COND_Z": 25.0,
    "PUMP_COND_Z": 2.0,
    "DEA_Z": 5.0,
    "PUMP_FW_Z": 15.0,
    "AFTCOOL_Z": 4.0,
    "FWPH_Z": 10.0,
    "THR_Z": 0.0,
    "GEN_Z": 50.0,
    "MOT_PUMP_COND_Z": 1.0,
    "MOT_PUMP_FW_Z": 3.0,
    "MOT_PUMP_SF_Z": 2.0,
    # The solar radiation and the cooling water enter free of charge.
    "PARAB_Q_c": 0.0,
    "C1_c": 0.0,
}

exergoeco_analysis.run(all_costs)
exergoeco_analysis.exergoeconomic_results()
exergoeco_analysis.evaluate_results()
