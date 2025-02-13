import logging
import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Compressor(Component):
    r"""
    Class for exergy and exergoeconomic analysis of compressors.

    This class performs exergy and exergoeconomic analysis calculations for compressors,
    considering thermal, mechanical, and physical exergy flows. The exergy product and fuel
    are calculated based on temperature relationships between inlet, outlet, and ambient conditions.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.
        Optional parameter 'Z_costs' (float): Investment cost rate of the component in currency/h.

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
        Power input to the compressor in :math:`\text{W}`.
    inl : dict
        Dictionary containing inlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        enthalpies, and specific exergies.
    Z_costs : float
        Investment cost rate of the component in currency/h.

    Notes
    -----
    The exergy analysis considers three cases based on temperature relationships:

    Case 1 - **Both temperatures above ambient** (:math:`T_\mathrm{in}, T_\mathrm{out} > T_0`):

    .. math::

        \dot{E}_\mathrm{P} &= \dot{m} \cdot (e_\mathrm{out}^\mathrm{PH} -
        e_\mathrm{in}^\mathrm{PH})\\
        \dot{E}_\mathrm{F} &= |\dot{W}|

    Case 2 - **Inlet below, outlet above ambient** (:math:`T_\mathrm{in} < T_0 < T_\mathrm{out}`):

    .. math::

        \dot{E}_\mathrm{P} &= \dot{m} \cdot e_\mathrm{out}^\mathrm{T} +
        \dot{m} \cdot (e_\mathrm{out}^\mathrm{M} - e_\mathrm{in}^\mathrm{M})\\
        \dot{E}_\mathrm{F} &= |\dot{W}| + \dot{m} \cdot e_\mathrm{in}^\mathrm{T}

    Case 3 - **Both temperatures below ambient** (:math:`T_\mathrm{in}, T_\mathrm{out} \leq T_0`):

    .. math::

        \dot{E}_\mathrm{P} &= \dot{m} \cdot (e_\mathrm{out}^\mathrm{M} -
        e_\mathrm{in}^\mathrm{M})\\
        \dot{E}_\mathrm{F} &= |\dot{W}| + \dot{m} \cdot (e_\mathrm{in}^\mathrm{T}
        - e_\mathrm{out}^\mathrm{T})

    For all valid cases, the exergy destruction is:

    .. math::

        \dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}

    where:
        - :math:`\dot{W}`: Power input
        - :math:`e^\mathrm{T}`: Thermal exergy
        - :math:`e^\mathrm{M}`: Mechanical exergy
        - :math:`e^\mathrm{PH}`: Physical exergy
    """

    def __init__(self, **kwargs):
        r"""Initialize compressor component with given parameters."""
        super().__init__(**kwargs)
        self.P = None
        self.Z_costs = kwargs.get('Z_costs', 0.0)  # Investment cost rate in currency/h

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the compressor.

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
            self.P = self.outl[0]['m'] * (self.outl[0]['h'] - self.inl[0]['h'])

        # Case 1: Both temperatures above ambient
        if round(self.inl[0]['T'], 5) >= T0 and round(self.outl[0]['T'], 5) > T0:
            self.E_P = self.outl[0]['m'] * (self.outl[0]['e_PH'] - self.inl[0]['e_PH'])
            self.E_F = abs(self.P)

        # Case 2: Inlet below, outlet above ambient
        elif round(self.inl[0]['T'], 5) < T0 and round(self.outl[0]['T'], 5) > T0:
            self.E_P = (self.outl[0]['m'] * self.outl[0]['e_T'] +
                        self.outl[0]['m'] * (self.outl[0]['e_M'] - self.inl[0]['e_M']))
            self.E_F = abs(self.P) + self.inl[0]['m'] * self.inl[0]['e_T']

        # Case 3: Both temperatures below ambient
        elif round(self.inl[0]['T'], 5) < T0 and round(self.outl[0]['T'], 5) <= T0:
            self.E_P = self.outl[0]['m'] * (self.outl[0]['e_M'] - self.inl[0]['e_M'])
            self.E_F = abs(self.P) + self.inl[0]['m'] * (self.inl[0]['e_T'] -
                                                        self.outl[0]['e_T'])

        # Invalid case: outlet temperature smaller than inlet
        else:
            logging.warning(
                f"Exergy balance of compressor '{self.label}' where outlet temperature is smaller "
                "than inlet temperature is not implemented."
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Compressor '{self.label}' exergy balance calculated: "
            f"E_P={self.E_P:.2f} W, E_F={self.E_F:.2f} W, E_D={self.E_D:.2f} W, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations):
        # c_in_ch = c_out_ch
        # delta c_therm = delta c_mech   # alt: c_out_th - c_in_th = c_out_mech - c_in_mech  ->  c_out_th - c_in_th - c_out_mech + c_in_mech = 0

        A[counter+0, self.inl[0]["CostVar_index"]["CH"]] = 1 / self.inl[0]["e_CH"] if self.inl[0]["e_CH"] != 0 else 1
        A[counter+0, self.outl[0]["CostVar_index"]["CH"]] = -1 / self.outl[0]["e_CH"] if self.outl[0]["e_CH"] != 0 else 1
        equations[counter+0] = f"aux_equality_chem_{self.outl[0]["name"]}"

        dET = self.outl[0]["e_T"] - self.inl[0]["e_T"]
        dEM = self.outl[0]["e_M"] - self.inl[0]["e_M"]

        if self.inl[0]["T"] > T0 and  self.outl[0]["T"] > T0:
            if dET != 0 and dEM != 0:
                A[counter+1, self.inl[0]["CostVar_index"]["T"]] = -1/dET
                A[counter+1, self.outl[0]["CostVar_index"]["T"]] = 1/dET
                A[counter+1, self.inl[0]["CostVar_index"]["M"]] = 1/dEM
                A[counter+1, self.outl[0]["CostVar_index"]["M"]] = -1/dEM
                equations[counter+1] = f"aux_p_rule_{self.name}"
            else:
                logging.warning("case that thermal or mechanical exergy at pump outlet doesn't change is not implemented in exergoeconomics yet")

        elif self.inl[0]["T"] <= T0 and  self.outl[0]["T"] > T0:
            A[counter+1, self.outl[0]["CostVar_index"]["T"]] = 1/self.outl[0]["e_T"]
            A[counter+1, self.inl[0]["CostVar_index"]["M"]] = 1/dEM
            A[counter+1, self.outl[0]["CostVar_index"]["M"]] = -1/dEM
            equations[counter+1] = f"aux_p_rule_{self.name}"

        else:
            A[counter+1, self.inl[0]["CostVar_index"]["T"]] = -1/self.inl[0]["e_T"]
            A[counter+1, self.outl[0]["CostVar_index"]["T"]] = 1/self.outl[0]["e_T"]
            equations[counter+1] = f"aux_f_rule_{self.name}"

        for i in range(2):
            b[counter+i]=0

        return [A, b, counter+2, equations]