import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


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

        T_in = self.inl[0]['T']
        T_out = self.outl[0]['T']

        # Case-specific exergy calculations
        if T_in > T0 and T_out > T0 and T_in > T_out:
            self.E_P = np.nan
            self.E_F = self.inl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])
        elif T_out <= T0 and T_in > T0:
            if split_physical_exergy:
                self.E_P = self.inl[0]['m'] * self.outl[0]['e_T']
                self.E_F = self.inl[0]['m'] * (self.inl[0]['e_T'] + self.inl[0]['e_M'] - 
                                        self.outl[0]['e_M'])
            else:
                logging.warning(
                    "Exergy balance of a valve, where outlet temperature is smaller than "
                    "ambient temperature, is not implemented for non-split physical exergy."
                    "Valve is treated as dissipative."
                )
                self.E_P = np.nan
                self.E_F = self.inl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])

        elif T_in <= T0 and T_out <= T0:
            if split_physical_exergy:
                self.E_P = self.inl[0]['m'] * (self.outl[0]['e_T'] - self.inl[0]['e_T'])
                self.E_F = self.inl[0]['m'] * (self.inl[0]['e_M'] - self.outl[0]['e_M'])
            else:
                logging.warning(
                    "Exergy balance of a valve, where both temperatures are smaller than "
                    "ambient temperature, is not implemented for non-split physical exergy."
                    "Valve is treated as dissipative."
                )
                self.E_P = np.nan
                self.E_F = self.inl[0]['m'] * (self.inl[0]['e_PH'] - self.outl[0]['e_PH'])
        else:
            logging.warning(
                "Exergy balance of a valve, where outlet temperature is larger than "
                "inlet temperature, is not implemented."
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Valve exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the valve.
        
        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:
        
        For T_in > T0 and T_out > T0:
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
        if self.inl[0]["T"] > T0 and self.outl[0]["T"] > T0:
            logging.warning("This case is not implemented. The Valve should be treated as dissipative!")

        elif self.outl[0]["T"] <= T0:
            # --- Mechanical cost equation (always added) ---
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
            equations[counter] = f"aux_{self.name}_mech_{self.outl[0]['name']}"
            b[counter] = 0
            counter += 1
        else:
            msg = ('Exergy balance of a valve, where outlet temperature is larger than inlet temperature is not implemented.')
            logging.warning(msg)
            
        if chemical_exergy_enabled:
            # --- Chemical cost equation (conditionally added) ---
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = (1 / self.inl[0]["E_CH"] if self.inl[0]["e_CH"] != 0 else 1)
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = (-1 / self.outl[0]["E_CH"] if self.outl[0]["e_CH"] != 0 else -1)
            equations[counter+1] = f"aux_{self.name}_chem_{self.outl[0]['name']}"
            # Set right-hand side for both rows.
            b[counter] = 0
            counter += 1
        
        return A, b, counter, equations
            
    def dis_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled=False, all_components=None):
        """
        Constructs the cost equations for a dissipative Valve in ExerPy,
        distributing the valve’s extra cost difference (C_diff) to all other productive 
        components (non-dissipative and non-CycleCloser) in proportion to their exergy destruction (E_D)
        and adding an extra overall cost balance row that enforces:
        
        .. math::
           (\dot C_{\mathrm{in},T} - \dot C_{\mathrm{out},T})
           + (\dot C_{\mathrm{in},M} - \dot C_{\mathrm{out},M})
           - \dot C_{\mathrm{diff}}
           = -\,\dot Z_{\mathrm{costs}}

        In this formulation, the unknown cost variable in the "dissipative" column (i.e. C_diff)
        is solved for, ensuring the valve’s cost balance.
        
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
        equations[counter] = f"diss_valve_thermal_{self.name}"
        counter += 1

        # --- Mechanical difference row ---
        if self.inl[0].get("E_M", 0) and self.outl[0].get("E_M", 0):
            A[counter, self.inl[0]["CostVar_index"]["M"]] = 1 / self.inl[0]["E_M"]
            A[counter, self.outl[0]["CostVar_index"]["M"]] = -1 / self.outl[0]["E_M"]
        else:
            A[counter, self.inl[0]["CostVar_index"]["M"]] = 1
            A[counter, self.outl[0]["CostVar_index"]["M"]] = -1
        b[counter] = 0
        equations[counter] = f"diss_valve_mechanical_{self.name}"
        counter += 1

        # --- Distribution of dissipative cost difference to other components based on E_D ---
        if all_components is None:
            all_components = []
        # Serving components: all productive components (excluding self, any dissipative, and CycleCloser)
        serving = [comp for comp in all_components 
                if comp is not self 
                and not getattr(comp, "dissipative", False) 
                and comp.__class__.__name__ != "CycleCloser"]
        total_E_D = sum(getattr(comp, "E_D", 0) for comp in serving)
        diss_col = self.inl[0]["CostVar_index"].get("dissipative")
        if diss_col is None:
            logging.warning(f"No 'dissipative' column allocated for {self.name}.")
        else:
            if total_E_D == 0:
                # Fall back to equal distribution if total exergy destruction is zero.
                for comp in serving:
                    A[comp.exergy_cost_line, diss_col] += 1 / len(serving) if len(serving) > 0 else 0
            else:
                for comp in serving:
                    weight = getattr(comp, "E_D", 0) / total_E_D
                    A[comp.exergy_cost_line, diss_col] += weight

        # --- Extra overall cost balance row ---
        # This row enforces:
        #   (C_in,T - C_out,T) + (C_in,M - C_out,M) - C_diff = - Z_costs
        A[counter, self.inl[0]["CostVar_index"]["T"]] = 1
        A[counter, self.outl[0]["CostVar_index"]["T"]] = -1
        A[counter, self.inl[0]["CostVar_index"]["M"]] = 1
        A[counter, self.outl[0]["CostVar_index"]["M"]] = -1
        # Subtract the unknown dissipative cost difference:
        A[counter, self.inl[0]["CostVar_index"]["dissipative"]] = -1
        b[counter] = -self.Z_costs
        equations[counter] = f"diss_valve_balance_{self.name}"
        counter += 1

        return A, b, counter, equations



    def exergoeconomic_balance(self, T0):
        """
        Perform exergoeconomic balance calculations for the valve.
        
        This method calculates various exergoeconomic parameters including:
        - Cost rates of product (C_P) and fuel (C_F)
        - Specific cost of product (c_P) and fuel (c_F)
        - Cost rate of exergy destruction (C_D)
        - Relative cost difference (r)
        - Exergoeconomic factor (f)
        
        Parameters
        ----------
        T0 : float
            Ambient temperature
            
        Notes
        -----
        The exergoeconomic balance considers thermal (T), chemical (CH),
        and mechanical (M) exergy components for the inlet and outlet streams.
        """
        if self.inl[0]["T"] > T0 and self.outl[0]["T"] > T0:
            self.C_F = self.inl[0]['C_PH'] - self.outl[0]['C_PH']
            self.C_P = np.nan
            # dissipative
        elif self.outl[0]["T"] <= T0 and self.inl[0]["T"] > T0:
            self.C_P = self.outl[0]["C_T"]
            self.C_F = self.inl[0]["C_T"] + (
                self.inl[0]["C_M"] - self.outl[0]["C_M"])
        elif self.inl[0]["T"] <= T0 and self.outl[0]["T"] <= T0:
            self.C_P = self.outl[0]["C_T"] - self.inl[0]["C_T"]
            self.C_F = self.inl[0]["C_M"] - self.outl[0]["C_M"]
        else:
            msg = ('Exergy balance of a valve, where outlet temperature is '
                'larger than inlet temperature is not implmented.')
            logging.warning(msg)
            self.C_P = np.nan
            self.C_F = np.nan

        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
