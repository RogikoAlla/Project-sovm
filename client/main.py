"""Command-line entry point for the King and Servant client."""

from __future__ import annotations

import argparse
import asyncio

from client.client import GameClient, render_message
from common.constants import DEFAULT_HOST, DEFAULT_PORT
from common.i18n import setup_i18n


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="King and Servant client")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--name", default="Player")
    parser.add_argument("--locale", default=None)
    return parser


async def run(client: GameClient, name: str) -> None:
    """Connect, join and print every incoming server message until EOF."""
    await client.connect()
    await client.join(name)
    while True:
        messages = await client.receive()
        if not messages:
            break
        for msg_type, payload in messages:
            text = render_message(msg_type, payload)
            if text:
                print(text)
    await client.close()


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, set up localisation and run the client."""
    args = build_parser().parse_args(argv)
    setup_i18n(args.locale)
    client = GameClient(args.host, args.port)
    asyncio.run(run(client, args.name))


if __name__ == "__main__":
    main()
