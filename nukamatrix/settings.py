"""Runtime settings menu overlay for NukaMatrix."""
from configparser import ConfigParser

from nukamatrix.config import Config

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
    PANEL_H = len(ALL_SETTINGS) + 6  # 13
    VAL_W = 9

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

    def _get_value(self, idx: int) -> str:
        s = ALL_SETTINGS[idx]
        val = getattr(self.config, s["key"])
        if s["type"] == "toggle":
            return "ON" if val else "OFF"
        return str(val)

    def _cycle_value(self, idx: int, direction: int = 1) -> None:
        values = ALL_SETTINGS[idx]["values"]
        key = ALL_SETTINGS[idx]["key"]
        current = getattr(self.config, key)
        try:
            idx_v = values.index(current)
        except ValueError:
            idx_v = 0
        idx_v = (idx_v + direction) % len(values)
        setattr(self.config, key, values[idx_v])
        self._dirty_fields.add(key)

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

    def _render(self, term, frame: int) -> None:
        w = self.PANEL_W
        h = self.PANEL_H
        ox = (term.width - w) // 2
        oy = (term.height - h) // 2
        iw = w - 2  # inner width between borders

        bdr = term.color(252)
        hdr = term.color(135)
        ftr = term.color(240)
        VT, HL = "\u2502", "\u2500"
        hline = HL * iw

        lines = []
        move = term.move_xy

        lines.append(move(ox, oy) + bdr("\u250c" + hline + "\u2510"))

        t = "\u25b8 Settings \u25c2"
        p = iw - len(t)
        pl, pr = p // 2, p - p // 2
        lines.append(move(ox, oy + 1) + bdr(VT) + " " * pl + hdr(t) + " " * pr + bdr(VT))

        lines.append(move(ox, oy + 2) + bdr("\u251c" + hline + "\u2524"))

        for i, s in enumerate(ALL_SETTINGS):
            val = self._get_value(i)
            vp = f"{val:^{self.VAL_W}}"

            if i == self._selected:
                t = f" \u25b8 {s['label']} [{vp}]"
                sel = term.bold(term.normal(term.color(15)(t)))
                fill = max(0, iw - len(t))
                content = sel + " " * fill
            else:
                t = f"   {s['label']}  {vp}"
                fill = max(0, iw - len(t))
                content = t + " " * fill

            lines.append(move(ox, oy + 3 + i) + bdr(VT) + content + bdr(VT))

        sep_y = oy + 3 + len(ALL_SETTINGS)
        lines.append(move(ox, sep_y) + bdr("\u251c" + hline + "\u2524"))

        ft = "\u2191\u2193 nav  \u2190\u2192 adj | 'q' SAVE  'ESC' cancel"
        content = ftr(ft) + " " * max(0, iw - len(ft))
        lines.append(move(ox, sep_y + 1) + bdr(VT) + content + bdr(VT))

        lines.append(move(ox, sep_y + 2) + bdr("\u2514" + hline + "\u2518"))

        # Force terminal to last line, then clear and print each row
        print(term.move_xy(0, term.height - h), end="")
        for line in lines:
            print(term.clear_eol, end="")
            print(line, end="\n")
        self._panel_bounds = (ox, oy, ox + w, oy + h)

    def run(self, term, frame: int) -> tuple:
        self._render(term, frame)
        while True:
            key = term.inkey(timeout=1.0)
            if key.lower() == "q":
                return (True, "charset" in self._dirty_fields or "lambda_mode" in self._dirty_fields)
            if key.code == term.KEY_ESCAPE:
                for k, v in self._snapshot.items():
                    setattr(self.config, k, v)
                self._dirty_fields.clear()
                return (False, False)
            actions = {
                term.KEY_DOWN:  (1,  0),
                term.KEY_UP:    (-1, 0),
                term.KEY_LEFT:  (0,  -1),
                term.KEY_RIGHT: (0,  1),
                term.KEY_ENTER: (0,  1),
            }
            if key.code in actions:
                ds, da = actions[key.code]
                if ds != 0:
                    self._selected = (self._selected + ds) % len(ALL_SETTINGS)
                if da != 0:
                    self._action(self._selected, delta=da)
                self._render(term, frame)

    def _action(self, idx: int, delta: int) -> None:
        if idx < 0 or idx >= len(ALL_SETTINGS):
            return
        s = ALL_SETTINGS[idx]
        if s["type"] == "cycle":
            self._cycle_value(idx, direction=delta)
        elif s["type"] == "range":
            self._adjust_range(idx, delta * max(1, s.get("step", 1)))
        elif s["type"] == "toggle":
            self._toggle_value(idx)

    def save_to_file(self) -> None:
        cp = ConfigParser()
        cp.add_section("display")
        for key in ["mode", "color", "charset", "speed", "fps", "bold", "rainbow", "lambda_mode"]:
            cp["display"][key] = str(getattr(self.config, key)).lower()
        import os
        try:
            with open(os.path.expanduser("~/.nukamatrix.conf"), "w") as f:
                cp.write(f)
        except OSError:
            pass
