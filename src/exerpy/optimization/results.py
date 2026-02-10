"""
Optimization result classes for exergoeconomic optimization.

This module provides classes to store, analyze, and visualize optimization results,
including Pareto front handling for multi-objective optimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .constraints import Constraint
    from .objectives import ObjectiveFunction
    from .variables import DesignVariable


@dataclass
class Solution:
    """
    A single solution from the optimization.

    Attributes
    ----------
    x : np.ndarray
        The design variable values.
    f : np.ndarray
        The objective function values (in minimization form).
    g : np.ndarray | None
        The constraint violation values (if any).
    feasible : bool
        Whether this solution satisfies all constraints.
    variable_names : list[str]
        Names of the design variables.
    objective_names : list[str]
        Names of the objectives.
    constraint_names : list[str]
        Names of the constraints.
    """

    x: np.ndarray
    f: np.ndarray
    g: np.ndarray | None
    feasible: bool
    variable_names: list[str]
    objective_names: list[str]
    constraint_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert solution to a dictionary."""
        result = {
            "variables": {name: float(val) for name, val in zip(self.variable_names, self.x, strict=False)},
            "objectives": {name: float(val) for name, val in zip(self.objective_names, self.f, strict=False)},
            "feasible": self.feasible,
        }
        if self.g is not None and len(self.constraint_names) > 0:
            result["constraints"] = {name: float(val) for name, val in zip(self.constraint_names, self.g, strict=False)}
        return result

    def __repr__(self) -> str:
        var_str = ", ".join(f"{n}={v:.4g}" for n, v in zip(self.variable_names, self.x, strict=False))
        obj_str = ", ".join(f"{n}={v:.4g}" for n, v in zip(self.objective_names, self.f, strict=False))
        return f"Solution(variables=[{var_str}], objectives=[{obj_str}], feasible={self.feasible})"


