"""
Pymoo problem definition for exergoeconomic optimization.

This module provides the ExergoeconomicProblem class that integrates
with pymoo's optimization framework.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

import numpy as np

if TYPE_CHECKING:
    from ..analyses import ExergoeconomicAnalysis, ExergyAnalysis
    from .adapters.base import SimulatorAdapter
    from .constraints import Constraint
    from .objectives import ObjectiveFunction
    from .variables import DesignVariable

logger = logging.getLogger(__name__)


class ExergoeconomicProblem:
    """
    Pymoo-compatible problem definition for exergoeconomic optimization.

    This class wraps the simulation model and exergy analysis to create
    an optimization problem that can be solved using pymoo algorithms.

    Parameters
    ----------
    adapter : SimulatorAdapter
        The simulator adapter (TESPy, Ebsilon, or Aspen).
    variables : list[DesignVariable]
        List of design variables to optimize.
    objectives : list[ObjectiveFunction]
        List of objective functions.
    constraints : list[Constraint]
        List of constraints.
    E_F : dict
        Fuel definition for ExergyAnalysis.
    E_P : dict
        Product definition for ExergyAnalysis.
    E_L : dict
        Loss definition for ExergyAnalysis (default empty).
    exergoeconomic_costs : dict | None
        Static cost data for ExergoeconomicAnalysis. Used if cost_function
        is not provided.
    cost_function : Callable | None
        Dynamic cost estimation function. Called after each successful
        exergy analysis with signature: (ExergyAnalysis) -> dict[str, float].
        Takes precedence over exergoeconomic_costs if provided.
    chemExLib : str | None
        Chemical exergy library name (e.g., 'Ahrendts').
    split_physical_exergy : bool
        Whether to split physical exergy into thermal and mechanical.
    infeasible_penalty : float
        Penalty value for infeasible solutions.

    Attributes
    ----------
    n_var : int
        Number of design variables.
    n_obj : int
        Number of objectives.
    n_constr : int
        Number of constraints.
    xl : np.ndarray
        Lower bounds for variables.
    xu : np.ndarray
        Upper bounds for variables.
    """

    def __init__(
        self,
        adapter: SimulatorAdapter,
        variables: list[DesignVariable],
        objectives: list[ObjectiveFunction],
        constraints: list[Constraint],
        E_F: dict,
        E_P: dict,
        E_L: dict | None = None,
        exergoeconomic_costs: dict | None = None,
        cost_function: Callable | None = None,
        chemExLib: str | None = None,
        split_physical_exergy: bool = True,
        infeasible_penalty: float = 1e10,
    ):
        self.adapter = adapter
        self.variables = variables
        self.objectives = objectives
        self.constraints = constraints
        self.E_F = E_F
        self.E_P = E_P
        self.E_L = E_L or {}
        self.exergoeconomic_costs = exergoeconomic_costs
        self.cost_function = cost_function
        self.chemExLib = chemExLib
        self.split_physical_exergy = split_physical_exergy
        self.infeasible_penalty = infeasible_penalty

        # Problem dimensions
        self.n_var = len(variables)
        self.n_obj = len(objectives)
        self.n_constr = len(constraints)

        # Bounds
        self.xl = np.array([v.lower_bound for v in variables])
        self.xu = np.array([v.upper_bound for v in variables])

        # Evaluation counter
        self._n_evals = 0

        # Cache for last successful evaluation
        self._last_exergy_analysis: ExergyAnalysis | None = None
        self._last_exergoeconomic_analysis: ExergoeconomicAnalysis | None = None

    def _apply_variables(self, x: np.ndarray) -> None:
        """Apply design variable values to the simulation model."""
        for i, var in enumerate(self.variables):
            self.adapter.set_param(var.spec, x[i])

    def _run_simulation(self) -> bool:
        """Run the simulation and return convergence status."""
        # Run in design mode (same as how most TESPy models are initially solved)
        return self.adapter.solve(design=True)

    def _run_exergy_analysis(self) -> ExergyAnalysis | None:
        """Run exergy analysis on the current simulation state."""
        from ..analyses import ExergyAnalysis
        from ..functions import add_total_exergy_flow

        try:
            # Export simulation state to ExerPy format
            model_data = self.adapter.export_to_exerpy()

            # Process the data to add total exergy flows (needed for E values)
            model_data = add_total_exergy_flow(model_data, self.split_physical_exergy)

            # Create ExergyAnalysis instance
            ea = ExergyAnalysis(
                component_data=model_data["components"],
                connection_data=model_data["connections"],
                Tamb=model_data["ambient_conditions"]["Tamb"],
                pamb=model_data["ambient_conditions"]["pamb"],
                chemExLib=self.chemExLib,
                split_physical_exergy=self.split_physical_exergy,
            )

            # Run analysis
            ea.analyse(E_F=self.E_F, E_P=self.E_P, E_L=self.E_L)

            return ea

        except Exception as e:
            logger.warning(f"Exergy analysis failed: {e}")
            return None

    def _run_exergoeconomic_analysis(self, exergy_analysis: ExergyAnalysis) -> ExergoeconomicAnalysis | None:
        """Run exergoeconomic analysis if cost data is provided.

        If a cost_function is set, it will be called to compute dynamic costs
        based on the current exergy analysis results. Otherwise, static
        exergoeconomic_costs are used.
        """
        # Determine costs to use
        if self.cost_function is not None:
            # Dynamic cost estimation
            try:
                costs = self.cost_function(exergy_analysis)
            except Exception as e:
                logger.warning(f"Cost function failed: {e}")
                return None
        elif self.exergoeconomic_costs is not None:
            # Static costs
            costs = self.exergoeconomic_costs
        else:
            # No costs available
            return None

        from ..analyses import ExergoeconomicAnalysis

        try:
            eea = ExergoeconomicAnalysis(exergy_analysis)
            eea.run(
                Exe_Eco_Costs=costs,
                Tamb=exergy_analysis.Tamb,
            )
            return eea

        except Exception as e:
            logger.warning(f"Exergoeconomic analysis failed: {e}")
            return None

    def evaluate_single(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool]:
        """
        Evaluate a single solution.

        Parameters
        ----------
        x : np.ndarray
            Design variable values.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, bool]
            Objective values, constraint values, and feasibility flag.
        """
        self._n_evals += 1

        # Initialize outputs
        f = np.full(self.n_obj, self.infeasible_penalty)
        g = np.full(self.n_constr, self.infeasible_penalty) if self.n_constr > 0 else np.array([])
        feasible = False

        try:
            # Apply design variables
            self._apply_variables(x)

            # Run simulation
            if not self._run_simulation():
                logger.debug(f"Simulation did not converge for x={x}")
                return f, g, feasible

            # Run exergy analysis
            ea = self._run_exergy_analysis()
            if ea is None:
                logger.debug(f"Exergy analysis failed for x={x}")
                return f, g, feasible

            # Run exergoeconomic analysis if needed
            eea = self._run_exergoeconomic_analysis(ea)

            # Cache results
            self._last_exergy_analysis = ea
            self._last_exergoeconomic_analysis = eea

            # Evaluate objectives
            for i, obj in enumerate(self.objectives):
                try:
                    result = obj.evaluate(ea, eea)
                    f[i] = result.value
                except Exception as e:
                    logger.warning(f"Objective '{obj.name}' evaluation failed: {e}")
                    f[i] = self.infeasible_penalty

            # Evaluate constraints
            for i, constr in enumerate(self.constraints):
                try:
                    result = constr.evaluate(self.adapter, ea, eea)
                    g[i] = result.value
                except Exception as e:
                    logger.warning(f"Constraint '{constr.name}' evaluation failed: {e}")
                    g[i] = self.infeasible_penalty

            # Check feasibility
            feasible = np.all(g <= 0) if self.n_constr > 0 else True

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")

        return f, g, feasible

    def evaluate(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Evaluate a population of solutions.

        Parameters
        ----------
        X : np.ndarray
            Population matrix of shape (n_pop, n_var).

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            Objective values (n_pop, n_obj) and constraint values (n_pop, n_constr).
        """
        n_pop = X.shape[0]
        F = np.zeros((n_pop, self.n_obj))
        G = np.zeros((n_pop, self.n_constr)) if self.n_constr > 0 else None

        for i in range(n_pop):
            f, g, _ = self.evaluate_single(X[i])
            F[i] = f
            if G is not None:
                G[i] = g

        return F, G

    def get_pymoo_problem(self) -> Any:
        """
        Create a pymoo Problem instance.

        Returns
        -------
        pymoo.core.problem.Problem
            A pymoo-compatible problem instance.
        """
        try:
            from pymoo.core.problem import Problem
        except ImportError:
            raise ImportError("pymoo is required for optimization. Install with: pip install pymoo")

        problem = self

        class PymooProblem(Problem):
            def __init__(self):
                super().__init__(
                    n_var=problem.n_var,
                    n_obj=problem.n_obj,
                    n_ieq_constr=problem.n_constr,
                    xl=problem.xl,
                    xu=problem.xu,
                )

            def _evaluate(self, X, out, *args, **kwargs):
                F, G = problem.evaluate(X)
                out["F"] = F
                if G is not None:
                    out["G"] = G

        return PymooProblem()

    @property
    def n_evaluations(self) -> int:
        """Total number of evaluations performed."""
        return self._n_evals

    def get_variable_names(self) -> list[str]:
        """Get list of variable names."""
        return [v.name for v in self.variables]

    def get_objective_names(self) -> list[str]:
        """Get list of objective names."""
        return [o.name for o in self.objectives]

    def get_constraint_names(self) -> list[str]:
        """Get list of constraint names."""
        return [c.name for c in self.constraints]

    def __repr__(self) -> str:
        return (
            f"ExergoeconomicProblem(n_var={self.n_var}, n_obj={self.n_obj}, "
            f"n_constr={self.n_constr}, adapter={self.adapter.name})"
        )
