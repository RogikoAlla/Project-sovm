"""Command-line entry point for the King and Servant client."""

from __future__ import annotations

import argparse
import asyncio

from client.client import GameClient
from client.input_handler import prompt_name
from common.constants import DEFAULT_HOST, DEFAULT_PORT
from common.i18n import setup_i18n


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="King and Servant client")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--name", default=None)
    parser.add_argument("--locale", default=None)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, set up localisation and run the client."""
    args = build_parser().parse_args(argv)
    setup_i18n(args.locale)
    name = args.name or prompt_name()
    client = GameClient(args.host, args.port, name)
    asyncio.run(client.connect())


if __name__ == "__main__":
    main()
