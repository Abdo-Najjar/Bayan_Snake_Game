"""Outfit shop: buy dresses and accessories with coins, with a live preview."""
import math

import pygame
from pygame import Vector2 as V

from ..config import W
from ..content.shop import SHOP_ITEMS, dress_color
from ..entities.bayan import Bayan
from ..graphics.art import background, draw_coin
from ..graphics.ui import CONFIRM_KEYS, overlay, panel
from .base import Scene

ROW_H = 40
LIST_X, LIST_W, LIST_Y = 450, 470, 110


class ShopScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.sel = 0
        self.message = None   # (text key, color, time left)
        self.preview = Bayan(0, 0)
        self.preview.facing = V(0.3, 1).normalize()

    def row_rect(self, i):
        return pygame.Rect(LIST_X, LIST_Y + i * ROW_H, LIST_W, ROW_H - 4)

    def choose(self):
        save, item = self.app.save, SHOP_ITEMS[self.sel]
        if not save.owns(item["id"]):
            if save["coins"] < item["price"]:
                self.app.sfx.play("denied")
                self.message = ("shop.not_enough", (255, 120, 120), 2.0)
                return
            save["coins"] -= item["price"]
            save["owned"].append(item["id"])
            self.app.sfx.play("coin")
            self.message = ("shop.bought", (150, 255, 150), 2.0)
        else:
            self.app.sfx.play("select")
        save[item["kind"]] = item["id"]
        save.write()

    def handle_event(self, e):
        n = len(SHOP_ITEMS)
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % n
                self.app.sfx.play("click")
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % n
                self.app.sfx.play("click")
            elif e.key in CONFIRM_KEYS:
                self.choose()
            elif e.key == pygame.K_ESCAPE:
                self.app.show_menu()
        elif e.type == pygame.MOUSEMOTION:
            for i in range(n):
                if self.row_rect(i).collidepoint(e.pos) and i != self.sel:
                    self.sel = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i in range(n):
                if self.row_rect(i).collidepoint(e.pos):
                    self.sel = i
                    self.choose()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            self.app.show_menu()

    def update(self, dt):
        super().update(dt)
        if self.message:
            key, color, left = self.message
            self.message = (key, color, left - dt) if left > dt else None
        # preview wears the hovered item on top of the current outfit
        save, item = self.app.save, SHOP_ITEMS[self.sel]
        dress = item["id"] if item["kind"] == "dress" else save["dress"]
        hat = item["id"] if item["kind"] == "hat" else save["hat"]
        self.preview.dress = dress_color(dress)
        self.preview.hat = hat
        self.preview.vel = V(1, 0)   # keeps the legs moving
        self.preview.walk += dt * 6

    def draw(self, surf):
        app, text, tr, save = self.app, self.app.text, self.app.tr, self.app.save
        surf.blit(background("grass"), (0, 0))
        overlay(surf, 110)
        text.draw(surf, tr("shop.title"), text.big, (255, 220, 240), (W / 2, 50))
        draw_coin(surf, 40, 40, 12)
        text.draw(surf, str(save["coins"]), text.mid, (255, 230, 120), (60, 40), align="midleft")

        # preview on a pedestal
        cx, cy = 225, 340
        pygame.draw.ellipse(surf, (60, 40, 70), (cx - 110, cy + 120, 220, 50))
        pygame.draw.ellipse(surf, (110, 80, 130), (cx - 110, cy + 112, 220, 50))
        sprite = pygame.transform.smoothscale(self.preview.render_sprite(), (64 * 4, 80 * 4))
        bob = math.sin(self.t * 3) * 4
        surf.blit(sprite, sprite.get_rect(center=(cx, cy - 20 + bob)))

        panel(surf, (LIST_X - 10, LIST_Y - 10, LIST_W + 20, len(SHOP_ITEMS) * ROW_H + 16))
        rtl = app.tr.rtl
        for i, item in enumerate(SHOP_ITEMS):
            r = self.row_rect(i)
            if i == self.sel:
                pygame.draw.rect(surf, (255, 140, 190), r, border_radius=10)
            name = tr(f"items.{item['id']}")
            owned = save.owns(item["id"])
            if save[item["kind"]] == item["id"]:
                status, col = tr("shop.equipped"), (150, 255, 150)
            elif owned:
                status, col = tr("shop.owned"), (200, 220, 255)
            else:
                status, col = tr("shop.price", n=item["price"]), (255, 230, 120)

            swatch_x = r.right - 22 if rtl else r.x + 22
            if item["kind"] == "dress":
                pygame.draw.circle(surf, item["color"], (swatch_x, r.centery), 11)
                pygame.draw.circle(surf, (255, 255, 255), (swatch_x, r.centery), 11, 2)
            else:
                pygame.draw.circle(surf, (90, 90, 120), (swatch_x, r.centery), 11)
                pygame.draw.circle(surf, (255, 255, 255), (swatch_x, r.centery), 11, 2)
            if rtl:
                text.draw(surf, name, text.small, (255, 255, 255), (r.right - 44, r.centery), align="midright")
                text.draw(surf, status, text.small, col, (r.x + 14, r.centery), align="midleft")
            else:
                text.draw(surf, name, text.small, (255, 255, 255), (r.x + 44, r.centery), align="midleft")
                text.draw(surf, status, text.small, col, (r.right - 14, r.centery), align="midright")

        if self.message:
            key, color, _ = self.message
            text.draw(surf, tr(key), text.mid, color, (cx, 560))
        text.draw(surf, tr("shop.footer"), text.small, (230, 230, 230), (W / 2, 610))
