"""The streams crossing the system boundary and the flow definitions built from their roles."""

import logging
import os

import pytest

from exerpy import ExergyAnalysis

EXAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "../examples"))
HEATPUMP = os.path.join(EXAMPLES, "exergoeconomic_analysis", "heatpump", "hp.json")
CGAM = os.path.join(EXAMPLES, "exergoeconomic_analysis", "cgam", "cgam.json")
CCPP = os.path.join(EXAMPLES, "exergy_analysis", "ccpp", "ccpp_tespy.json")
PARABOLIC = os.path.join(EXAMPLES, "exergy_analysis", "solar_thermal", "parabolic_ebs.json")

# The definitions the example scripts use, and the roles that amount to them.
EXAMPLES_FLOWS = {
    HEATPUMP: (
        {"e1": "F", "21": "P", "23": "P", "11": "L", "13": "L"},
        {"inputs": ["e1"], "outputs": []},
        {"inputs": ["23"], "outputs": ["21"]},
        {"inputs": ["13"], "outputs": ["11"]},
    ),
    CGAM: (
        {"10": "F", "1": "F", "8": "F", "E1": "P", "9": "P", "7": "L"},
        {"inputs": ["10", "1", "8"], "outputs": []},
        {"inputs": ["E1", "9"], "outputs": []},
        {"inputs": ["7"], "outputs": []},
    ),
    CCPP: (
        {"1": "F", "3": "F", "e15": "P", "h1": "P", "8": "L", "15": "L", "14": "L"},
        {"inputs": ["1", "3"], "outputs": []},
        {"inputs": ["e15", "h1"], "outputs": []},
        {"inputs": ["8", "15"], "outputs": ["14"]},
    ),
}


def _streams(path):
    ean = ExergyAnalysis.from_json(path)
    return ean, {stream["name"]: stream for stream in ean.boundary_streams()}


def _sorted(flow):
    return {key: sorted(names) for key, names in flow.items()}


class TestBoundaryStreams:
    def test_the_heat_pump(self):
        _, streams = _streams(HEATPUMP)
        assert {name: stream["direction"] for name, stream in streams.items()} == {
            "11": "in",
            "13": "out",
            "21": "in",
            "23": "out",
            "e1": "in",
        }
        assert streams["e1"]["kind"] == "power"
        assert streams["e1"]["outside"] == "grid"
        assert streams["23"]["outside"] == "water outlet"
        assert streams["23"]["E"] == pytest.approx(721324, rel=1e-3)

    def test_an_ebsilon_export(self):
        """Sources are marked by their type, control signals are left out, a dangling stream has no direction."""
        _, streams = _streams(CGAM)
        assert {name: stream["direction"] for name, stream in streams.items()} == {
            "1": "in",
            "10": "in",
            "8": "in",
            "7": "out",
            "9": "out",
            "E1": "out",
            "Rauchgas": None,
        }
        assert streams["Rauchgas"]["outside"] is None

    def test_a_tespy_export(self):
        _, streams = _streams(CCPP)
        assert {name: stream["direction"] for name, stream in streams.items()} == {
            "1": "in",
            "14": "in",
            "3": "in",
            "15": "out",
            "8": "out",
            "e15": "out",
            "h1": "out",
        }
        assert streams["h1"]["kind"] == "heat"
        assert streams["3"]["outside"] == "fuel inlet"

    def test_a_stream_without_exergy_is_still_reported(self):
        """The air entering the heat pump carries no exergy and is part of the loss definition nevertheless."""
        _, streams = _streams(HEATPUMP)
        assert streams["11"]["E"] == 0.0

    def test_the_heat_of_a_solar_collector_is_known_after_the_analysis(self):
        ean, streams = _streams(PARABOLIC)
        assert streams["PARAB_Q"]["direction"] == "in"
        assert streams["PARAB_Q"]["E"] is None
        ean.analyse(
            E_F={"inputs": ["PARAB_Q"], "outputs": []},
            E_P={"inputs": ["ETOT"], "outputs": []},
            E_L={"inputs": ["C2"], "outputs": ["C1"]},
        )
        after = {stream["name"]: stream for stream in ean.boundary_streams()}
        assert after["PARAB_Q"]["E"] == pytest.approx(ean.E_F)

    def test_every_other_stream_runs_between_two_components(self):
        ean, streams = _streams(HEATPUMP)
        for name in set(ean.connections) - set(streams):
            conn = ean.connections[name]
            assert conn["source_component"] in ean.components
            assert conn["target_component"] in ean.components


