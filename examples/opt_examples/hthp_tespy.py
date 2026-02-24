import logging

from tespy.components import Compressor, CycleCloser, Motor, PowerBus, PowerSource, Sink, Source, Valve
from tespy.components import MovingBoundaryHeatExchanger as HeatExchanger
from tespy.connections import Connection, PowerConnection, Ref
from tespy.networks import Network

from exerpy import ExergoeconomicAnalysis, ExergyAnalysis
from exerpy.cost_estimation.turton import TurtonCostEstimator

# Configure logging to show optimization errors
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logging.disable(logging.CRITICAL)

##################################################
# 1. TESPy Simulation of High-Temperature Heat Pump
##################################################

nw = Network(T_unit="C", p_unit="bar", h_unit="kJ / kg", m_unit="kg / s")

air_in = Source("air inlet")
air_out = Sink("air outlet")
air_comp = Compressor("AIR_COMP")

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

c11 = Connection(air_in, "out1", air_comp, "in1", label="11")
c12 = Connection(air_comp, "out1", air_hx, "in1", label="12")
c13 = Connection(air_hx, "out1", air_out, "in1", label="13")

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
nw.add_conns(c11, c12, c13)
nw.add_conns(c31, c32, c32c, c33, c34)
nw.add_conns(c41, c42)

power_input = PowerSource("grid")
distribution = PowerBus("electricity distribution", num_in=1, num_out=3)
motor1 = Motor("MOT1")
motor2 = Motor("MOT2")
motor3 = Motor("MOT3")

e1 = PowerSource("grid")
e1 = PowerConnection(power_input, "power", distribution, "power_in1", label="e1")
e2 = PowerConnection(distribution, "power_out1", motor1, "power_in", label="e2")
e3 = PowerConnection(motor1, "power_out", comp1, "power", label="e3")
e4 = PowerConnection(distribution, "power_out2", motor2, "power_in", label="e4")
e5 = PowerConnection(motor2, "power_out", comp2, "power", label="e5")
e6 = PowerConnection(distribution, "power_out3", motor3, "power_in", label="e6")
e7 = PowerConnection(motor3, "power_out", air_comp, "power", label="e7")

nw.add_conns(e1, e2, e3, e4, e5, e6, e7)

