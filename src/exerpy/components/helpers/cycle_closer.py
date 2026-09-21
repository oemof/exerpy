import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class CycleCloser(Component):
    r"""
    Component for closing cycles. This component is not considered in exergy analysis, but it is used in exergoeconomic analysis.
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
        logger.info(f"The exergy balance of a CycleCloser {self.name} is skipped.")

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        """
        Auxiliary equations for the cycle closer.

        This function adds two rows to the cost matrix A and the right-hand side vector b to enforce
        the following auxiliary cost relations:

        (1) 1/E_M_in * C_M_in - 1/E_M_out * C_M_out = 0
        (2) 1/E_T_in * C_T_in - 1/E_T_out * C_T_out = 0

        These equations ensure that the specific mechanical and thermal costs are equalized between
        the inlet and outlet of the cycle closer. Chemical exergy is not considered for the cycle closer.

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature (not used in this component).
        equations : list or dict
            Data structure for storing equation labels.
        chemical_exergy_enabled : bool
            Flag indicating whether chemical exergy auxiliary equations should be added.
            This flag is ignored for CycleCloser.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index (increased by 2).
        equations : list or dict
            Updated structure with equation labels.
        """
        # Cost equality equations of the physical exergy:
        for label in ["M", "T"] if split_physical_exergy else ["PH"]:
            A[counter, self.inl[0]["CostVar_index"][label]] = (
                (1 / self.inl[0][f"e_{label}"]) if self.inl[0][f"e_{label}"] != 0 else 1
            )
            A[counter, self.outl[0]["CostVar_index"][label]] = (
                (-1 / self.outl[0][f"e_{label}"]) if self.outl[0][f"e_{label}"] != 0 else -1
            )
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": f"c_{label}",
            }
            b[counter] = 0
            counter += 1

        if chemical_exergy_enabled:
            # Chemical cost equality equation:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = (
                (1 / self.inl[0]["e_CH"]) if self.inl[0]["e_CH"] != 0 else 1
            )
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = (
                (-1 / self.outl[0]["e_CH"]) if self.outl[0]["e_CH"] != 0 else -1
            )
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            b[counter] = 0

            counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True) -> None:
        """
        Exergoeconomic balance for the CycleCloser is not defined.

        This component does not generate or consume exergy, so all cost terms are undefined.

        Parameters
        ----------
        T0 : float
            Ambient temperature (unused).
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """
        self.C_F = np.nan
        self.C_P = np.nan
        self.C_D = np.nan
        self.c_TOT = np.nan
        self.C_TOT = np.nan
        self.r = np.nan
        self.f = np.nan
