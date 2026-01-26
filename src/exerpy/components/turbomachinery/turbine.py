import logging

import numpy as np

from exerpy.components.component import Component, component_registry


@component_registry
class Turbine(Component):
    r"""
    Class for exergy analysis of turbines.

    This class performs exergy analysis calculations for turbines, with definitions
    of exergy product and fuel varying based on the temperature relationships between
    inlet stream, outlet stream, and ambient conditions.

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
    P : float
        Power output of the turbine in :math:`\mathrm{W}`.
    inl : dict
        Dictionary containing inlet stream data with temperature, mass flows,
        enthalpies, and specific exergies. Must have at least one inlet.
    outl : dict
        Dictionary containing outlet streams data with temperature, mass flows,
        enthalpies, and specific exergies. Can have multiple outlets, their
        properties will be summed up in the calculations.

    Notes
    -----
    The exergy analysis considers three cases based on temperature relationships:

    .. math::

        \dot{E}_\mathrm{P} =
        \begin{cases}
        -P & T_\mathrm{in}, T_\mathrm{out} \geq T_0\\
        -P + \dot{E}_\mathrm{out}^\mathrm{T}
        & T_\mathrm{in} > T_0 \geq T_\mathrm{out}\\
        -P + \dot{E}_\mathrm{out}^\mathrm{T} - \dot{E}_\mathrm{in}^\mathrm{T}
        & T_0 \geq T_\mathrm{in}, T_\mathrm{out}
        \end{cases}

        \dot{E}_\mathrm{F} =
        \begin{cases}
        \dot{E}_\mathrm{in}^\mathrm{PH} - \dot{E}_\mathrm{out}^\mathrm{PH}
        & T_\mathrm{in}, T_\mathrm{out} \geq T_0\\
        \dot{E}_\mathrm{in}^\mathrm{T} + \dot{E}_\mathrm{in}^\mathrm{M} -
        \dot{E}_\mathrm{out}^\mathrm{M}
        & T_\mathrm{in} > T_0 \geq T_\mathrm{out}\\
        \dot{E}_\mathrm{in}^\mathrm{M} - \dot{E}_\mathrm{out}^\mathrm{M}
        & T_0 \geq T_\mathrm{in}, T_\mathrm{out}
        \end{cases}
    """

    def __init__(self, **kwargs):
        r"""Initialize turbine component with given parameters."""
        super().__init__(**kwargs)
        self.P = None

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the turbine.

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
        # Get net power flow
        net_power = 0.0  # Initialize to 0.0, not None
        for idx, conn in self.inl.items():
            if conn is not None and conn.get("kind") == "power" and "energy_flow" in conn:
                net_power -= conn["energy_flow"]  # Subtract inlet power
        for idx, conn in self.outl.items():
            if conn is not None and conn.get("kind") == "power" and "energy_flow" in conn:
                net_power += conn["energy_flow"]  # Add outlet power

        # Use net_power if available, otherwise calculate from enthalpy balance
        if net_power != 0.0:
            self.P = abs(net_power)
        else:
            self.P = self._total_outlet("m", "h") - self.inl[0]["m"] * self.inl[0]["h"]

        # Case 1: Both temperatures above ambient
        if self.inl[0]["T"] >= T0 and self.outl[0]["T"] >= T0 and self.inl[0]["T"] >= self.outl[0]["T"]:
            self.E_P = abs(self.P)
            self.E_F = self.inl[0]["m"] * self.inl[0]["e_PH"] - self._total_outlet("m", "e_PH")

        # Case 2: Inlet above, outlet at/below ambient
        elif self.inl[0]["T"] > T0 and self.outl[0]["T"] <= T0:
            if split_physical_exergy:
                self.E_P = abs(self.P) + self._total_outlet("m", "e_T")
                self.E_F = (
                    self.inl[0]["m"] * self.inl[0]["e_T"]
                    + self.inl[0]["m"] * self.inl[0]["e_M"]
                    - self._total_outlet("m", "e_M")
                )
            else:
                logging.warning(
                    "While dealing with expander below ambient, "
                    "physical exergy should be split into thermal and mechanical components!"
                )
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 3: Both temperatures at/below ambient
        elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] <= T0:
            if split_physical_exergy:
                self.E_P = abs(self.P) + (self._total_outlet("m", "e_T") - self.inl[0]["m"] * self.inl[0]["e_T"])
                self.E_F = self.inl[0]["m"] * self.inl[0]["e_M"] - self._total_outlet("m", "e_M")
            else:
                logging.warning(
                    "While dealing with expander below ambient, "
                    "physical exergy should be split into thermal and mechanical components!"
                )
                self.E_P = np.nan
                self.E_F = np.nan
        # Invalid case: outlet temperature larger than inlet
        else:
            logging.warning(
                "Exergy balance of a turbine where outlet temperature is larger "
                "than inlet temperature is not implemented."
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        if np.nan == self.E_F:
            self.E_D = self.inl[0]["m"] * self.inl[0]["e_PH"] - self._total_outlet("m", "e_PH") - abs(self.P)
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Exergy balance of Turbine {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def _total_outlet(self, mass_flow: str, property_name: str) -> float:
        r"""
        Calculate the sum of mass flow times property across all outlets.

        Parameters
        ----------
        mass_flow : str
            Key for the mass flow value.
        property_name : str
            Key for the property to be summed.

        Returns
        -------
        float
            Sum of mass flow times property across all outlets.
        """
        total = 0.0
        for outlet in self.outl.values():
            # Skip power connections; treat missing "kind" as material for backward compatibility
            if outlet and outlet.get("kind", "material") != "power" and mass_flow in outlet and property_name in outlet:
                total += outlet[mass_flow] * outlet[property_name]
        return total

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the turbine.

        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:

        For each material outlet (when inlet and first outlet are above ambient temperature T0):

        (1) 1/E_T_in * C_T_in - 1/E_T_out * C_T_out = 0
            - F-principle: specific thermal exergy costs equalized between inlet and each outlet

        (2) 1/E_M_in * C_M_in - 1/E_M_out * C_M_out = 0
            - F-principle: specific mechanical exergy costs equalized between inlet and each outlet

        (3) 1/E_CH_in * C_CH_in - 1/E_CH_out * C_CH_out = 0 (if chemical_exergy_enabled)
            - F-principle: specific chemical exergy costs equalized between inlet and each outlet

        For power outlets (with both source and target components):

        (4) 1/E_ref * C_ref - 1/E_out * C_out = 0
            - P-principle: specific power exergy costs equalized across all power outlets

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
            The updated row index after adding all auxiliary equations.
        equations : list or dict
            Updated structure with equation labels.
        """
        # Process only if the inlet and the first outlet are above T0.
        if self.inl[0]["T"] > T0 and self.outl[0]["T"] > T0:
            # Filter material outlets
            material_outlets = [outlet for outlet in self.outl.values() if outlet.get("kind") == "material"]
            # Determine number of rows per outlet.
            num_rows_per_outlet = 3 if chemical_exergy_enabled else 2

            for i, outlet in enumerate(material_outlets):
                row_offset = num_rows_per_outlet * i

                # --- Thermal exergy equation ---
                A[counter + row_offset, self.inl[0]["CostVar_index"]["T"]] = (
                    1 / self.inl[0]["E_T"] if self.inl[0]["e_T"] != 0 else 1
                )
                A[counter + row_offset, outlet["CostVar_index"]["T"]] = -1 / outlet["E_T"] if outlet["e_T"] != 0 else -1
                equations[counter + row_offset] = {
                    "kind": "aux_f_rule",
                    "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                    "property": "c_T",
                }

                # --- Mechanical exergy equation ---
                A[counter + row_offset + 1, self.inl[0]["CostVar_index"]["M"]] = (
                    1 / self.inl[0]["E_M"] if self.inl[0]["e_M"] != 0 else 1
                )
                A[counter + row_offset + 1, outlet["CostVar_index"]["M"]] = (
                    -1 / outlet["E_M"] if outlet["e_M"] != 0 else -1
                )
                equations[counter + row_offset + 1] = {
                    "kind": "aux_f_rule",
                    "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                    "property": "c_M",
                }

                # --- Chemical exergy equation (conditionally added) ---
                if chemical_exergy_enabled:
                    A[counter + row_offset + 2, self.inl[0]["CostVar_index"]["CH"]] = (
                        1 / self.inl[0]["E_CH"] if self.inl[0]["e_CH"] != 0 else 1
                    )
                    A[counter + row_offset + 2, outlet["CostVar_index"]["CH"]] = (
                        -1 / outlet["E_CH"] if outlet["e_CH"] != 0 else -1
                    )
                    equations[counter + row_offset + 2] = {
                        "kind": "aux_equality",
                        "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                        "property": "c_CH",
                    }

            # Update counter based on number of rows added for all material outlets.
            num_material_rows = num_rows_per_outlet * len(material_outlets)
            for j in range(num_material_rows):
                b[counter + j] = 0
            counter += num_material_rows
        else:
            logging.warning("Turbine with outlet below T0 not implemented in exergoeconomics yet!")

        # --- Auxiliary equation for shaft power equality ---
        power_outlets = [
            outlet
            for outlet in self.outl.values()
            if outlet.get("kind") == "power" and outlet.get("source_component") and outlet.get("target_component")
        ]
        if len(power_outlets) > 1:
            ref = power_outlets[0]
            ref_idx = ref["CostVar_index"]["exergy"]
            for outlet in power_outlets[1:]:
                cur_idx = outlet["CostVar_index"]["exergy"]
                A[counter, ref_idx] = 1 / ref["E"] if ref["E"] != 0 else 1
                A[counter, cur_idx] = -1 / outlet["E"] if outlet["E"] != 0 else -1
                b[counter] = 0
                equations[counter] = {
                    "kind": "aux_p_rule",
                    "objects": [self.name],
                    "property": "c_TOT (more power flows)",
                }
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""
        Perform exergoeconomic cost balance for the turbine.

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
        exergoeconomic indicators. The turbine may have multiple power outputs
        and multiple material outlets. The product cost includes the total cost
        of all power streams, while material outlet costs are summed accordingly.

        **Case 1: Inlet and outlet above ambient temperature**

        Both inlet and first material outlet satisfy :math:`T \geq T_0`:

        .. math::
            \dot{C}_{\mathrm{P}}
            = \sum \dot{C}^{\mathrm{TOT}}_{\mathrm{power,out}}

        .. math::
            \dot{C}_{\mathrm{F}}
            = \dot{C}^{\mathrm{PH}}_{\mathrm{in}}
            - \sum \dot{C}^{\mathrm{PH}}_{\mathrm{material,out}}

        **Case 2: Inlet above and outlet at or below ambient temperature**

        Inlet satisfies :math:`T > T_0` and first material outlet :math:`T \leq T_0`:

        .. math::
            \dot{C}_{\mathrm{P}}
            = \sum \dot{C}^{\mathrm{TOT}}_{\mathrm{power,out}}
            + \sum \dot{C}^{\mathrm{T}}_{\mathrm{material,out}}

        .. math::
            \dot{C}_{\mathrm{F}}
            = \dot{C}^{\mathrm{T}}_{\mathrm{in}}
            + \bigl(\dot{C}^{\mathrm{M}}_{\mathrm{in}}
            - \sum \dot{C}^{\mathrm{M}}_{\mathrm{material,out}}\bigr)

        **Case 3: Both inlet and outlet at or below ambient temperature**

        Both inlet and first material outlet satisfy :math:`T \leq T_0`:

        .. math::
            \dot{C}_{\mathrm{P}}
            = \sum \dot{C}^{\mathrm{TOT}}_{\mathrm{power,out}}
            + \bigl(\sum \dot{C}^{\mathrm{T}}_{\mathrm{material,out}}
            - \dot{C}^{\mathrm{T}}_{\mathrm{in}}\bigr)

        .. math::
            \dot{C}_{\mathrm{F}}
            = \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            - \sum \dot{C}^{\mathrm{M}}_{\mathrm{material,out}}

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
        # Sum the cost of all outlet power streams.
        C_power_out = sum(stream.get("C_TOT", 0) for stream in self.outl.values() if stream.get("kind") == "power")
        # Assume a single primary inlet for material cost properties.
        inlet = self.inl[0]
        # Filter material outlets and sum their cost components.
        material_outlets = [out for out in self.outl.values() if out.get("kind") == "material"]
        sum_C_PH_out = sum(out.get("C_PH", 0) for out in material_outlets)
        sum_C_T_out = sum(out.get("C_T", 0) for out in material_outlets)
        sum_C_M_out = sum(out.get("C_M", 0) for out in material_outlets)

        # Case 1: Both inlet and first outlet above ambient.
        if inlet["T"] >= T0 and self.outl[0]["T"] >= T0:
            self.C_P = C_power_out
            self.C_F = inlet.get("C_PH", 0) - sum_C_PH_out

        # Case 2: Inlet above ambient and outlet at or below ambient.
        elif inlet["T"] > T0 and self.outl[0]["T"] <= T0:
            self.C_P = C_power_out + sum_C_T_out
            self.C_F = inlet.get("C_T", 0) + (inlet.get("C_M", 0) - sum_C_M_out)

        # Case 3: Both inlet and outlet at or below ambient.
        elif inlet["T"] <= T0 and self.outl[0]["T"] <= T0:
            self.C_P = C_power_out + (sum_C_T_out - inlet.get("C_T", 0))
            self.C_F = inlet.get("C_M", 0) - sum_C_M_out

        else:
            logging.warning(
                "Exergoeconomic balance of a turbine with outlet temperature larger than inlet is not implemented."
            )
            self.C_P = np.nan
            self.C_F = np.nan

        # Calculate the specific cost terms and exergoeconomic parameters.
        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.C_P - self.C_F) / self.C_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
