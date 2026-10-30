"""Small math helpers."""
import math


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def angle_diff(a, b):
    """Shortest signed difference between two angles (radians)."""
    return (a - b + math.pi) % (2 * math.pi) - math.pi
