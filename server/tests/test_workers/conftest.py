import pytest


@pytest.fixture(autouse=True)
def publish(monkeypatch):
    messages = []

    def _mock_publish(body, exchange, routing_key, **kwargs):
        messages.append({"body": body, "exchange": exchange, "routing_key": routing_key, **kwargs})

    monkeypatch.setattr("core.transport.publish.publish", _mock_publish)
    return _mock_publish


@pytest.fixture(autouse=True)
def mock_config():
    class MockConfig(object):
        exchanges = {}
        queues = {}

        @property
        def internal_exchange(self):
            return "internal"

        @property
        def mqtt_exchange(self):
            return "mqtt"

    return MockConfig()


@pytest.fixture(autouse=True)
def base_handler(publish, mock_config, monkeypatch):
    class MockBaseHandler(object):
        name: str = "base"
        running: bool
        accepts: str = "json"
        outgoing_mark: str
        incoming_mark: str | list

        MOCK_MESSAGES: list

        def __init__(self, config, queues):
            self.config = config
            self.queues = queues
            self.redis_client = None
            self.connection = None
            self.MOCK_MESSAGES = []

        def start(self):
            return True

        def handle_message(self, body, message) -> None:
            raise NotImplementedError

        def dispatch(self, data, routing_data, exchange, **kwargs):
            self.MOCK_MESSAGES.append({"body": data, "exchange": exchange, "routing_key": routing_data, **kwargs})

        def set_locked(self, key: str, timeout: int = 0):
            return

        def get_locked(self, key: str) -> bool:
            return True

        def get_consumers(self, consumer, channel):
            return []

        def __str__(self) -> str:
            return self.__class__.__name__

    monkeypatch.setattr("core.worker_queue_handlers.base.BaseHandler", MockBaseHandler)
    return MockBaseHandler
