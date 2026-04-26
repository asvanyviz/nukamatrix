"""Matrix rain data model — cmatrix 2D grid port to Python."""

from dataclasses import dataclass, field
import random
from typing import Optional

# Sentinel value meaning "no active stream"
_NO_STREAM = -999


# ── Cell ────────────────────────────────────────────────────────

@dataclass(slots=True)
class Cell:
    """Single terminal cell — mirrors cmatrix `cmatrix` struct.

    Attributes:
        value:      Character to display (-1 = empty, 0 = blank space, >0 = char code)
        is_head:    True if this cell is the leading edge of a stream
        generation: Frame counter when cell was last changed (used for trail fade)
    """
    value: int = -1
    is_head: bool = False
    generation: int = 0

    @property
    def is_empty(self) -> bool:
        return self.value == -1

    @property
    def is_space(self) -> bool:
        return self.value == 0


# ── Column ─────────────────────────────────────────────────────

class Column:
    """Manages rain-state for a single screen column.

    Each column has its own:
    - stream_length: how many visible characters in the trail
    - spaces_left: countdown before a new stream spawns
    - update_interval: how often this column updates (1-3, randomized like cmatrix)
    - head_row: current row of the stream head (_NO_STREAM means no active stream)
    - speed: per-column speed multiplier for natural variation

    Zone support: when a column belongs to a zone (e.g. left portion of screen),
    `base_row` marks the zone's top offset and `zone_h` is the zone height.
    Streams spawn relative to the zone (above zone top) and die below zone bottom.
    """

    def __init__(
        self,
        col_index: int,
        max_rows: int,
        charset: str,
        base_interval: int = 2,
        base_row: int = 0,
        zone_h: int = 0,
    ):
        self.col_index = col_index
        self.max_rows = max_rows
        self.charset = charset
        self.base_row = base_row  # zone top row offset in global grid
        self.zone_h = zone_h or max_rows  # zone height

        # Stream state
        self.spaces_left: int = random.randint(0, self.zone_h)
        self.stream_length: int = random.randint(3, self.zone_h)
        self.head_row: int = _NO_STREAM
        self.update_interval: int = max(1, random.randint(1, base_interval))

        # Speed variation: each column rolls its own dice
        self.speed = random.uniform(0.5, 1.5)

        # Internal tick counter
        self._tick = 0

    @property
    def has_stream(self) -> bool:
        """True if a stream is active (even if head is off-screen above zone)."""
        return self.head_row != _NO_STREAM

    def tick(self, frame: int) -> bool:
        """Advance one frame. Returns True if this column should update."""
        self._tick += 1
        return self._tick >= self.update_interval

    def update(self, frame: int, grid: list[list[Cell]]):
        """Update column state for one step. Must only be called when tick() == True.

        This follows cmatrix logic:
        1. If no active stream and spaces_left > 0 → decrement delay counter
        2. If no active stream and spaces_left == 0 → spawn new stream above zone
        3. If active stream → advance head, write characters
        4. If stream reaches zone bottom → reset with new randomized parameters
        """
        # Count down spaces_left until a new stream can start
        if self.spaces_left > 0 and not self.has_stream:
            self.spaces_left -= 1
            return

        # Spawn new stream above visible zone area (negative row = off-screen above zone)
        if not self.has_stream:
            self.head_row = self.base_row + random.randint(-5, -1)
            self.stream_length = random.randint(3, self.zone_h)
            return

        # Advance head
        old_head = self.head_row
        self.head_row += int(round(self.speed))

        # Clear old head marker (it becomes body if it was in-zone)
        if 0 <= old_head < self.max_rows:
            grid[old_head][self.col_index].is_head = False

        # If head moved from off-zone-top onto visible area, write first head cell
        if old_head < self.base_row and self.base_row <= self.head_row < self.base_row + self.zone_h:
            row = self.head_row
            col = self.col_index
            if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
                cell = grid[row][col]
                cell.value = ord(random.choice(self.charset))
                cell.is_head = True
                cell.generation = frame
            return

        # Head moved in-zone → write body at old position, head at new position
        if self.base_row <= old_head < self.base_row + self.zone_h:
            row = old_head
            col = self.col_index
            if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
                cell = grid[row][col]
                cell.value = ord(random.choice(self.charset))
                cell.is_head = False
                cell.generation = frame

        if self.base_row <= self.head_row < self.base_row + self.zone_h:
            row = self.head_row
            col = self.col_index
            if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
                cell = grid[row][col]
                cell.value = ord(random.choice(self.charset))
                cell.is_head = True
                cell.generation = frame

        # Clean up tail: clear cells that scrolled out of the stream trail
        tail_row = self.head_row - self.stream_length
        if self.base_row <= tail_row < self.base_row + self.zone_h:
            row = tail_row
            col = self.col_index
            if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
                cell = grid[row][col]
                cell.value = -1
                cell.is_head = False

        # Stream fully scrolled off zone — reset with new delay
        zone_bottom = self.base_row + self.zone_h
        if self.head_row >= zone_bottom + self.stream_length:
            self.head_row = _NO_STREAM
            self.spaces_left = random.randint(0, self.zone_h)
            self.stream_length = random.randint(3, self.zone_h)
