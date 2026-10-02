"""Purchase equipment costs from the correlations of OpenPyTEA."""

import os

import pytest

from exerpy import ExergyAnalysis
from exerpy import costing

EXAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "../examples"))
HEATPUMP = os.path.join(EXAMPLES, "exergoeconomic_analysis", "heatpump", "hp.json")
HEATPUMP_EBSILON = os.path.join(EXAMPLES, "exergy_analysis", "heatpump", "hp_ebs.json")
CCPP = os.path.join(EXAMPLES, "exergy_analysis", "ccpp", "ccpp_tespy.json")


@pytest.fixture(scope="module")
def heat_pump():
    ean = ExergyAnalysis.from_json(HEATPUMP)
    ean.analyse(*ean.flows_from_roles({"e1": "F", "21": "P", "23": "P", "11": "L", "13": "L"}))
    return ean


@pytest.fixture(scope="module")
def ccpp():
    ean = ExergyAnalysis.from_json(CCPP)
    ean.analyse(*ean.flows_from_roles({"1": "F", "3": "F", "e15": "P", "h1": "P", "8": "L", "15": "L", "14": "L"}))
    return ean


class TestUnits:
    @pytest.mark.parametrize(
        ("units", "expected"),
        [
            ("shaft power, kW", ("rate", 1e-3)),
            ("fluid power, kW", ("rate", 1e-3)),
            ("consumed power, horsepower, Hp", ("rate", 1 / costing.HP)),
            ("electric power, MWe", ("rate", 1e-6)),
            ("heat absorbed, Btu/hr", ("rate", 1 / costing.BTU_PER_HOUR)),
            ("duty, MMBTU/h", ("rate", 1e-6 / costing.BTU_PER_HOUR)),
            ("area, m^2", ("area", 1.0)),
            ("heat-transfer area, ft^2", ("area", 1 / costing.FT2)),
            ("volume, m^3", ("volume", 1.0)),
            ("volume, gal", ("volume", 1 / costing.GALLON)),
            ("steam, kg/h", None),
            ("shell mass, kg", None),
            ("flow, L/s", None),
            ("gas flowrate, m3/s", None),
            ("m^3/h", None),
            ("Sm^3/s", None),
            ("flow at suction, ft^3/min", None),
            ("wastewater rate, gal/min", None),
            ("flow capacity, gpm x sqrt[head, ft]", None),
        ],
    )
    def test_the_units_of_a_correlation(self, units, expected):
        found = costing.dimension(units)
        if expected is None:
            assert found is None
        else:
            assert found[0] == expected[0]
            assert found[1] == pytest.approx(expected[1])

    def test_a_size_is_converted_only_within_its_dimension(self):
        assert costing.convert(894_071.0, "power", "driver power, kW") == pytest.approx(894.071)
        assert costing.convert(100.0, "area", "heat-transfer area, ft^2") == pytest.approx(1076.39, rel=1e-4)
        assert costing.convert(100.0, "area", "shaft power, kW") is None
        assert costing.convert(100.0, "volume", "steam, kg/h") is None


class TestSizes:
    def test_the_power_of_a_turbomachine(self, heat_pump):
        read = costing.size(heat_pump.components["COMP"])
        assert read["quantity"] == "power"
        assert read["value"] == pytest.approx(heat_pump.components["COMP"].P)

    def test_the_power_of_a_motor_comes_from_its_power_streams(self, heat_pump):
        read = costing.size(heat_pump.components["MOT1"])
        assert read["value"] == pytest.approx(716_155, rel=1e-3)

    def test_a_vessel_a_valve_and_a_combustion_chamber_have_no_size_from_the_model(self, ccpp):
        assert costing.size(ccpp.components["drum"]) is None
        assert costing.size(ccpp.components["dea steam inlet valve"]) is None
        assert costing.size(ccpp.components["CC"]) is None

    def test_the_default_correlation_tells_steam_from_gas(self, ccpp):
        assert costing.default_correlation(ccpp.components["ST1"]) == costing.STEAM_TURBINE
        assert costing.default_correlation(ccpp.components["GT"]) == costing.DEFAULTS["Turbine"]
        assert costing.default_correlation(ccpp.components["GEN1"]) is None


