import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class CombustionChamber(Component):
    """
    CombustionChamber component class.

    This class represents a combustion chamber within the system and is responsible for
    calculating the exergy balance specific to a combustion chamber. It handles the
    interactions between fuel and air inlets and the exhaust outlet to determine
    exergy product, exergy fuel, exergy destruction, and exergy efficiency.

    Attributes
    ----------
    E_P : float
        Exergy product (physical exergy difference between outlet and inlets).
    E_F : float
        Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
    E_D : float
        Exergy destruction (difference between exergy fuel and exergy product).
    epsilon : float
        Exergy efficiency.
    inl : list of dict
        List of inlet streams. The expected configuration is:
            - `inl[0]`: Air inlet
            - `inl[1]`: Fuel inlet
            - `inl[2]`: Secondary air inlet (additional)
    outl : list of dict
        List of outlet streams. The expected configuration is:
            - `outl[0]`: Exhaust outlet
            - `outl[1]`: Slag / ash outlet (additional)

    Methods
    -------
    __init__(**kwargs)
        Initializes the CombustionChamber component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the combustion chamber.
    """

    def __init__(self, **kwargs):
        """
        Initialize the CombustionChamber component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate the exergy balance of the combustion chamber.

        This method computes the exergy product, exergy fuel, exergy destruction,
        and exergy efficiency based on the inlet and outlet streams. It ensures that
        there are at least two inlets (air and fuel) and one outlet (exhaust).

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.

        Raises
        ------
        ValueError
            If the combustion chamber does not have at least two inlets (air and fuel)
            and one outlet (exhaust).

        Calculation Details
        -------------------
        - **Exergy Product (E_P)**:
            \[
            E_P = \dot{m}_{\text{exhaust}} \cdot e_{\text{PH,exhaust}} - \left( \dot{m}_{\text{air}} \cdot e_{\text{PH,air}} + \dot{m}_{\text{fuel}} \cdot e_{\text{PH,fuel}} \right)
            \]
        
        - **Exergy Fuel (E_F)**:
            \[
            E_F = \left( \dot{m}_{\text{fuel}} \cdot e_{\text{CH,fuel}} + \dot{m}_{\text{air}} \cdot e_{\text{CH,air}} \right) - \dot{m}_{\text{exhaust}} \cdot e_{\text{CH,exhaust}}
            \]
        
        - **Exergy Destruction (E_D)**:
            \[
            E_D = E_F - E_P
            \]
        
        - **Exergy Efficiency (\epsilon)**:
            \[
            \epsilon = \frac{E_P}{E_F}
            \]
        """
        # Check for necessary inlet and outlet data
        if not hasattr(self, 'inl') or not hasattr(self, 'outl') or len(self.inl) < 2 or len(self.outl) < 1:
            msg = "Combustion chamber requires at least two inlets (air and fuel) and one outlet (exhaust)."
            logging.error(msg)
            raise ValueError(msg)
        
        # Calculate total physical exergy of outlets
        total_E_P_out = sum(outlet['m'] * outlet['e_PH'] for outlet in self.outl.values())
        
        # Calculate total physical exergy of inlets
        total_E_P_in = sum(inlet['m'] * inlet['e_PH'] for inlet in self.inl.values())
        
        # Exergy Product (E_P)
        self.E_P = total_E_P_out - total_E_P_in
        
        # Calculate total chemical exergy of inlets
        total_E_F_in = sum(inlet['m'] * inlet['e_CH'] for inlet in self.inl.values())
        
        # Calculate total chemical exergy of outlets
        total_E_F_out = sum(outlet['m'] * outlet['e_CH'] for outlet in self.outl.values())
        
        # Exergy Fuel (E_F)
        self.E_F = total_E_F_in - total_E_F_out

        # Exergy destruction (difference between exergy fuel and exergy product)
        self.E_D = self.E_F - self.E_P

        # Exergy efficiency (epsilon)
        self.epsilon = self._calc_epsilon()

        # Log the results
        logging.info(
            f"Combustion Chamber Exergy balance calculated: "
            f"E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}"
        )