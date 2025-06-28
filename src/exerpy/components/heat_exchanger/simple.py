import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class SimpleHeatExchanger(Component):
    r"""
    Class for exergy and exergoeconomic analysis of simple heat exchangers.

    This class performs exergy and exergoeconomic analysis calculations for heat exchanger components,
    accounting for one inlet and one outlet stream across various temperature regimes, including
    above and below ambient temperature, and optional dissipative behavior.

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
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the heat exchanger component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - dissipative (bool): whether component has dissipative behavior, default False
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate in currency/h, default 0.0
        """
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the simple heat exchanger.

        **Heat release** :math:\dot{Q}<0

        Case 1: Both streams above ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Case 2: Inlet above and outlet below ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        Case 3: Both streams below ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}\bigr)
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        **Heat injection** :math:\dot{Q}>0

        Case 1: Both streams above ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        Case 2: Inlet below and outlet above ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        Case 3: Both streams below ambient temperature

        If split_physical_exergy=True:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{in}}\bigr)

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        Else:

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Fully dissipative or :math:\dot{Q}=0

        .. math::

            \dot{E}_{\mathrm{P}} = \mathrm{NaN}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        p0 : float
            Ambient pressure (Pa).
        split_physical_exergy : bool
            Whether to split thermal and mechanical exergy.

        Raises
        ------
        ValueError
            If required inlet or outlet are missing.
        """
        # Validate the number of inlets and outlets
        if not hasattr(self, 'inl') or not hasattr(self, 'outl') or len(self.inl) < 1 or len(self.outl) < 1:
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
                if split_physical_exergy:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else inlet['m'] * (inlet['e_T'] - outlet['e_T'])
                else:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
                self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])

            elif inlet['T'] >= T0 and outlet['T'] < T0:
                if split_physical_exergy:
                    self.E_P = outlet['m'] * outlet['e_T']
                    self.E_F = (inlet['m'] * inlet['e_T'] + outlet['m'] * outlet['e_T'] +
                            (inlet['m'] * inlet['e_M'] - outlet['m'] * outlet['e_M']))
                else:
                    self.E_P = outlet['m'] * outlet['e_PH']
                    self.E_F = inlet['m'] * inlet['e_PH']

            elif inlet['T'] <= T0 and outlet['T'] <= T0:
                if split_physical_exergy:
                    self.E_P = outlet['m'] * (outlet['e_T'] - inlet['e_T'])
                    self.E_F = self.E_P + inlet['m'] * (inlet['e_M'] - outlet['m'] * outlet['e_M'])
                else:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else \
                        outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                    self.E_F = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])

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
                if split_physical_exergy:
                    self.E_P = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                    self.E_F = outlet['m'] * (outlet['e_T'] - inlet['e_T'])
                else:
                    self.E_P = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                    self.E_F = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
            elif inlet['T'] < T0 and outlet['T'] > T0:
                if split_physical_exergy:
                    self.E_P = outlet['m'] * (outlet['e_T'] + inlet['e_T'])
                    self.E_F = (inlet['m'] * inlet['e_T'] +
                            (inlet['m'] * inlet['e_M'] - outlet['m'] * outlet['e_M']))
                else:
                    self.E_P = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])
                    self.E_F = outlet['m'] * (outlet['e_PH'] - inlet['e_PH'])

            elif inlet['T'] < T0 and outlet['T'] < T0:
                if split_physical_exergy:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else \
                        inlet['m'] * (inlet['e_T'] - outlet['e_T']) + \
                        (outlet['m'] * outlet['e_M'] - inlet['m'] * inlet['e_M'])
                    self.E_F = inlet['m'] * (inlet['e_T'] - outlet['e_T'])
                else:
                    self.E_P = np.nan if getattr(self, 'dissipative', False) else \
                        inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
                    self.E_F = inlet['m'] * (inlet['e_PH'] - outlet['e_PH'])
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
            f"SimpleHeatExchanger exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""
        This function must be implemented in the future.

        The exergoeconomic analysis of SimpleHeatExchanger is not implemented yet.
        """
        
        logging.error(
                    "The exergoeconomic analysis of SimpleHeatExchanger is not implemented yet. "
                    "This method will be implemented in a future release."
                )
        r"""
        Add auxiliary cost equations for the heat exchanger.

        For all cases:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{out}}}\,\dot{C}^{\mathrm{T}}_{\mathrm{out}}
            + \frac{1}{\dot{E}^{\mathrm{T}}_{\mathrm{in}}}\,\dot{C}^{\mathrm{Tc}}_{\mathrm{in}}
            = 0

        F rule for mechanical exergy:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{M}}_{\mathrm{out}}\,\dot{C}^{\mathrm{M}}_{\mathrm{out}}
            + \frac{1}{\dot{E}^{\mathrm{M}}_{\mathrm{in}}\,\dot{C}^{\mathrm{M}}_{\mathrm{in}}
            = 0

        F rule for chemical exergy:

        .. math::
            -\frac{1}{\dot{E}^{\mathrm{CH}}_{\mathrm{out}}}\,\dot{C}^{\mathrm{CH}}_{\mathrm{out}}
            + \frac{1}{\dot{E}^{\mathrm{CH}}_{\mathrm{in}}}\,\dot{C}^{\mathrm{CH}}_{\mathrm{in}}
            = 0

        """         
        """# For all cases: c_Tin = c_Tout
        A[counter, self.inl[0]["CostVar_index"]["T"]] = (1 / self.inl[0]["e_T"] 
                                                        if self.inl[0]["e_T"] != 0 else 1)
        A[counter, self.outl[0]["CostVar_index"]["T"]] = (-1 / self.outl[0]["e_T"]
                                                        if self.outl[0]["e_T"] != 0 else -1)
        equations[counter] = f"aux_equality_therm_{self.outl[0]['name']}"

        b[counter] = 0

        # For alle cases: c_Min = c_Mout
        A[counter+1, self.inl[0]["CostVar_index"]["M"]] = (1 / self.inl[0]["e_M"]
                                                            if self.inl[0]["e_M"] != 0 else 1)
        A[counter+1, self.outl[0]["CostVar_index"]["M"]] = (-1 / self.outl[0]["e_M"]
                                                            if self.outl[0]["e_M"] != 0 else 1)
        equations[counter+1] = f"aux_equality_mech_{self.outl[0]['name']}"
        b[counter+1] = 0

        # For all cases: c_CHin = c_CHout
        if chemical_exergy_enabled:
            A[counter+2, self.inl[0]["CostVar_index"]["CH"]] = (1 / self.inl[0]["e_CH"]
                                                                if self.inl[0]["e_CH"] != 0 else 1)
            A[counter+2, self.outl[0]["CostVar_index"]["CH"]] = (-1 / self.outl[0]["e_CH"]
                                                                if self.outl[0]["e_CH"] != 0 else 1)
            equations[counter+2] = f"aux_equality_chem_{self.outl[0]['name']}"
            b[counter+2] = 0
            counter += 3
        else:
            counter += 2

        return A, b, counter, equations"""
    
    def exergoeconomic_balance(self, T0):
        r"""
        This function must be implemented in the future.

        The exergoeconomic analysis of SimpleHeatExchanger is not implemented yet.
        """
        
        logging.error(
                    "The exergoeconomic analysis of SimpleHeatExchanger is not implemented yet. "
                    "This method will be implemented in a future release."
                )
        r"""
        Perform exergoeconomic cost balance for the simple heat exchanger.

        .. math::
            \dot{C}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{C}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{C}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{C}^{\mathrm{M}}_{\mathrm{out}}
            + \dot{Z}
            = 0

        In case the chemical exergy of the streams is know:

        .. math::
            \dot{C}^{\mathrm{CH}}_{\mathrm{in},1} =
            \dot{C}^{\mathrm{CH}}_{\mathrm{out},1}

        .. math::
            \dot{C}^{\mathrm{CH}}_{\mathrm{in},2} =
            \dot{C}^{\mathrm{CH}}_{\mathrm{out},2}

        This method computes cost coefficients and ratios:

        **Heat release** :math:\dot{Q}<0

        Case 1: Both streams above ambient temperature

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}

        Case 2: Inlet above and outlet below ambient temperature

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Case 3: Both streams below ambient temperature

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \bigl(\dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}\bigr)
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        **Heat injection** :math:\dot{Q}

        Case 1: Both streams above ambient temperature

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        Case 2: Inlet below and outlet above ambient temperature

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \dot{E}^{\mathrm{T}}_{\mathrm{in}}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{out}}\bigr)

        Case 3: Both streams below ambient temperature

        .. math::

            \dot{E}_{\mathrm{P}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}
            + \bigl(\dot{E}^{\mathrm{M}}_{\mathrm{out}}
            - \dot{E}^{\mathrm{M}}_{\mathrm{in}}\bigr)

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{T}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{out}}

        Fully dissipative or :math:\dot{Q}=0

        .. math::

            \dot{E}_{\mathrm{P}} = \mathrm{NaN}

        .. math::

            \dot{E}_{\mathrm{F}}
            = \dot{E}^{\mathrm{PH}}_{\mathrm{in}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{out}}
        
        Parameters
        ----------
        T0 : float
            Ambient temperature (K).
        """
