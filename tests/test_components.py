"""
Unit tests for individual component classes.

This file contains tests for CombustionChamber, HeatExchanger, and other components.
The tests verify that each component computes exergy balances correctly and handles errors appropriately.
"""

import numpy as np
import pytest

from exerpy.components.combustion.base import CombustionChamber
from exerpy.components.heat_exchanger.base import HeatExchanger
from exerpy.components.heat_exchanger.condenser import Condenser
from exerpy.components.heat_exchanger.simple import SimpleHeatExchanger
from exerpy.components.helpers.cycle_closer import CycleCloser
from exerpy.components.nodes.deaerator import Deaerator
from exerpy.components.nodes.drum import Drum
from exerpy.components.nodes.mixer import Mixer
from exerpy.components.nodes.storage import Storage
from exerpy.components.nodes.flash_tank import FlashTank
from exerpy.components.piping.valve import Valve
from exerpy.components.power_machines.generator import Generator
from exerpy.components.power_machines.motor import Motor
from exerpy.components.turbomachinery.compressor import Compressor
from exerpy.components.turbomachinery.pump import Pump
from exerpy.components.turbomachinery.turbine import Turbine


@pytest.fixture
def combustion_chamber():
    """
    Create a CombustionChamber instance with a specified investment cost.
    """
    return CombustionChamber(Z_costs=1000)

@pytest.fixture
def valid_streams():
    """
    Create dummy inlet and outlet stream data for a combustion chamber.
    
    For a combustion chamber, we assume:
      - Two inlets (e.g., air and fuel)
      - One outlet (exhaust)
    
    Example values (units assumed to be consistent with the component):
      - Inlet "air": mass flow m = 5, specific physical exergy e_PH = 500, and chemical exergy e_CH = 0
      - Inlet "fuel": m = 2, e_PH = 300, e_CH = 800
      - Outlet "exhaust": m = 7, e_PH = 700, e_CH = 200
    """
    inlet_air = {"m": 5, "e_PH": 500, "e_CH": 0}
    inlet_fuel = {"m": 2, "e_PH": 300, "e_CH": 800}
    outlet_exhaust = {"m": 7, "e_PH": 700, "e_CH": 200}
    return {
        "inlets": {"air": inlet_air, "fuel": inlet_fuel},
        "outlets": {"exhaust": outlet_exhaust}
    }

def test_combustion_chamber_calc_exergy_balance_success(combustion_chamber, valid_streams):
    """
    Test that CombustionChamber.calc_exergy_balance computes correct values.
    """
    # Set the inlets and outlets.
    combustion_chamber.inl = valid_streams["inlets"]
    combustion_chamber.outl = valid_streams["outlets"]

    # Call the exergy balance calculation.
    combustion_chamber.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)
    
    # Calculate expected values:
    # Physical exergy: sum(m * e_PH)
    total_E_P_in = valid_streams["inlets"]["air"]["m"] * valid_streams["inlets"]["air"]["e_PH"] \
                  + valid_streams["inlets"]["fuel"]["m"] * valid_streams["inlets"]["fuel"]["e_PH"]
    total_E_P_out = valid_streams["outlets"]["exhaust"]["m"] * valid_streams["outlets"]["exhaust"]["e_PH"]
    expected_E_P = total_E_P_out - total_E_P_in

    # Chemical exergy: sum(m * e_CH)
    total_E_F_in = valid_streams["inlets"]["air"]["m"] * valid_streams["inlets"]["air"]["e_CH"] \
                  + valid_streams["inlets"]["fuel"]["m"] * valid_streams["inlets"]["fuel"]["e_CH"]
    total_E_F_out = valid_streams["outlets"]["exhaust"]["m"] * valid_streams["outlets"]["exhaust"]["e_CH"]
    expected_E_F = total_E_F_in - total_E_F_out

    expected_E_D = expected_E_F - expected_E_P
    expected_epsilon = expected_E_P / expected_E_F if expected_E_F != 0 else None

    # Verify calculated values.
    assert combustion_chamber.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert combustion_chamber.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert combustion_chamber.E_D == pytest.approx(expected_E_D, rel=1e-3)
    if expected_epsilon is not None:
        assert combustion_chamber.epsilon == pytest.approx(expected_epsilon, rel=1e-3)

def test_combustion_chamber_missing_streams(combustion_chamber):
    """
    Test that calc_exergy_balance raises a ValueError when required streams are missing.
    """
    # Provide only one inlet and no outlet.
    combustion_chamber.inl = {"air": {"m": 5, "e_PH": 500, "e_CH": 0}}
    combustion_chamber.outl = {}
    
    with pytest.raises(ValueError, match="CombustionChamber requires at least two inlets .*"):
        combustion_chamber.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)

@pytest.fixture
def heat_exchanger():
    """
    Create a HeatExchanger instance.
    """
    return HeatExchanger()

@pytest.fixture
def valid_heat_exchanger_streams():
    """
    Create dummy inlet and outlet stream data for a heat exchanger.
    
    For a heat exchanger, we assume:
      - Two inlets:
         * Inlet 0 (hot inlet): m = 5, e_PH = 1000, e_M = 200, T = 320 K.
         * Inlet 1 (cold inlet): m = 4, e_T = 350, e_M = 120, T = 330 K.
      - Two outlets:
         * Outlet 0 (hot outlet): m = 5, e_PH = 900, e_M = 180, T = 310 K.
         * Outlet 1 (cold outlet): m = 4, e_T = 340, e_M = 110, T = 310 K.
         
    (For simplicity, we assume that when split_physical_exergy is True, 
     the calculation uses e_T for stream 1 and e_PH for stream 0 along with mechanical terms.)
    """
    inlet_hot = {"m": 5, "e_PH": 1000, "e_M": 200, "e_T": 0, "T": 320}
    inlet_cold = {"m": 4, "e_T": 350, "e_M": 120, "T": 330, "e_PH": 0}
    outlet_hot = {"m": 5, "e_PH": 900, "e_M": 180, "e_T": 0, "T": 310}
    outlet_cold = {"m": 4, "e_T": 340, "e_M": 110, "T": 310, "e_PH": 0}
    # Use integer keys instead of strings.
    return {"inlets": {0: inlet_hot, 1: inlet_cold},
            "outlets": {0: outlet_hot, 1: outlet_cold}}

def test_heat_exchanger_calc_exergy_balance_success(heat_exchanger, valid_heat_exchanger_streams):
    """
    Test that HeatExchanger.calc_exergy_balance computes the correct exergy values
    for a valid set of streams (Case 1: all streams above ambient).
    """
    T0 = 300  # Ambient temperature
    p0 = 101325  # Ambient pressure
    heat_exchanger.inl = valid_heat_exchanger_streams["inlets"]
    heat_exchanger.outl = valid_heat_exchanger_streams["outlets"]
    
    heat_exchanger.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    # Expected calculations based on provided streams:
    # E_P = (m_outlet[1] * e_T_outlet[1]) - (m_inlet[1] * e_T_inlet[1])
    expected_E_P = (4 * 340) - (4 * 350)   # 1360 - 1400 = -40
    # E_F = (m_inlet[0] * e_PH_inlet[0] - m_outlet[0] * e_PH_outlet[0])
    #       + (m_inlet[1] * e_M_inlet[1] - m_outlet[1] * e_M_outlet[1])
    expected_E_F = (5 * 1000 - 5 * 900) + (4 * 120 - 4 * 110)  # (5000-4500)+(480-440)=500+40 = 540
    expected_E_D = expected_E_F - expected_E_P  # 540 - (-40) = 580
    expected_epsilon = expected_E_P / expected_E_F  # -40/540 ≈ -0.07407

    assert heat_exchanger.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert heat_exchanger.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert heat_exchanger.E_D == pytest.approx(expected_E_D, rel=1e-3)
    if expected_epsilon is not None:
        assert heat_exchanger.epsilon == pytest.approx(expected_epsilon, rel=1e-3)

