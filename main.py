import time
import hid
from rich.live import Live

from services.link.device_link import parser
from helper import image_processing, tui
from helper.debug_log import log
from helper.vlm_wrapper import VlmWrapper
from services.data.listener_service import ListenerService
from services.link.reader_service import ReaderService
from components.camera_reader import CameraService, find_cameras
from components.inventory_ledger import InventoryLedger
from components.item_database import ItemDatabase

ITEMS_PATH = "data/items.json"


def split_pairs(pairs):
    """((base, new), (base, new), ...) -> ((base, base, ...), (new, new, ...))"""
    olds, news = zip(*pairs)
    return olds, news


def log_inventory(ledger):
    """Log the current inventory: grams and servings per item, and the macro totals."""
    servings = ledger.servings()
    for item, grams in ledger.totals().items():
        serving_text = f", {servings[item]:.2f} servings" if item in servings else ""
        log(f"  {item}: {grams:.0f} g{serving_text}")
    macros = ledger.macros()
    log("  TOTAL: " + ", ".join(f"{name} {value:.1f}" for name, value in macros.items()))


def on_change(data, cameras, vision, ledger):
    old = data.old
    new = data.new
    at = data.at
    delta = data.delta

    log(f"Weight changed from {old} to {new} with a delta of {delta}")

    t = time.time()
    pairs = cameras.capture()
    log(f"Captured {len(pairs)} camera(s) in {time.time() - t:.2f} s")

    composites = [image_processing.side_by_side(base, new) for base, new in pairs]

    t = time.time()
    log("Asking the VLM...")
    product = vision.identify(composites, delta)
    log(f"VLM answered in {time.time() - t:.2f} s: {product}")

    log(f"RESULT: {product}: {delta:+} g")

    if product in (None, "nothing") or delta is None:
        log("Inventory unchanged (nothing identified)")
        return
    entry = ledger.record(at, delta, product)
    log(f"Ledger entry recorded: {entry}")
    log_inventory(ledger)


def main():
    log("Starting up")
    devs = hid.enumerate(0x0922)
    if not devs:
        raise SystemExit("No Dymo scale found. Is it switched on?")
    log(f"Scale found: {devs[0]['product_string']}")

    dev = hid.device()

    reader_service = ReaderService(lambda: parser.read_weight(dev), window=10)

    t = time.time()
    camera_indices = find_cameras()
    log(f"Cameras found: {camera_indices} ({time.time() - t:.2f} s)")
    cameras = CameraService(camera_indices, debug=True)

    t = time.time()
    log(f"Loading the item database from {ITEMS_PATH}...")
    database = ItemDatabase(ITEMS_PATH)
    items = database.handles()
    log(f"Item database loaded ({time.time() - t:.2f} s): {len(items)} items: {', '.join(items)}")

    ledger = InventoryLedger(database.nutrition_table(), database.serving_table(), window=10)
    log("Inventory ledger created (window: 10 entries)")

    log("Loading the VLM...")
    vision = VlmWrapper("qwen3-vl:8b-instruct", items + ["nothing"])
    t = time.time()
    log(f"VLM ready ({time.time() - t:.2f} s)")

    listener_service = ListenerService(reader_service.latest,
                                       callback=lambda data: on_change(data, cameras, vision, ledger),
                                       threshold=10)

    try:
        dev.open_path(devs[0]["path"])
        log("Scale opened")
        reader_service.start()
        log("Reader service started")

        t = time.time()
        cameras.start()
        log(f"Cameras started, base pictures taken ({time.time() - t:.2f} s)")

        listener_service.start()
        log("Listener service started")

        # The TUI redraws in place at the bottom; log lines appear above it.
        with Live(tui.render(ledger, "waiting for scale", None),
                  refresh_per_second=4, redirect_stdout=True) as live:
            if reader_service.latest() is None:
                log("Waiting for the scale (switch it on if it's off)...")
                while reader_service.latest() is None:
                    cameras.show_debug()
                    live.update(tui.render(ledger, "waiting for scale", None))
                    time.sleep(0.05)

            log(f"ALL READY. Current weight: {reader_service.latest()}")

            while True:
                cameras.show_debug()
                live.update(tui.render(ledger, "ready", reader_service.latest()))
                time.sleep(0.05)

    except KeyboardInterrupt:
        log("Ctrl+C pressed")

    finally:
        log("Shutting down")
        listener_service.stop()
        cameras.stop()
        reader_service.stop()
        dev.close()
        log("Stopped")


if __name__ == "__main__":
    main()