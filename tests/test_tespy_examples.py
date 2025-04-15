import os
import pathlib
import runpy

import pytest

path = os.path.join(os.path.dirname(__file__), "..", "examples")
examples = pathlib.Path(path).glob('**/*tespy.py')

@pytest.mark.parametrize('script', examples)
def test_tespy_model_execution(script):
    runpy.run_path(script)
