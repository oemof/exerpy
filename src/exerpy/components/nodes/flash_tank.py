import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class FlashTank(Component):
    r"""
    Class for exergy and exergoeconomic analysis of flash tank.

    This class performs exergy and exergoeconomic analysis calculations for flash tank components,
    accounting for two inlet and two outlet streams.

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
        Initialize the flash tank component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate in currency/h, default 0.0
        """
        self.dissipative = False
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the flash tank.

        Parameters
        ----------
        T0 : float
            Ambient temperature in Kelvin.
        p0 : float
            Ambient pressure in Pascal.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Raises
        ------
        ValueError
            If the number of inlet or outlet streams is less than two.

        Notes
        -----
        The definition of exergy fuel and product for this component has not been validated yet. For now, the 
        exergy fuel is defined as the sum of the inlet streams' exergies, and the exergy product is defined as the
        sum of the outlet streams' exergies. The exergy destruction is calculated as the difference between the exergy fuel and product. 
        .. math::

            \dot{E}_\mathrm{F} = \sum_{i=1}^{n} \dot{E}_i^\mathrm{PH}

        .. math::

            \dot{E}_\mathrm{P} = \sum_{j=1}^{m} \dot{E}_j^\mathrm{PH}

        """
        # Ensure that the component has at least two outlets and one inlet.
        if len(self.inl) < 1 or len(self.outl) < 2:
            raise ValueError("Flash tank requires at least one inlet and two outlets.")
        
        if split_physical_exergy:
            exergy_type = 'e_T'
        else:
            exergy_type = 'e_PH'

        # Calculate exergy fuel (E_F) from inlet streams.
        self.E_F = sum(inlet['m'] * inlet[exergy_type] for inlet in self.inl.values())
        # Calculate exergy product (E_P) from outlet streams.
        self.E_P = sum(outlet['m'] * outlet[exergy_type] for outlet in self.outl.values())

        # Exergy destruction and efficiency.
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results.
        logging.info(
            f"FlashTank exergy balance calculated: "
            f"E_F = {self.E_F:.2f} W, E_P = {self.E_P:.2f} W, E_D = {self.E_D:.2f} W, "
            f"Efficiency = {self.epsilon:.2%}"
        )
