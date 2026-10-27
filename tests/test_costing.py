"""Purchased equipment costs from the correlations of OpenPyTEA."""

import json
import os
import runpy

import CoolProp.CoolProp as CP
import pytest

from exerpy import ExergyAnalysis
from exerpy import costing

EXAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "../examples"))
HEATPUMP = os.path.join(EXAMPLES, "exergoeconomic_analysis", "heatpump", "hp.json")
HEATPUMP_EBSILON = os.path.join(EXAMPLES, "exergy_analysis", "heatpump", "hp_ebs.json")
CCPP = os.path.join(EXAMPLES, "exergy_analysis", "ccpp", "ccpp_tespy.json")
SIMULATORS = ("tespy", "ebs", "aspen")

# Coefficients of the heat pump condenser per section; HFC/HFO condensers have no comparable cell.
CONDENSER_U = {("gas", "liquid"): 500.0, ("two-phase", "liquid"): 2500.0, ("liquid", "liquid"): 1500.0}


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
            ("steam, kg/h", ("mass_flow", 3600.0)),
            ("feed rate, lb/hr", ("mass_flow", 3600 / costing.LB)),
            ("shell mass, kg", None),
            ("flow, L/s", ("volume_flow", 1e3)),
            ("gas flowrate, m3/s", ("volume_flow", 1.0)),
            ("m^3/h", ("volume_flow", 3600.0)),
            ("Sm^3/s", None),
            ("flow at suction, ft^3/min", ("volume_flow", 60 / costing.FT3)),
            ("Flow rate gas entering fan, ACFM", ("volume_flow", 60 / costing.FT3)),
            ("wastewater rate, gal/min", ("volume_flow", 60 / costing.GALLON)),
            ("flow capacity, gpm x sqrt[head, ft]", None),
            ("(lb/hr) / (suction pressure, torr)", None),
            ("Width, in & length, ft", None),
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
        assert costing.convert(1.0, "volume_flow", "Flow rate gas entering fan, ACFM") == pytest.approx(
            2118.88, rel=1e-4
        )


def _steam_generator():
    from exerpy.components.heat_exchanger.steam_generator import SteamGenerator

    # Feed water raised to live steam, with a blowdown; enthalpies in J/kg.
    return SteamGenerator(
        name="SG",
        inl={0: {"kind": "material", "m": 10.0, "h": 500e3}, 2: {"kind": "heat", "energy_flow": 25.0e6}},
        outl={0: {"kind": "material", "m": 9.9, "h": 3000e3}, 2: {"kind": "material", "m": 0.1, "h": 1.4e6}},
    )


