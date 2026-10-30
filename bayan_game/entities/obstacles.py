"""Static things on the map: rocks and circular zones (quicksand, poison, bushes)."""
import math
import random

import pygame
from pygame import Vector2 as V


class Rock:
    def __init__(self, x, y, r):
        self.pos = V(x, y)
        self.r = r
        # bumpy outline so rocks don't look like perfect circles
        self.shape = []
        for i in range(10):
            a = i / 10 * 2 * math.pi
            rr = r * random.uniform(0.85, 1.08)
            self.shape.append((math.cos(a) * rr, math.sin(a) * rr))

    def push_out(self, pos, radius):
        d = pos - self.pos
        dist = d.length()
        min_d = self.r + radius
        if dist < min_d:
            if dist == 0:
                d, dist = V(1, 0), 1
            pos.update(self.pos + d / dist * min_d)

    def draw(self, surf, terrain):
        x, y = self.pos
        shadow = (40, 90, 40) if terrain in ("grass", "forest") else (60, 50, 50)
        pygame.draw.ellipse(surf, shadow, (x - self.r, y + self.r * 0.5, self.r * 2, self.r * 0.8))
        pts = [(x + px, y + py) for px, py in self.shape]
        body = (95, 80, 80) if terrain == "lair" else (120, 115, 110)
        pygame.draw.polygon(surf, body, pts)
        pygame.draw.polygon(surf, (70, 62, 60), pts, 3)
        pygame.draw.circle(surf, (160, 155, 150), (int(x - self.r * 0.3), int(y - self.r * 0.3)), max(3, self.r // 4))
        if terrain == "snow":
            pygame.draw.ellipse(surf, (250, 252, 255), (x - self.r * 0.8, y - self.r, self.r * 1.6, self.r * 0.7))


class Zone:
    """kind: "sand" (slows), "poison" (slows, fades away) or "bush" (hides Bayan)."""

    def __init__(self, kind, pos, r, life=None):
        self.kind = kind
        self.pos = V(pos)
        self.r = r
        self.life = life
        self.max_life = life
        self.seed = random.uniform(0, 10)
        if kind == "bush":
            self.blobs = []
            for _ in range(9):
                a = random.uniform(0, 2 * math.pi)
                d = random.uniform(0, r * 0.55)
                self.blobs.append((math.cos(a) * d, math.sin(a) * d, random.uniform(r * 0.4, r * 0.55)))

    def contains(self, p, margin=0):
        return (p - self.pos).length() < self.r - margin

    @property
    def expired(self):
        return self.life is not None and self.life <= 0

    def update(self, dt):
        if self.life is not None:
            self.life -= dt

    def draw(self, surf, t, see_through=False):
        x, y = self.pos
        r = self.r
        if self.kind == "sand":
            pygame.draw.ellipse(surf, (196, 150, 85), (x - r, y - r * 0.75, r * 2, r * 1.5))
            for i in range(3):
                k = 0.8 - i * 0.22
                a = t * (1.5 + i) + self.seed
                rect = (x - r * k, y - r * 0.75 * k, r * 2 * k, r * 1.5 * k)
                pygame.draw.arc(surf, (160, 115, 60), rect, a, a + 2.2, 2)
        elif self.kind == "poison":
            fade = min(1.0, self.life / 1.5) if self.life is not None else 1.0
            s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            c = r + 2
            pygame.draw.ellipse(s, (130, 220, 60, int(140 * fade)), (2, c - r * 0.7, r * 2, r * 1.4))
            for i in range(3):
                bx = c + math.cos(self.seed + i * 2) * r * 0.45
                by = c + math.sin(self.seed + i * 2) * r * 0.3
                br = 2 + (math.sin(t * 4 + i + self.seed) + 1) * 2
                pygame.draw.circle(s, (200, 255, 150, int(200 * fade)), (int(bx), int(by)), int(br), 1)
            surf.blit(s, (x - c, y - c))
        elif self.kind == "bush":
            s = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
            c = r * 1.5
            for bx, by, br in self.blobs:
                pygame.draw.circle(s, (30, 80, 35), (int(c + bx), int(c + by)), int(br) + 2)
            for bx, by, br in self.blobs:
                pygame.draw.circle(s, (55, 135, 55), (int(c + bx), int(c + by)), int(br))
                pygame.draw.circle(s, (85, 170, 75), (int(c + bx - br * 0.3), int(c + by - br * 0.3)), int(br * 0.35))
            if see_through:
                s.set_alpha(165)
            surf.blit(s, (x - c, y - c))
