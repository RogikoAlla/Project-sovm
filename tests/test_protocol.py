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


class TestDecodeMessage:
    """Tests for decode_message."""

    def test_round_trip(self):
        """Encoding then decoding should recover original type and payload."""
        encoded = encode_message(MSG_THROW, {"card": "7"})
        msg_type, payload = decode_message(encoded.decode().strip())
        assert msg_type == MSG_THROW
        assert payload == {"card": "7"}

    def test_invalid_json_raises(self):
        """Invalid JSON should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            decode_message("not-json")

    def test_missing_type_raises(self):
        """Message without 'type' key should raise ValueError."""
        with pytest.raises(ValueError):
            decode_message(json.dumps({"payload": "x"}))


class TestSplitFrames:
    """Tests for split_frames buffer handling."""

    def test_single_complete_frame(self):
        """A buffer with one newline should yield one frame."""
        frames, remainder = split_frames('{"type":"PING","payload":null}\n')
        assert len(frames) == 1
        assert remainder == ""

    def test_partial_frame_held(self):
        """Incomplete last frame should be returned as remainder."""
        frames, remainder = split_frames('{"type":"PING","payload":null}\n{"partial"')
        assert len(frames) == 1
        assert remainder == '{"partial"'

    def test_multiple_frames(self):
        """Buffer with multiple newlines should yield multiple frames."""
        frames, remainder = split_frames("A\nB\nC\n")
        assert frames == ["A", "B", "C"]
        assert remainder == ""

    def test_empty_buffer(self):
        """Empty buffer should yield no frames and empty remainder."""
        frames, remainder = split_frames("")
        assert frames == []
        assert remainder == ""

