"""Step-by-step tutorial: move, gems, dash, power-ups, then a slow practice snake."""
import math

import pygame
from pygame import Vector2 as V

from ..config import W, H, TOP
from ..content.shop import dress_color
from ..entities.bayan import Bayan
from ..entities.effects import Effects
from ..entities.pickups import PowerUp
from ..entities.snake import Snake
from ..graphics.ambient import Ambient
from ..graphics.art import aa_circle, background, draw_gem, draw_star, vignette
from ..graphics.ui import MenuList, draw_keycap, overlay, panel
from .base import Scene

STEPS = ("move", "gem", "dash", "power", "snake")
GOALS = {"move": 3, "gem": 2, "dash": 2, "power": 1, "snake": 3}
HINTS = {"move": "tutorial.move_hint", "dash": "tutorial.dash_hint", "power": "tutorial.power_hint",
         "snake": "tutorial.snake_hint"}
MOVE_TARGETS = (V(220, 260), V(740, 300), V(480, 500))
GEM_SPOTS = (V(250, 470), V(720, 220), V(160, 250), V(800, 500), V(480, 230))
PRACTICE_SNAKE = dict(speed=72, turn=2.0)
STEP_PAUSE = 1.0


class TutorialScene(Scene):
    music = "tutorial"
    ambience = "grass"
    show_cursor = False

    def __init__(self, app, then):
        super().__init__(app)
        self.then = then                       # called when the tutorial is skipped
        save = app.save
        self.bayan = Bayan(W / 2, (TOP + H) / 2 + 40, dress_color(save["dress"]), save["hat"])
        self.effects = Effects()
        self.ambient = Ambient("grass")
        self.step_i = -1
        self.progress = 0
        self.wait = 0.0                        # short pause after finishing a step
        self.gem = None
        self.gem_i = 0
        self.power = None
        self.snake = None
        self.shield = False
        self.menu = None
        self.next_step()

    # ---------------------------------------------------------------- flow
    @property
    def step(self):
        return STEPS[self.step_i] if self.step_i < len(STEPS) else "done"

    def next_step(self):
        self.step_i += 1
        self.progress = 0
        self.gem = self.power = None
        if self.step in ("gem", "snake"):
            self.spawn_gem()
        elif self.step == "power":
            self.power = PowerUp("shield", V(720, 420))
            self.power.life = float("inf")
        if self.step == "snake":
            self.snake = Snake(V(60, TOP + 60), "normal", PRACTICE_SNAKE)
            self.snake.place(V(60, TOP + 60), self.bayan.pos)
            self.snake.sleep = 1.0
        if self.step == "done":
            self.finish_tutorial()

    def finish_tutorial(self):
        self.app.save["tutorial_done"] = True
        self.app.save.write()
        self.app.sfx.play("level")
        self.effects.burst(self.bayan.pos, (255, 255, 255), 40, 260)
        tr = self.app.tr
        self.menu = MenuList(lambda: [("start", tr("tutorial.start")), ("menu", tr("tutorial.menu"))],
                             W / 2, 400, 320, 48, 12)
        pygame.mouse.set_visible(True)

    def advance(self):
        self.progress += 1
        if self.progress >= GOALS[self.step]:
            self.app.sfx.play("power")
            self.effects.burst(self.bayan.pos, (255, 230, 120), 30, 220)
            self.float_text(self.app.tr("tutorial.great"), self.bayan.pos, (255, 240, 140))
            self.gem = None
            self.wait = STEP_PAUSE
        elif self.step in ("gem", "snake"):
            self.spawn_gem()

    def spawn_gem(self):
        self.gem = V(GEM_SPOTS[self.gem_i % len(GEM_SPOTS)])
        self.gem_i += 1

    def float_text(self, s, pos, color):
        img = self.app.text.render(s, self.app.text.mid, color).copy()
        self.effects.floater(img, V(pos) - V(0, 40), 1.4)

    # ---------------------------------------------------------------- input
    def handle_event(self, e):
        if self.step == "done":
            result = self.menu.handle_event(e)
            if result and result[1] == "activate":
                self.app.sfx.play("select")
                if result[0] == "start":
                    self.app.start_level(0)
                else:
                    self.app.show_menu()
            elif result:
                self.app.sfx.play("click")
            return
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_ESCAPE:
            self.app.save["tutorial_done"] = True
            self.app.save.write()
            self.then()
        elif e.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
            if self.bayan.try_dash():
                self.app.sfx.play("dash")
                if self.step == "dash" and self.wait <= 0:
                    self.app.sfx.play("gem")
                    self.advance()

    # ---------------------------------------------------------------- update
    def update(self, dt):
        super().update(dt)
        self.effects.update(dt)
        self.ambient.update(dt, self.t)
        if self.step == "done":
            return
        if self.wait > 0:
            self.wait -= dt
            if self.wait <= 0:
                self.next_step()
                return

        k = pygame.key.get_pressed()
        direction = V((k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a]),
                      (k[pygame.K_DOWN] or k[pygame.K_s]) - (k[pygame.K_UP] or k[pygame.K_w]))
        self.update_step(dt, direction)

    def update_step(self, dt, direction):
        b = self.bayan
        b.update(dt, direction, [])
        if self.wait > 0:
            return
        if self.step == "move":
            if (MOVE_TARGETS[self.progress] - b.pos).length() < 28:
                self.app.sfx.play("gem")
                self.effects.burst(b.pos, (150, 230, 255), 14, 150)
                self.advance()
        elif self.gem is not None and (self.gem - b.pos).length() < b.R + 14:
            self.app.sfx.play("gem")
            self.effects.burst(self.gem, (255, 230, 80))
            self.advance()
        if self.step == "power" and self.power and (self.power.pos - b.pos).length() < b.R + 16:
            self.shield = True
            self.effects.burst(self.power.pos, (120, 190, 255), 22, 200)
            self.float_text(self.app.tr("power.shield"), self.power.pos, (200, 230, 255))
            self.power = None
            self.advance()
        if self.step == "snake":
            self.snake.update(dt, b, True, [], [], self.t)
            if not b.safe and self.snake.catches(b):
                b.invuln = 1.5
                self.snake.sleep = 1.0
                if self.shield:
                    self.shield = False
                    self.app.sfx.play("shield")
                    self.float_text(self.app.tr("float.shield_saved"), b.pos, (160, 210, 255))
                else:
                    self.app.sfx.play("hit")
                    self.float_text(self.app.tr("tutorial.caught"), b.pos, (255, 150, 150))
                far = V(W - 60 if b.pos.x < W / 2 else 60, H - 60 if b.pos.y < (TOP + H) / 2 else TOP + 60)
                self.snake.place(far, b.pos)

    # ---------------------------------------------------------------- drawing
    def draw(self, surf):
        t, b = self.t, self.bayan
        surf.blit(background("grass"), (0, 0))
        if self.step == "move" and self.wait <= 0:
            self.draw_target(surf, MOVE_TARGETS[self.progress])
        if self.gem is not None:
            draw_gem(surf, self.gem, t)
            self.draw_pointer(surf, self.gem)
        if self.power:
            self.power.draw(surf, t)
            self.draw_pointer(surf, self.power.pos)
        if self.step == "snake":
            self.snake.draw(surf, t)
        if self.step != "done":
            b.draw(surf, t, self.app.name_label(), shield=self.shield)
        self.ambient.draw(surf, t)
        self.effects.draw(surf)
        surf.blit(vignette(surf.get_size()), (0, 0))
        if self.step == "done":
            self.draw_done(surf)
        else:
            self.draw_banner(surf)
            self.draw_keys(surf)

    def draw_target(self, surf, pos):
        pulse = math.sin(self.t * 5)
        glow = pygame.Surface((110, 110), pygame.SRCALPHA)
        aa_circle(glow, (120, 220, 255, 90), (55, 55), 42 + pulse * 4)
        aa_circle(glow, (255, 255, 255, 255), (55, 55), 30 + pulse * 3, 5)
        aa_circle(glow, (90, 200, 255, 255), (55, 55), 25 + pulse * 3, 3)
        surf.blit(glow, (pos.x - 55, pos.y - 55))
        self.draw_pointer(surf, pos)

    def draw_pointer(self, surf, pos):
        """A bouncing arrow above the thing to go to."""
        y = pos.y - 42 - abs(math.sin(self.t * 4)) * 10
        pts = [(pos.x - 10, y - 14), (pos.x + 10, y - 14), (pos.x, y)]
        pygame.draw.polygon(surf, (255, 255, 255), pts)
        pygame.draw.polygon(surf, (60, 60, 80), pts, 2)

    def draw_banner(self, surf):
        text, tr = self.app.text, self.app.tr
        box = pygame.Rect(W / 2 - 420, 14, 840, 96)
        panel(surf, box, color=(35, 30, 55), alpha=225)
        text.draw(surf, tr("tutorial.step", n=self.step_i + 1, total=len(STEPS)), text.tiny, (255, 220, 120),
                  (box.centerx, box.y + 20))
        text.draw(surf, tr(f"tutorial.{self.step}"), text.mid, (255, 255, 255), (box.centerx, box.y + 52))
        goal = GOALS[self.step]
        for i in range(goal):
            x = box.centerx - (goal - 1) * 14 + i * 28
            draw_star(surf, x, box.bottom - 14, 9, i < self.progress)
        text.draw(surf, tr("tutorial.skip"), text.tiny, (220, 220, 230), (W / 2, H - 14))

    def draw_keys(self, surf):
        text, tr = self.app.text, self.app.tr
        k = pygame.key.get_pressed()
        if self.step == "move":
            cx, y = W / 2, H - 150
            draw_keycap(surf, text, "^", (cx - 26, y, 52, 46), k[pygame.K_UP] or k[pygame.K_w])
            for dx, label, keys in ((-58, "<", (pygame.K_LEFT, pygame.K_a)), (0, "v", (pygame.K_DOWN, pygame.K_s)),
                                    (58, ">", (pygame.K_RIGHT, pygame.K_d))):
                draw_keycap(surf, text, label, (cx + dx - 26, y + 54, 52, 46), any(k[x] for x in keys))
        elif self.step == "dash":
            draw_keycap(surf, text, "Space", (W / 2 - 130, H - 110, 260, 50), k[pygame.K_SPACE])
        hint = HINTS.get(self.step)
        if hint:
            text.draw(surf, tr(hint), text.small, (255, 255, 255), (W / 2, H - 40))

    def draw_done(self, surf):
        text, tr = self.app.text, self.app.tr
        overlay(surf, 140)
        text.draw(surf, tr("tutorial.done_title"), text.huge, (255, 235, 120), (W / 2, 190),
                  outline=((90, 30, 70), 3))
        text.draw(surf, tr("tutorial.done_text"), text.mid, (255, 255, 255), (W / 2, 270))
        for i in range(3):
            draw_star(surf, W / 2 - 70 + i * 70, 335, 22)
        self.menu.draw(surf, text, self.t)
