"""TESPy-specific thermodynamic diagram plotting.

Provides functions to generate log(p)-h and T-s diagrams from a TESPy
network, using fluprodia for background isolines and TESPy's
``get_plotting_data`` for physically accurate process lines.
"""

import logging

import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Cache computed FluidPropertyDiagram objects (expensive to build)
_diagram_cache = {}


def _get_diagram(fluid):
    """Return a cached FluidPropertyDiagram for *fluid* (built on first call)."""
    if fluid not in _diagram_cache:
        try:
            from fluprodia import FluidPropertyDiagram
        except ImportError:
            raise ImportError(
                "The 'fluprodia' package is required for thermodynamic diagrams. "
                "Install it with: pip install fluprodia"
            )
        logger.info("Computing isolines for %s ...", fluid)
        d = FluidPropertyDiagram(fluid)
        d.set_unit_system(T="°C", p="bar", h="kJ/kg", s="kJ/kgK")
        T_crit = d.convert_from_SI(d.T_crit, "T")
        d.set_isolines_subcritical(T_min=-40, T_max=T_crit - 2)
        d.calc_isolines()
        _diagram_cache[fluid] = d
    return _diagram_cache[fluid]


def _get_fluid_from_connection(nw, connection_label):
    """Extract the pure fluid name from a TESPy connection by label."""
    for conn in nw.conns["object"]:
        if conn.label == connection_label:
            fluid_data = conn.fluid.val
            nonzero = {k: v for k, v in fluid_data.items() if v > 0}
            if len(nonzero) == 1:
                return next(iter(nonzero))
            sorted_fluids = sorted(nonzero, key=lambda k: nonzero[k], reverse=True)
            return sorted_fluids[0]
    raise ValueError(f"Connection '{connection_label}' not found in network.")


def _resolve_diagram_limits(points, diagram_type):
    """Compute axis limits from state points with margin.

    Returns (x_min, x_max, y_min, y_max).
    """
    if diagram_type == "logph":
        x_key, y_key = "h", "p"
    else:
        x_key, y_key = "s", "T"

    x_vals = [pt[x_key] for pt in points.values()]
    y_vals = [pt[y_key] for pt in points.values()]

    x_margin = (max(x_vals) - min(x_vals)) * 0.3 or 50
    if diagram_type == "logph":
        return min(x_vals) - x_margin, max(x_vals) + x_margin, min(y_vals) / 3, max(y_vals) * 3
    else:
        y_margin = (max(y_vals) - min(y_vals)) * 0.3 or 10
        return min(x_vals) - x_margin, max(x_vals) + x_margin, min(y_vals) - y_margin, max(y_vals) + y_margin


def _plot_diagram(
    nw,
    connection_label,
    diagram_type,
    title,
    figsize,
    show_labels,
    show_plot,
    save_path,
    dpi,
    return_fig,
    ax,
    color,
):
    """Shared implementation for log(p)-h and T-s diagrams."""
    from tespy.tools import get_plotting_data

    fluid = _get_fluid_from_connection(nw, connection_label)
    diagram = _get_diagram(fluid)

    # Retrieve process lines and state points from TESPy
    processes, points = get_plotting_data(nw, connection_label)
    processes = {key: diagram.calc_individual_isoline(**value) for key, value in processes.items() if value is not None}

    x_min, x_max, y_min, y_max = _resolve_diagram_limits(points, diagram_type)

    # Set up axis keys for the diagram type
    if diagram_type == "logph":
        x_key, y_key = "h", "p"
        x_label, y_label = "h [kJ/kg]", "p [bar]"
    else:
        x_key, y_key = "s", "T"
        x_label, y_label = "s [kJ/kgK]", "T [°C]"

    # Create figure if no axes provided
    created_fig = ax is None
    if created_fig:
        fig, ax = plt.subplots(1, figsize=figsize)
    else:
        fig = ax.get_figure()

    # Draw background isolines
    diagram.draw_isolines(fig, ax, diagram_type, x_min, x_max, y_min, y_max)

    # Plot process lines (smooth, physically accurate curves)
    for label, values in processes.items():
        ax.plot(values[x_key], values[y_key], color=color, linewidth=2.5)

    # Plot state points
    for label, point in points.items():
        ax.scatter(point[x_key], point[y_key], color="k", s=60, zorder=5)
        if show_labels:
            ax.annotate(
                label,
                (point[x_key], point[y_key]),
                textcoords="offset points",
                xytext=(8, 8),
                fontsize=9,
                fontweight="bold",
                zorder=6,
            )

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    if title is not None:
        ax.set_title(title, fontsize=14, fontweight="bold")
    elif created_fig:
        default_title = f"Log(p)\u2013h Diagram: {fluid}" if diagram_type == "logph" else f"T\u2013s Diagram: {fluid}"
        ax.set_title(default_title, fontsize=14, fontweight="bold")

    if created_fig:
        fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
        logger.info("Saved %s diagram to %s", diagram_type, save_path)

    if show_plot and created_fig:
        plt.show()

    if return_fig:
        return fig, ax

    if created_fig and not show_plot:
        plt.close(fig)

    return None


