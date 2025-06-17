import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Drum(Component):
    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate exergy balance of a merge.

        Parameters
        ----------
        T0 : float
            Ambient temperature T0 / K.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Note
        ----
        Please note, that the exergy balance accounts for physical exergy only.

        .. math::

            \dot{E}_\mathrm{P} = \sum \dot{E}_{\mathrm{out,}j}^\mathrm{PH}\\
            \dot{E}_\mathrm{F} = \sum \dot{E}_{\mathrm{in,}i}^\mathrm{PH}
        """
        self.E_P = (
            self.outl[0]['e_PH'] * self.outl[0]['m']
            + self.outl[1]['e_PH'] * self.outl[1]['m']
        )
        self.E_F = (
            self.inl[0]['e_PH'] * self.inl[0]['m']
            + self.inl[1]['e_PH'] * self.inl[1]['m']
        )

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Drum exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the drum.
        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:
        (1-2) Chemical exergy cost equations (if enabled)
            - F-principle: specific chemical exergy costs equalized between inlet and both outlets
            - First equation balances inlet with outlet 0
            - Second equation balances inlet with outlet 1
        (3) Thermal exergy cost equation
            - P-principle: specific thermal exergy costs are equalized between both outlets
        (4) Mechanical exergy cost equation
            - P-principle: specific mechanical exergy costs are equalized between both outlets
        (5) Thermal-Mechanical coupling for outlet 0
            - P-principle: thermal and mechanical specific costs must be equal at outlet 0
        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature.
        equations : dict
            Dictionary for storing equation labels.
        chemical_exergy_enabled : bool
            Flag indicating whether chemical exergy auxiliary equations should be added.
        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index.
        equations : dict
            Updated dictionary with equation labels.
        """

        # --- Chemical cost auxiliary equations ---
        if chemical_exergy_enabled:
            # Equation 1: Balance between inlet 0 and outlet 0 for chemical exergy
            if self.inl[0]["e_CH"] != 0:
                A[counter, self.inl[0]["CostVar_index"]["CH"]] = 1 / self.inl[0]["E_CH"]
            else:
                A[counter, self.inl[0]["CostVar_index"]["CH"]] = 1
            if self.outl[0]["e_CH"] != 0:
                A[counter, self.outl[0]["CostVar_index"]["CH"]] = -1 / self.outl[0]["E_CH"]
            else:
                A[counter, self.outl[0]["CostVar_index"]["CH"]] = -1
            equations[counter] = f"aux_drum_chem1_{self.outl[0]['name']}"
            
            # Equation 2: Balance between inlet 0 and outlet 1 for chemical exergy
            if self.inl[0]["e_CH"] != 0:
                A[counter+1, self.inl[0]["CostVar_index"]["CH"]] = 1 / self.inl[0]["E_CH"]
            else:
                A[counter+1, self.inl[0]["CostVar_index"]["CH"]] = 1
            if self.outl[1]["e_CH"] != 0:
                A[counter+1, self.outl[1]["CostVar_index"]["CH"]] = -1 / self.outl[1]["E_CH"]
            else:
                A[counter+1, self.outl[1]["CostVar_index"]["CH"]] = -1
            equations[counter+1] = f"aux_drum_chem2_{self.outl[1]['name']}"
            chem_rows = 2
        else:
            chem_rows = 0

        # --- Thermal cost auxiliary equation ---
        # For thermal exergy, we balance the two outlets.
        if (self.outl[0]["e_T"] != 0) and (self.outl[1]["e_T"] != 0):
            A[counter+chem_rows, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["E_T"]
            A[counter+chem_rows, self.outl[1]["CostVar_index"]["T"]] = -1 / self.outl[1]["E_T"]
        elif self.outl[0]["e_T"] == 0 and self.outl[1]["e_T"] != 0:
            A[counter+chem_rows, self.outl[0]["CostVar_index"]["T"]] = 1
        elif self.outl[0]["e_T"] != 0 and self.outl[1]["e_T"] == 0:
            A[counter+chem_rows, self.outl[1]["CostVar_index"]["T"]] = -1
        else:
            A[counter+chem_rows, self.outl[0]["CostVar_index"]["T"]] = 1
            A[counter+chem_rows, self.outl[1]["CostVar_index"]["T"]] = -1
        equations[counter+chem_rows] = f"aux_drum_therm_{self.outl[0]['name']}_{self.outl[1]['name']}"

        # --- Mechanical cost auxiliary equation ---
        if self.outl[0]["e_M"] != 0:
            A[counter+chem_rows+1, self.outl[0]["CostVar_index"]["M"]] = 1 / self.outl[0]["E_M"]
        else:
            A[counter+chem_rows+1, self.outl[0]["CostVar_index"]["M"]] = 1
        if self.outl[1]["e_M"] != 0:
            A[counter+chem_rows+1, self.outl[1]["CostVar_index"]["M"]] = -1 / self.outl[1]["E_M"]
        else:
            A[counter+chem_rows+1, self.outl[1]["CostVar_index"]["M"]] = -1
        equations[counter+chem_rows+1] = f"aux_drum_mech_{self.outl[0]['name']}_{self.outl[1]['name']}"

        # --- Thermal-Mechanical coupling equation for outlet 0 ---
        # This enforces that the thermal and mechanical cost components at outlet 0 are consistent.
        if (self.outl[0]["e_T"] != 0) and (self.outl[0]["e_M"] != 0):
            A[counter+chem_rows+2, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["E_T"]
            A[counter+chem_rows+2, self.outl[0]["CostVar_index"]["M"]] = -1 / self.outl[0]["E_M"]
        elif (self.outl[0]["e_T"] == 0) and (self.outl[0]["e_M"] == 0):
            A[counter+chem_rows+2, self.outl[0]["CostVar_index"]["T"]] = 1
            A[counter+chem_rows+2, self.outl[0]["CostVar_index"]["M"]] = -1
        elif self.outl[0]["e_T"] == 0:
            A[counter+chem_rows+2, self.outl[0]["CostVar_index"]["T"]] = 1
        else:
            A[counter+chem_rows+2, self.outl[0]["CostVar_index"]["M"]] = -1
        equations[counter+chem_rows+2] = f"aux_drum_therm_mech_{self.outl[0]['name']}"

        # Set the right-hand side entries to zero for all added rows.
        for i in range(chem_rows + 3):
            b[counter + i] = 0

        return A, b, counter + chem_rows + 3, equations
