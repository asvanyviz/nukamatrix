"""PyMatrix configuration constants and defaults.

Supports three-tier config precedence (highest overrides lowest):
  1. CLI arguments
  2. Config file (~/.nukamatrix.conf or XDG_CONFIG_HOME/nukamatrix/nukamatrix.conf)
  3. Hardcoded defaults
"""

import configparser
import os
from dataclasses import dataclass, field

# ── Character Sets ──────────────────────────────────────────────

# Katakana + ASCII mix (closest to cmatrix default)
KANA_CHARSET = "".join(
    chr(c)
    for c in range(0x30A0, 0x30FF + 1)  # Katakana full block
)  # 96 characters

ASCII_CHARSET = "".join(chr(c) for c in range(0x21, 0x7E))  # printable ASCII: !~

# Halfwidth katakana (cmatrix uses these)
HALFWIDTH_KANA = "".join(chr(c) for c in range(0xFF66, 0xFF9E))

# Lambda set
LAMBDA_CHARSET = "λ"

# Mixed charset: kana + numbers + symbols
MIXED_CHARSET = KANA_CHARSET + "0123456789@#$%&"

CHARSETS = {
    "ascii": ASCII_CHARSET,
    "kana": HALFWIDTH_KANA,
    "mixed": MIXED_CHARSET,
    "lambda": LAMBDA_CHARSET,
}

# ── Color Scheme ────────────────────────────────────────────────

# Color names -> blessed color attribute names
COLOR_MAP = {
    "green": "green",
    "red": "red",
    "blue": "blue",
    "white": "white",
    "yellow": "yellow",
    "cyan": "cyan",
    "magenta": "magenta",
}

# ── Defaults ────────────────────────────────────────────────────

DEFAULT_FPS = 30
DEFAULT_SPEED = 2  # 0-10, maps to update frequency
DEFAULT_COLOR = "green"
DEFAULT_CHARSET = "mixed"
DEFAULT_BOLD = True
DEFAULT_RAINBOW = False
DEFAULT_MODE = "pure-matrix"

# Even column spacing (like cmatrix - characters on even positions)
COLUMN_STEP = 2

# Allowed display modes
ALLOWED_MODES = ["pure-matrix", "matrix+stats", "stats-grid", "custom"]

# Speed-to-update-interval mapping
# speed 0 = slowest (update every 10 frames), speed 10 = fastest (every frame)
def speed_to_interval(speed: int) -> int:
    """Convert speed 0-10 to update interval in frames (higher = slower)."""
    if speed <= 0:
        return 10
    return max(1, 10 - speed)


# ── Config File Support ──────────────────────────────────────

def _get_config_paths() -> list[str]:
    """Return candidate config file paths in priority order."""
    paths = []
    # XDG spec
    xdg_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_home:
        paths.append(os.path.join(xdg_home, "nukamatrix", "nukamatrix.conf"))
    # ~/.config/nukamatrix/nukamatrix.conf
    paths.append(os.path.expanduser("~/.config/nukamatrix/nukamatrix.conf"))
    # ~/.nukamatrix.conf (legacy/simple)
    paths.append(os.path.expanduser("~/.nukamatrix.conf"))
    return paths


def load_config_file(path: str | None = None) -> dict:
    """Load config from an INI file.

    Args:
        path: explicit file path, or None to search default locations.

    Returns:
        Dict of {key: value} with parsed types.
    """
    if path:
        candidates = [path]
    else:
        candidates = _get_config_paths()

    for candidate in candidates:
        if os.path.isfile(candidate):
            cp = configparser.ConfigParser()
            cp.read(candidate)
            result = {}
            if cp.has_section("display"):
                for key, val in cp["display"].items():
                    result[key] = _parse_config_value(key, val)
            return result
    return {}  # no config file found — caller uses defaults


def _parse_config_value(key: str, value: str):
    """Parse a config INI string value into the appropriate Python type."""
    v = value.strip()
    # Booleans
    if v.lower() in ("true", "yes", "on", "1"):
        return True
    if v.lower() in ("false", "no", "off", "0"):
        return False
    # Integer
    try:
        return int(v)
    except ValueError:
        pass
    # Float
    try:
        return float(v)
    except ValueError:
        pass
    # String
    return v

# ── Config Dataclass ───────────────────────────────────────────

def _resolve_config(file_values: dict, cli_overrides: dict | None = None) -> dict:
    """Resolve config: file values < CLI overrides.

    Args:
        file_values: Dict loaded from config file.
        cli_overrides: Dict from argparse (only explicitly set args).

    Returns:
        Resolved dict ready for Config(**...).
    """
    resolved = dict(file_values)
    if cli_overrides:
        for key, val in cli_overrides.items():
            if val is not None:
                resolved[key] = val
    return resolved


@dataclass
class Config:
    """Runtime configuration with mutable fields for menu changes."""
    fps: int = DEFAULT_FPS
    speed: int = DEFAULT_SPEED
    color: str = DEFAULT_COLOR
    charset: str = DEFAULT_CHARSET
    bold: bool = DEFAULT_BOLD
    rainbow: bool = DEFAULT_RAINBOW
    lambda_mode: bool = False
    screensaver: bool = False
    mode: str = DEFAULT_MODE  # pure-matrix | matrix+stats | stats-grid | custom

    @classmethod
    def with_file(cls, config_path: str | None = None, cli_overrides: dict | None = None) -> "Config":
        """Create a Config merging file + CLI overrides.

        Precedence: CLI > config file > defaults.
        """
        file_vals = load_config_file(config_path)
        resolved = _resolve_config(file_vals, cli_overrides)
        return cls(**resolved)

    @property
    def effective_charset(self) -> str:
        if self.lambda_mode:
            return LAMBDA_CHARSET
        return CHARSETS.get(self.charset, MIXED_CHARSET)

    @property
    def update_interval(self) -> int:
        return speed_to_interval(self.speed)
