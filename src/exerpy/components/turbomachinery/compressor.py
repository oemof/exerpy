import logging

import numpy as np

from exerpy.components.component import Component, component_registry


@component_registry
class Compressor(Component):
    r"""
    Class for exergy and exergoeconomic analysis of compressors.

    This class performs exergy and exergoeconomic analysis calculations for compressors,
    considering thermal, mechanical, and physical exergy flows. The exergy product and fuel
    are calculated based on temperature relationships between inlet, outlet, and ambient conditions.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.
        Optional parameter 'Z_costs' (float): Investment cost rate of the component in currency/h.

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
    P : float
        Power input to the compressor in :math:`\mathrm{W}`.
    inl : dict
        Dictionary containing inlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.
    Z_costs : float
        Investment cost rate of the component in currency/h.

    Notes
    -----
    The exergy analysis considers three cases based on temperature relationships:

    Case 1 - **Both temperatures above ambient** (:math:`T_\mathrm{in}, T_\mathrm{out} > T_0`):

    .. math::

        \dot{E}_\mathrm{P} &= \dot{m} \cdot (e_\mathrm{out}^\mathrm{PH} -
        e_\mathrm{in}^\mathrm{PH})\\
        \dot{E}_\mathrm{F} &= |\dot{W}|

    Case 2 - **Inlet below, outlet above ambient** (:math:`T_\mathrm{in} < T_0 < T_\mathrm{out}`):

    .. math::

        \dot{E}_\mathrm{P} &= \dot{m} \cdot e_\mathrm{out}^\mathrm{T} +
        \dot{m} \cdot (e_\mathrm{out}^\mathrm{M} - e_\mathrm{in}^\mathrm{M})\\
        \dot{E}_\mathrm{F} &= |\dot{W}| + \dot{m} \cdot e_\mathrm{in}^\mathrm{T}

    Case 3 - **Both temperatures below ambient** (:math:`T_\mathrm{in}, T_\mathrm{out} \leq T_0`):

    .. math::

        \dot{E}_\mathrm{P} &= \dot{m} \cdot (e_\mathrm{out}^\mathrm{M} -
        e_\mathrm{in}^\mathrm{M})\\
        \dot{E}_\mathrm{F} &= |\dot{W}| + \dot{m} \cdot (e_\mathrm{in}^\mathrm{T}
        - e_\mathrm{out}^\mathrm{T})

    For all valid cases, the exergy destruction is:

    .. math::

        \dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}

    where:
        - :math:`\dot{W}`: Power input
        - :math:`e^\mathrm{T}`: Thermal exergy
        - :math:`e^\mathrm{M}`: Mechanical exergy
        - :math:`e^\mathrm{PH}`: Physical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize compressor component with given parameters."""
        super().__init__(**kwargs)
        self.P = None
        self.Z_costs = kwargs.get("Z_costs", 0.0)  # Investment cost rate in currency/h

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the compressor.

        Performs exergy balance calculations considering the temperature relationships
        between inlet stream, outlet stream, and ambient conditions.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        """
        # Get power flow
        if (
            1 in self.inl
            and self.inl[1] is not None
            and self.inl[1].get("kind") == "power"
            and "energy_flow" in self.inl[1]
        ):
            self.P = self.inl[1]["energy_flow"]
        else:
            self.P = self.outl[0]["m"] * (self.outl[0]["h"] - self.inl[0]["h"])

        # First, check for the invalid case: outlet temperature smaller than inlet temperature.
        if self.inl[0]["T"] > self.outl[0]["T"]:
            logging.warning(
                f"Exergy balance of compressor '{self.name}' where outlet temperature ({self.outl[0]['T']}) "
                f"is smaller than inlet temperature ({self.inl[0]['T']}) is not implemented."
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Case 1: Both temperatures above ambient
        elif round(self.inl[0]["T"], 5) >= T0 and round(self.outl[0]["T"], 5) > T0:
            self.E_P = self.outl[0]["m"] * (self.outl[0]["e_PH"] - self.inl[0]["e_PH"])
            self.E_F = abs(self.P)

        # Case 2: Inlet below, outlet above ambient
        elif round(self.inl[0]["T"], 5) < T0 and round(self.outl[0]["T"], 5) > T0:
            if split_physical_exergy:
                self.E_P = self.outl[0]["m"] * self.outl[0]["e_T"] + self.outl[0]["m"] * (
                    self.outl[0]["e_M"] - self.inl[0]["e_M"]
                )
                self.E_F = abs(self.P) + self.inl[0]["m"] * self.inl[0]["e_T"]
            else:
                logging.warning(
                    "While dealing with compressor below ambient, "
                    "physical exergy should be split into thermal and mechanical components!"
                )
                self.E_P = self.outl[0]["m"] * (self.outl[0]["e_PH"] - self.inl[0]["e_PH"])
                self.E_F = abs(self.P)

        # Case 3: Both temperatures below ambient
        elif round(self.inl[0]["T"], 5) < T0 and round(self.outl[0]["T"], 5) <= T0:
            if split_physical_exergy:
                self.E_P = self.outl[0]["m"] * (self.outl[0]["e_M"] - self.inl[0]["e_M"])
                self.E_F = abs(self.P) + self.inl[0]["m"] * (self.inl[0]["e_T"] - self.outl[0]["e_T"])
            else:
                logging.warning(
                    "While dealing with compressor below ambient, "
                    "physical exergy should be split into thermal and mechanical components!"
                )
                self.E_P = self.outl[0]["m"] * (self.outl[0]["e_PH"] - self.inl[0]["e_PH"])
                self.E_F = abs(self.P)

        # Invalid case: outlet temperature smaller than inlet
        else:
            logging.warning(
                f"Exergy balance of compressor '{self.name}' where outlet temperature is smaller "
                "than inlet temperature is not implemented."
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Exergy balance of Compressor {self.name} calculated: "
            f"E_P={self.E_P:.2f} W, E_F={self.E_F:.2f} W, E_D={self.E_D:.2f} W, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the compressor.

        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:

        (1) Chemical exergy cost equation (if enabled):
            1/E_CH_in * C_CH_in - 1/E_CH_out * C_CH_out = 0
            - F-principle: specific chemical exergy costs equalized between inlet/outlet

        (2) Thermal/Mechanical exergy cost equations (based on temperature conditions):

            Case 1 (T_in > T0, T_out > T0):
            1/dET * C_T_out - 1/dET * C_T_in - 1/dEM * C_M_out + 1/dEM * C_M_in = 0
            - P-principle: relates inlet/outlet thermal and mechanical exergy costs

            Case 2 (T_in ≤ T0, T_out > T0):
            1/E_T_out * C_T_out - 1/dEM * C_M_out + 1/dEM * C_M_in = 0
            - P-principle: relates outlet thermal and inlet/outlet mechanical exergy costs

            Case 3 (T_in ≤ T0, T_out ≤ T0):
            1/E_T_out * C_T_out - 1/E_T_in * C_T_in = 0
            - F-principle: specific thermal exergy costs equalized between inlet/outlet

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature.
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
            The updated row index (increased by 2 if chemical exergy is enabled, or by 1 otherwise).
        equations : list or dict
            Updated structure with equation labels.
        """
        # --- Chemical equality equation (row added only if enabled) ---
        if chemical_exergy_enabled:
            # Set the chemical cost equality:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = (
                (1 / self.inl[0]["E_CH"]) if self.inl[0]["e_CH"] != 0 else 1
            )
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = (
                (-1 / self.outl[0]["E_CH"]) if self.outl[0]["e_CH"] != 0 else 1
            )
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            chem_row = 1
        else:
            chem_row = 0

        # --- Thermal/Mechanical cost equation ---
        # Compute differences in thermal and mechanical exergy:
        dET = self.outl[0]["E_T"] - self.inl[0]["E_T"]
        dEM = self.outl[0]["E_M"] - self.inl[0]["E_M"]

        # The row for the thermal/mechanical equation:
        row_index = counter + chem_row
        if self.inl[0]["T"] > T0 and self.outl[0]["T"] > T0:
            if dET != 0 and dEM != 0:
                A[row_index, self.inl[0]["CostVar_index"]["T"]] = -1 / dET
                A[row_index, self.outl[0]["CostVar_index"]["T"]] = 1 / dET
                A[row_index, self.inl[0]["CostVar_index"]["M"]] = 1 / dEM
                A[row_index, self.outl[0]["CostVar_index"]["M"]] = -1 / dEM
                equations[row_index] = {
                    "kind": "aux_p_rule",
                    "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                    "property": "c_T, c_M",
                }
            else:
                logging.warning("Case where thermal or mechanical exergy difference is zero is not implemented.")
        elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] > T0:
            A[row_index, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["E_T"]
            A[row_index, self.inl[0]["CostVar_index"]["M"]] = 1 / dEM
            A[row_index, self.outl[0]["CostVar_index"]["M"]] = -1 / dEM
            equations[row_index] = {
                "kind": "aux_p_rule",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_T, c_M",
            }
        else:
            A[row_index, self.inl[0]["CostVar_index"]["T"]] = -1 / self.inl[0]["E_T"]
            A[row_index, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["E_T"]
            equations[row_index] = {
                "kind": "aux_f_rule",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_T",
            }

        # Set the right-hand side entry for the thermal/mechanical row to zero.
        b[row_index] = 0

        # Update the counter accordingly.
        new_counter = counter + 2 if chemical_exergy_enabled else counter + 1

        return A, b, new_counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""
        Perform exergoeconomic cost balance for the compressor.

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
        exergoeconomic indicators. The compressor consumes power (fuel) to increase
        the exergy of the working fluid (product).

        **Case 1: Both inlet and outlet above ambient temperature**

        Both inlet and outlet satisfy :math:`T \geq T_0`:

        .. math::
            \dot{C}_{\mathrm{P}}
            = \dot{C}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{C}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::
            \dot{C}_{\mathrm{F}}
            = \dot{C}^{\mathrm{TOT}}_{\mathrm{power,in}}

        **Case 2: Inlet at or below and outlet above ambient temperature**

        Inlet satisfies :math:`T \leq T_0` and outlet :math:`T > T_0`:

        .. math::
            \dot{C}_{\mathrm{P}}
            = \dot{C}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{C}^{\mathrm{M}}_{\mathrm{out}}
            - \dot{C}^{\mathrm{M}}_{\mathrm{in}}\bigr)

        .. math::
            \dot{C}_{\mathrm{F}}
            = \dot{C}^{\mathrm{TOT}}_{\mathrm{power,in}}
            + \dot{C}^{\mathrm{T}}_{\mathrm{in}}

        **Case 3: Both inlet and outlet at or below ambient temperature**

        Both inlet and outlet satisfy :math:`T \leq T_0`:

        .. math::
            \dot{C}_{\mathrm{P}}
            = \dot{C}^{\mathrm{M}}_{\mathrm{out}}
            - \dot{C}^{\mathrm{M}}_{\mathrm{in}}

        .. math::
            \dot{C}_{\mathrm{F}}
            = \dot{C}^{\mathrm{TOT}}_{\mathrm{power,in}}
            + \bigl(\dot{C}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{C}^{\mathrm{T}}_{\mathrm{out}}\bigr)

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

        Raises
        ------
        ValueError
            If no inlet power stream is found.
        """
        # Retrieve the cost of power from the inlet stream of kind "power"
        power_cost = None
        for stream in self.inl.values():
            if stream.get("kind") == "power":
                power_cost = stream.get("C_TOT")
                break
        if power_cost is None:
            logging.error("No inlet power stream found to determine power cost (C_TOT).")
            raise ValueError("No inlet power stream found for exergoeconomic_balance.")

        # Compute product and fuel costs depending on inlet/outlet temperatures relative to T0.
        if self.inl[0]["T"] >= T0 and self.outl[0]["T"] >= T0:
            self.C_P = self.outl[0]["C_PH"] - self.inl[0]["C_PH"]
            self.C_F = power_cost
        elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] > T0:
            self.C_P = self.outl[0]["C_T"] + (self.outl[0]["C_M"] - self.inl[0]["C_M"])
            self.C_F = power_cost + self.inl[0]["C_T"]
        elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] <= T0:
            self.C_P = self.outl[0]["C_M"] - self.inl[0]["C_M"]
            self.C_F = power_cost + (self.inl[0]["C_T"] - self.outl[0]["C_T"])

        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.C_P - self.C_F) / self.C_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
