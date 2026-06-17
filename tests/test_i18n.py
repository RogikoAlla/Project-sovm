"""Tests for the gettext-based localisation layer."""

import builtins

from common import i18n


def test_russian_translation():
    translate = i18n.get_translator("ru")
    assert translate("Enter your name: ") == "Введите ваше имя: "
    assert translate("Name cannot be empty.") == "Имя не может быть пустым."


def test_english_translation():
    translate = i18n.get_translator("en")
    assert translate("Enter your name: ") == "Enter your name: "


def test_unknown_locale_falls_back_to_identity():
    translate = i18n.get_translator("zz")
    assert translate("Enter your name: ") == "Enter your name: "


def test_none_locale_uses_lang_env(monkeypatch):
    monkeypatch.setenv("LANG", "ru_RU.UTF-8")
    translate = i18n.get_translator(None)
    assert translate("Name cannot be empty.") == "Имя не может быть пустым."


def test_resolve_locale_defaults_to_english(monkeypatch):
    monkeypatch.delenv("LANG", raising=False)
    assert i18n._resolve_locale(None) == "en"


def test_setup_installs_builtin(monkeypatch):
    monkeypatch.setattr(builtins, "_", None, raising=False)
    i18n.setup_i18n("ru")
    assert builtins._("Enter your name: ") == "Введите ваше имя: "
