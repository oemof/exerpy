import os
import pathlib
import runpy

import numpy as np
import pandas as pd
import pytest

from exerpy import ExergyAnalysis
from exerpy.analyses import _load_json

path = os.path.join(os.path.dirname(__file__), "..", "examples")
examples = sorted(pathlib.Path(path).glob("**/*tespy.py"))

# Maximum acceptable relative deviation between the tespy results and the
# results of the other simulators. The observed deviations are all around or
# below 1 %, see the validation notebooks next to the example scripts.
RELATIVE_TOLERANCE = 0.02


def _relative_differences(path1, path2):
    """Relative connection data differences between two simulator exports.

    Same comparison as in the validation notebooks of the examples.
    """
    simulator_results = []
    for json_path in (path1, path2):
        contents = _load_json(str(json_path))
        settings = contents.get("settings", {})
        simulator_results += [
            ExergyAnalysis.from_json(str(json_path), **settings)
        ]

    sim1, sim2 = simulator_results

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
    return (
        (df_sim1 - df_sim2) / df_sim2
    ).abs().replace(np.inf, 0).fillna(0)


@pytest.mark.parametrize("script", examples, ids=lambda script: script.stem)
def test_tespy_model_execution(script):
    runpy.run_path(script)

    tespy_json = script.with_suffix(".json")
    assert tespy_json.is_file(), (
        f"Expected the script {script.name} to export its results to "
        f"{tespy_json.name}."
    )

    reference_jsons = [
        reference for suffix in ("_ebs.json", "_aspen.json")
        if (reference := tespy_json.with_name(
            tespy_json.name.replace("_tespy.json", suffix)
        )).is_file()
    ]
    assert reference_jsons, (
        f"No reference results of other simulators found next to {script.name}."
    )

    for reference_json in reference_jsons:
        diff = _relative_differences(tespy_json, reference_json)
        assert (diff <= RELATIVE_TOLERANCE).all().all(), (
            f"Deviation between {tespy_json.name} and {reference_json.name} "
            f"exceeds {RELATIVE_TOLERANCE:.0%}:\n"
            f"{diff[(diff > RELATIVE_TOLERANCE).any(axis=1)]}"
        )
