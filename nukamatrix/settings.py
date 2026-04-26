"""Runtime settings menu overlay for NukaMatrix.

All colors use term.color(N) which works with any 256-color terminal.
"""

from configparser import ConfigParser

from nukamatrix.config import Config

# ── Color constants (256-color) ─────────────────────────────────
_BORDER = 252       # light gray
_HEADER = 135       # purple
_VALUE_TEXT = 15    # white (always visible on any bg)
_SELECTED_FG = 15   # white for selected row text
_LABEL = 188        # light gray
_ARROW = 255        # white
_FOOTER = 240       # dim gray

# ── Unicode constants ───────────────────────────────────────────
_UP = "\u2191"
_DOWN = "\u2193"
_LEFT = "\u2190"
_RIGHT = "\u2192"
_VBAR = "\u2502"
_ARROW_CHAR = "\u25b8"

# ── Settings Row Definition ──────────────────────────────────────

ALL_SETTINGS = [
    {"key": "color",        "label": "Color",       "type": "cycle", "values": ["green", "red", "blue", "cyan", "magenta", "yellow", "white"]},
    {"key": "rainbow",      "label": "Rainbow",     "type": "toggle"},
    {"key": "speed",        "label": "Speed",       "type": "range",  "min": 0, "max": 10, "step": 1},
    {"key": "fps",          "label": "FPS",         "type": "range",  "min": 15, "max": 60, "step": 5},
    {"key": "charset",      "label": "Charset",     "type": "cycle", "values": ["ascii", "kana", "mixed"]},
    {"key": "bold",         "label": "Bold",        "type": "toggle"},
    {"key": "lambda_mode",  "label": "Lambda mode", "type": "toggle"},
]


