import logging

import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry


@component_registry
class Mixer(Component):
    r"""
    Class for exergy analysis of mixers.

    This class performs exergy analysis calculations for mixers with multiple
    inlet streams and generally one outlet stream (multiple outlets are possible). 
    The exergy product and fuel definitions vary based on the temperature 
    relationships between inlet streams, outlet streams, and ambient conditions.

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

        \forall i \in \text{mixer inlets}
    """

    def __init__(self, **kwargs):
        r"""Initialize mixer component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the mixer.

        Performs exergy balance calculations considering the temperature relationships
        between inlet streams, outlet stream(s), and ambient conditions.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\text{K}`.
        p0 : float
            Ambient pressure in :math:`\text{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined.
        """
        # Ensure that the component has at least two inlets and one outlet.
        if len(self.inl) < 2 or len(self.outl) < 1:
            raise ValueError("Mixer requires at least two inlets and one outlet.")
        
        # Compute effective outlet state by aggregating all outlet streams.
        # Assume that all outlets share the same thermodynamic state.
        outlet_list = list(self.outl.values())
        first_outlet = outlet_list[0]
        T_out = first_outlet['T']
        e_out_PH = first_outlet['e_PH']
        # Verify that all outlets have the same thermodynamic state.
        for outlet in outlet_list:
            if outlet['T'] != T_out or outlet['e_PH'] != e_out_PH:
                msg = "All outlets in Mixer must have the same thermodynamic state."
                logging.error(msg)
                raise ValueError(msg)
        # Sum the mass of all outlet streams (if needed for further analysis)
        m_out_total = sum(outlet.get('m', 0) for outlet in outlet_list)
        
        # Initialize exergy product and fuel.
        self.E_P = 0
        self.E_F = 0

        # Case 1: Outlet temperature is greater than ambient.
        if T_out > T0:
            for _, inlet in self.inl.items():
                # Case when inlet temperature is lower than outlet temperature.
                if inlet['T'] < T_out:
                    if inlet['T'] >= T0:
                        # Contribution to exergy product from inlets above ambient.
                        self.E_P += inlet['m'] * (e_out_PH - inlet['e_PH'])
                    else:  # inlet['T'] < T0
                        self.E_P += inlet['m'] * e_out_PH
                        self.E_F += inlet['m'] * inlet['e_PH']
                else:  # inlet['T'] > T_out
                    self.E_F += inlet['m'] * (inlet['e_PH'] - e_out_PH)
        
        # Case 2: Outlet temperature equals ambient.
        elif T_out == T0:
            self.E_P = np.nan
            for _, inlet in self.inl.items():
                self.E_F += inlet['m'] * inlet['e_PH']
        
        # Case 3: Outlet temperature is less than ambient.
        else:  # T_out < T0
            for _, inlet in self.inl.items():
                if inlet['T'] > T_out:
                    if inlet['T'] >= T0:
                        self.E_P += inlet['m'] * e_out_PH
                        self.E_F += inlet['m'] * inlet['e_PH']
                    else:  # inlet['T'] < T0
                        self.E_P += inlet['m'] * (e_out_PH - inlet['e_PH'])
                else:  # inlet['T'] <= T_out
                    self.E_F += inlet['m'] * (inlet['e_PH'] - e_out_PH)
        
        # Calculate exergy destruction and efficiency.
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()
        
        # Log the results.
        logging.info(
            f"Mixer exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
    )