"""Reusable UI pieces: dark overlays, panels and a keyboard/mouse button list."""
import math

import pygame

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


def overlay(surf, alpha=150, color=(0, 0, 0)):
    o = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    o.fill((*color, alpha))
    surf.blit(o, (0, 0))


def panel(surf, rect, color=(25, 35, 50), alpha=210, border=(255, 255, 255), radius=18):
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
    pygame.draw.rect(s, (*border, 70), s.get_rect(), 2, border_radius=radius)
    surf.blit(s, rect)


class MenuList:
    """A vertical column of buttons.

    `items` is a callable returning [(key, label), ...] so labels can change
    (language switch, setting values). handle_event returns (key, action) where
    action is "move", "activate", "left" or "right", or None.
    """

    def __init__(self, items, center_x, top, width=340, height=50, gap=12):
        self.items = items
        self.center_x = center_x
        self.top = top
        self.width = width
        self.height = height
        self.gap = gap
        self.sel = 0

    def rects(self):
        out = []
        for i in range(len(self.items())):
            r = pygame.Rect(0, 0, self.width, self.height)
            r.midtop = (self.center_x, self.top + i * (self.height + self.gap))
            out.append(r)
        return out

    def current_key(self):
        items = self.items()
        return items[self.sel][0] if items else None

    def handle_event(self, e):
        items = self.items()
        if not items:
            return None
        self.sel = min(self.sel, len(items) - 1)
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(items)
                return self.current_key(), "move"
            if e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(items)
                return self.current_key(), "move"
            if e.key in CONFIRM_KEYS:
                return self.current_key(), "activate"
            if e.key in (pygame.K_LEFT, pygame.K_a):
                return self.current_key(), "left"
            if e.key in (pygame.K_RIGHT, pygame.K_d):
                return self.current_key(), "right"
        elif e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects()):
                if r.collidepoint(e.pos) and i != self.sel:
                    self.sel = i
                    return self.current_key(), "move"
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self.rects()):
                if r.collidepoint(e.pos):
                    self.sel = i
                    return self.current_key(), "activate"
        return None

    def draw(self, surf, text, t, font=None):
        font = font or text.mid
        for i, ((_, label), r) in enumerate(zip(self.items(), self.rects())):
            selected = i == self.sel
            rr = r.inflate(10, 4) if selected else r
            if selected:
                rr = rr.move(0, int(math.sin(t * 5) * 2))
            s = pygame.Surface(rr.size, pygame.SRCALPHA)
            fill = (255, 140, 190, 235) if selected else (30, 45, 60, 200)
            pygame.draw.rect(s, fill, s.get_rect(), border_radius=14)
            pygame.draw.rect(s, (255, 255, 255, 220 if selected else 60), s.get_rect(), 2, border_radius=14)
            surf.blit(s, rr)
            color = (255, 255, 255) if selected else (220, 230, 240)
            text.draw(surf, label, font, color, rr.center)
