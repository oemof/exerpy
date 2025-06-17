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
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\mathrm{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\mathrm{P}` in :math:`\mathrm{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\mathrm{W}`.
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

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the motor.

        Calculates the exergy product (mechanical power output), exergy fuel 
        (electrical power input), and the resulting exergy destruction and efficiency.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        """      

        if self.outl[0]['energy_flow'] > self.inl[0]['energy_flow']:
            pruduct = self.inl[0]['energy_flow']
            fuel = self.outl[0]['energy_flow']
        else:
            pruduct = self.outl[0]['energy_flow']
            fuel = self.inl[0]['energy_flow']

        # Exergy product is the mechanical power output
        self.E_P = pruduct
        
        # Exergy fuel is the electrical power input
        self.E_F = fuel
        
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

    
    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the motor.
        
        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the auxiliary cost relations for the motor. Since the motor converts mechanical
        or thermal energy to electrical energy, the auxiliary equations typically enforce:
        
        - No additional auxiliary equations are needed for motors as electrical energy 
          is pure exergy and the cost balance equations are sufficient.
        
        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature.
        equations : dict
            Dictionary for storing equation labels.
        chemical_exergy_enabled : bool
            Flag indicating whether chemical exergy auxiliary equations should be added.
        
        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index.
        equations : dict
            Updated dictionary with equation labels.
        """
        return [A, b, counter, equations]
    
    def exergoeconomic_balance(self, T0):
        """
        Perform exergoeconomic balance calculations for the motor.
        
        This method calculates various exergoeconomic parameters including:
        - Cost rates of product (C_P) and fuel (C_F)
        - Specific cost of product (c_P) and fuel (c_F)
        - Cost rate of exergy destruction (C_D)
        - Relative cost difference (r)
        - Exergoeconomic factor (f)
        
        Parameters
        ----------
        T0 : float
            Ambient temperature
            
        Notes
        -----
        The exergoeconomic balance considers thermal (T), chemical (CH),
        and mechanical (M) exergy components for the inlet and outlet streams.
        """
        self.C_P = self.outl[0].get("C_TOT", 0)
        self.C_F = self.inl[0].get("C_TOT", 0)
        
        if self.E_P == 0 or self.E_F == 0:
            raise ValueError(f"E_P or E_F is zero; cannot compute specific costs for component: {self.name}.")
        
        self.c_P = self.C_P / self.E_P
        self.c_F = self.C_F / self.E_F
        self.C_D = self.c_F * self.E_D   # Ensure that self.E_D is computed beforehand.
        self.r = (self.C_P - self.C_F) / self.C_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) != 0 else 0
