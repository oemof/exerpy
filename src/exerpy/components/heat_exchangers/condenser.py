import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Condenser(Component):
    """
    Condenser component class.

    This class represents a condenser within the system, responsible for
    calculating the exergy balance specific to condensation processes.
    It evaluates the exergy interactions between multiple inlet and outlet
    streams to determine exergy loss and exergy destruction.

    Attributes
    ----------
    E_L : float
        Exergy loss associated with heat transfer (difference in physical exergy 
        between specific outlet and inlet streams).
    E_D : float
        Exergy destruction, calculated as the difference between the primary 
        inlet and outlet streams minus exergy loss (E_L), representing
        irreversibilities in the condensation process.
    E_P : None
        Exergy product, not defined for a condenser as there is no exergy output
        intended for productive use.
    E_F : None
        Exergy fuel, typically undefined for a condenser as it does not involve 
        an external exergy input for production purposes.
    epsilon : None
        Exergy efficiency, not applicable to a condenser due to the nature of 
        exergy interactions focused on loss and destruction.

    Methods
    -------
    __init__(**kwargs)
        Initializes the Condenser component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the condenser.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Condenser component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the condenser.

        This method computes exergy loss and exergy destruction based on the inlet
        and outlet streams involved in the condensation process.

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.

        Raises
        ------
        ValueError
            If the condenser does not have exactly two inlets and two outlets.

        Calculation Details
        -------------------
        The exergy balance is determined based on exergy transfer due to heat loss (`E_L`)
        and the exergy destruction within the system:

        - **Exergy Loss (E_L)**:
            \[
            E_L = \dot{m}_{\text{out,1}} \cdot (e_{\text{PH,out,1}} - e_{\text{PH,in,1}})
            \]
            Represents the exergy loss due to heat transfer from the process.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = \dot{m}_{\text{out,0}} \cdot (e_{\text{PH,in,0}} - e_{\text{PH,out,0}}) - E_L
            \]
            Accounts for the irreversibilities and losses in the condenser.

        Note
        ----
        Exergy product (E_P) and exergy fuel (E_F) are generally undefined in a
        condenser due to the focus on exergy loss rather than productive exergy usage.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 2:
            raise ValueError("Condenser requires two inlets and two outlets.")
        
        # Calculate exergy loss (E_L) for the heat transfer process
        self.E_L = self.outl[1]['m'] * (self.outl[1]['e_PH'] - self.inl[1]['e_PH'])

        # Calculate exergy destruction (E_D)
        self.E_D = self.outl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH']) - self.E_L

        # Exergy fuel and product are not typically defined for a condenser
        self.E_F = None
        self.E_P = None
        self.epsilon = None

        # Log the exergy balance results
        logging.info(f"Condenser exergy balance calculated: E_D={self.E_D}, E_L={self.E_L}")
