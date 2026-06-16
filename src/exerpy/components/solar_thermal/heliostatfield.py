import logging

import numpy as np

from exerpy.components.component import Component, component_registry
from exerpy.functions import fluid_property_data

from . import T_SUN


@component_registry
class Heliostatfield(Component):
    r"""
    Class for exergy analysis of a heliostat field.

    The heliostat field concentrates incoming solar radiation and delivers heat to the
    central receiver. The fuel is the exergy of the incoming solar heat and the product is
    the exergy of the heat effectively delivered to the receiver; their difference is the
    optical loss of the field. Radiation is converted to exergy with the Petela/Spanner factor
    :math:`\alpha = 1 - \frac{4}{3}\,T_0 / T_\mathrm{sun}`.

    All thermal and optical losses are accounted as exergy destruction
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
        Incoming solar heat input :math:`\dot{Q}_\mathrm{solar}` in :math:`\mathrm{W}`.
    P : float
        Effective heat delivered to the receiver :math:`\dot{Q}_\mathrm{eff}` in :math:`\mathrm{W}`.
    inl : dict
        Inlet connections (a heliostat field has no material inlet).
    outl : dict
        Heat outlet connections: the heat delivered to the receiver and the incoming solar
        heat (both carry heat, no mass flow).
    """

    def __init__(self, **kwargs):
        r"""
        Initialize the heliostat field component.

        Parameters
        ----------
        Q_Solar : float, optional
            Incoming solar heat input in :math:`\mathrm{W}`.
        **kwargs : dict
            Arbitrary keyword arguments passed to the parent class.
        """
        super().__init__(**kwargs)
        self.Q_Solar = kwargs.get("Q_Solar")
        self.P = None

    def calc_exergy_balance(self, T0: float, p0: float, split_physical_exergy) -> None:
        r"""
        Calculate the exergy balance of the heliostat field.

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
            The method updates the attributes E_F, E_P, E_D, and epsilon of the component instance.

        Raises
        ------
        ValueError
            If the component has no outlet connections attribute, or no valid heat output to
            the receiver.

        Notes
        -----
        Solar radiation is converted to exergy with the Petela/Spanner factor
        :math:`\alpha = 1 - \frac{4}{3}\,T_0 / T_\mathrm{sun}`, with
        :math:`T_\mathrm{sun} = 5778\ \mathrm{K}`.

        - Exergy fuel: the incoming solar heat exergy,
          :math:`\dot{E}_\mathrm{F} = \dot{Q}_\mathrm{solar}\,\alpha`.
        - Exergy product: the exergy of the heat delivered to the receiver,
          :math:`\dot{E}_\mathrm{P} = \dot{Q}_\mathrm{eff}\,\alpha`.
        - Exergy destruction: :math:`\dot{E}_\mathrm{D} = \dot{E}_\mathrm{F} - \dot{E}_\mathrm{P}`.
        - Exergetic efficiency: :math:`\varepsilon = \dot{E}_\mathrm{P} / \dot{E}_\mathrm{F}`.

        If the field has no outlet connections, all exergy values are set to zero and epsilon
        to NaN.
        """
        # Validate the number of inlets and outlets
        if not hasattr(self, "outl"):
            msg = f"Heliostat field {self.name} requires outlet connections."
            logging.error(msg)
            raise ValueError(msg)

        # The heliostat field has heat outlet connection(s) only (the link to the receiver
        # and the synthetic solar heat-flux connection) and no material inlet.
        if len(self.outl) == 0:
            logging.warning(f"Heliostat Field '{self.name}' has no outlet connections.")
            self.E_F = 0
            self.E_P = 0
            self.E_D = 0
            self.epsilon = np.nan
            return

        # Extract inlet and outlet streams
        # Normalize placeholder zeros to None for safety (some parsers use 0 as placeholder)
        if hasattr(self, "inl") and 0 in self.inl and self.inl[0] == 0:
            self.inl[0] = None
        if hasattr(self, "outl") and 0 in self.outl and self.outl[0] == 0:
            self.outl[0] = None

        # Effective heat delivered to the receiver is the internal heat outlet (outl[0]); use
        # its raw heat flow (the Petela/Spanner factor is applied below).
        if 0 in self.outl and self.outl[0] is not None and self.outl[0].get("kind") == "heat":
            out0 = self.outl[0]
            self.P = out0.get("energy_flow") if out0.get("energy_flow") is not None else out0.get("E")
        if self.P is None:
            msg = f"Heliostat field {self.name} has no valid heat output on its receiver link."
            logging.error(msg)
            raise ValueError(msg)
        if self.Q_Solar is None:
            msg = f"Heliostat field {self.name} has no solar heat input (Q_Solar)."
            logging.error(msg)
            raise ValueError(msg)

        # Convert the incoming solar heat to exergy with the Petela/Spanner factor.
        alpha = 1 - (4 / 3) * (T0 / T_SUN)

        # Calculate exergy of incoming Heat
        self.E_F = self.Q_Solar * alpha  # Total incoming solar exergy
        # Calculate exergy of effective Heat
        # Use 'energy_flow' key for heat connections from the parser
        self.E_P = self.P * alpha  # Exergy of effective heat output
        # Calculate exergy destruction
        self.E_D = self.E_F - self.E_P

        # Write the computed exergy flows back onto the heat connections so that the rest
        # of the pipeline and the system-level E_F/E_P accounting can read them. Heat
        # connections are created with E=None, so without this the solar heat carries no
        # exergy and the system fuel would be zero.
        #
        # The incoming solar heat is modelled as a boundary heat connection (one side has
        # no component), while the heat delivered to the receiver is an internal connection
        # (both sides connected). Classify by topology rather than by inlet/outlet slot,
        # because the synthetic solar connection is stored as an outlet here.
        #   - boundary solar heat connection -> fuel exergy E_F
        #   - internal heat connection (to receiver) -> product exergy E_P
        try:
            for conn in list(self.outl.values()) + list(self.inl.values()):
                if conn is None or conn.get("kind") != "heat":
                    continue
                if conn.get("source_component") is None or conn.get("target_component") is None:
                    conn["E"] = self.E_F
                else:
                    conn["E"] = self.E_P
                conn["E_unit"] = fluid_property_data["heat"]["SI_unit"]
        except (KeyError, TypeError) as e:
            logging.warning(f"Could not write back exergy to connection for Heliostat '{self.name}': {e}")

        # Calculate exergy efficiency
        self.epsilon = self.calc_epsilon()

        # Log the results
        logging.info(
            f"Heliostat Field Exergy Balance: "
            f"E_P={self.E_P:.2f}, E_F={self.E_F:.2f}, E_D={self.E_D:.2f}, "
            f"Efficiency={self.epsilon:.2%}"
        )

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled):
        r"""Exergoeconomic auxiliary equations are not yet implemented for this component."""
        raise NotImplementedError("Exergoeconomic analysis is not yet implemented for the Heliostatfield component.")

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False):
        r"""Exergoeconomic balance is not yet implemented for this component."""
        raise NotImplementedError("Exergoeconomic analysis is not yet implemented for the Heliostatfield component.")
