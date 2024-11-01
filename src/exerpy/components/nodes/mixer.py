import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Mixer(Component):
    """
    Mixer component class.

    This class represents a mixer within the system, responsible for calculating
    the exergy balance specific to a mixing process. It manages the exergy interactions
    between multiple inlet streams and a single outlet stream to assess exergy product,
    exergy fuel, exergy destruction, and exergy efficiency.

    Attributes
    ----------
    E_P : float
        Exergy product, representing the net exergy available in the outlet stream relative
        to the inlets, calculated based on the thermal conditions of the streams.
    E_F : float
        Exergy fuel, calculated as the sum of exergy inputs required from each inlet to
        achieve the desired mixing effect, relative to the outlet stream.
    E_D : float
        Exergy destruction, representing the irreversibilities within the mixer, calculated
        as the difference between exergy fuel and exergy product.
    epsilon : float
        Exergy efficiency, defined as the ratio of exergy product to exergy fuel, indicating
        the efficiency of exergy transfer in the mixer.

    Methods
    -------
    __init__(**kwargs)
        Initializes the Mixer component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the mixer.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Mixer component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the mixer.

        This method computes the exergy product, exergy fuel, exergy destruction,
        and exergy efficiency based on the thermal and exergy states of the inlet
        and outlet streams relative to a reference temperature (T0). The calculation
        varies depending on whether the outlet temperature is above, equal to, or
        below the reference temperature.

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.

        Raises
        ------
        ValueError
            If the mixer does not have at least two inlets and one outlet.

        Calculation Details
        -------------------
        The exergy balance is determined by examining the outlet temperature
        relative to T0:

        - **Exergy Product (E_P)**:
            Calculated from the physical exergy difference in the outlet stream
            relative to each inlet stream, with specific adjustments based on
            whether the outlet temperature is greater than, equal to, or less
            than T0.

        - **Exergy Fuel (E_F)**:
            Derived from the exergy input needed to achieve the desired mixing,
            dependent on thermal conditions of the inlet streams relative to
            the outlet stream.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
            Represents irreversibilities within the mixing process.

        - **Exergy Efficiency (\(\epsilon\))**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
            Indicates the efficiency of the exergy transfer in the mixer.

        The method considers cases where the outlet temperature is either above,
        equal to, or below the reference temperature, affecting the calculation
        of E_P and E_F.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Mixer requires at least two inlets and one outlet.")

        self.E_P = 0
        self.E_F = 0

        # Case 1: Outlet temperature is greater than T0
        if self.outl[0]['T'] > T0:
            for _, inlet in self.inl.items():
                if inlet['T'] < self.outl[0]['T']:
                    if inlet['T'] >= T0:
                        self.E_P += inlet['m'] * (self.outl[0]['e_PH'] - inlet['e_PH'])
                    else:
                        self.E_P += inlet['m'] * self.outl[0]['e_PH']
                        self.E_F += inlet['E_PH']
                else:
                    self.E_F += inlet['m'] * (inlet['e_PH'] - self.outl[0]['e_PH'])
        
        # Case 2: Outlet temperature is equal to T0
        elif self.outl[0]['T'] == T0:
            self.E_P = np.nan
            for _, inlet in self.inl.items():
                self.E_F += inlet['E_PH']
        
        # Case 3: Outlet temperature is less than T0
        else:
            for _, inlet in self.inl.items():
                if inlet['T'] > self.outl[0]['T']:
                    if inlet['T'] >= T0:
                        self.E_P += inlet['m'] * self.outl[0]['e_PH']
                        self.E_F += inlet['E_PH']
                    else:
                        self.E_P += inlet['m'] * (self.outl[0]['e_PH'] - inlet['e_PH'])
                else:
                    self.E_F += inlet['m'] * (inlet['e_PH'] - self.outl[0]['e_PH'])

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self._calc_epsilon()

        # Log the exergy balance results
        logging.info(f"Mixer exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")
