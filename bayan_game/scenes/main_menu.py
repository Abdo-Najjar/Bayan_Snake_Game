"""Title screen with an animated chase in the background."""
import math

import pygame
from pygame import Vector2 as V

from ..config import W
from ..content.levels import LEVELS
from ..content.shop import dress_color
from ..entities.bayan import Bayan
from ..entities.snake import Snake
from ..graphics.ambient import Ambient
from ..graphics.art import background, draw_coin, draw_star, vignette
from ..graphics.ui import MenuList, overlay
from .base import Scene


class MainMenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.items, W / 2, 215, width=300, height=46, gap=10)
        save = app.save
        self.bayan = Bayan(W / 2, 560, dress_color(save["dress"]), save["hat"])
        self.snake = Snake(V(100, 560), "normal", dict(speed=170, turn=2.4))
        self.snake.grow(4)
        self.ambient = Ambient("grass")

    def items(self):
        tr = self.app.tr
        return [(k, tr(f"menu.{k}")) for k in ("play", "levels", "shop", "settings", "quit")]

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.request_quit()
            return
        result = self.menu.handle_event(e)
        if not result:
            return
        key, action = result
        if action == "move":
            self.app.sfx.play("click")
        elif action == "activate":
            self.app.sfx.play("select")
            app = self.app
            if key == "play":
                app.start_level(min(app.save["unlocked"], len(LEVELS)) - 1)
            elif key == "levels":
                app.show_levels()
            elif key == "shop":
                app.show_shop()
            elif key == "settings":
                app.show_settings(back=self)
            elif key == "quit":
                app.request_quit()

    def update(self, dt):
        super().update(dt)
        b = self.bayan
        old = V(b.pos)
        a = self.t * 0.9
        b.pos.update(W / 2 + math.cos(a) * 340, 565 + math.sin(a * 2) * 35)
        b.vel = (b.pos - old) / dt if dt else V()
        if b.vel.length_squared() > 0:
            b.facing = b.vel.normalize()
        b.walk += dt * 14
        self.snake.update(dt, b, True, [], [], self.t)
        self.ambient.update(dt, self.t)

    def draw(self, surf):
        app, text, tr = self.app, self.app.text, self.app.tr
        surf.blit(background("grass"), (0, 0))
        self.snake.draw(surf, self.t)
        self.bayan.draw(surf, self.t, app.name_label())
        self.ambient.draw(surf, self.t)
        overlay(surf, 60)
        surf.blit(vignette(surf.get_size(), 190), (0, 0))

        bob = math.sin(self.t * 2) * 5
        text.draw(surf, tr("game.title"), text.huge, (255, 220, 240), (W / 2, 80 + bob), outline=((90, 30, 70), 3))
        text.draw(surf, tr("game.subtitle"), text.small, (255, 255, 255), (W / 2, 145))
        self.menu.draw(surf, text, self.t)

        # coins and stars in the corner
        draw_coin(surf, 30, 30, 11)
        text.draw(surf, str(app.save["coins"]), text.mid, (255, 230, 120), (48, 30), align="midleft")
        draw_star(surf, 30, 68, 12)
        text.draw(surf, f"{app.save.total_stars()} / {len(LEVELS) * 3}", text.mid, (255, 230, 120),
                  (48, 68), align="midleft")
        text.draw(surf, tr("menu.hint"), text.tiny, (230, 230, 230), (W / 2, 626))
