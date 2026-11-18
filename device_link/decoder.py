STATUS = {1: "fault", 2: "zero", 3: "in motion", 4: "stable",
          5: "under zero", 6: "overweight", 7: "needs calibration",
          8: "needs re-zeroing"}
UNITS = {2: "g", 11: "oz", 12: "lb"}


def decode(data):
    if not data or len(data) < 6:
        return None
    _report_id, status, unit, exp, lo, hi = data[:6]
    if exp > 127:                     # scaling exponent is a signed byte
        exp -= 256
    value = (lo | (hi << 8)) * (10 ** exp)
    if status == 5:                   # negative weight
        value = -value
    return value, UNITS.get(unit, f"unit {unit}"), STATUS.get(status, status)