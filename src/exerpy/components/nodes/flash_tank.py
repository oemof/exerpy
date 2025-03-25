import logging
import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class FlashTank(Component):
    r"""
    Class for exergy analysis of flash tanks.

    This class performs exergy analysis calculations for flash tanks where a feed
    stream is partially flashed into two different outlet streams (e.g., vapor and liquid).
    The exergy fuel is calculated using the physical/thermal exergy of the inlet streams,
    while the exergy product is computed as the sum of the physical exergy of the outlet streams.
    Exergy destruction is the difference between the fuel and product, and the efficiency is defined
    as ε = E_P / E_F.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to the parent class.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component (W), computed from the inlet streams.
    E_P : float
        Exergy product of the component (W), computed from the outlet streams.
    E_D : float
        Exergy destruction (W).
    epsilon : float
        Exergetic efficiency, defined as E_P/E_F.
    inl : dict
        Dictionary containing inlet streams data (e.g., temperature, mass flow, specific exergy).
    outl : dict
        Dictionary containing outlet streams data (e.g., temperature, mass flow, specific exergy).
    """

    def __init__(self, **kwargs):
        r"""Initialize flash tank component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy: bool) -> None:
        r"""
        Calculate the exergy balance of the flash tank.

        The exergy fuel (E_F) is computed as the sum of the inlet streams' exergy.
        If split_physical_exergy is True, the thermal exergy (e_T) is used;
        otherwise, the physical exergy (e_PH) is used.
        The exergy product (E_P) is calculated as the sum of the physical exergy of the
        outlet streams. Exergy destruction (E_D) is the difference E_F - E_P, and
        exergetic efficiency is ε = E_P / E_F.

        Parameters
        ----------
        T0 : float
            Ambient temperature in Kelvin.
        p0 : float
            Ambient pressure in Pascal.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.
        """
        # Ensure that at least two inlet streams and two outlet streams are provided.
        if len(self.inl) < 2 or len(self.outl) < 2:
            raise ValueError("FlashTank requires at least two inlets and two outlets.")
        
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
