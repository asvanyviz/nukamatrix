"""MatrixEngine — main loop orchestrating update, render, and input with multi-mode support."""

import signal
import time
from blessed import Terminal

from nukamatrix.config import Config, COLUMN_STEP
from nukamatrix.core.matrix import Cell, Column
from nukamatrix.core.renderer import Renderer
from nukamatrix.modes import DisplayMode
from nukamatrix.panels.layout import (
    LayoutDefinition,
    layout_full_matrix,
    layout_matrix_sidebar,
    layout_quarter_grid,
)
from nukamatrix.panels.sysinfo import CpuPanel, MemPanel, DiskPanel, NetPanel, ClockPanel
from nukamatrix.utils.sysinfo import SysInfoCollector


class MultiModeEngine:
    """Main engine loop with multi-mode support.

    Modes:
    - pure-matrix: Full-screen matrix rain (original behavior)
    - matrix+stats: Matrix on left 70%, system info panels on right 30%
    - stats-grid: 2x2 quadrant grid showing CPU, Mem, Disk, Net
    - custom: Configurable layout

    Usage:
        config = Config(fps=30, speed=4, color="green", mode="matrix+stats")
        engine = MultiModeEngine(config)
        engine.run()
    """

    def __init__(self, config: Config):
        self.config = config
        self.term = Terminal()
        self._frame = 0

        # State
        self._running = False
        self._columns: list[Column] = []
        self._grid: list[list[Cell]] = []

        # Dimensions
        self._cols = 0
        self._rows = 0

        # Resize handling
        self._resize_pending = False

        # Timing
        self._last_frame_time = 0.0

        # Renderers — one per matrix zone
        self._renderers: list[tuple[int, int, int, int, Renderer]] = []

        # Panels
        self._sysinfo: SysInfoCollector | None = None
        self._panels: list = []

        # Layout
        self._layout: LayoutDefinition | None = None

        # Mode
        self._mode = DisplayMode.from_string(getattr(config, 'mode', 'pure-matrix'))

        # Offscreen buffer for mode-specific clearing
        self._last_rendered_zones: list[tuple[int, int, int, int]] = []

    # ── Setup / Teardown ────────────────────────────────────────

    def _compute_layout(self) -> LayoutDefinition:
        """Compute layout zones based on current mode."""
        w, h = self.term.width, self.term.height
        if self._mode == DisplayMode.PURE_MATRIX:
            return layout_full_matrix(w, h)
        elif self._mode == DisplayMode.MATRIX_STATS:
            return layout_matrix_sidebar(w, h, sidebar_ratio=0.30)
        elif self._mode == DisplayMode.STATS_GRID:
            return layout_quarter_grid(w, h)
        else:  # custom
            return layout_quarter_grid(w, h)  # fallback

    def _init_layout(self):
        """Set up zones, matrix grid, panels, and renderers."""
        self._layout = self._compute_layout()
        self._renderers = []
        self._panels = []

        if self._sysinfo is None:
            self._sysinfo = SysInfoCollector()

        # Initialize sysinfo collector once
        self._sysinfo.update()

        # Set up panels
        self._setup_panels()

        # Set up renderers and grids per zone
        for zone, assignment in zip(self._layout.zones, self._layout.assignments):
            if assignment == "matrix":
                zone_clamped = zone.clamp(self.term.width, self.term.height)
                renderer = Renderer(self.term, self.config)
                renderer.zone_x = zone_clamped.x
                renderer.zone_y = zone_clamped.y
                renderer.zone_w = zone_clamped.width
                renderer.zone_h = zone_clamped.height
                self._renderers.append((
                    zone_clamped.x, zone_clamped.y,
                    zone_clamped.width, zone_clamped.height,
                    renderer
                ))
                self._init_grid_for_zone(zone_clamped.x, zone_clamped.y,
                                         zone_clamped.width, zone_clamped.height)

        self._frame = 0
        print(self.term.clear, end="")

    def _init_grid_for_zone(self, ox: int, oy: int, w: int, h: int):
        """Create columns and grid for a matrix zone with offset."""
        active_cols = (w + COLUMN_STEP - 1) // COLUMN_STEP
        cols = [
            Column(
                col_index=c * COLUMN_STEP + ox,
                max_rows=oy + h,
                base_row=oy,
                zone_h=h,
                charset=self.config.effective_charset,
                base_interval=max(1, self.config.update_interval),
            )
            for c in range(active_cols)
        ]
        # Allocate 2D grid for the whole screen (simple, avoids zone boundary issues)
        if not self._grid or len(self._grid) < self.term.height:
            self._grid = [
                [Cell() for _ in range(self.term.width)]
                for _ in range(self.term.height)
            ]
        self._columns.extend(cols)

    def _setup_panels(self):
        """Create sysinfo panels based on layout assignments."""
        # Create one of each panel type (they'll be reused)
        for zone, assignment in zip(self._layout.zones, self._layout.assignments):
            if assignment == "cpu":
                p = CpuPanel(zone.x, zone.y, zone.width, zone.height)
                p.set_collector(self._sysinfo)
                self._panels.append(p)
            elif assignment == "mem":
                p = MemPanel(zone.x, zone.y, zone.width, zone.height)
                p.set_collector(self._sysinfo)
                self._panels.append(p)
            elif assignment == "disk":
                p = DiskPanel(zone.x, zone.y, zone.width, zone.height)
                p.set_collector(self._sysinfo)
                self._panels.append(p)
            elif assignment == "net":
                p = NetPanel(zone.x, zone.y, zone.width, zone.height)
                p.set_collector(self._sysinfo)
                self._panels.append(p)
            elif assignment == "clock":
                self._panels.append(ClockPanel(zone.x, zone.y, zone.width, zone.height))

    def _init_signal(self):
        """Set up SIGWINCH handler for terminal resize."""
        def _resize_handler(signum, frame):
            self._resize_pending = True
        signal.signal(signal.SIGWINCH, _resize_handler)

    # ── Core loop ───────────────────────────────────────────────

    def run(self):
        """Run the main loop until stopped."""
        self._running = True
        self._init_signal()
        self._init_layout()

        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            print(self.term.clear, end="")

            while self._running:
                frame_start = time.monotonic()

                # Re-read FPS from config each frame (settings can change it)
                fps = max(1, self.config.fps)
                frame_interval = 1.0 / fps

                # Detect config changes that affect column intervals
                if hasattr(self, '_last_speed') and self._last_speed != self.config.speed:
                    # Speed changed — update all column intervals
                    for col in self._columns:
                        col.update_interval = max(1, speed_to_interval(self.config.speed))
                self._last_speed = self.config.speed

                # Handle resize
                if self._resize_pending:
                    self._resize_pending = False
                    if self.term.width != self._cols or self.term.height != self._rows:
                        self._cols = self.term.width
                        self._rows = self.term.height
                        self._grid = []
                        self._columns = []
                        self._init_layout()

                # 1. Update sysinfo (if panels active)
                if self._mode != DisplayMode.PURE_MATRIX and self._sysinfo:
                    self._set_panel_colors()
                    self._sysinfo.update()

                # 2. Update matrix columns
                self._update()

                # 3. Render
                self._render()

                # 4. Check input
                self._check_input(self._frame)

                # 5. Frame timing
                self._frame += 1
                elapsed = time.monotonic() - frame_start
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def stop(self):
        """Signal the engine to stop on next frame."""
        self._running = False

    # ── Update ──────────────────────────────────────────────────

    def _update(self):
        """Update all columns that are due for a step."""
        for col in self._columns:
            if col.tick(self._frame):
                col.update(self._frame, self._grid)

    # ── Render ──────────────────────────────────────────────────

    def _render(self):
        """Render based on current mode."""
        if self._mode == DisplayMode.PURE_MATRIX:
            self._render_pure_matrix()
        elif self._mode == DisplayMode.MATRIX_STATS:
            self._render_matrix_stats()
        elif self._mode == DisplayMode.STATS_GRID:
            self._render_stats_grid()
        else:
            self._render_custom()

    def _render_pure_matrix(self):
        """Full-screen matrix rain."""
        for ox, oy, w, h, renderer in self._renderers:
            renderer.render_zone(self._grid, self._frame, ox, oy, w, h)

    def _render_matrix_stats(self):
        """Matrix on left, panels on right.

        Key: only re-render the matrix portion (left side), panels on right.
        This avoids clearing the panels every frame.
        """
        # Render matrix zone
        for ox, oy, w, h, renderer in self._renderers:
            renderer.render_zone(self._grid, self._frame, ox, oy, w, h)

        # Render panels (right side) every few frames for anti burn-in pulse
        # But always update data
        if self._frame % 2 == 0:  # update panels at half the matrix fps
            for panel in self._panels:
                panel.render(self.term, self._frame)

    def _render_stats_grid(self):
        """Full-screen quad grid with system info panels only.
        
        Clears the screen each frame to prevent ghosting from previous mode.
        """
        # Clear screen first
        print(self.term.clear, end="")
        
        # Render all panels
        for panel in self._panels:
            panel.render(self.term, self._frame)

        # Draw subtle dividers at quadrant borders
        self._render_grid_dividers()

    def _render_custom(self):
        """Custom layout — same as stats-grid for now."""
        self._render_stats_grid()

    def _render_grid_dividers(self):
        """Draw subtle divider lines at quadrant borders.
        
        Anti burn-in: pulse color and pattern every frame.
        """
        w, h = self.term.width, self.term.height
        half_w = w // 2
        half_h = h // 2

        # Pick color based on frame cycle
        color_cycle = [self.term.color(238), self.term.color(240), self.term.color(236)]
        c = color_cycle[(self._frame // 20) % len(color_cycle)]

        # Vertical divider line
        mid_line = ""
        for y in range(h):
            if (y + self._frame) % 6 == 0:
                mid_line += c(self.term.move_xy(half_w, y) + "│")
        print(mid_line, end="")

        # Horizontal divider line
        mid_line2 = ""
        for x in range(w):
            if (x + self._frame) % 6 == 0:
                mid_line2 += c(self.term.move_xy(x, half_h) + "─")
        print(mid_line2, end="")

    # ── Settings ────────────────────────────────────────────────

    def _open_settings(self, frame: int) -> None:
        """Open the settings menu overlay."""
        import traceback as _tb
        try:
            from nukamatrix.settings import SettingsMenu
            menu = SettingsMenu(self.config)
            save, needs_reinit = menu.run(self.term, frame)

            # DEBUG: log config state after menu closes
            import sys
            sys.stderr.write(f"DEBUG after menu: save={save} reinit={needs_reinit} "
                             f"color={self.config.color} speed={self.config.speed} "
                             f"fps={self.config.fps} rainbow={self.config.rainbow}\n")
            sys.stderr.flush()

            import time
            if save:
                menu.save_to_file()
                msg = f"  OK: color={self.config.color} speed={self.config.speed} fps={self.config.fps} rainbow={self.config.rainbow} bold={self.config.bold}  "
            else:
                msg = "  DISCARDED (ESC) — press 'q' to save  "
            print(self.term.move_xy(0, self.term.height - 1) +
                  self.term.normal + self.term.bright_white(self.term.on_blue(msg)), end="")
            time.sleep(2)

            if needs_reinit:
                # Charset or lambda changed -> rebuild columns
                self._columns = []
                self._grid = []
                self._init_layout()
        except Exception as e:
            # Log error to terminal and resume
            with self.term.location(0, 0):
                print(self.term.move_xy(0, 0) + self.term.on_red(self.term.white(f" [Settings Error: {e}] ")) + "  press key to continue  ", end="")
            # Show traceback at bottom of screen
            tb_text = _tb.format_exc()
            for i, line in enumerate(tb_text.splitlines()):
                print(self.term.move_xy(0, self.term.height - 3 + i) + self.term.red(line), end="")
            # Wait for any key
            while not self.term.inkey(timeout=0.1):
                pass

    # ── Input ───────────────────────────────────────────────────

    def _check_input(self, frame: int = 0):
        """Check for non-blocking keyboard input."""
        key = self.term.inkey(timeout=0)
        if not key:
            return

        # Screensaver mode — exit on any key
        if self.config.screensaver:
            self.stop()
            return

        # Open settings menu
        if key.lower() == "p":
            self._open_settings(frame)
            return

        if key.lower() == "q" or key.name == "KEY_ESCAPE":
            self.stop()
            return

        # Tab / Space to cycle modes
        if key == '\t' or key.code == 9:
            self._cycle_mode()

    def _cycle_mode(self):
        """Cycle through display modes."""
        modes = list(DisplayMode)
        idx = (modes.index(self._mode) + 1) % len(modes)
        self._mode = modes[idx]
        self._columns = []
        self._grid = []
        self._init_layout()

    # ── Public API ──────────────────────────────────────────────

    @property
    def current_terminal_size(self) -> tuple[int, int]:
        return self.term.width, self.term.height

    @property
    def grid(self) -> list[list[Cell]]:
        return self._grid

    @property
    def frame_count(self) -> int:
        return self._frame



