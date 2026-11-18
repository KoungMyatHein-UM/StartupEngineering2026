import threading
import time
from dataclasses import dataclass

from helper.debug_log import log


@dataclass(frozen=True)
class WeightChange:
    """The data package passed to the callback. Raw fields only; delta is derived."""
    old: float          # weight before the step
    new: float          # weight after the step
    old_unit: str
    new_unit: str
    at: float           # when the step was detected (time.time())

    @property
    def delta(self):
        """new - old, or None if the scale switched units in between."""
        return self.new - self.old if self.old_unit == self.new_unit else None


class ListenerService:
    """Polls the reader and calls back when one step in the weight is at least `threshold`.

    Each accepted reading is compared with the previous accepted reading. Small steps
    below the threshold are ignored and do not add up.
    The callback runs on this service's thread and receives one WeightChange.
    The first reading only sets the starting point; it does not trigger the callback.
    """

    def __init__(self, source, callback, threshold, interval=0.01):
        self._source = source                    # cheap function returning (value, unit, status)
        self._callback = callback                # called as callback(change)
        self._threshold = threshold              # minimum |delta| to report, in the scale's unit
        self._interval = interval                # seconds between polls
        self._previous = None                    # last accepted reading seen
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="ListenerService")

    # --- lifecycle (like @PostConstruct / @PreDestroy) ---
    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join()

    def _is_step(self, old, new):
        if new[1] != old[1]:                     # unit switched on the scale: always report
            return True
        return abs(new[0] - old[0]) >= self._threshold

    # --- the background loop ---
    def _run(self):
        while not self._stop.is_set():
            reading = self._source()
            if reading is None and self._previous is not None:
                # The reader was reset (scale switched back on): the next value is a new start.
                log("reader reset; waiting for a new starting point")
                self._previous = None
            if reading is not None:
                old = self._previous
                if old is None:
                    log(f"starting point: {reading}")
                    self._previous = reading     # starting point, no callback
                elif reading[:2] != old[:2]:     # a new accepted value
                    self._previous = reading
                    step = self._is_step(old, reading)
                    log(f"new value {old[:2]} -> {reading[:2]}, step: {step}")
                    if step:
                        self._callback(WeightChange(old=old[0], new=reading[0],
                                                    old_unit=old[1], new_unit=reading[1],
                                                    at=time.time()))
            self._stop.wait(self._interval)      # returns early when stop() is called