class TestSizes:
    def test_the_sizes_of_a_turbomachine(self, heat_pump):
        comp = heat_pump.components["COMP"]
        read = costing.sizes(comp)
        assert set(read) == {"power", "mass_flow", "volume_flow", "pressure_ratio"}
        assert read["power"] == pytest.approx(comp.P)
        assert read["mass_flow"] == pytest.approx(heat_pump.connections["33"]["m"])
        assert read["pressure_ratio"] == pytest.approx(
            heat_pump.connections["34"]["p"] / heat_pump.connections["33"]["p"]
        )

    def test_the_volume_flow_is_the_one_of_the_inlet(self, heat_pump):
        assert costing.size(heat_pump.components["FAN"], "volume_flow") == pytest.approx(
            heat_pump.connections["11"]["v"]
        )

    def test_the_power_of_a_motor_comes_from_its_power_streams(self, heat_pump):
        assert costing.sizes(heat_pump.components["MOT1"]) == {"power": pytest.approx(716_155, rel=1e-3)}

    def test_a_vessel_a_valve_and_a_combustion_chamber_have_no_size_from_the_model(self, ccpp):
        for name in ("drum", "dea steam inlet valve", "CC"):
            assert costing.sizes(ccpp.components[name]) == {}
        with pytest.raises(ValueError, match="has no size 'volume'"):
            costing.size(ccpp.components["drum"], "volume")

    def test_a_steam_generator_is_sized_by_its_heat_and_its_live_steam(self):
        read = costing.sizes(_steam_generator())
        assert read == {
            "heat": pytest.approx(9.9 * 3000e3 + 0.1 * 1.4e6 - 10.0 * 500e3),
            "mass_flow": pytest.approx(9.9),
        }

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

    def test_a_capacity_exported_in_kilowatts_per_kelvin_is_recognised(self, tmp_path):
        """Older EBSILON exports state kA in kW/K under a W/K label; the heat flow tells."""
        with open(HEATPUMP_EBSILON) as f:
            data = json.load(f)
        data["components"]["HeatExchanger"]["COND"]["kA"] /= 1e3
        older_export = tmp_path / "hp_ebs_kA_in_kW.json"
        older_export.write_text(json.dumps(data))
        ean = ExergyAnalysis.from_json(str(older_export))
        cond = ean.components["COND"]
        assert cond.kA < 1000
        design = costing.heat_exchanger(cond)
        assert design["kA"] == pytest.approx(cond.kA * 1e3)
        assert design["phase_change"] == ["hot"]

    def test_the_area_by_capacity_needs_U(self, heat_pump):
        cond = heat_pump.components["COND"]
        assert costing.size(cond, "area", method="kA") is None
        with_U = costing.heat_exchanger_area(cond, U=1000.0, method="kA")
        assert with_U["area"] == pytest.approx(costing.heat_exchanger(cond)["kA"] / 1000.0)
        assert with_U["method"] == "kA"

    def test_the_heat_and_the_capacity_of_a_heat_exchanger(self, heat_pump):
        cond = heat_pump.components["COND"]
        design = costing.heat_exchanger(cond)
        read = costing.sizes(cond, U=CONDENSER_U)
        assert read["heat"] == pytest.approx(design["Q"])
        assert read["kA"] == pytest.approx(design["kA"])
        assert read["dT_lm"] == pytest.approx(design["dT_lm"])

    def test_the_sections_of_a_condenser(self, heat_pump):
        sections = costing.heat_exchanger_sections(heat_pump.components["COND"], U=CONDENSER_U)
        phases = [(section["hot"], section["cold"]) for section in sections["sections"]]
        assert phases == [("gas", "liquid"), ("two-phase", "liquid"), ("liquid", "liquid")]
        assert sum(section["Q"] for section in sections["sections"]) == pytest.approx(sections["Q"])
        assert sections["fluids"] == {"hot": "HFC/HFO", "cold": "water/steam"}
        for section in sections["sections"]:
            assert section["U"] == CONDENSER_U[(section["hot"], section["cold"])]
            assert (section["U_scope"], section["U_cell"], section["U_sources"]) == ("user", None, [])
        expected = sum(s["Q"] / (s["U"] * s["dT_lm"]) for s in sections["sections"])
        assert sections["area"] == pytest.approx(expected)

    def test_a_steam_condenser_takes_the_coefficient_of_its_cell(self, ccpp):
        sections = costing.heat_exchanger_sections(ccpp.components["COND"])
        assert sections["fluids"] == {"hot": "water/steam", "cold": "water/steam"}
        condensing = [s for s in sections["sections"] if (s["hot"], s["cold"]) == ("two-phase", "liquid")]
        assert condensing
        cell = costing.U_DEFAULTS[("shell_and_tube", "two-phase", "liquid", "water/steam", "water/steam")]
        for section in condensing:
            assert (section["U"], section["U_scope"], section["U_cell"]) == (cell["U"], "default", cell["cell"])
            assert section["U_sources"] == cell["sources"]
            assert section["U_n_sources"] == cell["n_sources"] >= 3

    @pytest.mark.parametrize(
        ("composition", "group"),
        [
            ({"water": 1.0}, "water/steam"),
            ({"R245FA": 1.0}, "HFC/HFO"),
            ({"R1234ze(E)": 1.0}, "HFC/HFO"),
            ({"NH3": 1.0}, "ammonia"),
            ({"R290": 1.0}, "hydrocarbon refrigerants"),
            ({"NH3": 0.4, "H2O": 0.6}, "ammonia-water (absorption)"),
            ({"MM": 1.0}, "siloxanes"),
            ({"CO2": 1.0}, "CO2"),
            ({"Ar": 0.0129, "CO2": 0.0005, "N2": 0.7552, "O2": 0.2314}, "air"),
            ({"Ar": 0.012, "CO2": 0.06, "H2O": 0.05, "N2": 0.72, "O2": 0.158}, "flue gas"),
            ({"CO2": 0.049, "H2O": 0.052, "H2OG": 0.052, "N2": 0.744, "O2": 0.155}, "flue gas"),
            ({"CH4": 0.9, "C2H6": 0.1}, "natural gas"),
            ({"INCOMP::TVP1": 1.0}, "thermal oil"),
            ({"Toluene": 1.0}, "toluene/aromatics"),
            ({"Ethanol": 1.0}, None),
            ({}, None),
        ],
    )
    def test_the_fluid_group_of_a_stream(self, composition, group):
        assert costing.fluid_group({"mass_composition": composition}) == group

    def test_every_cell_names_known_sources_fluids_and_type(self):
        groups = {*costing._GROUP_NAMES, *costing._GROUP_PARTS, "HFC/HFO", "air", "flue gas"}
        groups.add("ammonia-water (absorption)")
        for cell in costing.U_CELLS:
            assert set(cell["sources"]) <= set(costing.U_SOURCES)
            assert {cell["hot_fluid"], cell["cold_fluid"]} <= groups
            assert cell["exchanger_type"] in costing.EXCHANGER_TYPES
            assert cell["range"][0] <= cell["U"] <= cell["range"][1]
            assert cell["n_sources"] <= cell["n_values"]

    def test_one_default_per_exchanger_type_phases_and_fluids(self):
        keys = {(c["exchanger_type"], c["hot"], c["cold"], c["hot_fluid"], c["cold_fluid"]) for c in costing.U_CELLS}
        assert set(costing.U_DEFAULTS) == keys
        # The residual superheat of a feedwater heater is a special zone, not the desuperheating default.
        assert costing.U_DEFAULTS[("shell_and_tube", "gas", "liquid", "water/steam", "water/steam")]["cell"] == "C016"

    def test_the_exchanger_type_selects_the_cells(self, ccpp):
        eco = ccpp.components["ECO"]
        with pytest.raises(ValueError, match=r"no comparable cell for flue gas \(gas\) to water/steam \(liquid\)"):
            costing.heat_exchanger_sections(eco)
        sections = costing.heat_exchanger_sections(eco, exchanger_type="finned_tube")
        assert [s["U_cell"] for s in sections["sections"]] == ["C037"]
        with pytest.raises(ValueError, match="Unknown exchanger type"):
            costing.heat_exchanger_sections(eco, exchanger_type="finned")

    def test_a_section_without_a_cell_asks_for_U(self, heat_pump):
        cond = heat_pump.components["COND"]
        with pytest.raises(ValueError, match=r"no comparable cell for HFC/HFO \(gas\) to water/steam \(liquid\)"):
            costing.heat_exchanger_sections(cond, exchanger_type="plate")
        partial = {("gas", "liquid"): 500.0}
        with pytest.raises(ValueError, match=r"HFC/HFO \(two-phase\) to water/steam \(liquid\)"):
            costing.heat_exchanger_sections(cond, U=partial, exchanger_type="plate")

    def test_a_default_with_few_sources_is_reported(self, ccpp, caplog):
        with caplog.at_level("WARNING", logger="exerpy"):
            costing.heat_exchanger_sections(ccpp.components["ECO"], exchanger_type="finned_tube")
        assert "rests on 1 independent source(s) (cell C037)" in caplog.text

    def test_one_U_for_every_section(self, heat_pump):
        sections = costing.heat_exchanger_sections(heat_pump.components["COND"], U=500.0)
        assert {(s["U"], s["U_scope"], s["U_cell"]) for s in sections["sections"]} == {(500.0, "user", None)}
        assert sections["area"] == pytest.approx(sum(s["Q"] / (500.0 * s["dT_lm"]) for s in sections["sections"]))

    @pytest.mark.parametrize(("p", "expected"), [(100e5, costing.SUPERCRITICAL), (30e5, costing.GAS)])
    def test_a_stream_above_its_critical_pressure_is_supercritical(self, p, expected):
        inlet, outlet = ({"m": 1.0, "T": T, "p": p, "mass_composition": {"CO2": 1.0}} for T in (400.0, 350.0))
        for conn in (inlet, outlet):
            conn["h"] = CP.PropsSI("H", "T", conn["T"], "P", p, "CO2")
        side = costing._Side(inlet, outlet, inlet["h"] - outlet["h"], hot=True)
        assert side.phase(0.5 * side.Q) == expected

    def test_the_sections_agree_between_the_exports_of_the_same_plant(self, heat_pump):
        ebsilon = ExergyAnalysis.from_json(HEATPUMP_EBSILON)
        a = costing.heat_exchanger_sections(heat_pump.components["EVA"], U=50.0)["area"]
        b = costing.heat_exchanger_sections(ebsilon.components["EVA"], U=50.0)["area"]
        assert a == pytest.approx(b, rel=1e-3)

    @pytest.mark.parametrize("plant, names", [("ccpp", ("COND", "ECO", "EVA", "SH")), ("cgam", ("APH", "EV", "PH"))])
    def test_every_simulator_gives_the_same_sections(self, plant, names):
        """Each simulator has its own enthalpy reference and its own names; the sections do not depend on them."""
        results = {}
        for simulator in SIMULATORS:
            ean = ExergyAnalysis.from_json(
                os.path.join(EXAMPLES, "exergy_analysis", plant, f"{plant}_{simulator}.json")
            )
            results[simulator] = {
                name: costing.heat_exchanger_sections(ean.components[name], U=1000.0) for name in names
            }
        for name in names:
            tespy = results["tespy"][name]
            for simulator in SIMULATORS[1:]:
                other = results[simulator][name]
                assert other is not None, (simulator, name)
                assert other["fluids"] == tespy["fluids"], (simulator, name)
                assert other["sections"][0]["hot"] == tespy["sections"][0]["hot"], (simulator, name)
                assert other["area"] == pytest.approx(tespy["area"], rel=0.03), (simulator, name)

    def test_a_stream_without_volume_flow_takes_the_phase_of_its_fluid_group(self):
        flue_gas = {"name": "fg", "m": 1.0, "mass_composition": {"N2": 0.74, "O2": 0.15, "CO2": 0.06, "H2O": 0.05}}
        assert costing._single_phase(flue_gas) == costing.GAS
        assert costing._single_phase({**flue_gas, "v": 0.5}) == costing.GAS
        assert costing._single_phase({**flue_gas, "v": 0.001}) == costing.LIQUID
        with pytest.raises(ValueError, match="no volume flow"):
            costing._single_phase({"name": "x", "m": 1.0, "mass_composition": {"Ethanol": 0.5, "Methanol": 0.5}})

    def test_a_mixture_is_followed_as_a_single_phase(self, ccpp):
        """The flue gas side of the economiser has no CoolProp fluid and counts as a gas."""
        sections = costing.heat_exchanger_sections(ccpp.components["ECO"], exchanger_type="finned_tube")
        assert [(s["hot"], s["cold"]) for s in sections["sections"]] == [("gas", "liquid")]

    def test_saturated_ends_without_quality_follow_the_export(self, ccpp):
        """A TESPy export states its enthalpies in CoolProp's frame, so the wet steam is placed."""
        sections = costing.heat_exchanger_sections(ccpp.components["COND"])
        assert sections is not None
        assert any(section["hot"] == "two-phase" for section in sections["sections"])

    def test_the_default_method_uses_the_sections(self, heat_pump):
        cond = heat_pump.components["COND"]
        read = costing.heat_exchanger_area(cond, U=CONDENSER_U)
        assert (read["method"], read["exchanger_type"]) == ("sections", "shell_and_tube")
        assert read["area"] == pytest.approx(costing.heat_exchanger_sections(cond, U=CONDENSER_U)["area"])
        assert costing.size(cond, "area", U=CONDENSER_U) == pytest.approx(read["area"])


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
        assert estimate["reference_year"] == year == 2010
        assert estimate["method"] == "correlation"
        assert estimate["quantity"] == "power"
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
        cond = heat_pump.components["COND"]
        estimate = costing.estimate(cond, "u_shell_tube_hx_towler_2010", U=CONDENSER_U)
        assert estimate["size"] == pytest.approx(costing.size(cond, "area", U=CONDENSER_U))
        assert estimate["quantity"] == "area"
        assert estimate["sizing"]["exchanger_type"] == "shell_and_tube"
        by_kA = costing.estimate(cond, "u_shell_tube_hx_towler_2010", U=1000.0, method="kA")
        assert by_kA["size"] == pytest.approx(269.7, rel=0.02)

    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            ("u_shell_tube_hx_towler_2010", "shell_and_tube"),
            ("plate_frame_hx_towler_2010", "plate"),
            ("air_cooled_finfan_seider_2013", "air_cooled"),
            ("double_pipe_hx_towler_2010", "double_pipe"),
            ("spiral_plate_hx_turton_2001", "other"),
            ("plate_fin_3streams_hx_esdu_1997", "plate_fin"),
        ],
    )
    def test_the_exchanger_type_follows_the_correlation(self, key, expected):
        assert costing.exchanger_type_of(key) == expected

    def test_a_plate_correlation_sizes_a_plate_exchanger(self, heat_pump):
        estimate = costing.estimate(heat_pump.components["COND"], "plate_frame_hx_towler_2010", U=CONDENSER_U)
        assert estimate["sizing"]["exchanger_type"] == "plate"

    def test_a_fan_is_sized_by_its_volume_flow(self, heat_pump):
        key = "centrifugal_backward_curved_fan_head_9-15_seider_2013"
        estimate = costing.estimate(heat_pump.components["FAN"], key, outside="parallel")
        assert estimate["quantity"] == "volume_flow"
        assert estimate["size"] == pytest.approx(heat_pump.connections["11"]["v"] / costing.FT3 * 60)

    def test_a_boiler_correlation_takes_the_live_steam(self):
        estimate = costing.estimate(_steam_generator(), "boilers_packaged_towler_2010")
        assert estimate["quantity"] == "mass_flow"
        assert estimate["size"] == pytest.approx(9.9 * 3600)

    def test_a_correlation_on_another_size_takes_the_size_by_hand(self, ccpp):
        drum = ccpp.components["drum"]
        with pytest.raises(ValueError, match="give the size in"):
            costing.estimate(drum, "vertical_vessel_turton_2001")
        estimate = costing.estimate(drum, "vertical_vessel_turton_2001", value=5.0)
        assert estimate["size"] == 5.0
        assert estimate["reference_year"] == 2001

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

    def test_the_purchase_costs_example(self):
        pytest.importorskip("tespy")
        example = runpy.run_path(os.path.join(EXAMPLES, "exergoeconomic_analysis", "heatpump", "hp_purchase_costs.py"))
        assert example["estimates"]["FAN"]["method"] == "parallel"
        assert example["estimates"]["FAN"]["quantity"] == "volume_flow"
        assert example["estimates"]["COMP"]["method"] == "scaled"
        analyses = {"known costs": "known", "scaled": "scaled", "equations": "eq", "openpytea": "correlated"}
        analyses["combined"] = "mixed"
        rates = {option: example[name].compute_component_costs() for option, name in analyses.items()}
        scaling = example["scaled"].scaling
        assert {name: s["size_by"] for name, s in scaling.items()} == {
            "COMP": "power",
            "FAN": "volume_flow",
            "COND": "area",
            "EVA": "area",
        }
        assert rates["openpytea"]["MOT2"][2] == 0
        for option, table in rates.items():
            assert set(table) == set(example["known_costs"]), option
            assert all(z[2] > 0 for name, z in table.items() if not (option == "openpytea" and name == "MOT2"))
        assert rates["combined"]["COMP"] == pytest.approx(rates["known costs"]["COMP"], rel=0.1)
