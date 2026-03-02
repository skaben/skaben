def test_base_handler(base_handler, mock_config):
    from core.worker_queue_handlers.base import BaseHandler

    handler = BaseHandler(mock_config, mock_config.queues)
    test_payload = {"data": {"test": "test"}, "routing_data": ["topic", "device", "key"], "exchange": "exchange"}

    assert handler.name == "base"
    assert handler.accepts == "json"

    handler.dispatch(**test_payload)

    assert handler.MOCK_MESSAGES
    assert handler.MOCK_MESSAGES[0] == {
        "body": test_payload["data"],
        "routing_key": test_payload["routing_data"],
        "exchange": test_payload["exchange"],
    }
