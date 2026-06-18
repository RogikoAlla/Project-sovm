"""Gettext-based internationalisation helpers for King and Servant."""

from __future__ import annotations

import builtins
import gettext
import os
from typing import Callable

DOMAIN = "messages"


def _locale_dir() -> str:
    """Return the absolute path to the bundled ``locale`` directory."""
    here = os.path.dirname(__file__)
    return os.path.join(here, "locale")


def _resolve_locale(locale: str | None) -> str:
    """Pick an explicit locale or fall back to ``LANG``/English."""
    if locale:
        return locale
    lang_env = os.environ.get("LANG", "en")
    return lang_env.split("_")[0].split(".")[0] or "en"


def get_translator(locale: str | None = None) -> Callable[[str], str]:
    """Return a translation function, falling back to identity if no catalog."""
    locale = _resolve_locale(locale)
    try:
        translation = gettext.translation(
            DOMAIN, localedir=_locale_dir(), languages=[locale]
        )
        return translation.gettext
    except FileNotFoundError:
        return lambda s: s


def setup_i18n(locale: str | None = None) -> None:
    """Install ``_`` as a builtin so any module can translate strings."""
    builtins._ = get_translator(locale)
