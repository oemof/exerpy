__version__ = "0.0.1"

import importlib.resources
import os

__datapath__ = os.path.join(importlib.resources.files("exerpy"), "data")

from .analyses import ExergyAnalysis
from .analyses import ExergoeconomicAnalysis