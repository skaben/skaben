import pytest
from event_contexts.alert.events import AlertCounterEvent, AlertStateEvent
from pydantic import ValidationError


def test_alert_state_event_valid():
    event = AlertStateEvent(event_type="alert_state", event_source="test", state="active")
    encoded = event.encode()

    assert event.event_type == "alert_state"
    assert event.state == "active"
    assert encoded.headers == {"event_type": "alert_state", "event_source": "test"}
    assert encoded.data == {"state": "active", "counter_reset": True}


def test_alert_state_event_missing_state():
    with pytest.raises(ValidationError):
        AlertStateEvent(event_type="alert_state")


def test_alert_counter_event_valid():
    event = AlertCounterEvent(event_type="alert_counter", value=10, change="increase", comment="test mock")
    assert event.event_type == "alert_counter"
    assert event.value == 10
    assert event.change == "increase"
    assert event.comment == "test mock"


def test_alert_counter_event_invalid_change():
    with pytest.raises(ValidationError):
        AlertCounterEvent(event_type="alert_counter", value=10, change="invalid_change")
