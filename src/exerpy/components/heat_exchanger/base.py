import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class HeatExchanger(Component):
    r"""
    Class for exergy analysis of heat exchangers.

    This class performs exergy analysis calculations for heat exchangers, considering
    different temperature regimes relative to the ambient temperature. The exergy
    product and fuel definitions vary based on the temperature levels of the streams.
    Stream 0 represents the hot stream and stream 1 represents the cold stream.

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
    inl : dict
        Dictionary containing inlet streams data (0: hot stream, 1: cold stream) with 
        temperature, mass flows, and specific exergies.
    outl : dict
        Dictionary containing outlet streams data (0: hot stream, 1: cold stream) with 
        temperature, mass flows, and specific exergies.

    Notes
    -----
    The exergy analysis considers six different cases based on stream temperatures
    relative to ambient temperature :math:`T_0`. Stream indices refer to hot (0) and
    cold (1) streams:

    Case 1 - **All streams above ambient temperature**:
    
    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{T}_{\mathrm{out,1}} 
        - \dot{m}_{\mathrm{in,1}} \cdot e^\mathrm{T}_{\mathrm{in,1}}\\
        \dot{E}_\mathrm{F} &= \dot{m}_{\mathrm{in,0}} \cdot e^\mathrm{PH}_{\mathrm{in,0}} 
        - \dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{PH}_{\mathrm{out,0}} + 
        \dot{m}_{\mathrm{in,1}} \cdot e^\mathrm{M}_{\mathrm{in,1}} 
        - \dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{M}_{\mathrm{out,1}}

    Case 2 - **All streams below or at ambient temperature**:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{T}_{\mathrm{out,0}} 
        - \dot{m}_{\mathrm{in,0}} \cdot e^\mathrm{T}_{\mathrm{in,0}}\\
        \dot{E}_\mathrm{F} &= \dot{m}_{\mathrm{in,1}} \cdot e^\mathrm{PH}_{\mathrm{in,1}} 
        - \dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{PH}_{\mathrm{out,1}} + 
        \dot{m}_{\mathrm{in,0}} \cdot e^\mathrm{M}_{\mathrm{in,0}} 
        - \dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{M}_{\mathrm{out,0}}

    Case 3 - **Hot stream inlet/outlet above ambient, cold stream inlet/outlet below ambient**:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{T}_{\mathrm{out,0}} 
        + \dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{T}_{\mathrm{out,1}}\\
        \dot{E}_\mathrm{F} &= \dot{m}_{\mathrm{in,0}} \cdot e^\mathrm{PH}_{\mathrm{in,0}} 
        + \dot{m}_{\mathrm{in,1}} \cdot e^\mathrm{PH}_{\mathrm{in,1}} 
        - (\dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{M}_{\mathrm{out,0}} 
        + \dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{M}_{\mathrm{out,1}})

    Case 4 - **First inlet above ambient, all other streams below or at ambient**:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{T}_{\mathrm{out,0}}\\
        \dot{E}_\mathrm{F} &= \dot{m}_{\mathrm{in,0}} \cdot e^\mathrm{PH}_{\mathrm{in,0}} 
        + \dot{m}_{\mathrm{in,1}} \cdot e^\mathrm{PH}_{\mathrm{in,1}} 
        - (\dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{PH}_{\mathrm{out,1}} 
        + \dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{M}_{\mathrm{out,0}})

    Case 5 - **Hot stream inlet/outlet above ambient, cold stream inlet/outlet below or at ambient**:

    .. math::
        \dot{E}_\mathrm{P} &= \text{NaN}\\
        \dot{E}_\mathrm{F} &= \dot{m}_{\mathrm{in,0}} \cdot e^\mathrm{PH}_{\mathrm{in,0}} 
        - \dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{PH}_{\mathrm{out,0}} 
        + \dot{m}_{\mathrm{in,1}} \cdot e^\mathrm{PH}_{\mathrm{in,1}} 
        - \dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{PH}_{\mathrm{out,1}}

    Case 6 - **Second outlet above ambient, all others below or at ambient**:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{T}_{\mathrm{out,1}}\\
        \dot{E}_\mathrm{F} &= \dot{m}_{\mathrm{in,0}} \cdot e^\mathrm{PH}_{\mathrm{in,0}} 
        - \dot{m}_{\mathrm{out,0}} \cdot e^\mathrm{PH}_{\mathrm{out,0}} 
        + \dot{m}_{\mathrm{in,1}} \cdot e^\mathrm{PH}_{\mathrm{in,1}} 
        - \dot{m}_{\mathrm{out,1}} \cdot e^\mathrm{M}_{\mathrm{out,1}}

    Note that in Case 5, the exergy product :math:`\dot{E}_\mathrm{P}` is undefined (NaN),
    leading to an exergy destruction equal to the exergy fuel:
    :math:`\dot{E}_\mathrm{D} = \dot{E}_\mathrm{F}`.

    The exergy destruction is calculated as:

    .. math::
        \dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}

    And the exergetic efficiency as:

    .. math::
        \varepsilon = \frac{\dot{E}_\mathrm{P}}{\dot{E}_\mathrm{F}}

    Where:
        - :math:`e^\mathrm{T}`: Thermal exergy
        - :math:`e^\mathrm{PH}`: Physical exergy
        - :math:`e^\mathrm{M}`: Mechanical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize heat exchanger component with given parameters."""
        super().__init__(**kwargs)
    
    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the heat exchanger.

        Performs exergy balance calculations considering different temperature regimes
        relative to the ambient temperature. The method automatically determines the
        appropriate case based on stream temperatures.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined.

        Notes
        -----
        This method updates the following component attributes:
            - E_P (Exergy product)
            - E_F (Exergy fuel)
            - E_D (Exergy destruction)
            - epsilon (Exergetic efficiency)

        The calculation requires two inlet and two outlet streams, and their
        temperature relationships with ambient temperature determine which case
        of exergy analysis is applied.
        """
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 2:
            raise ValueError("Heat exchanger requires two inlets and two outlets.")

        # Access the streams via .values() to iterate over the actual stream data
        all_streams = list(self.inl.values()) + list(self.outl.values())

        # Case 1: All streams are above the ambient temperature
        if all([stream['T'] >= T0 for stream in all_streams]):
            self.E_P = self.outl[1]['m'] * self.outl[1]['e_T'] - self.inl[1]['m'] * self.inl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_M'] - self.outl[1]['m'] * self.outl[1]['e_M'])

        # Case 2: All streams are below or equal to the ambient temperature
        elif all([stream['T'] <= T0 for stream in all_streams]):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] - self.inl[0]['m'] * self.inl[0]['e_T']
            self.E_F = self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'] + (
                self.inl[0]['m'] * self.inl[0]['e_M'] - self.outl[0]['m'] * self.outl[0]['e_M'])

        # Case 3: Some streams are above and others below ambient temperature
        elif (self.inl[0]['T'] > T0 and self.outl[1]['T'] > T0 and
              self.outl[0]['T'] <= T0 and self.inl[1]['T'] <= T0):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T'] + self.outl[1]['m'] * self.outl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'] - (
                self.outl[0]['m'] * self.outl[0]['e_M'] + self.outl[1]['m'] * self.outl[1]['e_M'])

        # Case 4: First inlet is above ambient, others below or equal
        elif (self.inl[0]['T'] > T0 and self.inl[1]['T'] <= T0 and
              self.outl[0]['T'] <= T0 and self.outl[1]['T'] <= T0):
            self.E_P = self.outl[0]['m'] * self.outl[0]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] + self.inl[1]['m'] * self.inl[1]['e_PH'] - (
                self.outl[1]['m'] * self.outl[1]['e_PH'] + self.outl[0]['m'] * self.outl[0]['e_M'])

        # Case 5: Inlets are higher but outlets are below or equal to ambient
        elif (self.inl[0]['T'] > T0 and self.outl[0]['T'] > T0 and
              self.inl[1]['T'] <= T0 and self.outl[1]['T'] <= T0):
            self.E_P = np.nan
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_PH'])

        # Case 6: One outlet is above ambient, others lower
        else:
            self.E_P = self.outl[1]['m'] * self.outl[1]['e_T']
            self.E_F = self.inl[0]['m'] * self.inl[0]['e_PH'] - self.outl[0]['m'] * self.outl[0]['e_PH'] + (
                self.inl[1]['m'] * self.inl[1]['e_PH'] - self.outl[1]['m'] * self.outl[1]['e_M'])

        # Calculate exergy destruction and efficiency
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Compressor exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def exergoeconomic_balance(self, T0):
        r"""
        Assign cost of exergy fuel and product depending on stream temperatures.

        This method implements logic for a two-inlet / two-outlet heat exchanger:
        depending on the stream temperatures relative to T0, it sets the
        exergoeconomic cost flows :math:`C_F` and :math:`C_P`. Then, it computes
        the cost of exergy destruction, relative cost difference, and
        exergoeconomic factor.

        Parameters
        ----------
        T0 : float
            Ambient temperature in Kelvin.

        Notes
        -----
        - ``self.inl[0]``, ``self.inl[1]`` : Inlet dictionaries
          for the hot and cold stream, each containing cost fields
          like ``"C_PH"``, ``"C_T"``, ``"C_M"``, etc., as well as the temperature
          under key ``"T"``.
        - ``self.outl[0]``, ``self.outl[1]`` : Outlet dictionaries with similar
          data fields.

        The logic is:
          1) Check if ``dissipative`` is True; if so, set
             ``C_P = nan`` and ``C_F = sum inbound``.
          2) Otherwise, use temperature-based branching to set
             ``self.C_P`` and ``self.C_F`` from the
             cost fields in the inbound/outbound streams
             (like ``["C_PH"]``, ``["C_T"]``, ``["C_M"]``, etc.).
          3) Compute ``self.c_F = C_F / E_F``, ``self.c_P = C_P / E_P``,
             ``self.C_D = C_F - C_P``, ``self.r = (c_P - c_F) / c_F``,
             and ``self.f = Z_costs / (Z_costs + C_D)``.
        """
        # 1) Check if the HeatExchanger is 'dissipative'
        if getattr(self, "dissipative", False):
            self.C_P = np.nan
            # Summation of inbound total cost flows
            c_in0 = self.inl[0].get("C_tot", 0.0)
            c_in1 = self.inl[1].get("C_tot", 0.0)
            self.C_F = c_in0 + c_in1

        else:
            # Convenience references
            i0, i1 = self.inl[0], self.inl[1]
            o0, o1 = self.outl[0], self.outl[1]

            # Collect all temperatures
            all_temps = [i0["T"], i1["T"], o0["T"], o1["T"]]

            if all(t > T0 for t in all_temps):
                # Case 1: All streams above T0
                self.C_P = o1["C_T"] - i1["C_T"]
                self.C_F = i0["C_PH"] - o0["C_PH"] + (i1["C_M"] - o1["C_M"])

            elif all(t <= T0 for t in all_temps):
                # Case 2: All streams below or equal to T0
                self.C_P = o0["C_T"] - i0["C_T"]
                self.C_F = i1["C_PH"] - o1["C_PH"] + (i0["C_M"] - o0["C_M"])

            elif (i0["T"] > T0 and o1["T"] > T0 and
                  o0["T"] <= T0 and i1["T"] <= T0):
                # Case 3: Hot inlet/outlet above T0, cold inlet/outlet below T0
                self.C_P = o0["C_T"] + o1["C_T"]
                self.C_F = i0["C_PH"] + i1["C_PH"] - (o0["C_M"] + o1["C_M"])

            elif (i0["T"] > T0 and i1["T"] <= T0 and
                  o0["T"] <= T0 and o1["T"] <= T0):
                # Case 4: First inlet above T0, all other streams below or equal
                self.C_P = o0["C_T"]
                self.C_F = i0["C_PH"] + i1["C_PH"] - (o1["C_PH"] + o0["C_M"])

            elif (i0["T"] > T0 and o0["T"] > T0 and
                  i1["T"] <= T0 and o1["T"] <= T0):
                # Case 5: Hot stream inlet/outlet above T0, cold stream inlet/outlet below or equal
                self.C_P = np.nan
                self.C_F = (i0["C_PH"] - o0["C_PH"]) + (i1["C_PH"] - o1["C_PH"])

            else:
                # Case 6: Second outlet above T0, all others below or equal
                self.C_P = o1["C_T"]
                self.C_F = (i0["C_PH"] - o0["C_PH"]) + (i1["C_PH"] - o1["C_M"])

        # 3) Compute c_F, c_P, C_D, r, f
        if self.E_F != 0.0:
            self.c_F = self.C_F / self.E_F
        else:
            self.c_F = np.nan

        if (self.E_P is not None) and (self.E_P != 0.0) and not np.isnan(self.E_P):
            self.c_P = self.C_P / self.E_P
        else:
            self.c_P = np.nan

        # Cost of exergy destruction
        if not np.isnan(self.C_P) and not np.isnan(self.C_F):
            self.C_D = self.C_F - self.C_P
        elif np.isnan(self.C_P) and not np.isnan(self.C_F):
            self.C_D = self.C_F  # Since C_P is undefined
        else:
            self.C_D = np.nan

        # Relative cost difference
        if (not np.isnan(self.c_F)) and (self.c_F != 0.0) and (not np.isnan(self.c_P)):
            self.r = (self.c_P - self.c_F) / self.c_F
        else:
            self.r = np.nan

        # Exergoeconomic factor f = Z_costs / (Z_costs + C_D)
        Z = getattr(self, "Z_costs", 0.0)
        if not np.isnan(self.C_D):
            denom = Z + self.C_D
        else:
            denom = Z
        if denom != 0.0:
            self.f = Z / denom
        else:
            self.f = np.nan

        # Log the results
        logging.info(
            f"HeatExchanger exergoeconomic balance calculated: "
            f"C_P={self.C_P}, C_F={self.C_F}, C_D={self.C_D}, "
            f"c_F={self.c_F}, c_P={self.c_P}, r={self.r}, f={self.f}"
        )

    def aux_eqs(self, exergy_cost_matrix, exergy_cost_vector, counter, T0):
        r"""
        Insert the F/P-rule style auxiliary equations ensuring
        c^T_in = c^T_out, c^M_in = c^M_out, c^CH_in = c^CH_out, etc.,
        depending on the temperature scenario for the 2 inlets (0,1)
        and 2 outlets (0,1).

        This logic matches the 6-case structure used in the exergoeconomic_balance
        method. For each scenario, we insert 5 lines enforcing equality of the
        specific exergy cost for T, M, CH.

        Parameters
        ----------
        exergy_cost_matrix : ndarray
            The main exergoeconomic matrix being assembled.

        exergy_cost_vector : ndarray
            The main RHS vector of the exergoeconomic system.

        counter : int
            Current row index in the matrix to place equations.

        T0 : float
            Ambient temperature in Kelvin.

        Returns
        -------
        list
            [exergy_cost_matrix, exergy_cost_vector, new_counter]
            with updated matrix, vector, and row index.
        """
        # Convenience references
        i0, i1 = self.inl[0], self.inl[1]    # inlet dictionaries (hot=0, cold=1)
        o0, o1 = self.outl[0], self.outl[1]  # outlet dictionaries

        # Helper functions
        def all_above(*streams):
            return all(s["T"] > T0 for s in streams)

        def all_below_eq(*streams):
            return all(s["T"] <= T0 for s in streams)

        # All streams list
        all_streams = [i0, i1, o0, o1]

        # Initialize list to track if a scenario is matched
        scenario_matched = False

        # 1) All streams above T0
        if all_above(*all_streams):
            scenario_matched = True
            # row 0 => c^T_in0 = c^T_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+0, i0, o0, "T")
            # row 1 => c^M_in0 = c^M_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+1, i0, o0, "M")
            # row 2 => c^M_in1 = c^M_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+2, i1, o1, "M")
            # row 3 => c^CH_in0 = c^CH_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+3, i0, o0, "CH")
            # row 4 => c^CH_in1 = c^CH_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+4, i1, o1, "CH")

            # Set RHS=0 for these rows
            for k in range(5):
                exergy_cost_vector[counter + k] = 0.0

            counter += 5

        # 2) All streams below or equal to T0
        elif all_below_eq(*all_streams):
            scenario_matched = True
            # row 0 => c^T_in1 = c^T_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+0, i1, o1, "T")
            # row 1 => c^M_in1 = c^M_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+1, i1, o1, "M")
            # row 2 => c^M_in0 = c^M_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+2, i0, o0, "M")
            # row 3 => c^CH_in0 = c^CH_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+3, i0, o0, "CH")
            # row 4 => c^CH_in1 = c^CH_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+4, i1, o1, "CH")

            # Set RHS=0 for these rows
            for k in range(5):
                exergy_cost_vector[counter + k] = 0.0

            counter += 5

        # 3) Hot inlet/outlet above T0, cold inlet/outlet below T0
        elif (i0["T"] > T0 and o1["T"] > T0 and
              o0["T"] <= T0 and i1["T"] <= T0):
            scenario_matched = True
            # row 0 => c^T_in0 = c^T_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+0, i0, o0, "T")
            # row 1 => c^M_in0 = c^M_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+1, i0, o0, "M")
            # row 2 => c^M_in1 = c^M_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+2, i1, o1, "M")
            # row 3 => c^CH_in0 = c^CH_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+3, i0, o0, "CH")
            # row 4 => c^CH_in1 = c^CH_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+4, i1, o1, "CH")

            # Set RHS=0 for these rows
            for k in range(5):
                exergy_cost_vector[counter + k] = 0.0

            counter += 5

        # 4) First inlet above T0, all other streams below or equal to T0
        elif (i0["T"] > T0 and i1["T"] <= T0 and
              o0["T"] <= T0 and o1["T"] <= T0):
            scenario_matched = True
            # row 0 => c^T_in0 = c^T_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+0, i0, o0, "T")
            # row 1 => c^M_in0 = c^M_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+1, i0, o0, "M")
            # row 2 => c^M_in1 = c^M_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+2, i1, o1, "M")
            # row 3 => c^CH_in0 = c^CH_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+3, i0, o0, "CH")
            # row 4 => c^CH_in1 = c^CH_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+4, i1, o1, "CH")

            # Set RHS=0 for these rows
            for k in range(5):
                exergy_cost_vector[counter + k] = 0.0

            counter += 5

        # 5) Hot inlet/outlet above T0, cold inlet/outlet below or equal to T0
        elif (i0["T"] > T0 and o0["T"] > T0 and
              i1["T"] <= T0 and o1["T"] <= T0):
            scenario_matched = True
            # row 0 => c^T_in0 = c^T_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+0, i0, o0, "T")
            # row 1 => c^M_in0 = c^M_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+1, i0, o0, "M")
            # row 2 => c^M_in1 = c^M_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+2, i1, o1, "M")
            # row 3 => c^CH_in0 = c^CH_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+3, i0, o0, "CH")
            # row 4 => c^CH_in1 = c^CH_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+4, i1, o1, "CH")

            # Set RHS=0 for these rows
            for k in range(5):
                exergy_cost_vector[counter + k] = 0.0

            counter += 5

        # 6) Second outlet above T0, all others below or equal to T0
        else:
            scenario_matched = True
            # row 0 => c^T_in0 = c^T_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+0, i0, o0, "T")
            # row 1 => c^M_in0 = c^M_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+1, i0, o0, "M")
            # row 2 => c^M_in1 = c^M_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+2, i1, o1, "M")
            # row 3 => c^CH_in0 = c^CH_out0
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+3, i0, o0, "CH")
            # row 4 => c^CH_in1 = c^CH_out1
            self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter+4, i1, o1, "CH")

            # Set RHS=0 for these rows
            for k in range(5):
                exergy_cost_vector[counter + k] = 0.0

            counter += 5

        # If no scenario matched (should not happen), set dummy equations
        if not scenario_matched:
            for k in range(5):
                exergy_cost_vector[counter + k] = 0.0
            counter += 5

        return [exergy_cost_matrix, exergy_cost_vector, counter]

    def dis_eqs(self, exergy_cost_matrix, exergy_cost_vector, counter, T0):
        r"""
        Insert dissipative cost distribution equations.

        If the heat exchanger is dissipative, distribute the cost of exergy destruction
        among the serving components.

        Parameters
        ----------
        exergy_cost_matrix : ndarray
            The main exergoeconomic matrix being assembled.

        exergy_cost_vector : ndarray
            The main RHS vector of the exergoeconomic system.

        counter : int
            Current row index in the matrix to place equations.

        T0 : float
            Ambient temperature in Kelvin.

        Returns
        -------
        list
            [exergy_cost_matrix, exergy_cost_vector, new_counter]
            with updated matrix, vector, and row index.
        """
        # Check if the component is dissipative
        if not getattr(self, "dissipative", False):
            return [exergy_cost_matrix, exergy_cost_vector, counter]

        # Check if serving_components is defined
        if not hasattr(self, "serving_components") or self.serving_components is None:
            logging.warning("Dissipative HeatExchanger has no serving_components defined.")
            return [exergy_cost_matrix, exergy_cost_vector, counter]

        num_serving = len(self.serving_components)
        if num_serving == 0:
            logging.warning("Dissipative HeatExchanger has an empty serving_components list.")
            return [exergy_cost_matrix, exergy_cost_vector, counter]

        # Distribute the cost equally among serving components
        fraction = 1.0 / num_serving

        for comp in self.serving_components:
            # Distribute thermal exergy cost
            exergy_cost_matrix[counter, comp.inl[0]["Ex_C_col"]["T"]] += fraction
            exergy_cost_matrix[counter, comp.outl[0]["Ex_C_col"]["T"]] += -fraction
            exergy_cost_matrix[counter, comp.inl[1]["Ex_C_col"]["T"]] += fraction
            exergy_cost_matrix[counter, comp.outl[1]["Ex_C_col"]["T"]] += -fraction

            # Distribute mechanical exergy cost
            exergy_cost_matrix[counter+1, comp.inl[0]["Ex_C_col"]["M"]] += fraction
            exergy_cost_matrix[counter+1, comp.outl[0]["Ex_C_col"]["M"]] += -fraction
            exergy_cost_matrix[counter+1, comp.inl[1]["Ex_C_col"]["M"]] += fraction
            exergy_cost_matrix[counter+1, comp.outl[1]["Ex_C_col"]["M"]] += -fraction

            # Distribute chemical exergy cost
            exergy_cost_matrix[counter+2, comp.inl[0]["Ex_C_col"]["CH"]] += fraction
            exergy_cost_matrix[counter+2, comp.outl[0]["Ex_C_col"]["CH"]] += -fraction
            exergy_cost_matrix[counter+2, comp.inl[1]["Ex_C_col"]["CH"]] += fraction
            exergy_cost_matrix[counter+2, comp.outl[1]["Ex_C_col"]["CH"]] += -fraction

            # Increment counter for each serving component's distribution
            counter += 3  # Assuming 3 rows per serving component

        # Set the cost rate equation for dissipative component
        exergy_cost_matrix[counter, self.Ex_C_col["dissipative"]] = 1.0
        exergy_cost_vector[counter] = self.Z_costs
        counter += 1

        return [exergy_cost_matrix, exergy_cost_vector, counter]

    def _insert_cost_eq(self, matrix, vector, row, in_conn, out_conn, exergy_type):
        """
        Helper method to insert cost equality equations into the matrix.

        Parameters
        ----------
        matrix : ndarray
            The main exergoeconomic matrix being assembled.

        vector : ndarray
            The main RHS vector of the exergoeconomic system.

        row : int
            Row index to insert the equation.

        in_conn : dict
            Inlet connection dictionary.

        out_conn : dict
            Outlet connection dictionary.

        exergy_type : str
            Type of exergy ('T', 'M', 'CH').

        Returns
        -------
        None
        """
        in_e = in_conn.get(f"e_{exergy_type}", 0.0)
        out_e = out_conn.get(f"e_{exergy_type}", 0.0)

        if in_e != 0.0 and out_e != 0.0:
            matrix[row, in_conn["Ex_C_col"][exergy_type]] = 1.0 / in_e
            matrix[row, out_conn["Ex_C_col"][exergy_type]] = -1.0 / out_e
        elif in_e == 0.0 and out_e != 0.0:
            matrix[row, in_conn["Ex_C_col"][exergy_type]] = 1.0
        elif in_e != 0.0 and out_e == 0.0:
            matrix[row, out_conn["Ex_C_col"][exergy_type]] = 1.0
        else:
            # Both exergies are zero; enforce c_in - c_out = 0
            matrix[row, in_conn["Ex_C_col"][exergy_type]] = 1.0
            matrix[row, out_conn["Ex_C_col"][exergy_type]] = -1.0



    