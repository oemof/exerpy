"""
Integration tests for the ExergyAnalysis class.

This file contains tests that perform end-to-end verification of the ExergyAnalysis class
by loading real example files (e.g., cgam_ebs.json) and ensuring that the analysis returns
expected results. These tests check the integration of file loading, parsing, and calculation.
"""

import logging
import os
from itertools import combinations

import numpy as np
import pandas as pd
import pytest

from exerpy import ExergyAnalysis
from exerpy.analyses import _load_json

# The exergy analysis examples: every sub directory holds the exports of the same plant from
# the different simulators. The exports live one level deeper than the examples directory, so
# the tree is walked instead of listing a single level.
_basepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../examples/exergy_analysis/")
examples_json = []
for directory, _subdirs, files in sorted(os.walk(_basepath)):
    exports = {}
    for file in sorted(files):
        if not file.endswith(".json"):
            continue
        path = os.path.join(directory, file)
        # Skip JSON files that are not analysis exports; only exports carry a "components" section.
        try:
            if "components" not in _load_json(path):
                continue
        except (ValueError, OSError):
            continue
        exports[file.removesuffix(".json")] = path
    # An export is named <model>_<simulator>.json, so group by model: only exports of the
    # same plant may be compared with each other, not e.g. a parabolic trough with a solar tower.
    models = {}
    for stem, path in exports.items():
        models.setdefault(stem.rsplit("_", 1)[0], {})[stem] = path
    examples_json.extend(models.values())

TESTCASES = [{c: example[c] for c in case} for example in examples_json for case in combinations(example, 2)]


@pytest.mark.parametrize("testcase", TESTCASES)
def test_validate_simulators_connection_data(testcase, caplog):
    if any("hp_cascade" in p for p in testcase.values()):
        pytest.skip("ignoring the high‐temp/high‐pressure example")

    simulator_results = []

    caplog.set_level(logging.INFO)
    logging.info(f"TESTCASE {'-'.join(testcase)}")
    caplog.set_level(logging.WARNING)

    for path in testcase.values():
        contents = _load_json(path)
        if "settings" not in contents:
            contents["settings"] = {}

        simulator_results += [ExergyAnalysis.from_json(path, **contents["settings"])]

    sim1 = simulator_results[0]
    sim2 = simulator_results[1]

    columns = ["m", "p", "T"]
    if sim1.chemExLib is not None and sim2.chemExLib is not None:
        columns.append("e_CH")
    if sim1.split_physical_exergy and sim2.split_physical_exergy:
        columns.append("e_M")
        columns.append("e_T")
    elif not sim1.split_physical_exergy and not sim2.split_physical_exergy:
        columns.append("e_PH")
    # If split_physical_exergy settings differ, only compare base columns (m, p, T)

    df_sim1 = pd.DataFrame.from_dict(sim1._connection_data, orient="index").sort_index()[columns].dropna(how="all")
    df_sim2 = pd.DataFrame.from_dict(sim2._connection_data, orient="index").sort_index()[columns].dropna(how="all")

    overlapping_index = list(set(df_sim1.index.tolist()) & set(df_sim2.index.tolist()))
    df_sim1 = df_sim1.loc[overlapping_index].round(6)
    df_sim2 = df_sim2.loc[overlapping_index].round(6)

    # inf means that sim2 has 0 value, comparison does not make sense there
    # and sometimes there seem to be NaN values in the dataframes, those are
    # removed as well
    diff_to_sim2 = ((df_sim1 - df_sim2) / df_sim2).abs().replace(np.inf, 0).fillna(0)
    assert (diff_to_sim2 < 2e-2).all().all()


@pytest.fixture
def exergy_analysis():
    """Set up the ExergyAnalysis object using the data from cgam_ebs.json."""
    # Define the path to the JSON file
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../examples/exergy_analysis/cgam/cgam_ebs.json")
    )
    # Return an initialized ExergyAnalysis object
    return ExergyAnalysis.from_json(file_path, split_physical_exergy=False)


def test_exergy_analysis_results(exergy_analysis):
    """Test the overall exergy analysis results, allowing for a tolerance of 100."""
    fuel = {"inputs": ["1", "10"], "outputs": []}
    product = {"inputs": ["E1", "9"], "outputs": ["8"]}
    loss = {"inputs": ["7"], "outputs": []}
    exergy_analysis.analyse(fuel, product, loss)

    # Check the calculated values with a tolerance of 100
    assert pytest.approx(exergy_analysis.E_F, abs=100) == 85081016
    assert pytest.approx(exergy_analysis.E_P, abs=100) == 42753645
    assert pytest.approx(exergy_analysis.E_D, abs=100) == 39466737
    assert pytest.approx(exergy_analysis.E_L, abs=100) == 2860633


@pytest.fixture
def solar_tower_analysis():
    """Set up the ExergyAnalysis object from the solar-tower example JSON."""
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../examples/exergy_analysis/solar_thermal/solar_tower_ebs.json")
    )
    return ExergyAnalysis.from_json(file_path, split_physical_exergy=False)


