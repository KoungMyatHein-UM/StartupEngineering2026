import queue
import sys

import cv2
import numpy as np

from helper import image_processing

# Fastest camera backend per OS
BACKEND = {"win32": cv2.CAP_DSHOW, "darwin": cv2.CAP_AVFOUNDATION}.get(sys.platform, cv2.CAP_ANY)


def find_cameras(max_index=6):
    """Return the indices of cameras that open and deliver a frame."""
    # MacBook: index 0 is the built-in camera. (On a Mac without one, 0 may be a USB camera.)
    skip = {0} if sys.platform == "darwin" else set()
    found = []
    for i in range(max_index):
        if i in skip:
            continue
        cap = cv2.VideoCapture(i, BACKEND)
        if cap.isOpened() and cap.read()[0]:
            found.append(i)
        cap.release()
    return found


class CameraService:
    """One read per camera at startup as the base. One read per camera on capture().
    capture() returns ((base, new), (base, new), ...) and replaces the base with new.

    Buffers are nuked: each camera is opened only for its read and released right after,
    so no old frames can pile up in a driver buffer between reads.

    Debug mode: every capture is also queued for display. Call show_debug() regularly
    from the MAIN thread to open/update one window per camera showing base | new."""

    def __init__(self, indices, debug=False):
        self._indices = list(indices)
        self._base = None                                 # one frame per camera
        self._debug = queue.Queue() if debug else None    # captures waiting to be shown

    # --- lifecycle ---
    def start(self):
        self._base = self._read()
        return self

    def stop(self):
        if self._debug is not None:
            cv2.destroyAllWindows()                       # must run on the main thread

    # --- public API ---
    def capture(self):
        new = self._read()
        pairs = tuple(zip(self._base, new))
        self._base = new
        if self._debug is not None:
            self._debug.put(pairs)
        return pairs

    # --- debug display ---
    def show_debug(self, wait_ms=1):
        """Call regularly from the MAIN thread. Shows the newest capture: base | new."""
        if self._debug is None:
            return
        pairs = None
        while True:                                       # skip to the newest capture
            try:
                pairs = self._debug.get_nowait()
            except queue.Empty:
                break
        if pairs is not None:
            for index, (base, new) in zip(self._indices, pairs):
                cv2.imshow(f"camera {index}: base | new", image_processing.side_by_side(base, new))
        cv2.waitKey(wait_ms)

    # --- internals ---
    def _read(self):
        """Open each camera (fresh, empty buffer), read one frame, release it again."""
        frames = []
        for i in self._indices:
            cap = cv2.VideoCapture(i, BACKEND)
            try:
                if not cap.isOpened():
                    raise RuntimeError(f"camera {i} did not open")
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"camera {i} did not deliver a frame")
                frames.append(frame)
            finally:
                cap.release()                             # nuke: nothing can buffer while closed
        return tuple(frames)