import numpy as np
from msgspec import UNSET
from msgspec import UnsetType

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.components.component import set_equal_specific_cost
from exerpy.logger import logger
from exerpy.quantities import Temperature


@component_registry
class SimpleHeatExchanger(Component):
    r"""
    Class for exergy and exergoeconomic analysis of simple heat exchangers.

    This class performs exergy and exergoeconomic analysis calculations for heat exchanger components,
    accounting for one inlet and one outlet stream across various temperature regimes, including
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
    T_hot : float, optional
        Temperature of the heat source in K, for a stream that takes in heat above the ambient
        temperature. Given, the fuel is the exergy of the heat at that temperature,
        :math:`\dot{E}_\mathrm{F} = \dot{Q}\,(1 - T_0/T_\mathrm{hot})`, so the loss of the heat
        transfer from the source counts as exergy destruction of the component.
    T_cold : float, optional
        Temperature of the heat consumer in K, for a stream that releases heat above the ambient
        temperature. Given, the product is the exergy of the heat at that temperature,
        :math:`\dot{E}_\mathrm{P} = |\dot{Q}|\,(1 - T_0/T_\mathrm{cold})`.

    Without them, the heat is valued at the exergy change of the stream itself, and the loss of the
    heat transfer to or from the outside lies outside the component.
    """

    class Input(Component.Input, kw_only=True):
        # True: the heat release is no product, its exergy is destroyed.
        dissipative: bool | None | UnsetType = UNSET
        # Temperature of the heat source (heat input) or consumer (heat release).
        T_hot: Temperature | None | UnsetType = UNSET
        T_cold: Temperature | None | UnsetType = UNSET

    def __init__(self, **kwargs):
        r"""
        Initialize the heat exchanger component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - dissipative (bool): whether component has dissipative behavior, default False
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate in currency/h, default 0.0
            - T_hot (float): temperature of the heat source in K, default None
            - T_cold (float): temperature of the heat consumer in K, default None
        """
        self.T_hot = None
        self.T_cold = None
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the simple heat exchanger.

        **Heat release** :math:\dot{Q}<0

        Case 1: Both streams above ambient temperature. With split physical exergy the heat is valued at
        the change of thermal exergy, so the friction of the stream is exergy destruction. Without the
        split :math:`\mathrm{PH}` takes the place of :math:`\mathrm{T}`: the pressure drop is then part of
        the exergy of the heat, and the component warns.

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Case 2: Inlet above and outlet below ambient temperature. The product is the thermal
        exergy the stream gains below the ambient temperature. The heat released above it serves no
        purpose, since heat transfer across the ambient temperature has no meaningful product
        :cite:`Bejan1996`, so the thermal exergy of the inlet is destroyed. Without the split the warm
        and the cold exergy cannot be told apart: the heat carries the net change of physical exergy,
        :math:`\dot{E}_{\mathrm{P}} = \dot{E}_{\mathrm{F}} = |\dot{E}^{\mathrm{PH}}_{\mathrm{out}}
        - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}|`, nothing is destroyed, and the component warns.

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Case 3: Both streams below ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}\bigr)
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        **Heat injection** :math:\dot{Q}>0

        Case 1: Both streams above ambient temperature. As for the heat release, the heat is the
        change of thermal exergy with split physical exergy and of physical exergy without.

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        Case 2: Inlet below and outlet above ambient temperature. The product is the thermal exergy
        of the outlet. The cold exergy of the inlet is used up while the heat warms the stream to the
        ambient temperature, which has no meaningful product :cite:`Bejan1996`, so it is destroyed,
        as when a stream is cooled across the ambient temperature. Without the split, as there,
        :math:`\dot{E}_{\mathrm{P}} = \dot{E}_{\mathrm{F}} = |\dot{E}^{\mathrm{PH}}_{\mathrm{out}}
        - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}|` and the component warns.

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Case 3: Both streams below ambient temperature. The cold exergy the stream gives up leaves
        with the heat and is the product; the pressure drop is fuel and destroyed :cite:`Bejan1996`.

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Fully dissipative or :math:\dot{Q}=0

        .. math::

            \dot{E}_{\mathrm{P}} = \mathrm{NaN}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

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
            If required inlet or outlet are missing.
        """
        # Validate the number of inlets and outlets
        if not hasattr(self, "inl") or not hasattr(self, "outl") or len(self.inl) < 1 or len(self.outl) < 1:
            msg = "SimpleHeatExchanger requires at least one inlet and one outlet as well as one heat flow."
            logger.error(msg)
            raise ValueError(msg)
        if len(self.inl) > 2 or len(self.outl) > 2:
            msg = "SimpleHeatExchanger requires a maximum of two inlets and two outlets."
            logger.error(msg)
            raise ValueError(msg)

        # Extract inlet and outlet streams
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Calculate heat transfer Q
        Q = outlet["m"] * outlet["h"] - inlet["m"] * inlet["h"]

        # Initialize E_P and E_F
        self.E_P = 0.0
        self.E_F = 0.0

        # With split the heat is the change of thermal exergy; without it, as the user chose, the change of
        # physical exergy, which includes the pressure drop.
        th = "e_T" if split_physical_exergy else "e_PH"
        p_in, p_out = inlet.get("p"), outlet.get("p")
        if not split_physical_exergy and Q != 0 and p_in is not None and p_out is not None and p_out < p_in:
            logger.warning(
                f"SimpleHeatExchanger {self.name}: without split physical exergy, the exergy lost by the pressure "
                f"drop ({(p_in - p_out) / 1e5:.3g} bar) is counted in the exergy of the heat, not as exergy "
                f"destruction. Split the physical exergy to see it as destruction."
            )
        self._warn_heat_connection_exergy(inlet, outlet, Q, T0, split_physical_exergy)

        # Case 1: Heat is released (Q < 0)
        if Q < 0:
            if inlet["T"] >= T0 and outlet["T"] >= T0:
                self.E_P = np.nan if getattr(self, "dissipative", False) else inlet["m"] * (inlet[th] - outlet[th])
                self.E_F = inlet["m"] * (inlet["e_PH"] - outlet["e_PH"])

            elif inlet["T"] >= T0 and outlet["T"] < T0:
                if split_physical_exergy:
                    self.E_P = outlet["m"] * outlet["e_T"]
                    self.E_F = (
                        inlet["m"] * inlet["e_T"]
                        + outlet["m"] * outlet["e_T"]
                        + (inlet["m"] * inlet["e_M"] - outlet["m"] * outlet["e_M"])
                    )
                else:
                    self.E_P = self._net_change_across_ambient(inlet, outlet, "cooled")
                    self.E_F = self.E_P

            elif inlet["T"] <= T0 and outlet["T"] < T0:
                if split_physical_exergy:
                    self.E_P = outlet["m"] * (outlet["e_T"] - inlet["e_T"])
                    self.E_F = self.E_P + inlet["m"] * inlet["e_M"] - outlet["m"] * outlet["e_M"]
                else:
                    self.E_P = (
                        np.nan
                        if getattr(self, "dissipative", False)
                        else outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
                    )
                    self.E_F = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])

            else:
                # Unimplemented corner case
                logger.warning("SimpleHeatExchanger: unimplemented case (Q < 0, T_in < T0 < T_out?).")
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 2: Heat is added (Q > 0)
        elif Q > 0:
            if inlet["T"] >= T0 and outlet["T"] >= T0:
                self.E_P = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
                self.E_F = outlet["m"] * (outlet[th] - inlet[th])
            elif inlet["T"] < T0 and outlet["T"] >= T0:
                if split_physical_exergy:
                    # The cold exergy of the inlet is used up before the heat raises the stream above T0.
                    self.E_P = outlet["m"] * outlet["e_T"]
                    self.E_F = (
                        inlet["m"] * inlet["e_T"]
                        + outlet["m"] * outlet["e_T"]
                        + (inlet["m"] * inlet["e_M"] - outlet["m"] * outlet["e_M"])
                    )
                else:
                    self.E_P = self._net_change_across_ambient(inlet, outlet, "heated")
                    self.E_F = self.E_P

            elif inlet["T"] < T0 and outlet["T"] <= T0:
                if split_physical_exergy:
                    # The cold exergy the stream gives up goes with the heat (product); the pressure drop is
                    # fuel that is destroyed.
                    self.E_P = (
                        np.nan if getattr(self, "dissipative", False) else inlet["m"] * (inlet["e_T"] - outlet["e_T"])
                    )
                    self.E_F = inlet["m"] * (inlet["e_T"] - outlet["e_T"]) + (
                        inlet["m"] * inlet["e_M"] - outlet["m"] * outlet["e_M"]
                    )
                else:
                    self.E_P = (
                        np.nan if getattr(self, "dissipative", False) else inlet["m"] * (inlet["e_PH"] - outlet["e_PH"])
                    )
                    self.E_F = inlet["m"] * (inlet["e_PH"] - outlet["e_PH"])
            else:
                logger.warning("SimpleHeatExchanger: unimplemented case (Q > 0, T_in > T0 > T_out?).")
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 3: Fully dissipative or Q == 0
        else:
            self.E_P = np.nan
            self.E_F = inlet["m"] * (inlet["e_PH"] - outlet["e_PH"])

        self._value_heat_at_temperature(Q, inlet, outlet, T0)

        # Calculate exergy destruction
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logger.info(
            f"Exergy balance of SimpleHeatExchanger {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def _heat_stream(self):
        """The heat connection of the component, or ``None``."""
        for conn in [*self.inl.values(), *self.outl.values()]:
            if conn.get("kind") == "heat":
                return conn
        return None

    def _net_change_across_ambient(self, inlet, outlet, verb):
        """Net change of physical exergy of a stream crossing T0 without split, which the heat carries."""
        logger.warning(
            f"SimpleHeatExchanger {self.name}: the stream is {verb} across the ambient temperature. Without split "
            f"physical exergy the warm and the cold exergy cannot be told apart, so the heat carries the net change "
            f"and nothing is destroyed. Split the physical exergy for a meaningful balance."
        )
        return abs(outlet["m"] * outlet["e_PH"] - inlet["m"] * inlet["e_PH"])

    def _warn_heat_connection_exergy(self, inlet, outlet, Q, T0, split_physical_exergy):
        """Warn where the heat connection carries another exergy than the heat in the component balance."""
        if self._heat_stream() is None or Q == 0:
            return
        if getattr(self, "dissipative", False):
            logger.warning(
                f"SimpleHeatExchanger {self.name} is dissipative and destroys the exergy of its heat, but the heat "
                f"connection still carries the change of thermal exergy of the stream. Listed in E_L, this exergy is "
                f"counted twice."
            )
        elif split_physical_exergy and (inlet["T"] >= T0) != (outlet["T"] >= T0):
            logger.warning(
                f"SimpleHeatExchanger {self.name}: the stream crosses the ambient temperature. The heat connection "
                f"carries the net change of thermal exergy of the stream, while the component values the heat at the "
                f"thermal exergy of the outlet, so the exergy balance of the plant may not close."
            )

    def heat_exergy_reversed(self, T0, split_physical_exergy=True):
        """True if the exergy of the heat flows against the heat, as it does below the ambient temperature."""
        inlet, outlet = self.inl.get(0), self.outl.get(0)
        if not inlet or not outlet or "T" not in inlet or "T" not in outlet:
            return False
        if not split_physical_exergy and (inlet["T"] >= T0) != (outlet["T"] >= T0):
            # Across T0 without split the heat carries the net change of physical exergy.
            Q = outlet["m"] * outlet["h"] - inlet["m"] * inlet["h"]
            gain = outlet["m"] * outlet["e_PH"] - inlet["m"] * inlet["e_PH"]
            return (gain > 0) != (Q > 0)
        return outlet["T"] < T0

    def _heat_is_product(self, Q, T0, split_physical_exergy):
        """True if the exergy of the heat leaves the component, so the heat is its product."""
        return Q != 0 and (Q < 0) != self.heat_exergy_reversed(T0, split_physical_exergy)

    def _value_heat_at_temperature(self, Q, inlet, outlet, T0):
        """Value the heat at ``T_hot`` or ``T_cold`` where given; return ``"source"``, ``"consumer"`` or None."""
        above_ambient = inlet["T"] >= T0 and outlet["T"] >= T0
        heat = self._heat_stream()
        if Q > 0 and self.T_hot is not None:
            if not above_ambient:
                logger.warning(
                    f"SimpleHeatExchanger {self.name}: T_hot is used only for a stream above the ambient "
                    f"temperature, so it is ignored."
                )
                return None
            if self.T_hot <= max(inlet["T"], outlet["T"]):
                raise ValueError(
                    f"SimpleHeatExchanger {self.name}: the heat source at T_hot = {self.T_hot} K has to be "
                    f"hotter than the stream it heats, which reaches {max(inlet['T'], outlet['T']):.2f} K."
                )
            self.E_F = Q * (1 - T0 / self.T_hot)
            if heat is not None:
                heat["E"] = self.E_F
            return "source"
        if Q < 0 and self.T_cold is not None and not getattr(self, "dissipative", False):
            if not above_ambient:
                logger.warning(
                    f"SimpleHeatExchanger {self.name}: T_cold is used only for a stream above the ambient "
                    f"temperature, so it is ignored."
                )
                return None
            if not T0 < self.T_cold < min(inlet["T"], outlet["T"]):
                raise ValueError(
                    f"SimpleHeatExchanger {self.name}: the heat consumer at T_cold = {self.T_cold} K has to "
                    f"be colder than the stream that heats it, which falls to {min(inlet['T'], outlet['T']):.2f} K, "
                    f"and warmer than the ambient temperature."
                )
            self.E_P = -Q * (1 - T0 / self.T_cold)
            if heat is not None:
                heat["E"] = self.E_P
            return "consumer"
        return None

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the simple heat exchanger.

        Writing :math:`x` for the cost variable of the physical exergy, the rules hold in both split
        modes with :math:`x = \mathrm{T}` for split physical exergy and :math:`x = \mathrm{PH}`
        without it.

        The cost of the heat follows the direction of its exergy, which below the ambient
        temperature is against the heat (see :meth:`heat_exergy_reversed`).

        **Heat as product**, when its exergy leaves: heat released above or taken in below the
        ambient temperature. The stream gives up the fuel, so it follows the F-principle:

        .. math::

            \frac{\dot{C}^{x}_\mathrm{in}}{\dot{E}^{x}_\mathrm{in}}
            = \frac{\dot{C}^{x}_\mathrm{out}}{\dot{E}^{x}_\mathrm{out}}

        **Heat as fuel**, when its exergy enters: the cost balance alone prices the outlet, so no
        rule is written:

        .. math::

            \dot{C}^{x}_\mathrm{out}
            = \dot{C}^{x}_\mathrm{in} + \dot{C}^\mathrm{TOT}_\mathrm{heat} + \dot{Z}

        The pressure and the composition pass through at their own specific cost in either case.
        The mechanical rule exists only with split physical exergy, since without it the stream has
        no mechanical cost variable; the chemical rule exists whenever chemical exergy is enabled:

        .. math::

            \frac{\dot{C}^\mathrm{M}_\mathrm{in}}{\dot{E}^\mathrm{M}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{M}_\mathrm{out}}{\dot{E}^\mathrm{M}_\mathrm{out}}
            \qquad
            \frac{\dot{C}^\mathrm{CH}_\mathrm{in}}{\dot{E}^\mathrm{CH}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{CH}_\mathrm{out}}{\dot{E}^\mathrm{CH}_\mathrm{out}}

        Without a heat connection there is no cost variable for the heat, so no rule is written for
        the physical exergy and the cost balance alone prices the outlet. The heat then has no cost,
        and the component warns.

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
        # Extract inlet and outlet
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Calculate heat transfer Q
        Q = outlet["m"] * outlet["h"] - inlet["m"] * inlet["h"]

        # Equality equation for mechanical exergy costs (c_M,in = c_M,out). Without the split there is no
        # mechanical cost variable, the rule below acts on the physical exergy instead.
        if split_physical_exergy:
            set_equal_specific_cost(A, counter, inlet, outlet, "M")
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": "c_M",
            }
            b[counter] = 0
            counter += 1

        phys = "T" if split_physical_exergy else "PH"

        # Equality equation for chemical exergy costs (c_CH,in = c_CH,out)
        if chemical_exergy_enabled:
            set_equal_specific_cost(A, counter, inlet, outlet, "CH")
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": "c_CH",
            }
            b[counter] = 0
            counter += 1

        # Heat as product: F-rule on the stream. Heat as fuel or no heat stream: the cost balance prices the outlet.
        heat = self._heat_stream()
        heat_is_product = self._heat_is_product(Q, T0, split_physical_exergy)
        if heat is None and Q != 0:
            logger.warning(
                f"SimpleHeatExchanger '{self.name}' has no heat connection, so the heat has no cost: "
                + ("its cost stays in the outlet stream." if heat_is_product else "it enters without cost.")
            )
        elif heat_is_product:
            set_equal_specific_cost(A, counter, inlet, outlet, phys)
            equations[counter] = {
                "kind": "aux_f_rule",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": f"c_{phys}",
            }
            b[counter] = 0
            counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform exergoeconomic cost balance for the simple heat exchanger.

        Fuel and product costs follow the exergy definitions of :meth:`calc_exergy_balance`. The heat
        is the product or a fuel by the direction of its exergy (see :meth:`heat_exergy_reversed`),
        with :math:`\dot{C}_\mathrm{Q}` the cost of the heat connection, zero without one, and
        :math:`\dot{Z}` including the share of dissipative costs.

        **Heat as product** (heat released above or taken in below the ambient temperature). The
        stream gives up the fuel at the specific costs it enters with, :math:`x \in \{\mathrm{T},
        \mathrm{M}\}` with split physical exergy and :math:`x = \mathrm{PH}` without:

        .. math::

            \dot{C}_\mathrm{F} = \sum_x c^{x}_\mathrm{in}
            \bigl(\dot{E}^{x}_\mathrm{in} - \dot{E}^{x}_\mathrm{out}\bigr),
            \qquad
            \dot{C}_\mathrm{P} = \dot{C}_\mathrm{Q}

        Without a heat connection :math:`\dot{C}_\mathrm{P} = \dot{C}_\mathrm{F} + \dot{Z}`.

        **Heat as fuel**, both streams above the ambient temperature, or without split:

        .. math::

            \dot{C}_\mathrm{F} = \dot{C}_\mathrm{Q},
            \qquad
            \dot{C}_\mathrm{P} = \dot{C}^{x}_\mathrm{out} - \dot{C}^{x}_\mathrm{in}
            \quad (x = \mathrm{PH})

        Both streams below the ambient temperature, with split:

        .. math::

            \dot{C}_\mathrm{F} = \dot{C}_\mathrm{Q}
            + \dot{C}^{\mathrm{M}}_\mathrm{in} - \dot{C}^{\mathrm{M}}_\mathrm{out},
            \qquad
            \dot{C}_\mathrm{P} = \dot{C}^{\mathrm{T}}_\mathrm{out} - \dot{C}^{\mathrm{T}}_\mathrm{in}

        The stream crossing the ambient temperature, with split:

        .. math::

            \dot{C}_\mathrm{F} = \dot{C}^{\mathrm{T}}_\mathrm{in} + \dot{C}_\mathrm{Q}
            + \dot{C}^{\mathrm{M}}_\mathrm{in} - \dot{C}^{\mathrm{M}}_\mathrm{out},
            \qquad
            \dot{C}_\mathrm{P} = \dot{C}^{\mathrm{T}}_\mathrm{out}

        Without a product (dissipative), :math:`\dot{C}_\mathrm{P}` is NaN; for :math:`\dot{Q} = 0`,
        :math:`\dot{C}_\mathrm{F} = \dot{C}^{\mathrm{PH}}_\mathrm{in} - \dot{C}^{\mathrm{PH}}_\mathrm{out}`.

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
        """
        inlet = self.inl[0]
        outlet = self.outl[0]
        Q = outlet["m"] * outlet["h"] - inlet["m"] * inlet["h"]
        heat = self._heat_stream()
        C_Q = heat["C_TOT"] if heat is not None and heat.get("C_TOT") is not None else None
        crossing = (inlet["T"] >= T0) != (outlet["T"] >= T0)

        if Q == 0:
            self.C_F = inlet["C_PH"] - outlet["C_PH"]
            self.C_P = np.nan
        elif np.isnan(self.E_F):
            self.C_F = self.C_P = np.nan
        elif self._heat_is_product(Q, T0, split_physical_exergy):
            labels = ("T", "M") if split_physical_exergy else ("PH",)
            self.C_F = sum(
                inlet[f"c_{x}"] * (inlet["m"] * inlet[f"e_{x}"] - outlet["m"] * outlet[f"e_{x}"]) for x in labels
            )
            self.C_P = C_Q if C_Q is not None else self.C_F + self.Z_costs + getattr(self, "Z_diss", 0)
        elif split_physical_exergy and crossing:
            self.C_F = inlet["C_T"] + (C_Q or 0.0) + inlet["C_M"] - outlet["C_M"]
            self.C_P = outlet["C_T"]
        elif split_physical_exergy and outlet["T"] < T0:
            self.C_F = (C_Q or 0.0) + inlet["C_M"] - outlet["C_M"]
            self.C_P = outlet["C_T"] - inlet["C_T"]
        else:
            self.C_F = C_Q or 0.0
            self.C_P = outlet["C_PH"] - inlet["C_PH"]
        if np.isnan(self.E_P):
            self.C_P = np.nan

        # Calculate specific costs and exergoeconomic indicators
        self.c_F = self.C_F / self.E_F if self.E_F else np.nan
        self.c_P = self.C_P / self.E_P if self.E_P else np.nan
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F else np.nan
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) else np.nan
