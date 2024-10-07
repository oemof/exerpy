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
        # Get power flow in case it wasn't read during the parsing
        if self.P is None:
            self.P = self.outl[0]['m'] * (self.inl[0]['h'] - self.outl[0]['h'])
            # TODO in case of more outlet change the code

        # Calculate exergy destruction based on the inlet and outlet temperatures
        if self.inl[0]['T'] >= T0 and self.outl[0]['T'] >= T0:
            # Case 1: Both inlet and outlet temperatures are greater than ambient temperature
            self.E_P = abs(self.P)  # Assuming P is already stored as power
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

        # Exergy efficiency (epsilon) calculation
        self.epsilon = self._calc_epsilon()


@component_registry
class CombustionChamber(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a combustion chamber.

        Parameters:
        T0 (float): Ambient temperature in Kelvin.
        p0 (float): Ambient pressure in Pascal.
        """
        # Check for necessary inlet and outlet data
        if not hasattr(self, 'inl') or not hasattr(self, 'outl') or len(self.inl) < 2 or len(self.outl) < 1:
            msg = "Combustion chamber requires two inlets (fuel and air) and one outlet (exhaust)."
            logging.error(msg)
            raise ValueError(msg)
        
        # Exergy product (physical exergy difference between outlet and inlets)
        self.E_P = self.outl[0]['m'] * self.outl[0]['e_PH'] - (self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'])

        # Exergy fuel (chemical exergy of fuel and air minus exhaust exergy)
        self.E_F = (self.inl[0]['m'] * self.inl[0]['e_CH'] + self.inl[1]['m'] * self.inl[1]['e_CH']) - self.outl[0]['m'] * self.outl[0]['e_CH']

        # Exergy destruction (difference between exergy fuel and exergy product)
        self.E_D = self.E_F - self.E_P

        # Exergy efficiency (epsilon)
        self.epsilon = self._calc_epsilon()

        # Log the results
        logging.info(f"Combustion Chamber Exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")

@component_registry
class Generator(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a generator.
        This method overrides the base class method for the specific behavior of a generator.
        """
        # Exergy product (physical exergy difference between outlet and inlets)
        self.E_P = self.outl[0]['energy_flow']

        # Exergy fuel (chemical exergy of fuel and air minus exhaust exergy)
        self.E_F = self.inl[0]['energy_flow']

        # Exergy destruction (difference between exergy fuel and exergy product)
        self.E_D = self.E_F - self.E_P

        # Exergy efficiency (epsilon)
        self.epsilon = self._calc_epsilon()

        # Log the results
        logging.info(f"Generator balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")


@component_registry
class HeatExchanger(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a heat exchanger.
        
        Parameters:
        T0 (float): Ambient temperature in Kelvin.
        p0 (float): Ambient pressure in Pascal.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) != 2 or len(self.outl) != 2:
            raise ValueError("Heat exchanger requires two inlets and two outlets.")

        # Access the streams via .values() to iterate over the actual stream data
        all_streams = list(self.inl.values()) + list(self.outl.values())

        # Case 1: All streams are above the ambient temperature
        if all([stream['T'] > T0 for stream in all_streams]):
            self.E_P = self.outl[1]['m'] * self.outl[1]['e_T'] - self.inl[1]['m'] * self.inl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_M'] - self.outl[1]['m'] * self.outl[1]['e_M'])

        # Case 2: All streams are below or equal to the ambient temperature
        elif all([stream['T'] <= T0 for stream in all_streams]):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] - self.inl[0]['m'] * self.inl[0]['e_T']
            self.E_F = self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'] + (
                self.inl[0]['m'] * self.inl[0]['e_M'] - self.outl[0]['m'] * self.outl[0]['e_M'])

        # Case 3: Some streams are above and others below ambient temperature
        elif (self.inl[0]['T'] > T0 and self.outl[1]['T'] > T0 and
              self.outl[0]['T'] <= T0 and self.inl[1]['T'] <= T0):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] + self.outl[1]['m'] * self.outl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'] - (
                self.outl[0]['m'] * self.outl[0]['e_M'] + self.outl[1]['m'] * self.outl[1]['e_M'])

        # Case 4: First inlet is above ambient, others below or equal
        elif (self.inl[0]['T'] > T0 and self.inl[1]['T'] <= T0 and
              self.outl[0]['T'] <= T0 and self.outl[1]['T'] <= T0):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'] - (
                self.outl[1]['m'] * self.outl[1]['e_PH'] + self.outl[0]['m'] * self.outl[0]['e_M'])

        # Case 5: Inlets are higher but outlets are below or equal to ambient
        elif (self.inl[0]['T'] > T0 and self.outl[0]['T'] > T0 and
              self.inl[1]['T'] <= T0 and self.outl[1]['T'] <= T0):
            self.E_P = np.nan
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'])

        # Case 6: One outlet is above ambient, others lower
        else:
            self.E_P = self.outl[1]['m'] * self.outl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_M'])

        # Calculate exergy destruction and efficiency
        self.E_bus = {"chemical": np.nan, "physical": np.nan, "massless": np.nan}
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P
        self.epsilon = self._calc_epsilon()

        logging.info(f"Heat Exchanger exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")
