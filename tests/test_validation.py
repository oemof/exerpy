"""
Validation of the example plants modelled in EBSILON, Aspen Plus and TESPy.

The heat pump, the combined cycle power plant and the CGAM process are modelled in all three simulators; the
example scripts store the results of each model. These tests analyse the stored results again and compare the
exergy destruction of each component (or group of components, where the simulators divide the plant
differently) and the exergetic efficiency of the plant with the results based on EBSILON.
"""

import math
import os

import pytest

from exerpy import ExergyAnalysis

_EXAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../examples/exergy_analysis")

#: Largest relative deviation of the exergy destruction of a component from the result based on EBSILON.
E_D_TOLERANCE = 0.006
#: Largest deviation of the exergetic efficiency of the plant from the result based on EBSILON (0.1 points).
EPSILON_TOLERANCE = 0.001


def _boundaries(fuel, product, loss):
    return {
        "E_F": {"inputs": fuel, "outputs": []},
        "E_P": {"inputs": product[0], "outputs": product[1]},
        "E_L": {"inputs": loss[0], "outputs": loss[1]},
    }


# Fuel, product and loss as in the example scripts, and the components each simulator models differently
MODELS = {
    "hp": {
        "folder": "heatpump",
        "groups": {"PUMP-MOTOR": "MOT3"},
        "ebs": _boundaries(["E1", "E2", "E3"], (["23"], ["21"]), (["13"], ["11"])),
        "aspen": _boundaries(["E1", "E2", "E3"], (["23"], ["21"]), (["13"], ["11"])),
        "tespy": _boundaries(["e1"], (["23"], ["21"]), (["13"], ["11"])),
    },
    "ccpp": {
        "folder": "ccpp",
        "groups": {
            "MIX": "DEA",
            "dea steam inlet valve": "DEA",
            "drum": "EVA",
            "drum pump": "EVA",
            "drum pump motor": "EVA",
            "PUMP1-MOTOR": "MOT1",
            "PUMP2-MOTOR": "MOT2",
        },
        "ebs": _boundaries(["1", "3"], (["ETOT", "H1"], []), (["8", "15"], ["14"])),
        "aspen": _boundaries(["1", "3"], (["ETOT", "HC_HEAT"], []), (["8", "15"], ["14"])),
        "tespy": _boundaries(["1", "3"], (["e15", "h1"], []), (["8", "15"], ["14"])),
    },
    "cgam": {
        "folder": "cgam",
        "groups": {"COMB": "CC", "DRUM": "EV"},
        "ebs": _boundaries(["1", "10"], (["E1", "9"], ["8"]), (["7"], [])),
        "aspen": _boundaries(["1", "10"], (["E1", "9"], ["8"]), (["7"], [])),
        "tespy": _boundaries(["1", "10"], (["e3", "9"], ["8"]), (["7"], [])),
    },
}


def _analyse(model, simulator, split_physical_exergy):
    """Exergy destruction in W of each component or group, and the exergetic efficiency of the plant."""
    spec = MODELS[model]
    path = os.path.join(_EXAMPLES, spec["folder"], f"{model}_{simulator}.json")
    ean = ExergyAnalysis.from_json(path, split_physical_exergy=split_physical_exergy)
    ean.analyse(**spec[simulator])
    E_D = {}
    for name, component in ean.components.items():
        value = getattr(component, "E_D", None)
        if value is not None and math.isfinite(value):
            group = spec["groups"].get(name, name)
            E_D[group] = E_D.get(group, 0.0) + value
    return E_D, ean.epsilon


@pytest.mark.parametrize("split_physical_exergy", [True, False])
@pytest.mark.parametrize("simulator", ["aspen", "tespy"])
@pytest.mark.parametrize("model", list(MODELS))
def test_against_ebsilon(model, simulator, split_physical_exergy):
    E_D_reference, epsilon_reference = _analyse(model, "ebs", split_physical_exergy)
    E_D, epsilon = _analyse(model, simulator, split_physical_exergy)

    # no relative deviation of components that destroy less than 1 W
    deviations = {
        name: E_D[name] / reference - 1
        for name, reference in E_D_reference.items()
        if name in E_D and abs(reference) > 1.0
    }
    assert len(deviations) >= 5
    assert all(abs(deviation) <= E_D_TOLERANCE for deviation in deviations.values()), deviations
    assert epsilon == pytest.approx(epsilon_reference, abs=EPSILON_TOLERANCE)
