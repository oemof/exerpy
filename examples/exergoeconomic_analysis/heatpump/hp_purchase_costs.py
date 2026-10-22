"""Purchased equipment costs of the TESPy heat pump from four sources, carried to the cost rates Z.

1. known costs from a source, 2. scaled costs of reference components, 3. user-defined cost equations,
4. the correlations of OpenPyTEA (Tamarona et al. 2026, doi:10.1016/j.softx.2026.102816).

All costs, the cost index and the heat transfer coefficients are placeholders. Needs
``pip install exerpy[tespy,costs]``; option 4 reads its correlations and cost index from OpenPyTEA.
"""

from tespy.components import Compressor
from tespy.components import CycleCloser
from tespy.components import HeatExchanger
from tespy.components import Motor
from tespy.components import PowerBus
from tespy.components import PowerSource
from tespy.components import Pump
from tespy.components import Sink
from tespy.components import Source
from tespy.components import Valve
from tespy.connections import Connection
from tespy.connections import PowerConnection
from tespy.networks import Network

from exerpy import EconomicAnalysis
from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis
from exerpy import costing

pamb = 101300
Tamb = 283.15

# [tespy_model]
nw = Network(iterinfo=False)
nw.units.set_defaults(
    temperature="degC",
    pressure="bar",
    pressure_difference="bar",
    enthalpy="kJ / kg",
    mass_flow="kg / s",
    heat="kW",
    power="kW",
)

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

c11 = Connection(air_in, "out1", fan, "in1", label="11")
c12 = Connection(fan, "out1", evaporator, "in1", label="12")
c13 = Connection(evaporator, "out1", air_out, "in1", label="13")

c21 = Connection(water_in, "out1", pump, "in1", label="21")
c22 = Connection(pump, "out1", condenser, "in2", label="22")
c23 = Connection(condenser, "out2", water_out, "in1", label="23")

c30 = Connection(condenser, "out1", cc, "in1", label="30")
c31 = Connection(cc, "out1", valve, "in1", label="31")
c32 = Connection(valve, "out1", evaporator, "in2", label="32")
c33 = Connection(evaporator, "out2", compressor, "in1", label="33")
c34 = Connection(compressor, "out1", condenser, "in1", label="34")

nw.add_conns(c11, c12, c13)
nw.add_conns(c21, c22, c23)
nw.add_conns(c30, c31, c32, c33, c34)

c11.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=10, p=1.013)
c13.set_attr(T=8, p=1.013)

c21.set_attr(fluid={"water": 1}, T=70, p=5, m=10)
c23.set_attr(T=120, p=5)

c32.set_attr(p=0.6, fluid={"R245FA": 1})
c34.set_attr(p=23)

compressor.set_attr(eta_s=0.8)
fan.set_attr(eta_s=0.85)
pump.set_attr(eta_s=0.8)
evaporator.set_attr(dp1=0.03, dp2=0.05, ttd_u=5)
condenser.set_attr(dp1=0.05, dp2=0.05, ttd_l=5)

power_input = PowerSource("grid")
distribution = PowerBus("electricity distribution", num_in=1, num_out=3)
motor1 = Motor("MOT1")
motor2 = Motor("MOT2")
motor3 = Motor("MOT3")

e1 = PowerConnection(power_input, "power", distribution, "power_in1", label="e1")
e2 = PowerConnection(distribution, "power_out3", motor3, "power_in", label="E3")
e3 = PowerConnection(motor3, "power_out", pump, "power", label="e3")
e4 = PowerConnection(distribution, "power_out1", motor1, "power_in", label="E1")
e5 = PowerConnection(motor1, "power_out", fan, "power", label="e5")
e6 = PowerConnection(distribution, "power_out2", motor2, "power_in", label="E2")
e7 = PowerConnection(motor2, "power_out", compressor, "power", label="e7")
nw.add_conns(e1, e2, e3, e4, e5, e6, e7)

motor1.set_attr(eta=0.985)
motor2.set_attr(eta=0.985)
motor3.set_attr(eta=0.985)

nw.solve("design")
nw.assert_convergence()

