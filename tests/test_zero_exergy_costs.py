"""Auxiliary cost equations where a stream carries no exergy of one share.

A stream without exergy of a share carries no cost of it, C = c * E = 0. Where an auxiliary equation
would equate specific costs with such a stream, the outlet involved gets C = 0 instead, and an inlet
without the share adds nothing to a mixing rule.
"""

import os

import CoolProp.CoolProp as CP
import numpy as np
import pytest

from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis
from exerpy.components.component import set_equal_specific_cost
from exerpy.components.component import set_mixing_cost
from exerpy.components.turbomachinery.compressor import Compressor
from exerpy.components.turbomachinery.pump import Pump

T0 = 288.15
P0 = 101300.0
EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


def _cost_stream(name, first_column, **E):
    """A stream with one cost variable per exergy flow given in ``E``."""
    stream = {"name": name, "m": 2.0, "CostVar_index": {}}
    for i, (label, value) in enumerate(E.items()):
        stream["E" if label == "exergy" else f"E_{label}"] = value
        stream["CostVar_index"][label] = first_column + i
    return stream


def _state(fluid, T, p, m, source=None, target=None, connector=0):
    """A material stream at the given state, its exergy split into a thermal and a mechanical share."""
    h, s = CP.PropsSI("H", "T", T, "P", p, fluid), CP.PropsSI("S", "T", T, "P", p, fluid)
    h0, s0 = CP.PropsSI("H", "T", T0, "P", P0, fluid), CP.PropsSI("S", "T", T0, "P", P0, fluid)
    hA, sA = CP.PropsSI("H", "T", T0, "P", p, fluid), CP.PropsSI("S", "T", T0, "P", p, fluid)
    e_T = (h - hA) - T0 * (s - sA)
    e_M = (hA - h0) - T0 * (sA - s0)
    return {
        "kind": "material",
        "source_component": source,
        "source_connector": connector if source else None,
        "target_component": target,
        "target_connector": connector if target else None,
        "m": m,
        "T": T,
        "p": p,
        "h": h,
        "s": s,
        "e_T": e_T,
        "e_M": e_M,
        "e_PH": e_T + e_M,
        "E_T": m * e_T,
        "E_M": m * e_M,
        "E_PH": m * (e_T + e_M),
        "E": m * (e_T + e_M),
    }


def _power(source, target, connector, E):
    return {
        "kind": "power",
        "source_component": source,
        "source_connector": connector if source else None,
        "target_component": target,
        "target_connector": connector if target else None,
        "energy_flow": E,
        "E": E,
    }


def _run(components, connections, fuel, product, costs, split_physical_exergy=True):
    ean = ExergyAnalysis(components, connections, T0, P0, split_physical_exergy=split_physical_exergy)
    ean.analyse(E_F=fuel, E_P=product, E_L={"inputs": [], "outputs": []})
    eco = ExergoeconomicAnalysis(ean)
    eco.run(costs)
    assert eco.system_costs["C_P"] == pytest.approx(eco.system_costs["C_F"] + eco.system_costs["Z"], rel=1e-9)
    return eco


@pytest.mark.parametrize(
    ("E_ref", "E_out", "ref_is_outlet", "expected"),
    [
        (2.0, 4.0, False, [0.5, -0.25]),
        # Either side without exergy: the outlet carries no cost of the share, the inlet is left alone.
        (0.0, 4.0, False, [0.0, 1.0]),
        (2.0, 0.0, False, [0.0, 1.0]),
        (0.0, 0.0, False, [0.0, 1.0]),
        # Two outlets: the one without exergy carries no cost of the share.
        (0.0, 4.0, True, [1.0, 0.0]),
        (2.0, 0.0, True, [0.0, 1.0]),
        (0.0, 0.0, True, [0.0, 1.0]),
    ],
)
def test_equal_specific_cost_row(E_ref, E_out, ref_is_outlet, expected):
    A = np.zeros((1, 2))
    set_equal_specific_cost(A, 0, _cost_stream("ref", 0, M=E_ref), _cost_stream("out", 1, M=E_out), "M", ref_is_outlet)
    assert A[0] == pytest.approx(expected)


def test_mixing_row_skips_an_inlet_without_exergy():
    """An idle inlet (no mass flow) adds nothing and does not divide by zero."""
    A = np.zeros((1, 3))
    inlets = [_cost_stream("a", 0, M=4.0), {**_cost_stream("b", 1, M=0.0), "m": 0.0}]
    set_mixing_cost(A, 0, inlets, _cost_stream("out", 2, M=8.0), "M")
    assert A[0] == pytest.approx([0.25, 0.0, -0.125])


