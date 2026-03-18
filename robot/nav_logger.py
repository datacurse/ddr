import csv
import os
from datetime import datetime

LOG_DIR = ".studies/nav_logs"
LOG_FIELDS = [
    "t", "event", "cell", "facing", "heading_offset",
    "aruco_id", "aruco_angle",
    "line_angle", "line_ox", "line_oy",
    "turn_cmd", "turn_deg",
    "speed", "lv", "rv", "d_mm", "rem_mm",
]


def ts() -> str:
    now = datetime.now()
    return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


class NavLogger:
    def __init__(self, log_dir: str = LOG_DIR):
        self._log_dir = log_dir
        self._file = None
        self._writer = None
        self.defaults: dict = {}

    @property
    def is_open(self) -> bool:
        return self._file is not None

    def open(self) -> str:
        """Create a new timestamped CSV file. Returns the file path."""
        os.makedirs(self._log_dir, exist_ok=True)
        path = os.path.join(self._log_dir, f"{datetime.now():%Y-%m-%d_%H%M%S}.csv")
        self._file = open(path, "w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=LOG_FIELDS, extrasaction="ignore")
        self._writer.writeheader()
        return path

    def log(self, **kw):
        """Write a row. Merges defaults, auto-fills 't'. No-op if not open."""
        if not self._writer:
            return
        row = {**self.defaults, **kw}
        row.setdefault("t", ts())
        self._writer.writerow(row)
        self._file.flush()

    def close(self):
        """Close the CSV file."""
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None
