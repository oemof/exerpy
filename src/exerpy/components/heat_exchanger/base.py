import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


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

    def _temperature_case(self, T0):
        """Classify the heat exchanger temperature configuration.

        Uses a tolerance of 0.01 K to handle floating-point edge cases
        where stream temperatures are numerically very close to T0.

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).

        Returns
        -------
        int
            Case number (1-7).
        """
        tol = 0.01  # K

        T0_in = self.inl[0]["T"]
        T1_in = self.inl[1]["T"]
        T0_out = self.outl[0]["T"]
        T1_out = self.outl[1]["T"]

        all_T = [T0_in, T1_in, T0_out, T1_out]

        def above(T):
            return T0 + tol < T

        def at_or_below(T):
            return T0 + tol >= T

        # Case 1: All streams at or above T0
        if all(T0 - tol <= T for T in all_T):
            return 1
        # Case 2: All streams at or below T0
        if all(at_or_below(T) for T in all_T):
            return 2
        # Case 3: Both streams crossing T0
        if above(T0_in) and above(T1_out) and at_or_below(T0_out) and at_or_below(T1_in):
            return 3
        # Case 4: Only hot inlet above T0
        if above(T0_in) and at_or_below(T1_in) and at_or_below(T0_out) and at_or_below(T1_out):
            return 4
        # Case 5: Only cold inlet below T0
        if above(T0_in) and at_or_below(T1_in) and above(T0_out) and above(T1_out):
            return 5
        # Case 6: Hot stream always above, cold stream always below (dissipative)
        if above(T0_in) and at_or_below(T1_in) and above(T0_out) and at_or_below(T1_out):
            return 6
        # Case 7: Unrecognized
        return 7

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

        Case 2: All streams below or equal to ambient temperature

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

        Case 3: Both stream crossing ambient temperature

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

        Case 4: Only the hot inlet above ambient temperature

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

        Case 5: Only the cold inlet below ambient temperature

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

        Case 6: Hot stream always above and cold stream always below ambiente temperature (dissipative case):

        .. math::
            \dot{E}_{\mathrm{P}} = \mathrm{NaN}

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{PH}}_{\mathrm{in},1}
                    - \dot{E}^{\mathrm{PH}}_{\mathrm{out},1}\bigr)
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out},2}
            + \dot{E}^{\mathrm{PH}}_{\mathrm{in},2}

        If `dissipative` is `True`, the component is treated as dissipative:

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

        if not self.dissipative:
            case = self._temperature_case(T0)
            # Case 1: All streams are above the ambient temperature
            if case == 1:
                if split_physical_exergy:
                    self.E_P = self.outl[1]["m"] * self.outl[1]["e_T"] - self.inl[1]["m"] * self.inl[1]["e_T"]
                    self.E_F = (
                        self.inl[0]["m"] * self.inl[0]["e_PH"]
                        - self.outl[0]["m"] * self.outl[0]["e_PH"]
                        + (self.inl[1]["m"] * self.inl[1]["e_M"] - self.outl[1]["m"] * self.outl[1]["e_M"])
                    )
                else:
                    self.E_P = self.outl[1]["m"] * self.outl[1]["e_PH"] - self.inl[1]["m"] * self.inl[1]["e_PH"]
                    self.E_F = self.inl[0]["m"] * self.inl[0]["e_PH"] - self.outl[0]["m"] * self.outl[0]["e_PH"]

            # Case 2: All streams are below or equal to the ambient temperature
            elif case == 2:
                if split_physical_exergy:
                    self.E_P = self.outl[0]["m"] * self.outl[0]["e_T"] - self.inl[0]["m"] * self.inl[0]["e_T"]
                    self.E_F = (
                        self.inl[1]["m"] * self.inl[1]["e_PH"]
                        - self.outl[1]["m"] * self.outl[1]["e_PH"]
                        + (self.inl[0]["m"] * self.inl[0]["e_M"] - self.outl[0]["m"] * self.outl[0]["e_M"])
                    )
                else:
                    logger.warning(
                        "While dealing with heat exchnager below ambient temperautre, "
                        "physical exergy should be split into thermal and mechanical components!"
                    )
                    self.E_P = self.outl[0]["m"] * self.outl[0]["e_PH"] - self.inl[0]["m"] * self.inl[0]["e_PH"]
                    self.E_F = self.inl[1]["m"] * self.inl[1]["e_PH"] - self.outl[1]["m"] * self.outl[1]["e_PH"]

            # Case 3: Both stream crossing T0 (hot inlet and cold outlet > T0, hot outlet and cold inlet <= T0)
            elif case == 3:
                if split_physical_exergy:
                    self.E_P = self.outl[0]["m"] * self.outl[0]["e_T"] + self.outl[1]["m"] * self.outl[1]["e_T"]
                    self.E_F = (
                        self.inl[0]["m"] * self.inl[0]["e_PH"]
                        + self.inl[1]["m"] * self.inl[1]["e_PH"]
                        - (self.outl[0]["m"] * self.outl[0]["e_M"] + self.outl[1]["m"] * self.outl[1]["e_M"])
                    )
                else:
                    logger.warning(
                        "While dealing with heat exchnager below ambient temperautre, "
                        "physical exergy should be split into thermal and mechanical components!"
                    )
                    self.E_P = self.outl[0]["m"] * self.outl[0]["e_PH"] + self.outl[1]["m"] * self.outl[1]["e_PH"]
                    self.E_F = self.inl[0]["m"] * self.inl[0]["e_PH"] + self.inl[1]["m"] * self.inl[1]["e_PH"]

            # Case 4: Only hot inlet > T0
            elif case == 4:
                if split_physical_exergy:
                    self.E_P = self.outl[0]["m"] * self.outl[0]["e_T"]
                    self.E_F = (
                        self.inl[0]["m"] * self.inl[0]["e_PH"]
                        + self.inl[1]["m"] * self.inl[1]["e_PH"]
                        - (self.outl[1]["m"] * self.outl[1]["e_PH"] + self.outl[0]["m"] * self.outl[0]["e_M"])
                    )
                else:
                    logger.warning(
                        "While dealing with heat exchnager below ambient temperautre, "
                        "physical exergy should be split into thermal and mechanical components!"
                    )
                    self.E_P = self.outl[0]["m"] * self.outl[0]["e_PH"]
                    self.E_F = self.inl[0]["m"] * self.inl[0]["e_PH"] + (
                        self.inl[1]["m"] * self.inl[1]["e_PH"] - self.outl[1]["m"] * self.outl[1]["e_PH"]
                    )

            # Case 5: Only cold inlet <= T0
            elif case == 5:
                if split_physical_exergy:
                    self.E_P = self.outl[1]["m"] * self.outl[1]["e_T"]
                    self.E_F = (
                        self.inl[0]["m"] * self.inl[0]["e_PH"]
                        - self.outl[0]["m"] * self.outl[0]["e_PH"]
                        + (self.inl[1]["m"] * self.inl[1]["e_PH"] - self.outl[1]["m"] * self.outl[1]["e_M"])
                    )
                else:
                    logger.warning(
                        "While dealing with heat exchnager below ambient temperautre, "
                        "physical exergy should be split into thermal and mechanical components!"
                    )
                    self.E_P = self.outl[1]["m"] * self.outl[1]["e_PH"]
                    self.E_F = (
                        self.inl[0]["m"] * self.inl[0]["e_PH"]
                        - self.outl[0]["m"] * self.outl[0]["e_PH"]
                        + (self.inl[1]["m"] * self.inl[1]["e_PH"])
                    )

            # Case 6: hot stream always above T0, cold stream always below T0 (dissipative case)
            elif case == 6:
                self.E_P = np.nan
                self.E_F = (
                    self.inl[0]["m"] * self.inl[0]["e_PH"]
                    - self.outl[0]["m"] * self.outl[0]["e_PH"]
                    + (self.inl[1]["m"] * self.inl[1]["e_PH"] - self.outl[1]["m"] * self.outl[1]["e_PH"])
                )

                logger.info(
                    f"Component {self.name}: dissipative temperature configuration detected "
                    "(hot stream above T0, cold stream below T0). Treated as dissipative automatically."
                )

            # Case 7: Not implemented case
            else:
                logger.error(
                    f"The heat exchanger {self.name} has an unexpected temperature configuration. "
                    "Please check the inlet and outlet temperatures."
                )

        else:
            self.E_F = (
                self.inl[0]["m"] * self.inl[0]["e_PH"]
                - self.outl[0]["m"] * self.outl[0]["e_PH"]
                - self.outl[1]["m"] * self.outl[1]["e_PH"]
                + self.inl[1]["m"] * self.inl[1]["e_PH"]
            )
            self.E_P = np.nan
        # Calculate exergy destruction and efficiency
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logger.info(
            f"Exergy balance of HeatExchanger {self.name} calculated: "
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
                A[row, in_item["CostVar_index"][var]] = 1 / in_item["E_" + var]
                A[row, out_item["CostVar_index"][var]] = -1 / out_item["E_" + var]
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
        case = self._temperature_case(T0)
        # Case 1: All temperatures > T0.
        if case == 1:
            set_thermal_f_hot(A, counter + 0)
            equations[counter] = {
                "kind": "aux_f_rule_hot",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_T",
            }
        # Case 2: All temperatures <= T0.
        elif case == 2:
            set_thermal_f_cold(A, counter + 0)
            equations[counter] = {
                "kind": "aux_f_rule_cold",
                "objects": [self.name, self.inl[1]["name"], self.outl[1]["name"]],
                "property": "c_T",
            }
        # Case 3: Both stream crossing T0 (hot inlet and cold outlet > T0, hot outlet and cold inlet <= T0)
        elif case == 3:
            set_thermal_p_rule(A, counter + 0)
            equations[counter] = {
                "kind": "aux_p_rule",
                "objects": [self.name, self.outl[0]["name"], self.outl[1]["name"]],
                "property": "c_T",
            }
        # Case 4: Only hot inlet > T0
        elif case == 4:
            set_thermal_f_cold(A, counter + 0)
            equations[counter] = {
                "kind": "aux_f_rule_cold",
                "objects": [self.name, self.inl[1]["name"], self.outl[1]["name"]],
                "property": "c_T",
            }
        # Case 5: Only cold inlet <= T0
        elif case == 5:
            set_thermal_f_hot(A, counter + 0)
            equations[counter] = {
                "kind": "aux_f_rule_hot",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_T",
            }
        # Case 6: hot stream always above T0, cold stream always below T0 (dissipative case)
        elif case == 6:
            logger.info(
                f"Component {self.name}: dissipative temperature configuration detected in aux_eqs. "
                "Skipping auxiliary equations (handled by dis_eqs)."
            )
            return A, b, counter, equations
        # Case 7: Not implemented case
        else:
            logger.error(
                f"The heat exchanger {self.name} has an unexpected temperature configuration. "
                "Please check the inlet and outlet temperatures."
            )

        # Mechanical equations (always added)
        set_equal(A, counter + 1, self.inl[0], self.outl[0], "M")
        set_equal(A, counter + 2, self.inl[1], self.outl[1], "M")
        equations[counter + 1] = {
            "kind": "aux_equality",
            "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
            "property": "c_M",
        }
        equations[counter + 2] = {
            "kind": "aux_equality",
            "objects": [self.name, self.inl[1]["name"], self.outl[1]["name"]],
            "property": "c_M",
        }

        # Only add chemical auxiliary equations if chemical exergy is enabled.
        if chemical_exergy_enabled:
            set_equal(A, counter + 3, self.inl[0], self.outl[0], "CH")
            set_equal(A, counter + 4, self.inl[1], self.outl[1], "CH")
            equations[counter + 3] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            equations[counter + 4] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[1]["name"], self.outl[1]["name"]],
                "property": "c_CH",
            }
            num_aux_eqs = 5
        else:
            # Skip chemical auxiliary equations.
            num_aux_eqs = 3

        for i in range(num_aux_eqs):
            b[counter + i] = 0

        return A, b, counter + num_aux_eqs, equations

    def dis_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled=False, all_components=None):
        r"""
        Construct cost equations for a dissipative HeatExchanger.

        Distributes the heat exchanger's extra cost difference (C_diff) to all other productive
        components (non-dissipative and non-CycleCloser) in proportion to their exergy destruction (E_D)
        and adds an overall cost balance row that enforces:

        .. math::
           (\dot C_{\mathrm{in},1} - \dot C_{\mathrm{out},1})
           + (\dot C_{\mathrm{in},2} - \dot C_{\mathrm{out},2})
           - \dot C_{\mathrm{diff}}
           = -\,\dot Z_{\mathrm{costs}}

        The equality equations enforce that specific costs are equal between inlet and outlet
        for each exergy component (thermal, mechanical, chemical) on both the hot and cold streams.

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the cost matrix.
        T0 : float
            Ambient temperature (K).
        equations : dict
            Dictionary mapping row indices to equation labels.
        chemical_exergy_enabled : bool, optional
            Flag indicating whether chemical exergy is considered.
        all_components : list, optional
            Global list of all component objects; if not provided, defaults to [].

        Returns
        -------
        tuple
            Updated (A, b, counter, equations).
        """

        def set_equal_dis(A, row, in_item, out_item, var):
            if in_item.get("E_" + var, 0) and out_item.get("E_" + var, 0):
                A[row, in_item["CostVar_index"][var]] = 1 / in_item["E_" + var]
                A[row, out_item["CostVar_index"][var]] = -1 / out_item["E_" + var]
            else:
                A[row, in_item["CostVar_index"][var]] = 1
                A[row, out_item["CostVar_index"][var]] = -1

        # --- Thermal equality for hot stream ---
        set_equal_dis(A, counter, self.inl[0], self.outl[0], "T")
        b[counter] = 0
        equations[counter] = {
            "kind": "dis_equality",
            "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
            "property": "c_T",
        }
        counter += 1

        # --- Thermal equality for cold stream ---
        set_equal_dis(A, counter, self.inl[1], self.outl[1], "T")
        b[counter] = 0
        equations[counter] = {
            "kind": "dis_equality",
            "objects": [self.name, self.inl[1]["name"], self.outl[1]["name"]],
            "property": "c_T",
        }
        counter += 1

        # --- Mechanical equality for hot stream ---
        set_equal_dis(A, counter, self.inl[0], self.outl[0], "M")
        b[counter] = 0
        equations[counter] = {
            "kind": "dis_equality",
            "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
            "property": "c_M",
        }
        counter += 1

        # --- Mechanical equality for cold stream ---
        set_equal_dis(A, counter, self.inl[1], self.outl[1], "M")
        b[counter] = 0
        equations[counter] = {
            "kind": "dis_equality",
            "objects": [self.name, self.inl[1]["name"], self.outl[1]["name"]],
            "property": "c_M",
        }
        counter += 1

        # --- Chemical equality (if enabled) ---
        if chemical_exergy_enabled:
            set_equal_dis(A, counter, self.inl[0], self.outl[0], "CH")
            b[counter] = 0
            equations[counter] = {
                "kind": "dis_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            counter += 1

            set_equal_dis(A, counter, self.inl[1], self.outl[1], "CH")
            b[counter] = 0
            equations[counter] = {
                "kind": "dis_equality",
                "objects": [self.name, self.inl[1]["name"], self.outl[1]["name"]],
                "property": "c_CH",
            }
            counter += 1

        # --- Distribution of dissipative cost difference to other components based on E_D ---
        if all_components is None:
            all_components = []
        serving = [
            comp
            for comp in all_components
            if comp is not self
            and hasattr(comp, "exergy_cost_line")
            and not comp.__class__.__name__.endswith("PowerBus")
            and hasattr(comp, "E_D")
            and not np.isnan(comp.E_D)
        ]
        total_E_D = sum(comp.E_D for comp in serving)
        diss_col = self.inl[0]["CostVar_index"].get("dissipative")
        if diss_col is None:
            logger.error(f"No 'dissipative' column allocated for {self.name}.")
        else:
            if total_E_D == 0:
                if len(serving) > 0:
                    for comp in serving:
                        A[comp.exergy_cost_line, diss_col] = 1 / len(serving)
                else:
                    logger.warning(f"No serving components found for dissipative component {self.name}")
            else:
                for comp in serving:
                    weight = getattr(comp, "E_D", 0) / total_E_D
                    comp.serving_weight = weight
                    A[comp.exergy_cost_line, diss_col] = weight

        # --- Overall cost balance row ---
        # (C_in_hot - C_out_hot) + (C_in_cold - C_out_cold) - C_diff = -Z_costs
        A[counter, self.inl[0]["CostVar_index"]["T"]] = 1
        A[counter, self.outl[0]["CostVar_index"]["T"]] = -1
        A[counter, self.inl[0]["CostVar_index"]["M"]] = 1
        A[counter, self.outl[0]["CostVar_index"]["M"]] = -1
        A[counter, self.inl[1]["CostVar_index"]["T"]] = 1
        A[counter, self.outl[1]["CostVar_index"]["T"]] = -1
        A[counter, self.inl[1]["CostVar_index"]["M"]] = 1
        A[counter, self.outl[1]["CostVar_index"]["M"]] = -1
        if chemical_exergy_enabled:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = 1
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = -1
            A[counter, self.inl[1]["CostVar_index"]["CH"]] = 1
            A[counter, self.outl[1]["CostVar_index"]["CH"]] = -1
        A[counter, self.inl[0]["CostVar_index"]["dissipative"]] = -1
        b[counter] = -self.Z_costs
        equations[counter] = {"kind": "dis_balance", "objects": [self.name], "property": "dissipative_cost_balance"}
        counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
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
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        """
        case = self._temperature_case(T0)
        # Dissipative heat exchanger (E_P is NaN): no identifiable product
        if np.isnan(self.E_P):
            self.C_P = np.nan
            self.C_F = self.inl[0]["C_PH"] - self.outl[0]["C_PH"] + (self.inl[1]["C_PH"] - self.outl[1]["C_PH"])
        # Case 1: All streams are above the ambient temperature
        elif case == 1:
            self.C_P = self.outl[1]["C_T"] - self.inl[1]["C_T"]
            self.C_F = self.inl[0]["C_PH"] - self.outl[0]["C_PH"] + (self.inl[1]["C_M"] - self.outl[1]["C_M"])
        # Case 2: All streams are below or equal to the ambient temperature
        elif case == 2:
            self.C_P = self.outl[0]["C_T"] - self.inl[0]["C_T"]
            self.C_F = self.inl[1]["C_PH"] - self.outl[1]["C_PH"] + (self.inl[0]["C_M"] - self.outl[0]["C_M"])
        # Case 3: Both stream crossing T0 (hot inlet and cold outlet > T0, hot outlet and cold inlet <= T0)
        elif case == 3:
            self.C_P = self.outl[0]["C_T"] + self.outl[1]["C_T"]
            self.C_F = self.inl[0]["C_PH"] + self.inl[1]["C_PH"] - (self.outl[0]["C_M"] + self.outl[1]["C_M"])
        # Case 4: Only hot inlet > T0
        elif case == 4:
            self.C_P = self.outl[0]["C_T"]
            self.C_F = self.inl[0]["C_PH"] + self.inl[1]["C_PH"] - (self.outl[1]["C_PH"] + self.outl[0]["C_M"])
        # Case 5: Only cold inlet <= T0
        elif case == 5:
            self.C_P = self.outl[1]["C_T"]
            self.C_F = self.inl[0]["C_PH"] - self.outl[0]["C_PH"] + (self.inl[1]["C_PH"] - self.outl[1]["C_M"])
        # Case 7: Not implemented case
        else:
            logger.error(
                f"The heat exchanger {self.name} has an unexpected temperature configuration. "
                "Please check the inlet and outlet temperatures."
            )

        self.c_F = self.C_F / self.E_F if self.E_F != 0 else np.nan
        self.c_P = self.C_P / self.E_P if not np.isnan(self.E_P) and self.E_P != 0 else np.nan
        self.C_D = self.c_F * self.E_D if not np.isnan(self.c_F) else np.nan
        self.r = (
            (self.c_P - self.c_F) / self.c_F
            if not np.isnan(self.c_P) and not np.isnan(self.c_F) and self.c_F != 0
            else np.nan
        )
        self.f = (
            self.Z_costs / (self.Z_costs + self.C_D)
            if not np.isnan(self.C_D) and (self.Z_costs + self.C_D) != 0
            else np.nan
        )
