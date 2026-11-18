from .decoder import decode


def read_weight(dev):
    """Wait for the next report (up to 1 s)."""
    return decode(dev.read(6, 1000))

def read_latest(dev):
    """Wait for a report, then clear the queue and return the newest one."""
    data = dev.read(6, 1000)
    if not data:
        return None
    dev.set_nonblocking(True)
    try:
        while True:
            more = dev.read(6)        # returns [] once the queue is empty
            if not more:
                break
            data = more
    finally:
        dev.set_nonblocking(False)
    return decode(data)

