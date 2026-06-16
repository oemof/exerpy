import numpy as np

from exerpy.components.component import Component, component_registry
from exerpy.functions import fluid_property_data
from exerpy.logger import logger

from . import T_SUN


@component_registry
class ParabolicTrough(Component):
    r"""
    Class for exergy analysis of a parabolic trough collector.

    A parabolic trough concentrates incoming solar radiation onto an absorber tube and raises
    the physical exergy of the heat-transfer fluid flowing through it. The fuel is the exergy
    of the incoming solar heat and the product is the physical-exergy increase of the fluid;
    the difference is the exergy destruction. A single modelled branch may stand in for
    ``num_branches`` identical parallel branches, applied as the scaling factor :math:`\beta`.

    All thermal and optical losses of the collector are accounted as exergy destruction
    (:math:`\dot{E}_\mathrm{D}`), not as a separate exergy loss.

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
    Q_Solar : float
        Incoming solar heat input per branch :math:`\dot{Q}_\mathrm{solar}` in :math:`\mathrm{W}`.
    beta : float
        Number of identical parallel branches the modelled branch represents.
    inl : dict
        Inlet connections, including the heat-transfer-fluid stream.
    outl : dict
        Outlet connections, including the heat-transfer-fluid stream.
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the parabolic trough component.

        Parameters
        ----------
        Q_Solar : float, optional
            Incoming solar heat input per branch in :math:`\mathrm{W}`.
        num_branches : float, optional
            Number of identical parallel branches the modelled branch represents (default 1).
        **kwargs : dict
            Arbitrary keyword arguments passed to the parent class.
        """
        super().__init__(**kwargs)
        self.Q_Solar = kwargs.get("Q_Solar")
        if self.Q_Solar is None:
            logger.warning(f"Q_Solar not provided for Parabolic Trough component '{self.name}'.")

        num_branches = kwargs.get("num_branches")
        if num_branches is None:
            logger.warning(f"num_branches not provided for Parabolic Trough component '{self.name}'; assuming 1.")
        self.beta = num_branches or 1

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the parabolic trough.

        Parameters
        ----------
        T0 : float
            Ambient temperature in :math:`\mathrm{K}`.
        p0 : float
            Ambient pressure in :math:`\mathrm{Pa}`.
        split_physical_exergy : bool
            Flag indicating whether physical exergy is split into thermal and mechanical parts.

        Returns
        -------
        None
            The method updates the attributes E_F, E_P, E_D, and epsilon of the component.

        Raises
        ------
        ValueError
            If the component lacks a material inlet/outlet, or no solar heat input is given.

        Notes
        -----
        Solar radiation is converted to exergy with the Petela/Spanner factor
        :math:`\alpha = 1 - \frac{4}{3}\,T_0 / T_\mathrm{sun}`, with
        :math:`T_\mathrm{sun} = 5778\ \mathrm{K}`.

        Without splitting physical exergy:

        - Exergy fuel: the incoming solar heat exergy, scaled by the number of branches,
          :math:`\dot{E}_\mathrm{F} = \beta\,\dot{Q}_\mathrm{solar}\,\alpha`.
        - Exergy product: the physical-exergy increase of the heat-transfer fluid,
          :math:`\dot{E}_\mathrm{P} = \beta\,\dot{m}\,(e^\mathrm{PH}_\mathrm{out} - e^\mathrm{PH}_\mathrm{in})`.

        With split physical exergy (useful output is thermal exergy, as in the
        SimpleHeatExchanger heat-release product):

        - Exergy product: the thermal-exergy gain,
          :math:`\dot{E}_\mathrm{P} = \beta\,\dot{m}\,(e^\mathrm{T}_\mathrm{out} - e^\mathrm{T}_\mathrm{in})`.
        - Exergy fuel: solar heat plus the fluid's mechanical-exergy decrease,
          :math:`\dot{E}_\mathrm{F} = \beta\,\dot{Q}_\mathrm{solar}\,\alpha + \beta\,\dot{m}\,(e^\mathrm{M}_\mathrm{in} - e^\mathrm{M}_\mathrm{out})`.

        In both cases :math:`\dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}` equals the
        true destruction. All thermal and optical losses are accounted as exergy destruction. If
        the fluid is not above ambient temperature (off-design), the fuel and product are NaN.
        """
        # Validate connections exist
        if not hasattr(self, "inl") or not hasattr(self, "outl"):
            msg = f"Parabolic trough {self.name} requires inlet and outlet connections."
            logger.error(msg)
            raise ValueError(msg)

        if self.Q_Solar is None:
            msg = f"Parabolic trough {self.name} has no solar heat input (Q_Solar)."
            logger.error(msg)
            raise ValueError(msg)

        # Pick the heat-transfer-fluid inlet/outlet. Do not assume fixed connection counts or
        # slots: the parser also attaches solar heat connections (an internal heat link and the
        # synthetic boundary connection), which must be skipped here.
        material_inlets = [
            c for c in self.inl.values() if c is not None and c.get("kind", "material") not in ("heat", "power")
        ]
        material_outlets = [
            c for c in self.outl.values() if c is not None and c.get("kind", "material") not in ("heat", "power")
        ]
        if not material_inlets or not material_outlets:
            msg = f"Parabolic trough {self.name} requires at least one material inlet " "and one material outlet."
            logger.error(msg)
            raise ValueError(msg)

        inlet = material_inlets[0]
        outlet = material_outlets[0]

        # Convert the incoming solar heat to exergy with the Petela/Spanner factor, scaled to
        # all branches the modelled branch represents.
        alpha = 1 - (4 / 3) * (T0 / T_SUN)
        self.E_Solar = self.Q_Solar * alpha * self.beta

        if inlet["T"] >= T0 and outlet["T"] >= T0:
            if split_physical_exergy:
                self.E_P = self.beta * outlet["m"] * (outlet["e_T"] - inlet["e_T"])
                self.E_F = self.E_Solar + self.beta * outlet["m"] * (inlet["e_M"] - outlet["e_M"])
            else:
                self.E_P = self.beta * outlet["m"] * (outlet["e_PH"] - inlet["e_PH"])
                self.E_F = self.E_Solar
        else:
            logger.warning(
                f"Parabolic trough {self.name}: fluid not above ambient temperature; "
                "exergy fuel and product set to NaN (off-design not implemented)."
            )
            self.E_P = np.nan
            self.E_F = np.nan

        # Exergy destruction (all thermal and optical losses are counted here).
        if np.isnan(self.E_P):
            self.E_D = self.E_F
        else:
            self.E_D = self.E_F - self.E_P

        # Calculate exergy efficiency.
        self.epsilon = self.calc_epsilon()

        # Write the solar fuel exergy onto the boundary solar heat connection so the
        # system-level E_F accounting can read it (heat connections are created with E=None).
        try:
            for conn in list(self.outl.values()) + list(self.inl.values()):
                if (
                    conn is not None
                    and conn.get("kind") == "heat"
                    and (conn.get("source_component") is None or conn.get("target_component") is None)
                ):
                    conn["E"] = self.E_F
                    conn["E_unit"] = fluid_property_data["heat"]["SI_unit"]
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not write back exergy to connection for Parabolic Trough '{self.name}': {e}")

        # Log the results.
        logger.info(
            f"Parabolic-Trough exergy balance calculated: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""Exergoeconomic auxiliary equations are not yet implemented for this component."""
        raise NotImplementedError("Exergoeconomic analysis is not yet implemented for the ParabolicTrough component.")

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""Exergoeconomic balance is not yet implemented for this component."""
        raise NotImplementedError("Exergoeconomic analysis is not yet implemented for the ParabolicTrough component.")
