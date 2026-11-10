import numpy as np
from msgspec import UNSET
from msgspec import UnsetType

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.components.component import set_equal_specific_cost
from exerpy.components.component import set_mixing_cost
from exerpy.logger import logger
from exerpy.quantities import Branches


def _mixing_roles(streams, outlet, T0, form):
    """Role of each inlet of a mixing node: ``"fuel"``, ``"product"`` or ``"cross"``.

    An inlet on the other side of the ambient temperature than the outlet crosses it, so its exergy at
    the inlet is fuel and the exergy it carries at the outlet product. Otherwise a decrease of its
    specific exergy is fuel and an increase product (SPECO, p. 1267).
    """
    T_out = outlet["T"]
    roles = []
    for _, inlet in streams:
        if (T_out > T0 and inlet["T"] < T0) or (T_out < T0 and inlet["T"] >= T0):
            roles.append("cross")
        elif outlet[f"e_{form}"] > inlet[f"e_{form}"]:
            roles.append("product")
        else:
            roles.append("fuel")
    return roles


def _with_chemical_exergy(streams, outlet):
    """True if every stream of the node carries chemical exergy."""
    return all(stream.get("e_CH") is not None for stream in [outlet] + [inlet for _, inlet in streams])


def _mixing_fuel_and_product(streams, outlet, T0, split_physical_exergy):
    """Exergy product and fuel of a mixing node from ``(number of branches, inlet)`` pairs and the outlet.

    With split physical exergy the thermal exergy decides the roles and the decrease of mechanical
    exergy of every inlet is fuel (SPECO, eq. 14). With chemical exergy the decrease of the sum of
    chemical exergies is fuel (SPECO, eq. 35). With the outlet at the ambient temperature there is no
    product, and the fuel is the decrease of exergy of all inlets.
    """
    form = "T" if split_physical_exergy else "PH"
    e_out = outlet[f"e_{form}"]
    E_P = np.nan if outlet["T"] == T0 else 0
    E_F = 0
    roles = _mixing_roles(streams, outlet, T0, form)
    for (n, inlet), role in zip(streams, roles, strict=True):
        m = n * inlet["m"]
        e_in = inlet[f"e_{form}"]
        if outlet["T"] == T0 or role == "fuel":
            E_F += m * (e_in - e_out)
        elif role == "product":
            E_P += m * (e_out - e_in)
        else:
            E_P += m * e_out
            E_F += m * e_in
        if split_physical_exergy:
            E_F += m * (inlet["e_M"] - outlet["e_M"])
    if _with_chemical_exergy(streams, outlet):
        E_F += sum(n * inlet["m"] * (inlet["e_CH"] - outlet["e_CH"]) for n, inlet in streams)
    return E_P, E_F


def _mixing_fuel_cost(streams, outlets, T0, split_physical_exergy):
    """Cost of the fuel of a mixing node, on the same exergy forms and streams as its fuel.

    ``outlets`` are the outlets at the mixed state; their cost rates are summed.
    """
    form = "T" if split_physical_exergy else "PH"
    outlet = outlets[0]
    roles = _mixing_roles(streams, outlet, T0, form)
    C_F = 0
    for (n, inlet), role in zip(streams, roles, strict=True):
        # At the ambient temperature every inlet only gives up exergy.
        if outlet["T"] == T0 or role == "fuel":
            C_F += n * inlet["m"] * inlet[f"c_{form}"] * (inlet[f"e_{form}"] - outlet[f"e_{form}"])
        elif role == "cross":
            C_F += n * inlet[f"C_{form}"]
    forms = ["M"] if split_physical_exergy else []
    if _with_chemical_exergy(streams, outlet):
        forms.append("CH")
    for x in forms:
        C_F += sum(n * inlet[f"C_{x}"] for n, inlet in streams) - sum(o[f"C_{x}"] for o in outlets)
    return C_F


