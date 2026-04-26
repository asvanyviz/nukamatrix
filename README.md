# PyMatrix 🟢

> Terminal Matrix Rain — inspired by **cmatrix**, reimagined in Python

A Python terminal screensaver that recreates the iconic Matrix falling-characters effect, powered by the `blessed` library. Features multiple display modes, real-time system info panels, and full color customization.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/Powerd_by-blessed-orange" alt="Powered by blessed">
</p>

## ✨ Features

- **🌧 Classic Matrix Rain** — Full-screen falling katakana/ASCII characters with trail fade
- **📊 Multi-Mode Display** — 4 modes: pure matrix, matrix+stats, stats-grid, custom
- **🖥 System Info Panels** — CPU, Memory, Disk I/O, Network throughput with animated bars
- **🌈 Color Modes** — 7 solid colors + rainbow cycling
- **⚡ Configurable** — Speed, FPS, charset, bold — via CLI or config file
- **🔄 Runtime Mode Cycling** — Press `Tab` to switch modes without quitting
- **📺 Screensaver Mode** — Exit on any key press
- **🎯 Zone Rendering** — Only updates visible regions, no wasted terminal I/O
- **🔥 Anti Burn-in** — Color-cycling panels with pulsing borders
- **📦 Pip Installable** — `pip install nukamatrix` (or editable)
- **🐧 Linux / macOS** — Works anywhere Python 3.10+ runs

## 📸 Screenshots

### Pure Matrix (green)
```
  ンガ  ィクケガ   コ    ィ
   グ ァ コ ィガ    ゲ
ガ ィ ァン ィ コ ァ ギ
  アギ  ク ィ  コ ウ
```

### Matrix + Stats (matrix+stats)
```
  ッギ ィコ ァ  ┌ CPU ───────┐
  ァ ェコ ギ    ║ 85.3% ████████░░ ║
 ギ ィ ィ   ウ  ║ Freq: 3600 MHz ║
    ァコ ァ     ║ Load: 2.41 ... ║
                └──────────────┘
```

### Stats Grid (dashboard)
```
┌── CPU ──────┐ ┌── MEMORY ───┐
│ 85.3% ███░░ │ │ 62.1% ████░ │
│ Freq: ...   │ │ Used: 12.4G │
├─────────────┤ ├─────────────┤
┌── DISK ─────┐ ┌── NETWORK ──┐
│ 45.2% ██░░░ │ │ ▼ Down: ... │
│ Read: 12 MB │ │ ▲ Up:   2 M │
└─────────────┘ └─────────────┘
```

## 🚀 Quick Start

### Install

```bash
# From PyPI (when published)
pip install nukamatrix

# From source
pip install git+https://github.com/asvanyviz/nukamatrix.git

# Or download, unzip, and install editable
git clone https://github.com/asvanyviz/nukamatrix.git
cd nukamatrix
pip install -e .
```

### Run

```bash
# Default (green matrix rain)
nukamatrix

# With options
nukamatrix --mode matrix+stats --color red --speed 6

# Lambda mode (the lambda one 🐑)
nukamatrix --lambda --rainbow

# Screensaver mode — exit on any key
nukamatrix -s
```

## 🎮 Controls

| Key | Action |
|-----|--------|
| `q` / `ESC` | Quit |
| `Tab` | Cycle display modes |
| Any key | Exit (screensaver mode only) |

## 📋 CLI Reference

```
Usage: nukamatrix [OPTIONS]

Options:
  -V, --version         Show version and exit
  --mode MODE           Display mode: pure-matrix, matrix+stats, stats-grid, custom
  --color COLOR         Rain color: green, red, blue, white, yellow, cyan, magenta
  --rainbow             Enable rainbow color cycling
  --no-rainbow          Disable rainbow
  --lambda              Lambda mode (λ characters only)
  --charset CHARSET     Character set: ascii, kana, mixed (default: mixed)
  --speed N             Rain speed 0-10 (0=slowest, 10=fastest, default: 4)
  --fps N               Target FPS 15-60 (default: 30)
  --bold                Enable bold characters
  --no-bold             Disable bold
  -s, --s               Screensaver mode — exit on any key
  --config FILE         Path to config INI file (default: ~/.nukamatrix.conf)
  -h, --help            Show help message and exit
```