def plot_logph(
    nw,
    connection_label,
    title=None,
    figsize=(12, 8),
    show_labels=True,
    show_plot=True,
    save_path=None,
    dpi=150,
    return_fig=False,
    ax=None,
    color="tab:red",
):
    """Plot a log(p)-h diagram for a fluid cycle in a TESPy network.

    Uses TESPy's ``get_plotting_data`` for physically accurate process
    lines (isentropic, isenthalpic, etc.) and fluprodia for background
    isolines (saturation dome, isotherms, isobars).

    Parameters
    ----------
    nw : tespy.networks.Network
        A converged TESPy network.
    connection_label : str
        Label of any connection in the cycle to plot (e.g. ``"c1"``).
        TESPy traces the full cycle from this starting connection.
    title : str, optional
        Figure title. Auto-generated from fluid name if ``None``.
    figsize : tuple, optional
        Figure size ``(width, height)`` in inches. Default ``(12, 8)``.
    show_labels : bool, optional
        If ``True``, annotate each state point with its connection label.
    show_plot : bool, optional
        If ``True``, call ``plt.show()``.
    save_path : str, optional
        File path to save the figure (e.g. ``"logph.png"``).
    dpi : int, optional
        Resolution for saved figure. Default 150.
    return_fig : bool, optional
        If ``True``, return ``(fig, ax)`` instead of ``None``.
    ax : matplotlib.axes.Axes, optional
        Existing axes to plot on. If ``None``, a new figure is created.
    color : str, optional
        Color for the cycle process lines. Default ``"tab:red"``.

    Returns
    -------
    tuple of (Figure, Axes) or None
        Returned only when *return_fig* is ``True``.

    Examples
    --------
    >>> from exerpy.parser.from_tespy.plotting import plot_logph  # doctest: +SKIP
    >>> plot_logph(nw, "c1", save_path="logph.png")  # doctest: +SKIP
    """
    return _plot_diagram(
        nw, connection_label, "logph", title, figsize, show_labels, show_plot, save_path, dpi, return_fig, ax, color
    )


def plot_Ts(
    nw,
    connection_label,
    title=None,
    figsize=(12, 8),
    show_labels=True,
    show_plot=True,
    save_path=None,
    dpi=150,
    return_fig=False,
    ax=None,
    color="tab:red",
):
    """Plot a T-s diagram for a fluid cycle in a TESPy network.

    Uses TESPy's ``get_plotting_data`` for physically accurate process
    lines and fluprodia for background isolines.

    Parameters
    ----------
    nw : tespy.networks.Network
        A converged TESPy network.
    connection_label : str
        Label of any connection in the cycle to plot (e.g. ``"c1"``).
        TESPy traces the full cycle from this starting connection.
    title : str, optional
        Figure title. Auto-generated from fluid name if ``None``.
    figsize : tuple, optional
        Figure size ``(width, height)`` in inches. Default ``(12, 8)``.
    show_labels : bool, optional
        If ``True``, annotate each state point with its connection label.
    show_plot : bool, optional
        If ``True``, call ``plt.show()``.
    save_path : str, optional
        File path to save the figure (e.g. ``"Ts.png"``).
    dpi : int, optional
        Resolution for saved figure. Default 150.
    return_fig : bool, optional
        If ``True``, return ``(fig, ax)`` instead of ``None``.
    ax : matplotlib.axes.Axes, optional
        Existing axes to plot on. If ``None``, a new figure is created.
    color : str, optional
        Color for the cycle process lines. Default ``"tab:red"``.

    Returns
    -------
    tuple of (Figure, Axes) or None
        Returned only when *return_fig* is ``True``.

    Examples
    --------
    >>> from exerpy.parser.from_tespy.plotting import plot_Ts  # doctest: +SKIP
    >>> plot_Ts(nw, "c1", save_path="Ts.png")  # doctest: +SKIP
    """
    return _plot_diagram(
        nw, connection_label, "Ts", title, figsize, show_labels, show_plot, save_path, dpi, return_fig, ax, color
    )
