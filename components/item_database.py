import json


class ItemDatabase:
    """A dumb read-only wrapper around items.json.

    The file maps item handles (the names the VLM answers with) to their data, e.g.
    {"coke": {"nutrition_per_gram": {"calories": 0.42, ...}, "serving_g": 250, "packaging_g": 40}}"""

    def __init__(self, path="items.json"):
        with open(path, encoding="utf-8") as f:
            self._items = json.load(f)

    def handles(self):
        """All item handles, e.g. ["coke", "nutella", "beef jerky"]. For the VLM's product list."""
        return list(self._items)

    def nutrition_per_gram(self, handle):
        """Per-gram macros of one item, e.g. {"calories": 0.42, "fat": 0.0, ...}."""
        return dict(self._items[handle]["nutrition_per_gram"])

    def nutrition_table(self):
        """Per-gram macros of every item, {handle: {...}}. For the ledger's constructor."""
        return {handle: self.nutrition_per_gram(handle) for handle in self._items}

    def serving_table(self):
        """Recommended serving size in grams of every item that has one, {handle: grams}.
        Items without a serving size (e.g. onions) are left out."""
        return {handle: data["serving_g"] for handle, data in self._items.items()
                if data.get("serving_g") is not None}


if __name__ == "__main__":
    import os
    import tempfile

    SAMPLE = {
        "coke": {"nutrition_per_gram": {"calories": 0.42, "fat": 0.0, "protein": 0.0, "carbs": 0.106},
                 "serving_g": 250, "packaging_g": 40},
        "nutella": {"nutrition_per_gram": {"calories": 5.39, "fat": 0.309, "protein": 0.063, "carbs": 0.575},
                    "serving_g": 15, "packaging_g": None},
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(SAMPLE, f)
        path = f.name
    try:
        db = ItemDatabase(path)

        # handles: all keys, in file order
        assert db.handles() == ["coke", "nutella"]

        # nutrition_per_gram: the per-gram macros of one item
        assert db.nutrition_per_gram("nutella") == SAMPLE["nutella"]["nutrition_per_gram"]

        # returned data is a copy: changing it doesn't change the database
        db.nutrition_per_gram("coke")["calories"] = 999
        assert db.nutrition_per_gram("coke")["calories"] == 0.42
        db.handles().append("pizza")
        assert db.handles() == ["coke", "nutella"]

        # nutrition_table: every item, only the macros (no serving or packaging fields)
        table = db.nutrition_table()
        assert set(table) == {"coke", "nutella"}
        assert table["coke"] == SAMPLE["coke"]["nutrition_per_gram"]

        # serving_table: grams per serving, only for items that have one
        assert db.serving_table() == {"coke": 250, "nutella": 15}

        # unknown handle: KeyError
        try:
            db.nutrition_per_gram("pizza")
            raise AssertionError("expected KeyError for an unknown handle")
        except KeyError:
            pass

        # the real file in the project, if present, loads and is complete
        if os.path.exists("items.json"):
            real = ItemDatabase("items.json")
            for handle in real.handles():
                macros = real.nutrition_per_gram(handle)
                assert set(macros) == {"calories", "fat", "protein", "carbs"}, handle

        print("All ItemDatabase tests passed.")
    finally:
        os.remove(path)