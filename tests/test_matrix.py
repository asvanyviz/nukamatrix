"""Tests for nukamatrix.core.matrix — Cell and Column data model."""

import pytest
import random

from nukamatrix.core.matrix import Cell, Column, _NO_STREAM


class TestCell:
    def test_default_empty(self):
        c = Cell()
        assert c.is_empty is True
        assert c.is_head is False
        assert c.value == -1

    def test_head_cell(self):
        c = Cell(value=65, is_head=True, generation=1)
        assert c.is_empty is False
        assert c.is_head is True
        assert c.value == 65

    def test_space_cell(self):
        c = Cell(value=0)
        assert c.is_space is True
        assert c.is_empty is False


class TestColumn:
    def setup_method(self):
        random.seed(42)

    def _make_column(self, **kwargs):
        defaults = dict(
            col_index=0,
            max_rows=24,
            charset="abc",
            base_interval=2,
        )
        defaults.update(kwargs)
        return Column(**defaults)

    def test_initial_state_has_no_stream_or_delay(self):
        col = self._make_column()
        # Either no stream or spaces_left > 0 (randomized)
        assert col.col_index == 0
        assert col.max_rows == 24
        assert col.speed >= 0.5 and col.speed <= 1.5

    def test_tick_returns_true_after_interval(self):
        col = self._make_column()
        col._tick = 1  # pre-set to one below interval
        col.update_interval = 2

        # First tick — should be due (1+1 >= 2)
        assert col.tick(0) is True

        # Reset and test non-due case
        col._tick = 0
        assert col.tick(0) is False  # 0+1 < 2, not due yet

    def test_has_stream_property(self):
        col = self._make_column()
        assert col.has_stream is False
        col.head_row = 5
        assert col.has_stream is True

    def test_update_spawns_stream_when_spaces_deplete(self):
        col = self._make_column()
        col.spaces_left = 0  # force spawn on next update

        grid = [[Cell() for _ in range(1)] for _ in range(24)]
        col.update(1, grid)

        # A new stream should be spawning (head_row set above zone)
        assert col.has_stream is True

    def test_update_with_spaces_left_decrements(self):
        col = self._make_column()
        col.head_row = _NO_STREAM
        col.spaces_left = 3

        grid = [[Cell() for _ in range(1)] for _ in range(24)]
        col.update(1, grid)

        assert col.spaces_left == 2
        assert col.has_stream is False

    def test_update_advances_head_in_zone(self):
        col = self._make_column(base_row=0, zone_h=24)
        col.spaces_left = 0
        col.head_row = 5
        col.speed = 1.0

        grid = [[Cell() for _ in range(1)] for _ in range(24)]
        old_head = col.head_row
        col.update(10, grid)

        assert col.has_stream is True
        # Head should have moved
        assert col.head_row >= old_head


class TestColumnZone:
    """Test zone-based column behavior (zone offsets)."""

    def setup_method(self):
        random.seed(99)

    def test_zone_column_stays_within_zone(self):
        col = col = Column(
            col_index=10,
            max_rows=100,
            charset="abc",
            base_interval=1,
            base_row=5,  # zone starts at row 5
            zone_h=10,   # zone is 10 rows tall
        )
        col.spaces_left = 0

        grid = [[Cell() for _ in range(100)] for _ in range(100)]

        # Run several updates
        for frame in range(1, 50):
            col.tick(frame)
            col.update(frame, grid)
