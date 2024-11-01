import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Deaerator(Component):
    """
    Deaerator component class.

    This class represents a deaerator within the system, responsible for calculating
    the exergy balance specific to a deaerator. It evaluates the thermal and exergy
    interactions between multiple inlet streams and a single outlet stream to assess
    the exergy product, exergy fuel, exergy destruction, and exergy efficiency.

    Attributes
    ----------
    E_P : float
        Exergy product, calculated based on the difference in physical exergy between
        the outlet and inlets, depending on whether the outlet temperature is above,
        below, or equal to the ambient reference temperature (T0).
    E_F : float
        Exergy fuel, representing the total exergy input required by the deaerator to
        achieve the desired heating or cooling, determined from the physical exergy of
        the inlet streams relative to the outlet.
    E_D : float
        Exergy destruction, representing irreversibilities within the deaerator, calculated
        as the difference between exergy fuel and exergy product.
    epsilon : float
        Exergy efficiency, defined as the ratio of exergy product to exergy fuel, indicating
        the effectiveness of the deaeration process.

    Methods
    -------
    __init__(**kwargs)
        Initializes the Deaerator component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the deaerator.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Deaerator component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the deaerator.

        This method computes the exergy product, exergy fuel, exergy destruction,
        and exergy efficiency based on the inlet and outlet streams, considering
        different scenarios where the outlet temperature is above, equal to, or below
        the reference temperature (T0).

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.

        Raises
        ------
        ValueError
            If the deaerator does not have at least two inlets and one outlet.

        Calculation Details
        -------------------
        The exergy balance is determined by examining the relationship between
        the inlet and outlet temperatures relative to T0:

        - **Exergy Product (E_P)**:
            Derived from the physical exergy difference between inlet and outlet
            streams, with case-specific adjustments based on whether outlet temperature
            is greater than, equal to, or less than T0.

        - **Exergy Fuel (E_F)**:
            Calculated from the energy input necessary to achieve the desired effect
            in the deaeration process, differing across scenarios based on thermal
            conditions of the streams.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
            Represents the irreversibilities within the deaerator process.

        - **Exergy Efficiency (\(\epsilon\))**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
            Indicates the exergy utilization efficiency within the deaerator.

        This method handles cases where the outlet temperature is either above, equal to,
        or below the reference temperature, with each scenario affecting how E_P and E_F
        are calculated.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Deaerator requires at least two inlets and one outlet.")

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
        logging.info(f"Deaerator exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")