def test_heat_exchanger_missing_streams(heat_exchanger):
    """
    Test that calc_exergy_balance raises a ValueError when the required two inlets and two outlets are missing.
    """
    # Provide only one inlet and one outlet.
    heat_exchanger.inl = {0: {"m": 5, "e_PH": 1000, "e_M": 200, "e_T": 0, "T": 320}}
    heat_exchanger.outl = {0: {"m": 5, "e_PH": 900, "e_M": 180, "e_T": 0, "T": 310}}
    
    with pytest.raises(ValueError, match="Heat exchanger requires two inlets and two outlets."):
        heat_exchanger.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)

@pytest.fixture
def condenser():
    """
    Create a Condenser instance.
    """
    return Condenser()

@pytest.fixture
def valid_condenser_streams():
    """
    Create dummy inlet and outlet stream data for a condenser.
    
    We assume:
      - Two inlets:
         * Inlet 0: m = 10, e_PH = 1500.
         * Inlet 1: m = 8, e_PH = 1000.
      - Two outlets:
         * Outlet 0: m = 10, e_PH = 1400.
         * Outlet 1: m = 8, e_PH = 900.
    
    Expected calculations:
      E_L = m_outlet[1] * (e_PH_outlet[1] - e_PH_inlet[1])
          = 8 * (900 - 1000) = 8 * (-100) = -800.
      
      E_D = m_outlet[0] * (e_PH_inlet[0] - e_PH_outlet[0]) - E_L
          = 10 * (1500 - 1400) - (-800)
          = 10 * 100 + 800 = 1000 + 800 = 1800.
    
    The condenser does not define E_F, E_P, or epsilon.
    """
    inlet0 = {"m": 10, "e_PH": 1500, "T": 320}
    inlet1 = {"m": 8, "e_PH": 1000, "T": 330}
    outlet0 = {"m": 10, "e_PH": 1400, "T": 310}
    outlet1 = {"m": 8, "e_PH": 900, "T": 310}
    return {"inlets": {0: inlet0, 1: inlet1},
            "outlets": {0: outlet0, 1: outlet1}}

def test_condenser_calc_exergy_balance_success(condenser, valid_condenser_streams):
    """
    Test that Condenser.calc_exergy_balance computes correct exergy loss and destruction.
    """
    T0 = 300  # Ambient temperature
    p0 = 101325  # Ambient pressure
    condenser.inl = valid_condenser_streams["inlets"]
    condenser.outl = valid_condenser_streams["outlets"]
    
    condenser.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    # Expected calculations:
    expected_E_L = 8 * (900 - 1000)  # -800
    expected_E_D = 10 * (1500 - 1400) - expected_E_L  # 10*100 + 800 = 1000 + 800 = 1800
    
    assert condenser.E_L == pytest.approx(expected_E_L, rel=1e-3)
    assert condenser.E_D == pytest.approx(expected_E_D, rel=1e-3)
    # For a condenser, E_F, E_P, and epsilon are undefined.
    assert condenser.E_F is None
    assert condenser.E_P is None
    assert condenser.epsilon is None

def test_condenser_missing_streams(condenser):
    """
    Test that calc_exergy_balance raises a ValueError when fewer than two inlets or outlets are provided.
    """
    T0 = 300
    p0 = 101325
    # Case 1: Only one inlet provided.
    condenser.inl = {0: {"m": 10, "e_PH": 1500, "T": 320}}
    condenser.outl = {0: {"m": 10, "e_PH": 1400, "T": 310}, 1: {"m": 8, "e_PH": 900, "T": 310}}
    with pytest.raises(ValueError, match="Condenser requires two inlets and two outlets."):
        condenser.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    # Case 2: Only one outlet provided.
    condenser.inl = {0: {"m": 10, "e_PH": 1500, "T": 320}, 1: {"m": 8, "e_PH": 1000, "T": 330}}
    condenser.outl = {0: {"m": 10, "e_PH": 1400, "T": 310}}
    with pytest.raises(ValueError, match="Condenser requires two inlets and two outlets."):
        condenser.calc_exergy_balance(T0, p0, split_physical_exergy=True)

@pytest.fixture
def simple_hex():
    """
    Create a SimpleHeatExchanger instance.
    """
    return SimpleHeatExchanger()

@pytest.fixture
def valid_simple_hex_streams():
    """
    Create dummy inlet and outlet stream data for a simple heat exchanger.

    We assume a heat release case (Q < 0) with one inlet and one outlet.

    For example:
      - Inlet: m = 5, h = 2200, T = 350 K, e_T = 400, e_PH = 500, e_M = 100.
      - Outlet: m = 5, h = 2000, T = 340 K, e_T = 380, e_PH = 480, e_M = 110.
    
    Then:
      Q = 5 * 2000 - 5 * 2200 = -1000 (W)
      With split_physical_exergy = True:
        E_P = m * (e_T_in - e_T_out) = 5 * (400 - 380) = 100 W
        E_F = m * (e_PH_in - e_PH_out) = 5 * (500 - 480) = 100 W
        E_D = E_F - E_P = 0
        Efficiency = E_P / E_F = 1.0
    """
    inlet = {"m": 5, "h": 2200, "T": 350, "e_T": 400, "e_PH": 500, "e_M": 100}
    outlet = {"m": 5, "h": 2000, "T": 340, "e_T": 380, "e_PH": 480, "e_M": 110}
    # Use integer keys, since the component expects e.g. self.inl[0]
    return {"inlets": {0: inlet},
            "outlets": {0: outlet}}

def test_simple_hex_calc_exergy_balance_success(simple_hex, valid_simple_hex_streams):
    """
    Test that SimpleHeatExchanger.calc_exergy_balance computes correct exergy values
    for a valid heat release case.
    """
    T0 = 300  # Ambient temperature
    p0 = 101325  # Ambient pressure
    simple_hex.inl = valid_simple_hex_streams["inlets"]
    simple_hex.outl = valid_simple_hex_streams["outlets"]
    
    simple_hex.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_E_P = 5 * (400 - 380)   # 5*20 = 100 W
    expected_E_F = 5 * (500 - 480)   # 5*20 = 100 W
    expected_E_D = expected_E_F - expected_E_P  # 0 W
    expected_epsilon = 1.0

    assert simple_hex.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert simple_hex.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert simple_hex.E_D == pytest.approx(expected_E_D, rel=1e-3)
    assert simple_hex.epsilon == pytest.approx(expected_epsilon, rel=1e-3)

