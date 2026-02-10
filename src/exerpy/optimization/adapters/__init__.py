"""
Simulator adapters for exergoeconomic optimization.

This module provides adapters for different simulation tools that can be
used with the ExergoeconomicOptimizer.

Available Adapters
------------------
- TESPyAdapter: For TESPy thermal engineering system models
- EbsilonAdapter: For Ebsilon Professional models (Windows only)
- AspenAdapter: For Aspen Plus models (Windows only)

The adapters provide a unified interface for:
- Getting and setting simulation parameters
- Running the simulation solver
- Exporting simulation state to ExerPy format
"""

from .base import SimulatorAdapter

__all__ = ["SimulatorAdapter"]

# Lazy imports for simulator-specific adapters to avoid import errors
# when the required packages are not installed


def __getattr__(name: str):
    """Lazy import of simulator-specific adapters."""
    if name == "TESPyAdapter":
        from .tespy import TESPyAdapter

        return TESPyAdapter
    elif name == "EbsilonAdapter":
        from .ebsilon import EbsilonAdapter

        return EbsilonAdapter
    elif name == "AspenAdapter":
        from .aspen import AspenAdapter

        return AspenAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
