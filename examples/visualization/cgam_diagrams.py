"""
Sankey and waterfall diagrams for the CGAM example.

The script loads the exported exergy analysis results, so no simulator is
required to run it:

    python examples/visualization/cgam_diagrams.py

The interactive diagrams are written as HTML files next to this script and
opened in the default browser (pass --no-show to only write the files).
"""

import sys
import webbrowser
from pathlib import Path

from exerpy import ExergyAnalysis

HERE = Path(__file__).parent

# [analysis_section]
ean = ExergyAnalysis.from_json(str(HERE / ".." / "exergy_analysis" / "cgam" / "cgam_tespy.json"))

fuel = {"inputs": ["1", "10"], "outputs": []}
product = {"inputs": ["e3", "9"], "outputs": ["8"]}
loss = {"inputs": ["7"], "outputs": []}

ean.analyse(E_F=fuel, E_P=product, E_L=loss)
# [sankey_section]
# Mode 1: one link per connection carrying the total exergy flow E. Since the
# product definition has inputs and outputs, an intermediate "E_P net" node
# shows the gross product flows next to the net product.
ean.plot_sankey(
    mode=1,
    title="CGAM – Sankey diagram (total exergy)",
    output_path=str(HERE / "cgam_sankey_total.html"),
)

# Mode 2: material links are split into physical (E_PH) and chemical (E_CH)
# exergy. Requires an analysis with chemical exergy enabled.
ean.plot_sankey(
    mode=2,
    title="CGAM – Sankey diagram (physical + chemical exergy)",
    output_path=str(HERE / "cgam_sankey_split.html"),
)

# Group the heat recovery steam generator into a single node.
ean.plot_sankey(
    groups={"HRSG": ["EV", "PH", "DRUM"]},
    node_colors={"CC": "#C62828", "EXP": "#388E3C"},
    title="CGAM – Sankey diagram (grouped heat recovery steam generator)",
    output_path=str(HERE / "cgam_sankey_grouped.html"),
)
# [waterfall_section]
fig = ean.plot_exergy_waterfall_plotly(title="CGAM – Exergy waterfall", show_plot=False)
fig.write_html(HERE / "cgam_waterfall.html")

fig, ax = ean.plot_exergy_waterfall(title="CGAM – Exergy waterfall", show_plot=False)
fig.savefig(HERE / "cgam_waterfall.png", dpi=150, bbox_inches="tight")
# [show_section]
html_files = [
    HERE / "cgam_sankey_total.html",
    HERE / "cgam_sankey_split.html",
    HERE / "cgam_sankey_grouped.html",
    HERE / "cgam_waterfall.html",
]

for path in html_files + [HERE / "cgam_waterfall.png"]:
    print(f"written: {path}")

if "--no-show" not in sys.argv:
    for path in html_files:
        webbrowser.open(path.resolve().as_uri())
