import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Motor(Component):
    r"""
    Class for exergy analysis of motors.

    This class performs exergy analysis calculations for motors, converting electrical
    energy into mechanical energy. The exergy product is defined as the mechanical 
    power output, while the exergy fuel is the electrical power input.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\text{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\mathrm{P}` in :math:`\text{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\text{W}`.
    epsilon : float
        Exergetic efficiency of the component :math:`\varepsilon` in :math:`-`.
    inl : dict
        Dictionary containing inlet stream data with energy flow.
    outl : dict
        Dictionary containing outlet stream data with energy flow.

    Notes
    -----
    The exergy analysis for a motor is straightforward as both electrical and mechanical
    energy are pure exergy. The equations are:

    .. math::

        \dot{E}_\mathrm{P} & = \dot{W}_\mathrm{mech}

        \dot{E}_\mathrm{F} & = \dot{W}_\mathrm{el}

        \dot{E}_\mathrm{D} & = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}

    where:
        - :math:`\dot{W}_\mathrm{mech}`: Mechanical power output
        - :math:`\dot{W}_\mathrm{el}`: Electrical power input
    """

    def __init__(self, **kwargs):
        r"""Initialize motor component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the motor.

        Calculates the exergy product (mechanical power output), exergy fuel 
        (electrical power input), and the resulting exergy destruction and efficiency.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.
        """      
        # Exergy product is the mechanical power output
        self.E_P = self.outl[0]['energy_flow']
        
        # Exergy fuel is the electrical power input
        self.E_F = self.inl[0]['energy_flow']
        
        # Calculate exergy destruction
        self.E_D = self.E_F - self.E_P
        
        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Motor exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )