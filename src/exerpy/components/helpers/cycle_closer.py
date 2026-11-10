import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.components.component import set_equal_specific_cost
from exerpy.components.heat_exchanger.base import HeatExchanger
from exerpy.logger import logger


@component_registry
class CycleCloser(Component):
    r"""
    Component for closing cycles. This component is not considered in exergy analysis, but it is used in exergoeconomic analysis.
    """

    def __init__(self, **kwargs):
        r"""Initialize CycleCloser component with given parameters."""
        super().__init__(**kwargs)
        self.closed_cycle = True

    def is_closed_cycle(self, components):
        """
        Check that no stream enters the cycle of the closer from outside.

        The fluid is followed downstream from the outlet of the closer. A heat exchanger passes each
        inlet on to the outlet on the same connector, every other component to all of its outlets. The
        cycle is open if a component on it takes in a stream that is not part of the cycle but passes
        on into it. A walk that does not come back to the closer counts as closed.

        Parameters
        ----------
        components : dict
            All components of the plant, by name.

        Returns
        -------
        bool
            False if a stream from outside the cycle enters it.
        """

        def material(streams):
            return {key: conn for key, conn in streams.items() if conn and conn.get("kind", "material") == "material"}

        def downstream(comp, connector):
            # The outlets that the fluid entering on this connector leaves by
            if connector not in material(comp.inl):
                return []
            outlets = material(comp.outl)
            if isinstance(comp, HeatExchanger):
                return [outlets[connector]] if connector in outlets else []
            return list(outlets.values())

        reached = {}
        todo = list(material(self.outl).values())
        while todo:
            conn = todo.pop()
            if id(conn) in reached:
                continue
            reached[id(conn)] = conn
            target = components.get(conn.get("target_component"))
            if target is not None and target is not self:
                todo += downstream(target, conn.get("target_connector"))

        if not any(id(conn) in reached for conn in self.inl.values()):
            return True
        for conn in reached.values():
            comp = components.get(conn.get("target_component"))
            if comp is None or comp is self:
                continue
            for connector, inlet in material(comp.inl).items():
                if id(inlet) not in reached and any(id(out) in reached for out in downstream(comp, connector)):
                    return False
        return True

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

        The composition of a closed cycle does not change, so its chemical exergy is neither fuel nor
        product of any component, and the rules around the cycle leave the level of its cost open. The
        cycle closer sets it to zero:

        .. math::

            \dot{C}^\mathrm{CH}_\mathrm{out} = 0

        When a stream enters the cycle from outside (see :meth:`is_closed_cycle`), such as make-up
        water, that stream sets the chemical cost, and it passes the closer unchanged:

        .. math::

            \frac{\dot{C}^\mathrm{CH}_\mathrm{in}}{\dot{E}^\mathrm{CH}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{CH}_\mathrm{out}}{\dot{E}^\mathrm{CH}_\mathrm{out}}

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
            set_equal_specific_cost(A, counter, self.inl[0], self.outl[0], label)
            equations[counter] = {
                "kind": "aux_equality",
                "objects": [self.name, self.inl[0]["name"], self.outl[0]["name"]],
                "property": f"c_{label}",
            }
            b[counter] = 0
            counter += 1

        if chemical_exergy_enabled:
            inlet, outlet = self.inl[0], self.outl[0]
            if self.closed_cycle or not inlet.get("E_CH") or not outlet.get("E_CH"):
                # Nothing else sets the chemical cost of a closed cycle; without chemical exergy there is none.
                A[counter, outlet["CostVar_index"]["CH"]] = 1
                equations[counter] = {"kind": "aux_zero", "objects": [self.name, outlet["name"]], "property": "C_CH"}
            else:
                A[counter, inlet["CostVar_index"]["CH"]] = 1 / inlet["E_CH"]
                A[counter, outlet["CostVar_index"]["CH"]] = -1 / outlet["E_CH"]
                equations[counter] = {
                    "kind": "aux_equality",
                    "objects": [self.name, inlet["name"], outlet["name"]],
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
