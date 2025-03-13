import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Condenser(Component):
    """
    Condenser component class.

    This class represents a condenser within the system, responsible for
    calculating the exergy balance specific to condensation processes.
    It evaluates the exergy interactions between multiple inlet and outlet
    streams to determine exergy loss and exergy destruction.

    Attributes
    ----------
    E_L : float
        Exergy loss associated with heat transfer (difference in physical exergy 
        between specific outlet and inlet streams).
    E_D : float
        Exergy destruction, calculated as the difference between the primary 
        inlet and outlet streams minus exergy loss (E_L), representing
        irreversibilities in the condensation process.
    E_P : None
        Exergy product, not defined for a condenser as there is no exergy output
        intended for productive use.
    E_F : None
        Exergy fuel, typically undefined for a condenser as it does not involve 
        an external exergy input for production purposes.
    epsilon : None
        Exergy efficiency, not applicable to a condenser due to the nature of 
        exergy interactions focused on loss and destruction.

    Methods
    -------
    __init__(**kwargs)
        Initializes the Condenser component with given parameters.
    calc_exergy_balance(T0, p0)
        Calculates the exergy balance of the condenser.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Condenser component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments passed to the base class initializer.
        """
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float, split_pyhsical_exergy) -> None:
        """
        Calculate the exergy balance of the condenser.

        This method computes exergy loss and exergy destruction based on the inlet
        and outlet streams involved in the condensation process.

        Parameters
        ----------
        T0 : float
            Reference temperature in Kelvin.
        p0 : float
            Reference pressure in Pascals.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Raises
        ------
        ValueError
            If the condenser does not have exactly two inlets and two outlets.

        Calculation Details
        -------------------
        The exergy balance is determined based on exergy transfer due to heat loss (`E_L`)
        and the exergy destruction within the system:

        - **Exergy Loss (E_L)**:
            \[
            E_L = \dot{m}_{\text{out,1}} \cdot (e_{\text{PH,out,1}} - e_{\text{PH,in,1}})
            \]
            Represents the exergy loss due to heat transfer from the process.

        - **Exergy Destruction (E_D)**:
            \[
            E_D = \dot{m}_{\text{out,0}} \cdot (e_{\text{PH,in,0}} - e_{\text{PH,out,0}}) - E_L
            \]
            Accounts for the irreversibilities and losses in the condenser.

        Note
        ----
        Exergy product (E_P) and exergy fuel (E_F) are generally undefined in a
        condenser due to the focus on exergy loss rather than productive exergy usage.
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
        elif all([c["T"] <= T0 for c in self.inl + self.outl]):
            set_thermal_f_cold(A, counter + 0)
            equations[counter] = f"aux_f_rule_cold_{self.name}"
        # Case 3: Mixed temperatures: inl[0]["T"] > T0 and outl[1]["T"] > T0, while outl[0]["T"] <= T0 and inl[1]["T"] <= T0.
        elif (self.inl[0]["T"] > T0 and self.outl[1]["T"] > T0 and
            self.outl[0]["T"] <= T0 and self.inl[1]["T"] <= T0):
            set_thermal_p_rule(A, counter + 0)
            equations[counter] = f"aux_p_rule_{self.name}"
        # Case 4: Mixed temperatures: inl[0]["T"] > T0, inl[1]["T"] <= T0, and both outl[0]["T"] and outl[1]["T"] <= T0.
        elif (self.inl[0]["T"] > T0 and self.inl[1]["T"] <= T0 and
            self.outl[0]["T"] <= T0 and self.outl[1]["T"] <= T0):
            set_thermal_f_cold(A, counter + 0)
            equations[counter] = f"aux_f_rule_cold_{self.name}"
        # Case 5: Mixed temperatures: inl[0]["T"] > T0, inl[1]["T"] <= T0, and both outl[0]["T"] and outl[1]["T"] > T0.
        elif (self.inl[0]["T"] > T0 and self.inl[1]["T"] <= T0 and
            self.outl[0]["T"] > T0 and self.outl[1]["T"] > T0):
            set_thermal_f_hot(A, counter + 0)
            equations[counter] = f"aux_f_rule_hot_{self.name}"
        # Case 6: Mixed temperatures (dissipative case): inl[0]["T"] > T0, inl[1]["T"] <= T0, outl[0]["T"] > T0, and outl[1]["T"] <= T0.
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
