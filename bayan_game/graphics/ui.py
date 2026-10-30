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

    def __init__(self, items, center_x, top, width=340, height=50, gap=12, adjustable=()):
        self.items = items
        # keys whose value changes with left/right: a click on the button's left half
        # sends "left", the right half sends "right"; the mouse wheel works too
        self.adjustable = set(adjustable)
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
                    if self.current_key() in self.adjustable:
                        return self.current_key(), "left" if e.pos[0] < r.centerx else "right"
                    return self.current_key(), "activate"
        elif e.type == pygame.MOUSEWHEEL and e.y:
            pos = pygame.mouse.get_pos()
            for i, r in enumerate(self.rects()):
                if r.collidepoint(pos) and items[i][0] in self.adjustable:
                    self.sel = i
                    return self.current_key(), "right" if e.y > 0 else "left"
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


class ConfirmDialog:
    """A small yes/no box shown on top of the current scene."""

    def __init__(self, app, title_key, text_key, on_yes):
        self.app = app
        self.title_key = title_key
        self.text_key = text_key
        self.on_yes = on_yes
        self.t = 0.0
        tr = app.tr
        w, h = app.canvas.get_size()
        self.box = pygame.Rect(0, 0, 440, 300)
        self.box.center = (w // 2, h // 2)
        self.menu = MenuList(lambda: [("yes", tr("confirm.yes")), ("no", tr("confirm.no"))],
                             self.box.centerx, self.box.y + 150, 300, 46, 12)
        self.menu.sel = 1   # "no" is selected by default so Enter never quits by accident
        self.closed = False

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.closed = True
            return
        result = self.menu.handle_event(e)
        if not result:
            return
        key, action = result
        if action == "move":
            self.app.sfx.play("click")
        elif action == "activate":
            self.app.sfx.play("select")
            self.closed = True
            if key == "yes":
                self.on_yes()

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        text, tr = self.app.text, self.app.tr
        overlay(surf, 150)
        grow = min(1.0, self.t * 8)
        box = self.box.inflate(-40 * (1 - grow), -40 * (1 - grow))
        panel(surf, box, color=(35, 30, 55), alpha=240)
        text.draw(surf, tr(self.title_key), text.mid, (255, 220, 240), (box.centerx, box.y + 55))
        text.draw(surf, tr(self.text_key), text.small, (220, 220, 235), (box.centerx, box.y + 100))
        self.menu.draw(surf, text, self.t)


def draw_keycap(surf, text, label, rect, pressed=False):
    """A keyboard key drawn as a button; it sinks and lights up while pressed."""
    rect = pygame.Rect(rect)
    depth = 2 if pressed else 6
    pygame.draw.rect(surf, (60, 60, 80), rect.move(0, 6), border_radius=10)
    top = rect.move(0, 6 - depth)
    pygame.draw.rect(surf, (255, 200, 225) if pressed else (245, 245, 250), top, border_radius=10)
    pygame.draw.rect(surf, (90, 90, 110), top, 2, border_radius=10)
    text.draw(surf, label, text.small, (50, 50, 70), top.center, shadow=False)
