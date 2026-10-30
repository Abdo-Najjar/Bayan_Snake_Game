"""Loads the PNG sprites (assets/sprites) and builds what the game draws from them.

Bayan is built from layers, so outfits work without a picture per combination:
grayscale layers (dress, cap, hijab) are tinted with the outfit color at runtime.
All results are cached, so each combination is built only once.
"""
import json
import os

import pygame

from ..config import ASSETS_DIR

SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
FROZEN_TINT = (175, 215, 245)


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


class SpriteBank:
    def __init__(self, root=SPRITES_DIR):
        self.root = root
        self._images = {}
        self._cache = {}
        with open(os.path.join(root, "bayan", "manifest.json"), encoding="utf-8") as f:
            self.bayan_info = json.load(f)
        with open(os.path.join(root, "snakes", "manifest.json"), encoding="utf-8") as f:
            self.snake_info = json.load(f)

    # ---------------------------------------------------------------- basics
    def image(self, *parts):
        key = os.path.join(*parts)
        img = self._images.get(key)
        if img is None:
            img = pygame.image.load(os.path.join(self.root, key))
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            self._images[key] = img
        return img

    def _cached(self, key, build):
        img = self._cache.get(key)
        if img is None:
            if len(self._cache) > 3000:
                self._cache.clear()
            img = build()
            self._cache[key] = img
        return img

    @staticmethod
    def tint(img, color):
        out = img.copy()
        out.fill((*color[:3], 255), special_flags=pygame.BLEND_RGBA_MULT)
        return out

    def frozen(self, img):
        out = self.tint(img, FROZEN_TINT)
        out.fill((35, 40, 50, 0), special_flags=pygame.BLEND_RGB_ADD)
        return out

    # ---------------------------------------------------------------- icons
    def icon(self, name, size):
        size = max(4, int(size))
        return self._cached(("icon", name, size),
                            lambda: pygame.transform.smoothscale(self.image("icons", f"{name}.png"), (size, size)))

    # ---------------------------------------------------------------- Bayan
    def bayan_layers(self, hat):
        """(layer file, tint mode) in drawing order for the given accessory."""
        layers = [("shadow", None), ("legs", None), ("dress", "dress"), ("dress_trim", None), ("arms", None)]
        if hat == "hijab":
            layers += [("hijab_back", "light"), ("head", None), ("hijab_front", "light")]
        else:
            layers += [("hair_back", None), ("head", None), ("hair_front", None)]
            layers.append((f"hat_{hat}", "dark" if hat == "cap" else None))
        return layers

    def bayan(self, direction, frame, dress, hat, flip=False, scale=1.0):
        """Bayan composed for one frame. Size is (64, 80) * scale; body center at (32, 50) * scale."""
        key = ("bayan", direction, frame, tuple(dress), hat, flip, scale)
        return self._cached(key, lambda: self._build_bayan(direction, frame, dress, hat, flip, scale))

    def _build_bayan(self, direction, frame, dress, hat, flip, scale):
        fw, fh = self.bayan_info["frame_size"]
        tints = {"dress": dress, "light": _mix(dress, (255, 255, 255), 0.45), "dark": _mix(dress, (0, 0, 0), 0.18)}
        canvas = pygame.Surface((fw, fh), pygame.SRCALPHA)
        for name, tint in self.bayan_layers(hat):
            path = os.path.join(self.root, "bayan", direction, f"{name}.png")
            if not os.path.exists(path):
                continue
            sheet = self.image("bayan", direction, f"{name}.png")
            part = sheet.subsurface((frame * fw, 0, fw, fh))
            canvas.blit(self.tint(part, tints[tint]) if tint else part, (0, 0))
        if flip:
            canvas = pygame.transform.flip(canvas, True, False)
        base = self.bayan_info["scale"]
        size = (round(fw / base * scale), round(fh / base * scale))
        return canvas if size == (fw, fh) else pygame.transform.smoothscale(canvas, size)

    # ---------------------------------------------------------------- snakes
    def _sheet_frame(self, img, count, index):
        w = img.get_width() // count
        return img.subsurface((index * w, 0, w, img.get_height()))

    def snake_head(self, kind, state, angle_deg, radius, frozen=False):
        """Head rotated to angle_deg (0 = facing right), sized for the given head radius."""
        bucket = int(round(angle_deg / 4)) * 4 % 360
        info = self.snake_info["snakes"][kind]
        states = info["head_frames"]
        index = states.index(state) if state in states else 0

        def build():
            img = self._sheet_frame(self.image("snakes", f"{kind}_head.png"), len(states), index)
            if frozen:
                img = self.frozen(img)
            return pygame.transform.rotozoom(img, -bucket, radius / info["radius"])
        return self._cached(("head", kind, index, bucket, round(radius, 1), frozen), build)

    def snake_segment(self, kind, variant, radius, frozen=False):
        radius = round(radius * 2) / 2
        info = self.snake_info["snakes"][kind]

        def build():
            img = self._sheet_frame(self.image("snakes", f"{kind}_body.png"), info["body_frames"], variant % 2)
            if frozen:
                img = self.frozen(img)
            k = radius / info["radius"]
            size = (max(2, round(img.get_width() * k)), max(2, round(img.get_height() * k)))
            return pygame.transform.smoothscale(img, size)
        return self._cached(("seg", kind, variant % 2, radius, frozen), build)


_bank = None


def bank():
    """Shared SpriteBank, created on first use (after the window exists)."""
    global _bank
    if _bank is None:
        _bank = SpriteBank()
    return _bank