class TestHeatExchangers:
    def test_the_capacity_comes_from_the_simulation(self, heat_pump):
        design = costing.heat_exchanger(heat_pump.components["COND"])
        assert design["Q"] == pytest.approx(2.1057e6, rel=1e-3)
        assert design["dT_lm"] == pytest.approx(7.8, abs=0.1)
        assert design["kA_source"] == "simulation"
        assert design["kA"] == pytest.approx(design["Q"] / design["dT_lm"], rel=0.02)

    def test_a_capacity_exported_in_kilowatts_per_kelvin_is_recognised(self):
        """Older EBSILON exports state kA in kW/K under a W/K label; the duty tells."""
        ean = ExergyAnalysis.from_json(HEATPUMP_EBSILON)
        cond = ean.components["COND"]
        assert cond.kA < 1000
        design = costing.heat_exchanger(cond)
        assert design["kA"] == pytest.approx(cond.kA * 1e3)
        assert design["phase_change"] == ["hot"]

    def test_the_area_by_capacity_needs_U(self, heat_pump):
        cond = heat_pump.components["COND"]
        without_U = costing.size(cond, method="kA")
        assert without_U["value"] is None
        with_U = costing.size(cond, U=1000.0, method="kA")
        assert with_U["value"] == pytest.approx(costing.heat_exchanger(cond)["kA"] / 1000.0)
        assert with_U["details"]["method"] == "kA"

    def test_the_sections_of_a_condenser(self, heat_pump):
        sections = costing.heat_exchanger_sections(heat_pump.components["COND"])
        phases = [(section["hot"], section["cold"]) for section in sections["sections"]]
        assert phases == [("gas", "liquid"), ("two-phase", "liquid"), ("liquid", "liquid")]
        assert sum(section["Q"] for section in sections["sections"]) == pytest.approx(sections["Q"])
        assert sections["area"] == pytest.approx(65.6, rel=0.02)
        for section in sections["sections"]:
            assert (
                section["U"]
                == costing.U_PHASE[(costing.PHASES_INDEX[section["hot"]], costing.PHASES_INDEX[section["cold"]])]
            )

    def test_the_sections_agree_between_the_exports_of_the_same_plant(self, heat_pump):
        ebsilon = ExergyAnalysis.from_json(HEATPUMP_EBSILON)
        a = costing.heat_exchanger_sections(heat_pump.components["EVA"])["area"]
        b = costing.heat_exchanger_sections(ebsilon.components["EVA"])["area"]
        assert a == pytest.approx(b, rel=1e-3)

    def test_a_mixture_is_followed_as_a_single_phase(self, ccpp):
        """The flue gas side of the economiser has no CoolProp fluid and counts as a gas."""
        sections = costing.heat_exchanger_sections(ccpp.components["ECO"])
        assert [(s["hot"], s["cold"]) for s in sections["sections"]] == [("gas", "liquid")]

    def test_saturated_ends_without_quality_follow_the_export(self, ccpp):
        """A TESPy export states its enthalpies in CoolProp's frame, so the wet steam is placed."""
        sections = costing.heat_exchanger_sections(ccpp.components["COND"])
        assert sections is not None
        assert any(section["hot"] == "two-phase" for section in sections["sections"])

    def test_the_default_method_uses_the_sections(self, heat_pump):
        read = costing.size(heat_pump.components["COND"])
        assert read["details"]["method"] == "sections"
        assert read["value"] == pytest.approx(65.6, rel=0.02)


