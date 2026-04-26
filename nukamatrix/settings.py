"""Runtime settings menu overlay for NukaMatrix.

All colors use term.color(N) which works with any 256-color terminal.
"""

from configparser import ConfigParser

from nukamatrix.config import Config

# ── Color constants (256-color) ─────────────────────────────────
_BORDER = 252       # light gray
_HEADER = 135       # purple
_SELECTED_FG = 15   # white
_SELECTED_BG = 235  # dark gray
_LABEL = 245        # gray
_VALUE_BG = 234     # very dark gray
_ARROW = 255        # white
_FOOTER = 240       # dim gray

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
    """Interactive settings overlay menu.

    Usage:
        menu = SettingsMenu(config)
        save, needs_reinit = menu.run(term, frame)
        # save=True  → user pressed q (save config)
        # needs_reinit=True → charset/lambda changed → caller must reinit columns
    """

    PANEL_W = 36
    PANEL_H = len(ALL_SETTINGS) + 8  # header + border + footer + spacing

    def __init__(self, config: Config):
        self.config = config
        self._selected = 0  # index into ALL_SETTINGS
        # Snapshot for discard
        self._snapshot = {
            "color": config.color,
            "rainbow": config.rainbow,
            "speed": config.speed,
            "fps": config.fps,
            "charset": config.charset,
            "bold": config.bold,
            "lambda_mode": config.lambda_mode,
        }
        self._dirty_fields = set()

    # ── Value Helpers ───────────────────────────────────────────

    def _get_value(self, idx: int) -> str:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        val = getattr(self.config, key)
        if s["type"] == "toggle":
            return " ON " if val else " OFF "
        if s["type"] == "cycle":
            return f" {val} "
        if s["type"] == "range":
            return f" {val:>3} "
        return str(val)

    def _cycle_value(self, idx: int, direction: int = 1) -> None:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        values = s["values"]
        current_val = getattr(self.config, key)
        # Defensive: if value isn't in list (bad config file), start from 0
        try:
            idx_v = values.index(current_val)
        except ValueError:
            idx_v = 0
        idx_v = (idx_v + direction) % len(values)
        setattr(self.config, key, values[idx_v])
        self._dirty_fields.add(key)

    def _toggle_value(self, idx: int) -> None:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        setattr(self.config, key, not getattr(self.config, key))
        self._dirty_fields.add(key)

    def _adjust_range(self, idx: int, delta: int) -> None:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        val = getattr(self.config, key) + delta
        val = max(s["min"], min(s["max"], val))
        setattr(self.config, key, val)
        self._dirty_fields.add(key)

    # ── Render ──────────────────────────────────────────────────

    def _render(self, term, frame: int) -> None:
        w = self.PANEL_W
        h = self.PANEL_H
        ox = (term.width - w) // 2
        oy = (term.height - h) // 2
        b = term.color(_BORDER)
        hd = term.color(_HEADER)
        lb = term.color(_LABEL)
        ar = term.color(_ARROW)
        ft = term.color(_FOOTER)
        sf = term.color(_SELECTED_FG)
        sb = term.color(_SELECTED_BG)
        vb = term.color(_VALUE_BG)
        V = "│"

        # Build each line of the panel
        lines = []

        # Line 0: ┌─────┐
        lines.append(term.move_xy(ox, oy) + b("┌" + "─" * (w - 2) + "┐"))

        # Line 1: │  ▸ Settings ◂  │
        label = "▸ Settings ◂"
        pad = w - 2 - len(label)
        pl, pr = pad // 2, pad - pad // 2
        lines.append(term.move_xy(ox, oy + 1) + b(V) + " " * pl + hd(label) + " " * pr + b(V))

        # Line 2: ├─────┤
        lines.append(term.move_xy(ox, oy + 2) + b("├" + "─" * (w - 2) + "┤"))

        # Lines 3+: settings
        for i, setting in enumerate(ALL_SETTINGS):
            row_y = oy + 3 + i
            vl = setting["label"]
            vs = self._get_value(i)
            vw = 9
            content_w = w - 3  # inner width between │ borders

            if i == self._selected:
                val_display = sb(sf(vs.center(vw)))
                # ▸ Color [  green  ]
                # prefix: " ▸ " (3) + label + " [" (2) + value (9) + "]" (1)
                prefix = f" {ar('▸')} {vl} ["
                suffix = "]"
                remaining = max(0, content_w - len(prefix) - vw - len(suffix))
                row_inner = prefix + val_display + suffix + " " * remaining
                row_inner = row_inner[:content_w]
            else:
                val_bg = vb(" " + vs.center(vw - 2) + " ")
                prefix = f"   {lb(vl)} "
                remaining = max(0, content_w - len(prefix) - (vw - 2))
                row_inner = prefix + val_bg + " " * remaining
                row_inner = row_inner[:content_w]

            lines.append(term.move_xy(ox, row_y) + b(V) + row_inner + b(V))

        # Separator
        sep_y = oy + 3 + len(ALL_SETTINGS)
        lines.append(term.move_xy(ox, sep_y) + b("├" + "─" * (w - 2) + "┤"))

        # Footer
        footer_text = ft("\u2191\u2193 nav  \u2190\u2192 adj  ")[:w - 2].ljust(w - 2)
        f_y = sep_y + 1
        lines.append(term.move_xy(ox, f_y) + b(V) + footer_text + b(V))

        # Bottom border
        lines.append(term.move_xy(ox, f_y + 1) + b("└" + "─" * (w - 2) + "┘"))

        # Clear panel area first (each row at correct position), then render
        # Use single print to avoid I/O overhead
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
            (save, needs_reinit):
                save=True if user chose to save config
                needs_reinit=True if charset/lambda changed → columns must be rebuilt
        """
        self._render(term, frame)

        while True:
            # timeout — no idle re-render
            key = term.inkey(timeout=1.0)

            if key.lower() == "q":
                return (True, "charset" in self._dirty_fields or "lambda_mode" in self._dirty_fields)

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
        """Apply an action (adjust/toggle/cycle) on the selected setting."""
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
        """Write current config to the default config file (~/.nukamatrix.conf)."""
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
            pass  # Config not saved — in-memory settings still active
