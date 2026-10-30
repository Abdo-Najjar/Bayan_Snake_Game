"""Bayan, the player character."""
import math

import pygame
from pygame import Vector2 as V

from .. import config
from ..config import W, H, TOP
from ..graphics.art import mix, shade
from ..utils import clamp

SKIN = (255, 214, 170)
HAIR = (80, 45, 25)


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
    def draw(self, surf, t, label=None, alpha=255, shield=False):
        for gpos, life in self.ghosts:
            s = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.dress, int(life * 600)), (15, 15), 12)
            surf.blit(s, (gpos.x - 15, gpos.y - 15))

        if self.invuln > 0 and int(t * 14) % 2 == 0:
            return  # blink while protected

        sprite = self.render_sprite()
        if alpha < 255:
            sprite.set_alpha(alpha)
        surf.blit(sprite, (self.pos.x - 32, self.pos.y - 50))

        if shield:
            r = 26 + int(math.sin(t * 6) * 2)
            bubble = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(bubble, (90, 170, 255, 60), (r + 2, r + 2), r)
            pygame.draw.circle(bubble, (160, 210, 255, 200), (r + 2, r + 2), r, 2)
            surf.blit(bubble, (self.pos.x - r - 2, self.pos.y - r - 6))
        if label is not None:
            surf.blit(label, label.get_rect(center=(self.pos.x, self.pos.y - 42)))

    def render_sprite(self):
        """Bayan drawn on a 64x80 transparent surface; body center at (32, 50)."""
        s = pygame.Surface((64, 80), pygame.SRCALPHA)
        x, y = 32, 50
        fx = self.facing.x
        moving = self.vel.length_squared() > 1
        swing = math.sin(self.walk) * 4 if moving else 0
        dress, dark = self.dress, shade(self.dress, 0.75)

        pygame.draw.ellipse(s, (0, 0, 0, 60), (x - 12, y + 12, 24, 8))
        # legs and shoes
        pygame.draw.line(s, SKIN, (x - 4, y + 8), (x - 4 + swing, y + 16), 3)
        pygame.draw.line(s, SKIN, (x + 4, y + 8), (x + 4 - swing, y + 16), 3)
        pygame.draw.circle(s, dark, (int(x - 4 + swing), y + 17), 3)
        pygame.draw.circle(s, dark, (int(x + 4 - swing), y + 17), 3)
        # arms
        pygame.draw.line(s, SKIN, (x - 6, y - 3), (x - 11 - swing * 0.5, y + 5), 3)
        pygame.draw.line(s, SKIN, (x + 6, y - 3), (x + 11 + swing * 0.5, y + 5), 3)
        # dress
        body = [(x, y - 9), (x - 12, y + 11), (x + 12, y + 11)]
        pygame.draw.polygon(s, dress, body)
        pygame.draw.polygon(s, dark, body, 2)
        pygame.draw.line(s, (255, 255, 255), (x - 9, y + 7), (x + 9, y + 7), 2)

        looking_away = self.facing.y < -0.7
        if self.hat == "hijab":
            scarf = mix(dress, (255, 255, 255), 0.45)
            pygame.draw.polygon(s, scarf, [(x - 10, y - 17), (x + 10, y - 17), (x + 12, y - 3), (x - 12, y - 3)])
            pygame.draw.circle(s, scarf, (x, y - 17), 11)
            pygame.draw.circle(s, shade(scarf, 0.8), (x, y - 17), 11, 1)
            if not looking_away:
                pygame.draw.circle(s, SKIN, (int(x + fx * 2), y - 15), 7)
                self._face(s, x + fx * 2.5, y - 16)
            return s

        bounce = math.sin(self.walk * 0.5) * 2
        tail_x = x - (fx if abs(fx) > 0.2 else 0.6) * 11
        pygame.draw.circle(s, HAIR, (int(tail_x), int(y - 13 + bounce)), 5)
        pygame.draw.circle(s, HAIR, (x, y - 17), 10)
        if not looking_away:
            pygame.draw.circle(s, SKIN, (int(x + fx * 2), y - 14), 8)
            self._face(s, x + fx * 3, y - 15)
        self._hat(s, x, y, fx)
        return s

    @staticmethod
    def _face(s, ex, ey):
        pygame.draw.circle(s, (30, 30, 30), (int(ex - 3), int(ey)), 2)
        pygame.draw.circle(s, (30, 30, 30), (int(ex + 3), int(ey)), 2)
        pygame.draw.circle(s, (240, 120, 120), (int(ex - 5), int(ey + 4)), 2)
        pygame.draw.circle(s, (240, 120, 120), (int(ex + 5), int(ey + 4)), 2)
        pygame.draw.arc(s, (150, 50, 50), (ex - 3, ey + 1, 6, 5), math.pi + 0.3, 2 * math.pi - 0.3, 1)

    def _hat(self, s, x, y, fx):
        if self.hat == "bow":
            pygame.draw.polygon(s, (230, 40, 80), [(x, y - 26), (x - 6, y - 30), (x - 6, y - 22)])
            pygame.draw.polygon(s, (230, 40, 80), [(x, y - 26), (x + 6, y - 30), (x + 6, y - 22)])
            pygame.draw.circle(s, (255, 200, 220), (x, y - 26), 2)
        elif self.hat == "flower":
            cx, cy = x + 6, y - 24
            for i in range(5):
                a = i / 5 * 2 * math.pi
                pygame.draw.circle(s, (255, 130, 180), (int(cx + math.cos(a) * 3.5), int(cy + math.sin(a) * 3.5)), 3)
            pygame.draw.circle(s, (255, 220, 60), (cx, cy), 2)
        elif self.hat == "crown":
            pts = [(x - 8, y - 24), (x - 8, y - 32), (x - 4, y - 27), (x, y - 34),
                   (x + 4, y - 27), (x + 8, y - 32), (x + 8, y - 24)]
            pygame.draw.polygon(s, (250, 205, 50), pts)
            pygame.draw.polygon(s, (200, 150, 20), pts, 1)
            pygame.draw.circle(s, (230, 40, 80), (x, y - 27), 2)
        elif self.hat == "cap":
            cap = shade(self.dress, 0.85)
            pygame.draw.ellipse(s, cap, (x - 11, y - 30, 22, 11))
            brim_x = x + (fx if abs(fx) > 0.2 else 0.5) * 9
            pygame.draw.ellipse(s, shade(cap, 0.8), (brim_x - 7, y - 23, 14, 4))
