import logging

from exerpy.components.component import Component, component_registry


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
        The definition of exergy fuel and product for this component has not been validated yet. For now, the
        exergy fuel is defined as the inlet streams exergy, and the exergy product is defined as the
        sum of the outlet streams' exergies (i). The exergy destruction is calculated as the difference between the exergy fuel and product.
        .. math::

            \dot{E}_\mathrm{F} = \dot{E}_{in}^\mathrm{PH}

        .. math::

            \dot{E}_\mathrm{P} = \sum_{i=1}^{m} \dot{E}_i^\mathrm{PH}

        """
        # Ensure that the component has at least two outlets and one inlet.
        if len(self.inl) < 1 or len(self.outl) < 2:
            raise ValueError("Flash tank requires one inlet and two outlets.")

        exergy_type = "e_T" if split_physical_exergy else "e_PH"

        # Calculate exergy fuel (E_F) from inlet streams.
        self.E_F = sum(inlet["m"] * inlet[exergy_type] for inlet in self.inl.values())
        # Calculate exergy product (E_P) from outlet streams.
        self.E_P = sum(outlet["m"] * outlet[exergy_type] for outlet in self.outl.values())

        # Exergy destruction and efficiency.
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results.
        logging.info(
            f"Exergy balance of FlashTank {self.name} calculated: "
            f"E_F = {self.E_F:.2f} W, E_P = {self.E_P:.2f} W, E_D = {self.E_D:.2f} W, "
            f"Efficiency = {self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the flash tank.

        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        equality of specific exergy costs between the single inlet stream and each outlet stream.
        Thermal and mechanical costs are always equated; chemical costs are equated only if enabled.

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

        # --- Thermal product‐rule: c_T,out0 = c_T,out1 ---
        #  1/e_T,out0 · C_T,out0  − 1/e_T,out1 · C_T,out1 = 0
        if out0["e_T"] != 0 and out1["e_T"] != 0:
            A[counter, out0["CostVar_index"]["T"]] = 1.0 / out0["e_T"]
            A[counter, out1["CostVar_index"]["T"]] = -1.0 / out1["e_T"]
        elif out0["e_T"] == 0 and out1["e_T"] != 0:
            A[counter, out0["CostVar_index"]["T"]] = 1.0
        elif out0["e_T"] != 0 and out1["e_T"] == 0:
            A[counter, out1["CostVar_index"]["T"]] = 1.0
        else:
            A[counter, out0["CostVar_index"]["T"]] = 1.0
            A[counter, out1["CostVar_index"]["T"]] = -1.0

        equations[counter] = {
            "kind": "aux_p_rule",
            "objects": [self.name, out0["name"], out1["name"]],
            "property": "c_T",
        }
        b[counter] = 0.0
        counter += 1

        # --- Mechanical equality: c_M,inlet = c_M,outlet_i for each outlet ---
        for out in (out0, out1):
            if inlet["e_M"] != 0 and out["e_M"] != 0:
                A[counter, inlet["CostVar_index"]["M"]] = 1.0 / inlet["e_M"]
                A[counter, out["CostVar_index"]["M"]] = -1.0 / out["e_M"]
            elif inlet["e_M"] == 0 and out["e_M"] != 0:
                A[counter, inlet["CostVar_index"]["M"]] = 1.0
            elif inlet["e_M"] != 0 and out["e_M"] == 0:
                A[counter, out["CostVar_index"]["M"]] = 1.0
            else:
                A[counter, inlet["CostVar_index"]["M"]] = 1.0
                A[counter, out["CostVar_index"]["M"]] = -1.0

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
                if inlet["e_CH"] != 0 and out["e_CH"] != 0:
                    A[counter, inlet["CostVar_index"]["CH"]] = 1.0 / inlet["e_CH"]
                    A[counter, out["CostVar_index"]["CH"]] = -1.0 / out["e_CH"]
                elif inlet["e_CH"] == 0 and out["e_CH"] != 0:
                    A[counter, inlet["CostVar_index"]["CH"]] = 1.0
                elif inlet["e_CH"] != 0 and out["e_CH"] == 0:
                    A[counter, out["CostVar_index"]["CH"]] = 1.0
                else:
                    A[counter, inlet["CostVar_index"]["CH"]] = 1.0
                    A[counter, out["CostVar_index"]["CH"]] = -1.0

                equations[counter] = {
                    "kind": "aux_equality",
                    "objects": [self.name, inlet["name"], out["name"]],
                    "property": "c_CH",
                }
                b[counter] = 0.0
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""
        Perform exergoeconomic cost balance for the flash tank.

        The general cost balance is:

        .. math::
            \dot{C}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            - \sum_{i=1}^{n} \dot{C}^{\mathrm{T}}_{\mathrm{out},i}
            - \sum_{i=1}^{n} \dot{C}^{\mathrm{M}}_{\mathrm{out},i}
            + \dot{Z}
            = 0

        Parameters
        ----------
        T0 : float
            Ambient temperature
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        """

        # Calculate total cost of inlet streams (thermal + mechanical [+ chemical if enabled])
        C_F = 0.0
        for inlet in self.inl.values():
            C_F += inlet["m"] * (inlet["c_T"] + inlet["c_M"])
            if chemical_exergy_enabled:
                C_F += inlet["m"] * inlet["c_CH"]
        self.C_F = C_F

        # Calculate total cost of outlet streams (thermal + mechanical [+ chemical if enabled])
        C_P = 0.0
        for outlet in self.outl.values():
            C_P += outlet["m"] * (outlet["c_T"] + outlet["c_M"])
            if chemical_exergy_enabled:
                C_P += outlet["m"] * outlet["c_CH"]
        self.C_P = C_P

        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
