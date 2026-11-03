"""
Live test of the EBSILON and Aspen Plus parsers on the example models.

The test runs the simulators, so it needs both of them with a license and takes a few minutes. It runs only
if the environment variable EXERPY_SIMULATOR_TESTS is 1, e.g. ``EXERPY_SIMULATOR_TESTS=1 pytest
tests/test_simulators.py``. It checks that the parsers still produce the results the example scripts stored,
which the other tests use as the results of the simulators.
"""

import os

import pytest

from exerpy import ExergyAnalysis

pytestmark = pytest.mark.skipif(
    os.environ.get("EXERPY_SIMULATOR_TESTS") != "1", reason="set EXERPY_SIMULATOR_TESTS=1 to run the simulators"
)

_EXAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "../examples/exergy_analysis"))

# folder and chemical exergy library of each example
MODELS = {"hp": ("heatpump", None), "ccpp": ("ccpp", "Ahrendts"), "cgam": ("cgam", "Ahrendts")}
KEYS = ("m", "T", "p", "h", "s", "e_PH", "e_T", "e_M", "e_CH")


@pytest.mark.parametrize("simulator", ["aspen", "ebsilon"])
@pytest.mark.parametrize("model", list(MODELS))
def test_parser_reproduces_stored_results(model, simulator):
    folder, chemExLib = MODELS[model]
    base = os.path.join(_EXAMPLES, folder)
    if simulator == "aspen":
        parsed = ExergyAnalysis.from_aspen(
            os.path.join(base, f"{model}.bkp"), chemExLib=chemExLib, split_physical_exergy=True
        )
        stored = ExergyAnalysis.from_json(os.path.join(base, f"{model}_aspen.json"))
    else:
        parsed = ExergyAnalysis.from_ebsilon(
            os.path.join(base, f"{model}.ebs"), chemExLib=chemExLib, split_physical_exergy=True
        )
        stored = ExergyAnalysis.from_json(os.path.join(base, f"{model}_ebs.json"))

    mismatches = []
    for name, conn in stored.connections.items():
        if conn.get("kind") != "material":
            continue
        for key in KEYS:
            if conn.get(key) is None:
                continue
            value = parsed.connections[name].get(key)
            if value is None or value != pytest.approx(conn[key], rel=1e-6, abs=1e-3):
                mismatches.append((name, key, value, conn[key]))
    assert not mismatches
