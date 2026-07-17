"""
Demonstrate the exerpy visualization module (Sankey and waterfall diagrams).

The script loads the exported exergy analysis results of the combined cycle
power plant (ccpp) example, so no simulator is required to run it:

    python examples/visualization/ccpp_diagrams.py

The interactive diagrams are written as HTML files next to this script and
opened in the default browser (pass --no-show to only write the files).
"""

import sys
import webbrowser
from pathlib import Path

from exerpy import ExergyAnalysis

HERE = Path(__file__).parent

# ----------------------------------------------------------------------------------------------------------------------
# 1. Load the ccpp example results and run the exergy analysis
# ----------------------------------------------------------------------------------------------------------------------
ean = ExergyAnalysis.from_json(str(HERE / ".." / "exergy_analysis" / "ccpp" / "ccpp_tespy.json"))

fuel = {"inputs": ["1", "3"], "outputs": []}
product = {"inputs": ["e15", "h1"], "outputs": []}
loss = {"inputs": ["8", "15"], "outputs": ["14"]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)

# ----------------------------------------------------------------------------------------------------------------------
# 2. Sankey diagrams
# ----------------------------------------------------------------------------------------------------------------------
# Mode 1: one link per connection carrying the total exergy flow E.
ean.plot_sankey(
    mode=1,
    title="CCPP – Sankey diagram (total exergy)",
    output_path=str(HERE / "ccpp_sankey_total.html"),
)

# Mode 2: material links are split into physical (E_PH) and chemical (E_CH)
# exergy. Requires an analysis with chemical exergy enabled.
ean.plot_sankey(
    mode=2,
    title="CCPP – Sankey diagram (physical + chemical exergy)",
    output_path=str(HERE / "ccpp_sankey_split.html"),
)

# Components can be aggregated into groups and nodes can be colored
# individually. Links inside a group are hidden.
ean.plot_sankey(
    groups={"Steam cycle": ["DEA", "COND", "FP", "CP", "DP"]},
    node_colors={"CC": "#C62828", "GT": "#388E3C"},
    title="CCPP – Sankey diagram (grouped steam cycle)",
    output_path=str(HERE / "ccpp_sankey_grouped.html"),
)

# ----------------------------------------------------------------------------------------------------------------------
# 3. Waterfall diagrams
# ----------------------------------------------------------------------------------------------------------------------
# Interactive plotly variant. Bar colors can be customized via the `colors`
# dict with the keys "fuel", "destruction", "loss" and "product".
fig = ean.plot_exergy_waterfall_plotly(title="CCPP – Exergy waterfall", show_plot=False)
fig.write_html(HERE / "ccpp_waterfall.html")

# Static matplotlib variant of the same diagram, exported as PNG.
fig, ax = ean.plot_exergy_waterfall(title="CCPP – Exergy waterfall", show_plot=False)
fig.savefig(HERE / "ccpp_waterfall.png", dpi=150, bbox_inches="tight")

# ----------------------------------------------------------------------------------------------------------------------
# 4. Show the results
# ----------------------------------------------------------------------------------------------------------------------
html_files = [
    HERE / "ccpp_sankey_total.html",
    HERE / "ccpp_sankey_split.html",
    HERE / "ccpp_sankey_grouped.html",
    HERE / "ccpp_waterfall.html",
]

for path in html_files + [HERE / "ccpp_waterfall.png"]:
    print(f"written: {path}")

if "--no-show" not in sys.argv:
    for path in html_files:
        webbrowser.open(path.resolve().as_uri())
