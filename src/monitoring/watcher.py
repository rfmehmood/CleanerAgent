import time
import threading
import shutil
from typing import Callable, Optional

class BackgroundStorageMonitor:
    """
    Opt-in background storage monitor.
    Periodically checks disk free space and alerts if capacity becomes critically low.
    Runs strictly in a background thread without blocking the user interface.
    """

    def __init__(self, interval_seconds: int = 3600, alert_callback: Optional[Callable[[str, float], None]] = None):
        self.interval_seconds = interval_seconds
        self.alert_callback = alert_callback
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run_loop(self):
        while self.is_running:
            try:
                for letter in "CDE":
                    drive_root = f"{letter}:\\"
                    try:
                        usage = shutil.disk_usage(drive_root)
                        free_gb = usage.free / (1024**3)
                        pct_used = (usage.used / usage.total) * 100
                        if free_gb < 5.0 or pct_used > 92.0:
                            if self.alert_callback:
                                self.alert_callback(drive_root, free_gb)
                    except Exception:
                        pass
            except Exception:
                pass

            # Sleep in small increments to allow immediate cancellation
            for _ in range(int(self.interval_seconds)):
                if not self.is_running:
                    break
                time.sleep(1.0)
