"""Tests for the EconomicAnalysis class, which turns equipment costs into component cost rates."""

import logging
import os

import numpy as np
import pandas as pd
import pytest

from exerpy.analyses import EconomicAnalysis
from exerpy.analyses import ExergoeconomicAnalysis
from exerpy.analyses import ExergyAnalysis

PEC = {"COMP": 300000.0, "COND": 120000.0, "EVA": 150000.0, "VAL": 5000.0}
PARAMETERS = {"i_eff": 0.12, "n": 20, "tau": 6000, "f_tci": 6.32, "omc_share": 0.015}

HEATPUMP = os.path.abspath(os.path.join(os.path.dirname(__file__), "../examples/exergoeconomic_analysis/heatpump"))


def _economic(**overrides):
    return EconomicAnalysis(PEC=PEC, **{**PARAMETERS, **overrides})


class TestFactors:
    def test_capital_recovery_factor(self):
        """CRF = i (1+i)^n / ((1+i)^n - 1)."""
        eco = _economic()
        i, n = PARAMETERS["i_eff"], PARAMETERS["n"]
        assert eco.compute_crf() == pytest.approx(i * (1 + i) ** n / ((1 + i) ** n - 1))

    def test_cost_escalation_levelization_factor(self):
        eco = _economic(r_n=0.05)
        k = 1.05 / 1.12
        assert eco.compute_celf() == pytest.approx(k * (1 - k**20) / (1 - k) * eco.compute_crf())

    @pytest.mark.parametrize(
        ("r_n", "expected", "given", "levelized"),
        [
            (0.06, 1.57883, 8.336e6, 12.417e6),  # fuel
            (0.05, 1.45581, 4.981e6, 6.905e6),  # operating and maintenance
        ],
    )
    def test_against_the_worked_example_of_the_reference(self, r_n, expected, given, levelized):
        """Bejan et al. levelize the cogeneration plant of their chapter 3 with these numbers.

        The factor carries a leading k, and the cost it multiplies is the one at the beginning of the
        first year, so the expenditure of the first year has to be discounted by its own escalation.
        """
        eco = EconomicAnalysis(PEC={"X": 1.0}, i_eff=0.12, n=20, tau=8000, f_tci=1.0, omc_share=0.0)
        assert eco.compute_crf() == pytest.approx(0.13388, abs=5e-6)
        assert eco.compute_celf(r_n) == pytest.approx(expected, abs=5e-6)
        # The reference prints its results rounded to thousands of dollars.
        assert given / (1 + r_n) * eco.compute_celf(r_n) == pytest.approx(levelized, rel=5e-4)

    def test_escalation_equal_to_the_rate_of_return(self):
        """k = 1 would divide by zero; the factor is n times the CRF there."""
        eco = _economic(r_n=PARAMETERS["i_eff"])
        assert eco.compute_celf() == pytest.approx(PARAMETERS["n"] * eco.compute_crf())

    def test_total_capital_investment_grows_the_equipment_cost(self):
        eco = _economic()
        assert eco.total_PEC == pytest.approx(sum(PEC.values()))
        assert pytest.approx(6.32 * sum(PEC.values())) == eco.TCI


class TestCostRates:
    def test_the_cost_rates_add_up_to_the_revenue_requirement(self):
        eco = _economic()
        total = sum(Z for _, _, Z in eco.compute_component_costs().values())
        assert total == pytest.approx(eco.total_revenue_requirement() / eco.tau)

    def test_the_revenue_requirement_is_carrying_charges_plus_om(self):
        eco = _economic()
        assert eco.total_revenue_requirement() == pytest.approx(
            eco.levelized_carrying_charges() + eco.levelized_om_costs()
        )

    def test_the_cost_rates_are_shared_out_by_equipment_cost(self):
        eco = _economic()
        costs = eco.compute_component_costs()
        total_Z = sum(Z for _, _, Z in costs.values())
        for name, (_, _, Z) in costs.items():
            assert Z / total_Z == pytest.approx(PEC[name] / sum(PEC.values()))

    def test_the_operating_hours_scale_every_cost_rate(self):
        """A plant running half the year carries twice the cost rate."""
        base = _economic(tau=8000).compute_z()
        half = _economic(tau=4000).compute_z()
        for key, value in base.items():
            assert half[key] == pytest.approx(2 * value)

    def test_a_share_of_om_cost_per_component(self):
        shares = {"COMP": 0.03, "COND": 0.01, "EVA": 0.02, "VAL": 0.0}
        eco = _economic(omc_share=shares)
        first_year = eco.first_year_om_costs()
        for name, share in shares.items():
            assert first_year[name] == pytest.approx(share * PEC[name])

    def test_an_installation_factor_per_component(self):
        """A component with a higher f_TCI carries a proportionally higher investment cost rate."""
        factors = {"COMP": 4.0, "COND": 8.0, "EVA": 6.0, "VAL": 2.0}
        eco = _economic(f_tci=factors, omc_share=0.0)
        costs = eco.compute_component_costs()
        crf = eco.compute_crf()
        for name, factor in factors.items():
            assert costs[name][0] == pytest.approx(factor * PEC[name] * crf / eco.tau)
        assert pytest.approx(sum(factors[n] * PEC[n] for n in PEC)) == eco.TCI

    def test_compute_z_is_keyed_for_the_exergoeconomic_analysis(self):
        eco = _economic()
        z = eco.compute_z()
        assert set(z) == {f"{name}_Z" for name in PEC}
        assert all(value > 0 for value in z.values())


