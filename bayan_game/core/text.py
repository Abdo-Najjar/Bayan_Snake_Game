"""Fonts and cached text rendering."""
import os

import pygame

# Tahoma covers Arabic and Latin; DejaVu/Noto are fallbacks on other systems.
FONT_CANDIDATES = {
    False: ["C:/Windows/Fonts/tahoma.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/Arial Unicode.ttf"],
    True: ["C:/Windows/Fonts/tahomabd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/Library/Fonts/Arial Unicode.ttf"],
}


def load_font(size, bold=False):
    for path in FONT_CANDIDATES[bold]:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("tahoma,arial,dejavusans", size, bold=bold)


class Text:
    def __init__(self):
        self.huge = load_font(64, True)
        self.big = load_font(40, True)
        self.mid = load_font(26, True)
        self.small = load_font(20)
        self.tiny = load_font(15, True)
        self._cache = {}

    def render(self, s, font, color):
        key = (s, id(font), tuple(color))
        img = self._cache.get(key)
        if img is None:
            if len(self._cache) > 400:
                self._cache.clear()
            img = font.render(s, True, color)
            self._cache[key] = img
        return img

    def draw(self, surf, s, font, color, pos, align="center", shadow=True):
        """align is any pygame.Rect anchor: center, midleft, midright, topleft..."""
        img = self.render(s, font, color)
        rect = img.get_rect(**{align: pos})
        if shadow:
            surf.blit(self.render(s, font, (20, 20, 20)), rect.move(2, 2))
        surf.blit(img, rect)
        return rect
