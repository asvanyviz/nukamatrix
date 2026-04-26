"""Abstract panel base + border rendering."""

from blessed import Terminal
from abc import ABC, abstractmethod


class PanelBorder:
    """Border style configuration."""
    # Single-line borders
    TL = "┌"
    TR = "┐"
    BL = "└"
    BR = "┘"
    H = "─"
    V = "│"


class Panel(ABC):
    """Base class for renderable panels.

    Each panel occupies a rectangular region (x, y, w, h) and renders
    its content inside borders.

    Anti burn-in: every frame the panel varies its color/border slightly.
    """

    def __init__(self, x: int, y: int, width: int, height: int, title: str = ""):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.title = title

    @abstractmethod
    def render(self, term: Terminal, frame: int):
        """Render the panel at its position.

        Args:
            term: blessed Terminal instance
            frame: current frame counter (for animation/pulsing)
        """
        ...

    def _render_border(self, term: Terminal, frame: int) -> list[str]:
        """Render panel border with animated color.

        Returns lines that should be placed at panel position.
        """
        # Color pulsing based on frame
        color_idx = (frame // 30) % 3  # cycle every 30 frames
        if color_idx == 0:
            border_attr = term.green
        elif color_idx == 1:
            border_attr = term.cyan
        else:
            border_attr = term.color(33)  # yellow-ish

        b = PanelBorder
        w = self.width
        inner_w = w - 2
        lines = []

        # Top border
        top = b.TL + border_attr(b.H * (inner_w - len(self.title) - 2))
        if self.title:
            top += f" {self.title} "
            top += border_attr(b.H * max(0, inner_w - len(self.title) - 4))
        else:
            top += border_attr(b.H * max(0, inner_w - 2))
        top += b.TR
        lines.append(top)

        # Middle rows (content area, to be filled by subclass)
        mid_attr = border_attr  # keep same border color for vertical lines
        for i in range(self.height - 2):
            lines.append(mid_attr(b.V) + " " * inner_w + mid_attr(b.V))

        # Bottom border
        lines.append(b.BL + border_attr(b.H * (w - 2)) + b.BR)

        return lines

    def _content_lines(self, term: Terminal, frame: int) -> list[str]:
        """Override in subclass to provide inner content lines.

        Each string should be inner_w characters wide.
        Must return exactly (height - 2) lines.
        """
        return [" " * (self.width - 2)] * max(0, self.height - 2)

    def _full_render(self, term: Terminal, frame: int):
        """Combine border + content into final output line list."""
        b = PanelBorder
        w = self.width
        inner_w = w - 2

        # Determine border color (pulsing)
        color_idx = (frame // 30) % 3
        if color_idx == 0:
            border_attr = term.green
        elif color_idx == 1:
            border_attr = term.cyan
        else:
            border_attr = term.color(33)

        lines = []

        # Top border with title
        inner_label = f" {self.title} "
        label_len = len(inner_label)
        left_pad = (inner_w - label_len) // 2
        right_pad = inner_w - label_len - left_pad
        top = b.TL + " " * left_pad + inner_label + " " * right_pad + b.TR
        # Colorize the border chars
        top_colored = border_attr(b.TL) + " " * left_pad + inner_label + " " * right_pad + border_attr(b.TR)
        lines.append(top_colored)

        # Content rows
        content = self._content_lines(term, frame)
        for i, c in enumerate(content):
            if i >= self.height - 2:
                break
            padded = c.ljust(inner_w)[:inner_w]
            row = border_attr(b.V) + padded + border_attr(b.V)
            lines.append(row)

        # Fill remaining rows if content was short
        remaining = (self.height - 2) - len(content)
        for _ in range(remaining):
            lines.append(border_attr(b.V) + " " * inner_w + border_attr(b.V))

        # Bottom border
        lines.append(border_attr(b.BL) + border_attr(b.H * (w - 2)) + border_attr(b.BR))

        return lines
