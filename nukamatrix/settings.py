"""Runtime settings menu overlay for NukaMatrix."""

from blessed import Terminal

from configparser import ConfigParser

from nukamatrix.config import Config

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
        if s["type"] in ("cycle", "toggle"):
            if s["type"] == "toggle":
                return " ON " if val else " OFF "
            return f" {val} "
        elif s["type"] == "range":
            return f" {val:>3} "
        return str(val)

    def _cycle_value(self, idx: int, direction: int = 1) -> None:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        values = s["values"]
        idx_v = values.index(getattr(self.config, key))
        idx_v = (idx_v + direction) % len(values)
        new_val = values[idx_v]
        setattr(self.config, key, new_val)
        self._dirty_fields.add(key)

    def _toggle_value(self, idx: int) -> None:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        val = not getattr(self.config, key)
        setattr(self.config, key, val)
        self._dirty_fields.add(key)

    def _adjust_range(self, idx: int, delta: int) -> None:
        s = ALL_SETTINGS[idx]
        key = s["key"]
        val = getattr(self.config, key) + delta
        val = max(s["min"], min(s["max"], val))
        setattr(self.config, key, val)
        self._dirty_fields.add(key)

    # ── Render ──────────────────────────────────────────────────

    def _render(self, term: Terminal, frame: int) -> None:
        w = self.PANEL_W
        h = self.PANEL_H
        ox = (term.width - w) // 2
        oy = (term.height - h) // 2

        border_c = term.bright_white
        header_c = term.bright_magenta
        footer_c = term.dim
        selected_bg = term.black
        selected_fg = term.bright_white

        # Clear panel area
        for row in range(h):
            print(term.move_xy(ox, oy + row) + " " * w, end="")

        # Top border
        top = border_c("┌") + border_c("─") * (w - 2) + border_c("┐")
        print(term.move_xy(ox, oy) + top, end="")

        # Header
        label = " Settings "
        left = (w - 2 - len(label)) // 2
        right = w - 2 - len(label) - left
        header = border_c("│") + " " * left + header_c(label) + " " * right + border_c("│")
        print(term.move_xy(ox, oy + 1) + header, end="")

        # Separator
        sep = border_c("├") + border_c("─") * (w - 2) + border_c("┤")
        print(term.move_xy(ox, oy + 2) + sep, end="")

        # Settings rows
        for i, setting in enumerate(ALL_SETTINGS):
            row_y = oy + 3 + i
            line_label = f"  {setting['label']}"
            value_str = self._get_value(i)
            value_width = 9
            fill = w - 6 - len(line_label) - value_width
            if i == self._selected:
                val_display = selected_bg(selected_fg(value_str.center(value_width)))
                fill_spaces = ' ' * fill
                arrow = term.white('▸')
                lbl = term.bold(header_c(line_label))
                line = f" {arrow} {lbl} [{val_display}]{fill_spaces}"
            else:
                val_bg = footer_c(' ' + term.color(234)(value_str.center(value_width)) + ' ')
                fill_spaces = ' ' * fill
                lbl_dim = term.color(245)(line_label)
                line = f"   {lbl_dim} {val_bg}{fill_spaces}"
            # Ensure line doesn't overflow
            line = line[:w - 2]
            print(term.move_xy(ox, row_y) + border_c("│") + line + border_c("│"), end="")

        # Separator
        sep2 = border_c("├") + border_c("─") * (w - 2) + border_c("┤")
        print(term.move_xy(ox, oy + 3 + len(ALL_SETTINGS)) + sep2, end="")

        # Footer
        footer1 = border_c("│") + f"  ↑↓ nav  ←→ adj  ".ljust(w - 2) + border_c("│")
        footer2 = border_c("│") + f"  Enter toggle  q save".ljust(w - 2) + border_c("│")

        # Bottom border
        bot = border_c("└") + border_c("─") * (w - 2) + border_c("┘")
        bot_y = oy + 3 + len(ALL_SETTINGS) + 2
        print(term.move_xy(ox, bot_y - 2) + footer_c(footer1), end="")
        print(term.move_xy(ox, bot_y - 1) + footer_c(footer2), end="")
        print(term.move_xy(ox, bot_y) + bot, end="")

        # Store computed panel bounds for cursor hiding
        self._panel_bounds = (ox, oy, ox + w, oy + h)

    # ── Input / Loop ────────────────────────────────────────────

    def run(self, term: Terminal, frame: int) -> tuple[bool, bool]:
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

            if self._selected == 0:  # Color — ↑↓ cycles through colors
                if key.code == term.KEY_DOWN:
                    self._selected = (self._selected + 1) % len(ALL_SETTINGS)
                    self._render(term, frame)
                elif key.code == term.KEY_UP:
                    self._selected = (self._selected - 1) % len(ALL_SETTINGS)
                    self._render(term, frame)
                elif key.code in (term.KEY_LEFT,):
                    self._cycle_value(self._selected, direction=-1)
                    self._render(term, frame)
                elif key.code in (term.KEY_RIGHT,):
                    self._cycle_value(self._selected, direction=1)
                    self._render(term, frame)
                elif key.code == term.KEY_ENTER:
                    # Also accept Enter for cycling in cycle type
                    self._cycle_value(self._selected, direction=1)
                    self._render(term, frame)
            else:
                current = ALL_SETTINGS[self._selected]
                if key.code == term.KEY_DOWN:
                    self._selected = (self._selected + 1) % len(ALL_SETTINGS)
                    self._render(term, frame)
                elif key.code == term.KEY_UP:
                    self._selected = (self._selected - 1) % len(ALL_SETTINGS)
                    self._render(term, frame)
                elif key.code == term.KEY_LEFT:
                    if current["type"] == "cycle":
                        self._cycle_value(self._selected, direction=-1)
                    elif current["type"] == "range":
                        self._adjust_range(self._selected, delta=-current.get("step", 1))
                    elif current["type"] == "toggle":
                        self._toggle_value(self._selected)
                    self._render(term, frame)
                elif key.code == term.KEY_RIGHT:
                    if current["type"] == "cycle":
                        self._cycle_value(self._selected, direction=1)
                    elif current["type"] == "range":
                        self._adjust_range(self._selected, delta=current.get("step", 1))
                    elif current["type"] == "toggle":
                        self._toggle_value(self._selected)
                    self._render(term, frame)
                elif key.code == term.KEY_ENTER:
                    if current["type"] == "toggle":
                        self._toggle_value(self._selected)
                    elif current["type"] == "cycle":
                        self._cycle_value(self._selected, direction=1)
                    self._render(term, frame)

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
        # Write to flat file in home — no makedirs needed for ~/.file
        with open(config_path, "w") as f:
            cp.write(f)
