"""
Shared pytest configuration.

The plotting tests must not depend on an interactive matplotlib backend: a GUI backend needs a
working Tk installation and a display, which is not given on CI or in every editor's test runner.
Selecting the non-interactive Agg backend here makes the tests behave the same way regardless of
how they are started. The tox environments set MPLBACKEND=Agg for the same reason.
"""

import matplotlib
import pytest

from exerpy.units import entries

matplotlib.use("Agg")

# Numbers that identify or count rather than measure, so they have no unit.
UNITLESS = {
    "type_index",
    "source_connector",
    "target_connector",
    "source_component_type",
    "target_component_type",
    "fluid_type_id",
    "num_branches",
}


@pytest.fixture
def values_without_unit():
    """Return a function that lists the paths of the numbers in a document that have no unit."""

    def find(data):
        return [
            f"{path}.{key}"
            for entry, path in entries(data)
            for key, value in entry.items()
            if isinstance(value, int | float)
            and not isinstance(value, bool)
            and key not in UNITLESS
            and not key.startswith("_")
            and f"{key}_unit" not in entry
        ]

    return find
