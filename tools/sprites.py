"""Draws the game's PNG sprites into bayan_game/assets/sprites.

Everything is drawn at 4x the in-game size, so it stays smooth when the game scales it down.
The PNGs can be replaced with hand-drawn art as long as the sizes and frame layout stay the same
(see README.md).
"""
import json
import math
import os
import random

import pygame

S = 4                                   # supersampling factor
OUTLINE = (55, 30, 40)
SKIN, SKIN_SHADE = (255, 218, 182), (238, 186, 150)
HAIR, HAIR_LIGHT = (84, 50, 30), (138, 88, 54)
GRAY, GRAY_SHADE, GRAY_DARK = (240, 240, 240), (205, 205, 205), (180, 180, 180)

# Bayan sheet layout
FW, FH = 64 * S, 80 * S                  # one frame
OX, OY = 32 * S, 50 * S                  # body center inside a frame
FRAMES = 5                               # idle + 4 walking frames
SWING = [0, 4, 0, -4, 0]                 # leg swing per frame
BOUNCE = [0, 1, 0, -1, 0]                # ponytail bounce per frame
DIRECTIONS = ("down", "up", "side")      # side faces right; the game mirrors it for left


# ================================================================ helpers
def surface(w, h):
    return pygame.Surface((int(w), int(h)), pygame.SRCALPHA)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def lighten(c, k):
    return lerp(c[:3], (255, 255, 255), k)


def add_outline(surf, color=OUTLINE, thickness=S):
    """Cartoon outline: the shape's silhouette, grown by `thickness`, drawn behind it."""
    mask = pygame.mask.from_surface(surf, 20)
    sil = mask.to_surface(setcolor=(*color[:3], 255), unsetcolor=(0, 0, 0, 0))
    out = surface(*surf.get_size())
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx * dx + dy * dy <= thickness * thickness:
                out.blit(sil, (dx, dy))
    out.blit(surf, (0, 0))
    return out


def blend(surf, draw_fn, color, *args):
    """Draws a translucent shape blended onto surf (pygame.draw alone would overwrite alpha)."""
    tmp = surface(*surf.get_size())
    draw_fn(tmp, color, *args)
    surf.blit(tmp, (0, 0))


def shaded_circle(surf, center, r, light, dark, shine=True):
    """A ball lit from the top-left: dark rim, lighter middle, small white shine."""
    cx, cy = center
    steps = max(8, int(r / 2))
    for i in range(steps):
        k = i / steps
        rr = r * (1 - 0.78 * k)
        off = r * 0.28 * k
        pygame.draw.circle(surf, lerp(dark, light, k), (cx - off, cy - off), rr)
    if shine:
        blend(surf, pygame.draw.ellipse, (255, 255, 255, 120),
              pygame.Rect(cx - r * 0.55, cy - r * 0.62, r * 0.55, r * 0.32))


def limb(surf, a, b, width, color):
    pygame.draw.line(surf, color, a, b, int(width))
    pygame.draw.circle(surf, color, a, width / 2)
    pygame.draw.circle(surf, color, b, width / 2)