class TestValidation:
    @pytest.mark.parametrize(
        ("overrides", "match"),
        [
            ({"i_eff": 0}, "'i_eff' has to be a positive number"),
            ({"n": 0}, "'n' has to be a positive number"),
            ({"tau": -1}, "'tau' has to be a positive number"),
            ({"f_tci": 0}, "'f_tci' of component .* is not a positive number"),
        ],
    )
    def test_a_parameter_that_cannot_be_zero(self, overrides, match):
        with pytest.raises(ValueError, match=match):
            _economic(**overrides)

    def test_a_negative_equipment_cost(self):
        with pytest.raises(ValueError, match="not a positive number"):
            EconomicAnalysis(PEC={"COMP": -1.0}, **PARAMETERS)

    def test_a_missing_factor_for_one_component(self):
        with pytest.raises(ValueError, match="'omc_share' is missing for component"):
            _economic(omc_share={"COMP": 0.02})

    def test_no_equipment_cost_at_all(self):
        with pytest.raises(ValueError, match="at least one component is required"):
            EconomicAnalysis(PEC={}, **PARAMETERS)

    def test_a_share_for_a_component_without_an_equipment_cost(self):
        with pytest.raises(ValueError, match="names components without a purchase equipment cost"):
            _economic(omc_share={"NOT_THERE": 0.02})


class TestResults:
    def test_two_tables_with_a_total_row(self):
        df_components, df_plant = _economic().economic_results(print_results=False)
        assert isinstance(df_components, pd.DataFrame) and isinstance(df_plant, pd.DataFrame)
        assert "TOT" in df_components.index
        assert df_components.loc["TOT", "PEC [EUR]"] == pytest.approx(sum(PEC.values()))
        assert set(df_plant.index) >= {"PEC", "TCI", "CRF", "CELF", "TRR levelized"}
        assert np.isfinite(df_plant.loc["TRR levelized", "value"])

    def test_the_currency_shows_up_in_the_columns(self):
        df_components, df_plant = _economic().economic_results(print_results=False)
        assert any("EUR" in column for column in df_components.columns)
        eco = EconomicAnalysis(PEC=PEC, currency="USD", **PARAMETERS)
        df_components, _ = eco.economic_results(print_results=False)
        assert any("USD" in column for column in df_components.columns)


def _heatpump_analysis():
    ean = ExergyAnalysis.from_json(os.path.join(HEATPUMP, "hp.json"))
    ean.analyse(
        E_F={"inputs": ["e1"], "outputs": []},
        E_P={"inputs": ["23"], "outputs": ["21"]},
        E_L={"inputs": ["13"], "outputs": ["11"]},
    )
    return ean


def _example_pec():
    """The purchase equipment costs of the heat pump example."""
    return EconomicAnalysis.from_json(os.path.join(HEATPUMP, "hp_costs_detailed.json")).PEC


