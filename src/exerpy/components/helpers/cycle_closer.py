import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class CycleCloser(Component):
    r"""
    Component for closing cycles. This component is not analyzed in exergy analysis.
    """
    def __init__(self, **kwargs):
        r"""Initialize CycleCloser component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        The CycleCloser component does not have an exergy balance calculation.
        """      
        self.E_D = np.nan
        self.E_F = np.nan
        self.E_P = np.nan
        self.E_L = np.nan
        self.epsilon = np.nan

        # Log the results
        logging.info(
            f"The exergy balance of a CycleCloser component is skipped."
        )