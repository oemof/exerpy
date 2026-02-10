"""
High-level optimizer interface for exergoeconomic optimization.

This module provides the ExergoeconomicOptimizer class, which offers a
user-friendly API for setting up and running optimizations using pymoo.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Literal

import numpy as np

from .constraints import (
    BoundConstraint,
    Constraint,
    ConstraintType,
    ExergoeconomicConstraint,
    ExergyConstraint,
    RelativeConstraint,
)
from .objectives import (
    CustomObjective,
    MaximizeExergyEfficiency,
    MinimizeExergyDestruction,
    MinimizeTotalCost,
    ObjectiveFunction,
    OptimizationSense,
)
from .problem import ExergoeconomicProblem
from .results import OptimizationResult, Solution
from .variables import DesignVariable

if TYPE_CHECKING:
    from .adapters.base import SimulatorAdapter

logger = logging.getLogger(__name__)


# Available algorithms in pymoo
AVAILABLE_ALGORITHMS = {
    # Single-objective
    "GA": "Genetic Algorithm",
    "DE": "Differential Evolution",
    "PSO": "Particle Swarm Optimization",
    "ES": "Evolution Strategy",
    "CMAES": "CMA-ES",
    "NelderMead": "Nelder-Mead Simplex",
    "PatternSearch": "Pattern Search",
    # Multi-objective
    "NSGA2": "Non-dominated Sorting Genetic Algorithm II",
    "NSGA3": "Non-dominated Sorting Genetic Algorithm III",
    "MOEAD": "Multi-objective Evolutionary Algorithm based on Decomposition",
    "CTAEA": "Constrained Two-Archive Evolutionary Algorithm",
    "SMSEMOA": "S-Metric Selection EMOA",
}


class ExergoeconomicOptimizer:
    """
    High-level interface for exergoeconomic optimization.

    This class provides a fluent API for building and running optimization
    problems. It supports both single and multi-objective optimization
    using various pymoo algorithms.

    Parameters
    ----------
    adapter : SimulatorAdapter
        The simulator adapter (TESPy, Ebsilon, or Aspen).

    Examples
    --------
    >>> from exerpy.optimization import ExergoeconomicOptimizer, TESPyAdapter
    >>> from exerpy.optimization.objectives import MinimizeTotalCost, MaximizeExergyEfficiency
    >>>
    >>> adapter = TESPyAdapter(network, Tamb=298.15, pamb=101325)
    >>> optimizer = (
    ...     ExergoeconomicOptimizer(adapter)
    ...     .add_variable("HP Pressure", "connection", "2", "p", bounds=(50e5, 150e5))
    ...     .add_variable("Reheat Temp", "connection", "5", "T", bounds=(700, 900))
    ...     .add_objective(MinimizeTotalCost())
    ...     .add_objective(MaximizeExergyEfficiency())
    ...     .add_constraint("T_max", "<=", "connection:5:T", 873.15)
    ...     .set_exergy_definitions(
    ...         E_F={"inputs": ["fuel_conn"]},
    ...         E_P={"inputs": ["power_out"]},
    ...     )
    ... )
    >>> result = optimizer.optimize(algorithm="NSGA2", n_gen=100)
    """

    def __init__(self, adapter: SimulatorAdapter):
        self.adapter = adapter
        self._variables: list[DesignVariable] = []
        self._objectives: list[ObjectiveFunction] = []
        self._constraints: list[Constraint] = []

        # Exergy definitions
        self._E_F: dict | None = None
        self._E_P: dict | None = None
        self._E_L: dict | None = None

        # Optional settings
        self._chemExLib: str | None = None
        self._split_physical_exergy: bool = True
        self._exergoeconomic_costs: dict | None = None
        self._cost_function: Callable | None = None
        self._infeasible_penalty: float = 1e10
        self._seed: int | None = None

    def add_variable(
        self,
        name: str,
        target_type: Literal["connection", "component"],
        target_id: str,
        parameter: str,
        bounds: tuple[float, float],
        initial: float | None = None,
        unit: str | None = None,
        description: str | None = None,
    ) -> ExergoeconomicOptimizer:
        """
        Add a design variable to the optimization problem.

        Parameters
        ----------
        name : str
            Human-readable name for the variable.
        target_type : {"connection", "component"}
            Whether the variable targets a connection or component.
        target_id : str
            Identifier of the connection or component.
        parameter : str
            Parameter name (e.g., 'p', 'T', 'm', 'eta_s').
        bounds : tuple[float, float]
            Lower and upper bounds (min, max).
        initial : float | None
            Initial value (uses current model value if None).
        unit : str | None
            Unit string for display.
        description : str | None
            Description of what this variable represents.

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        var = DesignVariable(
            name=name,
            target_type=target_type,
            target_id=target_id,
            parameter=parameter,
            bounds=bounds,
            initial=initial,
            unit=unit,
            description=description,
        )
        self._variables.append(var)
        return self

    def add_objective(self, objective: ObjectiveFunction) -> ExergoeconomicOptimizer:
        """
        Add an objective function.

        Parameters
        ----------
        objective : ObjectiveFunction
            The objective function instance.

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        self._objectives.append(objective)
        return self

    def minimize(
        self,
        name: str,
        func: Any | None = None,
        unit: str | None = None,
    ) -> ExergoeconomicOptimizer:
        """
        Add a minimization objective.

        Parameters
        ----------
        name : str
            Name of the objective. Can be a preset name like "exergy_destruction",
            "total_cost", or a custom name with a provided function.
        func : callable | None
            Custom function (ea, eea) -> float. If None, uses preset.
        unit : str | None
            Unit string for display.

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        if func is None:
            # Use preset objectives
            presets = {
                "exergy_destruction": MinimizeExergyDestruction(name),
                "total_cost": MinimizeTotalCost(name),
            }
            if name.lower() in presets:
                self._objectives.append(presets[name.lower()])
            else:
                raise ValueError(f"Unknown preset objective: {name}")
        else:
            obj = CustomObjective(func=func, name=name, sense=OptimizationSense.MINIMIZE, unit=unit)
            self._objectives.append(obj)
        return self

    def maximize(
        self,
        name: str,
        func: Any | None = None,
        unit: str | None = None,
    ) -> ExergoeconomicOptimizer:
        """
        Add a maximization objective.

        Parameters
        ----------
        name : str
            Name of the objective. Can be "exergy_efficiency" or custom.
        func : callable | None
            Custom function (ea, eea) -> float.
        unit : str | None
            Unit string for display.

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        if func is None:
            presets = {
                "exergy_efficiency": MaximizeExergyEfficiency(name),
            }
            if name.lower() in presets:
                self._objectives.append(presets[name.lower()])
            else:
                raise ValueError(f"Unknown preset objective: {name}")
        else:
            obj = CustomObjective(func=func, name=name, sense=OptimizationSense.MAXIMIZE, unit=unit)
            self._objectives.append(obj)
        return self

    def add_constraint(
        self,
        name: str,
        constraint_type: Literal["<=", ">=", "=="],
        lhs: str,
        rhs: float | str,
    ) -> ExergoeconomicOptimizer:
        """
        Add a constraint to the optimization problem.

        Parameters
        ----------
        name : str
            Human-readable name for the constraint.
        constraint_type : {"<=", ">=", "=="}
            Type of constraint.
        lhs : str
            Left-hand side specification. Can be:
            - "connection:id:param" for connection parameters
            - "component:id:param" for component parameters
            - "exergy:attribute" for system exergy values
            - "exergy:component_id:attribute" for component exergy values
            - "cost:attribute" for exergoeconomic values
        rhs : float | str
            Right-hand side. Either a float value or another specification
            string (for relative constraints).

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        ct = ConstraintType(constraint_type)

        # Parse left-hand side
        lhs_parts = lhs.split(":")

        if lhs_parts[0] in ["connection", "component"]:
            # Parameter constraint
            if isinstance(rhs, (int, float)):
                constr = BoundConstraint(name=name, spec=lhs, constraint_type=ct, bound=float(rhs))
            else:
                # Relative constraint
                constr = RelativeConstraint(name=name, spec_lhs=lhs, constraint_type=ct, spec_rhs=rhs)

        elif lhs_parts[0] == "exergy":
            # Exergy constraint
            if len(lhs_parts) == 2:
                # System-level: exergy:epsilon
                constr = ExergyConstraint(
                    name=name,
                    attribute=lhs_parts[1],
                    constraint_type=ct,
                    bound=float(rhs),
                )
            else:
                # Component-level: exergy:comp_id:E_D
                constr = ExergyConstraint(
                    name=name,
                    attribute=lhs_parts[2],
                    constraint_type=ct,
                    bound=float(rhs),
                    component_id=lhs_parts[1],
                )

        elif lhs_parts[0] == "cost":
            # Exergoeconomic constraint
            if len(lhs_parts) == 2:
                constr = ExergoeconomicConstraint(
                    name=name,
                    attribute=lhs_parts[1],
                    constraint_type=ct,
                    bound=float(rhs),
                )
            else:
                constr = ExergoeconomicConstraint(
                    name=name,
                    attribute=lhs_parts[2],
                    constraint_type=ct,
                    bound=float(rhs),
                    component_id=lhs_parts[1],
                )
        else:
            raise ValueError(f"Unknown constraint specification: {lhs}")

        self._constraints.append(constr)
        return self

    def add_custom_constraint(self, constraint: Constraint) -> ExergoeconomicOptimizer:
        """
        Add a custom constraint object.

        Parameters
        ----------
        constraint : Constraint
            The constraint instance.

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        self._constraints.append(constraint)
        return self

    def set_exergy_definitions(
        self,
        E_F: dict,
        E_P: dict,
        E_L: dict | None = None,
    ) -> ExergoeconomicOptimizer:
        """
        Set the fuel, product, and loss definitions for exergy analysis.

        These definitions specify how exergy flows are categorized for the
        system-level exergy balance.

        Parameters
        ----------
        E_F : dict
            Fuel definition. Specifies the exergy inputs to the system.
            Format: {"inputs": ["conn1", "conn2"], "outputs": ["conn3"]}
        E_P : dict
            Product definition. Specifies the useful exergy output.
            Format: {"inputs": ["conn4"], "outputs": ["conn5"]}
        E_L : dict | None
            Loss definition. Specifies exergy losses to the environment.
            Format: {"inputs": ["conn6"], "outputs": ["conn7"]}

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.

        Examples
        --------
        >>> optimizer.set_exergy_definitions(
        ...     E_F={"inputs": ["e1"]},  # Power input
        ...     E_P={"inputs": ["42"], "outputs": ["41"]},  # Steam generation
        ...     E_L={"inputs": ["12"], "outputs": ["11"]},  # Heat rejection
        ... )
        """
        self._E_F = E_F
        self._E_P = E_P
        self._E_L = E_L
        return self

    def set_chemical_exergy_library(self, library: str) -> ExergoeconomicOptimizer:
        """
        Set the chemical exergy library.

        Parameters
        ----------
        library : str
            Library name (e.g., 'Ahrendts').

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        self._chemExLib = library
        return self

    def set_exergoeconomic_costs(self, costs: dict) -> ExergoeconomicOptimizer:
        """
        Set static exergoeconomic cost data.

        Note: For dynamic cost estimation during optimization (recommended),
        use set_cost_function() instead.

        Parameters
        ----------
        costs : dict
            Cost data for ExergoeconomicAnalysis.

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        self._exergoeconomic_costs = costs
        return self

    def set_cost_function(
        self,
        cost_function: Callable,
    ) -> ExergoeconomicOptimizer:
        """
        Set a dynamic cost estimation function.

        The cost function is called after each successful simulation and exergy
        analysis during optimization. This allows component costs (Z values) to
        be recalculated based on the current operating point.

        Parameters
        ----------
        cost_function : Callable[[ExergyAnalysis], dict[str, float]]
            A function that takes an ExergyAnalysis object and returns a
            dictionary of costs in the format expected by ExergoeconomicAnalysis.

            The returned dictionary should contain:
            - Component investment cost rates: "<component>_Z" in currency/h
            - Boundary stream costs: "<connection>_c" in currency/GJ

            Example return value:
            {
                "COMP1_Z": 25.5,      # EUR/h
                "COMP2_Z": 38.0,      # EUR/h
                "HX1_Z": 10.2,        # EUR/h
                "e1_c": 111.111,      # EUR/GJ (fuel cost)
                "41_c": 0.0,          # EUR/GJ (inlet stream)
            }

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.

        Examples
        --------
        >>> def my_cost_function(ea: ExergyAnalysis) -> dict:
        ...     costs = {}
        ...     # Calculate Z based on component power/heat duty
        ...     for name, comp in ea.components.items():
        ...         if hasattr(comp, 'E_F'):
        ...             # Simple cost correlation: Z = a * E_F^b
        ...             costs[f"{name}_Z"] = 0.1 * comp.E_F ** 0.6
        ...     # Add boundary costs
        ...     costs["fuel_c"] = 111.111  # EUR/GJ
        ...     return costs
        ...
        >>> optimizer.set_cost_function(my_cost_function)
        """
        self._cost_function = cost_function
        return self

    def set_split_physical_exergy(self, split: bool) -> ExergoeconomicOptimizer:
        """
        Set whether to split physical exergy.

        Parameters
        ----------
        split : bool
            If True, split into thermal and mechanical components.

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        self._split_physical_exergy = split
        return self

    def set_seed(self, seed: int) -> ExergoeconomicOptimizer:
        """
        Set the random seed for reproducibility.

        Parameters
        ----------
        seed : int
            Random seed value.

        Returns
        -------
        ExergoeconomicOptimizer
            Self for method chaining.
        """
        self._seed = seed
        return self

    def _get_algorithm(self, algorithm: str, pop_size: int, **kwargs) -> Any:
        """Get a pymoo algorithm instance."""
        try:
            from pymoo.algorithms.moo.ctaea import CTAEA
            from pymoo.algorithms.moo.moead import MOEAD
            from pymoo.algorithms.moo.nsga2 import NSGA2
            from pymoo.algorithms.moo.nsga3 import NSGA3
            from pymoo.algorithms.moo.sms import SMSEMOA
            from pymoo.algorithms.soo.nonconvex.cmaes import CMAES
            from pymoo.algorithms.soo.nonconvex.de import DE
            from pymoo.algorithms.soo.nonconvex.es import ES
            from pymoo.algorithms.soo.nonconvex.ga import GA
            from pymoo.algorithms.soo.nonconvex.nelder import NelderMead
            from pymoo.algorithms.soo.nonconvex.pattern import PatternSearch
            from pymoo.algorithms.soo.nonconvex.pso import PSO
        except ImportError:
            raise ImportError("pymoo is required for optimization. Install with: pip install pymoo")

        algorithm_map = {
            "GA": lambda: GA(pop_size=pop_size, **kwargs),
            "DE": lambda: DE(pop_size=pop_size, **kwargs),
            "PSO": lambda: PSO(pop_size=pop_size, **kwargs),
            "ES": lambda: ES(pop_size=pop_size, **kwargs),
            "CMAES": lambda: CMAES(**kwargs),
            "NelderMead": lambda: NelderMead(**kwargs),
            "PatternSearch": lambda: PatternSearch(**kwargs),
            "NSGA2": lambda: NSGA2(pop_size=pop_size, **kwargs),
            "NSGA3": lambda: NSGA3(pop_size=pop_size, **kwargs),
            "MOEAD": lambda: MOEAD(pop_size=pop_size, **kwargs),
            "CTAEA": lambda: CTAEA(pop_size=pop_size, **kwargs),
            "SMSEMOA": lambda: SMSEMOA(pop_size=pop_size, **kwargs),
        }

        if algorithm not in algorithm_map:
            raise ValueError(f"Unknown algorithm: {algorithm}. Available: {list(algorithm_map.keys())}")

        return algorithm_map[algorithm]()

    def _print_setup(self, algorithm: str, n_gen: int, pop_size: int) -> None:
        """Print optimization setup information."""
        print("\n" + "=" * 70)
        print("EXERGOECONOMIC OPTIMIZATION")
        print("=" * 70)

        # Print objectives
        obj_names = [obj.name for obj in self._objectives]
        if len(obj_names) == 1:
            print(f"Objective: {obj_names[0]}")
        else:
            print(f"Objectives ({len(obj_names)}):")
            for name in obj_names:
                print(f"  - {name}")

        # Print design variables
        print(f"\nDesign Variables ({len(self._variables)}):")
        for var in self._variables:
            bounds_str = f"[{var.lower_bound:.2f}, {var.upper_bound:.2f}]"
            unit_str = f" {var.unit}" if var.unit else ""
            desc_str = f" - {var.description}" if var.description else ""
            print(f"  - {var.name}: {bounds_str}{unit_str}{desc_str}")

        # Print constraints if any
        if self._constraints:
            print(f"\nConstraints ({len(self._constraints)}):")
            for constr in self._constraints:
                print(f"  - {constr.name}")

        # Print algorithm info
        print(f"\nAlgorithm: {algorithm}")
        print(f"Population size: {pop_size}")
        print(f"Generations: {n_gen}")
        print("=" * 70)
        print()

    def _evaluate_baseline(self, problem: ExergoeconomicProblem) -> dict[str, float]:
        """Evaluate baseline values at current design point."""
        baseline = {}

        # Get current variable values from the model
        for var in self._variables:
            current_val = self.adapter.get_param(var.spec)
            baseline[var.name] = current_val

        # Evaluate objectives at current point
        x_current = np.array([baseline[var.name] for var in self._variables])
        f, g, feasible = problem.evaluate_single(x_current)

        for i, obj in enumerate(self._objectives):
            baseline[obj.name] = f[i]

        return baseline

    def _print_baseline(self, baseline: dict[str, float]) -> None:
        """Print baseline values before optimization."""
        print("Baseline Values:")
        print("-" * 40)

        # Print variable values
        for var in self._variables:
            val = baseline.get(var.name, 0)
            unit_str = f" {var.unit}" if var.unit else ""
            print(f"  {var.name}: {val:.4f}{unit_str}")

        # Print objective values
        for obj in self._objectives:
            val = baseline.get(obj.name, 0)
            unit_str = f" {obj.unit}" if obj.unit else ""
            print(f"  {obj.name}: {val:.4f}{unit_str}")

        print("-" * 40)
        print()

    def optimize(
        self,
        E_F: dict | None = None,
        E_P: dict | None = None,
        E_L: dict | None = None,
        exergoeconomic_costs: dict | None = None,
        algorithm: str = "NSGA2",
        n_gen: int = 100,
        pop_size: int = 50,
        verbose: bool = True,
        save_history: bool = True,
        **algorithm_kwargs,
    ) -> OptimizationResult:
        """
        Run the optimization.

        Parameters
        ----------
        E_F : dict | None
            Fuel definition for ExergyAnalysis. If None, uses the value
            set via set_exergy_definitions().
        E_P : dict | None
            Product definition for ExergyAnalysis. If None, uses the value
            set via set_exergy_definitions().
        E_L : dict | None
            Loss definition for ExergyAnalysis. If None, uses the value
            set via set_exergy_definitions().
        exergoeconomic_costs : dict | None
            Static exergoeconomic costs. If None, uses set_exergoeconomic_costs()
            value or the dynamic cost function set via set_cost_function().
        algorithm : str
            Optimization algorithm name (default: "NSGA2").
            Available: GA, DE, PSO, ES, CMAES, NelderMead, PatternSearch,
            NSGA2, NSGA3, MOEAD, CTAEA, SMSEMOA.
        n_gen : int
            Number of generations (default: 100).
        pop_size : int
            Population size (default: 50).
        verbose : bool
            If True, print progress (default: True).
        save_history : bool
            If True, save convergence history (default: True).
        **algorithm_kwargs
            Additional arguments passed to the algorithm.

        Returns
        -------
        OptimizationResult
            The optimization results including Pareto front and best solution.
        """
        try:
            from pymoo.optimize import minimize as pymoo_minimize
            from pymoo.termination import get_termination
        except ImportError:
            raise ImportError("pymoo is required for optimization. Install with: pip install pymoo")

        # Resolve exergy definitions (prefer explicit params over stored values)
        resolved_E_F = E_F if E_F is not None else self._E_F
        resolved_E_P = E_P if E_P is not None else self._E_P
        resolved_E_L = E_L if E_L is not None else self._E_L

        # Validate setup
        if not self._variables:
            raise ValueError("No design variables defined")
        if not self._objectives:
            raise ValueError("No objectives defined")
        if resolved_E_F is None:
            raise ValueError(
                "No fuel definition (E_F) provided. Either pass E_F to optimize() "
                "or call set_exergy_definitions() before optimization."
            )
        if resolved_E_P is None:
            raise ValueError(
                "No product definition (E_P) provided. Either pass E_P to optimize() "
                "or call set_exergy_definitions() before optimization."
            )

        # Print optimization setup
        if verbose:
            self._print_setup(algorithm, n_gen, pop_size)

        # Create problem
        problem = ExergoeconomicProblem(
            adapter=self.adapter,
            variables=self._variables,
            objectives=self._objectives,
            constraints=self._constraints,
            E_F=resolved_E_F,
            E_P=resolved_E_P,
            E_L=resolved_E_L,
            exergoeconomic_costs=exergoeconomic_costs or self._exergoeconomic_costs,
            cost_function=self._cost_function,
            chemExLib=self._chemExLib,
            split_physical_exergy=self._split_physical_exergy,
            infeasible_penalty=self._infeasible_penalty,
        )

        # Evaluate and print baseline values
        baseline = self._evaluate_baseline(problem)
        if verbose:
            self._print_baseline(baseline)

        pymoo_problem = problem.get_pymoo_problem()

        # Get algorithm
        algo = self._get_algorithm(algorithm, pop_size, **algorithm_kwargs)

        # Termination
        termination = get_termination("n_gen", n_gen)

        # Run optimization
        logger.info(f"Starting optimization with {algorithm}, {n_gen} generations, pop_size={pop_size}")

        res = pymoo_minimize(
            pymoo_problem,
            algo,
            termination,
            seed=self._seed,
            verbose=verbose,
            save_history=save_history,
        )

        # Process results
        return self._process_results(res, problem, algorithm, n_gen, save_history, baseline)

    def _process_results(
        self,
        res: Any,
        problem: ExergoeconomicProblem,
        algorithm: str,
        n_gen: int,
        save_history: bool,
        baseline: dict[str, float] | None = None,
    ) -> OptimizationResult:
        """Process pymoo results into OptimizationResult."""
        variable_names = problem.get_variable_names()
        objective_names = problem.get_objective_names()
        constraint_names = problem.get_constraint_names()

        # Extract all solutions
        solutions = []
        pareto_front = []

        if res.X is not None:
            # Handle both single and multi-objective results
            X = res.X if res.X.ndim == 2 else res.X.reshape(1, -1)
            F = res.F if res.F.ndim == 2 else res.F.reshape(1, -1)
            G = res.G if res.G is not None and res.G.size > 0 else None
            if G is not None and G.ndim == 1:
                G = G.reshape(1, -1)

            for i in range(X.shape[0]):
                sol = Solution(
                    x=X[i],
                    f=F[i],
                    g=G[i] if G is not None else None,
                    feasible=np.all(G[i] <= 0) if G is not None else True,
                    variable_names=variable_names,
                    objective_names=objective_names,
                    constraint_names=constraint_names,
                )
                solutions.append(sol)
                pareto_front.append(sol)

        # Extract history if available
        history = {}
        if save_history and hasattr(res, "history") and res.history is not None:
            best_per_gen = []
            for gen_data in res.history:
                if hasattr(gen_data, "opt") and gen_data.opt is not None:
                    opt_f = gen_data.opt.get("F")
                    if opt_f is not None and len(opt_f) > 0:
                        best_per_gen.append(opt_f[0].tolist())
            if best_per_gen:
                history["best_per_generation"] = best_per_gen

        # Determine best solution
        best_solution = solutions[0] if solutions else None

        # Determine termination reason
        termination_reason = "max_gen"
        if hasattr(res, "termination") and res.termination is not None:
            termination_reason = str(res.termination)

        return OptimizationResult(
            variables=self._variables,
            objectives=self._objectives,
            constraints=self._constraints,
            solutions=solutions,
            pareto_front=pareto_front,
            best_solution=best_solution,
            n_generations=n_gen,
            n_evaluations=problem.n_evaluations,
            algorithm=algorithm,
            termination_reason=termination_reason,
            history=history,
            baseline_values=baseline,
        )

    def list_available_algorithms(self) -> dict[str, str]:
        """
        List available optimization algorithms.

        Returns
        -------
        dict[str, str]
            Dictionary mapping algorithm names to descriptions.
        """
        return AVAILABLE_ALGORITHMS.copy()

    def __repr__(self) -> str:
        return (
            f"ExergoeconomicOptimizer(adapter={self.adapter.name}, "
            f"n_var={len(self._variables)}, n_obj={len(self._objectives)}, "
            f"n_constr={len(self._constraints)})"
        )
