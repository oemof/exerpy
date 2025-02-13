__version__ = "0.0.1"

import importlib.resources
import os
import sys

__datapath__ = os.path.join(importlib.resources.files("exerpy"), "data")


from .analyses import ExergyAnalysis
