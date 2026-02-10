"""
Constraint definitions for exergoeconomic optimization.

This module provides classes to define constraints on design variables,
simulation outputs, and exergoeconomic results.

Constraints are formulated for pymoo as g(x) <= 0 (inequality) or h(x) == 0 (equality).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

from .variables import VariableSpec

if TYPE_CHECKING:
    from ..analyses import ExergoeconomicAnalysis, ExergyAnalysis
    from .adapters.base import SimulatorAdapter


class ConstraintType(Enum):
    """Type of constraint."""

    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN_OR_EQUAL = ">="
    EQUAL = "=="


@dataclass
class ConstraintResult:
    """
    Result of evaluating a constraint.

    Attributes
    ----------
    value : float
        The constraint violation value (formulated for pymoo: g(x) <= 0).
        Negative or zero means satisfied, positive means violated.
    raw_lhs : float
        The raw left-hand side value.
    raw_rhs : float
        The raw right-hand side value.
    satisfied : bool
        Whether the constraint is satisfied.
    name : str
        Name of the constraint.
    """

    value: float
    raw_lhs: float
    raw_rhs: float
    satisfied: bool
    name: str


class Constraint(ABC):
    """
    Abstract base class for optimization constraints.

    Constraints are evaluated and converted to the pymoo format where
    g(x) <= 0 represents a satisfied constraint.
    """

    def __init__(self, name: str, constraint_type: ConstraintType | str):
        """
        Initialize the constraint.

        Parameters
        ----------
        name : str
            Human-readable name for the constraint.
        constraint_type : ConstraintType | str
            The type of constraint ('<=', '>=', or '==').
        """
        self.name = name
        if isinstance(constraint_type, str):
            self.constraint_type = ConstraintType(constraint_type)
        else:
            self.constraint_type = constraint_type

    @abstractmethod
    def _get_lhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        """Get the left-hand side value of the constraint."""
        ...

    @abstractmethod
    def _get_rhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        """Get the right-hand side value of the constraint."""
        ...

    def evaluate(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> ConstraintResult:
        """
        Evaluate the constraint.

        Returns a ConstraintResult with the violation value formulated for pymoo
        (g(x) <= 0 means satisfied).

        Parameters
        ----------
        adapter : SimulatorAdapter
            The simulator adapter for accessing model parameters.
        exergy_analysis : ExergyAnalysis | None
            The exergy analysis results (if available).
        exergoeconomic_analysis : ExergoeconomicAnalysis | None
            The exergoeconomic analysis results (if available).

        Returns
        -------
        ConstraintResult
            The constraint evaluation result.
        """
        lhs = self._get_lhs(adapter, exergy_analysis, exergoeconomic_analysis)
        rhs = self._get_rhs(adapter, exergy_analysis, exergoeconomic_analysis)

        # Convert to pymoo format: g(x) <= 0
        if self.constraint_type == ConstraintType.LESS_THAN_OR_EQUAL:
            # lhs <= rhs  =>  lhs - rhs <= 0
            value = lhs - rhs
            satisfied = lhs <= rhs
        elif self.constraint_type == ConstraintType.GREATER_THAN_OR_EQUAL:
            # lhs >= rhs  =>  rhs - lhs <= 0
            value = rhs - lhs
            satisfied = lhs >= rhs
        else:  # EQUAL
            # lhs == rhs  =>  |lhs - rhs| <= tolerance (handled specially)
            value = abs(lhs - rhs)
            satisfied = abs(lhs - rhs) < 1e-6

        return ConstraintResult(value=value, raw_lhs=lhs, raw_rhs=rhs, satisfied=satisfied, name=self.name)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', type={self.constraint_type.value})"


class BoundConstraint(Constraint):
    """
    Constraint on a simulation parameter value.

    This constrains a connection or component parameter to be within bounds
    or compared to a fixed value.

    Parameters
    ----------
    name : str
        Human-readable name for the constraint.
    spec : VariableSpec | str
        The variable specification (e.g., "connection:5:T").
    constraint_type : ConstraintType | str
        The type of constraint ('<=', '>=', or '==').
    bound : float
        The bound value to compare against.
    """

    def __init__(
        self,
        name: str,
        spec: VariableSpec | str,
        constraint_type: ConstraintType | str,
        bound: float,
    ):
        super().__init__(name, constraint_type)
        if isinstance(spec, str):
            self.spec = VariableSpec.from_string(spec)
        else:
            self.spec = spec
        self.bound = bound

    def _get_lhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return adapter.get_param(self.spec)

    def _get_rhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return self.bound


class RelativeConstraint(Constraint):
    """
    Constraint comparing two simulation parameters.

    This constrains the relationship between two parameters, e.g.,
    pressure at connection 2 must be greater than pressure at connection 4.

    Parameters
    ----------
    name : str
        Human-readable name for the constraint.
    spec_lhs : VariableSpec | str
        The left-hand side variable specification.
    constraint_type : ConstraintType | str
        The type of constraint ('<=', '>=', or '==').
    spec_rhs : VariableSpec | str
        The right-hand side variable specification.
    """

    def __init__(
        self,
        name: str,
        spec_lhs: VariableSpec | str,
        constraint_type: ConstraintType | str,
        spec_rhs: VariableSpec | str,
    ):
        super().__init__(name, constraint_type)
        if isinstance(spec_lhs, str):
            self.spec_lhs = VariableSpec.from_string(spec_lhs)
        else:
            self.spec_lhs = spec_lhs
        if isinstance(spec_rhs, str):
            self.spec_rhs = VariableSpec.from_string(spec_rhs)
        else:
            self.spec_rhs = spec_rhs

    def _get_lhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return adapter.get_param(self.spec_lhs)

    def _get_rhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return adapter.get_param(self.spec_rhs)


class ExergyConstraint(Constraint):
    """
    Constraint on exergy analysis results.

    Parameters
    ----------
    name : str
        Human-readable name for the constraint.
    attribute : str
        The exergy analysis attribute to constrain (e.g., 'epsilon', 'E_D', 'E_F').
    constraint_type : ConstraintType | str
        The type of constraint ('<=', '>=', or '==').
    bound : float
        The bound value to compare against.
    component_id : str | None
        If specified, constraint applies to this component, otherwise system-level.
    """

    def __init__(
        self,
        name: str,
        attribute: str,
        constraint_type: ConstraintType | str,
        bound: float,
        component_id: str | None = None,
    ):
        super().__init__(name, constraint_type)
        self.attribute = attribute
        self.bound = bound
        self.component_id = component_id

    def _get_lhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if exergy_analysis is None:
            raise ValueError("ExergyAnalysis required for ExergyConstraint")

        if self.component_id is not None:
            if self.component_id not in exergy_analysis.components:
                raise ValueError(f"Component '{self.component_id}' not found")
            target = exergy_analysis.components[self.component_id]
        else:
            target = exergy_analysis

        if not hasattr(target, self.attribute):
            raise ValueError(f"Attribute '{self.attribute}' not found on target")
        return getattr(target, self.attribute)

    def _get_rhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return self.bound


class ExergoeconomicConstraint(Constraint):
    """
    Constraint on exergoeconomic analysis results.

    Parameters
    ----------
    name : str
        Human-readable name for the constraint.
    attribute : str
        The exergoeconomic attribute to constrain (e.g., 'C_D', 'r', 'f', 'C_TOT').
    constraint_type : ConstraintType | str
        The type of constraint ('<=', '>=', or '==').
    bound : float
        The bound value to compare against.
    component_id : str | None
        If specified, constraint applies to this component, otherwise system-level.
    """

    def __init__(
        self,
        name: str,
        attribute: str,
        constraint_type: ConstraintType | str,
        bound: float,
        component_id: str | None = None,
    ):
        super().__init__(name, constraint_type)
        self.attribute = attribute
        self.bound = bound
        self.component_id = component_id

    def _get_lhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if exergoeconomic_analysis is None:
            raise ValueError("ExergoeconomicAnalysis required for ExergoeconomicConstraint")

        if self.component_id is not None:
            if self.component_id not in exergoeconomic_analysis.components:
                raise ValueError(f"Component '{self.component_id}' not found")
            target = exergoeconomic_analysis.components[self.component_id]
        else:
            target = exergoeconomic_analysis

        if not hasattr(target, self.attribute):
            raise ValueError(f"Attribute '{self.attribute}' not found on target")
        return getattr(target, self.attribute)

    def _get_rhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return self.bound


class CustomConstraint(Constraint):
    """
    User-defined constraint using a callable.

    Parameters
    ----------
    name : str
        Human-readable name for the constraint.
    func : Callable
        A function that takes (adapter, ExergyAnalysis, ExergoeconomicAnalysis)
        and returns the left-hand side value.
    constraint_type : ConstraintType | str
        The type of constraint ('<=', '>=', or '==').
    bound : float | Callable
        The bound value or a callable that computes it.

    Examples
    --------
    >>> constraint = CustomConstraint(
    ...     name="Pinch point",
    ...     func=lambda a, ea, eea: a.get_param(VariableSpec.from_string("connection:5:T"))
    ...                          - a.get_param(VariableSpec.from_string("connection:6:T")),
    ...     constraint_type=">=",
    ...     bound=10.0,  # Minimum 10 K pinch point
    ... )
    """

    def __init__(
        self,
        name: str,
        func: Callable[[Any, Any, Any], float],
        constraint_type: ConstraintType | str,
        bound: float | Callable[[Any, Any, Any], float],
    ):
        super().__init__(name, constraint_type)
        self._func = func
        self._bound = bound

    def _get_lhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return self._func(adapter, exergy_analysis, exergoeconomic_analysis)

    def _get_rhs(
        self,
        adapter: SimulatorAdapter,
        exergy_analysis: ExergyAnalysis | None = None,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if callable(self._bound):
            return self._bound(adapter, exergy_analysis, exergoeconomic_analysis)
        return self._bound