## ⚙️ Configuration File

PyMatrix reads an INI config file for persistent defaults. Supports both legacy `~/.nukamatrix.conf` and XDG spec `~/.config/nukamatrix/nukamatrix.conf`.

**Precedence:** CLI arguments > config file > hardcoded defaults

### Example `~/.nukamatrix.conf`

```ini
[display]
mode = matrix+stats
color = cyan
speed = 6
fps = 45
bold = true
rainbow = false
charset = mixed
```

### Available options

| Key | Values | Default |
|-----|--------|---------|
| `mode` | `pure-matrix`, `matrix+stats`, `stats-grid`, `custom` | `pure-matrix` |
| `color` | `green`, `red`, `blue`, `white`, `yellow`, `cyan`, `magenta` | `green` |
| `speed` | `0` - `10` | `4` |
| `fps` | `15` - `60` | `30` |
| `bold` | `true` / `false` | `true` |
| `rainbow` | `true` / `false` | `false` |
| `charset` | `ascii`, `kana`, `mixed` | `mixed` |
| `lambda_mode` | `true` / `false` | `false` |
| `screensaver` | `true` / `false` | `false` |

## 🛠 Architecture

```
nukamatrix/
├── __init__.py          # package version
├── __main__.py          # CLI entry point (argparse + boot)
├── config.py            # dataclass, constants, config file loader
├── modes.py             # DisplayMode enum
├── core/
│   ├── __init__.py
│   ├── engine.py        # main loop, mode routing, resize handling
│   ├── matrix.py        # Cell + Column data model
│   └── renderer.py     # blessed terminal rendering + zone support
├── panels/
│   ├── __init__.py
│   ├── base.py          # Panel base class + border rendering
│   ├── sysinfo.py       # CPU, Mem, Disk, Net, Clock panels
│   └── layout.py        # Layout zones (full, sidebar, grid)
├── utils/
│   ├── __init__.py
│   └── sysinfo.py       # psutil collector with /proc fallback
└── tests/
    ├── test_config.py
    └── test_matrix.py
```

### Design Principles

- **Zone-based rendering** — Each mode defines rectangular zones; only matrix pixels in matrix zones get updated
- **psutil with /proc fallback** — Works with or without `psutil` installed
- **Frame-timed** — Deterministic frame timing via `time.monotonic()`
- **Anti burn-in** — Panel borders and dividers pulse colors every frame

## 📦 Requirements

- **Python 3.10+**
- **blessed** — Terminal fullscreen/cbreak/color management
- **psutil** — System info (optional, falls back to `/proc`)

## 🧪 Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check nukamatrix/ tests/

# Build package
python -m build
```

## 🆚 vs cmatrix

| Feature | cmatrix | PyMatrix |
|---------|---------|----------|
| Language | C | Python |
| Matrix Rain | ✅ | ✅ |
| Color Options | 8 | 7 + rainbow |
| Bold | ✅ | ✅ |
| Lambda Mode | ✅ | ✅ |
| System Info | ❌ | ✅ (5 panels) |
| Multi-Mode | ❌ | ✅ |
| Config File | ❌ | ✅ (INI) |
| Resize | ✅ | ✅ |
| Screensaver | ✅ | ✅ |

## 📜 License

[MIT License](LICENSE) — do whatever you want.

## 🙏 Credits

- **cmatrix** by Chris Allegretta — the original inspiration
- **blessed** library — terminal manipulation without curses boilerplate
- **psutil** — cross-platform system metrics

---

<p align="center">
  <em>"The Matrix has you..."</em> 🟢
</p>
