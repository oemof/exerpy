import logging
import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Turbine(Component):
    """
    Turbine component class.

    This class represents a turbine within the system, responsible for calculating
    the exergy balance specific to a turbine. It evaluates the exergy interactions
    between the inlet and outlet streams, considering power output to determine
    exergy product, exergy fuel, exergy destruction, and exergy efficiency based
    on various operational scenarios.

    Attributes
    ----------
    E_P : float
        Exergy product, representing net mechanical work output of the turbine, with 
        calculations that vary based on the inlet and outlet temperatures
        relative to the reference temperature (T0).
    E_F : float
        Exergy fuel, defined as the net exergy input from the inlet stream, adjusted
        by the physical exergy difference between inlet and outlet streams.
    E_D : float
        Exergy destruction, representing irreversibilities within the turbine,
        calculated as the difference between exergy fuel and exergy product.
    epsilon : float
        Exergy efficiency, defined as the ratio of exergy product to exergy fuel,
        indicating the efficiency of exergy transfer in the turbine.

    Methods
    -------
    __init__(**kwargs)
        Initializes the Turbine component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the turbine.
    _total_outlet(property_name: str) -> float
        Calculates the sum of a specified property across all defined outlets.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Turbine component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the turbine.

        This method computes the exergy product, exergy fuel, exergy destruction,
        and exergy efficiency based on the thermal and exergy states of the inlet
        and outlet streams relative to a reference temperature (T0). Different cases
        are considered based on whether the inlet and outlet temperatures are above,
        below, or at the ambient temperature.

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.

        Calculation Details
        -------------------
        - **Exergy Product (E_P)**:
            Represents the net mechanical work output of the turbine, with
            case-specific formulas depending on the inlet and outlet
            temperatures compared to T0.

        - **Exergy Fuel (E_F)**:
            Defined as the exergy input derived from the inlet stream, adjusted for
            differences in physical exergy between inlet and outlet streams.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
            Represents irreversibilities within the turbine process.

        - **Exergy Efficiency (\(\epsilon\))**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
            Indicates the efficiency of exergy transfer in the turbine.

        This method handles cases where both inlet and outlet temperatures are above T0,
        where only the inlet is above T0, and where both are below T0.
        """
        # Get power flow in case it wasn't read during the parsing
        if self.P is None:
            self.P = self._total_outlet('m') * (self.inl[0]['h'] - self.outl[0]['h'])

        # Case 1: Both inlet and outlet temperatures are greater than ambient temperature
        if self.inl[0]['T'] >= T0 and self.outl[0]['T'] >= T0:
            self.E_P = abs(self.P)
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])

        # Case 2: Inlet temperature is greater than ambient, but outlet is less than or equal to ambient
        elif self.inl[0]['T'] > T0 and self.outl[0]['T'] <= T0:
            self.E_P = -self.P + self._total_outlet('m') * self.outl[0]['h']
            self.E_F = self.inl[0]['h'] + (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])

        # Case 3: Both inlet and outlet temperatures are less than or equal to ambient temperature
        elif self.inl[0]['T'] <= T0 and self.outl[0]['T'] <= T0:
            self.E_P = -self.P + (self._total_outlet('m') * self.outl[0]['h'] - self.inl[0]['h'] * self.inl[0]['m'])
            self.E_F = self.inl[0]['e_PH'] * self.inl[0]['m'] - self.outl[0]['e_PH'] * self.outl[0]['m']

        # Invalid case: if outlet temperature is larger than inlet temperature
        else:
            msg = ('Exergy balance of a turbine where outlet temperature is '
                   'larger than inlet temperature is not implemented.')
            logging.warning(msg)
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self._calc_epsilon()

    def _total_outlet(self, property_name: str) -> float:
        """
        Sum the specified property for all defined outlets.

        Parameters
        ----------
        property_name : str
            The property to be summed (e.g., 'h', 'e_PH', 'T').

        Returns
        -------
        float
            Sum of the specified property for all outlets, or 0 if no outlets are defined.
        """
        total_value = 0.0
        for outlet in self.outl.values():
            if outlet and property_name in outlet:
                total_value += outlet[property_name]
        return total_value
