

def component_registry(type):
    component_registry.items[type.__name__] = type
    return type


component_registry.items = {}


@component_registry
class Component:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance for an individual component.
        """
        pass

@component_registry
class Turbine(Component):

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        """
        Calculate exergy balance of a turbine.
        """
        pass
