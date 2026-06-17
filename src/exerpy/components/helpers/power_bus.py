import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class PowerBus(Component):
    r"""
    Component for power busses. This component is not considered in exergy analysis, but it is used in exergoeconomic analysis.
    """

    def __init__(self, **kwargs):
        r"""Initialize CycleCloser component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        The PowerBus component does not have an exergy balance calculation.
        """
        self.E_D = np.nan
        self.E_F = np.nan
        self.E_P = np.nan
        self.E_L = np.nan
        self.epsilon = np.nan

        # Log the results
        logger.info(f"The exergy balance of a PowerBus {self.name} is skipped.")

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
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

        # Splitter case
        if len(self.inl) >= 1 and len(self.outl) <= 1:
            logger.info(f"PowerBus {self.name} has only one output, no auxiliary equations added.")

        # Mixer case
        elif len(self.inl) == 1 and len(self.outl) > 1:
            logger.info(f"PowerBus {self.name} has multiple outputs, auxiliary equations will be added.")
            for out in list(self.outl.values())[:]:
                A[counter, self.inl[0]["CostVar_index"]["exergy"]] = (
                    (1 / self.inl[0]["E"]) if self.inl[0]["E"] != 0 else 1
                )
                A[counter, out["CostVar_index"]["exergy"]] = (-1 / out["E"]) if out["E"] != 0 else -1
                equations[counter] = {
                    "kind": "aux_power_eq",
                    "objects": [self.name, self.inl[0]["name"], out["name"]],
                    "property": "c_TOT",
                }
                b[counter] = 0
                counter += 1

        # General case with multiple inputs and outputs
        elif len(self.inl) > 1 and len(self.outl) > 1:
            logger.info(
                f"PowerBus {self.name} has multiple inputs and outputs, "
                f"adding cost balance and outlet equality equations."
            )

            # Cost balance equation: sum(C_in) - sum(C_out) = 0  (Z = 0 for PowerBus)
            for inl in self.inl.values():
                A[counter, inl["CostVar_index"]["exergy"]] = 1
            for out in self.outl.values():
                A[counter, out["CostVar_index"]["exergy"]] = -1
            equations[counter] = {
                "kind": "cost_balance",
                "objects": [self.name],
                "property": "c_TOT",
            }
            b[counter] = 0
            counter += 1

            # Equalize specific costs of all outlets: c_ref = c_out_i
            outlet_list = list(self.outl.values())
            ref_out = outlet_list[0]
            for out in outlet_list[1:]:
                A[counter, ref_out["CostVar_index"]["exergy"]] = (1 / ref_out["E"]) if ref_out["E"] != 0 else 1
                A[counter, out["CostVar_index"]["exergy"]] = (-1 / out["E"]) if out["E"] != 0 else -1
                equations[counter] = {
                    "kind": "aux_power_eq",
                    "objects": [self.name, ref_out["name"], out["name"]],
                    "property": "c_TOT",
                }
                b[counter] = 0
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False) -> None:
        """
        Exergoeconomic balance for the PowerBus is not defined.

        This component does not convert or destroy exergy, so all cost terms are undefined.

        Parameters
        ----------
        T0 : float
            Ambient temperature (unused).
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        """
        self.C_F = np.nan
        self.C_P = np.nan
        self.C_D = np.nan
        self.c_TOT = np.nan
        self.C_TOT = np.nan
        self.r = np.nan
        self.f = np.nan
