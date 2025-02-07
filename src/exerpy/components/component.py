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