class TestAgainstAPlant:
    def test_a_component_without_an_equipment_cost_is_reported(self):
        ean = _heatpump_analysis()
        incomplete = dict(_example_pec())
        del incomplete["VAL"]
        eco = EconomicAnalysis(PEC=incomplete, **PARAMETERS)
        with pytest.raises(ValueError, match=r"No purchase equipment cost for the components \['VAL'\]"):
            eco.compute_z(ean)

    def test_an_equipment_cost_for_a_component_that_is_not_there(self):
        ean = _heatpump_analysis()
        eco = EconomicAnalysis(PEC={**_example_pec(), "GHOST": 1000.0}, **PARAMETERS)
        with pytest.raises(ValueError, match="not in the plant"):
            eco.compute_z(ean)

    def test_an_equipment_cost_for_a_component_that_carries_no_cost_balance(self):
        """The cycle closer and the power bus are wiring, not equipment."""
        ean = _heatpump_analysis()
        eco = EconomicAnalysis(PEC={**_example_pec(), "cc": 1000.0}, **PARAMETERS)
        with pytest.raises(ValueError, match="carry no cost balance"):
            eco.compute_z(ean)

    def test_the_whole_workflow_from_equipment_cost_to_product_cost(self):
        """The cost rates feed the exergoeconomic analysis and the cost balance of the plant closes."""
        ean = _heatpump_analysis()
        eco = EconomicAnalysis(PEC=_example_pec(), **PARAMETERS)
        costs = {**eco.compute_z(ean), "e1_c": 30.0, "11_c": 0.0, "21_c": 0.0}

        exergoeco = ExergoeconomicAnalysis(ean, currency="EUR")
        exergoeco.run(costs)

        system = exergoeco.system_costs
        assert system["C_P"] == pytest.approx(system["C_F"] + system["Z"], rel=1e-6)
        # The investment the economic analysis levelized is the investment the plant is charged.
        assert system["Z"] == pytest.approx(eco.total_revenue_requirement() / eco.tau, rel=1e-9)
        for name, (residual, balanced) in exergoeco.check_cost_balance(tol=1e-6).items():
            assert balanced, f"{name} not balanced: residual={residual}"


