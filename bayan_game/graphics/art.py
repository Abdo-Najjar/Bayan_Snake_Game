"""Backgrounds and small drawing helpers (hearts, stars, gems, coins, icons)."""
import math
import random

import pygame
from pygame import gfxdraw

from ..config import W, H, TOP


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


# ---------------------------------------------------------------- smooth shapes
def aa_circle(surf, color, center, radius, width=0):
    """Circle with anti-aliased (smooth) edges. width > 0 draws only the outline."""
    x, y, r = int(center[0]), int(center[1]), int(radius)
    if r < 1:
        return
    if not width:
        gfxdraw.filled_circle(surf, x, y, r, color)
    gfxdraw.aacircle(surf, x, y, r, color)
    for i in range(1, width):
        gfxdraw.aacircle(surf, x, y, r - i, color)


def aa_polygon(surf, color, points, width=0):
    """Polygon with anti-aliased edges. width > 0 draws only the outline."""
    pts = [(int(round(px)), int(round(py))) for px, py in points]
    if not width:
        gfxdraw.filled_polygon(surf, pts, color)
    gfxdraw.aapolygon(surf, pts, color)


_vignette = {}


def vignette(size, strength=150):
    """Darkens the screen edges a little to give depth."""
    key = (size, strength)
    if key not in _vignette:
        sw, sh = 96, 64
        small = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(sh):
            for x in range(sw):
                dx = (x + 0.5) / sw * 2 - 1
                dy = (y + 0.5) / sh * 2 - 1
                d = math.sqrt(dx * dx + dy * dy) / math.sqrt(2)
                a = max(0.0, (d - 0.45) / 0.55) ** 2
                small.set_at((x, y), (0, 0, 0, int(strength * a)))
        _vignette[key] = pygame.transform.smoothscale(small, size)
    return _vignette[key]


# ---------------------------------------------------------------- backgrounds
_SEEDS = {"grass": 7, "desert": 11, "snow": 23, "forest": 31, "lair": 47}
_bg_cache = {}


def background(terrain):
    if terrain not in _bg_cache:
        _bg_cache[terrain] = _make_background(terrain)
    return _bg_cache[terrain]


def _flower(bg, rnd, x, y):
    c = rnd.choice([(255, 255, 255), (255, 230, 80), (255, 150, 200)])
    for a in range(5):
        ang = a / 5 * 2 * math.pi
        pygame.draw.circle(bg, c, (int(x + math.cos(ang) * 3), int(y + math.sin(ang) * 3)), 2)
    pygame.draw.circle(bg, (250, 200, 40), (x, y), 2)


