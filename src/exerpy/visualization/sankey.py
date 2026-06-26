"""Sankey diagram builder for exergy analysis results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .colors import DEFAULT_NODE_COLOR
from .colors import ED_COLOR
from .colors import TERMINAL_COLORS
from .colors import connection_base_color
from .colors import hex_to_rgba
from .colors import shade

if TYPE_CHECKING:
    from exerpy.analyses import ExergyAnalysis

# Component types that are true 1:1 pass-throughs (no topological change, no transformation).
# Splitter (1→N) and Mixer (N→1) are NOT pass-throughs: they change topology.
_DEFAULT_PASSTHROUGH_TYPES: frozenset[str] = frozenset({"CycleCloser"})

# Skip destruction links for these types (E_D is None or structurally zero)
_NO_DESTRUCTION_TYPES: frozenset[str] = frozenset({"CycleCloser", "PowerBus", "Splitter", "Mixer"})

# Special terminal node IDs
_EF = "__E_F__"
_EP = "__E_P__"
_ED = "__E_D__"
_EL = "__E_L__"
_EP_NET = "__E_P_net__"
_EL_NET = "__E_L_net__"


class SankeyBuilder:
    """
    Builds a Plotly Sankey diagram from a completed ExergyAnalysis result.

    Parameters
    ----------
    analysis : ExergyAnalysis
        Must have had ``.analyse()`` called.
    mode : {1, 2, 3}
        1 – total exergy E per link
        2 – split material links into E_PH + E_CH (requires chemical_exergy_enabled)
        3 – split material links into E_T + E_M + E_CH (requires split_physical_exergy)
    collapse_passthroughs : bool or list[str]
        True  → collapse CycleCloser nodes (default)
        False → show every node
        list  → collapse only the listed component type names
    groups : dict[str, list[str]], optional
        Visual grouping: ``{"Group name": ["comp1", "comp2", ...]}``.
        Internal connections are hidden; only boundary-crossing links are shown.
    """

    def __init__(
        self,
        analysis: ExergyAnalysis,
        mode: int = 1,
        collapse_passthroughs: bool | list[str] = True,
        groups: dict[str, list[str]] | None = None,
        node_colors: dict[str, str] | None = None,
    ) -> None:
        if not hasattr(analysis, "E_F"):
            raise RuntimeError("Call ExergyAnalysis.analyse() before building Sankey.")
        if mode == 2 and not analysis.chemical_exergy_enabled:
            raise ValueError("Mode 2 requires chemical_exergy_enabled=True.")
        if mode == 3 and not analysis.split_physical_exergy:
            raise ValueError("Mode 3 requires split_physical_exergy=True.")

        self.analysis = analysis
        self.mode = mode
        self.groups: dict[str, list[str]] = groups or {}
        self.node_colors: dict[str, str] = node_colors or {}

        if collapse_passthroughs is True:
            self._passthrough_types: frozenset[str] = _DEFAULT_PASSTHROUGH_TYPES
        elif collapse_passthroughs is False:
            self._passthrough_types = frozenset()
        else:
            self._passthrough_types = frozenset(collapse_passthroughs)

        self._nodes: list[dict] = []
        self._links: list[dict] = []
        self._node_idx: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> tuple[list[dict], list[dict]]:
        """Build and return ``(nodes, links)`` lists."""
        self._nodes = []
        self._links = []
        self._node_idx = {}

        collapsed = self._find_collapsed()
        routes = self._build_routes(collapsed)
        terminal_ids = self._terminal_conn_ids()

        self._add_component_nodes(collapsed)
        self._add_terminal_nodes()
        self._add_connection_links(routes, terminal_ids)
        self._add_destruction_links(collapsed)
        self._add_terminal_links(routes)

        if self.groups:
            self._apply_grouping()

        return self._nodes, self._links

    def to_plotly(self, title: str | None = None):
        """Return a Plotly ``Figure`` containing the Sankey trace."""
        try:
            import plotly.graph_objects as go
        except ImportError as exc:
            raise ImportError("plotly is required for Sankey diagrams: pip install plotly") from exc

        nodes, links = self.build()
        fig = go.Figure(go.Sankey(
            arrangement="snap",
            node=dict(
                pad=15,
                thickness=20,
                label=[n["label"] for n in nodes],
                color=[n["color"] for n in nodes],
            ),
            link=dict(
                source=[lk["source"] for lk in links],
                target=[lk["target"] for lk in links],
                value=[max(lk["value"], 0.0) for lk in links],
                color=[lk["color"] for lk in links],
                label=[lk.get("label", "") for lk in links],
            ),
        ))
        fig.update_layout(
            title_text=title or "Exergy Sankey Diagram",
            font_size=12,
        )
        return fig

    def to_html(self, path: str, title: str | None = None) -> None:
        """Export the Sankey diagram to an HTML file."""
        self.to_plotly(title=title).write_html(path)

    # ------------------------------------------------------------------
    # Node building
    # ------------------------------------------------------------------

    def _add_node(self, node_id: str, label: str, color: str) -> int:
        idx = len(self._nodes)
        self._nodes.append({"id": node_id, "label": label, "color": color})
        self._node_idx[node_id] = idx
        return idx

    def _find_collapsed(self) -> set[str]:
        return {
            name
            for name, comp in self.analysis.components.items()
            if comp.__class__.__name__ in self._passthrough_types
        }

    def _add_component_nodes(self, collapsed: set[str]) -> None:
        for comp_name in self.analysis.components:
            if comp_name in collapsed:
                continue
            color = self.node_colors.get(comp_name, DEFAULT_NODE_COLOR)
            self._add_node(comp_name, comp_name, color)

    def _add_terminal_nodes(self) -> None:
        for node_id, label, key in (
            (_EF, "E_F (Fuel)", "E_F"),
            (_EP, "E_P (Product)", "E_P"),
            (_ED, "E_D (Destruction)", "E_D"),
            (_EL, "E_L (Loss)", "E_L"),
        ):
            self._add_node(node_id, label, TERMINAL_COLORS[key])

        # Intermediate "net" nodes only when a terminal has both inputs and outputs
        if self.analysis.E_P_dict.get("inputs") and self.analysis.E_P_dict.get("outputs"):
            self._add_node(_EP_NET, "E_P net", TERMINAL_COLORS["E_P"])
        if self.analysis.E_L_dict.get("inputs") and self.analysis.E_L_dict.get("outputs"):
            self._add_node(_EL_NET, "E_L net", TERMINAL_COLORS["E_L"])

    # ------------------------------------------------------------------
    # Routing (for 1:1 collapsed pass-through nodes)
    # ------------------------------------------------------------------

    def _build_routes(
        self, collapsed: set[str]
    ) -> dict[str, tuple[str | None, str | None] | None]:
        """
        Return ``{conn_id: (eff_source, eff_target)}`` after collapsing pass-through nodes.

        Connections whose *target* is a collapsed node are marked ``None`` (skipped).
        Connections whose *source* is a collapsed node get their source remapped to
        the real upstream component via the pass-through chain.
        """
        conns = self.analysis.connections

        def upstream(comp: str | None, depth: int = 0) -> str | None:
            if comp is None or comp not in collapsed or depth > 50:
                return comp
            for cd in conns.values():
                if cd.get("target_component") == comp:
                    return upstream(cd.get("source_component"), depth + 1)
            return comp

        routes: dict[str, tuple[str | None, str | None] | None] = {}
        for conn_id, cd in conns.items():
            src = cd.get("source_component")
            tgt = cd.get("target_component")
            if tgt in collapsed:
                # Input to a collapsed node: skip (the downstream connection takes over)
                routes[conn_id] = None
            elif src in collapsed:
                # Output from collapsed node: remap source to real upstream
                routes[conn_id] = (upstream(src), tgt)
            else:
                routes[conn_id] = (src, tgt)

        return routes

    def _terminal_conn_ids(self) -> set[str]:
        result: set[str] = set()
        for d in (self.analysis.E_F_dict, self.analysis.E_P_dict, self.analysis.E_L_dict):
            result.update(d.get("inputs", []))
            result.update(d.get("outputs", []))
        return result

    # ------------------------------------------------------------------
    # Link building
    # ------------------------------------------------------------------

    def _add_link(
        self, source_id: str, target_id: str, value: float, color: str, label: str = ""
    ) -> None:
        if not (value > 0):
            return
        src = self._node_idx.get(source_id)
        tgt = self._node_idx.get(target_id)
        if src is None or tgt is None:
            return
        self._links.append({"source": src, "target": tgt, "value": value, "color": color, "label": label})

    def _sub_links(self, conn_data: dict) -> list[tuple[float, str, str]]:
        """Return ``[(value_W, rgba_color, sub_label), ...]`` based on self.mode."""
        kind = conn_data.get("kind")
        E = conn_data.get("E") or 0
        base = connection_base_color(conn_data)

        # Non-material connections and mode 1 always use total E
        if kind in ("power", "heat") or self.mode == 1:
            return [(E, hex_to_rgba(base, 0.5), "E")]

        if self.mode == 2:
            E_PH = conn_data.get("E_PH") or 0
            E_CH = conn_data.get("E_CH") or 0
            result = []
            if E_PH > 0:
                result.append((E_PH, hex_to_rgba(base, 0.6), "E_PH"))
            if E_CH > 0:
                result.append((E_CH, hex_to_rgba(shade(base, 0.75), 0.5), "E_CH"))
            return result or [(E, hex_to_rgba(base, 0.5), "E")]

        # mode 3: E_T = e_T * m, E_M = e_M * m, E_CH from stored value
        m = conn_data.get("m") or 0
        e_T = conn_data.get("e_T") or 0
        e_M = conn_data.get("e_M") or 0
        E_T = e_T * m
        E_M = e_M * m
        E_CH = conn_data.get("E_CH") or 0
        result = []
        if E_T > 0:
            result.append((E_T, hex_to_rgba(base, 0.70), "E_T"))
        if E_M > 0:
            result.append((E_M, hex_to_rgba(shade(base, 0.80), 0.60), "E_M"))
        if E_CH > 0:
            result.append((E_CH, hex_to_rgba(shade(base, 0.60), 0.50), "E_CH"))
        return result or [(E, hex_to_rgba(base, 0.5), "E")]

    def _add_connection_links(
        self, routes: dict, terminal_ids: set[str]
    ) -> None:
        for conn_id, conn_data in self.analysis.connections.items():
            if conn_id in terminal_ids:
                continue
            route = routes.get(conn_id)
            if route is None:
                continue
            src_id, tgt_id = route
            if src_id not in self._node_idx or tgt_id not in self._node_idx:
                continue
            if src_id == tgt_id:
                continue
            for value, color, sub_label in self._sub_links(conn_data):
                self._add_link(src_id, tgt_id, value, color, f"{conn_id} [{sub_label}]: {value * 1e-3:.1f} kW")

    def _add_destruction_links(self, collapsed: set[str]) -> None:
        ed_color = hex_to_rgba(ED_COLOR, 0.4)
        for comp_name, comp in self.analysis.components.items():
            if comp_name in collapsed:
                continue
            if comp.__class__.__name__ in _NO_DESTRUCTION_TYPES:
                continue
            E_D = getattr(comp, "E_D", None)
            if not (E_D and E_D > 0):
                continue
            self._add_link(comp_name, _ED, E_D, ed_color, f"{comp_name} E_D: {E_D * 1e-3:.1f} kW")

    def _add_terminal_links(self, routes: dict) -> None:
        conns = self.analysis.connections
        use_ep_net = _EP_NET in self._node_idx
        use_el_net = _EL_NET in self._node_idx

        def _color(conn_data: dict) -> str:
            return hex_to_rgba(connection_base_color(conn_data), 0.5)

        def _E(conn_id: str) -> float:
            cd = conns.get(conn_id)
            return (cd.get("E") or 0) if cd else 0

        def _inside(conn_id: str, side: str) -> str | None:
            """Return the component node ID on 'source' or 'target' side that is inside the system."""
            cd = conns.get(conn_id)
            if cd is None:
                return None
            # Use routing if available (handles collapsed nodes)
            route = routes.get(conn_id)
            if route is not None:
                src, tgt = route
            else:
                src, tgt = cd.get("source_component"), cd.get("target_component")
            node_id = src if side == "source" else tgt
            return node_id if node_id in self._node_idx else None

        def _lbl(conn_id: str, tag: str) -> str:
            return f"{conn_id} [{tag}]: {_E(conn_id) * 1e-3:.1f} kW"

        # --- E_F ---
        # "inputs": fuel flows from outside INTO the system → E_F node → component
        for c in self.analysis.E_F_dict.get("inputs", []):
            tgt = _inside(c, "target")
            if tgt:
                self._add_link(_EF, tgt, _E(c), _color(conns[c]), _lbl(c, "E_F in"))

        # "outputs": something returns from system back to fuel boundary → component → E_F node
        for c in self.analysis.E_F_dict.get("outputs", []):
            src = _inside(c, "source")
            if src:
                self._add_link(src, _EF, _E(c), _color(conns[c]), _lbl(c, "E_F return"))

        # --- E_P ---
        # "inputs": product leaves system → component → E_P (or intermediate)
        ep_sink = _EP_NET if use_ep_net else _EP
        for c in self.analysis.E_P_dict.get("inputs", []):
            src = _inside(c, "source")
            if src:
                self._add_link(src, ep_sink, _E(c), _color(conns[c]), _lbl(c, "E_P"))

        # "outputs": something enters system as part of product definition → intermediate → component
        for c in self.analysis.E_P_dict.get("outputs", []):
            tgt = _inside(c, "target")
            if tgt:
                self._add_link(ep_sink, tgt, _E(c), _color(conns[c]), _lbl(c, "E_P return"))

        # Net link from intermediate to final E_P node
        if use_ep_net:
            net = self.analysis.E_P
            self._add_link(_EP_NET, _EP, net, hex_to_rgba(TERMINAL_COLORS["E_P"], 0.7), f"E_P net: {net * 1e-3:.1f} kW")

        # --- E_L ---
        el_sink = _EL_NET if use_el_net else _EL
        for c in self.analysis.E_L_dict.get("inputs", []):
            src = _inside(c, "source")
            if src:
                self._add_link(src, el_sink, _E(c), _color(conns[c]), _lbl(c, "E_L"))

        for c in self.analysis.E_L_dict.get("outputs", []):
            tgt = _inside(c, "target")
            if tgt:
                self._add_link(el_sink, tgt, _E(c), _color(conns[c]), _lbl(c, "E_L return"))

        if use_el_net:
            net = self.analysis.E_L
            self._add_link(_EL_NET, _EL, net, hex_to_rgba(TERMINAL_COLORS["E_L"], 0.7), f"E_L net: {net * 1e-3:.1f} kW")

    # ------------------------------------------------------------------
    # Grouping
    # ------------------------------------------------------------------

    def _apply_grouping(self) -> None:
        """
        Replace groups of components with single aggregate nodes.
        Internal connections (both endpoints in the same group) are dropped.
        Cross-boundary connections are remapped to the group node.
        """
        comp_to_group: dict[str, str] = {
            member: gname
            for gname, members in self.groups.items()
            for member in members
        }

        new_nodes: list[dict] = []
        new_idx: dict[str, int] = {}
        group_added: set[str] = set()

        for node in self._nodes:
            nid = node["id"]
            if nid in comp_to_group:
                gname = comp_to_group[nid]
                if gname not in group_added:
                    gidx = len(new_nodes)
                    new_idx[gname] = gidx
                    new_nodes.append({"id": gname, "label": f"[{gname}]", "color": "#546E7A"})
                    group_added.add(gname)
                new_idx[nid] = new_idx[gname]
            else:
                new_idx[nid] = len(new_nodes)
                new_nodes.append(node)

        new_links: list[dict] = []
        for lk in self._links:
            old_src_id = self._nodes[lk["source"]]["id"]
            old_tgt_id = self._nodes[lk["target"]]["id"]
            grp_src = comp_to_group.get(old_src_id)
            grp_tgt = comp_to_group.get(old_tgt_id)

            # Drop connections internal to a group
            if grp_src and grp_tgt and grp_src == grp_tgt:
                continue

            new_src = grp_src or old_src_id
            new_tgt = grp_tgt or old_tgt_id
            new_src_idx = new_idx[new_src]
            new_tgt_idx = new_idx[new_tgt]
            if new_src_idx == new_tgt_idx:
                continue

            new_links.append({**lk, "source": new_src_idx, "target": new_tgt_idx})

        self._nodes = new_nodes
        self._links = new_links
        self._node_idx = {n["id"]: i for i, n in enumerate(new_nodes)}
