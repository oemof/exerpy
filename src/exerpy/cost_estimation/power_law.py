"""
Power-law cost estimation module.

Provides equipment cost estimation using power-law scaling correlations
for heat pump components (compressors, motors, plate heat exchangers).
Costs are adjusted via cost-index (CI) ratios from
a reference year to a target year, and an installation factor converts
PEC to TCI.

The correlations are fluid-dependent: different refrigerants map to
different cost-type categories with their own reference cost, reference
size, and scaling exponent.

References
----------
.. [1] T. Ommen, W.B. Jensen, B. Elmegaard, "Technical and economic working
   domains of industrial heat pumps: Part 1 - Single stage vapour compression
   heat pumps," International Journal of Refrigeration, vol. 55, pp. 168-182,
   2015. doi:10.1016/j.ijrefrig.2015.02.012
   (compressor, motor, plate heat exchanger correlations)
"""

import logging

import numpy as np
from tabulate import tabulate

from ..components.helpers.cycle_closer import CycleCloser
from ..components.helpers.power_bus import PowerBus

logger = logging.getLogger("exerpy.cost_estimation.power_law")


# ============================================================================
# Cost correlation data
# ============================================================================

# Cost index ratios (reference year -> target year)
# Format: {reference_year: {target_year: ratio}}
# Default ratios provided for common reference years -> 2024.
_DEFAULT_CI_RATIOS = {
    2013: {2025: 1.4743},
    2020: {2025: 1.4030},
}

# Refrigerant -> cost-type mapping
_FLUID_COST_TYPE = {
    "R290": "R290_R600a",
    "R600a": "R290_R600a",
    "R1270": "R290_R600a",
    "R600": "R290_R600a",
    "R717": "R717_LP",
}

# --- Compressor: sized by suction volumetric flow rate [m^3/h] ---
# (PEC_W [EUR], X_W [m^3/h], alpha)  — Ref. [1]
_COMP_COST = {
    "R290_R600a": (19_850, 279.8, 0.73),
    "R717_LP": (11_914, 178.4, 0.66),
}

# --- Electrical motor: sized by shaft power [kW] ---
# For R290/R600a/R1270/R600 motor cost = 0 (included in compressor)  — Ref. [1]
_MOTOR_COST = {
    "R290_R600a": (0, 0, 0),
    "R717_LP": (10_710, 250, 0.65),
}

# --- Plate heat exchanger: sized by area [m^2] ---  — Ref. [1]
_PHX_COST = {
    "R290_R600a": (15_526, 42, 0.8),
    "R717_LP": (15_526, 42, 0.8),
}


# ============================================================================
# PEC helper functions
# ============================================================================


def _pec_compressor(V_dot_m3h, fluid):
    """PEC of a compressor (reference-year EUR), sized by suction volumetric flow [m^3/h]."""
    cost_type = _FLUID_COST_TYPE[fluid]
    PEC_W, X_W, alpha = _COMP_COST[cost_type]
    return PEC_W * (V_dot_m3h / X_W) ** alpha


def _pec_motor(W_kW, fluid):
    """PEC of an electrical motor (reference-year EUR), sized by shaft power [kW].

    Returns 0 for fluid types whose motor cost is included in the compressor.
    """
    cost_type = _FLUID_COST_TYPE[fluid]
    PEC_W, X_W, alpha = _MOTOR_COST[cost_type]
    if PEC_W == 0:
        return 0.0
    return PEC_W * (W_kW / X_W) ** alpha


def _pec_plate_hx(A_m2, fluid):
    """PEC of a plate heat exchanger (reference-year EUR), sized by area [m^2]."""
    cost_type = _FLUID_COST_TYPE[fluid]
    PEC_W, X_W, alpha = _PHX_COST[cost_type]
    return PEC_W * (A_m2 / X_W) ** alpha


# ============================================================================
# Main estimator class
# ============================================================================


