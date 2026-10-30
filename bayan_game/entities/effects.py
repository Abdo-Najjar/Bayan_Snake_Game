"""Short-lived visual effects: particle bursts and floating text."""
import math
import random

import pygame
from pygame import Vector2 as V


class Effects:
    def __init__(self):
        self.particles = []   # [pos, vel, life, color]
        self.floaters = []    # [image, pos, life]

    def burst(self, pos, color, n=18, speed=160):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(speed * 0.3, speed)
            self.particles.append([V(pos), V(math.cos(a), math.sin(a)) * s, random.uniform(0.4, 0.8), color])

    def floater(self, image, pos, life=1.2):
        self.floaters.append([image, V(pos), life])

    def update(self, dt):
        for p in self.particles:
            p[0] += p[1] * dt
            p[1] *= 0.92
            p[2] -= dt
        self.particles = [p for p in self.particles if p[2] > 0]
        for f in self.floaters:
            f[1].y -= 40 * dt
            f[2] -= dt
        self.floaters = [f for f in self.floaters if f[2] > 0]

    def draw(self, surf):
        for pos, _, life, col in self.particles:
            pygame.draw.circle(surf, col, (int(pos.x), int(pos.y)), max(1, int(life * 6)))
        for img, pos, life in self.floaters:
            img.set_alpha(int(255 * min(1.0, life * 2)))
            surf.blit(img, img.get_rect(center=pos))
