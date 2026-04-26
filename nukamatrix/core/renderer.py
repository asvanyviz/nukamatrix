"""Renderer — blessed terminal rendering layer for PyMatrix.

Translates the 2D cell grid into blessed terminal output with proper
color handling (green shades, white head, rainbow cycling).

Supports zone rendering: only render a rectangular sub-region of the grid.
"""

from blessed import Terminal

from nukamatrix.config import Config
from nukamatrix.core.matrix import Cell


class Renderer:
    """Renders a 2D cell grid to a blessed fullscreen terminal."""

    def __init__(self, term: Terminal, config: Config):
        self.term = term
        self.config = config
        self._frame = 0

        # Zone rendering support
        self.zone_x = 0
        self.zone_y = 0
        self.zone_w = 0
        self.zone_h = 0

    # ── Color helpers ───────────────────────────────────────────

    def _trail_color(self, age: int, max_age: int = 15):
        """Return a color attribute for a trail character based on its age.

        Age 0 = freshly written (bright), higher = dimmer → fades to nothing.
        Returns a bounded callable that can wrap a character string.
        """
        normalized = min(age / max_age, 1.0)

        # 4-tier fade: bright → normal → dark → dimmest
        if normalized < 0.25:
            attr = self.term.bright_green
        elif normalized < 0.5:
            attr = self.term.green
        elif normalized < 0.75:
            attr = self.term.color(22)  # dark green from 256-color palette
        else:
            # Very old trail — near-invisible
            attr = self.term.color(232)

        return attr

    def _head_color(self):
        """Head is always white (bold/bright)."""
        if self.config.rainbow:
            return self._rainbow_attr(0)
        if self.config.bold:
            # Return a callable that wraps text: bold(bright_white(text))
            return lambda ch: self.term.bold(self.term.bright_white(ch))
        return self.term.bright_white

    def _rainbow_attr(self, offset: int = 0):
        """Rainbow color cycling based on frame and position offset."""
        colors = [
            self.term.red,
            self.term.yellow,
            self.term.bright_green,
            self.term.cyan,
            self.term.blue,
            self.term.magenta,
        ]
        idx = (self._frame + offset) % len(colors)
        return colors[idx]

    # ── Main render ─────────────────────────────────────────────

    def clear(self):
        """Clear the entire screen."""
        print(self.term.clear, end="")

    def render(self, grid: list[list[Cell]], frame: int):
        """Render the cell grid to the terminal in a single frame.

        Uses a single print call per frame for minimum terminal I/O.
        Each row is built as a colored string, then cursor homes and dumps.

        Args:
            grid: 2D cell grid [row][col]
            frame: current frame number (for color cycling)
        """
        self._frame = frame
        rows = len(grid)
        if rows == 0:
            return
        cols = len(grid[0])

        # Build full-screen frame buffer as list of row strings
        output_lines = []
        for row_idx in range(rows):
            line_parts = []
            for col_idx in range(cols):
                cell = grid[row_idx][col_idx]
                if cell.is_empty or cell.is_space or cell.value < 0:
                    line_parts.append(" ")
                    continue

                ch = chr(cell.value)
                age = frame - cell.generation

                if cell.is_head:
                    attr = self._head_color()
                else:
                    if self.config.rainbow:
                        attr = self._rainbow_attr(row_idx + col_idx)
                    else:
                        attr = self._trail_color(age)

                try:
                    line_parts.append(attr(ch))
                except (TypeError, AttributeError):
                    # Fallback if blessed color call fails
                    line_parts.append(ch)

            output_lines.append("".join(line_parts))

        # Cursor home + print all lines in one shot
        print(self.term.move_xy(0, 0) + "\n".join(output_lines), end="")

    def render_zone(self, grid: list[list[Cell]], frame: int,
                    ox: int, oy: int, w: int, h: int):
        """Render only a rectangular sub-zone of the grid.

        This is the key method for multi-mode: matrix rain renders only
        to its assigned zone (e.g. left 70% of screen), leaving the
        right side for panels.

        Args:
            grid: 2D cell grid [row][col]
            frame: current frame number
            ox: zone offset x (column start)
            oy: zone offset y (row start)
            w: zone width in columns
            h: zone height in rows
        """
        self._frame = frame

        # Build output line by line for the zone
        for row_idx in range(oy, oy + h):
            if row_idx >= len(grid):
                break
            line_parts = []
            for col_idx in range(ox, ox + w):
                if col_idx >= len(grid[row_idx]):
                    line_parts.append(" ")
                    continue

                cell = grid[row_idx][col_idx]
                if cell.is_empty or cell.is_space or cell.value < 0:
                    line_parts.append(" ")
                    continue

                ch = chr(cell.value)
                age = frame - cell.generation

                if cell.is_head:
                    attr = self._head_color()
                else:
                    if self.config.rainbow:
                        attr = self._rainbow_attr(row_idx + col_idx)
                    else:
                        attr = self._trail_color(age)

                try:
                    line_parts.append(attr(ch))
                except (TypeError, AttributeError):
                    line_parts.append(ch)

            line = "".join(line_parts)
            # Print this zone row at the correct terminal position
            print(self.term.move_xy(ox, row_idx) + line, end="")
