import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

from cause_classifier import CauseClassifier


class TestCauseClassifier:
    def test_physical_rule_heater_resistance(self):
        result = CauseClassifier.physical_rules(
            affected_ratio=0.9,
            sudden_drop=False,
            flow_rate=15.0,
            flow_drop=False,
            nominal_flow=16.5,
        )
        assert result is not None
        assert result['cause'] == 'HEATER_RESISTANCE_HS'
        assert result['confidence'] == 1.0
        assert result['method'] == 'physical_rule'

    def test_physical_rule_pump_failure(self):
        result = CauseClassifier.physical_rules(
            affected_ratio=0.9,
            sudden_drop=True,
            flow_rate=4.0,
            flow_drop=True,
            nominal_flow=16.5,
        )
        assert result is not None
        assert result['cause'] == 'HEATER_POMPE_HS'
        assert result['confidence'] == 1.0
        assert result['method'] == 'physical_rule'

    def test_ambiguous_case_returns_none(self):
        result = CauseClassifier.physical_rules(
            affected_ratio=0.5,
            sudden_drop=False,
            flow_rate=14.0,
            flow_drop=False,
            nominal_flow=16.5,
        )
        assert result is None

    def test_auto_label_all_classes(self):
        assert CauseClassifier.auto_label(
            affected_ratio=0.9, sudden_drop=False, flow_drop=False,
            flow_rate=15.0, variance=0.05, R_squared=0.5,
            delta_T_calcaire_slope=0.01,
        ) == 'HEATER_RESISTANCE_HS'

        assert CauseClassifier.auto_label(
            affected_ratio=0.9, sudden_drop=True, flow_drop=True,
            flow_rate=4.0, variance=0.05, R_squared=0.5,
            delta_T_calcaire_slope=0.01,
        ) == 'HEATER_POMPE_HS'

        assert CauseClassifier.auto_label(
            affected_ratio=0.8, sudden_drop=False, flow_drop=False,
            flow_rate=0.3, variance=0.05, R_squared=0.5,
            delta_T_calcaire_slope=0.01,
        ) == 'NIVEAU_BAS_VANNE_PANNE'

        assert CauseClassifier.auto_label(
            affected_ratio=0.3, sudden_drop=False, flow_drop=False,
            flow_rate=16.5, variance=0.5, R_squared=0.2,
            delta_T_calcaire_slope=0.01,
        ) == 'BULLES_AIR'

        assert CauseClassifier.auto_label(
            affected_ratio=0.25, sudden_drop=False, flow_drop=False,
            flow_rate=16.5, variance=0.05, R_squared=0.9,
            delta_T_calcaire_slope=0.05,
        ) == 'CALCAIRE_TUYAUX'

        assert CauseClassifier.auto_label(
            affected_ratio=0.2, sudden_drop=False, flow_drop=False,
            flow_rate=16.5, variance=0.05, R_squared=0.8,
            delta_T_calcaire_slope=0.01,
        ) == 'ISOLATION_DEGRADEE'

        assert CauseClassifier.auto_label(
            affected_ratio=0.5, sudden_drop=False, flow_drop=False,
            flow_rate=11.0, variance=0.05, R_squared=0.5,
            delta_T_calcaire_slope=0.01, nominal_flow=16.5,
        ) == 'FUITE_CIRCUIT'
