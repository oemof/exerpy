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
    """
    Turbine component class.

    This class represents a turbine component in the system and is responsible for
    calculating the exergy balance specific to a turbine.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Turbine component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a turbine.

        This method overrides the base class method for the specific behavior of a turbine.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
        """
        # Get power flow in case it wasn't read during the parsing
        if self.P is None:
            self.P = self._total_outlet('m') * (self.inl[0]['h'] - self.outl[0]['h'])

        # Calculate exergy destruction based on the inlet and outlet temperatures
        if self.inl[0]['T'] >= T0 and self.outl[0]['T'] >= T0:
            # Case 1: Both inlet and outlet temperatures are greater than ambient temperature
            self.E_P = abs(self.P)  # Assuming P is already stored as power
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])
        elif self.inl[0]['T'] > T0 and self.outl[0]['T'] <= T0:
            # Case 2: Inlet temperature is greater than ambient, but outlet is less than or equal to ambient
            self.E_P = -self.P + self._total_outlet('m') * self.outl[0]['h']
            self.E_F = (self.inl[0]['h'] +
                        (self.inl[0]['e_PH'] - self.outl[0]['e_PH']))
        elif self.inl[0]['T'] <= T0 and self.outl[0]['T'] <= T0:
            # Case 3: Both inlet and outlet temperatures are less than or equal to ambient temperature
            self.E_P = (-self.P +
                        (+ self._total_outlet('m') * self.outl[0]['h'] - self.inl[0]['h'] * self.inl[0]['m']))
            self.E_F = (self.inl[0]['e_PH'] * self.inl[0]['m'] -
                        self.outl[0]['e_PH'] * self.outl[0]['m'])
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



@component_registry
class Compressor(Component):
    """
    Compressor component class.

    This class represents a compressor component in the system and is responsible for
    calculating the exergy balance specific to a compressor.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Compressor component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a compressor.

        This method overrides the base class method for the specific behavior of a compressor.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
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
class Pump(Component):
    """
    Pump component class.

    This class represents a pump component in the system and is responsible for
    calculating the exergy balance specific to a pump.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Pump component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a pump.

        This method overrides the base class method for the specific behavior of a pump.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
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
    """
    CombustionChamber component class.

    This class represents a combustion chamber component in the system and is responsible for
    calculating the exergy balance specific to a combustion chamber.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the CombustionChamber component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a combustion chamber.

        This method overrides the base class method for the specific behavior of a combustion chamber.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
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
    """
    Generator component class.

    This class represents a generator component in the system and is responsible for
    calculating the exergy balance specific to a generator.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Generator component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a generator.

        This method overrides the base class method for the specific behavior of a generator.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
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
class Motor(Component):
    """
    Motor component class.

    This class represents a motor component in the system and is responsible for
    calculating the exergy balance specific to a motor.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Motor component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a motor.

        This method overrides the base class method for the specific behavior of a motor.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
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
        logging.info(f"Motor balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")


@component_registry
class HeatExchanger(Component):
    """
    HeatExchanger component class.

    This class represents a heat exchanger component in the system and is responsible for
    calculating the exergy balance specific to a heat exchanger.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the HeatExchanger component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a heat exchanger.

        This method overrides the base class method for the specific behavior of a heat exchanger.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 2:
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


