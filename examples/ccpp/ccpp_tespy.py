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
compressor = Compressor("gas turbine compressor")
combustion = DiabaticCombustionChamber("combustion chamber")
gasturbine = Turbine("gas turbine")

superheater = HeatExchanger("superheater")
evaporator = HeatExchanger("evaporator")
economizer = HeatExchanger("economizer")

drum = Drum("drum")
feed_pump = Pump("feed pump")
condensate_pump = Pump("condensate pump")
hp_steam_turbine = Turbine("high pressure steam turbine")
lp_steam_turbine = Turbine("low pressure steam turbine")

deaerator = Merge("deaerator", num_in=3)
dea_steam_valve = Valve("dea steam inlet valve")
extraction = Splitter("turbine outlet extraction", num_out=3)
heating_condenser = SimpleHeatExchanger("heating condenser")
main_condenser = Condenser("main condenser")

water_in = Source("cooling water source")
water_out = Sink("cooling water sink")

cc = CycleCloser("cycle closer")

c1 = Connection(air_in, "out1", compressor, "in1", label="c1")
c2 = Connection(compressor, "out1", combustion, "in1", label="c2")
c3 = Connection(fuel_in, "out1", combustion, "in2", label="c3")
c4 = Connection(combustion, "out1", gasturbine, "in1", label="c4")
c5 = Connection(gasturbine, "out1", superheater, "in1", label="c5")
c6 = Connection(superheater, "out1", evaporator, "in1", label="c6")
c7 = Connection(evaporator, "out1", economizer, "in1", label="c7")
c8 = Connection(economizer, "out1", flue_gas_out, "in1", label="c8")

nw.add_conns(c1, c2, c3, c4, c5, c6, c7, c8)

c9 = Connection(superheater, "out2", cc, "in1", label="c9")
c0 = Connection(cc, "out1", hp_steam_turbine, "in1", label="c0")
c0a = Connection(hp_steam_turbine, "out1", extraction, "in1", label="c0a")
c10 = Connection(extraction, "out1", dea_steam_valve, "in1", label="c10")
c10a = Connection(dea_steam_valve, "out1", deaerator, "in1", label="c10a")

c11 = Connection(extraction, "out2", heating_condenser, "in1", label="c11")
c12 = Connection(extraction, "out3", lp_steam_turbine, "in1", label="c12")
c13 = Connection(lp_steam_turbine, "out1", main_condenser, "in1", label="c13")

c14 = Connection(water_in, "out1", main_condenser, "in2", label="c14")
c15 = Connection(main_condenser, "out2", water_out, "in1", label="c15")

c16 = Connection(main_condenser, "out1", condensate_pump, "in1", label="c16")

c17 = Connection(condensate_pump, "out1", deaerator, "in3", label="c17")
c18 = Connection(heating_condenser, "out1", deaerator, "in2", label="c18")
c20 = Connection(deaerator, "out1", feed_pump, "in1", label="c20")

c21 = Connection(feed_pump, "out1", economizer, "in2", label="c21")
c22 = Connection(economizer, "out2", drum, "in1", label="c22")
c22a = Connection(drum, "out1", evaporator, "in2", label="c22a")
c22b = Connection(evaporator, "out2", drum, "in2", label="c22b")
c23 = Connection(drum, "out2", superheater, "in2", label="c23")

nw.add_conns(c9, c0, c0a, c10, c10a, c11, c12, c13, c14, c15, c16, c17, c18, c20, c21, c22, c22a, c22b, c23)

net_power = Bus("net power")
net_power.add_comps(
    {"comp": gasturbine, "base": "component", "char": 0.985},
    {"comp": hp_steam_turbine, "base": "component", "char": 0.985},
    {"comp": lp_steam_turbine, "base": "component", "char": 0.985},
    {"comp": compressor, "base": "bus", "char": 0.985},
    {"comp": feed_pump, "base": "bus", "char": 0.985},
    {"comp": condensate_pump, "base": "bus", "char": 0.985},
)
nw.add_busses(net_power)

c1.set_attr(
    fluid={
        "AR": 0.0128,
        "CO2": 0.0004,
        "H2O": 0.0063,
        "N2": 0.7505,
        "O2": 0.2299
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
c7.set_attr(p=Ref(c8, 1, 0.003))
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

c18.set_attr(x=0)
c20.set_attr(x=0)

c21.set_attr()
c22.set_attr(Td_bp=-6, p=Ref(c21, 1, -0.02))
c22b.set_attr(m=Ref(c9, 10, 0))
c23.set_attr(p=Ref(c9, 1, 0.05))

nw.solve("design")

c3.set_attr(m=None)
c4.set_attr(T=1150)

c9.set_attr(T=None)
superheater.set_attr(ttd_u=25)

c15.set_attr(T=301.0255 - 273.15)

c1.set_attr(m=637.8845562751899)
# net_power.set_attr(P=-300e6)

heating_condenser.set_attr(Q=-100e6)

nw.solve("design")
nw.print_results()
