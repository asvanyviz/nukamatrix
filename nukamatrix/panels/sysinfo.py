"""System info panel implementations."""

import time

from blessed import Terminal

from nukamatrix.panels.base import Panel
from nukamatrix.utils.sysinfo import SysSnapshot, SysInfoCollector


# ── Color helpers ──────────────────────────────────────────────

def _usage_color(term: Terminal, pct: float, classes: tuple[str, str, str]) -> str:
    """Return 'low/mid/high' css-like class key."""
    if pct < 40:
        return classes[0]
    elif pct < 75:
        return classes[1]
    return classes[2]


def _format_bar_str(val_pct: float, width: int = 20) -> str:
    filled = max(0, min(width, int(val_pct / 100 * width)))
    return "█" * filled + "░" * (width - filled)


# ── Panels ─────────────────────────────────────────────────────


class CpuPanel(Panel):
    """CPU usage panel with per-core breakdown."""

    def __init__(self, x: int, y: int, width: int = 30, height: int = 12):
        super().__init__(x, y, width, height, " CPU ")
        self._snapshot: SysSnapshot | None = None
        self._last_update = 0.0
        self._collector: SysInfoCollector | None = None

    def set_collector(self, collector: SysInfoCollector):
        self._collector = collector

    def update(self):
        if self._collector:
            self._snapshot = self._collector.update()
            self._last_update = time.monotonic()

    def render(self, term: Terminal, frame: int):
        self.update()
        if not self._snapshot:
            return

        s = self._snapshot
        lines = self._border_header(term, frame)

        cpu = s.cpu
        # Usage line
        pct = cpu.usage_pct
        bar = _format_bar_str(pct, self.width - 4)
        if pct < 40:
            bar_colored = f"  {term.green(bar)}"
        elif pct < 75:
            bar_colored = f"  {term.yellow(bar)}"
        else:
            bar_colored = f"  {term.red(bar)}"

        pct_colored = f"{pct:5.1f}%"
        lines.append(f"{term.bold(term.white(pct_colored))}{bar_colored}")

        # Freq + cores
        lines.append(f"  Freq: {term.cyan(f'{cpu.freq_mhz:.0f} MHz')}  "
                     f"Cores: {cpu.cores_phys}P/{cpu.cores_log}L")

        # Load average
        lines.append(f"  Load: {term.yellow(f'{cpu.load_avg[0]:.2f}')} "
                     f"{term.color(250)(f'{cpu.load_avg[1]:.2f}')} "
                     f"{term.color(240)(f'{cpu.load_avg[2]:.2f}')}  (1/5/15)")

        # Divider
        lines.append(term.dim("  " + "─" * (self.width - 4)))
        lines.append(term.dim("  Per-core:"))

        # Per-core bars (show at most 8 if many cores)
        bars = cpu.per_cpu[:min(8, len(cpu.per_cpu))]
        for i, c in enumerate(bars):
            b = _format_bar_str(c, self.width - 6)
            if c < 40:
                cb = term.green(b)
            elif c < 75:
                cb = term.yellow(b)
            else:
                cb = term.red(b)
            lines.append(f"  C{i:2d} {term.color(250)(f'{c:5.1f}%')}{cb}")

        self._emit(term, frame, lines)

    def _border_header(self, term: Terminal, frame: int) -> list[str]:
        return []

    def _emit(self, term: Terminal, frame: int, inner_lines: list[str]):
        """Build bordered output and print at panel position."""
        b_l, b_r = term.green("│"), term.green("│")
        if (frame // 30) % 2 == 1:
            b_l, b_r = term.cyan("│"), term.cyan("│")

        # Top
        border_c = term.green if (frame // 60) % 2 == 0 else term.cyan
        inner_w = self.width - 2
        label = " CPU "
        left = (inner_w - len(label)) // 2
        right = inner_w - len(label) - left
        print(term.move_xy(self.x, self.y) + border_c("┌") +
              " " * left + label + " " * right + border_c("┐"), end="")

        # Inner content
        for i, line in enumerate(inner_lines[:self.height - 2]):
            row = line.ljust(inner_w)[:inner_w]
            print(term.move_xy(self.x, self.y + 1 + i) + b_l + row + b_r, end="")

        # Fill remaining
        for i in range(len(inner_lines), self.height - 2):
            print(term.move_xy(self.x, self.y + 1 + i) + b_l + " " * inner_w + b_r, end="")

        # Bottom
        by = self.y + self.height - 1
        h_char = border_c if border_c else term.green
        print(term.move_xy(self.x, by) + border_c("└") +
              border_c("─" * (self.width - 2)) + border_c("┘"), end="")


class MemPanel(Panel):
    """Memory usage panel."""

    def __init__(self, x: int, y: int, width: int = 30, height: int = 8):
        super().__init__(x, y, width, height, " MEMORY ")
        self._snapshot: SysSnapshot | None = None
        self._last_update = 0.0
        self._collector: SysInfoCollector | None = None

    def set_collector(self, collector: SysInfoCollector):
        self._collector = collector

    def update(self):
        if self._collector:
            self._snapshot = self._collector.update()
            self._last_update = time.monotonic()

    def render(self, term: Terminal, frame: int):
        self.update()
        if not self._snapshot:
            return

        m = self._snapshot.mem
        lines = []

        # Main usage bar
        used_pct = m.usage_pct
        bar = _format_bar_str(used_pct, self.width - 4)
        if used_pct < 50:
            bar_colored = f"  {term.green(bar)}"
        elif used_pct < 80:
            bar_colored = f"  {term.yellow(bar)}"
        else:
            bar_colored = f"  {term.red(bar)}"

        lines.append(f"{term.bold(term.white(f'{used_pct:5.1f}%'))}{bar_colored}")

        # Breakdown
        lines.append(f"  Used:  {term.color(220)(f'{m.used_gb:6.2f} GB')}")
        lines.append(f"  Free:  {term.green(f'{m.free_gb:6.2f} GB')}")
        lines.append(f"  Avail: {term.cyan(f'{m.available_gb:6.2f} GB')}")
        lines.append(f"  Total: {term.white(f'{m.total_gb:6.2f} GB')}")

        # Swap (if present)
        if m.swap_total_gb > 0:
            sw_pct = m.swap_used_gb / m.swap_total_gb * 100 if m.swap_total_gb else 0
            sw_bar = _format_bar_str(sw_pct, self.width - 6)
            lines.append(term.dim("  ─" * (self.width // 2 - 2)))
            lines.append(f"  Swap: {term.color(135)(f'{sw_pct:5.1f}%')} "
                        f"{term.color(135)(sw_bar)}")
            lines.append(f"        {m.swap_used_gb:.2f}/{m.swap_total_gb:.2f} GB")

        self._emit_bordered(term, frame, lines)

    def _emit_bordered(self, term: Terminal, frame: int, inner_lines: list[str]):
        border_c = term.green if (frame // 60) % 2 == 0 else term.cyan
        b_l, b_r = border_c("│"), border_c("│")
        if (frame // 30) % 2 == 1:
            b_l, b_r = term.cyan("│"), term.cyan("│")

        inner_w = self.width - 2
        label = " MEMORY "
        left = (inner_w - len(label)) // 2
        right = inner_w - len(label) - left
        print(term.move_xy(self.x, self.y) + border_c("┌") +
              " " * left + label + " " * right + border_c("┐"), end="")

        for i, line in enumerate(inner_lines[:self.height - 2]):
            row = line.ljust(inner_w)[:inner_w]
            print(term.move_xy(self.x, self.y + 1 + i) + b_l + row + b_r, end="")

        for i in range(len(inner_lines), self.height - 2):
            print(term.move_xy(self.x, self.y + 1 + i) + b_l + " " * inner_w + b_r, end="")

        print(term.move_xy(self.x, self.y + self.height - 1) + border_c("└") +
              border_c("─" * (self.width - 2)) + border_c("┘"), end="")


class DiskPanel(Panel):
    """Disk usage + I/O panel."""

    def __init__(self, x: int, y: int, width: int = 30, height: int = 10):
        super().__init__(x, y, width, height, " DISK ")
        self._snapshot: SysSnapshot | None = None
        self._collector: SysInfoCollector | None = None

    def set_collector(self, collector: SysInfoCollector):
        self._collector = collector

    def update(self):
        if self._collector:
            self._snapshot = self._collector.update()

    def render(self, term: Terminal, frame: int):
        self.update()
        if not self._snapshot:
            return

        d = self._snapshot.disk
        lines = []

        # Usage bar
        bar = _format_bar_str(d.usage_pct, self.width - 4)
        if d.usage_pct < 50:
            bar_colored = f"  {term.green(bar)}"
        elif d.usage_pct < 80:
            bar_colored = f"  {term.yellow(bar)}"
        else:
            bar_colored = f"  {term.red(bar)}"
        lines.append(f"{term.bold(term.white(f'{d.usage_pct:5.1f}%'))}{bar_colored}")
        lines.append(f"  Used:  {term.color(220)(f'{d.used_gb:6.2f} GB')}")
        lines.append(f"  Free:  {term.green(f'{d.free_gb:6.2f} GB')}")
        lines.append(f"  Total: {term.white(f'{d.total_gb:6.2f} GB')}")

        lines.append(term.dim("  " + "─" * (self.width - 4)))
        lines.append(term.dim("  I/O (MB/s):"))

        # I/O rates with pulsing indicator
        pulse = "●" if (frame // 15) % 2 == 0 else "○"
        read_c = term.cyan if (frame // 30) % 2 == 0 else term.green
        write_c = term.magenta if (frame // 30) % 2 == 0 else term.yellow

        lines.append(f"  {read_c(pulse)} Read:  {read_c(f'{d.read_bytes_sec:7.2f}')}")
        lines.append(f"  {write_c(pulse)} Write: {write_c(f'{d.write_bytes_sec:7.2f}')}")

        self._emit_bordered(term, frame, lines)

    def _emit_bordered(self, term: Terminal, frame: int, inner_lines: list[str]):
        border_c = term.green if (frame // 60) % 2 == 0 else term.cyan
        b_l, b_r = border_c("│"), border_c("│")
        inner_w = self.width - 2
        label = " DISK "
        left = (inner_w - len(label)) // 2
        right = inner_w - len(label) - left

        print(term.move_xy(self.x, self.y) + border_c("┌") +
              " " * left + label + " " * right + border_c("┐"), end="")

        for i, line in enumerate(inner_lines[:self.height - 2]):
            row = line.ljust(inner_w)[:inner_w]
            print(term.move_xy(self.x, self.y + 1 + i) + b_l + row + b_r, end="")

        for i in range(len(inner_lines), self.height - 2):
            print(term.move_xy(self.x, self.y + 1 + i) + b_l + " " * inner_w + b_r, end="")

        print(term.move_xy(self.x, self.y + self.height - 1) + border_c("└") +
              border_c("─" * (self.width - 2)) + border_c("┘"), end="")


class NetPanel(Panel):
    """Network throughput panel."""

    def __init__(self, x: int, y: int, width: int = 30, height: int = 8):
        super().__init__(x, y, width, height, " NETWORK ")
        self._snapshot: SysSnapshot | None = None
        self._collector: SysInfoCollector | None = None

    def set_collector(self, collector: SysInfoCollector):
        self._collector = collector

    def update(self):
        if self._collector:
            self._snapshot = self._collector.update()

    def render(self, term: Terminal, frame: int):
        self.update()
        if not self._snapshot:
            return

        n = self._snapshot.net
        lines = []

        # Pulsing arrows
        rx_pulse = "▼" if (frame // 15) % 2 == 0 else "▽"
        tx_pulse = "▲" if (frame // 15) % 2 == 0 else "△"

        recv_c = term.green if (frame // 30) % 2 == 0 else term.cyan
        sent_c = term.magenta if (frame // 30) % 2 == 0 else term.yellow

        # Download
        lines.append(f"  {recv_c(rx_pulse)} Down: {recv_c(n.recv_str)}")
        lines.append(f"  {sent_c(tx_pulse)} Up:   {sent_c(n.sent_str)}")

        lines.append(term.dim("  " + "─" * (self.width - 4)))

        # Total counters
        lines.append(f"  RX: {term.color(250)(f'{n.bytes_recv_total / (1024**3):.2f} GB')}")
        lines.append(f"  TX: {term.color(250)(f'{n.bytes_sent_total / (1024**3):.2f} GB')}")

        self._emit_bordered(term, frame, lines)

    def _emit_bordered(self, term: Terminal, frame: int, inner_lines: list[str]):
        border_c = term.green if (frame // 60) % 2 == 0 else term.cyan
        b_l, b_r = border_c("│"), border_c("│")
        inner_w = self.width - 2
        label = " NETWORK "
        left = (inner_w - len(label)) // 2
        right = inner_w - len(label) - left

        print(term.move_xy(self.x, self.y) + border_c("┌") +
              " " * left + label + " " * right + border_c("┐"), end="")

        for i, line in enumerate(inner_lines[:self.height - 2]):
            row = line.ljust(inner_w)[:inner_w]
            print(term.move_xy(self.x, self.y + 1 + i) + b_l + row + b_r, end="")

        for i in range(len(inner_lines), self.height - 2):
            print(term.move_xy(self.x, self.y + 1 + i) + b_l + " " * inner_w + b_r, end="")

        print(term.move_xy(self.x, self.y + self.height - 1) + border_c("└") +
              border_c("─" * (self.width - 2)) + border_c("┘"), end="")


class ClockPanel(Panel):
    """Simple clock panel — anti burn-in via color cycling."""

    COLORS = ["green", "cyan", "yellow", "white", "blue", "magenta"]

    def __init__(self, x: int, y: int, width: int = 20, height: int = 5):
        super().__init__(x, y, width, height, " TIME ")
        self._last_sec = -1

    def render(self, term: Terminal, frame: int):
        import datetime
        now = datetime.datetime.now()
        sec = now.second
        changed = sec != self._last_sec
        self._last_sec = sec

        if not changed and frame % 30 != 0:
            return  # don't re-render every frame if second hasn't changed

        border_c = getattr(term, self.COLORS[frame % len(self.COLORS)])
        b_l, b_r = border_c("│"), border_c("│")
        inner_w = self.width - 2

        label = " TIME "
        left = (inner_w - len(label)) // 2
        right = inner_w - len(label) - left

        hhmm_ss = f"  {now.strftime('%H:%M:%S')}"
        date_s = f"  {now.strftime('%Y-%m-%d')}"
        day_s = f"  {now.strftime('%A')}"[:2].upper()

        top = term.move_xy(self.x, self.y) + border_c("┌") + " " * left + label + " " * right + border_c("┐")
        r1 = term.move_xy(self.x, self.y + 1) + b_l + hhmm_ss.ljust(inner_w)[:inner_w] + b_r
        r2 = term.move_xy(self.x, self.y + 2) + b_l + date_s.ljust(inner_w)[:inner_w] + b_r
        r3 = term.move_xy(self.x, self.y + 3) + b_l + day_s.ljust(inner_w)[:inner_w] + b_r
        bot = term.move_xy(self.x, self.y + 4) + border_c("└") + border_c("─" * (self.width - 2)) + border_c("┘")

        # Colorize clock digits
        color_name = self.COLORS[(frame // 10) % len(self.COLORS)]
        clock_attr = getattr(term, color_name)

        # Re-render with colored clock
        hhmm_ss_colored = "  " + clock_attr(now.strftime('%H:%M:%S'))

        r1 = term.move_xy(self.x, self.y + 1) + b_l

        # Build r1 with colored time in the middle
        time_str = clock_attr(now.strftime('%H:%M:%S'))
        remaining = inner_w - len(now.strftime('%H:%M:%S'))
        r1 += time_str + " " * max(0, remaining)
        r1 += b_r

        print(top, end="")
        print(r1, end="")
        print(term.move_xy(self.x, self.y + 2) + b_l + date_s.ljust(inner_w)[:inner_w] + b_r, end="")
        print(term.move_xy(self.x, self.y + 3) + b_l + day_s.ljust(inner_w)[:inner_w] + b_r, end="")
        print(bot, end="")