def _make_background(terrain):
    bg = pygame.Surface((W, H))
    rnd = random.Random(_SEEDS.get(terrain, 1))

    def spot():
        return rnd.randrange(W), rnd.randrange(TOP, H)

    if terrain == "grass":
        bg.fill((110, 190, 90))
        for _ in range(500):
            x, y = spot()
            c = rnd.choice([(95, 170, 75), (125, 205, 100), (100, 180, 80)])
            pygame.draw.line(bg, c, (x, y), (x + rnd.randint(-3, 3), y - rnd.randint(4, 9)), 2)
        for _ in range(40):
            _flower(bg, rnd, *spot())

    elif terrain == "desert":
        bg.fill((233, 201, 140))
        for _ in range(700):
            x, y = spot()
            pygame.draw.circle(bg, rnd.choice([(218, 182, 118), (245, 220, 165)]), (x, y), rnd.randint(1, 2))
        for _ in range(30):
            x, y = spot()
            w = rnd.randint(60, 160)
            pygame.draw.arc(bg, (214, 176, 110), (x, y, w, w // 3), 0.3, 2.8, 2)
        for _ in range(8):
            x, y = spot()
            g, d = (80, 150, 70), (55, 115, 50)
            pygame.draw.rect(bg, g, (x - 4, y - 22, 8, 24), border_radius=4)
            pygame.draw.rect(bg, g, (x - 13, y - 14, 6, 10), border_radius=3)
            pygame.draw.rect(bg, g, (x + 7, y - 18, 6, 10), border_radius=3)
            pygame.draw.line(bg, d, (x, y - 20), (x, y), 1)

    elif terrain == "snow":
        bg.fill((226, 238, 248))
        for _ in range(14):
            x, y = spot()
            w = rnd.randint(80, 200)
            pygame.draw.ellipse(bg, (205, 228, 245), (x - w // 2, y - w // 6, w, w // 3))
            pygame.draw.line(bg, (250, 252, 255), (x - w // 4, y - 3), (x + w // 6, y - 6), 2)
        for _ in range(450):
            x, y = spot()
            pygame.draw.circle(bg, rnd.choice([(255, 255, 255), (205, 222, 240)]), (x, y), rnd.randint(1, 3))

    elif terrain == "forest":
        bg.fill((66, 120, 62))
        for _ in range(700):
            x, y = spot()
            pygame.draw.ellipse(bg, rnd.choice([(55, 100, 50), (90, 150, 80), (75, 135, 60)]), (x, y, 5, 3))
        for _ in range(16):
            x, y = spot()
            pygame.draw.rect(bg, (240, 230, 210), (x - 2, y - 4, 4, 7))
            pygame.draw.ellipse(bg, (210, 50, 50), (x - 7, y - 9, 14, 8))
            pygame.draw.circle(bg, (255, 255, 255), (x - 2, y - 6), 1)
            pygame.draw.circle(bg, (255, 255, 255), (x + 3, y - 7), 1)

    else:  # lair
        bg.fill((52, 36, 40))
        for _ in range(400):
            x, y = spot()
            pygame.draw.circle(bg, rnd.choice([(40, 28, 32), (66, 46, 50)]), (x, y), rnd.randint(1, 3))
        for _ in range(20):
            x, y = spot()
            pts = [(x, y)]
            for _ in range(rnd.randint(3, 6)):
                x += rnd.randint(-30, 30)
                y += rnd.randint(-20, 20)
                pts.append((x, y))
            pygame.draw.lines(bg, (130, 55, 30), False, pts, 6)
            pygame.draw.lines(bg, (255, 130, 40), False, pts, 2)
    return bg


# ---------------------------------------------------------------- icons (PNG sprites)
def _blit_icon(surf, name, cx, cy, size):
    from .sprites import bank   # imported here: sprites need the window to exist first
    img = bank().icon(name, size)
    surf.blit(img, img.get_rect(center=(round(cx), round(cy))))


def draw_heart(surf, x, y, size, filled=True):
    _blit_icon(surf, "heart" if filled else "heart_empty", x, y + size * 0.15, size * 1.5)


def star_points(cx, cy, r, inner=0.45, rot=-math.pi / 2):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * inner
        a = rot + i * math.pi / 5
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts


def draw_star(surf, cx, cy, r, filled=True):
    _blit_icon(surf, "star" if filled else "star_empty", cx, cy, r * 2.5)


def draw_gem(surf, pos, t, size=12):
    pulse = 1 + math.sin(t * 6) * 0.08
    glow = pygame.Surface((80, 80), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 240, 120, 60), (40, 40), int(size * 2.2 * pulse))
    surf.blit(glow, (pos[0] - 40, pos[1] - 40))
    _blit_icon(surf, "gem", pos[0], pos[1] + math.sin(t * 3) * 2, int(size * 2.6 * pulse / 2) * 2)


def draw_coin(surf, x, y, r=9):
    _blit_icon(surf, "coin", x, y, r * 2.6)


def draw_lock(surf, x, y, size=16, color=None):
    _blit_icon(surf, "lock", x, y - size * 0.3, size * 2.4)


POWER_COLORS = {
    "speed": (255, 200, 40),
    "shield": (80, 160, 255),
    "freeze": (130, 220, 255),
    "ghost": (200, 200, 240),
}


def draw_power_icon(surf, kind, cx, cy, size=12):
    _blit_icon(surf, kind, cx, cy, size * 2.6)
