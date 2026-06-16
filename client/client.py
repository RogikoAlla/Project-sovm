"""Networking skeleton for the King and Servant client. """

from __future__ import annotations

from typing import Any

from common.constants import DEFAULT_HOST, DEFAULT_PORT, ENCODING
from common.protocol import decode_message, encode_message, split_frames


class GameClient:
    """Holds connection settings and the incoming byte buffer."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._buffer = ""

    def encode(self, msg_type: str, payload: Any = None) -> bytes:
        """Encode an outgoing message to bytes ready to send."""
        return encode_message(msg_type, payload)

    def feed(self, data: bytes) -> list[tuple[str, Any]]:
        """Buffer received bytes and return any complete decoded messages."""
        self._buffer += data.decode(ENCODING)
        frames, self._buffer = split_frames(self._buffer)
        return [decode_message(frame) for frame in frames]
