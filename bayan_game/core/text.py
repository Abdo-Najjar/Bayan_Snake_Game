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

    def draw(self, surf, s, font, color, pos, align="center", shadow=True, outline=None):
        """align is any pygame.Rect anchor: center, midleft, midright, topleft...
        outline: optional (color, thickness) drawn around the letters."""
        img = self.render(s, font, color)
        rect = img.get_rect(**{align: pos})
        if outline:
            o_color, o_size = outline
            o_img = self.render(s, font, o_color)
            surf.blit(o_img, rect.move(0, o_size + 2))
            for dx in range(-o_size, o_size + 1):
                for dy in range(-o_size, o_size + 1):
                    if dx * dx + dy * dy <= o_size * o_size:
                        surf.blit(o_img, rect.move(dx, dy))
        elif shadow:
            surf.blit(self.render(s, font, (20, 20, 20)), rect.move(2, 2))
        surf.blit(img, rect)
        return rect