def save(surf, *parts):
    path = os.path.join(*parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pygame.image.save(surf, path)


# ================================================================ Bayan
def P(x, y):
    """Design coordinates (in-game pixels around the body center) -> sheet pixels."""
    return (OX + x * S, OY + y * S)


def R(x, y, w, h):
    return pygame.Rect(OX + x * S, OY + y * S, w * S, h * S)


def clip_above(surf, y):
    surf.set_clip(pygame.Rect(0, 0, FW, OY + y * S))


def clip_left_of(surf, x):
    surf.set_clip(pygame.Rect(0, 0, OX + x * S, FH))


def draw_shadow(fr, f, d):
    blend(fr, pygame.draw.ellipse, (0, 0, 0, 60), R(-12, 12, 24, 7))


def draw_legs(fr, f, d):
    sw = SWING[f]
    shoe = (150, 60, 95)
    if d == "side":
        for x0, k, color in ((-1, -1, SKIN_SHADE), (1, 1, SKIN)):
            end = (x0 + k * sw * 0.8, 15.5)
            limb(fr, P(x0, 8), P(*end), 3.4 * S, color)
            pygame.draw.ellipse(fr, shade(shoe, 0.85 if k < 0 else 1), R(end[0] - 2, end[1] - 1, 6, 3.6))
    else:
        for x0, lift in ((-4, max(0, sw) * 0.45), (4, max(0, -sw) * 0.45)):
            end = (x0, 15.5 - lift)
            limb(fr, P(x0, 8), P(*end), 3.4 * S, SKIN)
            pygame.draw.ellipse(fr, shoe, R(end[0] - 3, end[1] - 1, 6, 3.6))


def draw_arms(fr, f, d):
    sw = SWING[f]
    if d == "side":
        hand = (1 - sw * 0.9, 4)
        limb(fr, P(1, -4), P(*hand), 3 * S, SKIN)
        pygame.draw.circle(fr, SKIN, P(*hand), 2 * S)
    else:
        for side in (-1, 1):
            hand = (side * 10.5 - side * sw * 0.35, 4)
            limb(fr, P(side * 6, -4), P(*hand), 3 * S, SKIN)
            pygame.draw.circle(fr, SKIN, P(*hand), 2 * S)


def dress_shape(d):
    if d == "side":
        return [(-3, -9), (3, -9), (5, -6), (9.5, 9.5), (5, 12), (-5, 12), (-9.5, 9.5), (-5, -6)]
    return [(-3.5, -9), (3.5, -9), (6.5, -6), (12, 9), (8, 11.5), (0, 12.5), (-8, 11.5), (-12, 9), (-6.5, -6)]


def draw_dress(fr, f, d):
    pts = [P(*p) for p in dress_shape(d)]
    pygame.draw.polygon(fr, GRAY, pts)
    fr.set_clip(pygame.Rect(OX + 2 * S, 0, FW, FH))       # shade the right side
    pygame.draw.polygon(fr, GRAY_SHADE, pts)
    fr.set_clip(None)
    for x0, x1 in ((-2.5, -6), (2.5, 6)):                 # folds
        pygame.draw.line(fr, GRAY_DARK, P(x0, -3), P(x1, 10), int(0.8 * S))
    sleeves = [(1, -5.5)] if d == "side" else [(-6, -5.5), (6, -5.5)]
    for sx, sy in sleeves:
        shaded_circle(fr, P(sx, sy), 3.3 * S, GRAY, GRAY_SHADE, shine=False)


def draw_dress_trim(fr, f, d):
    if d == "side":
        band = [(-8.5, 8.5), (-4, 10.3), (4, 10.3), (8.5, 8.5)]
    else:
        band = [(-11, 8), (-6, 10), (0, 10.8), (6, 10), (11, 8)]
    pygame.draw.lines(fr, (255, 255, 255), False, [P(*p) for p in band], int(1.6 * S))
    if d == "down":
        pygame.draw.circle(fr, (255, 255, 255), P(0, -9), 2.6 * S, int(S))


def draw_head(fr, f, d):
    if d == "up":
        return
    cx = 1.5 if d == "side" else 0
    shaded_circle(fr, P(cx, -14.5), 8 * S, SKIN, SKIN_SHADE, shine=False)
    eyes = [(4.6, -15)] if d == "side" else [(-3, -15), (3, -15)]
    for ex, ey in eyes:
        pygame.draw.ellipse(fr, (35, 25, 40), R(ex - 1.25, ey - 1.8, 2.5, 3.6))
        pygame.draw.circle(fr, (255, 255, 255), P(ex + 0.35, ey - 0.8), 0.75 * S)
    cheeks = [(5.6, -11.8)] if d == "side" else [(-5, -11.8), (5, -11.8)]
    for bx, by in cheeks:
        blend(fr, pygame.draw.ellipse, (255, 120, 140, 130), R(bx - 1.6, by - 0.9, 3.2, 1.8))
    mx = 4.2 if d == "side" else 0
    pygame.draw.arc(fr, (170, 60, 70), R(mx - 1.6, -13.4, 3.2, 2.4), math.pi + 0.25, 2 * math.pi - 0.25,
                    int(0.7 * S))


def draw_hair_back(fr, f, d):
    b = BOUNCE[f]
    tie = (235, 60, 100)
    if d == "up":
        shaded_circle(fr, P(0, -8.5 + b), 5.4 * S, HAIR_LIGHT, HAIR, shine=False)
        pygame.draw.circle(fr, tie, P(0, -12.3), 1.7 * S)
    else:
        tx = -10.5
        shaded_circle(fr, P(tx, -13 + b), 5.2 * S, HAIR_LIGHT, HAIR, shine=False)
        pygame.draw.circle(fr, tie, P(-7.6, -15.2), 1.7 * S)
    shaded_circle(fr, P(-0.5 if d == "side" else 0, -17), 10.5 * S, HAIR_LIGHT, HAIR, shine=False)


def draw_hair_front(fr, f, d):
    if d == "up":
        shaded_circle(fr, P(0, -17), 10.5 * S, HAIR_LIGHT, HAIR, shine=False)
        pygame.draw.line(fr, shade(HAIR, 0.8), P(0, -27), P(0, -19), int(0.8 * S))
        return
    cx = 1.5 if d == "side" else 0
    clip_above(fr, -15.8)
    shaded_circle(fr, P(cx - 0.3, -17.5), 9.7 * S, HAIR_LIGHT, HAIR, shine=False)
    fr.set_clip(None)
    strands = (-3, 0.5, 4, 7) if d == "side" else (-5.5, -2, 2, 5.5)
    for x in strands:
        pygame.draw.polygon(fr, HAIR, [P(x - 2, -16.2), P(x + 2, -16.2), P(x + 0.3, -13.8)])
    if d == "side":
        clip_left_of(fr, cx - 3.2)
        shaded_circle(fr, P(cx - 0.3, -17.5), 9.7 * S, HAIR_LIGHT, HAIR, shine=False)
        fr.set_clip(None)
    blend(fr, pygame.draw.arc, (255, 255, 255, 90), R(-6, -25, 9, 6), 1.9, 2.9, int(1.1 * S))


# ---- hats (drawn once per direction, the same in every frame)
def hat_bow(fr, f, d):
    cx = -1.5 if d == "side" else 0
    cy = -26.5
    red, dark = (238, 64, 104), (196, 40, 80)
    for side in (-1, 1):
        pygame.draw.polygon(fr, red, [P(cx, cy), P(cx + side * 6.5, cy - 4), P(cx + side * 7, cy + 3.5)])
        pygame.draw.polygon(fr, dark, [P(cx, cy), P(cx + side * 7, cy + 3.5), P(cx + side * 5, cy + 1)])
    pygame.draw.circle(fr, (255, 190, 210), P(cx, cy), 2 * S)


def hat_flower(fr, f, d):
    cx, cy = {"down": (6.5, -24), "side": (-2, -25.5), "up": (-6.5, -24)}[d]
    for i in range(5):
        a = i / 5 * 2 * math.pi - math.pi / 2
        shaded_circle(fr, P(cx + math.cos(a) * 3.2, cy + math.sin(a) * 3.2), 2.8 * S,
                      (255, 190, 215), (240, 110, 160), shine=False)
    shaded_circle(fr, P(cx, cy), 1.9 * S, (255, 235, 120), (240, 180, 40), shine=False)


def hat_crown(fr, f, d):
    w = 0.8 if d == "side" else 1.0
    cx = -1 if d == "side" else 0
    base_y = -24
    shape = [(-8, 0), (-8, -8), (-4, -4), (0, -10), (4, -4), (8, -8), (8, 0)]
    pts = [P(cx + x * w, base_y + y) for x, y in shape]
    pygame.draw.polygon(fr, (252, 210, 70), pts)
    pygame.draw.rect(fr, (232, 170, 40), R(cx - 8 * w, base_y - 2.5, 16 * w, 2.5))
    for x, y in ((-8, -8), (0, -10), (8, -8)):
        pygame.draw.circle(fr, (255, 240, 160), P(cx + x * w, base_y + y), 1.2 * S)
    pygame.draw.circle(fr, (230, 40, 70), P(cx, base_y - 3.5), 1.4 * S)
    for x in (-5, 5):
        pygame.draw.circle(fr, (70, 150, 255), P(cx + x * w, base_y - 2.5), 1 * S)


def hat_cap(fr, f, d):
    fr.set_clip(pygame.Rect(0, 0, FW, OY - 20.3 * S))
    shaded_circle(fr, P(0, -19.5), 10.8 * S, GRAY, GRAY_SHADE, shine=False)
    fr.set_clip(None)
    if d == "down":
        pygame.draw.ellipse(fr, GRAY_SHADE, R(-9, -22.2, 18, 4.4))
    elif d == "side":
        pygame.draw.ellipse(fr, GRAY_SHADE, R(3, -22.5, 12, 4))
    pygame.draw.circle(fr, GRAY_DARK, P(0, -30), 1.3 * S)


def hijab_back(fr, f, d):
    pygame.draw.polygon(fr, GRAY_SHADE, [P(-10, -17), P(10, -17), P(12.5, -2), P(0, 0.5), P(-12.5, -2)])
    shaded_circle(fr, P(0, -17), 11.2 * S, GRAY, GRAY_SHADE, shine=False)


def hijab_front(fr, f, d):
    shaded_circle(fr, P(0, -17), 11.2 * S, GRAY, GRAY_SHADE, shine=False)
    if d == "down":
        pygame.draw.ellipse(fr, (0, 0, 0, 0), R(-6.8, -21.8, 13.6, 15.5))
    elif d == "side":
        pygame.draw.ellipse(fr, (0, 0, 0, 0), R(-2.8, -21.6, 11.5, 15))


BAYAN_LAYERS = {
    "shadow": (draw_shadow, False),
    "legs": (draw_legs, True),
    "dress": (draw_dress, True),
    "dress_trim": (draw_dress_trim, False),
    "arms": (draw_arms, True),
    "hair_back": (draw_hair_back, True),
    "head": (draw_head, True),
    "hair_front": (draw_hair_front, True),
    "hat_bow": (hat_bow, True),
    "hat_flower": (hat_flower, True),
    "hat_crown": (hat_crown, True),
    "hat_cap": (hat_cap, True),
    "hijab_back": (hijab_back, True),
    "hijab_front": (hijab_front, True),
}


def build_bayan(out_dir):
    for d in DIRECTIONS:
        for name, (draw, outline) in BAYAN_LAYERS.items():
            sheet = surface(FW * FRAMES, FH)
            for f in range(FRAMES):
                fr = surface(FW, FH)
                draw(fr, f, d)
                if outline:
                    fr = add_outline(fr)
                sheet.blit(fr, (f * FW, 0))
            save(sheet, out_dir, "bayan", d, f"{name}.png")
    manifest = dict(scale=S, frame_size=[FW, FH], frames=FRAMES, anchor=[OX, OY], directions=list(DIRECTIONS))
    with open(os.path.join(out_dir, "bayan", "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)


# ================================================================ snakes
SNAKES = {
    "normal": dict(r=13, c1=(60, 170, 70), c2=(40, 130, 50), pattern="diamond"),
    "small": dict(r=9, c1=(232, 200, 60), c2=(196, 160, 40), pattern="speckle"),
    "lunger": dict(r=13, c1=(222, 82, 62), c2=(172, 52, 42), pattern="ring"),
    "poison": dict(r=13, c1=(152, 92, 204), c2=(112, 62, 162), pattern="dots"),
    "boss": dict(r=24, c1=(132, 46, 58), c2=(86, 28, 40), pattern="gold"),
}


def snake_segment(r, color, pattern, seed):
    size = int((r + 3) * 2 * S)
    s = surface(size, size)
    c = (size / 2, size / 2)
    rr = r * S
    shaded_circle(s, c, rr, lighten(color, 0.3), shade(color, 0.72))
    rnd = random.Random(seed)
    light = lighten(color, 0.45)
    if pattern == "diamond":
        k = rr * 0.38
        pygame.draw.polygon(s, light, [(c[0], c[1] - k), (c[0] + k, c[1]), (c[0], c[1] + k), (c[0] - k, c[1])])
    elif pattern == "speckle":
        for _ in range(5):
            a, dist = rnd.uniform(0, 6.3), rnd.uniform(0, rr * 0.6)
            pygame.draw.circle(s, shade(color, 0.6), (c[0] + math.cos(a) * dist, c[1] + math.sin(a) * dist), rr * 0.12)
    elif pattern == "ring":
        pygame.draw.circle(s, shade(color, 0.55), c, rr * 0.6, int(rr * 0.16))
    elif pattern == "dots":
        for dx, dy in ((-0.3, -0.2), (0.3, 0.25)):
            pygame.draw.circle(s, light, (c[0] + dx * rr, c[1] + dy * rr), rr * 0.18)
    elif pattern == "gold":
        shaded_circle(s, c, rr * 0.34, (255, 225, 120), (210, 150, 50))
    return add_outline(s, shade(color, 0.42), S)


def snake_head(spec, state, boss=False):
    r = spec["r"]
    c1, c2 = spec["c1"], spec["c2"]
    size = int((r * 1.7 + (r * 0.9 if boss else 0)) * 2 * S)
    s = surface(size, size)
    cx, cy = size / 2, size / 2
    rr = r * S

    def H(x, y):  # head coordinates in units of r, x points forward
        return (cx + x * rr, cy + y * rr)

    if boss:
        bone, bone_dark = (238, 228, 205), (196, 180, 152)
        for side in (-1, 1):
            horn = [H(-0.15, side * 0.62), H(-0.55, side * 0.42), H(-1.35, side * 1.2)]
            pygame.draw.polygon(s, bone, horn)
            pygame.draw.polygon(s, bone_dark, [H(-0.35, side * 0.52), H(-0.55, side * 0.42), H(-1.35, side * 1.2)])

    ball = surface(rr * 2 + 8, rr * 2 + 8)
    shaded_circle(ball, (rr + 4, rr + 4), rr, lighten(c1, 0.3), shade(c1, 0.72))
    ball = pygame.transform.smoothscale(ball, (int((rr * 2 + 8) * 1.18), rr * 2 + 8))
    s.blit(ball, ball.get_rect(center=(cx + rr * 0.08, cy)))
    pygame.draw.ellipse(s, lighten(c1, 0.25), pygame.Rect(H(-0.55, -0.22), (rr * 0.6, rr * 0.44)))

    for side in (-1, 1):                                   # nostrils
        pygame.draw.circle(s, shade(c2, 0.6), H(0.95, side * 0.2), rr * 0.07)
    eye_r = rr * (0.26 if boss else 0.31)
    for side in (-1, 1):
        ex, ey = H(0.33, side * 0.46)
        if state == "closed":
            pygame.draw.arc(s, shade(c2, 0.4), pygame.Rect(ex - eye_r, ey - eye_r * 0.6, eye_r * 2, eye_r * 1.4),
                            math.pi * 1.1, math.pi * 1.9, int(S * 1.2))
            continue
        sclera = (255, 92, 80) if state == "angry" else (255, 236, 120)
        shaded_circle(s, (ex, ey), eye_r, sclera, shade(sclera, 0.8), shine=False)
        pygame.draw.ellipse(s, (25, 20, 25), pygame.Rect(ex - eye_r * 0.2 + eye_r * 0.25, ey - eye_r * 0.75,
                                                         eye_r * 0.4, eye_r * 1.5))
        pygame.draw.circle(s, (255, 255, 255), (ex - eye_r * 0.25, ey - eye_r * 0.4), eye_r * 0.25)
        if state == "angry":
            pygame.draw.line(s, shade(c2, 0.4), H(0.05, side * 0.8), H(0.62, side * 0.5), int(S * 1.6))
    return add_outline(s, shade(c2, 0.42), S)


def build_snakes(out_dir):
    manifest = {}
    for kind, spec in SNAKES.items():
        boss = kind == "boss"
        heads = [snake_head(spec, st, boss) for st in ("open", "closed", "angry")]
        hw, hh = heads[0].get_size()
        sheet = surface(hw * 3, hh)
        for i, h in enumerate(heads):
            sheet.blit(h, (i * hw, 0))
        save(sheet, out_dir, "snakes", f"{kind}_head.png")
        segs = [snake_segment(spec["r"], col, spec["pattern"], seed) for seed, col in enumerate((spec["c1"], spec["c2"]))]
        sw, sh = segs[0].get_size()
        sheet = surface(sw * 2, sh)
        for i, sg in enumerate(segs):
            sheet.blit(sg, (i * sw, 0))
        save(sheet, out_dir, "snakes", f"{kind}_body.png")
        manifest[kind] = dict(radius=spec["r"] * S, head_frames=["open", "closed", "angry"], body_frames=2)
    with open(os.path.join(out_dir, "snakes", "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(scale=S, snakes=manifest), fh, indent=1)


# ================================================================ icons (32x32 in game, 128x128 here)
IC = 32 * S


def icon_canvas():
    return surface(IC, IC)


def U(x, y):
    """Icon coordinates from -1..1 -> pixels (with a margin for the outline)."""
    return (IC / 2 + x * IC * 0.4, IC / 2 + y * IC * 0.4)


def two_tone_polygon(s, pts, top, bottom, split=0.5):
    pygame.draw.polygon(s, top, pts)
    s.set_clip(pygame.Rect(0, IC * split, IC, IC))
    pygame.draw.polygon(s, bottom, pts)
    s.set_clip(None)


def icon_speed():
    s = icon_canvas()
    for i, y in enumerate((-0.35, 0.05, 0.45)):
        limb(s, U(-1.0 + i * 0.1, y), U(-0.55 + i * 0.1, y), 2.2 * S, (255, 236, 160))
    bolt = [U(*p) for p in ((0.25, -1), (-0.5, 0.12), (-0.02, 0.12), (-0.22, 1), (0.62, -0.2), (0.12, -0.2))]
    two_tone_polygon(s, bolt, (255, 214, 50), (255, 160, 30))
    shine = [U(*p) for p in ((0.18, -0.8), (-0.3, 0.02), (-0.12, 0.02), (0.2, -0.55))]
    pygame.draw.polygon(s, (255, 246, 170), shine)
    return add_outline(s, (130, 70, 10), int(1.3 * S))


def icon_shield():
    s = icon_canvas()
    pts = []
    for i in range(11):                     # slightly curved top edge
        x = -0.82 + i * 0.164
        pts.append(U(x, -0.88 + 0.08 * (x * x)))
    for i in range(1, 16):                  # rounded sides meeting at the bottom point
        t = i / 15
        pts.append(U(0.82 * math.cos(t * math.pi / 2) ** 0.55, -0.82 + t * 1.85))
    for i in range(15, 0, -1):
        t = i / 15
        pts.append(U(-0.82 * math.cos(t * math.pi / 2) ** 0.55, -0.82 + t * 1.85))
    two_tone_polygon(s, pts, (90, 160, 250), (50, 105, 215))
    inner = [(IC / 2 + (x - IC / 2) * 0.72, IC / 2 + (y - IC / 2) * 0.72 - 2 * S) for x, y in pts]
    pygame.draw.polygon(s, (230, 240, 255), inner, int(1.2 * S))
    star = []
    for i in range(10):
        rr = 0.32 if i % 2 == 0 else 0.14
        a = -math.pi / 2 + i * math.pi / 5
        star.append(U(math.cos(a) * rr, -0.1 + math.sin(a) * rr))
    pygame.draw.polygon(s, (255, 255, 255), star)
    blend(s, pygame.draw.ellipse, (255, 255, 255, 90), pygame.Rect(U(-0.62, -0.7), (IC * 0.2, IC * 0.12)))
    return add_outline(s, (20, 40, 95), int(1.3 * S))


def icon_freeze():
    s = icon_canvas()
    for color, width in (((70, 150, 220), 3.2 * S), ((200, 240, 255), 1.5 * S)):
        for i in range(6):
            a = i * math.pi / 3
            ca, sa = math.cos(a), math.sin(a)
            limb(s, U(0, 0), U(ca * 0.95, sa * 0.95), width, color)
            for side in (-1, 1):
                b = a + side * 0.7
                base = (ca * 0.55, sa * 0.55)
                limb(s, U(*base), U(base[0] + math.cos(b) * 0.3, base[1] + math.sin(b) * 0.3), width * 0.8, color)
    shaded_circle(s, U(0, 0), 4.5 * S, (230, 250, 255), (120, 200, 245))
    return add_outline(s, (30, 80, 140), int(1.2 * S))


def icon_ghost():
    s = icon_canvas()
    body, shadow = (252, 252, 255), (212, 218, 245)
    for color, clip in ((body, None), (shadow, pygame.Rect(IC * 0.58, 0, IC, IC))):
        s.set_clip(clip)
        pygame.draw.circle(s, color, U(0, -0.25), IC * 0.3)
        pygame.draw.rect(s, color, pygame.Rect(U(-0.75, -0.25), (IC * 0.6, IC * 0.36)))
        for i in range(3):
            pygame.draw.circle(s, color, U(-0.5 + i * 0.5, 0.65), IC * 0.1)
        s.set_clip(None)
    for x in (-0.28, 0.28):
        pygame.draw.ellipse(s, (40, 40, 70), pygame.Rect(U(x - 0.1, -0.4), (IC * 0.08, IC * 0.13)))
        pygame.draw.circle(s, (255, 255, 255), U(x - 0.04, -0.33), IC * 0.015)
    for x in (-0.45, 0.45):
        blend(s, pygame.draw.ellipse, (255, 150, 170, 140), pygame.Rect(U(x - 0.1, -0.12), (IC * 0.08, IC * 0.04)))
    pygame.draw.arc(s, (40, 40, 70), pygame.Rect(U(-0.1, -0.15), (IC * 0.08, IC * 0.06)), math.pi, 2 * math.pi,
                    int(0.8 * S))
    return add_outline(s, (70, 80, 125), int(1.3 * S))


def icon_gem():
    s = icon_canvas()
    outline = [U(-0.85, -0.3), U(-0.45, -0.8), U(0.45, -0.8), U(0.85, -0.3), U(0, 0.95)]
    pygame.draw.polygon(s, (255, 196, 40), outline)
    facets = [
        ([(-0.85, -0.3), (-0.45, -0.8), (-0.2, -0.3)], (255, 226, 110)),
        ([(-0.45, -0.8), (0.45, -0.8), (0.2, -0.3), (-0.2, -0.3)], (255, 242, 160)),
        ([(0.45, -0.8), (0.85, -0.3), (0.2, -0.3)], (250, 200, 60)),
        ([(-0.85, -0.3), (-0.2, -0.3), (0, 0.95)], (255, 212, 70)),
        ([(-0.2, -0.3), (0.2, -0.3), (0, 0.95)], (255, 188, 40)),
        ([(0.2, -0.3), (0.85, -0.3), (0, 0.95)], (226, 150, 22)),
    ]
    for pts, color in facets:
        pygame.draw.polygon(s, color, [U(*p) for p in pts])
    for a, b in (((-0.85, -0.3), (0.85, -0.3)), ((-0.2, -0.3), (0, 0.95)), ((0.2, -0.3), (0, 0.95))):
        pygame.draw.line(s, (255, 250, 210), U(*a), U(*b), int(0.6 * S))
    cx, cy = U(-0.45, -0.52)
    for dx, dy in ((1, 0), (0, 1)):
        pygame.draw.line(s, (255, 255, 255), (cx - dx * 4 * S, cy - dy * 4 * S), (cx + dx * 4 * S, cy + dy * 4 * S),
                         int(1.2 * S))
    return add_outline(s, (150, 90, 10), int(1.3 * S))


def heart_points(scale=1.0, oy=0.0):
    pts = []
    for i in range(60):
        t = i / 60 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append(U(x / 17 * scale, y / 17 * scale + oy))
    return pts


def icon_heart(empty=False):
    s = icon_canvas()
    top, bottom = ((150, 150, 160), (115, 115, 125)) if empty else ((242, 70, 100), (205, 40, 75))
    two_tone_polygon(s, heart_points(1.0, 0.05), top, bottom, 0.55)
    if not empty:
        blend(s, pygame.draw.ellipse, (255, 255, 255, 150), pygame.Rect(U(-0.62, -0.55), (IC * 0.16, IC * 0.1)))
    return add_outline(s, (90, 90, 100) if empty else (120, 20, 45), int(1.3 * S))


def star_points_icon(rr=0.95, inner=0.47, oy=0.05):
    pts = []
    for i in range(10):
        r = rr if i % 2 == 0 else rr * inner
        a = -math.pi / 2 + i * math.pi / 5
        pts.append(U(math.cos(a) * r, math.sin(a) * r + oy))
    return pts


def icon_star(empty=False):
    s = icon_canvas()
    top, bottom = ((128, 128, 142), (100, 100, 115)) if empty else ((255, 218, 60), (245, 170, 30))
    two_tone_polygon(s, star_points_icon(), top, bottom, 0.55)
    if not empty:
        pygame.draw.polygon(s, (255, 240, 150), star_points_icon(0.42, 0.47, 0.0))
    return add_outline(s, (75, 75, 90) if empty else (150, 90, 10), int(1.3 * S))


def icon_coin():
    s = icon_canvas()
    shaded_circle(s, U(0, 0), IC * 0.38, (255, 214, 80), (214, 150, 30), shine=False)
    pygame.draw.circle(s, (232, 168, 40), U(0, 0), IC * 0.29, int(1.2 * S))
    star = []
    for i in range(10):
        r = 0.42 if i % 2 == 0 else 0.19
        a = -math.pi / 2 + i * math.pi / 5
        star.append(U(math.cos(a) * r, math.sin(a) * r + 0.03))
    pygame.draw.polygon(s, (240, 178, 45), star)
    blend(s, pygame.draw.arc, (255, 255, 255, 170), pygame.Rect(U(-0.75, -0.75), (IC * 0.6, IC * 0.6)), 1.9, 2.9,
          int(1.4 * S))
    return add_outline(s, (140, 90, 10), int(1.3 * S))


def icon_lock():
    s = icon_canvas()
    pygame.draw.arc(s, (150, 155, 168), pygame.Rect(U(-0.45, -0.95), (IC * 0.36, IC * 0.6)), 0, math.pi, int(3 * S))
    body = pygame.Rect(U(-0.65, -0.25), (IC * 0.52, IC * 0.46))
    pygame.draw.rect(s, (196, 200, 212), body, border_radius=int(3 * S))
    s.set_clip(pygame.Rect(IC * 0.52, 0, IC, IC))
    pygame.draw.rect(s, (165, 170, 185), body, border_radius=int(3 * S))
    s.set_clip(None)
    pygame.draw.circle(s, (60, 60, 75), U(0, 0.05), IC * 0.05)
    pygame.draw.rect(s, (60, 60, 75), pygame.Rect(U(-0.03, 0.05), (IC * 0.025, IC * 0.1)))
    return add_outline(s, (60, 60, 75), int(1.3 * S))


ICONS = {
    "speed": icon_speed, "shield": icon_shield, "freeze": icon_freeze, "ghost": icon_ghost,
    "gem": icon_gem, "coin": icon_coin, "lock": icon_lock,
    "heart": icon_heart, "heart_empty": lambda: icon_heart(True),
    "star": icon_star, "star_empty": lambda: icon_star(True),
}


def build_icons(out_dir):
    for name, fn in ICONS.items():
        save(fn(), out_dir, "icons", f"{name}.png")


def build_all(out_dir):
    build_bayan(out_dir)
    build_snakes(out_dir)
    build_icons(out_dir)