class SettingsMenu:
    """Interactive settings overlay menu."""

    PANEL_W = 36
    PANEL_H = len(ALL_SETTINGS) + 8  # 7 settings + header(2) + sep(2) + footer(1) + bottom(1)

    def __init__(self, config: Config):
        self.config = config
        self._selected = 0
        self._snapshot = {
            "color": config.color, "rainbow": config.rainbow,
            "speed": config.speed, "fps": config.fps,
            "charset": config.charset, "bold": config.bold,
            "lambda_mode": config.lambda_mode,
        }
        self._dirty_fields = set()

    # ── Value Helpers ───────────────────────────────────────────

    def _get_value(self, idx: int) -> str:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        val = getattr(self.config, key)
        if s["type"] == "toggle":
            return "ON" if val else "OFF"
        if s["type"] == "cycle":
            return val
        if s["type"] == "range":
            return str(val)
        return str(val)

    def _cycle_value(self, idx: int, direction: int = 1) -> None:
        s = ALL_SETTINGS[idx]
        values = s["values"]
        current = getattr(self.config, s["key"])
        try:
            idx_v = values.index(current)
        except ValueError:
            idx_v = 0
        idx_v = (idx_v + direction) % len(values)
        setattr(self.config, s["key"], values[idx_v])
        self._dirty_fields.add(s["key"])

    def _toggle_value(self, idx: int) -> None:
        key = ALL_SETTINGS[idx]["key"]
        setattr(self.config, key, not getattr(self.config, key))
        self._dirty_fields.add(key)

    def _adjust_range(self, idx: int, delta: int) -> None:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        val = max(s["min"], min(s["max"], getattr(self.config, key) + delta))
        setattr(self.config, key, val)
        self._dirty_fields.add(key)

    # ── Render ──────────────────────────────────────────────────

    def _render(self, term, frame: int) -> None:
        w = self.PANEL_W
        h = self.PANEL_H
        ox = (term.width - w) // 2
        oy = (term.height - h) // 2
        bdr = term.color(_BORDER)
        hdr = term.color(_HEADER)
        lbl = term.color(_LABEL)
        val = term.color(_VALUE_TEXT)
        ftr = term.color(_FOOTER)
        sf = term.color(_SELECTED_FG)
        arw = term.color(_ARROW)
        V = _VBAR

        lines = []

        # ── Top border ──
        top = bdr("\u250c" + "\u2500" * (w - 2) + "\u2510")
        lines.append(term.move_xy(ox, oy) + top)

        # ── Header ──
        label = "\u25b8 Settings \u25c2"
        pad = w - 2 - len(label)
        pl, pr = pad // 2, pad - pad // 2
        lines.append(term.move_xy(ox, oy + 1) + bdr(V) + " " * pl + hdr(label) + " " * pr + bdr(V))

        # ── Separator ──
        lines.append(term.move_xy(ox, oy + 2) + bdr("\u251c" + "\u2500" * (w - 2) + "\u2524"))

        # ── Settings rows ──
        inner_w = w - 3  # between vertical bars
        for i, setting in enumerate(ALL_SETTINGS):
            row_y = oy + 3 + i
            vl = setting["label"]
            vs = self._get_value(i)
            vs_w = max(len(vs), 3)  # minimum 3 chars wide

            if i == self._selected:
                # Selected row: highlighted
                val_str = sf(f" {vs:^{vs_w+2}} ")
                # Right-pad spaces to fill
                raw = f" {arw(_ARROW_CHAR)} {term.bold(vl)} [{val_str}]"
                # Compute visible width (without escape codes)
                plain_len = len(f"  {_ARROW_CHAR}  {vl} [ {' '*(vs_w+2)} ]")
                fill = max(0, inner_w - plain_len)
                row_inner = raw + " " * fill
            else:
                # Normal row
                val_str = val(f" {vs:^{vs_w+2}} ")
                row_inner = f"   {lbl(vl)} {val_str} " + " " * max(0, inner_w - (4 + len(vl) + 1 + (vs_w + 2) + 1))

            row_inner = row_inner[:inner_w]
            lines.append(term.move_xy(ox, row_y) + bdr(V) + row_inner + bdr(V))

        # ── Second separator ──
        sep_y = oy + 3 + len(ALL_SETTINGS)
        lines.append(term.move_xy(ox, sep_y) + bdr("\u251c" + "\u2500" * (w - 2) + "\u2524"))

        # ── Footer ──
        footer_text = ftr(f"{_UP}{_DOWN} nav  {_LEFT}{_RIGHT} adj  ")[:inner_w].ljust(inner_w)
        lines.append(term.move_xy(ox, sep_y + 1) + bdr(V) + footer_text + bdr(V))

        # ── Bottom border ──
        lines.append(term.move_xy(ox, sep_y + 2) + bdr("\u2514" + "\u2500" * (w - 2) + "\u2518"))

        # ── Clear area + render in one print ──
        output = []
        for row in range(h):
            output.append(term.move_xy(ox, oy + row) + " " * w)
        output.extend(lines)
        print("\n".join(output), end="")

        self._panel_bounds = (ox, oy, ox + w, oy + h)

    # ── Input / Loop ────────────────────────────────────────────

    def run(self, term, frame: int) -> tuple:
        """Run the settings menu event loop.

        Returns:
            (save, needs_reinit): save=True → save config,
            needs_reinit=True → charset/lambda changed, reinit columns
        """
        self._render(term, frame)

        while True:
            key = term.inkey(timeout=1.0)

            if key.lower() == "q":
                return (True,
                        "charset" in self._dirty_fields or
                        "lambda_mode" in self._dirty_fields)

            if key.code == term.KEY_ESCAPE:
                for k, v in self._snapshot.items():
                    setattr(self.config, k, v)
                self._dirty_fields.clear()
                return (False, False)

            if key.code == term.KEY_DOWN:
                self._selected = (self._selected + 1) % len(ALL_SETTINGS)
                self._render(term, frame)
            elif key.code == term.KEY_UP:
                self._selected = (self._selected - 1) % len(ALL_SETTINGS)
                self._render(term, frame)
            elif key.code == term.KEY_LEFT:
                self._action(self._selected, delta=-1)
                self._render(term, frame)
            elif key.code == term.KEY_RIGHT:
                self._action(self._selected, delta=1)
                self._render(term, frame)
            elif key.code == term.KEY_ENTER:
                self._action(self._selected, delta=1)
                self._render(term, frame)

    def _action(self, idx: int, delta: int) -> None:
        """Apply action on selected setting."""
        if idx < 0 or idx >= len(ALL_SETTINGS):
            return
        current = ALL_SETTINGS[idx]
        t = current["type"]
        if t == "cycle":
            self._cycle_value(idx, direction=delta)
        elif t == "range":
            step = max(1, current.get("step", 1))
            self._adjust_range(idx, delta=delta * step)
        elif t == "toggle":
            self._toggle_value(idx)

    # ── Config Saving ───────────────────────────────────────────

    def save_to_file(self) -> None:
        """Write current config to ~/.nukamatrix.conf."""
        cp = ConfigParser()
        cp.add_section("display")
        cp["display"]["mode"] = self.config.mode
        cp["display"]["color"] = self.config.color
        cp["display"]["charset"] = self.config.charset
        cp["display"]["speed"] = str(self.config.speed)
        cp["display"]["fps"] = str(self.config.fps)
        cp["display"]["bold"] = str(self.config.bold).lower()
        cp["display"]["rainbow"] = str(self.config.rainbow).lower()
        cp["display"]["lambda_mode"] = str(self.config.lambda_mode).lower()

        import os
        config_path = os.path.expanduser("~/.nukamatrix.conf")
        try:
            with open(config_path, "w") as f:
                cp.write(f)
        except OSError:
            pass  # In-memory settings still active
