import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Condenser(Component):
    r"""
    Class for exergy and exergoeconomic analysis of condensers (only dissipative).

    This class performs exergy and exergoeconomic analysis calculations for condenser components,
    accounting for two inlet and two outlet streams. This class should be used only for dissipative 
    condensers. For non-dissipative condensers, use components that are modeled in ExerPy using the 
    `HeatExchanger` class.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\mathrm{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\mathrm{W}`.
    E_L : float
        Exergy loss of the component :math:`\dot{E}_\mathrm{L}` in :math:`\mathrm{W}`.
    inl : dict
        Dictionary containing inlet stream data with mass flows and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with mass flows and specific exergies.
    Z_costs : float
        Investment cost rate of the component in currency/h.
    C_F : float
        Cost of fuel stream :math:`\dot{C}_F` in currency/h.
    C_D : float
        Cost of exergy destruction :math:`\dot{C}_D` in currency/h.
    c_F : float
        Specific cost of fuel stream (currency per unit exergy).
    f : float
        Exergoeconomic factor, :math:`\dot{Z}/(\dot{Z} + \dot{C}_D)`.
    Ex_C_col : dict
        Custom cost coefficients collection passed via `kwargs`.
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the condenser component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate in currency/h, default 0.0
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the condenser.

        In order to distinguish between the exergetic destruction because of heat transfer
        and the exergetic loss (coldf stream leaving the system) the exergetic losses and
        destruction are calculated as follows:

        .. math::

            \dot{E}_{\mathrm{L}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}

        .. math::

            \dot{E}_{\mathrm{D}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}
            - \dot{E}_{\mathrm{L}}

        However, these value can only be accessed via the attributes `E_L` and `E_D` of the component. 
        In the table of final results of the exergy analysis of the system, the exergy destruction of 
        the condenser is counted as the exergy loss and the exergetic destruction due to heat transfer.

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
            If required inlets or outlets are missing.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 2:
            raise ValueError("Condenser requires two inlets and two outlets.")
        
        # Calculate exergy loss (E_L) for the heat transfer process
        self.E_L = self.outl[1]['m'] * (self.outl[1]['e_PH'] - self.inl[1]['e_PH'])

        # Calculate exergy destruction (E_D)
        self.E_D = self.outl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH']) - self.E_L

        # Exergy fuel and product are not typically defined for a condenser
        self.E_F = None
        self.E_P = None
        self.epsilon = None

        # Log the exergy balance results
        logging.info(f"Condenser exergy balance calculated: E_D={self.E_D}, E_L={self.E_L}")


    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""
        Add auxiliary cost equations for the condenser.

        This method appends rows to the cost matrix to enforce:

        Case 1: All streams above ambient temperature

        F rule for thermal exergy of the hot stream:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{out},1}}\,\dot{C}^{\mathrm{T}}_{\mathrm{out},1}
            + \frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{in},1}}\,\dot{C}^{\mathrm{T}}_{\mathrm{in},1}
            = 0

        Case 2: All streams below or equal to ambient temperature

        F rule for thermal exergy of the cold stream:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{out},2}}\,\dot{C}^{\mathrm{T}}_{\mathrm{out},2}
            + \frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{in},2}}\,\dot{C}^{\mathrm{T}}_{\mathrm{in},2}
            = 0

        Case 3: Both stream crossing ambient temperature

        P rule for thermal exergy of both outlets:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{out},1}}\,\dot{C}^{\mathrm{T}}_{\mathrm{out},1}
            + \frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{out},2}}\,\dot{C}^{\mathrm{T}}_{\mathrm{out},2}
            = 0

        Case 4: Only the hot inlet above ambient temperature

        F rule for thermal exergy of the cold stream:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{out},2}}\,\dot{C}^{\mathrm{T}}_{\mathrm{out},2}
            + \frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{in},2}}\,\dot{C}^{\mathrm{T}}_{\mathrm{in},2}
            = 0

        Case 5: Only the cold inlet below ambient temperature

        F rule for thermal exergy of the hot stream:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{out},1}}\,\dot{C}^{\mathrm{T}}_{\mathrm{out},1}
            + \frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{in},1}}\,\dot{C}^{\mathrm{T}}_{\mathrm{in},1}
            = 0

        Case 6: Hot stream always above and cold stream always below ambiente temperature (dissipative case): 

        The dissipative is not handeld here!

        For all cases, the mechanical and chemical exergy costs are handled as follows:

        F rule for mechanical exergy of the hot stream:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{M}}_{\mathrm{out},i}}\,\dot{C}^{\mathrm{M}}_{\mathrm{out},i}
            + \frac{1}{\dot{E}^{\mathrm{M}}_{\mathrm{in},i}}\,\dot{C}^{\mathrm{M}}_{\mathrm{in},i}
            = 0

        F rule for chemical exergy on hot branch:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{CH}}_{\mathrm{out},i}}\,\dot{C}^{\mathrm{CH}}_{\mathrm{out},i}
            + \frac{1}{\dot{E}^{\mathrm{CH}}_{\mathrm{in},i}}\,\dot{C}^{\mathrm{CH}}_{\mathrm{in},i}
            = 0

        Parameters
        ----------
        A : numpy.ndarray
            Current cost matrix.
        b : numpy.ndarray
            Current RHS vector.
        counter : int
            Starting row index for auxiliary equations.
        T0 : float
            Ambient temperature (K).
        equations : dict or list
            Structure for equation labels.
        chemical_exergy_enabled : bool
            Must be True to include chemical exergy mixing.

        Returns
        -------
        A : numpy.ndarray
            Updated cost matrix.
        b : numpy.ndarray
            Updated RHS vector.
        counter : int
            Updated row index after adding equations.
        equations : dict or list
            Updated labels.

        Raises
        ------
        ValueError
            If required cost variable indices are missing.
        """
        # Equality equation for mechanical and chemical exergy costs.
        def set_equal(A, row, in_item, out_item, var):
            if in_item["e_" + var] != 0 and out_item["e_" + var] != 0:
                A[row, in_item["CostVar_index"][var]] = 1 / in_item["e_" + var]
                A[row, out_item["CostVar_index"][var]] = -1 / out_item["e_" + var]
            elif in_item["e_" + var] == 0 and out_item["e_" + var] != 0:
                A[row, in_item["CostVar_index"][var]] = 1
            elif in_item["e_" + var] != 0 and out_item["e_" + var] == 0:
                A[row, out_item["CostVar_index"][var]] = 1
            else:
                A[row, in_item["CostVar_index"][var]] = 1
                A[row, out_item["CostVar_index"][var]] = -1

        # Thermal fuel rule on hot stream: c_T_in0 = c_T_out0.
        def set_thermal_f_hot(A, row):
            if self.inl[0]["e_T"] != 0 and self.outl[0]["e_T"] != 0:
                A[row, self.inl[0]["CostVar_index"]["T"]] = 1 / self.inl[0]["E_T"]
                A[row, self.outl[0]["CostVar_index"]["T"]] = -1 / self.outl[0]["E_T"]
            elif self.inl[0]["e_T"] == 0 and self.outl[0]["e_T"] != 0:
                A[row, self.inl[0]["CostVar_index"]["T"]] = 1
            elif self.inl[0]["e_T"] != 0 and self.outl[0]["e_T"] == 0:
                A[row, self.outl[0]["CostVar_index"]["T"]] = 1
            else:
                A[row, self.inl[0]["CostVar_index"]["T"]] = 1
                A[row, self.outl[0]["CostVar_index"]["T"]] = -1

        # Thermal fuel rule on cold stream: c_T_in1 = c_T_out1.
        def set_thermal_f_cold(A, row):
            if self.inl[1]["e_T"] != 0 and self.outl[1]["e_T"] != 0:
                A[row, self.inl[1]["CostVar_index"]["T"]] = 1 / self.inl[1]["E_T"]
                A[row, self.outl[1]["CostVar_index"]["T"]] = -1 / self.outl[1]["E_T"]
            elif self.inl[1]["e_T"] == 0 and self.outl[1]["e_T"] != 0:
                A[row, self.inl[1]["CostVar_index"]["T"]] = 1
            elif self.inl[1]["e_T"] != 0 and self.outl[1]["e_T"] == 0:
                A[row, self.outl[1]["CostVar_index"]["T"]] = 1
            else:
                A[row, self.inl[1]["CostVar_index"]["T"]] = 1
                A[row, self.outl[1]["CostVar_index"]["T"]] = -1

        # Thermal product rule: Equate the two outlet thermal costs (c_T_out0 = c_T_out1).
        def set_thermal_p_rule(A, row):
            if self.outl[0]["e_T"] != 0 and self.outl[1]["e_T"] != 0:
                A[row, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["E_T"]
                A[row, self.outl[1]["CostVar_index"]["T"]] = -1 / self.outl[1]["E_T"]
            elif self.outl[0]["e_T"] == 0 and self.outl[1]["e_T"] != 0:
                A[row, self.outl[0]["CostVar_index"]["T"]] = 1
            elif self.outl[0]["e_T"] != 0 and self.outl[1]["e_T"] == 0:
                A[row, self.outl[1]["CostVar_index"]["T"]] = 1
            else:
                A[row, self.outl[0]["CostVar_index"]["T"]] = 1
                A[row, self.outl[1]["CostVar_index"]["T"]] = -1

        # Determine the thermal case based on temperatures.
        # Case 1: All temperatures > T0.
        if all([c["T"] > T0 for c in list(self.inl.values()) + list(self.outl.values())]):
            set_thermal_f_hot(A, counter + 0)
            equations[counter] = f"aux_f_rule_hot_{self.name}"
        # Case 2: All temperatures <= T0.
        elif all([c["T"] <= T0 for c in list(self.inl.values()) + list(self.outl.values())]):
            set_thermal_f_cold(A, counter + 0)
            equations[counter] = f"aux_f_rule_cold_{self.name}"
            logging.warning(
                f"All temperatures in {self.name} are below ambient temperature. " \
                "This is not a typical case for a dissipative condenser."
            )
        # Case 3: Both stream crossing T0 (hot inlet and cold outlet > T0, hot outlet and cold inlet <= T0)
        elif (self.inl[0]["T"] > T0 and self.outl[1]["T"] > T0 and
            self.outl[0]["T"] <= T0 and self.inl[1]["T"] <= T0):
            set_thermal_p_rule(A, counter + 0)
            equations[counter] = f"aux_p_rule_{self.name}"
            logging.warning(
                f"Hot inlet and cold outlet in {self.name} are above ambient temperature, " \
                "while hot outlet and cold inlet are below. This is not a typical case for a dissipative condenser." \
                "The exergoeconomic analysis is counting the outlets as products."
            )
        # Case 4: Only hot inlet > T0
        elif (self.inl[0]["T"] > T0 and self.inl[1]["T"] <= T0 and
            self.outl[0]["T"] <= T0 and self.outl[1]["T"] <= T0):
            set_thermal_f_cold(A, counter + 0)
            equations[counter] = f"aux_f_rule_cold_{self.name}"
            logging.warning(
                f"Cold inlet in {self.name} is below ambient temperature. " \
                "This is not a typical case for a dissipative condenser."
            )
        # Case 5: Only cold inlet <= T0
        elif (self.inl[0]["T"] > T0 and self.inl[1]["T"] <= T0 and
            self.outl[0]["T"] > T0 and self.outl[1]["T"] > T0):
            set_thermal_f_hot(A, counter + 0)
            equations[counter] = f"aux_f_rule_hot_{self.name}"
            logging.warning(
                f"Cold inlet in {self.name} is below ambient temperature. " \
                "This is not a typical case for a dissipative condenser."
            )
        # Case 6: hot stream always above T0, cold stream always below T0
        elif (self.inl[0]["T"] > T0 and self.inl[1]["T"] <= T0 and
            self.outl[0]["T"] > T0 and self.outl[1]["T"] <= T0):
            print("you shouldn't see this")
            return
        # Case 7: Default case.
        else:
            set_thermal_f_hot(A, counter + 0)
            equations[counter] = f"aux_f_rule_hot_{self.name}"
        
        # Mechanical equations (always added)
        set_equal(A, counter + 1, self.inl[0], self.outl[0], "M")
        set_equal(A, counter + 2, self.inl[1], self.outl[1], "M")
        equations[counter + 1] = f"aux_equality_mech_{self.outl[0]['name']}"
        equations[counter + 2] = f"aux_equality_mech_{self.outl[1]['name']}"
        
        # Only add chemical auxiliary equations if chemical exergy is enabled.
        if chemical_exergy_enabled:
            set_equal(A, counter + 3, self.inl[0], self.outl[0], "CH")
            set_equal(A, counter + 4, self.inl[1], self.outl[1], "CH")
            equations[counter + 3] = f"aux_equality_chem_{self.outl[0]['name']}"
            equations[counter + 4] = f"aux_equality_chem_{self.outl[1]['name']}"
            num_aux_eqs = 5
        else:
            # Skip chemical auxiliary equations.
            num_aux_eqs = 3

        for i in range(num_aux_eqs):
            b[counter + i] = 0

        return A, b, counter + num_aux_eqs, equations
    
    def exergoeconomic_balance(self, T0):
        r"""
        Perform exergoeconomic cost balance for the condenser.

        Even though this class should only consider dissipative condensers, the exergoeconomic balance is
        still performed to ensure consistency. Please note that same of the following cases cases are not 
        typical for dissipative condensers. This may change in a future version of ExerPy.

        .. math::
            \dot{C}^{\mathrm{T}}_{\mathrm{in},1}
            + \dot{C}^{\mathrm{M}}_{\mathrm{in},1}
            + \dot{C}^{\mathrm{T}}_{\mathrm{in},2}
            + \dot{C}^{\mathrm{M}}_{\mathrm{in},2}
            - \dot{C}^{\mathrm{T}}_{\mathrm{out},1}
            - \dot{C}^{\mathrm{M}}_{\mathrm{out},1}
            - \dot{C}^{\mathrm{T}}_{\mathrm{out},2}
            - \dot{C}^{\mathrm{M}}_{\mathrm{out},2}
            + \dot{Z}
            = 0

        In case the chemical exergy of the streams is know:

        .. math::
            \dot{C}^{\mathrm{CH}}_{\mathrm{in},1} =
            \dot{C}^{\mathrm{CH}}_{\mathrm{out},1}

        .. math::
            \dot{C}^{\mathrm{CH}}_{\mathrm{in},2} =
            \dot{C}^{\mathrm{CH}}_{\mathrm{out},2}

        This method computes cost coefficients and ratios:

        Case 1: All streams above ambient temperature

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\mathrm{out},2}
                    - \dot{C}^{\mathrm{T}}_{\mathrm{in},2}

        .. math::
            \dot{C}_F = \dot{C}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{C}^{\mathrm{PH}}_{\mathrm{out},1}
                    + \bigl(\dot{C}^{\mathrm{M}}_{\mathrm{in},2}
                            - \dot{C}^{\mathrm{M}}_{\mathrm{out},2}\bigr)

        Case 2: All streams below or equal to ambient temperature

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\mathrm{out},1}
                    - \dot{C}^{\mathrm{T}}_{\mathrm{in},1}

        .. math::
            \dot{C}_F = \dot{C}^{\mathrm{PH}}_{\mathrm{in},2}
                    - \dot{C}^{\mathrm{PH}}_{\mathrm{out},2}
                    + \bigl(\dot{C}^{\mathrm{M}}_{\mathrm{in},1}
                            - \dot{C}^{\mathrm{M}}_{\mathrm{out},1}\bigr)

        Case 3: Both stream crossing ambient temperature

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\mathrm{out},1}
                    + \dot{C}^{\mathrm{T}}_{\mathrm{out},2}

        .. math::
            \dot{C}_F = \dot{C}^{\mathrm{PH}}_{\mathrm{in},1}
                    + \dot{C}^{\mathrm{PH}}_{\mathrm{in},2}
                    - \bigl(\dot{C}^{\mathrm{M}}_{\mathrm{out},1}
                            + \dot{C}^{\mathrm{M}}_{\mathrm{out},2}\bigr)

        Case 4: Only the hot inlet above ambient temperature

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\mathrm{out},1}

        .. math::
            \dot{C}_F = \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{in},1}
                            + \dot{C}^{\mathrm{PH}}_{\mathrm{in},2}\bigr)
                    - \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{out},2}
                            + \dot{C}^{\mathrm{M}}_{\mathrm{out},1}\bigr)

        Case 5: Only the cold inlet below ambient temperature

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\mathrm{out},2}

        .. math::
            \dot{C}_F = \dot{C}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{C}^{\mathrm{PH}}_{\mathrm{out},1}
                    + \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{in},2}
                            - \dot{C}^{\mathrm{M}}_{\mathrm{out},2}\bigr)

        Case 6: Hot stream always above and cold stream always below ambient temperature (dissipative case):

        .. math::
            \dot{C}_P = \mathrm{NaN}

        .. math::
            \dot{C}_F = \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{C}^{\mathrm{PH}}_{\mathrm{out},1}\bigr)
            - \dot{C}^{\mathrm{PH}}_{\mathrm{out},2}
            + \dot{C}^{\mathrm{PH}}_{\mathrm{in},2}
        
        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        """
        if all([c["T"] > T0 for c in list(self.inl.values()) + list(self.outl.values())]):
            self.C_P = self.outl[1]["C_T"] - self.inl[1]["C_T"]
            self.C_F = self.inl[0]["C_PH"] - self.outl[0]["C_PH"] + (
                self.inl[1]["C_M"] - self.outl[1]["C_M"])
        elif all([c["T"] <= T0 for c in list(self.inl.values()) + list(self.outl.values())]):
            self.C_P = self.outl[0]["C_T"] - self.inl[0]["C_T"]
            self.C_F = self.inl[1]["C_PH"] - self.outl[1]["C_PH"] + (
                self.inl[0]["C_M"] - self.outl[0]["C_M"])
        elif (self.inl[0]["T"] > T0 and self.outl[1]["T"] > T0 and
              self.outl[0]["T"] <= T0 and self.inl[1]["T"] <= T0):
            self.C_P = self.outl[0]["C_T"] + self.outl[1]["C_T"]
            self.C_F = self.inl[0]["C_PH"] + self.inl[1]["C_PH"] - (
                self.outl[0]["C_M"] + self.outl[1]["C_M"])
        elif (self.inl[0]["T"] > T0 and self.inl[1]["T"] <= T0 and
              self.outl[0]["T"] <= T0 and self.outl[1]["T"] <= T0):
            self.C_P = self.outl[0]["C_T"]
            self.C_F = self.inl[0]["C_PH"] + self.inl[1]["C_PH"] - (
               self.outl[1]["C_PH"] + self.outl[0]["C_M"])
        else:
            self.C_P = self.outl[1]["C_T"]
            self.C_F = self.inl[0]["C_PH"] - self.outl[0]["C_PH"] + (
                self.inl[1]["C_PH"] - self.outl[1]["C_M"])

        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
