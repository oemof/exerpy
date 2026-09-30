from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


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

        if self.outl[0]["energy_flow"] > self.inl[0]["energy_flow"]:
            pruduct = self.inl[0]["energy_flow"]
            fuel = self.outl[0]["energy_flow"]
        else:
            pruduct = self.outl[0]["energy_flow"]
            fuel = self.inl[0]["energy_flow"]

        # Exergy product is the mechanical power output
        self.E_P = pruduct

        # Exergy fuel is the electrical power input
        self.E_F = fuel

        # Calculate exergy destruction
        self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logger.info(
            f"Exergy balance of Motor {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the motor.

        The motor converts electrical power into shaft power. Both streams are power, each carrying one cost variable, and the
        outlet is the only one the component produces, so the cost balance alone determines it:

        .. math::

            \dot{C}^\mathrm{TOT}_\mathrm{out}
            = \dot{C}^\mathrm{TOT}_\mathrm{in} + \dot{Z}

        No auxiliary equation is therefore written, and the split of the physical exergy does not
        apply: it concerns material streams only, and this component has none.

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
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

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

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform exergoeconomic cost balance for the motor (power-consuming component).

        The motor is a power-consuming component (e.g., electric motor, pump motor)
        where mechanical/electrical work is consumed to drive a process. The general
        exergoeconomic balance equation is:

        .. math::
            \dot{C}_{\mathrm{in}}^{\mathrm{TOT}} - \dot{C}_{\mathrm{out}}^{\mathrm{TOT}}
            + \dot{C}_{\mathrm{W}} + \dot{Z} = 0

        For a motor, the fuel is the input stream (typically electrical power),
        and the product is the output stream (mechanical work or driven fluid):

        .. math::
            \dot{C}_{\mathrm{F}} = \dot{C}_{\mathrm{in}}^{\mathrm{TOT}}

        .. math::
            \dot{C}_{\mathrm{P}} = \dot{C}_{\mathrm{out}}^{\mathrm{TOT}}

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
            Default is False.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

        Attributes Set
        --------------
        C_P : float
            Cost rate of product (currency/time).
        C_F : float
            Cost rate of fuel (currency/time).
        c_P : float
            Specific cost of product (currency/energy).
        c_F : float
            Specific cost of fuel (currency/energy).
        C_D : float
            Cost rate of exergy destruction (currency/time).
        r : float
            Relative cost difference (dimensionless).
        f : float
            Exergoeconomic factor (dimensionless).

        Raises
        ------
        ValueError
            If E_P or E_F is zero, preventing computation of specific costs.

        Notes
        -----
        The motor is a power-consuming component, opposite in function to a generator.
        Unlike heat exchangers or pumps, the motor does not add Z_costs to close the
        cost balance in the C_P calculation. The cost balance is determined by
        the total exergy costs of inlet and outlet streams.

        The relative cost difference r is calculated using total cost rates
        (C_P and C_F) rather than specific costs (c_P and c_F), which is
        mathematically equivalent for this component type.

        The exergy destruction E_D must be computed prior to calling this method.

        For motors coupled with pumps or compressors, the fuel is typically the
        electrical energy consumed, and the product is the mechanical work delivered
        to the driven equipment.
        """
        self.C_P = self.outl[0].get("C_TOT", 0)
        self.C_F = self.inl[0].get("C_TOT", 0)

        if self.E_P == 0 or self.E_F == 0:
            raise ValueError(f"E_P or E_F is zero; cannot compute specific costs for component: {self.name}.")

        self.c_P = self.C_P / self.E_P
        self.c_F = self.C_F / self.E_F
        self.C_D = self.c_F * self.E_D  # Ensure that self.E_D is computed beforehand.
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) != 0 else 0