def test_simple_hex_invalid_streams(simple_hex):
    """
    Test that calc_exergy_balance raises a ValueError when the required stream data are missing.
    """
    T0 = 300
    p0 = 101325
    # Set inlets and outlets to empty dictionaries.
    simple_hex.inl = {}
    simple_hex.outl = {}
    
    with pytest.raises(ValueError, match="SimpleHeatExchanger requires at least one inlet and one outlet"):
        simple_hex.calc_exergy_balance(T0, p0, split_physical_exergy=True)

def test_cyclecloser_calc_exergy_balance():
    """
    Test that CycleCloser.calc_exergy_balance sets exergy attributes to NaN.
    """
    cc = CycleCloser()
    cc.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)
    # Verify that the exergy-related attributes are set to NaN.
    assert np.isnan(cc.E_D)
    assert np.isnan(cc.E_F)
    assert np.isnan(cc.E_P)
    assert np.isnan(cc.E_L)
    assert np.isnan(cc.epsilon)

@pytest.fixture
def deaerator():
    """
    Create a Deaerator instance.
    """
    return Deaerator()

# --- Test Case 1: Outlet temperature greater than ambient ---
@pytest.fixture
def deaerator_streams_outlet_above():
    """
    Create dummy inlet and outlet data for a deaerator where the outlet temperature (T_out)
    is greater than the ambient temperature (T0).

    In this case, for each inlet:
      - If T_in < T_out and T_in >= T0:
          E_P contribution = m * (e_PH_out - e_PH_in)
      - If T_in < T0:
          E_P contribution = m * e_PH_out, and E_F contribution = m * e_PH_in
      - Otherwise (T_in > T_out) add to E_F: m * (e_PH_in - e_PH_out)

    For this test we choose:
      T0 = 300 K,
      Outlet: T = 320 K, e_PH = 950
      Inlet0: T = 310 K, m = 10, e_PH = 900   → T_in>=T0, T_in < T_out, so: contribution = 10*(950-900)=500
      Inlet1: T = 290 K, m = 5, e_PH = 800    → T_in < T0, so: E_P += 5*950 = 4750 and E_F += 5*800 = 4000

    Expected:
      E_P = 500 + 4750 = 5250 W,
      E_F = 4000 W,
      E_D = E_F - E_P = 4000 - 5250 = -1250 W.
    """
    inlets = {
        0: {"T": 310, "m": 10, "e_PH": 900},
        1: {"T": 290, "m": 5, "e_PH": 800}
    }
    outlets = {
        0: {"T": 320, "m": 1, "e_PH": 950}  # mass here is not used in calculation
    }
    return inlets, outlets

def test_deaerator_outlet_above(deaerator, deaerator_streams_outlet_above):
    T0 = 300
    p0 = 101325
    inl, outl = deaerator_streams_outlet_above
    deaerator.inl = inl
    deaerator.outl = outl

    deaerator.calc_exergy_balance(T0, p0, split_physical_exergy=True)

    expected_E_P = 10 * (950 - 900) + 5 * 950   # 500 + 4750 = 5250
    expected_E_F = 5 * 800                      # 4000
    expected_E_D = expected_E_F - expected_E_P   # 4000 - 5250 = -1250

    assert deaerator.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert deaerator.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert deaerator.E_D == pytest.approx(expected_E_D, rel=1e-3)

# --- Test Case 2: Outlet temperature equal to ambient ---
@pytest.fixture
def deaerator_streams_outlet_equal():
    """
    Create dummy stream data where the outlet temperature equals the ambient temperature.

    For this case, the code sets:
      - E_P = NaN
      - E_F is the sum over all inlets: m * e_PH

    Let T0 = 300 K, outlet: T = 300 K.
      Inlet0: T = 310 K, m = 10, e_PH = 900   → contribution = 10 * 900 = 9000
      Inlet1: T = 290 K, m = 5, e_PH = 800    → contribution = 5 * 800 = 4000

    Expected:
      E_F = 9000 + 4000 = 13000 W,
      E_P = NaN, and E_D = E_F (13000 W).
    """
    inlets = {
        0: {"T": 310, "m": 10, "e_PH": 900},
        1: {"T": 290, "m": 5, "e_PH": 800}
    }
    outlets = {
        0: {"T": 300, "m": 1, "e_PH": 850}  # e_PH here is irrelevant since T_out == T0
    }
    return inlets, outlets

def test_deaerator_outlet_equal(deaerator, deaerator_streams_outlet_equal):
    T0 = 300
    p0 = 101325
    inl, outl = deaerator_streams_outlet_equal
    deaerator.inl = inl
    deaerator.outl = outl

    deaerator.calc_exergy_balance(T0, p0, split_physical_exergy=True)

    expected_E_F = 10 * 900 + 5 * 800  # 9000 + 4000 = 13000
    assert np.isnan(deaerator.E_P)
    assert deaerator.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert deaerator.E_D == pytest.approx(expected_E_F, rel=1e-3)
    # Efficiency is not defined when E_P is NaN; assume calc_epsilon returns NaN.
    assert np.isnan(deaerator.epsilon)

# --- Test Case 3: Outlet temperature below ambient ---
@pytest.fixture
def deaerator_streams_outlet_below():
    """
    Create dummy stream data where the outlet temperature is below the ambient temperature.

    Let T0 = 300 K, outlet: T = 290 K, e_PH = 280.
    For each inlet:
      - If T_in > T_out:
          if T_in >= T0, then E_P += m * e_PH_out and E_F += m * e_PH_in.
          If T_in < T0, then E_P += m * (e_PH_out - e_PH_in).
    
    For this test, choose:
      Inlet0: T = 310 K, m = 10, e_PH = 900   → T_in >= T0 so: E_P += 10 * 280 = 2800, E_F += 10 * 900 = 9000.
      Inlet1: T = 290 K, m = 5, e_PH = 800    → T_in == outlet T so: falls into else: E_F += 5*(800 - 280) = 5*520 = 2600.
    
    Expected:
      E_P = 2800,
      E_F = 9000 + 2600 = 11600,
      E_D = 11600 - 2800 = 8800.
    """
    inlets = {
        0: {"T": 310, "m": 10, "e_PH": 900},
        1: {"T": 290, "m": 5, "e_PH": 800}
    }
    outlets = {
        0: {"T": 290, "m": 1, "e_PH": 280}
    }
    return inlets, outlets

def test_deaerator_outlet_below(deaerator, deaerator_streams_outlet_below):
    T0 = 300
    p0 = 101325
    inl, outl = deaerator_streams_outlet_below
    deaerator.inl = inl
    deaerator.outl = outl

    deaerator.calc_exergy_balance(T0, p0, split_physical_exergy=True)

    expected_E_P = 10 * 280   # Only inlet0 contributes: 2800
    expected_E_F = 10 * 900 + 5 * (800 - 280)  # 9000 + 2600 = 11600
    expected_E_D = expected_E_F - expected_E_P  # 11600 - 2800 = 8800

    assert deaerator.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert deaerator.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert deaerator.E_D == pytest.approx(expected_E_D, rel=1e-3)

def test_deaerator_missing_temperature():
    """Test that calc_exergy_balance raises a KeyError when temperature is missing."""
    deaerator = Deaerator()
    deaerator.inl = {0: {"m": 10, "e_PH": 900}, 1: {"m": 5, "e_PH": 800}}
    deaerator.outl = {0: {"m": 15, "e_PH": 850}}  # Missing 'T'
    
    with pytest.raises(KeyError):
        deaerator.calc_exergy_balance(300, 101325, split_physical_exergy=True)

