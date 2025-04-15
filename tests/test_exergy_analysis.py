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

_basepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../examples/")
directories = [
    os.path.join(_basepath, dirname) for dirname in os.listdir(_basepath)
    if os.path.isdir(os.path.join(_basepath, dirname))
]
examples_json = []
for directory in directories:
    examples_json.append({})
    for file in os.listdir(directory):
        if file.endswith(".json"):
            examples_json[-1][file.removesuffix(".json")] = os.path.join(directory, file)

TESTCASES = [
    {c: example[c] for c in case} for example in examples_json
    for case in combinations(example, 2)
]


@pytest.mark.parametrize(
        "testcase", TESTCASES
    )
def test_validate_simulators_connection_data(testcase, caplog):
    simulator_results = []

    caplog.set_level(logging.INFO)
    logging.info(f"TESTCASE {'-'.join(testcase)}")
    caplog.set_level(logging.WARNING)

    for path in testcase.values():
        contents = _load_json(path)
        if "settings" not in contents:
            contents["settings"] = {}

        simulator_results += [
            ExergyAnalysis.from_json(path, **contents["settings"])
        ]

    sim1 = simulator_results[0]
    sim2 = simulator_results[1]

    columns = ["m", "p", "T"]
    if sim1.chemExLib is not None:
        columns.append("e_CH")
    if sim1.split_physical_exergy:
        columns.append("e_M")
        columns.append("e_T")
    else:
        columns.append("e_PH")

    df_sim1 = pd.DataFrame.from_dict(
        sim1._connection_data, orient="index"
    ).sort_index()[columns].dropna(how="all")
    df_sim2 = pd.DataFrame.from_dict(
        sim2._connection_data, orient="index"
    ).sort_index()[columns].dropna(how="all")

    overlapping_index = list(
        set(df_sim1.index.tolist()) & set(df_sim2.index.tolist())
    )
    df_sim1 = df_sim1.loc[overlapping_index].round(6)
    df_sim2 = df_sim2.loc[overlapping_index].round(6)

    # inf means that sim2 has 0 value, comparison does not make sense there
    # and sometimes there seem to be NaN values in the dataframes, those are
    # removed as well
    diff_to_sim2 = (
        (df_sim1 - df_sim2) / df_sim2
    ).abs().replace(np.inf, 0).fillna(0)
    assert (diff_to_sim2 < 2e-2).all().all()


@pytest.fixture
def exergy_analysis():
    """Set up the ExergyAnalysis object using the data from cgam_ebs.json."""
    # Define the path to the JSON file
    file_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '../examples/cgam/cgam_ebs.json'
        )
    )
    # Return an initialized ExergyAnalysis object
    return ExergyAnalysis.from_json(file_path, split_physical_exergy=False)


def test_exergy_analysis_results(exergy_analysis):
    """Test the overall exergy analysis results, allowing for a tolerance of 100."""
    fuel = {"inputs": ['1', '10'], "outputs": []}
    product = {"inputs": ['E1', '9'], "outputs": ['8']}
    loss = {"inputs": ['7'], "outputs": []}
    exergy_analysis.analyse(fuel, product, loss)

    # Check the calculated values with a tolerance of 100
    assert pytest.approx(exergy_analysis.E_F, abs=100) == 85081016
    assert pytest.approx(exergy_analysis.E_P, abs=100) == 42753645
    assert pytest.approx(exergy_analysis.E_D, abs=100) == 39466737
    assert pytest.approx(exergy_analysis.E_L, abs=100) == 2860633
