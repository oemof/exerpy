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