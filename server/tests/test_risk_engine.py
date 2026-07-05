"""Exhaustive unit tests for RiskEngine."""
from core.risk_engine import Event, RiskConfig, RiskResult, compute_risk


def test_empty_events_safe(risk_config):
    result = compute_risk([], risk_config)
    assert result.score == 0
    assert result.level == "safe"
    assert result.breakdown == {}


def test_single_event_weight(risk_config):
    events = [Event(type="tab_switch", weight=10)]
    result = compute_risk(events, risk_config)
    assert result.score == 10
    assert result.level == "safe"
    assert result.breakdown["tab_switch"] == 10


def test_review_threshold(risk_config):
    events = [
        Event(type="tab_switch", weight=15),
        Event(type="window_blur", weight=20),
    ]
    result = compute_risk(events, risk_config)
    assert result.score == 35
    assert result.level == "review"


def test_suspicious_threshold(risk_config):
    events = [
        Event(type="ocr_flag", weight=40),
        Event(type="object_flag", weight=25),
    ]
    result = compute_risk(events, risk_config)
    assert result.score == 65
    assert result.level == "suspicious"


def test_config_default_weights(risk_config):
    events = [Event(type="tab_switch", weight=0)]
    result = compute_risk(events, risk_config)
    assert result.breakdown["tab_switch"] == 10


def test_event_weight_override(risk_config):
    events = [Event(type="tab_switch", weight=50)]
    result = compute_risk(events, risk_config)
    assert result.score == 50
    assert result.level == "review"


def test_duplicate_events_accumulate(risk_config):
    events = [
        Event(type="tab_switch", weight=10),
        Event(type="tab_switch", weight=10),
    ]
    result = compute_risk(events, risk_config)
    assert result.score == 20
    assert result.breakdown["tab_switch"] == 20


def test_idempotent(risk_config, sample_events):
    r1 = compute_risk(sample_events, risk_config)
    r2 = compute_risk(sample_events, risk_config)
    assert r1 == r2


def test_type_normalization(risk_config):
    events = [Event(type="TAB-SWITCH", weight=10)]
    result = compute_risk(events, risk_config)
    assert "tab_switch" in result.breakdown


def test_zero_weight_events_ignored(risk_config):
    events = [Event(type="unknown_type", weight=0)]
    result = compute_risk(events, risk_config)
    assert result.score == 0


def test_custom_thresholds():
    config = RiskConfig(weights={"tab_switch": 10}, thresholds={"review": 5, "suspicious": 15})
    result = compute_risk([Event(type="tab_switch", weight=10)], config)
    assert result.level == "review"

    result2 = compute_risk([Event(type="tab_switch", weight=10), Event(type="tab_switch", weight=10)], config)
    assert result2.level == "suspicious"
