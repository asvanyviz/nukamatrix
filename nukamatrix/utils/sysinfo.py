"""System information collector using psutil."""

import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

# ── CPU fallback via /proc ──────────────────────────────────────

def _read_proc_stat() -> Optional[tuple[int, int]]:
    """Read /proc/stat for total/idle jiffies. Returns None if unavailable."""
    try:
        with open("/proc/stat") as f:
            line = f.readline()
        parts = line.split()
        if parts[0] != "cpu":
            return None
        # fields: user nice system idle iowait irq softirq steal
        nums = [int(x) for x in parts[1:9]]
        total = sum(nums)
        idle = nums[3] + nums[4]  # idle + iowait
        return total, idle
    except (OSError, ValueError, IndexError):
        return None


# ── Data types ──────────────────────────────────────────────────

@dataclass
class CPUInfo:
    usage_pct: float = 0.0          # 0-100
    freq_mhz: float = 0.0           # current MHz
    cores_phys: int = 0
    cores_log: int = 0
    load_avg: tuple[float, float, float] = (0, 0, 0)  # 1/5/15 min
    per_cpu: list[float] = field(default_factory=list)  # per-core usage

    @property
    def bar(self) -> str:
        """Visual usage bar (20 chars)."""
        filled = int(self.usage_pct / 5)
        return "█" * filled + "░" * (20 - filled)

    @property
    def bar_pct_color_class(self) -> str:
        """Color hint: 'low' / 'mid' / 'high'."""
        if self.usage_pct < 40:
            return "low"
        elif self.usage_pct < 75:
            return "mid"
        return "high"


@dataclass
class MemInfo:
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    available_gb: float = 0.0
    usage_pct: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0

    @property
    def bar(self) -> str:
        filled = int(self.usage_pct / 5)
        return "█" * filled + "░" * (20 - filled)

    @property
    def bar_color_class(self) -> str:
        if self.usage_pct < 50:
            return "low"
        elif self.usage_pct < 80:
            return "mid"
        return "high"


@dataclass
class DiskInfo:
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    usage_pct: float = 0.0
    read_bytes_sec: float = 0.0     # MB/s read rate
    write_bytes_sec: float = 0.0    # MB/s write rate

    @property
    def bar(self) -> str:
        filled = int(self.usage_pct / 5)
        return "█" * filled + "░" * (20 - filled)


@dataclass
class NetInfo:
    recv_mbps: float = 0.0       # download speed
    sent_mbps: float = 0.0       # upload speed
    bytes_sent_total: int = 0
    bytes_recv_total: int = 0
    packets_sent: int = 0
    packets_recv: int = 0

    @property
    def recv_str(self) -> str:
        if self.recv_mbps >= 1000:
            return f"{self.recv_mbps / 1000:.1f} Gbps"
        return f"{self.recv_mbps:.1f} Mbps"

    @property
    def sent_str(self) -> str:
        if self.sent_mbps >= 1000:
            return f"{self.sent_mbps / 1000:.1f} Gbps"
        return f"{self.sent_mbps:.1f} Mbps"


@dataclass
class SysSnapshot:
    cpu: CPUInfo = field(default_factory=CPUInfo)
    mem: MemInfo = field(default_factory=MemInfo)
    disk: DiskInfo = field(default_factory=DiskInfo)
    net: NetInfo = field(default_factory=NetInfo)
    uptime_sec: float = 0
    hostname: str = ""
    kernel: str = ""


# ── Main collector ──────────────────────────────────────────────

