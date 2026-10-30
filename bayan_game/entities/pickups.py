"""Power-ups lying on the map."""
import math

import pygame

from .. import config
from ..graphics.art import POWER_COLORS, draw_power_icon


class PowerUp:
    def __init__(self, kind, pos):
        self.kind = kind
        self.pos = pos
        self.life = config.POWER_LIFETIME

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, surf, t):
        if self.life < 2 and int(t * 8) % 2:
            return
        x = self.pos.x
        y = self.pos.y + math.sin(t * 4) * 3
        glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*POWER_COLORS[self.kind], 80), (30, 30), 22 + int(math.sin(t * 6) * 2))
        surf.blit(glow, (x - 30, y - 30))
        pygame.draw.circle(surf, (40, 50, 70), (int(x), int(y)), 16)
        pygame.draw.circle(surf, POWER_COLORS[self.kind], (int(x), int(y)), 16, 3)
        draw_power_icon(surf, self.kind, x, y, 10)