class TestFromJson:
    """The cost assumptions can come from a file instead of the script."""

    def _write(self, tmp_path, data):
        import json

        path = tmp_path / "costs.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_a_plant_wide_value_is_overridden_per_component(self, tmp_path):
        path = self._write(
            tmp_path,
            {
                "i_eff": 0.12,
                "n": 20,
                "tau": 6000,
                "f_tci": 4.5,
                "omc_share": 0.015,
                "components": {"COMP": {"PEC": 300000.0, "f_tci": 6.3}, "VAL": {"PEC": 5000.0}},
            },
        )
        eco = EconomicAnalysis.from_json(path)
        assert eco.f_tci == {"COMP": 6.3, "VAL": 4.5}
        assert eco.omc_share == {"COMP": 0.015, "VAL": 0.015}

    def test_a_component_may_be_a_plain_number(self, tmp_path):
        path = self._write(
            tmp_path,
            {"i_eff": 0.12, "n": 20, "tau": 6000, "f_tci": 4.5, "omc_share": 0.015, "components": {"VAL": 5000.0}},
        )
        assert EconomicAnalysis.from_json(path).PEC == {"VAL": 5000.0}

    def test_the_years_of_the_cost_index_are_read_as_numbers(self, tmp_path):
        """JSON has no integer keys, so the years arrive as strings."""
        path = self._write(
            tmp_path,
            {
                "i_eff": 0.12,
                "n": 20,
                "tau": 6000,
                "f_tci": 4.5,
                "omc_share": 0.015,
                "reference_year": 2025,
                "cost_index": {"2021": 112.0, "2025": 143.0},
                "components": {"COMP": {"PEC": 100000.0, "cost_year": 2021}},
            },
        )
        eco = EconomicAnalysis.from_json(path)
        assert set(eco.cost_index) == {2021, 2025}
        assert eco.reference_PEC["COMP"] == pytest.approx(100000.0 * 143.0 / 112.0)

    def test_a_stream_cost_may_be_a_plain_number(self, tmp_path):
        path = self._write(
            tmp_path,
            {
                "i_eff": 0.12,
                "n": 20,
                "tau": 6000,
                "f_tci": 4.5,
                "omc_share": 0.015,
                "components": {"VAL": 5000.0},
                "fuel_costs": {"e1": {"c": 30.0, "r_n": 0.04}, "11": 0.0},
            },
        )
        eco = EconomicAnalysis.from_json(path)
        assert eco.compute_c()["11_c"] == pytest.approx(0.0)
        assert eco.compute_c()["e1_c"] == pytest.approx(30.0 * eco.compute_celf(0.04))

    def test_a_key_that_is_not_a_cost_assumption(self, tmp_path):
        path = self._write(
            tmp_path,
            {
                "i_eff": 0.12,
                "n": 20,
                "tau": 6000,
                "f_tci": 4.5,
                "omc_share": 0.015,
                "components": {"VAL": 5000.0},
                "taux": 1,
            },
        )
        with pytest.raises(ValueError, match="keys that are not cost assumptions"):
            EconomicAnalysis.from_json(path)

    def test_a_component_without_an_equipment_cost(self, tmp_path):
        path = self._write(
            tmp_path,
            {
                "i_eff": 0.12,
                "n": 20,
                "tau": 6000,
                "f_tci": 4.5,
                "omc_share": 0.015,
                "components": {"VAL": {"f_tci": 3.0}},
            },
        )
        with pytest.raises(ValueError, match="has no purchase equipment cost"):
            EconomicAnalysis.from_json(path)

    def test_no_components_at_all(self, tmp_path):
        path = self._write(tmp_path, {"i_eff": 0.12, "n": 20, "tau": 6000, "f_tci": 4.5, "omc_share": 0.015})
        with pytest.raises(ValueError, match="describes no components"):
            EconomicAnalysis.from_json(path)

    @pytest.mark.parametrize("filename", ["hp_costs_simple.json", "hp_costs_detailed.json"])
    def test_either_example_file_costs_the_plant(self, filename):
        """The same plant, described once with one set of assumptions and once per component."""
        ean = _heatpump_analysis()
        eco = EconomicAnalysis.from_json(os.path.join(HEATPUMP, filename))
        exergoeco = ExergoeconomicAnalysis(ean, currency="EUR")
        exergoeco.run(eco.compute_costs(ean))
        assert exergoeco.system_costs["C_P"] == pytest.approx(
            exergoeco.system_costs["C_F"] + exergoeco.system_costs["Z"], rel=1e-6
        )

    def test_the_simple_file_needs_no_index_and_no_per_component_entry(self):
        """Every component takes the values given once for the whole plant."""
        eco = EconomicAnalysis.from_json(os.path.join(HEATPUMP, "hp_costs_simple.json"))
        assert set(eco.f_tci.values()) == {6.32}
        assert set(eco.omc_share.values()) == {0.015}
        assert set(eco.cost_year.values()) == {None}
        assert eco.cost_index == {}
        # Nothing is escalated, so the reference cost is the cost as given.
        assert eco.total_PEC == pytest.approx(sum(eco.PEC.values()))

    def test_the_example_file_drives_the_whole_workflow(self):
        """The file of the heat pump example costs the plant and the cost balance closes."""
        ean = _heatpump_analysis()
        eco = EconomicAnalysis.from_json(os.path.join(HEATPUMP, "hp_costs_detailed.json"))
        exergoeco = ExergoeconomicAnalysis(ean, currency="EUR")
        exergoeco.run(eco.compute_costs(ean))

        system = exergoeco.system_costs
        assert system["C_P"] == pytest.approx(system["C_F"] + system["Z"], rel=1e-6)
        assert system["Z"] == pytest.approx(sum(eco.compute_z().values()), rel=1e-9)
        # The quotes come from three different years and are all carried to 2025.
        assert eco.reference_year == 2025
        assert eco.total_PEC > sum(eco.PEC.values())
        for name, (residual, balanced) in exergoeco.check_cost_balance(tol=1e-6).items():
            assert balanced, f"{name} not balanced: residual={residual}"


