import os

import matplotlib

matplotlib.use("Agg")

import pytest

from exerpy import ExergyAnalysis
from exerpy.visualization import SankeyBuilder

_CCPP_JSON = os.path.join(os.path.dirname(__file__), "../examples/exergy_analysis/ccpp/ccpp_tespy.json")

_TERMINAL_LABELS = {"E_F (Fuel)", "E_P (Product)", "E_D (Destruction)", "E_L (Loss)", "E_L net"}


@pytest.fixture(scope="module")
def ccpp():
    ean = ExergyAnalysis.from_json(_CCPP_JSON)
    ean.analyse(
        E_F={"inputs": ["1", "3"], "outputs": []},
        E_P={"inputs": ["e15", "h1"], "outputs": []},
        E_L={"inputs": ["8", "15"], "outputs": ["14"]},
    )
    return ean


def _flows(nodes, links):
    """Return per-node (inflow, outflow) sums keyed by node id."""
    inflow = {n["id"]: 0.0 for n in nodes}
    outflow = {n["id"]: 0.0 for n in nodes}
    for lk in links:
        outflow[nodes[lk["source"]]["id"]] += lk["value"]
        inflow[nodes[lk["target"]]["id"]] += lk["value"]
    return inflow, outflow


class TestSankeyCcpp:
    def test_node_and_link_count(self, ccpp):
        # 26 components - 1 collapsed CycleCloser + 4 terminals + 1 E_L net helper
        nodes, links = SankeyBuilder(ccpp, mode=1).build()
        assert len(nodes) == 30
        assert len(links) == 64

    def test_mode_2_splits_material_links(self, ccpp):
        nodes, links = SankeyBuilder(ccpp, mode=2).build()
        assert len(nodes) == 30
        assert len(links) > 64
        sub_labels = {lk["label"].split("[")[1].split("]")[0] for lk in links if "[" in lk["label"]}
        assert "E_PH" in sub_labels
        assert "E_CH" in sub_labels

    def test_mode_3_requires_split_physical_exergy(self, ccpp):
        with pytest.raises(ValueError):
            SankeyBuilder(ccpp, mode=3)

    def test_all_link_values_positive(self, ccpp):
        _, links = SankeyBuilder(ccpp, mode=1).build()
        assert all(lk["value"] > 0 for lk in links)

    def test_component_nodes_balance(self, ccpp):
        # Everything entering a component node must leave it (to other
        # components, terminals or E_D). Only terminal nodes are unbalanced.
        nodes, links = SankeyBuilder(ccpp, mode=1).build()
        inflow, outflow = _flows(nodes, links)
        for node in nodes:
            if node["label"] in _TERMINAL_LABELS:
                continue
            assert inflow[node["id"]] == pytest.approx(outflow[node["id"]], rel=1e-3)

    def test_destruction_total_matches_analysis(self, ccpp):
        # Regression: Mixer destruction (deaerator) used to be dropped.
        nodes, links = SankeyBuilder(ccpp, mode=1).build()
        inflow, _ = _flows(nodes, links)
        assert inflow["__E_D__"] == pytest.approx(ccpp.E_D, rel=1e-6)
        dea_ed = [lk for lk in links if nodes[lk["source"]]["id"] == "DEA" and nodes[lk["target"]]["id"] == "__E_D__"]
        assert len(dea_ed) == 1

    def test_loss_helper_node(self, ccpp):
        # E_L has both inputs and outputs in the ccpp definition, so an
        # intermediate "E_L net" node must be present; E_P has only inputs.
        nodes, links = SankeyBuilder(ccpp, mode=1).build()
        ids = {n["id"] for n in nodes}
        assert "__E_L_net__" in ids
        assert "__E_P_net__" not in ids
        inflow, outflow = _flows(nodes, links)
        # gross loss flows enter the helper node, returns and the net loss leave it
        assert inflow["__E_L_net__"] == pytest.approx(outflow["__E_L_net__"], rel=1e-3)
        # the terminal E_L node receives exactly the net loss of the analysis
        assert inflow["__E_L__"] == pytest.approx(ccpp.E_L, rel=1e-6)

    def test_collapse_passthroughs(self, ccpp):
        nodes_collapsed, _ = SankeyBuilder(ccpp, collapse_passthroughs=True).build()
        nodes_full, _ = SankeyBuilder(ccpp, collapse_passthroughs=False).build()
        ids_collapsed = {n["id"] for n in nodes_collapsed}
        ids_full = {n["id"] for n in nodes_full}
        assert "cycle closer" not in ids_collapsed
        assert "cycle closer" in ids_full
        assert len(nodes_full) == len(nodes_collapsed) + 1

    def test_grouping(self, ccpp):
        members = ["ECO", "EVA", "SH", "drum", "drum pump"]
        nodes, links = SankeyBuilder(ccpp, groups={"HRSG": members}).build()
        ids = {n["id"] for n in nodes}
        assert "HRSG" in ids
        assert not set(members) & ids
        # 5 members merge into 1 node; internal links disappear
        assert len(nodes) == 26
        assert len(links) < 64

    def test_node_colors_override(self, ccpp):
        nodes, _ = SankeyBuilder(ccpp, node_colors={"CC": "#C62828"}).build()
        by_id = {n["id"]: n for n in nodes}
        assert by_id["CC"]["color"] == "#C62828"
        assert by_id["GT"]["color"] != "#C62828"

    def test_to_plotly_figure(self, ccpp):
        fig = ccpp.plot_sankey(mode=1, title="test")
        trace = fig.data[0]
        assert trace.type == "sankey"
        assert len(trace.node.label) == 30
        assert len(trace.link.value) == 64