class DefaultCostEstimator:
    """
    Cost estimator using power-law scaling correlations for heat pump components.

    Supports compressors, motors, and plate heat exchangers
    with fluid-dependent cost-type categories. Costs are adjusted from a
    reference year to the target year via cost-index ratios, and an installation
    factor converts PEC to TCI.

    Parameters
    ----------
    exergoeconomic_analysis : ExergoeconomicAnalysis
        Instance of ExergoeconomicAnalysis to estimate costs for.

    Attributes
    ----------
    execo : ExergoeconomicAnalysis
        Reference to the exergoeconomic analysis instance.
    connections : dict
        Dictionary of all energy/material connections in the system.
    components : dict
        Dictionary of all components in the system.
    currency : str
        Currency symbol used in cost reporting.
    """

    def __init__(self, exergoeconomic_analysis):
        self.execo = exergoeconomic_analysis
        self.connections = exergoeconomic_analysis.connections
        self.components = exergoeconomic_analysis.components
        self.currency = exergoeconomic_analysis.currency

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def estimate_costs(
        self,
        operating_hours=7500,
        equipment_lifetime=20,
        interest_rate=0.10,
        escalation_rate=0.02,
        maintenance_factor=0.03,
        installation_factor=6.32,
        ci_ratios=None,
        cost_ref_year=2013,
        custom_U_values=None,
        custom_sizes=None,
        custom_mappings=None,
    ):
        """
        Estimate purchased equipment costs for all components in the system.

        Uses power-law scaling correlations with cost-index adjustment and
        installation factor. Annualization is performed using capital recovery
        factor (CRF) and cost escalation levelization factor (CELF).

        Parameters
        ----------
        operating_hours : float, optional
            Annual full-load operating hours (default: 7500).
        equipment_lifetime : int, optional
            Equipment lifetime in years (default: 20).
        interest_rate : float, optional
            Effective interest rate for capital recovery (default: 0.10).
        escalation_rate : float, optional
            Nominal cost escalation rate for O&M (default: 0.02).
        maintenance_factor : float, optional
            Annual maintenance cost as fraction of TCI (default: 0.03).
        installation_factor : float, optional
            TCI = installation_factor * PEC (default: 6.32).
        ci_ratios : dict, optional
            Cost-index ratios ``{ref_year: ratio_to_target}``. If ``None``,
            built-in ratios to year 2024 are used.
        cost_ref_year : int, optional
            Reference year for compressor/motor/PHX correlations (default: 2013).
        custom_U_values : dict, optional
            Heat transfer coefficients ``{component_name: U}`` in W/(m^2 K)
            for heat exchanger area estimation.
        custom_sizes : dict, optional
            Override size parameters ``{component_name: size_value}``.
        custom_mappings : dict, optional
            Override equipment type for specific components.
            Format: ``{component_name: "compressor"|"motor"|"plate_hx"}``.

        Returns
        -------
        dict
            ``{component_name_Z: cost_in_currency_per_hour, ...}``
        """
        from ..analyses import EconomicAnalysis

        ci_ratios = ci_ratios if ci_ratios is not None else _DEFAULT_CI_RATIOS
        custom_U_values = custom_U_values or {}
        custom_sizes = custom_sizes or {}
        custom_mappings = custom_mappings or {}

        self._custom_U_values = custom_U_values
        self._hx_using_default_U = []

        # --- Compute PEC for each component (ref-year cost) ---
        pec_ref = {}  # {comp_name: (pec_in_ref_year, ref_year)}
        cost_details = {}

        for comp_name, component in self.components.items():
            if isinstance(component, CycleCloser | PowerBus):
                continue

            comp_class = component.__class__.__name__

            # Determine equipment type
            if comp_name in custom_mappings:
                eq_type = custom_mappings[comp_name]
            else:
                eq_type = self._detect_equipment_type(comp_class)

            # Components with no cost correlation
            if eq_type is None:
                pec_ref[comp_name] = (0.0, cost_ref_year)
                cost_details[comp_name] = {
                    "equipment_type": "N/A",
                    "size": 0,
                    "size_unit": "-",
                    "fluid": "-",
                    "PEC_ref": 0,
                    "TCI": 0,
                    "Z_hourly": 0,
                }
                continue

            # Get sizing parameter
            size = custom_sizes[comp_name] if comp_name in custom_sizes else self._get_size(component, eq_type)

            fluid = self._detect_fluid(component)

            # Calculate PEC
            pec, ref_year, size_unit = self._calculate_pec(eq_type, size, fluid)

            pec_ref[comp_name] = (pec, ref_year)
            cost_details[comp_name] = {
                "equipment_type": eq_type,
                "size": size if size is not None else 0,
                "size_unit": size_unit,
                "fluid": fluid or "-",
                "PEC_ref": pec,
                "TCI": 0,  # filled below
                "Z_hourly": 0,  # filled below
            }

        # --- Apply CI adjustment and installation factor ---
        comp_names = []
        pec_list = []
        for comp_name, (pec, ref_year) in pec_ref.items():
            ci = self._get_ci_ratio(ci_ratios, ref_year)
            tci = installation_factor * pec * ci
            comp_names.append(comp_name)
            pec_list.append(tci)
            if comp_name in cost_details:
                cost_details[comp_name]["TCI"] = tci

        # --- Annualize via EconomicAnalysis ---
        econ = EconomicAnalysis(
            {
                "tau": operating_hours,
                "i_eff": interest_rate,
                "n": equipment_lifetime,
                "r_n": escalation_rate,
            }
        )
        omc_relative = [maintenance_factor] * len(pec_list)
        _, _, Z_total = econ.compute_component_costs(pec_list, omc_relative)

        # --- Build result dict ---
        estimated_costs = {}
        for name, z in zip(comp_names, Z_total, strict=False):
            estimated_costs[f"{name}_Z"] = z
            if name in cost_details:
                cost_details[name]["Z_hourly"] = z

        self._estimated_cost_details = cost_details

        # Warn about default U values
        if self._hx_using_default_U:
            logger.warning(
                "The following heat exchangers use DEFAULT U values for area estimation. "
                "Provide custom_U_values for accurate sizing:"
            )
            for cname, default_U in self._hx_using_default_U:
                logger.warning(f"  - {cname}: U = {default_U} W/(m2-K)")

        return estimated_costs

    def print_estimated_costs(self):
        """Print a summary table of estimated component costs."""
        if not hasattr(self, "_estimated_cost_details") or not self._estimated_cost_details:
            print("No estimated costs available. Run estimate_costs() first.")
            return

        headers = [
            "Component",
            "Type",
            "Size",
            "Unit",
            "Fluid",
            f"PEC [{self.currency}]",
            f"TCI [{self.currency}]",
            f"Z [{self.currency}/h]",
        ]
        rows = []
        for comp_name, d in self._estimated_cost_details.items():
            rows.append(
                [
                    comp_name,
                    d["equipment_type"],
                    f"{d['size']:.2f}" if d["size"] else "-",
                    d["size_unit"],
                    d["fluid"],
                    f"{d['PEC_ref']:,.0f}",
                    f"{d['TCI']:,.0f}",
                    f"{d['Z_hourly']:.4f}",
                ]
            )

        print("\n" + "=" * 110)
        print("ESTIMATED COMPONENT COSTS (Default Correlations)")
        print("=" * 110)
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print()

    # ------------------------------------------------------------------
    # Equipment type detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_equipment_type(comp_class):
        """Map an ExerPy component class name to an equipment type string.

        Returns
        -------
        str or None
            One of ``"compressor"``, ``"motor"``, ``"plate_hx"``,
            or ``None`` for components with no cost correlation.
        """
        _map = {
            "Compressor": "compressor",
            "Motor": "motor",
            "Generator": "motor",
            "HeatExchanger": "plate_hx",
            "SectionedHeatExchanger": "plate_hx",
            "Condenser": "plate_hx",
            "SteamGenerator": "plate_hx",
            "SimpleHeatExchanger": "plate_hx",
            "DissipativeHeatExchanger": "plate_hx",
        }
        return _map.get(comp_class)

    # ------------------------------------------------------------------
    # Fluid detection
    # ------------------------------------------------------------------

    def _detect_fluid(self, component):
        """Detect the dominant refrigerant flowing through a component.

        Inspects inlet connections and returns the fluid with the highest
        mass fraction that is listed in ``_FLUID_COST_TYPE``.

        Returns
        -------
        str or None
            Refrigerant name (e.g. ``"R290"``), or ``None`` if no known
            refrigerant is found.
        """
        if not hasattr(component, "inl"):
            return None

        for idx in component.inl:
            inlet = component.inl[idx]
            composition = inlet.get("mass_composition", {})
            if not composition:
                continue
            # Find the dominant fluid
            dominant = max(composition, key=composition.get)
            if dominant in _FLUID_COST_TYPE:
                return dominant
            # Also check all fluids, not just dominant
            for fluid_name in composition:
                if fluid_name in _FLUID_COST_TYPE:
                    return fluid_name
        return None

    # ------------------------------------------------------------------
    # Size extraction
    # ------------------------------------------------------------------

    def _get_size(self, component, eq_type):
        """Extract the sizing parameter for a component.

        Returns
        -------
        float or None
        """
        if eq_type == "compressor":
            return self._get_compressor_vdot(component)
        elif eq_type == "motor":
            return self._get_power_kW(component)
        elif eq_type == "plate_hx":
            return self._get_hx_area(component)
        return None

    def _get_compressor_vdot(self, component):
        """Suction volumetric flow rate [m^3/h] from the compressor inlet.

        The parsers store the volumetric flow ``v`` [m^3/s] on the inlet
        connection (tespy's ``v`` property is a volumetric flow, not the
        specific volume): ``V_dot = v * 3600``.
        """
        if not hasattr(component, "inl"):
            return None
        for idx in component.inl:
            v = component.inl[idx].get("v")
            if v is not None and v > 0:
                return v * 3600  # m^3/s * 3600 s/h = m^3/h
        return None

    def _get_power_kW(self, component):
        """Shaft power [kW] from component exergy fuel (E_F)."""
        if hasattr(component, "E_F") and component.E_F is not None:
            return abs(component.E_F) / 1000  # W -> kW
        return None

    def _get_hx_area(self, component):
        """Heat exchanger area [m^2] estimated as Q / (U * LMTD)."""
        Q_kW = self._calculate_heat_duty(component)
        if Q_kW is None or Q_kW <= 0:
            return None
        U = self._get_U_value(component)
        LMTD = self._estimate_LMTD(component)
        if U > 0 and LMTD > 0:
            return (Q_kW * 1000) / (U * LMTD)  # m^2
        return None

    # ------------------------------------------------------------------

    def _calculate_heat_duty(self, component):
        """Heat duty [kW] from connection enthalpies."""
        try:
            if hasattr(component, "inl") and hasattr(component, "outl"):
                inl = component.inl
                outl = component.outl
                # Try hot side (index 0)
                if 0 in inl and 0 in outl:
                    m = inl[0].get("m", 0)
                    h_in = inl[0].get("h", 0)
                    h_out = outl[0].get("h", 0)
                    Q_kW = abs(m * (h_in - h_out)) / 1000
                    if Q_kW > 0:
                        return Q_kW
                # Try cold side (index 1)
                if 1 in inl and 1 in outl:
                    m = inl[1].get("m", 0)
                    h_in = inl[1].get("h", 0)
                    h_out = outl[1].get("h", 0)
                    Q_kW = abs(m * (h_out - h_in)) / 1000
                    if Q_kW > 0:
                        return Q_kW
        except Exception as e:
            logger.debug(f"Could not calculate heat duty for {component.name}: {e}")
        return None

    def _estimate_LMTD(self, component):
        """Estimate counter-current LMTD [K]."""
        try:
            if hasattr(component, "inl") and hasattr(component, "outl"):
                inl = component.inl
                outl = component.outl
                if 0 in inl and 0 in outl and 1 in inl and 1 in outl:
                    T_hot_in = inl[0].get("T", 0)
                    T_hot_out = outl[0].get("T", 0)
                    T_cold_in = inl[1].get("T", 0)
                    T_cold_out = outl[1].get("T", 0)
                    dT1 = T_hot_in - T_cold_out
                    dT2 = T_hot_out - T_cold_in
                    if dT1 > 0 and dT2 > 0 and abs(dT1 - dT2) > 0.01:
                        return max((dT1 - dT2) / np.log(dT1 / dT2), 1.0)
                    elif dT1 > 0 and dT2 > 0:
                        return (dT1 + dT2) / 2
        except Exception:
            pass
        return 10.0

    def _get_U_value(self, component):
        """Overall heat transfer coefficient [W/(m^2 K)]."""
        if component.name in self._custom_U_values:
            return self._custom_U_values[component.name]
        # Defaults by component class
        comp_class = component.__class__.__name__
        defaults = {
            "Condenser": 3696,
            "SteamGenerator": 1483,
            "SimpleHeatExchanger": 1494,
        }
        default_U = defaults.get(comp_class, 1483)
        self._hx_using_default_U.append((component.name, default_U))
        return default_U

    # ------------------------------------------------------------------
    # PEC calculation dispatch
    # ------------------------------------------------------------------

    def _calculate_pec(self, eq_type, size, fluid):
        """Calculate PEC and return (pec, ref_year, size_unit).

        Returns
        -------
        tuple
            ``(pec_value, reference_year, size_unit_string)``
        """
        if size is None or size <= 0:
            return 0.0, 2013, "-"

        if eq_type == "compressor":
            if fluid and fluid in _FLUID_COST_TYPE:
                return _pec_compressor(size, fluid), 2013, "m3/h"
            logger.warning(f"Unknown fluid '{fluid}' for compressor cost — using 0")
            return 0.0, 2013, "m3/h"

        if eq_type == "motor":
            if fluid and fluid in _FLUID_COST_TYPE:
                return _pec_motor(size, fluid), 2013, "kW"
            return 0.0, 2013, "kW"

        if eq_type == "plate_hx":
            if fluid and fluid in _FLUID_COST_TYPE:
                return _pec_plate_hx(size, fluid), 2013, "m2"
            # Fallback: use R290_R600a row (same as R717_LP for PHX)
            return _pec_plate_hx(size, "R290"), 2013, "m2"

        return 0.0, 2013, "-"

    # ------------------------------------------------------------------
    # CI ratio lookup
    # ------------------------------------------------------------------

    @staticmethod
    def _get_ci_ratio(ci_ratios, ref_year):
        """Look up the CI ratio for a reference year.

        If the exact year is found in ``ci_ratios``, the first available
        target-year ratio is returned. Falls back to 1.0 if not found.
        """
        if ref_year in ci_ratios:
            entry = ci_ratios[ref_year]
            if isinstance(entry, dict):
                # Return the first (or only) target year ratio
                return next(iter(entry.values()))
            # Allow simple {ref_year: ratio} format
            return entry
        logger.warning(f"No CI ratio for reference year {ref_year} — using 1.0")
        return 1.0