@component_registry
class Condenser(Component):
    """
    Condenser component class.

    This class represents a condenser component in the system and is responsible for
    calculating the exergy balance specific to a condenser.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Condenser component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a condenser.

        This method overrides the base class method for the specific behavior of a condenser.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 2:
            raise ValueError("Condenser requires two inlets and two outlets.")
        
        self.E_L = self.outl[1]['m'] * (self.outl[1]['e_PH'] - self.inl[1]['e_PH'])
        self.E_D = self.outl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH']) - self.E_L

        self.E_F = None
        self.E_P = None
        self.epsilon = None

        logging.info(f"Condenser exergy balance calculated: E_D={self.E_D}, E_L={self.E_L}")


@component_registry
class Deaerator(Component):
    """
    Deaerator component class.

    This class represents a deaerator component in the system and is responsible for
    calculating the exergy balance specific to a deaerator.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Deaerator component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a deaerator.

        This method overrides the base class method for the specific behavior of a deaerator.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Deaerator requires at least two inlets and one outlet.")

        self.E_P = 0
        self.E_F = 0
        # Check if outlet temperature is greater than T0
        if self.outl[0]['T'] > T0:
            for _, inlet in self.inl.items():  # Iterate through the dictionary values
                if inlet['T'] < self.outl[0]['T']:
                    if inlet['T'] >= T0:
                        self.E_P += inlet['m'] * (self.outl[0]['e_PH'] - inlet['e_PH'])
                    else:
                        self.E_P += inlet['m'] * self.outl[0]['e_PH']
                        self.E_F += inlet['E_PH']
                else:
                    self.E_F += inlet['m'] * (inlet['e_PH'] - self.outl[0]['e_PH'])
        # Check if outlet temperature is equal to T0
        elif self.outl[0]['T'] == T0:
            self.E_P = np.nan
            for _, inlet in self.inl.items():
                self.E_F += inlet['E_PH']
        # Handle case where outlet temperature is less than T0
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

        self.E_bus = {"chemical": np.nan, "physical": np.nan, "massless": np.nan}
        self.E_D = self.E_F - self.E_P
        self.epsilon = self._calc_epsilon()

        # Log the results
        logging.info(f"Deaerator exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")


@component_registry
class HeatConsumer(Component):
    """
    Heat consumer component class.

    This class represents a heat consumer component in the system and is responsible for
    calculating the exergy balance specific to a heat consumer.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Heat consumer component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a deaerator.

        This method overrides the base class method for the specific behavior of a heat consumer.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 1 or len(self.outl) < 1:
            raise ValueError("Heat consumer requires one inlet and one outlet.")

        self.E_F = self.inl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])

        Q_out = self.inl[0]['m'] * (self.inl[0]['h'] - self.outl[0]['h'])

        T_boundary = (self.outl[0]['h'] - self.inl[0]['h']) / (self.outl[0]['s'] - self.inl[0]['s'])  # TODO: consider the pressure drops (integrate)!

        self.E_P = Q_out * (1 - T0 / T_boundary)

        self.E_D = self.E_F - self.E_P

        self.epsilon = self._calc_epsilon()

        # Log the results
        logging.info(f"Deaerator exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")


@component_registry
class Mixer(Component):
    """
    Mixer component class.

    This class represents a mixer component in the system and is responsible for
    calculating the exergy balance specific to a mixer.

    Attributes:
        E_P (float): Exergy product (physical exergy difference between outlet and inlets).
        E_F (float): Exergy fuel (chemical exergy of fuel and air minus exhaust exergy).
        E_D (float): Exergy destruction (difference between exergy fuel and exergy product).
        epsilon (float): Exergy efficiency.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Mixer component.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a mixer.

        This method overrides the base class method for the specific behavior of a mixer.

        Args:
            T0 (float): Reference temperature.
            p0 (float): Reference pressure.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Mixer requires at least two inlets and one outlet.")

        self.E_P = 0
        self.E_F = 0
        # Check if outlet temperature is greater than T0
        if self.outl[0]['T'] > T0:
            for _, inlet in self.inl.items():  # Iterate through the dictionary values
                if inlet['T'] < self.outl[0]['T']:
                    if inlet['T'] >= T0:
                        self.E_P += inlet['m'] * (self.outl[0]['e_PH'] - inlet['e_PH'])
                    else:
                        self.E_P += inlet['m'] * self.outl[0]['e_PH']
                        self.E_F += inlet['E_PH']
                else:
                    self.E_F += inlet['m'] * (inlet['e_PH'] - self.outl[0]['e_PH'])
        # Check if outlet temperature is equal to T0
        elif self.outl[0]['T'] == T0:
            self.E_P = np.nan
            for _, inlet in self.inl.items():
                self.E_F += inlet['E_PH']
        # Handle case where outlet temperature is less than T0
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


        self.E_bus = {"chemical": np.nan, "physical": np.nan, "massless": np.nan}
        self.E_D = self.E_F - self.E_P
        self.epsilon = self._calc_epsilon()

        # Log the results
        logging.info(f"Mixer exergy balance calculated: E_P={self.E_P}, E_F={self.E_F}, E_D={self.E_D}, Efficiency={self.epsilon}")
