"""Tests for pymatrix.config module."""

import pytest
import tempfile
import os

from pymatrix.config import (
    Config,
    COLOR_MAP,
    ALLOWED_MODES,
    KANA_CHARSET,
    ASCII_CHARSET,
    HALFWIDTH_KANA,
    CHARSETS,
    LAMBDA_CHARSET,
    speed_to_interval,
    load_config_file,
    _parse_config_value,
)


# ── Constants ──────────────────────────────────────────────────

class TestConstants:
    def test_color_map(self):
        assert "green" in COLOR_MAP
        assert "red" in COLOR_MAP
        assert "cyan" in COLOR_MAP
        assert len(COLOR_MAP) == 7

    def test_allowed_modes(self):
        assert ALLOWED_MODES == ["pure-matrix", "matrix+stats", "stats-grid", "custom"]

    def test_charsets(self):
        assert "ascii" in CHARSETS
        assert "kana" in CHARSETS
        assert "mixed" in CHARSETS
        assert "lambda" in CHARSETS

    def test_kana_not_empty(self):
        assert len(KANA_CHARSET) > 0
        assert len(HALFWIDTH_KANA) > 0
        assert len(ASCII_CHARSET) > 0
        assert "λ" == LAMBDA_CHARSET


# ── Speed mapping ─────────────────────────────────────────────

class TestSpeedInterval:
    @pytest.mark.parametrize("speed,expected", [
        (0, 10),
        (1, 9),
        (2, 8),
        (4, 6),
        (5, 5),
        (9, 1),
        (10, 1),
    ])
    def test_speed_to_interval(self, speed, expected):
        assert speed_to_interval(speed) == expected


# ── Config dataclass ──────────────────────────────────────────

class TestConfig:
    def test_defaults(self):
        c = Config()
        assert c.fps == 30
        assert c.speed == 4
        assert c.color == "green"
        assert c.charset == "mixed"
        assert c.bold is True
        assert c.rainbow is False
        assert c.lambda_mode is False
        assert c.screensaver is False
        assert c.mode == "pure-matrix"

    def test_custom_values(self):
        c = Config(fps=60, speed=8, color="red", mode="stats-grid")
        assert c.fps == 60
        assert c.speed == 8
        assert c.color == "red"
        assert c.mode == "stats-grid"

    def test_effective_charset_default(self):
        c = Config()
        assert "0" in c.effective_charset
        assert "@" in c.effective_charset

    def test_effective_charset_lambda(self):
        c = Config(lambda_mode=True)
        assert c.effective_charset == "λ"

    def test_effective_charset_explicit(self):
        c = Config(charset="ascii", lambda_mode=False)
        assert c.effective_charset == ASCII_CHARSET

    def test_update_interval(self):
        c = Config(speed=0)
        assert c.update_interval == 10
        c = Config(speed=10)
        assert c.update_interval == 1


# ── Config file parsing ───────────────────────────────────────

class TestParseConfigValue:
    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("True", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("1", True),
        ("42", 42),
        ("3.14", 3.14),
        ("green", "green"),
        ("pure-matrix", "pure-matrix"),
        ("mixed", "mixed"),
    ])
    def test_parse(self, value, expected):
        assert _parse_config_value("test", value) == expected


class TestLoadConfigFile:
    def test_missing_file_returns_empty(self):
        result = load_config_file("/nonexistent/path/pymatrix.conf")
        assert result == {}

    def test_valid_ini_file(self):
        content = (
            "[display]\n"
            "speed = 7\n"
            "color = red\n"
            "fps = 60\n"
            "bold = true\n"
            "rainbow = false\n"
            "mode = matrix+stats\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(content)
            f.flush()
            try:
                result = load_config_file(f.name)
                assert result["speed"] == 7
                assert result["color"] == "red"
                assert result["fps"] == 60
                assert result["bold"] is True
                assert result["rainbow"] is False
                assert result["mode"] == "matrix+stats"
            finally:
                os.unlink(f.name)

    def test_invalid_section_ignored(self):
        content = "[other]\nspeed = 7\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(content)
            f.flush()
            try:
                result = load_config_file(f.name)
                assert result == {}
            finally:
                os.unlink(f.name)


class TestConfigWithFile:
    def test_cli_overrides_file(self):
        content = "[display]\nspeed = 2\ncolor = blue\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(content)
            f.flush()
            try:
                cli = {"speed": 8, "color": "red"}
                c = Config.with_file(config_path=f.name, cli_overrides=cli)
                assert c.speed == 8     # CLI wins
                assert c.color == "red" # CLI wins
                assert c.mode == "pure-matrix"  # default (not in file)
            finally:
                os.unlink(f.name)

    def test_file_with_partial_cli(self):
        """Only color from CLI, rest from file."""
        content = "[display]\nspeed = 2\ncolor = blue\nfps = 15\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(content)
            f.flush()
            try:
                # Only override color via CLI
                cli = {"color": "green"}
                c = Config.with_file(config_path=f.name, cli_overrides=cli)
                assert c.color == "green"   # CLI
                assert c.fps == 15          # file
                assert c.speed == 2         # file
            finally:
                os.unlink(f.name)
