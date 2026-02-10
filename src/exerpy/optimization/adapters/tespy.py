"""
TESPy adapter for the optimization framework.

This module provides the TESPyAdapter class that allows the ExergoeconomicOptimizer
to interact with TESPy simulation models.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .base import SimulatorAdapter

if TYPE_CHECKING:
    from tespy.networks import Network

    from ..variables import VariableSpec

logger = logging.getLogger(__name__)


class TESPyAdapter(SimulatorAdapter):
    """
    Adapter for TESPy (Thermal Engineering Systems in Python) models.

    This adapter wraps a TESPy Network object and provides the interface
    required by the ExergoeconomicOptimizer.

    Parameters
    ----------
    network : tespy.networks.Network
        The TESPy network to optimize.
    Tamb : float
        Ambient temperature in K for exergy calculations.
    pamb : float
        Ambient pressure in Pa for exergy calculations.

    Examples
    --------
    >>> from tespy.networks import Network
    >>> nw = Network(...)  # Build your TESPy model
    >>> adapter = TESPyAdapter(nw, Tamb=298.15, pamb=101325)
    >>> adapter.solve()
    True
    """

    name = "TESPy"

    def __init__(self, network: Network, Tamb: float, pamb: float):
        super().__init__(network)
        self.Tamb = Tamb
        self.pamb = pamb

        # Build lookup dictionaries for faster access
        self._connections: dict[str, Any] = {}
        self._components: dict[str, Any] = {}
        self._rebuild_lookups()

    def _rebuild_lookups(self) -> None:
        """Rebuild the connection and component lookup dictionaries."""
        # Build connection lookup
        self._connections = {}
        for conn in self.model.conns["object"]:
            self._connections[conn.label] = conn

        # Build component lookup
        self._components = {}
        for comp in self.model.comps["object"]:
            self._components[comp.label] = comp

    @property
    def network(self) -> Network:
        """Get the TESPy Network object."""
        return self.model

    def get_param(self, spec: VariableSpec, use_si: bool = False) -> float:
        """
        Get a parameter value from the TESPy model.

        Parameters
        ----------
        spec : VariableSpec
            The variable specification.
        use_si : bool
            If True, return value in SI units. If False, return in network units.
            Default is False (network units), for consistency with set_param.

        Returns
        -------
        float
            The parameter value.

        Raises
        ------
        KeyError
            If the connection/component or parameter does not exist.
        """
        from ..variables import TargetType

        if spec.target_type == TargetType.CONNECTION:
            return self._get_connection_param(spec.target_id, spec.parameter, use_si)
        else:  # COMPONENT
            return self._get_component_param(spec.target_id, spec.parameter)

    def _get_connection_param(self, conn_id: str, parameter: str, use_si: bool = False) -> float:
        """Get a parameter from a connection.

        Parameters
        ----------
        conn_id : str
            The connection identifier.
        parameter : str
            The parameter name.
        use_si : bool
            If True, return value in SI units. If False, return in network units.

        Returns
        -------
        float
            The parameter value.
        """
        if conn_id not in self._connections:
            raise KeyError(f"Connection '{conn_id}' not found in network")

        conn = self._connections[conn_id]

        # Handle common thermodynamic properties
        if parameter in ["m", "p", "h", "T", "s", "v", "x", "vol"]:
            attr = conn.get_attr(parameter)
            if use_si:
                return attr.val_SI if hasattr(attr, "val_SI") else attr.val
            else:
                return attr.val if hasattr(attr, "val") else attr.val_SI
        elif parameter == "fluid":
            return conn.fluid.val
        else:
            # Try to get as a generic attribute
            if hasattr(conn, parameter):
                val = getattr(conn, parameter)
                if use_si:
                    if hasattr(val, "val_SI"):
                        return val.val_SI
                    elif hasattr(val, "val"):
                        return val.val
                else:
                    if hasattr(val, "val"):
                        return val.val
                    elif hasattr(val, "val_SI"):
                        return val.val_SI
                return val
            raise KeyError(f"Parameter '{parameter}' not found on connection '{conn_id}'")

    def _get_component_param(self, comp_id: str, parameter: str) -> float:
        """Get a parameter from a component."""
        if comp_id not in self._components:
            raise KeyError(f"Component '{comp_id}' not found in network")

        comp = self._components[comp_id]

        if hasattr(comp, parameter):
            val = getattr(comp, parameter)
            if hasattr(val, "val"):
                return val.val
            return val
        else:
            raise KeyError(f"Parameter '{parameter}' not found on component '{comp_id}'")

    def set_param(self, spec: VariableSpec, value: float) -> None:
        """
        Set a parameter value in the TESPy model.

        Parameters
        ----------
        spec : VariableSpec
            The variable specification.
        value : float
            The new value to set.

        Raises
        ------
        KeyError
            If the connection/component or parameter does not exist.
        """
        from ..variables import TargetType

        if spec.target_type == TargetType.CONNECTION:
            self._set_connection_param(spec.target_id, spec.parameter, value)
        else:  # COMPONENT
            self._set_component_param(spec.target_id, spec.parameter, value)

    def _set_connection_param(self, conn_id: str, parameter: str, value: float) -> None:
        """Set a parameter on a connection."""
        if conn_id not in self._connections:
            raise KeyError(f"Connection '{conn_id}' not found in network")

        conn = self._connections[conn_id]

        # Use TESPy's set_attr method for proper handling
        conn.set_attr(**{parameter: value})
        logger.debug(f"Set connection '{conn_id}' parameter '{parameter}' to {value}")

    def _set_component_param(self, comp_id: str, parameter: str, value: float) -> None:
        """Set a parameter on a component."""
        if comp_id not in self._components:
            raise KeyError(f"Component '{comp_id}' not found in network")

        comp = self._components[comp_id]

        # Use TESPy's set_attr method for proper handling
        comp.set_attr(**{parameter: value})
        logger.debug(f"Set component '{comp_id}' parameter '{parameter}' to {value}")

    def solve(self, design: bool = False, init_path: str | None = None) -> bool:
        """
        Solve the TESPy network.

        Parameters
        ----------
        design : bool
            If True, solve in design mode. Otherwise use offdesign mode.
        init_path : str | None
            Optional path to initialization data.

        Returns
        -------
        bool
            True if the solver converged successfully.
        """
        try:
            mode = "design" if design else "offdesign"
            kwargs = {"mode": mode, "print_results": False}  # Suppress TESPy output
            if init_path:
                kwargs["init_path"] = init_path

            self.model.solve(**kwargs)
            # Use the .converged attribute (TESPy >= 0.9)
            self._last_solve_success = getattr(self.model, "converged", True)
            if not self._last_solve_success:
                logger.warning("TESPy solve did not converge.")
            return self._last_solve_success
        except Exception as e:
            logger.error(f"TESPy solve failed with exception: {e}")
            self._last_solve_success = False
            return False

    def export_to_exerpy(self) -> dict[str, Any]:
        """
        Export the current TESPy network state to ExerPy format.

        Returns
        -------
        dict[str, Any]
            Dictionary in ExerPy's expected format.
        """
        from ...parser.from_tespy.tespy_parser import to_exerpy

        return to_exerpy(self.model, self.Tamb, self.pamb)

    def get_convergence_info(self) -> dict[str, Any]:
        """
        Get information about the last solve convergence.

        Returns
        -------
        dict[str, Any]
            Dictionary with convergence information.
        """
        return {
            "converged": self._last_solve_success,
            "residual": self.model.res[-1] if self.model.res else None,
            "iterations": len(self.model.res) if self.model.res else 0,
            "tolerance": self.model.tol_res,
        }

    def list_connections(self) -> list[str]:
        """
        List all connection labels in the network.

        Returns
        -------
        list[str]
            List of connection labels.
        """
        return list(self._connections.keys())

    def list_components(self) -> list[str]:
        """
        List all component labels in the network.

        Returns
        -------
        list[str]
            List of component labels.
        """
        return list(self._components.keys())

    def get_connection_state(self, conn_id: str) -> dict[str, float]:
        """
        Get the full thermodynamic state of a connection.

        Parameters
        ----------
        conn_id : str
            The connection identifier.

        Returns
        -------
        dict[str, float]
            Dictionary with thermodynamic properties.
        """
        if conn_id not in self._connections:
            raise KeyError(f"Connection '{conn_id}' not found")

        conn = self._connections[conn_id]
        return {
            "m": conn.m.val_SI,
            "p": conn.p.val_SI,
            "h": conn.h.val_SI,
            "T": conn.T.val_SI,
            "s": conn.s.val_SI,
        }

    def save_state(self) -> dict[str, Any]:
        """
        Save the current network state for potential restoration.

        Returns
        -------
        dict[str, Any]
            Dictionary containing the current state of all variables.
        """
        state = {"connections": {}, "components": {}}

        for label, conn in self._connections.items():
            state["connections"][label] = {
                "m": conn.m.val_SI if conn.m.is_set else None,
                "p": conn.p.val_SI if conn.p.is_set else None,
                "h": conn.h.val_SI if conn.h.is_set else None,
                "T": conn.T.val_SI if conn.T.is_set else None,
            }

        return state

    def __repr__(self) -> str:
        return (
            f"TESPyAdapter(network={self.model.mode}, "
            f"connections={len(self._connections)}, "
            f"components={len(self._components)})"
        )
