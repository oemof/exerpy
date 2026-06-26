"""Exergy destruction waterfall diagram."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .colors import WATERFALL_COLORS

if TYPE_CHECKING:
    from exerpy.analyses import ExergyAnalysis


def _prepare_data(analysis: ExergyAnalysis, exclude_components: list[str] | None):
    """Extract and sort component data for waterfall plotting."""
    df, _, _ = analysis.exergy_results(print_results=False)

    if exclude_components is None:
        exclude_components = []

    total_row = df[df["Component"] == "TOT"].iloc[0]
    epsilon_total = total_row["epsilon [%]"]
    E_F_total = total_row["E_F [kW]"]
    loss_percent = (total_row["E_L [kW]"] / E_F_total) * 100 if E_F_total != 0 else 0

    comp_data = df[
        (df["Component"] != "TOT")
        & (df["E_F [kW]"].notna())
        & (~df["Component"].isin(exclude_components))
        & (df["y [%]"].notna())
    ].copy().sort_values("y [%]", ascending=False)

    return comp_data, epsilon_total, loss_percent


def _resolve_colors(user_colors: dict[str, str] | None) -> dict[str, str]:
    palette = dict(WATERFALL_COLORS)
    if user_colors:
        palette.update(user_colors)
    return palette


def plot_exergy_waterfall(
    analysis: ExergyAnalysis,
    title: str | None = None,
    figsize: tuple[float, float] = (12, 10),
    exclude_components: list[str] | None = None,
    colors: dict[str, str] | None = None,
    show_plot: bool = True,
):
    """
    Create an exergy destruction waterfall diagram using Matplotlib.

    Visualizes exergy flow through the system as a waterfall chart, showing how
    exergy is destroyed in each component from the exergetic fuel (100%) down to
    the exergetic product and losses.

    Parameters
    ----------
    analysis : ExergyAnalysis
        Completed analysis instance (analyse() must be called first).
    title : str, optional
        Title for the plot. If None, no title is displayed.
    figsize : tuple, optional
        Figure size as (width, height) in inches. Default is (12, 10).
    exclude_components : list, optional
        List of component names to exclude from the diagram.
        By default, all components with NaN E_F (Exergetic Fuel) are excluded,
        as well as CycleCloser and PowerBus components.
    colors : dict, optional
        Override bar colors. Keys: "fuel", "destruction", "loss", "product".
        Defaults are taken from ``exerpy.visualization.colors.WATERFALL_COLORS``.
    show_plot : bool, optional
        Whether to display the plot immediately. Default is True.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object containing the waterfall diagram.
    ax : matplotlib.axes.Axes
        The axes object of the waterfall diagram.

    Raises
    ------
    RuntimeError
        If the exergy analysis has not been performed yet (analyse() not called).

    Notes
    -----
    - The waterfall diagram displays exergy values as percentages of the total fuel exergy.
    - Components are sorted by their exergy destruction rate (y [%]) in descending order.
    - Each bar represents the remaining exergy after destruction in that component.
    - Red bars indicate exergy destruction in components.
    - Blue bar represents the initial exergetic fuel (100%).
    - Green bar represents the final exergetic product.

    Examples
    --------
    >>> analysis = ExergyAnalysis.from_tespy(network, Tamb=288.15, pamb=101325)  # doctest: +SKIP
    >>> analysis.analyse(E_F={'inputs': ['fuel']}, E_P={'outputs': ['power']})  # doctest: +SKIP
    >>> fig, ax = analysis.plot_exergy_waterfall(title='Power Plant Exergy Waterfall')  # doctest: +SKIP
    >>> fig.savefig('exergy_waterfall.pdf')  # doctest: +SKIP

    See Also
    --------
    exergy_results : Display tabular exergy analysis results.
    print_exergy_summary : Print a text summary of exergy analysis.
    plot_exergy_waterfall_plotly : Plotly version of this diagram.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    if not hasattr(analysis, "epsilon") or analysis.epsilon is None:
        raise RuntimeError("Exergy analysis has not been performed yet. Please call analyse() first.")

    palette = _resolve_colors(colors)
    comp_data, epsilon_total, loss_percent = _prepare_data(analysis, exclude_components)

    bar_values = [100.0]
    current = 100.0
    for y in comp_data["y [%]"]:
        current -= y
        bar_values.append(current)
    bar_values.append(epsilon_total)

    space_labels = (
        ["Exergetic fuel"]
        + list(comp_data["Component"])
        + ["Exergetic loss", "Exergetic product"]
    )

    fig, ax = plt.subplots(figsize=figsize)
    n_bars = len(bar_values)
    bar_positions = np.arange(n_bars)
    bar_colors = (
        [palette["fuel"]]
        + [palette["destruction"]] * (n_bars - 2)
        + [palette["product"]]
    )

    for pos, value, color in zip(bar_positions, bar_values, bar_colors, strict=False):
        ax.barh(pos, value, color=color, alpha=0.8, height=0.6)
        ax.text(value - 2, pos, f"{value:.2f}%", va="center", ha="right", fontsize=9, fontweight="bold", color="white")

    space_positions = [-0.5] + [i + 0.5 for i in range(n_bars - 1)] + [n_bars - 0.5]
    for i, (space_pos, label) in enumerate(zip(space_positions, space_labels, strict=False)):
        if i == 0:
            ax.text(2, space_pos, label, va="center", ha="left", fontsize=10, fontweight="bold", style="italic")
        elif i == len(space_labels) - 2:
            ax.text(2, space_pos, f"{label} (-{loss_percent:.2f}%)", va="center", ha="left", fontsize=10, fontweight="bold", style="italic")
        elif i == len(space_labels) - 1:
            ax.text(2, space_pos, label, va="center", ha="left", fontsize=10, fontweight="bold", style="italic")
        else:
            y_rate = comp_data.iloc[i - 1]["y [%]"]
            ax.text(2, space_pos, f"{label} (-{y_rate:.2f}%)", va="center", ha="left", fontsize=10, fontweight="bold")

    ax.set_yticks(bar_positions)
    ax.set_yticklabels([""] * n_bars)
    ax.set_xlabel("Exergy [%]", fontsize=12, fontweight="bold")
    if title is not None:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.set_xlim(0, 100)
    ax.set_ylim(-1, n_bars)
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.invert_yaxis()
    plt.tight_layout()

    if show_plot:
        plt.show()

    return fig, ax


