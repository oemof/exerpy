import logging
import numpy as np

def component_registry(cls):
    """
    A decorator function to register components in the component registry.
    Registers the class using the class's name as the key.
    """
    component_registry.items[cls.__name__] = cls
    return cls


# Initialize the registry to store components
component_registry.items = {}


@component_registry
class Component:
    def __init__(self, **kwargs):
        """
        Base class for components. Initializes the component with provided keyword arguments.
        """
        self.__dict__.update(kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance for an individual component.
        This method should be overridden in derived classes.
        """
        pass

    def _calc_epsilon(self):
        if self.E_F == 0:
            return np.nan
        else:
            return self.E_P / self.E_F


@component_registry
class Turbine(Component):
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a turbine.

        Parameters:
        T0 (float): Ambient temperature in Kelvin.
        p0 (float): Ambient pressure in Pascal.
        """

        # Calculate exergy destruction based on the inlet and outlet temperatures
        if self.inl[0]['T'] >= T0 and self.outl[0]['T'] >= T0:
            # Case 1: Both inlet and outlet temperatures are greater than ambient temperature
            self.E_P = abs(self.P)  # Assuming P is already stored as power or a similar attribute
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])
        elif self.inl[0]['T'] > T0 and self.outl[0]['T'] <= T0:
            # Case 2: Inlet temperature is greater than ambient, but outlet is less than or equal to ambient
            self.E_P = -self.P + self.outl[0]['h']
            self.E_F = (self.inl[0]['h'] +
                        (self.inl[0]['e_PH'] - self.outl[0]['e_PH']))
        elif self.inl[0]['T'] <= T0 and self.outl[0]['T'] <= T0:
            # Case 3: Both inlet and outlet temperatures are less than or equal to ambient temperature
            self.E_P = (-self.P +
                        (self.outl[0]['h'] - self.inl[0]['h']))
            self.E_F = (self.inl[0]['e_PH'] -
                        self.outl[0]['e_PH'])
        else:
            # Invalid case: if outlet temperature is larger than inlet temperature
            msg = ('Exergy balance of a turbine where outlet temperature is '
                'larger than inlet temperature is not implemented.')
            logging.warning(msg)
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_bus = {"chemical": 0, "physical": 0, "massless": abs(self.P)}  # Adjust as needed
        self.E_D = self.E_F - self.E_P
        self.epsilon = self._calc_epsilon()



@component_registry
class Compressor(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a turbine.
        This method overrides the base class method for the specific behavior of a turbine.
        """
        # Get power flow in case it wasn't read during the parsing
        if self.P is None:
            self.P = self.outl[0]['m'] * (self.outl[0]['h'] - self.inl[0]['h'])
        
        # Case 1: Both inlet and outlet temperatures are greater than ambient temperature
        if round(self.inl[0]['T'],5) >= T0 and round(self.outl[0]['T'],5) > T0:
            # Exergy product (useful exergy output, here it's mechanical work)
            self.E_P = self.outl[0]['m'] * (self.outl[0]['e_PH'] - self.inl[0]['e_PH'])
            # Exergy fuel (input to the process), based on the physical exergy difference
            self.E_F = abs(self.P)

        # Case 2: Inlet temperature is less than ambient, but outlet is greater than ambient temperature
        elif round(self.inl[0]['T'],5) < T0 and round(self.outl[0]['T'],5) > T0:
            # Exergy product (mechanical work + thermal exergy change)
            self.E_P = abs(self.P) + (self.outl[0]['e_PH'] - self.inl[0]['e_M'])
            # Exergy fuel includes mechanical and thermal exergy at the inlet
            self.E_F = (self.inl[0]['e_M'] + self.inl[0]['e_PH'])

        # Case 3: Both inlet and outlet temperatures are less than or equal to ambient temperature
        elif round(self.inl[0]['T'],5) < T0 and round(self.outl[0]['T'],5) <= T0:
            # Exergy product (mechanical work only, assuming no useful thermal exergy)
            self.E_P = self.outl[0]['e_M'] - self.inl[0]['e_M']
            # Exergy fuel is primarily the mechanical exergy difference and thermal exergy at the inlet
            self.E_F = (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])

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

        # Assume no chemical exergy (chemical = 0) and massless exergy is based on power (self.P)
        self.E_bus = {"chemical": 0, "physical": 0, "massless": abs(self.P)}

        # Exergy efficiency (epsilon) calculation
        self.epsilon = self._calc_epsilon()


@component_registry
class CombustionChamber(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a turbine.
        This method overrides the base class method for the specific behavior of a turbine.
        """
        pass


@component_registry
class Generator(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a generator.
        This method overrides the base class method for the specific behavior of a turbine.
        """
        pass