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


    def aux_eqs(self, A, b, counter, T0):
        """
        Auxiliary equations for the compressor.
        
        This method adds two rows to the cost matrix A and vector b that enforce:
        1. Equality of the chemical cost per unit exergy between the inlet and outlet,
            i.e. c_in_ch = c_out_ch.
        2. Equality of the changes in thermal and mechanical costs,
            i.e. c_out_th - c_in_th - (c_out_mech - c_in_mech) = 0.
        
        The coefficients are determined using the specific exergy values:
        - For the chemical cost row:
            If the inlet (or outlet) chemical exergy (e_CH) is nonzero, use 1/e_CH;
            otherwise, set the coefficient to 1.
        - For the thermal/mechanical cost row, the treatment depends on the temperature
            levels of inlet and outlet relative to the ambient T0:
            Case 1: If both inlet and outlet temperatures exceed T0, then
                    if Δe_T (outlet e_T minus inlet e_T) and Δe_M (outlet e_M minus inlet e_M) are nonzero:
                        * Set: c_in_th coefficient = -1/Δe_T, c_out_th coefficient = 1/Δe_T,
                                c_in_mech coefficient = 1/Δe_M, c_out_mech coefficient = -1/Δe_M.
                    Otherwise, the case is not implemented.
            Case 2: If the inlet temperature is below T0 and outlet above T0, then
                    set: c_out_th coefficient = 1/(outlet e_T),
                        c_in_mech coefficient = 1/Δe_M, c_out_mech coefficient = -1/Δe_M.
            Case 3: Otherwise (both below ambient), set:
                    c_in_th coefficient = -1/(inlet e_T) and c_out_th coefficient = 1/(outlet e_T).
        
        In all rows, the right-hand side is zero.
        
        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature in SI (K).
        
        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index (counter + 2).
        """
        # --- Chemical cost auxiliary equation ---
        # Enforce: (1/e_CH_in)*c_in_ch - (1/e_CH_out)*c_out_ch = 0.
        in_chem = self.inl[0]["e_CH"]
        out_chem = self.outl[0]["e_CH"]
        if in_chem != 0:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = 1 / in_chem
        else:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = 1
        if out_chem != 0:
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = -1 / out_chem
        else:
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = -1

        # --- Thermal and Mechanical cost auxiliary equation ---
        # Define differences in thermal and mechanical exergy between outlet and inlet.
        dET = self.outl[0]["e_T"] - self.inl[0]["e_T"]
        dEM = self.outl[0]["e_M"] - self.inl[0]["e_M"]

        # Get inlet and outlet temperatures (assumed in SI units).
        Tin = self.inl[0]["T"]
        Tout = self.outl[0]["T"]

        if Tin > T0 and Tout > T0:
            # Case 1: Both temperatures above ambient.
            if dET != 0 and dEM != 0:
                A[counter+1, self.inl[0]["CostVar_index"]["T"]] = -1 / dET
                A[counter+1, self.outl[0]["CostVar_index"]["T"]] = 1 / dET
                A[counter+1, self.inl[0]["CostVar_index"]["M"]] = 1 / dEM
                A[counter+1, self.outl[0]["CostVar_index"]["M"]] = -1 / dEM
            else:
                logging.error("For compressor '%s': thermal or mechanical exergy difference is zero; auxiliary equation not implemented for this case.", self.label)
        elif Tin <= T0 and Tout > T0:
            # Case 2: Inlet below, outlet above ambient.
            if self.outl[0]["e_T"] != 0 and dEM != 0:
                A[counter+1, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["e_T"]
                A[counter+1, self.inl[0]["CostVar_index"]["M"]] = 1 / dEM
                A[counter+1, self.outl[0]["CostVar_index"]["M"]] = -1 / dEM
            else:
                logging.error("For compressor '%s': invalid exergy values in case 2 of auxiliary equation.", self.label)
        else:
            # Case 3: Both temperatures below ambient.
            if self.inl[0]["e_T"] != 0 and self.outl[0]["e_T"] != 0:
                A[counter+1, self.inl[0]["CostVar_index"]["T"]] = -1 / self.inl[0]["e_T"]
                A[counter+1, self.outl[0]["CostVar_index"]["T"]] = 1 / self.outl[0]["e_T"]
            else:
                logging.error("For compressor '%s': invalid thermal exergy values in case 3 of auxiliary equation.", self.label)

        # Set the right-hand side entries to zero.
        b[counter] = 0
        b[counter+1] = 0

        return A, b, counter + 2