def test_drum_calc_exergy_balance_success():
    """
    Test that Drum.calc_exergy_balance computes the correct exergy balance values
    given valid inlet and outlet stream data.
    """
    drum = Drum()
    # Define two inlets and two outlets.
    # Inlets:
    #   Inlet 0: mass = 10, e_PH = 900 (W/kg)
    #   Inlet 1: mass = 5, e_PH = 800 (W/kg)
    # Outlets:
    #   Outlet 0: mass = 1, e_PH = 1000 (W/kg)
    #   Outlet 1: mass = 2, e_PH = 1100 (W/kg)
    drum.inl = {
        0: {"m": 10, "e_PH": 900},
        1: {"m": 5, "e_PH": 800}
    }
    drum.outl = {
        0: {"m": 1, "e_PH": 1000},
        1: {"m": 2, "e_PH": 1100}
    }
    T0 = 300    # Ambient temperature (K)
    p0 = 101325 # Ambient pressure (Pa)
    drum.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    # Expected calculations:
    # E_P = (1*1000 + 2*1100) = 1000 + 2200 = 3200 W
    # E_F = (10*900 + 5*800) = 9000 + 4000 = 13000 W
    # E_D = E_F - E_P = 13000 - 3200 = 9800 W
    # Efficiency, epsilon = E_P / E_F = 3200 / 13000 ≈ 0.24615
    expected_E_P = 3200
    expected_E_F = 13000
    expected_E_D = 9800
    expected_epsilon = expected_E_P / expected_E_F

    assert drum.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert drum.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert drum.E_D == pytest.approx(expected_E_D, rel=1e-3)
    assert drum.epsilon == pytest.approx(expected_epsilon, rel=1e-3)

def test_drum_invalid_inlets():
    """
    Test that if fewer than two inlets are provided, a KeyError is raised.
    (Because the implementation expects self.inl[1] to exist.)
    """
    drum = Drum()
    # Only one inlet provided
    drum.inl = {
        0: {"m": 10, "e_PH": 900}
    }
    # Provide two outlets
    drum.outl = {
        0: {"m": 1, "e_PH": 1000},
        1: {"m": 2, "e_PH": 1100}
    }
    with pytest.raises(KeyError):
        drum.calc_exergy_balance(300, 101325, split_physical_exergy=True)

def test_drum_invalid_outlets():
    """
    Test that if fewer than two outlets are provided, a KeyError is raised.
    (Because the implementation expects self.outl[1] to exist.)
    """
    drum = Drum()
    # Provide two inlets
    drum.inl = {
        0: {"m": 10, "e_PH": 900},
        1: {"m": 5, "e_PH": 800}
    }
    # Only one outlet provided
    drum.outl = {
        0: {"m": 1, "e_PH": 1000}
    }
    with pytest.raises(KeyError):
        drum.calc_exergy_balance(300, 101325, split_physical_exergy=True)

def test_mixer_calc_exergy_balance_success():
    """
    Test that Mixer.calc_exergy_balance computes the correct exergy balance values
    given valid inlet and outlet stream data.
    
    We assume the following:
      - Two inlets:
          Inlet 0: Temperature = 310 K, mass flow = 10, e_PH = 800 [W/kg]
          Inlet 1: Temperature = 330 K, mass flow = 5,  e_PH = 850 [W/kg]
      - One outlet:
          Outlet 0: Temperature = 320 K, mass flow = 15, e_PH = 810 [W/kg]
          
    For inlets with temperature less than the outlet, the contribution is:
        m * (outlet_e_PH - inlet_e_PH)
    For inlets with temperature higher than the outlet, the contribution is added to E_F:
        m * (inlet_e_PH - outlet_e_PH)
    
    In this case:
      - Inlet 0 (310 < 320): contributes to E_P = 10*(810 - 800) = 100
      - Inlet 1 (330 > 320): contributes to E_F = 5*(850 - 810) = 200
      
    Therefore:
      - E_P = 100, E_F = 200, E_D = E_F - E_P = 100, and epsilon = 100/200 = 0.5
    """
    mixer = Mixer()
    mixer.inl = {
        0: {"T": 310, "m": 10, "e_PH": 800},
        1: {"T": 330, "m": 5,  "e_PH": 850}
    }
    mixer.outl = {
        0: {"T": 320, "m": 15, "e_PH": 810}
    }
    T0 = 300
    p0 = 101325

    mixer.calc_exergy_balance(T0, p0, split_physical_exergy=True)

    expected_E_P = 10 * (810 - 800)  # = 100
    expected_E_F = 5 * (850 - 810)   # = 200
    expected_E_D = expected_E_F - expected_E_P  # = 100
    expected_epsilon = expected_E_P / expected_E_F  # = 0.5

    assert mixer.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert mixer.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert mixer.E_D == pytest.approx(expected_E_D, rel=1e-3)
    assert mixer.epsilon == pytest.approx(expected_epsilon, rel=1e-3)


def test_mixer_invalid_streams():
    """
    Test that Mixer.calc_exergy_balance raises a ValueError when the required streams are missing.
    """
    mixer = Mixer()
    
    # Test with no inlets.
    mixer.inl = {}
    mixer.outl = {0: {"T": 320, "m": 15, "e_PH": 810}}
    with pytest.raises(ValueError, match="Mixer requires at least two inlets"):
        mixer.calc_exergy_balance(300, 101325, split_physical_exergy=True)
    
    # Test with inlets present but no outlet.
    mixer.inl = {
        0: {"T": 310, "m": 10, "e_PH": 800},
        1: {"T": 330, "m": 5,  "e_PH": 850}
    }
    mixer.outl = {}
    with pytest.raises(ValueError, match="Mixer requires at least two inlets and one outlet."):
        mixer.calc_exergy_balance(300, 101325, split_physical_exergy=True)

def test_valve_all_above_ambient():
    """
    Test Valve.exergy_balance for the case when both inlet and outlet temperatures are above ambient.
    Expected:
      - E_P is NaN.
      - E_F = m * (e_PH,in - e_PH,out).
      - E_D equals E_F.
    """
    valve = Valve()
    # Example: T0=300; inlet T=320, outlet T=330 (both above ambient)
    valve.inl = {0: {"T": 340, "m": 10, "e_PH": 1000}}
    valve.outl = {0: {"T": 330, "m": 10, "e_PH": 950}}
    T0 = 300
    p0 = 101325
    valve.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_E_F = 10 * (1000 - 950)  # 10*50 = 500
    # When both temperatures are above ambient, E_P is not defined (NaN) and E_D equals E_F.
    assert np.isnan(valve.E_P)
    assert valve.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert valve.E_D == pytest.approx(expected_E_F, rel=1e-3)


