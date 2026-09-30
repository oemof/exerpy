"""
Unit and integration tests for the ExergoeconomicAnalysis class.

This file contains tests that verify the exergoeconomic analysis workflow,
including cost variable initialization, cost assignment, matrix construction,
solving, results generation, and evaluation.
"""

import logging
import os
import re

import numpy as np
import pandas as pd
import pytest

from exerpy.analyses import ExergoeconomicAnalysis
from exerpy.analyses import ExergyAnalysis
from exerpy.components.component import Component
from exerpy.components.component import component_registry
from exerpy.components.helpers.cycle_closer import CycleCloser

# =============================================================================
# Mock Components with Exergoeconomic Methods
# =============================================================================


@component_registry
class MockExergoTurbine(Component):
    """Mock turbine for exergoeconomic testing (Case 1: both T > T0)."""

    def calc_exergy_balance(self, T0, p0, split_physical_exergy=True):
        # Sum power from outlet power connections
        total_power = sum(conn.get("energy_flow", 0) for conn in self.outl.values() if conn.get("kind") == "power")
        self.P = total_power
        self.E_P = self.P
        # E_F = PH_in - PH_out (material streams only)
        mat_outl_ePH = sum(o["m"] * o["e_PH"] for o in self.outl.values() if o.get("kind") == "material")
        self.E_F = self.inl[0]["m"] * self.inl[0]["e_PH"] - mat_outl_ePH
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        """F-principle: c_T_in = c_T_out, c_M_in = c_M_out."""
        inlet = self.inl[0]
        outlet = self.outl[0]
        # Only material outlets
        material_outlets = [o for o in self.outl.values() if o.get("kind") == "material"]
        for outlet in material_outlets:
            # Thermal: 1/E_T_in * C_T_in - 1/E_T_out * C_T_out = 0
            A[counter, inlet["CostVar_index"]["T"]] = 1 / inlet["E_T"] if inlet["e_T"] != 0 else 1
            A[counter, outlet["CostVar_index"]["T"]] = -1 / outlet["E_T"] if outlet["e_T"] != 0 else -1
            equations[counter] = {"kind": "aux_f_rule", "objects": [self.name], "property": "c_T"}
            b[counter] = 0

            # Mechanical: 1/E_M_in * C_M_in - 1/E_M_out * C_M_out = 0
            A[counter + 1, inlet["CostVar_index"]["M"]] = 1 / inlet["E_M"] if inlet["e_M"] != 0 else 1
            A[counter + 1, outlet["CostVar_index"]["M"]] = -1 / outlet["E_M"] if outlet["e_M"] != 0 else -1
            equations[counter + 1] = {"kind": "aux_f_rule", "objects": [self.name], "property": "c_M"}
            b[counter + 1] = 0
            counter += 2
        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        """Case 1: T_in, T_out >= T0. Product = power, Fuel = PH_in - PH_out."""
        C_power_out = sum(s.get("C_TOT", 0) for s in self.outl.values() if s.get("kind") == "power")
        material_outlets = [o for o in self.outl.values() if o.get("kind") == "material"]
        sum_C_PH_out = sum(o.get("C_PH", 0) for o in material_outlets)

        self.C_P = C_power_out
        self.C_F = self.inl[0].get("C_PH", 0) - sum_C_PH_out
        self.c_F = self.C_F / self.E_F if self.E_F != 0 else 0
        self.c_P = self.C_P / self.E_P if self.E_P != 0 else 0
        self.C_D = self.c_F * self.E_D
        self.r = (self.C_P - self.C_F) / self.C_F if self.C_F != 0 else 0
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) != 0 else 0


