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


def _color(term, n: int, text: str = "") -> str:
    """Apply 256-color to text, or return callable."""
    if text:
        return term.color(n)(text)
    return term.color(n)


class SettingsMenu:
    """Interactive settings overlay menu.

    Usage:
        menu = SettingsMenu(config)
        save, needs_reinit = menu.run(term, frame)
        # save=True  → user pressed q (save config)
        # needs_reinit=True → charset/lambda changed → caller must reinit columns
    """

    PANEL_W = 34
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
        idx_v = values.index(getattr(self.config, key))
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
        c_border = term.color(_BORDER)
        c_header = term.color(_HEADER)
        c_label = term.color(_LABEL)
        c_arrow = term.color(_ARROW)
        c_footer = term.color(_FOOTER)
        c_sel_fg = term.color(_SELECTED_FG)
        c_sel_bg = term.color(_SELECTED_BG)
        c_val_bg = term.color(_VALUE_BG)

        # Border chars
        TL, TR = "┌", "┐"
        BL, BR = "└", "┘"
        H, V = "─", "│"
        MT, MB = "├", "┤"

        # Clear panel area
        for row in range(h):
            print(term.move_xy(ox, oy + row) + " " * w, end="")

        # Top border
        print(term.move_xy(ox, oy) + c_border(TL + H * (w - 2) + TR), end="")

        # Header
        label = "▸ Settings ◂"
        padding = w - 2 - len(label)
        pad_l = padding // 2
        pad_r = padding - pad_l
        hdr = c_border(V) + " " * pad_l + c_header(label) + " " * pad_r + c_border(V)
        print(term.move_xy(ox, oy + 1) + hdr, end="")

        # Separator
        print(term.move_xy(ox, oy + 2) + c_border(MT + H * (w - 2) + MB), end="")

        # Settings rows
        for i, setting in enumerate(ALL_SETTINGS):
            row_y = oy + 3 + i
            line_label = setting["label"]
            value_str = self._get_value(i)
            value_width = 9
            content_w = w - 6  # minus "│ " and " │"
            fill = content_w - len(line_label) - 1 - value_width - 2  # arrow + space + label + [ + value + ]

            if i == self._selected:
                # Selected: arrow + label + [value]
                arrow = c_arrow("▸")
                val_padded = value_str.center(value_width)
                val_display = c_sel_bg(c_sel_fg(val_padded))
                fill_sp = " " * max(0, fill)
                row_text = f" {arrow} {line_label} [{val_display}]{fill_sp}"
                # Print with highlighted row background
                row_clear = term.move_xy(ox + 1, row_y) + c_sel_bg(" " * (w - 3))
                print(row_clear, end="")
                print(term.move_xy(ox + 1, row_y) + row_text[:w - 3], end="")
                print(term.move_xy(ox, row_y) + c_border(V), end="")
            else:
                val_bg = c_val_bg(" " + value_str.center(value_width - 2) + " ")
                fill_sp = " " * max(0, fill)
                row_text = f"   {c_label(line_label)} {val_bg}{fill_sp}"
                # Ensure line doesn't overflow
                row_text = row_text[:content_w]
                print(term.move_xy(ox, row_y) + c_border(V) + row_text + c_border(V), end="")

        # Separator
        sep_y = oy + 3 + len(ALL_SETTINGS)
        print(term.move_xy(ox, sep_y) + c_border(MT + H * (w - 2) + MB), end="")

        # Footer
        footer1 = c_footer("↑↓ nav  ←→ adj  ")
        footer2 = c_footer("Enter toggle  q save  ")
        f_y = sep_y + 1
        print(term.move_xy(ox, f_y) + c_border(V) + footer1[:w - 2].ljust(w - 2) + c_border(V), end="")
        print(term.move_xy(ox, f_y + 1) + c_border(BL + H * (w - 2) + BR), end="")

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
            key = term.inkey(timeout=0.5)
            if not key:
                # Re-render for pulse effects even with no input
                self._render(term, frame)
                continue

            if key.lower() == "q":
                return (True, "charset" in self._dirty_fields or "lambda_mode" in self._dirty_fields)

            if key.code == term.KEY_ESCAPE:
                # Restore original values
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
        with open(config_path, "w") as f:
            cp.write(f)
