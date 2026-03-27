"""
Optimization result classes for exergoeconomic optimization.

This module provides classes to store, analyze, and visualize optimization results,
including Pareto front handling for multi-objective optimization.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .constraints import Constraint
    from .objectives import ObjectiveFunction
    from .variables import DesignVariable

logger = logging.getLogger(__name__)


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
    diagnostics: dict[str, Any] = field(default_factory=dict)

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
    baseline_diagnostics: dict | None = None

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

        # Print improvement summary
        if len(self.objectives) == 1:
            obj_name = self.best_solution.objective_names[0]
            if obj_name in baseline:
                base_val = baseline[obj_name]
                opt_val = self.best_solution.f[0]
                if base_val != 0:
                    improvement = (base_val - opt_val) / abs(base_val) * 100
                    direction = "reduction" if improvement > 0 else "increase"
                    print(f"\n{obj_name} {direction}: {abs(improvement):.2f}%")
        elif len(self.objectives) > 1 and self.pareto_front:
            print(f"\nMulti-objective result: {len(self.pareto_front)} Pareto-optimal solutions")
            pareto_f = np.array([sol.f for sol in self.pareto_front])
            for i, obj in enumerate(self.objectives):
                unit = obj.unit if obj.unit else ""
                unit_str = f" {unit}" if unit else ""
                obj_min = pareto_f[:, i].min()
                obj_max = pareto_f[:, i].max()
                print(f"  {obj.name}: [{obj_min:.4f}, {obj_max:.4f}]{unit_str}")

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

    def save(self, filepath: str | Path) -> None:
        """
        Save optimization results to a JSON file for later analysis.

        The saved file contains all solution data, diagnostics, baseline values,
        and metadata needed to recreate plots and tables without re-running
        the optimization.

        Parameters
        ----------
        filepath : str | Path
            Path to the output JSON file. The .json extension is added
            automatically if not present.
        """
        filepath = Path(filepath)
        if filepath.suffix != ".json":
            filepath = filepath.with_suffix(".json")

        def _solution_to_dict(sol: Solution) -> dict:
            return {
                "x": sol.x.tolist(),
                "f": sol.f.tolist(),
                "g": sol.g.tolist() if sol.g is not None else None,
                "feasible": sol.feasible,
                "variable_names": sol.variable_names,
                "objective_names": sol.objective_names,
                "constraint_names": sol.constraint_names,
                "diagnostics": sol.diagnostics,
            }

        data = {
            "algorithm": self.algorithm,
            "n_generations": self.n_generations,
            "n_evaluations": self.n_evaluations,
            "termination_reason": self.termination_reason,
            "variables": [
                {
                    "name": v.name,
                    "target_type": v.target_type.value,
                    "target_id": v.target_id,
                    "parameter": v.parameter,
                    "bounds": list(v.bounds),
                    "initial": v.initial,
                    "unit": v.unit,
                    "description": v.description,
                }
                for v in self.variables
            ],
            "objectives": [
                {
                    "name": o.name,
                    "unit": getattr(o, "unit", None),
                    "class": type(o).__name__,
                }
                for o in self.objectives
            ],
            "constraints": [
                {
                    "name": c.name,
                    "class": type(c).__name__,
                }
                for c in self.constraints
            ],
            "solutions": [_solution_to_dict(sol) for sol in self.solutions],
            "pareto_front": [_solution_to_dict(sol) for sol in self.pareto_front],
            "best_solution": _solution_to_dict(self.best_solution) if self.best_solution else None,
            "baseline_values": self.baseline_values,
            "baseline_diagnostics": self.baseline_diagnostics,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Results saved to {filepath}")
        print(f"Results saved to {filepath}")

    @classmethod
    def load(cls, filepath: str | Path) -> OptimizationResult:
        """
        Load optimization results from a previously saved JSON file.

        The loaded result supports all plotting and printing methods.
        Note that objective/constraint objects are replaced with lightweight
        stubs since the original callable objects cannot be serialized.

        Parameters
        ----------
        filepath : str | Path
            Path to the JSON file saved by ``save()``.

        Returns
        -------
        OptimizationResult
            The loaded optimization result.
        """
        from .variables import DesignVariable

        filepath = Path(filepath)
        with open(filepath) as f:
            data = json.load(f)

        def _dict_to_solution(d: dict) -> Solution:
            return Solution(
                x=np.array(d["x"]),
                f=np.array(d["f"]),
                g=np.array(d["g"]) if d["g"] is not None else None,
                feasible=d["feasible"],
                variable_names=d["variable_names"],
                objective_names=d["objective_names"],
                constraint_names=d.get("constraint_names", []),
                diagnostics=d.get("diagnostics", {}),
            )

        # Reconstruct DesignVariable objects
        variables = []
        for vd in data["variables"]:
            variables.append(
                DesignVariable(
                    name=vd["name"],
                    target_type=vd["target_type"],
                    target_id=vd["target_id"],
                    parameter=vd["parameter"],
                    bounds=tuple(vd["bounds"]),
                    initial=vd.get("initial"),
                    unit=vd.get("unit"),
                    description=vd.get("description"),
                )
            )

        # Use lightweight stubs for objectives and constraints (only need .name and .unit)
        objectives = [_ObjectiveStub(o["name"], o.get("unit")) for o in data["objectives"]]
        constraints = [_ConstraintStub(c["name"]) for c in data["constraints"]]

        solutions = [_dict_to_solution(d) for d in data["solutions"]]
        pareto_front = [_dict_to_solution(d) for d in data["pareto_front"]]
        best_solution = _dict_to_solution(data["best_solution"]) if data["best_solution"] else None

        result = cls(
            variables=variables,
            objectives=objectives,
            constraints=constraints,
            solutions=solutions,
            pareto_front=pareto_front,
            best_solution=best_solution,
            n_generations=data["n_generations"],
            n_evaluations=data["n_evaluations"],
            algorithm=data["algorithm"],
            termination_reason=data.get("termination_reason", "loaded"),
            baseline_values=data.get("baseline_values"),
            baseline_diagnostics=data.get("baseline_diagnostics"),
        )

        logger.info(f"Results loaded from {filepath}")
        return result

    def plot_variable_influence(
        self,
        figsize_per_plot: tuple[float, float] = (5, 4),
        colormap: str = "viridis",
        use_pareto: bool = True,
    ) -> Any:
        """
        Plot the influence of each design variable on each objective.

        Creates a grid of scatter plots (n_variables x n_objectives) where each
        subplot shows one variable vs. one objective, colored by the other objective
        (for multi-objective problems) or in a single color (for single-objective).

        Parameters
        ----------
        figsize_per_plot : tuple[float, float]
            Size of each individual subplot.
        colormap : str
            Matplotlib colormap name for coloring points.
        use_pareto : bool
            If True, plots only Pareto front solutions. If False, plots all solutions.

        Returns
        -------
        matplotlib.figure.Figure
            The figure object.
        """
        import matplotlib.pyplot as plt
        from matplotlib.colors import Normalize

        solutions = self.pareto_front if use_pareto and self.pareto_front else self.solutions
        if not solutions:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No solutions available", ha="center", va="center", transform=ax.transAxes)
            return fig

        n_vars = self.n_variables
        n_objs = self.n_objectives

        x_data = np.array([sol.x for sol in solutions])
        f_data = np.array([sol.f for sol in solutions])

        fig, axes = plt.subplots(
            n_objs,
            n_vars,
            figsize=(figsize_per_plot[0] * n_vars, figsize_per_plot[1] * n_objs),
            squeeze=False,
        )

        for j in range(n_objs):
            # Color by the other objective (if multi-objective), else by the objective itself
            if n_objs > 1:
                color_obj_idx = 1 - j if n_objs == 2 else (j + 1) % n_objs
                c_values = f_data[:, color_obj_idx]
                color_label = self.objectives[color_obj_idx].name
            else:
                c_values = f_data[:, 0]
                color_label = self.objectives[0].name

            norm = Normalize(vmin=c_values.min(), vmax=c_values.max())

            for i in range(n_vars):
                ax = axes[j, i]
                sc = ax.scatter(
                    x_data[:, i],
                    f_data[:, j],
                    c=c_values,
                    cmap=colormap,
                    norm=norm,
                    edgecolors="k",
                    linewidths=0.3,
                    s=40,
                    alpha=0.85,
                )

                var = self.variables[i]
                obj = self.objectives[j]
                var_label = f"{var.name} [{var.unit}]" if var.unit else var.name
                obj_label = f"{obj.name} [{obj.unit}]" if obj.unit else obj.name

                ax.set_xlabel(var_label, fontsize=9)
                ax.set_ylabel(obj_label, fontsize=9)
                ax.tick_params(labelsize=8)
                ax.grid(True, alpha=0.3)

            # Add colorbar for this row
            cbar = fig.colorbar(sc, ax=axes[j, :].tolist(), shrink=0.8, pad=0.02)
            color_unit = self.objectives[color_obj_idx].unit if n_objs > 1 else self.objectives[0].unit
            cbar_label = f"{color_label} [{color_unit}]" if color_unit else color_label
            cbar.set_label(cbar_label, fontsize=9)

        source = "Pareto front" if use_pareto and self.pareto_front else "All solutions"
        fig.suptitle(f"Variable Influence on Objectives ({source}, n={len(solutions)})", fontsize=13, y=1.01)
        fig.tight_layout()
        return fig

    def plot_correlation_matrix(
        self,
        use_pareto: bool = True,
        figsize: tuple[float, float] | None = None,
        colormap: str = "RdBu_r",
    ) -> Any:
        """
        Plot a correlation heatmap between all variables and objectives.

        Parameters
        ----------
        use_pareto : bool
            If True, uses only Pareto front solutions.
        figsize : tuple[float, float] | None
            Figure size. If None, auto-sized based on number of parameters.
        colormap : str
            Matplotlib colormap name.

        Returns
        -------
        matplotlib.figure.Figure
            The figure object.
        """
        import matplotlib.pyplot as plt

        solutions = self.pareto_front if use_pareto and self.pareto_front else self.solutions
        if not solutions:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No solutions available", ha="center", va="center", transform=ax.transAxes)
            return fig

        # Build labels
        var_labels = []
        for v in self.variables:
            var_labels.append(f"{v.name} [{v.unit}]" if v.unit else v.name)
        obj_labels = []
        for o in self.objectives:
            obj_labels.append(f"{o.name} [{o.unit}]" if o.unit else o.name)
        all_labels = var_labels + obj_labels

        # Build data matrix
        x_data = np.array([sol.x for sol in solutions])
        f_data = np.array([sol.f for sol in solutions])
        data = np.hstack([x_data, f_data])

        # Compute correlation
        corr = np.corrcoef(data, rowvar=False)
        n = len(all_labels)

        if figsize is None:
            size = max(6, n * 0.9)
            figsize = (size, size)

        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(corr, cmap=colormap, vmin=-1, vmax=1, aspect="equal")

        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(all_labels, rotation=45, ha="right", fontsize=9)
        ax.set_yticklabels(all_labels, fontsize=9)

        # Annotate cells
        for i in range(n):
            for j in range(n):
                color = "white" if abs(corr[i, j]) > 0.6 else "black"
                ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=8, color=color)

        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("Pearson Correlation", fontsize=10)

        # Draw separator lines between variables and objectives
        n_vars = self.n_variables
        ax.axhline(y=n_vars - 0.5, color="k", linewidth=1.5)
        ax.axvline(x=n_vars - 0.5, color="k", linewidth=1.5)

        source = "Pareto front" if use_pareto and self.pareto_front else "All solutions"
        ax.set_title(f"Correlation Matrix ({source}, n={len(solutions)})", fontsize=12, pad=12)
        fig.tight_layout()
        return fig

    def plot_pairwise_objectives(
        self,
        use_pareto: bool = True,
        figsize_per_plot: tuple[float, float] = (5, 4),
        colormap: str = "viridis",
    ) -> Any:
        """
        Plot pairwise objective trade-offs colored by each design variable.

        For a bi-objective problem, creates one row per variable, each showing
        the Pareto front colored by that variable's value.

        Parameters
        ----------
        use_pareto : bool
            If True, plots only Pareto front solutions.
        figsize_per_plot : tuple[float, float]
            Size of each individual subplot.
        colormap : str
            Matplotlib colormap name.

        Returns
        -------
        matplotlib.figure.Figure
            The figure object.
        """
        import matplotlib.pyplot as plt
        from matplotlib.colors import Normalize

        solutions = self.pareto_front if use_pareto and self.pareto_front else self.solutions
        if not solutions or self.n_objectives < 2:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Need multi-objective results", ha="center", va="center", transform=ax.transAxes)
            return fig

        n_vars = self.n_variables
        x_data = np.array([sol.x for sol in solutions])
        f_data = np.array([sol.f for sol in solutions])

        # For >2 objectives, generate all pairs; for 2, just one pair
        from itertools import combinations

        obj_pairs = list(combinations(range(self.n_objectives), 2))
        n_pairs = len(obj_pairs)

        fig, axes = plt.subplots(
            n_vars,
            n_pairs,
            figsize=(figsize_per_plot[0] * n_pairs, figsize_per_plot[1] * n_vars),
            squeeze=False,
        )

        for col, (oi, oj) in enumerate(obj_pairs):
            obj_i = self.objectives[oi]
            obj_j = self.objectives[oj]
            xlabel = f"{obj_i.name} [{obj_i.unit}]" if obj_i.unit else obj_i.name
            ylabel = f"{obj_j.name} [{obj_j.unit}]" if obj_j.unit else obj_j.name

            for row in range(n_vars):
                ax = axes[row, col]
                var = self.variables[row]
                c_values = x_data[:, row]
                norm = Normalize(vmin=c_values.min(), vmax=c_values.max())

                sc = ax.scatter(
                    f_data[:, oi],
                    f_data[:, oj],
                    c=c_values,
                    cmap=colormap,
                    norm=norm,
                    edgecolors="k",
                    linewidths=0.3,
                    s=40,
                    alpha=0.85,
                )

                ax.set_xlabel(xlabel, fontsize=9)
                ax.set_ylabel(ylabel, fontsize=9)
                ax.tick_params(labelsize=8)
                ax.grid(True, alpha=0.3)

                cbar = fig.colorbar(sc, ax=ax, shrink=0.9, pad=0.02)
                var_label = f"{var.name} [{var.unit}]" if var.unit else var.name
                cbar.set_label(var_label, fontsize=8)

        source = "Pareto front" if use_pareto and self.pareto_front else "All solutions"
        fig.suptitle(f"Objective Trade-offs by Variable ({source}, n={len(solutions)})", fontsize=13, y=1.01)
        fig.tight_layout()
        return fig

    def plot_exergoeconomic_diagnostics(
        self,
        use_pareto: bool = True,
        figsize: tuple[float, float] | None = None,
    ) -> Any:
        """
        Plot exergoeconomic f-factor and r-factor diagnostics across Pareto solutions.

        Shows how the exergoeconomic factors (f and r) of each component vary
        across the Pareto front. This reveals whether the optimization produced
        exergoeconomically balanced designs and highlights components where
        investment and destruction costs are imbalanced.

        The plot consists of two subplots:
        - Top: f-factor (exergoeconomic factor) per component across solutions.
          f close to 0 = destruction-dominated, f close to 1 = investment-dominated.
          A horizontal band at f=0.25-0.75 marks the "balanced" zone.
        - Bottom: r-factor (relative cost difference) per component across solutions.
          High r = component is a cost bottleneck.

        Parameters
        ----------
        use_pareto : bool
            If True, uses only Pareto front solutions.
        figsize : tuple[float, float] | None
            Figure size. If None, auto-sized.

        Returns
        -------
        matplotlib.figure.Figure
            The figure object.
        """
        import matplotlib.pyplot as plt

        solutions = self.pareto_front if use_pareto and self.pareto_front else self.solutions
        # Filter solutions that have diagnostics with component data
        solutions = [s for s in solutions if s.diagnostics.get("components")]
        if not solutions:
            fig, ax = plt.subplots()
            ax.text(
                0.5, 0.5, "No exergoeconomic diagnostics available", ha="center", va="center", transform=ax.transAxes
            )
            return fig

        # Collect all component names that appear in any solution
        all_components = set()
        for sol in solutions:
            all_components.update(sol.diagnostics["components"].keys())
        comp_names = sorted(all_components)

        n_sol = len(solutions)
        n_comp = len(comp_names)

        # Build f and r matrices: (n_solutions x n_components)
        f_matrix = np.full((n_sol, n_comp), np.nan)
        r_matrix = np.full((n_sol, n_comp), np.nan)

        for i, sol in enumerate(solutions):
            for j, comp in enumerate(comp_names):
                data = sol.diagnostics["components"].get(comp, {})
                if data.get("f") is not None:
                    f_matrix[i, j] = data["f"]
                if data.get("r") is not None:
                    r_matrix[i, j] = data["r"]

        # Sort solutions by first objective for consistent x-axis
        sort_idx = np.argsort([sol.f[0] for sol in solutions])
        f_matrix = f_matrix[sort_idx]
        r_matrix = r_matrix[sort_idx]
        sorted_obj_values = np.array([solutions[i].f[0] for i in sort_idx])

        if figsize is None:
            figsize = (max(10, n_comp * 1.2), 10)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True)

        # Use first objective as x-axis label
        obj0 = self.objectives[0]
        xlabel = f"{obj0.name} [{obj0.unit}]" if obj0.unit else obj0.name

        # Color palette for components
        cmap = plt.get_cmap("tab10" if n_comp <= 10 else "tab20")
        colors = [cmap(i % cmap.N) for i in range(n_comp)]

        # --- Top plot: f-factor ---
        for j, comp in enumerate(comp_names):
            valid = ~np.isnan(f_matrix[:, j])
            if valid.any():
                ax1.plot(sorted_obj_values[valid], f_matrix[valid, j], "o-", color=colors[j], label=comp, markersize=4)

        # Balanced zone
        ax1.axhspan(0.25, 0.75, alpha=0.1, color="green", label="Balanced zone")
        ax1.axhline(y=0.5, color="green", linestyle="--", alpha=0.4)
        ax1.set_ylabel("f-factor [-]", fontsize=11)
        ax1.set_ylim(-0.05, 1.05)
        ax1.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.set_title("Exergoeconomic Factor (f): Investment vs. Destruction Balance", fontsize=12)

        # --- Bottom plot: r-factor ---
        for j, comp in enumerate(comp_names):
            valid = ~np.isnan(r_matrix[:, j])
            if valid.any():
                ax2.plot(sorted_obj_values[valid], r_matrix[valid, j], "s-", color=colors[j], label=comp, markersize=4)

        ax2.set_ylabel("r-factor [-]", fontsize=11)
        ax2.set_xlabel(xlabel, fontsize=11)
        ax2.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.set_title("Relative Cost Difference (r): Cost Bottleneck Indicator", fontsize=12)

        source = "Pareto front" if use_pareto and self.pareto_front else "All solutions"
        fig.suptitle(f"Exergoeconomic Diagnostics ({source}, n={n_sol})", fontsize=13, y=1.01)
        fig.tight_layout()
        return fig

    def print_exergoeconomic_diagnostics(
        self,
        use_pareto: bool = True,
    ) -> None:
        """
        Print a summary table of exergoeconomic diagnostics for Pareto solutions.

        Shows the range of f and r values for each component across all Pareto
        solutions, highlighting components that are consistently imbalanced.

        Parameters
        ----------
        use_pareto : bool
            If True, uses only Pareto front solutions.
        """
        solutions = self.pareto_front if use_pareto and self.pareto_front else self.solutions
        solutions = [s for s in solutions if s.diagnostics.get("components")]
        if not solutions:
            print("No exergoeconomic diagnostics available.")
            return

        # Collect data per component
        comp_data: dict[str, dict[str, list]] = {}
        for sol in solutions:
            for comp_name, data in sol.diagnostics["components"].items():
                if comp_name not in comp_data:
                    comp_data[comp_name] = {"f": [], "r": [], "C_D": [], "Z": []}
                for key in ("f", "r", "C_D", "Z"):
                    if data.get(key) is not None:
                        comp_data[comp_name][key].append(data[key])

        print("\n" + "=" * 90)
        print("EXERGOECONOMIC DIAGNOSTICS ACROSS PARETO FRONT")
        print("=" * 90)
        print(
            f"{'Component':<20} {'f_min':>8} {'f_max':>8} {'f_mean':>8} {'r_min':>8} {'r_max':>8} {'r_mean':>8} {'Note'}"
        )
        print("-" * 90)

        for comp_name in sorted(comp_data.keys()):
            data = comp_data[comp_name]
            f_vals = data["f"]
            r_vals = data["r"]

            if not f_vals or not r_vals:
                continue

            f_min, f_max, f_mean = min(f_vals), max(f_vals), sum(f_vals) / len(f_vals)
            r_min, r_max, r_mean = min(r_vals), max(r_vals), sum(r_vals) / len(r_vals)

            # Diagnostic note
            note = ""
            if f_mean < 0.25:
                note = "Destruction-dominated -> invest more"
            elif f_mean > 0.75:
                note = "Investment-dominated -> accept more E_D"
            elif abs(f_max - f_min) > 0.3:
                note = "Sensitive to design point"

            print(
                f"{comp_name:<20} {f_min:>8.3f} {f_max:>8.3f} {f_mean:>8.3f} "
                f"{r_min:>8.3f} {r_max:>8.3f} {r_mean:>8.3f} {note}"
            )

        print("=" * 90)
        print("f < 0.25: destruction cost dominates -> improve component efficiency")
        print("f > 0.75: investment cost dominates -> use cheaper/simpler equipment")
        print("High r: component is a major cost bottleneck")

    def get_component_comparison_dataframe(
        self,
        solution_index: int | None = None,
        use_pareto: bool = True,
    ) -> pd.DataFrame:
        """
        Get a DataFrame comparing baseline and optimized component-level exergoeconomic data.

        Parameters
        ----------
        solution_index : int | None
            Index of the Pareto solution to compare against. If None, shows
            the Pareto range (min–max) for each parameter.
        use_pareto : bool
            If True, selects from Pareto front solutions.

        Returns
        -------
        pd.DataFrame
            Comparison DataFrame with columns for each exergoeconomic parameter.
        """
        if self.baseline_diagnostics is None or not self.baseline_diagnostics.get("components"):
            return pd.DataFrame()

        solutions = self.pareto_front if use_pareto and self.pareto_front else self.solutions
        solutions = [s for s in solutions if s.diagnostics.get("components")]
        if not solutions:
            return pd.DataFrame()

        baseline_comps = self.baseline_diagnostics["components"]
        params = ["epsilon", "E_D", "y", "y_star", "c_F", "c_P", "C_D", "Z", "r", "f"]

        rows = []
        for comp_name in sorted(baseline_comps.keys()):
            base = baseline_comps[comp_name]

            if solution_index is not None:
                # Compare against a specific solution
                sol = solutions[solution_index]
                opt = sol.diagnostics.get("components", {}).get(comp_name, {})
                row = {"Component": comp_name}
                for p in params:
                    base_val = base.get(p)
                    opt_val = opt.get(p)
                    row[f"{p}_base"] = base_val
                    row[f"{p}_opt"] = opt_val
                    if base_val is not None and opt_val is not None and base_val != 0:
                        row[f"{p}_change_%"] = (opt_val - base_val) / abs(base_val) * 100
                    else:
                        row[f"{p}_change_%"] = None
                rows.append(row)
            else:
                # Show Pareto range
                row = {"Component": comp_name}
                for p in params:
                    base_val = base.get(p)
                    row[f"{p}_base"] = base_val
                    vals = [
                        s.diagnostics["components"].get(comp_name, {}).get(p)
                        for s in solutions
                        if s.diagnostics.get("components", {}).get(comp_name, {}).get(p) is not None
                    ]
                    if vals:
                        row[f"{p}_min"] = min(vals)
                        row[f"{p}_max"] = max(vals)
                    else:
                        row[f"{p}_min"] = None
                        row[f"{p}_max"] = None
                rows.append(row)

        return pd.DataFrame(rows)

    def print_component_comparison(
        self,
        solution_index: int | None = None,
        use_pareto: bool = True,
    ) -> None:
        """
        Print a comparison table of component exergoeconomic parameters
        between the baseline and optimized design(s).

        Parameters
        ----------
        solution_index : int | None
            Index of the Pareto solution to compare against. If None, shows
            the Pareto range (min–max) for each parameter.
        use_pareto : bool
            If True, selects from Pareto front solutions.
        """
        if self.baseline_diagnostics is None or not self.baseline_diagnostics.get("components"):
            print("No baseline diagnostics available.")
            return

        solutions = self.pareto_front if use_pareto and self.pareto_front else self.solutions
        solutions = [s for s in solutions if s.diagnostics.get("components")]
        if not solutions:
            print("No optimized diagnostics available.")
            return

        baseline_comps = self.baseline_diagnostics["components"]
        params = ["epsilon", "E_D", "y", "y_star", "c_F", "c_P", "Z", "r", "f"]
        param_units = {
            "epsilon": "-",
            "E_D": "kW",
            "y": "%",
            "y_star": "%",
            "c_F": "currency/GJ",
            "c_P": "currency/GJ",
            "Z": "currency/h",
            "r": "%",
            "f": "%",
        }

        print("\n" + "=" * 120)
        if solution_index is not None:
            sol = solutions[solution_index]
            obj_str = ", ".join(f"{n}={v:.4f}" for n, v in zip(sol.objective_names, sol.f, strict=False))
            print(f"COMPONENT COMPARISON: Baseline vs. Solution #{solution_index} ({obj_str})")
        else:
            print(f"COMPONENT COMPARISON: Baseline vs. Pareto Range ({len(solutions)} solutions)")
        print("=" * 120)

        for param in params:
            unit = param_units.get(param, "")
            print(f"\n--- {param} [{unit}] ---")

            if solution_index is not None:
                print(f"  {'Component':<20} {'Baseline':>12} {'Optimized':>12} {'Change':>12}")
                print(f"  {'-' * 56}")
                sol = solutions[solution_index]
                for comp_name in sorted(baseline_comps.keys()):
                    base_val = baseline_comps[comp_name].get(param)
                    opt_val = sol.diagnostics.get("components", {}).get(comp_name, {}).get(param)
                    if base_val is None:
                        continue
                    base_str = f"{base_val:>12.4f}"
                    opt_str = f"{opt_val:>12.4f}" if opt_val is not None else f"{'N/A':>12}"
                    if base_val is not None and opt_val is not None and base_val != 0:
                        change = (opt_val - base_val) / abs(base_val) * 100
                        change_str = f"{change:>+11.1f}%"
                    else:
                        change_str = f"{'':>12}"
                    print(f"  {comp_name:<20} {base_str} {opt_str} {change_str}")
            else:
                print(f"  {'Component':<20} {'Baseline':>12} {'Pareto Min':>12} {'Pareto Max':>12}")
                print(f"  {'-' * 56}")
                for comp_name in sorted(baseline_comps.keys()):
                    base_val = baseline_comps[comp_name].get(param)
                    if base_val is None:
                        continue
                    vals = [
                        s.diagnostics["components"].get(comp_name, {}).get(param)
                        for s in solutions
                        if s.diagnostics.get("components", {}).get(comp_name, {}).get(param) is not None
                    ]
                    base_str = f"{base_val:>12.4f}"
                    min_str = f"{min(vals):>12.4f}" if vals else f"{'N/A':>12}"
                    max_str = f"{max(vals):>12.4f}" if vals else f"{'N/A':>12}"
                    print(f"  {comp_name:<20} {base_str} {min_str} {max_str}")

        print("\n" + "=" * 120)

    def plot_component_comparison(
        self,
        solution_index: int | None = None,
        use_pareto: bool = True,
        params: list[str] | None = None,
        figsize: tuple[float, float] | None = None,
    ) -> Any:
        """
        Plot a comparison of component exergoeconomic parameters between
        baseline and optimized design(s).

        Creates grouped bar charts showing the baseline value and the optimized
        value (or Pareto range) for each component and parameter.

        Parameters
        ----------
        solution_index : int | None
            Index of the Pareto solution to compare. If None, shows the
            Pareto range as error bars.
        use_pareto : bool
            If True, selects from Pareto front solutions.
        params : list[str] | None
            Parameters to plot. Default: ["epsilon", "f", "r", "c_P", "c_F"].
        figsize : tuple[float, float] | None
            Figure size. If None, auto-sized.

        Returns
        -------
        matplotlib.figure.Figure
            The figure object.
        """
        import matplotlib.pyplot as plt

        if self.baseline_diagnostics is None or not self.baseline_diagnostics.get("components"):
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No baseline diagnostics available", ha="center", va="center", transform=ax.transAxes)
            return fig

        solutions = self.pareto_front if use_pareto and self.pareto_front else self.solutions
        solutions = [s for s in solutions if s.diagnostics.get("components")]
        if not solutions:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No optimized diagnostics available", ha="center", va="center", transform=ax.transAxes)
            return fig

        if params is None:
            params = ["epsilon", "f", "r", "c_P", "c_F", "Z", "y", "y_star"]

        baseline_comps = self.baseline_diagnostics["components"]
        comp_names = sorted(baseline_comps.keys())
        n_comp = len(comp_names)
        n_params = len(params)

        if figsize is None:
            figsize = (max(10, n_comp * 1.5), 4 * n_params)

        fig, axes = plt.subplots(n_params, 1, figsize=figsize, squeeze=False)

        x = np.arange(n_comp)
        bar_width = 0.35

        for row, param in enumerate(params):
            ax = axes[row, 0]

            base_vals = []
            for comp in comp_names:
                v = baseline_comps[comp].get(param)
                base_vals.append(v if v is not None else 0)

            ax.bar(x - bar_width / 2, base_vals, bar_width, label="Baseline", color="steelblue", alpha=0.8)

            if solution_index is not None:
                sol = solutions[solution_index]
                opt_vals = []
                for comp in comp_names:
                    v = sol.diagnostics.get("components", {}).get(comp, {}).get(param)
                    opt_vals.append(v if v is not None else 0)
                ax.bar(x + bar_width / 2, opt_vals, bar_width, label="Optimized", color="coral", alpha=0.8)
            else:
                # Show mean with min-max error bars
                mean_vals = []
                err_low = []
                err_high = []
                for comp in comp_names:
                    vals = [
                        s.diagnostics["components"].get(comp, {}).get(param)
                        for s in solutions
                        if s.diagnostics.get("components", {}).get(comp, {}).get(param) is not None
                    ]
                    if vals:
                        m = sum(vals) / len(vals)
                        mean_vals.append(m)
                        err_low.append(m - min(vals))
                        err_high.append(max(vals) - m)
                    else:
                        mean_vals.append(0)
                        err_low.append(0)
                        err_high.append(0)

                ax.bar(
                    x + bar_width / 2,
                    mean_vals,
                    bar_width,
                    label="Pareto mean",
                    color="coral",
                    alpha=0.8,
                    yerr=[err_low, err_high],
                    capsize=3,
                    error_kw={"ecolor": "black", "linewidth": 1},
                )

            # Special annotations for f-factor
            if param == "f":
                ax.axhline(y=0.5, color="green", linestyle="--", alpha=0.4)
                ax.axhspan(0.25, 0.75, alpha=0.05, color="green")

            ax.set_xticks(x)
            ax.set_xticklabels(comp_names, rotation=45, ha="right", fontsize=9)
            ax.set_ylabel(param, fontsize=11)
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3, axis="y")

        if solution_index is not None:
            fig.suptitle(f"Component Comparison: Baseline vs. Solution #{solution_index}", fontsize=13, y=1.01)
        else:
            fig.suptitle(f"Component Comparison: Baseline vs. Pareto Range (n={len(solutions)})", fontsize=13, y=1.01)
        fig.tight_layout()
        return fig

    def __repr__(self) -> str:
        return (
            f"OptimizationResult(algorithm='{self.algorithm}', "
            f"n_solutions={len(self.solutions)}, "
            f"pareto_size={len(self.pareto_front)})"
        )


class _ObjectiveStub:
    """Lightweight stand-in for ObjectiveFunction when loading from JSON."""

    def __init__(self, name: str, unit: str | None = None):
        self.name = name
        self.unit = unit

    def __repr__(self) -> str:
        return f"ObjectiveStub('{self.name}')"


class _ConstraintStub:
    """Lightweight stand-in for Constraint when loading from JSON."""

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"ConstraintStub('{self.name}')"
