import pandas as pd

from tespy.components import Compressor
from tespy.components import Condenser
from tespy.components import CycleCloser
from tespy.components import DiabaticCombustionChamber
from tespy.components import Drum
from tespy.components import HeatExchanger
from tespy.components import Merge
from tespy.components import Pump
from tespy.components import SimpleHeatExchanger
from tespy.components import Sink
from tespy.components import Source
from tespy.components import Splitter
from tespy.components import Turbine
from tespy.components import Valve
from tespy.connections import Bus
from tespy.connections import Connection
from tespy.connections import Ref
from tespy.networks import Network


nw = Network(T_unit="C", p_unit="bar")

air_in = Source("air inlet")
fuel_in = Source("fuel inlet")
flue_gas_out = Sink("flue gas outlet")
compressor = Compressor("COMP")
combustion = DiabaticCombustionChamber("CC")
gasturbine = Turbine("GT")

superheater = HeatExchanger("SH")
evaporator = HeatExchanger("EVA")
economizer = HeatExchanger("ECO")

drum = Drum("drum")
feed_pump = Pump("PUMP2")
condensate_pump = Pump("PUMP1")
drum_pump = Pump("drum pump")
hp_steam_turbine = Turbine("ST1")
lp_steam_turbine = Turbine("ST2")

deaerator = Merge("DEA", num_in=3)
dea_steam_valve = Valve("dea steam inlet valve")
extraction = Splitter("turbine outlet extraction", num_out=3)
heating_condenser = SimpleHeatExchanger("HC")
main_condenser = Condenser("COND")

water_in = Source("cooling water source")
water_out = Sink("cooling water sink")

cc = CycleCloser("cycle closer")

c1 = Connection(air_in, "out1", compressor, "in1", label="1")
c2 = Connection(compressor, "out1", combustion, "in1", label="2")
c3 = Connection(fuel_in, "out1", combustion, "in2", label="3")
c4 = Connection(combustion, "out1", gasturbine, "in1", label="4")
c5 = Connection(gasturbine, "out1", superheater, "in1", label="5")
c6 = Connection(superheater, "out1", evaporator, "in1", label="6")
c7 = Connection(evaporator, "out1", economizer, "in1", label="7")
c8 = Connection(economizer, "out1", flue_gas_out, "in1", label="8")

nw.add_conns(c1, c2, c3, c4, c5, c6, c7, c8)

c9 = Connection(superheater, "out2", cc, "in1", label="9")
c0 = Connection(cc, "out1", hp_steam_turbine, "in1", label="_0")
c0a = Connection(hp_steam_turbine, "out1", extraction, "in1", label="_??a")
c10 = Connection(extraction, "out1", dea_steam_valve, "in1", label="10")
c10a = Connection(dea_steam_valve, "out1", deaerator, "in1", label="10a")

c11 = Connection(extraction, "out2", heating_condenser, "in1", label="11")
c12 = Connection(extraction, "out3", lp_steam_turbine, "in1", label="12")
c13 = Connection(lp_steam_turbine, "out1", main_condenser, "in1", label="13")

c14 = Connection(water_in, "out1", main_condenser, "in2", label="14")
c15 = Connection(main_condenser, "out2", water_out, "in1", label="15")

c16 = Connection(main_condenser, "out1", condensate_pump, "in1", label="16")

c17 = Connection(condensate_pump, "out1", deaerator, "in3", label="17")
c18 = Connection(heating_condenser, "out1", deaerator, "in2", label="18")
c20 = Connection(deaerator, "out1", feed_pump, "in1", label="20")

c21 = Connection(feed_pump, "out1", economizer, "in2", label="21")
c22 = Connection(economizer, "out2", drum, "in1", label="22")
c22a = Connection(drum, "out1", drum_pump, "in1", label="22a")
c22b = Connection(drum_pump, "out1", evaporator, "in2", label="22b")
c22c = Connection(evaporator, "out2", drum, "in2", label="22c")
c23 = Connection(drum, "out2", superheater, "in2", label="23")

nw.add_conns(c9, c0, c0a, c10, c10a, c11, c12, c13, c14, c15, c16, c17, c18, c20, c21, c22, c22a, c22b, c22c, c23)

