import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class HeatExchanger(Component):
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
        self.dissipative = False
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the heat exchanger.

        Case 1: All streams above ambient temperature

        If `split_physical_exergy=True`:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out},2}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in},2}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in},2}
                    - \dot{E}^{\mathrm{M}}_{\mathrm{out},2}\bigr)

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}

        Case 2: All streams below ambient temperature

        If `split_physical_exergy=True`:

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out},1}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in},1}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in},1}
                    - \dot{E}^{\mathrm{M}}_{\mathrm{out},1}\bigr)

        Else

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in},1}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}

        Case 3: Hot stream above, cold stream below ambient temperature

        If `split_physical_exergy=True`:

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out},1}
            + \dot{E}^{\mathrm{T}}_{\mathrm{out},2}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
            + \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}
            - \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{out},1}
                    + \dot{E}^{\mathrm{M}}_{\mathrm{out},2}\bigr)

        Else:

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out},1}
            + \dot{E}^{\mathrm{T}}_{\mathrm{out},2}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
            + \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}

        Case 4: Only inlet 1 above ambient temperature

        If `split_physical_exergy=True`:

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out},1}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
                    + \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}\bigr)
            - \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{out},2}
                    + \dot{E}^{\mathrm{M}}_{\mathrm{out},1}\bigr)

        Else:

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
                    + \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}\bigr)
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}

        Case 5: Both inlets above, both outlets below ambient temperature

        .. math::
            \dot{E}_{\mathrm{P}} = \mathrm{NaN}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}\bigr)
            + \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},2}
                    - \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}\bigr)

        Case 6: Cold inlet below, others above ambient temperature

        If `split_physical_exergy=True`:
        
        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out},2}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}\bigr)
            + \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},2}
                    - \dot{E}^{\mathrm{M}}_{\mathrm{out},2}\bigr)
       
        Else:

        .. math::
            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}\bigr)
            + \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}

        Dissipative case:

        .. math::
            \dot{E}_{\mathrm{P}} = \mathrm{NaN}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}\bigr)
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}
            + \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}

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
            raise ValueError("Heat exchanger requires two inlets and two outlets.")

        # Access the streams via .values() to iterate over the actual stream data
        all_streams = list(self.inl.values()) + list(self.outl.values())

        if not self.dissipative:
            # Case 1: All streams are above the ambient temperature
            if all([stream['T'] >= T0 for stream in all_streams]):
                if split_physical_exergy:
                    self.E_P = self.outl[1]['m'] * self.outl[1]['e_T'] - self.inl[1]['m'] * self.inl[1]['e_T']
                    self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                        self.inl[1]['m'] * self.inl[1]['e_M'] - self.outl[1]['m'] * self.outl[1]['e_M'])
                else:
                    self.E_P = self.outl[1]['m'] * self.outl[1]['e_PH'] - self.inl[1]['m'] * self.inl[1]['e_PH']
                    self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH']

            # Case 2: All streams are below or equal to the ambient temperature
            elif all([stream['T'] <= T0 for stream in all_streams]):
                if split_physical_exergy:
                    self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] - self.inl[0]['m'] * self.inl[0]['e_T']
                    self.E_F = self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'] + (
                        self.inl[0]['m'] * self.inl[0]['e_M'] - self.outl[0]['m'] * self.outl[0]['e_M'])
                else:
                    logging.warning("While dealing with heat exchnager below ambient temperautre, "
                    "physical exergy should be split into thermal and mechanical components!")
                    self.E_P = self.outl[0]['m'] * self.outl[0]['e_PH'] - self.inl[0]['m'] * self.inl[0]['e_PH']
                    self.E_F = self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH']

            # Case 3: Hot stream from above to lower ambient, cold stream from lower to above ambient
            elif (self.inl[0]['T'] > T0 and self.outl[1]['T'] > T0 and
                self.outl[0]['T'] <= T0 and self.inl[1]['T'] <= T0):
                if split_physical_exergy:
                    self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] + self.outl[1]['m'] * self.outl[1]['e_T']
                    self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'] - (
                        self.outl[0]['m'] * self.outl[0]['e_M'] + self.outl[1]['m'] * self.outl[1]['e_M'])
                else:
                    logging.warning("While dealing with heat exchnager below ambient temperautre, "
                    "physical exergy should be split into thermal and mechanical components!")
                    self.E_P = self.outl[0]['m'] * self.outl[0]['e_PH'] + self.outl[1]['m'] * self.outl[1]['e_PH']
                    self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH']

            # Case 4: Hot stream inlet above ambient, all others below or equal to ambient
            elif (self.inl[0]['T'] > T0 and self.inl[1]['T'] <= T0 and
                self.outl[0]['T'] <= T0 and self.outl[1]['T'] <= T0):
                if split_physical_exergy:
                    self.E_P = self.outl[0]['m'] * self.outl[0]['e_T']
                    self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'] - (
                        self.outl[1]['m'] * self.outl[1]['e_PH'] + self.outl[0]['m'] * self.outl[0]['e_M'])
                else:
                    logging.warning("While dealing with heat exchnager below ambient temperautre, "
                    "physical exergy should be split into thermal and mechanical components!")
                    self.E_P = self.outl[0]['m'] * self.outl[0]['e_PH']
                    self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + (
                        self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'])

            # Case 5: Inlets are higher but outlets are below or equal to ambient
            elif (self.inl[0]['T'] > T0 and self.outl[0]['T'] > T0 and
                self.inl[1]['T'] <= T0 and self.outl[1]['T'] <= T0):
                self.E_P = np.nan
                self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                    self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'])

            # Case 6: Cold inlet is lower ambient, others higher
            else:
                if split_physical_exergy:
                    self.E_P = self.outl[1]['m'] * self.outl[1]['e_T']
                    self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                        self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_M'])
                else:
                    logging.warning("While dealing with heat exchnager below ambient temperautre, "
                    "physical exergy should be split into thermal and mechanical components!")
                    self.E_P = self.outl[1]['m'] * self.outl[1]['e_PH']
                    self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                        self.inl[1]['m'] * self.inl[1]['e_PH'])

        else:
            self.E_F = (
                self.inl[0]['m'] * self.inl[0]['e_PH']
                - self.outl[0]['m'] * self.outl[0]['e_PH']
                - self.outl[1]['m'] * self.outl[1]['e_PH']
                + self.inl[1]['m'] * self.inl[1]['e_PH']
            )
            self.E_P = np.nan
        # Calculate exergy destruction and efficiency
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"HeatExchanger exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""
        Add auxiliary cost equations for the heat exchanger.

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

        Case 3: Hot ends above, cold ends below ambient temperature

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

        Case 6: Hot inlet above, cold inlet below ambient temperature (dissipative case): 

        The dissipative is not handeld here.

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
        r"""
        Perform exergoeconomic cost balance for the heat exchanger.

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

        Case 3: Hot inlet 1 and outlet 2 above, cold inlet 2 and outlet 1 below ambient

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\mathrm{out},1}
                    + \dot{C}^{\mathrm{T}}_{\mathrm{out},2}

        .. math::
            \dot{C}_F = \dot{C}^{\mathrm{PH}}_{\mathrm{in},1}
                    + \dot{C}^{\mathrm{PH}}_{\mathrm{in},2}
                    - \bigl(\dot{C}^{\mathrm{M}}_{\mathrm{out},1}
                            + \dot{C}^{\mathrm{M}}_{\mathrm{out},2}\bigr)

        Case 4: Only inlet 1 above ambient temperature

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\mathrm{out},1}

        .. math::
            \dot{C}_F = \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{in},1}
                            + \dot{C}^{\mathrm{PH}}_{\mathrm{in},2}\bigr)
                    - \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{out},2}
                            + \dot{C}^{\mathrm{M}}_{\mathrm{out},1}\bigr)

        Case 5: Both inlets above, both outlets below ambient temperature

        .. math::
            \dot{C}_P = \dot{C}^{\mathrm{T}}_{\mathrm{out},2}

        .. math::
            \dot{C}_F = \dot{C}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{C}^{\mathrm{PH}}_{\mathrm{out},1}
                    + \bigl(\dot{C}^{\mathrm{PH}}_{\mathrm{in},2}
                            - \dot{C}^{\mathrm{M}}_{\mathrm{out},2}\bigr)

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