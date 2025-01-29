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
            msg = "Simple heat exchanger requires at least one inlet and one outlet as well as one heat flow."
            logging.error(msg)
            raise ValueError(msg)
        if len(self.inl) > 2 or len(self.outl) > 2:
            msg = "Simple heat exchanger requires a maximum of two inlets and two outlets."
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
                logging.warning(f"Exergy balance for simple heat exchangers with outlet temperature higher "
                                "than inlet temperature during heat release is not implemented.")
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
                logging.warning(f"Exergy balance for simple heat exchangers with inlet temperature "
                                "higher than outlet temperature during heat addition is not implemented.")
                self.E_P = np.nan
                self.E_F = np.nan

        # Case 3: Fully dissipative (Q == 0 or other scenarios)
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
            f"Compressor exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
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
        - self.Z_costs must be set beforehand (e.g. by ExergoeconomicAnalysis)
        - self.E_F, self.E_P, self.E_D already computed by calc_exergy_balance
        """
        # For convenience, read inlet/outlet dictionaries
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Build "cost flows" from thermal, physical, mechanical exergies, analog to TESPy
        # E.g. "C_therm_in = mass_flow_in * e_T_in"
        C_therm_in = inlet['m'] * inlet['e_T']
        C_therm_out = outlet['m'] * outlet['e_T']

        C_mech_in = inlet['m'] * inlet['e_M']
        C_mech_out = outlet['m'] * outlet['e_M']

        C_phys_in = inlet['m'] * inlet['e_PH']
        C_phys_out = outlet['m'] * outlet['e_PH']

        # Heat transfer
        Q = outlet['m'] * outlet['h'] - inlet['m'] * inlet['h']

        # Initialize result placeholders
        self.C_F = 0.0
        self.C_P = 0.0

        # === CASE 1: Heat release (Q < 0) ===
        if Q < 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                # both above ambient
                if getattr(self, 'dissipative', False):
                    self.C_P = np.nan
                else:
                    self.C_P = C_therm_in - C_therm_out
                self.C_F = C_phys_in - C_phys_out

            elif inlet['T'] >= T0 and outlet['T'] < T0:
                # inlet above, outlet below T0
                self.C_P = C_therm_out
                self.C_F = (C_therm_in + C_therm_out + (C_mech_in - C_mech_out))

            elif inlet['T'] <= T0 and outlet['T'] <= T0:
                # both below T0
                self.C_P = C_therm_out - C_therm_in
                # the line in TESPy is ambiguous but we mirror it
                self.C_F = (self.C_P + (C_mech_in - C_mech_out))

            else:
                # unimplemented corner case
                logging.warning(
                    "SimpleHeatExchanger: unimplemented case (Q < 0, T_in < T0 < T_out?)."
                )
                self.C_P = np.nan
                self.C_F = np.nan

        # === CASE 2: Heat addition (Q > 0) ===
        elif Q > 0:
            if inlet['T'] >= T0 and outlet['T'] >= T0:
                # both above T0
                self.C_P = C_phys_out - C_phys_in
                self.C_F = C_therm_out - C_therm_in

            elif inlet['T'] < T0 and outlet['T'] > T0:
                self.C_P = C_therm_out + C_therm_in
                self.C_F = (C_therm_in + (C_mech_in - C_mech_out))

            elif inlet['T'] < T0 and outlet['T'] < T0:
                # both below T0
                if getattr(self, 'dissipative', False):
                    self.C_P = np.nan
                else:
                    self.C_P = (C_therm_in - C_therm_out) + (C_mech_out - C_mech_in)
                self.C_F = (C_therm_in - C_therm_out)

            else:
                logging.warning(
                    "SimpleHeatExchanger: unimplemented case (Q > 0, T_in > T0 > T_out?)."
                )
                self.C_P = np.nan
                self.C_F = np.nan

        # === CASE 3: Q == 0 or "fully dissipative" fallback ===
        else:
            self.C_P = np.nan
            self.C_F = C_phys_in - C_phys_out

        # Debug check difference
        logging.debug(
            f"{self.label}: difference C_P - (C_F + Z_costs) = "
            f"{self.C_P - (self.C_F + getattr(self, 'Z_costs', 0.0))}"
        )

        # === Calculate final exergoeconomic metrics ===
        # c_F, c_P: cost per exergy flow [currency/W], if E_F/E_P nonzero
        if self.E_F and self.E_F > 1e-12:
            self.c_F = self.C_F / self.E_F
        else:
            self.c_F = None

        if self.E_P and self.E_P > 1e-12:
            self.c_P = self.C_P / self.E_P
        else:
            self.c_P = None

        # Cost flow associated with destruction: C_D = c_F * E_D
        if self.c_F is not None and self.E_D is not None:
            self.C_D = (self.c_F * self.E_D) if self.c_F > 1e-12 else 0.0
        else:
            self.C_D = None

        # Relative cost difference: (C_P - C_F)/C_F => or (c_P - c_F)/c_F
        if self.c_F and self.c_P:
            self.r = (self.c_P - self.c_F) / self.c_F
        else:
            self.r = None

        # Exergoeconomic factor: f = Z_costs / (Z_costs + C_D)
        ZC = getattr(self, 'Z_costs', 0.0)
        if self.C_D is not None and self.C_D > 1e-12:
            self.f = ZC / (ZC + self.C_D)
        else:
            self.f = None
