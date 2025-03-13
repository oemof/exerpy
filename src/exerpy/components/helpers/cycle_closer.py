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

    
    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the CycleCloser.
        
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
        # Mechanical cost equality equation:
        A[counter, self.inl[0]["CostVar_index"]["M"]] = (1 / self.inl[0]["e_M"]) if self.inl[0]["e_M"] != 0 else 1
        A[counter, self.outl[0]["CostVar_index"]["M"]] = (-1 / self.outl[0]["e_M"]) if self.outl[0]["e_M"] != 0 else -1
        equations[counter] = f"aux_cyclecloser_mech"
        b[counter] = 0

        # Thermal cost equality equation:
        A[counter+1, self.inl[0]["CostVar_index"]["T"]] = (1 / self.inl[0]["e_T"]) if self.inl[0]["e_T"] != 0 else 1
        A[counter+1, self.outl[0]["CostVar_index"]["T"]] = (-1 / self.outl[0]["e_T"]) if self.outl[0]["e_T"] != 0 else -1
        equations[counter+1] = f"aux_cyclecloser_thermal"
        b[counter+1] = 0

        counter += 2
        return A, b, counter, equations
    
    def exergoeconomic_balance(self, T0):
        self.C_P = np.nan
        self.C_F = np.nan   
        self.c_F = np.nan 
        self.c_P = np.nan 
        self.C_D = np.nan 
        self.r = np.nan 
        self.f = np.nan 