def plot_exergy_waterfall_plotly(
    analysis: ExergyAnalysis,
    title: str | None = None,
    exclude_components: list[str] | None = None,
    colors: dict[str, str] | None = None,
    show_plot: bool = True,
):
    """
    Create an exergy destruction waterfall diagram using Plotly.

    Interactive version of the waterfall chart. Components are sorted by their
    exergy destruction rate (y [%]) in descending order.

    Parameters
    ----------
    analysis : ExergyAnalysis
        Completed analysis instance (analyse() must be called first).
    title : str, optional
        Title for the plot. If None, a default title is used.
    exclude_components : list, optional
        List of component names to exclude from the diagram.
        By default, all components with NaN E_F (Exergetic Fuel) are excluded,
        as well as CycleCloser and PowerBus components.
    colors : dict, optional
        Override bar colors. Keys: "fuel", "destruction", "loss", "product".
        Defaults are taken from ``exerpy.visualization.colors.WATERFALL_COLORS``.
    show_plot : bool, optional
        Whether to display the plot immediately. Default is True.

    Returns
    -------
    fig : plotly.graph_objects.Figure

    Raises
    ------
    RuntimeError
        If the exergy analysis has not been performed yet (analyse() not called).

    Examples
    --------
    >>> analysis = ExergyAnalysis.from_tespy(network, Tamb=288.15, pamb=101325)  # doctest: +SKIP
    >>> analysis.analyse(E_F={'inputs': ['fuel']}, E_P={'outputs': ['power']})  # doctest: +SKIP
    >>> fig = analysis.plot_exergy_waterfall_plotly(title='Power Plant Exergy Waterfall')  # doctest: +SKIP
    >>> fig.write_html('waterfall.html')  # doctest: +SKIP

    See Also
    --------
    plot_exergy_waterfall : Matplotlib version of this diagram.
    """
    import plotly.graph_objects as go

    if not hasattr(analysis, "epsilon") or analysis.epsilon is None:
        raise RuntimeError("Exergy analysis has not been performed yet. Please call analyse() first.")

    palette = _resolve_colors(colors)
    comp_data, epsilon_total, loss_percent = _prepare_data(analysis, exclude_components)

    names = (
        ["E_F (100%)"]
        + [f"{name} (-{y:.2f}%)" for name, y in zip(comp_data["Component"], comp_data["y [%]"], strict=False)]
        + [f"E_L (-{loss_percent:.2f}%)", "E_P"]
    )
    measures = ["absolute"] + ["relative"] * len(comp_data) + ["relative", "total"]
    x_values = [100.0] + [-y for y in comp_data["y [%]"]] + [-loss_percent, 0]
    text = (
        ["100.00%"]
        + [f"-{y:.2f}%" for y in comp_data["y [%]"]]
        + [f"-{loss_percent:.2f}%", f"{epsilon_total:.2f}%"]
    )
    bar_colors = (
        [palette["fuel"]]
        + [palette["destruction"]] * len(comp_data)
        + [palette["loss"], palette["product"]]
    )

    fig = go.Figure(go.Waterfall(
        orientation="h",
        measure=measures,
        y=names,
        x=x_values,
        text=text,
        textposition="inside",
        connector={"line": {"color": "#9E9E9E", "dash": "dot", "width": 1}},
        decreasing={"marker": {"color": palette["destruction"]}},
        increasing={"marker": {"color": palette["destruction"]}},
        totals={"marker": {"color": palette["product"]}},
        marker={"color": bar_colors},
    ))

    fig.update_layout(
        title_text=title or "Exergy Waterfall Diagram",
        xaxis_title="Exergy [%]",
        xaxis={"range": [0, 105]},
        font_size=12,
        showlegend=False,
    )

    if show_plot:
        fig.show()

    return fig
