"""Bayan, the player character."""
import math

import pygame
from pygame import Vector2 as V

from .. import config
from ..config import W, H, TOP
from ..graphics.art import aa_circle
from ..graphics.sprites import bank
from ..utils import clamp

WALK_FRAMES = 4      # frames 1..4 of the sprite sheet; frame 0 is standing still


class Bayan:
    R = config.BAYAN_RADIUS

    def __init__(self, x, y, dress=(255, 105, 180), hat="bow"):
        self.pos = V(x, y)
        self.vel = V()
        self.facing = V(1, 0)
        self.dress = dress
        self.hat = hat
        self.dash_t = 0.0
        self.dash_cd = 0.0
        self.invuln = 0.0
        self.walk = 0.0
        self.ghosts = []

    # ---------------------------------------------------------------- state
    @property
    def dashing(self):
        return self.dash_t > 0

    @property
    def safe(self):
        return self.dashing or self.invuln > 0

    @property
    def dash_ready(self):
        return 1 - self.dash_cd / config.DASH_COOLDOWN

    def try_dash(self):
        if self.dash_cd <= 0:
            self.dash_t = config.DASH_TIME
            self.dash_cd = config.DASH_COOLDOWN
            return True
        return False

    # ---------------------------------------------------------------- update
    def update(self, dt, direction, rocks, slow=False, ice=False, boost=False):
        old = V(self.pos)
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.facing = V(direction)

        speed = config.BAYAN_SPEED
        if boost:
            speed *= config.SPEED_BOOST
        if slow:
            speed *= config.SLOW_FACTOR

        if self.dashing:
            desired = self.facing * config.DASH_SPEED
            self.ghosts.append([V(self.pos), 0.25])
        else:
            desired = direction * speed

        if ice and not self.dashing:
            self.vel += (desired - self.vel) * min(1.0, config.ICE_GRIP * dt)
        else:
            self.vel = V(desired)

        self.pos += self.vel * dt
        self.pos.x = clamp(self.pos.x, self.R, W - self.R)
        self.pos.y = clamp(self.pos.y, TOP + self.R, H - self.R)
        for r in rocks:
            r.push_out(self.pos, self.R)
        if dt > 0:
            self.vel = (self.pos - old) / dt   # walls and rocks stop momentum

        if self.vel.length_squared() > 1:
            self.walk += dt * 14
        self.dash_t = max(0.0, self.dash_t - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.invuln = max(0.0, self.invuln - dt)
        for g in self.ghosts:
            g[1] -= dt
        self.ghosts = [g for g in self.ghosts if g[1] > 0]

    # ---------------------------------------------------------------- drawing
    def sprite_pose(self):
        """(direction, frame, flip) for the current facing and walk cycle."""
        fx, fy = self.facing.x, self.facing.y
        if abs(fy) > abs(fx):
            direction, flip = ("down" if fy > 0 else "up"), False
        else:
            direction, flip = "side", fx < 0
        moving = self.vel.length_squared() > 1
        frame = 1 + int(self.walk / (math.pi / 2)) % WALK_FRAMES if moving else 0
        return direction, frame, flip

    def render_sprite(self, scale=1.0):
        """Bayan on a (64, 80) * scale transparent surface; body center at (32, 50) * scale."""
        direction, frame, flip = self.sprite_pose()
        return bank().bayan(direction, frame, self.dress, self.hat, flip, scale)

    def draw(self, surf, t, label=None, alpha=255, shield=False):
        for gpos, life in self.ghosts:
            s = pygame.Surface((30, 30), pygame.SRCALPHA)
            aa_circle(s, (*self.dress, int(life * 600)), (15, 15), 12)
            surf.blit(s, (gpos.x - 15, gpos.y - 15))

        if self.invuln > 0 and int(t * 14) % 2 == 0:
            return  # blink while protected

        sprite = self.render_sprite()
        if alpha < 255:
            sprite = sprite.copy()      # the sprite is cached, don't change the shared one
            sprite.set_alpha(alpha)
        surf.blit(sprite, (self.pos.x - 32, self.pos.y - 50))

        if shield:
            r = 26 + int(math.sin(t * 6) * 2)
            bubble = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            aa_circle(bubble, (90, 170, 255, 60), (r + 2, r + 2), r)
            aa_circle(bubble, (160, 210, 255, 200), (r + 2, r + 2), r, 2)
            surf.blit(bubble, (self.pos.x - r - 2, self.pos.y - r - 6))
        if label is not None:
            surf.blit(label, label.get_rect(center=(self.pos.x, self.pos.y - 44)))
