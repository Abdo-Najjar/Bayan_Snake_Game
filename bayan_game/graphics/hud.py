"""The info bar at the top of the gameplay screen."""
import math

import pygame
from pygame import Vector2 as V

from .. import config
from ..config import W, TOP
from .art import POWER_COLORS, draw_coin, draw_gem, draw_heart, draw_power_icon


def draw_hud(surf, app, game):
    text, tr = app.text, app.tr
    bar = pygame.Surface((W, TOP), pygame.SRCALPHA)
    bar.fill((20, 40, 25, 215))
    surf.blit(bar, (0, 0))

    # lives
    for i in range(config.START_LIVES):
        draw_heart(surf, 28 + i * 34, 22, 20, i < game.lives)

    # dash meter
    ready = game.bayan.dash_ready
    pygame.draw.rect(surf, (60, 60, 60), (130, 17, 110, 16), border_radius=8)
    pygame.draw.rect(surf, (120, 220, 255) if ready >= 1 else (90, 140, 170),
                     (130, 17, int(110 * ready), 16), border_radius=8)
    text.draw(surf, tr("hud.dash"), text.tiny, (255, 255, 255), (185, 25), shadow=False)

    # active power-ups with a ring showing time left
    x = 270
    for kind, left, total in game.active_powers():
        pygame.draw.circle(surf, (40, 50, 70), (x, 26), 17)
        if total:
            end = -math.pi / 2 + 2 * math.pi * (left / total)
            pygame.draw.arc(surf, POWER_COLORS[kind], (x - 17, 9, 34, 34), -math.pi / 2, end, 3)
        else:
            pygame.draw.circle(surf, POWER_COLORS[kind], (x, 26), 17, 3)
        draw_power_icon(surf, kind, x, 26, 9)
        x += 42

    # middle: gems or boss health
    cx = W / 2 + 40
    if game.boss:
        text.draw(surf, tr("hud.boss"), text.tiny, (255, 200, 200), (cx, 14))
        for i in range(config.BOSS_HP):
            col = (230, 50, 60) if i < game.boss.hp else (70, 70, 70)
            pygame.draw.rect(surf, col, (cx - 75 + i * 52, 26, 46, 14), border_radius=5)
    else:
        draw_gem(surf, V(cx - 50, 26), game.t, 10)
        text.draw(surf, f"{game.collected} / {game.goal}", text.mid, (255, 235, 120), (cx + 10, 25))

    # right: coins and level
    draw_coin(surf, W - 250, 26)
    text.draw(surf, str(app.save["coins"]), text.small, (255, 230, 120), (W - 235, 25), align="midleft")
    text.draw(surf, tr("hud.level", n=game.level_index + 1), text.small, (255, 255, 255), (W - 80, 25))
