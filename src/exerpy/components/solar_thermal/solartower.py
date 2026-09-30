import numpy as np

from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.logger import logger

from . import T_SUN


@component_registry
class SolarTower(Component):
    r"""
    Class for exergy analysis of Solar Tower.

    The component has a working-fluid inlet and outlet plus a heat connection that carries
    the solar heat input. The fuel is the supplied solar heat exergy and the product is the
    physical exergy gained by the working fluid.

    All thermal losses are accounted as exergy destruction (:math:`\dot{E}_\mathrm{D}`), not
    as a separate exergy loss.

    Attributes
    ----------
    E_F : float
        Exergy fuel of the component :math:`\dot{E}_\mathrm{F}` in :math:`\mathrm{W}`.
    E_P : float
        Exergy product of the component :math:`\dot{E}_\mathrm{P}` in :math:`\mathrm{W}`.
    E_D : float
        Exergy destruction of the component :math:`\dot{E}_\mathrm{D}` in :math:`\mathrm{W}`.
    epsilon : float
        Exergetic efficiency of the component :math:`\varepsilon` in :math:`-`.
    inl : dict
        Inlet connections: the working-fluid stream and the heat connection that carries
        the solar heat input (the latter has no mass flow).
    outl : dict
        Outlet connection: the working-fluid stream.
    """

    def __init__(self, **kwargs):
        r"""
        Initializes the SolarTower component.
        """
        super().__init__(**kwargs)
        self.F = None

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Method to calculate the exergy balance of the Solar Tower component.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag to indicate whether to split physical exergy into thermal and mechanical parts.

        Returns
        -------
        None
            The method updates the attributes E_F, E_P, E_D, and epsilon of the component instance.

        Raises
        ------
        ValueError
            If there is no outlet, more than one outlet, or no valid solar heat input.

        Notes
        -----
        Without splitting physical exergy:

        - Exergy fuel: the supplied solar heat exergy,
          :math:`\dot{E}_\mathrm{F} = |\dot{E}_\mathrm{heat}|`.
        - Exergy product: the physical-exergy gain of the working fluid,
          :math:`\dot{E}_\mathrm{P} = \dot{m}\,(e^\mathrm{PH}_\mathrm{out} - e^\mathrm{PH}_\mathrm{in})`.

        With split physical exergy (the receiver's useful output is thermal exergy, as in the
        SimpleHeatExchanger heat-release product):

        - Exergy product: the thermal-exergy gain,
          :math:`\dot{E}_\mathrm{P} = \dot{m}\,(e^\mathrm{T}_\mathrm{out} - e^\mathrm{T}_\mathrm{in})`.
        - Exergy fuel: solar heat plus the fluid's mechanical-exergy decrease,
          :math:`\dot{E}_\mathrm{F} = |\dot{E}_\mathrm{heat}| + \dot{m}\,(e^\mathrm{M}_\mathrm{in} - e^\mathrm{M}_\mathrm{out})`.

        In both cases :math:`\dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}` equals the
        true destruction and :math:`\varepsilon = \dot{E}_\mathrm{P} / \dot{E}_\mathrm{F}`.
        """
        # Validate the number of inlets and outlets
        if not hasattr(self, "inl") or not hasattr(self, "outl") or len(self.outl) != 1:
            msg = "SolarTower requires at least one inlet and exactly one outlet."
            logger.error(msg)
            raise ValueError(msg)

        if len(self.inl) < 1:
            msg = "SolarTower requires at least one inlet stream."
            logger.error(msg)
            raise ValueError(msg)

        # Extract inlet and outlet streams
        inlet = self.inl[0]
        outlet = self.outl[0]

        # Solar heat input: the heat-kind inlet connection (selected by kind, not a fixed
        # slot, so the result does not depend on component-evaluation order). If it already
        # carries an exergy value (written by an upstream heliostat field) use it directly;
        # otherwise convert its raw heat flow with the Petela/Spanner factor.
        heat_inlets = [c for c in self.inl.values() if c is not None and c.get("kind") == "heat"]
        if not heat_inlets:
            msg = f"SolarTower {self.name} has no solar heat input connection."
            logger.error(msg)
            raise ValueError(msg)
        heat_in = heat_inlets[0]
        if heat_in.get("E") is not None:
            self.F = heat_in["E"]
        elif heat_in.get("energy_flow") is not None:
            self.F = heat_in["energy_flow"] * (1 - (4 / 3) * (T0 / T_SUN))
        else:
            msg = f"SolarTower {self.name} has no valid solar heat input."
            logger.error(msg)
            raise ValueError(msg)

        # The receiver's useful output is the THERMAL exergy delivered to the working fluid
        # (as in the SimpleHeatExchanger heat-release product). With split physical exergy the
        # product is the thermal-exergy gain; the fluid's mechanical-exergy decrease (pressure
        # drop) is booked into the fuel, so E_D = E_F - E_P stays the true destruction.
        if split_physical_exergy:
            self.E_P = outlet["m"] * (outlet["e_T"] - inlet["e_T"])
            self.E_F = abs(self.F) + outlet["m"] * (inlet["e_M"] - outlet["e_M"])
        else:
            self.E_P = outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
            self.E_F = abs(self.F)

        # Calculate exergetic efficiency
        self.epsilon = self.calc_epsilon()

        # Calculate exergy destruction
        if not np.isnan(self.E_P):
            self.E_D = self.E_F - self.E_P
        else:
            self.E_D = self.E_F

        # Log the results
        logger.info(
            f"Solar Tower exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def _fluid_streams(self):
        """Return the working-fluid inlet and outlet, skipping the solar heat connections."""
        material_inlets = [
            c for c in self.inl.values() if c is not None and c.get("kind", "material") not in ("heat", "power")
        ]
        material_outlets = [
            c for c in self.outl.values() if c is not None and c.get("kind", "material") not in ("heat", "power")
        ]
        if not material_inlets or not material_outlets:
            msg = f"{self.__class__.__name__} {self.name} has no working-fluid inlet and outlet."
            logger.error(msg)
            raise ValueError(msg)
        return material_inlets[0], material_outlets[0]

    def _solar_cost(self):
        """Return the cost rate of the solar heat entering the component."""
        heat_inlets = [c for c in self.inl.values() if c is not None and c.get("kind") == "heat"]
        if not heat_inlets:
            msg = (
                f"{self.__class__.__name__} {self.name} has no solar heat inlet connection, so its "
                f"cost cannot be determined."
            )
            logger.error(msg)
            raise ValueError(msg)
        return heat_inlets[0].get("C_TOT", 0.0)

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        r"""
        Auxiliary equations for the solar tower.

        The component absorbs solar heat, so the thermal exergy the working fluid gains is its
        product and the cost balance alone determines it. What the fluid does not gain passes
        through at its own specific cost (F-principle).

        With split physical exergy the fluid loses pressure, so its mechanical exergy is part of the
        fuel and needs the rule:

        .. math::

            \frac{\dot{C}^\mathrm{M}_\mathrm{in}}{\dot{E}^\mathrm{M}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{M}_\mathrm{out}}{\dot{E}^\mathrm{M}_\mathrm{out}}

        Without the split the fluid carries a single cost variable for its physical exergy, that
        variable is the product, and **no auxiliary equation is written**; the cost balance fixes it:

        .. math::

            \dot{C}^\mathrm{PH}_\mathrm{out}
            = \dot{C}^\mathrm{PH}_\mathrm{in} + \dot{C}^\mathrm{TOT}_\mathrm{solar} + \dot{Z}

        With chemical exergy enabled, either way, the composition does not change:

        .. math::

            \frac{\dot{C}^\mathrm{CH}_\mathrm{in}}{\dot{E}^\mathrm{CH}_\mathrm{in}}
            = \frac{\dot{C}^\mathrm{CH}_\mathrm{out}}{\dot{E}^\mathrm{CH}_\mathrm{out}}

        Parameters
        ----------
        A : numpy.ndarray
            Coefficient matrix of the cost equation system.
        b : numpy.ndarray
            Right-hand side vector of the cost equation system.
        counter : int
            Index of the next free row.
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        equations : dict
            Dictionary documenting the equations.
        chemical_exergy_enabled : bool
            Whether chemical exergy is part of the analysis.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.

        Returns
        -------
        tuple
            The updated matrix, vector, row index and equation dictionary.
        """
        inlet, outlet = self._fluid_streams()

        if split_physical_exergy:
            A[counter, inlet["CostVar_index"]["M"]] = 1 / inlet["E_M"] if inlet["e_M"] != 0 else 1
            A[counter, outlet["CostVar_index"]["M"]] = -1 / outlet["E_M"] if outlet["e_M"] != 0 else -1
            equations[counter] = {
                "kind": "aux_f_rule",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": "c_M",
            }
            b[counter] = 0
            counter += 1

        if chemical_exergy_enabled:
            A[counter, inlet["CostVar_index"]["CH"]] = 1 / inlet["E_CH"] if inlet["e_CH"] != 0 else 1
            A[counter, outlet["CostVar_index"]["CH"]] = -1 / outlet["E_CH"] if outlet["e_CH"] != 0 else -1
            equations[counter] = {
                "kind": "aux_f_rule",
                "objects": [self.name, inlet["name"], outlet["name"]],
                "property": "c_CH",
            }
            b[counter] = 0
            counter += 1

        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        r"""
        Perform the exergoeconomic cost balance of the solar tower.

        Fuel and product follow :meth:`calc_exergy_balance`: the product is the thermal (with
        split physical exergy) or physical exergy gain of the working fluid, the fuel is the
        solar heat plus, with the split, the mechanical exergy the fluid loses over the
        pressure drop.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        chemical_exergy_enabled : bool, optional
            If True, chemical exergy is considered in the calculations.
        split_physical_exergy : bool, optional
            If True, the physical exergy of a material stream is split into a thermal and a
            mechanical share, each with its own cost variable. If False, the stream carries a
            single cost variable for its physical exergy. Default is True.
        """
        inlet, outlet = self._fluid_streams()
        C_solar = self._solar_cost()

        if split_physical_exergy:
            self.C_P = outlet["C_T"] - inlet["C_T"]
            self.C_F = C_solar + (inlet["C_M"] - outlet["C_M"])
        else:
            self.C_P = outlet["C_PH"] - inlet["C_PH"]
            self.C_F = C_solar

        self.c_F = self.C_F / self.E_F if self.E_F else np.nan
        self.c_P = self.C_P / self.E_P if self.E_P else np.nan
        self.C_D = self.c_F * self.E_D
        self.r = (self.c_P - self.c_F) / self.c_F if self.c_F else np.nan
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) else np.nan
