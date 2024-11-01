import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Generator(Component):
    """
    Generator component class.

    This class represents a generator within the system, responsible for calculating
    the exergy balance specific to a generator. It assesses the exergy interactions
    between fuel input and electrical output to determine exergy product, exergy fuel,
    exergy destruction, and exergy efficiency.

    Attributes
    ----------
    E_P : float
        Exergy product, defined as the energy flow in the outlet, representing the net
        electrical work output of the generator.
    E_F : float
        Exergy fuel, representing the energy input to the generator, representing the
        mechanical work input of the generator.
    E_D : float
        Exergy destruction, representing irreversibilities within the generator, calculated
        as the difference between exergy fuel and exergy product.
    epsilon : float
        Exergy efficiency, defined as the ratio of exergy product to exergy fuel, indicating
        the efficiency of exergy transfer in the generator.

    Methods
    -------
    __init__(**kwargs)
        Initializes the Generator component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the generator.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Generator component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the generator.

        This method computes the exergy product, exergy fuel, exergy destruction,
        and exergy efficiency based on the energy flows of the inlet and outlet streams.

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.

        Calculation Details
        -------------------
        - **Exergy Product (E_P)**:
            Defined as the energy flow at the outlet, representing the electrical
            power output.

        - **Exergy Fuel (E_F)**:
            The energy input from the fuel, representing the mechanical work 
            input of the generator.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
            Represents irreversibilities within the generator process.

        - **Exergy Efficiency (\(\epsilon\))**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
            Indicates the efficiency of exergy transfer in the generator.

        The method directly calculates exergy attributes based on input and output
        energy flows without further temperature-based distinctions.
        """
        # Exergy product (physical exergy difference between outlet and inlets)
        self.E_P = self.outl[0]['energy_flow']

        # Exergy fuel (chemical exergy of fuel and air minus exhaust exergy)
        self.E_F = self.inl[0]['energy_flow']

        # Exergy destruction (difference between exergy fuel and exergy product)
        self.E_D = self.E_F - self.E_P

        # Exergy efficiency (epsilon)
        self.epsilon = self._calc_epsilon()

        # Log the exergy balance results
        logging.info(f"Generator exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")