@component_registry
class MockExergoCompressor(Component):
    """Mock compressor for exergoeconomic testing (Case 1: both T > T0)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.Z_costs = kwargs.get("Z_costs", 0.0)

    def calc_exergy_balance(self, T0, p0, split_physical_exergy=True):
        # Power input
        power_conn = None
        for conn in self.inl.values():
            if conn.get("kind") == "power":
                power_conn = conn
                break
        self.P = power_conn["energy_flow"] if power_conn else 0
        self.E_F = abs(self.P)
        self.E_P = self.outl[0]["m"] * (self.outl[0]["e_PH"] - self.inl[0]["e_PH"])
        self.E_D = self.E_F - self.E_P
        self.epsilon = self.calc_epsilon()

    def aux_eqs(self, A, b, counter, T0, equations, chemical_exergy_enabled, split_physical_exergy=True):
        """P-principle for Case 1: (c_T_out - c_T_in)/dET = (c_M_out - c_M_in)/dEM."""
        inlet = self.inl[0]
        outlet = self.outl[0]
        dET = outlet["E_T"] - inlet["E_T"]
        dEM = outlet["E_M"] - inlet["E_M"]
        if dET != 0 and dEM != 0:
            A[counter, inlet["CostVar_index"]["T"]] = -1 / dET
            A[counter, outlet["CostVar_index"]["T"]] = 1 / dET
            A[counter, inlet["CostVar_index"]["M"]] = 1 / dEM
            A[counter, outlet["CostVar_index"]["M"]] = -1 / dEM
            equations[counter] = {"kind": "aux_p_rule", "objects": [self.name], "property": "c_T, c_M"}
        b[counter] = 0
        counter += 1
        return A, b, counter, equations

    def exergoeconomic_balance(self, T0, chemical_exergy_enabled=False, split_physical_exergy=True):
        """Case 1: T_in, T_out >= T0. Product = PH_out - PH_in, Fuel = power."""
        power_cost = 0
        for stream in self.inl.values():
            if stream.get("kind") == "power":
                power_cost = stream.get("C_TOT", 0)
                break
        self.C_P = self.outl[0].get("C_PH", 0) - self.inl[0].get("C_PH", 0)
        self.C_F = power_cost
        self.c_F = self.C_F / self.E_F if self.E_F != 0 else 0
        self.c_P = self.C_P / self.E_P if self.E_P != 0 else 0
        self.C_D = self.c_F * self.E_D
        self.r = (self.C_P - self.C_F) / self.C_F if self.C_F != 0 else 0
        self.f = self.Z_costs / (self.Z_costs + self.C_D) if (self.Z_costs + self.C_D) != 0 else 0


# =============================================================================
# Fixtures
# =============================================================================

# System layout:
#   [ambient air] --conn "1"--> [Compressor C1] --conn "2"--> [Turbine T1] --conn "3"--> [exhaust]
#   [power in]    --conn "P_in"--> [Compressor C1]
#   [Turbine T1]  --conn "P_out"--> [power out]


@pytest.fixture
def mock_exergoecon_component_data():
    """Component data for exergoeconomic testing."""
    return {
        "MockExergoCompressor": {"C1": {"name": "C1", "type": "MockExergoCompressor", "type_index": 24, "eta_s": 0.85}},
        "MockExergoTurbine": {"T1": {"name": "T1", "type": "MockExergoTurbine", "type_index": 23, "eta_s": 0.9}},
    }


@pytest.fixture
def mock_exergoecon_connection_data():
    """Connection data with e_T, e_M, E_T, E_M fields for exergoeconomic analysis."""
    return {
        "1": {
            "kind": "material",
            "source_component": None,
            "source_connector": None,
            "target_component": "C1",
            "target_connector": 0,
            "T": 298.15,
            "p": 101325,
            "m": 100.0,
            "h": 300000,
            "s": 6800,
            "e_PH": 0.0,
            "e_T": 0.0,
            "e_M": 0.0,
            "E_PH": 0.0,
            "E_T": 0.0,
            "E_M": 0.0,
            "E": 0.0,
            "mass_composition": {"N2": 0.79, "O2": 0.21},
        },
        "2": {
            "kind": "material",
            "source_component": "C1",
            "source_connector": 0,
            "target_component": "T1",
            "target_connector": 0,
            "T": 600.0,
            "p": 1013250,
            "m": 100.0,
            "h": 610000,
            "s": 7100,
            "e_PH": 300.0,
            "e_T": 100.0,
            "e_M": 200.0,
            "E_PH": 30000.0,
            "E_T": 10000.0,
            "E_M": 20000.0,
            "E": 30000.0,
            "mass_composition": {"N2": 0.79, "O2": 0.21},
        },
        "3": {
            "kind": "material",
            "source_component": "T1",
            "source_connector": 0,
            "target_component": None,
            "target_connector": None,
            "T": 400.0,
            "p": 101325,
            "m": 100.0,
            "h": 400000,
            "s": 7200,
            "e_PH": 50.0,
            "e_T": 30.0,
            "e_M": 20.0,
            "E_PH": 5000.0,
            "E_T": 3000.0,
            "E_M": 2000.0,
            "E": 5000.0,
            "mass_composition": {"N2": 0.79, "O2": 0.21},
        },
        "P_in": {
            "kind": "power",
            "source_component": None,
            "source_connector": None,
            "target_component": "C1",
            "target_connector": 1,
            "energy_flow": 31000.0,
            "E": 31000.0,
        },
        "P_out": {
            "kind": "power",
            "source_component": "T1",
            "source_connector": 1,
            "target_component": None,
            "target_connector": None,
            "energy_flow": 21000.0,
            "E": 21000.0,
        },
    }


@pytest.fixture
def analyzed_exergy(mock_exergoecon_component_data, mock_exergoecon_connection_data):
    """Pre-analyzed ExergyAnalysis instance with split_physical_exergy=True."""
    ea = ExergyAnalysis(
        mock_exergoecon_component_data,
        mock_exergoecon_connection_data,
        298.15,
        101325,
        split_physical_exergy=True,
    )
    fuel = {"inputs": ["1", "P_in"], "outputs": []}
    product = {"inputs": ["P_out", "3"], "outputs": []}
    ea.analyse(fuel, product)
    return ea


@pytest.fixture
def exergoecon(analyzed_exergy):
    """ExergoeconomicAnalysis instance ready for testing."""
    return ExergoeconomicAnalysis(analyzed_exergy)


@pytest.fixture
def valid_costs():
    """Cost dictionary with all required Z and c values."""
    return {
        "C1_Z": 80.0,  # currency/h
        "T1_Z": 100.0,  # currency/h
        "1_c": 0.0,  # currency/GJ (free ambient air)
        "P_in_c": 5.0,  # currency/GJ (external power input cost)
    }


# =============================================================================
# Group A: __init__() Tests
# =============================================================================


class TestInit:
    def test_init_without_split_physical_exergy(self, mock_exergoecon_component_data, mock_exergoecon_connection_data):
        """A material stream carries a single physical cost variable when the split is off."""
        ea = ExergyAnalysis(
            mock_exergoecon_component_data,
            mock_exergoecon_connection_data,
            298.15,
            101325,
            split_physical_exergy=False,
        )
        ea.analyse({"inputs": ["1", "P_in"]}, {"inputs": ["P_out", "3"]})
        eco = ExergoeconomicAnalysis(ea)
        assert eco.split_physical_exergy is False
        assert eco.cost_labels == ("PH",)

    def test_init_succeeds_with_split_true(self, exergoecon, analyzed_exergy):
        """Attributes correctly set from ExergyAnalysis."""
        assert exergoecon.connections is analyzed_exergy.connections
        assert exergoecon.components is analyzed_exergy.components
        assert exergoecon.Tamb == 298.15
        assert exergoecon.pamb == 101325
        assert exergoecon.E_F_dict is analyzed_exergy.E_F_dict
        assert exergoecon.E_P_dict is analyzed_exergy.E_P_dict

    def test_init_default_currency_eur(self, exergoecon):
        """Default currency is EUR."""
        assert exergoecon.currency == "EUR"

    def test_init_custom_currency(self, analyzed_exergy):
        """Custom currency stored."""
        eco = ExergoeconomicAnalysis(analyzed_exergy, currency="USD")
        assert eco.currency == "USD"

    def test_init_empty_state(self, exergoecon):
        """Initial state has zero variables and empty dicts."""
        assert exergoecon.num_variables == 0
        assert exergoecon.variables == {}
        assert exergoecon.equations == {}


# =============================================================================
# Group B: initialize_cost_variables() Tests
# =============================================================================


class TestInitializeCostVariables:
    def test_initialize_material_stream_indices(self, exergoecon):
        """Material streams get T and M indices (2 per stream without chem exergy)."""
        exergoecon.initialize_cost_variables()
        for name, conn in exergoecon.connections.items():
            if conn.get("kind") == "material" and "CostVar_index" in conn:
                assert "T" in conn["CostVar_index"]
                assert "M" in conn["CostVar_index"]

    def test_initialize_power_connection_index(self, exergoecon):
        """Power connections get 1 'exergy' index."""
        exergoecon.initialize_cost_variables()
        for name, conn in exergoecon.connections.items():
            if conn.get("kind") == "power" and "CostVar_index" in conn:
                assert "exergy" in conn["CostVar_index"]
                assert len(conn["CostVar_index"]) == 1

    def test_initialize_total_variable_count(self, exergoecon):
        """num_variables matches expected count: 3 material * 2 + 2 power * 1 = 8."""
        exergoecon.initialize_cost_variables()
        assert exergoecon.num_variables == 8

    def test_initialize_variables_dict(self, exergoecon):
        """Variables dict maps indices to correct names."""
        exergoecon.initialize_cost_variables()
        var_names = list(exergoecon.variables.values())
        # Check that variable names follow the pattern C_{name}_T, C_{name}_M, C_{name}_TOT
        assert any("_T" in v for v in var_names)
        assert any("_M" in v for v in var_names)
        assert any("_TOT" in v for v in var_names)

    def test_initialize_with_chemical_exergy(self, mock_exergoecon_component_data, mock_exergoecon_connection_data):
        """With chemical exergy, material streams get 3 indices (T, M, CH)."""
        # Add e_CH to material connections
        for name, conn in mock_exergoecon_connection_data.items():
            if conn.get("kind") == "material":
                conn["e_CH"] = 50.0
                conn["E_CH"] = conn["m"] * conn["e_CH"]
        ea = ExergyAnalysis(
            mock_exergoecon_component_data,
            mock_exergoecon_connection_data,
            298.15,
            101325,
            chemExLib="Ahrendts",
            split_physical_exergy=True,
        )
        ea.analyse({"inputs": ["1", "P_in"]}, {"inputs": ["P_out", "3"]})
        eco = ExergoeconomicAnalysis(ea)
        eco.initialize_cost_variables()
        # 3 material streams * 3 (T, M, CH) + 2 power * 1 = 11
        assert eco.num_variables == 11
        for name, conn in eco.connections.items():
            if conn.get("kind") == "material" and "CostVar_index" in conn:
                assert "CH" in conn["CostVar_index"]


# =============================================================================
# Group C: assign_user_costs() Tests
# =============================================================================


class TestAssignUserCosts:
    def test_assign_component_z_costs_conversion(self, exergoecon, valid_costs):
        """Z cost converted from currency/h to currency/s (÷3600)."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        comp_c1 = exergoecon.components["C1"]
        assert comp_c1.Z_costs == pytest.approx(80.0 / 3600)

    def test_assign_missing_component_cost_raises(self, exergoecon):
        """ValueError for missing component Z cost."""
        exergoecon.initialize_cost_variables()
        incomplete_costs = {"1_c": 0.0}  # Missing C1_Z and T1_Z
        with pytest.raises(ValueError, match="mandatory but not provided"):
            exergoecon.assign_user_costs(incomplete_costs)

    def test_assign_input_material_cost(self, exergoecon, valid_costs):
        """c_TOT, C_TOT, c_T, C_T, c_M, C_M correctly computed."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        conn1 = exergoecon.connections["1"]
        # 1_c = 0.0, so all costs should be 0
        assert conn1["c_TOT"] == pytest.approx(0.0)
        assert conn1["C_TOT"] == pytest.approx(0.0)

    def test_assign_missing_input_cost_raises(self, exergoecon):
        """ValueError for missing input connection cost."""
        exergoecon.initialize_cost_variables()
        costs_no_conn = {"C1_Z": 80.0, "T1_Z": 100.0}  # Missing 1_c
        with pytest.raises(ValueError, match="mandatory but not provided"):
            exergoecon.assign_user_costs(costs_no_conn)

    def test_assign_power_input_no_cost_required(self, exergoecon):
        """Power input without cost doesn't raise (but system may be underdetermined)."""
        exergoecon.initialize_cost_variables()
        # Costs without P_in_c — code doesn't raise for missing power input costs
        costs_no_power = {"C1_Z": 80.0, "T1_Z": 100.0, "1_c": 0.0}
        exergoecon.assign_user_costs(costs_no_power)  # Should not raise

    def test_assign_zero_cost_input(self, exergoecon, valid_costs):
        """Zero cost (free ambient air) works correctly."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        conn1 = exergoecon.connections["1"]
        assert conn1["c_TOT"] == 0.0
        assert conn1["C_TOT"] == 0.0
        assert conn1.get("c_T", 0) == 0.0
        assert conn1.get("c_M", 0) == 0.0

    def test_assign_nonzero_input_cost(self, exergoecon):
        """Non-zero input cost distributes correctly."""
        exergoecon.initialize_cost_variables()
        costs = {"C1_Z": 80.0, "T1_Z": 100.0, "1_c": 10.0, "P_in_c": 5.0}  # 10 currency/GJ
        exergoecon.assign_user_costs(costs)
        conn1 = exergoecon.connections["1"]
        expected_c_TOT = 10.0 * 1e-9
        assert conn1["c_TOT"] == pytest.approx(expected_c_TOT)
        assert conn1["C_TOT"] == pytest.approx(expected_c_TOT * conn1["E"])


# =============================================================================
# Group D: construct_matrix() Tests
# =============================================================================


class TestConstructMatrix:
    def test_matrix_dimensions(self, exergoecon, valid_costs):
        """A is (num_variables × num_variables), b has length num_variables."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        n = exergoecon.num_variables
        assert exergoecon._A.shape == (n, n)
        assert exergoecon._b.shape == (n,)

    def test_cost_balance_rows(self, exergoecon, valid_costs):
        """Cost balance rows: inlet +1, outlet -1, b = -Z_costs."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        # Find the compressor's cost balance row
        comp_c1 = exergoecon.components["C1"]
        row = comp_c1.exergy_cost_line
        # b should be -Z_costs
        assert exergoecon._b[row] == pytest.approx(-comp_c1.Z_costs)

    def test_boundary_equations(self, exergoecon, valid_costs):
        """Input streams generate boundary condition equations."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        # Check that boundary equations exist in equations dict
        boundary_eqs = [eq for eq in exergoecon.equations.values() if eq.get("kind") == "boundary"]
        assert len(boundary_eqs) > 0

    def test_aux_equations_called(self, exergoecon, valid_costs):
        """Equation counter advances and equations dict populated with aux rules."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        aux_eqs = [eq for eq in exergoecon.equations.values() if "aux" in eq.get("kind", "")]
        assert len(aux_eqs) > 0

    def test_equations_dict_populated(self, exergoecon, valid_costs):
        """All rows have entries in self.equations."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        # Every row index from 0..num_variables-1 should be in equations
        for i in range(exergoecon.num_variables):
            assert i in exergoecon.equations, f"Row {i} missing from equations dict"


