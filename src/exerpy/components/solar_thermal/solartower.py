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

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""Exergoeconomic auxiliary equations are not yet implemented for this component."""
        raise NotImplementedError("Exergoeconomic analysis is not yet implemented for the SolarTower component.")

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""Exergoeconomic balance is not yet implemented for this component."""
        raise NotImplementedError("Exergoeconomic analysis is not yet implemented for the SolarTower component.")
