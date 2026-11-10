import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.components.component import set_equal_specific_cost
from exerpy.logger import logger


@component_registry
class FlashTank(Component):
    r"""
    Class for exergy and exergoeconomic analysis of flash tank.

    This class performs exergy and exergoeconomic analysis calculations for flash tank components,
    accounting for two inlet and two outlet streams.

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
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the flash tank component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate in currency/h, default 0.0
        """
        self.dissipative = False
        super().__init__(**kwargs)

    @staticmethod
    def _flow(streams, form, kind="E"):
        """Sum of the exergy (``kind="E"``) or cost (``kind="C"``) flows of one form over the streams."""
        if kind == "E":
            return sum(s["m"] * s[f"e_{form}"] for s in streams.values())
        return sum(s[f"C_{form}"] for s in streams.values())

    def _decreasing_forms(self, split_physical_exergy):
        """Exergy forms whose decrease is fuel: mechanical (with split) and chemical (if known)."""
        forms = ["M"] if split_physical_exergy else []
        if all(s.get("e_CH") is not None for s in (*self.inl.values(), *self.outl.values())):
            forms.append("CH")
        return forms

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the flash tank.

        Parameters
        ----------
        T0 : float
            Ambient temperature in Kelvin.
        p0 : float
            Ambient pressure in Pascal.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Raises
        ------
        ValueError
            If the number of inlet or outlet streams is less than two.

        Notes
        -----
        The thermal exergy of the inlet is fuel and that of the outlets is product. The decrease of
        mechanical exergy (with split physical exergy) and of chemical exergy (if known) is fuel as
        well, so the exergy destruction is the full exergy balance:

        .. math::
            \dot{E}_\mathrm{F} = \dot{E}_\mathrm{in}^\mathrm{T}
            + \Bigl(\dot{E}_\mathrm{in}^\mathrm{M} - \sum_{i} \dot{E}_{\mathrm{out},i}^\mathrm{M}\Bigr)
            + \Bigl(\dot{E}_\mathrm{in}^\mathrm{CH} - \sum_{i} \dot{E}_{\mathrm{out},i}^\mathrm{CH}\Bigr)

        .. math::
            \dot{E}_\mathrm{P} = \sum_{i} \dot{E}_{\mathrm{out},i}^\mathrm{T}

        Without the split, :math:`\mathrm{PH}` takes the place of :math:`\mathrm{T}` and the
        mechanical term falls away. The cost of fuel and product follows the same forms.
        """
        # Ensure that the component has at least two outlets and one inlet.
        if len(self.inl) < 1 or len(self.outl) < 2:
            raise ValueError("Flash tank requires one inlet and two outlets.")

        phys = "T" if split_physical_exergy else "PH"
        self.E_F = self._flow(self.inl, phys)
        self.E_P = self._flow(self.outl, phys)
        # The decrease of mechanical and chemical exergy is fuel.
        for form in self._decreasing_forms(split_physical_exergy):
            self.E_F += self._flow(self.inl, form) - self._flow(self.outl, form)

        # Exergy destruction and efficiency.
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results.
        logger.info(
            f"Exergy balance of FlashTank {self.name} calculated: "
            f"E_F = {self.E_F:.2f} W, E_P = {self.E_P:.2f} W, E_D = {self.E_D:.2f} W, "
            f"Efficiency = {self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the flash tank.

        The tank separates one stream into a vapour and a liquid outlet. Both come out of the same
        vessel, so both are product and both are priced alike (P-principle), while the pressure and
        the composition merely pass through (F-principle).

        With split physical exergy, the two outlets carry the same specific cost of their thermal
        exergy, and each keeps the specific cost of the mechanical exergy of the inlet:

        .. math::

            \frac{\dot{C}^\mathrm{T}_{\mathrm{out},1}}{\dot{E}^\mathrm{T}_{\mathrm{out},1}}
            = \frac{\dot{C}^\mathrm{T}_{\mathrm{out},2}}{\dot{E}^\mathrm{T}_{\mathrm{out},2}}
            \qquad
            \frac{\dot{C}^\mathrm{M}_\mathrm{in}}{\dot{E}^\mathrm{M}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{M}_{\mathrm{out},j}}{\dot{E}^\mathrm{M}_{\mathrm{out},j}}

        Without the split the mechanical rules fall away and the P-rule acts on the physical exergy
        of the two outlets instead:

        .. math::

            \frac{\dot{C}^\mathrm{PH}_{\mathrm{out},1}}{\dot{E}^\mathrm{PH}_{\mathrm{out},1}}
            = \frac{\dot{C}^\mathrm{PH}_{\mathrm{out},2}}{\dot{E}^\mathrm{PH}_{\mathrm{out},2}}

        With chemical exergy enabled, either way:

        .. math::

            \frac{\dot{C}^\mathrm{CH}_\mathrm{in}}{\dot{E}^\mathrm{CH}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{CH}_{\mathrm{out},j}}{\dot{E}^\mathrm{CH}_{\mathrm{out},j}}

        Note that these are equalities of specific cost, cost divided by the exergy *flow* of the
        stream, so two outlets carrying different mass flows are priced the same per unit of exergy.

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature (not used).
        equations : list or dict
            Data structure for storing equation labels.
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
            The updated row index after adding equations.
        equations : list or dict
            Updated structure with equation labels.
        """
        # single inlet
        inlet = self.inl[0]
        # two outlets (assumed indices 0 and 1)
        out0 = self.outl[0]
        out1 = self.outl[1]

        phys = "T" if split_physical_exergy else "PH"

        # --- Physical product-rule: c_x,out0 = c_x,out1 ---
        #  1/e_x,out0 · C_x,out0  - 1/e_x,out1 · C_x,out1 = 0
        set_equal_specific_cost(A, counter, out0, out1, phys, ref_is_outlet=True)

        equations[counter] = {
            "kind": "aux_p_rule",
            "objects": [self.name, out0["name"], out1["name"]],
            "property": f"c_{phys}",
        }
        b[counter] = 0.0
        counter += 1

        # --- Mechanical equality: c_M,inlet = c_M,outlet_i for each outlet ---
        # Without the split the rule above already covers the physical exergy of both outlets.
        if split_physical_exergy:
            for out in (out0, out1):
                set_equal_specific_cost(A, counter, inlet, out, "M")
                equations[counter] = {
                    "kind": "aux_equality",
                    "objects": [self.name, inlet["name"], out["name"]],
                    "property": "c_M",
                }
                b[counter] = 0.0
                counter += 1

        # --- Chemical equality, if enabled: c_CH,inlet = c_CH,outlet_i ---
        if chemical_exergy_enabled:
            for out in (out0, out1):
                set_equal_specific_cost(A, counter, inlet, out, "CH")
                equations[counter] = {
                    "kind": "aux_equality",
                    "objects": [self.name, inlet["name"], out["name"]],
                    "property": "c_CH",
                }
                b[counter] = 0.0
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform exergoeconomic cost balance for the flash tank.

        The cost of fuel and product follows the exergy forms of :meth:`calc_exergy_balance`:

        .. math::
            \dot{C}_\mathrm{F} = \dot{C}_\mathrm{in}^\mathrm{T}
            + \Bigl(\dot{C}_\mathrm{in}^\mathrm{M} - \sum_{i} \dot{C}_{\mathrm{out},i}^\mathrm{M}\Bigr)
            + \Bigl(\dot{C}_\mathrm{in}^\mathrm{CH} - \sum_{i} \dot{C}_{\mathrm{out},i}^\mathrm{CH}\Bigr)
            \qquad
            \dot{C}_\mathrm{P} = \sum_{i} \dot{C}_{\mathrm{out},i}^\mathrm{T}

        Parameters
        ----------
        T0 : float
            Ambient temperature
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """

        phys = "T" if split_physical_exergy else "PH"
        self.C_F = self._flow(self.inl, phys, "C")
        self.C_P = self._flow(self.outl, phys, "C")
        for form in self._decreasing_forms(split_physical_exergy):
            self.C_F += self._flow(self.inl, form, "C") - self._flow(self.outl, form, "C")

        self.c_F = self.C_F / self.E_F if self.E_F else np.nan
        self.c_P = self.C_P / self.E_P if self.E_P else np.nan
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F else np.nan
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) else np.nan
