"""Mode definitions and routing for PyMatrix multi-mode system."""

from enum import Enum

MODES = [
    "pure-matrix",
    "matrix+stats",
    "stats-grid",
    "custom",
]


class DisplayMode(Enum):
    PURE_MATRIX = "pure-matrix"
    MATRIX_STATS = "matrix+stats"
    STATS_GRID = "stats-grid"
    CUSTOM = "custom"

    @classmethod
    def from_string(cls, s: str) -> "DisplayMode":
        mapping = {
            "pure-matrix": cls.PURE_MATRIX,
            "matrix+stats": cls.MATRIX_STATS,
            "stats-grid": cls.STATS_GRID,
            "custom": cls.CUSTOM,
        }
        return mapping.get(s, cls.PURE_MATRIX)
