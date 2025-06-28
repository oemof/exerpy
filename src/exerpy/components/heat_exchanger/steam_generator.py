import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class SteamGenerator(Component):
    r"""
    Class for exergy and exergoeconomic analysis of heat exchangers.

    This class performs exergy and exergoeconomic analysis calculations for heat exchanger components,
    accounting for two inlet and two outlet streams across various temperature regimes, including
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

    Notes
    -----
    The component has several input and output streams as follows.

    Inlet streams:

    - inl[0]: Feed water inlet (high pressure)
    - inl[1]: Steam inlet (intermediate pressure)
    - inl[2]: Heat inlet (providing the heat input Q)
    - inl[3]: Water injection (high pressure)
    - inl[4]: Water injection (intermediate pressure)

    Outlet streams:

    - outl[0]: Superheated steam outlet (high pressure)
    - outl[1]: Superheated steam outlet (intermediate pressure)
    - outl[2]: Drain / Blow down outlet

    """

    def __init__(self, **kwargs):
        r"""
        Initialize the steam generator component.

        Parameters
        ----------
        **kwargs : dict
            Arbitrary keyword arguments. Recognized keys:
            - Ex_C_col (dict): custom cost coefficients, default {}
            - Z_costs (float): investment cost rate in currency/h, default 0.0
        """        
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Compute the exergy balance of the steam generator.

        The exergy fuel is defined as follows. 

        If `split_physical_exergy` is `True`:

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl[\dot{E}^{\mathrm{T}}_{\mathrm{out,HP}} - \dot{E}^{\mathrm{T}}_{\mathrm{in,HP}}\bigr]
            + \bigl[\dot{E}^{\mathrm{T}}_{\mathrm{out,IP}} - \dot{E}^{\mathrm{T}}_{\mathrm{in,IP}}\bigr]
            - \dot{E}^{\mathrm{T}}_{\mathrm{w,HP}}
            - \dot{E}^{\mathrm{T}}_{\mathrm{w,IP}}

        If `split_physical_exergy` is `False`:

        .. math::
            \dot{E}_{\mathrm{F}}
            = \bigl[\dot{E}^{\mathrm{PH}}_{\mathrm{out,HP}} - \dot{E}^{\mathrm{PH}}_{\mathrm{in,HP}}\bigr]
            + \bigl[\dot{E}^{\mathrm{PH}}_{\mathrm{out,IP}} - \dot{E}^{\mathrm{PH}}_{\mathrm{in,IP}}\bigr]
            - \dot{E}^{\mathrm{PH}}_{\mathrm{w,HP}}
            - \dot{E}^{\mathrm{PH}}_{\mathrm{w,IP}}

        The exergy product is defined as:

        .. math::

            \dot{E}_\mathrm{P} = \Bigl[ \dot E^{\mathrm{PH}}_{\mathrm{out,HP}}
            - \dot E^{\mathrm{PH}}_{\mathrm{in,HP}} \Bigr]
            + \Bigl[ \dot E^{\mathrm{PH}}_{\mathrm{out,IP}}
            - \dot E^{\mathrm{PH}}_{\mathrm{in,IP}} \Bigr]
            - \dot E^{\mathrm{PH}}_{\mathrm{w,HP}}
            - \dot E^{\mathrm{PH}}_{\mathrm{w,IP}}

        where the subscripts HP and IP denote high and intermediate pressure streams,
        respectively, and w stands for water injection.

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
            If required inlets or outlets are missing.
        """
        # Ensure that all necessary streams exist
        required_inlets = [0]
        required_outlets = [0, 2]
        for idx in required_inlets:
            if idx not in self.inl:
                raise ValueError(f"Missing inlet stream with index {idx}.")
        for idx in required_outlets:
            if idx not in self.outl:
                raise ValueError(f"Missing outlet stream with index {idx}.")

        if split_physical_exergy:
            exergy_type = 'e_T'
        else:
            exergy_type = 'e_PH'

        # Calculate exergy fuel
        # High pressure part: Superheated steam outlet (HP) minus Feed water inlet (HP)
        E_F_HP = self.outl[0]['m'] * self.outl[0][exergy_type] - self.inl[0]['m'] * self.inl[0][exergy_type]
        # Intermediate pressure part: Superheated steam outlet (IP) minus Steam inlet (IP)
        E_F_IP = self.outl.get(1, {}).get('m', 0) * self.outl.get(1, {}).get(exergy_type, 0) - self.inl.get(1, {}).get('m', 0) * self.inl.get(1, {}).get(exergy_type, 0)
        # Water injection contributions (assumed to be negative)
        E_F_w_inj = self.inl.get(2, {}).get('m', 0) * self.inl.get(2, {}).get(exergy_type, 0) + self.inl.get(3, {}).get('m', 0) * self.inl.get(3, {}).get(exergy_type, 0)
        self.E_F = E_F_HP + E_F_IP - E_F_w_inj
        logging.warning(f"Since the temperature level of the heat source of the steam generator is unknown, "
                        "the exergy fuel of this component is calculated based on the thermal exergy value of the water streams.")
        # Calculate exergy product
        # High pressure part: Superheated steam outlet (HP) minus Feed water inlet (HP)
        E_P_HP = self.outl[0]['m'] * self.outl[0]['e_PH'] - self.inl[0]['m'] * self.inl[0]['e_PH']
        # Intermediate pressure part: Superheated steam outlet (IP) minus Steam inlet (IP)
        E_P_IP = self.outl.get(1, {}).get('m', 0) * self.outl.get(1, {}).get('e_PH', 0) - self.inl.get(1, {}).get('m', 0) * self.inl.get(1, {}).get('e_PH', 0)
        # Water injection contributions (assumed to be negative)
        E_P_w_inj = self.inl.get(2, {}).get('m', 0) * self.inl.get(2, {}).get('e_PH', 0) + self.inl.get(3, {}).get('m', 0) * self.inl.get(3, {}).get('e_PH', 0)
        self.E_P = E_P_HP + E_P_IP - E_P_w_inj

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"SteamGenerator exergy balance calculated: "
            f"E_P = {self.E_P:.2f} W, E_F = {self.E_F:.2f} W, "
            f"E_D = {self.E_D:.2f} W, Efficiency = {self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""
        This function must be implemented in the future.

        The exergoeconomic analysis of SteamGenerator is not implemented yet.
        """
        logging.error(
            "The exergoeconomic analysis of SteamGenerator is not implemented yet. "
            "This method will be implemented in a future release."
        )
        """
        Auxiliary equations for the steam generator.
        
        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        the following auxiliary cost relations:
        
        (1) c_T(heat_source)/E_F = c_T(HP_outlet)/E_T(HP) + c_T(IP_outlet)/E_T(IP)
            - P-principle: thermal exergy costs from heat source are distributed to steam outlets
            
        (2) 1/E_M_in(HP) * C_M_in(HP) - 1/E_M_out(HP) * C_M_out(HP) = 0
            - F-principle: specific mechanical exergy costs equalized between HP inlet/outlet
            
        (3) 1/E_M_in(IP) * C_M_in(IP) - 1/E_M_out(IP) * C_M_out(IP) = 0
            - F-principle: specific mechanical exergy costs equalized between IP inlet/outlet
            
        (4-5) Chemical exergy cost equations (if enabled) for HP and IP streams
            - F-principle: specific chemical exergy costs equalized between inlets/outlets
        
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

    def exergoeconomic_balance(self, T0):
        r"""
        This function must be implemented in the future.

        The exergoeconomic analysis of SteamGenerator is not implemented yet.
        """
        
        logging.error(
            "The exergoeconomic analysis of SteamGenerator is not implemented yet. "
            "This method will be implemented in a future release."
        )
        """
        Perform exergoeconomic balance calculations for the steam generator.
        
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
        # 1) Product cost rate: HP and IP steam net physical exergy costs, minus injection
        C_P_hp = (self.outl[0]['m'] * self.outl[0]['C_PH']
                  - self.inl[0]['m'] * self.inl[0]['C_PH'])
        C_P_ip = 0.0
        if 1 in self.outl and 1 in self.inl:
            C_P_ip = (self.outl[1]['m'] * self.outl[1]['C_PH']
                      - self.inl[1]['m'] * self.inl[1]['C_PH'])
        # Subtract water injection costs
        C_P_w = 0.0
        if 3 in self.inl:
            C_P_w += self.inl[3]['m'] * self.inl[3]['C_PH']
        if 4 in self.inl:
            C_P_w += self.inl[4]['m'] * self.inl[4]['C_PH']
        self.C_P = C_P_hp + C_P_ip - C_P_w

        # 2) Fuel cost rate: cost of heat exergy stream
        self.C_F = self.inl[2]['C_T']

        # 3) Specific costs and destruction cost
        self.c_F = self.C_F / self.E_F if self.E_F != 0 else float('nan')
        self.c_P = self.C_P / self.E_P if self.E_P != 0 else float('nan')
        self.C_D = self.C_F - self.C_P
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F != 0 else float('nan')
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) != 0 else float('nan')