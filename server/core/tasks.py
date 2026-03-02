from typing import List

from core.helpers import format_routing_key
from core.transport.config import SkabenQueue
from core.transport.publish import get_interface
from core.models import DeviceTopic, DeviceTopicManager


def update_devices(topics: List[str]) -> List[str]:
    send_to = topics[:]
    for special in DeviceTopicManager.special_topics:
        if special in topics:
            send_to.extend(DeviceTopic.objects.get_topics_by_type(special))
    result = set([topic for topic in send_to if topic not in DeviceTopicManager.special_topics])
    with get_interface() as publisher:
        for topic in result:
            publisher.publish(
                body={},
                exchange=publisher.config.exchanges.get("internal"),
                routing_key=format_routing_key(SkabenQueue.CLIENT_UPDATE.value, topic, "all"),
            )
    return list(result)
