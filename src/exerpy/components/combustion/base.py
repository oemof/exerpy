from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class CombustionChamber(Component):
    r"""
    Class for exergy and exergoeconomic analysis of combustion chambers.

    This class performs exergy and exergoeconomic analysis calculations for combustion chambers,
    considering both thermal and mechanical exergy flows, as well as chemical exergy flows.
    The combustion gas leaves at outlet 0. With split physical exergy, the exergy product is the
    increase of the thermal exergy from all inlets to the combustion gas and the exergy fuel the
    decrease of the chemical and the mechanical exergy. Without the split, the product is the
    increase of the physical exergy and the fuel the decrease of the chemical exergy. Every further
    material outlet, such as ash or slag, is no product of the chamber: its exergy is subtracted from
    the fuel and it takes the cost per exergy unit of the fuel stream, wherever it goes next.

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
        Dictionary containing inlet stream data with mass flows and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with mass flows and specific exergies.
    Z_costs : float
        Investment cost rate of the component in currency/h.
    C_P : float
        Cost of product stream :math:`\dot{C}_P` in currency/h.
    C_F : float
        Cost of fuel stream :math:`\dot{C}_F` in currency/h.
    C_D : float
        Cost of exergy destruction :math:`\dot{C}_D` in currency/h.
    c_P : float
        Specific cost of product stream (currency per unit exergy).
    c_F : float
        Specific cost of fuel stream (currency per unit exergy).
    r : float
        Relative cost difference, :math:`(c_P - c_F)/c_F`.
    f : float
        Exergoeconomic factor, :math:`\dot{Z}/(\dot{Z} + \dot{C}_D)`.
    Ex_C_col : dict
        Custom cost coefficients collection passed via `kwargs`.

    Notes
    -----
    This component requires the calculation of both physical and chemical exergy.
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the combustion chamber component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate (currency/h), default 0.0
        """
        super().__init__(**kwargs)
        # Initialize additional attributes if necessary
        self.Ex_C_col = kwargs.get("Ex_C_col", {})
        self.Z_costs = kwargs.get("Z_costs", 0.0)  # Cost rate in currency/h

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the combustion chamber.

        The sums over :math:`\mathrm{in}` run over all inlets. The combustion gas leaves at outlet 0;
        every further outlet :math:`\mathrm{A}`, such as ash or slag, is no product. As for the ash of
        a gasification reactor, its exergy is subtracted from the fuel, whether it leaves the plant or is
        used further downstream. With split physical exergy, the thermal exergy of fuel and oxidant is raised
        (product) at the expense of their chemical and mechanical exergy (fuel):

        .. math::
            \dot{E}_\mathrm{P} = \dot{E}^{\mathrm{T}}_{\mathrm{gas}}
                               - \sum \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::
            \dot{E}_\mathrm{F} = \Bigl(\sum \dot{E}^{\mathrm{CH}}_{\mathrm{in}}
                                       - \dot{E}^{\mathrm{CH}}_{\mathrm{gas}}\Bigr)
                               + \Bigl(\sum \dot{E}^{\mathrm{M}}_{\mathrm{in}}
                                       - \dot{E}^{\mathrm{M}}_{\mathrm{gas}}\Bigr)
                               - \sum_\mathrm{A} \bigl(\dot{E}^{\mathrm{T}}_{\mathrm{A}}
                                       + \dot{E}^{\mathrm{M}}_{\mathrm{A}}
                                       + \dot{E}^{\mathrm{CH}}_{\mathrm{A}}\bigr)

        Without the split:

        .. math::
            \dot{E}_\mathrm{P} = \dot{E}^{\mathrm{PH}}_{\mathrm{gas}}
                               - \sum \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::
            \dot{E}_\mathrm{F} = \sum \dot{E}^{\mathrm{CH}}_{\mathrm{in}}
                               - \dot{E}^{\mathrm{CH}}_{\mathrm{gas}}
                               - \sum_\mathrm{A} \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{A}}
                                       + \dot{E}^{\mathrm{CH}}_{\mathrm{A}}\bigr)

        The exergy destruction :math:`\dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}`
        is the same in both cases: the total exergy of all inlets less that of all outlets.

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        p0 : float
            Ambient pressure (Pa).
        split_physical_exergy : bool
            Whether to split thermal and mechanical exergy.

        Raises
        ------
        ValueError
            If fewer than two inlets or no outlets are defined, if a stream is no material stream, if
            outlet 0 is missing or if a stream has no chemical exergy.
        """
        # Check for necessary inlet and outlet data
        if not hasattr(self, "inl") or not hasattr(self, "outl") or len(self.inl) < 2 or len(self.outl) < 1:
            msg = "CombustionChamber requires at least two inlets (air and fuel) and one outlet (exhaust)."
            logger.error(msg)
            raise ValueError(msg)
        for direction, streams in (("inlet", self.inl), ("outlet", self.outl)):
            for idx, stream in streams.items():
                kind = stream.get("kind", "material")
                if kind != "material":
                    msg = (
                        f"The combustion chamber {self.name} has a stream of kind '{kind}' at {direction} {idx}. "
                        "Only material streams are supported: the combustion gas at outlet 0 and ash or slag "
                        "at further outlets. Heat outputs such as wall heat or irradiation are not."
                    )
                    logger.error(msg)
                    raise ValueError(msg)
        if 0 not in self.outl:
            msg = f"The combustion chamber {self.name} needs its combustion gas at outlet 0."
            logger.error(msg)
            raise ValueError(msg)
        if any(stream.get("e_CH") is None for stream in (*self.inl.values(), *self.outl.values())):
            msg = (
                f"The combustion chamber {self.name} needs the chemical exergy of its streams. Pass chemExLib "
                "(e.g. chemExLib='Ahrendts') to the analysis or give e_CH for every stream."
            )
            logger.error(msg)
            raise ValueError(msg)

        forms = ("T", "M", "CH") if split_physical_exergy else ("PH", "CH")
        E_ash = sum(stream["m"] * stream[f"e_{form}"] for stream in self._ash_outlets() for form in forms)
        if split_physical_exergy:
            self.E_P = self._exergy_increase("T")
            self.E_F = -self._exergy_increase("CH") - self._exergy_increase("M") - E_ash
        else:
            self.E_P = self._exergy_increase("PH")
            self.E_F = -self._exergy_increase("CH") - E_ash

        # Exergy destruction (difference between exergy fuel and exergy product)
        self.E_D = self.E_F - self.E_P

        # Exergetic efficiency (epsilon)
        self.epsilon = self.calc_epsilon()

        # Log the results
        logger.info(
            f"Exergy balance of CombustionChamber {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def _exergy_increase(self, form):
        """Exergy flow of one form (``"T"``, ``"M"``, ``"PH"`` or ``"CH"``) of the combustion gas minus all inlets."""
        gas = self.outl[0]
        return gas["m"] * gas[f"e_{form}"] - sum(stream["m"] * stream[f"e_{form}"] for stream in self.inl.values())

    def _cost_increase(self, form):
        """Cost rate of one exergy form of the combustion gas minus all inlets."""
        return self.outl[0][f"C_{form}"] - sum(stream[f"C_{form}"] for stream in self.inl.values())

    def _ash_outlets(self):
        """Outlets other than the combustion gas, such as ash or slag."""
        return [stream for idx, stream in self.outl.items() if idx != 0]

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Add auxiliary cost equations for the combustion chamber.

        The hot gas leaving the chamber at outlet 0 is the product, so the cost of its thermal exergy
        is left to the cost balance. What the chamber does not raise is blended: the gas takes the
        mass-weighted mean of the specific costs of all inlets (F-principle).

        **With split physical exergy** the rule is written for the mechanical exergy; **without the
        split** the stream carries a single cost variable for its physical exergy, that variable is
        the product, and no mechanical rule exists. The cost balance determines it:

        .. math::

            \dot{C}^\mathrm{PH}_\mathrm{gas} + \dot{C}^\mathrm{CH}_\mathrm{gas}
            + \sum_\mathrm{A} \bigl(\dot{C}^\mathrm{PH}_\mathrm{A} + \dot{C}^\mathrm{CH}_\mathrm{A}\bigr)
            = \sum_{i} \bigl(\dot{C}^\mathrm{PH}_{\mathrm{in},i} + \dot{C}^\mathrm{CH}_{\mathrm{in},i}\bigr)
            + \dot{Z}

        The chemical rule is written in either mode, and a combustion chamber needs the chemical
        exergy to be enabled at all, since the fuel enters as chemical exergy.

        For :math:`x = \mathrm{M}` (only with split physical exergy) and :math:`x = \mathrm{CH}`, the
        rule :math:`\dot m_\mathrm{gas}\,c^{x}_\mathrm{gas} = \sum_{i} \dot m_{i}\,c^{x}_{\mathrm{in},i}`
        over all inlets :math:`i` is written into the matrix as

        .. math::
            -\frac{1}{\dot{E}^{x}_{\mathrm{gas}}}\,\dot{C}^{x}_{\mathrm{gas}}
            + \sum_{i} \frac{\dot m_{i}}{\sum_{j} \dot m_{j}}
              \frac{1}{\dot{E}^{x}_{\mathrm{in},i}}\,\dot{C}^{x}_{\mathrm{in},i}
            = 0

        An inlet without exergy of the form :math:`x` brings no cost of it and is left out of the sum.
        If the gas has no exergy of the form :math:`x`, the row sets its cost to zero,
        :math:`\dot{C}^{x}_{\mathrm{gas}} = 0`.

        Every further outlet :math:`\mathrm{A}`, such as ash or slag, takes the
        cost per exergy unit of the fuel stream, the inlet with the largest chemical exergy flow
        (F-principle). For each of its exergy forms :math:`x` (T, M and CH with split physical
        exergy, PH and CH without):

        .. math::
            \frac{\dot{C}^{x}_{\mathrm{A}}}{\dot{E}^{x}_{\mathrm{A}}}
            = \frac{\sum_{y} \dot{C}^{y}_{\mathrm{fuel}}}{\sum_{y} \dot{E}^{y}_{\mathrm{fuel}}}

        If the ash has no exergy of the form :math:`x`, the row sets
        :math:`\dot{C}^{x}_{\mathrm{A}} = 0`.

        Parameters
        ----------
        A : numpy.ndarray
            Current cost matrix.
        b : numpy.ndarray
            Current RHS vector.
        counter : int
            Starting row index.
        T0 : float
            Ambient temperature.
        equations : dict or list
            Structure for equation labels.
        chemical_exergy_enabled : bool
            Must be True to include chemical exergy mixing.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

        Returns
        -------
        A : numpy.ndarray
            Updated cost matrix.
        b : numpy.ndarray
            Updated RHS vector.
        counter : int
            Updated row index.
        equations : dict or list
            Updated labels.

        Raises
        ------
        ValueError
            If chemical_exergy_enabled is False.
        """
        # For the combustion chamber, chemical exergy is mandatory.
        if not chemical_exergy_enabled:
            raise ValueError(
                "Chemical exergy is mandatory for the combustion chamber. "
                "Please make sure that your exergy analysis considers the chemical exergy."
            )

        inlets = list(self.inl.values())
        gas = self.outl[0]
        m_in = sum(inlet["m"] for inlet in inlets)
        names = [self.name] + [inlet["name"] for inlet in inlets] + [gas["name"]]

        # Without the split the cost balance alone determines the cost of the physical exergy of the
        # gas, so only the chemical mixing rule is needed.
        for label in ("M", "CH") if split_physical_exergy else ("CH",):
            E = f"E_{label}"
            if gas[E] != 0:
                A[counter, gas["CostVar_index"][label]] = -1 / gas[E]
                for inlet in inlets:
                    # An inlet without exergy of this form brings no cost of it.
                    if inlet[E] != 0:
                        A[counter, inlet["CostVar_index"][label]] = inlet["m"] / (m_in * inlet[E])
            else:
                A[counter, gas["CostVar_index"][label]] = 1
            b[counter] = 0
            equations[counter] = {"kind": "aux_mixing", "objects": names, "property": f"c_{label}"}
            counter += 1

        # Ash takes the cost per exergy unit of the fuel stream, the inlet with the most chemical exergy.
        labels = ("T", "M", "CH") if split_physical_exergy else ("PH", "CH")
        fuel = max(inlets, key=lambda inlet: inlet["E_CH"])
        for ash in self._ash_outlets():
            E_fuel = sum(fuel[f"E_{label}"] for label in labels)
            for label in labels:
                E = ash[f"E_{label}"]
                if E != 0:
                    A[counter, ash["CostVar_index"][label]] = 1 / E
                    for fuel_label in labels:
                        A[counter, fuel["CostVar_index"][fuel_label]] = -1 / E_fuel
                else:
                    A[counter, ash["CostVar_index"][label]] = 1
                b[counter] = 0
                equations[counter] = {
                    "kind": "aux_f_rule",
                    "objects": [self.name, fuel["name"], ash["name"]],
                    "property": f"c_{label}",
                }
                counter += 1

        return [A, b, counter, equations]

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform exergoeconomic cost balance for the combustion chamber.

        .. math::
            \sum_{i} \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{in},i} + \dot{C}^{\mathrm{CH}}_{\mathrm{in},i}\bigr)
            - \dot{C}^{\mathrm{PH}}_{\mathrm{gas}} - \dot{C}^{\mathrm{CH}}_{\mathrm{gas}}
            - \sum_\mathrm{A} \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{A}} + \dot{C}^{\mathrm{CH}}_{\mathrm{A}}\bigr)
            + \dot{Z} = 0

        This method computes cost coefficients and ratios. Fuel and product take the same exergy
        forms as in :meth:`calc_exergy_balance`: the combustion gas at outlet 0 against all inlets,
        with the further outlets :math:`\mathrm{A}` such as ash subtracted from the
        fuel, so that :math:`\dot{C}_\mathrm{P} = \dot{C}_\mathrm{F} + \dot{Z}`. With split
        physical exergy:

        .. math::
            \dot{C}_\mathrm{P} = \dot{C}^{\mathrm{T}}_{\mathrm{gas}}
                               - \sum \dot{C}^{\mathrm{T}}_{\mathrm{in}}

        .. math::
            \dot{C}_\mathrm{F} = \Bigl(\sum \dot{C}^{\mathrm{CH}}_{\mathrm{in}}
                                       - \dot{C}^{\mathrm{CH}}_{\mathrm{gas}}\Bigr)
                               + \Bigl(\sum \dot{C}^{\mathrm{M}}_{\mathrm{in}}
                                       - \dot{C}^{\mathrm{M}}_{\mathrm{gas}}\Bigr)
                               - \sum_\mathrm{A} \bigl(\dot{C}^{\mathrm{T}}_{\mathrm{A}}
                                       + \dot{C}^{\mathrm{M}}_{\mathrm{A}}
                                       + \dot{C}^{\mathrm{CH}}_{\mathrm{A}}\bigr)

        Without the split:

        .. math::
            \dot{C}_\mathrm{P} = \dot{C}^{\mathrm{PH}}_{\mathrm{gas}}
                               - \sum \dot{C}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::
            \dot{C}_\mathrm{F} = \sum \dot{C}^{\mathrm{CH}}_{\mathrm{in}}
                               - \dot{C}^{\mathrm{CH}}_{\mathrm{gas}}
                               - \sum_\mathrm{A} \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{A}}
                                       + \dot{C}^{\mathrm{CH}}_{\mathrm{A}}\bigr)

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """
        forms = ("T", "M", "CH") if split_physical_exergy else ("PH", "CH")
        C_ash = sum(stream[f"C_{form}"] for stream in self._ash_outlets() for form in forms)
        if split_physical_exergy:
            self.C_P = self._cost_increase("T")
            self.C_F = -self._cost_increase("CH") - self._cost_increase("M") - C_ash
        else:
            self.C_P = self._cost_increase("PH")
            self.C_F = -self._cost_increase("CH") - C_ash
        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
