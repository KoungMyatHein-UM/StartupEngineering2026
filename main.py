import time
import hid

from device_link import parser
from reader_service import ReaderService

devs = hid.enumerate(0x0922)
if not devs:
    raise SystemExit("No Dymo scale found. Is it switched on?")

dev = hid.device()
dev.open_path(devs[0]["path"])

reader_service = ReaderService(lambda: parser.read_weight(dev), window=10)
reader_service.start()

try:
    while True:
        r = reader_service.latest()
        if r:
            print(r)
            pass
        time.sleep(0.1)
finally:
    reader_service.stop()
    dev.close()