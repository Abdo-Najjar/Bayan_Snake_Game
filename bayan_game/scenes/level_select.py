"""Grid of levels with stars and locks."""
import math

import pygame

from ..config import W
from ..content.levels import LEVELS
from ..graphics.art import background, draw_coin, draw_lock, draw_star, shade
from ..graphics.ui import CONFIRM_KEYS, overlay
from .base import Scene

COLS = 3
CARD_W, CARD_H, GAP = 230, 120, 25
GRID_X = (W - (COLS * CARD_W + (COLS - 1) * GAP)) // 2
GRID_Y = 140
TERRAIN_COLORS = {
    "grass": (90, 170, 80), "desert": (215, 175, 100), "snow": (150, 195, 230),
    "forest": (50, 110, 55), "lair": (130, 45, 55),
}


class LevelSelectScene(Scene):
    def __init__(self, app, selected=None):
        super().__init__(app)
        last_open = min(app.save["unlocked"], len(LEVELS)) - 1
        self.sel = last_open if selected is None else selected

    def card_rect(self, i):
        col, row = i % COLS, i // COLS
        return pygame.Rect(GRID_X + col * (CARD_W + GAP), GRID_Y + row * (CARD_H + GAP), CARD_W, CARD_H)

    def try_start(self):
        if self.app.save.is_unlocked(self.sel):
            self.app.sfx.play("select")
            self.app.start_level(self.sel)
        else:
            self.app.sfx.play("denied")

    def handle_event(self, e):
        n = len(LEVELS)
        if e.type == pygame.KEYDOWN:
            moves = {pygame.K_LEFT: -1, pygame.K_a: -1, pygame.K_RIGHT: 1, pygame.K_d: 1,
                     pygame.K_UP: -COLS, pygame.K_w: -COLS, pygame.K_DOWN: COLS, pygame.K_s: COLS}
            if e.key in moves:
                self.sel = (self.sel + moves[e.key]) % n
                self.app.sfx.play("click")
            elif e.key in CONFIRM_KEYS:
                self.try_start()
            elif e.key == pygame.K_ESCAPE:
                self.app.show_menu()
        elif e.type == pygame.MOUSEMOTION:
            for i in range(n):
                if self.card_rect(i).collidepoint(e.pos) and i != self.sel:
                    self.sel = i
                    self.app.sfx.play("click")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i in range(n):
                if self.card_rect(i).collidepoint(e.pos):
                    self.sel = i
                    self.try_start()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            self.app.show_menu()

    def draw(self, surf):
        app, text, tr, save = self.app, self.app.text, self.app.tr, self.app.save
        surf.blit(background("grass"), (0, 0))
        overlay(surf, 120)
        text.draw(surf, tr("levels.title"), text.big, (255, 220, 240), (W / 2, 70), outline=((90, 30, 70), 3))
        draw_coin(surf, W - 120, 40, 11)
        text.draw(surf, str(save["coins"]), text.mid, (255, 230, 120), (W - 102, 40), align="midleft")

        for i, lvl in enumerate(LEVELS):
            r = self.card_rect(i)
            selected = i == self.sel
            if selected:
                r = r.move(0, int(math.sin(self.t * 5) * 3))
            unlocked = save.is_unlocked(i)
            base = TERRAIN_COLORS[lvl["terrain"]]
            pygame.draw.rect(surf, shade(base, 0.6), r.move(0, 5), border_radius=16)
            pygame.draw.rect(surf, base, r, border_radius=16)
            pygame.draw.rect(surf, (255, 255, 255) if selected else shade(base, 0.7), r, 4 if selected else 2,
                             border_radius=16)
            text.draw(surf, tr("levels.level", n=i + 1), text.mid, (255, 255, 255), (r.centerx, r.y + 28))
            text.draw(surf, tr(f"terrain.{lvl['terrain']}"), text.tiny, (255, 255, 240), (r.centerx, r.y + 58))
            if unlocked:
                got = save.stars(i)
                for s in range(3):
                    draw_star(surf, r.centerx - 36 + s * 36, r.y + 92, 13, s < got)
            else:
                dark = pygame.Surface(r.size, pygame.SRCALPHA)
                pygame.draw.rect(dark, (0, 0, 0, 140), dark.get_rect(), border_radius=16)
                surf.blit(dark, r)
                draw_lock(surf, r.centerx, r.y + 95, 18)

        text.draw(surf, tr("levels.footer"), text.small, (230, 230, 230), (W / 2, 600))
