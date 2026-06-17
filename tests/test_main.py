"""Tests for the client command-line entry point."""

from client.main import build_parser
from common.constants import DEFAULT_HOST, DEFAULT_PORT


def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.host == DEFAULT_HOST
    assert args.port == DEFAULT_PORT
    assert args.name is None


def test_parser_custom_values():
    args = build_parser().parse_args(["--host", "1.2.3.4", "--port", "9", "--name", "Bob"])
    assert args.host == "1.2.3.4"
    assert args.port == 9
    assert args.name == "Bob"