def test_solar_tower_example_results(solar_tower_analysis):
    """End-to-end check of the solar-tower example (heliostat field + receiver).

    The fuel 'SF' is a component name; analyse() resolves it to the synthetic SF_Q
    heat connection. Reference values are from solar_tower_ebs.json system_results.
    """
    fuel = {"inputs": ["SF"], "outputs": []}
    product = {"inputs": ["ETOT"], "outputs": []}
    loss = {"inputs": ["C2"], "outputs": ["C1"]}
    solar_tower_analysis.analyse(E_F=fuel, E_P=product, E_L=loss)

    assert pytest.approx(solar_tower_analysis.E_F, rel=1e-4) == 134258774.662513
    assert pytest.approx(solar_tower_analysis.E_P, rel=1e-4) == 29406492.324328158
    assert pytest.approx(solar_tower_analysis.E_D, rel=1e-4) == 103316169.97763622
    assert pytest.approx(solar_tower_analysis.E_L, rel=1e-4) == 1536112.3605486117


# The fuel, product and loss definitions of every example, taken from the example script next to
# the export. With them the exergy balance of the example has to close: the exergy destruction of
# the system must be the sum of the exergy destruction of its components. A deviation means that
# either a component balance or the accounting of the system boundary is wrong, so this is checked
# for every example and every simulator.
EXERGY_FLOWS = {
    "ccpp/ccpp_tespy": (
        {"inputs": ["1", "3"], "outputs": []},
        {"inputs": ["e15", "h1"], "outputs": []},
        {"inputs": ["8", "15"], "outputs": ["14"]},
    ),
    "ccpp/ccpp_ebs": (
        {"inputs": ["1", "3"], "outputs": []},
        {"inputs": ["ETOT", "H1"], "outputs": []},
        {"inputs": ["8", "15"], "outputs": ["14"]},
    ),
    "ccpp/ccpp_aspen": (
        {"inputs": ["1", "3"], "outputs": []},
        {"inputs": ["ETOT", "HC_HEAT"], "outputs": []},
        {"inputs": ["8", "15"], "outputs": ["14"]},
    ),
    "cgam/cgam_tespy": (
        {"inputs": ["1", "10"], "outputs": []},
        {"inputs": ["e3", "9"], "outputs": ["8"]},
        {"inputs": ["7"], "outputs": []},
    ),
    "cgam/cgam_ebs": (
        {"inputs": ["1", "10"], "outputs": []},
        {"inputs": ["E1", "9"], "outputs": ["8"]},
        {"inputs": ["7"], "outputs": []},
    ),
    "cgam/cgam_aspen": (
        {"inputs": ["1", "10"], "outputs": []},
        {"inputs": ["E1", "9"], "outputs": ["8"]},
        {"inputs": ["7"], "outputs": []},
    ),
    "heatpump/hp_tespy": (
        {"inputs": ["e1"], "outputs": []},
        {"inputs": ["23"], "outputs": ["21"]},
        {"inputs": ["13"], "outputs": ["11"]},
    ),
    "heatpump/hp_ebs": (
        {"inputs": ["E1", "E2", "E3"], "outputs": []},
        {"inputs": ["23"], "outputs": ["21"]},
        {"inputs": ["13"], "outputs": ["11"]},
    ),
    "heatpump/hp_aspen": (
        {"inputs": ["E1", "E2", "E3"], "outputs": []},
        {"inputs": ["23"], "outputs": ["21"]},
        {"inputs": ["13"], "outputs": ["11"]},
    ),
    "solar_thermal/parabolic_ebs": (
        {"inputs": ["PARAB"], "outputs": []},
        {"inputs": ["ETOT"], "outputs": []},
        {"inputs": ["C2"], "outputs": ["C1"]},
    ),
    "solar_thermal/solar_tower_ebs": (
        {"inputs": ["SF"], "outputs": []},
        {"inputs": ["ETOT"], "outputs": []},
        {"inputs": ["C2"], "outputs": ["C1"]},
    ),
    "json_example/example": (
        {"inputs": ["1", "3"], "outputs": []},
        {"inputs": ["E1"], "outputs": []},
        {"inputs": ["5"], "outputs": []},
    ),
}


@pytest.mark.parametrize("example", sorted(EXERGY_FLOWS), ids=lambda example: example.replace("/", "-"))
def test_exergy_balance_of_examples_closes(example, caplog):
    """
    Test that the system exergy destruction equals the sum of the component destructions.

    This is the exergy balance of the whole plant: nothing may be destroyed that no component
    destroys, and nothing a component destroys may be missing from the system. The check runs
    over every example and every simulator, so a component balance or an accounting of the system
    boundary that stops adding up is caught before a release.
    """
    E_F, E_P, E_L = EXERGY_FLOWS[example]
    path = os.path.join(_basepath, f"{example}.json")
    contents = _load_json(path)

    ean = ExergyAnalysis.from_json(path, **contents.get("settings", {}))
    with caplog.at_level(logging.WARNING):
        ean.analyse(E_F=E_F, E_P=E_P, E_L=E_L)

    destruction_of_components = sum(
        component.E_D
        for component in ean.components.values()
        if component.__class__.__name__ != "CycleCloser" and component.E_D is not None and np.isfinite(component.E_D)
    )

    assert pytest.approx(destruction_of_components, rel=1e-5) == ean.E_D
    # The analysis must not report the balance as broken either
    assert "does not match overall system exergy destruction" not in caplog.text