def test_valve_heat_release_split_true():
    """
    Test Valve.exergy_balance for the case where inlet is above ambient and outlet is below ambient,
    with split physical exergy enabled.
    Expected:
      - E_P = m * (outlet e_T)
      - E_F = m * (inlet e_T + inlet e_M - outlet e_M)
    """
    valve = Valve()
    # Example: T0=300; inlet T=320, outlet T=290.
    valve.inl = {0: {"T": 320, "m": 10, "e_PH": 1000, "e_T": 400, "e_M": 150}}
    valve.outl = {0: {"T": 290, "m": 10, "e_PH": 950, "e_T": 350, "e_M": 130}}
    T0 = 300
    p0 = 101325
    valve.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_E_P = 10 * 350           # = 3500
    expected_E_F = 10 * (400 + 150 - 130)  # = 10 * 420 = 4200
    expected_E_D = expected_E_F - expected_E_P  # = 4200 - 3500 = 700
    expected_epsilon = expected_E_P / expected_E_F  # ≈ 0.8333
    
    assert valve.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert valve.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert valve.E_D == pytest.approx(expected_E_D, rel=1e-3)
    assert valve.epsilon == pytest.approx(expected_epsilon, rel=1e-3)


def test_valve_both_below_ambient_split_true():
    """
    Test Valve.exergy_balance for the case when both inlet and outlet temperatures are below ambient,
    with split physical exergy enabled.
    Expected:
      - E_P = m * (outlet e_T - inlet e_T)
      - E_F = m * (inlet e_M - outlet e_M)
    """
    valve = Valve()
    # Example: T0=300; inlet T=290, outlet T=280.
    valve.inl = {0: {"T": 290, "m": 10, "e_PH": 950, "e_T": 300, "e_M": 200}}
    valve.outl = {0: {"T": 280, "m": 10, "e_PH": 930, "e_T": 280, "e_M": 180}}
    T0 = 300
    p0 = 101325
    valve.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_E_P = 10 * (280 - 300)  # = 10 * (-20) = -200
    expected_E_F = 10 * (200 - 180)   # = 10 * 20 = 200
    expected_E_D = expected_E_F - expected_E_P  # = 200 - (-200) = 400
    expected_epsilon = expected_E_P / expected_E_F  # = -200/200 = -1
    
    assert valve.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert valve.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert valve.E_D == pytest.approx(expected_E_D, rel=1e-3)
    assert valve.epsilon == pytest.approx(expected_epsilon, rel=1e-3)


def test_valve_unimplemented_case():
    """
    Test Valve.calc_exergy_balance for the unimplemented case where outlet temperature
    is higher than inlet temperature.
    
    Expected behavior:
      - Both E_P and E_F (and thus E_D) are set to NaN.
    """
    valve = Valve()
    # Set inlet temperature higher than ambient and outlet temperature even higher (T_out > T_in)
    valve.inl = {0: {"T": 310, "m": 10, "e_PH": 1000, "e_T": 500, "e_M": 150}}
    valve.outl = {0: {"T": 320, "m": 10, "e_PH": 950, "e_T": 480, "e_M": 140}}
    T0 = 300
    p0 = 101325

    valve.calc_exergy_balance(T0, p0, split_physical_exergy=True)

    assert np.isnan(valve.E_P), "E_P should be NaN when outlet temperature is greater than inlet temperature."
    # If your intended behavior is that E_F is also NaN in this case, the test expects that.
    assert np.isnan(valve.E_F), "E_F should be NaN when outlet temperature is greater than inlet temperature."
    assert np.isnan(valve.E_D), "E_D should be NaN when exergy fuel is NaN."

def test_valve_missing_streams():
    """
    Test that Valve.exergy_balance raises a ValueError when required streams are missing.
    """
    valve = Valve()
    valve.inl = {}  # Missing inlet stream
    valve.outl = {0: {"T": 290, "m": 10, "e_PH": 930, "e_T": 280, "e_M": 180}}
    T0 = 300
    p0 = 101325
    with pytest.raises(ValueError, match="Valve requires at least one inlet and one outlet."):
        valve.calc_exergy_balance(T0, p0, split_physical_exergy=True)

@pytest.fixture
def generator():
    """Create a Generator instance for testing."""
    return Generator(name="Gen1")

def test_generator_calc_exergy_balance(generator):
    """
    Test that Generator.calc_exergy_balance correctly calculates exergy balance.
    
    Expected behavior:
      - E_P is equal to the outlet energy flow.
      - E_F is equal to the inlet energy flow.
      - E_D is the difference E_F - E_P.
      - Exergetic efficiency (epsilon) is computed as E_P/E_F.
    """
    # Set up dummy inlet and outlet streams with energy flow values (in Watts)
    generator.inl = {0: {"energy_flow": 100.0}}
    generator.outl = {0: {"energy_flow": 80.0}}
    T0 = 300  # ambient temperature (not used in the calculation)
    p0 = 101325

    generator.calc_exergy_balance(T0, p0, split_physical_exergy=True)

    expected_E_P = 80.0
    expected_E_F = 100.0
    expected_E_D = expected_E_F - expected_E_P  # 20.0
    expected_efficiency = expected_E_P / expected_E_F  # 0.8

    assert generator.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert generator.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert generator.E_D == pytest.approx(expected_E_D, rel=1e-3)
    assert generator.epsilon == pytest.approx(expected_efficiency, rel=1e-3)

@pytest.fixture
def motor():
    """Return a new Motor instance."""
    return Motor()

def test_motor_calc_exergy_balance_basic(motor):
    """
    Test that Motor.calc_exergy_balance correctly computes exergy balance.
    
    Given:
      - Inlet (electrical input) energy flow = 100000 W
      - Outlet (mechanical output) energy flow = 80000 W
    
    Expect:
      - E_F = 100000 W
      - E_P = 80000 W
      - E_D = 20000 W
      - ε = 0.8
    """
    # Set up inlet and outlet streams
    motor.inl = {0: {"energy_flow": 100000}}
    motor.outl = {0: {"energy_flow": 80000}}
    
    T0 = 300
    p0 = 101325
    motor.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    assert motor.E_F == pytest.approx(100000, rel=1e-3)
    assert motor.E_P == pytest.approx(80000, rel=1e-3)
    assert motor.E_D == pytest.approx(20000, rel=1e-3)
    # Assuming calc_epsilon computes E_P/E_F when E_F != 0.
    assert motor.epsilon == pytest.approx(0.8, rel=1e-3)

def test_motor_calc_exergy_balance_zero_input(motor):
    """
    Test the behavior when both electrical input and mechanical output are zero.
    
    Expect:
      - E_F, E_P, and E_D are zero.
      - Efficiency is not defined (calc_epsilon should return NaN).
    """
    motor.inl = {0: {"energy_flow": 0}}
    motor.outl = {0: {"energy_flow": 0}}
    
    T0 = 300
    p0 = 101325
    motor.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    assert motor.E_F == 0
    assert motor.E_P == 0
    assert motor.E_D == 0
    assert np.isnan(motor.epsilon)

def test_motor_missing_inlet_raises(motor):
    """
    Test that calc_exergy_balance raises an error if the inlet stream is missing.
    """
    # No inlet stream provided.
    motor.inl = {}
    motor.outl = {0: {"energy_flow": 80000}}
    
    T0 = 300
    p0 = 101325
    with pytest.raises(KeyError):
        motor.calc_exergy_balance(T0, p0, split_physical_exergy=True)

def test_motor_missing_outlet_raises(motor):
    """
    Test that calc_exergy_balance raises an error if the outlet stream is missing.
    """
    motor.inl = {0: {"energy_flow": 100000}}
    motor.outl = {}
    
    T0 = 300
    p0 = 101325
    with pytest.raises(KeyError):
        motor.calc_exergy_balance(T0, p0, split_physical_exergy=True)

@pytest.fixture
def compressor():
    """Return a fresh Compressor instance with a name for logging."""
    return Compressor(name="TestCompressor", Z_costs=1000)

def test_compressor_case1_above_ambient(compressor):
    """
    Case 1: Both inlet and outlet temperatures are above ambient.
    Expected:
      - Power input P = m*(h_out - h_in)
      - Exergy product: E_P = m*(e_PH_out - e_PH_in)
      - Exergy fuel: E_F = |P|
    """
    m = 5
    # Dummy values:
    # Inlet: T = 310 K, h = 500, e_PH = 1000
    # Outlet: T = 320 K, h = 600, e_PH = 1100
    compressor.inl = {0: {"T": 310, "m": m, "h": 500, "e_PH": 1000}}
    compressor.outl = {0: {"T": 320, "m": m, "h": 600, "e_PH": 1100}}
    T0 = 300
    p0 = 101325

    compressor.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_P = m * (600 - 500)            # 5 * 100 = 500 W
    expected_E_P = m * (1100 - 1000)          # 5 * 100 = 500 W
    expected_E_F = abs(expected_P)           # 500 W
    expected_E_D = expected_E_F - expected_E_P  # 0 W

    assert compressor.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert compressor.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert compressor.E_D == pytest.approx(expected_E_D, rel=1e-3)
    # Efficiency = E_P / E_F when E_F != 0.
    assert compressor.epsilon == pytest.approx(expected_E_P / expected_E_F, rel=1e-3)

def test_compressor_case2_inlet_below_outlet_above(compressor):
    """
    Case 2: Inlet temperature is below ambient and outlet is above ambient.
    With split_physical_exergy=True.
    Expected (using the compressor's formulas):
      - Power input P = m*(h_out - h_in)
      - E_P = m*(e_T_out + (e_M_out - e_M_in))
      - E_F = |P| + m*e_T_in
    """
    m = 5
    # Dummy stream data:
    # Inlet: T = 290 (<T0=300), h = 450, e_T = 400, e_M = 100, e_PH not used here.
    # Outlet: T = 320 (>T0), h = 550, e_T = 500, e_M = 150, e_PH not used here.
    compressor.inl = {0: {"T": 290, "m": m, "h": 450, "e_T": 400, "e_M": 100, "e_PH": 0}}
    compressor.outl = {0: {"T": 320, "m": m, "h": 550, "e_T": 500, "e_M": 150, "e_PH": 0}}
    T0 = 300
    p0 = 101325

    compressor.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_P = m * (550 - 450)             # 5 * 100 = 500 W
    expected_E_P = m * (500 + (150 - 100))     # 5 * (500 + 50) = 5 * 550 = 2750 W
    expected_E_F = abs(expected_P) + m * 400   # 500 + 5 * 400 = 500 + 2000 = 2500 W
    expected_E_D = expected_E_F - expected_E_P  # 2500 - 2750 = -250 W

    assert compressor.E_P == pytest.approx(expected_E_P, rel=1e-3)
    assert compressor.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert compressor.E_D == pytest.approx(expected_E_D, rel=1e-3)
    assert compressor.epsilon == pytest.approx(expected_E_P / expected_E_F, rel=1e-3)

def test_compressor_case3_both_below(compressor):
    """
    Case 3: Both inlet and outlet temperatures are below or equal to ambient.
    With split_physical_exergy=True.
    Expected:
      - E_P = m*(e_M_out - e_M_in)
      - E_F = |P| + m*(e_T_in - e_T_out)
    """
    m = 5
    # Dummy stream data:
    # Inlet: T = 290, h = 450, e_T = 400, e_M = 100
    # Outlet: T = 300 (<=T0=300), h = 460, e_T = 350, e_M = 120
    compressor.inl = {0: {"T": 290, "m": m, "h": 450, "e_T": 400, "e_M": 100, "e_PH": 0}}
    compressor.outl = {0: {"T": 300, "m": m, "h": 460, "e_T": 350, "e_M": 120, "e_PH": 0}}
    T0 = 300
    p0 = 101325

    compressor.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_P = m * (120 - 100)              # 5 * 20 = 100 W
    expected_E_F = abs(m * (460-450)) + m*(400 - 350)  # |5*10| + 5*50 = 50 + 250 = 300 W
    expected_E_D = expected_E_F - expected_P  # 300 - 100 = 200 W

    assert compressor.E_P == pytest.approx(expected_P, rel=1e-3)
    assert compressor.E_F == pytest.approx(expected_E_F, rel=1e-3)
    assert compressor.E_D == pytest.approx(expected_E_D, rel=1e-3)
    assert compressor.epsilon == pytest.approx(expected_P / expected_E_F, rel=1e-3)

def test_compressor_invalid_case(compressor):
    """
    Test an invalid case for the compressor:
    When outlet temperature is smaller than inlet temperature, the case is not implemented.
    Expected: both E_P and E_F are set to NaN.
    """
    m = 5
    # Inlet T = 320, Outlet T = 310 (invalid: outlet < inlet)
    compressor.inl = {0: {"T": 320, "m": m, "h": 500, "e_PH": 1100, "e_T": 600, "e_M": 200}}
    compressor.outl = {0: {"T": 310, "m": m, "h": 480, "e_PH": 1050, "e_T": 580, "e_M": 190}}
    T0 = 300
    p0 = 101325

    compressor.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    assert np.isnan(compressor.E_P)
    assert np.isnan(compressor.E_F)

@pytest.fixture
def pump():
    """Return a new Pump instance."""
    return Pump(name="Pump1")

def test_pump_case1_above_ambient(pump):
    """
    Case 1: Both inlet and outlet temperatures are above ambient (T0).
    Expected:
      - E_P = m * (e_PH_out - e_PH_in)
      - E_F = |P|, with P = m * (h_out - h_in)
    """
    T0 = 300
    p0 = 101325
    m = 5
    # Define inlet stream: temperature above ambient
    pump.inl = {
        0: {"T": 310, "m": m, "h": 500, "e_PH": 1000, "e_T": 900, "e_M": 150}
    }
    # Define outlet stream: temperature above ambient
    pump.outl = {
        0: {"T": 320, "m": m, "h": 600, "e_PH": 1100, "e_T": 950, "e_M": 160}
    }
    # Calculate power: P = m*(h_out - h_in) = 5*(600-500) = 500 W.
    pump.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    E_P_expected = m * (1100 - 1000)  # = 5*100 = 500 W.
    E_F_expected = abs(500)  # = 500 W.
    E_D_expected = E_F_expected - E_P_expected  # 0 W.
    assert pump.E_P == pytest.approx(E_P_expected, rel=1e-3)
    assert pump.E_F == pytest.approx(E_F_expected, rel=1e-3)
    assert pump.E_D == pytest.approx(E_D_expected, rel=1e-3)

