import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Deaerator(Component):
    r"""
    Class for exergy analysis of deaerators.

    This class performs exergy analysis calculations for deaerators with multiple 
    inlet streams and one outlet stream. The exergy product and fuel definitions 
    vary based on the temperature relationships between inlet streams, outlet 
    stream, and ambient conditions.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\text{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\mathrm{P}` in :math:`\text{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\text{W}`.
    epsilon : float
        Exergetic efficiency of the component :math:`\varepsilon` in :math:`-`.
    inl : dict
        Dictionary containing inlet streams data with temperature, mass flows,
        and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        and specific exergies.

    Notes
    -----
    The exergy analysis accounts for physical exergy only. The equations for exergy
    product and fuel are defined based on temperature relationships:

    .. math::

        \dot{E}_\mathrm{P} =
        \begin{cases}
        \begin{cases}
        \sum_i \dot{m}_i \cdot (e_\mathrm{out}^\mathrm{PH} -
        e_{\mathrm{in,}i}^\mathrm{PH})
        & T_{\mathrm{in,}i} < T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} \geq T_0 \\
        \sum_i \dot{m}_i \cdot e_\mathrm{out}^\mathrm{PH}
        & T_{\mathrm{in,}i} < T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} < T_0 \\
        \end{cases} & T_\mathrm{out} > T_0\\
        \text{not defined (nan)} & T_\mathrm{out} = T_0\\
        \begin{cases}
        \sum_i \dot{m}_i \cdot e_\mathrm{out}^\mathrm{PH}
        & T_{\mathrm{in,}i} > T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} \geq T_0 \\
        \sum_i \dot{m}_i \cdot (e_\mathrm{out}^\mathrm{PH} -
        e_{\mathrm{in,}i}^\mathrm{PH})
        & T_{\mathrm{in,}i} > T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} < T_0 \\
        \end{cases} & T_\mathrm{out} < T_0\\
        \end{cases}

        \dot{E}_\mathrm{F} =
        \begin{cases}
        \begin{cases}
        \sum_i \dot{m}_i \cdot (e_{\mathrm{in,}i}^\mathrm{PH} -
        e_\mathrm{out}^\mathrm{PH})
        & T_{\mathrm{in,}i} > T_\mathrm{out} \\
        \sum_i \dot{m}_i \cdot e_{\mathrm{in,}i}^\mathrm{PH}
        & T_{\mathrm{in,}i} < T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} < T_0 \\
        \end{cases} & T_\mathrm{out} > T_0\\
        \sum_i \dot{m}_i \cdot e_{\mathrm{in,}i}^\mathrm{PH}
        & T_\mathrm{out} = T_0\\
        \begin{cases}
        \sum_i \dot{m}_i \cdot e_{\mathrm{in,}i}^\mathrm{PH}
        & T_{\mathrm{in,}i} > T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} \geq T_0 \\
        \sum_i \dot{m}_i \cdot (e_{\mathrm{in,}i}^\mathrm{PH} -
        e_\mathrm{out}^\mathrm{PH})
        & T_{\mathrm{in,}i} < T_\mathrm{out} \\
        \end{cases} & T_\mathrm{out} < T_0\\
        \end{cases}

        \forall i \in \text{deaerator inlets}
    """

    def __init__(self, **kwargs):
        r"""Initialize deaerator component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the deaerator.

        Performs exergy balance calculations considering the temperature relationships
        between inlet streams, outlet stream, and ambient conditions.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined.
        """      
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Deaerator requires at least two inlets and one outlet.")

        self.E_P = 0
        self.E_F = 0

        # Case 1: Outlet temperature is greater than T0
        if self.outl[0]['T'] > T0:
            for _, inlet in self.inl.items():
                if inlet['T'] < self.outl[0]['T']:  # Tin < Tout
                    if inlet['T'] >= T0:  # and Tin >= T0
                        self.E_P += inlet['m'] * (self.outl[0]['e_PH'] - inlet['e_PH'])
                    else:  # and Tin < T0
                        self.E_P += inlet['m'] * self.outl[0]['e_PH']
                        self.E_F += inlet['m'] * inlet['e_PH']
                else:  # Tin > Tout
                    self.E_F += inlet['m'] * (inlet['e_PH'] - self.outl[0]['e_PH'])

        # Case 2: Outlet temperature is equal to T0
        elif self.outl[0]['T'] == T0:
            self.E_P = np.nan
            for _, inlet in self.inl.items():
                self.E_F += inlet['m'] * inlet['e_PH']

        # Case 3: Outlet temperature is less than T0
        else:
            for _, inlet in self.inl.items():
                if inlet['T'] > self.outl[0]['T']:  # Tin > Tout
                    if inlet['T'] >= T0:  # and Tin >= T0
                        self.E_P += inlet['m'] * self.outl[0]['e_PH']
                        self.E_F += inlet['m'] * inlet['e_PH']
                    else:  # and Tin < T0
                        self.E_P += inlet['m'] * (self.outl[0]['e_PH'] - inlet['e_PH'])
                else:  # Tin < Tout
                    self.E_F += inlet['m'] * (inlet['e_PH'] - self.outl[0]['e_PH'])

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Deaerator exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

        # Log the results
        logging.info(
            f"Deaerator exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the deaerator.

        This function adds auxiliary rows to the cost matrix A and the right-hand side vector b 
        to enforce cost relations for the chemical and mechanical cost components.
        
        For the chemical cost equation:
        - If chemical exergy is enabled and the outlet (self.outl[0]) has nonzero chemical exergy (e_CH),
            then for each inlet the coefficient is set proportionally to its mass fraction and the inverse of its e_CH.
        - If the outlet's chemical exergy is zero, or if chemical exergy is not enabled,
            a fallback coefficient of 1 is assigned.
        
        For the mechanical cost equation:
        - The coefficients are set based on the outlet’s mechanical exergy (e_M) and the inlet mass fractions.
        
        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature (provided for consistency; not used in this function).
        equations : list or dict
            Data structure for storing equation labels.
        chemical_exergy_enabled : bool
            Flag indicating whether chemical exergy auxiliary equations should be added.

        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index (increased by 2 if chemical exergy is enabled, or by 1 otherwise).
        equations : list or dict
            Updated structure with equation labels.
        """
        # --- Chemical cost auxiliary equation (conditionally added) ---
        if chemical_exergy_enabled:
            if self.outl[0]["e_CH"] != 0:
                A[counter, self.outl[0]["CostVar_index"]["CH"]] = -1 / self.outl[0]["E_CH"]
                # Iterate over inlet streams for chemical mixing.
                for inlet in self.inl.values():
                    if inlet["e_CH"] != 0:
                        A[counter, inlet["CostVar_index"]["CH"]] = inlet["m"] / (self.outl[0]["m"] * inlet["E_CH"])
                    else:
                        A[counter, inlet["CostVar_index"]["CH"]] = 1
            else:
                # Outlet chemical exergy is zero: assign fallback for all inlets.
                for inlet in self.inl.values():
                    A[counter, inlet["CostVar_index"]["CH"]] = 1
            equations[counter] = f"aux_mixing_chem_{self.outl[0]['name']}"
            chem_row = 1  # One row added for chemical equation.
        else:
            chem_row = 0  # No row added.

        # --- Mechanical cost auxiliary equation ---
        mech_row = 0  # This row will always be added.
        if self.outl[0]["e_M"] != 0:
            A[counter + chem_row, self.outl[0]["CostVar_index"]["M"]] = -1 / self.outl[0]["E_M"]
            # Iterate over inlet streams for mechanical mixing.
            for inlet in self.inl.values():
                if inlet["e_M"] != 0:
                    A[counter + chem_row, inlet["CostVar_index"]["M"]] = inlet["m"] / (self.outl[0]["m"] * inlet["E_M"])
                else:
                    A[counter + chem_row, inlet["CostVar_index"]["M"]] = 1
        else:
            for inlet in self.inl.values():
                A[counter + chem_row, inlet["CostVar_index"]["M"]] = 1
        equations[counter + chem_row] = f"aux_mixing_mech_{self.outl[0]['name']}"

        # Set the right-hand side entries to zero for the added rows.
        if chemical_exergy_enabled:
            b[counter] = 0
            b[counter + 1] = 0
            counter += 2  # Two rows were added.
        else:
            b[counter] = 0
            counter += 1  # Only one row was added.

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0):
        self.C_P = 0
        self.C_F = 0
        if self.outl[0]["T"] > T0:
            for i in self.inl:
                if i["T"] < self.outl[0]["T"]:
                    # cold inlets
                    self.C_F += i["C_M"] + i["C_CH"]
                else:
                    # hot inlets
                    self.C_F += - i["M"] * i["C_T"] * i["e_T"] + (
                        i["C_T"] + i["C_M"] + i["C_CH"])
            self.C_F += (-self.outl[0]["C_M"] - self.outl[0]["C_CH"])
        elif self.outl[0]["T"] - 1e-6 < T0 and self.outl[0]["T"] + 1e-6 > T0:
            # dissipative
            for i in self.inl:
                self.C_F += i["C_TOT"]
        else:
            for i in self.inl:
                if i["T"] > self.outl[0]["T"]:
                    # hot inlets
                    self.C_F += i["C_M"] + i["C_CH"]
                else:
                    # cold inlets
                    self.C_F += - i["M"] * i["C_T"] * i["e_T"] + (
                        i["C_T"] + i["C_M"] + i["C_CH"])
            self.C_F += (-self.outl[0]["C_M"] - self.outl[0]["C_CH"])
        self.C_P = self.C_F + self.Z_costs      # +1/num_serving_comps * C_diff
        # ToDo: add case that merge profits from dissipative component(s)


        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)