__version__ = "0.0.1"

import importlib.resources
import os
import sys

__datapath__ = os.path.join(importlib.resources.files("exerpy"), "data")
__ebsilon_path__ = os.getenv("EBS")
if __ebsilon_path__ is not None:
    sys.path.append(__ebsilon_path__)


from .analyses import ExergyAnalysis
