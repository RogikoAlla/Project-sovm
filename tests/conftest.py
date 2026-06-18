"""Shared pytest fixtures."""

import pytest

from common.i18n import setup_i18n


@pytest.fixture(autouse=True)
def force_english_locale(monkeypatch):
    """Use English locale by default in tests."""
    monkeypatch.setenv("LANG", "en")
    setup_i18n("en")
    yield
    setup_i18n("en")

