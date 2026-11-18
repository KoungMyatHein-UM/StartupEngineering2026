import cv2
import ollama


class VlmWrapper:
    """Asks a local VLM (via Ollama) which product was added to or removed from the crate.

    A plain tool class: it holds the settings and does work only when called.
    identify() blocks while the model thinks (a few seconds)."""

    def __init__(self, model, products, keep_alive="1h"):
        """model: Ollama model name, e.g. "qwen3-vl:8b".
        products: the closed list of product names the model may answer with.
        keep_alive: how long Ollama keeps the model loaded after a call."""
        self._model = model
        self._products = list(products)
        self._keep_alive = keep_alive

    def warm_up(self):
        """Load the model now, so the first identify() isn't slowed down by loading."""
        ollama.generate(model=self._model, prompt="", keep_alive=self._keep_alive)

    def identify(self, composites, delta):
        """composites: one side-by-side helper per camera (base left, new right).
        delta: weight change in grams (+ added, - removed), or None if unknown.
        Returns a product name from the list, or None if the answer isn't on the list."""
        if delta is None:
            action, verb = "An item changed.", "changed"
        elif delta > 0:
            action, verb = f"The weight went up by {delta:.0f} g, so an item was ADDED.", "added"
        else:
            action, verb = f"The weight went down by {-delta:.0f} g, so an item was REMOVED.", "removed"

        prompt = (
            "Each helper shows the same crate from one camera: BEFORE on the left (labelled "
            "'before') and AFTER on the right (labelled 'after').\n"
            f"{action}\n"
            f"Which of these products was {verb}: {', '.join(self._products)}?\n"
            "Answer with only the product name from the list, nothing else."
        )
        images = [cv2.imencode(".jpg", image)[1].tobytes() for image in composites]

        response = ollama.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt, "images": images}],
            think=False,
            keep_alive=self._keep_alive,
            options={"temperature": 0},          # same input -> same answer
        )
        return self._match(response.message.content)

    def _match(self, answer):
        """Map the model's free-text answer onto the product list (case-insensitive)."""
        text = answer.strip().strip(".").lower()
        for product in self._products:
            if text == product.lower():
                return product
        for product in self._products:            # e.g. "Almond oil bottle" -> "almond oil"
            if product.lower() in text:
                return product
        return None