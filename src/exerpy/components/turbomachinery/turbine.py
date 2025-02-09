import logging
import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

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
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\text{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\mathrm{P}` in :math:`\text{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\text{W}`.
    epsilon : float
        Exergetic efficiency of the component :math:`\varepsilon` in :math:`-`.
    P : float
        Power output of the turbine in :math:`\text{W}`.
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

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the turbine.

        Performs exergy balance calculations considering the temperature relationships
        between inlet stream, outlet stream, and ambient conditions.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.
        """      
        # Get power flow if not already available
        if self.P is None:
            self.P = self._total_outlet('m', 'h') - self.inl[0]['m'] * self.inl[0]['h']

        # Case 1: Both temperatures above ambient
        if self.inl[0]['T'] >= T0 and self.outl[0]['T'] >= T0:
            self.E_P = abs(self.P)
            self.E_F = (self.inl[0]['m'] * self.inl[0]['e_PH'] - 
                        self._total_outlet('m', 'e_PH'))

        # Case 2: Inlet above, outlet at/below ambient
        elif self.inl[0]['T'] > T0 and self.outl[0]['T'] <= T0:
            self.E_P = abs(self.P) + self._total_outlet('m', 'e_T')
            self.E_F = (self.inl[0]['m'] * self.inl[0]['e_T'] + 
                        self.inl[0]['m'] * self.inl[0]['e_M'] - 
                        self._total_outlet('m', 'e_M'))

        # Case 3: Both temperatures at/below ambient
        elif self.inl[0]['T'] <= T0 and self.outl[0]['T'] <= T0:
            self.E_P = abs(self.P) + (
                self._total_outlet('m', 'e_T') - self.inl[0]['m'] * self.inl[0]['e_T'])
            self.E_F = (self.inl[0]['m'] * self.inl[0]['e_M'] - 
                        self._total_outlet('m', 'e_M'))

        # Invalid case: outlet temperature larger than inlet
        else:
            logging.warning(
                'Exergy balance of a turbine where outlet temperature is larger '
                'than inlet temperature is not implemented.'
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Turbine exergy balance calculated: "
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
            if outlet and mass_flow in outlet and property_name in outlet:
                total += outlet[mass_flow] * outlet[property_name]
        return total
    

    def exergoeconomic_balance(self, T0: float) -> None:
        """        
        Calculate the exergoeconomic balance of the turbine.

        This function calculates:
        - C_P: Cost flow associated with the product exergy
        - C_F: Cost flow associated with the fuel exergy
        - c_F: Specific cost for fuel exergy [currency / W]
        - c_P: Specific cost for product exergy [currency / W]
        - C_D: Cost flow of exergy destruction
        - r: Relative cost difference
        - f: Exergoeconomic factor

        Requires:
        - self.inl[0] and self.outl[i] each have 'e_PH', 'e_CH' (if applicable), 'm', 'e_T', 'e_M'
        - self.Z_costs must be set beforehand (e.g., by ExergoeconomicAnalysis)
        - self.E_F, self.E_P, self.E_D already computed by calc_exergy_balance
        """
        # Extract inlet connection
        inlet = self.inl[0]

        # Initialize sums for outlet properties
        total_m_out = 0.0
        total_e_PH_out = 0.0
        total_e_CH_out = 0.0
        total_e_T_out = 0.0
        total_e_M_out = 0.0

        # Sum properties over all outlet connections
        for outlet in self.outl.values():
            if outlet:
                total_m_out += outlet.get('m', 0.0)
                total_e_PH_out += outlet.get('e_PH', 0.0) * outlet.get('m', 0.0)
                total_e_CH_out += outlet.get('e_CH', 0.0) * outlet.get('m', 0.0)
                total_e_T_out += outlet.get('e_T', 0.0) * outlet.get('m', 0.0)
                total_e_M_out += outlet.get('e_M', 0.0) * outlet.get('m', 0.0)

        # Calculate cost flows based on temperature relationships
        if inlet['T'] >= T0 and all(out['T'] >= T0 for out in self.outl.values() if out):
            # Case 1: Both inlet and all outlets above ambient
            self.C_P = self.C_bus
            self.C_F = inlet.get('e_PH', 0.0) * inlet.get('m', 0.0) - total_e_PH_out
        elif inlet['T'] > T0 and all(out['T'] <= T0 for out in self.outl.values() if out):
            # Case 2: Inlet above, all outlets at or below ambient
            self.C_P = self.C_bus + total_e_T_out
            self.C_F = inlet.get('e_T', 0.0) * inlet.get('m', 0.0) + \
                    inlet.get('e_M', 0.0) * inlet.get('m', 0.0) - \
                    total_e_M_out
        elif all(out['T'] <= T0 for out in self.outl.values() if out):
            # Case 3: Both inlet and all outlets at or below ambient
            self.C_P = self.C_bus + (total_e_T_out - inlet.get('e_T', 0.0) * inlet.get('m', 0.0))
            self.C_F = inlet.get('e_M', 0.0) * inlet.get('m', 0.0) - total_e_M_out
        else:
            # Invalid or unsupported case
            logging.warning(
                'Exergy balance of a turbine where outlet temperature is larger '
                'than inlet temperature is not implemented.'
            )
            self.C_P = np.nan
            self.C_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.C_F - self.C_P
        self.c_F = self.C_F / self.E_F if self.E_F and self.E_F > 1e-12 else 0.0
        self.c_P = self.C_P / self.E_P if self.E_P and self.E_P > 1e-12 and not np.isnan(self.E_P) else 0.0
        self.r = ((self.c_P - self.c_F) / self.c_F) if self.c_F else 0.0
        Z = self.Z_costs
        denom = Z + self.C_D if self.C_D else Z
        self.f = (Z / denom) if denom != 0.0 else 0.0

        # Log the results
        logging.info(
            f"Turbine '{self.label}' exergoeconomic calculations: "
            f"C_P={self.C_P:.2f}, C_F={self.C_F:.2f}, C_D={self.C_D:.2f}, "
            f"c_F={self.c_F:.4f}, c_P={self.c_P:.4f}, r={self.r:.4f}, f={self.f:.4f}"
        )


    def aux_eqs(self, exergy_cost_matrix, exergy_cost_vector, counter: int, T0: float):
        r"""
        Insert auxiliary cost equations ensuring cost flow consistency.

        For Turbine, ensures that:
        - Sum of exergy costs for each type across outlets equals inlet
        - C_P + C_F = Z_costs

        Parameters
        ----------
        exergy_cost_matrix : ndarray
            The main exergoeconomic matrix being assembled.
        exergy_cost_vector : ndarray
            The main RHS vector of the exergoeconomic system.
        counter : int
            Current row index for equations.
        T0 : float
            Ambient temperature in Kelvin.

        Returns
        -------
        list
            [exergy_cost_matrix, exergy_cost_vector, new_counter]
            with updated matrix, vector, and row index.
        """
        # Extract inlet and outlets
        inlet = self.inl[0]

        # Check temperature conditions to determine which equations to insert
        inlet_above = inlet['T'] > T0
        outlets_above = all(out['T'] > T0 for out in self.outl.values() if out)

        if inlet_above and outlets_above:
            # Case where inlet and all outlets are above ambient
            # Insert equations for 'therm', 'mech', 'chemical'

            # Therm exergy cost consistency: C_P = C_F + Z_costs
            therm_in_col = inlet["Ex_C_col"].get("therm")
            therm_out_cols = [out["Ex_C_col"].get("therm") for out in self.outl.values() if out and "therm" in out["Ex_C_col"]]

            if therm_in_col is not None and all(col is not None for col in therm_out_cols):
                # Equation: Sum(c_therm_out) - c_therm_in = 0
                exergy_cost_matrix[counter, therm_in_col] = -1.0  # -c_therm_in
                for col in therm_out_cols:
                    exergy_cost_matrix[counter, col] = 1.0   # +c_therm_out
                exergy_cost_vector[counter] = 0.0
                counter += 1
            else:
                logging.error("Therm exergy type missing in Ex_C_col for Turbine.")
                raise KeyError("Therm exergy type missing in Ex_C_col for Turbine.")

            # Mech exergy cost consistency: C_P = C_F + Z_costs
            mech_in_col = inlet["Ex_C_col"].get("mech")
            mech_out_cols = [out["Ex_C_col"].get("mech") for out in self.outl.values() if out and "mech" in out["Ex_C_col"]]

            if mech_in_col is not None and all(col is not None for col in mech_out_cols):
                # Equation: Sum(c_mech_out) - c_mech_in = 0
                exergy_cost_matrix[counter, mech_in_col] = -1.0  # -c_mech_in
                for col in mech_out_cols:
                    exergy_cost_matrix[counter, col] = 1.0   # +c_mech_out
                exergy_cost_vector[counter] = 0.0
                counter += 1
            else:
                logging.error("Mech exergy type missing in Ex_C_col for Turbine.")
                raise KeyError("Mech exergy type missing in Ex_C_col for Turbine.")

            # Chemical exergy cost consistency: C_P = C_F + Z_costs
            chemical_in_col = inlet["Ex_C_col"].get("chemical")
            chemical_out_cols = [out["Ex_C_col"].get("chemical") for out in self.outl.values() if out and "chemical" in out["Ex_C_col"]]

            if chemical_in_col is not None and all(col is not None for col in chemical_out_cols):
                # Equation: Sum(c_chemical_out) - c_chemical_in = 0
                exergy_cost_matrix[counter, chemical_in_col] = -1.0  # -c_chemical_in
                for col in chemical_out_cols:
                    exergy_cost_matrix[counter, col] = 1.0   # +c_chemical_out
                exergy_cost_vector[counter] = 0.0
                counter += 1
            else:
                logging.error("Chemical exergy type missing in Ex_C_col for Turbine.")
                raise KeyError("Chemical exergy type missing in Ex_C_col for Turbine.")

            # Insert Exergy Flow Equation: C_P + C_F - Z_costs = 0
            C_P_col = self.Ex_C_col.get("C_P")
            C_F_col = self.Ex_C_col.get("C_F")

            if C_P_col is not None and C_F_col is not None:
                # Equation: C_P + C_F - Z_costs = 0 => C_P + C_F = Z_costs
                exergy_cost_matrix[counter, C_P_col] = 1.0
                exergy_cost_matrix[counter, C_F_col] = 1.0
                exergy_cost_vector[counter] = self.Z_costs
                counter += 1
            else:
                logging.error("C_P and/or C_F exergy cost columns missing in Ex_C_col for Turbine.")
                raise KeyError("C_P and/or C_F exergy cost columns missing in Ex_C_col for Turbine.")
        else:
            # Unsupported temperature case
            logging.warning("Turbine with outlet temperatures not all above ambient T0 is not implemented in exergoeconomics yet.")
            # Depending on your implementation, you might want to raise an exception or handle differently

        # Return the updated matrix, vector, and counter
        return [exergy_cost_matrix, exergy_cost_vector, counter]
