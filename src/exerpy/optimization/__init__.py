"""
Exergoeconomic optimization module for ExerPy.

This module provides a generalized optimization framework for exergoeconomic
analysis of energy systems. It supports multiple simulation backends (TESPy,
Ebsilon Professional, Aspen Plus) and uses pymoo for single and multi-objective
optimization.

Main Classes
------------
ExergoeconomicOptimizer
    High-level interface for setting up and running optimizations.
    Provides a fluent API for adding variables, objectives, and constraints.

ExergoeconomicProblem
    Low-level pymoo problem definition. Used internally by the optimizer
    but can also be used directly for advanced use cases.

DesignVariable
    Represents a design variable that can be optimized.

ObjectiveFunction
    Abstract base class for objective functions. Built-in objectives include:
    - MinimizeExergyDestruction
    - MaximizeExergyEfficiency
    - MinimizeTotalCost
    - MinimizeCostOfExergyDestruction
    - MinimizeLevelizedCost
    - CustomObjective

Constraint
    Abstract base class for constraints. Built-in constraints include:
    - BoundConstraint
    - RelativeConstraint
    - ExergyConstraint
    - ExergoeconomicConstraint
    - CustomConstraint

OptimizationResult
    Contains optimization results including Pareto front for multi-objective
    problems and provides visualization methods.

Adapters
--------
The adapters submodule provides simulator-specific implementations:
- TESPyAdapter: For TESPy models
- EbsilonAdapter: For Ebsilon Professional models
- AspenAdapter: For Aspen Plus models

Example
-------
>>> from exerpy.optimization import ExergoeconomicOptimizer
>>> from exerpy.optimization.adapters import TESPyAdapter
>>> from exerpy.optimization.objectives import MinimizeTotalCost, MaximizeExergyEfficiency
>>>
>>> # Create adapter for your simulation model
>>> adapter = TESPyAdapter(network, Tamb=298.15, pamb=101325)
>>>
>>> # Build optimization problem
>>> optimizer = (
...     ExergoeconomicOptimizer(adapter)
...     .add_variable("HP Pressure", "connection", "2", "p", bounds=(50e5, 150e5))
...     .add_variable("Reheat Temp", "connection", "5", "T", bounds=(700, 900))
...     .add_objective(MinimizeTotalCost())
...     .add_objective(MaximizeExergyEfficiency())
...     .add_constraint("T_max", "<=", "connection:5:T", 873.15)
... )
>>>
>>> # Run optimization
>>> result = optimizer.optimize(
...     E_F={"fuel": 1.0},
...     E_P={"power": 1.0},
...     algorithm="NSGA2",
...     n_gen=100,
... )
>>>
>>> # Analyze results
>>> print(result.summary())
>>> result.plot_pareto()
"""

from .constraints import (
    BoundConstraint,
    Constraint,
    ConstraintType,
    CustomConstraint,
    ExergoeconomicConstraint,
    ExergyConstraint,
    RelativeConstraint,
)
from .objectives import (
    CustomObjective,
    MaximizeComponentEfficiency,
    MaximizeExergyEfficiency,
    MaximizeProductExergy,
    MinimizeComponentExergyDestruction,
    MinimizeCostOfExergyDestruction,
    MinimizeExergyDestruction,
    MinimizeFuelConsumption,
    MinimizeLevelizedCost,
    MinimizeProductCost,
    MinimizeProductSubsetCost,
    MinimizeTotalCost,
    ObjectiveFunction,
    OptimizationSense,
    WeightedSumObjective,
)
from .optimizer import ExergoeconomicOptimizer
from .problem import ExergoeconomicProblem
from .results import OptimizationResult, Solution
from .variables import DesignVariable, TargetType, VariableSpec

__all__ = [
    # Main classes
    "ExergoeconomicOptimizer",
    "ExergoeconomicProblem",
    "OptimizationResult",
    "Solution",
    # Variables
    "DesignVariable",
    "VariableSpec",
    "TargetType",
    # Objectives
    "ObjectiveFunction",
    "OptimizationSense",
    "MinimizeExergyDestruction",
    "MaximizeExergyEfficiency",
    "MinimizeComponentExergyDestruction",
    "MaximizeComponentEfficiency",
    "MinimizeTotalCost",
    "MinimizeCostOfExergyDestruction",
    "MinimizeLevelizedCost",
    "MinimizeProductCost",
    "MinimizeProductSubsetCost",
    "MinimizeFuelConsumption",
    "MaximizeProductExergy",
    "CustomObjective",
    "WeightedSumObjective",
    # Constraints
    "Constraint",
    "ConstraintType",
    "BoundConstraint",
    "RelativeConstraint",
    "ExergyConstraint",
    "ExergoeconomicConstraint",
    "CustomConstraint",
]
