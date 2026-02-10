"""
Base adapter interface for simulator integration.

This module defines the SimulatorAdapter protocol that all simulator-specific
adapters must implement to work with the ExergoeconomicOptimizer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..variables import VariableSpec


class SimulatorAdapter(ABC):
    """
    Abstract base class defining the interface for simulator adapters.

    Each simulator (TESPy, Ebsilon, Aspen) must implement this interface
    to allow the optimizer to interact with the simulation model.

    The adapter is responsible for:
    - Getting/setting parameter values in the simulation model
    - Running the simulation solver
    - Exporting simulation state to ExerPy's JSON format

    Attributes
    ----------
    name : str
        Name of the simulator (e.g., 'TESPy', 'Ebsilon', 'Aspen').
    model : Any
        The underlying simulation model object.
    """

    name: str = "base"

    def __init__(self, model: Any):
        """
        Initialize the adapter with a simulation model.

        Parameters
        ----------
        model : Any
            The simulation model object (TESPy Network, Ebsilon path, etc.).
        """
        self.model = model
        self._last_solve_success = False

    @abstractmethod
    def get_param(self, spec: VariableSpec) -> float:
        """
        Get the current value of a parameter from the simulation model.

        Parameters
        ----------
        spec : VariableSpec
            Specification identifying the parameter location.

        Returns
        -------
        float
            The current parameter value.

        Raises
        ------
        KeyError
            If the specified parameter does not exist.
        """
        ...

    @abstractmethod
    def set_param(self, spec: VariableSpec, value: float) -> None:
        """
        Set a parameter value in the simulation model.

        Parameters
        ----------
        spec : VariableSpec
            Specification identifying the parameter location.
        value : float
            The new value to set.

        Raises
        ------
        KeyError
            If the specified parameter does not exist.
        ValueError
            If the value is invalid for this parameter.
        """
        ...

    @abstractmethod
    def solve(self) -> bool:
        """
        Run the simulation solver.

        Returns
        -------
        bool
            True if the simulation converged successfully, False otherwise.
        """
        ...

    @abstractmethod
    def export_to_exerpy(self) -> dict[str, Any]:
        """
        Export the current simulation state to ExerPy's JSON format.

        This should return a dictionary in the format expected by
        ExergyAnalysis.from_json() or the internal _process_json() method.

        Returns
        -------
        dict[str, Any]
            Dictionary containing 'components', 'connections', and
            'ambient_conditions' keys.
        """
        ...

    @property
    def last_solve_success(self) -> bool:
        """Whether the last solve() call was successful."""
        return self._last_solve_success

    def get_connection_param(self, connection_id: str, parameter: str) -> float:
        """
        Convenience method to get a connection parameter.

        Parameters
        ----------
        connection_id : str
            The connection identifier.
        parameter : str
            The parameter name (e.g., 'p', 'T', 'm', 'h', 's').

        Returns
        -------
        float
            The parameter value.
        """
        from ..variables import TargetType, VariableSpec

        spec = VariableSpec(target_type=TargetType.CONNECTION, target_id=connection_id, parameter=parameter)
        return self.get_param(spec)

    def set_connection_param(self, connection_id: str, parameter: str, value: float) -> None:
        """
        Convenience method to set a connection parameter.

        Parameters
        ----------
        connection_id : str
            The connection identifier.
        parameter : str
            The parameter name.
        value : float
            The new value.
        """
        from ..variables import TargetType, VariableSpec

        spec = VariableSpec(target_type=TargetType.CONNECTION, target_id=connection_id, parameter=parameter)
        self.set_param(spec, value)

    def get_component_param(self, component_id: str, parameter: str) -> float:
        """
        Convenience method to get a component parameter.

        Parameters
        ----------
        component_id : str
            The component identifier.
        parameter : str
            The parameter name (e.g., 'eta_s', 'pr', 'Q').

        Returns
        -------
        float
            The parameter value.
        """
        from ..variables import TargetType, VariableSpec

        spec = VariableSpec(target_type=TargetType.COMPONENT, target_id=component_id, parameter=parameter)
        return self.get_param(spec)

    def set_component_param(self, component_id: str, parameter: str, value: float) -> None:
        """
        Convenience method to set a component parameter.

        Parameters
        ----------
        component_id : str
            The component identifier.
        parameter : str
            The parameter name.
        value : float
            The new value.
        """
        from ..variables import TargetType, VariableSpec

        spec = VariableSpec(target_type=TargetType.COMPONENT, target_id=component_id, parameter=parameter)
        self.set_param(spec, value)

    def validate_variable(self, spec: VariableSpec) -> bool:
        """
        Check if a variable specification is valid for this model.

        Parameters
        ----------
        spec : VariableSpec
            The variable specification to validate.

        Returns
        -------
        bool
            True if the variable exists and can be modified.
        """
        try:
            self.get_param(spec)
            return True
        except (KeyError, ValueError, AttributeError):
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={type(self.model).__name__})"
