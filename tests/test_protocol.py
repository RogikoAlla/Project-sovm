"""Unit tests for common.protocol wire encoding/decoding."""

import json
import pytest
from common.constants import MSG_THROW, MSG_ERROR
from common.protocol import decode_message, encode_message, split_frames


class TestEncodeMessage:
    """Tests for encode_message."""

    def test_encodes_to_bytes(self):
        """encode_message should return bytes."""
        assert isinstance(encode_message(MSG_THROW, {"card": "A"}), bytes)

    def test_ends_with_newline(self):
        """Encoded message should end with newline."""
        assert encode_message(MSG_THROW).endswith(b"\n")

    def test_json_structure(self):
        """Encoded message body should be valid JSON with type and payload."""
        obj = json.loads(encode_message(MSG_ERROR, "bad card").strip())
        assert obj["type"] == MSG_ERROR
        assert obj["payload"] == "bad card"

    def test_none_payload(self):
        """None payload should be serialized as null."""
        obj = json.loads(encode_message("PING").strip())
        assert obj["payload"] is None