class TestFlowsFromRoles:
    @pytest.mark.parametrize("path", EXAMPLES_FLOWS)
    def test_the_roles_give_the_definitions_of_the_examples(self, path):
        roles, E_F, E_P, E_L = EXAMPLES_FLOWS[path]
        ean = ExergyAnalysis.from_json(path)
        built = ean.flows_from_roles(roles)
        assert [_sorted(flow) for flow in built] == [_sorted(E_F), _sorted(E_P), _sorted(E_L)]

    @pytest.mark.parametrize("path", EXAMPLES_FLOWS)
    def test_the_analysis_comes_out_the_same(self, path):
        roles, E_F, E_P, E_L = EXAMPLES_FLOWS[path]
        by_hand = ExergyAnalysis.from_json(path)
        by_hand.analyse(E_F=E_F, E_P=E_P, E_L=E_L)
        by_roles = ExergyAnalysis.from_json(path)
        by_roles.analyse(*by_roles.flows_from_roles(roles))
        assert pytest.approx((by_hand.E_F, by_hand.E_P, by_hand.E_L)) == (by_roles.E_F, by_roles.E_P, by_roles.E_L)

    def test_words_and_case_are_accepted(self):
        ean = ExergyAnalysis.from_json(HEATPUMP)
        E_F, E_P, E_L = ean.flows_from_roles(
            {"e1": "fuel", "23": "Product", "21": "PRODUCT", "13": " loss ", "11": "l"}
        )
        assert E_F == {"inputs": ["e1"], "outputs": []}
        assert E_P == {"inputs": ["23"], "outputs": ["21"]}
        assert E_L == {"inputs": ["13"], "outputs": ["11"]}

    def test_a_stream_left_out_is_part_of_no_definition(self):
        ean = ExergyAnalysis.from_json(HEATPUMP)
        flows = ean.flows_from_roles({"e1": "F", "23": "P"})
        assert all("11" not in names for flow in flows for names in flow.values())

    def test_an_unknown_role(self):
        ean = ExergyAnalysis.from_json(HEATPUMP)
        with pytest.raises(ValueError, match="neither fuel, product nor loss"):
            ean.flows_from_roles({"e1": "byproduct"})

    def test_a_stream_inside_the_plant(self):
        ean = ExergyAnalysis.from_json(HEATPUMP)
        with pytest.raises(ValueError, match="no stream crossing the system boundary"):
            ean.flows_from_roles({"E1": "F"})

    def test_a_stream_attached_on_neither_side(self):
        ean = ExergyAnalysis.from_json(CGAM)
        with pytest.raises(ValueError, match="neither side"):
            ean.flows_from_roles({"Rauchgas": "L"})


class TestUnaccountedStreams:
    """The warning about boundary streams missing from the definitions is unchanged."""

    def test_a_dangling_stream_is_reported(self, caplog):
        roles, E_F, E_P, E_L = EXAMPLES_FLOWS[CGAM]
        ean = ExergyAnalysis.from_json(CGAM)
        with caplog.at_level(logging.WARNING, logger="exerpy"):
            ean.analyse(E_F=E_F, E_P=E_P, E_L=E_L)
        assert "'Rauchgas'" in caplog.text

    def test_a_complete_definition_is_silent(self, caplog):
        roles, E_F, E_P, E_L = EXAMPLES_FLOWS[HEATPUMP]
        ean = ExergyAnalysis.from_json(HEATPUMP)
        with caplog.at_level(logging.WARNING, logger="exerpy"):
            ean.analyse(E_F=E_F, E_P=E_P, E_L=E_L)
        assert "not included in E_F, E_P, or E_L" not in caplog.text