class TestWithOpenPyTEA:
    @pytest.fixture(autouse=True)
    def _needs_openpytea(self):
        pytest.importorskip("openpytea")

    def test_the_correlations_of_a_class_come_from_its_categories(self):
        table = costing.correlations("Compressor")
        assert set(table["category"]) <= set(costing.CATEGORIES["Compressor"])
        assert "centrifugal_compressor_towler_2010" in set(table["key"])
        assert costing.correlations("Valve").empty
        assert len(costing.correlations()) > 400

    def test_the_fit_to_the_range(self):
        row = costing.correlation("centrifugal_pump_turton_2001")
        assert costing.fit(row, 50.0)["status"] == "in range"
        assert costing.fit(row, 0.5) == {"lower": 1.0, "upper": 300.0, "ratio": 0.5, "status": "below"}
        assert costing.fit(row, 600.0)["status"] == "above"
        assert costing.fit(row, 600.0)["ratio"] == pytest.approx(2.0)
        assert costing.fit(row, None)["status"] == "unknown"
        assert costing.fit({"s_lower": None, "s_upper": None}, 5.0)["status"] == "unbounded"

    def test_the_estimate_is_the_correlation_at_its_own_year(self, heat_pump):
        from openpytea.equipment import CostCorrelationDB

        comp = heat_pump.components["COMP"]
        estimate = costing.estimate(comp, "centrifugal_compressor_towler_2010")
        cost, units, year = CostCorrelationDB().evaluate("centrifugal_compressor_towler_2010", comp.P * 1e-3)
        assert estimate["PEC"] == pytest.approx(cost)
        assert estimate["cost_year"] == year == 2010
        assert estimate["method"] == "correlation"
        assert estimate["fit"]["status"] == "in range"

    def test_a_size_below_the_range_is_scaled_from_the_lower_bound(self, heat_pump):
        from openpytea.equipment import CostCorrelationDB

        pump = heat_pump.components["PUMP"]
        estimate = costing.estimate(pump, "centrifugal_pump_turton_2001")
        at_bound, _, _ = CostCorrelationDB().evaluate("centrifugal_pump_turton_2001", 1.0)
        assert estimate["method"] == "scaled"
        assert estimate["bound"] == 1.0
        assert estimate["PEC"] == pytest.approx(at_bound * (estimate["size"] / 1.0) ** costing.EXPONENT)
        assert estimate["units"] == 1
        with pytest.raises(ValueError, match="below lower bound"):
            costing.estimate(pump, "centrifugal_pump_turton_2001", outside="parallel")

    def test_a_size_above_the_range_is_scaled_or_split(self, ccpp):
        turbine = ccpp.components["GT"]
        scaled = costing.estimate(turbine, costing.DEFAULTS["Turbine"], exponent=0.7)
        assert scaled["method"] == "scaled"
        assert scaled["units"] == 1
        assert scaled["fit"]["status"] == "above"
        parallel = costing.estimate(turbine, costing.DEFAULTS["Turbine"], outside="parallel")
        assert parallel["method"] == "parallel"
        assert parallel["units"] > 1
        assert scaled["PEC"] < parallel["PEC"]

    def test_a_heat_exchanger_is_costed_by_its_sections_by_default(self, heat_pump):
        estimate = costing.estimate(heat_pump.components["COND"], "u_shell_tube_hx_towler_2010")
        assert estimate["size"] == pytest.approx(65.6, rel=0.02)
        by_kA = costing.estimate(heat_pump.components["COND"], "u_shell_tube_hx_towler_2010", U=1000.0, method="kA")
        assert by_kA["size"] == pytest.approx(269.7, rel=0.02)

    def test_a_correlation_on_another_size_takes_the_size_by_hand(self, ccpp):
        drum = ccpp.components["drum"]
        with pytest.raises(ValueError, match="give it in"):
            costing.estimate(drum, "vertical_vessel_turton_2001")
        estimate = costing.estimate(drum, "vertical_vessel_turton_2001", value=5.0)
        assert estimate["size"] == 5.0
        assert estimate["cost_year"] == 2001

    def test_an_unknown_correlation(self, heat_pump):
        with pytest.raises(KeyError):
            costing.estimate(heat_pump.components["COMP"], "no_such_key")

    def test_the_heating_value_of_a_fuel_stream(self):
        methane = {"mass_composition": {"CH4": 1.0}, "m": 2.0}
        assert costing.heating_value(methane) == pytest.approx(50.0e6)
        assert costing.energy_flow(methane) == pytest.approx(100.0e6)
        assert costing.heating_value({"mass_composition": {"N2": 0.79, "O2": 0.21}}) is None
        assert costing.energy_flow({"mass_composition": {"N2": 1.0}, "m": 1.0}) is None
        assert costing.energy_flow({"energy_flow": 5.0, "mass_composition": {"CH4": 1.0}, "m": 1.0}) == 5.0

    def test_the_exchange_rates(self):
        assert set(range(1996, 2026)) <= set(costing.USD_PER_EUR)
        assert all(0.8 < rate < 1.6 for rate in costing.USD_PER_EUR.values())
        assert costing.per_dollar("USD", 2010) == 1.0
        assert costing.per_dollar("eur", 2010) == pytest.approx(1 / 1.3257)
        assert costing.per_dollar("EUR", 1990) == pytest.approx(1 / costing.USD_PER_EUR[1996])
        assert costing.per_dollar("GBP", 2010) is None

    def test_the_cost_index_of_openpytea(self):
        index = costing.cost_index()
        assert 2001 in index and 2024 in index
        assert index[2024] > index[2001]
