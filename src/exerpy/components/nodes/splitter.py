import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


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
        # Number of identical parallel branches each modelled outlet represents (1 for an
        # ordinary splitter; >1 when one branch stands in for a field of parallel branches).
        self.num_branches = kwargs.get("num_branches", 1) or 1

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
        # Each modelled outlet represents num_branches identical parallel branches.
        E_out = self.num_branches * sum(outlet.get("m", 0) * outlet.get("e_PH") for outlet in outlet_list)
        self.E_P = np.nan
        self.E_F = np.nan
        self.E_D = E_in - E_out
        self.epsilon = np.nan

        # Log the results.
        logger.info(
            f"Exergy balance of Splitter {self.name} calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the splitter.

        A splitter divides one stream into several of the same state, so every branch leaves at the
        specific cost of the inlet. It converts nothing and gets no cost balance of its own.

        With split physical exergy, for every outlet :math:`j`:

        .. math::

            \frac{\dot{C}^\mathrm{T}_\mathrm{in}}{\dot{E}^\mathrm{T}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{T}_{\mathrm{out},j}}{\dot{E}^\mathrm{T}_{\mathrm{out},j}}
            \qquad
            \frac{\dot{C}^\mathrm{M}_\mathrm{in}}{\dot{E}^\mathrm{M}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{M}_{\mathrm{out},j}}{\dot{E}^\mathrm{M}_{\mathrm{out},j}}

        Without the split, one rule per outlet instead of two:

        .. math::

            \frac{\dot{C}^\mathrm{PH}_\mathrm{in}}{\dot{E}^\mathrm{PH}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{PH}_{\mathrm{out},j}}{\dot{E}^\mathrm{PH}_{\mathrm{out},j}}

        With chemical exergy enabled, either way:

        .. math::

            \frac{\dot{C}^\mathrm{CH}_\mathrm{in}}{\dot{E}^\mathrm{CH}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{CH}_{\mathrm{out},j}}{\dot{E}^\mathrm{CH}_{\mathrm{out},j}}

        A branch that carries no exergy carries no cost either, so its cost variable is set to zero
        rather than equated:

        .. math::

            \dot{C}^{x}_{\mathrm{out},j} = 0
            \qquad \text{for} \qquad \dot{E}^{x}_{\mathrm{out},j} = 0

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
            The updated row index after adding equations.
        equations : list or dict
            Updated structure with equation labels.
        """
        # The single inlet is not necessarily on connector 0: the parsers number the
        # connectors as the model does, so take the connection itself.
        inlet = next(iter(self.inl.values()))

        # Cost equality of the physical exergy for each outlet: c_x_inlet = c_x_outlet,
        # where c_x = C_x / (m * e_x), so we divide by (m * e_x) to equate specific costs.
        labels = ["T", "M"] if split_physical_exergy else ["PH"]
        if chemical_exergy_enabled:
            labels.append("CH")

        for label in labels:
            for outlet in self.outl.values():
                E_in = inlet["m"] * inlet[f"e_{label}"]
                E_out = outlet["m"] * outlet[f"e_{label}"]
                if E_out == 0:
                    # A branch that carries no exergy carries no cost either. Equating specific
                    # costs would leave a cost on it that then leaves the system unaccounted.
                    A[counter, outlet["CostVar_index"][label]] = 1
                else:
                    A[counter, inlet["CostVar_index"][label]] = (1 / E_in) if E_in != 0 else 1
                    A[counter, outlet["CostVar_index"][label]] = -1 / E_out
                equations[counter] = {
                    "kind": "aux_equality",
                    "objects": [self.name, inlet["name"], outlet["name"]],
                    "property": f"c_{label}",
                }
                b[counter] = 0
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
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
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """

        self.C_P = np.nan
        self.C_F = np.nan
        self.c_F = np.nan
        self.c_P = np.nan
        self.C_D = np.nan
        self.r = np.nan
        self.f = np.nan
