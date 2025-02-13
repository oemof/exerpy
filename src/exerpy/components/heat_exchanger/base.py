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
        self.dissipative = False
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

        if not self.dissipative:
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


    def aux_eqs(self, A, b, counter, T0, equations):
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
                A[row, self.inl[0]["CostVar_index"]["T"]] = 1 / self.inl[0]["e_T"]
                A[row, self.outl[0]["CostVar_index"]["T"]] = -1 / self.outl[0]["e_T"]
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
                A[row, self.inl[1]["CostVar_index"]["T"]] = 1 / self.inl[1]["e_T"]
                A[row, self.outl[1]["CostVar_index"]["T"]] = -1 / self.outl[1]["e_T"]
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
                A[row, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["e_T"]
                A[row, self.outl[1]["CostVar_index"]["T"]] = -1 / self.outl[1]["e_T"]
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
        elif all([c["T"] <= T0 for c in self.inl + self.outl]):
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
        
        # Mechanical and chemical equations are always set.
        set_equal(A, counter + 1, self.inl[0], self.outl[0], "M")
        set_equal(A, counter + 2, self.inl[1], self.outl[1], "M")
        set_equal(A, counter + 3, self.inl[0], self.outl[0], "CH")
        set_equal(A, counter + 4, self.inl[1], self.outl[1], "CH")
        equations[counter +1] = f"aux_equality_mech_{self.outl[0]["name"]}"
        equations[counter +2] = f"aux_equality_mech_{self.outl[1]["name"]}"
        equations[counter +3] = f"aux_equality_chem_{self.outl[0]["name"]}"
        equations[counter +4] = f"aux_equality_chem_{self.outl[1]["name"]}"

        for i in range(5):
            b[counter + i] = 0
        return [A, b, counter + 5, equations]
