import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class CombustionChamber(Component):
    r"""
    Class for exergy analysis of combustion chambers.

    This class performs exergy analysis calculations for combustion chambers,
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
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\text{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\mathrm{P}` in :math:`\text{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\text{W}`.
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
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.

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