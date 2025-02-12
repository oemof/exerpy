import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Valve(Component):
    r"""
    Class for exergy analysis of valves.

    This class performs exergy analysis calculations for isenthalpic valves with 
    one inlet and one outlet stream. The exergy product and fuel definitions
    vary based on the temperature relationships between inlet stream, outlet stream,
    and ambient conditions.

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
    inl : dict
        Dictionary containing inlet stream data with temperature, mass flows,
        and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        and specific exergies.

    Notes
    -----
    The exergy analysis accounts for physical, thermal, and mechanical exergy
    based on temperature relationships:

    .. math::

        \dot{E}_\mathrm{P} =
        \begin{cases}
        \text{not defined (nan)}
        & T_\mathrm{in}, T_\mathrm{out} > T_0\\
        \dot{m} \cdot e_\mathrm{out}^\mathrm{T}
        & T_\mathrm{in} > T_0 \geq T_\mathrm{out}\\
        \dot{m} \cdot (e_\mathrm{out}^\mathrm{T} - e_\mathrm{in}^\mathrm{T})
        & T_0 \geq T_\mathrm{in}, T_\mathrm{out}
        \end{cases}

        \dot{E}_\mathrm{F} =
        \begin{cases}
        \dot{m} \cdot (e_\mathrm{in}^\mathrm{PH} - e_\mathrm{out}^\mathrm{PH})
        & T_\mathrm{in}, T_\mathrm{out} > T_0\\
        \dot{m} \cdot (e_\mathrm{in}^\mathrm{T} + e_\mathrm{in}^\mathrm{M} 
        - e_\mathrm{out}^\mathrm{M})
        & T_\mathrm{in} > T_0 \geq T_\mathrm{out}\\
        \dot{m} \cdot (e_\mathrm{in}^\mathrm{M} - e_\mathrm{out}^\mathrm{M})
        & T_0 \geq T_\mathrm{in}, T_\mathrm{out}
        \end{cases}

    For all cases, except when :math:`T_\mathrm{out} > T_\mathrm{in}`, the exergy 
    destruction is calculated as:

    .. math::
        \dot{E}_\mathrm{D} = \begin{cases}
        \dot{E}_\mathrm{F} & \text{if } \dot{E}_\mathrm{P} = \text{nan}\\
        \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P} & \text{otherwise}
        \end{cases}

    Where:
        - :math:`e^\mathrm{T}`: Thermal exergy
        - :math:`e^\mathrm{PH}`: Physical exergy
        - :math:`e^\mathrm{M}`: Mechanical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize valve component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the valve.

        Performs exergy balance calculations considering the temperature relationships
        between inlet stream, outlet stream, and ambient conditions.

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
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 1 or len(self.outl) < 1:
            raise ValueError("Valve requires at least one inlet and one outlet.")

        T_in = self.inl[0]['T']
        T_out = self.outl[0]['T']

        # Case-specific exergy calculations
        if T_in > T0 and T_out > T0:
            self.E_P = np.nan
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])
        elif T_out <= T0 and T_in > T0:
            self.E_P = self.inl[0]['m'] * self.outl[0]['e_T']
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_T'] + self.inl[0]['e_M'] - 
                                        self.outl[0]['e_M'])
        elif T_in <= T0 and T_out <= T0:
            self.E_P = self.inl[0]['m'] * (self.outl[0]['e_T'] - self.inl[0]['e_T'])
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_M'] - self.outl[0]['e_M'])
        else:
            logging.warning(
                "Exergy balance of a valve, where outlet temperature is larger than "
                "inlet temperature, is not implemented."
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Valve exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )