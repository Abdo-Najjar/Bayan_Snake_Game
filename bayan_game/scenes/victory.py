"""Shown after beating the giant snake."""
import math
import random

import pygame
from pygame import Vector2 as V

from ..config import W, H
from ..content.levels import LEVELS
from ..content.shop import dress_color
from ..entities.bayan import Bayan
from ..entities.effects import Effects
from ..graphics.art import background, draw_star
from ..graphics.ui import MenuList, overlay
from .base import Scene

FIREWORK_COLORS = [(255, 220, 80), (255, 120, 180), (120, 220, 255), (160, 255, 150)]


class VictoryScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.effects = Effects()
        save = app.save
        self.bayan = Bayan(W / 2, 330, dress_color(save["dress"]), save["hat"])
        self.bayan.facing = V(0, 1)
        self.menu = MenuList(lambda: [("menu", app.tr("win.continue"))], W / 2, 520, 300, 50)

    def handle_event(self, e):
        if self.t < 1.0:
            return
        result = self.menu.handle_event(e)
        if result and result[1] == "activate":
            self.app.sfx.play("select")
            self.app.show_menu()

    def update(self, dt):
        super().update(dt)
        if random.random() < 0.08:
            pos = V(random.uniform(100, W - 100), random.uniform(80, H - 250))
            self.effects.burst(pos, random.choice(FIREWORK_COLORS), 30, 220)
        self.effects.update(dt)
        self.bayan.pos.y = 330 - abs(math.sin(self.t * 4)) * 25   # happy jumping

    def draw(self, surf):
        text, tr, save = self.app.text, self.app.tr, self.app.save
        surf.blit(background("grass"), (0, 0))
        overlay(surf, 120)
        self.effects.draw(surf)
        text.draw(surf, tr("win.title"), text.big, (255, 235, 120), (W / 2, 110))
        text.draw(surf, tr("win.subtitle"), text.mid, (255, 255, 255), (W / 2, 165))
        sprite = pygame.transform.smoothscale(self.bayan.render_sprite(), (64 * 3, 80 * 3))
        surf.blit(sprite, sprite.get_rect(center=self.bayan.pos))
        draw_star(surf, W / 2 - 120, 460, 16)
        text.draw(surf, tr("win.stars", n=save.total_stars(), max=len(LEVELS) * 3), text.mid,
                  (255, 230, 120), (W / 2 + 10, 460))
        self.menu.draw(surf, text, self.t)
