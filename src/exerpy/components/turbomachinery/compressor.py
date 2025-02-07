import logging
import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Compressor(Component):
    r"""
    Class for exergy analysis of compressors.

    This class performs exergy analysis calculations for compressors, with definitions
    of exergy product and fuel varying based on the temperature relationships between
    inlet stream, outlet stream, and ambient conditions.

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
    P : float
        Power input to the compressor in :math:`\text{W}`.
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

        \dot{E}_\mathrm{P} &= \dot{m} \cdot e_\mathrm{out}^\mathrm{T} + 
        \dot{m} \cdot (e_\mathrm{out}^\mathrm{M} - e_\mathrm{in}^\mathrm{M})\\
        \dot{E}_\mathrm{F} &= |\dot{W}| + \dot{m} \cdot e_\mathrm{in}^\mathrm{T}

    Case 3 - **Both temperatures below ambient** (:math:`T_\mathrm{in}, T_\mathrm{out} \leq T_0`):

    .. math::

        \dot{E}_\mathrm{P} &= \dot{m} \cdot (e_\mathrm{out}^\mathrm{M} - 
        e_\mathrm{in}^\mathrm{M})\\
        \dot{E}_\mathrm{F} &= |\dot{W}| + \dot{m} \cdot (e_\mathrm{in}^\mathrm{T} 
        - e_\mathrm{out}^\mathrm{T})

    For all valid cases, the exergy destruction is:

    .. math::

        \dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}

    where:
        - :math:`\dot{W}`: Power input
        - :math:`e^\mathrm{T}`: Thermal exergy
        - :math:`e^\mathrm{PH}`: Physical exergy
        - :math:`e^\mathrm{M}`: Mechanical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize compressor component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the compressor.

        Performs exergy balance calculations considering the temperature relationships
        between inlet stream, outlet stream, and ambient conditions.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.
        """      
        # Get power flow if not already available
        if self.P is None:
            self.P = self.outl[0]['m'] * (self.outl[0]['h'] - self.inl[0]['h'])

        # Case 1: Both temperatures above ambient
        if round(self.inl[0]['T'], 5) >= T0 and round(self.outl[0]['T'], 5) > T0:
            self.E_P = self.outl[0]['m'] * (self.outl[0]['e_PH'] - self.inl[0]['e_PH'])
            self.E_F = abs(self.P)

        # Case 2: Inlet below, outlet above ambient
        elif round(self.inl[0]['T'], 5) < T0 and round(self.outl[0]['T'], 5) > T0:
            self.E_P = (self.outl[0]['m'] * self.outl[0]['e_T'] + 
                        self.outl[0]['m'] * (self.outl[0]['e_M'] - self.inl[0]['e_M']))
            self.E_F = abs(self.P) + self.inl[0]['m'] * self.inl[0]['e_T']

        # Case 3: Both temperatures below ambient
        elif round(self.inl[0]['T'], 5) < T0 and round(self.outl[0]['T'], 5) <= T0:
            self.E_P = self.outl[0]['m'] * (self.outl[0]['e_M'] - self.inl[0]['e_M'])
            self.E_F = abs(self.P) + self.inl[0]['m'] * (self.inl[0]['e_T'] - 
                                                        self.outl[0]['e_T'])

        # Invalid case: outlet temperature smaller than inlet
        else:
            logging.warning(
                'Exergy balance of a compressor where outlet temperature is smaller '
                'than inlet temperature is not implemented.'
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Compressor exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )