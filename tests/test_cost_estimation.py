"""Tests for the power-law cost estimation module."""
import pytest

from exerpy.cost_estimation.power_law import (
    DefaultCostEstimator,
    _pec_compressor,
)


class _FakeComponent:
    def __init__(self, inl):
        self.inl = inl


def _bare_estimator():
    # The sizing helpers do not touch the analysis object, so skip __init__.
    return object.__new__(DefaultCostEstimator)


def test_compressor_vdot_uses_volumetric_flow():
    """The parsers store the volumetric flow [m^3/s] under ``v``; the size in
    m^3/h must be v * 3600 and must NOT scale with the mass flow (regression
    test: the size was previously multiplied by the mass flow twice)."""
    est = _bare_estimator()
    v = 1.2  # m^3/s
    small = _FakeComponent({0: {"m": 1.0, "v": v}})
    large = _FakeComponent({0: {"m": 9.0, "v": v}})
    assert est._get_compressor_vdot(small) == pytest.approx(v * 3600)
    assert est._get_compressor_vdot(large) == pytest.approx(v * 3600)


def test_compressor_vdot_missing_data():
    est = _bare_estimator()
    assert est._get_compressor_vdot(_FakeComponent({0: {"m": 1.0}})) is None
    assert est._get_compressor_vdot(object()) is None


def test_pec_compressor_reference_point():
    """At the reference size the correlation must return the reference cost."""
    assert _pec_compressor(279.8, "R600") == pytest.approx(19_850)