# [exergy_analysis]
ean = ExergyAnalysis.from_tespy(nw, Tamb, pamb)
ean.analyse(
    E_F={"inputs": ["e1"], "outputs": []},
    E_P={"inputs": ["23"], "outputs": ["21"]},
    E_L={"inputs": ["13"], "outputs": ["11"]},
)

# [economic]
# The same economic assumptions for every option.
plant = {
    "i_eff": 0.12,
    "n": 20,
    "tau": 6000,
    "f_tci": 4.5,
    "omc_share": 0.015,
    "r_n": 0.05,
    "base_year": 2025,
    "fuel_costs": {"e1": {"c": 30.0, "r_n": 0.04}, "11": 0.0, "21": 0.0},
    "currency": "EUR",
}

# [sizes]
# No comparable cell for these exchangers, so U is given per (hot phase, cold phase) section (assumed values).
exchangers = {
    "COND": {
        "exchanger_type": "plate",
        "U": {("gas", "liquid"): 500.0, ("two-phase", "liquid"): 2500.0, ("liquid", "liquid"): 1500.0},
    },
    "EVA": {"exchanger_type": "air_cooled", "U": {("gas", "two-phase"): 450.0, ("gas", "gas"): 200.0}},
}
sizes = {name: costing.sizes(component, **exchangers.get(name, {})) for name, component in ean.components.items()}
for name, values in sizes.items():
    if values:
        print(f"{name:5s}", ", ".join(f"{q} = {v:,.4g} {costing.UNITS[q]}" for q, v in values.items()))

# [option1]
# Option 1: known costs from a source, in EUR, with their reference year.
known_costs = {
    "COMP": (300000.0, 2021),
    "COND": (120000.0, 2021),
    "EVA": (150000.0, 2021),
    "FAN": (40000.0, 2024),
    "MOT1": (25000.0, 2024),
    "MOT2": (60000.0, 2023),
    "MOT3": (8000.0, 2023),
    "PUMP": (15000.0, 2023),
    "VAL": (5000.0, 2023),
}
user_cost_index = {2021: 112.0, 2023: 133.0, 2024: 139.0, 2025: 143.0}

# [option1_z]
known = EconomicAnalysis(
    PEC={name: cost for name, (cost, _) in known_costs.items()},
    reference_year={name: year for name, (_, year) in known_costs.items()},
    cost_index=user_cost_index,
    **plant,
)
z_known = known.compute_component_costs()

# [option2]
# Option 2: reference components of another size, scaled by the size named in size_by.
references = {
    "COMP": {"PEC_ref": 250000.0, "size_ref": 600e3, "size_by": "power", "exponent": 0.8},
    "FAN": {"PEC_ref": 30000.0, "size_ref": 150.0, "size_by": "volume_flow"},
    "COND": {"PEC_ref": 90000.0, "size_ref": 50.0, "size_by": "area", **exchangers["COND"]},
    "EVA": {"PEC_ref": 120000.0, "size_ref": 250.0, "size_by": "area", **exchangers["EVA"]},
}
reference_years = {"COMP": 2021, "FAN": 2024, "COND": 2023, "EVA": 2021}

# [option2_z]
# Components without a reference keep their known costs.
scaled = EconomicAnalysis(
    PEC={**{name: cost for name, (cost, _) in known_costs.items()}, **references},
    reference_year={**{name: year for name, (_, year) in known_costs.items()}, **reference_years},
    cost_index=user_cost_index,
    exergy_analysis=ean,
    **plant,
)
z_scaled = scaled.compute_component_costs()


# [option3]
# Option 3: user-defined cost equations in EUR of the base year (fictitious placeholders).
def fictitious_compressor_cost(power_kw, pressure_ratio):
    return 1200.0 * power_kw**0.8 * pressure_ratio**0.1


def fictitious_fan_cost(volume_flow_m3s):
    return 900.0 * volume_flow_m3s**0.8


def fictitious_pump_cost(power_kw):
    return 2000.0 + 150.0 * power_kw