class TestCostIndexAndOmBasis:
    """The two refinements the reference method needs beyond a single index ratio."""

    def test_the_index_is_bridged_to_a_reference_year_it_does_not_reach(self, caplog):
        """A published index stops at the last year that has passed; the rest escalates."""
        eco = EconomicAnalysis(
            PEC={"C": 100000.0},
            i_eff=0.10,
            n=20,
            tau=7500,
            f_tci=4.16,
            omc_share=0.03,
            cost_year=2013,
            reference_year=2026,
            cost_index={2013: 1.0, 2024: 1.4102},
            r_n=0.02,
        )
        with caplog.at_level(logging.WARNING):
            escalated = eco.reference_PEC["C"]
        assert escalated == pytest.approx(100000.0 * 1.4102 * 1.02**2)
        assert "bridged with the nominal escalation rate" in caplog.text

    def test_the_index_alone_is_used_when_it_reaches_the_reference_year(self):
        eco = EconomicAnalysis(
            PEC={"C": 100000.0},
            i_eff=0.10,
            n=20,
            tau=7500,
            f_tci=4.0,
            omc_share=0.03,
            cost_year=2021,
            reference_year=2025,
            cost_index={2021: 112.0, 2025: 143.0},
            r_n=0.02,
        )
        assert eco.reference_PEC["C"] == pytest.approx(100000.0 * 143.0 / 112.0)

    def test_costs_from_several_years_need_an_index(self):
        with pytest.raises(ValueError, match="'cost_index' is required"):
            EconomicAnalysis(
                PEC={"A": 1.0, "B": 2.0},
                i_eff=0.1,
                n=20,
                tau=7500,
                f_tci=4.0,
                omc_share=0.03,
                cost_year={"A": 2020, "B": 2024},
                reference_year=2024,
            )

    @pytest.mark.parametrize("basis", ["PEC", "TCI"])
    def test_the_maintenance_share_may_be_taken_of_either_basis(self, basis):
        eco = EconomicAnalysis(
            PEC={"C": 100000.0}, i_eff=0.10, n=20, tau=7500, f_tci=4.16, omc_share=0.03, omc_basis=basis
        )
        expected = 0.03 * 100000.0 * (4.16 if basis == "TCI" else 1.0)
        assert eco.first_year_om_costs()["C"] == pytest.approx(expected)

    def test_the_two_bases_differ_by_the_installation_factor(self):
        """A share meant for the total investment is badly wrong on the equipment cost."""
        kwargs = dict(PEC={"C": 100000.0}, i_eff=0.10, n=20, tau=7500, f_tci=4.16, omc_share=0.03)
        on_pec = EconomicAnalysis(**kwargs, omc_basis="PEC").levelized_om_costs()
        on_tci = EconomicAnalysis(**kwargs, omc_basis="TCI").levelized_om_costs()
        assert on_tci / on_pec == pytest.approx(4.16)

    def test_an_unknown_basis(self):
        with pytest.raises(ValueError, match="'omc_basis' is neither 'PEC' nor 'TCI'"):
            EconomicAnalysis(PEC={"C": 1.0}, i_eff=0.1, n=20, tau=7500, f_tci=4.0, omc_share=0.03, omc_basis="FCI")

    def test_the_basis_can_be_set_in_the_json_file(self, tmp_path):
        import json

        path = tmp_path / "costs.json"
        path.write_text(
            json.dumps(
                {
                    "i_eff": 0.1,
                    "n": 20,
                    "tau": 7500,
                    "f_tci": 4.16,
                    "omc_share": 0.03,
                    "omc_basis": "TCI",
                    "components": {"C": 100000.0},
                }
            ),
            encoding="utf-8",
        )
        eco = EconomicAnalysis.from_json(str(path))
        assert eco.omc_basis == "TCI"
        assert eco.first_year_om_costs()["C"] == pytest.approx(0.03 * 4.16 * 100000.0)


class TestLevelizedFuelCost:
    """The cost of the entering streams over a year, levelized."""

    def test_it_is_the_levelized_price_times_the_exergy_over_the_year(self):
        ean = _heatpump_analysis()
        eco = EconomicAnalysis.from_json(os.path.join(HEATPUMP, "hp_costs_detailed.json"))
        expected = (
            sum(
                eco.compute_c()[f"{name}_c"] * 1e-9 * (ean.connections[name].get("E") or 0.0) * 3600
                for name in eco.fuel_costs
            )
            * eco.tau
        )
        assert eco.levelized_fuel_costs(ean) == pytest.approx(expected)
        assert eco.levelized_fuel_costs(ean) > 0

    def test_it_enters_the_total_revenue_requirement(self):
        ean = _heatpump_analysis()
        eco = EconomicAnalysis.from_json(os.path.join(HEATPUMP, "hp_costs_detailed.json"))
        assert eco.total_revenue_requirement(ean) == pytest.approx(
            eco.levelized_carrying_charges() + eco.levelized_om_costs() + eco.levelized_fuel_costs(ean)
        )

    def test_without_the_exergy_analysis_there_is_no_fuel_cost(self):
        """The exergy of the entering streams is unknown, so the sum is left out."""
        eco = EconomicAnalysis.from_json(os.path.join(HEATPUMP, "hp_costs_detailed.json"))
        assert eco.levelized_fuel_costs() == 0.0
        assert eco.total_revenue_requirement() == pytest.approx(
            eco.levelized_carrying_charges() + eco.levelized_om_costs()
        )

    def test_a_plant_whose_streams_are_all_free(self):
        eco = EconomicAnalysis(
            PEC={"C": 1000.0},
            i_eff=0.1,
            n=20,
            tau=8000,
            f_tci=4.0,
            omc_share=0.02,
            fuel_costs={"e1": 0.0, "11": 0.0, "21": 0.0},
        )
        assert eco.levelized_fuel_costs(_heatpump_analysis()) == pytest.approx(0.0)
