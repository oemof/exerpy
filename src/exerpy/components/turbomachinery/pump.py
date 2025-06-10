import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Pump(Component):
    r"""
    Class for exergy analysis of pumps.

    This class performs exergy analysis calculations for pumps, with definitions
    of exergy product and fuel varying based on the temperature relationships between
    inlet stream, outlet stream, and ambient conditions.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\mathrm{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\mathrm{P}` in :math:`\mathrm{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\mathrm{W}`.
    epsilon : float
        Exergetic efficiency of the component :math:`\varepsilon` in :math:`-`.
    P : float
        Power input to the pump in :math:`\mathrm{W}`.
    inl : dict
        Dictionary containing inlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.

    Notes
    -----
    The exergy analysis considers three cases based on temperature relationships:

    Case 1 - **Both temperatures above ambient** (:math:`T_\mathrm{in}, T_\mathrm{out} > T_0`):

    .. math::

        \dot{E}_\mathrm{P} &= \dot{m} \cdot (e_\mathrm{out}^\mathrm{PH} -
        e_\mathrm{in}^\mathrm{PH})\\
        \dot{E}_\mathrm{F} &= |\dot{W}|

    Case 2 - **Inlet below, outlet above ambient** (:math:`T_\mathrm{in} < T_0 < T_\mathrm{out}`):

    .. math::

        \dot{E}_\mathrm{P} &= |\dot{W}| + (e_\mathrm{out}^\mathrm{PH} -
        e_\mathrm{in}^\mathrm{M})\\
        \dot{E}_\mathrm{F} &= e_\mathrm{in}^\mathrm{M} + e_\mathrm{in}^\mathrm{PH}

    Case 3 - **Both temperatures below ambient** (:math:`T_\mathrm{in}, T_\mathrm{out} \leq T_0`):

    .. math::

        \dot{E}_\mathrm{P} &= e_\mathrm{out}^\mathrm{M} - e_\mathrm{in}^\mathrm{M}\\
        \dot{E}_\mathrm{F} &= e_\mathrm{in}^\mathrm{PH} - e_\mathrm{out}^\mathrm{PH}

    For all valid cases, the exergy destruction is:

    .. math::

        \dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}

    where:
        - :math:`\dot{W}`: Power input
        - :math:`e^\mathrm{PH}`: Physical exergy
        - :math:`e^\mathrm{M}`: Mechanical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize pump component with given parameters."""
        super().__init__(**kwargs)
        self.P = None

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the pump.

        Performs exergy balance calculations considering the temperature relationships
        between inlet stream, outlet stream, and ambient conditions.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        """
        # Get power flow if not already available
        if self.P is None:
            self.P = self.outl[0]['m'] * (self.outl[0]['h'] - self.inl[0]['h'])

        # First, check for the invalid case: outlet temperature smaller than inlet temperature.
        if self.inl[0]['T'] > self.outl[0]['T']:
            logging.warning(
                f"Exergy balance of compressor '{self.name}' where outlet temperature ({self.outl[0]['T']}) "
                f"is smaller than inlet temperature ({self.inl[0]['T']}) is not implemented."
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Case 1: Both temperatures above ambient
        elif round(self.inl[0]['T'], 5) >= T0 and round(self.outl[0]['T'], 5) > T0:
            self.E_P = self.outl[0]['m'] * (self.outl[0]['e_PH'] - self.inl[0]['e_PH'])
            self.E_F = abs(self.P)

        # Case 2: Inlet below, outlet above ambient
        elif round(self.inl[0]['T'], 5) < T0 and round(self.outl[0]['T'], 5) > T0:
            if split_physical_exergy:
                self.E_P = (self.outl[0]['m'] * self.outl[0]['e_T'] +
                            self.outl[0]['m'] * (self.outl[0]['e_M'] - self.inl[0]['e_M']))
                self.E_F = abs(self.P) + self.inl[0]['m'] * self.inl[0]['e_T']
            else:
                logging.warning("While dealing with pump below ambient, "
                                "physical exergy should be split into thermal and mechanical components!")
                self.E_P = self.outl[0]['m'] * (self.outl[0]['e_PH'] - self.inl[0]['e_PH'])
                self.E_F = abs(self.P)

        # Case 3: Both temperatures below ambient
        elif round(self.inl[0]['T'], 5) < T0 and round(self.outl[0]['T'], 5) <= T0:
            if split_physical_exergy:
                self.E_P = self.outl[0]['m'] * (self.outl[0]['e_M'] - self.inl[0]['e_M'])
                self.E_F = abs(self.P) + self.inl[0]['m'] * (self.inl[0]['e_T'] -
                                                            self.outl[0]['e_T'])
            else:
                logging.warning("While dealing with pump below ambient, "
                                "physical exergy should be split into thermal and mechanical components!")
                self.E_P = self.outl[0]['m'] * (self.outl[0]['e_PH'] - self.inl[0]['e_PH'])
                self.E_F = abs(self.P)

        # Invalid case: outlet temperature smaller than inlet
        else:
            logging.warning(
                'Exergy balance of a pump where outlet temperature is smaller '
                'than inlet temperature is not implemented.'
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Pump exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the pump.
        
        This function sets up auxiliary equations that enforce:
        (i) equality of chemical cost between the inlet and outlet (c_in_CH = c_out_CH), and
        (ii) a relationship between the thermal and mechanical cost differences.
        
        The pump uses a p‐rule (if both inlet and outlet temperatures exceed T0)
        or an f‐rule (if not) to relate the inlet and outlet thermal and mechanical cost
        coefficients. These coefficients are computed using the differences in thermal 
        (dET = e_T,out − e_T,in) and mechanical (dEM = e_M,out − e_M,in) exergy.
        
        If chemical exergy is enabled (chemical_exergy_enabled is True), one row is added 
        for chemical cost equality and one row for the combined thermal/mechanical relation.
        Otherwise, only the thermal/mechanical equation is added.
        
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
        # --- Chemical equality equation (row added only if enabled) ---
        if chemical_exergy_enabled:
            # Set the chemical cost equality:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = (1 / self.inl[0]["E_CH"]) if self.inl[0]["e_CH"] != 0 else 1
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = (-1 / self.outl[0]["E_CH"]) if self.outl[0]["e_CH"] != 0 else 1
            equations[counter] = f"aux_equality_chem_{self.outl[0]['name']}"
            chem_row = 1
        else:
            chem_row = 0

        # --- Thermal/Mechanical cost equation ---
        # Compute differences in thermal and mechanical exergy:
        dET = self.outl[0]["E_T"] - self.inl[0]["E_T"]
        dEM = self.outl[0]["E_M"] - self.inl[0]["E_M"]
        
        # The row for the thermal/mechanical equation:
        row_index = counter + chem_row
        if self.inl[0]["T"] > T0 and self.outl[0]["T"] > T0:
            if dET != 0 and dEM != 0:
                A[row_index, self.inl[0]["CostVar_index"]["T"]] = -1 / dET
                A[row_index, self.outl[0]["CostVar_index"]["T"]] = 1 / dET
                A[row_index, self.inl[0]["CostVar_index"]["M"]] = 1 / dEM
                A[row_index, self.outl[0]["CostVar_index"]["M"]] = -1 / dEM
                equations[row_index] = f"aux_p_rule_{self.name}"
            else:
                logging.warning("Case where thermal or mechanical exergy difference is zero is not implemented.")
        elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] > T0:
            A[row_index, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["E_T"]
            A[row_index, self.inl[0]["CostVar_index"]["M"]] = 1 / dEM
            A[row_index, self.outl[0]["CostVar_index"]["M"]] = -1 / dEM
            equations[row_index] = f"aux_p_rule_{self.name}"
        else:
            A[row_index, self.inl[0]["CostVar_index"]["T"]] = -1 / self.inl[0]["E_T"]
            A[row_index, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["E_T"]
            equations[row_index] = f"aux_f_rule_{self.name}"
        
        # Set the right-hand side entry for the thermal/mechanical row to zero.
        b[row_index] = 0

        # Update the counter accordingly.
        if chemical_exergy_enabled:
            new_counter = counter + 2
        else:
            new_counter = counter + 1

        return A, b, new_counter, equations

    def exergoeconomic_balance(self, T0):
        # Retrieve the cost of power from the inlet stream of kind "power"
        power_cost = None
        for stream in self.inl.values():
            if stream.get("kind") == "power":
                power_cost = stream.get("C_TOT")
                break
        if power_cost is None:
            logging.error("No inlet power stream found to determine power cost (C_TOT).")
            raise ValueError("No inlet power stream found for exergoeconomic_balance.")

        # Compute product and fuel costs depending on inlet/outlet temperatures relative to T0.
        if self.inl[0]["T"] >= T0 and self.outl[0]["T"] >= T0:
            self.C_P = self.outl[0]["C_PH"] - self.inl[0]["C_PH"]
            self.C_F = power_cost
        elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] > T0:
            self.C_P = self.outl[0]["C_T"] + (self.outl[0]["C_M"] - self.inl[0]["C_M"])
            self.C_F = power_cost + self.inl[0]["C_T"]
        elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] <= T0:
            self.C_P = self.outl[0]["C_M"] - self.inl[0]["C_M"]
            self.C_F = power_cost + (self.inl[0]["C_T"] - self.outl[0]["C_T"])

        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.C_P - self.C_F) / self.C_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
