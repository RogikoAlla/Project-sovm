"""Entry point for the King and Servant server."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from common.constants import DEFAULT_HOST, DEFAULT_PORT, DECK_36, DECK_52
from server.server import GameServer


def _parse_args(argv=None):
    """Parse CLI arguments for the server."""
    parser = argparse.ArgumentParser(
        prog="kas-server",
        description="King and Servant — game server",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="TCP port")
    parser.add_argument(
        "--deck",
        type=int,
        choices=[DECK_36, DECK_52],
        default=DECK_36,
        help="Deck size: 36 or 52 cards",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    return parser.parse_args(argv)


def main(argv=None):
    """Start the King and Servant server."""
    args = _parse_args(argv)
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    server = GameServer(host=args.host, port=args.port, deck_size=args.deck)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