# =============================================================================
# Group E: solve_exergoeconomic_analysis() Tests
# =============================================================================


class TestSolve:
    def test_solve_assigns_material_costs(self, exergoecon, valid_costs):
        """C_T, c_T, C_M, c_M, C_TOT, c_TOT set on material connections."""
        exergoecon.run(valid_costs)
        for name, conn in exergoecon.connections.items():
            if conn.get("kind") == "material":
                source = conn.get("source_component")
                target = conn.get("target_component")
                if source in exergoecon.components or target in exergoecon.components:
                    assert "C_T" in conn, f"C_T missing for connection {name}"
                    assert "c_T" in conn, f"c_T missing for connection {name}"
                    assert "C_M" in conn, f"C_M missing for connection {name}"
                    assert "c_M" in conn, f"c_M missing for connection {name}"
                    assert "C_TOT" in conn, f"C_TOT missing for connection {name}"
                    assert "c_TOT" in conn, f"c_TOT missing for connection {name}"

    def test_solve_assigns_power_costs(self, exergoecon, valid_costs):
        """C_TOT, c_TOT set on power connections."""
        exergoecon.run(valid_costs)
        for name, conn in exergoecon.connections.items():
            if conn.get("kind") == "power":
                source = conn.get("source_component")
                target = conn.get("target_component")
                if source in exergoecon.components or target in exergoecon.components:
                    assert "C_TOT" in conn, f"C_TOT missing for power {name}"
                    assert "c_TOT" in conn, f"c_TOT missing for power {name}"

    def test_solve_calls_exergoeconomic_balance(self, exergoecon, valid_costs):
        """Components have C_F, C_P, C_D, r, f after solve."""
        exergoecon.run(valid_costs)
        for comp in exergoecon.components.values():
            assert hasattr(comp, "C_F"), f"C_F missing on {comp.name}"
            assert hasattr(comp, "C_P"), f"C_P missing on {comp.name}"
            assert hasattr(comp, "C_D"), f"C_D missing on {comp.name}"
            assert hasattr(comp, "r"), f"r missing on {comp.name}"
            assert hasattr(comp, "f"), f"f missing on {comp.name}"

    def test_solve_system_costs(self, exergoecon, valid_costs):
        """system_costs dict has C_F, C_P, Z in currency/h."""
        exergoecon.run(valid_costs)
        assert "C_F" in exergoecon.system_costs
        assert "C_P" in exergoecon.system_costs
        assert "Z" in exergoecon.system_costs
        # Z should match sum of all Z costs converted to currency/h
        expected_Z = valid_costs["C1_Z"] + valid_costs["T1_Z"]
        assert exergoecon.system_costs["Z"] == pytest.approx(expected_Z, rel=1e-6)

    def test_solve_cost_balance_cp_eq_cf_plus_z(self, exergoecon, valid_costs):
        """System-level: C_P ≈ C_F + Z."""
        exergoecon.run(valid_costs)
        sc = exergoecon.system_costs
        assert sc["C_P"] == pytest.approx(sc["C_F"] + sc["Z"], abs=1e-3)

    def test_solve_zero_exergy_no_division_error(self, mock_exergoecon_component_data, mock_exergoecon_connection_data):
        """Connections with E=0 don't crash."""
        # Connection "1" already has E=0 (ambient air with zero exergy)
        ea = ExergyAnalysis(
            mock_exergoecon_component_data,
            mock_exergoecon_connection_data,
            298.15,
            101325,
            split_physical_exergy=True,
        )
        ea.analyse({"inputs": ["1", "P_in"], "outputs": []}, {"inputs": ["P_out", "3"], "outputs": []})
        eco = ExergoeconomicAnalysis(ea)
        costs = {"C1_Z": 80.0, "T1_Z": 100.0, "1_c": 0.0, "P_in_c": 5.0}
        eco.run(costs)  # Should not raise

    def test_solve_loss_cost_distribution(self, mock_exergoecon_component_data, mock_exergoecon_connection_data):
        """Loss stream C_TOT distributed to product streams."""
        ea = ExergyAnalysis(
            mock_exergoecon_component_data,
            mock_exergoecon_connection_data,
            298.15,
            101325,
            split_physical_exergy=True,
        )
        fuel = {"inputs": ["1", "P_in"], "outputs": []}
        product = {"inputs": ["P_out"], "outputs": []}
        loss = {"inputs": ["3"], "outputs": []}
        ea.analyse(fuel, product, loss)
        eco = ExergoeconomicAnalysis(ea)
        costs = {"C1_Z": 80.0, "T1_Z": 100.0, "1_c": 0.0, "P_in_c": 5.0}
        eco.run(costs)
        # After loss distribution, P_out should have received the loss cost share
        assert eco.system_costs["C_P"] == pytest.approx(eco.system_costs["C_F"] + eco.system_costs["Z"], abs=1e-3)


