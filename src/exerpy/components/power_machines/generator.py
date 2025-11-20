import logging

from exerpy.components.component import Component, component_registry


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

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the generator.

        Calculates the exergy product (electrical power output), exergy fuel (input power),
        and the resulting exergy destruction and efficiency.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        """
        # Exergy product is the electrical power output
        self.E_P = self.outl[0]["energy_flow"]

        # Exergy fuel is the input power
        self.E_F = self.inl[0]["energy_flow"]

        # Calculate exergy destruction
        self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Exergy balance of Generator {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the generator.

        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the auxiliary cost relations for the generator. Since the generator converts mechanical
        or thermal energy to electrical energy, the auxiliary equations typically enforce:

        - No additional auxiliary equations are needed for generators as electrical energy
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

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""
        Perform exergoeconomic cost balance for the generator (power-producing component).

        The generator is a power-producing component (e.g., electrical generator, turbine)
        where mechanical/electrical work is extracted from a flowing stream. The general
        exergoeconomic balance equation is:

        .. math::
            \dot{C}_{\mathrm{in}}^{\mathrm{TOT}} - \dot{C}_{\mathrm{out}}^{\mathrm{TOT}}
            - \dot{C}_{\mathrm{P}} + \dot{Z} = 0

        For a generator, the product is the power output (electrical or mechanical),
        and the fuel is the exergy decrease in the working fluid:

        .. math::
            \dot{C}_{\mathrm{P}} = \dot{C}_{\mathrm{out}}^{\mathrm{TOT}}

        .. math::
            \dot{C}_{\mathrm{F}} = \dot{C}_{\mathrm{in}}^{\mathrm{TOT}}

        **Calculated exergoeconomic indicators:**

        Specific cost of fuel:

        .. math::
            c_{\mathrm{F}} = \frac{\dot{C}_{\mathrm{F}}}{\dot{E}_{\mathrm{F}}}

        Specific cost of product:

        .. math::
            c_{\mathrm{P}} = \frac{\dot{C}_{\mathrm{P}}}{\dot{E}_{\mathrm{P}}}

        Cost rate of exergy destruction:

        .. math::
            \dot{C}_{\mathrm{D}} = c_{\mathrm{F}} \cdot \dot{E}_{\mathrm{D}}

        Relative cost difference:

        .. math::
            r = \frac{\dot{C}_{\mathrm{P}} - \dot{C}_{\mathrm{F}}}{\dot{C}_{\mathrm{F}}}

        Exergoeconomic factor:

        .. math::
            f = \frac{\dot{Z}}{\dot{Z} + \dot{C}_{\mathrm{D}}}

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
            Default is False.

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
        Unlike other components, the generator does not add Z_costs to close the
        cost balance in the C_P calculation. The cost balance is determined by
        the total exergy costs of inlet and outlet streams.

        The relative cost difference r is calculated using total cost rates
        (C_P and C_F) rather than specific costs (c_P and c_F), which is
        mathematically equivalent for this component type.

        The exergy destruction E_D must be computed prior to calling this method.
        """
        self.C_P = self.outl[0].get("C_TOT", 0)
        self.C_F = self.inl[0].get("C_TOT", 0)

        if self.E_P == 0 or self.E_F == 0:
            raise ValueError(f"E_P or E_F is zero; cannot compute specific costs for component: {self.name}.")

        self.c_P = self.C_P / self.E_P
        self.c_F = self.C_F / self.E_F
        self.C_D = self.c_F * self.E_D  # Ensure that self.E_D is computed beforehand.
        self.r = (self.C_P - self.C_F) / self.C_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) != 0 else 0