@dataclass
class OptimizationResult:
    """
    Results from an optimization run.

    This class stores all solutions, the Pareto front (for multi-objective),
    and provides methods for analysis and visualization.

    Attributes
    ----------
    variables : list[DesignVariable]
        The design variables used in optimization.
    objectives : list[ObjectiveFunction]
        The objective functions used.
    constraints : list[Constraint]
        The constraints used.
    solutions : list[Solution]
        All feasible solutions found.
    pareto_front : list[Solution]
        Non-dominated solutions (for multi-objective optimization).
    best_solution : Solution | None
        The best solution (for single-objective) or first Pareto solution.
    n_generations : int
        Number of generations run.
    n_evaluations : int
        Total number of function evaluations.
    algorithm : str
        Name of the optimization algorithm used.
    termination_reason : str
        Reason for termination.
    history : dict[str, Any]
        Optional history data from the optimization.
    """

    variables: list[DesignVariable]
    objectives: list[ObjectiveFunction]
    constraints: list[Constraint]
    solutions: list[Solution]
    pareto_front: list[Solution]
    best_solution: Solution | None
    n_generations: int
    n_evaluations: int
    algorithm: str
    termination_reason: str = "max_gen"
    history: dict[str, Any] = field(default_factory=dict)
    baseline_values: dict[str, float] | None = None

    @property
    def n_objectives(self) -> int:
        """Number of objectives."""
        return len(self.objectives)

    @property
    def n_variables(self) -> int:
        """Number of design variables."""
        return len(self.variables)

    @property
    def n_constraints(self) -> int:
        """Number of constraints."""
        return len(self.constraints)

    @property
    def is_multi_objective(self) -> bool:
        """Whether this is a multi-objective optimization result."""
        return self.n_objectives > 1

    def get_pareto_dataframe(self) -> pd.DataFrame:
        """
        Get the Pareto front as a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with variables and objectives for each Pareto solution.
        """
        if not self.pareto_front:
            return pd.DataFrame()

        data = []
        for sol in self.pareto_front:
            row = {}
            for name, val in zip(sol.variable_names, sol.x, strict=False):
                row[f"var_{name}"] = val
            for name, val in zip(sol.objective_names, sol.f, strict=False):
                row[f"obj_{name}"] = val
            row["feasible"] = sol.feasible
            data.append(row)

        return pd.DataFrame(data)

    def get_solutions_dataframe(self) -> pd.DataFrame:
        """
        Get all solutions as a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with variables and objectives for all solutions.
        """
        if not self.solutions:
            return pd.DataFrame()

        data = []
        for sol in self.solutions:
            row = {}
            for name, val in zip(sol.variable_names, sol.x, strict=False):
                row[f"var_{name}"] = val
            for name, val in zip(sol.objective_names, sol.f, strict=False):
                row[f"obj_{name}"] = val
            row["feasible"] = sol.feasible
            data.append(row)

        return pd.DataFrame(data)

    def plot_pareto(
        self,
        objective_indices: tuple[int, int] = (0, 1),
        ax: Any = None,
        show_all: bool = False,
        figsize: tuple[float, float] = (10, 8),
        **kwargs,
    ) -> Any:
        """
        Plot the Pareto front for 2D visualization.

        Parameters
        ----------
        objective_indices : tuple[int, int]
            Indices of the two objectives to plot (default: first two).
        ax : matplotlib.axes.Axes | None
            Axes to plot on. If None, creates a new figure.
        show_all : bool
            If True, also shows non-Pareto solutions in gray.
        figsize : tuple[float, float]
            Figure size if creating new figure.
        **kwargs
            Additional arguments passed to scatter plot.

        Returns
        -------
        matplotlib.axes.Axes
            The axes object.
        """
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)

        i, j = objective_indices

        if show_all and self.solutions:
            all_f = np.array([sol.f for sol in self.solutions])
            ax.scatter(all_f[:, i], all_f[:, j], c="lightgray", alpha=0.5, label="All solutions", **kwargs)

        if self.pareto_front:
            pareto_f = np.array([sol.f for sol in self.pareto_front])
            ax.scatter(pareto_f[:, i], pareto_f[:, j], c="red", marker="o", label="Pareto front", **kwargs)

        ax.set_xlabel(self.objectives[i].name)
        ax.set_ylabel(self.objectives[j].name)
        ax.set_title("Pareto Front")
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax

    def plot_convergence(
        self,
        objective_index: int = 0,
        ax: Any = None,
        figsize: tuple[float, float] = (10, 6),
    ) -> Any:
        """
        Plot the convergence history.

        Parameters
        ----------
        objective_index : int
            Index of the objective to plot.
        ax : matplotlib.axes.Axes | None
            Axes to plot on. If None, creates a new figure.
        figsize : tuple[float, float]
            Figure size if creating new figure.

        Returns
        -------
        matplotlib.axes.Axes
            The axes object.
        """
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)

        if "best_per_generation" not in self.history:
            ax.text(
                0.5,
                0.5,
                "No convergence history available",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            return ax

        best_values = self.history["best_per_generation"]
        if isinstance(best_values[0], (list, np.ndarray)):
            # Multi-objective: extract specific objective
            values = [gen[objective_index] for gen in best_values]
        else:
            values = best_values

        generations = range(1, len(values) + 1)
        ax.plot(generations, values, "b-", linewidth=2)
        ax.set_xlabel("Generation")
        ax.set_ylabel(self.objectives[objective_index].name)
        ax.set_title("Convergence History")
        ax.grid(True, alpha=0.3)

        return ax

    def plot_parallel_coordinates(
        self,
        include_objectives: bool = True,
        ax: Any = None,
        figsize: tuple[float, float] = (12, 6),
        colormap: str = "viridis",
    ) -> Any:
        """
        Plot parallel coordinates of Pareto solutions.

        Parameters
        ----------
        include_objectives : bool
            If True, includes objectives in the plot.
        ax : matplotlib.axes.Axes | None
            Axes to plot on. If None, creates a new figure.
        figsize : tuple[float, float]
            Figure size if creating new figure.
        colormap : str
            Colormap to use for coloring lines.

        Returns
        -------
        matplotlib.axes.Axes
            The axes object.
        """
        import matplotlib.pyplot as plt
        from matplotlib.colors import Normalize

        if not self.pareto_front:
            return None

        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)

        # Collect data
        var_names = self.pareto_front[0].variable_names
        obj_names = self.pareto_front[0].objective_names if include_objectives else []

        all_names = list(var_names) + list(obj_names)
        n_dims = len(all_names)

        # Normalize data for each dimension
        data = []
        for sol in self.pareto_front:
            row = list(sol.x)
            if include_objectives:
                row.extend(sol.f)
            data.append(row)
        data = np.array(data)

        # Normalize each column to [0, 1]
        mins = data.min(axis=0)
        maxs = data.max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1  # Avoid division by zero
        normalized = (data - mins) / ranges

        # Color by first objective
        cmap = plt.get_cmap(colormap)
        norm = Normalize(vmin=data[:, -len(obj_names)].min(), vmax=data[:, -len(obj_names)].max())

        # Plot lines
        x = range(n_dims)
        for i, row in enumerate(normalized):
            color = cmap(norm(data[i, len(var_names)])) if include_objectives else cmap(i / len(normalized))
            ax.plot(x, row, c=color, alpha=0.7)

        # Set up axes
        ax.set_xticks(x)
        ax.set_xticklabels(all_names, rotation=45, ha="right")
        ax.set_ylabel("Normalized Value")
        ax.set_title("Parallel Coordinates (Pareto Front)")

        # Add min/max labels
        for i, name in enumerate(all_names):
            ax.annotate(f"{mins[i]:.3g}", (i, -0.05), ha="center", fontsize=8)
            ax.annotate(f"{maxs[i]:.3g}", (i, 1.05), ha="center", fontsize=8)

        ax.set_ylim(-0.1, 1.15)
        ax.grid(True, alpha=0.3, axis="y")

        return ax

    def summary(self) -> str:
        """
        Get a text summary of the optimization results.

        Returns
        -------
        str
            Summary string.
        """
        lines = [
            "=" * 70,
            "OPTIMIZATION RESULTS",
            "=" * 70,
            f"Algorithm: {self.algorithm}",
            f"Generations: {self.n_generations}",
            f"Function evaluations: {self.n_evaluations}",
            f"Termination: {self.termination_reason}",
            "",
            f"Variables: {self.n_variables}",
            f"Objectives: {self.n_objectives}",
            f"Constraints: {self.n_constraints}",
            "",
            f"Feasible solutions found: {len(self.solutions)}",
            f"Pareto front size: {len(self.pareto_front)}",
        ]

        if self.best_solution is not None:
            lines.append("")
            lines.append("Optimal Solution:")
            lines.append("-" * 70)

            # Variables with units
            for i, (name, val) in enumerate(zip(self.best_solution.variable_names, self.best_solution.x, strict=False)):
                unit = self.variables[i].unit if i < len(self.variables) and self.variables[i].unit else ""
                unit_str = f" {unit}" if unit else ""
                lines.append(f"  {name}: {val:.4f}{unit_str}")

            lines.append("")
            lines.append("Objective Values:")
            for i, (name, val) in enumerate(
                zip(self.best_solution.objective_names, self.best_solution.f, strict=False)
            ):
                unit = self.objectives[i].unit if i < len(self.objectives) and self.objectives[i].unit else ""
                unit_str = f" {unit}" if unit else ""
                lines.append(f"  {name}: {val:.4f}{unit_str}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print the optimization results summary to console."""
        print(self.summary())

    def print_comparison(
        self,
        baseline_values: dict[str, float] | None = None,
        variable_units: dict[str, str] | None = None,
    ) -> None:
        """
        Print a comparison table between baseline and optimal values.

        Parameters
        ----------
        baseline_values : dict[str, float] | None
            Dictionary mapping variable/objective names to their baseline values.
            If None, uses the baseline_values stored during optimization.
        variable_units : dict[str, str] | None
            Optional dictionary mapping names to their units.
        """
        if self.best_solution is None:
            print("No optimal solution found.")
            return

        # Use stored baseline if not provided
        baseline = baseline_values if baseline_values is not None else self.baseline_values
        if baseline is None:
            print("No baseline values available for comparison.")
            return

        units = variable_units or {}

        print("\n" + "=" * 75)
        print("OPTIMIZATION COMPARISON")
        print("=" * 75)
        print(f"{'Parameter':<30} {'Baseline':>15} {'Optimal':>15} {'Change':>12}")
        print("-" * 75)

        # Print variables
        for i, (name, opt_val) in enumerate(zip(self.best_solution.variable_names, self.best_solution.x, strict=False)):
            if name in baseline:
                base_val = baseline[name]
                change = opt_val - base_val
                unit = units.get(name, "")
                if i < len(self.variables) and self.variables[i].unit:
                    unit = self.variables[i].unit
                param_str = f"{name} [{unit}]" if unit else name
                print(f"{param_str:<30} {base_val:>15.4f} {opt_val:>15.4f} {change:>+12.4f}")

        # Print objectives
        for i, (name, opt_val) in enumerate(
            zip(self.best_solution.objective_names, self.best_solution.f, strict=False)
        ):
            if name in baseline:
                base_val = baseline[name]
                change = opt_val - base_val
                unit = units.get(name, "")
                if i < len(self.objectives) and self.objectives[i].unit:
                    unit = self.objectives[i].unit
                param_str = f"{name} [{unit}]" if unit else name
                print(f"{param_str:<30} {base_val:>15.4f} {opt_val:>15.4f} {change:>+12.4f}")

        print("=" * 75)

        # Print improvement for single objective
        if len(self.objectives) == 1:
            obj_name = self.best_solution.objective_names[0]
            if obj_name in baseline:
                base_val = baseline[obj_name]
                opt_val = self.best_solution.f[0]
                if base_val != 0:
                    improvement = (base_val - opt_val) / abs(base_val) * 100
                    direction = "reduction" if improvement > 0 else "increase"
                    print(f"\n{obj_name} {direction}: {abs(improvement):.2f}%")

    def to_json(self) -> dict[str, Any]:
        """
        Convert results to a JSON-serializable dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of results.
        """
        return {
            "algorithm": self.algorithm,
            "n_generations": self.n_generations,
            "n_evaluations": self.n_evaluations,
            "termination_reason": self.termination_reason,
            "n_variables": self.n_variables,
            "n_objectives": self.n_objectives,
            "n_constraints": self.n_constraints,
            "variable_names": [v.name for v in self.variables],
            "objective_names": [o.name for o in self.objectives],
            "constraint_names": [c.name for c in self.constraints],
            "pareto_front": [sol.to_dict() for sol in self.pareto_front],
            "best_solution": self.best_solution.to_dict() if self.best_solution else None,
        }

    def __repr__(self) -> str:
        return (
            f"OptimizationResult(algorithm='{self.algorithm}', "
            f"n_solutions={len(self.solutions)}, "
            f"pareto_size={len(self.pareto_front)})"
        )
