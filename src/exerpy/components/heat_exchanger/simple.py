import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class SimpleHeatExchanger(Component):
    r"""
    Class for exergy analysis of simple heat exchangers.

    This class performs exergy analysis calculations for simple heat exchangers with
    one primary flow stream and heat transfer. The exergy product and fuel definitions
    vary based on the direction of heat transfer and temperature levels relative to
    ambient temperature.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.
        Optional parameter 'dissipative' (bool) to indicate if the component
        is considered fully dissipative.

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
        Dictionary containing inlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.

    Notes
    -----
    The exergy analysis considers three main cases based on heat transfer direction
    and temperatures relative to ambient temperature :math:`T_0`:

    Case 1 - **Heat Release** (:math:`\dot{Q} < 0`):

    a) Both temperatures above ambient:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m} \cdot (e^\mathrm{T}_\mathrm{in} - 
        e^\mathrm{T}_\mathrm{out})\\
        \dot{E}_\mathrm{F} &= \dot{m} \cdot (e^\mathrm{PH}_\mathrm{in} - 
        e^\mathrm{PH}_\mathrm{out})

    b) Inlet above, outlet below ambient:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_\mathrm{out} \cdot e^\mathrm{T}_\mathrm{out}\\
        \dot{E}_\mathrm{F} &= \dot{m}_\mathrm{in} \cdot e^\mathrm{T}_\mathrm{in} + 
        \dot{m}_\mathrm{out} \cdot e^\mathrm{T}_\mathrm{out} + 
        (\dot{m}_\mathrm{in} \cdot e^\mathrm{M}_\mathrm{in} - 
        \dot{m}_\mathrm{out} \cdot e^\mathrm{M}_\mathrm{out})

    c) Both temperatures below ambient:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_\mathrm{out} \cdot 
        (e^\mathrm{T}_\mathrm{out} - e^\mathrm{T}_\mathrm{in})\\
        \dot{E}_\mathrm{F} &= \dot{E}_\mathrm{P} + \dot{m}_\mathrm{in} \cdot 
        (e^\mathrm{M}_\mathrm{in} - e^\mathrm{M}_\mathrm{out})

    Case 2 - **Heat Addition** (:math:`\dot{Q} > 0`):

    a) Both temperatures above ambient:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_\mathrm{out} \cdot 
        (e^\mathrm{PH}_\mathrm{out} - e^\mathrm{PH}_\mathrm{in})\\
        \dot{E}_\mathrm{F} &= \dot{m}_\mathrm{out} \cdot 
        (e^\mathrm{T}_\mathrm{out} - e^\mathrm{T}_\mathrm{in})

    b) Inlet below, outlet above ambient:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_\mathrm{out} \cdot 
        (e^\mathrm{T}_\mathrm{out} + e^\mathrm{T}_\mathrm{in})\\
        \dot{E}_\mathrm{F} &= \dot{m}_\mathrm{in} \cdot e^\mathrm{T}_\mathrm{in} + 
        (\dot{m}_\mathrm{in} \cdot e^\mathrm{M}_\mathrm{in} - 
        \dot{m}_\mathrm{out} \cdot e^\mathrm{M}_\mathrm{out})

    c) Both temperatures below ambient:

    .. math::
        \dot{E}_\mathrm{P} &= \dot{m}_\mathrm{in} \cdot 
        (e^\mathrm{T}_\mathrm{in} - e^\mathrm{T}_\mathrm{out}) + 
        (\dot{m}_\mathrm{out} \cdot e^\mathrm{M}_\mathrm{out} - 
        \dot{m}_\mathrm{in} \cdot e^\mathrm{M}_\mathrm{in})\\
        \dot{E}_\mathrm{F} &= \dot{m}_\mathrm{in} \cdot 
        (e^\mathrm{T}_\mathrm{in} - e^\mathrm{T}_\mathrm{out})

    Case 3 - **Dissipative** (it is not possible to specify the exergy product :math:`\dot{E}_\mathrm{P}` for this component):

    .. math::
        \dot{E}_\mathrm{P} &= \text{NaN}\\
        \dot{E}_\mathrm{F} &= \dot{m}_\mathrm{in} \cdot 
        (e^\mathrm{PH}_\mathrm{in} - e^\mathrm{PH}_\mathrm{out})

    For all cases, the exergy destruction is calculated as:

    .. math::
        \dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}

    Where:
        - :math:`e^\mathrm{T}`: Thermal exergy
        - :math:`e^\mathrm{PH}`: Physical exergy
        - :math:`e^\mathrm{M}`: Mechanical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize simple heat exchanger component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the simple heat exchanger.

        Performs exergy balance calculations considering both heat transfer direction
        and temperature levels relative to ambient temperature.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined or
            exceed the maximum allowed number.
        """      
        # Validate the number of inlets and outlets
        if not hasattr(self, 'inl') or not hasattr(self, 'outl'):
            msg = "SimpleHeatExchanger requires at least one inlet and one outlet as well as one heat flow."
            logging.error(msg)
            raise ValueError(msg)
        if len(self.inl) > 2 or len(self.outl) > 2:
            msg = "SimpleHeatExchanger requires a maximum of two inlets and two outlets."
            logging.error(msg)
            raise ValueError(msg)

        # Extract inlet and outlet streams
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Calculate heat transfer Q
        Q = outlet['m'] * outlet['h'] - inlet['m'] * inlet['h']

        # Initialize E_P and E_F
        self.E_P = 0.0
        self.E_F = 0.0

        # Case 1: Heat is released (Q < 0)
        if Q < 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                self.E_P = np.nan if getattr(self, 'dissipative', False) else inlet['m'] * (inlet['e_T'] - outlet['e_T'])
                self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
            elif inlet['T'] >= T0 and outlet['T'] < T0:
                self.E_P = outlet['m'] * outlet['e_T']
                self.E_F = (inlet['m'] * inlet['e_T'] +
                           outlet['m'] * outlet['e_T'] +
                           (inlet['m'] * inlet['e_M'] - outlet['m'] * outlet['e_M']))
            elif inlet['T'] <= T0 and outlet['T'] <= T0:
                self.E_P = outlet['m'] * (outlet['e_T'] - inlet['e_T'])
                self.E_F = self.E_P + inlet['m'] * (inlet['e_M'] - outlet['m'] * outlet['e_M'])
            else:
                # Unimplemented corner case
                logging.warning(
                    "SimpleHeatExchanger: unimplemented case (Q < 0, T_in < T0 < T_out?)."
                )
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 2: Heat is added (Q > 0)
        elif Q > 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                self.E_P = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                self.E_F = outlet['m'] * (outlet['e_T'] - inlet['e_T'])
            elif inlet['T'] < T0 and outlet['T'] > T0:
                self.E_P = outlet['m'] * (outlet['e_T'] + inlet['e_T'])
                self.E_F = (inlet['m'] * inlet['e_T'] +
                           (inlet['m'] * inlet['e_M'] - outlet['m'] * outlet['e_M']))
            elif inlet['T'] < T0 and outlet['T'] < T0:
                self.E_P = np.nan if getattr(self, 'dissipative', False) else \
                    inlet['m'] * (inlet['e_T'] - outlet['e_T']) + \
                    (outlet['m'] * outlet['e_M'] - inlet['m'] * inlet['e_M'])
                self.E_F = inlet['m'] * (inlet['e_T'] - outlet['e_T'])
            else:
                logging.warning(
                    "SimpleHeatExchanger: unimplemented case (Q > 0, T_in > T0 > T_out?)."
                )
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 3: Fully dissipative or Q == 0
        else:
            self.E_P = np.nan
            self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])

        # Calculate exergy destruction
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"SimpleHeatExchanger '{self.label}' exergoeconomic balance calculated: "
            f"E_P={self.E_P:.2f} W, E_F={self.E_F:.2f} W, E_D={self.E_D:.2f} W, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def exergoeconomic_balance(self, T0: float) -> None:
        """        
        This function calculates:
        - C_P, the cost flow associated with the product exergy
        - C_F, the cost flow associated with the fuel exergy
        - c_F, c_P as specific costs [currency / W of exergy]
        - C_D, cost flow of exergy destruction
        - r, relative cost difference
        - f, exergoeconomic factor

        Requires:
        - self.inl[0], self.outl[0] each has e_T, e_PH, e_M, T, h, m
        - self.Z_costs must be set beforehand (e.g., by ExergoeconomicAnalysis)
        - self.E_F, self.E_P, self.E_D already computed by calc_exergy_balance
        """
        # For convenience, read inlet/outlet dictionaries
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Build "cost flows" from thermal, physical, mechanical exergies
        C_T_in = inlet['m'] * inlet['e_T']
        C_T_out = outlet['m'] * outlet['e_T']

        C_PH_in = inlet['m'] * inlet['e_PH']
        C_PH_out = outlet['m'] * outlet['e_PH']

        C_M_in = inlet['m'] * inlet['e_M']
        C_M_out = outlet['m'] * outlet['e_M']

        # Initialize result placeholders
        self.C_F = 0.0
        self.C_P = 0.0

        # Heat transfer Q
        Q = outlet['m'] * outlet['h'] - inlet['m'] * inlet['h']

        # === CASE 1: Heat release (Q < 0) ===
        if Q < 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                if getattr(self, 'dissipative', False):
                    self.C_P = np.nan
                else:
                    self.C_P = C_T_in - C_T_out
                self.C_F = C_PH_in - C_PH_out

            elif inlet['T'] >= T0 and outlet['T'] < T0:
                self.C_P = C_T_out
                self.C_F = (C_T_in + C_T_out + (C_M_in - C_M_out))

            elif inlet['T'] <= T0 and outlet['T'] <= T0:
                self.C_P = C_T_out - C_T_in
                self.C_F = self.C_P + (C_M_in - C_M_out)

            else:
                # Unimplemented corner case
                logging.warning(
                    f"SimpleHeatExchanger '{self.label}': unimplemented case (Q < 0, T_in < T0 < T_out?)."
                )
                self.C_P = np.nan
                self.C_F = np.nan

        # === CASE 2: Heat addition (Q > 0) ===
        elif Q > 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                self.C_P = C_PH_out - C_PH_in
                self.C_F = C_T_out - C_T_in

            elif inlet['T'] < T0 and outlet['T'] > T0:
                self.C_P = C_T_out + C_T_in
                self.C_F = (C_T_in + (C_M_in - C_M_out))

            elif inlet['T'] < T0 and outlet['T'] < T0:
                if getattr(self, 'dissipative', False):
                    self.C_P = np.nan
                else:
                    self.C_P = (C_T_in - C_T_out) + (C_M_out - C_M_in)
                self.C_F = (C_T_in - C_T_out)

            else:
                logging.warning(
                    f"SimpleHeatExchanger '{self.label}': unimplemented case (Q > 0, T_in > T0 > T_out?)."
                )
                self.C_P = np.nan
                self.C_F = np.nan

        # === CASE 3: Fully dissipative or Q == 0 ===
        else:
            self.C_P = np.nan
            self.C_F = C_PH_in - C_PH_out

        # Debug check difference
        logging.debug(
            f"{self.label}: difference C_P - (C_F + Z_costs) = "
            f"{self.C_P - (self.C_F + self.Z_costs)}"
        )

        # === Calculate final exergoeconomic metrics ===
        # c_F, c_P: cost per exergy flow [currency/W], if E_F/E_P nonzero
        self.c_F = self.C_F / self.E_F if self.E_F and self.E_F > 1e-12 else None
        self.c_P = self.C_P / self.E_P if self.E_P and self.E_P > 1e-12 and not np.isnan(self.E_P) else None

        # Cost flow associated with destruction: C_D = c_F * E_D
        self.C_D = (self.c_F * self.E_D) if self.c_F and self.E_D else None

        # Relative cost difference: (c_P - c_F)/c_F
        self.r = ((self.c_P - self.c_F) / self.c_F) if self.c_F and self.c_P else None

        # Exergoeconomic factor: f = Z_costs / (Z_costs + C_D)
        Z = self.Z_costs
        denom = Z + self.C_D if self.C_D else Z
        self.f = (Z / denom) if denom != 0.0 else None

    def aux_eqs(self, exergy_cost_matrix, exergy_cost_vector, counter, T0):
        r"""
        Insert auxiliary cost equations ensuring cost flow consistency.

        For SimpleHeatExchanger, ensures that:
        - c_T_in = c_T_out
        - c_PH_in = c_PH_out
        - c_M_in = c_M_out

        Each equation is inserted as:
        c_in - c_out = 0

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
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Insert equations:
        # c_T_in - c_T_out = 0
        # c_PH_in - c_PH_out = 0
        # c_M_in - c_M_out = 0

        # Thermal Exergy Cost Equation
        self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter, inlet, outlet, "T")
        exergy_cost_vector[counter] = 0.0
        counter += 1

        # Physical Exergy Cost Equation
        self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter, inlet, outlet, "PH")
        exergy_cost_vector[counter] = 0.0
        counter += 1

        # Mechanical Exergy Cost Equation
        self._insert_cost_eq(exergy_cost_matrix, exergy_cost_vector, counter, inlet, outlet, "M")
        exergy_cost_vector[counter] = 0.0
        counter += 1

        return [exergy_cost_matrix, exergy_cost_vector, counter]

    def dis_eqs(self, exergy_cost_matrix, exergy_cost_vector, counter, T0):
        r"""
        Insert dissipative cost distribution equations.

        If the heat exchanger is 'dissipative', distribute the cost of exergy destruction
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
            logging.warning("Dissipative SimpleHeatExchanger has no serving_components defined.")
            return [exergy_cost_matrix, exergy_cost_vector, counter]

        num_serving = len(self.serving_components)
        if num_serving == 0:
            logging.warning("Dissipative SimpleHeatExchanger has an empty serving_components list.")
            return [exergy_cost_matrix, exergy_cost_vector, counter]

        # Distribute the cost equally among serving components
        fraction = 1.0 / num_serving

        for comp in self.serving_components:
            # Distribute thermal exergy cost
            exergy_cost_matrix[counter, comp.inl[0]["Ex_C_col"]["T"]] += fraction
            exergy_cost_matrix[counter, comp.outl[0]["Ex_C_col"]["T"]] += -fraction

            # Distribute physical exergy cost
            exergy_cost_matrix[counter + 1, comp.inl[0]["Ex_C_col"]["PH"]] += fraction
            exergy_cost_matrix[counter + 1, comp.outl[0]["Ex_C_col"]["PH"]] += -fraction

            # Distribute mechanical exergy cost
            exergy_cost_matrix[counter + 2, comp.inl[0]["Ex_C_col"]["M"]] += fraction
            exergy_cost_matrix[counter + 2, comp.outl[0]["Ex_C_col"]["M"]] += -fraction

            # Increment counter for each serving component's distribution
            counter += 3  # Assuming 3 rows per serving component

        # Set the cost rate equation for dissipative component
        # Assuming a dedicated cost column for dissipative components named "dissipative"
        if "dissipative" in self.Ex_C_col:
            dissipative_col = self.Ex_C_col["dissipative"]
            exergy_cost_matrix[counter, dissipative_col] = 1.0
            exergy_cost_vector[counter] = self.Z_costs
            counter += 1
        else:
            logging.warning("Dissipative cost column 'dissipative' not found in Ex_C_col.")

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
            Type of exergy ('T', 'PH', 'M').

        Returns
        -------
        None
        """
        in_e = in_conn.get(f"e_{exergy_type}", 0.0)
        out_e = out_conn.get(f"e_{exergy_type}", 0.0)

        if exergy_type not in in_conn["Ex_C_col"] or exergy_type not in out_conn["Ex_C_col"]:
            logging.error(f"Exergy type '{exergy_type}' not found in Ex_C_col mappings.")
            raise KeyError(f"Exergy type '{exergy_type}' not found in Ex_C_col mappings.")

        in_col = in_conn["Ex_C_col"][exergy_type]
        out_col = out_conn["Ex_C_col"][exergy_type]

        if in_e != 0.0 and out_e != 0.0:
            matrix[row, in_col] = 1.0 / in_e
            matrix[row, out_col] = -1.0 / out_e
        elif in_e == 0.0 and out_e != 0.0:
            # If inbound exergy is zero, enforce c_in = 0
            matrix[row, in_col] = 1.0
        elif in_e != 0.0 and out_e == 0.0:
            # If outbound exergy is zero, enforce c_out = 0
            matrix[row, out_col] = 1.0
        else:
            # Both exergies are zero; enforce c_in - c_out = 0
            matrix[row, in_col] = 1.0
            matrix[row, out_col] = -1.0
