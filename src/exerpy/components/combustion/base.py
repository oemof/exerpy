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
    C_P : float
        Cost of product stream :math:`\dot{C}_P` in currency/h.
    C_F : float
        Cost of fuel stream :math:`\dot{C}_F` in currency/h.
    C_D : float
        Cost of exergy destruction :math:`\dot{C}_D` in currency/h.
    c_P : float
        Specific cost of product stream (currency per unit exergy).
    c_F : float
        Specific cost of fuel stream (currency per unit exergy).
    r : float
        Relative cost difference, :math:`(c_P - c_F)/c_F`.
    f : float
        Exergoeconomic factor, :math:`\dot{Z}/(\dot{Z} + \dot{C}_D)`.
    Ex_C_col : dict
        Custom cost coefficients collection passed via `kwargs`.
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the combustion chamber component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate (currency/h), default 0.0
        """
        super().__init__(**kwargs)
        # Initialize additional attributes if necessary
        self.Ex_C_col = kwargs.get('Ex_C_col', {})
        self.Z_costs = kwargs.get('Z_costs', 0.0)  # Cost rate in currency/h

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the combustion chamber.

        .. math::
            \dot{E}_P = \dot{E}^{\mathrm{T}}_{\text{out}}
                      + \dot{E}^{\mathrm{M}}_{\text{out}}
                      - \bigl(\dot{E}^{\mathrm{T}}_{\text{in},1}
                              + \dot{E}^{\mathrm{M}}_{\text{in},1}
                              + \dot{E}^{\mathrm{T}}_{\text{in},2}
                              + \dot{E}^{\mathrm{M}}_{\text{in},2}\bigr)

        .. math::
            \dot{E}_F = \dot{E}^{\mathrm{CH}}_{\text{in},1}
                      + \dot{E}^{\mathrm{CH}}_{\text{in},2}
                      - \dot{E}^{\mathrm{CH}}_{\text{out}}

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        p0 : float
            Ambient pressure (Pa).
        split_physical_exergy : bool
            Whether to split thermal and mechanical exergy.

        Raises
        ------
        ValueError
            If fewer than two inlets or no outlets are defined.
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
        r"""
        Add auxiliary cost equations for mixing in the combustion chamber.

        This method appends two rows to the cost matrix to enforce:

        1. Mechanical mixing:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{M}}_{\text{out}}}\,\dot{C}^{\mathrm{M}}_{\text{out}}
            + \frac{\dot m_{1}}{\dot m_{1} + \dot m_{2}}
              \frac{1}{\dot{E}^{\mathrm{M}}_{\text{in},1}}\,\dot{C}^{\mathrm{M}}_{\text{in},1}
            + \frac{\dot m_{2}}{\dot m_{1} + \dot m_{2}}
              \frac{1}{\dot{E}^{\mathrm{M}}_{\text{in},2}}\,\dot{C}^{\mathrm{M}}_{\text{in},2}
            = 0

        2. Chemical mixing:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{CH}}_{\text{out}}}\,\dot{C}^{\mathrm{CH}}_{\text{out}}
            + \frac{\dot m_{1}}{\dot m_{1} + \dot m_{2}}
              \frac{1}{\dot{E}^{\mathrm{CH}}_{\text{in},1}}\,\dot{C}^{\mathrm{CH}}_{\text{in},1}
            + \frac{\dot m_{2}}{\dot m_{1} + \dot m_{2}}
              \frac{1}{\dot{E}^{\mathrm{CH}}_{\text{in},2}}\,\dot{C}^{\mathrm{CH}}_{\text{in},2}
            = 0

        Parameters
        ----------
        A : numpy.ndarray
            Current cost matrix.
        b : numpy.ndarray
            Current RHS vector.
        counter : int
            Starting row index.
        T0 : float
            Ambient temperature.
        equations : dict or list
            Structure for equation labels.
        chemical_exergy_enabled : bool
            Must be True to include chemical exergy mixing.

        Returns
        -------
        A : numpy.ndarray
            Updated cost matrix.
        b : numpy.ndarray
            Updated RHS vector.
        counter : int
            Updated row index.
        equations : dict or list
            Updated labels.

        Raises
        ------
        ValueError
            If chemical_exergy_enabled is False.
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
        r"""
        Perform exergoeconomic cost balance for the combustion chamber.

        This method computes cost coefficients and ratios:

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\text{out}}
                      - \bigl(\dot{C}^{\mathrm{T}}_{\text{in},1}
                              + \dot{C}^{\mathrm{T}}_{\text{in},2}\bigr)

        .. math::
            \dot{C}_F = \dot{C}^{\mathrm{CH}}_{\text{in},1}
                      + \dot{C}^{\mathrm{CH}}_{\text{in},2}
                      - \dot{C}^{\mathrm{CH}}_{\text{out}}
                      + \dot{C}^{\mathrm{M}}_{\text{in},1}
                      + \dot{C}^{\mathrm{M}}_{\text{in},2}
                      - \dot{C}^{\mathrm{M}}_{\text{out}}

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
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