import time
import hid

from device_link import parser
from helper import image_processing
from helper.debug_log import log
from helper.vlm_wrapper import VlmWrapper
from services.data.listener_service import ListenerService
from services.link.reader_service import ReaderService
from services.vision.camera_service import CameraService, find_cameras


def split_pairs(pairs):
    """((base, new), (base, new), ...) -> ((base, base, ...), (new, new, ...))"""
    olds, news = zip(*pairs)
    return olds, news


def on_change(data, cameras, vision):
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

    vision = VlmWrapper("qwen3-vl:8b", ["almond oil", "coke", "butter"])
    t = time.time()
    log("Loading the VLM...")
    vision.warm_up()
    log(f"VLM ready ({time.time() - t:.2f} s)")

    listener_service = ListenerService(reader_service.latest,
                                       callback=lambda data: on_change(data, cameras, vision),
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

        log(f"ALL READY. Current weight: {reader_service.latest()}")

        while True:
            cameras.show_debug()
            time.sleep(0.05)

    finally:
        log("Shutting down")
        listener_service.stop()
        cameras.stop()
        reader_service.stop()
        dev.close()
        log("Stopped")


if __name__ == "__main__":
    main()