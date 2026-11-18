import cv2
import numpy as np


def split_pairs(pairs):
    """((base, new), (base, new), ...) -> ((base, base, ...), (new, new, ...))"""
    olds, news = zip(*pairs)
    return olds, news


def mask_to_difference(base, new, threshold=25):
    """Keep only the pixels that changed between base and new, in both frames, cropped to them.

    threshold: how much a pixel must change (0-255, greyscale) to count as changed.
    Returns (base, new) unchanged if nothing changed."""
    grey_base = cv2.GaussianBlur(cv2.cvtColor(base, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    grey_new = cv2.GaussianBlur(cv2.cvtColor(new, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    diff = cv2.absdiff(grey_base, grey_new)
    _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, np.ones((15, 15), np.uint8))   # close small gaps in the object
    points = cv2.findNonZero(mask)
    if points is None:
        return base, new
    x, y, w, h = cv2.boundingRect(points)                  # crop to the changed area
    return (cv2.bitwise_and(base, base, mask=mask)[y:y + h, x:x + w],
            cv2.bitwise_and(new, new, mask=mask)[y:y + h, x:x + w])


def side_by_side(base, new, old_name="before", new_name="after"):
    """Label copies of both frames "base" and "new" and put them next to each other.
    The originals are left untouched."""
    labelled = []
    for frame, label in ((base, old_name), (new, new_name)):
        frame = frame.copy()
        cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        labelled.append(frame)
    return np.hstack(labelled)