# Simulation with starting values
c11.set_attr(fluid={"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, T=20, p=1.013)
c13.set_attr(T=Ref(c11, 1, -5), p=Ref(c11, 1, 0))

c21.set_attr(fluid={"R290": 1}, td_dew=5)
c22.set_attr(p=6.4)
c23.set_attr(td_bubble=5)
c24.set_attr(p=0.823)

c31.set_attr(fluid={"R600a": 1}, td_dew=5)
c32.set_attr(p=17.5)
c33.set_attr(x=0)
c34.set_attr(T=60)

c41.set_attr(fluid={"water": 1}, p=2, x=0, m=1)
c42.set_attr(x=1)

comp1.set_attr(eta_s=0.8)
comp2.set_attr(eta_s=0.8)
air_comp.set_attr(eta_s=0.8)

steam_gen.set_attr(pr1=0.95, pr2=1)
air_hx.set_attr(pr1=0.99, pr2=0.95)
ihx.set_attr(pr1=0.95, pr2=0.95)

motor1.set_attr(eta=0.985)
motor2.set_attr(eta=0.985)
motor3.set_attr(eta=0.985)

# Simulation with fixed values
nw.solve("design")

c22.set_attr(p=None)
c24.set_attr(p=None)
c32.set_attr(p=None)

air_hx.set_attr(ttd_l=5)
ihx.set_attr(td_pinch=5)
steam_gen.set_attr(ttd_l=5)

nw.solve("design")
nw.print_results()


##################################################
# 2. Exergy Analysis
##################################################

# Ambient conditions
Tamb = 293.15  # K (20°C)
pamb = 101325  # Pa

# Create exergy analysis from TESPy network
ean = ExergyAnalysis.from_tespy(nw, Tamb=Tamb, pamb=pamb)

# Define fuel and product for heat pump system
fuel = {"inputs": ["e1"]}
product = {"inputs": ["42"], "outputs": ["41"]}  # Exergy increase of water/steam
loss = {"inputs": ["13"], "outputs": ["11"]}  # Exergy change of air (from inlet to outlet)

# Run exergy analysis
ean.analyse(E_F=fuel, E_P=product, E_L=loss)
ean.exergy_results()

# Store baseline values
baseline_E_F = ean.E_F
baseline_E_P = ean.E_P
baseline_epsilon = ean.epsilon
baseline_E_D = ean.E_D


##################################################
# 3. Exergoeconomic Analysis
##################################################

# Create exergoeconomic analysis
exergoeco_analysis = ExergoeconomicAnalysis(ean)

# Create Turton cost estimator
cost_estimator = TurtonCostEstimator(exergoeco_analysis)

# Estimate component costs automatically
estimated_costs = cost_estimator.estimate_costs(
    cepci_year=2024,
    regional_factor=1.2,
    operating_hours=5500,
    custom_mappings={
        "AIR_HX": "heat_exchangers.air_cooler",  # Use air cooler instead of shell-and-tube
        "AIR_COMP": "compressors.centrifugal_fan",  # Use axial fan cost correlation for air compressor
    },
    custom_U_values={
        "AIR_HX": 50,  # W/(m2K) - air-side heat exchanger
        "IHX": 1500,  # W/(m2K) - internal heat exchanger
        "STEAM_GEN": 5000,  # W/(m2K) - steam generator
    },
    equipment_lifetime=20,
    interest_rate=0.10,
    escalation_rate=0.02,
    maintenance_factor=0.03,  # % of capital cost per year
)

# Print cost breakdown
cost_estimator.print_estimated_costs()

# Add boundary stream costs and run analysis
# Cost keys must match connection names exactly: "<connection_name>_c"
all_costs = {**estimated_costs, "e1_c": 111.111, "11_c": 0.0, "41_c": 0.0}  # currency/GJ
exergoeco_analysis.run(all_costs)
exergoeco_analysis.exergoeconomic_results()


##################################################
# 4. Exergoeconomic Optimization with Dynamic Costs
##################################################

from exerpy.optimization import ExergoeconomicOptimizer
from exerpy.optimization.adapters import TESPyAdapter
from exerpy.optimization.objectives import MinimizeLevelizedCost


def calculate_costs(ea: ExergyAnalysis) -> dict:
    # Create temporary ExergoeconomicAnalysis to use with TurtonCostEstimator
    temp_eea = ExergoeconomicAnalysis(ea)

    # Create cost estimator and calculate Z values based on current component sizes
    cost_est = TurtonCostEstimator(temp_eea)
    estimated_costs = cost_est.estimate_costs(
        cepci_year=2024,
        regional_factor=1.2,
        operating_hours=5500,
        custom_mappings={
            "AIR_HX": "heat_exchangers.air_cooler",  # Use air cooler instead of shell-and-tube
            "AIR_COMP": "compressors.centrifugal_fan",  # Use axial fan cost correlation for air compressor
        },
        custom_U_values={
            "AIR_HX": 50,  # W/(m2K) - air-side heat exchanger
            "IHX": 1500,  # W/(m2K) - internal heat exchanger
            "STEAM_GEN": 5000,  # W/(m2K) - steam generator
        },
        equipment_lifetime=20,
        interest_rate=0.10,
        escalation_rate=0.02,
        maintenance_factor=0.03,
    )

    # Add boundary stream costs (these are typically fixed)
    estimated_costs["e1_c"] = 111.111  # EUR/GJ - electricity cost
    estimated_costs["11_c"] = 0.0  # EUR/GJ - ambient air (free)
    estimated_costs["41_c"] = 0.0  # EUR/GJ - inlet water (no exergy cost assigned)

    return estimated_costs


# Create adapter for TESPy model
adapter = TESPyAdapter(nw, Tamb=Tamb, pamb=pamb)

# Set up optimizer to minimize specific product cost (c_P)
# Using dynamic cost function that recalculates Z values at each design point
optimizer = (
    ExergoeconomicOptimizer(adapter)
    .add_variable(
        name="T34",
        target_type="connection",
        target_id="34",
        parameter="T",
        bounds=(45.0, 75.0),  # Temperature bounds in °C
        unit="°C",
        description="Temperature after valve 2 (IHX inlet, cold side)",
    )
    .add_variable(
        name="ttd_l_ihx",
        target_type="component",
        target_id="IHX",
        parameter="td_pinch",
        bounds=(3.0, 10.0),  # temperature difference at cold side of IHX
        unit="K",
        description="Terminal temperature difference at cold side of IHX",
    )
    .add_variable(
        name="ttd_l_air_hx",
        target_type="component",
        target_id="AIR_HX",
        parameter="ttd_l",
        bounds=(3.0, 10.0),  # temperature difference at cold side of air HX
        unit="K",
        description="Terminal temperature difference at cold side of air heat exchanger",
    )
    .add_variable(
        name="ttd_l_steam_gen",
        target_type="component",
        target_id="STEAM_GEN",
        parameter="ttd_l",
        bounds=(3.0, 10.0),  # temperature difference at cold side of steam generator
        unit="K",
        description="Terminal temperature difference at cold side of steam generator",
    )
    .add_variable(
        name="Td_bp_21",
        target_type="connection",
        target_id="21",
        parameter="td_dew",
        bounds=(1.0, 10.0),  # dew point temperature bounds for R245FA at compressor inlet
        unit="K",
        description="Dew point temperature of R245FA at COMP1 inlet (affects mass flow and size)",
    )
    .add_variable(
        name="Td_bp_23",
        target_type="connection",
        target_id="23",
        parameter="td_bubble",
        bounds=(1.0, 10.0),  # boiling point temperature bounds for R245FA at valve outlet
        unit="K",
        description="Boiling point temperature of R245FA at IHX outlet (affects mass flow and size)",
    )
    .add_variable(
        name="Td_bp_31",
        target_type="connection",
        target_id="31",
        parameter="td_dew",
        bounds=(1.0, 10.0),  # dew point temperature bounds for R1233zdE at compressor inlet
        unit="K",
        description="Dew point temperature of R1233zdE at COMP2 inlet (affects mass flow and size)",
    )
    .add_objective(MinimizeLevelizedCost())
    .set_exergy_definitions(E_F=fuel, E_P=product, E_L=loss)  # Exergy balance definitions
    .set_cost_function(calculate_costs)  # Dynamic cost estimation
    .set_seed(42)
)

# Run optimization with single-objective genetic algorithm
# E_F, E_P, E_L are already set via set_exergy_definitions()
result = optimizer.optimize(
    algorithm="GA",
    n_gen=5,
    pop_size=7,
    verbose=True,
)

# Print optimization results summary (built-in method)
result.print_summary()

# Compare baseline and optimal values (baseline is automatically captured)
result.print_comparison()
