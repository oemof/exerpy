import logging

import numpy as np

from exerpy.components.component import Component, component_registry


@component_registry
class Splitter(Component):
    r"""
    Class for exergy analysis of splitters.

    This class performs exergy analysis calculations for splitters with one
    inlet stream and multiple outlet stream. For this component, it is not
    reasonable to define exergy fuel and product in the same way as for other components,
    since the splitter does not convert energy from one form to another.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments passed to parent class.

    Attributes
    ----------
    inl : dict
        Dictionary containing inlet streams data with temperature, mass flows,
        and specific exergies.
    outl : dict
        Dictionary containing outlet stream data with temperature, mass flows,
        and specific exergies.

    """

    def __init__(self, **kwargs):
        r"""Initialize splitter component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the splitter.

        Performs exergy balance calculations.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical components.

        Raises
        ------
        ValueError
            If the required inlet and outlet streams are not properly defined.
        """
        # Ensure that the component has at least two inlets and one outlet.
        if len(self.inl) < 1 or len(self.outl) < 2:
            raise ValueError("Splitter requires at least one inlet and two outlets.")
        outlet_list = list(self.outl.values())
        inlet_list = list(self.inl.values())
        E_in = sum(inlet.get("m", 0) * inlet.get("e_PH") for inlet in inlet_list)
        E_out = sum(outlet.get("m", 0) * outlet.get("e_PH") for outlet in outlet_list)
        self.E_P = np.nan
        self.E_F = np.nan
        self.E_D = E_in - E_out
        self.epsilon = np.nan

        # Log the results.
        logging.info(
            f"Exergy balance of Splitter {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        """
        Auxiliary equations for the splitter.

        This function adds rows to the cost matrix A and the right-hand-side vector b to enforce
        equality of specific exergy costs between the single inlet stream and each outlet stream.
        Thermal and mechanical costs are always equated; chemical costs are equated only if enabled.

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature (not used).
        equations : list or dict
            Data structure for storing equation labels.
        chemical_exergy_enabled : bool
            Flag indicating whether chemical exergy auxiliary equations should be added.

        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index after adding equations.
        equations : list or dict
            Updated structure with equation labels.
        """
        inlet = self.inl[0]

        # Thermal cost equality for each outlet
        for outlet in self.outl.values():
            A[counter, inlet["CostVar_index"]["T"]] = (1 / inlet["e_T"]) if inlet["e_T"] != 0 else 1
            A[counter, outlet["CostVar_index"]["T"]] = (-1 / outlet["e_T"]) if outlet["e_T"] != 0 else -1
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": "c_T",
            }
            b[counter] = 0
            counter += 1

        # Mechanical cost equality for each outlet
        for outlet in self.outl.values():
            A[counter, inlet["CostVar_index"]["M"]] = (1 / inlet["e_M"]) if inlet["e_M"] != 0 else 1
            A[counter, outlet["CostVar_index"]["M"]] = (-1 / outlet["e_M"]) if outlet["e_M"] != 0 else -1
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": "c_M",
            }
            b[counter] = 0
            counter += 1

        # Chemical cost equality for each outlet (if enabled)
        if chemical_exergy_enabled:
            for outlet in self.outl.values():
                A[counter, inlet["CostVar_index"]["CH"]] = (1 / inlet["e_CH"]) if inlet["e_CH"] != 0 else 1
                A[counter, outlet["CostVar_index"]["CH"]] = (-1 / outlet["e_CH"]) if outlet["e_CH"] != 0 else -1
                equations[counter] = {
                    "kind": "aux_equality",
                    "objects": [self.name, inlet["name"], outlet["name"]],
                    "property": "c_CH",
                }
                b[counter] = 0
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        """
        The exergoeconomic balance for the Splitter component is not neglected,
        as it does not perform any conversion of energy forms.
        Instead, it is assumed that the specific costs of the inlet and outlet streams are equal.


        Parameters
        ----------
        T0 : float
            Ambient temperature
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        """

        self.C_P = np.nan
        self.C_F = np.nan
        self.c_F = np.nan
        self.c_P = np.nan
        self.C_D = np.nan
        self.r = np.nan
        self.f = np.nan
