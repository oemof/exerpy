import logging

import numpy as np

from exerpy.components.component import Component, component_registry


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
    The exergy analysis accounts for physical exergy only. The equations for exergy
    product and fuel are defined based on temperature relationships:

    .. math::
        \displaystyle
        \dot E_{P} =
        \begin{cases}
            \displaystyle
            \sum_{i}\dot m_{i}\,\bigl(e_{\mathrm{out}}^{\mathrm{PH}}
            -e_{\mathrm{in},i}^{\mathrm{PH}}\bigr),
            \quad \text{if }T_{\mathrm{in},i}<T_{\mathrm{out}}\text{ and }T_{\mathrm{in},i}\ge T_{0},\\[8pt]
            \displaystyle
            \sum_{i}\dot m_{i}\,e_{\mathrm{out}}^{\mathrm{PH}},
            \quad \text{if }T_{\mathrm{in},i}<T_{\mathrm{out}}\text{ and }T_{\mathrm{in},i}<T_{0},\\[8pt]
            \displaystyle
            \text{not defined (nan)},
            \quad \text{if }T_{\mathrm{out}}=T_{0},\\[8pt]
            \displaystyle
            \sum_{i}\dot m_{i}\,e_{\mathrm{out}}^{\mathrm{PH}},
            \quad \text{if }T_{\mathrm{in},i}>T_{\mathrm{out}}\text{ and }T_{\mathrm{in},i}\ge T_{0},\\[8pt]
            \displaystyle
            \sum_{i}\dot m_{i}\,\bigl(e_{\mathrm{out}}^{\mathrm{PH}}
            -e_{\mathrm{in},i}^{\mathrm{PH}}\bigr),
            \quad \text{if }T_{\mathrm{in},i}>T_{\mathrm{out}}\text{ and }T_{\mathrm{in},i}<T_{0}.
        \end{cases}

    .. math::
        \displaystyle
        \dot E_{F} =
        \begin{cases}
            \displaystyle
            \sum_{i}\dot m_{i}\,\bigl(e_{\mathrm{in},i}^{\mathrm{PH}}
            -e_{\mathrm{out}}^{\mathrm{PH}}\bigr),
            \quad \text{if }T_{\mathrm{out}}>T_{0}\text{ and }T_{\mathrm{in},i}>T_{\mathrm{out}},\\[8pt]
            \displaystyle
            \sum_{i}\dot m_{i}\,e_{\mathrm{in},i}^{\mathrm{PH}},
            \quad \text{if }T_{\mathrm{out}}>T_{0}\text{ and }T_{\mathrm{in},i}<T_{\mathrm{out}}
            \text{ and }T_{\mathrm{in},i}<T_{0},\\[8pt]
            \displaystyle
            \sum_{i}\dot m_{i}\,e_{\mathrm{in},i}^{\mathrm{PH}},
            \quad \text{if }T_{\mathrm{out}}=T_{0},\\[8pt]
            \displaystyle
            \sum_{i}\dot m_{i}\,e_{\mathrm{in},i}^{\mathrm{PH}},
            \quad \text{if }T_{\mathrm{out}}<T_{0}\text{ and }T_{\mathrm{in},i}>T_{\mathrm{out}},\\[8pt]
            \displaystyle
            \sum_{i}\dot m_{i}\,\bigl(e_{\mathrm{in},i}^{\mathrm{PH}}
            -e_{\mathrm{out}}^{\mathrm{PH}}\bigr),
            \quad \text{if }T_{\mathrm{out}}<T_{0}\text{ and }T_{\mathrm{in},i}<T_{\mathrm{out}}.
        \end{cases}

    """

    def __init__(self, **kwargs):
        r"""Initialize deaerator component with given parameters."""
        super().__init__(**kwargs)

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

        self.E_P = 0
        self.E_F = 0

        # Case 1: Outlet temperature is greater than T0
        if self.outl[0]["T"] > T0:
            for _, inlet in self.inl.items():
                if inlet["T"] < self.outl[0]["T"]:  # Tin < Tout
                    if inlet["T"] >= T0:  # and Tin >= T0
                        self.E_P += inlet["m"] * (self.outl[0]["e_PH"] - inlet["e_PH"])
                    else:  # and Tin < T0
                        self.E_P += inlet["m"] * self.outl[0]["e_PH"]
                        self.E_F += inlet["m"] * inlet["e_PH"]
                else:  # Tin > Tout
                    self.E_F += inlet["m"] * (inlet["e_PH"] - self.outl[0]["e_PH"])

        # Case 2: Outlet temperature is equal to T0
        elif self.outl[0]["T"] == T0:
            self.E_P = np.nan
            for _, inlet in self.inl.items():
                self.E_F += inlet["m"] * inlet["e_PH"]

        # Case 3: Outlet temperature is less than T0
        else:
            for _, inlet in self.inl.items():
                if inlet["T"] > self.outl[0]["T"]:  # Tin > Tout
                    if inlet["T"] >= T0:  # and Tin >= T0
                        self.E_P += inlet["m"] * self.outl[0]["e_PH"]
                        self.E_F += inlet["m"] * inlet["e_PH"]
                    else:  # and Tin < T0
                        self.E_P += inlet["m"] * (self.outl[0]["e_PH"] - inlet["e_PH"])
                else:  # Tin < Tout
                    self.E_F += inlet["m"] * (inlet["e_PH"] - self.outl[0]["e_PH"])

        # Calculate exergy destruction and efficiency
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Exergy balance of Deaerator {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the deaerator.

        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:

        (1) Mixing equation for chemical exergy costs (if enabled):

        - The outlet's specific chemical exergy cost is calculated as a mass-weighted average of the inlet streams' specific chemical exergy costs

        - This enforces proper chemical exergy cost distribution through the deaerator

        (2) Mixing equation for mechanical exergy costs:

        - The outlet's specific mechanical exergy cost is calculated as a mass-weighted average of the inlet streams' specific mechanical exergy costs

        - This ensures mechanical exergy costs are properly conserved in the mixing process

        Both equations implement the proportionality rule for mixing processes where
        the outlet's specific costs should reflect the contribution of each inlet stream.

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
            if self.outl[0]["e_CH"] != 0:
                A[counter, self.outl[0]["CostVar_index"]["CH"]] = -1 / self.outl[0]["E_CH"]
                # Iterate over inlet streams for chemical mixing.
                for inlet in self.inl.values():
                    if inlet["e_CH"] != 0:
                        A[counter, inlet["CostVar_index"]["CH"]] = inlet["m"] / (self.outl[0]["m"] * inlet["E_CH"])
                    else:
                        A[counter, inlet["CostVar_index"]["CH"]] = 1
            else:
                # Outlet chemical exergy is zero: assign fallback for all inlets.
                for inlet in self.inl.values():
                    A[counter, inlet["CostVar_index"]["CH"]] = 1
            equations[counter] = {
                "kind": "aux_mixing",
                "objects": [self.name, self.inl[0]["name"], self.inl[1]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            chem_row = 1  # One row added for chemical equation.
        else:
            chem_row = 0  # No row added.

        # --- Mechanical cost auxiliary equation ---
        if self.outl[0]["e_M"] != 0:
            A[counter + chem_row, self.outl[0]["CostVar_index"]["M"]] = -1 / self.outl[0]["E_M"]
            # Iterate over inlet streams for mechanical mixing.
            for inlet in self.inl.values():
                if inlet["e_M"] != 0:
                    A[counter + chem_row, inlet["CostVar_index"]["M"]] = inlet["m"] / (self.outl[0]["m"] * inlet["E_M"])
                else:
                    A[counter + chem_row, inlet["CostVar_index"]["M"]] = 1
        else:
            for inlet in self.inl.values():
                A[counter + chem_row, inlet["CostVar_index"]["M"]] = 1
        equations[counter + chem_row] = {
            "kind": "aux_mixing",
            "objects": [self.name, self.inl[0]["name"], self.inl[1]["name"], self.outl[0]["name"]],
            "property": "c_M",
        }

        # Set the right-hand side entries to zero for the added rows.
        if chemical_exergy_enabled:
            b[counter] = 0
            b[counter + 1] = 0
            counter += 2  # Two rows were added.
        else:
            b[counter] = 0
            counter += 1  # Only one row was added.

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
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

        The product is defined as the outlet stream. The fuel consists of all inlet
        streams, with specific treatment depending on temperature levels. The cost
        balance is closed using:

        .. math::
            \dot{C}_{\mathrm{P}} = \dot{C}_{\mathrm{F}} + \dot{Z}

        **Case 1: Outlet above ambient temperature**

        When :math:`T_{\mathrm{out}} > T_0`:

        For cold inlets (:math:`T_{\mathrm{in}} < T_{\mathrm{out}}`):

        .. math::
            \dot{C}_{\mathrm{F,cold}} = \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{CH}}_{\mathrm{in}}

        For hot inlets (:math:`T_{\mathrm{in}} \geq T_{\mathrm{out}}`):

        .. math::
            \dot{C}_{\mathrm{F,hot}} = -\dot{m}_{\mathrm{in}} \cdot c^{\mathrm{T}}_{\mathrm{in}}
            \cdot e^{\mathrm{T}}_{\mathrm{in}}
            + \left(\dot{C}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{CH}}_{\mathrm{in}}\right)

        Total fuel cost:

        .. math::
            \dot{C}_{\mathrm{F}} = \sum \dot{C}_{\mathrm{F,cold}}
            + \sum \dot{C}_{\mathrm{F,hot}}
            - \dot{C}^{\mathrm{M}}_{\mathrm{out}}
            - \dot{C}^{\mathrm{CH}}_{\mathrm{out}}

        **Case 2: Outlet at ambient temperature (dissipative)**

        When :math:`|T_{\mathrm{out}} - T_0| < 10^{-6}`:

        .. math::
            \dot{C}_{\mathrm{F}} = \sum_{\mathrm{in}} \dot{C}^{\mathrm{TOT}}_{\mathrm{in}}

        **Case 3: Outlet below ambient temperature**

        When :math:`T_{\mathrm{out}} < T_0`:

        For hot inlets (:math:`T_{\mathrm{in}} > T_{\mathrm{out}}`):

        .. math::
            \dot{C}_{\mathrm{F,hot}} = \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{CH}}_{\mathrm{in}}

        For cold inlets (:math:`T_{\mathrm{in}} \leq T_{\mathrm{out}}`):

        .. math::
            \dot{C}_{\mathrm{F,cold}} = -\dot{m}_{\mathrm{in}} \cdot c^{\mathrm{T}}_{\mathrm{in}}
            \cdot e^{\mathrm{T}}_{\mathrm{in}}
            + \left(\dot{C}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{CH}}_{\mathrm{in}}\right)

        Total fuel cost:

        .. math::
            \dot{C}_{\mathrm{F}} = \sum \dot{C}_{\mathrm{F,hot}}
            + \sum \dot{C}_{\mathrm{F,cold}}
            - \dot{C}^{\mathrm{M}}_{\mathrm{out}}
            - \dot{C}^{\mathrm{CH}}_{\mathrm{out}}

        **Calculated exergoeconomic indicators:**

        .. math::
            c_{\mathrm{F}} = \frac{\dot{C}_{\mathrm{F}}}{\dot{E}_{\mathrm{F}}}

        .. math::
            c_{\mathrm{P}} = \frac{\dot{C}_{\mathrm{P}}}{\dot{E}_{\mathrm{P}}}

        .. math::
            \dot{C}_{\mathrm{D}} = c_{\mathrm{F}} \cdot \dot{E}_{\mathrm{D}}

        .. math::
            r = \frac{c_{\mathrm{P}} - c_{\mathrm{F}}}{c_{\mathrm{F}}}

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

        Notes
        -----
        The deaerator treats thermal, mechanical, and chemical exergy components
        differently depending on whether inlets are "hot" or "cold" relative to
        the outlet temperature. The distinction ensures proper cost allocation
        for streams that provide heating versus those being heated.

        Future development may include merging profits from dissipative components.
        """
        self.C_P = 0
        self.C_F = 0
        if self.outl[0]["T"] > T0:
            for i in self.inl:
                if i["T"] < self.outl[0]["T"]:
                    # cold inlets
                    self.C_F += i["C_M"] + i["C_CH"]
                else:
                    # hot inlets
                    self.C_F += -i["M"] * i["C_T"] * i["e_T"] + (i["C_T"] + i["C_M"] + i["C_CH"])
            self.C_F += -self.outl[0]["C_M"] - self.outl[0]["C_CH"]
        elif self.outl[0]["T"] - 1e-6 < T0 and self.outl[0]["T"] + 1e-6 > T0:
            # dissipative
            for i in self.inl:
                self.C_F += i["C_TOT"]
        else:
            for i in self.inl:
                if i["T"] > self.outl[0]["T"]:
                    # hot inlets
                    self.C_F += i["C_M"] + i["C_CH"]
                else:
                    # cold inlets
                    self.C_F += -i["M"] * i["C_T"] * i["e_T"] + (i["C_T"] + i["C_M"] + i["C_CH"])
            self.C_F += -self.outl[0]["C_M"] - self.outl[0]["C_CH"]
        self.C_P = self.C_F + self.Z_costs  # +1/num_serving_comps * C_diff
        # ToDo: add case that merge profits from dissipative component(s)

        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
