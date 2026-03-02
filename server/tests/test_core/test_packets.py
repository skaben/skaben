import json

from core.transport.packets import CUP


def test_cup_encode():
    """Test CUP encode method"""
    # Create a packet with some data
    packet = CUP(uid="00ff00ff00ff", topic="device_x", datahold={"power": True}, timestamp=12345)

    expected_data = {"timestamp": 12345, "datahold": {"power": True}}

    assert packet.encode() == json.dumps(expected_data).replace(" ", "")