# =============================================================================
# Group F: run() Tests
# =============================================================================


class TestRun:
    def test_run_full_workflow(self, exergoecon, valid_costs):
        """system_costs populated after run."""
        exergoecon.run(valid_costs)
        assert hasattr(exergoecon, "system_costs")
        assert exergoecon.system_costs["C_F"] > 0 or exergoecon.system_costs["Z"] > 0

    def test_run_with_allow_singular(self, exergoecon, valid_costs):
        """Flag passed through correctly (no error for well-formed system)."""
        exergoecon.run(valid_costs, allow_singular=True)
        assert hasattr(exergoecon, "system_costs")

    def test_run_missing_costs_raises(self, exergoecon):
        """Missing costs raise ValueError."""
        with pytest.raises(ValueError):
            exergoecon.run({})


# =============================================================================
# Group G: check_cost_balance() Tests
# =============================================================================


class TestCheckCostBalance:
    def test_check_cost_balance_all_satisfied(self, exergoecon, valid_costs):
        """All components balanced after successful solve."""
        exergoecon.run(valid_costs)
        balances = exergoecon.check_cost_balance()
        for name, (residual, is_balanced) in balances.items():
            assert is_balanced, f"Component {name} not balanced: residual={residual}"

    def test_check_cost_balance_custom_tolerance(self, exergoecon, valid_costs):
        """Custom tol parameter works."""
        exergoecon.run(valid_costs)
        balances = exergoecon.check_cost_balance(tol=1e-3)
        for name, (residual, is_balanced) in balances.items():
            assert is_balanced

    def test_check_cost_balance_skips_cyclecloser(self, exergoecon, valid_costs):
        """CycleCloser excluded from checks."""
        exergoecon.run(valid_costs)
        balances = exergoecon.check_cost_balance()
        # No CycleCloser in our system, but verify pattern works
        for name in balances:
            comp = exergoecon.components.get(name)
            assert not isinstance(comp, CycleCloser)


# =============================================================================
# Group H: exergoeconomic_results() Tests
# =============================================================================


class TestExergoeconomicResults:
    def test_returns_four_dataframes(self, exergoecon, valid_costs):
        """Returns tuple of 4 DataFrames."""
        exergoecon.run(valid_costs)
        result = exergoecon.exergoeconomic_results(print_results=False)
        assert len(result) == 4
        for df in result:
            assert isinstance(df, pd.DataFrame)

    def test_component_columns(self, exergoecon, valid_costs):
        """Correct column names including currency."""
        exergoecon.run(valid_costs)
        df_comp, _, _, _ = exergoecon.exergoeconomic_results(print_results=False)
        expected_cols = [
            "C_F [EUR/h]",
            "C_P [EUR/h]",
            "C_D [EUR/h]",
            "Z [EUR/h]",
            "C_D+Z [EUR/h]",
            "f [%]",
            "r [%]",
            "c_F [EUR/GJ]",
            "c_P [EUR/GJ]",
        ]
        for col in expected_cols:
            assert col in df_comp.columns, f"Column '{col}' missing from component results"

    def test_tot_row_present(self, exergoecon, valid_costs):
        """TOT row exists with system totals."""
        exergoecon.run(valid_costs)
        df_comp, _, _, _ = exergoecon.exergoeconomic_results(print_results=False)
        tot_rows = df_comp[df_comp["Component"] == "TOT"]
        assert len(tot_rows) == 1

    def test_material_cost_columns(self, exergoecon, valid_costs):
        """Material connections table has cost columns."""
        exergoecon.run(valid_costs)
        _, _, df_mat2, _ = exergoecon.exergoeconomic_results(print_results=False)
        expected = ["C^T [EUR/h]", "C^M [EUR/h]", "C^TOT [EUR/h]", "c^T [EUR/GJ_ex]", "c^M [EUR/GJ_ex]"]
        for col in expected:
            assert col in df_mat2.columns, f"Column '{col}' missing from material cost results"

    def test_non_material_columns(self, exergoecon, valid_costs):
        """Non-material table has C^TOT, c^TOT."""
        exergoecon.run(valid_costs)
        _, _, _, df_non_mat = exergoecon.exergoeconomic_results(print_results=False)
        assert "C^TOT [EUR/h]" in df_non_mat.columns
        assert "c^TOT [EUR/GJ_ex]" in df_non_mat.columns

    def test_custom_currency_in_headers(self, analyzed_exergy, valid_costs):
        """Currency appears in column headers."""
        eco = ExergoeconomicAnalysis(analyzed_exergy, currency="USD")
        eco.run(valid_costs)
        df_comp, _, _, _ = eco.exergoeconomic_results(print_results=False)
        assert "C_F [USD/h]" in df_comp.columns

    def test_print_false_no_output(self, exergoecon, valid_costs, capsys):
        """print_results=False produces no stdout."""
        exergoecon.run(valid_costs)
        exergoecon.exergoeconomic_results(print_results=False)
        captured = capsys.readouterr()
        assert captured.out == ""


# =============================================================================
# Group I: evaluate_results() Tests
# =============================================================================


