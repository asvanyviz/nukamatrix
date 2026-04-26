#!/usr/bin/env python3
"""PyMatrix entry point — allows `python -m nukamatrix` to work.

Supports multi-mode display:
  pure-matrix     Full-screen matrix rain (classic)
  matrix+stats    Matrix on left, system info panels on right
  stats-grid      2x2 quadrant grid with CPU, RAM, Disk, Network panels
  custom          Configurable layout

Press Tab to cycle modes at runtime (when not in screensaver mode).
"""

import argparse
import sys

from nukamatrix.config import Config, COLOR_MAP, ALLOWED_MODES
from nukamatrix.modes import DisplayMode

__version__ = "0.1.0"


def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        prog="nukamatrix",
        description=(
            "PyMatrix — Terminal Matrix Rain screensaver\n\n"
            "A Python reimagining of cmatrix with multi-mode display, "
            "system info panels, and per-frame color cycling.\n"
            "Config file: ~/.nukamatrix.conf or XDG_CONFIG_HOME/nukamatrix/nukamatrix.conf"
        ),
        epilog=(
            "Modes:\n"
            "  pure-matrix    Full-screen rain (default)\n"
            "  matrix+stats   Rain left, system info right\n"
            "  stats-grid     4-quadrant system info dashboard\n"
            "  custom         Configurable layout\n\n"
            "Controls:\n"
            "  q / ESC    Quit\n"
            "  Tab        Cycle display modes\n"
            "  Any key    Exit screensaver mode\n\n"
            "Home: https://github.com/asvanyviz/nukamatrix"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--mode",
        choices=ALLOWED_MODES,
        default=None,  # None so file config can take priority
        help=(
            "Display mode (default: pure-matrix, or from config file):\n"
            "  pure-matrix: full-screen rain\n"
            "  matrix+stats: rain left, panels right\n"
            "  stats-grid: system info quad\n"
            "  custom: configurable layout"
        ),
    )
    parser.add_argument(
        "--color",
        choices=list(COLOR_MAP.keys()),
        default=None,
        help="Rain color (default: green, or from config file)",
    )
    parser.add_argument(
        "--rainbow",
        action="store_true",
        default=None,
        help="Rainbow color cycling",
    )
    parser.add_argument(
        "--no-rainbow",
        action="store_false",
        dest="rainbow",
        help="Disable rainbow",
    )
    parser.add_argument(
        "--lambda",
        dest="lambda_mode",
        action="store_true",
        default=None,
        help="Lambda mode (λ characters only)",
    )
    parser.add_argument(
        "--charset",
        choices=["ascii", "kana", "mixed"],
        default=None,
        help="Character set (default: mixed, or from config file)",
    )
    parser.add_argument(
        "--speed",
        type=int,
        choices=range(0, 11),
        default=None,
        metavar="N",
        help="Rain speed: 0=slowest, 10=fastest (default: 4, or from config file)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        choices=range(15, 61),
        default=None,
        metavar="N",
        help="Target FPS 15-60 (default: 30, or from config file)",
    )
    parser.add_argument(
        "--bold",
        action="store_true",
        default=None,
        help="Enable bold characters",
    )
    parser.add_argument(
        "--no-bold",
        action="store_false",
        dest="bold",
        help="Disable bold",
    )
    parser.add_argument(
        "-s", "--s",
        action="store_true",
        dest="screensaver",
        default=None,
        help="Screensaver mode — exit on any key",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        metavar="FILE",
        help="Path to config INI file (default: ~/.nukamatrix.conf)",
    )

    args = parser.parse_args()

    # CLI overrides: only collect args where user explicitly set something
    cli_overrides = {
        "fps": args.fps,
        "speed": args.speed,
        "color": args.color,
        "charset": args.charset,
        "bold": args.bold,
        "rainbow": args.rainbow,
        "lambda_mode": args.lambda_mode,
        "screensaver": args.screensaver,
        "mode": args.mode,
    }

    return Config.with_file(config_path=args.config, cli_overrides=cli_overrides)


def main():
    config = parse_args()

    # Use MultiModeEngine from core.engine
    from nukamatrix.core.engine import MultiModeEngine
    engine = MultiModeEngine(config)

    try:
        engine.run()
    except KeyboardInterrupt:
        pass
    finally:
        # Ensure terminal is restored
        print("\n", end="")


if __name__ == "__main__":
    main()
