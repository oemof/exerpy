import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Storage(Component):
    r"""
    Class for exergy and exergoeconomic analysis of a storage.

    This class performs exergy and exergoeconomic analysis calculations for storage components,
    accounting for one inlet and one outlet stream.

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
        Initialize the storage component.

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
        Compute the exergy balance of the storage.

        Parameters
        ----------
        T0 : float
            Ambient temperature in Kelvin.
        p0 : float
            Ambient pressure in Pascal.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Notes
        -----
        The exergy analysis considers the cases where the storage is either charged or discharged.

        Case 1 (Charging):

        .. math::

            \dot{E}_\mathrm{F} = \dot{E}_\mathrm{in}^\mathrm{PH} - \dot{E}_\mathrm{out}^\mathrm{PH}

        .. math::
            \dot{E}_\mathrm{P} = (\dot{m}_\mathrm{in} - \dot{m}_\mathrm{out}) \cdot e_\mathrm{out}^\mathrm{PH}

            
        Case 2 (Discharging):

        .. math::

            \dot{E}_\mathrm{F} = (\dot{m}_\mathrm{out} - \dot{m}_\mathrm{in}) \cdot e_\mathrm{out}^\mathrm{PH}

        .. math::

            \dot{E}_\mathrm{P} = \dot{E}_\mathrm{out}^\mathrm{PH} - \dot{E}_\mathrm{in}^\mathrm{PH}
         
        """

        if self.outl[0]['m'] < self.inl[0]['m']:
            logging.info(f"Storage '{self.name}' is charged.")
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH']
            self.E_P = (self.inl[0]['m'] - self.outl[0]['m']) * self.outl[0]['e_PH']  # assuming that exergy is stored at the same temperature as the outlet
            self.E_D = self.E_F - self.E_P
        elif self.outl[0]['m'] > self.inl[0]['m']:
            logging.info(f"Storage '{self.name}' is discharged.")
            self.E_F =  (self.outl[0]['m'] - self.inl[0]['m']) * self.outl[0]['e_PH']  # assuming that exergy is stored at the same temperature as the outlet
            self.E_P =  self.outl[0]['m'] * self.outl[0]['e_PH'] - self.inl[0]['m'] * self.inl[0]['e_PH']  
            self.E_D = self.E_F - self.E_P

        self.epsilon = self.E_P / self.E_F if self.E_F != 0 else np.nan

        # Log the results.
        logging.info(
            f"Storage exergy balance calculated: "
            f"E_F = {self.E_F:.2f} W, E_P = {self.E_P:.2f} W, E_D = {self.E_D:.2f} W, "
        )

    def exergoeconomic_balance(self, T0):
        r"""
        This class has not been implemented yet!
        """
        pass