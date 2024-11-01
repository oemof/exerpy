import logging
import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Compressor(Component):
    """
    Compressor component class.

    This class represents a compressor within the system, responsible for calculating
    the exergy balance specific to a compressor. It evaluates the exergy interactions
    between power input and compressed output to determine exergy product, exergy fuel,
    exergy destruction, and exergy efficiency across different operational conditions.

    Attributes
    ----------
    E_P : float
        Exergy product, representing the mechanical or thermal exergy gain of the 
        compressed outlet stream, with calculations that vary based on inlet
        and outlet temperatures relative to the reference temperature (T0).
    E_F : float
        Exergy fuel, defined as the power input needed to drive the compression,
        adjusted according to the thermal and physical exergy of inlet and outlet streams.
    E_D : float
        Exergy destruction, representing irreversibilities within the compressor,
        calculated as the difference between exergy fuel and exergy product.
    epsilon : float
        Exergy efficiency, defined as the ratio of exergy product to exergy fuel,
        indicating the efficiency of exergy transfer in the compressor.

    Methods
    -------
    __init__(**kwargs)
        Initializes the Compressor component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the compressor.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Compressor component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the compressor.

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
            Calculated as the mechanical or thermal exergy gain of the compressed outlet stream,
            with case-specific formulas based on the relative temperatures of the inlet
            and outlet streams compared to T0.

        - **Exergy Fuel (E_F)**:
            Defined as the power input needed to drive the compressor, adjusted by the
            thermal and physical exergy state of the inlet stream.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
            Represents irreversibilities within the compression process.

        - **Exergy Efficiency (\(\epsilon\))**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
            Indicates the effectiveness of exergy transfer in the compressor.

        The method handles various cases where both the inlet and outlet temperatures
        are above T0, where only the outlet is above T0, or where both are below T0.
        """
        # Get power flow in case it wasn't read during the parsing
        if self.P is None:
            self.P = self.outl[0]['m'] * (self.outl[0]['h'] - self.inl[0]['h'])
        
        # Case 1: Both inlet and outlet temperatures are greater than ambient temperature
        if round(self.inl[0]['T'], 5) >= T0 and round(self.outl[0]['T'], 5) > T0:
            # Exergy product (useful exergy output, here it's mechanical work)
            self.E_P = self.outl[0]['m'] * (self.outl[0]['e_PH'] - self.inl[0]['e_PH'])
            # Exergy fuel (input to the process), based on the physical exergy difference
            self.E_F = abs(self.P)

        # Case 2: Inlet temperature is less than ambient, but outlet is greater than ambient temperature
        elif round(self.inl[0]['T'], 5) < T0 and round(self.outl[0]['T'], 5) > T0:
            # Exergy product (thermal exergy at the outlet + mechanical exergy change)
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] + self.outl[0]['m'] * (self.outl[0]['e_M'] - self.inl[0]['e_M'])
            # Exergy fuel includes power input and thermal exergy at the inlet
            self.E_F = abs(self.P) + self.inl[0]['m'] + self.inl[0]['e_T']

        # Case 3: Both inlet and outlet temperatures are less than or equal to ambient temperature
        elif round(self.inl[0]['T'], 5) < T0 and round(self.outl[0]['T'], 5) <= T0:
            # Exergy product (thermal exergy at the outlet + mechanical exergy change)
            self.E_P = self.outl[0]['m'] * (self.outl[0]['e_M'] - self.inl[0]['e_M'])
            # Exergy fuel includes power input and thermal exergy at the inlet
            self.E_F = abs(self.P) + self.inl[0]['m'] + (self.inl[0]['e_T'] - self.outl[0]['e_T'])

        # Invalid case: if outlet temperature is smaller than inlet temperature, this condition is not supported
        else:
            msg = ('Exergy balance of a compressor where outlet temperature '
                   'is smaller than inlet temperature is not implemented.')
            logging.warning(msg)
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        # Exergy destruction is the difference between the fuel and the useful product
        self.E_D = self.E_F - self.E_P

        # Exergy efficiency (epsilon) calculation
        self.epsilon = self._calc_epsilon()