class TestSankeyEdgeCases:
    @staticmethod
    def _fake_analysis(E_ab):
        """Minimal duck-typed analysis with a single A -> B connection."""

        class _Analysis:
            pass

        analysis = _Analysis()
        analysis.E_F = 1000.0
        analysis.E_P = 800.0
        analysis.E_L = 0.0
        analysis.chemical_exergy_enabled = False
        analysis.split_physical_exergy = False
        analysis.components = {
            "A": type("Turbine", (), {"E_D": 50.0})(),
            "B": type("Generator", (), {"E_D": None})(),
        }
        analysis.connections = {
            "fuel": {"kind": "power", "source_component": None, "target_component": "A", "E": 1000.0},
            "ab": {"kind": "power", "source_component": "A", "target_component": "B", "E": E_ab},
            "prod": {"kind": "power", "source_component": "B", "target_component": None, "E": 800.0},
        }
        analysis.E_F_dict = {"inputs": ["fuel"], "outputs": []}
        analysis.E_P_dict = {"inputs": ["prod"], "outputs": []}
        analysis.E_L_dict = {"inputs": [], "outputs": []}
        return analysis

    def test_negative_exergy_flow_is_dropped(self):
        # Negative flows cannot be rendered by a Sankey; they must be
        # dropped instead of producing a corrupt diagram.
        nodes, links = SankeyBuilder(self._fake_analysis(E_ab=-100.0)).build()
        ab_links = [lk for lk in links if nodes[lk["source"]]["id"] == "A" and nodes[lk["target"]]["id"] == "B"]
        assert ab_links == []
        assert all(lk["value"] > 0 for lk in links)

    def test_positive_exergy_flow_is_kept(self):
        nodes, links = SankeyBuilder(self._fake_analysis(E_ab=900.0)).build()
        ab_links = [lk for lk in links if nodes[lk["source"]]["id"] == "A" and nodes[lk["target"]]["id"] == "B"]
        assert len(ab_links) == 1
        assert ab_links[0]["value"] == pytest.approx(900.0)

    def test_requires_analysed_instance(self):
        class _Empty:
            pass

        with pytest.raises(RuntimeError):
            SankeyBuilder(_Empty())


class TestWaterfall:
    def test_matplotlib_waterfall(self, ccpp):
        fig, ax = ccpp.plot_exergy_waterfall(title="test", show_plot=False)
        # fuel bar + one bar per component with valid destruction + product bar
        n_bars = len(ax.patches)
        assert n_bars > 2
        assert ax.patches[0].get_width() == pytest.approx(100.0)

    def test_plotly_waterfall(self, ccpp):
        fig = ccpp.plot_exergy_waterfall_plotly(title="test", show_plot=False)
        bar = fig.data[0]
        assert bar.type == "bar"
        # first bar: fuel from 0 to 100 %
        assert bar.base[0] == pytest.approx(0.0)
        assert bar.x[0] == pytest.approx(100.0)
        # last bar: product from 0 to epsilon_total
        df, _, _ = ccpp.exergy_results(print_results=False)
        epsilon_total = df[df["Component"] == "TOT"].iloc[0]["epsilon [%]"]
        assert bar.base[-1] == pytest.approx(0.0)
        assert bar.x[-1] == pytest.approx(epsilon_total)

    def test_plotly_waterfall_custom_colors(self, ccpp):
        fig = ccpp.plot_exergy_waterfall_plotly(show_plot=False, colors={"fuel": "#111111", "product": "#222222"})
        bar_colors = fig.data[0].marker.color
        assert bar_colors[0] == "#111111"
        assert bar_colors[-1] == "#222222"

    def test_exclude_components(self, ccpp):
        fig_all = ccpp.plot_exergy_waterfall_plotly(show_plot=False)
        fig_less = ccpp.plot_exergy_waterfall_plotly(show_plot=False, exclude_components=["CC"])
        assert len(fig_less.data[0].x) == len(fig_all.data[0].x) - 1
