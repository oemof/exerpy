import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Generator(Component):
    r"""
    Class for exergy analysis of generators.

    This class performs exergy analysis calculations for generators, converting mechanical 
    or thermal energy flow into electrical energy. The exergy product is defined as 
    the electrical power output, while the exergy fuel is the input energy flow.

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
    The exergy analysis for a generator is straightforward as electrical energy
    is pure exergy. The equations are:

    .. math::

        \dot{E}_\mathrm{P} & = \dot{W}_\mathrm{el}

        \dot{E}_\mathrm{F} & = \dot{W}_\mathrm{in}

        \dot{E}_\mathrm{D} & = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}

    where:
        - :math:`\dot{W}_\mathrm{el}`: Electrical power output
        - :math:`\dot{W}_\mathrm{in}`: Input power
    """

    def __init__(self, **kwargs):
        r"""Initialize generator component with given parameters."""
        super().__init__(**kwargs)
        # Ex_C_col will be assigned by ExergoeconomicAnalysis.run()
        self.Ex_C_col = {}

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the generator.

        Calculates the exergy product (electrical power output), exergy fuel (input power),
        and the resulting exergy destruction and efficiency.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.
        """      
        # Exergy product is the electrical power output
        self.E_P = self.outl[0]['energy_flow']
        
        # Exergy fuel is the input power
        self.E_F = self.inl[0]['energy_flow']
        
        # Calculate exergy destruction
        self.E_D = self.E_F - self.E_P
        
        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()
        
        # Log the results
        logging.info(
            f"Generator exergy balance calculated: "
            f"Generator exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        return [A, b, counter, equations]
    
    def exergoeconomic_balance(self, T0):
        self.C_P = self.outl[0].get("C_TOT", 0)
        self.C_F = self.inl[0].get("C_TOT", 0)
        
        if self.E_P == 0 or self.E_F == 0:
            raise ValueError(f"E_P or E_F is zero; cannot compute specific costs for component: {self.name}.")
        
        self.c_P = self.C_P / self.E_P
        self.c_F = self.C_F / self.E_F
        self.C_D = self.c_F * self.E_D   # Ensure that self.E_D is computed beforehand.
        self.r = (self.C_P - self.C_F) / self.C_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) != 0 else 0
