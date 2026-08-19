"""
Unit tests for environment-driven configuration parsing.
"""

import pytest

from finops_engine.config import _env_bool, _env_int


def test_env_bool_parses_truthy_values(monkeypatch):
    for raw in ("1", "true", "True", "YES", "on", " 1 "):
        monkeypatch.setenv("TEST_BOOL", raw)
        assert _env_bool("TEST_BOOL", False) is True


def test_env_bool_parses_falsy_and_missing(monkeypatch):
    monkeypatch.setenv("TEST_BOOL", "false")
    assert _env_bool("TEST_BOOL", True) is False
    monkeypatch.delenv("TEST_BOOL", raising=False)
    assert _env_bool("TEST_BOOL", True) is True


def test_env_int_parses_valid_value(monkeypatch):
    monkeypatch.setenv("TEST_INT", "42")
    assert _env_int("TEST_INT", 15) == 42


def test_env_int_falls_back_on_garbage(monkeypatch):
    monkeypatch.setenv("TEST_INT", "abc")
    assert _env_int("TEST_INT", 15) == 15


def test_env_int_falls_back_on_too_small(monkeypatch):
    monkeypatch.setenv("TEST_INT", "0")
    assert _env_int("TEST_INT", 15) == 15


def test_env_int_uses_default_when_missing(monkeypatch):
    monkeypatch.delenv("TEST_INT", raising=False)
    assert _env_int("TEST_INT", 15) == 15


@pytest.mark.parametrize("bad_value", ["abc", "0", "-3", ""])
def test_settings_survive_bad_metrics_refresh_value(monkeypatch, bad_value):
    """A malformed FINOP_METRICS_REFRESH_SECONDS must never crash app startup."""
    monkeypatch.setenv("FINOP_METRICS_REFRESH_SECONDS", bad_value)
    from finops_engine.config import Settings

    assert Settings().metrics_refresh_seconds == 15
