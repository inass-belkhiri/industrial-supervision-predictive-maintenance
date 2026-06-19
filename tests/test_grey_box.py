import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

from grey_box import GreyBoxModel


def test_classify_urgency():
    assert GreyBoxModel._classify_urgency(43.0) == 'OK'
    assert GreyBoxModel._classify_urgency(42.0) == 'OK'
    assert GreyBoxModel._classify_urgency(41.8) == 'FAIBLE'
    assert GreyBoxModel._classify_urgency(41.5) == 'FAIBLE'
    assert GreyBoxModel._classify_urgency(41.3) == 'MOYEN'
    assert GreyBoxModel._classify_urgency(41.0) == 'MOYEN'
    assert GreyBoxModel._classify_urgency(40.7) == 'HAUTE'
    assert GreyBoxModel._classify_urgency(40.0) == 'URGENT'
    assert GreyBoxModel._classify_urgency(39.5) == 'URGENT'


def test_set_calibration():
    model = GreyBoxModel()
    model.set_calibration(1, 1, 43.5)
    assert model.calibration_temps[(1, 1)] == 43.5
    assert model.delta_T_normal[(1, 1)] == pytest.approx(1.5, abs=0.01)


def test_compute_normal():
    model = GreyBoxModel()
    model.set_calibration(1, 1, 43.5)
    result = model.compute(1, 1, T_mold=43.5, flow_lpm=16.5)
    assert result['urgence'] == 'OK'
    assert result['delta_T_measured'] == pytest.approx(1.5, abs=0.01)
    assert result['delta_T_calcaire'] == pytest.approx(0.0, abs=0.001)
    assert result['epaisseur_mm'] == pytest.approx(0.0, abs=0.001)
    assert result['degradation_pct'] == pytest.approx(0.0, abs=0.1)


def test_compute_with_calcaire():
    model = GreyBoxModel()
    model.set_calibration(1, 1, 43.5)
    result = model.compute(1, 1, T_mold=42.0, flow_lpm=16.5)
    assert result['delta_T_measured'] == pytest.approx(3.0, abs=0.01)
    assert result['delta_T_calcaire'] > 0
    assert result['epaisseur_mm'] > 0
    assert result['urgence'] == 'OK'


def test_compute_critical():
    model = GreyBoxModel()
    model.set_calibration(1, 1, 43.5)
    result = model.compute(1, 1, T_mold=39.0, flow_lpm=16.5)
    assert result['urgence'] == 'URGENT'
    assert result['degradation_pct'] == pytest.approx(100.0, abs=0.1)


def test_compute_no_calibration():
    model = GreyBoxModel()
    result = model.compute(1, 1, T_mold=42.0, flow_lpm=16.5)
    assert result['delta_T_calcaire'] >= 0
    assert 'urgence' in result
