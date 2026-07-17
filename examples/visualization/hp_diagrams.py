"""
Sankey and waterfall diagrams for the air source heat pump example.

The script loads the exported exergy analysis results, so no simulator is
required to run it:

    python examples/visualization/hp_diagrams.py

The interactive diagrams are written as HTML files next to this script and
opened in the default browser (pass --no-show to only write the files).
"""

import sys
import webbrowser
from pathlib import Path

from exerpy import ExergyAnalysis

HERE = Path(__file__).parent

# [analysis_section]
ean = ExergyAnalysis.from_json(str(HERE / ".." / "exergy_analysis" / "heatpump" / "hp_tespy.json"))

fuel = {"inputs": ["e1"], "outputs": []}
product = {"inputs": ["23"], "outputs": ["21"]}
loss = {"inputs": ["13"], "outputs": ["11"]}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
# [sankey_section]
# The heat pump analysis runs without chemical exergy, so only mode 1 is
# available. Product and loss definitions both have inputs and outputs, so the
# diagram shows intermediate "E_P net" and "E_L net" nodes.
ean.plot_sankey(
    mode=1,
    title="Heat pump – Sankey diagram (total exergy)",
    output_path=str(HERE / "hp_sankey_total.html"),
)

# Group the electric drives into a single node.
ean.plot_sankey(
    groups={"Drives": ["electricity distribution", "MOT1", "MOT2", "MOT3"]},
    node_colors={"COMP": "#C62828", "COND": "#388E3C"},
    title="Heat pump – Sankey diagram (grouped drives)",
    output_path=str(HERE / "hp_sankey_grouped.html"),
)
# [waterfall_section]
fig = ean.plot_exergy_waterfall_plotly(title="Heat pump – Exergy waterfall", show_plot=False)
fig.write_html(HERE / "hp_waterfall.html")

fig, ax = ean.plot_exergy_waterfall(title="Heat pump – Exergy waterfall", show_plot=False)
fig.savefig(HERE / "hp_waterfall.png", dpi=150, bbox_inches="tight")
# [show_section]
html_files = [
    HERE / "hp_sankey_total.html",
    HERE / "hp_sankey_grouped.html",
    HERE / "hp_waterfall.html",
]

for path in html_files + [HERE / "hp_waterfall.png"]:
    print(f"written: {path}")

if "--no-show" not in sys.argv:
    for path in html_files:
        webbrowser.open(path.resolve().as_uri())
