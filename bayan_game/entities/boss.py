"""The giant snake fought in the last level.

Cycle: chase -> aim (telegraphed) -> charge in a straight line.
Charging into a rock costs it one HP and stuns it; hitting a wall only stuns it briefly.
"""
import math

import pygame
from pygame import Vector2 as V

from .. import config
from ..config import W, H, TOP
from ..graphics.art import star_points
from ..utils import angle_diff, clamp
from .snake import Snake

CHASE_TIME = 3.5
AIM_TIME = 0.95
CHARGE_TIME = 1.6
STUN_ROCK = 2.6
STUN_WALL = 1.0


class Boss(Snake):
    def __init__(self, pos, cfg, speed_mult=1.0):
        super().__init__(pos, "normal", cfg, speed_mult)
        self.kind = "boss"
        self.head_r = 24
        self.spacing = 17
        self.body = [V(pos) for _ in range(20)]
        self.color, self.color2 = (130, 45, 55), (85, 28, 38)
        self.hp = config.BOSS_HP
        self.mode_t = CHASE_TIME
        self.flash = 0.0

    @property
    def harmful(self):
        return self.mode != "stunned"

    def place(self, pos, toward):
        super().place(pos, toward)
        self.mode_t = CHASE_TIME

    def grow(self, n=2):
        pass  # the boss doesn't grow from gems

    def update(self, dt, target, visible, rocks, zones, t):
        events = []
        self.flash = max(0.0, self.flash - dt)
        if self.sleep > 0:
            self.sleep -= dt
            return events
        self.mode_t -= dt

        if self.mode == "chase":
            goal = self.choose_goal(dt, target, visible)
            self.steer(goal - self.head, dt, rocks)
            self.advance(dt, self.speed, 0.3, rocks, t)
            if self.mode_t <= 0 and visible:
                self.mode, self.mode_t = "aim", AIM_TIME
                events.append(("hiss", None))

        elif self.mode == "aim":
            d = target.pos - self.head
            self.angle += clamp(angle_diff(math.atan2(d.y, d.x), self.angle), -5 * dt, 5 * dt)
            if self.mode_t <= 0:
                self.mode, self.mode_t = "charge", CHARGE_TIME

        elif self.mode == "charge":
            head = self.head
            head += V(math.cos(self.angle), math.sin(self.angle)) * config.BOSS_CHARGE_SPEED * dt
            hit = next((r for r in rocks if (head - r.pos).length() < r.r + self.head_r), None)
            out = not (self.head_r <= head.x <= W - self.head_r and TOP + self.head_r <= head.y <= H - self.head_r)
            if hit:
                hit.push_out(head, self.head_r)
                self.hp -= 1
                self.flash = 0.4
                self.mode, self.mode_t = "stunned", STUN_ROCK
                events.append(("boss_hit", hit))
            elif out:
                head.x = clamp(head.x, self.head_r, W - self.head_r)
                head.y = clamp(head.y, TOP + self.head_r, H - self.head_r)
                self.mode, self.mode_t = "stunned", STUN_WALL
                events.append(("boss_wall", None))
            elif self.mode_t <= 0:
                self.mode, self.mode_t = "chase", CHASE_TIME
            self.follow()

        elif self.mode == "stunned":
            if self.mode_t <= 0:
                self.mode, self.mode_t = "chase", (CHASE_TIME if self.hp > 1 else 2.4)
        return events

    def draw(self, surf, t, frozen=False):
        if self.mode == "aim":
            # dashed line showing where the charge will go
            fwd = V(math.cos(self.angle), math.sin(self.angle))
            for i in range(2, 16):
                if i % 2 == 0:
                    a = self.head + fwd * (i * 22)
                    b = self.head + fwd * (i * 22 + 14)
                    pygame.draw.line(surf, (255, 70, 70), a, b, 3)
        if self.flash > 0:
            c1 = c2 = (255, 255, 255)
        elif frozen:
            c1, c2 = (170, 215, 240), (130, 180, 220)
        else:
            c1, c2 = self.color, self.color2
        n = len(self.body)
        for i in range(n - 1, 0, -1):
            k = i / (n - 1)
            r = self.head_r * (1 - 0.55 * k)
            p = self.body[i]
            pygame.draw.circle(surf, c2, (int(p.x), int(p.y)), int(r) + 2)
            pygame.draw.circle(surf, c1, (int(p.x), int(p.y)), int(r))
            pygame.draw.circle(surf, (230, 180, 80), (int(p.x), int(p.y)), max(2, int(r * 0.3)))

        h = self.head
        fwd = V(math.cos(self.angle), math.sin(self.angle))
        side = V(-fwd.y, fwd.x)
        for s in (1, -1):  # horns
            base = h - fwd * 6 + side * 14 * s
            tip = h - fwd * 22 + side * 24 * s
            pygame.draw.polygon(surf, (235, 225, 200), [base - fwd * 6, base + fwd * 6, tip])
        self.draw_head(surf, t, c1, c2, frozen)

        if self.mode == "stunned":
            for i in range(3):
                a = t * 4 + i * 2.1
                cx = h.x + math.cos(a) * 26
                cy = h.y - 28 + math.sin(a) * 8
                pygame.draw.polygon(surf, (255, 220, 60), star_points(cx, cy, 6))
