import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.components.component import set_equal_specific_cost
from exerpy.components.component import set_mixing_cost
from exerpy.components.nodes.mixer import _mixing_fuel_and_product
from exerpy.components.nodes.mixer import _mixing_fuel_cost
from exerpy.logger import logger


@component_registry
class Deaerator(Component):
    r"""
    Class for exergy analysis of deaerators.

    This class performs exergy analysis calculations for deaerators with multiple
    inlet streams and one outlet stream. The exergy product and fuel definitions
    vary based on the temperature relationships between inlet streams, outlet
    stream, and ambient conditions.

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
    well :cite:`lazzaretto2006speco`:

    .. math::
        \dot E_{F} \mathrel{+}= \sum_{i}\dot m_{i}\,\bigl(e_{\mathrm{in},i}^{\mathrm{CH}}
        -e_{\mathrm{out}}^{\mathrm{CH}}\bigr)

    A further material outlet, such as the vent, leaves with its own exergy: the sums above take all
    inlets to the state of the main outlet 0, so for each vent :math:`v` the fuel is corrected by
    :math:`\dot m_v (e_{\mathrm{out}} - e_v)` in every exergy form, and the exergy destruction is the
    full balance. The vent leaves at the specific costs of the main outlet.
    """

    def __init__(self, **kwargs):
        r"""Initialize deaerator component with given parameters."""
        super().__init__(**kwargs)

    def _vents(self):
        """Material outlets besides the main outlet 0, such as the vent."""
        return [o for k, o in self.outl.items() if k != 0 and o.get("kind", "material") == "material"]

    def _forms(self, split_physical_exergy):
        """Exergy forms of the streams: T and M with split, PH without, and CH where known."""
        forms = ["T", "M"] if split_physical_exergy else ["PH"]
        streams = [*self.inl.values(), *self.outl.values()]
        if all(st.get("e_CH") is not None for st in streams):
            forms.append("CH")
        return forms

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the deaerator.

        Performs exergy balance calculations considering the temperature relationships
        between inlet streams, outlet stream, and ambient conditions.

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
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Deaerator requires at least two inlets and one outlet.")

        streams = [(1, inlet) for inlet in self.inl.values()]
        self.E_P, self.E_F = _mixing_fuel_and_product(streams, self.outl[0], T0, split_physical_exergy)
        # A further outlet such as the vent leaves at its own state: the share of the inlets it takes
        # leaves the fuel at the state of the main outlet and with its own exergy instead.
        for vent in self._vents():
            for x in self._forms(split_physical_exergy):
                self.E_F += vent["m"] * (self.outl[0][f"e_{x}"] - vent[f"e_{x}"])

        # Calculate exergy destruction and efficiency
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logger.info(
            f"Exergy balance of Deaerator {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the deaerator.

        A deaerator mixes several streams into one. The stream leaving it is warmer than the colder
        inlets, so its thermal exergy is the product of the mixing, while what the component does
        not raise is simply blended.

        Writing :math:`x` for a cost variable that merely passes through, the outlet takes the
        mass-weighted mean of the specific costs of the inlets:

        .. math::

            \frac{\dot{C}^{x}_\mathrm{out}}{\dot{E}^{x}_\mathrm{out}}
            = \sum_{i} \frac{\dot{m}_{\mathrm{in},i}}{\sum_{k} \dot{m}_{\mathrm{in},k}}
              \cdot \frac{\dot{C}^{x}_{\mathrm{in},i}}{\dot{E}^{x}_{\mathrm{in},i}}

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
            The updated row index (increased by 2 if chemical exergy is enabled, or by 1 otherwise).
        equations : dict
            Updated dictionary with equation labels.
        """
        # --- Chemical cost auxiliary equation (conditionally added) ---
        if chemical_exergy_enabled:
            set_mixing_cost(A, counter, self.inl.values(), self.outl[0], "CH")
            equations[counter] = {
                "kind": "aux_mixing",
                "objects": [self.name, self.inl[0]["name"], self.inl[1]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            chem_row = 1  # One row added for chemical equation.
        else:
            chem_row = 0  # No row added.

        # Mechanical cost auxiliary equation. Without the split the cost balance of the component is
        # the mixing rule for the physical exergy of the outlet already.
        if split_physical_exergy:
            set_mixing_cost(A, counter + chem_row, self.inl.values(), self.outl[0], "M")
            equations[counter + chem_row] = {
                "kind": "aux_mixing",
                "objects": [self.name, self.inl[0]["name"], self.inl[1]["name"], self.outl[0]["name"]],
                "property": "c_M",
            }

        # Set the right-hand side entries to zero for the added rows.
        num_rows = (1 if chemical_exergy_enabled else 0) + (1 if split_physical_exergy else 0)
        for i in range(num_rows):
            b[counter + i] = 0
        counter += num_rows

        # A vent leaves at the specific costs of the main outlet.
        labels = (["T", "M"] if split_physical_exergy else ["PH"]) + (["CH"] if chemical_exergy_enabled else [])
        for vent in self._vents():
            for label in labels:
                set_equal_specific_cost(A, counter, self.outl[0], vent, label, ref_is_outlet=True)
                b[counter] = 0
                equations[counter] = {
                    "kind": "aux_p_rule",
                    "objects": [self.name, self.outl[0]["name"], vent["name"]],
                    "property": f"c_{label}",
                }
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform exergoeconomic cost balance for the deaerator (mixing component).

        The deaerator is a mixing component where multiple streams combine. The general
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
        The deaerator treats thermal, mechanical, and chemical exergy components
        differently depending on whether inlets are "hot" or "cold" relative to
        the outlet temperature. The distinction ensures proper cost allocation
        for streams that provide heating versus those being heated.

        Future development may include merging profits from dissipative components.
        """
        streams = [(1, inlet) for inlet in self.inl.values()]
        self.C_F = _mixing_fuel_cost(streams, [self.outl[0]], T0, split_physical_exergy)
        for vent in self._vents():
            for x in self._forms(split_physical_exergy):
                main = self.outl[0]
                c_main = main[f"C_{x}"] / main[f"E_{x}"] if main[f"E_{x}"] else 0.0
                self.C_F += c_main * vent["m"] * main[f"e_{x}"] - vent[f"C_{x}"]
        self.C_P = self.C_F + self.Z_costs + getattr(self, "Z_diss", 0)

        self.c_F = self.C_F / self.E_F if self.E_F else np.nan
        self.c_P = self.C_P / self.E_P if self.E_P else np.nan
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F else np.nan
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) else np.nan