@component_registry
class Mixer(Component):
    r"""
    Class for exergy analysis of mixers.

    This class performs exergy analysis calculations for mixers with multiple
    inlet streams and generally one outlet stream (multiple outlets are possible).
    The exergy product and fuel definitions vary based on the temperature
    relationships between inlet streams, outlet streams, and ambient conditions.

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
        Dictionary containing inlet streams data with temperature, mass flows,
        and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        and specific exergies.

    Notes
    -----
    The exergy product and fuel follow the change of the specific exergy of each inlet
    :math:`i` on its way to the outlet :cite:`lazzaretto2006speco`. A decrease is fuel, an increase
    product. An inlet on the other side of the ambient temperature than the outlet crosses it, so its
    exergy at the inlet is fuel and the exergy it carries at the outlet product:

    .. math::

        \dot E_{P} = \sum_{i \in P} \dot m_{i}\,\bigl(e_{\mathrm{out}} - e_{\mathrm{in},i}\bigr)
        + \sum_{i \in X} \dot m_{i}\,e_{\mathrm{out}}
        \qquad
        \dot E_{F} = \sum_{i \in F} \dot m_{i}\,\bigl(e_{\mathrm{in},i} - e_{\mathrm{out}}\bigr)
        + \sum_{i \in X} \dot m_{i}\,e_{\mathrm{in},i}

    with :math:`P` the inlets whose specific exergy rises, :math:`F` those whose specific exergy falls
    and :math:`X` those that cross the ambient temperature; :math:`e` is the physical exergy
    :math:`e^\mathrm{PH}`. With the outlet exactly at the ambient temperature there is no product,
    :math:`\dot E_{P}` is NaN and :math:`\dot E_{F} = \dot E_{D} = \sum_{i} \dot m_{i}\,
    (e_{\mathrm{in},i} - e_{\mathrm{out}})`.

    With split physical exergy, the thermal exergy :math:`e^\mathrm{T}` takes the place of
    :math:`e^\mathrm{PH}` in these sums, and the decrease of mechanical exergy of every inlet is
    part of the fuel :cite:`lazzaretto2006speco`:

    .. math::
        \dot E_{F} \mathrel{+}= \sum_{i}\dot m_{i}\,\bigl(e_{\mathrm{in},i}^{\mathrm{M}}
        -e_{\mathrm{out}}^{\mathrm{M}}\bigr)

    With chemical exergy, the decrease of the sum of the chemical exergies is part of the fuel as
    well, so that inlets of different composition are covered :cite:`lazzaretto2006speco`:

    .. math::
        \dot E_{F} \mathrel{+}= \sum_{i}\dot m_{i}\,\bigl(e_{\mathrm{in},i}^{\mathrm{CH}}
        -e_{\mathrm{out}}^{\mathrm{CH}}\bigr)

    An inlet that stands for several identical parallel branches, such as the outlet of a
    ``ParabolicTrough`` with ``num_branches`` :math:`n`, counts :math:`n` times, here and in the cost
    equations, every other inlet once.
    """

    class Input(Component.Input, kw_only=True):
        num_branches: Branches | None | UnsetType = UNSET

    def __init__(self, **kwargs):
        r"""Initialize mixer component with given parameters."""
        super().__init__(**kwargs)
        # How often each inlet exists, by connector: the number of parallel branches it stands for,
        # set by the analysis. An inlet not listed exists once.
        self.branches = {}
        # Only kept to warn if it is not used, see the analysis.
        self.num_branches = kwargs.get("num_branches")

    def _single_outlet(self):
        """Return the single outlet, whatever connector index the model gave it."""
        return next(iter(self.outl.values()))

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the mixer.

        Performs exergy balance calculations considering the temperature relationships
        between inlet streams, outlet stream(s), and ambient conditions.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined.
        """
        # Ensure that the component has at least two inlets and one outlet.
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Mixer requires at least two inlets and one outlet.")

        # Compute effective outlet state by aggregating all outlet streams.
        # Assume that all outlets share the same thermodynamic state.
        outlet_list = list(self.outl.values())
        first_outlet = outlet_list[0]
        T_out = first_outlet["T"]
        e_out_PH = first_outlet["e_PH"]
        # Verify that all outlets have the same thermodynamic state.
        for outlet in outlet_list:
            if outlet["T"] != T_out or outlet["e_PH"] != e_out_PH:
                msg = "All outlets in Mixer must have the same thermodynamic state."
                logger.error(msg)
                raise ValueError(msg)
        # Sum the mass of all outlet streams (if needed for further analysis)
        sum(outlet.get("m", 0) for outlet in outlet_list)

        streams = [(self.branches.get(k, 1), inlet) for k, inlet in self.inl.items()]
        self.E_P, self.E_F = _mixing_fuel_and_product(streams, first_outlet, T0, split_physical_exergy)

        # Calculate exergy destruction and efficiency; without a product all the fuel is destroyed.
        self.E_D = self.E_F if np.isnan(self.E_P) else self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results.
        logger.info(
            f"Exergy balance of Mixer {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the mixer.

        A mixer brings several streams together into one. The thermal exergy of the outlet is the
        product of the mixing, while what the component does not raise is simply blended.

        Writing :math:`x` for a cost variable that merely passes through, the outlet takes the
        mass-weighted mean of the specific costs of the inlets:

        .. math::

            \frac{\dot{C}^{x}_\mathrm{out}}{\dot{E}^{x}_\mathrm{out}}
            = \sum_{i} \frac{n_{i} \, \dot{m}_{\mathrm{in},i}}{\sum_{k} n_{k} \, \dot{m}_{\mathrm{in},k}}
              \cdot \frac{\dot{C}^{x}_{\mathrm{in},i}}{\dot{E}^{x}_{\mathrm{in},i}}

        where :math:`n_{i}` is the number of parallel branches inlet :math:`i` stands for (1 for a
        single stream).

        With split physical exergy this rule is written for the mechanical exergy,
        :math:`x = \mathrm{M}`, while the thermal exergy of the outlet is the product of the
        mixing and is left to the cost balance.

        Without the split there is no mechanical cost variable, and the single cost variable of the
        physical exergy of the outlet is the product, so **no mixing rule is written at all**; the
        cost balance alone determines it:

        .. math::

            \dot{C}^\mathrm{PH}_\mathrm{out}
            = \sum_{i} \dot{C}^\mathrm{PH}_{\mathrm{in},i} + \dot{Z}

        With chemical exergy enabled the rule is written for :math:`x = \mathrm{CH}` in either
        mode, since the composition of the outlet is the mixture of the inlets.

        An inlet without exergy of the share adds nothing to the sum, and an outlet without it carries
        no cost of it, :math:`\dot{C}^{x}_\mathrm{out} = 0`.

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature (provided for consistency; not used in this function).
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
            The updated row index (increased by 2 if chemical exergy is enabled, or by 1 otherwise).
        equations : list or dict
            Updated structure with equation labels.
        """
        # --- Chemical cost auxiliary equation (conditionally added) ---
        branches = [self.branches.get(k, 1) for k in self.inl]
        if chemical_exergy_enabled:
            set_mixing_cost(A, counter, self.inl.values(), self._single_outlet(), "CH", branches)
            equations[counter] = {
                "kind": "aux_mixing",
                "objects": [self.name] + [i["name"] for i in self.inl.values()] + [self._single_outlet()["name"]],
                "property": "c_CH",
            }
            chem_row = 1  # One row added for chemical equation.
        else:
            chem_row = 0  # No row added.

        # Mechanical cost auxiliary equation. Without the split the cost balance of the component is
        # the mixing rule for the physical exergy of the outlet already.
        if split_physical_exergy:
            set_mixing_cost(A, counter + chem_row, self.inl.values(), self._single_outlet(), "M", branches)

            # Dynamically build the list of inlet names
            inlet_names = [inlet["name"] for inlet in self.inl.values()]

            equations[counter + chem_row] = {
                "kind": "aux_mixing",
                "objects": [self.name] + inlet_names + [self._single_outlet()["name"]],
                "property": "c_M",
            }

        # Set the right-hand side entries to zero for the added rows.
        num_rows = (1 if chemical_exergy_enabled else 0) + (1 if split_physical_exergy else 0)
        for i in range(num_rows):
            b[counter + i] = 0
        counter += num_rows

        # Further outlets leave at the same state and the same specific cost as the first one.
        first = self._single_outlet()
        labels = (["T", "M"] if split_physical_exergy else ["PH"]) + (["CH"] if chemical_exergy_enabled else [])
        for out in list(self.outl.values())[1:]:
            for label in labels:
                set_equal_specific_cost(A, counter, first, out, label, ref_is_outlet=True)
                b[counter] = 0
                equations[counter] = {
                    "kind": "aux_p_rule",
                    "objects": [self.name, first["name"], out["name"]],
                    "property": f"c_{label}",
                }
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform exergoeconomic cost balance for the mixer.

        The mixer is a component where multiple streams combine. The general
        exergoeconomic balance equation is:

        .. math::
            \sum_{\mathrm{in}} \left(\dot{C}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{CH}}_{\mathrm{in}}\right)
            - \sum_{\mathrm{out}} \left(\dot{C}^{\mathrm{T}}_{\mathrm{out}}
            + \dot{C}^{\mathrm{M}}_{\mathrm{out}}
            + \dot{C}^{\mathrm{CH}}_{\mathrm{out}}\right)
            + \dot{Z}
            = 0

        The cost of the fuel takes the same exergy forms and streams as the fuel of
        :meth:`calc_exergy_balance` :cite:`lazzaretto2006speco`. An inlet whose specific exergy
        :math:`e^{x}` falls (:math:`x = \mathrm{T}` with split physical exergy, :math:`\mathrm{PH}`
        without) gives up that decrease at its own specific cost, an inlet crossing the ambient
        temperature brings its whole cost of that form, and the decrease of mechanical (with split) and
        chemical exergy (if known) of all inlets is fuel:

        .. math::

            \dot{C}_\mathrm{F} = \sum_{i \in F} \dot m_{i}\, c^{x}_{\mathrm{in},i}
            \bigl(e^{x}_{\mathrm{in},i} - e^{x}_\mathrm{out}\bigr)
            + \sum_{i \in X} \dot C^{x}_{\mathrm{in},i}
            + \sum_{y \in \{\mathrm{M}, \mathrm{CH}\}} \Bigl(\sum_{i} \dot C^{y}_{\mathrm{in},i}
            - \dot C^{y}_\mathrm{out}\Bigr)

        With the outlet at the ambient temperature every inlet only gives up exergy, so all inlets
        count as :math:`F`. The product cost closes the balance,
        :math:`\dot{C}_\mathrm{P} = \dot{C}_\mathrm{F} + \dot{Z} + \dot{Z}_\mathrm{diss}`.

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

        Notes
        -----
        The mixer treats thermal, mechanical, and chemical exergy components
        differently depending on whether inlets are "hot" or "cold" relative to
        the outlet temperature. The distinction ensures proper cost allocation
        for streams that provide heating versus those being heated.

        Future development may include merging profits from dissipative components.
        """
        streams = [(self.branches.get(k, 1), inlet) for k, inlet in self.inl.items()]
        self.C_F = _mixing_fuel_cost(streams, list(self.outl.values()), T0, split_physical_exergy)
        self.C_P = self.C_F + self.Z_costs + getattr(self, "Z_diss", 0)

        self.c_F = self.C_F / self.E_F if self.E_F else np.nan
        self.c_P = self.C_P / self.E_P if self.E_P else np.nan
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F else np.nan
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) else np.nan