class TestEvaluateResults:
    def test_evaluate_default_sort_cd_plus_z(self, exergoecon, valid_costs):
        """Returns DataFrame sorted by C_D+Z descending."""
        exergoecon.run(valid_costs)
        df = exergoecon.evaluate_results()
        vals = df["C_D+Z [EUR/h]"].values
        assert all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))

    def test_evaluate_sort_by_all_options(self, exergoecon, valid_costs):
        """All 5 sort options work."""
        exergoecon.run(valid_costs)
        for sort_by in ["C_D+Z", "C_D", "Z", "r", "f"]:
            df = exergoecon.evaluate_results(sort_by=sort_by)
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0

    def test_evaluate_invalid_sort_raises(self, exergoecon, valid_costs):
        """Invalid sort_by raises ValueError."""
        exergoecon.run(valid_costs)
        with pytest.raises(ValueError, match="Invalid sort_by"):
            exergoecon.evaluate_results(sort_by="invalid")

    def test_evaluate_top_n_limits_output(self, exergoecon, valid_costs, capsys):
        """top_n limits printed rows."""
        exergoecon.run(valid_costs)
        exergoecon.evaluate_results(top_n=1)
        captured = capsys.readouterr()
        assert "Top 1" in captured.out

    def test_evaluate_excludes_tot_row(self, exergoecon, valid_costs):
        """TOT row not in returned DataFrame."""
        exergoecon.run(valid_costs)
        df = exergoecon.evaluate_results()
        assert "TOT" not in df["Component"].values


# =============================================================================
# Group J: detect_linear_dependencies() Tests
# =============================================================================


