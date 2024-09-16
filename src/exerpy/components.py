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


@component_registry
class Turbine(Component):
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a turbine.

        Parameters:
        T0 (float): Ambient temperature in Kelvin.
        p0 (float): Ambient pressure in Pascal.
        """
        # Access the inlet and outlet temperature from the fluid_properties
        T_in = self.inl[0]['fluid_properties']['temperature']
        T_out = self.outl[0]['fluid_properties']['temperature']

        # Calculate exergy destruction based on the inlet and outlet temperatures
        if T_in >= T0 and T_out >= T0:
            # Case 1: Both inlet and outlet temperatures are greater than ambient temperature
            self.E_P = -self.P  # Assuming P is already stored as power or a similar attribute
            self.E_F = (self.inl[0]['fluid_properties']['physical_exergy'] -
                        self.outl[0]['fluid_properties']['physical_exergy'])
        elif T_in > T0 and T_out <= T0:
            # Case 2: Inlet temperature is greater than ambient, but outlet is less than or equal to ambient
            self.E_P = -self.P + self.outl[0]['fluid_properties']['enthalpy']
            self.E_F = (self.inl[0]['fluid_properties']['enthalpy'] +
                        (self.inl[0]['fluid_properties']['physical_exergy'] - self.outl[0]['fluid_properties']['physical_exergy']))
        elif T_in <= T0 and T_out <= T0:
            # Case 3: Both inlet and outlet temperatures are less than or equal to ambient temperature
            self.E_P = (-self.P +
                        (self.outl[0]['fluid_properties']['enthalpy'] - self.inl[0]['fluid_properties']['enthalpy']))
            self.E_F = (self.inl[0]['fluid_properties']['physical_exergy'] -
                        self.outl[0]['fluid_properties']['physical_exergy'])
        else:
            # Invalid case: if outlet temperature is larger than inlet temperature
            msg = ('Exergy balance of a turbine where outlet temperature is '
                'larger than inlet temperature is not implemented.')
            logging.warning(msg)
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_bus = {"chemical": 0, "physical": 0, "massless": -self.P}  # Adjust as needed
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
        pass


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