"""
Objective function definitions for exergoeconomic optimization.

This module provides the ObjectiveFunction protocol and built-in objective
functions that can be used with the ExergoeconomicOptimizer.

All objectives are formulated for minimization. For maximization objectives
(like efficiency), the negative value is returned.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..analyses import ExergoeconomicAnalysis, ExergyAnalysis


class OptimizationSense(Enum):
    """Direction of optimization."""

    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


@dataclass
class ObjectiveResult:
    """
    Result of evaluating an objective function.

    Attributes
    ----------
    value : float
        The objective value (always formulated for minimization).
    raw_value : float
        The original value before transformation for minimization.
    name : str
        Name of the objective.
    unit : str | None
        Unit of the objective value.
    """

    value: float
    raw_value: float
    name: str
    unit: str | None = None


class ObjectiveFunction(ABC):
    """
    Abstract base class for objective functions.

    All objectives must implement the evaluate method which computes
    the objective value from exergy and/or exergoeconomic analysis results.

    Objectives are always formulated for minimization. If the natural
    sense is maximization (e.g., efficiency), the implementation should
    return the negative value.
    """

    def __init__(self, name: str, sense: OptimizationSense = OptimizationSense.MINIMIZE, unit: str | None = None):
        """
        Initialize the objective function.

        Parameters
        ----------
        name : str
            Human-readable name for the objective.
        sense : OptimizationSense
            Whether to minimize or maximize (internally converted to minimization).
        unit : str | None
            Unit of the objective value for display.
        """
        self.name = name
        self.sense = sense
        self.unit = unit

    @abstractmethod
    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        """
        Compute the raw objective value.

        Parameters
        ----------
        exergy_analysis : ExergyAnalysis
            The exergy analysis results.
        exergoeconomic_analysis : ExergoeconomicAnalysis | None
            The exergoeconomic analysis results (if available).

        Returns
        -------
        float
            The raw objective value.
        """
        ...

    def evaluate(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> ObjectiveResult:
        """
        Evaluate the objective function.

        Parameters
        ----------
        exergy_analysis : ExergyAnalysis
            The exergy analysis results.
        exergoeconomic_analysis : ExergoeconomicAnalysis | None
            The exergoeconomic analysis results (if available).

        Returns
        -------
        ObjectiveResult
            The objective evaluation result.
        """
        raw_value = self._compute(exergy_analysis, exergoeconomic_analysis)

        # Convert to minimization form
        value = -raw_value if self.sense == OptimizationSense.MAXIMIZE else raw_value

        return ObjectiveResult(value=value, raw_value=raw_value, name=self.name, unit=self.unit)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', sense={self.sense.value})"


class MinimizeExergyDestruction(ObjectiveFunction):
    """
    Minimize total exergy destruction in the system.

    This objective targets the total exergy destruction (E_D) which represents
    thermodynamic irreversibilities in the system.
    """

    def __init__(self, name: str = "Total Exergy Destruction"):
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit="W")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return exergy_analysis.E_D


class MaximizeExergyEfficiency(ObjectiveFunction):
    """
    Maximize the overall exergy efficiency of the system.

    The exergy efficiency (epsilon) is defined as E_P / E_F.
    """

    def __init__(self, name: str = "Exergy Efficiency"):
        super().__init__(name=name, sense=OptimizationSense.MAXIMIZE, unit="-")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return exergy_analysis.epsilon


class MinimizeComponentExergyDestruction(ObjectiveFunction):
    """
    Minimize exergy destruction in a specific component.

    Parameters
    ----------
    component_id : str
        The identifier of the component to target.
    """

    def __init__(self, component_id: str, name: str | None = None):
        self.component_id = component_id
        name = name or f"E_D ({component_id})"
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit="W")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if self.component_id not in exergy_analysis.components:
            raise ValueError(f"Component '{self.component_id}' not found in analysis")
        return exergy_analysis.components[self.component_id].E_D


class MaximizeComponentEfficiency(ObjectiveFunction):
    """
    Maximize the exergy efficiency of a specific component.

    Parameters
    ----------
    component_id : str
        The identifier of the component to target.
    """

    def __init__(self, component_id: str, name: str | None = None):
        self.component_id = component_id
        name = name or f"Efficiency ({component_id})"
        super().__init__(name=name, sense=OptimizationSense.MAXIMIZE, unit="-")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if self.component_id not in exergy_analysis.components:
            raise ValueError(f"Component '{self.component_id}' not found in analysis")
        return exergy_analysis.components[self.component_id].epsilon


class MinimizeTotalCost(ObjectiveFunction):
    """
    Minimize the total cost rate of the system.

    This requires exergoeconomic analysis to be performed.
    The total cost rate includes investment, operation & maintenance,
    and exergy destruction costs.
    """

    def __init__(self, name: str = "Total Cost Rate"):
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit="$/h")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if exergoeconomic_analysis is None:
            raise ValueError("ExergoeconomicAnalysis required for MinimizeTotalCost objective")
        return exergoeconomic_analysis.C_TOT


class MinimizeCostOfExergyDestruction(ObjectiveFunction):
    """
    Minimize the total cost rate associated with exergy destruction.

    This represents the economic penalty of thermodynamic irreversibilities.
    """

    def __init__(self, name: str = "Cost of Exergy Destruction"):
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit="$/h")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if exergoeconomic_analysis is None:
            raise ValueError("ExergoeconomicAnalysis required for MinimizeCostOfExergyDestruction objective")
        # Sum C_D over all components
        total_c_d = sum(comp.C_D for comp in exergoeconomic_analysis.components.values() if hasattr(comp, "C_D"))
        return total_c_d


class MinimizeLevelizedCost(ObjectiveFunction):
    """
    Minimize the levelized cost of a single product stream.

    This is computed as the specific cost (c_TOT) of the product exergy stream,
    as determined by the exergoeconomic analysis.

    Parameters
    ----------
    product_stream : str
        The connection identifier for the product stream.
    name : str
        Human-readable name for the objective.
    """

    def __init__(self, product_stream: str, name: str = "Levelized Cost"):
        self.product_stream = product_stream
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit="EUR/GJ")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if exergoeconomic_analysis is None:
            raise ValueError("ExergoeconomicAnalysis required for MinimizeLevelizedCost objective")
        if self.product_stream not in exergoeconomic_analysis.connections:
            raise ValueError(f"Product stream '{self.product_stream}' not found")

        conn = exergoeconomic_analysis.connections[self.product_stream]
        c_TOT = conn.get("c_TOT")
        if c_TOT is None:
            raise ValueError(f"Specific cost 'c_TOT' not available for stream '{self.product_stream}'")
        # c_TOT is in currency/kJ after solving; convert to currency/GJ
        return c_TOT * 1e6


class MinimizeProductSubsetCost(ObjectiveFunction):
    """
    Minimize the specific cost of a product defined as a difference of streams.

    This is the key objective for multi-product systems where each product is
    defined as a set of input and output streams (same format as the E_P
    definition in ExergyAnalysis).

    The specific cost is computed as:

        c_P = (sum C_TOT_inputs - sum C_TOT_outputs) / (sum E_inputs - sum E_outputs)

    converted to currency/GJ.

    Parameters
    ----------
    inputs : list[str]
        Connection identifiers for the product input streams (higher exergy).
    outputs : list[str]
        Connection identifiers for the product output streams (lower exergy).
    name : str
        Human-readable name for the objective.

    Examples
    --------
    For a heat pump with heating product (water heated from stream 41 to 42):

    >>> obj = MinimizeProductSubsetCost(
    ...     inputs=["42"], outputs=["41"], name="c_P Heating"
    ... )

    For a cooling product (water cooled from stream 11 to 13):

    >>> obj = MinimizeProductSubsetCost(
    ...     inputs=["13"], outputs=["11"], name="c_P Cooling"
    ... )
    """

    def __init__(
        self,
        inputs: list[str],
        outputs: list[str] | None = None,
        name: str = "Specific Product Cost",
    ):
        self.inputs = inputs
        self.outputs = outputs or []
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit="EUR/GJ")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if exergoeconomic_analysis is None:
            raise ValueError("ExergoeconomicAnalysis required for MinimizeProductSubsetCost objective")

        connections = exergoeconomic_analysis.connections

        # Sum cost rates: C_TOT is in currency/s after solving
        C_product = 0.0
        for name in self.inputs:
            if name not in connections:
                raise ValueError(f"Input stream '{name}' not found in connections")
            C_product += connections[name].get("C_TOT", 0)
        for name in self.outputs:
            if name not in connections:
                raise ValueError(f"Output stream '{name}' not found in connections")
            C_product -= connections[name].get("C_TOT", 0)

        # Sum exergy flows: E is in kW after exergy analysis
        E_product = 0.0
        for name in self.inputs:
            E_product += connections[name].get("E", 0)
        for name in self.outputs:
            E_product -= connections[name].get("E", 0)

        if E_product <= 0:
            return 1e10  # Penalty for invalid product exergy

        # c_P [currency/GJ] = C [currency/s] / E [kW=kJ/s] * 1e6
        return C_product / E_product * 1e6


class MinimizeProductCost(ObjectiveFunction):
    """
    Minimize the specific cost of the product (c_P).

    This is the key metric in exergoeconomic optimization, representing
    the unit cost of the product exergy in currency per energy unit (e.g., EUR/GJ).

    c_P is calculated as C_P / E_P * 1e9, where:
    - C_P is the total product cost rate in currency/s
    - E_P is the product exergy in W
    - 1e9 converts from currency/J to currency/GJ
    """

    def __init__(self, name: str = "Specific Product Cost"):
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit="EUR/GJ")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        if exergoeconomic_analysis is None:
            raise ValueError("ExergoeconomicAnalysis required for MinimizeProductCost objective")
        # c_P = C_P / E_P * 1e9 / 3600 (C_P in currency/h, E_P in W)
        # Formula: c (EUR/GJ) = C (EUR/h) / E (W) * 1e9 / 3600
        C_P = exergoeconomic_analysis.system_costs.get("C_P", 0)  # currency/h
        E_P = exergy_analysis.E_P  # W
        if E_P <= 0:
            return 1e10  # Penalty for invalid E_P
        return C_P / E_P * 1e9 / 3600  # currency/GJ


class MinimizeFuelConsumption(ObjectiveFunction):
    """
    Minimize the fuel exergy input to the system.
    """

    def __init__(self, name: str = "Fuel Exergy"):
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit="W")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return exergy_analysis.E_F


class MaximizeProductExergy(ObjectiveFunction):
    """
    Maximize the product exergy output from the system.
    """

    def __init__(self, name: str = "Product Exergy"):
        super().__init__(name=name, sense=OptimizationSense.MAXIMIZE, unit="W")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return exergy_analysis.E_P


class CustomObjective(ObjectiveFunction):
    """
    User-defined objective function using a callable.

    Parameters
    ----------
    func : Callable
        A function that takes (ExergyAnalysis, ExergoeconomicAnalysis | None)
        and returns a float value.
    name : str
        Name for the objective.
    sense : OptimizationSense
        Whether to minimize or maximize.
    unit : str | None
        Unit of the objective value.

    Examples
    --------
    >>> obj = CustomObjective(
    ...     func=lambda ea, eea: ea.E_D / ea.E_F,  # Exergy destruction ratio
    ...     name="Exergy Destruction Ratio",
    ...     sense=OptimizationSense.MINIMIZE,
    ... )
    """

    def __init__(
        self,
        func: Callable[[Any, Any], float],
        name: str,
        sense: OptimizationSense = OptimizationSense.MINIMIZE,
        unit: str | None = None,
    ):
        super().__init__(name=name, sense=sense, unit=unit)
        self._func = func

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        return self._func(exergy_analysis, exergoeconomic_analysis)


class WeightedSumObjective(ObjectiveFunction):
    """
    Combine multiple objectives into a single weighted sum.

    This is useful for converting multi-objective problems into single-objective
    using the weighted sum method.

    Parameters
    ----------
    objectives : list[tuple[ObjectiveFunction, float]]
        List of (objective, weight) pairs.
    name : str
        Name for the combined objective.
    """

    def __init__(self, objectives: list[tuple[ObjectiveFunction, float]], name: str = "Weighted Sum"):
        super().__init__(name=name, sense=OptimizationSense.MINIMIZE, unit=None)
        self.objectives = objectives

        # Validate weights
        total_weight = sum(w for _, w in objectives)
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(f"Weights should sum to 1.0, got {total_weight}")

    def _compute(
        self,
        exergy_analysis: ExergyAnalysis,
        exergoeconomic_analysis: ExergoeconomicAnalysis | None = None,
    ) -> float:
        total = 0.0
        for obj, weight in self.objectives:
            result = obj.evaluate(exergy_analysis, exergoeconomic_analysis)
            total += weight * result.value
        return total