net_power = Bus("net power")
net_power.add_comps(
    {"comp": gasturbine, "base": "component", "char": 0.995},
    {"comp": hp_steam_turbine, "base": "component", "char": 0.985},
    {"comp": lp_steam_turbine, "base": "component", "char": 0.985},
    {"comp": compressor, "base": "bus", "char": 0.995},
    {"comp": feed_pump, "base": "bus", "char": 0.985},
    {"comp": condensate_pump, "base": "bus", "char": 0.985},
    {"comp": drum_pump, "base": "bus", "char": 0.985},
)
heat_output = Bus("heat output")
heat_output.add_comps(
    {"comp": heating_condenser, "base": "component"}
)
nw.add_busses(net_power, heat_output)

c1.set_attr(
    fluid={
        "AR": 0.01282,
        "CO2": 0.00040,
        "H2O": 0.00634,
        "N2": 0.75051,
        "O2": 0.22993
    },
    m=10,
    p=1.013,
    T=15
)
c2.set_attr(p=15.51)
c3.set_attr(fluid={"CH4": 1}, p=Ref(c2, 1, 0), T=15, m=0.3)
c4.set_attr(p=15)

c5.set_attr(p=Ref(c6, 1, 0.007))
c6.set_attr(p=Ref(c7, 1, 0.007))
c7.set_attr(p=Ref(c8, 1, 0.007))
c8.set_attr(p=1.013)

compressor.set_attr(eta_s=0.9)
combustion.set_attr(eta=1)
gasturbine.set_attr(eta_s=0.92)
superheater.set_attr()
evaporator.set_attr(ttd_l=10)
economizer.set_attr()
heating_condenser.set_attr(Q=-1e6)

hp_steam_turbine.set_attr(eta_s=0.93)
lp_steam_turbine.set_attr(eta_s=0.89)

feed_pump.set_attr(eta_s=0.8)
condensate_pump.set_attr(eta_s=0.8)

c9.set_attr(fluid={"water": 1}, p=50, T=505)
c10.set_attr(p=15)
c10a.set_attr(p=10)
c13.set_attr(p=0.05)
c14.set_attr(fluid={"water": 1}, p=1.013, T=15)
c15.set_attr(p=1.013, T=25)
c16.set_attr(p=0.05)
c17.set_attr(h0=100e3)

c18.set_attr(Td_bp=-10)
c20.set_attr(x=0)

c21.set_attr()
c22.set_attr(Td_bp=-6, p=Ref(c21, 1, -0.02))
c22b.set_attr(m=Ref(c9, 10, 0))
c22c.set_attr(p=Ref(c22b, 1, -0.03), h=Ref(c22b, 1, 100))
c23.set_attr(p=Ref(c9, 1, 0.05))

nw.solve("design")

c22c.set_attr(h=None)
drum_pump.set_attr(eta_s=0.8)

c3.set_attr(m=None)
c4.set_attr(T=1150)

c9.set_attr(T=None)
superheater.set_attr(ttd_u=25)

c15.set_attr(T=301.0255 - 273.15)

c1.set_attr(m=637.8845562751899)

heating_condenser.set_attr(Q=-100e6)

nw.solve("design")
c1.set_attr(m=None)
net_power.set_attr(P=-300e6)
nw.solve("design")

nw.print_results()

p0 = 101300
T0 = 288.15


from exerpy import ExergyAnalysis


ean = ExergyAnalysis.from_tespy(nw, T0, p0, chemExLib="Ahrendts", split_physical_exergy=False)

# export of the results for validation
import json
from exerpy.parser.from_tespy.tespy_config import EXERPY_TESPY_MAPPINGS


json_export = nw.to_exerpy(T0, p0, EXERPY_TESPY_MAPPINGS)
with open("examples/ccpp/ccpp_tespy.json", "w", encoding="utf-8") as f:
    json.dump(json_export, f, indent=2)

fuel = {
    "inputs": ['1', '3'],
    "outputs": []
}

product = {
    "inputs": [
        'generator_of_GT__net power',
        'generator_of_ST1__net power',
        'generator_of_ST2__net power',
        'HC__generator_of_HC'
    ],
    "outputs": [
        'net power__motor_of_PUMP2',
        'net power__motor_of_drum pump',
        'net power__motor_of_PUMP1',
        'net power__motor_of_COMP',
    ]
}

loss = {
    "inputs": ['8', '15'],
    "outputs": ['14']
}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
df_component_results, _, _ = ean.exergy_results()
df_component_results.to_csv("examples/ccpp/ccpp_components_tespy.csv")