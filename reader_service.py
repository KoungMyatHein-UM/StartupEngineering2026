import threading
from collections import deque


class ReaderService:
    def __init__(self, source, window=10, n=2):
        if not 1 <= n <= window:
            raise ValueError("n must be between 1 and the window size")
        self._source = source                    # any function that returns the next value
        self._window = deque(maxlen=window)      # raw history, owned by the service
        self._n = n                              # consecutive matches needed to accept a value
        self._latest = None                      # last accepted value; written only by _run()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="ReaderService")

    # --- lifecycle (like @PostConstruct / @PreDestroy) ---
    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        self._thread.join()                      # wait for the loop to finish

    # --- the background loop (the single writer) ---
    def _run(self):
        while not self._stop.is_set():
            try:
                value = self._source()
            except OSError:
                continue
            if value is None:
                continue
            with self._lock:
                self._window.append(value)
                accepted = self._find_latest_valid()
                if accepted is not None:         # nothing found: keep the previous value
                    self._latest = accepted

    def _find_latest_valid(self):
        """Scan the window backwards for the newest value repeated n times in a row."""
        w = self._window
        for i in range(len(w) - 1, self._n - 2, -1):
            key = w[i][:2]                       # value + unit; the status byte is ignored
            if all(w[i - k][:2] == key for k in range(1, self._n)):
                return w[i]
        return None

    # --- public API, safe to call from any thread ---
    def latest(self):
        """Last accepted value, or None before the first one. Lock-free."""
        return self._latest

    def snapshot(self):
        with self._lock:
            return list(self._window)            # a copy, so callers can't modify our state