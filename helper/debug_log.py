import threading
import time


def log(message):
    """Debug print with time and thread name."""
    print(f"[{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d}] "
          f"[{threading.current_thread().name}] {message}", flush=True)