import logging

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class SteamGenerator(Component):
    r"""
    Class for exergy analysis of steam generators.

    This class performs exergy analysis calculations for steam generators.
    The component has several input and output streams as follows:

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

    The exergy product is defined as:

    .. math::
        \dot{E}_P = \Bigl[ \dot{m}_{\mathrm{out,HP}}\,e_{\mathrm{out,HP}}
        - \dot{m}_{\mathrm{in,HP}}\,e_{\mathrm{in,HP}} \Bigr]
        + \Bigl[ \dot{m}_{\mathrm{out,IP}}\,e_{\mathrm{out,IP}}
        - \dot{m}_{\mathrm{in,IP}}\,e_{\mathrm{in,IP}} \Bigr]
        - \dot{m}_{\mathrm{w,HP}}\,e_{\mathrm{w,HP}}
        - \dot{m}_{\mathrm{w,IP}}\,e_{\mathrm{w,IP}}

    where:
        - \(\dot{m}\) is the mass flow rate and \(e\) is the specific exergy of the stream.
        - The subscripts HP and IP denote high and intermediate pressure streams,
          respectively, and 'w' stands for water injection.

    The exergy fuel is computed from the heat input as:

    .. math::
        \dot{E}_F = E_q = Q \left( 1 - \frac{T_b}{T_0} \right)

    with the thermodynamic temperature difference defined by

    .. math::
        T_b = \frac{h_{\mathrm{out,HP}} - h_{\mathrm{in,HP}}}{s_{\mathrm{out,HP}} - s_{\mathrm{in,HP}}}

    where:
        - \(h\) and \(s\) are the specific enthalpy and entropy,
        - \(T_0\) is the ambient temperature.

    The exergy destruction and efficiency are then given by:

    .. math::
        \dot{E}_D = \dot{E}_F - \dot{E}_P \quad\text{and}\quad \varepsilon = \frac{\dot{E}_P}{\dot{E}_F}

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to the parent class.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component :math:`\dot{E}_F` in :math:`\text{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_P` in :math:`\text{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_D` in :math:`\text{W}`.
    epsilon : float
        Exergetic efficiency :math:`\varepsilon`.
    inl : dict
        Dictionary containing inlet streams.
    outl : dict
        Dictionary containing outlet streams.
    """

    def __init__(self, **kwargs):
        r"""Initialize steam generator component with given parameters."""
        self.dissipative = False
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the steam generator.

        This method computes the exergy fuel from the heat inlet using the relation

        .. math::
            E_F = Q \left(1 - \frac{T_b}{T_0}\right),
            \quad T_b = \frac{h_{\mathrm{out,HP}} - h_{\mathrm{in,HP}}}{s_{\mathrm{out,HP}} - s_{\mathrm{in,HP}}}

        and the exergy product as

        .. math::
            E_P = \Bigl[ \dot{m}_{\mathrm{out,HP}}\,e_{\mathrm{out,HP}} -
            \dot{m}_{\mathrm{in,HP}}\,e_{\mathrm{in,HP}} \Bigr]
            + \Bigl[ \dot{m}_{\mathrm{out,IP}}\,e_{\mathrm{out,IP}} -
            \dot{m}_{\mathrm{in,IP}}\,e_{\mathrm{in,IP}} \Bigr]
            - \dot{m}_{\mathrm{w,HP}}\,e_{\mathrm{w,HP}}
            - \dot{m}_{\mathrm{w,IP}}\,e_{\mathrm{w,IP}}

        The exergy destruction is given by

        .. math::
            E_D = E_F - E_P

        and the exergetic efficiency is

        .. math::
            \varepsilon = \frac{E_P}{E_F}

        Parameters
        ----------
        T0 : float
            Ambient temperature in Kelvin.
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

        # Calculate T_b for high pressure streams: from superheated steam outlet (HP) and feed water inlet (HP)
        try:
            T_b = (self.outl[0]['h'] - self.inl[0]['h']) / (self.outl[0]['s'] - self.inl[0]['s'])
        except ZeroDivisionError:
            raise ZeroDivisionError("Division by zero encountered in calculating T_b. Check entropy differences.")
       
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
        logging.error("Auxiliary equations are not implemented for steam generator.")

    def exergoeconomic_balance(self, T0):
        logging.error("Exergoeconomic balance is not implemented for steam generator.")