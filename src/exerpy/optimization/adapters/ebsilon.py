"""
Ebsilon adapter for the optimization framework.

This module provides the EbsilonAdapter class that allows the ExergoeconomicOptimizer
to interact with Ebsilon Professional simulation models via COM interface.

Note: This adapter requires Windows and Ebsilon Professional to be installed.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

from .base import SimulatorAdapter

if TYPE_CHECKING:
    from ..variables import VariableSpec

logger = logging.getLogger(__name__)


class EbsilonAdapter(SimulatorAdapter):
    """
    Adapter for Ebsilon Professional models.

    This adapter wraps an Ebsilon model file and provides the interface
    required by the ExergoeconomicOptimizer. It uses COM automation to
    interact with Ebsilon.

    Parameters
    ----------
    model_path : str
        Path to the Ebsilon .ebs model file.
    Tamb : float | None
        Ambient temperature in K. If None, will be read from model.
    pamb : float | None
        Ambient pressure in Pa. If None, will be read from model.
    split_physical_exergy : bool
        Whether to split physical exergy into thermal and mechanical components.

    Notes
    -----
    - Requires Windows operating system
    - Requires Ebsilon Professional to be installed
    - Requires the EBS environment variable to be set

    Examples
    --------
    >>> adapter = EbsilonAdapter("path/to/model.ebs")
    >>> adapter.solve()
    True
    """

    name = "Ebsilon"

    def __init__(
        self,
        model_path: str,
        Tamb: float | None = None,
        pamb: float | None = None,
        split_physical_exergy: bool = True,
    ):
        # Import here to avoid import errors on non-Windows systems
        from ...parser.from_ebsilon import is_ebsilon_available

        if not is_ebsilon_available():
            raise RuntimeError(
                "Ebsilon is not available. Please ensure you are on Windows "
                "and the EBS environment variable is set to your Ebsilon installation path."
            )

        super().__init__(model_path)
        self.model_path = model_path
        self._Tamb = Tamb
        self._pamb = pamb
        self.split_physical_exergy = split_physical_exergy

        # COM objects - initialized lazily
        self._app = None
        self._ebs_model = None
        self._oc = None
        self._initialized = False

        # Caches for component and connection lookups
        self._components: dict[str, Any] = {}
        self._connections: dict[str, Any] = {}

    def _ensure_initialized(self) -> None:
        """Initialize the Ebsilon COM connection if not already done."""
        if self._initialized:
            return

        try:
            from win32com.client import Dispatch

            # Start COM server
            self._app = Dispatch("EbsOpen.Application")
            self._ebs_model = self._app.Open(self.model_path)
            self._oc = self._app.ObjectCaster

            # Run initial simulation to populate values
            self._ebs_model.SimulateNew()

            # Build lookups
            self._rebuild_lookups()

            self._initialized = True
            logger.info(f"Ebsilon model initialized: {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to initialize Ebsilon model: {e}")
            raise RuntimeError(f"Could not initialize Ebsilon model: {e}")

    def _rebuild_lookups(self) -> None:
        """Build lookup dictionaries for components and connections."""
        self._components = {}
        self._connections = {}

        total_objects = self._ebs_model.Objects.Count

        for j in range(1, total_objects + 1):
            obj = self._ebs_model.Objects.Item(j)

            # Components (epObjectKindComp = 10)
            if obj.IsKindOf(10):
                comp_cast = self._oc.CastToComp(obj)
                self._components[comp_cast.Name] = {
                    "object": obj,
                    "cast": comp_cast,
                    "type_index": comp_cast.Kind - 10000,
                }

            # Connections/Pipes (epObjectKindPipe = 16)
            elif obj.IsKindOf(16):
                pipe_cast = self._oc.CastToPipe(obj)
                self._connections[pipe_cast.Name] = {
                    "object": obj,
                    "cast": pipe_cast,
                }

    @property
    def Tamb(self) -> float:
        """Get the ambient temperature."""
        if self._Tamb is not None:
            return self._Tamb
        # Read from model if not set
        self._ensure_initialized()
        # Ambient conditions are typically set in component type 46
        for name, comp_data in self._components.items():
            if comp_data["type_index"] == 46:
                comp46 = self._oc.CastToComp46(comp_data["object"])
                if comp46.FTYP.Value == 26:  # Temperature
                    from ...functions import convert_to_SI
                    from ...parser.from_ebsilon.ebsilon_config import unit_id_to_string

                    self._Tamb = convert_to_SI(
                        "T", comp46.MEASM.Value, unit_id_to_string.get(comp46.MEASM.Dimension, "Unknown")
                    )
                    return self._Tamb
        raise ValueError("Ambient temperature not found in model and not provided")

    @property
    def pamb(self) -> float:
        """Get the ambient pressure."""
        if self._pamb is not None:
            return self._pamb
        # Read from model if not set
        self._ensure_initialized()
        for name, comp_data in self._components.items():
            if comp_data["type_index"] == 46:
                comp46 = self._oc.CastToComp46(comp_data["object"])
                if comp46.FTYP.Value == 13:  # Pressure
                    from ...functions import convert_to_SI
                    from ...parser.from_ebsilon.ebsilon_config import unit_id_to_string

                    self._pamb = convert_to_SI(
                        "p", comp46.MEASM.Value, unit_id_to_string.get(comp46.MEASM.Dimension, "Unknown")
                    )
                    return self._pamb
        raise ValueError("Ambient pressure not found in model and not provided")

    def get_param(self, spec: VariableSpec) -> float:
        """
        Get a parameter value from the Ebsilon model.

        Parameters
        ----------
        spec : VariableSpec
            The variable specification.

        Returns
        -------
        float
            The parameter value.
        """
        from ..variables import TargetType

        self._ensure_initialized()

        if spec.target_type == TargetType.CONNECTION:
            return self._get_connection_param(spec.target_id, spec.parameter)
        else:
            return self._get_component_param(spec.target_id, spec.parameter)

    def _get_connection_param(self, conn_id: str, parameter: str) -> float:
        """Get a parameter from a connection (pipe)."""
        if conn_id not in self._connections:
            raise KeyError(f"Connection '{conn_id}' not found in model")

        pipe = self._connections[conn_id]["cast"]

        # Map parameter names to Ebsilon attributes
        param_map = {
            "m": "M",
            "T": "T",
            "p": "P",
            "h": "H",
            "s": "S",
            "x": "X",
        }

        ebs_param = param_map.get(parameter, parameter.upper())

        if hasattr(pipe, ebs_param):
            attr = getattr(pipe, ebs_param)
            if hasattr(attr, "Value"):
                return attr.Value
            return attr
        raise KeyError(f"Parameter '{parameter}' not found on connection '{conn_id}'")

    def _get_component_param(self, comp_id: str, parameter: str) -> float:
        """Get a parameter from a component."""
        if comp_id not in self._components:
            raise KeyError(f"Component '{comp_id}' not found in model")

        comp_data = self._components[comp_id]
        type_index = comp_data["type_index"]

        # Get the specifically cast component
        cast_method = f"CastToComp{type_index}"
        if hasattr(self._oc, cast_method):
            comp = getattr(self._oc, cast_method)(comp_data["object"])
        else:
            comp = comp_data["cast"]

        # Map common parameter names
        param_map = {
            "eta_s": "ETAIN",
            "eta_mech": "ETAMN",
            "eta_el": "ETAEN",
            "Q": "QT",
            "P": "QSHAFT",
        }

        ebs_param = param_map.get(parameter, parameter.upper())

        if hasattr(comp, ebs_param):
            attr = getattr(comp, ebs_param)
            if hasattr(attr, "Value"):
                return attr.Value
            return attr
        raise KeyError(f"Parameter '{parameter}' not found on component '{comp_id}'")

    def set_param(self, spec: VariableSpec, value: float) -> None:
        """
        Set a parameter value in the Ebsilon model.

        Parameters
        ----------
        spec : VariableSpec
            The variable specification.
        value : float
            The new value to set.
        """
        from ..variables import TargetType

        self._ensure_initialized()

        if spec.target_type == TargetType.CONNECTION:
            self._set_connection_param(spec.target_id, spec.parameter, value)
        else:
            self._set_component_param(spec.target_id, spec.parameter, value)

    def _set_connection_param(self, conn_id: str, parameter: str, value: float) -> None:
        """Set a parameter on a connection (pipe)."""
        if conn_id not in self._connections:
            raise KeyError(f"Connection '{conn_id}' not found in model")

        pipe = self._connections[conn_id]["cast"]

        param_map = {
            "m": "M",
            "T": "T",
            "p": "P",
            "h": "H",
            "s": "S",
            "x": "X",
        }

        ebs_param = param_map.get(parameter, parameter.upper())

        if hasattr(pipe, ebs_param):
            attr = getattr(pipe, ebs_param)
            if hasattr(attr, "Value"):
                attr.Value = value
                logger.debug(f"Set connection '{conn_id}' parameter '{parameter}' to {value}")
                return
        raise KeyError(f"Parameter '{parameter}' not found on connection '{conn_id}'")

    def _set_component_param(self, comp_id: str, parameter: str, value: float) -> None:
        """Set a parameter on a component."""
        if comp_id not in self._components:
            raise KeyError(f"Component '{comp_id}' not found in model")

        comp_data = self._components[comp_id]
        type_index = comp_data["type_index"]

        cast_method = f"CastToComp{type_index}"
        if hasattr(self._oc, cast_method):
            comp = getattr(self._oc, cast_method)(comp_data["object"])
        else:
            comp = comp_data["cast"]

        param_map = {
            "eta_s": "ETAIN",
            "eta_mech": "ETAMN",
            "eta_el": "ETAEN",
            "Q": "QT",
            "P": "QSHAFT",
        }

        ebs_param = param_map.get(parameter, parameter.upper())

        if hasattr(comp, ebs_param):
            attr = getattr(comp, ebs_param)
            if hasattr(attr, "Value"):
                attr.Value = value
                logger.debug(f"Set component '{comp_id}' parameter '{parameter}' to {value}")
                return
        raise KeyError(f"Parameter '{parameter}' not found on component '{comp_id}'")

    def solve(self) -> bool:
        """
        Run the Ebsilon simulation.

        Returns
        -------
        bool
            True if the simulation completed successfully.
        """
        self._ensure_initialized()

        try:
            # Run simulation
            self._ebs_model.SimulateNew()

            # Check for errors
            calc_errors = self._ebs_model.CalculationErrors
            error_count = calc_errors.Count

            if error_count > 0:
                for i in range(1, error_count + 1):
                    error = calc_errors.Item(i)
                    logger.warning(f"Ebsilon warning {i}: {error.Description}")

            self._last_solve_success = True
            return True

        except Exception as e:
            logger.error(f"Ebsilon simulation failed: {e}")
            self._last_solve_success = False
            return False

    def export_to_exerpy(self) -> dict[str, Any]:
        """
        Export the current Ebsilon model state to ExerPy format.

        Returns
        -------
        dict[str, Any]
            Dictionary in ExerPy's expected format.
        """
        from ...parser.from_ebsilon.ebsilon_parser import EbsilonModelParser

        # Create a temporary parser to use its parsing logic
        # This reuses the existing parsing infrastructure
        parser = EbsilonModelParser(self.model_path, split_physical_exergy=self.split_physical_exergy)

        # Share our COM objects
        parser.app = self._app
        parser.model = self._ebs_model
        parser.oc = self._oc
        parser.Tamb = self.Tamb
        parser.pamb = self.pamb

        # Parse the model
        parser.parse_model()

        return parser.get_sorted_data()

    def list_connections(self) -> list[str]:
        """List all connection names in the model."""
        self._ensure_initialized()
        return list(self._connections.keys())

    def list_components(self) -> list[str]:
        """List all component names in the model."""
        self._ensure_initialized()
        return list(self._components.keys())

    def close(self) -> None:
        """Close the Ebsilon COM connection."""
        if self._ebs_model is not None:
            with contextlib.suppress(Exception):
                self._ebs_model.Close()
        self._ebs_model = None
        self._app = None
        self._oc = None
        self._initialized = False

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

    def __repr__(self) -> str:
        return f"EbsilonAdapter(model_path='{self.model_path}', initialized={self._initialized})"
