import logging

import numpy as np

from exerpy.components.component import Component, component_registry


@component_registry
class Valve(Component):
    r"""
    Class for exergy and exergoeconomic analysis of valves.

    This class performs exergy and exergoeconomic analysis calculations for valve components,
    accounting for one inlet and one outlet streams across various temperature regimes, including
    above and below ambient temperature.

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

    Notes
    -----
    The exergy analysis accounts for physical, thermal, and mechanical exergy
    based on temperature relationships:

    .. math::

        \dot{E}_\mathrm{P} =
        \begin{cases}
        \text{not defined (nan)}
        & T_\mathrm{in}, T_\mathrm{out} > T_0\\
        \dot{m} \cdot e_\mathrm{out}^\mathrm{T}
        & T_\mathrm{in} > T_0 \geq T_\mathrm{out}\\
        \dot{m} \cdot (e_\mathrm{out}^\mathrm{T} - e_\mathrm{in}^\mathrm{T})
        & T_0 \geq T_\mathrm{in}, T_\mathrm{out}
        \end{cases}

        \dot{E}_\mathrm{F} =
        \begin{cases}
        \dot{m} \cdot (e_\mathrm{in}^\mathrm{PH} - e_\mathrm{out}^\mathrm{PH})
        & T_\mathrm{in}, T_\mathrm{out} > T_0\\
        \dot{m} \cdot (e_\mathrm{in}^\mathrm{T} + e_\mathrm{in}^\mathrm{M}
        - e_\mathrm{out}^\mathrm{M})
        & T_\mathrm{in} > T_0 \geq T_\mathrm{out}\\
        \dot{m} \cdot (e_\mathrm{in}^\mathrm{M} - e_\mathrm{out}^\mathrm{M})
        & T_0 \geq T_\mathrm{in}, T_\mathrm{out}
        \end{cases}

    For all cases, except when :math:`T_\mathrm{out} > T_\mathrm{in}`, the exergy
    destruction is calculated as:

    .. math::
        \dot{E}_\mathrm{D} = \begin{cases}
        \dot{E}_\mathrm{F} & \text{if } \dot{E}_\mathrm{P} = \text{nan}\\
        \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P} & \mathrm{otherwise}
        \end{cases}

    Where:
        - :math:`e^\mathrm{T}`: Thermal exergy
        - :math:`e^\mathrm{PH}`: Physical exergy
        - :math:`e^\mathrm{M}`: Mechanical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize valve component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the valve.

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

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 1 or len(self.outl) < 1:
            raise ValueError("Valve requires at least one inlet and one outlet.")

        T_in = self.inl[0]["T"]
        T_out = self.outl[0]["T"]

        p_in = self.inl[0]["p"]
        p_out = self.outl[0]["p"]

        # Check for zero mass flow
        if abs(self.inl[0]["m"]) < 1e-10:
            logging.info(f"Valve {self.name} has zero mass flow: exergy balance not considered.")
            self.E_P = np.nan
            self.E_F = np.nan
            self.E_D = np.nan
            self.epsilon = np.nan
            return

        # Check if inlet and outlet are physically identical
        if abs(T_in - T_out) < 1e-2 and abs(p_in - p_out) <= 1e-4 * max(p_in, 1e-9):
            logging.info(f"Valve {self.name} inlet and outlet are physically identical.")
            self.E_P = 0.0
            self.E_F = 0.0
            self.E_D = 0.0
            self.epsilon = 1.0
            logging.info(
                f"Valve exergy balance calculated: "
                f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
                f"Efficiency={self.epsilon:.2%}"
            )
            return

        # Case 1: Both temperatures above ambient
        if T_in > T0 and T_out > T0:
            self.E_P = np.nan
            self.E_F = self.inl[0]["m"] * (self.inl[0]["e_PH"] - self.outl[0]["e_PH"])

        # Case 2: Inlet above ambient, outlet below or equal to ambient
        elif T_in > T0 and T_out <= T0:
            if split_physical_exergy:
                self.E_P = self.inl[0]["m"] * self.outl[0]["e_T"]
                self.E_F = self.inl[0]["m"] * (self.inl[0]["e_T"] + self.inl[0]["e_M"] - self.outl[0]["e_M"])
            else:
                logging.warning(
                    "Exergy balance of a valve, where outlet temperature is smaller than "
                    "ambient temperature, is not implemented for non-split physical exergy. "
                    "Valve is treated as dissipative."
                )
                self.E_P = np.nan
                self.E_F = self.inl[0]["m"] * (self.inl[0]["e_PH"] - self.outl[0]["e_PH"])

        # Case 3: Both temperatures below ambient
        elif T_in <= T0 and T_out <= T0:
            if split_physical_exergy:
                self.E_P = self.inl[0]["m"] * (self.outl[0]["e_T"] - self.inl[0]["e_T"])
                self.E_F = self.inl[0]["m"] * (self.inl[0]["e_M"] - self.outl[0]["e_M"])
            else:
                logging.warning(
                    "Exergy balance of a valve, where both temperatures are smaller than "
                    "ambient temperature, is not implemented for non-split physical exergy."
                    "Valve is treated as dissipative."
                )
                self.E_P = np.nan
                self.E_F = self.inl[0]["m"] * (self.inl[0]["e_PH"] - self.outl[0]["e_PH"])

        # Case 4: Inlet below or at ambient, outlet above ambient
        elif T_in <= T0 and T_out > T0:
            logging.warning(
                f"Valve {self.name} with temperature increase from below ambient to above ambient - "
                "non-physical behavior. Treated as dissipative."
            )
            self.E_P = np.nan
            self.E_F = self.inl[0]["m"] * (self.inl[0]["e_PH"] - self.outl[0]["e_PH"])

        else:
            logging.error(
                f"Valve {self.name} encountered an unexpected condition: "
                f"T_in={T_in:.2f} K, T_out={T_out:.2f} K, T0={T0:.2f} K. "
                "This should not occur - exergy balance cannot be calculated."
            )
            self.E_P = np.nan
            self.E_F = np.nan
            self.E_D = np.nan
            self.epsilon = np.nan
            return

        # Calculate exergy destruction
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Exergy balance of Valve {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the valve.

        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:

        For (T_in > T0 and T_out > T0) or (T_in <= T0 and T_out > T0):
            - Valve is treated as dissipative (warning issued)

        For T_out <= T0:
        (1) 1/E_M_in * C_M_in - 1/E_M_out * C_M_out = 0

        - F-principle: specific mechanical exergy costs equalized between inlet/outlet

        - If E_M is zero for either stream, appropriate fallback coefficients are used

        When chemical_exergy_enabled is True:
        (2) 1/E_CH_in * C_CH_in - 1/E_CH_out * C_CH_out = 0

        - F-principle: specific chemical exergy costs equalized between inlet/outlet
        - If E_CH is zero for either stream, appropriate fallback coefficients are used

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
            The updated row index.
        equations : dict
            Updated dictionary with equation labels.
        """

        # Check if valve is dissipative
        if np.isnan(self.E_P):
            logging.warning(f"Valve {self.name} is dissipative - no auxiliary equations added.")
            return A, b, counter, equations

        # Productive valve - T_out must be ≤ T0 (Cases 2 or 3)
        # Mechanical cost equation (always added for productive valves)
        if self.inl[0]["e_M"] != 0 and self.outl[0]["e_M"] != 0:
            A[counter, self.inl[0]["CostVar_index"]["M"]] = 1 / self.inl[0]["E_M"]
            A[counter, self.outl[0]["CostVar_index"]["M"]] = -1 / self.outl[0]["E_M"]
        elif self.inl[0]["e_M"] == 0 and self.outl[0]["e_M"] != 0:
            A[counter, self.inl[0]["CostVar_index"]["M"]] = 1
        elif self.inl[0]["e_M"] != 0 and self.outl[0]["e_M"] == 0:
            A[counter, self.outl[0]["CostVar_index"]["M"]] = 1
        else:
            A[counter, self.inl[0]["CostVar_index"]["M"]] = 1
            A[counter, self.outl[0]["CostVar_index"]["M"]] = -1
        equations[counter] = {
            "kind": "aux_equality",
            "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
            "property": "c_M",
        }
        b[counter] = 0
        counter += 1

        if chemical_exergy_enabled:
            # --- Chemical cost equation (conditionally added) ---
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = 1 / self.inl[0]["E_CH"] if self.inl[0]["e_CH"] != 0 else 1
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = (
                -1 / self.outl[0]["E_CH"] if self.outl[0]["e_CH"] != 0 else -1
            )
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            # Set right-hand side for both rows.
            b[counter] = 0
            counter += 1

        return A, b, counter, equations

    def dis_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled=False, all_components=None):
        r"""
        Constructs the cost equations for a dissipative Valve in ExerPy,
        distributing the valve's extra cost difference (C_diff) to all other productive
        components (non-dissipative and non-CycleCloser) in proportion to their exergy destruction (E_D)
        and adding an extra overall cost balance row that enforces:

        .. math::
           (\dot C_{\mathrm{in},T} - \dot C_{\mathrm{out},T})
           + (\dot C_{\mathrm{in},M} - \dot C_{\mathrm{out},M})
           - \dot C_{\mathrm{diff}}
           = -\,\dot Z_{\mathrm{costs}}

        In this formulation, the unknown cost variable in the "dissipative" column (i.e. C_diff)
        is solved for, ensuring the valve's cost balance.

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the cost matrix.
        T0 : float
            Ambient temperature (not explicitly used here).
        equations : dict
            Dictionary mapping row indices to equation labels.
        chemical_exergy_enabled : bool, optional
            Flag indicating whether chemical exergy is considered. (Ignored here.)
        all_components : list, optional
            Global list of all component objects; if not provided, defaults to [].

        Returns
        -------
        tuple
            Updated (A, b, counter, equations).

        Notes
        -----
        - It is assumed that each inlet/outlet stream's CostVar_index dictionary has keys: "T" (thermal), "M" (mechanical), and "dissipative" (the extra unknown).
        - self.Z_costs is the known cost rate (in currency/s) for the valve.
        """
        # --- Thermal difference row ---
        if self.inl[0].get("E_T", 0) and self.outl[0].get("E_T", 0):
            A[counter, self.inl[0]["CostVar_index"]["T"]] = 1 / self.inl[0]["E_T"]
            A[counter, self.outl[0]["CostVar_index"]["T"]] = -1 / self.outl[0]["E_T"]
        else:
            A[counter, self.inl[0]["CostVar_index"]["T"]] = 1
            A[counter, self.outl[0]["CostVar_index"]["T"]] = -1
        b[counter] = 0
        equations[counter] = {
            "kind": "dis_equality",
            "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
            "property": "c_T",
        }
        counter += 1

        # --- Mechanical difference row ---
        if self.inl[0].get("E_M", 0) and self.outl[0].get("E_M", 0):
            A[counter, self.inl[0]["CostVar_index"]["M"]] = 1 / self.inl[0]["E_M"]
            A[counter, self.outl[0]["CostVar_index"]["M"]] = -1 / self.outl[0]["E_M"]
        else:
            A[counter, self.inl[0]["CostVar_index"]["M"]] = 1
            A[counter, self.outl[0]["CostVar_index"]["M"]] = -1
        b[counter] = 0
        equations[counter] = {
            "kind": "dis_equality",
            "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
            "property": "c_M",
        }
        counter += 1

        # --- Chemical difference row (if chemical exergy is enabled) ---
        if chemical_exergy_enabled:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = 1 / self.inl[0]["E_CH"] if self.inl[0]["E_CH"] != 0 else 1
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = (
                -1 / self.outl[0]["E_CH"] if self.outl[0]["E_CH"] != 0 else -1
            )
            b[counter] = 0
            equations[counter] = {
                "kind": "dis_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            counter += 1

        # --- Distribution of dissipative cost difference to other components based on E_D ---
        if all_components is None:
            all_components = []
        # Serving components: all productive components (excluding self, any dissipative, and CycleCloser)
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
            logging.error(f"No 'dissipative' column allocated for {self.name}.")
        else:
            if total_E_D == 0:
                if len(serving) > 0:
                    for comp in serving:
                        A[comp.exergy_cost_line, diss_col] = 1 / len(serving)
                else:
                    logging.warning(f"No serving components found for dissipative component {self.name}")
            else:
                for comp in serving:
                    weight = getattr(comp, "E_D", 0) / total_E_D
                    comp.serving_weight = weight
                    A[comp.exergy_cost_line, diss_col] = weight

        # --- Extra overall cost balance row ---
        # This row enforces:
        #   (C_in,T - C_out,T) + (C_in,M - C_out,M) - C_diff = - Z_costs
        A[counter, self.inl[0]["CostVar_index"]["T"]] = 1
        A[counter, self.outl[0]["CostVar_index"]["T"]] = -1
        A[counter, self.inl[0]["CostVar_index"]["M"]] = 1
        A[counter, self.outl[0]["CostVar_index"]["M"]] = -1
        if chemical_exergy_enabled:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = 1
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = -1
        # Subtract the unknown dissipative cost difference:
        A[counter, self.inl[0]["CostVar_index"]["dissipative"]] = -1
        b[counter] = -self.Z_costs
        equations[counter] = {"kind": "dis_balance", "objects": [self.name], "property": "dissipative_cost_balance"}
        counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""
        Perform exergoeconomic cost balance for the valve (throttling component).

        The valve is a throttling device that reduces pressure without doing work.
        Unlike other components, a valve can be either **dissipative** (purely destructive)
        or **productive** depending on temperature conditions and whether physical
        exergy is split into thermal and mechanical components.

        **Dissipative Valve (E_P is NaN):**

        When the valve has no identifiable product (Cases 1, 4, or Cases 2-3 without split),
        the entire exergy loss is considered destruction. The cost of fuel is the decrease
        in physical exergy cost:

        .. math::
            \dot{C}_{\mathrm{F}} = \dot{C}_{\mathrm{in}}^{\mathrm{PH}} - \dot{C}_{\mathrm{out}}^{\mathrm{PH}}

        .. math::
            \dot{C}_{\mathrm{P}} = \text{NaN (no product)}

        **Productive Valve (E_P has a value):**

        When physical exergy is split (split_physical_exergy=True) and specific temperature
        conditions are met, the valve can have a product:

        *Case 2 (Inlet above T0, outlet below T0):*

        The product is the thermal exergy at the outlet (cooling capacity), and the fuel
        is the thermal exergy decrease plus the mechanical exergy loss:

        .. math::
            \dot{C}_{\mathrm{P}} = \dot{C}_{\mathrm{out}}^{\mathrm{T}}

        .. math::
            \dot{C}_{\mathrm{F}} = \dot{C}_{\mathrm{in}}^{\mathrm{T}} + (\dot{C}_{\mathrm{in}}^{\mathrm{M}} - \dot{C}_{\mathrm{out}}^{\mathrm{M}})

        *Case 3 (Both inlet and outlet below T0):*

        The product is the increase in thermal exergy (cooling capacity increase), and
        the fuel is the mechanical exergy loss:

        .. math::
            \dot{C}_{\mathrm{P}} = \dot{C}_{\mathrm{out}}^{\mathrm{T}} - \dot{C}_{\mathrm{in}}^{\mathrm{T}}

        .. math::
            \dot{C}_{\mathrm{F}} = \dot{C}_{\mathrm{in}}^{\mathrm{M}} - \dot{C}_{\mathrm{out}}^{\mathrm{M}}

        **Calculated exergoeconomic indicators:**

        Specific cost of fuel:

        .. math::
            c_{\mathrm{F}} = \frac{\dot{C}_{\mathrm{F}}}{\dot{E}_{\mathrm{F}}}

        Specific cost of product:

        .. math::
            c_{\mathrm{P}} = \frac{\dot{C}_{\mathrm{P}}}{\dot{E}_{\mathrm{P}}}

        Cost rate of exergy destruction:

        .. math::
            \dot{C}_{\mathrm{D}} = c_{\mathrm{F}} \cdot \dot{E}_{\mathrm{D}}

        Relative cost difference:

        .. math::
            r = \frac{c_{\mathrm{P}} - c_{\mathrm{F}}}{c_{\mathrm{F}}}

        Exergoeconomic factor:

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
        C_P : float or NaN
            Cost rate of product (currency/time). NaN for dissipative valves.
        C_F : float or NaN
            Cost rate of fuel (currency/time).
        c_P : float or NaN
            Specific cost of product (currency/energy). NaN for dissipative valves.
        c_F : float or NaN
            Specific cost of fuel (currency/energy).
        C_D : float or NaN
            Cost rate of exergy destruction (currency/time).
        r : float or NaN
            Relative cost difference (dimensionless). NaN for dissipative valves.
        f : float or NaN
            Exergoeconomic factor (dimensionless).

        Notes
        -----
        The valve is unique among components because:

        1. It typically has no capital cost (Z_costs ≈ 0), making the exergoeconomic
        factor f close to zero.

        2. It can be dissipative (no product) or productive (identifiable product)
        depending on the analysis approach and temperature conditions.

        3. For dissipative valves, many exergoeconomic parameters are NaN since there
        is no identifiable product.

        4. The relative cost difference r is calculated using specific costs (c_P and c_F)
        rather than total cost rates, unlike generator and motor components.

        5. The method handles NaN values throughout to accommodate both dissipative
        and productive valve configurations.

        The exergy destruction E_D and product/fuel definitions E_P and E_F must be
        computed prior to calling this method (via exergy_balance).

        For refrigeration cycles (Case 2) or cryogenic applications (Case 3), the
        productive valve approach may be more appropriate. For typical throttling
        applications, the dissipative approach is standard.
        """
        # Check if valve is dissipative
        if np.isnan(self.E_P):
            # Dissipative valve (Cases 1, 4, or Cases 2-3 without split)
            self.C_F = self.inl[0]["C_PH"] - self.outl[0]["C_PH"]
            self.C_P = np.nan
        else:
            # Productive valve (Cases 2 or 3 with split_physical_exergy=True)
            if self.outl[0]["T"] <= T0 and self.inl[0]["T"] > T0:
                # Case 2 with split
                self.C_P = self.outl[0]["C_T"]
                self.C_F = self.inl[0]["C_T"] + (self.inl[0]["C_M"] - self.outl[0]["C_M"])
            elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] <= T0:
                # Case 3 with split
                self.C_P = self.outl[0]["C_T"] - self.inl[0]["C_T"]
                self.C_F = self.inl[0]["C_M"] - self.outl[0]["C_M"]
            else:
                logging.error(f"Productive valve {self.name} in unexpected temperature regime.")
                self.C_P = np.nan
                self.C_F = np.nan

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
