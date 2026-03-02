from core.transport.events import EncodedEventType, SkabenEvent


def test_skaben_event_init():
    event = SkabenEvent(event_type="test_event", event_source="test_source")
    assert event.event_type == "test_event"
    assert event.event_source == "test_source"


def test_skaben_event_encode():
    event = SkabenEvent(event_type="test_event", event_source="test_source")
    encoded_event = event.encode()
    assert encoded_event.headers == {"event_type": "test_event", "event_source": "test_source"}


def test_skaben_event_decode():
    event_headers = {"event_type": "test_event", "event_source": "test_source"}
    decoded_event = SkabenEvent.decode(event_headers, {})
    assert decoded_event == {"event_type": "test_event", "event_source": "test_source"}


def test_encoded_event_init():
    encoded_event = EncodedEventType(headers={"event_type": "test_event"}, data={})
    assert encoded_event.headers == {"event_type": "test_event"}
