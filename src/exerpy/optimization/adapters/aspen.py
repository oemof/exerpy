"""
Aspen Plus adapter for the optimization framework.

This module provides the AspenAdapter class that allows the ExergoeconomicOptimizer
to interact with Aspen Plus simulation models via COM interface.

Note: This adapter requires Windows and Aspen Plus to be installed.
"""

from __future__ import annotations

import contextlib
import logging
import os
from typing import TYPE_CHECKING, Any

from .base import SimulatorAdapter

if TYPE_CHECKING:
    from ..variables import VariableSpec

logger = logging.getLogger(__name__)


class AspenAdapter(SimulatorAdapter):
    """
    Adapter for Aspen Plus models.

    This adapter wraps an Aspen Plus model file (.bkp) and provides the interface
    required by the ExergoeconomicOptimizer. It uses COM automation to
    interact with Aspen Plus.

    Parameters
    ----------
    model_path : str
        Path to the Aspen Plus .bkp model file.
    Tamb : float | None
        Ambient temperature in K. If None, will be read from model.
    pamb : float | None
        Ambient pressure in Pa. If None, will be read from model.
    split_physical_exergy : bool
        Whether to split physical exergy into thermal and mechanical components.

    Notes
    -----
    - Requires Windows operating system
    - Requires Aspen Plus to be installed

    Examples
    --------
    >>> adapter = AspenAdapter("path/to/model.bkp")
    >>> adapter.solve()
    True
    """

    name = "Aspen"

    def __init__(
        self,
        model_path: str,
        Tamb: float | None = None,
        pamb: float | None = None,
        split_physical_exergy: bool = True,
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Aspen model not found: {model_path}")

        super().__init__(model_path)
        self.model_path = model_path
        self._Tamb = Tamb
        self._pamb = pamb
        self.split_physical_exergy = split_physical_exergy

        # COM object - initialized lazily
        self._aspen = None
        self._initialized = False

        # Caches
        self._streams: dict[str, Any] = {}
        self._blocks: dict[str, Any] = {}

    def _ensure_initialized(self) -> None:
        """Initialize the Aspen COM connection if not already done."""
        if self._initialized:
            return

        try:
            from win32com.client import Dispatch

            # Start Aspen Plus application
            self._aspen = Dispatch("Apwn.Document")
            self._aspen.InitFromArchive2(self.model_path)

            # Build lookups
            self._rebuild_lookups()

            self._initialized = True
            logger.info(f"Aspen model initialized: {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to initialize Aspen model: {e}")
            raise RuntimeError(f"Could not initialize Aspen model: {e}")

    def _rebuild_lookups(self) -> None:
        """Build lookup dictionaries for streams and blocks."""
        self._streams = {}
        self._blocks = {}

        # Get streams
        stream_nodes = self._aspen.Tree.FindNode(r"\Data\Streams")
        if stream_nodes is not None:
            for stream_node in stream_nodes.Elements:
                self._streams[stream_node.Name] = stream_node.Name

        # Get blocks
        block_nodes = self._aspen.Tree.FindNode(r"\Data\Blocks")
        if block_nodes is not None:
            for block_node in block_nodes.Elements:
                self._blocks[block_node.Name] = block_node.Name

    @property
    def Tamb(self) -> float:
        """Get the ambient temperature."""
        if self._Tamb is not None:
            return self._Tamb

        self._ensure_initialized()
        from ...functions import convert_to_SI

        temp_node = self._aspen.Tree.FindNode(r"\Data\Setup\Sim-Options\Input\REF_TEMP")
        if temp_node is not None and temp_node.Value is not None:
            self._Tamb = convert_to_SI("T", temp_node.Value, temp_node.UnitString)
            return self._Tamb
        raise ValueError("Ambient temperature not found in model and not provided")

    @property
    def pamb(self) -> float:
        """Get the ambient pressure."""
        if self._pamb is not None:
            return self._pamb

        self._ensure_initialized()
        from ...functions import convert_to_SI

        pres_node = self._aspen.Tree.FindNode(r"\Data\Setup\Sim-Options\Input\REF_PRES")
        if pres_node is not None and pres_node.Value is not None:
            self._pamb = convert_to_SI("p", pres_node.Value, pres_node.UnitString)
            return self._pamb
        raise ValueError("Ambient pressure not found in model and not provided")

    def get_param(self, spec: VariableSpec) -> float:
        """
        Get a parameter value from the Aspen model.

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
            return self._get_stream_param(spec.target_id, spec.parameter)
        else:
            return self._get_block_param(spec.target_id, spec.parameter)

    def _get_stream_param(self, stream_id: str, parameter: str) -> float:
        """Get a parameter from a stream."""
        if stream_id not in self._streams:
            raise KeyError(f"Stream '{stream_id}' not found in model")

        # Map parameter names to Aspen tree paths
        param_paths = {
            "T": rf"\Data\Streams\{stream_id}\Output\TEMP_OUT\MIXED",
            "p": rf"\Data\Streams\{stream_id}\Output\PRES_OUT\MIXED",
            "h": rf"\Data\Streams\{stream_id}\Output\HMX_MASS\MIXED",
            "s": rf"\Data\Streams\{stream_id}\Output\SMX_MASS\MIXED",
            "m": rf"\Data\Streams\{stream_id}\Output\MASSFLMX\MIXED",
        }

        if parameter in param_paths:
            node = self._aspen.Tree.FindNode(param_paths[parameter])
            if node is not None and node.Value is not None:
                return node.Value
            raise KeyError(f"Parameter '{parameter}' not available for stream '{stream_id}'")

        raise KeyError(f"Unknown parameter '{parameter}' for stream")

    def _get_block_param(self, block_id: str, parameter: str) -> float:
        """Get a parameter from a block."""
        if block_id not in self._blocks:
            raise KeyError(f"Block '{block_id}' not found in model")

        # Map parameter names to Aspen tree paths
        param_paths = {
            "eta_s": rf"\Data\Blocks\{block_id}\Output\EFF_ISEN",
            "eta_mech": rf"\Data\Blocks\{block_id}\Output\EFF_MECH",
            "P": rf"\Data\Blocks\{block_id}\Output\BRAKE_POWER",
            "Q": rf"\Data\Blocks\{block_id}\Output\QNET",
        }

        if parameter in param_paths:
            node = self._aspen.Tree.FindNode(param_paths[parameter])
            if node is not None and node.Value is not None:
                return node.Value
            raise KeyError(f"Parameter '{parameter}' not available for block '{block_id}'")

        # Try generic input path
        input_node = self._aspen.Tree.FindNode(rf"\Data\Blocks\{block_id}\Input\{parameter}")
        if input_node is not None and input_node.Value is not None:
            return input_node.Value

        raise KeyError(f"Unknown parameter '{parameter}' for block")

    def set_param(self, spec: VariableSpec, value: float) -> None:
        """
        Set a parameter value in the Aspen model.

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
            self._set_stream_param(spec.target_id, spec.parameter, value)
        else:
            self._set_block_param(spec.target_id, spec.parameter, value)

    def _set_stream_param(self, stream_id: str, parameter: str, value: float) -> None:
        """Set a parameter on a stream."""
        if stream_id not in self._streams:
            raise KeyError(f"Stream '{stream_id}' not found in model")

        # Map to input paths (not output)
        param_paths = {
            "T": rf"\Data\Streams\{stream_id}\Input\TEMP\MIXED",
            "p": rf"\Data\Streams\{stream_id}\Input\PRES\MIXED",
            "m": rf"\Data\Streams\{stream_id}\Input\TOTFLOW\MIXED",
        }

        if parameter in param_paths:
            node = self._aspen.Tree.FindNode(param_paths[parameter])
            if node is not None:
                node.Value = value
                logger.debug(f"Set stream '{stream_id}' parameter '{parameter}' to {value}")
                return

        raise KeyError(f"Cannot set parameter '{parameter}' on stream '{stream_id}'")

    def _set_block_param(self, block_id: str, parameter: str, value: float) -> None:
        """Set a parameter on a block."""
        if block_id not in self._blocks:
            raise KeyError(f"Block '{block_id}' not found in model")

        # Try input path
        input_node = self._aspen.Tree.FindNode(rf"\Data\Blocks\{block_id}\Input\{parameter}")
        if input_node is not None:
            input_node.Value = value
            logger.debug(f"Set block '{block_id}' parameter '{parameter}' to {value}")
            return

        raise KeyError(f"Cannot set parameter '{parameter}' on block '{block_id}'")

    def solve(self) -> bool:
        """
        Run the Aspen Plus simulation.

        Returns
        -------
        bool
            True if the simulation completed successfully.
        """
        self._ensure_initialized()

        try:
            # Run the simulation
            self._aspen.Run2()

            # Check convergence status
            # In Aspen, we can check the RUN_STATUS node
            status_node = self._aspen.Tree.FindNode(r"\Data\Results Summary\RUN_STATUS")
            if status_node is not None:
                self._last_solve_success = status_node.Value == "SUCCESS"
            else:
                # Assume success if no status node
                self._last_solve_success = True

            if not self._last_solve_success:
                logger.warning("Aspen simulation did not converge")

            return self._last_solve_success

        except Exception as e:
            logger.error(f"Aspen simulation failed: {e}")
            self._last_solve_success = False
            return False

    def export_to_exerpy(self) -> dict[str, Any]:
        """
        Export the current Aspen model state to ExerPy format.

        Returns
        -------
        dict[str, Any]
            Dictionary in ExerPy's expected format.
        """
        from ...parser.from_aspen.aspen_parser import AspenModelParser

        # Create a parser instance
        parser = AspenModelParser(self.model_path, split_physical_exergy=self.split_physical_exergy)

        # Share our COM object
        parser.aspen = self._aspen
        parser.Tamb = self.Tamb
        parser.pamb = self.pamb

        # Parse streams and blocks
        parser.parse_streams()
        parser.parse_blocks()

        return parser.get_sorted_data()

    def list_streams(self) -> list[str]:
        """List all stream names in the model."""
        self._ensure_initialized()
        return list(self._streams.keys())

    def list_blocks(self) -> list[str]:
        """List all block names in the model."""
        self._ensure_initialized()
        return list(self._blocks.keys())

    def list_connections(self) -> list[str]:
        """List all connection (stream) names in the model."""
        return self.list_streams()

    def list_components(self) -> list[str]:
        """List all component (block) names in the model."""
        return self.list_blocks()

    def reinitialize(self) -> None:
        """Reinitialize the model from the original file."""
        self.close()
        self._ensure_initialized()

    def close(self) -> None:
        """Close the Aspen COM connection."""
        if self._aspen is not None:
            with contextlib.suppress(Exception):
                self._aspen.Close()
        self._aspen = None
        self._initialized = False

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

    def __repr__(self) -> str:
        return f"AspenAdapter(model_path='{self.model_path}', initialized={self._initialized})"