def test_mixing_row_of_an_outlet_without_exergy():
    A = np.zeros((1, 3))
    inlets = [_cost_stream("a", 0, M=4.0), _cost_stream("b", 1, M=-1.0)]
    set_mixing_cost(A, 0, inlets, _cost_stream("out", 2, M=0.0), "M")
    assert A[0] == pytest.approx([0.0, 0.0, 1.0])


def test_mixing_row_counts_an_inlet_as_often_as_it_exists():
    """An inlet standing in for 3 parallel branches weighs 3 times its mass flow."""
    A = np.zeros((1, 3))
    inlets = [_cost_stream("a", 0, M=4.0), _cost_stream("b", 1, M=8.0)]
    set_mixing_cost(A, 0, inlets, _cost_stream("out", 2, M=10.0), "M", weights=[3, 1])
    # m_out = 3 * 2 + 2 = 8 kg/s
    assert A[0] == pytest.approx([3 * 2 / (8 * 4.0), 2 / (8 * 8.0), -0.1])


@pytest.mark.parametrize("component", [Pump, Compressor])
def test_chemical_row_of_a_stream_without_chemical_exergy(component):
    """Without chemical exergy on either side the outlet carries no chemical cost."""
    machine = component(name="M")
    machine.inl = {0: {**_cost_stream("in", 0, T=10.0, M=5.0, CH=0.0), "T": 300.0}}
    machine.outl = {0: {**_cost_stream("out", 3, T=12.0, M=9.0, CH=0.0), "T": 310.0}}
    A, b = np.zeros((2, 6)), np.zeros(2)
    machine.aux_eqs(A, b, 0, T0, {}, True, True)
    assert A[0] == pytest.approx([0, 0, 0, 0, 0, 1])


@pytest.mark.parametrize("component", [Pump, Compressor])
def test_share_without_exergy_rise_passes_through(component):
    """Above the ambient temperature, a share the stream does not gain keeps its specific cost."""
    machine = component(name="M")
    machine.inl = {0: {**_cost_stream("in", 0, T=10.0, M=5.0), "T": 300.0}}
    machine.outl = {0: {**_cost_stream("out", 2, T=10.0, M=9.0), "T": 310.0}}
    A, b = np.zeros((1, 4)), np.zeros(1)
    machine.aux_eqs(A, b, 0, T0, {}, False, True)
    assert A[0] == pytest.approx([0.1, 0, -0.1, 0])


def test_heat_exchanger_heating_ambient_air():
    """The air enters at the ambient state and leaves below the ambient pressure.

    Its inlet has no mechanical exergy, so the mechanical cost of the outlet is zero instead of
    pinning the inlet, whose cost is already set at the boundary.
    """
    connections = {
        "h1": _state("Water", 353.15, 3e5, 2.0, target="HX"),
        "h2": _state("Water", 313.15, 2.9e5, 2.0, source="HX"),
        "c1": _state("Air", T0, P0, 20.0, target="HX", connector=1),
        "c2": _state("Air", 300.0, P0 - 500.0, 20.0, source="HX", connector=1),
    }
    eco = _run(
        {"HeatExchanger": {"HX": {"name": "HX", "type": "HeatExchanger"}}},
        connections,
        {"inputs": ["h1"], "outputs": ["h2"]},
        {"inputs": ["c2"], "outputs": ["c1"]},
        {"HX_Z": 5.0, "h1_c": 20.0, "c1_c": 0.0},
    )
    assert connections["c1"]["E_M"] == 0
    assert connections["c2"]["E_M"] != 0
    assert eco.connections["c2"]["C_M"] == pytest.approx(0, abs=1e-12)
    assert eco.connections["c2"]["C_T"] > 0


def test_turbine_exhausting_at_ambient_pressure():
    """The exhaust has no mechanical exergy and carries no mechanical cost."""
    inlet = _state("Nitrogen", 900.0, 5e5, 10.0, target="EXP")
    outlet = _state("Nitrogen", 600.0, P0, 10.0, source="EXP")
    W = 10.0 * (inlet["h"] - outlet["h"])
    eco = _run(
        {"Turbine": {"EXP": {"name": "EXP", "type": "Turbine"}}},
        {"1": inlet, "2": outlet, "W": _power("EXP", None, 1, W)},
        {"inputs": ["1"], "outputs": ["2"]},
        {"inputs": ["W"], "outputs": []},
        {"EXP_Z": 50.0, "1_c": 10.0},
    )
    assert eco.connections["2"]["C_M"] == pytest.approx(0, abs=1e-15)
    assert eco.connections["2"]["c_T"] == pytest.approx(eco.connections["1"]["c_T"], rel=1e-9)


