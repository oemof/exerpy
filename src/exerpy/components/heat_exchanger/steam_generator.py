import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class SteamGenerator(Component):
    r"""
    Class for exergy and exergoeconomic analysis of heat exchangers.

    This class performs exergy and exergoeconomic analysis calculations for heat exchanger components,
    accounting for two inlet and two outlet streams across various temperature regimes, including
    above and below ambient temperature, and optional dissipative behavior.

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

    T_hot : float
        Temperature of the heat source :math:`T_\mathrm{hot}` in :math:`\mathrm{K}`.

    Notes
    -----
    The component has several input and output streams as follows.

    Inlet streams:

    - inl[0]: Feed water inlet (high pressure)
    - inl[1]: Steam inlet (intermediate pressure)
    - inl[2]: Heat inlet (providing the heat input Q)
    - inl[3]: Water injection (high pressure)
    - inl[4]: Water injection (intermediate pressure)

    Outlet streams:

    - outl[0]: Superheated steam outlet (high pressure)
    - outl[1]: Superheated steam outlet (intermediate pressure)
    - outl[2]: Drain / Blow down outlet

    The heat inlet is picked by its kind rather than by its index, so it may sit on any connector,
    and every material inlet that is neither the feed water nor the steam inlet is a water
    injection. The heat source of a steam generator is usually outside of the model, so its
    temperature is not known from the streams and has to be given as ``T_hot``.
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the steam generator component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - T_hot (float): temperature of the heat source in K
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate in currency/h, default 0.0
        """
        super().__init__(**kwargs)
        self.T_hot = kwargs.get("T_hot")

    def _streams(self):
        """Return the streams of the steam generator, grouped by their role.

        The roles follow the connector indices documented for the class. The heat inlet is picked
        by its kind rather than by its index, and every material inlet that is neither the feed
        water nor the steam inlet is a water injection.
        """
        heat_inlets = [c for c in self.inl.values() if c is not None and c.get("kind") == "heat"]
        for idx in (0,):
            if idx not in self.inl:
                raise ValueError(f"Missing inlet stream with index {idx}.")
        for idx in (0, 2):
            if idx not in self.outl:
                raise ValueError(f"Missing outlet stream with index {idx}.")

        injections = [
            c
            for key, c in sorted(self.inl.items())
            if key not in (0, 1) and c is not None and c.get("kind", "material") == "material"
        ]
        return {
            "heat": heat_inlets[0] if heat_inlets else None,
            "feed_water": self.inl[0],
            "steam_inlet": self.inl.get(1),
            "injections": injections,
            "steam_HP": self.outl[0],
            "steam_IP": self.outl.get(1),
            "drain": self.outl[2],
        }

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the steam generator.

        The fuel is the exergy of the heat entering the component,

        .. math::
            \dot{E}_{\mathrm{F}} = \dot{Q} \cdot \left(1 - \frac{T_0}{T_\mathrm{hot}}\right)

        with :math:`T_\mathrm{hot}` the temperature of the heat source, which the component takes
        from its ``T_hot`` attribute. The heat source of a steam generator is usually outside of the
        model, so that temperature is not known from the streams and has to be given.

        The product is the physical exergy the water and steam streams gain,

        .. math::

            \dot{E}_\mathrm{P} = \Bigl[ \dot E^{\mathrm{PH}}_{\mathrm{out,HP}}
            - \dot E^{\mathrm{PH}}_{\mathrm{in,HP}} \Bigr]
            + \Bigl[ \dot E^{\mathrm{PH}}_{\mathrm{out,IP}}
            - \dot E^{\mathrm{PH}}_{\mathrm{in,IP}} \Bigr]
            - \sum \dot E^{\mathrm{PH}}_{\mathrm{w}}

        where the subscripts HP and IP denote the high and the intermediate pressure streams and w
        the water injections. The drain is not part of the product, so its exergy is counted as
        destruction, together with the losses of the component.

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        p0 : float
            Ambient pressure (Pa).
        split_physical_exergy : bool
            Whether to split thermal and mechanical exergy. The fuel and the product of this
            component are the same either way.

        Raises
        ------
        ValueError
            If required inlets or outlets are missing.

        Notes
        -----
        Without ``T_hot`` the fuel cannot be evaluated from the heat, and the thermal exergy the
        water and steam streams gain is used instead. That makes the fuel of the component an
        approximation of itself: with split physical exergy it exceeds the product by the
        mechanical exergy alone, and without the split the two are equal and the exergy destruction
        is zero. The component warns in that case.
        """
        s = self._streams()

        def E_PH(stream):
            return 0.0 if stream is None else stream.get("m", 0) * stream.get("e_PH", 0)

        E_P_HP = E_PH(s["steam_HP"]) - E_PH(s["feed_water"])
        E_P_IP = E_PH(s["steam_IP"]) - E_PH(s["steam_inlet"])
        self.E_P = E_P_HP + E_P_IP - sum(E_PH(w) for w in s["injections"])

        if s["heat"] is not None and self.T_hot:
            Q = abs(s["heat"].get("energy_flow") or 0.0)
            self.E_F = Q * (1 - T0 / self.T_hot)
        else:
            logger.warning(
                f"Steam generator {self.name} has no heat source temperature T_hot, so its exergy "
                f"fuel is approximated by the thermal exergy the water and steam streams gain. Its "
                f"exergy destruction is then too small, and zero without split physical exergy."
            )
            exergy_type = "e_T" if split_physical_exergy else "e_PH"

            def E_label(stream):
                return 0.0 if stream is None else stream.get("m", 0) * stream.get(exergy_type, 0)

            self.E_F = (
                E_label(s["steam_HP"])
                - E_label(s["feed_water"])
                + E_label(s["steam_IP"])
                - E_label(s["steam_inlet"])
                - sum(E_label(w) for w in s["injections"])
            )

        # The parser cannot evaluate the exergy of the heat connection on its own, so the
        # component writes it back for the system-level accounting.
        if s["heat"] is not None:
            s["heat"]["E"] = self.E_F
            s["heat"]["E_unit"] = "W"

        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        logger.info(
            f"Exergy balance of SteamGenerator {self.name} calculated: "
            f"E_P = {self.E_P:.2f} W, E_F = {self.E_F:.2f} W, "
            f"E_D = {self.E_D:.2f} W, Efficiency = {self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the steam generator.

        The heat carries the cost into the component and the steam carries it out. Writing
        :math:`x` for a cost variable of a stream, the rules are the same in every split mode and
        only the set of :math:`x` changes: :math:`\{\mathrm{T}, \mathrm{M}\}` with split physical
        exergy, :math:`\{\mathrm{PH}\}` without, and :math:`\mathrm{CH}` in addition when chemical
        exergy is enabled.

        The drain leaves at the state of the boiler water, so it is priced like the high pressure
        steam, for every cost variable it carries (P-principle):

        .. math::

            \frac{\dot{C}^{x}_\mathrm{steam,HP}}{\dot{E}^{x}_\mathrm{steam,HP}}
            = \frac{\dot{C}^{x}_\mathrm{drain}}{\dot{E}^{x}_\mathrm{drain}}

        What the component does not raise passes through at its own specific cost (F-principle).
        That is the mechanical exergy with the split, and the chemical exergy when it is enabled;
        the product variable, :math:`\mathrm{T}` with the split and :math:`\mathrm{PH}` without, is
        left to the cost balance:

        .. math::

            \frac{\dot{C}^{x}_\mathrm{feed}}{\dot{E}^{x}_\mathrm{feed}}
            = \frac{\dot{C}^{x}_\mathrm{steam,HP}}{\dot{E}^{x}_\mathrm{steam,HP}}
            \qquad
            \frac{\dot{C}^{x}_\mathrm{in,IP}}{\dot{E}^{x}_\mathrm{in,IP}}
            = \frac{\dot{C}^{x}_\mathrm{steam,IP}}{\dot{E}^{x}_\mathrm{steam,IP}}

        Both steam outlets come from the same heat, so they are produced at the same specific cost
        (P-principle):

        .. math::

            \frac{\dot{C}^\mathrm{T}_\mathrm{steam,HP}}{\dot{E}^\mathrm{T}_\mathrm{steam,HP}}
            = \frac{\dot{C}^\mathrm{T}_\mathrm{steam,IP}}{\dot{E}^\mathrm{T}_\mathrm{steam,IP}}
            \qquad \text{or, without the split,} \qquad
            \frac{\dot{C}^\mathrm{PH}_\mathrm{steam,HP}}{\dot{E}^\mathrm{PH}_\mathrm{steam,HP}}
            = \frac{\dot{C}^\mathrm{PH}_\mathrm{steam,IP}}{\dot{E}^\mathrm{PH}_\mathrm{steam,IP}}

        Parameters
        ----------
        A : numpy.ndarray
            Coefficient matrix of the cost equation system.
        b : numpy.ndarray
            Right-hand side vector of the cost equation system.
        counter : int
            Index of the next free row.
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        equations : dict
            Dictionary documenting the equations.
        chemical_exergy_enabled : bool
            Whether chemical exergy is part of the analysis.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

        Returns
        -------
        tuple
            The updated matrix, vector, row index and equation dictionary.
        """
        s = self._streams()
        labels = ["T", "M"] if split_physical_exergy else ["PH"]
        if chemical_exergy_enabled:
            labels.append("CH")
        product = "T" if split_physical_exergy else "PH"

        def equal_specific_cost(A, b, counter, kind, first, second, label):
            """Give the two streams the same specific cost of the given exergy."""
            A[counter, first["CostVar_index"][label]] = 1 / first[f"E_{label}"] if first[f"e_{label}"] != 0 else 1
            A[counter, second["CostVar_index"][label]] = -1 / second[f"E_{label}"] if second[f"e_{label}"] != 0 else -1
            equations[counter] = {
                "kind": kind,
                "objects": [self.name, first["name"], second["name"]],
                "property": f"c_{label}",
            }
            b[counter] = 0
            return counter + 1

        # The drain comes out of the same water as the high pressure steam.
        for label in labels:
            counter = equal_specific_cost(A, b, counter, "aux_p_rule", s["steam_HP"], s["drain"], label)

        # What the component does not raise passes through at its own cost.
        for label in labels:
            if label == product:
                continue
            counter = equal_specific_cost(A, b, counter, "aux_f_rule", s["feed_water"], s["steam_HP"], label)

        if s["steam_IP"] is not None:
            for label in labels:
                if label == product:
                    continue
                inlet = s["steam_inlet"] if s["steam_inlet"] is not None else s["feed_water"]
                counter = equal_specific_cost(A, b, counter, "aux_f_rule", inlet, s["steam_IP"], label)
            counter = equal_specific_cost(A, b, counter, "aux_p_rule", s["steam_HP"], s["steam_IP"], product)

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform the exergoeconomic cost balance of the steam generator.

        Fuel and product follow :meth:`calc_exergy_balance`: the fuel is the heat entering the
        component and the product is the cost the water and steam streams gain. The drain is not
        part of the product, so the cost leaving with it raises the cost of the exergy destruction.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """
        s = self._streams()
        labels = ["C_T", "C_M"] if split_physical_exergy else ["C_PH"]
        if chemical_exergy_enabled:
            labels.append("C_CH")

        def cost(stream):
            return 0.0 if stream is None else sum(stream[label] for label in labels)

        C_P_HP = cost(s["steam_HP"]) - cost(s["feed_water"])
        C_P_IP = cost(s["steam_IP"]) - cost(s["steam_inlet"])
        self.C_P = C_P_HP + C_P_IP - sum(cost(w) for w in s["injections"])
        self.C_F = s["heat"].get("C_TOT", 0.0) if s["heat"] is not None else 0.0

        self.c_F = self.C_F / self.E_F if self.E_F else np.nan
        self.c_P = self.C_P / self.E_P if self.E_P else np.nan
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F else np.nan
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) else np.nan
