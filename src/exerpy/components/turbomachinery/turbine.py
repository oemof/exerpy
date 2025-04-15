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
        self.P = None

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
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
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.
        """
        # Get power flow if not already available
        if self.P is None:
            self.P = self._total_outlet('m', 'h') - self.inl[0]['m'] * self.inl[0]['h']

        # Case 1: Both temperatures above ambient
        if self.inl[0]['T'] >= T0 and self.outl[0]['T'] >= T0 and self.inl[0]['T'] >= self.outl[0]['T']:
            self.E_P = abs(self.P)
            self.E_F = (self.inl[0]['m'] * self.inl[0]['e_PH'] -
                        self._total_outlet('m', 'e_PH'))

        # Case 2: Inlet above, outlet at/below ambient
        elif self.inl[0]['T'] > T0 and self.outl[0]['T'] <= T0:
            if split_physical_exergy:
                self.E_P = abs(self.P) + self._total_outlet('m', 'e_T')
                self.E_F = (self.inl[0]['m'] * self.inl[0]['e_T'] +
                            self.inl[0]['m'] * self.inl[0]['e_M'] -
                            self._total_outlet('m', 'e_M'))
            else:
                logging.warning("While dealing with expander below ambient, "
                                "physical exergy should be split into thermal and mechanical components!")
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 3: Both temperatures at/below ambient
        elif self.inl[0]['T'] <= T0 and self.outl[0]['T'] <= T0:
            if split_physical_exergy:
                self.E_P = abs(self.P) + (
                    self._total_outlet('m', 'e_T') - self.inl[0]['m'] * self.inl[0]['e_T'])
                self.E_F = (self.inl[0]['m'] * self.inl[0]['e_M'] -
                            self._total_outlet('m', 'e_M'))
            else:
                logging.warning("While dealing with expander below ambient, "
                                "physical exergy should be split into thermal and mechanical components!")
                self.E_P = np.nan
                self.E_F = np.nan
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
        if self.E_F == np.nan:
            self.E_D = self.inl[0]['m'] * self.inl[0]['e_PH'] - self._total_outlet('m', 'e_PH') - abs(self.P)
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
    

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the turbine.
        
        This function sets up auxiliary equations for each material outlet of the turbine, provided
        that the inlet (self.inl[0]) and the first outlet (self.outl[0]) have temperatures above T0.
        For each material outlet with kind "material", the function adds:
        - A thermal exergy equation,
        - A mechanical exergy equation,
        - And, if chemical_exergy_enabled is True, a chemical exergy equation.
        Thus, each material outlet adds 3 rows if chemical exergy is enabled, or 2 rows otherwise.
        
        After processing the material outlets, the function adds auxiliary equations for shaft power 
        equality for power outlets (those with kind "power" that have both a source and a target).
        
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
                A[counter + row_offset, outlet["CostVar_index"]["T"]] = (
                    -1 / outlet["E_T"] if outlet["e_T"] != 0 else -1
                )
                equations[counter + row_offset] = f"aux_f_rule_{outlet['name']}"

                # --- Mechanical exergy equation ---
                A[counter + row_offset + 1, self.inl[0]["CostVar_index"]["M"]] = (
                    1 / self.inl[0]["E_M"] if self.inl[0]["e_M"] != 0 else 1
                )
                A[counter + row_offset + 1, outlet["CostVar_index"]["M"]] = (
                    -1 / outlet["E_M"] if outlet["e_M"] != 0 else -1
                )
                equations[counter + row_offset + 1] = f"aux_f_rule_{outlet['name']}"

                # --- Chemical exergy equation (conditionally added) ---
                if chemical_exergy_enabled:
                    A[counter + row_offset + 2, self.inl[0]["CostVar_index"]["CH"]] = (
                        1 / self.inl[0]["E_CH"] if self.inl[0]["e_CH"] != 0 else 1
                    )
                    A[counter + row_offset + 2, outlet["CostVar_index"]["CH"]] = (
                        -1 / outlet["E_CH"] if outlet["e_CH"] != 0 else -1
                    )
                    equations[counter + row_offset + 2] = f"aux_f_rule_{outlet['name']}"
            
            # Update counter based on number of rows added for all material outlets.
            num_material_rows = num_rows_per_outlet * len(material_outlets)
            for j in range(num_material_rows):
                b[counter + j] = 0
            counter += num_material_rows
        else:
            logging.warning("Turbine with outlet below T0 not implemented in exergoeconomics yet!")
        
        # --- Auxiliary equation for shaft power equality ---
        power_outlets = [outlet for outlet in self.outl.values()
                        if outlet.get("kind") == "power" and outlet.get("source_component") and outlet.get("target_component")]
        if len(power_outlets) > 1:
            ref = power_outlets[0]
            ref_idx = ref["CostVar_index"]["exergy"]
            for outlet in power_outlets[1:]:
                cur_idx = outlet["CostVar_index"]["exergy"]
                A[counter, ref_idx] = 1 / ref["E"] if ref["E"] != 0 else 1
                A[counter, cur_idx] = -1 / outlet["E"] if outlet["E"] != 0 else -1
                b[counter] = 0
                equations[counter] = f"aux_p_rule_power_{self.name}_{outlet['name']}"
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0):
        """
        Calculate the exergoeconomic balance for the turbine.

        The turbine may have multiple power outputs and multiple material outputs. In this
        function the cost of power is computed as the sum of C_TOT from all inlet streams of kind "power".
        Material outlet costs are summed over all outlets of kind "material". The cost balance is then
        computed according to the following cases:

        Case 1 (both inlet and first outlet above T0):
            C_P = (total power cost)
            C_F = C_PH_inlet - (sum of C_PH from material outlets)

        Case 2 (inlet above T0, outlet at or below T0):
            C_P = (total power cost) + (sum of C_T from material outlets)
            C_F = C_T_inlet + (C_M_inlet - (sum of C_M from material outlets))

        Case 3 (both inlet and outlet at or below T0):
            C_P = (total power cost) + ((sum of C_T from material outlets) - C_T_inlet)
            C_F = C_M_inlet - (sum of C_M from material outlets)

        Finally, the specific fuel cost (c_F), specific product cost (c_P), total cost destruction (C_D),
        relative difference (r), and exergoeconomic factor (f) are calculated.

        Parameters
        ----------
        T0 : float
            Ambient temperature.

        Raises
        ------
        ValueError
            If required cost values are missing.
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
            logging.warning("Exergoeconomic balance of a turbine with outlet temperature larger than inlet is not implemented.")
            self.C_P = np.nan
            self.C_F = np.nan

        # Calculate the specific cost terms and exergoeconomic parameters.
        self.c_F = self.C_F / self.E_F
        self.c_P = self.C_P / self.E_P
        self.C_D = self.c_F * self.E_D
        self.r = (self.C_P - self.C_F) / self.C_F
        self.f = self.Z_costs / (self.Z_costs + self.C_D)
