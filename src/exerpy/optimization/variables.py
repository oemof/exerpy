"""
Design variable definitions for exergoeconomic optimization.

This module provides classes to define design variables in a simulator-agnostic way,
allowing the same optimization problem specification to work with TESPy, Ebsilon, or Aspen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TargetType(Enum):
    """Type of target for a design variable."""

    CONNECTION = "connection"
    COMPONENT = "component"


@dataclass
class VariableSpec:
    """
    Specification for locating a parameter in a simulation model.

    This is used internally by adapters to map design variables to
    simulator-specific parameter locations.

    Attributes
    ----------
    target_type : TargetType
        Whether the variable targets a connection or component.
    target_id : str
        Identifier of the connection or component.
    parameter : str
        Name of the parameter to modify (e.g., 'p', 'T', 'm', 'eta_s').
    """

    target_type: TargetType
    target_id: str
    parameter: str

    def __str__(self) -> str:
        return f"{self.target_type.value}:{self.target_id}:{self.parameter}"

    @classmethod
    def from_string(cls, spec_string: str) -> VariableSpec:
        """
        Create a VariableSpec from a string representation.

        Parameters
        ----------
        spec_string : str
            String in format "target_type:target_id:parameter"
            e.g., "connection:2:p" or "component:turbine_hp:eta_s"

        Returns
        -------
        VariableSpec
            The parsed variable specification.
        """
        parts = spec_string.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid variable spec string: {spec_string}. Expected format: 'type:id:param'")

        target_type_str, target_id, parameter = parts
        try:
            target_type = TargetType(target_type_str)
        except ValueError:
            raise ValueError(f"Invalid target type: {target_type_str}. Must be 'connection' or 'component'")

        return cls(target_type=target_type, target_id=target_id, parameter=parameter)


@dataclass
class DesignVariable:
    """
    Definition of a design variable for optimization.

    A design variable represents a parameter in the simulation model that can be
    varied by the optimizer to find optimal operating conditions.

    Attributes
    ----------
    name : str
        Human-readable name for the variable (used in results and logging).
    target_type : TargetType | str
        Whether the variable targets a 'connection' or 'component'.
    target_id : str
        Identifier of the connection or component in the simulation model.
    parameter : str
        Name of the parameter to modify (e.g., 'p', 'T', 'm', 'eta_s').
    bounds : tuple[float, float]
        Lower and upper bounds for the variable (min, max).
    initial : float | None
        Initial value for the variable. If None, uses current model value.
    unit : str | None
        Optional unit string for display purposes.
    description : str | None
        Optional description of what this variable represents.

    Examples
    --------
    >>> var = DesignVariable(
    ...     name="HP turbine inlet pressure",
    ...     target_type="connection",
    ...     target_id="2",
    ...     parameter="p",
    ...     bounds=(50e5, 150e5),
    ...     unit="Pa"
    ... )
    """

    name: str
    target_type: TargetType | str
    target_id: str
    parameter: str
    bounds: tuple[float, float]
    initial: float | None = None
    unit: str | None = None
    description: str | None = None
    _metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Convert string to TargetType if needed
        if isinstance(self.target_type, str):
            self.target_type = TargetType(self.target_type)

        # Validate bounds
        if len(self.bounds) != 2:
            raise ValueError(f"Bounds must be a tuple of (min, max), got {self.bounds}")
        if self.bounds[0] >= self.bounds[1]:
            raise ValueError(f"Lower bound must be less than upper bound: {self.bounds}")

        # Validate initial value if provided
        if self.initial is not None and not (self.bounds[0] <= self.initial <= self.bounds[1]):
            raise ValueError(f"Initial value {self.initial} is outside bounds {self.bounds}")

    @property
    def spec(self) -> VariableSpec:
        """Get the VariableSpec for this design variable."""
        return VariableSpec(
            target_type=self.target_type,
            target_id=self.target_id,
            parameter=self.parameter,
        )

    @property
    def lower_bound(self) -> float:
        """Get the lower bound."""
        return self.bounds[0]

    @property
    def upper_bound(self) -> float:
        """Get the upper bound."""
        return self.bounds[1]

    def normalize(self, value: float) -> float:
        """
        Normalize a value to [0, 1] range based on bounds.

        Parameters
        ----------
        value : float
            The value to normalize.

        Returns
        -------
        float
            Normalized value in [0, 1].
        """
        return (value - self.lower_bound) / (self.upper_bound - self.lower_bound)

    def denormalize(self, normalized_value: float) -> float:
        """
        Convert a normalized [0, 1] value back to actual value.

        Parameters
        ----------
        normalized_value : float
            The normalized value in [0, 1].

        Returns
        -------
        float
            The actual value within bounds.
        """
        return self.lower_bound + normalized_value * (self.upper_bound - self.lower_bound)

    def __repr__(self) -> str:
        return (
            f"DesignVariable(name='{self.name}', "
            f"target={self.target_type.value}:{self.target_id}:{self.parameter}, "
            f"bounds={self.bounds})"
        )