def test_power_bus_with_an_outlet_without_power():
    """A 0 W outlet carries no cost, so the cost of the system closes."""
    eco = _run(
        {"PowerBus": {"BUS": {"name": "BUS", "type": "PowerBus"}}},
        {"e0": _power(None, "BUS", 0, 1e5), "eA": _power("BUS", None, 0, 1e5), "eB": _power("BUS", None, 1, 0.0)},
        {"inputs": ["e0"], "outputs": []},
        {"inputs": ["eA", "eB"], "outputs": []},
        {"e0_c": 30.0},
        split_physical_exergy=False,
    )
    assert eco.connections["eB"]["C_TOT"] == pytest.approx(0, abs=1e-15)
    assert eco.connections["eA"]["C_TOT"] == pytest.approx(eco.connections["e0"]["C_TOT"], rel=1e-12)


def test_mixer_with_an_idle_inlet():
    """An inlet without mass flow has exergy per kg but no exergy flow, and adds nothing."""
    connections = {
        "A": _state("Water", 350.0, 3e5, 5.0, target="MIX"),
        "B": _state("Water", 350.0, 3e5, 0.0, target="MIX", connector=1),
        "C": _state("Water", 350.0, 3e5, 5.0, source="MIX"),
    }
    eco = _run(
        {"Mixer": {"MIX": {"name": "MIX", "type": "Mixer"}}},
        connections,
        {"inputs": ["A", "B"], "outputs": ["C"]},
        {"inputs": [], "outputs": []},
        {"MIX_Z": 1.0, "A_c": 10.0, "B_c": 10.0},
    )
    assert eco.connections["C"]["c_M"] == pytest.approx(eco.connections["A"]["c_M"], rel=1e-9)


def test_mixer_outlet_without_mechanical_exergy():
    """The outlet leaves at the ambient pressure and carries no mechanical cost."""
    hot = _state("Water", 340.0, 3e5, 4.0, target="MIX")
    cold = _state("Water", 320.0, P0, 6.0, target="MIX", connector=1)
    h_mix = (4.0 * hot["h"] + 6.0 * cold["h"]) / 10.0
    out = _state("Water", CP.PropsSI("T", "H", h_mix, "P", P0, "Water"), P0, 10.0, source="MIX")
    eco = _run(
        {"Mixer": {"MIX": {"name": "MIX", "type": "Mixer"}}},
        {"A": hot, "B": cold, "C": out},
        {"inputs": ["A", "B"], "outputs": ["C"]},
        {"inputs": [], "outputs": []},
        {"MIX_Z": 1.0, "A_c": 20.0, "B_c": 20.0},
    )
    assert out["E_M"] == 0
    assert eco.connections["C"]["C_M"] == pytest.approx(0, abs=1e-15)


def test_refrigerant_loop_without_chemical_exergy():
    """R245fa has no chemical exergy in the library, so the closed loop carries no chemical cost."""
    ean = ExergyAnalysis.from_json(
        os.path.join(EXAMPLES, "exergy_analysis", "heatpump", "hp_tespy.json"), chemExLib="Ahrendts"
    )
    ean.analyse(
        E_F={"inputs": ["e1"], "outputs": []},
        E_P={"inputs": ["23"], "outputs": ["21"]},
        E_L={"inputs": ["13"], "outputs": ["11"]},
    )
    eco = ExergoeconomicAnalysis(ean)
    costs = {name + "_Z": 5.0 for name in ("COMP", "FAN", "COND", "EVA", "MOT1", "MOT2", "MOT3", "PUMP", "VAL")}
    eco.run({**costs, "e1_c": 30.0, "21_c": 0.0, "11_c": 0.0})
    loop = [c for c in eco.connections.values() if c.get("kind") == "material" and c.get("E_CH") == 0]
    assert loop
    for conn in loop:
        assert conn["C_CH"] == pytest.approx(0, abs=1e-12)
    assert eco.system_costs["C_P"] == pytest.approx(eco.system_costs["C_F"] + eco.system_costs["Z"], rel=1e-6)
