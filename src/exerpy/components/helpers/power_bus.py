import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger


@component_registry
class PowerBus(Component):
    r"""
    Component for power busses. This component is not considered in exergy analysis, but it is used in exergoeconomic analysis.
    """

    def __init__(self, **kwargs):
        r"""Initialize CycleCloser component with given parameters."""
        super().__init__(**kwargs)

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Skip the exergy balance of the power bus.

        The power bus is part of how the plant is wired, not a piece of equipment: it gathers power and hands
        it on. It neither converts nor destroys exergy, so its fuel, product, destruction and efficiency are
        all undefined and are set to NaN.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}` (unused).
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}` (unused).
        split_physical_exergy : bool
            Kept for a uniform component interface; the power bus carries no material stream
            to split.
        """
        self.E_D = np.nan
        self.E_F = np.nan
        self.E_P = np.nan
        self.E_L = np.nan
        self.epsilon = np.nan

        # Log the results
        logger.info(f"The exergy balance of a PowerBus {self.name} is skipped.")

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the power bus.

        A power bus gathers power and hands it on. It carries power streams only, one cost variable
        each, so the split of the physical exergy and the chemical exergy do not apply to it. It
        gets no cost balance row from the analysis, so it writes whatever it needs here, and what it
        needs depends on how it is wired.

        **One outlet.** The bus writes its own cost balance, which determines that outlet:

        .. math::

            \sum_{i} \dot{C}^\mathrm{TOT}_{\mathrm{out},i}
            = \sum_{i} \dot{C}^\mathrm{TOT}_{\mathrm{in},i}

        **One inlet, several outlets.** The power leaving is the same power that entered, so every
        outlet is priced like the inlet:

        .. math::

            \frac{\dot{C}^\mathrm{TOT}_\mathrm{in}}{\dot{E}^\mathrm{TOT}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{TOT}_{\mathrm{out},j}}{\dot{E}^\mathrm{TOT}_{\mathrm{out},j}}

        **Several inlets and several outlets.** The bus writes its cost balance and, on top of it,
        prices every outlet alike, against the first of them as a reference:

        .. math::

            \frac{\dot{C}^\mathrm{TOT}_\mathrm{ref}}{\dot{E}^\mathrm{TOT}_\mathrm{ref}}
            = \frac{\dot{C}^\mathrm{TOT}_{\mathrm{out},j}}{\dot{E}^\mathrm{TOT}_{\mathrm{out},j}}

        **No outlet.** Nothing is written.

        A bus has no investment cost of its own: it is a way of wiring the model, not a piece of
        equipment, so :math:`\dot{Z}` does not appear above and a cost given for one is rejected.

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

        # One outlet: the cost balance of the bus determines it. The PowerBus gets no cost
        # balance row of its own in the matrix, so it is written here.
        if len(self.outl) == 1:
            logger.info(f"PowerBus {self.name} has one output, adding its cost balance.")
            for inl in self.inl.values():
                A[counter, inl["CostVar_index"]["exergy"]] = 1
            for out in self.outl.values():
                A[counter, out["CostVar_index"]["exergy"]] = -1
            equations[counter] = {
                "kind": "cost_balance",
                "objects": [self.name],
                "property": "c_TOT",
            }
            b[counter] = 0
            counter += 1

        elif len(self.outl) == 0:
            logger.info(f"PowerBus {self.name} has no output, no auxiliary equations added.")

        # Mixer case
        elif len(self.inl) == 1 and len(self.outl) > 1:
            logger.info(f"PowerBus {self.name} has multiple outputs, auxiliary equations will be added.")
            # The single inlet is not necessarily on connector 0: the parsers number the
            # connectors as the model does, so take the connection itself.
            inlet = next(iter(self.inl.values()))
            for out in list(self.outl.values())[:]:
                A[counter, inlet["CostVar_index"]["exergy"]] = (1 / inlet["E"]) if inlet["E"] != 0 else 1
                A[counter, out["CostVar_index"]["exergy"]] = (-1 / out["E"]) if out["E"] != 0 else -1
                equations[counter] = {
                    "kind": "aux_power_eq",
                    "objects": [self.name, inlet["name"], out["name"]],
                    "property": "c_TOT",
                }
                b[counter] = 0
                counter += 1

        # General case with multiple inputs and outputs
        elif len(self.inl) > 1 and len(self.outl) > 1:
            logger.info(
                f"PowerBus {self.name} has multiple inputs and outputs, "
                f"adding cost balance and outlet equality equations."
            )

            # Cost balance equation: sum(C_in) - sum(C_out) = 0  (Z = 0 for PowerBus)
            for inl in self.inl.values():
                A[counter, inl["CostVar_index"]["exergy"]] = 1
            for out in self.outl.values():
                A[counter, out["CostVar_index"]["exergy"]] = -1
            equations[counter] = {
                "kind": "cost_balance",
                "objects": [self.name],
                "property": "c_TOT",
            }
            b[counter] = 0
            counter += 1

            # Equalize specific costs of all outlets: c_ref = c_out_i
            outlet_list = list(self.outl.values())
            ref_out = outlet_list[0]
            for out in outlet_list[1:]:
                A[counter, ref_out["CostVar_index"]["exergy"]] = (1 / ref_out["E"]) if ref_out["E"] != 0 else 1
                A[counter, out["CostVar_index"]["exergy"]] = (-1 / out["E"]) if out["E"] != 0 else -1
                equations[counter] = {
                    "kind": "aux_power_eq",
                    "objects": [self.name, ref_out["name"], out["name"]],
                    "property": "c_TOT",
                }
                b[counter] = 0
                counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True) -> None:
        """
        Exergoeconomic balance for the PowerBus is not defined.

        This component does not convert or destroy exergy, so all cost terms are undefined.

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