def test_pump_case2_inlet_below_outlet_above(pump):
    """
    Case 2: Inlet temperature is below ambient and outlet temperature is above ambient.
    With split physical exergy enabled:
      - E_P = m * [e_T_out + (e_M_out - e_M_in)]
      - E_F = |P| + m * e_T_in
    """
    T0 = 300
    p0 = 101325
    m = 5
    pump.inl = {
        0: {"T": 290, "m": m, "h": 500, "e_PH": 1000, "e_T": 300, "e_M": 200}
    }
    pump.outl = {
        0: {"T": 310, "m": m, "h": 600, "e_PH": 1100, "e_T": 350, "e_M": 220}
    }
    # Power: P = 5*(600-500)=500 W.
    pump.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    E_P_expected = m * (350 + (220 - 200))  # 5*(350+20)=5*370=1850 W.
    E_F_expected = abs(500) + m * 300         # 500 + 5*300 = 2000 W.
    E_D_expected = E_F_expected - E_P_expected # 2000 - 1850 = 150 W.
    assert pump.E_P == pytest.approx(E_P_expected, rel=1e-3)
    assert pump.E_F == pytest.approx(E_F_expected, rel=1e-3)
    assert pump.E_D == pytest.approx(E_D_expected, rel=1e-3)

def test_pump_case3_below_ambient(pump):
    """
    Case 3: Both inlet and outlet temperatures are below ambient.
    With split physical exergy enabled:
      - E_P = m * (e_M_out - e_M_in)
      - E_F = |P| + m * (e_T_in - e_T_out)
    """
    T0 = 300
    p0 = 101325
    m = 5
    pump.inl = {
        0: {"T": 290, "m": m, "h": 500, "e_PH": 1000, "e_T": 300, "e_M": 200}
    }
    pump.outl = {
        0: {"T": 295, "m": m, "h": 600, "e_PH": 1100, "e_T": 350, "e_M": 220}
    }
    # Power: P = 5*(600-500) = 500 W.
    pump.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    E_P_expected = m * (220 - 200)           # 5*(20)=100 W.
    E_F_expected = abs(500) + m * (300 - 350)  # 500 + 5*(-50)=500 -250=250 W.
    E_D_expected = E_F_expected - E_P_expected  # 250 - 100 = 150 W.
    assert pump.E_P == pytest.approx(E_P_expected, rel=1e-3)
    assert pump.E_F == pytest.approx(E_F_expected, rel=1e-3)
    assert pump.E_D == pytest.approx(E_D_expected, rel=1e-3)

def test_pump_invalid_case(pump):
    """
    Invalid Case: Outlet temperature is smaller than inlet temperature.
    Expected:
      - Both E_P and E_F should be set to NaN.
    """
    T0 = 300
    p0 = 101325
    m = 5
    pump.inl = {
        0: {"T": 320, "m": m, "h": 500, "e_PH": 1000, "e_T": 900, "e_M": 150}
    }
    pump.outl = {
        0: {"T": 310, "m": m, "h": 600, "e_PH": 1100, "e_T": 950, "e_M": 160}
    }
    pump.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    assert np.isnan(pump.E_P), "E_P should be NaN for invalid case."
    assert np.isnan(pump.E_F), "E_F should be NaN for invalid case."

@pytest.fixture
def turbine():
    """Return a new Turbine instance with a name for logging."""
    return Turbine(name="Turbine1")

def test_turbine_case1(turbine):
    """
    Case 1: Both inlet and outlet temperatures are above ambient.
    
    Setup:
      - Inlet: T = 310 K, m = 5, h = 400, e_PH = 1000.
      - Outlet: T = 320 K, m = 5, h = 380, e_PH = 950.
    
    Calculations:
      P = (5*380 - 5*400) = -100   → |P| = 100.
      E_P = |P| = 100.
      E_F = 5*1000 - 5*950 = 5000 - 4750 = 250.
      E_D = E_F - E_P = 250 - 100 = 150.
      Efficiency = E_P / E_F = 100 / 250 = 0.4.
    """
    T0 = 300
    p0 = 101325
    turbine.inl = {0: {"T": 320, "m": 5, "h": 400, "e_PH": 1000}}
    turbine.outl = {0: {"T": 310, "m": 5, "h": 380, "e_PH": 950}}
    
    turbine.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_P = -100
    expected_E_P = 100
    expected_E_F = 5000 - 4750  # = 250
    expected_E_D = expected_E_F - expected_E_P  # 250 - 100 = 150
    expected_epsilon = expected_E_P / expected_E_F  # 100/250 = 0.4

    assert np.isclose(turbine.P, expected_P, atol=1e-3)
    assert np.isclose(turbine.E_P, expected_E_P, atol=1e-3)
    assert np.isclose(turbine.E_F, expected_E_F, atol=1e-3)
    assert np.isclose(turbine.E_D, expected_E_D, atol=1e-3)
    assert np.isclose(turbine.epsilon, expected_epsilon, atol=1e-3)

def test_turbine_case2(turbine):
    """
    Case 2: Inlet temperature above ambient and outlet temperature at or below ambient.
    
    Setup:
      - Inlet: T = 310 K, m = 5, h = 400, e_T = 600, e_M = 150.
      - Outlet: T = 290 K, m = 5, h = 380, e_T = 580, e_M = 140.
    
    Calculations (as implemented):
      P = (5*380 - 5*400) = -100  → |P| = 100.
      E_P = |P| + 5*580 = 100 + 2900 = 3000.
      E_F = 5*600 + 5*150 - (5*140) = 3000 + 750 - 700 = 3050.
      E_D = 3050 - 3000 = 50.
      Efficiency = 3000 / 3050 ≈ 0.9836.
    """
    T0 = 300
    p0 = 101325
    m = 5
    turbine.inl = {0: {"T": 310, "m": m, "h": 400, "e_T": 600, "e_M": 150}}
    turbine.outl = {0: {"T": 290, "m": m, "h": 380, "e_T": 580, "e_M": 140}}
    
    turbine.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_P = -100
    expected_E_P = abs(expected_P) + m * 580  # 100 + 2900 = 3000
    expected_E_F = m * 600 + m * 150 - m * 140  # 3000 + 750 - 700 = 3050
    expected_E_D = expected_E_F - expected_E_P  # 3050 - 3000 = 50
    expected_epsilon = expected_E_P / expected_E_F  # 3000/3050 ≈ 0.9836

    assert np.isclose(turbine.P, expected_P, atol=1e-3)
    assert np.isclose(turbine.E_P, expected_E_P, atol=1e-3)
    assert np.isclose(turbine.E_F, expected_E_F, atol=1e-3)
    assert np.isclose(turbine.E_D, expected_E_D, atol=1e-3)
    assert np.isclose(turbine.epsilon, expected_epsilon, atol=1e-3)

def test_turbine_case3(turbine):
    """
    Case 3: Both inlet and outlet temperatures at or below ambient.
    
    Setup:
      - Inlet: T = 290 K, m = 5, h = 400, e_T = 450, e_M = 150.
      - Outlet: T = 280 K, m = 5, h = 380, e_T = 460, e_M = 140.
    
    Calculations:
      P = (5*380 - 5*400) = -100  → |P| = 100.
      E_P = |P| + [5*e_T(outlet) - 5*e_T(inlet)]
           = 100 + (5*460 - 5*450) = 100 + (2300 - 2250) = 100 + 50 = 150.
      E_F = 5*e_M(inlet) - 5*e_M(outlet) = 5*150 - 5*140 = 750 - 700 = 50.
      E_D = 50 - 150 = -100.
      Efficiency = E_P / E_F = 150 / 50 = 3.0.
      (Note: Efficiency >1 is nonphysical; this test merely verifies the implementation's formulas.)
    """
    T0 = 300
    p0 = 101325
    m = 5
    turbine.inl = {0: {"T": 290, "m": m, "h": 400, "e_T": 450, "e_M": 150}}
    turbine.outl = {0: {"T": 280, "m": m, "h": 380, "e_T": 460, "e_M": 140}}
    
    turbine.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    expected_P = -100
    expected_E_P = abs(expected_P) + (m * 460 - m * 450)  # 100 + (2300 - 2250) = 150
    expected_E_F = m * 150 - m * 140  # 750 - 700 = 50
    expected_E_D = expected_E_F - expected_E_P  # 50 - 150 = -100
    expected_epsilon = expected_E_P / expected_E_F  # 150/50 = 3.0

    assert np.isclose(turbine.P, expected_P, atol=1e-3)
    assert np.isclose(turbine.E_P, expected_E_P, atol=1e-3)
    assert np.isclose(turbine.E_F, expected_E_F, atol=1e-3)
    assert np.isclose(turbine.E_D, expected_E_D, atol=1e-3)
    assert np.isclose(turbine.epsilon, expected_epsilon, atol=1e-3)