class SysInfoCollector:
    """Collects system metrics using psutil with /proc fallback.

    Thread-safe for single-threaded use. Must call update() each frame.
    """

    def __init__(self):
        self.prev_disk = psutil.disk_io_counters() if _HAS_PSUTIL else None
        self.prev_net = psutil.net_io_counters() if _HAS_PSUTIL else None
        self.prev_cpu_time = _read_proc_stat()
        self.prev_time = time.monotonic()
        self.snapshot = SysSnapshot()
        self._initialized = False

        # Initialize CPU percent tracking (first call returns 0)
        if _HAS_PSUTIL:
            psutil.cpu_percent(interval=None)
        self.prev_net_data: Optional[tuple[int, int]] = None

    def update(self) -> SysSnapshot:
        """Collect a fresh snapshot. Call once per render cycle."""
        if _HAS_PSUTIL:
            self._update_psutil()
        else:
            self._update_proc()
        return self.snapshot

    def _update_psutil(self):
        s = self.snapshot

        # ── CPU ──────────────────────────────
        s.cpu.usage_pct = psutil.cpu_percent(interval=0)
        freq = psutil.cpu_freq()
        s.cpu.freq_mhz = freq.current if freq else 0
        s.cpu.cores_phys = psutil.cpu_count(logical=False) or 0
        s.cpu.cores_log = psutil.cpu_count(logical=True) or 0
        try:
            s.cpu.load_avg = psutil.getloadavg()
        except (OSError, AttributeError):
            pass
        s.cpu.per_cpu = psutil.cpu_percent(interval=0, percpu=True)

        # ── Memory ───────────────────────────
        vm = psutil.virtual_memory()
        s.mem.total_gb = vm.total / (1024 ** 3)
        s.mem.used_gb = vm.used / (1024 ** 3)
        s.mem.free_gb = vm.free / (1024 ** 3)
        s.mem.available_gb = vm.available / (1024 ** 3)
        s.mem.usage_pct = vm.percent

        sw = psutil.swap_memory()
        s.mem.swap_total_gb = sw.total / (1024 ** 3)
        s.mem.swap_used_gb = sw.used / (1024 ** 3)

        # ── Disk ─────────────────────────────
        now = time.monotonic()
        dt = max(now - self.prev_time, 0.001)

        try:
            disk = psutil.disk_usage("/")
            s.disk.total_gb = disk.total / (1024 ** 3)
            s.disk.used_gb = disk.used / (1024 ** 3)
            s.disk.free_gb = disk.free / (1024 ** 3)
            s.disk.usage_pct = disk.percent
        except OSError:
            pass

        dio = psutil.disk_io_counters()
        if dio and self.prev_disk:
            s.disk.read_bytes_sec = (dio.read_bytes - self.prev_disk.read_bytes) / dt / (1024 ** 2)
            s.disk.write_bytes_sec = (dio.write_bytes - self.prev_disk.write_bytes) / dt / (1024 ** 2)
        self.prev_disk = dio

        # ── Network ──────────────────────────
        nio = psutil.net_io_counters()
        if nio and self.prev_net:
            s.net.recv_mbps = (nio.bytes_recv - self.prev_net.bytes_recv) * 8 / dt / 1e6
            s.net.sent_mbps = (nio.bytes_sent - self.prev_net.bytes_sent) * 8 / dt / 1e6
            s.net.bytes_sent_total = nio.bytes_sent
            s.net.bytes_recv_total = nio.bytes_recv
            s.net.packets_sent = nio.packets_sent
            s.net.packets_recv = nio.packets_recv
        self.prev_net = nio

        self.prev_time = now

        # ── Meta ─────────────────────────────
        s.uptime_sec = time.monotonic() - self.prev_time  # nukamatrix uptime
        try:
            s.hostname = psutil.users()[0].host if psutil.users() else ""
        except Exception:
            pass
        try:
            import platform
            s.kernel = platform.release()
        except ImportError:
            pass

    def _update_proc(self):
        """Fallback path without psutil — reads /proc directly."""
        s = self.snapshot

        # ── CPU via /proc/stat ───────────────
        cpu = _read_proc_stat()
        if cpu and self.prev_cpu_time:
            total_d = cpu[0] - self.prev_cpu_time[0]
            idle_d = cpu[1] - self.prev_cpu_time[1]
            if total_d > 0:
                s.cpu.usage_pct = (1 - idle_d / total_d) * 100
        self.prev_cpu_time = cpu

        # ── Memory via /proc/meminfo ─────────
        try:
            with open("/proc/meminfo") as f:
                lines = f.read()
            mem = {}
            for line in lines.splitlines():
                parts = line.split()
                mem[parts[0].rstrip(":")] = int(parts[1]) * 1024  # kB → B

            s.mem.total_gb = mem.get("MemTotal", 0) / (1024 ** 3)
            s.mem.free_gb = mem.get("MemFree", 0) / (1024 ** 3)
            avail = mem.get("MemAvailable", mem.get("MemFree", 0))
            s.mem.available_gb = avail / (1024 ** 3)
            s.mem.used_gb = s.mem.total_gb - s.mem.available_gb
            if s.mem.total_gb > 0:
                s.mem.usage_pct = s.mem.used_gb / s.mem.total_gb * 100
        except (OSError, ValueError, KeyError):
            pass

        # ── Disk via /proc/diskstats ─────────
        now = time.monotonic()
        dt = max(now - self.prev_time, 0.001)

        try:
            with open("/proc/diskstats") as f:
                disk_lines = f.read()
            # Sum all read/write sectors
            r_sectors = 0
            w_sectors = 0
            for line in disk_lines.splitlines():
                parts = line.split()
                if len(parts) >= 11:
                    r_sectors += int(parts[5])   # sectors read
                    w_sectors += int(parts[9])   # sectors written
            # 1 sector = 512 bytes
            s.disk.read_bytes_sec = r_sectors * 512 / dt / (1024 ** 2)
            s.disk.write_bytes_sec = w_sectors * 512 / dt / (1024 ** 2)
        except (OSError, ValueError, IndexError):
            pass

        # ── Network via /proc/net/dev ────────
        try:
            with open("/proc/net/dev") as f:
                net_lines = f.read()
            net_recv = 0
            net_sent = 0
            for line in net_lines.splitlines()[2:]:  # skip header
                parts = line.split()
                if len(parts) >= 10:
                    iface = parts[0].rstrip(":")
                    if iface != "lo":
                        net_recv += int(parts[1])
                        net_sent += int(parts[9])
            if self.prev_net_data:
                s.net.recv_mbps = (net_recv - self.prev_net_data[0]) * 8 / dt / 1e6
                s.net.sent_mbps = (net_sent - self.prev_net_data[1]) * 8 / dt / 1e6
            self.prev_net_data = (net_recv, net_sent)
        except (OSError, ValueError, IndexError, AttributeError):
            pass

        self.prev_time = now

    # Store previous net counters for /proc fallback — declared in __init__
