import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class CycleCloser(Component):
    r"""
    Component for closing cycles. This component is not considered in exergy analysis, but it is used in exergoeconomic analysis.
    """

    def __init__(self, **kwargs):
        r"""Initialize CycleCloser component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Skip the exergy balance of the cycle closer.

        The cycle closer is part of how the plant is wired, not a piece of equipment: it closes a loop so that
        the model has a defined starting point. It neither converts nor destroys exergy, so its fuel, product,
        destruction and efficiency are all undefined and are set to NaN.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}` (unused).
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}` (unused).
        split_physical_exergy : bool
            Kept for a uniform component interface; the cycle closer carries no material stream
            to split.
        """
        self.E_D = np.nan
        self.E_F = np.nan
        self.E_P = np.nan
        self.E_L = np.nan
        self.epsilon = np.nan

        # Log the results
        logger.info(f"The exergy balance of a CycleCloser {self.name} is skipped.")

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the cycle closer.

        The cycle closer is an artefact of the model, not a piece of equipment: it passes the stream
        on untouched. Every cost variable therefore leaves it at the specific cost at which it
        entered, and the component gets no cost balance of its own.

        With split physical exergy:

        .. math::

            \frac{\dot{C}^\mathrm{T}_\mathrm{in}}{\dot{E}^\mathrm{T}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{T}_\mathrm{out}}{\dot{E}^\mathrm{T}_\mathrm{out}}
            \qquad
            \frac{\dot{C}^\mathrm{M}_\mathrm{in}}{\dot{E}^\mathrm{M}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{M}_\mathrm{out}}{\dot{E}^\mathrm{M}_\mathrm{out}}

        Without the split the stream carries one cost variable for its physical exergy, and the two
        rules collapse into one:

        .. math::

            \frac{\dot{C}^\mathrm{PH}_\mathrm{in}}{\dot{E}^\mathrm{PH}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{PH}_\mathrm{out}}{\dot{E}^\mathrm{PH}_\mathrm{out}}

        Chemical exergy is not considered here: the composition cannot change across a cycle closer,
        so the cost balance of the components around it already carries it.

        Parameters
        ----------
        A : numpy.ndarray
            The current cost matrix.
        b : numpy.ndarray
            The current right-hand-side vector.
        counter : int
            The current row index in the matrix.
        T0 : float
            Ambient temperature (not used in this component).
        equations : list or dict
            Data structure for storing equation labels.
        chemical_exergy_enabled : bool
            Flag indicating whether chemical exergy auxiliary equations should be added.
            This flag is ignored for CycleCloser.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

        Returns
        -------
        A : numpy.ndarray
            The updated cost matrix.
        b : numpy.ndarray
            The updated right-hand-side vector.
        counter : int
            The updated row index (increased by 2).
        equations : list or dict
            Updated structure with equation labels.
        """
        # Cost equality equations of the physical exergy. The coefficients are written on the exergy
        # flow of the stream, not on its specific exergy, as the F-principle requires.
        for label in ["M", "T"] if split_physical_exergy else ["PH"]:
            A[counter, self.inl[0]["CostVar_index"][label]] = (
                (1 / self.inl[0][f"E_{label}"]) if self.inl[0][f"e_{label}"] != 0 else 1
            )
            A[counter, self.outl[0]["CostVar_index"][label]] = (
                (-1 / self.outl[0][f"E_{label}"]) if self.outl[0][f"e_{label}"] != 0 else -1
            )
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": f"c_{label}",
            }
            b[counter] = 0
            counter += 1

        if chemical_exergy_enabled:
            # Chemical cost equality equation:
            A[counter, self.inl[0]["CostVar_index"]["CH"]] = (
                (1 / self.inl[0]["E_CH"]) if self.inl[0]["e_CH"] != 0 else 1
            )
            A[counter, self.outl[0]["CostVar_index"]["CH"]] = (
                (-1 / self.outl[0]["E_CH"]) if self.outl[0]["e_CH"] != 0 else -1
            )
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": "c_CH",
            }
            b[counter] = 0

            counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True) -> None:
        """
        Exergoeconomic balance for the CycleCloser is not defined.

        This component does not generate or consume exergy, so all cost terms are undefined.

        Parameters
        ----------
        T0 : float
            Ambient temperature (unused).
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """
        self.C_F = np.nan
        self.C_P = np.nan
        self.C_D = np.nan
        self.c_TOT = np.nan
        self.C_TOT = np.nan
        self.r = np.nan
        self.f = np.nan