class TestDetectLinearDependencies:
    def test_full_rank_system(self, exergoecon, valid_costs):
        """Well-formed system: zero_rows/columns empty, rank = num_variables."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        deps = exergoecon.detect_linear_dependencies()
        assert deps["zero_rows"] == []
        assert deps["zero_columns"] == []
        assert deps["matrix_rank"] == exergoecon.num_variables

    def test_detect_zero_row(self, exergoecon, valid_costs):
        """Manually zeroed row detected."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        # Zero out a row
        exergoecon._A[0, :] = 0
        deps = exergoecon.detect_linear_dependencies()
        assert 0 in deps["zero_rows"]

    def test_print_dependency_report_runs(self, exergoecon, valid_costs, capsys):
        """No crash, produces output."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        exergoecon.print_dependency_report()
        captured = capsys.readouterr()
        assert len(captured.out) > 0


# =============================================================================
# Group K: print_equations() and print_variables() Tests
# =============================================================================


class TestPrintHelpers:
    def test_print_equations_returns_dict(self, exergoecon, valid_costs):
        """Returns dict with sorted keys."""
        exergoecon.initialize_cost_variables()
        exergoecon.assign_user_costs(valid_costs)
        exergoecon.construct_matrix()
        eqs = exergoecon.print_equations()
        assert isinstance(eqs, dict)
        keys = list(eqs.keys())
        assert keys == sorted(keys)

    def test_print_variables_returns_dict(self, exergoecon, valid_costs):
        """Returns dict with integer keys mapping to variable names."""
        exergoecon.initialize_cost_variables()
        vars_dict = exergoecon.print_variables()
        assert isinstance(vars_dict, dict)
        for k, v in vars_dict.items():
            assert isinstance(k, int)
            assert isinstance(v, str)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    @pytest.fixture
    def json_example_path(self):
        """Path to the JSON example with pre-defined Z costs."""
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../examples/exergoeconomic_analysis/cgam/cgam.json")
        )

    @pytest.fixture
    def json_example_costs(self):
        """Pre-defined costs from cgam_exergoeconomic.py."""
        return {
            "AC_Z": 49.874,
            "CC_Z": 4.508,
            "EXP_Z": 49.911,
            "APH_Z": 11.899,
            "EV_Z": 11.843,
            "PH_Z": 5.629,
            "GEN_Z": 0.0,
            "1_c": 0.0,
            "10_c": 3.8635,
            "8_c": 0.0,
        }

    def test_json_example_exergoeconomic_full_workflow(self, json_example_path, json_example_costs):
        """Full workflow: load, analyse, run exergoeconomic, verify results."""
        ean = ExergyAnalysis.from_json(json_example_path)
        fuel = {"inputs": ["10", "1", "8"], "outputs": []}
        product = {"inputs": ["E1", "9"], "outputs": []}
        loss = {"inputs": ["7"], "outputs": []}
        ean.analyse(E_F=fuel, E_P=product, E_L=loss)

        eco = ExergoeconomicAnalysis(ean)
        eco.run(json_example_costs)

        # Verify system costs populated
        assert "C_F" in eco.system_costs
        assert "C_P" in eco.system_costs
        assert "Z" in eco.system_costs

        # Cost balance satisfied
        sc = eco.system_costs
        assert sc["C_P"] == pytest.approx(sc["C_F"] + sc["Z"], abs=0.1)

        # 4 DataFrames returned
        result = eco.exergoeconomic_results(print_results=False)
        assert len(result) == 4

        # Component cost balances (use relaxed tolerance for real-world numerical precision)
        balances = eco.check_cost_balance(tol=0.05)
        for name, (residual, is_balanced) in balances.items():
            assert is_balanced, f"Component {name} not balanced: residual={residual}"

    def test_json_example_numerical_values_positive(self, json_example_path, json_example_costs):
        """All C_F, C_P, Z values > 0 and finite."""
        ean = ExergyAnalysis.from_json(json_example_path)
        fuel = {"inputs": ["10", "1", "8"], "outputs": []}
        product = {"inputs": ["E1", "9"], "outputs": []}
        loss = {"inputs": ["7"], "outputs": []}
        ean.analyse(E_F=fuel, E_P=product, E_L=loss)

        eco = ExergoeconomicAnalysis(ean)
        eco.run(json_example_costs)

        sc = eco.system_costs
        assert sc["C_F"] > 0
        assert sc["C_P"] > 0
        assert sc["Z"] > 0
        assert np.isfinite(sc["C_F"])
        assert np.isfinite(sc["C_P"])
        assert np.isfinite(sc["Z"])

    def test_json_example_evaluate_results(self, json_example_path, json_example_costs):
        """evaluate_results() returns valid sorted DataFrame."""
        ean = ExergyAnalysis.from_json(json_example_path)
        fuel = {"inputs": ["10", "1", "8"], "outputs": []}
        product = {"inputs": ["E1", "9"], "outputs": []}
        loss = {"inputs": ["7"], "outputs": []}
        ean.analyse(E_F=fuel, E_P=product, E_L=loss)

        eco = ExergoeconomicAnalysis(ean)
        eco.run(json_example_costs)

        df = eco.evaluate_results(top_n=3, sort_by="C_D+Z")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "TOT" not in df["Component"].values
        # Values should be finite
        for val in df["C_D+Z [EUR/h]"].values:
            assert np.isfinite(val)


# =============================================================================
# Solar thermal plants
# =============================================================================

SOLAR_TOWER_COSTS = {
    "SF_Z": 1500.0,
    "ST_Z": 400.0,
    "SH_Z": 40.0,
    "EV_Z": 60.0,
    "ECO_Z": 30.0,
    "HPST_Z": 120.0,
    "IPST_Z": 90.0,
    "LPST_Z": 80.0,
    "COND_Z": 25.0,
    "AFTCOOL_Z": 4.0,
    "FWPH_Z": 10.0,
    "DEA_Z": 5.0,
    "THR_Z": 0.0,
    "PUMP_COND_Z": 2.0,
    "PUMP_FW_Z": 15.0,
    "PUMP_SF_Z": 5.0,
    "MOT_PUMP_COND_Z": 1.0,
    "MOT_PUMP_FW_Z": 3.0,
    "MOT_PUMP_SF_Z": 2.0,
    "GEN_Z": 50.0,
    "SF_Q_c": 0.0,
    "C1_c": 0.0,
}

PARABOLIC_COSTS = {
    "PARAB_Z": 2000.0,
    "PUMP_SF_Z": 5.0,
    "SH_Z": 40.0,
    "EV_Z": 60.0,
    "ECO_Z": 30.0,
    "HPST_Z": 120.0,
    "IPST_Z": 90.0,
    "LPST_Z": 80.0,
    "COND_Z": 25.0,
    "PUMP_COND_Z": 2.0,
    "DEA_Z": 5.0,
    "PUMP_FW_Z": 15.0,
    "AFTCOOL_Z": 4.0,
    "FWPH_Z": 10.0,
    "THR_Z": 0.0,
    "GEN_Z": 50.0,
    "MOT_PUMP_COND_Z": 1.0,
    "MOT_PUMP_FW_Z": 3.0,
    "MOT_PUMP_SF_Z": 2.0,
    "PARAB_Q_c": 0.0,
    "C1_c": 0.0,
}

SOLAR_PLANTS = {
    "solar_tower_ebs": ("SF", SOLAR_TOWER_COSTS, ("SF", "ST")),
    "parabolic_tespy": ("PARAB", PARABOLIC_COSTS, ("PARAB",)),
}


def _run_solar_with(name, costs):
    """Exergoeconomic analysis of one of the solar thermal example plants with the given costs."""
    fuel_stream = SOLAR_PLANTS.get(name, ("PARAB",))[0]
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), f"../examples/exergy_analysis/solar_thermal/{name}.json")
    )
    ean = ExergyAnalysis.from_json(path, split_physical_exergy=False)
    ean.analyse(
        E_F={"inputs": [fuel_stream], "outputs": []},
        E_P={"inputs": ["ETOT"], "outputs": []},
        E_L={"inputs": ["C2"], "outputs": ["C1"]},
    )
    eco = ExergoeconomicAnalysis(ean, currency="EUR")
    eco.run(costs)
    return eco


def _run_solar(name):
    """Exergoeconomic analysis of one of the solar thermal example plants."""
    return _run_solar_with(name, SOLAR_PLANTS[name][1])


class TestSolarThermalExergoeconomics:
    """The solar components close the cost matrix of a whole plant."""

    @pytest.mark.parametrize("name", SOLAR_PLANTS)
    def test_system_cost_balance_closes(self, name):
        eco = _run_solar(name)
        sc = eco.system_costs
        assert sc["C_P"] == pytest.approx(sc["C_F"] + sc["Z"], rel=1e-6)

    @pytest.mark.parametrize("name", SOLAR_PLANTS)
    def test_component_cost_balances_close(self, name):
        eco = _run_solar(name)
        for comp, (residual, balanced) in eco.check_cost_balance(tol=0.05).items():
            assert balanced, f"{comp} not balanced: residual={residual}"

    @pytest.mark.parametrize("name", SOLAR_PLANTS)
    def test_free_radiation_is_priced_into_the_product(self, name):
        """The radiation is free, so the whole product cost comes from the investment."""
        eco = _run_solar(name)
        _, costs, solar_components = SOLAR_PLANTS[name]
        assert eco.system_costs["C_F"] == pytest.approx(0.0, abs=1e-9)
        assert eco.system_costs["C_P"] == pytest.approx(sum(v for k, v in costs.items() if k.endswith("_Z")), rel=1e-9)
        for name_ in solar_components:
            comp = eco.components[name_]
            assert comp.C_P > 0 and np.isfinite(comp.C_P)
            assert np.isfinite(comp.f)

    @pytest.mark.parametrize("name", SOLAR_PLANTS)
    def test_results_are_produced(self, name):
        eco = _run_solar(name)
        assert len(eco.exergoeconomic_results(print_results=False)) == 4


# =============================================================================
# Storage
# =============================================================================


def _storage_streams(m_in, m_out):
    """Connection data of a storage with the given mass flows, in and out."""

    def stream(source, target, m, e_T, e_M):
        return {
            "kind": "material",
            "source_component": source,
            "source_connector": None if source is None else 0,
            "target_component": target,
            "target_connector": None if target is None else 0,
            "T": 500.0,
            "p": 1013250,
            "m": m,
            "e_T": e_T,
            "e_M": e_M,
            "e_PH": e_T + e_M,
            "E_T": m * e_T,
            "E_M": m * e_M,
            "E_PH": m * (e_T + e_M),
            "E": m * (e_T + e_M),
        }

    return {
        "1": stream(None, "ST", m_in, 150.0, 50.0),
        "2": stream("ST", None, m_out, 140.0, 40.0),
    }


def _run_storage(m_in, m_out, split_physical_exergy=True, Z=90.0):
    """Exergoeconomic analysis of a single storage between two boundaries."""
    components = {"Storage": {"ST": {"name": "ST", "type": "Storage"}}}
    ean = ExergyAnalysis(
        components,
        _storage_streams(m_in, m_out),
        298.15,
        101325,
        split_physical_exergy=split_physical_exergy,
    )
    ean.analyse(E_F={"inputs": ["1"], "outputs": []}, E_P={"inputs": ["2"], "outputs": []})
    eco = ExergoeconomicAnalysis(ean)
    eco.run({"ST_Z": Z, "1_c": 4.0})
    return eco, eco.components["ST"]


class TestStorage:
    """The stored exergy carries a cost variable of its own, so the balance closes."""

    @pytest.mark.parametrize("split", [True, False])
    @pytest.mark.parametrize(("m_in", "m_out"), [(10.0, 8.0), (8.0, 10.0), (10.0, 10.0)])
    def test_cost_balance_closes(self, m_in, m_out, split):
        eco, storage = _run_storage(m_in, m_out, split)
        residual, balanced = eco.check_cost_balance()["ST"]
        assert balanced, f"residual={residual}"

    def test_charging_produces_the_stored_exergy(self):
        eco, storage = _run_storage(10.0, 8.0)
        assert pytest.approx(storage.E_stored) == storage.E_P
        assert pytest.approx(storage.C_stored) == storage.C_P
        # The store is filled at the state of the outlet, so it is priced like it.
        outlet = eco.connections["2"]
        assert storage.C_stored / storage.E_stored == pytest.approx(outlet["C_T"] / outlet["E_T"])

    def test_discharging_is_fuelled_by_the_stored_exergy(self):
        eco, storage = _run_storage(8.0, 10.0)
        assert pytest.approx(storage.E_stored) == storage.E_F
        assert pytest.approx(storage.C_stored) == storage.C_F

    def test_holding_the_level_stores_nothing(self):
        eco, storage = _run_storage(10.0, 10.0)
        assert storage.E_stored == 0.0
        assert storage.C_stored == pytest.approx(0.0)
        assert pytest.approx(eco.connections["1"]["C_PH"]) == storage.C_F
        assert pytest.approx(eco.connections["2"]["C_PH"]) == storage.C_P

    @pytest.mark.parametrize("split", [True, False])
    def test_the_stored_exergy_gets_its_own_variable(self, split):
        eco, _ = _run_storage(10.0, 8.0, split)
        assert "stored_ST" in eco.variables.values()

    def test_indicators_are_finite(self):
        _, storage = _run_storage(10.0, 8.0)
        for name in ("c_F", "c_P", "C_D", "r", "f"):
            assert np.isfinite(getattr(storage, name)), name

    def test_aux_eqs_without_a_stored_variable_raises(self):
        _, storage = _run_storage(10.0, 8.0)
        del storage.stored_cost_index
        with pytest.raises(ValueError, match="no cost variable for its stored exergy"):
            storage.aux_eqs(np.zeros((1, 1)), np.zeros(1), 0, 298.15, {}, False, True)


# =============================================================================
# SteamGenerator
# =============================================================================

SG_Q = 1.0e8
SG_T_HOT = 1200.0


def _sg_stream(source, target, connector, m, e_T, e_M):
    return {
        "kind": "material",
        "source_component": source,
        "source_connector": connector if source else None,
        "target_component": target,
        "target_connector": connector if target else None,
        "T": 700.0,
        "p": 12000000,
        "m": m,
        "e_T": e_T,
        "e_M": e_M,
        "e_PH": e_T + e_M,
        "E_T": m * e_T,
        "E_M": m * e_M,
        "E_PH": m * (e_T + e_M),
        "E": m * (e_T + e_M),
    }


def _sg_connections(with_ip):
    conns = {
        "Q": {
            "kind": "heat",
            "source_component": None,
            "source_connector": None,
            "target_component": "SG",
            "target_connector": 3,
            "energy_flow": SG_Q,
            "E": None,
        },
        "fw": _sg_stream(None, "SG", 0, 60.0, 200000.0, 12000.0),
        "hp": _sg_stream("SG", None, 0, 58.0, 1400000.0, 10000.0),
        "drain": _sg_stream("SG", None, 2, 2.0, 900000.0, 9000.0),
    }
    if with_ip:
        conns["ip_in"] = _sg_stream(None, "SG", 1, 50.0, 700000.0, 3000.0)
        conns["ip"] = _sg_stream("SG", None, 1, 50.0, 1250000.0, 2800.0)
    return conns


def _run_steam_generator(with_ip=False, split_physical_exergy=True, T_hot=SG_T_HOT, Z=400.0):
    """Exergoeconomic analysis of a single steam generator between two boundaries."""
    components = {"SteamGenerator": {"SG": {"name": "SG", "type": "SteamGenerator", "T_hot": T_hot}}}
    ean = ExergyAnalysis(
        components,
        _sg_connections(with_ip),
        298.15,
        101325,
        split_physical_exergy=split_physical_exergy,
    )
    product = {"inputs": ["hp"] + (["ip"] if with_ip else []), "outputs": ["fw"] + (["ip_in"] if with_ip else [])}
    ean.analyse(E_F={"inputs": ["Q"], "outputs": []}, E_P=product, E_L={"inputs": ["drain"], "outputs": []})
    eco = ExergoeconomicAnalysis(ean)
    eco.run({"SG_Z": Z, "Q_c": 6.0, "fw_c": 3.0, **({"ip_in_c": 3.0} if with_ip else {})})
    return eco, eco.components["SG"]


class TestSteamGenerator:
    """The heat entering the component is its fuel, and the cost matrix closes."""

    def test_fuel_comes_from_the_heat_source_temperature(self):
        _, sg = _run_steam_generator()
        assert pytest.approx(SG_Q * (1 - 298.15 / SG_T_HOT)) == sg.E_F
        assert sg.E_D > 0

    @pytest.mark.parametrize("split", [True, False])
    def test_destruction_does_not_depend_on_the_split(self, split):
        _, with_split = _run_steam_generator(split_physical_exergy=True)
        _, without_split = _run_steam_generator(split_physical_exergy=False)
        assert pytest.approx(without_split.E_D) == with_split.E_D

    def test_without_a_heat_source_temperature_it_approximates_and_warns(self, caplog):
        with caplog.at_level(logging.WARNING):
            _, sg = _run_steam_generator(T_hot=None)
        assert "no heat source temperature T_hot" in caplog.text
        assert np.isfinite(sg.E_F)

    @pytest.mark.parametrize("split", [True, False])
    @pytest.mark.parametrize("with_ip", [False, True])
    def test_cost_balance_closes(self, with_ip, split):
        eco, _ = _run_steam_generator(with_ip, split)
        residual, balanced = eco.check_cost_balance(tol=1e-6)["SG"]
        assert balanced, f"residual={residual}"

    @pytest.mark.parametrize("with_ip", [False, True])
    def test_the_drain_is_priced_like_the_high_pressure_steam(self, with_ip):
        eco, _ = _run_steam_generator(with_ip)
        steam, drain = eco.connections["hp"], eco.connections["drain"]
        for label in ("T", "M"):
            assert drain[f"c_{label}"] == pytest.approx(steam[f"c_{label}"])

    def test_both_steam_outlets_cost_the_same(self):
        eco, _ = _run_steam_generator(with_ip=True)
        assert eco.connections["ip"]["c_T"] == pytest.approx(eco.connections["hp"]["c_T"])

    def test_the_heat_pays_for_the_product(self):
        eco, sg = _run_steam_generator()
        assert pytest.approx(eco.connections["Q"]["C_TOT"]) == sg.C_F
        assert np.isfinite(sg.c_P) and np.isfinite(sg.r) and np.isfinite(sg.f)

    def test_a_missing_drain_is_reported(self):
        conns = _sg_connections(False)
        del conns["drain"]
        ean = ExergyAnalysis(
            {"SteamGenerator": {"SG": {"name": "SG", "type": "SteamGenerator"}}}, conns, 298.15, 101325
        )
        with pytest.raises(ValueError, match="Missing outlet stream with index 2"):
            ean.analyse(E_F={"inputs": ["Q"], "outputs": []}, E_P={"inputs": ["hp"], "outputs": ["fw"]})


def test_a_component_without_a_cost_balance_rejects_an_investment_cost():
    """A power bus or a splitter carries no cost, so a cost given for it would disappear."""
    costs = dict(PARABOLIC_COSTS, SHAFT_Z=250.0)
    with pytest.raises(ValueError, match="'SHAFT' has no cost balance"):
        _run_solar_with("parabolic_tespy", costs)


# =============================================================================
# The same plant, modelled in two simulators
# =============================================================================

# The throttle sits in front of the deaerator. EBSILON lets its deaerator drop the pressure of the
# drain internally and reports 20 bar behind the throttle, while the TESPy merge equalises the
# pressures of its inlets, so the two throttles do not expand over the same pressure difference.
CROSS_SIMULATOR_EXCEPTIONS = {"THR"}


def _exergoeconomic_indicators(model):
    """The exergoeconomic results of every component of one of the parabolic trough models."""
    example = os.path.join(os.path.dirname(__file__), "../examples/exergy_analysis/solar_thermal", model)
    namespace = {}
    with open(example + ".py", encoding="utf-8") as script:
        exec(re.search(r"all_costs = \{.*?\n\}", script.read(), re.S).group(), namespace)  # noqa: S102
    eco = _run_solar_with(model, namespace["all_costs"])
    return {
        name: {key: getattr(comp, key, None) for key in ("C_F", "C_P", "C_D", "c_F", "c_P", "f", "r")}
        for name, comp in eco.components.items()
    }


def test_both_simulators_give_the_same_exergoeconomic_results():
    """The parabolic trough plant is modelled in EBSILON and in TESPy; costing it gives the same.

    This holds every part of the analysis together: the exergy of the streams, the auxiliary
    equations of every component and the scaling of the solar field, whose branches EBSILON models
    behind a header and TESPy as one collector carrying the whole flow.
    """
    ebsilon = _exergoeconomic_indicators("parabolic_ebs")
    tespy = _exergoeconomic_indicators("parabolic_tespy")

    shared = (set(ebsilon) & set(tespy)) - CROSS_SIMULATOR_EXCEPTIONS
    assert len(shared) >= 18, "the two models no longer share their components"

    for name in sorted(shared):
        for key, reference in ebsilon[name].items():
            value = tespy[name][key]
            if reference is None or not np.isfinite(reference) or reference == 0:
                continue
            assert value == pytest.approx(reference, rel=0.02), f"{name}.{key}: {value} against {reference}"


# =============================================================================
# Components that no costed example contains
# =============================================================================


def _material(source, target, connector, m, e_T, e_M, T=450.0, h=2.0e6):
    """One material stream between a component and the system boundary."""
    return {
        "kind": "material",
        "source_component": source,
        "source_connector": connector if source else None,
        "target_component": target,
        "target_connector": connector if target else None,
        "T": T,
        "p": 1000000,
        "m": m,
        "h": h,
        "e_T": e_T,
        "e_M": e_M,
        "e_PH": e_T + e_M,
        "E_T": m * e_T,
        "E_M": m * e_M,
        "E_PH": m * (e_T + e_M),
        "E": m * (e_T + e_M),
    }


def _run_single_component(component_type, connections, costs, split_physical_exergy=True, **flows):
    """Cost a plant made of one component between boundary streams."""
    name = next(iter(costs)).removesuffix("_Z")
    components = {component_type: {name: {"name": name, "type": component_type}}}
    ean = ExergyAnalysis(components, connections, 298.15, 101325, split_physical_exergy=split_physical_exergy)
    ean.analyse(**flows)
    eco = ExergoeconomicAnalysis(ean)
    eco.run(costs)
    return eco, eco.components[name]


def _flash_tank_connections():
    """A flash tank splitting a stream into a vapour and a liquid outlet."""
    return {
        "in": _material(None, "FT", 0, 10.0, 300000.0, 9000.0),
        "vap": _material("FT", None, 0, 3.0, 640000.0, 8800.0),
        "liq": _material("FT", None, 1, 7.0, 150000.0, 8800.0),
    }


class TestFlashTankExergoeconomics:
    """No costed example contains a flash tank, so it is covered here."""

    @pytest.mark.parametrize("split", [True, False])
    def test_cost_balance_closes(self, split):
        eco, _ = _run_single_component(
            "FlashTank",
            _flash_tank_connections(),
            {"FT_Z": 12.0, "in_c": 5.0},
            split,
            E_F={"inputs": ["in"], "outputs": []},
            E_P={"inputs": ["vap", "liq"], "outputs": []},
        )
        residual, balanced = eco.check_cost_balance(tol=1e-9)["FT"]
        assert balanced, f"residual={residual}"

    @pytest.mark.parametrize("split", [True, False])
    def test_fuel_and_product_are_cost_rates(self, split):
        """C_F and C_P sum the cost variables of the streams, not their specific costs."""
        eco, tank = _run_single_component(
            "FlashTank",
            _flash_tank_connections(),
            {"FT_Z": 12.0, "in_c": 5.0},
            split,
            E_F={"inputs": ["in"], "outputs": []},
            E_P={"inputs": ["vap", "liq"], "outputs": []},
        )
        labels = ["C_T", "C_M"] if split else ["C_PH"]
        assert pytest.approx(sum(eco.connections["in"][label] for label in labels)) == tank.C_F
        assert (
            pytest.approx(sum(eco.connections[name][label] for name in ("vap", "liq") for label in labels)) == tank.C_P
        )
        assert pytest.approx(tank.C_F + tank.Z_costs) == tank.C_P

    def test_both_outlets_leave_at_the_same_specific_cost(self):
        eco, _ = _run_single_component(
            "FlashTank",
            _flash_tank_connections(),
            {"FT_Z": 12.0, "in_c": 5.0},
            True,
            E_F={"inputs": ["in"], "outputs": []},
            E_P={"inputs": ["vap", "liq"], "outputs": []},
        )
        assert eco.connections["vap"]["c_T"] == pytest.approx(eco.connections["liq"]["c_T"])
        assert eco.connections["vap"]["c_M"] == pytest.approx(eco.connections["in"]["c_M"])


def _simple_heat_exchanger_connections(releasing):
    """A simple heat exchanger that either releases its heat or takes it in.

    Releasing, the heat is the product of the component and leaves it; taking it in, the heat is the
    fuel and the physical exergy the stream gains is the product.
    """
    if releasing:
        streams = {
            "in": _material(None, "SHE", 0, 10.0, 400000.0, 9000.0, T=600.0, h=3.4e6),
            "out": _material("SHE", None, 0, 10.0, 150000.0, 8500.0, T=400.0, h=3.0e6),
        }
        heat = {"source_component": "SHE", "source_connector": 999, "target_component": None, "target_connector": None}
        # The heat leaves at a lower temperature than the stream carries it, so the unit destroys exergy.
        heat["E"] = 0.8 * (streams["in"]["E_PH"] - streams["out"]["E_PH"])
    else:
        streams = {
            "in": _material(None, "SHE", 0, 10.0, 150000.0, 9000.0, T=400.0, h=3.0e6),
            "out": _material("SHE", None, 0, 10.0, 400000.0, 8500.0, T=600.0, h=3.4e6),
        }
        heat = {"source_component": None, "source_connector": None, "target_component": "SHE", "target_connector": 999}
        heat["E"] = (streams["out"]["E_PH"] - streams["in"]["E_PH"]) / 0.8
    heat.update(kind="heat", energy_flow=abs(streams["out"]["h"] - streams["in"]["h"]) * 10.0)
    streams["Q"] = heat
    return streams


class TestSimpleHeatExchangerExergoeconomics:
    """The simple heat exchanger appears in the CCPP example, which is not costed."""

    @pytest.mark.parametrize("split", [True, False])
    def test_releasing_heat_the_cost_balance_closes(self, split):
        eco, unit = _run_single_component(
            "SimpleHeatExchanger",
            _simple_heat_exchanger_connections(releasing=True),
            {"SHE_Z": 20.0, "in_c": 6.0},
            split,
            E_F={"inputs": ["in"], "outputs": ["out"]},
            E_P={"inputs": ["Q"], "outputs": []},
        )
        residual, balanced = eco.check_cost_balance(tol=1e-9)["SHE"]
        assert balanced, f"residual={residual}"
        # The heat is the product, so it carries the cost the stream gives up plus the investment.
        assert eco.connections["Q"]["C_TOT"] == pytest.approx(unit.C_F + unit.Z_costs)

    @pytest.mark.parametrize("split", [True, False])
    def test_absorbing_heat_the_cost_balance_closes(self, split):
        eco, _ = _run_single_component(
            "SimpleHeatExchanger",
            _simple_heat_exchanger_connections(releasing=False),
            {"SHE_Z": 20.0, "in_c": 6.0, "Q_c": 4.0},
            split,
            E_F={"inputs": ["Q"], "outputs": []},
            E_P={"inputs": ["out"], "outputs": ["in"]},
        )
        residual, balanced = eco.check_cost_balance(tol=1e-9)["SHE"]
        assert balanced, f"residual={residual}"

    def test_the_mechanical_exergy_passes_through_at_its_own_cost(self):
        eco, _ = _run_single_component(
            "SimpleHeatExchanger",
            _simple_heat_exchanger_connections(releasing=True),
            {"SHE_Z": 20.0, "in_c": 6.0},
            True,
            E_F={"inputs": ["in"], "outputs": ["out"]},
            E_P={"inputs": ["Q"], "outputs": []},
        )
        assert eco.connections["out"]["c_M"] == pytest.approx(eco.connections["in"]["c_M"])
        # Releasing heat above the ambient temperature, the thermal exergy follows the F-principle.
        assert eco.connections["out"]["c_T"] == pytest.approx(eco.connections["in"]["c_T"])
