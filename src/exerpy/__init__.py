__version__ = "0.0.5"

import importlib.resources
import os
import sys

__datapath__ = os.path.join(importlib.resources.files("exerpy"), "data")


from .analyses import EconomicAnalysis, ExergoeconomicAnalysis, ExergyAnalysis
