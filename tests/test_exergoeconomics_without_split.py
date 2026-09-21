"""Exergoeconomic analysis with and without split physical exergy.

The tests check the counting invariant every component has to respect: the cost variables of the
outlet streams of a component are determined by its own cost balance and by the auxiliary equations
it provides, so it has to write one equation less than it has outlet cost variables. A dissipative
component has no cost balance, but one cost variable of its own instead.
"""

import os

import numpy as np
import pytest

from exerpy import ExergoeconomicAnalysis
from exerpy import ExergyAnalysis
from exerpy.components.helpers.cycle_closer import CycleCloser
from exerpy.components.helpers.power_bus import PowerBus
from exerpy.components.nodes.splitter import Splitter

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")

# Gas turbine with a heat recovery steam generator: every stream above the ambient temperature.
CGAM = {
    "path": os.path.join(EXAMPLES, "exergoeconomic_analysis", "json_example", "example.json"),
    "chemExLib": None,
    "E_F": {"inputs": ["10", "1", "8"], "outputs": []},
    "E_P": {"inputs": ["E1", "9"], "outputs": []},
    "E_L": {"inputs": ["7"], "outputs": []},
    "costs": {
        "AC_Z": 80,
        "CC_Z": 30,
        "EXP_Z": 100,
        "GEN_Z": 40,
        "APH_Z": 50,
        "EV_Z": 60,
        "PH_Z": 35,
        "1_c": 0.0,
        "10_c": 10.0,
        "8_c": 0.5,
    },
}

# Heat pump: streams below the ambient temperature, a dissipative valve, motors and a power bus.
HEAT_PUMP = {
    "path": os.path.join(EXAMPLES, "exergy_analysis", "heatpump", "hp_tespy.json"),
    "chemExLib": None,
    "E_F": {"inputs": ["e1"], "outputs": []},
    "E_P": {"inputs": ["23"], "outputs": ["21"]},
    "E_L": {"inputs": ["13"], "outputs": ["11"]},
    "costs": {
        **{name + "_Z": 5.0 for name in ("COMP", "FAN", "COND", "EVA", "MOT1", "MOT2", "MOT3", "PUMP", "VAL")},
        "e1_c": 30.0,
        "21_c": 0.0,
        "11_c": 0.0,
    },
}

# Gas turbine with a drum, a combustion chamber and chemical exergy.
CGAM_CHEMICAL = {
    "path": os.path.join(EXAMPLES, "exergy_analysis", "cgam", "cgam_tespy.json"),
    "chemExLib": "Ahrendts",
    "E_F": {"inputs": ["1", "10"], "outputs": []},
    "E_P": {"inputs": ["e3", "9"], "outputs": ["8"]},
    "E_L": {"inputs": ["7"], "outputs": []},
    "costs": {
        "AC_Z": 20,
        "CC_Z": 10,
        "EXP_Z": 30,
        "APH_Z": 15,
        "EV_Z": 12,
        "PH_Z": 8,
        "DRUM_Z": 0.0,
        "1_c": 0.0,
        "10_c": 4.0,
        "8_c": 0.0,
    },
}

MODELS = {"cgam": CGAM, "heat_pump": HEAT_PUMP, "cgam_chemical": CGAM_CHEMICAL}


def _run(model, split, record=False):
    """Run the exergoeconomic analysis and, on request, record the rows of every component."""
    ean = ExergyAnalysis.from_json(model["path"], chemExLib=model["chemExLib"], split_physical_exergy=split)
    ean.analyse(E_F=model["E_F"], E_P=model["E_P"], E_L=model["E_L"])
    eco = ExergoeconomicAnalysis(ean)

    rows = {}
    if record:
        for comp in eco.components.values():
            for name in ("aux_eqs", "dis_eqs"):
                if callable(getattr(comp, name, None)):
                    _wrap(comp, name, rows)

    eco.run(model["costs"])
    return eco, rows


def _wrap(comp, name, rows):
    method = getattr(comp, name)

    def wrapper(A, b, counter, *args, **kwargs):
        result = method(A, b, counter, *args, **kwargs)
        rows[comp.name] = rows.get(comp.name, 0) + result[2] - counter
        return result

    setattr(comp, name, wrapper)


def _expected_rows(eco, comp):
    """Number of auxiliary equations the component has to provide."""
    outlet_variables = sum(
        # The extra cost variable of a dissipative component sits on its inlet, which is an outlet of
        # the component upstream. It belongs to the dissipative component, not to that one.
        len([key for key in conn["CostVar_index"] if key != "dissipative"])
        for conn in eco.connections.values()
        if conn.get("source_component") == comp.name
    )
    if getattr(comp, "is_dissipative", False):
        # No cost balance, but the extra cost variable of the dissipative component itself.
        return outlet_variables + 1
    if isinstance(comp, (CycleCloser, Splitter, PowerBus)):
        # These components have no cost balance equation.
        return outlet_variables
    return outlet_variables - 1


@pytest.mark.parametrize("model", MODELS.values(), ids=MODELS.keys())
@pytest.mark.parametrize("split", [True, False])
def test_number_of_auxiliary_equations(model, split):
    eco, rows = _run(model, split, record=True)
    for comp in eco.components.values():
        assert rows.get(comp.name, 0) == _expected_rows(
            eco, comp
        ), f"{comp.name} ({type(comp).__name__}) provides the wrong number of auxiliary equations"


@pytest.mark.parametrize("model", MODELS.values(), ids=MODELS.keys())
@pytest.mark.parametrize("split", [True, False])
def test_cost_of_every_material_stream_is_assigned(model, split):
    eco, _ = _run(model, split)
    for conn in eco.connections.values():
        part_of_the_system = (
            conn.get("source_component") in eco.components or conn.get("target_component") in eco.components
        )
        if conn.get("kind") != "material" or not part_of_the_system:
            continue
        assert np.isfinite(conn["C_PH"])
        assert np.isfinite(conn["c_PH"])
        assert ("C_T" in conn) is split
        assert ("C_M" in conn) is split


@pytest.mark.parametrize("model", MODELS.values(), ids=MODELS.keys())
@pytest.mark.parametrize("split", [True, False])
def test_cost_balance_of_the_system_closes(model, split):
    eco, _ = _run(model, split)
    costs = eco.system_costs
    assert costs["C_P"] == pytest.approx(costs["C_F"] + costs["Z"], rel=1e-6)


def test_results_table_columns_follow_the_cost_variables():
    _, _, df_split, _ = _run(CGAM, True)[0].exergoeconomic_results(print_results=False)
    _, _, df_unsplit, _ = _run(CGAM, False)[0].exergoeconomic_results(print_results=False)
    assert "C^T [EUR/h]" in df_split.columns
    assert "C^M [EUR/h]" in df_split.columns
    assert "C^PH [EUR/h]" not in df_split.columns
    assert "C^PH [EUR/h]" in df_unsplit.columns
    assert "c^PH [EUR/GJ_ex]" in df_unsplit.columns
    assert "C^T [EUR/h]" not in df_unsplit.columns
