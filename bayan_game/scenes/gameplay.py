"""Playing one level: intro countdown, play, pause, level complete and game over."""
import math
import random

import pygame
from pygame import Vector2 as V

from .. import config
from ..config import W, H, TOP
from ..content.levels import LEVELS
from ..content.shop import dress_color
from ..entities.bayan import Bayan
from ..entities.boss import Boss
from ..entities.effects import Effects
from ..entities.obstacles import Rock, Zone
from ..entities.pickups import PowerUp
from ..entities.snake import Snake
from ..graphics.ambient import Ambient
from ..graphics.art import background, draw_coin, draw_gem, draw_heart, draw_star, vignette
from ..graphics.hud import draw_hud
from ..graphics.ui import MenuList, overlay
from .base import Scene

INTRO_TIME = 3.0
CENTER = V(W / 2, (TOP + H) / 2)
CORNERS = (V(60, TOP + 60), V(W - 60, TOP + 60), V(60, H - 60), V(W - 60, H - 60))
GEM_RADIUS = 14


class GameplayScene(Scene):
    show_cursor = False

    def __init__(self, app, level_index):
        super().__init__(app)
        self.level_index = level_index
        self.cfg = LEVELS[level_index]
        self.terrain = self.cfg["terrain"]
        self.music = f"level_{level_index + 1}"      # every level has its own track
        self.ambience = self.terrain
        self.effects = Effects()
        self.ambient = Ambient(self.terrain)
        self.state = "intro"
        self.state_t = 0.0
        self.menu = None
        self.result = None
        self.build_level()

    # ================================================================ setup
    def build_level(self):
        cfg, save = self.cfg, self.app.save
        speed_mult = config.DIFFICULTY_SPEED[save["difficulty"]]
        self.lives = config.START_LIVES
        self.collected = 0
        self.goal = cfg["gems"]
        self.level_coins = 0
        self.rocks, self.zones = [], []
        self.power = None
        self.power_timer = random.uniform(4.0, 7.0)
        self.timers = {"speed": 0.0, "ghost": 0.0, "freeze": 0.0}
        self.shield = False
        self.heart = None
        self.minion_spawned = False

        lo, hi = cfg.get("rock_size", (22, 38))
        for _ in range(cfg["rocks"]):
            spot = self.free_spot(lambda: random.randint(lo, hi), min_center=140, min_corner=130, gap=60)
            if spot:
                self.rocks.append(Rock(spot[0].x, spot[0].y, spot[1]))
        for kind, count, size in (("sand", cfg.get("sand", 0), (45, 60)), ("bush", cfg.get("bushes", 0), (42, 55))):
            for _ in range(count):
                spot = self.free_spot(lambda: random.randint(*size), min_center=120, min_corner=90, gap=20)
                if spot:
                    self.zones.append(Zone(kind, spot[0], spot[1]))

        self.bayan = Bayan(CENTER.x, CENTER.y, dress_color(save["dress"]), save["hat"])
        corners = list(CORNERS)
        random.shuffle(corners)
        self.snakes = []
        self.boss = None
        for i, kind in enumerate(cfg["snakes"]):
            if kind == "boss":
                snake = self.boss = Boss(corners[i], cfg, speed_mult)
            else:
                snake = Snake(corners[i], kind, cfg, speed_mult, phase=i * 2.1)
            snake.place(corners[i], CENTER)
            snake.sleep = 0.4 * i
            self.snakes.append(snake)
        self.spawn_gem()

    def free_spot(self, radius_fn, min_center, min_corner, gap):
        """Random spot for a round object that doesn't overlap rocks or zones."""
        for _ in range(100):
            r = radius_fn()
            p = V(random.uniform(80, W - 80), random.uniform(TOP + 80, H - 80))
            if (p - CENTER).length() < min_center:
                continue
            if any((p - c).length() < min_corner for c in CORNERS):
                continue
            if any((p - o.pos).length() < r + o.r + gap for o in self.rocks + self.zones):
                continue
            return p, r
        return None

    def pickup_spot(self, avoid, min_dist):
        """Random spot reachable by Bayan, away from the given points."""
        for _ in range(200):
            p = V(random.uniform(40, W - 40), random.uniform(TOP + 40, H - 40))
            if any((p - r.pos).length() < r.r + GEM_RADIUS + 8 for r in self.rocks):
                continue
            if any(z.kind == "bush" and (p - z.pos).length() < z.r + GEM_RADIUS for z in self.zones):
                continue
            if any((p - a).length() < min_dist for a in avoid):
                continue
            return p
        return V(CENTER)

    def spawn_gem(self):
        avoid = [self.bayan.pos] + [s.head for s in self.snakes]
        self.gem = self.pickup_spot(avoid, 160)

    # ================================================================ states
    def enter(self):
        super().enter()
        self.refresh_cursor()

    def refresh_cursor(self):
        pygame.mouse.set_visible(self.state not in ("intro", "play"))

    def set_state(self, state):
        self.state = state
        self.state_t = 0.0
        tr = self.app.tr
        last = self.level_index + 1 >= len(LEVELS)
        if state == "paused":
            keys = ("resume", "restart", "settings", "levels", "main_menu")
            self.menu = MenuList(lambda: [(k, tr(f"pause.{k}")) for k in keys], W / 2, 220, 320, 46, 10)
        elif state == "done":
            first = ("finish", tr("done.finish")) if last else ("next", tr("done.next"))
            self.menu = MenuList(lambda: [first, ("replay", tr("done.replay")), ("levels", tr("done.levels"))],
                                 W / 2, 400, 300, 44, 10)
        elif state == "over":
            keys = ("retry", "levels", "main_menu")
            self.menu = MenuList(lambda: [(k, tr(f"over.{k}")) for k in keys], W / 2, 360, 300, 46, 10)
        else:
            self.menu = None
        self.refresh_cursor()

    def handle_event(self, e):
        app = self.app
        if self.state == "play":
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    if self.bayan.try_dash():
                        app.sfx.play("dash")
                elif e.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.set_state("paused")
            return
        if self.state == "paused" and e.type == pygame.KEYDOWN and e.key in (pygame.K_p, pygame.K_ESCAPE):
            self.set_state("play")
            return
        if not self.menu or (self.state in ("done", "over") and self.state_t < 0.6):
            return
        result = self.menu.handle_event(e)
        if not result:
            return
        key, action = result
        if action == "move":
            app.sfx.play("click")
            return
        if action != "activate":
            return
        app.sfx.play("select")
        if key == "resume":
            self.set_state("play")
        elif key in ("restart", "retry", "replay"):
            app.start_level(self.level_index)
        elif key == "settings":
            app.show_settings(back=self)
        elif key == "levels":
            app.show_levels(self.level_index)
        elif key == "main_menu":
            app.show_menu()
        elif key == "next":
            app.start_level(self.level_index + 1)
        elif key == "finish":
            app.show_victory()

    # ================================================================ update
    def update(self, dt):
        super().update(dt)
        self.state_t += dt
        self.effects.update(dt)
        if self.state != "paused":
            self.ambient.update(dt, self.t)
        if self.state == "intro" and self.state_t >= INTRO_TIME:
            self.set_state("play")
        elif self.state == "play":
            self.update_play(dt)

    def read_direction(self):
        k = pygame.key.get_pressed()
        x = (k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a])
        y = (k[pygame.K_DOWN] or k[pygame.K_s]) - (k[pygame.K_UP] or k[pygame.K_w])
        return V(x, y)

    @property
    def hidden(self):
        in_bush = any(z.kind == "bush" and z.contains(self.bayan.pos, 6) for z in self.zones)
        return self.timers["ghost"] > 0 or in_bush

    def update_play(self, dt, direction=None):
        b = self.bayan
        if direction is None:
            direction = self.read_direction()
        for k in self.timers:
            self.timers[k] = max(0.0, self.timers[k] - dt)
        for z in self.zones:
            z.update(dt)
        self.zones = [z for z in self.zones if not z.expired]

        slow = any(z.kind in ("sand", "poison") and z.contains(b.pos) for z in self.zones)
        b.update(dt, direction, self.rocks, slow=slow, ice=self.terrain == "snow", boost=self.timers["speed"] > 0)

        visible = not self.hidden
        frozen = self.timers["freeze"] > 0
        for s in list(self.snakes):
            if not frozen:
                for event, data in s.update(dt, b, visible, self.rocks, self.zones, self.t):
                    self.on_snake_event(s, event, data)
            if not b.safe and not frozen and s.catches(b):
                self.on_caught(s)
                if self.state != "play":
                    return

        if self.boss and self.boss.hp <= 0:
            self.effects.burst(self.boss.head, (255, 200, 80), 60, 320)
            self.complete_level()
            return

        self.update_pickups(dt)

    def on_snake_event(self, snake, event, data):
        app = self.app
        if event == "hiss":
            app.sfx.play("hiss")
        elif event == "puddle":
            self.zones.append(Zone("poison", data, 24, life=6.0))
        elif event == "boss_hit":
            if data in self.rocks:
                self.rocks.remove(data)
            app.sfx.play("boss_hit")
            app.shake(0.5)
            self.effects.burst(data.pos, (150, 140, 130), 30, 250)
            self.float_text(self.app.tr("float.boss_hit"), snake.head, (255, 120, 120))
            if snake.hp == 1 and not self.minion_spawned:
                self.minion_spawned = True
                corner = max(CORNERS, key=lambda c: (c - self.bayan.pos).length())
                minion = Snake(corner, "small", dict(speed=120, turn=2.4, predict=0.2),
                               config.DIFFICULTY_SPEED[app.save["difficulty"]], phase=1.3)
                minion.place(corner, self.bayan.pos)
                minion.sleep = 1.0
                self.snakes.append(minion)
                self.float_text(self.app.tr("float.minion"), CENTER, (255, 230, 120))
        elif event == "boss_wall":
            app.shake(0.2)

    def on_caught(self, snake):
        b, app = self.bayan, self.app
        if self.shield:
            self.shield = False
            b.invuln = 1.5
            snake.sleep = 0.8
            app.sfx.play("shield")
            self.effects.burst(b.pos, (120, 190, 255), 25, 220)
            self.float_text(app.tr("float.shield_saved"), b.pos, (160, 210, 255))
            return
        self.lives -= 1
        app.shake(0.4)
        self.effects.burst(b.pos, (255, 80, 120), 30, 220)
        if self.lives <= 0:
            app.sfx.play("lose")
            app.save.write()
            self.set_state("over")
            return
        app.sfx.play("hit")
        b.invuln = config.HIT_INVULNERABILITY
        far = sorted(CORNERS, key=lambda c: -(c - b.pos).length())
        for i, s in enumerate(self.snakes):
            s.place(far[i % len(far)], b.pos)
            s.sleep = 1.0

    def update_pickups(self, dt):
        b, app = self.bayan, self.app
        reach = b.R + GEM_RADIUS

        if self.gem and (self.gem - b.pos).length() < reach:
            app.sfx.play("gem")
            self.effects.burst(self.gem, (255, 230, 80))
            self.float_text(app.tr("float.gem", n=config.COINS_PER_GEM), self.gem, (255, 230, 120))
            self.add_coins(config.COINS_PER_GEM)
            if self.goal:
                self.collected += 1
                for s in self.snakes:
                    s.grow()
                if self.collected >= self.goal:
                    self.gem = None
                    self.complete_level()
                    return
            self.spawn_gem()
            if self.heart is None and self.lives < config.START_LIVES and random.random() < 0.3:
                self.heart = [self.pickup_spot([b.pos], 120), 8.0]

        if self.heart:
            self.heart[1] -= dt
            if (self.heart[0] - b.pos).length() < reach:
                self.lives = min(config.START_LIVES, self.lives + 1)
                app.sfx.play("heart")
                self.effects.burst(self.heart[0], (255, 80, 120))
                self.heart = None
            elif self.heart[1] <= 0:
                self.heart = None

        if self.power:
            if not self.power.update(dt):
                self.power = None
            elif (self.power.pos - b.pos).length() < reach + 2:
                self.activate_power(self.power.kind, self.power.pos)
                self.power = None
        else:
            self.power_timer -= dt
            if self.power_timer <= 0:
                self.power_timer = random.uniform(*config.POWER_SPAWN_DELAY)
                spot = self.pickup_spot([b.pos] + [s.head for s in self.snakes], 120)
                self.power = PowerUp(random.choice(config.POWER_KINDS), spot)

    def activate_power(self, kind, pos):
        app = self.app
        app.sfx.play("power")
        self.effects.burst(pos, (200, 230, 255), 22, 200)
        self.float_text(app.tr(f"power.{kind}"), pos, (255, 255, 255))
        if kind == "shield":
            self.shield = True
        else:
            self.timers[kind] = config.POWER_DURATION[kind]

    def active_powers(self):
        """(kind, time left, total time) for the HUD; shield has no timer."""
        out = [(k, left, config.POWER_DURATION[k]) for k, left in self.timers.items() if left > 0]
        if self.shield:
            out.append(("shield", 1, 0))
        return out

    def add_coins(self, n):
        self.app.save["coins"] += n
        self.level_coins += n

    def float_text(self, s, pos, color):
        img = self.app.text.render(s, self.app.text.small, color).copy()
        self.effects.floater(img, V(pos) - V(0, 30))

    def complete_level(self):
        app, save = self.app, self.app.save
        stars = max(1, self.lives)
        bonus = stars * config.COINS_PER_STAR + (config.BOSS_COINS if self.boss else 0)
        self.add_coins(bonus)
        save.record_stars(self.level_index, stars)
        save.unlock(self.level_index + 2)
        save.write()
        self.result = dict(stars=stars, coins=self.level_coins)
        app.sfx.play("level")
        self.effects.burst(self.bayan.pos, (255, 255, 255), 40, 260)
        self.set_state("done")

    # ================================================================ drawing
    def draw(self, surf):
        t = self.t
        surf.blit(background(self.terrain), (0, 0))
        for z in self.zones:
            if z.kind != "bush":
                z.draw(surf, t)
        for r in self.rocks:
            r.draw(surf, self.terrain)
        if self.gem:
            draw_gem(surf, self.gem, t)
        if self.heart and (self.heart[1] > 2 or int(t * 8) % 2):
            draw_heart(surf, int(self.heart[0].x), int(self.heart[0].y + math.sin(t * 4) * 3), 22)
        if self.power:
            self.power.draw(surf, t)

        frozen = self.timers["freeze"] > 0
        for s in self.snakes:
            s.draw(surf, t, frozen)
        if self.state != "over":
            alpha = 110 if self.timers["ghost"] > 0 else 255
            self.bayan.draw(surf, t, self.app.name_label(), alpha, self.shield)
        in_bush = any(z.kind == "bush" and z.contains(self.bayan.pos, 6) for z in self.zones)
        for z in self.zones:
            if z.kind == "bush":
                z.draw(surf, t, see_through=in_bush and z.contains(self.bayan.pos))
        if frozen:
            overlay(surf, 35, (150, 210, 255))
        self.ambient.draw(surf, t)
        self.effects.draw(surf)
        surf.blit(vignette(surf.get_size()), (0, 0))
        draw_hud(surf, self.app, self)

        draw_state = getattr(self, f"draw_{self.state}", None)
        if draw_state:
            draw_state(surf)

    def draw_intro(self, surf):
        text, tr = self.app.text, self.app.tr
        cx, cy = CENTER
        overlay(surf, 120)
        text.draw(surf, tr("intro.level", n=self.level_index + 1), text.huge, (255, 220, 240), (cx, cy - 110), outline=((90, 30, 70), 3))
        text.draw(surf, tr(f"terrain.{self.terrain}"), text.mid, (255, 235, 160), (cx, cy - 55))
        if self.boss:
            goal = tr("intro.boss_goal")
        else:
            goal = tr("intro.goal", gems=self.goal, snakes=len(self.snakes))
        text.draw(surf, goal, text.mid, (255, 255, 255), (cx, cy - 10))
        text.draw(surf, tr(f"level_tips.{self.level_index}"), text.small, (230, 240, 230), (cx, cy + 30))
        count = max(1, INTRO_TIME - int(self.state_t))
        text.draw(surf, str(int(count)), text.huge, (255, 235, 120), (cx, cy + 110), outline=((90, 30, 70), 3))

    def draw_paused(self, surf):
        overlay(surf, 160)
        self.app.text.draw(surf, self.app.tr("pause.title"), self.app.text.big, (255, 255, 255), (W / 2, 160), outline=((90, 30, 70), 3))
        self.menu.draw(surf, self.app.text, self.t)

    def draw_done(self, surf):
        text, tr = self.app.text, self.app.tr
        overlay(surf, 140)
        title = tr("done.boss_title") if self.boss else tr("done.title")
        text.draw(surf, title, text.huge, (255, 235, 120), (W / 2, 150), outline=((90, 30, 70), 3))
        for i in range(3):
            appear = self.state_t - 0.3 - i * 0.3
            if appear < 0:
                continue
            r = 34 * min(1.0, appear * 4)
            draw_star(surf, W / 2 - 90 + i * 90, 250, r, i < self.result["stars"])
        draw_coin(surf, W / 2 - 60, 330, 12)
        text.draw(surf, tr("done.coins", n=self.result["coins"]), text.mid, (255, 230, 120), (W / 2 + 10, 330))
        self.menu.draw(surf, text, self.t)

    def draw_over(self, surf):
        text, tr = self.app.text, self.app.tr
        overlay(surf, 170)
        text.draw(surf, tr("over.title"), text.huge, (255, 110, 110), (W / 2, 200), outline=((90, 30, 70), 3))
        draw_coin(surf, W / 2 - 60, 285, 12)
        text.draw(surf, tr("done.coins", n=self.level_coins), text.mid, (255, 230, 120), (W / 2 + 10, 285))
        self.menu.draw(surf, text, self.t)
