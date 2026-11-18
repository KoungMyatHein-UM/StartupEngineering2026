import threading
from collections import deque

from helper.debug_log import log


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
        if self._thread.is_alive():
            self._thread.join()                   # wait for the loop to finish

    # --- the background loop (the single writer) ---
    def _run(self):
        last_raw = None
        last_error = None
        while not self._stop.is_set():
            try:
                value = self._source()
            except OSError as e:                         # includes ScaleOffError
                if str(e) != last_error:                 # log each new error once, not every report
                    log(f"read error: {e}")
                    last_error = str(e)
                continue
            if last_error is not None:
                log("reading again")
                last_error = None
            if value is None:
                continue
            if value != last_raw:                        # only log changes, not every report
                log(f"raw report: {value}")
                last_raw = value
            with self._lock:
                self._window.append(value)
                accepted = self._find_latest_valid()
                if accepted is not None:         # nothing found: keep the previous value
                    if self._latest is None or accepted[:2] != self._latest[:2]:
                        log(f"accepted: {accepted}")
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