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
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def exergoeconomic_balance(self, T0: float) -> None:
        """        
        Calculate the exergoeconomic balance of the generator.

        This function calculates:
        - C_P: Cost flow associated with the product exergy (electrical power output)
        - C_F: Cost flow associated with the fuel exergy (input power)
        - c_F: Specific cost for fuel exergy [currency / W]
        - c_P: Specific cost for product exergy [currency / W]
        - C_D: Cost flow of exergy destruction (always 0 for Generator)
        - r: Relative cost difference
        - f: Exergoeconomic factor

        Requires:
        - self.inl[0] and self.outl[0] must have 'energy_flow' defined
        - self.Z_costs must be set beforehand (e.g., by ExergoeconomicAnalysis)
        - self.E_F, self.E_P already computed by calc_exergy_balance
        """
        # Calculate cost flows
        # C_P: Cost associated with product exergy (electrical output)
        self.C_P = self.E_P * self.c_P if hasattr(self, 'c_P') else 0.0

        # C_F: Cost associated with fuel exergy (mechanical input)
        # Since C_F = C_P + Z_costs
        self.C_F = self.C_P + self.Z_costs

        # Calculate specific costs
        self.c_F = self.C_F / self.E_F if self.E_F and self.E_F > 1e-12 else 0.0
        self.c_P = self.C_P / self.E_P if self.E_P and self.E_P > 1e-12 else 0.0

        # Relative cost difference
        self.r = ((self.c_P - self.c_F) / self.c_F) if self.c_F else 0.0

        # Exergoeconomic factor
        Z = self.Z_costs
        denom = Z + self.C_D if self.C_D else Z
        self.f = (Z / denom) if denom != 0.0 else 0.0

        # Log the results
        logging.info(
            f"Generator '{self.label}' exergoeconomic calculations: "
            f"C_P={self.C_P:.2f}, C_F={self.C_F:.2f}, C_D={self.C_D:.2f}, "
            f"c_F={self.c_F:.4f}, c_P={self.c_P:.4f}, r={self.r:.4f}, f={self.f:.4f}"
        )

    def aux_eqs(self, A, b, counter, T0, equations):
        return [A, b, counter, equations]