def test_turbine_invalid_case(turbine):
    """
    Test an invalid case for the turbine:
    When outlet temperature is larger than inlet temperature, the case is not implemented.
    Expected behavior: both E_P and E_F are set to NaN.
    """
    T0 = 300
    p0 = 101325
    turbine.inl = {0: {"T": 310, "m": 5, "h": 400, "e_PH": 1000}}
    turbine.outl = {0: {"T": 320, "m": 5, "h": 380, "e_PH": 950}}
    
    turbine.calc_exergy_balance(T0, p0, split_physical_exergy=True)
    
    assert np.isnan(turbine.E_P), "E_P should be NaN for invalid case (outlet T > inlet T)."
    assert np.isnan(turbine.E_F), "E_F should be NaN for invalid case (outlet T > inlet T)."

@pytest.fixture
def storage():
    """
    Create a Storage instance with default investment cost.
    """
    return Storage(Z_costs=0.0)

@pytest.fixture
def charging_streams():
    """
    Streams for charging (outlet mass < inlet mass):
    
    - Inlet 0: m = 10, e_PH = 100
    - Outlet 0: m = 5, e_PH = 80
    
    Expected:
      E_F = 10*100 - 5*80 = 600
      E_P = (10 - 5)*80 = 400
      E_D = 600 - 400 = 200
      ε = 400/600 ≈ 0.6667
    """
    inl = {0: {"m": 10, "e_PH": 100}}
    outl = {0: {"m": 5, "e_PH": 80}}
    return inl, outl

def test_storage_charging(storage, charging_streams):
    """
    Test calc_exergy_balance for charging case.
    """
    inl, outl = charging_streams
    storage.inl = inl
    storage.outl = outl
    storage.name = "TestStorageCharging"

    storage.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)

    assert storage.E_F == pytest.approx(600, rel=1e-6)
    assert storage.E_P == pytest.approx(400, rel=1e-6)
    assert storage.E_D == pytest.approx(200, rel=1e-6)
    assert storage.epsilon == pytest.approx(400/600, rel=1e-6)

@pytest.fixture
def discharging_streams():
    """
    Streams for discharging (outlet mass > inlet mass):
    
    - Inlet 0: m = 10, e_PH = 100
    - Outlet 0: m = 15, e_PH = 80
    
    Expected:
      E_F = (15 - 10)*80 = 400
      E_P = 15*80 - 10*100 = 200
      E_D = 400 - 200 = 200
      ε = 200/400 = 0.5
    """
    inl = {0: {"m": 10, "e_PH": 100}}
    outl = {0: {"m": 15, "e_PH": 80}}
    return inl, outl

def test_storage_discharging(storage, discharging_streams):
    """
    Test calc_exergy_balance for discharging case.
    """
    inl, outl = discharging_streams
    storage.inl = inl
    storage.outl = outl
    storage.name = "TestStorageDischarging"

    storage.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)

    assert storage.E_F == pytest.approx(400, rel=1e-6)
    assert storage.E_P == pytest.approx(200, rel=1e-6)
    assert storage.E_D == pytest.approx(200, rel=1e-6)
    assert storage.epsilon == pytest.approx(0.5, rel=1e-6)

def test_storage_missing_streams_raises(storage):
    """
    Test that calc_exergy_balance raises KeyError if inlet or outlet missing.
    """
    storage.inl = {}  # no inlet 0
    storage.outl = {0: {"m": 1, "e_PH": 50}}
    with pytest.raises(KeyError):
        storage.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)

    storage.inl = {0: {"m": 1, "e_PH": 50}}
    storage.outl = {}
    with pytest.raises(KeyError):
        storage.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)

@pytest.fixture
def flash_tank():
    """
    Create a FlashTank instance.
    """
    return FlashTank()

@pytest.fixture
def valid_flash_streams():
    """
    Create dummy inlet and outlet streams for FlashTank.

    Inlets:
      0: m = 3, e_PH = 100, e_T = 50
      1: m = 2, e_PH =  80, e_T = 40
    Outlets:
      0: m = 1, e_PH =  90, e_T = 45
      1: m = 4, e_PH =  70, e_T = 35
    """
    inl = {
        0: {"m": 3, "e_PH": 100, "e_T": 50},
        1: {"m": 2, "e_PH":  80, "e_T": 40}
    }
    outl = {
        0: {"m": 1, "e_PH":  90, "e_T": 45},
        1: {"m": 4, "e_PH":  70, "e_T": 35}
    }
    return inl, outl

def test_flash_tank_calc_exergy_balance_success(flash_tank, valid_flash_streams):
    """
    Test that FlashTank.calc_exergy_balance computes correct values
    when split_physical_exergy=True.
    """
    inl, outl = valid_flash_streams
    flash_tank.inl = inl
    flash_tank.outl = outl

    flash_tank.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)

    # E_F = 3*50 + 2*40 = 230
    # E_P = 1*45 + 4*35 = 185
    expected_E_F = 230
    expected_E_P = 185
    expected_E_D = expected_E_F - expected_E_P  # 45
    expected_epsilon = expected_E_P / expected_E_F

    assert flash_tank.E_F == pytest.approx(expected_E_F, rel=1e-6)
    assert flash_tank.E_P == pytest.approx(expected_E_P, rel=1e-6)
    assert flash_tank.E_D == pytest.approx(expected_E_D, rel=1e-6)
    assert flash_tank.epsilon == pytest.approx(expected_epsilon, rel=1e-6)

def test_flash_tank_missing_streams_raises(flash_tank):
    """
    Test that calc_exergy_balance raises ValueError when inlet <1 or outlets <2.
    """
    # No inlets
    flash_tank.inl = {}
    flash_tank.outl = {
        0: {"m": 1, "e_PH":  90, "e_T": 45},
        1: {"m": 2, "e_PH":  80, "e_T": 40}
    }
    with pytest.raises(ValueError, match="Flash tank requires at least one inlet and two outlets."):
        flash_tank.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)

    # Only one outlet
    flash_tank.inl = {
        0: {"m": 1, "e_PH": 100, "e_T": 50}
    }
    flash_tank.outl = {
        0: {"m": 1, "e_PH":  90, "e_T": 45}
    }
    with pytest.raises(ValueError, match="Flash tank requires at least one inlet and two outlets."):
        flash_tank.calc_exergy_balance(T0=300, p0=101325, split_physical_exergy=True)