def fictitious_motor_cost(power_kw):
    return 500.0 + 120.0 * power_kw**0.85


def fictitious_plate_exchanger_cost(area_m2):
    return 1200.0 * area_m2**0.75


def fictitious_air_cooler_cost(area_m2):
    return 300.0 * area_m2**0.8


equations = {
    "COMP": fictitious_compressor_cost(sizes["COMP"]["power"] * 1e-3, sizes["COMP"]["pressure_ratio"]),
    "FAN": fictitious_fan_cost(sizes["FAN"]["volume_flow"]),
    "PUMP": fictitious_pump_cost(sizes["PUMP"]["power"] * 1e-3),
    "MOT1": fictitious_motor_cost(sizes["MOT1"]["power"] * 1e-3),
    "MOT2": fictitious_motor_cost(sizes["MOT2"]["power"] * 1e-3),
    "MOT3": fictitious_motor_cost(sizes["MOT3"]["power"] * 1e-3),
    "COND": fictitious_plate_exchanger_cost(sizes["COND"]["area"]),
    "EVA": fictitious_air_cooler_cost(sizes["EVA"]["area"]),
    "VAL": 5000.0,  # no size from the model
}

# [option3_z]
# Costs of the base year: no reference year and no cost index needed.
eq = EconomicAnalysis(PEC=equations, **plant)
z_equations = eq.compute_component_costs()

# [option4]
# Option 4: OpenPyTEA correlations; components not chosen here take the default of their class.
choices = {
    "COMP": {"key": "screw_compressor_electric_motor_seider_2013"},  # includes the motor MOT2
    "FAN": {"key": "centrifugal_backward_curved_fan_head_9-15_seider_2013", "outside": "parallel"},
    "COND": {"key": "plate_frame_hx_towler_2010", "U": exchangers["COND"]["U"]},
    "EVA": {"key": "air_cooled_finfan_seider_2013", "U": exchangers["EVA"]["U"]},
}
estimates = {}
for name, component in ean.components.items():
    if name in ("VAL", "MOT2"):  # no correlation for the valve; MOT2 is part of COMP
        continue
    choice = choices.get(name, {"key": costing.default_correlation(component)})
    if choice["key"] is not None:
        estimates[name] = costing.estimate(component, **choice)

for name, estimate in estimates.items():
    print(
        f"{name:5s} {estimate['key']:55s} {estimate['size']:12,.1f} {estimate['size_units']:35s} "
        f"{estimate['fit']['status']:9s} {estimate['method']:11s} {estimate['PEC']:12,.0f} USD "
        f"{estimate['reference_year']}"
    )

# [option4_z]
# From USD of the correlation year to EUR, escalated with the cost index of OpenPyTEA.
openpytea = {
    name: estimate["PEC"] * costing.per_dollar("EUR", estimate["reference_year"])
    for name, estimate in estimates.items()
}
openpytea_years = {name: estimate["reference_year"] for name, estimate in estimates.items()}
openpytea.update({"VAL": 5000.0, "MOT2": 0.0})
openpytea_years.update({"VAL": 2025, "MOT2": 2025})
correlated = EconomicAnalysis(
    PEC=openpytea,
    reference_year=openpytea_years,
    cost_index=costing.cost_index(),
    **plant,
)
z_openpytea = correlated.compute_component_costs()

# [combined]
# Known costs for COMP and MOT2, OpenPyTEA for the rest.
combined = {**openpytea, "COMP": known_costs["COMP"][0], "MOT2": known_costs["MOT2"][0]}
combined_years = {**openpytea_years, "COMP": known_costs["COMP"][1], "MOT2": known_costs["MOT2"][1]}
mixed = EconomicAnalysis(
    PEC=combined,
    reference_year=combined_years,
    cost_index=costing.cost_index(),
    **plant,
)
z_combined = mixed.compute_component_costs()


# [exergoeconomic_run]
exergoeco_analysis = ExergoeconomicAnalysis(ean, currency="EUR")
exergoeco_analysis.run(mixed.compute_costs(ean))
exergoeco_analysis.exergoeconomic_results()
# [end]
