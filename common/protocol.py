"""Wire protocol helpers: encode/decode newline-delimited JSON messages."""

from __future__ import annotations

import json
from typing import Any

from common.constants import ENCODING, MSG_SEPARATOR


def encode_message(msg_type: str, payload: Any = None) -> bytes:
    r"""Encode a typed message to bytes for transmission.

    Each message is a single JSON line terminated by ``\n``.

    Args:
        msg_type: One of the ``MSG_*`` constants from ``common.constants``.
        payload: JSON-serializable payload (dict, list, str, or ``None``).

    Returns:
        UTF-8 encoded bytes ready to send over a socket.
    """
    envelope = {"type": msg_type, "payload": payload}
    return (json.dumps(envelope, ensure_ascii=False) + MSG_SEPARATOR).encode(ENCODING)


def decode_message(raw: str) -> tuple[str, Any]:
    """Decode a raw JSON string into ``(msg_type, payload)``.

    Args:
        raw: A single JSON line (without the trailing newline).

    Returns:
        Tuple of ``(msg_type, payload)``.

    Raises:
        ValueError: If *raw* is not valid JSON or missing ``type`` key.
    """
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON message: {raw!r}") from exc
    if "type" not in envelope:
        raise ValueError(f"Message missing 'type' field: {envelope!r}")
    return envelope["type"], envelope.get("payload")


def split_frames(buffer: str) -> tuple[list[str], str]:
    """Split a buffer containing zero or more newline-delimited messages.

    Args:
        buffer: Raw string that may contain partial messages.

    Returns:
        Tuple of ``(complete_messages, leftover_partial)``.
    """
    parts = buffer.split(MSG_SEPARATOR)
    # Last element is either empty (clean split) or a partial frame
    complete = [p for p in parts[:-1] if p.strip()]
    remainder = parts[-1]
    return complete, remainder
