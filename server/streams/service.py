from typing import Optional

from core.helpers import get_server_timestamp
from streams.serializers import StreamRecordSerializer


def write_event(stream: str, source: str, message: str, message_data: Optional[dict], mark: Optional[str]):
    """Записываем событие для отображения в потоке"""

    event_data = {
        "stream": stream,
        "source": source,
        "mark": mark or "",
        "timestamp": get_server_timestamp() + 1,  # fixing confusing 'too fast replies'
        "message": message,
        "message_data": message_data or {},
    }
    filtered = {key: val for key, val in event_data.items() if val}
    serializer = StreamRecordSerializer(data=filtered)
    if serializer.is_valid():
        serializer.save()
