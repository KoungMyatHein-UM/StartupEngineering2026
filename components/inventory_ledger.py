import threading
from collections import deque, namedtuple

Entry = namedtuple("Entry", ["timestamp", "delta", "item"])

MACROS = ("calories", "fat", "protein", "carbs")


class InventoryLedger:
    """A dumb class around a ledger: one base plus a window of the most recent entries.

    Each entry is (timestamp, delta, item). When the window holds more than `window`
    entries, the oldest one is compressed into the base: its delta is added to that item's
    grams in the base, and the entry itself is dropped. Entries are never edited.
    Everything else (grams, macros, servings) is derived from base + window on every query."""

    def __init__(self, nutrition_table, serving_table=None, window=10):
        """nutrition_table: per-gram macros per item handle, as returned by
        ItemDatabase.nutrition_table(), e.g.
        {"coke": {"calories": 0.42, "fat": 0.0, "protein": 0.0, "carbs": 0.106}}
        serving_table: grams per recommended serving per item handle, as returned by
        ItemDatabase.serving_table(), e.g. {"coke": 250, "nutella": 15}
        window: how many recent entries to keep before compressing into the base."""
        self._nutrition = dict(nutrition_table)          # own copy: later changes outside don't leak in
        self._servings = dict(serving_table or {})
        self._window_size = window
        self._base = {}                                   # item -> grams, from compressed entries
        self._window = deque()                            # the most recent entries, oldest first
        self._lock = threading.Lock()                     # written by the listener, read by the TUI

    def record(self, timestamp, delta, item):
        """Append one entry, compress the oldest into the base if the window is full, return it."""
        entry = Entry(timestamp, delta, item)
        with self._lock:
            self._window.append(entry)
            if len(self._window) > self._window_size:
                oldest = self._window.popleft()
                self._base[oldest.item] = self._base.get(oldest.item, 0) + oldest.delta
        return entry

    def base(self):
        """The compressed base: grams per item from entries that left the window (a copy)."""
        with self._lock:
            return dict(self._base)

    def entries(self):
        """The entries in the window, oldest first (a copy, so callers can't change the ledger)."""
        with self._lock:
            return list(self._window)

    def totals(self):
        """Derived: grams per item, base plus window, e.g. {"nutella": 625, "coke": 500}.
        Never below 0: scale jitter can make removals slightly larger than what was recorded."""
        with self._lock:
            totals = dict(self._base)
            for entry in self._window:
                totals[entry.item] = totals.get(entry.item, 0) + entry.delta
        return {item: max(0, grams) for item, grams in totals.items()}

    def item_macros(self):
        """Derived: calories, fat, protein and carbs per item, {item: {macro: value}}.
        Items missing from the nutrition table are left out."""
        result = {}
        for item, grams in self.totals().items():
            per_gram = self._nutrition.get(item)
            if per_gram is not None:
                result[item] = {macro: grams * per_gram.get(macro, 0.0) for macro in MACROS}
        return result

    def macros(self):
        """Derived: total calories, fat, protein and carbs in the inventory.
        Items missing from the nutrition table are left out."""
        result = dict.fromkeys(MACROS, 0.0)
        for per_item in self.item_macros().values():
            for macro in MACROS:
                result[macro] += per_item[macro]
        return result

    def macro(self, name):
        """Derived: one total, e.g. macro("calories")."""
        return self.macros()[name]

    def servings(self):
        """Derived: remaining recommended servings per item, as decimals,
        e.g. {"nutella": 41.7, "coke": 2.0}. Items without a serving size are left out."""
        return {item: grams / self._servings[item]
                for item, grams in self.totals().items() if item in self._servings}