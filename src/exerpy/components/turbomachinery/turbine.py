import logging
import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Turbine(Component):
    r"""
    Class for exergy analysis of turbines.

    This class performs exergy analysis calculations for turbines, with definitions
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
        Power output of the turbine in :math:`\text{W}`.
    inl : dict
        Dictionary containing inlet stream data with temperature, mass flows,
        enthalpies, and specific exergies. Must have at least one inlet.
    outl : dict
        Dictionary containing outlet streams data with temperature, mass flows,
        enthalpies, and specific exergies. Can have multiple outlets, their
        properties will be summed up in the calculations.

    Notes
    -----
    The exergy analysis considers three cases based on temperature relationships:

    .. math::

        \dot{E}_\mathrm{P} =
        \begin{cases}
        -P & T_\mathrm{in}, T_\mathrm{out} \geq T_0\\
        -P + \dot{E}_\mathrm{out}^\mathrm{T}
        & T_\mathrm{in} > T_0 \geq T_\mathrm{out}\\
        -P + \dot{E}_\mathrm{out}^\mathrm{T} - \dot{E}_\mathrm{in}^\mathrm{T}
        & T_0 \geq T_\mathrm{in}, T_\mathrm{out}
        \end{cases}

        \dot{E}_\mathrm{F} =
        \begin{cases}
        \dot{E}_\mathrm{in}^\mathrm{PH} - \dot{E}_\mathrm{out}^\mathrm{PH}
        & T_\mathrm{in}, T_\mathrm{out} \geq T_0\\
        \dot{E}_\mathrm{in}^\mathrm{T} + \dot{E}_\mathrm{in}^\mathrm{M} -
        \dot{E}_\mathrm{out}^\mathrm{M}
        & T_\mathrm{in} > T_0 \geq T_\mathrm{out}\\
        \dot{E}_\mathrm{in}^\mathrm{M} - \dot{E}_\mathrm{out}^\mathrm{M}
        & T_0 \geq T_\mathrm{in}, T_\mathrm{out}
        \end{cases}
    """

    def __init__(self, **kwargs):
        r"""Initialize turbine component with given parameters."""
        super().__init__(**kwargs)
        self.P = None

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the turbine.

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
            self.P = self._total_outlet('m', 'h') - self.inl[0]['m'] * self.inl[0]['h']

        # Case 1: Both temperatures above ambient
        if self.inl[0]['T'] >= T0 and self.outl[0]['T'] >= T0:
            self.E_P = abs(self.P)
            self.E_F = (self.inl[0]['m'] * self.inl[0]['e_PH'] -
                        self._total_outlet('m', 'e_PH'))

        # Case 2: Inlet above, outlet at/below ambient
        elif self.inl[0]['T'] > T0 and self.outl[0]['T'] <= T0:
            self.E_P = abs(self.P) + self._total_outlet('m', 'e_T')
            self.E_F = (self.inl[0]['m'] * self.inl[0]['e_T'] +
                        self.inl[0]['m'] * self.inl[0]['e_M'] -
                        self._total_outlet('m', 'e_M'))

        # Case 3: Both temperatures at/below ambient
        elif self.inl[0]['T'] <= T0 and self.outl[0]['T'] <= T0:
            self.E_P = abs(self.P) + (
                self._total_outlet('m', 'e_T') - self.inl[0]['m'] * self.inl[0]['e_T'])
            self.E_F = (self.inl[0]['m'] * self.inl[0]['e_M'] -
                        self._total_outlet('m', 'e_M'))

        # Invalid case: outlet temperature larger than inlet
        else:
            logging.warning(
                'Exergy balance of a turbine where outlet temperature is larger '
                'than inlet temperature is not implemented.'
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Turbine exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def _total_outlet(self, mass_flow: str, property_name: str) -> float:
        r"""
        Calculate the sum of mass flow times property across all outlets.

        Parameters
        ----------
        mass_flow : str
            Key for the mass flow value.
        property_name : str
            Key for the property to be summed.

        Returns
        -------
        float
            Sum of mass flow times property across all outlets.
        """
        total = 0.0
        for outlet in self.outl.values():
            if outlet and mass_flow in outlet and property_name in outlet:
                total += outlet[mass_flow] * outlet[property_name]
        return total