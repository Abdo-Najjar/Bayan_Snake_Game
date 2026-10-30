"""Snakes that chase Bayan.

Kinds (see content/levels.py):
  normal - steady chaser
  small  - short, fast and agile
  lunger - shakes for a moment, then lunges straight ahead
  poison - drops poison puddles that slow Bayan down
"""
import math
import random

import pygame
from pygame import Vector2 as V

from .. import config
from ..config import W, H, TOP
from ..content.levels import SNAKE_TYPES
from ..graphics.art import aa_circle
from ..utils import angle_diff, clamp

FROZEN = ((170, 215, 240), (130, 180, 220))
LUNGE_RANGE = 190
LUNGE_AIM_TIME = 0.55
LUNGE_TIME = 0.42
LUNGE_SPEED_MULT = 3.3
LUNGE_COOLDOWN = 3.0
POISON_DROP_EVERY = 1.7


class Snake:
    def __init__(self, pos, kind, cfg, speed_mult=1.0, phase=0.0):
        st = SNAKE_TYPES[kind]
        self.kind = kind
        self.speed = cfg["speed"] * st["speed"] * speed_mult
        self.turn = cfg["turn"] * st["turn"]
        self.predict = cfg.get("predict", 0.0)
        self.head_r = st["head_r"]
        self.spacing = self.head_r * 0.85
        self.color, self.color2 = st["colors"]
        self.body = [V(pos) for _ in range(st["length"])]
        self.angle = 0.0
        self.phase = phase
        self.sleep = 0.0
        self.mode = "chase"
        self.mode_t = 0.0
        self.lunge_cd = 2.5
        self.drop_t = 1.5
        self.last_seen = None
        self.wander = None
        self.wander_t = 0.0

    # ---------------------------------------------------------------- basics
    @property
    def head(self):
        return self.body[0]

    @property
    def harmful(self):
        return True

    def place(self, pos, toward):
        for seg in self.body:
            seg.update(pos)
        d = toward - pos
        self.angle = math.atan2(d.y, d.x)
        self.mode = "chase"
        self.last_seen = None

    def grow(self, n=2):
        for _ in range(n):
            self.body.append(V(self.body[-1]))
        self.speed = min(config.SNAKE_MAX_SPEED, self.speed * config.SNAKE_GROWTH)

    def catches(self, bayan):
        return self.harmful and (self.head - bayan.pos).length() < self.head_r + bayan.R - 3

    # ---------------------------------------------------------------- movement
    def choose_goal(self, dt, target, visible):
        """Chase Bayan when visible, otherwise check her last spot, then wander."""
        if visible:
            self.last_seen = V(target.pos)
            return target.pos + target.vel * self.predict
        if self.last_seen is not None and (self.last_seen - self.head).length() > 25:
            return self.last_seen
        self.last_seen = None
        self.wander_t -= dt
        if self.wander is None or self.wander_t <= 0 or (self.wander - self.head).length() < 30:
            self.wander = V(random.uniform(60, W - 60), random.uniform(TOP + 60, H - 60))
            self.wander_t = 3.0
        return self.wander

    def steer(self, want, dt, rocks, avoid=True):
        if want.length_squared() == 0:
            want = V(1, 0)
        want = want.normalize()
        head = self.head
        if avoid:
            fwd = V(math.cos(self.angle), math.sin(self.angle))
            for r in rocks:
                d = head - r.pos
                dist = d.length()
                reach = r.r + 70
                if 0 < dist < reach and fwd.dot(-d) > 0:
                    want += d / dist * ((reach - dist) / 70) * 1.6
            m = 45
            if head.x < m:
                want.x += (m - head.x) / m
            if head.x > W - m:
                want.x -= (head.x - (W - m)) / m
            if head.y < TOP + m:
                want.y += (TOP + m - head.y) / m
            if head.y > H - m:
                want.y -= (head.y - (H - m)) / m
        desired = math.atan2(want.y, want.x)
        step = self.turn * dt
        self.angle += clamp(angle_diff(desired, self.angle), -step, step)

    def advance(self, dt, speed, wiggle, rocks, t):
        ang = self.angle + math.sin(t * 7 + self.phase) * wiggle
        head = self.head
        head += V(math.cos(ang), math.sin(ang)) * speed * dt
        for r in rocks:
            r.push_out(head, self.head_r)
        head.x = clamp(head.x, self.head_r, W - self.head_r)
        head.y = clamp(head.y, TOP + self.head_r, H - self.head_r)
        self.follow()

    def follow(self):
        """Each body segment trails the one before it like a chain."""
        for i in range(1, len(self.body)):
            prev, seg = self.body[i - 1], self.body[i]
            d = seg - prev
            dist = d.length()
            if dist > self.spacing:
                seg.update(prev + d / dist * self.spacing)

    def update(self, dt, target, visible, rocks, zones, t):
        """Returns a list of (event, data) tuples for the game to react to."""
        events = []
        if self.sleep > 0:
            self.sleep -= dt
            return events

        goal = self.choose_goal(dt, target, visible)
        in_sand = any(z.kind == "sand" and z.contains(self.head) for z in zones)
        speed = self.speed * (0.55 if in_sand else 1.0) * (1.0 if visible else 0.8)

        if self.kind == "lunger":
            self.lunge_cd -= dt
            if (self.mode == "chase" and visible and self.lunge_cd <= 0
                    and (target.pos - self.head).length() < LUNGE_RANGE):
                self.mode, self.mode_t = "aim", LUNGE_AIM_TIME
                events.append(("hiss", None))
            if self.mode == "aim":
                self.mode_t -= dt
                d = target.pos - self.head
                self.angle += clamp(angle_diff(math.atan2(d.y, d.x), self.angle), -6 * dt, 6 * dt)
                if self.mode_t <= 0:
                    self.mode, self.mode_t = "lunge", LUNGE_TIME
                return events
            if self.mode == "lunge":
                self.mode_t -= dt
                self.advance(dt, speed * LUNGE_SPEED_MULT, 0, rocks, t)
                if self.mode_t <= 0:
                    self.mode, self.lunge_cd = "chase", LUNGE_COOLDOWN
                return events

        if self.kind == "poison":
            self.drop_t -= dt
            if self.drop_t <= 0:
                self.drop_t = POISON_DROP_EVERY
                events.append(("puddle", V(self.body[-1])))

        self.steer(goal - self.head, dt, rocks)
        self.advance(dt, speed, 0.45, rocks, t)
        return events

    # ---------------------------------------------------------------- drawing
    def draw(self, surf, t, frozen=False):
        c1, c2 = FROZEN if frozen else (self.color, self.color2)
        n = len(self.body)
        for i in range(n - 1, 0, -1):
            k = i / (n - 1)
            r = self.head_r * (1 - 0.6 * k)
            p = self.body[i]
            col = c1 if i % 2 else c2
            aa_circle(surf, col, (int(p.x), int(p.y)), int(r))
            hl = tuple(min(255, v + 50) for v in col)
            aa_circle(surf, hl, (int(p.x - r * 0.3), int(p.y - r * 0.3)), max(1, int(r * 0.3)))
        self.draw_head(surf, t, c1, c2, frozen)

    def draw_head(self, surf, t, c1, c2, frozen):
        h = V(self.head)
        aiming = self.mode == "aim"
        if aiming:
            h += V(random.uniform(-2, 2), random.uniform(-2, 2))
        fwd = V(math.cos(self.angle), math.sin(self.angle))
        side = V(-fwd.y, fwd.x)
        r = self.head_r
        if (t * 2.5 + self.phase) % 1 < 0.35 and self.sleep <= 0 and not frozen:
            base = h + fwd * (r + 1)
            tip = base + fwd * 10
            pygame.draw.line(surf, (220, 30, 50), base, tip, 2)
            pygame.draw.line(surf, (220, 30, 50), tip, tip + fwd * 5 + side * 4, 2)
            pygame.draw.line(surf, (220, 30, 50), tip, tip + fwd * 5 - side * 4, 2)
        aa_circle(surf, c2, (int(h.x), int(h.y)), r + 2)
        aa_circle(surf, c1, (int(h.x), int(h.y)), r)
        eye_col = (255, 60, 60) if aiming else (255, 240, 120)
        eye_r = max(3, r // 3)
        for s in (1, -1):
            e = h + fwd * (r * 0.4) + side * (r * 0.45) * s
            aa_circle(surf, eye_col, (int(e.x), int(e.y)), eye_r)
            if self.sleep > 0 or frozen:
                pygame.draw.line(surf, (20, 20, 20), (e.x - eye_r + 1, e.y), (e.x + eye_r - 1, e.y), 2)
            else:
                pygame.draw.ellipse(surf, (20, 20, 20), (e.x + fwd.x * 1.5 - 1, e.y + fwd.y * 1.5 - eye_r + 1,
                                                         2, eye_r * 2 - 2))
        if aiming:
            # warning mark above the head
            aa_circle(surf, (230, 40, 40), (int(h.x), int(h.y - r - 14)), 8)
            pygame.draw.line(surf, (255, 255, 255), (h.x, h.y - r - 19), (h.x, h.y - r - 12), 2)
            aa_circle(surf, (255, 255, 255), (int(h.x), int(h.y - r - 9)), 1)
