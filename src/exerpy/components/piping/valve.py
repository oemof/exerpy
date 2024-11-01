import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Valve(Component):
    """
    Valve component class.

    This class represents a valve within the system, responsible for calculating
    the exergy balance specific to a valve. It evaluates the exergy interactions
    between an inlet and an outlet stream to assess exergy product, exergy fuel,
    exergy destruction, and exergy efficiency.

    Attributes
    ----------
    E_P : float
        Exergy product, defined based on the temperature states of the inlet and
        outlet relative to the reference temperature (T0). For a valve, it typically
        represents the net exergy output.
    E_F : float
        Exergy fuel, representing the total exergy input needed to drive the valve process,
        calculated from the exergy difference between the inlet and outlet.
    E_D : float
        Exergy destruction, representing the irreversibilities within the valve,
        calculated as the difference between exergy fuel and exergy product.
    epsilon : float
        Exergy efficiency, defined as the ratio of exergy product to exergy fuel, indicating
        the efficiency of exergy transfer through the valve.

    Methods
    -------
    __init__(**kwargs)
        Initializes the Valve component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the valve.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Valve component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the valve.

        This method computes the exergy product, exergy fuel, exergy destruction,
        and exergy efficiency based on the inlet and outlet streams' thermal states
        relative to the reference temperature (T0). The calculation varies based
        on whether both temperatures are above, equal to, or below the reference
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
            If the valve does not have at least one inlet and one outlet.

        Calculation Details
        -------------------
        The exergy balance is calculated based on the relative temperatures of
        the inlet and outlet streams in comparison to T0:

        - **Exergy Product (E_P)**:
            Calculated from the physical exergy difference in the outlet stream
            relative to the inlet, with case-specific adjustments based on whether
            the inlet and outlet temperatures are above, equal to, or below T0.

        - **Exergy Fuel (E_F)**:
            Calculated based on the exergy input required to achieve the desired
            effect in the valve, dependent on the inlet and outlet thermal states.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
            Represents irreversibilities within the valve process.

        - **Exergy Efficiency (\(\epsilon\))**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
            Indicates the efficiency of exergy transfer through the valve.

        This method includes cases where both inlet and outlet temperatures are
        above T0, both are below, and where outlet temperature is equal to T0,
        affecting the values of E_P and E_F.
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
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_T'] + self.inl[0]['e_M'] - self.outl[0]['e_M'])
        elif T_in <= T0 and T_out <= T0:
            self.E_P = self.inl[0]['m'] * (self.outl[0]['e_T'] - self.inl[0]['e_T'])
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_M'] - self.outl[0]['e_M'])
        else:
            logging.warning("Exergy balance of a valve, where outlet temperature is larger than inlet temperature, is not implemented.")
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P
        
        self.epsilon = self._calc_epsilon()

        # Log the exergy balance results
        logging.info(f"Valve exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")
