"""Layout manager for panel positioning and resizing."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LayoutZone:
    """A rectangular zone in the terminal grid.

    Coordinates are in characters (not pixels).
    """
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def clamp(self, max_width: int, max_height: int) -> "LayoutZone":
        """Ensure zone fits within terminal bounds."""
        x = max(0, min(self.x, max_width - self.width))
        y = max(0, min(self.y, max_height - self.height))
        w = min(self.width, max_width - x)
        h = min(self.height, max_height - y)
        return LayoutZone(x, y, w, h)


@dataclass
class LayoutDefinition:
    """Defines how the screen is divided into zones."""
    zones: list[LayoutZone]
    # Zone assignments (e.g. "matrix", "cpu", "mem", "disk", "net", "clock")
    assignments: list[str]  # parallel to zones


def layout_full_matrix(term_w: int, term_h: int) -> LayoutDefinition:
    """Full-screen matrix rain zone."""
    return LayoutDefinition(
        zones=[LayoutZone(0, 0, term_w, term_h)],
        assignments=["matrix"],
    )


def layout_matrix_sidebar(term_w: int, term_h: int, sidebar_ratio: float = 0.30) -> LayoutDefinition:
    """Matrix on left, vertical sidebar of panels on right.

    Matrix takes ~70% left, sidebar ~30% right with panels stacked vertically.
    """
    split_x = int(term_w * (1 - sidebar_ratio))

    zone_matrix = LayoutZone(0, 0, split_x, term_h)

    sidebar_w = term_w - split_x
    num_panels = 5  # cpu, mem, disk, net, clock
    # Minimum panel height
    min_h = 5
    panel_h = max(min_h, term_h // num_panels)

    zones = [zone_matrix]
    assignments = ["matrix"]

    y = 0
    for panel_name in ["cpu", "mem", "disk", "net", "clock"]:
        if y + panel_h > term_h:
            break
        zones.append(LayoutZone(split_x, y, sidebar_w, panel_h))
        assignments.append(panel_name)
        y += panel_h

    return LayoutDefinition(zones=zones, assignments=assignments)


def layout_quarter_grid(term_w: int, term_h: int) -> LayoutDefinition:
    """2×2 quadrant grid — all four quadrants show system info."""
    half_w = term_w // 2
    half_h = term_h // 2

    return LayoutDefinition(
        zones=[
            LayoutZone(0, 0, half_w, half_h),         # top-left
            LayoutZone(half_w, 0, term_w - half_w, half_h),  # top-right
            LayoutZone(0, half_h, half_w, term_h - half_h),  # bottom-left
            LayoutZone(half_w, half_h, term_w - half_w, term_h - half_h),  # bottom-right
        ],
        assignments=["cpu", "mem", "disk", "net"],
    )


def layout_matrix_bottom(term_w: int, term_h: int, bottom_ratio: float = 0.30) -> LayoutDefinition:
    """Matrix on top, horizontal panel strip on bottom."""
    split_y = int(term_h * (1 - bottom_ratio))

    zone_matrix = LayoutZone(0, 0, term_w, split_y)

    bottom_h = term_h - split_y
    panel_w = max(20, term_w // 4)
    zones = [zone_matrix]
    assignments = ["matrix"]

    x = 0
    for panel_name in ["cpu", "mem", "disk", "net"]:
        if x + panel_w > term_w:
            break
        actual_w = min(panel_w, term_w - x)
        zones.append(LayoutZone(x, split_y, actual_w, bottom_h))
        assignments.append(panel_name)
        x += actual_w

    return LayoutDefinition(zones=zones, assignments=assignments)


def layout_custom(term_w: int, term_h: int, custom_zones: Optional[list[LayoutZone]] = None,
                   assignments: Optional[list[str]] = None) -> LayoutDefinition:
    """Custom user-defined layout. Falls back to quadrant grid."""
    if custom_zones and assignments and len(custom_zones) == len(assignments):
        return LayoutDefinition(zones=custom_zones, assignments=assignments)
    return layout_quarter_grid(term_w, term_h)
