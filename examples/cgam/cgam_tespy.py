from CoolProp.CoolProp import PropsSI as CPSI

from tespy.networks import Network
from tespy.components import (
    HeatExchanger, Turbine, Compressor, Drum,
    DiabaticCombustionChamber, Sink, Source, PowerSink, PowerBus
)
from tespy.connections import Connection, PowerConnection
from exerpy import ExergyAnalysis, ExergoeconomicAnalysis


nwk = Network(p_unit='bar', T_unit='C')

air_molar = {
    'O2': 0.2059, 'N2': 0.7748, 'CO2': 0.0003, 'H2O': 0.019, 'CH4': 0
}
molar_masses = {key: CPSI('M', key) * 1000 for key in air_molar}
M_air = sum([air_molar[key] * molar_masses[key] for key in air_molar])

air = {key: value / M_air * molar_masses[key] for key, value in air_molar.items()}

fuel = {f: (0 if f != 'CH4' else 1) for f in air}

amb = Source('ambient air')
ch4 = Source('methane')
fw = Source('feed water')

ch = Sink('chimney')
ls = Sink('live steam')

cmp = Compressor('AC')
aph = HeatExchanger('APH')
cb = DiabaticCombustionChamber('CC')
tur = Turbine('EXP')

eva = HeatExchanger('EV')
eco = HeatExchanger('PH')
dr = Drum('DRUM')

c1 = Connection(amb, 'out1', cmp, 'in1', label='1')
c2 = Connection(cmp, 'out1', aph, 'in2', label='2')
c3 = Connection(aph, 'out2', cb, 'in1', label='3')
c10 = Connection(ch4, 'out1', cb, 'in2', label='10')

nwk.add_conns(c1, c2, c3, c10)

c4 = Connection(cb, 'out1', tur, 'in1', label='4')
c5 = Connection(tur, 'out1', aph, 'in1', label='5')
c6 = Connection(aph, 'out1', eva, 'in1', label='6')
c6p = Connection(eva, 'out1', eco, 'in1', label='6P')
c7 = Connection(eco, 'out1', ch, 'in1', label='7')

nwk.add_conns(c4, c5, c6, c6p, c7)

c8 = Connection(fw, 'out1', eco, 'in2', label='8')
c8p = Connection(eco, 'out2', dr, 'in1', label='8P')
c11 = Connection(dr, 'out1', eva, 'in2', label='11')
c11p = Connection(eva, 'out2', dr, 'in2', label='11P')
c9 = Connection(dr, 'out2', ls, 'in1', label='9')

nwk.add_conns(c8, c8p, c11, c11p, c9)

c8.set_attr(p=20, T=25, m=14, fluid={"water": 1})
c1.set_attr(p=1.013, T=25, fluid=air)
c10.set_attr(T=25, fluid=fuel, p=12)
c7.set_attr(p=1.013)
c3.set_attr(T=850 - 273.15)
c4.set_attr(T=1520 - 273.15)
c8p.set_attr(Td_bp=-15)
c11p.set_attr(x=0.5)

cmp.set_attr(pr=10, eta_s=0.86)
cb.set_attr(eta=0.98, pr=0.95)
tur.set_attr(eta_s=0.86)
aph.set_attr(pr1=0.97, pr2=0.95)
eva.set_attr(pr1=0.95 ** 0.5)
eco.set_attr(pr1=0.95 ** 0.5, pr2=1)

shaft = PowerBus("shaft", num_in=1, num_out=2)
grid = PowerSink("grid")

e1 = PowerConnection(tur, "power", shaft, "power_in1", label="e1")
e2 = PowerConnection(shaft, "power_out1", cmp, "power", label="e2")
e3 = PowerConnection(shaft, "power_out2", grid, "power", label="e3")

nwk.add_conns(e1, e2, e3)

e3.set_attr(E=30e6)

nwk.solve('design')

# assert convergence of calculation
nwk.assert_convergence()

nwk.print_results()
# %%[tespy_model_section_end]
p0 = 101300
T0 = 298.15

ean = ExergyAnalysis.from_tespy(nwk, T0, p0, chemExLib='Ahrendts', split_physical_exergy=False)
# %%[exergy_analysis_setup]
fuel = {
    "inputs": ['1', '10'],
    "outputs": []
}

product = {
    "inputs": ['e3', '9'],
    "outputs": ['8']
}

loss = {
    "inputs": ['7'],
    "outputs": []
}
# %%[exergy_analysis_flows]
ean.analyse(E_F=fuel, E_P=product, E_L=loss)
df_component_results, _, _ = ean.exergy_results()
ean.export_to_json("examples/cgam/cgam_tespy.json")
df_component_results.to_csv("examples/cgam/cgam_components_tespy.csv")
# %%[exergy_analysis_results]
