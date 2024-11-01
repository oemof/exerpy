import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class HeatExchanger(Component):
    """
    HeatExchanger component class.

    This class represents a heat exchanger within the system, responsible for calculating
    the exergy balance specific to a heat exchanger. It evaluates the thermal interactions
    between multiple inlet and outlet streams and determines exergy product, exergy fuel,
    exergy destruction, and exergy efficiency.

    Attributes
    ----------
    E_P : float
        Exergy product, calculated as the net exergy transfer in the outlet streams relative
        to the inlet streams, dependent on the temperature states of the streams in relation to
        the reference temperature (T0).
    E_F : float
        Exergy fuel, defined as the net exergy input required to drive the heat exchange,
        determined based on thermal and physical exergy states of inlet and outlet streams.
    E_D : float
        Exergy destruction, representing the irreversibilities within the heat exchanger, calculated
        as the difference between exergy fuel and exergy product.
    epsilon : float
        Exergy efficiency, defined as the ratio of exergy product to exergy fuel, indicating
        the effectiveness of exergy transfer in the heat exchanger.

    Methods
    -------
    __init__(**kwargs)
        Initializes the HeatExchanger component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the heat exchanger.
    """

    def __init__(self, **kwargs):
        """
        Initialize the HeatExchanger component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the heat exchanger.

        This method computes the exergy product, exergy fuel, exergy destruction,
        and exergy efficiency based on the inlet and outlet streams' thermal states
        relative to a reference temperature (T0). Exergy balance cases vary
        according to whether streams are above, below, or equal to the ambient
        temperature.

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.

        Raises
        ------
        ValueError
            If the heat exchanger does not have exactly two inlets and two outlets.

        Calculation Details
        -------------------
        The exergy balance is calculated based on different scenarios for stream
        temperatures relative to T0:

        - **Exergy Product (E_P)**:
            Calculated from the physical exergy difference in outlet and inlet streams. 
            Cases may involve positive or zero exergy product depending on temperature 
            alignment with ambient conditions.

        - **Exergy Fuel (E_F)**:
            Derived from the energy input needed to achieve the desired heat exchange
            effects, calculated differently across scenarios based on stream temperatures 
            relative to T0.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
            Represents irreversibilities within the heat exchanger.

        - **Exergy Efficiency (\(\epsilon\))**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
            Represents the effectiveness of exergy transfer in the heat exchanger.

        This method considers multiple cases, including scenarios where all streams 
        are above, below, or mixed in relation to T0.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 2:
            raise ValueError("Heat exchanger requires two inlets and two outlets.")

        # Access the streams via .values() to iterate over the actual stream data
        all_streams = list(self.inl.values()) + list(self.outl.values())

        # Case 1: All streams are above the ambient temperature
        if all([stream['T'] >= T0 for stream in all_streams]):
            self.E_P = self.outl[1]['m'] * self.outl[1]['e_T'] - self.inl[1]['m'] * self.inl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_M'] - self.outl[1]['m'] * self.outl[1]['e_M'])

        # Case 2: All streams are below or equal to the ambient temperature
        elif all([stream['T'] <= T0 for stream in all_streams]):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] - self.inl[0]['m'] * self.inl[0]['e_T']
            self.E_F = self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'] + (
                self.inl[0]['m'] * self.inl[0]['e_M'] - self.outl[0]['m'] * self.outl[0]['e_M'])

        # Case 3: Some streams are above and others below ambient temperature
        elif (self.inl[0]['T'] > T0 and self.outl[1]['T'] > T0 and
              self.outl[0]['T'] <= T0 and self.inl[1]['T'] <= T0):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] + self.outl[1]['m'] * self.outl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'] - (
                self.outl[0]['m'] * self.outl[0]['e_M'] + self.outl[1]['m'] * self.outl[1]['e_M'])

        # Case 4: First inlet is above ambient, others below or equal
        elif (self.inl[0]['T'] > T0 and self.inl[1]['T'] <= T0 and
              self.outl[0]['T'] <= T0 and self.outl[1]['T'] <= T0):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'] - (
                self.outl[1]['m'] * self.outl[1]['e_PH'] + self.outl[0]['m'] * self.outl[0]['e_M'])

        # Case 5: Inlets are higher but outlets are below or equal to ambient
        elif (self.inl[0]['T'] > T0 and self.outl[0]['T'] > T0 and
              self.inl[1]['T'] <= T0 and self.outl[1]['T'] <= T0):
            self.E_P = np.nan
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'])

        # Case 6: One outlet is above ambient, others lower
        else:
            self.E_P = self.outl[1]['m'] * self.outl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_M'])

        # Calculate exergy destruction and efficiency
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P
        self.epsilon = self._calc_epsilon()

        logging.info(f"Heat Exchanger exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")
