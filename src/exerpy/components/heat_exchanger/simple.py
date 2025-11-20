import logging

import numpy as np

from exerpy.components.component import Component, component_registry


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
    """

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
        """
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the simple heat exchanger.

        **Heat release** :math:\dot{Q}<0

        Case 1: Both streams above ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Case 2: Inlet above and outlet below ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

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

        Case 1: Both streams above ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        Case 2: Inlet below and outlet above ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
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

        Case 3: Both streams below ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{in}}\bigr)

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}

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
            logging.error(msg)
            raise ValueError(msg)
        if len(self.inl) > 2 or len(self.outl) > 2:
            msg = "SimpleHeatExchanger requires a maximum of two inlets and two outlets."
            logging.error(msg)
            raise ValueError(msg)

        # Extract inlet and outlet streams
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Calculate heat transfer Q
        Q = outlet["m"] * outlet["h"] - inlet["m"] * inlet["h"]

        # Initialize E_P and E_F
        self.E_P = 0.0
        self.E_F = 0.0

        # Case 1: Heat is released (Q < 0)
        if Q < 0:
            if inlet["T"] >= T0 and outlet["T"] >= T0:
                if split_physical_exergy:
                    self.E_P = (
                        np.nan if getattr(self, "dissipative", False) else inlet["m"] * (inlet["e_T"] - outlet["e_T"])
                    )
                else:
                    self.E_P = (
                        np.nan if getattr(self, "dissipative", False) else inlet["m"] * (inlet["e_PH"] - outlet["e_PH"])
                    )
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
                    self.E_P = outlet["m"] * outlet["e_PH"]
                    self.E_F = inlet["m"] * inlet["e_PH"]

            elif inlet["T"] <= T0 and outlet["T"] < T0:
                if split_physical_exergy:
                    self.E_P = outlet["m"] * (outlet["e_T"] - inlet["e_T"])
                    self.E_F = self.E_P + inlet["m"] * (inlet["e_M"] - outlet["m"] * outlet["e_M"])
                else:
                    self.E_P = (
                        np.nan
                        if getattr(self, "dissipative", False)
                        else outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
                    )
                    self.E_F = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])

            else:
                # Unimplemented corner case
                logging.warning("SimpleHeatExchanger: unimplemented case (Q < 0, T_in < T0 < T_out?).")
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 2: Heat is added (Q > 0)
        elif Q > 0:
            if inlet["T"] >= T0 and outlet["T"] >= T0:
                if split_physical_exergy:
                    self.E_P = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
                    self.E_F = outlet["m"] * (outlet["e_T"] - inlet["e_T"])
                else:
                    self.E_P = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
                    self.E_F = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
            elif inlet["T"] < T0 and outlet["T"] >= T0:
                if split_physical_exergy:
                    self.E_P = outlet["m"] * (outlet["e_T"] + inlet["e_T"])
                    self.E_F = inlet["m"] * inlet["e_T"] + (inlet["m"] * inlet["e_M"] - outlet["m"] * outlet["e_M"])
                else:
                    self.E_P = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
                    self.E_F = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])

            elif inlet["T"] < T0 and outlet["T"] <= T0:
                if split_physical_exergy:
                    self.E_P = (
                        np.nan
                        if getattr(self, "dissipative", False)
                        else inlet["m"] * (inlet["e_T"] - outlet["e_T"])
                        + (outlet["m"] * outlet["e_M"] - inlet["m"] * inlet["e_M"])
                    )
                    self.E_F = inlet["m"] * (inlet["e_T"] - outlet["e_T"])
                else:
                    self.E_P = (
                        np.nan if getattr(self, "dissipative", False) else inlet["m"] * (inlet["e_PH"] - outlet["e_PH"])
                    )
                    self.E_F = inlet["m"] * (inlet["e_PH"] - outlet["e_PH"])
            else:
                logging.warning("SimpleHeatExchanger: unimplemented case (Q > 0, T_in > T0 > T_out?).")
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 3: Fully dissipative or Q == 0
        else:
            self.E_P = np.nan
            self.E_F = inlet["m"] * (inlet["e_PH"] - outlet["e_PH"])

        # Calculate exergy destruction
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Exergy balance of SimpleHeatExchanger {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""
        This function must be implemented in the future.

        The exergoeconomic analysis of SimpleHeatExchanger is not implemented yet.
        """

        # Extract inlet and outlet
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Calculate heat transfer Q
        Q = outlet["m"] * outlet["h"] - inlet["m"] * inlet["h"]

        # Extract temperatures
        T_in = inlet["T"]
        T_out = outlet["T"]

        # Equality equation for mechanical exergy costs (c_M,in = c_M,out)
        A[counter, inlet["CostVar_index"]["M"]] = 1 / inlet["E_M"] if inlet["e_M"] != 0 else 1
        A[counter, outlet["CostVar_index"]["M"]] = -1 / outlet["E_M"] if outlet["e_M"] != 0 else -1
        equations[counter] = {
            "kind": "aux_equality",
            "objects": [self.name, inlet["name"], outlet["name"]],
            "property": "c_M",
        }
        b[counter] = 0
        counter += 1

        # Equality equation for chemical exergy costs (c_CH,in = c_CH,out)
        if chemical_exergy_enabled:
            A[counter, inlet["CostVar_index"]["CH"]] = 1 / inlet["E_CH"] if inlet["e_CH"] != 0 else 1
            A[counter, outlet["CostVar_index"]["CH"]] = -1 / outlet["E_CH"] if outlet["e_CH"] != 0 else -1
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": "c_CH",
            }
            b[counter] = 0
            counter += 1

        # Thermal exergy cost equations

        # Case 1: Heat is released (Q < 0)
        if Q < 0:
            # Case 1.1: Both streams above ambient temperature
            if T_in >= T0 and T_out >= T0:
                # Apply F-rule to thermal exergy (c_T,in = c_T,out)
                A[counter, inlet["CostVar_index"]["T"]] = 1 / inlet["E_T"] if inlet["e_T"] != 0 else 1
                A[counter, outlet["CostVar_index"]["T"]] = -1 / outlet["E_T"] if outlet["e_T"] != 0 else -1
                equations[counter] = {
                    "kind": "aux_f_rule",
                    "objects": [self.name, inlet["name"], outlet["name"]],
                    "property": "c_T",
                }
                b[counter] = 0
                counter += 1

            elif T_in >= T0 and T_out < T0:
                # Tricky case: inlet above T0, outlet below T0
                logging.warning(
                    f"SimpleHeatExchanger '{self.name}': Stream crossing ambient temperature "
                    f"during heat release not implemented in exergoeconomics yet!"
                )

            else:
                # Tricky case: both streams below T0 while heat is released
                logging.warning(
                    f"SimpleHeatExchanger '{self.name}': Both streams below T0 during heat release "
                    f"not implemented in exergoeconomics yet!"
                )

        # Case 2: Heat is added (Q > 0)
        elif Q > 0:
            # Case 2.1: Both streams below ambient temperature
            if T_in < T0 and T_out < T0:
                # No auxiliary equation needed for thermal exergy
                # The cost balance will determine c_T,out based on c_T,in and c_heat
                pass

            elif T_in < T0 and T_out >= T0:
                # Tricky case: inlet below T0, outlet above T0
                logging.warning(
                    f"SimpleHeatExchanger '{self.name}': Stream crossing ambient temperature "
                    f"during heat absorption not implemented in exergoeconomics yet!"
                )

            # Case 2.2: Both streams above ambient temperature
            elif T_in >= T0 and T_out >= T0:
                # No auxiliary equation needed for thermal exergy
                # The cost balance will determine c_T,out based on c_T,in and c_heat
                pass

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""
        Perform exergoeconomic cost balance for the simple heat exchanger.

        The general exergoeconomic balance equation is:

        .. math::
            \dot{C}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{C}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{C}^{\mathrm{M}}_{\mathrm{out}}
            + \dot{Z}
            = 0

        In case the chemical exergy of the streams is known:

        .. math::
            \dot{C}^{\mathrm{CH}}_{\mathrm{in}} =
            \dot{C}^{\mathrm{CH}}_{\mathrm{out}}

        This method computes cost rates for product and fuel, and derives
        exergoeconomic indicators based on the operating conditions.

        **Heat release** (:math:`\dot{Q} < 0`)

        Case 1: Both streams above ambient temperature

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Case 2: Inlet above and outlet below ambient temperature

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

        **Heat injection** (:math:`\dot{Q} > 0`)

        Case 1: Both streams above ambient temperature

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        Case 2: Inlet below and outlet above ambient temperature

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Case 3: Both streams below ambient temperature

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{in}}\bigr)

        .. math::
            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        **Fully dissipative or** :math:`\dot{Q} = 0`

        .. math::
            \dot{E}_{\mathrm{P}} = \mathrm{NaN}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

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
        """
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Determine heat transfer direction
        Q = outlet["m"] * outlet["h"] - inlet["m"] * inlet["h"]

        # Case 1: Heat is released (Q < 0)
        if Q < 0:
            if inlet["T"] >= T0 and outlet["T"] >= T0:
                # Both streams above ambient
                self.C_P = outlet["C_T"] - inlet["C_T"]
                self.C_F = inlet["C_PH"] - outlet["C_PH"]
            elif inlet["T"] >= T0 and outlet["T"] < T0:
                # Inlet above, outlet below ambient
                self.C_P = outlet["C_T"]
                self.C_F = inlet["C_T"] + outlet["C_T"] + (inlet["C_M"] - outlet["C_M"])
            elif inlet["T"] <= T0 and outlet["T"] < T0:
                # Both streams below ambient
                self.C_P = outlet["C_T"] - inlet["C_T"]
                self.C_F = self.C_P + (inlet["C_M"] - outlet["C_M"])
            else:
                self.C_P = np.nan
                self.C_F = np.nan

        # Case 2: Heat is added (Q > 0)
        elif Q > 0:
            if inlet["T"] >= T0 and outlet["T"] >= T0:
                # Both streams above ambient
                self.C_P = outlet["C_PH"] - inlet["C_PH"]
                self.C_F = outlet["C_T"] - inlet["C_T"]
            elif inlet["T"] < T0 and outlet["T"] >= T0:
                # Inlet below, outlet above ambient
                self.C_P = outlet["C_T"] + inlet["C_T"]
                self.C_F = inlet["C_T"] + (inlet["C_M"] - outlet["C_M"])
            elif inlet["T"] < T0 and outlet["T"] <= T0:
                # Both streams below ambient
                self.C_P = inlet["C_T"] - outlet["C_T"] + (outlet["C_M"] - inlet["C_M"])
                self.C_F = inlet["C_T"] - outlet["C_T"]
            else:
                self.C_P = np.nan
                self.C_F = np.nan

        # Case 3: Fully dissipative or Q == 0
        else:
            self.C_P = np.nan
            self.C_F = inlet["C_PH"] - outlet["C_PH"]

        # Calculate specific costs and exergoeconomic indicators
        self.c_F = self.C_F / self.E_F if self.E_F else np.nan
        self.c_P = self.C_P / self.E_P if self.E_P else np.nan
        self.C_D = self.c_F * self.E_D if self.E_D else np.nan
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F else np.nan
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if self.C_D else np.nan
