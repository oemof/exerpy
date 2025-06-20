import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class CombustionChamber(Component):
    r"""
    Class for exergy and exergoeconomic analysis of combustion chambers.

    This class performs exergy and exergoeconomic analysis calculations for combustion chambers,
    considering both thermal and mechanical exergy flows, as well as chemical exergy flows.
    The exergy product is defined based on thermal and mechanical exergy differences,
    while the exergy fuel is based on chemical exergy differences.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.
        Optional parameter 'Z_costs' (float): Investment cost rate of the component in currency/h.

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
    inl : dict
        Dictionary containing inlet stream data with mass flows and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with mass flows and specific exergies.
    Z_costs : float
        Investment cost rate of the component in currency/h.

    Notes
    -----
    The exergy analysis considers the following definitions:

    .. math::
        \dot{E}_\mathrm{P} &= \sum_{out} \dot{m}_{out} \cdot e^\mathrm{T}_{out}
        + \sum_{out} \dot{m}_{out} \cdot e^\mathrm{M}_{out}
        - \sum_{in} \dot{m}_{in} \cdot e^\mathrm{T}_{in}
        - \sum_{in} \dot{m}_{in} \cdot e^\mathrm{M}_{in}

    .. math::
        \dot{E}_\mathrm{F} &= \sum_{in} \dot{m}_{in} \cdot e^\mathrm{CH}_{in}
        - \sum_{out} \dot{m}_{out} \cdot e^\mathrm{CH}_{out}

    The exergetic efficiency is calculated as:

    .. math::
        \varepsilon = \frac{\dot{E}_\mathrm{P}}{\dot{E}_\mathrm{F}}

    The exergy destruction follows from the exergy balance:

    .. math::
        \dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}
    """

    def __init__(self, **kwargs):
        r"""Initialize combustion chamber component with given parameters."""
        super().__init__(**kwargs)
        # Initialize additional attributes if necessary
        self.Ex_C_col = kwargs.get('Ex_C_col', {})
        self.Z_costs = kwargs.get('Z_costs', 0.0)  # Cost rate in currency/h

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the combustion chamber.

        Performs exergy balance calculations considering both physical and chemical
        exergy flows. The exergy product is based on physical exergy differences,
        while the exergy fuel is based on chemical exergy differences.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined.
        """
        # Check for necessary inlet and outlet data
        if not hasattr(self, 'inl') or not hasattr(self, 'outl') or len(self.inl) < 2 or len(self.outl) < 1:
            msg = "CombustionChamber requires at least two inlets (air and fuel) and one outlet (exhaust)."
            logging.error(msg)
            raise ValueError(msg)

        # Calculate total physical exergy of outlets
        total_E_P_out = sum(outlet['m'] * outlet['e_PH'] for outlet in self.outl.values())

        # Calculate total physical exergy of inlets
        total_E_P_in = sum(inlet['m'] * inlet['e_PH'] for inlet in self.inl.values())

        # Exergy Product (E_P)
        self.E_P = total_E_P_out - total_E_P_in

        # Calculate total chemical exergy of inlets
        total_E_F_in = sum(inlet['m'] * inlet['e_CH'] for inlet in self.inl.values())

        # Calculate total chemical exergy of outlets
        total_E_F_out = sum(outlet['m'] * outlet['e_CH'] for outlet in self.outl.values())

        # Exergy Fuel (E_F)
        self.E_F = total_E_F_in - total_E_F_out

        # Exergy destruction (difference between exergy fuel and exergy product)
        self.E_D = self.E_F - self.E_P

        # Exergetic efficiency (epsilon)
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"CombustionChamber exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the combustion chamber.
        
        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:
        
        (1) For mechanical exergy:
            - When all streams have non-zero mechanical exergy:
              c_M(outlet)/E_M(outlet) = weighted average of inlet specific mechanical exergy costs
            - When pressure can only decrease: c_M(outlet) is directly set
            
        (2) For chemical exergy:
            - When all streams have non-zero chemical exergy:
              c_CH(outlet)/E_CH(outlet) = weighted average of inlet specific chemical exergy costs
            - When an inlet has zero chemical exergy: its specific cost is directly set
        
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
        equations : dict or list
            Data structure for storing equation labels.
        chemical_exergy_enabled : bool
            Flag indicating whether chemical exergy is enabled.
        
        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index (counter + 2).
        equations : dict or list
            Updated structure with equation labels.
            
        Raises
        ------
        ValueError
            If chemical exergy is not enabled, which is mandatory for combustion chambers.
        """
        # For the combustion chamber, chemical exergy is mandatory.
        if not chemical_exergy_enabled:
            raise ValueError("Chemical exergy is mandatory for the combustion chamber!",
                             "Please make sure that your exergy analysis consider the chemical exergy.")

        # Convert inlet and outlet dictionaries to lists for ordered access.
        inlets = list(self.inl.values())
        outlets = list(self.outl.values())

        # --- Mechanical cost auxiliary equation ---
        if (outlets[0]["e_M"] != 0 and inlets[0]["e_M"] != 0 and inlets[1]["e_M"] != 0):
            A[counter, outlets[0]["CostVar_index"]["M"]] = -1 / outlets[0]["E_M"]
            A[counter, inlets[0]["CostVar_index"]["M"]] = (1 / inlets[0]["E_M"]) * inlets[0]["m"] / (inlets[0]["m"] + inlets[1]["m"])
            A[counter, inlets[1]["CostVar_index"]["M"]] = (1 / inlets[1]["E_M"]) * inlets[1]["m"] / (inlets[0]["m"] + inlets[1]["m"])
        else:  # pressure can only decrease in the combustion chamber (case with p_inlet = p0 and p_outlet < p0 NOT considered)
            A[counter, outlets[0]["CostVar_index"]["M"]] = 1
        equations[counter] = f"aux_mixing_mech_{self.outl[0]['name']}"

        # --- Chemical cost auxiliary equation ---
        if (outlets[0]["e_CH"] != 0 and inlets[0]["e_CH"] != 0 and inlets[1]["e_CH"] != 0):
            A[counter+1, outlets[0]["CostVar_index"]["CH"]] = -1 / outlets[0]["E_CH"]
            A[counter+1, inlets[0]["CostVar_index"]["CH"]] = (1 / inlets[0]["E_CH"]) * inlets[0]["m"] / (inlets[0]["m"] + inlets[1]["m"])
            A[counter+1, inlets[1]["CostVar_index"]["CH"]] = (1 / inlets[1]["E_CH"]) * inlets[1]["m"] / (inlets[0]["m"] + inlets[1]["m"])
        elif inlets[0]["e_CH"] == 0:
            A[counter+1, inlets[0]["CostVar_index"]["CH"]] = 1
        elif inlets[1]["e_CH"] == 0:
            A[counter+1, inlets[1]["CostVar_index"]["CH"]] = 1
        equations[counter+1] = f"aux_mixing_chem_{self.outl[0]['name']}"

        # Set the right-hand side entries to zero.
        b[counter]   = 0
        b[counter+1] = 0

        return [A, b, counter + 2, equations]

    def exergoeconomic_balance(self, T0):
        """
        Perform exergoeconomic balance calculations for the combustion chamber.
        
        This method calculates various exergoeconomic parameters including:
        - Cost rates of product (C_P) and fuel (C_F)
        - Specific cost of product (c_P) and fuel (c_F)
        - Cost rate of exergy destruction (C_D)
        - Relative cost difference (r)
        - Exergoeconomic factor (f)
        
        Parameters
        ----------
        T0 : float
            Ambient temperature
            
        Notes
        -----
        The exergoeconomic balance considers thermal (T), chemical (CH),
        and mechanical (M) exergy components for the inlet and outlet streams.
        """
        self.C_P = self.outl[0]["C_T"] - (
                self.inl[0]["C_T"] + self.inl[1]["C_T"]
        )
        self.C_F = (
                self.inl[0]["C_CH"] + self.inl[1]["C_CH"] -
                self.outl[0]["C_CH"] + self.inl[0]["C_M"] +
                self.inl[1]["C_M"] - self.outl[0]["C_M"]
        )
        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)