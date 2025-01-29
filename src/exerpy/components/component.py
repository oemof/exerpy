import numpy as np


def component_registry(cls):
    """
    A decorator function to register components in the component registry.
    Registers the class using the class's name as the key.
    """
    component_registry.items[cls.__name__] = cls
    return cls


# Initialize the registry to store components
component_registry.items = {}


@component_registry
class Component:
    r"""
    Base class for all ExerPy components.

    This class serves as the parent class for all exergy analysis components. It provides
    the basic structure and methods for exergy analysis calculations including the 
    calculation of exergetic efficiency and exergy balance.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments that will be assigned as attributes to the component.

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

    Notes
    -----
    The exergetic efficiency is calculated as the ratio of exergy product to 
    exergy fuel:

    .. math::

        \varepsilon = \frac{\dot{E}_\mathrm{P}}{\dot{E}_\mathrm{F}}

    The exergy balance for any component follows the principle:

    .. math::

        \dot{E}_\mathrm{F} = \dot{E}_\mathrm{P} + \dot{E}_\mathrm{D}


    See Also
    --------
    exerpy.components : Module containing all available components for exergy analysis
    """

    def __init__(self, **kwargs):
        r"""Initialize the component with given parameters."""
        self.__dict__.update(kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the component.

        This method should be implemented by child classes to perform specific
        exergy balance calculations.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.
        """
        pass

    def calc_epsilon(self):
        r"""
        Calculate the exergetic efficiency of the component.

        The exergetic efficiency is defined as the ratio of exergy product to 
        exergy fuel. If the exergy fuel is zero, the function returns NaN to 
        avoid division by zero.

        Returns
        -------
        float or nan
            Exergetic efficiency :math:`\varepsilon = \frac{\dot{E}_\mathrm{P}}{\dot{E}_\mathrm{F}}` 
            or NaN if :math:`\dot{E}_\mathrm{F} = 0`.

        Notes
        -----
        .. math::
            \varepsilon = \begin{cases}
            \frac{\dot{E}_\mathrm{P}}{\dot{E}_\mathrm{F}} & \text{if } \dot{E}_\mathrm{F} \neq 0\\
            \text{NaN} & \text{if } \dot{E}_\mathrm{F} = 0
            \end{cases}
        """
        if self.E_F == 0:
            return np.nan
        else:
            return self.E_P / self.E_F
        

    def exergoeconomic_balance(self):
        """
        Calculate exergoeconomic properties using a minimal approach.
        
        Assumes:
          - self.E_F, self.E_P, self.E_D : exergy [W] from exergy analysis
          - self.Z_costs : cost rate [currency/h] assigned externally
        Defines:
          - C_F, c_F  : cost flow and specific cost of exergy "fuel"
          - C_P, c_P  : cost flow and specific cost of exergy "product" (basic assumption)
          - C_D       : cost flow associated with exergy destruction
          - f         : exergoeconomic factor
          - r         : relative cost difference
        """

        # If not assigned elsewhere, default 0
        if not hasattr(self, "Z_costs"):
            self.Z_costs = 0.0

        # --- 1) Cost flow of exergy fuel, simple assumption ---
        # e.g. assume Z_costs is the entire "fuel" cost flow
        self.C_F = self.Z_costs

        # specific cost of fuel c_F [currency/W]
        if getattr(self, "E_F", 0.0) > 1e-12:
            self.c_F = self.C_F / self.E_F
        else:
            self.c_F = 0.0

        # --- 2) Cost flow of exergy destruction ---
        #   C_D = c_F * E_D
        if getattr(self, "E_D", 0.0) > 1e-12:
            self.C_D = self.c_F * self.E_D
        else:
            self.C_D = 0.0

        # --- 3) Cost flow & specific cost of product c_P (basic approach) ---
        if getattr(self, "E_P", 0.0) > 1e-12:
            # total product cost flow ~ C_F + Z_costs (can refine if needed)
            total_cost_flow = self.C_F + self.Z_costs
            self.c_P = total_cost_flow / self.E_P
        else:
            self.c_P = None

        # --- 4) Exergoeconomic factor f = Z_costs / (Z_costs + C_D) ---
        denom = self.Z_costs + self.C_D
        self.f = (self.Z_costs / denom) if denom > 1e-12 else None

        # --- 5) Relative cost difference r = (c_P - c_F)/c_F ---
        if self.c_F > 1e-12 and self.c_P is not None:
            self.r = (self.c_P - self.c_F) / self.c_F
        else:
            self.r = None
