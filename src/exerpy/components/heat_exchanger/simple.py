import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class SimpleHeatExchanger(Component):
    r"""
    Class for exergy analysis of simple heat exchangers.

    This class performs exergy analysis calculations for simple heat exchangers with
    one primary flow stream and heat transfer. The exergy product and fuel definitions
    vary based on the direction of heat transfer and temperature levels relative to
    ambient temperature.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.
        Optional parameter 'dissipative' (bool) to indicate if the component
        is considered fully dissipative.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component :math:`\dot{E}_\text{F}` in :math:`\text{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\text{P}` in :math:`\text{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\text{D}` in :math:`\text{W}`.
    epsilon : float
        Exergetic efficiency of the component :math:`\varepsilon` in :math:`-`.
    inl : dict
        Dictionary containing inlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.

    Notes
    -----
    The exergy analysis considers three main cases based on heat transfer
    direction and temperatures relative to ambient temperature :math:`T_0`:

    Case 1 - **Heat Release** (:math:`\dot{Q} < 0`):

    a) Both temperatures above ambient:

    .. math::

        \dot{E}_\text{P} &= \dot{m} \cdot (e^\text{T}_\text{in} -
        e^\text{T}_\text{out})\\
        \dot{E}_\text{F} &= \dot{m} \cdot (e^\text{PH}_\text{in} -
        e^\text{PH}_\text{out})

    b) Inlet above, outlet below ambient:

    .. math::

        \dot{E}_\text{P} &= \dot{m}_\text{out} \cdot e^\text{T}_\text{out}\\
        \dot{E}_\text{F} &= \dot{m}_\text{in} \cdot e^\text{T}_\text{in} +
        \dot{m}_\text{out} \cdot e^\text{T}_\text{out} +
        (\dot{m}_\text{in} \cdot e^\text{M}_\text{in} -
        \dot{m}_\text{out} \cdot e^\text{M}_\text{out})

    c) Both temperatures below ambient:

    .. math::

        \dot{E}_\text{P} &= \dot{m}_\text{out} \cdot
        (e^\text{T}_\text{out} - e^\text{T}_\text{in})\\
        \dot{E}_\text{F} &= \dot{E}_\text{P} + \dot{m}_\text{in} \cdot
        (e^\text{M}_\text{in} - e^\text{M}_\text{out})

    Case 2 - **Heat Addition** (:math:`\dot{Q} > 0`):

    a) Both temperatures above ambient:

    .. math::

        \dot{E}_\text{P} &= \dot{m}_\text{out} \cdot
        (e^\text{PH}_\text{out} - e^\text{PH}_\text{in})\\
        \dot{E}_\text{F} &= \dot{m}_\text{out} \cdot
        (e^\text{T}_\text{out} - e^\text{T}_\text{in})

    b) Inlet below, outlet above ambient:

    .. math::

        \dot{E}_\text{P} &= \dot{m}_\text{out} \cdot
        (e^\text{T}_\text{out} + e^\text{T}_\text{in})\\
        \dot{E}_\text{F} &= \dot{m}_\text{in} \cdot e^\text{T}_\text{in} +
        (\dot{m}_\text{in} \cdot e^\text{M}_\text{in} -
        \dot{m}_\text{out} \cdot e^\text{M}_\text{out})

    c) Both temperatures below ambient:

    .. math::

        \dot{E}_\text{P} &= \dot{m}_\text{in} \cdot
        (e^\text{T}_\text{in} - e^\text{T}_\text{out}) +
        (\dot{m}_\text{out} \cdot e^\text{M}_\text{out} -
        \dot{m}_\text{in} \cdot e^\text{M}_\text{in})\\
        \dot{E}_\text{F} &= \dot{m}_\text{in} \cdot
        (e^\text{T}_\text{in} - e^\text{T}_\text{out})

    Case 3 - **Dissipative** (it is not possible to specify the exergy product
    :math:`\dot{E}_\text{P}` for this component):

    .. math::

        \dot{E}_\text{P} &= \text{NaN}\\
        \dot{E}_\text{F} &= \dot{m}_\text{in} \cdot
        (e^\text{PH}_\text{in} - e^\text{PH}_\text{out})

    For all cases, the exergy destruction is calculated as:

    .. math::

        \dot{E}_\text{D} = \dot{E}_\text{F} - \dot{E}_\text{P}

    Where:

    - :math:`e^\text{T}`: Thermal exergy
    - :math:`e^\text{PH}`: Physical exergy
    - :math:`e^\text{M}`: Mechanical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize simple heat exchanger component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the simple heat exchanger.

        Performs exergy balance calculations considering both heat transfer direction
        and temperature levels relative to ambient temperature.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined or
            exceed the maximum allowed number.
        """
        # Validate the number of inlets and outlets
        if not hasattr(self, 'inl') or not hasattr(self, 'outl') or len(self.inl) < 1 or len(self.outl) < 1:
            msg = "SimpleHeatExchanger requires at least one inlet and one outlet as well as one heat flow."
            logging.error(msg)
            raise ValueError(msg)
        if len(self.inl) > 2 or len(self.outl) > 2:
            msg = "SimpleHeatExchanger requires a maximum of two inlets and two outlets."
            logging.error(msg)
            raise ValueError(msg)

        # Extract inlet and outlet streams
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Calculate heat transfer Q
        Q = outlet['m'] * outlet['h'] - inlet['m'] * inlet['h']

        # Initialize E_P and E_F
        self.E_P = 0.0
        self.E_F = 0.0

        # Case 1: Heat is released (Q < 0)
        if Q < 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                if split_physical_exergy:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else inlet['m'] * (inlet['e_T'] - outlet['e_T'])
                else:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
                self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])

            elif inlet['T'] >= T0 and outlet['T'] < T0:
                if split_physical_exergy:
                    self.E_P = outlet['m'] * outlet['e_T']
                    self.E_F = (inlet['m'] * inlet['e_T'] + outlet['m'] * outlet['e_T'] +
                            (inlet['m'] * inlet['e_M'] - outlet['m'] * outlet['e_M']))
                else:
                    self.E_P = outlet['m'] * outlet['e_PH']
                    self.E_F = inlet['m'] * inlet['e_PH']

            elif inlet['T'] <= T0 and outlet['T'] <= T0:
                if split_physical_exergy:
                    self.E_P = outlet['m'] * (outlet['e_T'] - inlet['e_T'])
                    self.E_F = self.E_P + inlet['m'] * (inlet['e_M'] - outlet['m'] * outlet['e_M'])
                else:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else \
                        outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                    self.E_F = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])

            else:
                # Unimplemented corner case
                logging.warning(
                    "SimpleHeatExchanger: unimplemented case (Q < 0, T_in < T0 < T_out?)."
                )
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 2: Heat is added (Q > 0)
        elif Q > 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                if split_physical_exergy:
                    self.E_P = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                    self.E_F = outlet['m'] * (outlet['e_T'] - inlet['e_T'])
                else:
                    self.E_P = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                    self.E_F = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
            elif inlet['T'] < T0 and outlet['T'] > T0:
                if split_physical_exergy:
                    self.E_P = outlet['m'] * (outlet['e_T'] + inlet['e_T'])
                    self.E_F = (inlet['m'] * inlet['e_T'] +
                            (inlet['m'] * inlet['e_M'] - outlet['m'] * outlet['e_M']))
                else:
                    self.E_P = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                    self.E_F = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])

            elif inlet['T'] < T0 and outlet['T'] < T0:
                if split_physical_exergy:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else \
                        inlet['m'] * (inlet['e_T'] - outlet['e_T']) + \
                        (outlet['m'] * outlet['e_M'] - inlet['m'] * inlet['e_M'])
                    self.E_F = inlet['m'] * (inlet['e_T'] - outlet['e_T'])
                else:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else \
                        inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
                    self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
            else:
                logging.warning(
                    "SimpleHeatExchanger: unimplemented case (Q > 0, T_in > T0 > T_out?)."
                )
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 3: Fully dissipative or Q == 0
        else:
            self.E_P = np.nan
            self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])

        # Calculate exergy destruction
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"SimpleHeatExchanger exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )
