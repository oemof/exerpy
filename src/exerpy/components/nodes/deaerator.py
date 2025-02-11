import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry

@component_registry
class Deaerator(Component):
    r"""
    Class for exergy analysis of deaerators.

    This class performs exergy analysis calculations for deaerators with multiple 
    inlet streams and one outlet stream. The exergy product and fuel definitions 
    vary based on the temperature relationships between inlet streams, outlet 
    stream, and ambient conditions.

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
        Dictionary containing inlet streams data with temperature, mass flows,
        and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        and specific exergies.

    Notes
    -----
    The exergy analysis accounts for physical exergy only. The equations for exergy
    product and fuel are defined based on temperature relationships:

    .. math::

        \dot{E}_\mathrm{P} =
        \begin{cases}
        \begin{cases}
        \sum_i \dot{m}_i \cdot (e_\mathrm{out}^\mathrm{PH} -
        e_{\mathrm{in,}i}^\mathrm{PH})
        & T_{\mathrm{in,}i} < T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} \geq T_0 \\
        \sum_i \dot{m}_i \cdot e_\mathrm{out}^\mathrm{PH}
        & T_{\mathrm{in,}i} < T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} < T_0 \\
        \end{cases} & T_\mathrm{out} > T_0\\
        \text{not defined (nan)} & T_\mathrm{out} = T_0\\
        \begin{cases}
        \sum_i \dot{m}_i \cdot e_\mathrm{out}^\mathrm{PH}
        & T_{\mathrm{in,}i} > T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} \geq T_0 \\
        \sum_i \dot{m}_i \cdot (e_\mathrm{out}^\mathrm{PH} -
        e_{\mathrm{in,}i}^\mathrm{PH})
        & T_{\mathrm{in,}i} > T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} < T_0 \\
        \end{cases} & T_\mathrm{out} < T_0\\
        \end{cases}

        \dot{E}_\mathrm{F} =
        \begin{cases}
        \begin{cases}
        \sum_i \dot{m}_i \cdot (e_{\mathrm{in,}i}^\mathrm{PH} -
        e_\mathrm{out}^\mathrm{PH})
        & T_{\mathrm{in,}i} > T_\mathrm{out} \\
        \sum_i \dot{m}_i \cdot e_{\mathrm{in,}i}^\mathrm{PH}
        & T_{\mathrm{in,}i} < T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} < T_0 \\
        \end{cases} & T_\mathrm{out} > T_0\\
        \sum_i \dot{m}_i \cdot e_{\mathrm{in,}i}^\mathrm{PH}
        & T_\mathrm{out} = T_0\\
        \begin{cases}
        \sum_i \dot{m}_i \cdot e_{\mathrm{in,}i}^\mathrm{PH}
        & T_{\mathrm{in,}i} > T_\mathrm{out} \text{ & }
        T_{\mathrm{in,}i} \geq T_0 \\
        \sum_i \dot{m}_i \cdot (e_{\mathrm{in,}i}^\mathrm{PH} -
        e_\mathrm{out}^\mathrm{PH})
        & T_{\mathrm{in,}i} < T_\mathrm{out} \\
        \end{cases} & T_\mathrm{out} < T_0\\
        \end{cases}

        \forall i \in \text{deaerator inlets}
    """

    def __init__(self, **kwargs):
        r"""Initialize deaerator component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float) -> None:
        r"""
        Calculate the exergy balance of the deaerator.

        Performs exergy balance calculations considering the temperature relationships
        between inlet streams, outlet stream, and ambient conditions.

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
        """      
        # Ensure that the component has both inlet and outlet streams
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Deaerator requires at least two inlets and one outlet.")

        self.E_P = 0
        self.E_F = 0

        # Case 1: Outlet temperature is greater than T0
        if self.outl[0]['T'] > T0:
            for _, inlet in self.inl.items():
                if inlet['T'] < self.outl[0]['T']:  # Tin < Tout
                    if inlet['T'] >= T0:  # and Tin >= T0
                        self.E_P += inlet['m'] * (self.outl[0]['e_PH'] - inlet['e_PH'])
                    else:  # and Tin < T0
                        self.E_P += inlet['m'] * self.outl[0]['e_PH']
                        self.E_F += inlet['m'] * inlet['e_PH']
                else:  # Tin > Tout
                    self.E_F += inlet['m'] * (inlet['e_PH'] - self.outl[0]['e_PH'])

        # Case 2: Outlet temperature is equal to T0
        elif self.outl[0]['T'] == T0:
            self.E_P = np.nan
            for _, inlet in self.inl.items():
                self.E_F += inlet['m'] * inlet['e_PH']

        # Case 3: Outlet temperature is less than T0
        else:
            for _, inlet in self.inl.items():
                if inlet['T'] > self.outl[0]['T']:  # Tin > Tout
                    if inlet['T'] >= T0:  # and Tin >= T0
                        self.E_P += inlet['m'] * self.outl[0]['e_PH']
                        self.E_F += inlet['m'] * inlet['e_PH']
                    else:  # and Tin < T0
                        self.E_P += inlet['m'] * (self.outl[0]['e_PH'] - inlet['e_PH'])
                else:  # Tin < Tout
                    self.E_F += inlet['m'] * (inlet['e_PH'] - self.outl[0]['e_PH'])

        # Calculate exergy destruction and efficiency
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Deaerator exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

        # Log the results
        logging.info(
            f"Compressor exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )


    def aux_eqs(self, A, b, counter, T0, equations):
        if self.outl[0]["e_CH"] != 0:
            A[counter+0, self.outl[0]["CostVar_index"]["CH"]] = -1 / self.outl[0]["e_CH"]
            for i, inlet in enumerate(self.outl.values()):
                A[counter+0, inlet["CostVar_index"]["CH"]] = inlet["m"] / (self.outl[0]["m"] * inlet["e_CH"])
        else:
            A[counter+0, self.outl[i]["CostVar_index"]["CH"]] = 1
        equations[counter] = f"aux_mixing_chem_{self.outl[0]["name"]}"

        if self.outl[0]["e_M"] != 0:
            A[counter+1, self.outl[0]["CostVar_index"]["M"]] = -1 / self.outl[0]["e_M"]
            for i, inlet in enumerate(self.outl.values()):
                A[counter+1, inlet["CostVar_index"]["M"]] = inlet["m"] / (self.outl[0]["m"] * inlet["e_M"])
        else:
            A[counter+1, self.outl[i]["CostVar_index"]["M"]] = 1
        equations[counter] = f"aux_mixing_mech_{self.outl[0]["name"]}"

        for i in range(2):
            b[counter+i]=0

        return [A, b, counter+2, equations]