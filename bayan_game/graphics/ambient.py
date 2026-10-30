"""Gentle moving details on top of each terrain: pollen, blowing sand, snow, fireflies, embers."""
import math
import random

import pygame

from ..config import W, H, TOP

# terrain: (count, color, size range, base velocity, glow)
STYLES = {
    "grass": (26, (255, 250, 200), (1.5, 2.5), (12, -6), False),
    "desert": (45, (245, 215, 160), (1.0, 2.0), (140, 10), False),
    "snow": (70, (255, 255, 255), (1.5, 3.5), (-15, 45), False),
    "forest": (22, (210, 255, 120), (2.0, 3.0), (0, 0), True),
    "lair": (38, (255, 140, 50), (1.5, 3.0), (5, -40), True),
}


class Ambient:
    def __init__(self, terrain):
        self.count, self.color, self.size, self.vel, self.glow = STYLES.get(terrain, STYLES["grass"])
        self.parts = [self._new(random.uniform(0, W), random.uniform(TOP, H)) for _ in range(self.count)]
        self.glow_img = None
        if self.glow:
            self.glow_img = pygame.Surface((24, 24), pygame.SRCALPHA)
            for r in range(12, 0, -2):
                pygame.draw.circle(self.glow_img, (*self.color, int(70 * (1 - r / 12)) + 10), (12, 12), r)

    def _new(self, x, y):
        return [x, y, random.uniform(*self.size), random.uniform(0, 6.28), random.uniform(0.6, 1.4)]

    def update(self, dt, t):
        vx, vy = self.vel
        for p in self.parts:
            x, y, size, phase, speed = p
            p[0] = x + (vx * speed + math.sin(t * 1.5 + phase) * 15) * dt
            p[1] = y + (vy * speed + math.cos(t * 1.2 + phase) * 10) * dt
            if p[0] < -10 or p[0] > W + 10 or p[1] < TOP - 10 or p[1] > H + 10:
                # re-enter from the side the wind comes from
                if abs(vx) > abs(vy):
                    nx, ny = (-5 if vx > 0 else W + 5), random.uniform(TOP, H)
                elif vy != 0:
                    nx, ny = random.uniform(0, W), (TOP - 5 if vy > 0 else H + 5)
                else:
                    nx, ny = random.uniform(0, W), random.uniform(TOP, H)
                p[:] = self._new(nx, ny)

    def draw(self, surf, t):
        for x, y, size, phase, _ in self.parts:
            if self.glow:
                twinkle = (math.sin(t * 3 + phase) + 1) / 2
                if twinkle < 0.2:
                    continue
                surf.blit(self.glow_img, (x - 12, y - 12))
            pygame.draw.circle(surf, self.color, (int(x), int(y)), max(1, int(size)))
