import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class SimpleHeatExchanger(Component):
    """
    SimpleHeatExchanger component class.

    This class represents a simple heat exchanger within the system and is responsible for
    calculating the exergy balance specific to a simple heat exchanger. It manages the
    thermal interactions between a single inlet and outlet stream to determine the
    exergy product, exergy fuel, exergy destruction, and exergy efficiency based on the
    thermal conditions of the streams relative to a reference environment.

    Attributes
    ----------
    E_P : float
        Exergy product (physical exergy difference between outlet and inlet).
    E_F : float
        Exergy fuel (physical and thermal exergy differences).
    E_D : float
        Exergy destruction (difference between exergy fuel and exergy product).
    epsilon : float
        Exergy efficiency, defined as the ratio of exergy product to exergy fuel.
    inl : list of dict
        List of inlet streams. The expected configuration is:
            - `inl[0]`: Single fluid inlet.
            - `inl[1]`: Heat flow (of heat consumer).
    outl : list of dict
        List of outlet streams. The expected configuration is:
            - `outl[0]`: Single fluid outlet.
            - `outl[1]`: Heat flow (of heat extractor).

    Methods
    -------
    __init__(**kwargs)
        Initializes the SimpleHeatExchanger component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the simple heat exchanger.
    """

    def __init__(self, **kwargs):
        """
        Initialize the SimpleHeatExchanger component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the simple heat exchanger.

        This method computes the exergy product, exergy fuel, exergy destruction,
        and exergy efficiency based on the inlet and outlet streams. It evaluates
        the thermal states of the streams relative to a reference temperature and
        applies appropriate calculations for different thermal scenarios.

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.

        Raises
        ------
        ValueError
            If the simple heat exchanger does not have exactly one inlet and one outlet.

        Calculation Details
        -------------------
        The exergy balance is determined based on the heat transfer (`Q`) and the
        temperature states of the inlet and outlet streams relative to the reference
        temperature (T0):

        - **Heat Transfer (Q)**:
            \[
            Q = \dot{m}_{\text{out}} \cdot h_{\text{out}} - \dot{m}_{\text{in}} \cdot h_{\text{in}}
            \]
            Represents the net heat transfer between the inlet and outlet streams.

        - **Exergy Product (E_P)**:
            - **When Heat is Released (Q < 0)**:
                \[
                E_P = 
                \begin{cases}
                \text{NaN} & \text{if dissipative} \\
                \dot{m}_{\text{in}} \cdot (e_{\text{PH,in}} - e_{\text{PH,out}})
                \end{cases}
                \]
            - **When Heat is Added (Q > 0)**:
                \[
                E_P = \dot{m}_{\text{out}} \cdot (e_{\text{PH,out}} - e_{\text{PH,in}})
                \]

        - **Exergy Fuel (E_F)**:
            - **When Heat is Released (Q < 0)**:
                \[
                E_F = \dot{m}_{\text{in}} \cdot (e_{\text{PH,in}} - e_{\text{PH,out}})
                \]
                or
                \[
                E_F = \dot{m}_{\text{in}} \cdot e_{\text{T,in}} + \dot{m}_{\text{out}} \cdot e_{\text{T,out}} + (\dot{m}_{\text{in}} \cdot e_{\text{M,in}} - \dot{m}_{\text{out}} \cdot e_{\text{M,out}})
                \]
            - **When Heat is Added (Q > 0)**:
                \[
                E_F = \dot{m}_{\text{out}} \cdot (e_{\text{T,out}} - e_{\text{T,in}})
                \]

        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
            Represents the irreversibilities within the heat exchanger.

        - **Exergy Efficiency (\(\epsilon\))**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
            Indicates how effectively the heat exchanger transfers exergy.

        The method handles different cases based on whether heat is released or added
        and the temperature states of the inlet and outlet streams relative to T0.
        """
        # Validate the number of inlets and outlets
        if not hasattr(self, 'inl') or not hasattr(self, 'outl'):
            msg = "Simple heat exchanger requires at least one inlet and one outlet as well as one heat flow."
            logging.error(msg)
            raise ValueError(msg)
        if len(self.inl) > 2 or len(self.outl) > 2:
            msg = "Simple heat exchanger requires a maximum of two inlets and two outlets."
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
                self.E_P = np.nan if getattr(self, 'dissipative', False) else inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
                self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
            elif inlet['T'] >= T0 and outlet['T'] < T0:
                self.E_P = outlet['m'] * outlet['e_T']
                self.E_F = (inlet['m'] * inlet['e_T'] +
                           outlet['m'] * outlet['e_T'] +
                           (inlet['m'] * inlet['e_M'] - outlet['m'] * outlet['e_M']))
            elif inlet['T'] <= T0 and outlet['T'] <= T0:
                self.E_P = outlet['m'] * (outlet['e_T'] - inlet['e_T'])
                self.E_F = self.E_P + inlet['m'] * (inlet['e_M'] - outlet['m'] * outlet['e_M'])
            else:
                logging.warning("Exergy balance for simple heat exchangers with outlet temperature higher than inlet temperature during heat release is not implemented.")
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 2: Heat is added (Q > 0)
        elif Q > 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                self.E_P = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                self.E_F = outlet['m'] * (outlet['e_T'] - inlet['e_T'])
            elif inlet['T'] < T0 and outlet['T'] > T0:
                self.E_P = outlet['m'] * (outlet['e_T'] + inlet['e_T'])
                self.E_F = (inlet['m'] * inlet['e_T'] +
                           (inlet['m'] * inlet['e_M'] - outlet['m'] * outlet['e_M']))
            elif inlet['T'] < T0 and outlet['T'] < T0:
                self.E_P = np.nan if getattr(self, 'dissipative', False) else \
                    inlet['m'] * (inlet['e_T'] - outlet['e_T']) + \
                    (outlet['m'] * outlet['e_M'] - inlet['m'] * inlet['e_M'])
                self.E_F = inlet['m'] * (inlet['e_T'] - outlet['e_T'])
            else:
                logging.warning("Exergy balance for simple heat exchangers with inlet temperature higher than outlet temperature during heat addition is not implemented.")
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 3: Fully dissipative (Q == 0 or other scenarios)
        else:
            self.E_P = np.nan
            self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])

        # Calculate exergy destruction
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self._calc_epsilon()

        # Log the results
        logging.info(
            f"Simple Heat Exchanger Exergy Balance Calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, Efficiency={self.epsilon:.2%}"
        )
